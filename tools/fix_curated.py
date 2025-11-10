#!/usr/bin/env python3
import argparse
import json
import os
import glob
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

CURATED_FIELDS = ("origin", "story", "example")
BACKUP_DIR = Path("backups")


def iter_files(scan_root: str):
    for path in glob.glob(os.path.join(scan_root, "**", "*.json"), recursive=True):
        yield Path(path)


def collapse_spaces(text: str) -> str:
    text = text.strip()
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    return text




def capitalize_sentence(text: str) -> str:
    chars = list(text)
    for idx, ch in enumerate(chars):
        if ch.isalpha():
            if ch.islower():
                chars[idx] = ch.upper()
            break
    return "".join(chars)


def ensure_period(text: str) -> str:
    if not text:
        return text
    if re.search(r"[.!?…]$", text):
        return text
    return text + "."


def replace_straight_quotes(text: str) -> Tuple[str, List[str]]:
    warnings: List[str] = []
    count = text.count('"')
    if count == 0:
        return text, warnings
    if count % 2 != 0:
        warnings.append("Unbalanced double quotes; leaving as-is")
        return text, warnings
    result = []
    open_quote = True
    for ch in text:
        if ch == '"':
            result.append('“' if open_quote else '”')
            open_quote = not open_quote
        else:
            result.append(ch)
    return "".join(result), warnings


def fix_field(field: str, text: str) -> Tuple[str, List[str]]:
    warnings: List[str] = []
    updated = collapse_spaces(text)
    updated = capitalize_sentence(updated)
    updated = ensure_period(updated)
    updated, quote_warnings = replace_straight_quotes(updated)
    warnings.extend(quote_warnings)
    return updated, warnings


def fix_entry(entry: Dict) -> Tuple[bool, Dict[str, str], List[str]]:
    changed_fields: Dict[str, str] = {}
    warnings: List[str] = []
    for field in CURATED_FIELDS:
        value = entry.get(field)
        if not isinstance(value, str):
            continue
        new_value, field_warnings = fix_field(field, value)
        warnings.extend(f"{field}: {w}" for w in field_warnings)
        if new_value != value:
            changed_fields[field] = new_value
    return bool(changed_fields), changed_fields, warnings


def load_entries(path: Path):
    try:
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse {path}: {exc}")
    if not isinstance(data, list):
        raise RuntimeError(f"File {path} must contain a JSON array")
    return data


def save_entries(path: Path, data: List[Dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def backup_file(path: Path, timestamp: str):
    BACKUP_DIR.mkdir(exist_ok=True)
    try:
        relative = path.relative_to(Path.cwd())
    except ValueError:
        relative = path
    safe_name = "__".join(relative.parts)
    backup_path = BACKUP_DIR / f"{timestamp}_{safe_name}"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path.write_bytes(path.read_bytes())
    return backup_path


def process_file(path: Path, write: bool, timestamp: str):
    data = load_entries(path)
    file_changed = False
    entry_warnings: List[str] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        changed, updates, warnings = fix_entry(entry)
        entry_warnings.extend(warnings)
        if changed:
            file_changed = True
            entry.update(updates)
    if not file_changed:
        return False, entry_warnings
    if write:
        backup_file(path, timestamp)
        save_entries(path, data)
    return True, entry_warnings


def parse_args():
    ap = argparse.ArgumentParser(description="Apply safe formatting fixes to curated fields")
    ap.add_argument("--scan", required=True, help="Directory to scan for JSON files")
    ap.add_argument("--write", action="store_true", help="Write fixes back to files")
    ap.add_argument("--dry-run", action="store_true", help="Show changes without writing (default)")
    return ap.parse_args()


def main():
    args = parse_args()
    write = args.write
    dry_run = args.dry_run or not write
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S") if write else ""

    any_changes = False
    for path in sorted(iter_files(args.scan)):
        try:
            changed, warnings = process_file(Path(path), write if not dry_run else False, timestamp)
        except RuntimeError as exc:
            print(exc)
            continue
        if changed:
            any_changes = True
            action = "Updated" if write and not dry_run else "Would update"
            print(f"{action} {path}")
        for warn in warnings:
            print(f"WARN [{path}]: {warn}")

    if not any_changes:
        print("No changes needed.")


if __name__ == "__main__":
    main()
