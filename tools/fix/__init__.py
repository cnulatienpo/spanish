from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from . import classify, coverage, dedupe, io, normalize, order, validate


def run(input_dir: str, output_dir: str, strict: bool = False, rebuild: bool = False) -> Dict[str, List[str]]:
    del rebuild  # No caching implemented yet; placeholder for interface compatibility
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    io.ensure_output_dir(output_path)

    raw_items, rejects = io.load_raw_items(input_path)

    classification = classify.classify_items(raw_items, strict=strict)
    normalization = normalize.normalize(classification)
    if strict and normalization.manual_review:
        raise ValueError("Manual review items remain after normalization")

    deduped = dedupe.dedupe(normalization.vocabulary, normalization.lessons)

    coverage_result = coverage.analyse_coverage(deduped.vocabulary, deduped.lessons)

    order_result = order.order_items(
        coverage_result.vocabulary,
        coverage_result.lessons,
        coverage_result.lesson_stats,
    )

    schema_dir = Path(__file__).resolve().parent.parent.parent / "schemas"
    validation_result = validate.validate_entries(
        coverage_result.vocabulary,
        coverage_result.lessons,
        schema_dir,
        strict=strict,
    )

    # Outputs
    io.write_jsonl(output_path / "vocabulary.jsonl", coverage_result.vocabulary)
    lesson_lookup = {lesson["id"]: lesson for lesson in coverage_result.lessons}
    ordered_lessons = [lesson_lookup[lesson_id] for lesson_id in order_result.lesson_order if lesson_id in lesson_lookup]
    io.write_jsonl(output_path / "lessons.jsonl", ordered_lessons)
    io.write_json(
        output_path / "index_order.json",
        {
            "vocabulary_order": order_result.vocabulary_order,
            "lesson_order": order_result.lesson_order,
        },
    )
    io.write_json(output_path / "forms_map.json", coverage_result.forms_map)
    io.write_json(output_path / "crosswalk.json", classification.crosswalk)

    io.write_csv(
        output_path / "reports" / "coverage_report.csv",
        ["lesson_id", "total_es_tokens", "known_tokens", "unknown_tokens", "percent_covered"],
        coverage_result.coverage_rows,
    )
    io.write_csv(
        output_path / "reports" / "forward_refs.csv",
        ["lesson_id", "prepack_id", "lemma"],
        coverage_result.forward_refs,
    )
    io.write_csv(
        output_path / "reports" / "dedup_log.csv",
        ["entry_type", "primary_id", "merged_id", "reason"],
        deduped.log_rows,
    )
    io.write_csv(
        output_path / "reports" / "new_stub_vocabulary.csv",
        ["lesson_id", "lemma"],
        coverage_result.stub_rows,
    )
    io.write_csv(
        output_path / "reports" / "validation_errors.csv",
        ["entry_type", "entry_id", "message"],
        ((error.entry_type, error.entry_id, error.message) for error in validation_result.errors),
    )

    if normalization.manual_review:
        io.dump_manual_review(output_path, "manual_review.json", normalization.manual_review)
    if rejects:
        io.dump_rejects(output_path, rejects)

    return {
        "vocabulary_order": order_result.vocabulary_order,
        "lesson_order": order_result.lesson_order,
    }

