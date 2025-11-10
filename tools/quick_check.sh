#!/usr/bin/env bash
set -euo pipefail
python tools/repo_healer.py --check || exit 1
grep -R -nE '<<<<<<<|=======|>>>>>>>' content || true
