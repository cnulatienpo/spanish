#!/usr/bin/env python3
"""Promote or demote vocabulary entries between CEFR levels."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple


def load_json(path: Path) -> List[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise SystemExit(f"Expected list in {path}")
    return data


def save_json(path: Path, items: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(items, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def find_entry(scan: Path, level: str, word: str) -> Tuple[Path, List[dict], int]:
    level_dir = scan / level
    if not level_dir.exists():
        raise SystemExit(f"Level directory not found: {level_dir}")
    matches: List[Tuple[Path, List[dict], int]] = []
    for path in sorted(level_dir.glob("*.json")):
        items = load_json(path)
        for idx, item in enumerate(items):
            if isinstance(item, dict) and item.get("word") == word:
                matches.append((path, items, idx))
    if not matches:
        raise SystemExit(f"Word '{word}' not found in level {level}")
    if len(matches) > 1:
        locations = ", ".join(str(match[0]) for match in matches)
        raise SystemExit(f"Multiple entries for '{word}' in level {level}: {locations}")
    return matches[0]


def backup_files(root: Path, files: List[Path]) -> Path:
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    backup_root = root / timestamp
    for file_path in files:
        rel_path = Path(os.path.relpath(file_path, Path.cwd()))
        target = backup_root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, target)
    return backup_root


def run_validate(scan: Path) -> None:
    cmd = [
        sys.executable,
        "tools/validate.py",
        "--scan-dir",
        str(scan),
        "--require-alpha",
    ]
    subprocess.run(cmd, check=True)


def promote(args: argparse.Namespace) -> None:
    scan = Path(args.scan)
    word = args.word
    from_level = args.from_level
    to_level = args.to_level

    source_path, source_items, index = find_entry(scan, from_level, word)
    entry = source_items[index]
    destination_dir = scan / to_level
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination_path = destination_dir / "promoted.json"
    dest_items = load_json(destination_path)

    print(f"Found '{word}' in {source_path}")
    print(f"Preparing to move to {destination_path}")

    if not args.write:
        print("--write flag not provided; no changes made.")
        return

    backup_root = backup_files(Path("backups"), [source_path] + ([destination_path] if destination_path.exists() else []))
    print(f"Backups created under {backup_root}")

    # Remove from source
    del source_items[index]
    save_json(source_path, source_items)

    # Update entry level and insert into destination maintaining alphabetical order
    entry["level"] = to_level
    dest_items.append(entry)
    dest_items.sort(key=lambda item: item.get("word", "").casefold())
    save_json(destination_path, dest_items)

    run_validate(scan)
    print(f"Moved '{word}' from {from_level} -> {to_level}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Promote or demote vocabulary entries")
    parser.add_argument("--word", required=True, help="Word to move")
    parser.add_argument("--from", dest="from_level", required=True, help="Source level")
    parser.add_argument("--to", dest="to_level", required=True, help="Destination level")
    parser.add_argument("--scan", required=True, help="Root directory containing level folders")
    parser.add_argument("--write", action="store_true", help="Apply changes")
    parser.set_defaults(func=promote)
    return parser


def main(argv: List[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
