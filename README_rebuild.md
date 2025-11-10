# Repo Healer Quickstart

This repository ships with a standalone healing pipeline that normalizes the
`content/` tree and produces canonical lesson and vocabulary bundles.

## Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

Run a dry validation to see what would be produced:

```bash
python tools/repo_healer.py --check
```

Generate canonical artifacts and audit reports:

```bash
python tools/repo_healer.py --write
```

Add `--strict` to make unknown CEFR levels fail the run.
