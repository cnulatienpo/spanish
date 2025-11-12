"""Shared helpers for the vocabulary gating tools."""

from __future__ import annotations

import csv
import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, MutableMapping, MutableSequence, Optional, Tuple, Union

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "gate" / "config"
DEFAULT_BANK_PATH = ROOT / "vocab" / "bank.csv"
DEFAULT_KITS_PATH = ROOT / "vocab" / "kits.csv"
DEFAULT_ALWAYS_ALLOW_PATH = CONFIG_DIR / "always_allow.json"
DEFAULT_FORMS_MAP_PATH = CONFIG_DIR / "forms_map.json"


@dataclass
class BankEntry:
    form: str
    lemma: str
    pos: str
    features: str
    level: str
    english: str


@dataclass
class Kit:
    kit_id: str
    forms: List[str]
    normalized_forms: List[str]
    notes: str


@dataclass
class GateLocation:
    container: Union[MutableMapping[str, Any], MutableSequence[Any]]
    key: Union[str, int]
    text: str
    path: Tuple[Any, ...]


def load_json(path: Union[str, Path]) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_forms_map(path: Optional[Union[str, Path]]) -> Dict[str, bool]:
    cfg_path = Path(path) if path else DEFAULT_FORMS_MAP_PATH
    if not cfg_path.exists():
        return {"normalize": True, "lower": True, "strip_punct": True}
    data = load_json(cfg_path)
    return {
        "normalize": bool(data.get("normalize", True)),
        "lower": bool(data.get("lower", True)),
        "strip_punct": bool(data.get("strip_punct", True)),
    }


def normalize_form(text: Optional[str], config: Dict[str, bool]) -> str:
    if text is None:
        return ""
    value = text
    if config.get("normalize", True):
        value = unicodedata.normalize("NFC", value)
    if config.get("strip_punct", True):
        # strip common punctuation used around tokens
        value = value.strip("\"'`¡!¿?.,:;()[]{}<>«»—-·…“”")
    value = value.strip()
    if config.get("lower", True):
        value = value.lower()
    return value


