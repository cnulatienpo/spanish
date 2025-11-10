# Codex Rebuilder

`codex_rebuilder` scans the `content/` tree, resolves merge conflicts, heals broken JSON, and emits canonical lesson and vocabulary datasets for MixMethod Spanish.

## Quickstart

```bash
cargo build --release
./target/release/codex_rebuilder --check
./target/release/codex_rebuilder --write
```

## Sanity Check

Run the rebuild then confirm that no merge conflict markers remain:

```bash
./target/release/codex_rebuilder --write && \
  grep -R -nE '<<<<<<<|=======|>>>>>>>' content || true
```

## Usage

- `--check`: run the scanner, report the audit, and leave existing files untouched.
- `--write`: (default) rebuild canonical JSON, audit, and reject fragments.
- `--strict`: treat schema failures or `level=UNSET` items as fatal.

The CLI writes:

- `build/canonical/lessons.mmspanish.json`
- `build/canonical/vocabulary.mmspanish.json`
- `build/reports/audit.md`
- `build/rejects/` (fragments that could not be repaired)

Outputs are deterministic and idempotent. Running `--write` twice produces identical files.
