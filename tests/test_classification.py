from __future__ import annotations

from tools.fix import classify, io


def test_classification_moves_vocab_out_of_lessons(sample_raw_dir):
    items, _ = io.load_raw_items(sample_raw_dir)
    result = classify.classify_items(items)
    vocab_lemmas = {item.data.get("lemma") for item in result.vocabulary}
    assert "hablar" in vocab_lemmas
    assert result.crosswalk["moved_to_vocabulary"]
    assert not result.manual_review
