#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path

def run(cmd):
    print("\n+", " ".join(str(x) for x in cmd))
    subprocess.run(cmd, check=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--output",default="pattern_lab_results")
    args=ap.parse_args()

    root=Path(args.output)
    root.mkdir(parents=True,exist_ok=True)
    py=sys.executable
    here=Path(__file__).resolve().parent

    run([py, str(here/"pattern_lab.py"), args.image, "--output", str(root/"analysis")])
    run([py, str(here/"binary_restore.py"), args.image, "--output", str(root/"restore"), "--mode", "all"])
    run([py, str(here/"fft_residual_tool.py"), args.image, "--output", str(root/"fft_residual")])

    print("\nAll done.")
    print("Start by inspecting:")
    print(root/"analysis/report.txt")
    print(root/"restore/otsu_binary_rgb.png")
    print(root/"restore/fixed127_binary_rgb.png")
    print(root/"restore/otsu_sdf_aa.png")
    print(root/"fft_residual/residual_spectral_candidates.csv")

if __name__=="__main__":
    main()
