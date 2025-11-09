from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple
import unicodedata

JSON_EXTENSIONS = {".json", ".jsonl", ".jsonl?", ".jsonl"}


@dataclass
class RawItem:
    data: Dict[str, Any]
    source_path: Path
    original_stream: str


@dataclass
class Reject:
    source_path: Path
    original_stream: str
    error: str


SPACE_RE = re.compile(r"[ \t]+")
TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")
UNQUOTED_KEY_RE = re.compile(r"([{,]\s*)([A-Za-z0-9_]+)(\s*:)" )


def ensure_output_dir(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "reports").mkdir(parents=True, exist_ok=True)
    (out_dir / "_manual_review").mkdir(parents=True, exist_ok=True)
    (out_dir / "_rejects").mkdir(parents=True, exist_ok=True)


def normalize_string(value: str) -> str:
    value = unicodedata.normalize("NFC", value)
    value = value.strip()
    value = SPACE_RE.sub(" ", value)
    return value


def to_snake_case(key: str) -> str:
    key = key.replace("-", " ").replace("/", " ")
    key = re.sub(r"[^0-9A-Za-z]+", " ", key)
    key = " ".join(part for part in key.split(" ") if part)
    return key.lower().replace(" ", "_")


def clean_data(obj: Any) -> Any:
    if isinstance(obj, dict):
        new_obj: Dict[str, Any] = {}
        for key, value in obj.items():
            new_key = to_snake_case(str(key))
            new_obj[new_key] = clean_data(value)
        return new_obj
    if isinstance(obj, list):
        return [clean_data(item) for item in obj]
    if isinstance(obj, str):
        return normalize_string(obj)
    return obj


def repair_text(text: str) -> Iterable[str]:
    stripped = text.lstrip("\ufeff")
    stripped = stripped.replace("\r\n", "\n")
    yield stripped
    no_trailing = TRAILING_COMMA_RE.sub(r"\1", stripped)
    if no_trailing != stripped:
        yield no_trailing
    unquoted = UNQUOTED_KEY_RE.sub(r"\1" + '"' + r"\2" + '"' + r"\3", no_trailing)
    if unquoted != no_trailing:
        yield unquoted


def parse_json_candidate(candidate: str) -> List[Any]:
    candidate = candidate.strip()
    if not candidate:
        return []
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        # Try JSON lines
        lines = [line for line in candidate.splitlines() if line.strip()]
        items: List[Any] = []
        for line in lines:
            items.append(json.loads(line))
        return items
    else:
        if isinstance(parsed, list):
            return list(parsed)
        return [parsed]


def parse_file(path: Path) -> List[Any]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    for candidate in repair_text(text):
        try:
            return parse_json_candidate(candidate)
        except json.JSONDecodeError:
            continue
    raise ValueError("Unable to parse JSON after repairs")


def load_raw_items(input_dir: Path) -> Tuple[List[RawItem], List[Reject]]:
    items: List[RawItem] = []
    rejects: List[Reject] = []
    for stream in ("lessons", "vocabulary"):
        stream_dir = input_dir / stream
        paths: List[Path] = []
        if stream_dir.is_dir():
            paths.extend(sorted(stream_dir.rglob("*.json")))
            paths.extend(sorted(stream_dir.rglob("*.jsonl")))
        direct = input_dir / f"{stream}.json"
        if direct.exists():
            paths.append(direct)
        directl = input_dir / f"{stream}.jsonl"
        if directl.exists():
            paths.append(directl)
        for path in sorted(set(paths)):
            try:
                parsed_objects = parse_file(path)
            except Exception as exc:  # pragma: no cover - defensive
                rejects.append(Reject(path, stream, str(exc)))
                continue
            for obj in parsed_objects:
                if not isinstance(obj, dict):
                    rejects.append(Reject(path, stream, "Non-object JSON entry"))
                    continue
                cleaned = clean_data(obj)
                items.append(RawItem(cleaned, path, stream))
    return items, rejects


def write_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            json.dump(record, fh, ensure_ascii=False, sort_keys=True)
            fh.write("\n")


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, sort_keys=True, indent=2)


def write_csv(path: Path, headers: List[str], rows: Iterable[Iterable[Any]]) -> None:
    import csv

    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)


def dump_manual_review(base_dir: Path, filename: str, records: Iterable[Dict[str, Any]]) -> None:
    target = base_dir / "_manual_review" / filename
    with target.open("w", encoding="utf-8") as fh:
        json.dump(list(records), fh, ensure_ascii=False, sort_keys=True, indent=2)


def dump_rejects(base_dir: Path, rejects: Iterable[Reject]) -> None:
    records = []
    for reject in rejects:
        records.append({
            "path": str(reject.source_path),
            "stream": reject.original_stream,
            "error": reject.error,
        })
    if not records:
        return
    dump_manual_review(base_dir, "_rejects.json", records)

