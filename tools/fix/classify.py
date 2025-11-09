from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from .io import RawItem


VOCAB_CUES = {
    "lemma",
    "word",
    "spanish",
    "gloss",
    "meaning",
    "definition_es",
    "english_gloss",
    "pos",
    "part_of_speech",
}

LESSON_CUES = {
    "title",
    "objectives",
    "content_blocks",
    "sections",
    "steps",
    "practice_refs",
}


@dataclass
class ClassificationResult:
    vocabulary: List[RawItem]
    lessons: List[RawItem]
    manual_review: List[Dict[str, str]]
    crosswalk: Dict[str, List[str]]


def _score_vocab(data: Dict[str, object]) -> int:
    score = 0
    keys = set(data)
    score += len(keys & VOCAB_CUES) * 2
    if any(k in data for k in ("lemma", "spanish", "word")):
        score += 3
    if isinstance(data.get("definition_es"), str) and len(data["definition_es"]) < 200:
        score += 1
    return score


def _score_lesson(data: Dict[str, object]) -> int:
    score = 0
    keys = set(data)
    score += len(keys & LESSON_CUES) * 2
    if isinstance(data.get("title"), str):
        score += 3
    if isinstance(data.get("content_blocks"), list) and data["content_blocks"]:
        score += 2
    text = " ".join(
        str(data.get(key, ""))
        for key in ("content", "body", "explanation", "text")
        if isinstance(data.get(key), str)
    )
    if len(text) > 160:
        score += 1
    return score


def classify_items(items: List[RawItem], strict: bool = False) -> ClassificationResult:
    vocabulary: List[RawItem] = []
    lessons: List[RawItem] = []
    manual_review: List[Dict[str, str]] = []
    crosswalk = {"moved_to_vocabulary": [], "moved_to_lessons": []}

    for item in items:
        vocab_score = _score_vocab(item.data)
        lesson_score = _score_lesson(item.data)
        label: str | None
        if vocab_score == 0 and lesson_score == 0:
            label = None
        elif vocab_score >= lesson_score:
            label = "vocabulary"
        else:
            label = "lesson"

        if label is None:
            manual_review.append(
                {
                    "path": str(item.source_path),
                    "reason": "ambiguous",
                    "original_stream": item.original_stream,
                }
            )
            continue

        if label == "vocabulary":
            vocabulary.append(item)
            if item.original_stream != "vocabulary":
                crosswalk["moved_to_vocabulary"].append(str(item.source_path))
        else:
            lessons.append(item)
            if item.original_stream != "lessons":
                crosswalk["moved_to_lessons"].append(str(item.source_path))

    if strict and manual_review:
        raise ValueError("Ambiguous items require manual review in strict mode")

    return ClassificationResult(vocabulary, lessons, manual_review, crosswalk)

