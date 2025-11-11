#!/usr/bin/env python3
import argparse, re, json, sys
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
            line = text.count('\n', 0, m.start()) + 1
            hits.append((str(p), line, m.group(0).strip()))
    return hits

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Repo Healer quick check — scans for conflict markers')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--strict', action='store_true')
    args = ap.parse_args()

    root = Path('content'); root.mkdir(parents=True, exist_ok=True)
    hits = scan_conflict_markers(root)

    out = ['Repo Healer quick check', f'- conflict markers: {len(hits)}']
    if hits:
        out.append('## markers')
        out += [f"- {p}:{ln} {tok}" for p,ln,tok in hits[:200]]
    Path('build/reports').mkdir(parents=True, exist_ok=True)
    Path('build/reports/audit-bootstrap.md').write_text('\n'.join(out), encoding='utf-8')
    print('\n'.join(out))

    if hits and (args.check or args.strict):
        sys.exit(1)
