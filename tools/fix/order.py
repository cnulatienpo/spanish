from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from .normalize import slugify

COMMON_LEMMAS = {
    "ser",
    "estar",
    "tener",
    "haber",
    "ir",
    "yo",
    "tu",
    "tú",
    "el",
    "él",
    "ella",
    "nosotros",
    "ustedes",
    "tiempo",
    "casa",
    "grande",
    "pequeño",
    "hola",
    "adios",
    "adiós",
}

POS_WEIGHTS = {
    "verb": 0.8,
    "adj": 0.5,
    "noun": 0.3,
}

GRAMMAR_KEYWORDS = {
    "subjuntiv": 1.5,
    "condicional": 1.0,
    "perífrasis": 1.0,
    "perifrasis": 1.0,
    "conjug": 0.7,
    "tabla": 0.5,
    "table": 0.5,
    "relativo": 0.7,
    "pronombre": 0.6,
}


@dataclass
class OrderResult:
    vocabulary_order: List[str]
    lesson_order: List[str]


def score_vocabulary(entry: Dict[str, Any]) -> float:
    score = 1.0
    lemma_key = entry["lemma"].lower()
    if lemma_key not in COMMON_LEMMAS:
        score += 0.5
    score += POS_WEIGHTS.get(entry.get("pos"), 0.2)
    if "irregular" in entry.get("tags", []):
        score += 0.4
    if len(entry["lemma"]) >= 10:
        score += 0.1
    return max(1.0, min(10.0, round(score, 2)))


def _collect_text_from_lesson(lesson: Dict[str, Any]) -> str:
    pieces: List[str] = []
    for block in lesson.get("content_blocks", []):
        if isinstance(block, dict):
            if isinstance(block.get("text"), str):
                pieces.append(block["text"])
            if isinstance(block.get("data"), str):
                pieces.append(block["data"])
            if isinstance(block.get("items"), list):
                for item in block["items"]:
                    if isinstance(item, dict):
                        pieces.extend(str(v) for v in item.values() if isinstance(v, str))
                    elif isinstance(item, str):
                        pieces.append(item)
    return " \n".join(pieces)


def score_lesson(lesson: Dict[str, Any], stats: Dict[str, Any]) -> float:
    score = 2.0
    text = _collect_text_from_lesson(lesson).lower()
    for keyword, weight in GRAMMAR_KEYWORDS.items():
        if keyword in text:
            score += weight
    has_table = any(block.get("kind") == "table" for block in lesson.get("content_blocks", []) if isinstance(block, dict))
    if has_table:
        score += 0.5
    unique_tokens = stats.get("unique_es_tokens", 0)
    score += unique_tokens / 100.0
    new_vocab_load = len(lesson.get("requires_vocab", []))
    score += new_vocab_load * 0.02
    cross_refs = len(lesson.get("requires_grammar", []))
    score += cross_refs * 0.3
    return max(1.0, min(10.0, round(score, 2)))


def _normalise_prerequisites(lessons: List[Dict[str, Any]]) -> None:
    id_by_title = {lesson["title"].lower(): lesson["id"] for lesson in lessons}
    id_by_slug = {slugify(lesson["title"]): lesson["id"] for lesson in lessons}
    known_ids = set(id_by_slug.values())
    for lesson in lessons:
        resolved: List[str] = []
        for req in lesson.get("requires_grammar", []):
            req_str = str(req)
            if req_str in known_ids:
                resolved.append(req_str)
                continue
            if req_str.startswith("lesson__") and req_str in known_ids:
                resolved.append(req_str)
                continue
            lower_req = req_str.lower()
            if lower_req in id_by_title:
                resolved.append(id_by_title[lower_req])
                continue
            slug_req = slugify(req_str)
            if slug_req in id_by_slug:
                resolved.append(id_by_slug[slug_req])
        lesson["requires_grammar"] = sorted(set(resolved))

    # Infer sequences like "Part 2"
    part_pattern = re.compile(r"(.*?)(?:\s*-)?\s*part(?:e)?\s*(\d+)", re.IGNORECASE)
    groups: Dict[str, List[Tuple[int, str]]] = {}
    for lesson in lessons:
        match = part_pattern.search(lesson["title"])
        if not match:
            continue
        base = match.group(1).strip().lower()
        try:
            index = int(match.group(2))
        except ValueError:
            continue
        groups.setdefault(base, []).append((index, lesson["id"]))
    for entries in groups.values():
        entries.sort()
        for idx in range(1, len(entries)):
            prev_id = entries[idx - 1][1]
            current_id = entries[idx][1]
            current = next(lesson for lesson in lessons if lesson["id"] == current_id)
            if prev_id not in current["requires_grammar"]:
                current["requires_grammar"].append(prev_id)
                current["requires_grammar"].sort()


def _toposort(lessons: List[Dict[str, Any]], scores: Dict[str, float]) -> List[str]:
    graph: Dict[str, set[str]] = {}
    all_ids = {lesson["id"] for lesson in lessons}
    for lesson in lessons:
        deps = {req for req in lesson.get("requires_grammar", []) if req in all_ids}
        graph[lesson["id"]] = deps
    incoming: Dict[str, int] = {lesson_id: len(deps) for lesson_id, deps in graph.items()}
    ready = [lesson_id for lesson_id, degree in incoming.items() if degree == 0]
    ready.sort(key=lambda lid: (scores.get(lid, 0), lid))
    order: List[str] = []
    while ready:
        current = ready.pop(0)
        order.append(current)
        for node, deps in graph.items():
            if current in deps:
                deps.remove(current)
                incoming[node] -= 1
                if incoming[node] == 0:
                    ready.append(node)
                    ready.sort(key=lambda lid: (scores.get(lid, 0), lid))
    if len(order) != len(graph):
        raise ValueError("Cycle detected in lesson prerequisites")
    return order


def order_items(vocabulary: List[Dict[str, Any]], lessons: List[Dict[str, Any]], lesson_stats: Dict[str, Any]) -> OrderResult:
    for entry in vocabulary:
        entry["difficulty"] = score_vocabulary(entry)
    vocabulary.sort(key=lambda item: (item["difficulty"], item["lemma"]))
    vocabulary_order = [entry["id"] for entry in vocabulary]

    _normalise_prerequisites(lessons)

    lesson_scores: Dict[str, float] = {}
    for lesson in lessons:
        stats = lesson_stats.get(lesson["id"], {})
        lesson_scores[lesson["id"]] = score_lesson(lesson, stats)
        lesson["difficulty"] = lesson_scores[lesson["id"]]

    lesson_order = _toposort(lessons, lesson_scores)
    return OrderResult(vocabulary_order, lesson_order)

