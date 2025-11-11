# Codex Repo Healer Prompts

(Appended v14 below.)

## v14 — Node ESM Minimal (zero deps)
Paste into Codex. It will output a single `tools/repo_healer.mjs` using **pure ESM** and **no npm deps** (only Node ≥ 18).

**ROLE:** Senior JS engineer. Build a one-file CLI (`repo_healer.mjs`) that:
- Recursively scans `content/**/*`
- Heals Git conflicts (`<<<<<<<`, `=======`, `>>>>>>>`) capturing A/B and deep-merging deterministically
- Extracts JSON blocks from mixed text
- Classifies into Lessons/Vocabulary
- Normalizes to strict schemas
- Dedupes + CEFR sorts
- Validates against embedded JSON Schemas (lightweight in-file validator)
- Writes: canonical JSON, audit.md, and rejects/

**Constraints**
- **No imports beyond Node core**: `fs`, `path`, `url`, `crypto`.
- Deterministic output; stable key order on write.
- Idempotent across runs.

**CLI**
```bash
node tools/repo_healer.mjs --check
node tools/repo_healer.mjs --write
node tools/repo_healer.mjs --strict
```

**Merge policy** (same as earlier versions)
- Scalars: newer mtime else longer string; keep loser in `notes.alt_variant`
- Arrays: union with stable order; strings compared after whitespace normalization
- Objects: deep merge; `definition|origin|story` concatenate with `\n\n— MERGED VARIANT —\n\n` when both present & unequal

**IDs**
- Vocab: `mmspanish__vocab_${sha256(spanish|pos|genderOrNull).slice(0,16)}`
- Lesson: `mmspanish__grammar_${unit.padStart(3,'0')}_${slug(title)}`

**Deliverables**
- `tools/repo_healer.mjs` (standalone)
- Optional: add npm scripts in package.json to run `check`/`write`
