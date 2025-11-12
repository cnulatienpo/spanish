#!/usr/bin/env python3
"""Validate that lessons only use vocabulary that has been unlocked."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Iterable

try:
    from .common import (
        DEFAULT_ALWAYS_ALLOW_PATH,
        DEFAULT_BANK_PATH,
        DEFAULT_FORMS_MAP_PATH,
        DEFAULT_KITS_PATH,
        build_form_to_kits,
        iter_spanish_locations,
        load_always_allow,
        load_bank,
        load_forms_map,
        load_kits,
        load_progress,
        normalize_form,
        tokenize,
    )
except ImportError:  # pragma: no cover - allow running as a script
    sys.path.append(str(Path(__file__).resolve().parent))
    from common import (  # type: ignore
        DEFAULT_ALWAYS_ALLOW_PATH,
        DEFAULT_BANK_PATH,
        DEFAULT_FORMS_MAP_PATH,
        DEFAULT_KITS_PATH,
        build_form_to_kits,
        iter_spanish_locations,
        load_always_allow,
        load_bank,
        load_forms_map,
        load_kits,
        load_progress,
        normalize_form,
        tokenize,
    )


def collect_lesson_forms(lesson: object, bank: Dict[str, list], forms_map: Dict[str, bool]) -> Dict[str, set[str]]:
    used: Dict[str, set[str]] = {}
    for location in iter_spanish_locations(lesson):
        for token, _, _ in tokenize(location.text):
            normalized = normalize_form(token, forms_map)
            if not normalized:
                continue
            if normalized not in bank:
                continue
            used.setdefault(normalized, set()).add(token)
    return used


def extract_lesson_kits(lesson: Dict[str, object]) -> set[str]:
    kit_ids: set[str] = set()
    for key in ("kits", "unlock_kits", "unlocks_kits", "unlock_vocab_kits"):
        value = lesson.get(key)
        if isinstance(value, str):
            kit_ids.add(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    kit_ids.add(item)
    metadata = lesson.get("metadata")
    if isinstance(metadata, dict):
        for key in ("kits", "unlock_kits"):
            value = metadata.get(key)
            if isinstance(value, str):
                kit_ids.add(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        kit_ids.add(item)
    return kit_ids


def load_lesson(path: Path) -> Dict[str, object]:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, dict):
        return data
    raise TypeError(f"Lesson file {path} does not contain a JSON object")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check vocabulary dependencies for lessons.")
    parser.add_argument("--level", required=True, help="CEFR level (for display only)")
    parser.add_argument("--bank", default=str(DEFAULT_BANK_PATH), help="Path to vocab bank CSV")
    parser.add_argument("--kits", default=str(DEFAULT_KITS_PATH), help="Path to kits CSV")
    parser.add_argument("--forms-map", default=str(DEFAULT_FORMS_MAP_PATH), help="Path to forms normalization config")
    parser.add_argument("--always-allow", default=str(DEFAULT_ALWAYS_ALLOW_PATH), help="Path to always-allow tokens config")
    parser.add_argument("--prior", required=False, help="Progress file describing learned forms before this step")
    parser.add_argument("--scan", required=True, help="Directory containing lesson JSON files to inspect")
    args = parser.parse_args(list(argv) if argv is not None else None)

    scan_dir = Path(args.scan)
    if not scan_dir.exists():
        print(f"[gate-check] Scan directory not found: {scan_dir}", file=sys.stderr)
        return 0

    forms_map = load_forms_map(args.forms_map)
    bank = load_bank(args.bank, forms_map)
    kits = load_kits(args.kits, forms_map)
    form_to_kits = build_form_to_kits(kits)
    _, always_allow_norm = load_always_allow(args.always_allow, forms_map)

    prior_forms: set[str] = set()
    if args.prior:
        prior_forms = load_progress(args.prior, kits, forms_map)
    prior_forms.update(always_allow_norm)

    lesson_files = sorted([p for p in scan_dir.rglob("*.json") if p.is_file()])
    if not lesson_files:
        print(f"[gate-check] No lesson JSON files found under {scan_dir}", file=sys.stderr)
        return 0

    failures: Dict[Path, Dict[str, set[str]]] = {}

    for lesson_path in lesson_files:
        lesson = load_lesson(lesson_path)
        lesson_kits = extract_lesson_kits(lesson)
        unlocked_forms: set[str] = set()
        for kit_id in lesson_kits:
            kit = kits.get(kit_id)
            if kit:
                unlocked_forms.update(kit.normalized_forms)
        for key in ("unlock_forms", "unlocks_forms", "unlock_vocab", "unlock_forms_list"):
            value = lesson.get(key)
            if isinstance(value, str):
                normalized = normalize_form(value, forms_map)
                if normalized:
                    unlocked_forms.add(normalized)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        normalized = normalize_form(item, forms_map)
                        if normalized:
                            unlocked_forms.add(normalized)
        used_forms = collect_lesson_forms(lesson, bank, forms_map)
        missing: Dict[str, set[str]] = {}
        for normalized, surfaces in used_forms.items():
            if normalized in prior_forms or normalized in unlocked_forms:
                continue
            missing[normalized] = surfaces
        if missing:
            failures[lesson_path] = missing

    if failures:
        print("[gate-check] Missing vocabulary dependencies detected:\n", file=sys.stderr)
        for path, missing_forms in failures.items():
            print(f"- {path}:", file=sys.stderr)
            for normalized, surfaces in sorted(missing_forms.items()):
                entry = bank.get(normalized, [None])[0]
                english = ""
                lemma = ""
                if entry:
                    english = entry.english.strip()
                    lemma = entry.lemma
                surface_examples = ", ".join(sorted(surfaces))
                kits_for_form = form_to_kits.get(normalized, [])
                hint_parts = []
                if english:
                    hint_parts.append(english)
                if lemma and lemma != english:
                    hint_parts.append(f"lemma: {lemma}")
                if kits_for_form:
                    hint_parts.append(f"kits: {', '.join(sorted(kits_for_form))}")
                hint = f" ({'; '.join(hint_parts)})" if hint_parts else ""
                print(f"    • {normalized}: {surface_examples}{hint}", file=sys.stderr)
        return 1

    print(f"[gate-check] All lessons under {scan_dir} respect learned vocabulary.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
