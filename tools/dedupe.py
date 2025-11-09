#!/usr/bin/env python3
import argparse, json, os, glob
from collections import defaultdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--conflicts", required=True)
    args = ap.parse_args()
    seen = defaultdict(list); files=[]
    for p in glob.glob(os.path.join(args.scan_dir,"**","*.json"), recursive=True):
        arr = json.load(open(p,encoding="utf-8"))
        for i,obj in enumerate(arr):
            seen[obj.get("word","").lower()].append((p,i,obj))
        files.append((p,arr))
    exact=[]; conflict=[]; keep={}
    for w, rows in seen.items():
        if len(rows) == 1:
            keep[w]=rows[0][2]; continue
        payloads = {json.dumps(r[2], ensure_ascii=False, sort_keys=True) for r in rows}
        if len(payloads)==1:
            exact.append(w); keep[w]=rows[0][2]
        else:
            conflict.append({"word":rows[0][2].get("word",""),"instances":[{"file":p,"idx":i} for p,i,_ in rows]})
            keep[w]=rows[0][2]
    json.dump(list(keep.values()), open(args.out,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump({"exact_duplicates":exact,"conflicts":conflict}, open(args.conflicts,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"deduped:{len(keep)} exact:{len(exact)} conflicts:{len(conflict)}")
    import sys
    sys.exit(1 if conflict else 0)


if __name__=="__main__":
    main()
