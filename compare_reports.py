#!/usr/bin/env python3
"""
Compare metrics.json files produced by pattern_lab.py.
"""

import argparse
import csv
import json
from pathlib import Path


FIELDS = [
    "width","height","distinct_rgb_colors","otsu_threshold",
    "exact_black_fraction","exact_white_fraction","non_binary_fraction",
    "exact_grayscale_fraction","chroma_spread_mean","nearest_binary_distance_mean",
    "nearest_binary_distance_p90","nearest_binary_distance_p99",
    "joint_rgb_entropy_bits_per_pixel","residual_entropy_bits_per_symbol",
    "horizontal_neighbor_conditional_entropy","horizontal_neighbor_MI",
    "vertical_neighbor_conditional_entropy","vertical_neighbor_MI",
    "normalized_spectral_entropy","accepted_fft_patches",
    "fft_patch_used","fft_min_flat_used","fft_fallback_global",
    "raw_rgb_zlib_ratio","raw_rgb_lzma_ratio","residual_zlib_ratio","residual_lzma_ratio",
]


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("metrics",nargs="+",help="metrics.json files")
    ap.add_argument("--output",default="comparison.csv")
    args=ap.parse_args()

    rows=[]
    for path in args.metrics:
        d=json.loads(Path(path).read_text())
        row={"source":path,"image":d.get("image","")}
        for k in FIELDS:
            row[k]=d.get(k,"")
        for ch,val in d.get("channel_entropies_bits",{}).items():
            row[f"entropy_{ch}"]=val
        for k,val in d.get("glcm",{}).items():
            row[f"glcm_{k}"]=val
        rows.append(row)

    keys=[]
    for row in rows:
        for k in row:
            if k not in keys:
                keys.append(k)

    with open(args.output,"w",newline="") as fh:
        wr=csv.DictWriter(fh,fieldnames=keys)
        wr.writeheader(); wr.writerows(rows)

    print(f"Wrote {args.output}")


if __name__=="__main__":
    main()
