#!/usr/bin/env python3
import argparse, json, os, math


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--batch-size", type=int, default=200)
    args = ap.parse_args()
    data = json.load(open(args.inp, encoding="utf-8"))
    os.makedirs(args.out_dir, exist_ok=True)
    n = len(data); k = 1
    for i in range(0, n, args.batch_size):
        chunk = data[i:i+args.batch_size]
        path = os.path.join(args.out_dir, f"batch_{k:03}.json")
        json.dump(chunk, open(path,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
        k += 1
    print(f"Wrote {k-1} files to {args.out_dir}")


if __name__ == "__main__":
    main()
