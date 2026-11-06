#!/usr/bin/env python3
"""Create a local source + frozen evidence archive; never upload or include private data."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
TOP_FILES = ('AGENTS.md', 'HANDOFF.md', 'README.md', 'pyproject.toml', 'requirements.lock.txt', '.gitignore')
SOURCE_DIRS = ('src', 'app', 'scripts', 'tests', 'configs', 'docs')
SKIP_PARTS = {'__pycache__', '.pytest_cache', '.git', '.env', 'private'}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def collect(root):
    """Use an allowlist, including ignored assets required by the unchanged freeze/runs."""
    paths = {root / p for p in TOP_FILES}
    for directory in SOURCE_DIRS + ('data',):
        for path in (root / directory).rglob('*'):
            parts = path.relative_to(root).parts
            if directory == 'data' and len(parts) > 1 and parts[1] in ('private', 'synthetic'):
                continue
            if path.is_file() and not any(p in SKIP_PARTS or p.endswith('.egg-info') for p in parts):
                paths.add(path)
    freeze = json.loads((root / 'docs/verification/s09/freeze.json').read_text())
    paths.update(root / p for p in freeze['artifact_hashes'])
    for name in ('s10-final', 's10-replay'):
        paths.update(p for p in (root / 'artifacts/runs' / name).rglob('*') if p.is_file())
    for path in paths:
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f'Symlink or external file is not packageable: {path}')
        if not path.is_file():
            raise ValueError(f'Missing deliverable: {path}')
        parts = path.relative_to(root).parts
        if any(p in SKIP_PARTS or p.startswith('.venv') or p.startswith('.env') for p in parts):
            raise ValueError(f'Excluded file requested by inventory: {path}')
    return sorted(paths)


def verify(root):
    root = root.resolve()
    manifest = json.loads((root / 'SUBMISSION_MANIFEST.json').read_text())
    for relative, entry in manifest['files'].items():
        path = root / relative
        if not path.resolve().is_relative_to(root) or path.is_symlink():
            raise ValueError(f'Unsafe manifest path: {relative}')
        if not path.is_file() or path.stat().st_size != entry['bytes'] or digest(path) != entry['sha256']:
            raise ValueError(f'Packaged file missing or changed: {relative}')
        if any(p in SKIP_PARTS or p.startswith('.venv') or p.startswith('.env') for p in Path(relative).parts):
            raise ValueError(f'Excluded file in package: {relative}')
    return dict(status='passed', files=len(manifest['files']), private_data=False,
                environments=False, symlinks=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--output', type=Path, help='NEW directory for archive and exact inventory')
    mode.add_argument('--verify-root', type=Path, help='Verify an extracted SUBMISSION_MANIFEST.json')
    args = parser.parse_args()
    if args.verify_root:
        print(json.dumps(verify(args.verify_root)))
        return
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    paths = collect(ROOT)
    # Keep outputs out of the inventory even when the caller selected docs/ or data/.
    if any(p.is_relative_to(output) for p in paths):
        raise ValueError('Package output overlaps an included source directory')
    inventory = {p.relative_to(ROOT).as_posix(): dict(sha256=digest(p), bytes=p.stat().st_size) for p in paths}
    inventory_path = output / 'inventory.json'
    inventory_path.write_text(json.dumps(dict(format='scholarready-submission-1', files=inventory,
        excludes=['Git metadata', 'virtual environments', 'private data', 'secrets',
                  'unselected historical generated runs', 'dependency wheels'],
        frozen_final_test_consumed=True, trained=False,
        note='Preserves original bytes and historical absolute provenance; executable paths resolve relative to extracted root.'), indent=2) + '\n')
    archive = output / 'scholarready-s11.tar.gz'
    with tarfile.open(archive, 'x:gz', compresslevel=6) as tar:
        for path in paths:
            tar.add(path, arcname='ScholarReady/' + path.relative_to(ROOT).as_posix(), recursive=False)
        tar.add(inventory_path, arcname='ScholarReady/SUBMISSION_MANIFEST.json')
    report = dict(status='created', files=len(paths), uncompressed_bytes=sum(v['bytes'] for v in inventory.values()),
                  archive=archive.name, archive_bytes=archive.stat().st_size, sha256=digest(archive),
                  inventory_sha256=digest(inventory_path))
    (output / 'package.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
