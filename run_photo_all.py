#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path

def run(cmd):
    print("\n+", " ".join(str(x) for x in cmd))
    subprocess.run(cmd,check=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--output",default="frog_photo_results")
    ap.add_argument("--preset",choices=["conservative","balanced","aggressive"],default="balanced")
    ap.add_argument("--fast",action="store_true")
    args=ap.parse_args()

    out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
    here=Path(__file__).resolve().parent
    py=sys.executable

    run([py,str(here/"photo_forensics.py"),args.image,"--output",str(out/"analysis")])

    cmd=[py,str(here/"frog_restore.py"),args.image,"--output",str(out/"restore"),"--preset",args.preset]
    if args.fast:
        cmd.append("--fast")
    run(cmd)

    print("\nAll done.")
    print("Inspect:")
    print(out/"restore"/f"restored_{args.preset}.png")
    print(out/"restore"/"removed_component_x8.png")
    print(out/"restore"/"texture_mask.png")
    print(out/"restore"/"cleanup_weight.png")
    print(out/"analysis"/"report.txt")
    print(out/"analysis"/"flat_patch_fft.png")

if __name__=="__main__":
    main()
