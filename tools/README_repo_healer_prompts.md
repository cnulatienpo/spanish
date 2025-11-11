# Codex Repo Healer Prompts

(Addendum for v12 is appended below.)

## v12 — Makefile + awk-only (ultra-minimal, no jq)
Paste into Codex. It will emit a POSIX `Makefile` and an `awk`-driven validator so the pipeline can run even on stripped-down systems.

**ROLE:** Senior build engineer. Generate:
- `Makefile` targets: `check`, `write`, `strict`, `clean`.
- A portable `tools/repo_healer_awk.sh` using `awk`, `sed`, `grep`, `sha256sum` only.
- A tiny JSON checker implemented in `awk` for primitives/arrays/objects (relaxed).
- Same semantics as prior versions: conflict healing, classification, normalization, dedupe, CEFR sort, idempotent outputs.

**Outputs**
- `build/canonical/lessons.mmspanish.json`
- `build/canonical/vocabulary.mmspanish.json`
- `build/reports/audit.md`
- `build/rejects/`

**CLI**
```sh
make check
make write
make strict
```

**Edge notes**
- If JSON too broken for awk checker, route fragment to `build/rejects/` with original text.
- Keep English examples verbatim; merge `definition|origin|story` with the standard separator.

(Full v12 prompt content: see commit body in this PR.)
