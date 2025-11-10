# Spanish Corpus Repair Toolkit

This repository provides a reproducible pipeline that repairs and normalises the
Spanish learning corpora used for lessons and vocabulary.  The command line
interface ingests messy JSON/JSONL sources, fixes common formatting problems,
classifies misplaced entries, deduplicates records, enforces vocabulary
coverage for lessons, and emits validated JSONL datasets ordered from easiest
to hardest.

## Quickstart

```bash
python -m pip install -r requirements.txt  # once, optional if jsonschema unavailable
python -m tools.fix --in ./data_raw --out ./data_clean
```

The `--strict` flag turns unresolved ambiguities into hard errors, while
`--rebuild` is reserved for future cache invalidation (currently a no-op).
All outputs are written under the chosen `--out` directory. Running the
pipeline repeatedly is idempotent.

## Pipeline Overview

1. **Load & Repair** – Parses every `*.json`/`*.jsonl` file under
   `lessons/` and `vocabulary/` (plus top-level files). Trailing commas,
   BOMs, and lightweight syntax issues are auto-corrected; unrecoverable files
   are copied to `_rejects` with an error report. Keys are coerced to
   `snake_case` and all strings are NFC-normalised.
2. **Classify** – Heuristics detect whether each object represents a vocabulary
   entry or a lesson. Misfiled items are redirected and tracked in
   `crosswalk.json`. Ambiguous objects fall into `_manual_review` unless
   `--strict` is used.
3. **Normalise** – Legacy field names are mapped to the target schemas.
   Stable IDs are generated (`vocab__<slug>` / `lesson__<slug>`), enum values
   are coerced, bilingual examples are structured, and default placeholders are
   filled where appropriate.
4. **Deduplicate** – Records with matching lemmas or titles are merged.
   Conflicting text keeps the richest description, while tags, examples, and
   synonyms are unioned. A detailed merge log is written to
   `reports/dedup_log.csv`.
5. **Coverage & Stubs** – Lessons are tokenised with a Spanish-friendly regex.
   Vocabulary coverage is enforced by mapping simple plural/verb variants back
   to known lemmas. Unknown forms produce stub vocabulary entries (tagged
   `auto_stub` + `needs_review`) and, when required, an automatically generated
   “Pre-vocab Pack” lesson inserted before the dependent lesson. Coverage
   metrics land in `reports/coverage_report.csv`, and new stubs are tracked in
   `reports/new_stub_vocabulary.csv`.
6. **Ordering & Difficulty** – Difficulty scores for vocabulary and lessons
   combine part-of-speech weighting, text complexity, structural cues, and
   prerequisite counts. A topological sort honours `requires_grammar` chains
   (including inferred “Part 1/Part 2” relationships) so the final ordering is
   both difficulty-aware and dependency-safe.
7. **Validation & Export** – JSON Schemas in `/schemas` are applied via
   `jsonschema`. Any validation failures are listed in
   `reports/validation_errors.csv`. Cleaned corpora are written to
   `vocabulary.jsonl`, `lessons.jsonl`, `forms_map.json`, and
   `index_order.json` (holding the canonical easy→hard ordering).

## Difficulty Heuristics

Vocabulary difficulty starts at 1.0 and increases based on rarity (simple
built-in frequency hints), part-of-speech weighting, irregularity tags,
and lemma length. Lesson difficulty starts at 2.0 and incorporates grammar
keywords, table presence, token density, new vocabulary load, and explicit
cross-lesson references. Scores are clipped between 1 and 10 and stored inside
each record.

## Reviewing Manual Buckets

The pipeline is conservative with uncertain data. Anything that cannot be
classified or normalised with confidence is copied to `_manual_review` in the
output directory. Start by reconciling those JSON dumps, update the raw data,
and re-run the CLI. Stub vocabulary entries flagged via
`reports/new_stub_vocabulary.csv` should be promoted into fully fleshed entries
(or removed) once definitions are confirmed.

---

## Vocabulary Pipeline

**Install**
```bash
pip install jsonschema
```

**Generate batches**
```bash
# Put headwords (one per line) into vocab/data/headwords/A1.txt (etc.)
python tools/generate.py --level A1 --in vocab/data/headwords/A1.txt --out vocab/out/A1/batch_001.json --batch-size 200
```

**Validate**
```bash
mkdir -p reports
bash ci/check.sh
```

**Split / Dedupe / Report (optional)**
```bash
python tools/split_batches.py --in vocab/out/B1/big.json --out-dir vocab/out/B1 --batch-size 200
python tools/dedupe.py --scan-dir vocab/out --out vocab/deduped.json --conflicts reports/dupe_conflicts.json
python tools/report.py --scan-dir vocab/out --out reports/agg.json --summary reports/agg.txt
```

**Targets:** A1:600 A2:1000 B1:1400 B2:1400 C1:900 C2:700  (Total 6000)

## Curation Passes

- **Curation Style Guide** — See [curator/style_guide.md](curator/style_guide.md) for tone and formatting rules covering the `english`, `origin`, `story`, and `example` fields. All curation passes must follow it.

