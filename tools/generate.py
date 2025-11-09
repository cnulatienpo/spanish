#!/usr/bin/env python3
# Generates batched vocab entries with TODO placeholders for curation.
# Targets (comment): A1:600 A2:1000 B1:1400 B2:1400 C1:900 C2:700  => 6000

import argparse, json, os, sys, unicodedata, csv

COMMON_POS = {
  # tiny lemma hints; everything else defaults to noun
  "ser":"verb","estar":"verb","tener":"verb","hacer":"verb","poder":"verb",
  "decir":"verb","ir":"verb","ver":"verb","dar":"verb","saber":"verb",
  "querer":"verb","llegar":"verb","pasar":"verb","poner":"verb","parecer":"verb",
  "tiempo":"noun","año":"noun","día":"noun","vida":"noun","gente":"noun","mano":"noun",
}

def load_pos_map(path):
    m = {}
    if not path: return m
    with open(path, newline='', encoding="utf-8") as f:
        for row in csv.DictReader(f):
            w = row["word"].strip()
            m[w.lower()] = (row.get("pos",""), row.get("gender",""))
    return m

def infer_pos(word, override):
    w = word.lower()
    if w in override and override[w][0]:
        return override[w][0]
    return COMMON_POS.get(w, "noun")

def infer_gender(pos, word, override):
    w = word.lower()
    if w in override and override[w][1]:
        return override[w][1]
    if pos == "noun":
        return "invariable"
    return "n/a"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", required=True, choices=["A1","A2","B1","B2","C1","C2"])
    ap.add_argument("--in", dest="inp", required=True, help="headwords .txt (one per line)")
    ap.add_argument("--out", required=True, help="output JSON array file")
    ap.add_argument("--batch-size", type=int, default=200)
    ap.add_argument("--pos-map", default=None, help="CSV word,pos,gender overrides")
    args = ap.parse_args()
    if args.batch_size <= 0 or args.batch_size > 250:
        print("--batch-size must be 1..250", file=sys.stderr); sys.exit(2)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    overrides = load_pos_map(args.pos_map)

    words=[]
    with open(args.inp, encoding="utf-8") as f:
        for line in f:
            w = unicodedata.normalize("NFC", line.strip())
            if not w: continue
            words.append(w)

    entries=[]
    for w in sorted(words, key=lambda s: s.lower()):
        pos = infer_pos(w, overrides)
        gender = infer_gender(pos, w, overrides)
        entries.append({
            "word": w,
            "pos": pos,
            "gender": gender,
            "english": "TODO",
            "origin": "TODO",
            "story": "TODO",
            "example": "TODO",
            "level": args.level,
            "_note": "needs curation"
        })

    if len(entries) > args.batch_size:
        print(f"WARNING: batch has {len(entries)} items (> {args.batch_size}). Consider split_batches.py", file=sys.stderr)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    from collections import Counter
    c = Counter(e["pos"] for e in entries)
    print(f"Generated {len(entries)} entries for {args.level}. POS counts: {dict(c)}")

if __name__ == "__main__":
    main()
