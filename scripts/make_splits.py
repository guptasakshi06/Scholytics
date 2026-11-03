#!/usr/bin/env python3
"""Create reproducible development-only assignments from input-only bundle reuse."""
import argparse
from pathlib import Path
from scholarready.dataset import sha256
from scholarready.pipeline import write_json
from scholarready.splitting import context, make_development_splits, validate_splits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    records, meta, groups, hashes = context(args.manifest, args.root)
    splits = make_development_splits(records, groups, sha256(args.manifest), meta['dataset_version'], args.seed)
    report = validate_splits(records, splits, groups, sha256(args.manifest))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as file:
        file.write('\n'.join(s.model_dump_json() for s in splits) + '\n')
    write_json(args.output.with_suffix('.metadata.json'), dict(report, bundle_hashes=hashes,
        split_hash=sha256(args.output), policy='connected applicant/source/hash/file/input-bundle; nested development only',
        layout_probe='fixed untuned layout_a -> layout_b diagnostic where feasible; no final-test claim'))
    print(report)


if __name__ == '__main__':
    main()
