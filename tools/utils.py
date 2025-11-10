from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import orjson

try:
    import rapidjson  # type: ignore
except Exception:  # pragma: no cover
    rapidjson = None  # type: ignore

CEFR_ORDER = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6, "UNSET": 7}
MERGE_SEPARATOR = "\n\n— MERGED VARIANT —\n\n"


def tolerant_load(text: str) -> Any:
    stripped = text.strip()
    if not stripped:
        raise ValueError("empty text")
    if rapidjson is not None:
        try:
            return rapidjson.loads(stripped)
        except Exception:
            pass
    cleaned = _repair_json(stripped)
    try:
        return orjson.loads(cleaned)
    except orjson.JSONDecodeError as exc:
        raise ValueError(f"unable to parse json: {exc}") from exc


def _repair_json(text: str) -> str:
    text = re.sub(r"//.*", "", text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r",(\s*[}\]])", r"\\1", text)
    def repl(match: re.Match[str]) -> str:
        return f'"{match.group(1)}":'
    text = re.sub(r"(?<=\{|,)\s*([A-Za-z0-9_]+)\s*:", repl, text)
    return text


def strip_conflicts(text: str) -> List[object]:
    pattern = re.compile(
        r"<<<<<<[^\n]*\n(?P<a>.*?)\n=======(?P<b>.*?)\n>>>>>>>[^\n]*",
        re.DOTALL,
    )
    segments: List[object] = []
    last = 0
    for match in pattern.finditer(text):
        start, end = match.span()
        if start > last:
            segments.append(text[last:start])
        segments.append({"A": match.group("a"), "B": match.group("b"), "marker": match.group(0)})
        last = end
    if last < len(text):
        segments.append(text[last:])
    return segments


def choose_newer_or_longer(
    a: Any,
    b: Any,
    mtimes: Optional[Tuple[Optional[datetime], Optional[datetime]]] = None,
) -> Tuple[Any, Any]:
    if mtimes:
        ma, mb = mtimes
        if ma and mb and ma != mb:
            return (a, b) if ma > mb else (b, a)
        if ma and not mb:
            return a, b
        if mb and not ma:
            return b, a
    a_len = len(str(a))
    b_len = len(str(b))
    if b_len > a_len:
        return b, a
    return a, b


def deep_merge(
    base: Any,
    incoming: Any,
    *,
    mtimes: Optional[Tuple[Optional[datetime], Optional[datetime]]] = None,
    alt_store: Optional[Dict[str, Any]] = None,
    path: Tuple[str, ...] = (),
) -> Any:
    if alt_store is None:
        alt_store = {}
    if base is None:
        return incoming
    if incoming is None:
        return base
    if isinstance(base, dict) and isinstance(incoming, dict):
        for key, value in incoming.items():
            if key in base:
                merged = deep_merge(
                    base[key],
                    value,
                    mtimes=mtimes,
                    alt_store=alt_store,
                    path=path + (str(key),),
                )
                if (
                    key in {"definition", "origin", "story"}
                    and isinstance(base[key], str)
                    and isinstance(merged, str)
                ):
                    base[key] = _merge_narrative(base[key], merged)
                else:
                    base[key] = merged
            else:
                base[key] = value
        return base
    if isinstance(base, list) and isinstance(incoming, list):
        seen: List[str] = []
        merged_list: List[Any] = []
        for item in base + incoming:
            key = _normalize_list_item(item)
            if key not in seen:
                seen.append(key)
                merged_list.append(item)
            else:
                if alt_store is not None:
                    alt_store.setdefault("duplicates", []).append({"path": "/".join(path), "value": item})
        return merged_list
    if isinstance(base, (str, int, float, bool)) and isinstance(incoming, (str, int, float, bool)):
        winner, loser = choose_newer_or_longer(base, incoming, mtimes)
        chosen = base if winner is base else incoming
        rejected = incoming if winner is base else base
        if rejected != chosen and alt_store is not None:
            alt_store.setdefault("alt_variant", {})["/".join(path)] = rejected
        return winner
    return incoming


def _merge_narrative(original: str, incoming: str) -> str:
    if not original.strip():
        return incoming
    if not incoming.strip():
        return original
    if original.strip() == incoming.strip():
        return original
    if incoming in original:
        return original
    if original in incoming:
        return incoming
    return f"{original}{MERGE_SEPARATOR}{incoming}"


def _normalize_list_item(item: Any) -> str:
    if isinstance(item, str):
        return " ".join(item.split()).strip().lower()
    return json.dumps(item, sort_keys=True, ensure_ascii=False)


def cefr_sort_key(item: Dict[str, Any]) -> Tuple[int, int, int, str]:
    level = item.get("level", "UNSET")
    unit = item.get("unit")
    lesson_number = item.get("lesson_number")
    identifier = item.get("id", "")
    return (
        CEFR_ORDER.get(level, CEFR_ORDER["UNSET"]),
        unit if isinstance(unit, int) else 9999,
        lesson_number if isinstance(lesson_number, int) else 9999,
        identifier,
    )


def stablehash(value: str) -> str:
    return hashlib.blake2b(value.encode("utf-8"), digest_size=8).hexdigest()


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-") or "untitled"


def ensure_notes(updated: Dict[str, Any], alt_store: Dict[str, Any]) -> None:
    if not alt_store:
        return
    existing = updated.get("notes")
    payload: Dict[str, Any]
    if existing:
        try:
            payload = json.loads(existing)
            if not isinstance(payload, dict):
                payload = {"original_notes": existing}
        except Exception:
            payload = {"original_notes": existing}
    else:
        payload = {}
    for key, value in alt_store.items():
        if key == "alt_variant":
            payload.setdefault("alt_variant", {}).update(value)
        else:
            payload[key] = value
    updated["notes"] = orjson.dumps(payload, option=orjson.OPT_SORT_KEYS).decode("utf-8")


def extract_json_blocks(text: str) -> List[str]:
    spans: List[str] = []
    start_stack: List[int] = []
    opening_stack: List[str] = []
    in_string = False
    escape = False
    for index, char in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char in "[{":
            start_stack.append(index)
            opening_stack.append(char)
            continue
        if char in "]}":
            if not start_stack:
                continue
            opening_stack.pop()
            start = start_stack.pop()
            if not start_stack:
                spans.append(text[start : index + 1])
    return spans


def to_datetime(path: Path) -> Optional[datetime]:
    try:
        stat = path.stat()
    except OSError:
        return None
    return datetime.fromtimestamp(stat.st_mtime)
