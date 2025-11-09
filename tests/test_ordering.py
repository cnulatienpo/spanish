from __future__ import annotations

import json

from tools.fix import run


def test_ordering_inserts_pre_vocab_and_respects_dependencies(sample_raw_dir, tmp_path):
    out_dir = tmp_path / "clean"
    orders = run(str(sample_raw_dir), str(out_dir))

    lessons = [
        json.loads(line)
        for line in (out_dir / "lessons.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    target = next(lesson for lesson in lessons if lesson["title"] == "Present Tense -ar Part 2")
    prepack = next(
        lesson
        for lesson in lessons
        if lesson["title"] == f"Pre-vocab Pack: {target['title']}"
    )
    assert prepack["id"] in target["requires_grammar"]
    stub_id = prepack["requires_vocab"][0]
    assert stub_id in target["requires_vocab"]
    assert orders["lesson_order"].index(prepack["id"]) < orders["lesson_order"].index(target["id"])

    forms_map = json.loads((out_dir / "forms_map.json").read_text(encoding="utf-8"))
    assert "nuevos" in forms_map
    assert forms_map["nuevos"]
