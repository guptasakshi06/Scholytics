#!/usr/bin/env python3
"""Reproduce local setup/CLI smoke or verify and recompute preserved final results."""
import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
from time import perf_counter
import uuid

ROOT = Path(__file__).resolve().parents[1]
TIMING_KEYS = {'ocr_seconds', 'preprocessing_seconds', 'end_to_end_page_seconds',
               'bundle_replay_rule_seconds', 'inference_index'}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inside(root, relative):
    path = (root / relative).resolve()
    require(path.is_relative_to(root.resolve()), f'Path escapes inventory root: {relative}')
    return path


def check_hashes(root, hashes):
    for relative, expected in hashes.items():
        path = inside(root, relative)
        require(path.is_file(), f'Missing packaged artifact: {relative}; see docs/REPRODUCIBILITY.md')
        require(digest(path) == expected, f'Artifact hash mismatch: {relative}')
    return len(hashes)


def semantic(value):
    if isinstance(value, dict):
        return {k: semantic(v) for k, v in value.items() if k not in TIMING_KEYS}
    if isinstance(value, list):
        return [semantic(v) for v in value]
    return value


def command(argv, output, name, expected=0):
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=180)
    write(output / (name + '.command.json'), dict(argv=argv, cwd=str(ROOT), exit_code=result.returncode))
    (output / (name + '.txt')).write_text(result.stdout + result.stderr, encoding='utf-8')
    require(result.returncode == expected, f'{name} exited {result.returncode}; inspect {output / (name + ".txt")}')


def smoke(output):
    # The environment checker is a sibling script, not a new production module.
    from check_environment import check_environment
    from scholarready.classification import LearnedClassifier
    from scholarready.schemas import ApplicationResult, ApplicantProfile, BundleInput

    environment = check_environment(output / 'environment', ocr_smoke=True)
    write(output / 'environment.json', environment)
    require(environment['status'] == 'passed', 'Environment check failed; inspect environment.json')
    mismatches = []
    for line in (ROOT / 'requirements.lock.txt').read_text().splitlines():
        if line and not line.startswith('#'):
            name, pinned = line.split('==')
            if version(name) != pinned:
                mismatches.append(name)
    require(not mismatches, 'Locked package versions differ: ' + ', '.join(mismatches))
    command([sys.executable, '-m', 'pip', 'check'], output, 'pip_check')
    model_path = ROOT / read(ROOT / 'configs/evaluation.json')['model']
    model = LearnedClassifier.load(model_path)
    require(model is not None, 'Frozen model reload failed')
    inputs = output / 'inputs'
    inputs.mkdir()
    fixtures = ROOT / 'tests/fixtures/pilot'
    for n in range(1, 6):
        shutil.copyfile(fixtures / f'src-{n:03d}.png', inputs / f'upload-{n}.png')
    shutil.copyfile(fixtures / 'src-002-p01-erased_content.png', inputs / 'erased.png')
    shutil.copyfile(fixtures / 'src-025.pdf', inputs / 'multipage.pdf')
    base = [sys.executable, '-m', 'scholarready']
    command(base + ['demo', '--profile', str(ROOT / 'configs/scholarship_demo.json'),
                    '--output', str(output / 'demo')], output, 'demo')
    demo = ApplicationResult.model_validate_json((output / 'demo/result.json').read_text())
    require((demo.overall_state, demo.completeness) == ('ready', 100.), 'Demo outcome differs')
    outcomes = {'demo': dict(overall_state=demo.overall_state, completeness=demo.completeness)}
    scenarios = [
        ('learned_complete', [f'upload-{n}.png' for n in range(1, 6)], True, 'ready', 100., True),
        ('missing_income', [f'upload-{n}.png' for n in (1, 3, 4, 5)], True, 'incomplete', 80., False),
        ('erased_income', ['upload-1.png', 'erased.png', 'upload-3.png', 'upload-4.png', 'upload-5.png'],
         True, 'needs_review', 80., False),
        ('pdf_unknown_category', ['multipage.pdf'], None, 'needs_review', None, False),
    ]
    for name, files, category, state, completeness, learned in scenarios:
        bundle = BundleInput(scenario_id='smoke-' + name, files=files, declared_type_hints={},
            profile=ApplicantProfile(applicant_reference='fictional-smoke',
                category_certificate_required=category, expected_name='Fictional Aster'))
        bundle_path = output / (name + '_inputs.json')
        write(bundle_path, bundle.model_dump(mode='json'))
        argv = base + ['analyze', '--bundle', str(bundle_path), '--input-root', str(inputs),
                       '--profile', str(ROOT / 'configs/scholarship_demo.json'),
                       '--output', str(output / name)]
        if learned:
            argv += ['--classifier', str(model_path)]
        command(argv, output, name)
        result = ApplicationResult.model_validate_json((output / name / 'result.json').read_text())
        require(result.overall_state == state, f'{name}: expected {state}, got {result.overall_state}')
        require(result.completeness == completeness, f'{name}: completeness differs')
        if name == 'missing_income':
            require(next(r.state for r in result.requirements if r.requirement_id == 'income') == 'missing',
                    'Missing income was not confirmed missing')
        if name == 'erased_income':
            require(next(r.state for r in result.requirements if r.requirement_id == 'income') != 'satisfied',
                    'Erased income was accepted')
        if name == 'pdf_unknown_category':
            require(len(result.documents[0].pages) == 2, 'PDF did not retain both pages')
        outcomes[name] = dict(overall_state=result.overall_state, completeness=result.completeness,
                              result_path=f'{name}/result.json')
    return dict(environment='environment.json', pip_check='passed', lock_versions='matched',
                model_sha256=digest(model_path / 'model.joblib'), outcomes=outcomes,
                inference_inputs='Renamed fictional media and explicit profiles; no references or annotations.',
                final_test_access=False, trained=False)


