#!/usr/bin/env python3
import argparse, json, os, sys, glob, unicodedata
from jsonschema import validate, Draft202012Validator

ALLOWED_POS = {"noun","verb","adjective","adverb","pronoun","preposition","conjunction","interjection","phrase","expression","determiner","auxiliary","particle"}
ALLOWED_GENDER = {"masculine","feminine","invariable","n/a"}
ALLOWED_LEVEL = {"A1","A2","B1","B2","C1","C2"}

ULTRA_COMMON = set(map(str.lower, """
ser estar tener hacer poder decir ir ver dar saber querer llegar pasar poner parecer quedar creer hablar llevar dejar seguir encontrar llamar tiempo año día cosa hombre mujer vida mano parte niño ojo persona
""".split()))

def load_schema():
    with open("schemas/vocabulary.schema.json", encoding="utf-8") as f:
        return json.load(f)

def iter_files(args):
    if args.inp:
        yield args.inp
        return
    for path in glob.glob(os.path.join(args.scan_dir, "**", "*.json"), recursive=True):
        yield path

def norm(s): return unicodedata.normalize("NFC", s)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", help="single JSON array file")
    ap.add_argument("--scan-dir", help="scan *.json under directory")
    ap.add_argument("--out-report", default=None)
    ap.add_argument("--out-summary", default=None)
    ap.add_argument("--require-alpha", action="store_true")
    ap.add_argument("--fail-on", choices=["ERROR","WARN"], default="ERROR")
    args = ap.parse_args()
    if not args.inp and not args.scan_dir:
        print("Provide --in or --scan-dir", file=sys.stderr); sys.exit(2)

    schema = load_schema()
    v = Draft202012Validator(schema)
    errors=[]; warns=[]
    all_items=[]; locations=[]  # (word,i,path)

    def add_err(idx, word, code, msg, path):
        errors.append({"index":idx,"word":word,"code":code,"message":msg,"file":path})
    def add_warn(idx, word, code, msg, path):
        warns.append({"index":idx,"word":word,"code":code,"message":msg,"file":path})

    for path in iter_files(args):
        try:
            data = json.load(open(path, encoding="utf-8"))
        except Exception as e:
            add_err(-1, "", "FILE_NOT_JSON", str(e), path); continue
        if not isinstance(data, list):
            add_err(-1, "", "TOP_NOT_ARRAY", "Top-level must be array", path); continue
        last_key=None
        for i, obj in enumerate(data):
            if not isinstance(obj, dict):
                add_err(i, "", "NOT_OBJECT", "Entry must be object", path); continue
            # schema validation
            for ve in sorted(v.iter_errors(obj), key=lambda e: e.path):
                add_err(i, obj.get("word",""), "SCHEMA", ve.message, path)
            # type/shape sanity
            for k in ["word","pos","gender","english","origin","story","example","level"]:
                if k in obj and not isinstance(obj[k], str):
                    add_err(i, obj.get("word",""), "TYPE", f"Field {k} must be string", path)
                if k in obj and isinstance(obj[k], str) and not obj[k].strip():
                    add_err(i, obj.get("word",""), "EMPTY", f"Field {k} empty", path)
            w = obj.get("word","")
            lword = w.lower()
            # ordering
            key = lword
            if args.require_alpha:
                if last_key is not None and key < last_key:
                    add_err(i, w, "ORDER", "Not sorted by lower(word)", path)
                last_key=key
            # pos/gender
            pos = obj.get("pos","")
            gender = obj.get("gender","")
            if pos not in ALLOWED_POS:
                add_err(i, w, "POS", f"Invalid pos {pos}", path)
            if gender not in ALLOWED_GENDER:
                add_err(i, w, "GENDER", f"Invalid gender {gender}", path)
            if pos != "noun" and gender != "n/a":
                add_warn(i, w, "GENDER_WARN", "Non-nouns should use gender n/a", path)
            if pos == "noun" and gender == "n/a":
                add_warn(i, w, "GENDER_WARN", "Noun with gender n/a", path)
            # level
            level = obj.get("level","")
            if level not in ALLOWED_LEVEL:
                add_err(i, w, "LEVEL", f"Invalid level {level}", path)
            # TODO flags
            for k in ("english","origin","story","example"):
                if obj.get(k) == "TODO":
                    add_warn(i, w, "TODO", f"{k} needs curation", path)
            # word style
            if w != w.strip():
                add_warn(i, w, "SPACES", "Leading/trailing spaces in word", path)
            if any(ch.isupper() for ch in w):
                add_warn(i, w, "CASE", "Uppercase in headword", path)
            # CEFR sanity
            if lword in ULTRA_COMMON and level in {"C1","C2"}:
                add_warn(i, w, "CEFR_OVER", f"Ultra-common marked {level}", path)
            if level in {"A1","A2"} and len(w) > 12:
                add_warn(i, w, "CEFR_UNDER", f"Long/possibly rare at {level}", path)
            all_items.append((lword, json.dumps(obj, ensure_ascii=False, sort_keys=True)))
            locations.append((w, i, path))

    # duplicates across all files
    from collections import defaultdict
    by_word=defaultdict(list)
    for idx,(lword,payload) in enumerate(all_items):
        by_word[lword].append((idx,payload))
    for lword, rows in by_word.items():
        if len(rows) > 1:
            payloads = set(p for _,p in rows)
            word, i, pth = locations[rows[0][0]]
            if len(payloads) == 1:
                warns.append({"index":i,"word":word,"code":"DUP_EXACT","message":"Exact duplicate entries","file":pth})
            else:
                errors.append({"index":i,"word":word,"code":"DUP_CONFLICT","message":"Conflicting duplicates","file":pth})

    # reports
    summary = []
    summary.append(f"Errors: {len(errors)}  Warnings: {len(warns)}")
    def fmt(rows):
        out=[]
        for r in rows[:500]:
            out.append(f"- [{r.get('file')}] idx={r.get('index')} word={r.get('word')} code={r.get('code')} :: {r.get('message')}")
        return "\n".join(out)
    if args.out_summary:
        os.makedirs(os.path.dirname(args.out_summary), exist_ok=True)
        with open(args.out_summary, "w", encoding="utf-8") as f:
            f.write("\n".join(summary)+ "\n\n## ERRORS\n"+fmt(errors)+ "\n\n## WARNINGS\n"+fmt(warns)+"\n")
    if args.out_report:
        os.makedirs(os.path.dirname(args.out_report), exist_ok=True)
        with open(args.out_report, "w", encoding="utf-8") as f:
            json.dump({"errors":errors,"warnings":warns}, f, ensure_ascii=False, indent=2)

    fail_on_warn = (args.fail_on == "WARN")
    exit_code = 0
    if errors or (fail_on_warn and warns):
        exit_code = 1
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
