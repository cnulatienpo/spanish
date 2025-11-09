#!/usr/bin/env bash
set -euo pipefail
mkdir -p reports
python tools/validate.py --scan-dir vocab/out --require-alpha --out-report reports/verify.json --out-summary reports/verify.txt --fail-on ERROR || true
echo "Report written to reports/verify.json and reports/verify.txt"
