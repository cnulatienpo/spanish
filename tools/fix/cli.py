from __future__ import annotations

import argparse
import json
from typing import Optional

from . import run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Repair and normalize Spanish learning corpora.")
    parser.add_argument("--in", dest="input_dir", required=True, help="Path to raw data directory")
    parser.add_argument("--out", dest="output_dir", required=True, help="Output directory for cleaned data")
    parser.add_argument("--strict", action="store_true", help="Fail on any unresolved ambiguity or validation error")
    parser.add_argument("--rebuild", action="store_true", help="Recompute all steps, ignoring caches (placeholder)")
    return parser


def main(argv: Optional[list[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    orders = run(args.input_dir, args.output_dir, strict=args.strict, rebuild=args.rebuild)
    print(json.dumps(orders, ensure_ascii=False, indent=2))


if __name__ == "__main__":  # pragma: no cover
    main()

