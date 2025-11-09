from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def sample_raw_dir(tmp_path: Path) -> Path:
    raw_dir = tmp_path / "data_raw"
    lessons_dir = raw_dir / "lessons"
    vocab_dir = raw_dir / "vocabulary"
    lessons_dir.mkdir(parents=True)
    vocab_dir.mkdir(parents=True)

    mixed_lessons = [
        {
            "Title": "Saludos Básicos",
            "Objectives": "Aprender saludos",
            "Content": "Hola y adiós.",
            "Practice_refs": ["intro_1"],
        },
        {
            "Title": "Present Tense -ar Part 1",
            "Objectives": ["Conjugate -ar verbs"],
            "Content": "Yo hablo. Tú hablas.",
            "Examples": ["Yo hablo || I speak", "Tú hablas || You speak"],
        },
        {
            "lemma": "hablar",
            "pos": "verbo",
            "english": "to speak",
            "definition": "Comunicar palabras.",
        },
    ]
    (lessons_dir / "mixed.json").write_text(json.dumps(mixed_lessons, ensure_ascii=False), encoding="utf-8")

    part_two = {
        "title": "Present Tense -ar Part 2",
        "content_blocks": [
            {
                "kind": "explanation",
                "text": "Nosotros hablamos con amigos nuevos.",
            }
        ],
    }
    (lessons_dir / "part2.jsonl").write_text(json.dumps(part_two, ensure_ascii=False) + "\n", encoding="utf-8")

    malformed_lesson = '{"title": "Broken", "content": [1,2,,]}'
    (lessons_dir / "bad.json").write_text(malformed_lesson, encoding="utf-8")

    vocab_entries = [
        {
            "word": "hola",
            "meaning": "hello",
            "definition_es": "Saludo.",
            "pos": "interjeccion",
        },
        {
            "word": "adiós",
            "meaning": "goodbye",
            "definition_es": "Despedida.",
            "pos": "interjeccion",
        },
        {
            "lemma": "tiempo",
            "pos": "sustantivo",
            "english_gloss": "time",
            "definition_es": "Duración.",
        },
    ]
    vocab_lines = "\n".join(json.dumps(entry, ensure_ascii=False) for entry in vocab_entries)
    (vocab_dir / "core.jsonl").write_text(vocab_lines + "\n", encoding="utf-8")

    malformed_vocab = "[{\"lemma\": \"amigo\", \"pos\": \"sustantivo\", \"english\": \"friend\", \"definition\": \"Persona cercana\",}]"
    (vocab_dir / "malformed.json").write_text(malformed_vocab, encoding="utf-8")

    return raw_dir

