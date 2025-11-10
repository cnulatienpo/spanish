#!/usr/bin/env bash
set -euo pipefail
pip show jsonschema >/dev/null 2>&1 || pip install jsonschema >/dev/null
mkdir -p reports
python tools/validate.py --scan-dir vocab/out --require-alpha --out-report reports/verify.json --out-summary reports/verify.txt --fail-on ERROR
python tools/lint_curated.py --scan vocab/out --out reports/lint.json --summary reports/lint.txt --fail-on ERROR
echo "Curated lint passed."
