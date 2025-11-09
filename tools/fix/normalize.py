from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .io import RawItem, normalize_string

POS_ALIASES = {
    "sustantivo": "noun",
    "sustantivo masculino": "noun",
    "sustantivo femenino": "noun",
    "verbo": "verb",
    "adjetivo": "adj",
    "adverbio": "adv",
    "preposicion": "prep",
    "preposición": "prep",
    "conjuncion": "conj",
    "conjunción": "conj",
    "pronombre": "pron",
    "determinante": "det",
    "numeral": "num",
    "interjeccion": "interj",
    "interjección": "interj",
    "auxiliar": "aux",
    "expresion": "expr",
    "expresión": "expr",
}

GENDER_ALIASES = {
    "masculino": "masculine",
    "femenino": "feminine",
    "masculine": "masculine",
    "feminine": "feminine",
}

NUMBER_ALIASES = {
    "singular": "singular",
    "plural": "plural",
    "invariable": "invariant",
    "invariante": "invariant",
}

REGISTER_ALIASES = {
    "formal": "formal",
    "informal": "informal",
    "neutral": "neutral",
}

CEFR_LEVELS = {"a1", "a2", "b1", "b2", "c1", "c2"}

SLUG_RE = re.compile(r"[^a-z0-9]+")


@dataclass
class NormalizationResult:
    vocabulary: List[Dict[str, Any]]
    lessons: List[Dict[str, Any]]
    manual_review: List[Dict[str, str]]


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = SLUG_RE.sub("-", value).strip("-")
    return value or "item"