def load_bank(path: Optional[Union[str, Path]], config: Dict[str, bool]) -> Dict[str, List[BankEntry]]:
    csv_path = Path(path) if path else DEFAULT_BANK_PATH
    entries: Dict[str, List[BankEntry]] = {}
    with open(csv_path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            form = row.get("form", "").strip()
            if not form:
                continue
            normalized = normalize_form(form, config)
            if not normalized:
                continue
            entry = BankEntry(
                form=form,
                lemma=row.get("lemma", ""),
                pos=row.get("pos", ""),
                features=row.get("features", ""),
                level=row.get("level", ""),
                english=row.get("english", ""),
            )
            entries.setdefault(normalized, []).append(entry)
    return entries


def load_kits(path: Optional[Union[str, Path]], config: Dict[str, bool]) -> Dict[str, Kit]:
    csv_path = Path(path) if path else DEFAULT_KITS_PATH
    kits: Dict[str, Kit] = {}
    if not csv_path.exists():
        return kits
    with open(csv_path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            kit_id = row.get("kit_id", "").strip()
            if not kit_id:
                continue
            forms_field = row.get("unlocks_forms", "")
            notes = row.get("notes", "").strip()
            raw_forms = [f.strip() for f in forms_field.split("|") if f.strip()]
            normalized_forms = [normalize_form(form, config) for form in raw_forms if normalize_form(form, config)]
            kits[kit_id] = Kit(kit_id=kit_id, forms=raw_forms, normalized_forms=normalized_forms, notes=notes)
    return kits


def load_always_allow(path: Optional[Union[str, Path]], config: Dict[str, bool]) -> Tuple[set[str], set[str]]:
    json_path = Path(path) if path else DEFAULT_ALWAYS_ALLOW_PATH
    raw_tokens: set[str] = set()
    normalized: set[str] = set()
    if json_path.exists():
        data = load_json(json_path)
        for token in data.get("tokens", []):
            if not isinstance(token, str):
                continue
            raw_tokens.add(token)
            norm = normalize_form(token, config)
            if norm:
                normalized.add(norm)
    return raw_tokens, normalized


def load_progress(path: Union[str, Path], kits: Dict[str, Kit], config: Dict[str, bool]) -> set[str]:
    data = load_json(path)
    allowed: set[str] = set()
    for form in data.get("allow_forms", []):
        if not isinstance(form, str):
            continue
        normalized = normalize_form(form, config)
        if normalized:
            allowed.add(normalized)
    for kit_id in data.get("kits", []):
        kit = kits.get(kit_id)
        if not kit:
            continue
        allowed.update(kit.normalized_forms)
    return allowed


def build_form_to_kits(kits: Dict[str, Kit]) -> Dict[str, List[str]]:
    mapping: Dict[str, List[str]] = {}
    for kit_id, kit in kits.items():
        for norm_form in kit.normalized_forms:
            mapping.setdefault(norm_form, []).append(kit_id)
    return mapping


def is_spanish_key(key: Optional[Union[str, int]]) -> bool:
    if key is None:
        return False
    key_str = str(key).lower()
    if not key_str:
        return False
    if key_str in {"es", "spanish", "spanish_line", "spanish_text", "spanish_sentence"}:
        return True
    if key_str.endswith("_es"):
        return True
    if "spanish" in key_str:
        return True
    return False


def update_context(context: Optional[Dict[str, Any]], obj: MutableMapping[str, Any]) -> Dict[str, Any]:
    field_spanish: set[str] = set()
    list_spanish: set[str] = set()
    if context:
        field_spanish.update(context.get("field_spanish", set()))
        list_spanish.update(context.get("list_spanish", set()))
    phase_raw = obj.get("phase") or obj.get("kind")
    if isinstance(phase_raw, str):
        phase = phase_raw.lower()
        if phase in {"spanish_entry", "spanish_focus", "spanish_reveal", "spanish_prompt", "spanish_flash", "spanish_line"}:
            field_spanish.add("line")
        if phase in {"mix_repetition", "mix_dialogue", "mix_pattern"}:
            list_spanish.add("pattern")
        if phase in {"mix_ladder", "ladder", "ladder_spanish"}:
            list_spanish.add("lines")
        if phase == "context_scene":
            field_spanish.update({"es", "you"})
        if phase in {"dialogue", "dialogue_spanish", "conversation_spanish"}:
            list_spanish.add("lines")
    return {"field_spanish": field_spanish, "list_spanish": list_spanish}


def should_gate_field(key: Union[str, int], context: Dict[str, Any]) -> bool:
    key_lower = str(key).lower()
    if key_lower in context.get("field_spanish", set()):
        return True
    return is_spanish_key(key)


def should_gate_list(key: Union[str, int], context: Dict[str, Any]) -> bool:
    key_lower = str(key).lower()
    if key_lower in context.get("list_spanish", set()):
        return True
    return is_spanish_key(key)


def iter_spanish_locations(obj: Any, path: Tuple[Any, ...] = (), context: Optional[Dict[str, Any]] = None) -> Iterator[GateLocation]:
    if isinstance(obj, MutableMapping):
        new_context = update_context(context, obj)
        for key, value in obj.items():
            new_path = path + (key,)
            if isinstance(value, str):
                if should_gate_field(key, new_context):
                    yield GateLocation(container=obj, key=key, text=value, path=new_path)
            elif isinstance(value, MutableSequence):
                if should_gate_list(key, new_context):
                    for idx, item in enumerate(value):
                        list_path = new_path + (idx,)
                        if isinstance(item, str):
                            yield GateLocation(container=value, key=idx, text=item, path=list_path)
                        else:
                            yield from iter_spanish_locations(item, list_path, new_context)
                else:
                    for idx, item in enumerate(value):
                        yield from iter_spanish_locations(item, new_path + (idx,), new_context)
            elif isinstance(value, MutableMapping):
                yield from iter_spanish_locations(value, new_path, new_context)
    elif isinstance(obj, MutableSequence):
        for idx, item in enumerate(obj):
            list_path = path + (idx,)
            if isinstance(item, str):
                if context and context.get("list_spanish"):
                    yield GateLocation(container=obj, key=idx, text=item, path=list_path)
            else:
                yield from iter_spanish_locations(item, list_path, context)


def tokenize(text: str) -> List[Tuple[str, int, int]]:
    tokens: List[Tuple[str, int, int]] = []
    idx = 0
    length = len(text)
    while idx < length:
        char = text[idx]
        if char.isspace():
            idx += 1
            continue
        if char.isalnum() or char == "_":
            start = idx
            idx += 1
            while idx < length and (text[idx].isalnum() or text[idx] == "_"):
                idx += 1
            tokens.append((text[start:idx], start, idx))
        else:
            start = idx
            idx += 1
            tokens.append((text[start:idx], start, idx))
    return tokens
