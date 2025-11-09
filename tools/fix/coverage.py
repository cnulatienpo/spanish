from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from .normalize import slugify

TOKEN_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", re.UNICODE)


@dataclass
class CoverageResult:
    vocabulary: List[Dict[str, Any]]
    lessons: List[Dict[str, Any]]
    forms_map: Dict[str, str]
    coverage_rows: List[Tuple[str, int, int, int, float]]
    stub_rows: List[Tuple[str, str]]
    forward_refs: List[Tuple[str, str, str]]
    lesson_stats: Dict[str, Dict[str, Any]]


def _lemma_key(value: str) -> str:
    return unicodedata.normalize("NFC", value).lower()


def _collect_strings(block: Dict[str, Any]) -> List[str]:
    strings: List[str] = []
    if not isinstance(block, dict):
        return strings
    kind = block.get("kind")
    if kind == "explanation":
        text = block.get("text")
        if isinstance(text, str):
            strings.append(text)
    elif kind == "examples":
        for item in block.get("items", []):
            if isinstance(item, dict) and isinstance(item.get("es"), str):
                strings.append(item["es"])
    elif kind == "table":
        data = block.get("data")
        if isinstance(data, dict):
            for value in data.values():
                if isinstance(value, str):
                    strings.append(value)
                elif isinstance(value, list):
                    strings.extend(str(v) for v in value if isinstance(v, str))
        elif isinstance(data, str):
            strings.append(data)
    else:
        for value in block.values():
            if isinstance(value, str):
                strings.append(value)
    return strings


def _tokenise(text: str) -> List[str]:
    return TOKEN_RE.findall(text)


def _guess_plural(token_key: str) -> List[str]:
    guesses: List[str] = []
    if token_key.endswith("es"):
        guesses.append(token_key[:-2])
    if token_key.endswith("s"):
        guesses.append(token_key[:-1])
    return guesses


def _guess_verbs(token_key: str) -> List[str]:
    guesses: List[str] = []
    endings = ["o", "as", "a", "amos", "an", "es", "e", "emos", "en", "imos", "ís", "ís", "ís", "áis", "an", "ían", "aba", "abas", "ábamos", "aban"]
    for ending in endings:
        if token_key.endswith(ending) and len(token_key) > len(ending) + 2:
            stem = token_key[: -len(ending)]
            for infinitive in (stem + "ar", stem + "er", stem + "ir"):
                guesses.append(infinitive)
    return guesses


def analyse_coverage(vocabulary: List[Dict[str, Any]], lessons: List[Dict[str, Any]]) -> CoverageResult:
    lemma_index: Dict[str, Dict[str, Any]] = {}
    forms_map: Dict[str, str] = {}
    existing_vocab_ids = set()
    for entry in vocabulary:
        key = _lemma_key(entry["lemma"])
        lemma_index[key] = entry
        forms_map[key] = entry["lemma"]
        existing_vocab_ids.add(entry["id"])

    coverage_rows: List[Tuple[str, int, int, int, float]] = []
    stub_rows: List[Tuple[str, str]] = []
    forward_refs: List[Tuple[str, str, str]] = []
    lesson_stats: Dict[str, Dict[str, Any]] = {}
    new_lessons: List[Dict[str, Any]] = []

    for lesson in lessons:
        strings: List[str] = []
        for block in lesson.get("content_blocks", []):
            strings.extend(_collect_strings(block))
        total_tokens = 0
        known_tokens = 0
        unknown_tokens = 0
        unique_tokens: set[str] = set()
        stubs_for_lesson: List[Dict[str, Any]] = []
        stub_ids_for_lesson: set[str] = set()
        requires_vocab: set[str] = set(lesson.get("requires_vocab", []))

        for text in strings:
            for token in _tokenise(text):
                total_tokens += 1
                token_key = _lemma_key(token)
                unique_tokens.add(token_key)
                resolved = None
                if token_key in lemma_index:
                    resolved = lemma_index[token_key]
                elif token_key in forms_map:
                    lemma_value = forms_map[token_key]
                    resolved = lemma_index[_lemma_key(lemma_value)]
                else:
                    # plural guesses
                    for guess in _guess_plural(token_key):
                        if guess in lemma_index:
                            resolved = lemma_index[guess]
                            forms_map[token_key] = resolved["lemma"]
                            break
                    if resolved is None:
                        for guess in _guess_verbs(token_key):
                            guess_key = _lemma_key(guess)
                            if guess_key in lemma_index:
                                resolved = lemma_index[guess_key]
                                forms_map[token_key] = resolved["lemma"]
                                break
                if resolved:
                    known_tokens += 1
                    requires_vocab.add(resolved["id"])
                else:
                    unknown_tokens += 1
                    slug = slugify(token)
                    vocab_id = f"vocab__{slug}"
                    if vocab_id not in existing_vocab_ids and vocab_id not in stub_ids_for_lesson:
                        stub_entry = {
                            "id": vocab_id,
                            "type": "vocabulary",
                            "lemma": token,
                            "pos": None,
                            "gender": None,
                            "number": None,
                            "english_gloss": "",
                            "definition_es": "",
                            "register": None,
                            "tags": ["auto_stub", "needs_review"],
                            "examples": [],
                            "synonyms": [],
                            "notes": "",
                        }
                        vocabulary.append(stub_entry)
                        lemma_index[_lemma_key(token)] = stub_entry
                        forms_map[token_key] = token
                        stubs_for_lesson.append(stub_entry)
                        stub_ids_for_lesson.add(vocab_id)
                        existing_vocab_ids.add(vocab_id)
                        stub_rows.append((lesson["id"], token))
                        requires_vocab.add(vocab_id)
                    else:
                        requires_vocab.add(vocab_id)
        coverage = (known_tokens / total_tokens) * 100 if total_tokens else 100.0
        coverage_rows.append((lesson["id"], total_tokens, known_tokens, unknown_tokens, round(coverage, 2)))
        lesson_stats[lesson["id"]] = {
            "total_tokens": total_tokens,
            "known_tokens": known_tokens,
            "unknown_tokens": unknown_tokens,
            "unique_es_tokens": len(unique_tokens),
        }
        lesson["requires_vocab"] = sorted(requires_vocab)

        if stubs_for_lesson:
            title = lesson["title"]
            pre_slug = slugify(f"pre-vocab {title}")
            pre_lesson_id = f"lesson__{pre_slug}"
            pre_lesson = {
                "id": pre_lesson_id,
                "type": "lesson",
                "title": f"Pre-vocab Pack: {title}",
                "cefr_hint": lesson.get("cefr_hint"),
                "objectives": [f"Aprender vocabulario clave para {title}"],
                "content_blocks": [
                    {
                        "kind": "explanation",
                        "text": "Este paquete introduce vocabulario necesario para la lección siguiente.",
                    },
                    {
                        "kind": "examples",
                        "items": [{"es": stub["lemma"], "en": stub.get("english_gloss", "")} for stub in stubs_for_lesson],
                    },
                ],
                "practice_refs": [],
                "requires_grammar": [],
                "requires_vocab": [stub["id"] for stub in stubs_for_lesson],
            }
            new_lessons.append(pre_lesson)
            lesson.setdefault("requires_grammar", [])
            if pre_lesson_id not in lesson["requires_grammar"]:
                lesson["requires_grammar"].append(pre_lesson_id)
            for stub in stubs_for_lesson:
                forward_refs.append((lesson["id"], pre_lesson_id, stub["lemma"]))

    lessons.extend(new_lessons)
    return CoverageResult(vocabulary, lessons, forms_map, coverage_rows, stub_rows, forward_refs, lesson_stats)

