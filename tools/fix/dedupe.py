from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple

from .normalize import slugify


@dataclass
class DedupResult:
    vocabulary: List[Dict[str, Any]]
    lessons: List[Dict[str, Any]]
    log_rows: List[Tuple[str, str, str, str]]


def _lemma_key(lemma: str) -> str:
    normalized = unicodedata.normalize("NFKD", lemma).encode("ascii", "ignore").decode("ascii")
    return normalized.lower()


def _merge_text(a: str, b: str) -> str:
    if not a:
        return b
    if not b:
        return a
    return a if len(a) >= len(b) else b


def _merge_optional(a: Any, b: Any) -> Any:
    return a if a not in (None, "") else b


def dedupe_vocabulary(items: List[Dict[str, Any]], log_rows: List[Tuple[str, str, str, str]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for item in items:
        key = _lemma_key(item["lemma"])
        grouped.setdefault(key, []).append(item)

    merged_items: List[Dict[str, Any]] = []
    for entries in grouped.values():
        primary = entries[0].copy()
        primary["id"] = f"vocab__{slugify(primary['lemma'])}"
        tags = set(primary.get("tags", []))
        examples = {json.dumps(example, sort_keys=True, ensure_ascii=False): example for example in primary.get("examples", [])}
        synonyms = set(primary.get("synonyms", []))

        for other in entries[1:]:
            log_rows.append(("vocabulary", primary["id"], other["id"], "merged duplicate lemma"))
            primary["english_gloss"] = _merge_text(primary.get("english_gloss", ""), other.get("english_gloss", ""))
            primary["definition_es"] = _merge_text(primary.get("definition_es", ""), other.get("definition_es", ""))
            primary["notes"] = _merge_text(primary.get("notes", ""), other.get("notes", ""))
            primary["pos"] = _merge_optional(primary.get("pos"), other.get("pos"))
            primary["gender"] = _merge_optional(primary.get("gender"), other.get("gender"))
            primary["number"] = _merge_optional(primary.get("number"), other.get("number"))
            primary["register"] = _merge_optional(primary.get("register"), other.get("register"))
            tags.update(other.get("tags", []))
            synonyms.update(other.get("synonyms", []))
            for example in other.get("examples", []):
                key = json.dumps(example, sort_keys=True, ensure_ascii=False)
                if key not in examples:
                    examples[key] = example
        primary["tags"] = sorted(tag for tag in tags if tag)
        primary["synonyms"] = sorted(syn for syn in synonyms if syn)
        primary["examples"] = list(examples.values())
        merged_items.append(primary)
    return merged_items


def dedupe_lessons(items: List[Dict[str, Any]], log_rows: List[Tuple[str, str, str, str]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for item in items:
        key = slugify(item["title"])
        grouped.setdefault(key, []).append(item)

    merged_items: List[Dict[str, Any]] = []
    for entries in grouped.values():
        primary = entries[0].copy()
        primary["id"] = f"lesson__{slugify(primary['title'])}"
        objectives = list(primary.get("objectives", []))
        blocks = {json.dumps(block, sort_keys=True, ensure_ascii=False): block for block in primary.get("content_blocks", [])}
        practice_refs = set(primary.get("practice_refs", []))
        requires_grammar = set(primary.get("requires_grammar", []))
        requires_vocab = set(primary.get("requires_vocab", []))

        for other in entries[1:]:
            log_rows.append(("lesson", primary["id"], other["id"], "merged duplicate title"))
            objectives.extend(obj for obj in other.get("objectives", []) if obj not in objectives)
            for block in other.get("content_blocks", []):
                key = json.dumps(block, sort_keys=True, ensure_ascii=False)
                if key not in blocks:
                    blocks[key] = block
            practice_refs.update(other.get("practice_refs", []))
            requires_grammar.update(other.get("requires_grammar", []))
            requires_vocab.update(other.get("requires_vocab", []))

        primary["objectives"] = objectives
        primary["content_blocks"] = list(blocks.values())
        primary["practice_refs"] = sorted(practice_refs)
        primary["requires_grammar"] = sorted(requires_grammar)
        primary["requires_vocab"] = sorted(requires_vocab)
        merged_items.append(primary)
    return merged_items


def dedupe(vocabulary: List[Dict[str, Any]], lessons: List[Dict[str, Any]]) -> DedupResult:
    log_rows: List[Tuple[str, str, str, str]] = []
    vocab = dedupe_vocabulary(vocabulary, log_rows)
    lesson = dedupe_lessons(lessons, log_rows)
    return DedupResult(vocab, lesson, log_rows)

