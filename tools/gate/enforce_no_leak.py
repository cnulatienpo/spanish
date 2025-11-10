#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Iron-clad vocabulary leak guard:
- Enforces that no Spanish surface form appears unless it is listed in the learned ledger.
- Modes:
    check  : scan and fail on first violation (or list all with --report).
    compile: produce sanitized copies with unknown Spanish replaced by English glosses.
Usage:
  python tools/gate/enforce_no_leak.py \
    --bank vocab/bank.csv \
    --learned progress/learned/A1_step_0002.json \
    --scan lessons/out/A1 docs/ ui/ \
    --mode check --strict
  # or compile a playable Spanglish build:
  python tools/gate/enforce_no_leak.py \
    --bank vocab/bank.csv \
    --learned progress/learned/A1_step_0002.json \
    --scan lessons/out/A1 \
    --mode compile --out build/A1_step_0002
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence, Set, Tuple

WORD_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:'[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)?", re.UNICODE)

Token = str
Gloss = str
Violation = Dict[str, str]


def load_bank(path: Path) -> Dict[Token, Gloss]:
    bank: Dict[Token, Gloss] = {}
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):
            form = (row.get("form") or "").strip()
            eng = (row.get("english") or "").strip()
            if not form:
                continue
            key = normalize(form)
            if key in bank and bank[key] != eng:
                print(
                    f"[WARN] Duplicate form '{form}' in vocab bank with different gloss; keeping first.",
                    file=sys.stderr,
                )
                continue
            bank[key] = eng
    return bank


def load_learned(path: Path) -> Set[Token]:
    with path.open(encoding="utf-8") as f:
        obj = json.load(f)
    return {normalize(t) for t in obj.get("allow_forms", [])}


def load_always(path: Optional[Path]) -> Set[Token]:
    if path is None:
        return set()
    if not path.exists():
        return set()
    with path.open(encoding="utf-8") as f:
        obj = json.load(f)
    return {normalize(t) for t in obj.get("tokens", [])}


def normalize(token: str) -> str:
    return unicodedata.normalize("NFKC", token).strip().lower()


def is_json_file(p: Path) -> bool:
    return p.suffix.lower() == ".json"


def iter_files(paths: Sequence[str]) -> Iterator[Path]:
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            for root, _, files in os.walk(p):
                for name in files:
                    yield Path(root) / name
        elif p.is_file():
            yield p


def tokenize(text: str) -> List[str]:
    return [m.group(0) for m in WORD_RE.finditer(text)]


def process_string(
    s: str,
    bank: Dict[Token, Gloss],
    allowed: Set[Token],
    always: Set[Token],
    mode: str,
) -> Tuple[str, List[Tuple[str, str]]]:
    """Returns (output_str, violations)."""
    tokens = tokenize(s)
    if mode == "check":
        violations: List[Tuple[str, str]] = []
        for t in tokens:
            nt = normalize(t)
            if nt in bank and nt not in allowed and nt not in always:
                violations.append((t, bank.get(nt, "")))
        return s, violations
    else:
        result: List[str] = []
        last_end = 0
        for match in WORD_RE.finditer(s):
            t = match.group(0)
            nt = normalize(t)
            if nt in bank and nt not in allowed and nt not in always:
                gloss = bank.get(nt, "")
                replacement = gloss if gloss else f"[{t}]"
                result.append(s[last_end:match.start()])
                result.append(replacement)
                last_end = match.end()
            else:
                result.append(s[last_end:match.end()])
                last_end = match.end()
        result.append(s[last_end:])
        return "".join(result), []


