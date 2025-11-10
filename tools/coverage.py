#!/usr/bin/env python3
"""Vocabulary coverage planning utilities."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict, Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


@dataclass
class VocabEntry:
    word: str
    pos: str
    level: str
    source_file: Path
    data: dict

    @property
    def normalized(self) -> str:
        return self.word.casefold()


def load_vocab(scan_dir: Path) -> List[VocabEntry]:
    entries: List[VocabEntry] = []
    for path in sorted(scan_dir.rglob("*.json")):
        if not path.is_file():
            continue
        try:
            items = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Failed parsing {path}: {exc}") from exc
        if not isinstance(items, list):
            raise SystemExit(f"Expected list in {path}")
        for item in items:
            if not isinstance(item, dict):
                continue
            word = item.get("word")
            pos = item.get("pos", "other")
            level = item.get("level")
            if not word or not level:
                continue
            entries.append(
                VocabEntry(
                    word=str(word),
                    pos=str(pos).lower(),
                    level=str(level),
                    source_file=path,
                    data=item,
                )
            )
    return entries


def load_targets(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        targets = json.load(fh)
    if "levels" not in targets or "total_target" not in targets:
        raise SystemExit("targets.json must define 'levels' and 'total_target'")
    return targets


def load_domain_map(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_frequency(freq_dir: Path) -> List[dict]:
    rows: List[dict] = []
    for csv_path in sorted(freq_dir.glob("*.csv")):
        with csv_path.open("r", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh, fieldnames=["lemma", "frequency", "pos", "domain_hint"])
            for row in reader:
                lemma = row.get("lemma")
                freq = row.get("frequency")
                if not lemma or lemma.lower() == "lemma":
                    # Skip header row if present
                    continue
                try:
                    frequency = int(freq)
                except (TypeError, ValueError):
                    frequency = 0
                rows.append(
                    {
                        "lemma": lemma.strip(),
                        "frequency": frequency,
                        "pos": (row.get("pos") or "other").lower(),
                        "domain_hint": (row.get("domain_hint") or "").strip(),
                        "source": csv_path.name,
                    }
                )
    rows.sort(key=lambda r: (-r["frequency"], r["lemma"].casefold()))
    return rows


def compute_counts(entries: Iterable[VocabEntry]) -> Tuple[Counter, Counter, Counter]:
    level_counts: Counter = Counter()
    pos_counts: Counter = Counter()
    domain_counts: Counter = Counter()
    for entry in entries:
        level_counts[entry.level] += 1
        pos_counts[entry.pos] += 1
        domain = entry.data.get("domain") or entry.data.get("domain_hint") or "unspecified"
        domain_counts[str(domain)] += 1
    return level_counts, pos_counts, domain_counts


def compute_duplicates(entries: Iterable[VocabEntry]) -> List[dict]:
    index: Dict[str, List[VocabEntry]] = defaultdict(list)
    for entry in entries:
        index[entry.normalized].append(entry)
    duplicates = []
    for word, items in sorted(index.items()):
        levels = {item.level for item in items}
        if len(levels) <= 1:
            continue
        duplicates.append(
            {
                "word": items[0].word,
                "occurrences": [
                    {
                        "level": item.level,
                        "file": str(item.source_file),
                    }
                    for item in items
                ],
            }
        )
    return duplicates


def determine_pos_status(pos_counts: Counter, total: int, pos_mix: dict) -> Dict[str, dict]:
    status = {}
    for pos, (min_ratio, max_ratio) in pos_mix.items():
        count = pos_counts.get(pos, 0)
        share = (count / total) if total else 0.0
        if share < min_ratio:
            flag = "below"
        elif share > max_ratio:
            flag = "above"
        else:
            flag = "within"
        status[pos] = {
            "count": count,
            "share": share,
            "target_range": [min_ratio, max_ratio],
            "status": flag,
        }
    # Include any additional POS encountered
    for pos, count in pos_counts.items():
        if pos in status:
            continue
        share = (count / total) if total else 0.0
        status[pos] = {
            "count": count,
            "share": share,
            "target_range": None,
            "status": "extra",
        }
    return status


def plan_suggestions(
    entries: List[VocabEntry],
    freq_rows: List[dict],
    level_targets: Dict[str, int],
    pos_status: Dict[str, dict],
) -> Dict[str, List[dict]]:
    existing = {entry.normalized for entry in entries}
    level_counts, _, _ = compute_counts(entries)
    level_gaps = {
        level: max(level_targets.get(level, 0) - level_counts.get(level, 0), 0)
        for level in level_targets
    }
    pos_needs = {pos for pos, info in pos_status.items() if info.get("status") == "below"}

    suggestions: Dict[str, List[dict]] = {level: [] for level in level_targets}
    used: set[str] = set()

    # Iterate frequency rows sorted by frequency descending
    for row in freq_rows:
        lemma_norm = row["lemma"].casefold()
        if lemma_norm in existing or lemma_norm in used:
            continue
        # Identify candidate levels that still have a gap
        remaining_levels = [lvl for lvl, gap in sorted(level_gaps.items(), key=lambda item: (-item[1], item[0])) if gap > 0]
        if not remaining_levels:
            break
        chosen_level = remaining_levels[0]
        reasons = {
            "level_gap": level_gaps[chosen_level],
        }
        if row["pos"] in pos_needs:
            reasons["pos_gap"] = row["pos"]
        if row.get("domain_hint"):
            reasons["domain_hint"] = row["domain_hint"]
        suggestion = {
            "lemma": row["lemma"],
            "frequency": row["frequency"],
            "pos": row["pos"],
            "domain_hint": row.get("domain_hint") or None,
            "reasons": reasons,
        }
        suggestions[chosen_level].append(suggestion)
        used.add(lemma_norm)
        level_gaps[chosen_level] = max(level_gaps[chosen_level] - 1, 0)
    return suggestions


def write_json_report(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def format_level_table(level_counts: Dict[str, dict]) -> str:
    headers = f"{'Level':<6} {'Count':>8} {'Target':>8} {'Gap':>8} {'Coverage':>10}"
    lines = [headers, "-" * len(headers)]
    for level, info in sorted(level_counts.items()):
        coverage = f"{info['coverage']*100:5.1f}%" if info["target"] else "--"
        lines.append(
            f"{level:<6} {info['count']:>8} {info['target']:>8} {info['gap']:>8} {coverage:>10}"
        )
    return "\n".join(lines)


def format_pos_table(pos_status: Dict[str, dict]) -> str:
    headers = f"{'POS':<12} {'Count':>8} {'Share':>8} {'Target':>15} {'Status':>10}"
    lines = [headers, "-" * len(headers)]
    for pos, info in sorted(pos_status.items()):
        share = f"{info['share']*100:5.1f}%"
        if info["target_range"]:
            target = f"{info['target_range'][0]*100:.0f}-{info['target_range'][1]*100:.0f}%"
        else:
            target = "--"
        lines.append(
            f"{pos:<12} {info['count']:>8} {share:>8} {target:>15} {info['status']:>10}"
        )
    return "\n".join(lines)


def write_text_report(
    path: Path,
    level_stats: Dict[str, dict],
    pos_status: Dict[str, dict],
    duplicates: List[dict],
    suggestions: Dict[str, List[dict]],
) -> None:
    lines: List[str] = []
    lines.append("Vocabulary coverage summary")
    lines.append("")
    lines.append("By level:")
    lines.append(format_level_table(level_stats))
    lines.append("")
    lines.append("By part of speech:")
    lines.append(format_pos_table(pos_status))
    lines.append("")
    if duplicates:
        lines.append("Duplicates across levels:")
        for dup in duplicates:
            locs = ", ".join(f"{item['level']} ({Path(item['file']).name})" for item in dup["occurrences"])
            lines.append(f"  - {dup['word']}: {locs}")
        lines.append("")
    lines.append("Suggested adds (top gaps):")
    for level, items in sorted(suggestions.items()):
        if not items:
            continue
        lines.append(f"  {level}:")
        for suggestion in items[:50]:
            reason_bits = []
            if "pos_gap" in suggestion["reasons"]:
                reason_bits.append(f"POS {suggestion['pos']}")
            if suggestion.get("domain_hint"):
                reason_bits.append(suggestion["domain_hint"])
            if not reason_bits:
                reason_bits.append("level gap")
            reason_text = ", ".join(reason_bits)
            lines.append(
                f"    - {suggestion['lemma']} ({suggestion['pos']}, {suggestion['frequency']}): {reason_text}"
            )
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def build_level_stats(level_counts: Counter, level_targets: Dict[str, int]) -> Dict[str, dict]:
    stats: Dict[str, dict] = {}
    for level, target in level_targets.items():
        count = level_counts.get(level, 0)
        gap = target - count
        stats[level] = {
            "count": count,
            "target": target,
            "gap": gap,
            "coverage": (count / target) if target else 0.0,
        }
    return stats


def plan_command(args: argparse.Namespace) -> None:
    scan_dir = Path(args.scan)
    freq_dir = Path(args.freq)
    targets_path = Path(args.targets)
    domains_path = Path(args.domains)
    out_json = Path(args.out)
    out_summary = Path(args.summary)

    entries = load_vocab(scan_dir)
    targets = load_targets(targets_path)
    domain_map = load_domain_map(domains_path)
    freq_rows = load_frequency(freq_dir)

    level_counts, pos_counts, domain_counts = compute_counts(entries)
    level_stats = build_level_stats(level_counts, targets["levels"])
    pos_status = determine_pos_status(pos_counts, sum(pos_counts.values()), targets.get("pos_mix", {}))
    duplicates = compute_duplicates(entries)
    suggestions = plan_suggestions(entries, freq_rows, targets["levels"], pos_status)

    report = {
        "total_entries": sum(level_counts.values()),
        "total_target": targets.get("total_target"),
        "levels": level_stats,
        "pos": pos_status,
        "domains": domain_counts,
        "domain_map": domain_map,
        "duplicates": duplicates,
        "suggestions": suggestions,
    }

    write_json_report(out_json, report)
    write_text_report(out_summary, level_stats, pos_status, duplicates, suggestions)

    print("Coverage summary:")
    print(f"  Total entries: {report['total_entries']} / {report['total_target']}")
    for level, info in sorted(level_stats.items()):
        pct = f"{info['coverage']*100:5.1f}%" if info['target'] else "--"
        print(f"    {level}: {info['count']} / {info['target']} ({pct})")
    missing_levels = {lvl: len(items) for lvl, items in suggestions.items() if items}
    if missing_levels:
        print("  Suggestions ready for:")
        for level, count in sorted(missing_levels.items()):
            print(f"    {level}: {count} candidates")
    else:
        print("  No suggestion gaps identified")
    print(f"  JSON report: {out_json}")
    print(f"  Summary: {out_summary}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Vocabulary coverage planner")
    subparsers = parser.add_subparsers(dest="command")

    plan_parser = subparsers.add_parser("plan", help="Generate coverage report")
    plan_parser.add_argument("--scan", required=True, help="Directory containing vocab batches")
    plan_parser.add_argument("--freq", required=True, help="Directory with frequency CSV seeds")
    plan_parser.add_argument("--targets", required=True, help="Targets JSON configuration")
    plan_parser.add_argument("--domains", required=True, help="Domain configuration JSON")
    plan_parser.add_argument("--out", required=True, help="Path to write JSON report")
    plan_parser.add_argument("--summary", required=True, help="Path to write text summary")
    plan_parser.set_defaults(func=plan_command)

    return parser


def main(argv: List[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
