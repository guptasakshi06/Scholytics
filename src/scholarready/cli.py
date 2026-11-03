"""Thin command-line adapter to the shared pipeline."""
import argparse
import json
import os
from pathlib import Path
import shlex
import sys

from . import __version__
from .classification import LearnedClassifier
from .config import load_config
from .ingestion import IngestionLimits, SUPPORTED
from .ocr import OCRSettings
from .pipeline import analyze
from .preprocessing import load_preprocessing
from .schemas import ApplicantProfile, BundleInput


def discover(path: Path, max_files: int) -> list[Path]:
    if not path.is_dir():
        return [path]
    files = []
    # Immediate media files only; do not parse any directory metadata/reference JSON.
    with os.scandir(path) as entries:
        for index, entry in enumerate(entries):
            if index >= 2000:
                raise ValueError('Directory entry limit (2000) exceeded; select a smaller input directory')
            if entry.is_file() and Path(entry.name).suffix.lower() in SUPPORTED:
                files.append(Path(entry.path))
                if len(files) > max_files:
                    raise ValueError(f'directory exceeds max_files={max_files}')
    if not files:
        raise ValueError('No PNG, JPG/JPEG or PDF input files found in directory (nonrecursive)')
    return sorted(files)


def main() -> None:
    parser = argparse.ArgumentParser(description='ScholarReady: local academic document readiness')
    parser.add_argument('--version', action='version', version=__version__)
    commands = parser.add_subparsers(dest='command', required=True)
    validate = commands.add_parser('validate-config', help='validate and print a fictional checklist')
    validate.add_argument('path')
    for command in ('analyze', 'demo'):
        sub = commands.add_parser(command, help='real local A/B/C OCR and limited baseline checklist')
        if command == 'analyze':
            source = sub.add_mutually_exclusive_group(required=True)
            source.add_argument('--input', type=Path, help='one image/PDF or nonrecursive media directory')
            source.add_argument('--bundle', type=Path, help='input-only JSON inventory; no expected/reference JSON')
            sub.add_argument('--input-root', type=Path, default=Path.cwd(), help='base for repository-relative bundle files; default working directory')
            sub.add_argument('--applicant-profile', type=Path, help='explicit attributes; overrides bundle profile')
        sub.add_argument('--profile', type=Path, default=Path('configs/scholarship_demo.json'))
        sub.add_argument('--branch', choices=['A', 'B', 'C'], default='A')
        sub.add_argument('--preprocessing', type=Path, help='DIP/quality JSON; defaults to dip-1.0')
        sub.add_argument('--classifier', type=Path, help='trusted local learned-model directory; default keyword baseline')
        sub.add_argument('--output', type=Path, required=True, help='new run directory (must not exist)')
        sub.add_argument('--ocr-timeout', type=float, default=20.)
        sub.add_argument('--psm', type=int, default=3)
        sub.add_argument('--max-files', type=int, default=20)
        sub.add_argument('--max-pages', type=int, default=40)
        sub.add_argument('--max-page-pixels', type=int, default=20_000_000)
        sub.add_argument('--max-total-pixels', type=int, default=100_000_000)
        sub.add_argument('--pdf-dpi', type=int, default=300)
    args = parser.parse_args()
    try:
        if args.command == 'validate-config':
            print(load_config(args.path).model_dump_json(indent=2))
            return
        config = load_config(args.profile)
        hints = {}
        if args.command == 'demo':
            # Tiny versioned fictional media; no generated labels or bulk dataset required.
            fixture_root = Path(__file__).resolve().parents[2] / 'tests/fixtures/pilot'
            paths = [fixture_root / f'src-{n:03d}.png' for n in range(1, 6)]
            applicant = ApplicantProfile(applicant_reference='fictional-demo',
                category_certificate_required=True, expected_name='Fictional Aster')
        elif args.bundle:
            bundle = BundleInput.model_validate_json(args.bundle.read_text(encoding='utf-8'))
            root = args.input_root.resolve()
            paths = [(root / name).resolve() for name in bundle.files]
            if any(not p.is_relative_to(root) for p in paths):
                raise ValueError('Bundle input symlink escapes --input-root')
            hints = {str((root / name).resolve()): hint for name, hint in bundle.declared_type_hints.items()}
            applicant = bundle.profile
        else:
            paths = discover(args.input, args.max_files)
            applicant = ApplicantProfile(applicant_reference='local-user')
        if args.command == 'analyze' and args.applicant_profile:
            applicant = ApplicantProfile.model_validate_json(args.applicant_profile.read_text(encoding='utf-8'))
        result = analyze(paths, config=config, applicant=applicant, output=args.output,
            classifier=LearnedClassifier.load(args.classifier) if args.classifier else None,
            hints=hints, branch=args.branch, preprocessing=load_preprocessing(args.preprocessing), settings=OCRSettings(psm=args.psm, timeout_seconds=args.ocr_timeout),
            limits=IngestionLimits(max_files=args.max_files, max_pages=args.max_pages,
                max_page_pixels=args.max_page_pixels, max_total_pixels=args.max_total_pixels, pdf_dpi=args.pdf_dpi),
            exact_command=shlex.join([sys.executable, '-m', 'scholarready', *sys.argv[1:]]))
        print(json.dumps(dict(run_id=result.run_id, overall_state=result.overall_state,
                             completeness=result.completeness, result_path=str(args.output.resolve() / 'result.json'))))
        if any(d.errors for d in result.documents):
            parser.exit(1, 'Processing errors preserved in result.json; review the failed inputs/pages.\n')
    except (OSError, ValueError) as exc:
        label = 'Configuration error' if args.command == 'validate-config' else 'Analysis error'
        parser.exit(2, f'{label}: {exc}\n')
