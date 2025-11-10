# MixMethod Spanish Canonical Rebuilder

This repo includes a fully automated fixer for Merge conflicts and canonical data regeneration.

## Requirements

* Node.js 20+
* npm (or a compatible package manager)

Install dependencies once:

```bash
npm install
```

## Rebuild workflow

To repair the `content/` directory, normalize entries, and rewrite the canonical bundles and audit report run:

```bash
npm run rebuild
```

This command performs:

1. Conflict marker resolution with both variants preserved for merging.
2. Classification into Lessons or Vocabulary.
3. Schema normalization, deduplication, deterministic sorting, and canonical emission under `build/`.
4. Validation (JSON Schema, idempotency check, and conflict marker scans).
5. Console summary of the audit report.

## Verification-only mode

To ensure that the repository is already in canonical form without rewriting files, run:

```bash
npm run check
```

`npm run check` rebuilds data in-memory, confirms idempotency, validates against schemas, and fails if the existing canonical files are out-of-date or invalid.
