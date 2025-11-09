from __future__ import annotations

import json

from tools.fix import run


def test_schema_validation_report_empty(sample_raw_dir, tmp_path):
    out_dir = tmp_path / "clean"
    run(str(sample_raw_dir), str(out_dir))
    report_path = out_dir / "reports" / "validation_errors.csv"
    lines = report_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1  # header only
    vocab_entries = [json.loads(line) for line in (out_dir / "vocabulary.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    assert all(entry["type"] == "vocabulary" for entry in vocab_entries)
    lesson_entries = [json.loads(line) for line in (out_dir / "lessons.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    assert all(entry["type"] == "lesson" for entry in lesson_entries)
