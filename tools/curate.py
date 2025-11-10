import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

COLUMNS = [
    "file",
    "index",
    "word",
    "pos",
    "gender",
    "level",
    "english",
    "origin",
    "story",
    "example",
    "auto_english",
    "auto_origin",
    "auto_story",
    "auto_example",
]

STORY_POS_DESCRIPTORS = {
    "noun": "un sustantivo frecuente",
    "verb": "un verbo común",
    "adjective": "un adjetivo descriptivo",
    "adverb": "un adverbio útil",
    "phrase": "una expresión habitual",
}

EXAMPLE_LIMITS = {
    "A1": 140,
    "A2": 140,
    "B1": 220,
    "B2": 220,
    "C1": 280,
    "C2": 280,
}


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def load_batches(level: str) -> List[Tuple[Path, List[dict]]]:
    base = Path("vocab/out") / level
    if not base.exists():
        raise FileNotFoundError(f"Level directory not found: {base}")
    batches: List[Tuple[Path, List[dict]]] = []
    for path in sorted(base.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        batches.append((path, data))
    return batches


def collect_todos(batches: Iterable[Tuple[Path, List[dict]]], limit: int) -> List[dict]:
    rows: List[dict] = []
    for file_path, entries in batches:
        for idx, entry in enumerate(entries):
            if limit and len(rows) >= limit:
                return rows
            if any(entry.get(field, "") == "TODO" for field in ("english", "origin", "story", "example")):
                row = {
                    "file": str(file_path.as_posix()),
                    "index": str(idx),
                    "word": nfc(str(entry.get("word", ""))),
                    "pos": nfc(str(entry.get("pos", ""))),
                    "gender": nfc(str(entry.get("gender", ""))),
                    "level": nfc(str(entry.get("level", ""))),
                    "english": nfc(str(entry.get("english", ""))),
                    "origin": nfc(str(entry.get("origin", ""))),
                    "story": nfc(str(entry.get("story", ""))),
                    "example": nfc(str(entry.get("example", ""))),
                    "auto_english": "",
                    "auto_origin": "",
                    "auto_story": "",
                    "auto_example": "",
                }
                rows.append(row)
    return rows


def export_tsv(rows: Iterable[dict], path: Path) -> None:
    if not rows:
        raise ValueError("No rows to export.")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            normalized = {column: nfc(str(row.get(column, ""))) for column in COLUMNS}
            writer.writerow(normalized)


def load_tsv(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError("TSV missing header row.")
        missing = [column for column in COLUMNS if column not in reader.fieldnames]
        if missing:
            raise ValueError(f"TSV missing required columns: {', '.join(missing)}")
        rows: List[dict] = []
        for row in reader:
            cleaned = {key: nfc(row.get(key, "")) for key in reader.fieldnames}
            rows.append(cleaned)
        return rows


def suggest_rows(rows: Iterable[dict], gloss_map: Dict[str, str], ety_map: Dict[str, str], templates: Dict[str, dict]) -> List[dict]:
    suggested: List[dict] = []
    for row in rows:
        updated = dict(row)
        word_key = row.get("word", "").strip()
        lower_key = word_key.casefold()
        english = row.get("english", "").strip()
        if english in ("", "TODO"):
            auto_english = gloss_map.get(word_key) or gloss_map.get(lower_key)
            if auto_english:
                updated["auto_english"] = nfc(auto_english)
        origin = row.get("origin", "").strip()
        if origin in ("", "TODO"):
            auto_origin = ety_map.get(word_key) or ety_map.get(lower_key)
            if auto_origin:
                updated["auto_origin"] = nfc(auto_origin)
        story = row.get("story", "").strip()
        if story in ("", "TODO"):
            origin_hint = updated.get("auto_origin") or row.get("origin", "").strip()
            auto_story = build_auto_story(
                word=row.get("word", ""),
                pos=row.get("pos", ""),
                level=row.get("level", ""),
                origin_text=origin_hint,
            )
            if auto_story:
                updated["auto_story"] = auto_story
        example = row.get("example", "").strip()
        if example in ("", "TODO"):
            auto_example = build_auto_example(
                word=row.get("word", ""),
                pos=row.get("pos", ""),
                level=row.get("level", ""),
                templates=templates,
            )
            if auto_example:
                updated["auto_example"] = auto_example
        suggested.append(updated)
    return suggested


def build_auto_story(word: str, pos: str, level: str, origin_text: str) -> str:
    if not word:
        return ""
    descriptor = STORY_POS_DESCRIPTORS.get(pos.lower(), "una palabra útil")
    sentences: List[str] = []
    sentences.append(f"Es {descriptor} en el nivel {level or 'A1'}.")
    origin_text = origin_text.strip()
    if origin_text:
        sentences.append(f"Se relaciona con su origen: {origin_text}")
    else:
        sentences.append("Se usa como referencia clara y segura en el aula.")
    story = " ".join(sentences)
    story = nfc(story)
    if len(story) > 280:
        story = story[:279].rstrip() + "…"
    return story


def build_auto_example(word: str, pos: str, level: str, templates: Dict[str, dict]) -> str:
    word = word.strip()
    if not word:
        return ""
    level_key = level.upper() if level else "A1"
    template_group = templates.get(level_key) or templates.get("A1", {})
    pos_key = pos.lower() if pos else "phrase"
    template = template_group.get(pos_key) or template_group.get("phrase") or "{word}."
    det_value = ""
    if pos_key == "noun":
        det_value = pick_article(word, templates.get("articles", {}))
    example = template.format(word=word, det=det_value)
    example = example.replace("\r\n", "\n").replace("\r", "\n")
    return nfc(example)


def pick_article(word: str, articles: Dict[str, str]) -> str:
    clean = word.strip()
    if not clean or " " in clean or "-" in clean:
        return ""
    if not clean:
        return ""
    first = clean[0].lower()
    vowels = set("aeiouáéíóúü")
    default_article = articles.get("default", "un ")
    vowel_article = articles.get("vowel_hint", default_article)
    return vowel_article if first in vowels else default_article


def merge_apply(rows: List[dict], write: bool) -> Tuple[int, int]:
    if not rows:
        print("No rows supplied; nothing to apply.")
        return (0, 0)
    update_map: Dict[Path, List[dict]] = defaultdict(list)
    for row in rows:
        file_value = row.get("file", "").strip()
        if not file_value:
            continue
        update_map[Path(file_value)].append(row)

    missing_refs: List[str] = []
    parsed_files: Dict[Path, List[dict]] = {}
    for file_path, file_rows in update_map.items():
        if not file_path.exists():
            missing_refs.append(f"Missing file: {file_path}")
            continue
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse JSON {file_path}: {exc}") from exc
        for row in file_rows:
            index_str = row.get("index", "0").strip()
            try:
                idx = int(index_str)
            except ValueError:
                missing_refs.append(f"Invalid index '{index_str}' for {file_path}")
                continue
            if idx < 0 or idx >= len(data):
                missing_refs.append(f"Index {idx} out of range for {file_path}")
        parsed_files[file_path] = data
    if missing_refs:
        print("Apply aborted due to missing references:")
        for line in missing_refs:
            print(f"  - {line}")
        raise SystemExit(1)

    total_updated = 0
    total_skipped = 0
    backups_dir = Path("backups")
    backups_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    for file_path, file_rows in update_map.items():
        data = parsed_files[file_path]
        changed = False
        for row in file_rows:
            index_str = row.get("index", "0").strip()
            try:
                idx = int(index_str)
            except ValueError:
                total_skipped += 1
                continue
            entry = data[idx]
            if not enforce_identity(entry, row):
                print(f"Warning: identity mismatch for {file_path} index {idx}; skipping row.")
                total_skipped += 1
                continue
            updated_here = False
            for field in ("english", "origin", "story", "example"):
                cell = row.get(field, "")
                cell = nfc(cell.strip())
                if not cell or cell == "TODO":
                    continue
                clean_value = cell.replace("\r\n", "\n").replace("\r", "\n")
                existing = nfc(str(entry.get(field, "")))
                if existing == clean_value:
                    continue
                if existing != "TODO" and not cell:
                    continue
                entry[field] = clean_value
                updated_here = True
            if updated_here:
                enforce_length_checks(entry)
                changed = True
                total_updated += 1
            else:
                total_skipped += 1
        if changed and write:
            backup_path = backups_dir / f"{timestamp}__{file_path.name}"
            shutil.copyfile(file_path, backup_path)
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as temp_handle:
                json.dump(data, temp_handle, ensure_ascii=False, indent=2)
                temp_handle.write("\n")
                temp_name = temp_handle.name
            os.replace(temp_name, file_path)
    if not write:
        print("--write flag not supplied; no changes written.")
    return total_updated, total_skipped


def enforce_identity(entry: dict, row: dict) -> bool:
    for field in ("word", "pos", "gender", "level"):
        entry_value = nfc(str(entry.get(field, ""))).strip()
        row_value = nfc(str(row.get(field, ""))).strip()
        if row_value and entry_value != row_value:
            return False
    return True


def enforce_length_checks(entry: dict) -> None:
    story = str(entry.get("story", ""))
    if story and len(story) > 600:
        print(f"Warning: story for '{entry.get('word')}' exceeds 600 chars ({len(story)}).")
    example = str(entry.get("example", ""))
    if example:
        level = str(entry.get("level", "")).upper()
        limit = EXAMPLE_LIMITS.get(level, 280)
        if len(example) > limit:
            print(
                f"Warning: example for '{entry.get('word')}' exceeds limit {limit} ({len(example)})."
            )


def run_validator() -> int:
    command = [
        sys.executable,
        "tools/validate.py",
        "--scan-dir",
        "vocab/out",
        "--require-alpha",
        "--out-report",
        "reports/verify.json",
        "--out-summary",
        "reports/verify.txt",
        "--fail-on",
        "ERROR",
    ]
    result = subprocess.run(command, check=False)
    return result.returncode


def handle_pick(args: argparse.Namespace) -> None:
    batches = load_batches(args.level)
    rows = collect_todos(batches, args.limit)
    if not rows:
        print("No TODO entries found for selection.")
        return
    output_path = Path(args.out)
    export_tsv(rows, output_path)
    print(f"Exported {len(rows)} rows to {output_path}")


def handle_suggest(args: argparse.Namespace) -> None:
    rows = load_tsv(Path(args.input))
    gloss_map = load_json_map(Path("curator/config/gloss_map.json"))
    ety_map = load_json_map(Path("curator/config/etymology_map.json"))
    templates = load_json_structure(Path("curator/config/example_templates.json"))
    suggested_rows = suggest_rows(rows, gloss_map, ety_map, templates)
    export_tsv(suggested_rows, Path(args.output))
    print(f"Autosuggestions saved to {args.output}")


def handle_apply(args: argparse.Namespace) -> None:
    rows = load_tsv(Path(args.input))
    updated, skipped = merge_apply(rows, args.write)
    print(f"Updated entries: {updated}; Skipped rows: {skipped}")
    if args.write and updated:
        code = run_validator()
        if code != 0:
            raise SystemExit(code)
        print("Validation complete. Check reports/verify.txt")


def handle_resume(args: argparse.Namespace) -> None:
    batches = load_batches(args.level)
    rows = collect_todos(batches, args.limit)
    if not rows:
        print("No TODO entries found for selection.")
        return
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    base_name = f"{args.level}_set_{timestamp}"
    pick_path = Path("curator/sheets") / f"{base_name}.tsv"
    suggest_path = Path("curator/sheets") / f"{base_name}_suggested.tsv"
    export_tsv(rows, pick_path)
    gloss_map = load_json_map(Path("curator/config/gloss_map.json"))
    ety_map = load_json_map(Path("curator/config/etymology_map.json"))
    templates = load_json_structure(Path("curator/config/example_templates.json"))
    suggested_rows = suggest_rows(rows, gloss_map, ety_map, templates)
    export_tsv(suggested_rows, suggest_path)
    print(f"Resume export complete: {pick_path}")
    print(f"Suggestions ready: {suggest_path}")


def load_json_map(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    normalized = {}
    for key, value in data.items():
        normalized[nfc(str(key))] = nfc(str(value))
    return normalized


def load_json_structure(path: Path):
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return normalize_structure(data)


def normalize_structure(value):
    if isinstance(value, str):
        return nfc(value)
    if isinstance(value, dict):
        return {nfc(str(k)): normalize_structure(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize_structure(v) for v in value]
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Batch curator tool with guardrails")
    subparsers = parser.add_subparsers(dest="command")

    pick_parser = subparsers.add_parser("pick", help="Select TODO entries and export a TSV")
    pick_parser.add_argument("--level", required=True, help="CEFR level to scan")
    pick_parser.add_argument("--limit", type=int, default=50, help="Maximum number of entries")
    pick_parser.add_argument("--out", required=True, help="Output TSV path")
    pick_parser.set_defaults(func=handle_pick)

    suggest_parser = subparsers.add_parser("suggest", help="Fill auto suggestion columns")
    suggest_parser.add_argument("--in", dest="input", required=True, help="Input TSV path")
    suggest_parser.add_argument("--out", dest="output", required=True, help="Output TSV path")
    suggest_parser.set_defaults(func=handle_suggest)

    apply_parser = subparsers.add_parser("apply", help="Apply curated data back into JSON")
    apply_parser.add_argument("--in", dest="input", required=True, help="Final TSV path")
    apply_parser.add_argument("--write", action="store_true", help="Persist changes to JSON files")
    apply_parser.set_defaults(func=handle_apply)

    resume_parser = subparsers.add_parser("resume", help="Pick and suggest in one step")
    resume_parser.add_argument("--level", required=True, help="CEFR level to scan")
    resume_parser.add_argument("--limit", type=int, default=50, help="Maximum number of entries")
    resume_parser.set_defaults(func=handle_resume)

    return parser


def main(argv: List[str] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
