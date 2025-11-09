from __future__ import annotations

from tools.fix import io


def test_parse_and_repair_handles_trailing_commas(sample_raw_dir):
    items, rejects = io.load_raw_items(sample_raw_dir)
    lemmas = {item.data.get("lemma") for item in items if item.data.get("lemma")}
    assert "hablar" in lemmas
    assert any(reject.source_path.name == "bad.json" for reject in rejects)
