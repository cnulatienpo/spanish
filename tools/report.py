#!/usr/bin/env python3
import argparse, json, os, glob
from collections import Counter


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--summary", required=True)
    args = ap.parse_args()
    levels=Counter(); pos=Counter(); todos=0; total=0
    for p in glob.glob(os.path.join(args.scan_dir,"**","*.json"), recursive=True):
        arr = json.load(open(p,encoding="utf-8"))
        for e in arr:
            total+=1
            levels[e.get("level","??")] += 1
            pos[e.get("pos","??")] += 1
            if any(e.get(k)=="TODO" for k in ("english","origin","story","example")):
                todos += 1
    rep = {"total":total,"by_level":levels,"by_pos":pos,"todo_fields":todos,"todo_pct": (todos/total*100 if total else 0)}
    json.dump(rep, open(args.out,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    with open(args.summary,"w",encoding="utf-8") as f:
        f.write(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__=="__main__":
    main()
