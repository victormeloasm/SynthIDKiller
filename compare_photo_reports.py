#!/usr/bin/env python3
import argparse, csv, json
from pathlib import Path

def flatten(prefix,obj,out):
    if isinstance(obj,dict):
        for k,v in obj.items():
            flatten(f"{prefix}{k}.",v,out)
    elif isinstance(obj,(list,tuple)):
        out[prefix[:-1]]=json.dumps(obj)
    else:
        out[prefix[:-1]]=obj

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("reports",nargs="+")
    ap.add_argument("--output",default="photo_comparison.csv")
    args=ap.parse_args()

    rows=[]
    fields=[]
    for p in args.reports:
        d=json.loads(Path(p).read_text())
        row={"source":p}
        flatten("",d,row)
        rows.append(row)
        for k in row:
            if k not in fields: fields.append(k)

    with open(args.output,"w",newline="") as fh:
        wr=csv.DictWriter(fh,fieldnames=fields)
        wr.writeheader(); wr.writerows(rows)

    print(f"Wrote {args.output}")

if __name__=="__main__":
    main()