def resolve_out_path(file_path: Path, scan_roots: Sequence[Path], out_root: Path) -> Path:
    file_path = file_path.resolve()
    for root in scan_roots:
        root_resolved = root.resolve()
        if root.is_dir():
            try:
                rel = file_path.relative_to(root_resolved)
                return out_root / rel
            except ValueError:
                continue
        else:
            if file_path == root_resolved:
                return out_root / file_path.name
    # Fallback: flatten
    return out_root / file_path.name


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", required=True)
    ap.add_argument("--learned", required=True, help="path to JSON with { 'allow_forms': [...] }")
    ap.add_argument("--scan", nargs="+", required=True, help="files or directories to scan")
    ap.add_argument(
        "--always",
        default="gate/config/always_allow.json",
        help="JSON with { 'tokens': [...] }",
    )
    ap.add_argument("--mode", choices=["check", "compile"], default="check")
    ap.add_argument("--strict", action="store_true", help="fail on first violation")
    ap.add_argument("--report", help="optional path to write JSON report of violations")
    ap.add_argument("--out", help="output dir for compile mode")
    args = ap.parse_args(argv)

    bank = load_bank(Path(args.bank))
    allowed = load_learned(Path(args.learned))
    always = load_always(Path(args.always) if args.always else None)

    if args.mode == "compile" and not args.out:
        ap.error("--out is required in compile mode")

    out_root = Path(args.out).resolve() if args.out else None
    if out_root:
        out_root.mkdir(parents=True, exist_ok=True)

    scan_roots: List[Path] = [Path(p).resolve() for p in args.scan]

    violations: List[Violation] = []
    exit_code = 0

    for file_path in iter_files(args.scan):
        file_path = file_path.resolve()
        try:
            if is_json_file(file_path):
                with file_path.open(encoding="utf-8") as reader:
                    data = json.load(reader)

                def rewrite(node):
                    if isinstance(node, dict):
                        return {k: rewrite(v) for k, v in node.items()}
                    if isinstance(node, list):
                        return [rewrite(x) for x in node]
                    if isinstance(node, str):
                        new_s, viols = process_string(node, bank, allowed, always, args.mode)
                        if args.mode == "check":
                            for token, gloss in viols:
                                violations.append(
                                    {"file": str(file_path), "token": token, "gloss": gloss}
                                )
                            return node
                        return new_s
                    return node

                rewritten = rewrite(data)

                if args.mode == "compile" and out_root:
                    out_path = resolve_out_path(file_path, scan_roots, out_root)
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    with out_path.open("w", encoding="utf-8") as writer:
                        json.dump(rewritten, writer, ensure_ascii=False, indent=2)
            else:
                with file_path.open("r", encoding="utf-8", errors="ignore") as reader:
                    text = reader.read()
                new_text, viols = process_string(text, bank, allowed, always, args.mode)
                if args.mode == "check":
                    for token, gloss in viols:
                        violations.append({"file": str(file_path), "token": token, "gloss": gloss})
                elif out_root:
                    out_path = resolve_out_path(file_path, scan_roots, out_root)
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    with out_path.open("w", encoding="utf-8") as writer:
                        writer.write(new_text)
        except Exception as exc:  # pragma: no cover - defensive guard for CLI
            print(f"[ERROR] {file_path}: {exc}", file=sys.stderr)
            return 2

        if args.mode == "check" and args.strict and violations:
            last = violations[-1]
            print(
                f"[LEAK] {last['file']}: '{last['token']}' not yet learned (→ '{last['gloss']}')",
                file=sys.stderr,
            )
            return 1

    if args.mode == "check":
        if args.report:
            report_path = Path(args.report)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            with report_path.open("w", encoding="utf-8") as writer:
                json.dump({"violations": violations}, writer, ensure_ascii=False, indent=2)
        if violations:
            print(f"[LEAKS] {len(violations)} unauthorized token(s) found.")
            for v in violations[:50]:
                print(f"  - {v['file']}: '{v['token']}' (→ '{v['gloss']}')")
            exit_code = 1
        else:
            print("No unauthorized Spanish tokens found.")
            exit_code = 0
    else:
        print(f"Compiled sanitized output to: {out_root}")
        exit_code = 0

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
