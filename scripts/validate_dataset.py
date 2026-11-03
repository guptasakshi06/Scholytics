#!/usr/bin/env python3
"""Validate pilot provenance, page/reference integrity, source links and bundles."""
import argparse
import json
from pathlib import Path
from scholarready.dataset import validate_dataset


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        manifest = args.manifest if args.manifest.is_absolute() else args.root / args.manifest
        result = validate_dataset(args.root, manifest)
    except (ValueError, OSError, KeyError, TypeError, RuntimeError) as exc:
        result = {"status": "failed", "error": str(exc)}
    serialized = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized)
    print(serialized, end="")
    raise SystemExit(0 if result["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
