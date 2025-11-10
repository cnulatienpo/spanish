from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import orjson

sys.path.append(str(Path(__file__).resolve().parents[1]))

from tools.models import Lesson, Vocabulary
from tools.utils import (
    cefr_sort_key,
    deep_merge,
    ensure_notes,
    extract_json_blocks,
    slugify,
    stablehash,
    strip_conflicts,
    tolerant_load,
)

LEVELS = {"A1", "A2", "B1", "B2", "C1", "C2", "UNSET"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Heal and normalize lesson/vocab JSON")
    parser.add_argument("--check", action="store_true", help="validate without writing outputs")
    parser.add_argument("--write", action="store_true", help="write canonical outputs")
    parser.add_argument("--strict", action="store_true", help="treat unknown levels as fatal")
    args = parser.parse_args()

    if not args.check and not args.write:
        parser.error("choose --check or --write")
    repo_root = Path(__file__).resolve().parents[1]
    content_root = repo_root / "content"
    if not content_root.exists():
        print("content/ directory not found", file=sys.stderr)
        sys.exit(1)

    audit = AuditTracker()
    processor = Healer(content_root, audit, strict=args.strict)
    processor.run_scan()

    lessons = processor.get_lessons()
    vocabulary = processor.get_vocabulary()

    validator = Validator(audit)
    validator.validate_lessons(lessons)
    validator.validate_vocabulary(vocabulary)

    writer = Writer(repo_root, lessons, vocabulary, audit, processor.rejects)

    if args.write:
        writer.write_outputs()
        processor.ensure_idempotent()
    else:
        writer.ensure_directories()

    summary = audit.render_summary()
    print(summary)

    writer.write_audit(summary)

    if validator.failed:
        sys.exit(1)


class AuditTracker:
    def __init__(self) -> None:
        self.files_scanned = 0
        self.fragments_parsed = 0
        self.fragments_repaired = 0
        self.fragments_rejected: List[Dict[str, Any]] = []
        self.conflict_files: set[str] = set()
        self.unknown_levels: List[str] = []
        self.duplicates_resolved: List[str] = []
        self.items_merged = 0
        self.duplicate_examples: List[str] = []

    def note_conflict_file(self, path: str) -> None:
        self.conflict_files.add(path)

    def add_reject(self, path: Path, reason: str, content: str) -> None:
        self.fragments_rejected.append({"path": str(path), "reason": reason, "content": content})

    def note_unknown_level(self, identifier: str) -> None:
        self.unknown_levels.append(identifier)

    def note_duplicate(self, identifier: str) -> None:
        self.duplicates_resolved.append(identifier)

    def note_duplicate_example(self, label: str) -> None:
        self.duplicate_examples.append(label)

    def render_summary(self) -> str:
        lines = [
            "Repo healer audit:",
            f"  Files scanned: {self.files_scanned}",
            f"  Fragments parsed: {self.fragments_parsed}",
            f"  Fragments repaired: {self.fragments_repaired}",
            f"  Fragments rejected: {len(self.fragments_rejected)}",
            f"  Items merged: {self.items_merged}",
        ]
        if self.conflict_files:
            lines.append("  Conflict markers removed from:")
            for path in sorted(self.conflict_files):
                lines.append(f"    - {path}")
        if self.unknown_levels:
            lines.append("  Items with level=UNSET:")
            for item in sorted(set(self.unknown_levels)):
                lines.append(f"    - {item}")
        if self.duplicates_resolved:
            lines.append("  Duplicate clusters resolved:")
            for ident in sorted(set(self.duplicates_resolved)):
                lines.append(f"    - {ident}")
        if self.duplicate_examples:
            lines.append("  Duplicate example pairs:")
            for label in sorted(set(self.duplicate_examples)):
                lines.append(f"    - {label}")
        if self.fragments_rejected:
            lines.append("  Rejected fragments:")
            for reject in self.fragments_rejected:
                lines.append(f"    - {reject['path']}: {reject['reason']}")
        return "\n".join(lines)


class Healer:
    def __init__(self, content_root: Path, audit: AuditTracker, strict: bool = False) -> None:
        self.content_root = content_root
        self.audit = audit
        self.strict = strict
        self.lesson_entries: Dict[str, Dict[str, Any]] = {}
        self.vocab_entries: Dict[str, Dict[str, Any]] = {}
        self.lesson_sources: Dict[str, set[str]] = defaultdict(set)
        self.vocab_sources: Dict[str, set[str]] = defaultdict(set)
        self.rejects: List[Dict[str, Any]] = []

    def run_scan(self) -> None:
        for path in sorted(self.content_root.rglob("*")):
            if path.is_dir():
                continue
            self.audit.files_scanned += 1
            self.process_file(path)

    def process_file(self, path: Path) -> None:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="latin-1")
        segments = strip_conflicts(text)
        rel_display = str(path.relative_to(self.content_root.parent))
        if any(isinstance(segment, dict) for segment in segments):
            self.audit.note_conflict_file(rel_display)
        for segment in segments:
            if isinstance(segment, str):
                self.handle_text_segment(path, segment)
            else:
                self.handle_conflict_segment(path, segment)

    def handle_text_segment(self, path: Path, text: str) -> None:
        self._extract_and_process(path, text)

    def handle_conflict_segment(self, path: Path, segment: Dict[str, str]) -> None:
        variant_a = segment.get("A", "")
        variant_b = segment.get("B", "")
        parsed_a = self._extract_objects(path, variant_a)
        parsed_b = self._extract_objects(path, variant_b)
        if parsed_a and parsed_b and len(parsed_a) == len(parsed_b) == 1:
            merged = self._merge_variants(path, parsed_a[0], parsed_b[0])
            if merged is not None:
                self._route_object(path, merged["data"], merged["notes"], conflict=True)
                return
        if parsed_a and not parsed_b:
            self._route_object(path, parsed_a[0]["data"], parsed_a[0]["notes"], conflict=True)
            self.audit.fragments_repaired += 1
            return
        if parsed_b and not parsed_a:
            self._route_object(path, parsed_b[0]["data"], parsed_b[0]["notes"], conflict=True)
            self.audit.fragments_repaired += 1
            return
        self.audit.add_reject(path, "unresolved conflict", segment.get("marker", ""))
        self.rejects.append({"path": str(path), "content": segment.get("marker", "")})

    def _extract_and_process(self, path: Path, text: str) -> None:
        for record in self._extract_objects(path, text):
            self._route_object(path, record["data"], record["notes"], conflict=False)

    def _extract_objects(self, path: Path, text: str) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        try:
            obj = tolerant_load(text)
            self.audit.fragments_parsed += 1
            results.extend(self._expand_object(obj))
            return results
        except Exception:
            pass
        fragments = extract_json_blocks(text)
        for fragment in fragments:
            try:
                data = tolerant_load(fragment)
                self.audit.fragments_parsed += 1
                self.audit.fragments_repaired += 1
                results.extend(self._expand_object(data))
            except Exception as exc:
                self.audit.add_reject(path, f"parse error: {exc}", fragment)
                self.rejects.append({"path": str(path), "content": fragment})
        return results

    def _expand_object(self, obj: Any) -> List[Dict[str, Any]]:
        if isinstance(obj, list):
            records: List[Dict[str, Any]] = []
            for item in obj:
                if isinstance(item, (dict, list)):
                    records.extend(self._expand_object(item))
            return records
        if isinstance(obj, dict):
            return [{"data": obj, "notes": {}}]
        return []

    def _merge_variants(
        self, path: Path, variant_a: Dict[str, Any], variant_b: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        data_a = deepcopy(variant_a["data"])
        data_b = deepcopy(variant_b["data"])
        alt_store: Dict[str, Any] = {}
        merged = deep_merge(data_a, data_b, alt_store=alt_store)
        ensure_notes(merged, alt_store)
        self.audit.fragments_repaired += 1
        return {"data": merged, "notes": alt_store}

    def _route_object(self, path: Path, data: Dict[str, Any], notes: Dict[str, Any], conflict: bool) -> None:
        classification = classify(data)
        rel_path = str(path.relative_to(self.content_root.parent))
        if classification == "lesson":
            normalized = normalize_lesson(data, rel_path, notes, self.strict, self.audit)
            key = lesson_dedupe_key(normalized)
            self._merge_entry(
                normalized,
                key,
                self.lesson_entries,
                self.lesson_sources,
                rel_path,
            )
        elif classification == "vocabulary":
            normalized = normalize_vocab(data, rel_path, notes, self.strict, self.audit)
            key = vocab_dedupe_key(normalized)
            self._merge_entry(
                normalized,
                key,
                self.vocab_entries,
                self.vocab_sources,
                rel_path,
            )
        else:
            self.audit.add_reject(path, "unclassified fragment", json.dumps(data, ensure_ascii=False))
            self.rejects.append({"path": rel_path, "content": json.dumps(data, ensure_ascii=False)})

    def _merge_entry(
        self,
        item: Dict[str, Any],
        key: str,
        entry_store: Dict[str, Dict[str, Any]],
        source_store: Dict[str, set[str]],
        source_path: str,
    ) -> None:
        source_store[key].add(source_path)
        if key in entry_store:
            alt_store: Dict[str, Any] = {}
            merged = deep_merge(entry_store[key], item, alt_store=alt_store)
            ensure_notes(merged, alt_store)
            entry_store[key] = merged
            self.audit.items_merged += 1
            identifier = merged.get("id") or key
            self.audit.note_duplicate(str(identifier))
        else:
            entry_store[key] = item

    def get_lessons(self) -> List[Dict[str, Any]]:
        lessons: List[Dict[str, Any]] = []
        for key, item in self.lesson_entries.items():
            item = deepcopy(item)
            item["source_files"] = sorted(self.lesson_sources[key])
            lessons.append(item)
        lessons.sort(key=cefr_sort_key)
        return lessons

    def get_vocabulary(self) -> List[Dict[str, Any]]:
        vocab_list: List[Dict[str, Any]] = []
        for key, item in self.vocab_entries.items():
            item = deepcopy(item)
            item["source_files"] = sorted(self.vocab_sources[key])
            vocab_list.append(item)
        vocab_list.sort(key=cefr_sort_key)
        return vocab_list

    def ensure_idempotent(self) -> None:
        lessons = self.get_lessons()
        vocabulary = self.get_vocabulary()
        lessons_json = orjson.dumps(lessons, option=orjson.OPT_SORT_KEYS)
        vocab_json = orjson.dumps(vocabulary, option=orjson.OPT_SORT_KEYS)
        rerun_lessons = orjson.loads(lessons_json)
        rerun_vocab = orjson.loads(vocab_json)
        if rerun_lessons != lessons or rerun_vocab != vocabulary:
            raise RuntimeError("idempotency check failed")


class Validator:
    def __init__(self, audit: AuditTracker) -> None:
        self.audit = audit
        self.failed = False

    def validate_lessons(self, lessons: List[Dict[str, Any]]) -> None:
        for item in lessons:
            try:
                Lesson.model_validate(item)
            except Exception as exc:
                print(f"Lesson validation error for {item.get('id')}: {exc}", file=sys.stderr)
                self.failed = True

    def validate_vocabulary(self, vocabulary: List[Dict[str, Any]]) -> None:
        for item in vocabulary:
            try:
                Vocabulary.model_validate(item)
            except Exception as exc:
                print(f"Vocabulary validation error for {item.get('id')}: {exc}", file=sys.stderr)
                self.failed = True


class Writer:
    def __init__(
        self,
        repo_root: Path,
        lessons: List[Dict[str, Any]],
        vocabulary: List[Dict[str, Any]],
        audit: AuditTracker,
        rejects: List[Dict[str, Any]],
    ) -> None:
        self.repo_root = repo_root
        self.lessons = lessons
        self.vocabulary = vocabulary
        self.audit = audit
        self.rejects = rejects
        self.canonical_dir = repo_root / "build" / "canonical"
        self.reports_dir = repo_root / "build" / "reports"
        self.rejects_dir = repo_root / "build" / "rejects"

    def ensure_directories(self) -> None:
        self.canonical_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.rejects_dir.mkdir(parents=True, exist_ok=True)

    def write_outputs(self) -> None:
        self.ensure_directories()
        lessons_path = self.canonical_dir / "lessons.mmspanish.json"
        vocab_path = self.canonical_dir / "vocabulary.mmspanish.json"
        lessons_path.write_bytes(orjson.dumps(self.lessons, option=orjson.OPT_SORT_KEYS))
        vocab_path.write_bytes(orjson.dumps(self.vocabulary, option=orjson.OPT_SORT_KEYS))
        self._write_rejects()

    def write_audit(self, summary: str) -> None:
        self.ensure_directories()
        (self.reports_dir / "audit.md").write_text(summary, encoding="utf-8")

    def _write_rejects(self) -> None:
        self.rejects_dir.mkdir(parents=True, exist_ok=True)
        for index, reject in enumerate(self.rejects, start=1):
            path = self.rejects_dir / f"reject_{index:04d}.json"
            payload = {
                "path": reject.get("path"),
                "content": reject.get("content"),
            }
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def classify(data: Dict[str, Any]) -> Optional[str]:
    if not isinstance(data, dict):
        return None
    keys = set(k.lower() for k in data.keys())
    if {"title", "nickname"}.issubset(keys) or "steps" in data:
        return "lesson"
    vocab_keys = {"spanish", "pos", "english_gloss", "definition"}
    if vocab_keys.intersection(keys):
        return "vocabulary"
    return None


def normalize_lesson(
    data: Dict[str, Any],
    source_path: str,
    notes: Dict[str, Any],
    strict: bool,
    audit: AuditTracker,
) -> Dict[str, Any]:
    normalized = deepcopy(data)
    normalized = normalize_keys(normalized)
    normalized["title"] = str(normalized.get("title", ""))
    normalized.setdefault("tags", [])
    normalized["tags"] = ensure_list(normalized.get("tags", []))
    label = f"lesson:{normalized.get('title', '')}"
    normalized["level"] = normalize_level(normalized.get("level"), source_path, strict, audit, label)
    normalized["nickname"] = str(normalized.get("nickname", ""))
    if not normalized["nickname"].strip():
        normalized["nickname"] = slugify(normalized.get("title", ""))
    normalized["steps"] = normalize_steps(normalized.get("steps", []))
    normalized["unit"] = safe_int(normalized.get("unit"), default=0)
    normalized["lesson_number"] = safe_int(normalized.get("lesson_number"), default=0)
    normalized.setdefault("notes", None)
    ensure_notes(normalized, notes)
    if "id" not in normalized or not isinstance(normalized["id"], str):
        normalized["id"] = build_lesson_id(normalized)
    normalized.setdefault("tags", [])
    normalized.setdefault("source_files", [])
    return normalized


def normalize_steps(raw_steps: Any) -> List[Dict[str, Any]]:
    steps: List[Dict[str, Any]] = []
    if not isinstance(raw_steps, list):
        return steps
    for step in raw_steps:
        if not isinstance(step, dict):
            continue
        phase = step.get("phase")
        if phase == "english_anchor" and "line" in step:
            steps.append({"phase": "english_anchor", "line": str(step["line"])})
        elif phase == "system_logic" and "line" in step:
            steps.append({"phase": "system_logic", "line": str(step["line"])})
        elif phase == "meaning_depth":
            steps.append(
                {
                    "phase": "meaning_depth",
                    "origin": str(step.get("origin", "")),
                    "story": str(step.get("story", "")),
                }
            )
        elif phase == "spanish_entry" and "line" in step:
            steps.append({"phase": "spanish_entry", "line": str(step.get("line", ""))})
        elif phase == "examples":
            items = step.get("items", [])
            if isinstance(items, list):
                steps.append(
                    {
                        "phase": "examples",
                        "items": [str(item) for item in items if str(item).strip()],
                    }
                )
    return steps


def normalize_vocab(
    data: Dict[str, Any],
    source_path: str,
    notes: Dict[str, Any],
    strict: bool,
    audit: AuditTracker,
) -> Dict[str, Any]:
    normalized = deepcopy(data)
    normalized = normalize_keys(normalized)
    normalized["spanish"] = str(normalized.get("spanish", "")).strip()
    normalized["pos"] = normalize_pos(normalized.get("pos"))
    gender = normalized.get("gender")
    if isinstance(gender, str):
        gender = gender.strip().lower()
        if gender not in {"masculine", "feminine"}:
            gender = None
    else:
        gender = None
    normalized["gender"] = gender if normalized["pos"] == "noun" else None
    normalized["english_gloss"] = str(normalized.get("english_gloss", normalized.get("gloss", ""))).strip()
    normalized["definition"] = str(normalized.get("definition", "")).strip()
    label = f"vocab:{normalized.get('spanish', '') or normalized.get('id', '')}"
    normalized["origin"] = normalize_optional(normalized.get("origin"))
    normalized["story"] = normalize_optional(normalized.get("story"))
    normalized["examples"] = normalize_examples(
        normalized.get("examples", []), audit, label
    )
    normalized["level"] = normalize_level(normalized.get("level"), source_path, strict, audit, label)
    normalized["tags"] = ensure_list(normalized.get("tags", []))
    normalized.setdefault("notes", None)
    ensure_notes(normalized, notes)
    if "id" not in normalized or not isinstance(normalized["id"], str) or not normalized["id"].startswith("mmspanish__vocab_"):
        normalized["id"] = build_vocab_id(normalized)
    normalized.setdefault("source_files", [])
    return normalized


def ensure_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return []


def normalize_keys(data: Dict[str, Any]) -> Dict[str, Any]:
    mapping = {
        "nick_name": "nickname",
        "nikname": "nickname",
        "lessonNumber": "lesson_number",
        "lessonNo": "lesson_number",
        "unitNumber": "unit",
    }
    for wrong, right in mapping.items():
        if wrong in data and right not in data:
            data[right] = data.pop(wrong)
    return data


def normalize_pos(value: Any) -> str:
    if not isinstance(value, str):
        return "expr"
    value = value.strip().lower()
    allowed = {"noun", "verb", "adj", "adv", "prep", "det", "pron", "conj", "expr"}
    return value if value in allowed else "expr"


def normalize_optional(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_examples(raw: Any, audit: AuditTracker, label: str) -> List[Dict[str, str]]:
    examples: List[Dict[str, str]] = []
    seen_keys: set[Tuple[str, str]] = set()
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                es = str(item.get("es", "")).strip()
                en = str(item.get("en", "")).strip()
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                es = str(item[0]).strip()
                en = str(item[1]).strip()
            else:
                continue
            if es and en:
                key = (es.lower(), en.lower())
                if key in seen_keys:
                    audit.note_duplicate_example(f"{label}|{es}")
                    continue
                seen_keys.add(key)
                examples.append({"es": es, "en": en})
    return examples


def normalize_level(
    value: Any,
    source_path: str,
    strict: bool,
    audit: AuditTracker,
    label: str,
) -> str:
    if isinstance(value, str) and value.upper() in LEVELS:
        level = value.upper()
    else:
        level = infer_level_from_path(source_path)
    if level not in LEVELS:
        level = "UNSET"
    if level == "UNSET" and label:
        audit.note_unknown_level(label)
        if strict:
            raise ValueError(f"unknown level for {label}")
    return level


def infer_level_from_path(path: str) -> str:
    lower = path.lower()
    for level in ["a1", "a2", "b1", "b2", "c1", "c2"]:
        if f"/{level}/" in lower or f"_{level}_" in lower or lower.endswith(f"_{level}.json"):
            return level.upper()
    return "UNSET"


def build_lesson_id(data: Dict[str, Any]) -> str:
    unit = int(data.get("unit", 0) or 0)
    slug = slugify(str(data.get("title", "lesson")))
    return f"mmspanish__grammar_{unit:03}_{slug}"


def build_vocab_id(data: Dict[str, Any]) -> str:
    key = f"{data.get('spanish','').lower()}|{data.get('pos')}|{data.get('gender')}"
    digest = stablehash(key)
    return f"mmspanish__vocab_{digest}"


def lesson_dedupe_key(data: Dict[str, Any]) -> str:
    unit = data.get("unit")
    lesson_number = data.get("lesson_number")
    title = data.get("title", "")
    nickname = data.get("nickname", "")
    if unit and lesson_number:
        return f"{title}|{unit}|{lesson_number}"
    return f"{title}|{nickname}"


def vocab_dedupe_key(data: Dict[str, Any]) -> str:
    gender = data.get("gender") or ""
    return f"{data.get('spanish','').lower()}|{data.get('pos')}|{gender}"


if __name__ == "__main__":
    main()