def final(output):
    from scholarready.classification import LearnedClassifier
    from scholarready.evaluation.experiment import (load_inference, page_predictions, bundle_predictions,
                                                   score_pages, score_bundles)
    from scholarready.evaluation.freeze import validate_freeze, selected_records

    config, frozen, support = validate_freeze(ROOT, ROOT / 'configs/evaluation.json')
    source = ROOT / 'artifacts/runs/s10-final'
    replay = ROOT / 'artifacts/runs/s10-replay'
    hashes = sum(check_hashes(p, read(p / 'artifact_hashes.json')) for p in (source, replay))
    assets = ROOT / 'docs/verification/s10/assets'
    check_hashes(assets, read(assets / 'asset_hashes.json'))
    copies = read(assets / 'compact_artifacts.json')
    for relative, entry in copies.items():
        check_hashes(ROOT, {relative: entry['sha256'], entry['source']: entry['sha256']})
    registry = read(ROOT / 'docs/verification/s10/run_registry.json')
    for item in registry['runs']:
        require(digest(inside(ROOT, item['consumption'])) == item['consumption_sha256'], 'Consumption record changed')
        for key, filename in [('run_sha256', 'run.json'), ('summary_sha256', 'summary.json')]:
            require(digest(inside(ROOT, item['output']) / filename) == item[key], 'Registered run changed')
    original = read(source / 'summary.json')
    require(semantic(original) == semantic(read(replay / 'summary.json')), 'Original saved replay differs')
    require(original['final_test_consumed'] is True, 'Final consumed status lost')
    records = selected_records(ROOT, config, 'test')
    bundles = [b for b in read((ROOT / config['manifest']).with_suffix('.metadata.json'))['bundles']
               if b['partition'] == 'test']
    model = LearnedClassifier.load(ROOT / config['model'])
    pending = []
    for spec in config['variants']:
        docs, index = load_inference(ROOT, source / spec['name'] / 'inference')
        require(index['selected_sample_ids'] == config['sample_ids']['test'], 'Saved sample selection differs')
        require(index['branch'] == spec['branch'] and index['preprocessing'] == spec['preprocessing'],
                'Saved preprocessing differs')
        for route, classifier in [('keyword', None)] + ([('learned', model)] if spec['name'] == 'A' else []):
            pages = page_predictions(records, docs, classifier)
            apps, seconds = bundle_predictions(ROOT, bundles, docs, classifier)
            folder = source / spec['name']
            require(semantic(pages) == semantic(read(folder / (route + '_pages_before_references.json'))),
                    f'Page predictions differ: {spec["name"]}/{route}')
            require(apps == read(folder / (route + '_bundles_before_references.json')),
                    f'Bundle predictions differ: {spec["name"]}/{route}')
            dest = output / spec['name']
            write(dest / (route + '_pages_before_references.json'), pages)
            write(dest / (route + '_bundles_before_references.json'), apps)
            pending.append((spec['name'], route, pages, apps, seconds))
    reports = []
    # Reuse the frozen scoring code only after every saved-OCR prediction was verified.
    for name, route, pages, apps, seconds in pending:
        metrics, rows = score_pages(ROOT, records, pages)
        readiness, bundle_rows = score_bundles(ROOT, bundles, apps)
        report = dict(name=name, route=route, page_metrics=metrics, readiness=readiness)
        prior = next(r for r in original['reports'] if (r['name'], r['route']) == (name, route))
        require(semantic(report) == semantic({k: prior[k] for k in report}), f'Metrics differ: {name}/{route}')
        require(semantic(rows) == semantic(read(source / name / (route + '_scored_pages.json'))), 'Scored pages differ')
        require(bundle_rows == read(source / name / (route + '_scored_bundles.json')), 'Scored bundles differ')
        reports.append(report)
    write(output / 'recomputed_summary.json', dict(partition='test', reports=reports, final_test_consumed=True))
    return dict(freeze_sha256=digest(ROOT / config['freeze_record']), frozen_files=len(frozen['artifact_hashes']),
                original_run_hashes=hashes, compact_files=len(copies), routes=len(reports),
                pages_per_route=len(records), bundles_per_route=len(bundles), support=support,
                semantic_predictions_and_metrics='identical', trained=False, new_ocr=False,
                source_run='artifacts/runs/s10-final', saved_replay='artifacts/runs/s10-replay',
                final_test_consumed=True, new_test_experiment=False,
                scope='Artifact verification and saved-OCR computation only; original timings retained, no new performance evidence.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['smoke', 'final'], required=True)
    parser.add_argument('--output', type=Path, help='NEW output directory; default unique artifacts/runs/reproduce-*')
    args = parser.parse_args()
    output = (args.output or ROOT / 'artifacts/runs' / f'reproduce-{args.mode}-{uuid.uuid4().hex[:10]}').resolve()
    os.chdir(ROOT)
    started = perf_counter()
    try:
        output.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.exit(2, f'Output already exists; choose a new directory: {output}\n')
    report = dict(mode=args.mode, command=shlex.join([sys.executable, *sys.argv]), root=str(ROOT),
                  python=platform.python_version(), executable=sys.executable,
                  started_utc=datetime.now(timezone.utc).isoformat())
    try:
        report['checks'] = (smoke if args.mode == 'smoke' else final)(output)
        report['status'] = 'passed'
    except Exception as exc:
        report.update(status='failed', error=f'{type(exc).__name__}: {exc}')
    report['wall_seconds'] = perf_counter() - started
    write(output / 'reproduction.json', report)
    print(json.dumps(dict(status=report['status'], mode=args.mode, output=str(output),
                         wall_seconds=report['wall_seconds'], error=report.get('error'))))
    raise SystemExit(0 if report['status'] == 'passed' else 1)


if __name__ == '__main__':
    main()
