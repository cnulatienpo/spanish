#!/usr/bin/env python3
import argparse, sys, os, re
from pathlib import Path

CONFLICT_RE = re.compile(r'^<<<<<<<|^=======|^>>>>>>>', re.M)

def scan_conflict_markers(root: Path):
    hits = []
    for p in root.rglob('*'):
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        for m in CONFLICT_RE.finditer(text):
            line = text.count('
', 0, m.start()) + 1
            hits.append((str(p), line, m.group(0).strip()))
    return hits

def main():
    import argparse
    ap = argparse.ArgumentParser(description='Repo Healer (bootstrap) — conflict guard + stubs')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--strict', action='store_true')
    args = ap.parse_args()

    root = Path('content')
    root.mkdir(parents=True, exist_ok=True)
    hits = scan_conflict_markers(root)

    report_dir = Path('build/reports'); report_dir.mkdir(parents=True, exist_ok=True)
    audit_path = report_dir / 'audit-bootstrap.md'

    lines = []
    lines.append('Repo Healer (bootstrap)')
    lines.append(f'- conflict markers: {len(hits)}')
    if hits:
        lines.append('## markers')
        for path, line, tok in hits[:200]:
            lines.append(f'- {path}:{line} `{tok}`')
        if len(hits) > 200:
            lines.append(f'… and {len(hits)-200} more')

    audit_path.write_text('
'.join(lines), encoding='utf-8')
    print('
'.join(lines))

    if hits and (args.strict or args.check):
        return 1
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
