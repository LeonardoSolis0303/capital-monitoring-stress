"""CLI: 0 complete / 1 selected baseline blocked / 2 invalid input or integrity."""

import argparse
import json
from pathlib import Path
import sys

from .reporting import run, verify


def main(argv=None):
    parser = argparse.ArgumentParser(description="Capital monitoring review pack")
    commands = parser.add_subparsers(dest="command", required=True)
    execute = commands.add_parser("run")
    execute.add_argument("--input", type=Path, required=True)
    execute.add_argument("--output", type=Path, required=True)
    integrity = commands.add_parser("verify")
    integrity.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            verify(args.output)
            print("Output integrity verified")
            return 0
        summary = run(args.input, args.output)
        print(json.dumps(summary, sort_keys=True))
        return 1 if summary["baseline_blocked"] else 0
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(f"capital-monitor: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
