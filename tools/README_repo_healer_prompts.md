# Codex Repo Healer Prompts

(Added v13 below.)

## v13 — Python Micro‑CLI (no external deps, stdlib‑only)
Paste into Codex. It will emit a tiny `tools/repo_healer.py` (≤ ~500 lines) that runs on Python 3.10+ without pip installs.

**ROLE:** Senior Python engineer. Generate a single‑file CLI that:
1) Scans `content/**/*`
2) Heals Git conflicts (captures A/B, merges deterministically)
3) Extracts JSON blocks from mixed text
4) Classifies → Lessons / Vocabulary
5) Normalizes to strict schemas
6) Dedupes + CEFR sorts
7) Validates (inline JSON Schema via a minimal validator implemented in stdlib)
8) Writes canonical JSON + audit + rejects

**Constraints**
- **No external packages.** Only `json`, `re`, `hashlib`, `argparse`, `pathlib`, `datetime`, `itertools`, `collections`.
- Deterministic stable key order when writing (custom `sort_keys`).
- Idempotent outputs on repeated runs.

**CLI**
```bash
python tools/repo_healer.py --check
python tools/repo_healer.py --write
python tools/repo_healer.py --strict
```

**IDs**
- Vocab: `mmspanish__vocab_{sha256(spanish|pos|genderOrNull)[:16]}`
- Lesson: `mmspanish__grammar_{unit:03}_{slug(title)}`

**Special merge**
- Scalars: newer mtime else longer string.
- Arrays: union with stable order; string equality normalized on whitespace only.
- Objects: recursive merge; for `definition|origin|story`, concatenate with `\n\n— MERGED VARIANT —\n\n`.

**Minimal schema validator**
Implement checks for required keys, enum membership, types (string/int/array/object/null), and nested array item shapes for examples/steps. If invalid → send to rejects with reason.

**Edge cases**
- Multiple fragments per file
- Non‑noun `gender` → null
- Missing `unit/lesson_number` → 9999 and log

**Deliverables**
- `tools/repo_healer.py` (all logic)
- Updates to CI: add a Python matrix job running `--check`
