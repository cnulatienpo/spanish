# Codex Rebuilder

`mix codex.rebuild` walks the `content/` tree, heals merge conflicts, normalises lessons and vocabulary, validates them against strict JSON schemas, and emits canonical artefacts under `build/`.

## Usage

```bash
mix deps.get
mix codex.rebuild --write
```

Use `--check` to run without touching canonical files and `--strict` to fail when any invalid or `UNSET` level entries remain.
