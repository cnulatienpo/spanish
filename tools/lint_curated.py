#!/usr/bin/env python3
import argparse
import json
import os
import sys
import glob
from collections import Counter, defaultdict
import re
from typing import Dict, List, Tuple, Iterable, Optional

RULES_PATH = os.path.join("curator", "rules.json")
REGEX_PATH = os.path.join(".curator", "regex.json")
CURATED_FIELDS = ("english", "origin", "story", "example")
LEVEL_BANDS = {
    "A1": "A1A2",
    "A2": "A1A2",
    "B1": "B1B2",
    "B2": "B1B2",
    "C1": "C1C2",
    "C2": "C1C2",
}

class RuleError(RuntimeError):
    pass

def load_rules() -> Dict:
    try:
        with open(RULES_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError as exc:
        raise RuleError(f"Missing rules file: {RULES_PATH}") from exc


def load_regex() -> Dict[str, str]:
    try:
        with open(REGEX_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError as exc:
        raise RuleError(f"Missing regex file: {REGEX_PATH}") from exc


def compile_patterns(regexes: Dict[str, str]) -> Dict[str, Optional[re.Pattern]]:
    compiled: Dict[str, Optional[re.Pattern]] = {}
    for key, pattern in regexes.items():
        if not pattern:
            continue
        try:
            compiled[key] = re.compile(pattern)
        except re.error:
            compiled[key] = None  # unsupported pattern
    return compiled


def iter_files(scan_root: str) -> Iterable[str]:
    for path in glob.glob(os.path.join(scan_root, "**", "*.json"), recursive=True):
        yield path


def sentence_count(text: str) -> int:
    return len([s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]) if text.strip() else 0


def is_sentence_case(text: str) -> bool:
    stripped = text.lstrip()
    if not stripped:
        return True
    first = stripped[0]
    if first.isalpha():
        return first == first.upper()
    return True


def ends_with_period(text: str) -> bool:
    return text.rstrip().endswith('.')


def has_long_paragraph(text: str, limit: int = 180) -> bool:
    paragraphs = [p for p in text.split('\n') if p.strip()]
    return any(len(p.strip()) > limit for p in paragraphs)


def detect_quotes(text: str, straight_pattern=None, curly_pattern=None) -> Tuple[bool, bool]:
    has_straight = bool(straight_pattern.search(text)) if straight_pattern else False
    has_curly = bool(curly_pattern.search(text)) if curly_pattern else False
    return has_straight, has_curly


def load_json(path: str) -> Tuple[bool, List[Dict], str]:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:
        return False, [], f"Failed to parse JSON: {exc}"
    if not isinstance(data, list):
        return False, [], "Top-level must be a JSON array"
    return True, data, ""


def add_issue(store: Dict[str, List[Dict]], severity: str, **payload) -> None:
    store[severity].append(payload)


def lint_entry(
    entry: Dict,
    index: int,
    file_path: str,
    rules: Dict,
    patterns: Dict[str, Optional[re.Pattern]],
    store: Dict[str, List[Dict]],
) -> None:
    word = entry.get("word", "")
    level = entry.get("level", "")
    band_key = LEVEL_BANDS.get(level)
    forbidden = rules.get("forbidden", {})
    straight_re = patterns.get("straight_quotes")
    curly_re = patterns.get("curly_quotes_ok")
    url_re = patterns.get("url")
    emoji_re = patterns.get("emoji")

    for field in CURATED_FIELDS:
        value = entry.get(field, None)
        if not isinstance(value, str) or not value.strip():
            add_issue(
                store,
                "ERROR",
                file=file_path,
                index=index,
                word=word,
                field=field,
                code="MISSING",
                message=f"{field} missing or empty",
            )
            continue

        text = value
        stripped = text.strip()

        # Capitalization check
        if rules.get("capitalization", {}).get("require_sentence_case", False):
            if not is_sentence_case(stripped):
                add_issue(
                    store,
                    "WARN",
                    file=file_path,
                    index=index,
                    word=word,
                    field=field,
                    code="SENTENCE_CASE",
                    message=f"{field} should start with a capital letter",
                )

        # Period check (skip english)
        if field != "english" and rules.get("capitalization", {}).get("end_with_period", False):
            if stripped and not ends_with_period(stripped):
                add_issue(
                    store,
                    "WARN",
                    file=file_path,
                    index=index,
                    word=word,
                    field=field,
                    code="PERIOD",
                    message=f"{field} should end with a period",
                )

        # Forbidden substrings
        forbidden_terms = list(forbidden.get("all_levels", [])) + list(forbidden.get(field, []))
        lower_text = stripped.lower()
        for term in forbidden_terms:
            if term and term.lower() in lower_text:
                add_issue(
                    store,
                    "ERROR",
                    file=file_path,
                    index=index,
                    word=word,
                    field=field,
                    code="FORBIDDEN",
                    message=f"Forbidden phrase '{term}' found in {field}",
                )
                break

        # URL check
        if url_re and url_re.search(text):
            add_issue(
                store,
                "ERROR",
                file=file_path,
                index=index,
                word=word,
                field=field,
                code="URL",
                message=f"URLs are not allowed in {field}",
            )

        # Emoji check
        if emoji_re and emoji_re.search(text):
            add_issue(
                store,
                "ERROR",
                file=file_path,
                index=index,
                word=word,
                field=field,
                code="EMOJI",
                message=f"Emoji characters are not allowed in {field}",
            )

        # Curly quotes check
        if rules.get("punctuation", {}).get("curly_quotes_only", False):
            has_straight, has_curly = detect_quotes(text, straight_re, curly_re)
            if has_straight:
                add_issue(
                    store,
                    "WARN",
                    file=file_path,
                    index=index,
                    word=word,
                    field=field,
                    code="STRAIGHT_QUOTES",
                    message=f"Replace straight quotes in {field} with curly quotes",
                )

        # Length bands
        if band_key and field in rules.get("length_targets", {}):
            bounds = rules["length_targets"][field].get(band_key)
            if bounds:
                lo, hi = bounds
                length = len(stripped)
                if length < lo or length > hi:
                    add_issue(
                        store,
                        "WARN",
                        file=file_path,
                        index=index,
                        word=word,
                        field=field,
                        code="LENGTH",
                        message=f"{field} length {length} chars outside suggested range {lo}-{hi}",
                    )

        # Field-specific style hints
        if field == "origin" and has_long_paragraph(stripped):
            add_issue(
                store,
                "WARN",
                file=file_path,
                index=index,
                word=word,
                field=field,
                code="ORIGIN_LONG",
                message="Origin paragraph too long; consider breaking it up",
            )
        if field == "story":
            sentences = sentence_count(stripped)
            if sentences > 3:
                add_issue(
                    store,
                    "WARN",
                    file=file_path,
                    index=index,
                    word=word,
                    field=field,
                    code="STORY_SENTENCES",
                    message="Story should be 1-3 sentences",
                )
        if field == "example":
            sentences = sentence_count(stripped)
            if sentences > 1:
                add_issue(
                    store,
                    "WARN",
                    file=file_path,
                    index=index,
                    word=word,
                    field=field,
                    code="EXAMPLE_SENTENCES",
                    message="Example should be a single sentence",
                )


def lint_path(path: str, rules: Dict, patterns: Dict[str, Optional[re.Pattern]], store: Dict[str, List[Dict]]):
    ok, data, err = load_json(path)
    if not ok:
        add_issue(
            store,
            "ERROR",
            file=path,
            index=-1,
            word="",
            field="",
            code="FILE",
            message=err,
        )
        return
    for idx, entry in enumerate(data):
        if not isinstance(entry, dict):
            add_issue(
                store,
                "ERROR",
                file=path,
                index=idx,
                word="",
                field="",
                code="TYPE",
                message="Each entry must be an object",
            )
            continue
        lint_entry(entry, idx, path, rules, patterns, store)


def write_summary(summary_path: str, store: Dict[str, List[Dict]]) -> None:
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    errors = store.get("ERROR", [])
    warns = store.get("WARN", [])
    lines = [f"Errors: {len(errors)}  Warnings: {len(warns)}"]

    def block(name: str, issues: List[Dict]):
        counts = Counter(i["code"] for i in issues)
        if not counts:
            return [f"{name}: none"]
        out = [f"{name}:"]
        for code, count in counts.most_common():
            out.append(f"- {code}: {count}")
        return out

    lines.extend(block("Top ERROR codes", errors))
    lines.extend(block("Top WARN codes", warns))
    with open(summary_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def write_report(report_path: str, store: Dict[str, List[Dict]]):
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump({"errors": store.get("ERROR", []), "warnings": store.get("WARN", [])}, fh, ensure_ascii=False, indent=2)


def parse_args():
    ap = argparse.ArgumentParser(description="Lint curated text fields against the style guide")
    ap.add_argument("--scan", required=True, help="Directory to scan for JSON files")
    ap.add_argument("--out", dest="out_report", help="Path to JSON output report")
    ap.add_argument("--summary", dest="summary", help="Path to text summary output")
    ap.add_argument("--fail-on", choices=["ERROR", "WARN"], default="ERROR")
    return ap.parse_args()


def main():
    args = parse_args()
    try:
        rules = load_rules()
        regexes = load_regex()
        patterns = compile_patterns(regexes)
    except RuleError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    store = defaultdict(list)

    for path in sorted(iter_files(args.scan)):
        lint_path(path, rules, patterns, store)

    if args.summary:
        write_summary(args.summary, store)
    if args.out_report:
        write_report(args.out_report, store)

    errors = store.get("ERROR", [])
    warns = store.get("WARN", [])
    fail_on_warn = args.fail_on == "WARN"
    exit_code = 0
    if errors or (fail_on_warn and warns):
        exit_code = 1

    if errors or warns:
        combined = errors + warns
        lines = []
        for issue in combined[:200]:
            lines.append(
                f"[{issue.get('file')}] idx={issue.get('index')} word={issue.get('word')} field={issue.get('field')} "
                f"{issue.get('code')} :: {issue.get('message')}"
            )
        if len(combined) > 200:
            lines.append(f"... and {len(combined) - 200} more issues")
        print("\n".join(lines))

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