def _first_non_empty(data: Dict[str, Any], keys: Iterable[str]) -> Optional[str]:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _normalise_pos(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = value.lower().strip()
    value = value.replace(".", "")
    if value in POS_ALIASES:
        return POS_ALIASES[value]
    allowed = {
        "noun",
        "verb",
        "adj",
        "adv",
        "prep",
        "conj",
        "pron",
        "det",
        "num",
        "interj",
        "aux",
        "expr",
    }
    return value if value in allowed else None


def _map_enum(value: Optional[str], mapping: Dict[str, str]) -> Optional[str]:
    if not value:
        return None
    value = value.lower().strip()
    if value in mapping:
        return mapping[value]
    inverse = set(mapping.values())
    return value if value in inverse else None


def _ensure_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [normalize_string(str(item)) for item in value if str(item).strip()]
    if isinstance(value, str):
        if not value:
            return []
        parts = [normalize_string(part) for part in re.split(r"[;,\n]", value) if part.strip()]
        return parts
    return [normalize_string(str(value))]


def _normalise_examples(value: Any) -> List[Dict[str, str]]:
    if not value:
        return []
    examples: List[Dict[str, str]] = []
    values: List[Any]
    if isinstance(value, list):
        values = value
    else:
        values = [value]
    for item in values:
        if isinstance(item, dict):
            es = normalize_string(str(item.get("es", ""))) if item.get("es") else ""
            en = normalize_string(str(item.get("en", ""))) if item.get("en") else ""
            if es or en:
                examples.append({"es": es, "en": en})
            continue
        if isinstance(item, str):
            if "||" in item:
                es, en = [normalize_string(part) for part in item.split("||", 1)]
            elif "|" in item:
                es, en = [normalize_string(part) for part in item.split("|", 1)]
            else:
                es, en = normalize_string(item), ""
            examples.append({"es": es, "en": en})
    return examples


def normalize_vocabulary(items: List[RawItem]) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    normalized: List[Dict[str, Any]] = []
    manual: List[Dict[str, str]] = []
    for item in items:
        data = item.data
        lemma = _first_non_empty(data, ("lemma", "spanish", "word", "palabra"))
        if not lemma:
            manual.append({"path": str(item.source_path), "reason": "missing lemma"})
            continue
        lemma = normalize_string(lemma)
        slug = slugify(lemma)

        pos = _normalise_pos(_first_non_empty(data, ("pos", "part_of_speech", "tipo")))
        gender = _map_enum(_first_non_empty(data, ("gender", "genero", "género")), GENDER_ALIASES)
        number = _map_enum(_first_non_empty(data, ("number", "numero", "número")), NUMBER_ALIASES)
        register = _map_enum(_first_non_empty(data, ("register", "registro")), REGISTER_ALIASES)

        english_gloss = _first_non_empty(data, ("english_gloss", "gloss", "meaning", "english")) or ""
        definition_es = _first_non_empty(data, ("definition_es", "def_es", "definicion", "definición", "definition")) or ""
        notes = _first_non_empty(data, ("notes", "nota", "notas")) or ""

        tags = _ensure_list(data.get("tags") or data.get("labels") or data.get("etiquetas"))
        if register is None and data.get("register"):
            tags.append("needs_review")
        if pos is None:
            tags.append("needs_review")

        synonyms = _ensure_list(data.get("synonyms") or data.get("sinonimos") or data.get("sinónimos"))
        examples = _normalise_examples(data.get("examples") or data.get("ejemplos"))

        normalized.append(
            {
                "id": f"vocab__{slug}",
                "type": "vocabulary",
                "lemma": lemma,
                "pos": pos,
                "gender": gender,
                "number": number,
                "english_gloss": english_gloss,
                "definition_es": definition_es,
                "register": register,
                "tags": sorted({tag for tag in tags if tag}),
                "examples": examples,
                "synonyms": sorted({syn for syn in synonyms if syn}),
                "notes": notes,
            }
        )
    return normalized, manual


def _normalise_content_blocks(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []
    existing = data.get("content_blocks")
    if isinstance(existing, list) and existing:
        for block in existing:
            if isinstance(block, dict):
                kind = block.get("kind") or "explanation"
                blocks.append({"kind": kind, **{k: v for k, v in block.items() if k != "kind"}})
            elif isinstance(block, str):
                blocks.append({"kind": "explanation", "text": block})
    else:
        text_fields = [
            normalize_string(str(data.get(key)))
            for key in ("content", "body", "texto")
            if isinstance(data.get(key), str)
        ]
        if text_fields:
            blocks.append({"kind": "explanation", "text": "\n\n".join(text_fields)})
    examples = data.get("examples")
    if isinstance(examples, list) and examples:
        block_items = []
        for item in _normalise_examples(examples):
            block_items.append(item)
        if block_items:
            blocks.append({"kind": "examples", "items": block_items})
    return blocks


def normalize_lessons(items: List[RawItem]) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    normalized: List[Dict[str, Any]] = []
    manual: List[Dict[str, str]] = []
    for item in items:
        data = item.data
        title = _first_non_empty(data, ("title", "name", "lesson", "heading"))
        if not title:
            manual.append({"path": str(item.source_path), "reason": "missing title"})
            continue
        title = normalize_string(title)
        slug = slugify(title)

        cefr = _first_non_empty(data, ("cefr", "cefr_hint", "level"))
        cefr_hint = cefr.lower() if cefr and cefr.lower() in CEFR_LEVELS else None

        objectives_raw = data.get("objectives") or data.get("goals")
        objectives = _ensure_list(objectives_raw)
        if not objectives and isinstance(data.get("objective"), str):
            objectives = [normalize_string(data["objective"])]

        content_blocks = _normalise_content_blocks(data)
        practice_refs = _ensure_list(data.get("practice_refs") or data.get("practice_ids"))
        requires_grammar = _ensure_list(data.get("requires_grammar") or data.get("prerequisites"))

        normalized.append(
            {
                "id": f"lesson__{slug}",
                "type": "lesson",
                "title": title,
                "cefr_hint": cefr_hint,
                "objectives": objectives,
                "content_blocks": content_blocks,
                "practice_refs": practice_refs,
                "requires_grammar": requires_grammar,
                "requires_vocab": [],
            }
        )
    return normalized, manual


def merge_manual(*groups: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    merged: List[Dict[str, str]] = []
    for group in groups:
        merged.extend(group)
    return merged


def normalize(classification_result: "ClassificationResult") -> NormalizationResult:
    from .classify import ClassificationResult

    vocab, vocab_manual = normalize_vocabulary(classification_result.vocabulary)
    lessons, lesson_manual = normalize_lessons(classification_result.lessons)
    manual = merge_manual(classification_result.manual_review, vocab_manual, lesson_manual)
    return NormalizationResult(vocab, lessons, manual)

