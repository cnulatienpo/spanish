# Repo Healer Quickstart

This repository now ships a TypeScript-powered healer that normalizes the
`content/` tree and produces canonical lesson and vocabulary bundles.

## Environment

```bash
npm install
```

## Usage

Run a dry validation to see what would be produced:

```bash
npm run check
```

Generate canonical artifacts and audit reports:

```bash
npm run rebuild
```

Add `--strict` to either command to fail on invalid items or unknown CEFR levels.
