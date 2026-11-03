"""Foundation commands only; document analysis arrives in S03."""
import argparse
from . import __version__
from .config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="ScholarReady: local academic document readiness")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate-config", help="validate and print a fictional checklist")
    validate.add_argument("path")
    args = parser.parse_args()
    if args.command == "validate-config":
        try:
            print(load_config(args.path).model_dump_json(indent=2))
        except (OSError, ValueError) as exc:
            parser.exit(2, f"Configuration error: {exc}\n")


if __name__ == "__main__":
    main()
