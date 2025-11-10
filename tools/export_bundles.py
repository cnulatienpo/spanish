#!/usr/bin/env python3
"""Bundle vocabulary batches for downstream consumption."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List


ORDERED_KEYS = [
    "word",
    "pos",
    "gender",
    "english",
    "origin",
    "story",
    "example",
    "level",
]


def load_vocab(scan_dir: Path) -> List[dict]:
    entries: List[dict] = []
    for path in sorted(scan_dir.rglob("*.json")):
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            continue
        entries.extend(data)
    return entries


def clean_entry(entry: dict) -> dict:
    cleaned = {}
    for key in ORDERED_KEYS:
        if key in entry:
            cleaned[key] = entry[key]
    extra_keys = [
        key
        for key in entry
        if key not in cleaned and not key.startswith("_")
    ]
    for key in sorted(extra_keys):
        cleaned[key] = entry[key]
    return cleaned


def group_by_level(entries: Iterable[dict]) -> Dict[str, List[dict]]:
    grouped: Dict[str, List[dict]] = {}
    for entry in entries:
        level = entry.get("level")
        if not level:
            continue
        grouped.setdefault(level, []).append(clean_entry(entry))
    for level_entries in grouped.values():
        level_entries.sort(key=lambda item: item.get("word", "").casefold())
    return grouped


def chunk_entries(entries: List[dict], max_file: int) -> List[List[dict]]:
    if max_file <= 0:
        return [entries]
    return [entries[i : i + max_file] for i in range(0, len(entries), max_file)]


def export_bundles(args: argparse.Namespace) -> None:
    scan_dir = Path(args.scan)
    bundle_dir = Path(args.bundle_dir)
    entries = load_vocab(scan_dir)
    grouped = group_by_level(entries)

    for level, level_entries in sorted(grouped.items()):
        chunks = chunk_entries(level_entries, args.max_file)
        level_path = bundle_dir / level
        level_path.mkdir(parents=True, exist_ok=True)
        for idx, chunk in enumerate(chunks, start=1):
            filename = f"bundle_{idx:03d}.json"
            bundle_path = level_path / filename
            bundle_path.write_text(
                json.dumps(chunk, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"{level}: wrote {bundle_path} ({len(chunk)} entries)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export vocabulary bundles")
    parser.add_argument("--scan", required=True, help="Directory containing vocab batches")
    parser.add_argument("--bundle-dir", required=True, help="Output directory for bundles")
    parser.add_argument("--format", required=True, help="Bundle format (only 'gamejson' supported)")
    parser.add_argument("--split-by", required=True, help="Grouping strategy (only 'level' supported)")
    parser.add_argument("--max-file", type=int, default=1000, help="Maximum entries per bundle file")
    parser.set_defaults(func=export_bundles)
    return parser


def main(argv: List[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.format != "gamejson":
        raise SystemExit("Only 'gamejson' format is supported")
    if args.split_by != "level":
        raise SystemExit("Only split-by 'level' is supported")
    args.func(args)


if __name__ == "__main__":
    main()
