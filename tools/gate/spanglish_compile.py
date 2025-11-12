#!/usr/bin/env python3
"""Rewrite lesson text into Spanglish according to progress state."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Iterable, Tuple

try:
    from .common import (
        DEFAULT_ALWAYS_ALLOW_PATH,
        DEFAULT_BANK_PATH,
        DEFAULT_FORMS_MAP_PATH,
        DEFAULT_KITS_PATH,
        load_always_allow,
        load_bank,
        load_forms_map,
        load_json,
        load_kits,
        load_progress,
        normalize_form,
        tokenize,
        iter_spanish_locations,
    )
except ImportError:  # pragma: no cover - allow running as a script
    sys.path.append(str(Path(__file__).resolve().parent))
    from common import (  # type: ignore
        DEFAULT_ALWAYS_ALLOW_PATH,
        DEFAULT_BANK_PATH,
        DEFAULT_FORMS_MAP_PATH,
        DEFAULT_KITS_PATH,
        load_always_allow,
        load_bank,
        load_forms_map,
        load_json,
        load_kits,
        load_progress,
        normalize_form,
        tokenize,
        iter_spanish_locations,
    )


def load_modes(config_dir: Path) -> Tuple[str, Dict[str, Dict[str, str]]]:
    modes_path = config_dir / "modes.json"
    if not modes_path.exists():
        raise FileNotFoundError(f"Missing gate config: {modes_path}")
    data = load_json(modes_path)
    fallback = data.get("fallback_mode", "mix")
    modes = data.get("modes", {})
    if fallback not in modes:
        raise ValueError(f"Fallback mode '{fallback}' not defined in modes.json")
    return fallback, modes


def gate_text(
    text: str,
    *,
    allowed_forms: set[str],
    bank: Dict[str, list],
    modes: Dict[str, Dict[str, str]],
    mode_key: str,
    forms_map: Dict[str, bool],
) -> Tuple[str, int]:
    mode = modes.get(mode_key, {})
    fmt = mode.get("format", "{english}")
    replacements = 0
    pieces = []
    last_index = 0
    for token, start, end in tokenize(text):
        pieces.append(text[last_index:start])
        normalized = normalize_form(token, forms_map)
        replacement = token
        if normalized and normalized not in allowed_forms:
            entries = bank.get(normalized)
            if entries:
                entry = entries[0]
                english = entry.english.strip() or entry.lemma or entry.form
                try:
                    replacement = fmt.format(form=token, english=english, lemma=entry.lemma or entry.form)
                except KeyError:
                    replacement = english
                replacements += int(replacement != token)
        pieces.append(replacement)
        last_index = end
    pieces.append(text[last_index:])
    return "".join(pieces), replacements


def compile_lesson(
    lesson: object,
    *,
    allowed_forms: set[str],
    bank: Dict[str, list],
    modes: Dict[str, Dict[str, str]],
    mode_key: str,
    forms_map: Dict[str, bool],
) -> int:
    replacements = 0
    for location in list(iter_spanish_locations(lesson)):
        updated, count = gate_text(
            location.text,
            allowed_forms=allowed_forms,
            bank=bank,
            modes=modes,
            mode_key=mode_key,
            forms_map=forms_map,
        )
        if count:
            location.container[location.key] = updated
            replacements += count
    return replacements


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile lessons into Spanglish based on learned vocabulary.")
    parser.add_argument("--level", required=True, help="CEFR level to compile (for logging only)")
    parser.add_argument("--step", required=True, help="Path to the progress .learned.json file")
    parser.add_argument("--scan", required=True, help="Directory containing source lessons")
    parser.add_argument("--out", required=True, help="Output directory for gated lessons")
    parser.add_argument("--mode", default=None, help="Override gating mode defined in config")
    parser.add_argument("--bank", default=str(DEFAULT_BANK_PATH), help="Path to vocab bank CSV")
    parser.add_argument("--kits", default=str(DEFAULT_KITS_PATH), help="Path to kits CSV")
    parser.add_argument("--forms-map", default=str(DEFAULT_FORMS_MAP_PATH), help="Path to forms normalization config")
    parser.add_argument("--always-allow", default=str(DEFAULT_ALWAYS_ALLOW_PATH), help="Path to always-allow tokens config")
    parser.add_argument("--config-dir", default=str(Path(DEFAULT_FORMS_MAP_PATH).parent), help="Directory containing gate config files")
    args = parser.parse_args(list(argv) if argv is not None else None)

    scan_dir = Path(args.scan)
    if not scan_dir.exists():
        print(f"[gate] Scan directory not found: {scan_dir}", file=sys.stderr)
        return 0

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    config_dir = Path(args.config_dir)
    fallback_mode, modes = load_modes(config_dir)
    mode_key = args.mode or fallback_mode
    if mode_key not in modes:
        print(f"[gate] Mode '{mode_key}' not defined. Available: {', '.join(sorted(modes))}", file=sys.stderr)
        return 2

    forms_map = load_forms_map(args.forms_map)
    bank = load_bank(args.bank, forms_map)
    kits = load_kits(args.kits, forms_map)
    _, always_allow_norm = load_always_allow(args.always_allow, forms_map)
    allowed_forms = load_progress(args.step, kits, forms_map)
    allowed_forms.update(always_allow_norm)

    lesson_files = sorted([p for p in scan_dir.rglob("*.json") if p.is_file()])
    if not lesson_files:
        print(f"[gate] No lesson JSON files found under {scan_dir}", file=sys.stderr)
        return 0

    total_files = 0
    total_replacements = 0
    for src_path in lesson_files:
        with open(src_path, "r", encoding="utf-8") as handle:
            lesson_data = json.load(handle)
        replacements = compile_lesson(
            lesson_data,
            allowed_forms=allowed_forms,
            bank=bank,
            modes=modes,
            mode_key=mode_key,
            forms_map=forms_map,
        )
        rel_path = src_path.relative_to(scan_dir)
        dest_path = out_dir / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "w", encoding="utf-8") as handle:
            json.dump(lesson_data, handle, ensure_ascii=False, indent=2)
        total_files += 1
        total_replacements += replacements
    print(f"[gate] Compiled {total_files} lessons with {total_replacements} replacements using mode '{mode_key}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
