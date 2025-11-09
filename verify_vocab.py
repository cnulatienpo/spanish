#!/usr/bin/env python3
"""CLI tool to validate cleaned Spanish vocabulary JSON files."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


ALLOWED_POS = {
    "noun",
    "verb",
    "adjective",
    "adverb",
    "pronoun",
    "preposition",
    "conjunction",
    "interjection",
    "phrase",
    "expression",
    "determiner",
    "auxiliary",
    "particle",
}

ALLOWED_GENDER = {"masculine", "feminine", "invariable", "n/a"}

ALLOWED_LEVELS = {"A1", "A2", "B1", "B2", "C1", "C2"}

HIGH_FREQUENCY_WORDS = {
    "ser",
    "estar",
    "tener",
    "hacer",
    "poder",
    "decir",
    "ir",
    "ver",
    "dar",
    "saber",
    "querer",
    "llegar",
    "pasar",
    "deber",
    "poner",
    "parecer",
    "quedar",
    "creer",
    "hablar",
    "llevar",
    "dejar",
    "seguir",
    "encontrar",
    "llamar",
    "tiempo",
    "año",
    "día",
    "cosa",
    "hombre",
    "mujer",
    "vida",
    "mano",
    "parte",
    "niño",
    "ojo",
    "trabajo",
    "punto",
    "gente",
    "ciudad",
    "agua",
    "momento",
    "padre",
    "madre",
    "mundo",
    "noche",
    "señor",
    "persona",
    "historia",
    "mes",
    "camino",
    "luz",
    "cuento",
    "país",
    "realidad",
    "niña",
    "voz",
    "nombre",
    "hijo",
    "cabeza",
    "amigo",
    "amor",
    "sentido",
    "fin",
    "familia",
    "idea",
    "caballo",
    "cuerpo",
    "número",
    "mano",
    "clase",
    "casa",
    "lado",
    "forma",
    "hombre",
    "palabra",
    "problema",
    "cuenta",
    "grupo",
    "condición",
    "gobierno",
    "programa",
    "después",
    "antes",
    "muy",
    "siempre",
    "nunca",
    "ya",
    "aquí",
    "allí",
    "bien",
    "mal",
    "más",
    "menos",
    "nuevo",
    "viejo",
    "primero",
    "último",
    "grande",
    "pequeño",
    "buen",
    "bueno",
    "mejor",
    "malo",
    "peor",
}

ADVANCED_WORDS = {
    "otorrinolaringólogo",
    "paralelepípedo",
    "idiosincrasia",
    "inconmensurable",
    "transustanciación",
    "homeostasis",
    "paradigma",
    "heterogéneo",
    "pernicioso",
    "alegoría",
    "subyugación",
    "dialéctica",
    "hiperbólico",
    "magnánimo",
    "morfosintaxis",
    "nefelibata",
    "onomatopeya",
    "paradójico",
    "quimera",
    "sesquipedalio",
}


@dataclass
class Issue:
    """Representation of a validation issue."""

    index: int
    word: str
    code: str
    message: str
    details: Dict[str, Any]

    def as_report_dict(self) -> Dict[str, Any]:
        data = {
            "index": self.index,
            "word": self.word,
            "code": self.code,
            "message": self.message,
        }
        data.update(self.details)
        return data


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="input_path", required=True, help="Path to vocabulary JSON file")
    parser.add_argument(
        "--require-alpha",
        action="store_true",
        help="Require entries to be sorted alphabetically by word",
    )
    parser.add_argument("--out-report", dest="out_report", help="Write machine-readable report to file")
    parser.add_argument("--out-summary", dest="out_summary", help="Write human-readable summary to file")
    parser.add_argument(
        "--fail-on",
        choices=["WARN", "ERROR"],
        default="ERROR",
        help="Exit with failure status when encountering issues at or above this severity",
    )
    return parser.parse_args(argv)


def load_entries(path: Path) -> List[Dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, UnicodeDecodeError):
        raise
    except json.JSONDecodeError as exc:  # pragma: no cover - structure for clarity
        raise ValueError(f"Invalid JSON: {exc}") from exc

    if not isinstance(data, list):
        raise ValueError("Top-level JSON structure must be an array")

    return data


def validate_entries(
    entries: List[Any],
    require_alpha: bool,
) -> Tuple[List[Issue], List[Issue], Dict[str, Any]]:
    errors: List[Issue] = []
    warnings: List[Issue] = []
    dedupe_data: Dict[str, Any] = {
        "exact_duplicates": [],
        "conflicts": [],
    }

    duplicates: Dict[str, List[Tuple[int, Dict[str, Any]]]] = defaultdict(list)

    def record_error(index: int, word: str, code: str, message: str, **details: Any) -> None:
        errors.append(Issue(index, word, code, message, details))

    def record_warning(index: int, word: str, code: str, message: str, **details: Any) -> None:
        warnings.append(Issue(index, word, code, message, details))

    prev_word_norm: Optional[str] = None
    bad_order_indices: List[int] = []

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            record_error(index, "<non-object>", "INVALID_ENTRY", "Entry must be a JSON object")
            continue

        for field in [
            "word",
            "pos",
            "gender",
            "english",
            "origin",
            "story",
            "example",
            "level",
        ]:
            if field not in entry:
                record_error(index, entry.get("word", "<missing word>"), "MISSING_FIELD", "missing required field", field=field)
                continue

            value = entry[field]
            if not isinstance(value, str):
                record_error(index, entry.get("word", "<missing word>"), "INVALID_TYPE", "field must be a string", field=field)
                continue

            if field in {"word", "english", "origin", "story", "example"}:
                if value.strip() == "":
                    record_error(index, entry.get("word", "<missing word>"), "EMPTY_FIELD", "field must not be empty", field=field)
            if field in {"pos", "gender", "level"} and value.strip() == "":
                record_error(index, entry.get("word", "<missing word>"), "EMPTY_FIELD", "field must not be empty", field=field)

        word = entry.get("word")
        word_str = word if isinstance(word, str) else ""

        # Gender and POS validations
        pos = entry.get("pos") if isinstance(entry.get("pos"), str) else None
        gender = entry.get("gender") if isinstance(entry.get("gender"), str) else None
        level = entry.get("level") if isinstance(entry.get("level"), str) else None

        if pos and pos not in ALLOWED_POS:
            record_error(index, word_str, "INVALID_POS", "pos must be one of allowed values", value=pos)

        if gender and gender not in ALLOWED_GENDER:
            record_error(index, word_str, "INVALID_GENDER", "gender must be one of allowed values", value=gender)

        if level and level not in ALLOWED_LEVELS:
            record_error(index, word_str, "INVALID_LEVEL", "level must be CEFR (A1-C2)", value=level)

        # Cross-field warnings
        if pos and gender:
            if pos == "noun" and gender == "n/a":
                record_warning(index, word_str, "GENDER_NOUN_NA", "noun entries usually require gender")
            if pos == "verb" and gender != "n/a":
                record_warning(index, word_str, "GENDER_VERB_NOT_NA", "verb entries should use gender 'n/a'")
            if pos in {"adjective", "adverb", "verb", "pronoun", "preposition", "conjunction", "interjection", "auxiliary", "particle"} and gender not in {None, "n/a"}:
                if gender != "n/a":
                    record_warning(index, word_str, "GENDER_INCONSISTENT", "gender unlikely for this part of speech", expected="n/a")

        # Word character sanity
        if isinstance(word, str):
            if word != word.strip():
                record_warning(index, word, "WORD_WHITESPACE", "word contains leading or trailing whitespace")
            if word != word.lower():
                record_warning(index, word, "WORD_UPPERCASE", "word contains uppercase characters")
            if pos not in {"phrase", "expression"} and len(word.split()) > 1:
                record_warning(index, word, "WORD_MULTI_TOKEN", "multi-word entries reserved for phrase/expression")
            # check for surrogate code points
            for ch in word:
                codepoint = ord(ch)
                if 0xD800 <= codepoint <= 0xDFFF:
                    record_error(index, word, "INVALID_CODEPOINT", "word contains invalid UTF-16 surrogate code point", codepoint=codepoint)

        # Check other string fields for invalid code points
        for field in ["english", "origin", "story", "example"]:
            value = entry.get(field)
            if isinstance(value, str):
                for ch in value:
                    codepoint = ord(ch)
                    if 0xD800 <= codepoint <= 0xDFFF:
                        record_error(index, word_str, "INVALID_CODEPOINT", f"{field} contains invalid UTF-16 surrogate code point", field=field, codepoint=codepoint)

        # Duplicate tracking
        if isinstance(word, str):
            duplicates[word.casefold()].append((index, entry))

        # CEFR heuristics
        if isinstance(word, str) and isinstance(level, str):
            word_norm = word.casefold()
            if word_norm in HIGH_FREQUENCY_WORDS and level in {"C1", "C2"}:
                record_warning(index, word, "CEFR_POSSIBLE_OVERTAG", "Very common word labelled as advanced", level=level)
            if word_norm in ADVANCED_WORDS and level in {"A1", "A2"}:
                record_warning(index, word, "CEFR_POSSIBLE_UNDERTAG", "Rare/technical word labelled as beginner", level=level)

        # Ordering check
        if require_alpha and isinstance(word, str):
            normalized = word.casefold()
            if prev_word_norm is not None and normalized <= prev_word_norm:
                if len(bad_order_indices) < 20:
                    bad_order_indices.append(index)
            prev_word_norm = normalized

    # Duplicate evaluation
    for word_norm, occurrences in duplicates.items():
        if len(occurrences) <= 1:
            continue
        indices = [idx for idx, _ in occurrences]
        base_entry = occurrences[0][1]
        all_equal = all(entry == base_entry for _, entry in occurrences[1:])
        word_display = occurrences[0][1].get("word", word_norm)
        if all_equal:
            dedupe_data["exact_duplicates"].append(word_display)
            for idx, _ in occurrences:
                record_warning(idx, word_display, "DUPLICATE_EXACT", "duplicate entry with identical fields", instances=indices)
        else:
            diff_fields: Dict[str, List[str]] = {}
            all_fields = set()
            for _, entry in occurrences:
                all_fields.update(entry.keys())
            for field in sorted(all_fields):
                values = [entry.get(field) for _, entry in occurrences]
                unique_values = {json.dumps(value, ensure_ascii=False, sort_keys=True) for value in values}
                if len(unique_values) > 1:
                    diff_fields[field] = values
            dedupe_data["conflicts"].append({
                "word": word_display,
                "instances": indices,
                "diff": diff_fields,
            })
            for idx, entry in occurrences:
                record_error(idx, entry.get("word", word_norm), "DUPLICATE_CONFLICT", "duplicate entries disagree", instances=indices, diff=diff_fields)

    ordering_info = None
    if require_alpha:
        ordering_info = {
            "required": True,
            "is_sorted": len(bad_order_indices) == 0,
            "first_bad_indices": bad_order_indices,
        }

    return errors, warnings, {"dedupe": dedupe_data, "ordering": ordering_info}


def build_summary(
    file_path: Path,
    entries: List[Any],
    errors: Iterable[Issue],
    warnings: Iterable[Issue],
    ordering_info: Optional[Dict[str, Any]],
    dedupe_info: Dict[str, Any],
) -> str:
    errors = list(errors)
    warnings = list(warnings)
    lines: List[str] = []
    lines.append(f"Validation summary for {file_path}")
    lines.append("=" * 80)
    lines.append(f"Total entries: {len(entries)}")
    lines.append(f"Errors: {len(errors)}")
    lines.append(f"Warnings: {len(warnings)}")
    lines.append("")

    def append_table(title: str, issues: List[Issue]) -> None:
        lines.append(title)
        lines.append("-" * len(title))
        if not issues:
            lines.append("(none)")
            lines.append("")
            return
        header = f"{'Index':>5}  {'Word':<20}  {'Code':<24}  Message"
        lines.append(header)
        lines.append("-" * len(header))
        for issue in issues:
            word_display = (issue.word or "")[:20]
            lines.append(f"{issue.index:>5}  {word_display:<20}  {issue.code:<24}  {issue.message}")
        lines.append("")

    append_table("Errors", errors)
    append_table("Warnings", warnings)

    lines.append("Duplicates")
    lines.append("----------")
    exact_dups = dedupe_info.get("exact_duplicates", []) if dedupe_info else []
    conflicts = dedupe_info.get("conflicts", []) if dedupe_info else []
    if not exact_dups and not conflicts:
        lines.append("(none)")
    else:
        if exact_dups:
            lines.append("Exact duplicates:")
            for word in exact_dups:
                lines.append(f"  - {word}")
        if conflicts:
            lines.append("Conflicting duplicates:")
            for conflict in conflicts:
                lines.append(f"  - {conflict['word']} (indices: {conflict['instances']})")
    lines.append("")

    if ordering_info:
        lines.append("Ordering")
        lines.append("--------")
        lines.append(f"Required: {ordering_info['required']}")
        lines.append(f"Is sorted: {ordering_info['is_sorted']}")
        if not ordering_info["is_sorted"]:
            bad_indices = ordering_info.get("first_bad_indices", [])
            lines.append(f"First bad indices: {bad_indices}")
        lines.append("")

    # CEFR highlight section
    cefr_issues = [issue for issue in warnings if issue.code.startswith("CEFR_")]
    lines.append("CEFR sanity highlights")
    lines.append("-----------------------")
    if not cefr_issues:
        lines.append("(none)")
    else:
        for issue in cefr_issues[:50]:
            level = issue.details.get("level")
            lines.append(f"- {issue.word} (index {issue.index}) level={level}: {issue.message}")
    lines.append("")

    return "\n".join(lines)


def build_machine_report(
    file_path: Path,
    entries: List[Any],
    errors: Iterable[Issue],
    warnings: Iterable[Issue],
    extra: Dict[str, Any],
) -> Dict[str, Any]:
    errors_list = [issue.as_report_dict() for issue in errors]
    warnings_list = [issue.as_report_dict() for issue in warnings]
    report = {
        "file": str(file_path),
        "total_entries": len(entries),
        "errors": errors_list,
        "warnings": warnings_list,
        "dedupe": extra.get("dedupe", {}),
        "ordering": extra.get("ordering"),
    }
    return report


def write_text(path: Optional[str], content: str) -> None:
    if not path:
        print(content)
        return
    Path(path).write_text(content, encoding="utf-8")


def write_json_report(path: Optional[str], data: Dict[str, Any]) -> None:
    if not path:
        return
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def determine_exit_code(fail_on: str, errors: List[Issue], warnings: List[Issue]) -> int:
    if fail_on == "ERROR":
        return 1 if errors else 0
    if fail_on == "WARN":
        return 1 if errors or warnings else 0
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    input_path = Path(args.input_path)

    try:
        entries = load_entries(input_path)
    except (OSError, UnicodeDecodeError):
        print(f"Failed to read file: {input_path}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    errors, warnings, extra = validate_entries(entries, args.require_alpha)

    ordering_info = extra.get("ordering")
    dedupe_info = extra.get("dedupe", {})

    summary = build_summary(input_path, entries, errors, warnings, ordering_info, dedupe_info)
    write_text(args.out_summary, summary)

    machine_report = build_machine_report(input_path, entries, errors, warnings, extra)
    write_json_report(args.out_report, machine_report)

    exit_code = determine_exit_code(args.fail_on, errors, warnings)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
