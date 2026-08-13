#!/usr/bin/env python3
"""
Binary image restoration for images intended to contain only black and white.

Produces exact 2-color candidates plus an optional edge-antialiased version.
No FFT notch is needed for the exact binary reconstruction: after a class decision, every pixel
is projected exactly onto 0 or 255.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
import matplotlib.pyplot as plt

from scipy.ndimage import distance_transform_edt, median_filter
from skimage.filters import threshold_otsu, threshold_li, threshold_yen
from skimage.restoration import denoise_tv_chambolle


def luma(rgb):
    f = rgb.astype(np.float64)
    return 0.2126*f[...,0] + 0.7152*f[...,1] + 0.0722*f[...,2]


def threshold_mask(y, t):
    return y > t


def save_binary(mask, rgb_path, bit1_path):
    a = np.where(mask, 255, 0).astype(np.uint8)
    Image.fromarray(a, mode="L").convert("RGB").save(rgb_path)
    # Literal one-bit PNG.
    Image.fromarray(a, mode="L").convert("1", dither=Image.Dither.NONE).save(bit1_path)


def signed_distance_aa(mask, width=0.85):
    """
    Signed-distance antialiasing.
    Interior pixels remain exactly black/white; only a narrow boundary band becomes gray.
    """
    inside = distance_transform_edt(mask)
    outside = distance_transform_edt(~mask)
    sdf = inside - outside
    coverage = np.clip(0.5 + sdf / max(width*2.0, 1e-9), 0.0, 1.0)
    return np.rint(coverage * 255.0).astype(np.uint8)


def difference_visual(original_luma, binary_luma, gain=2.0):
    d = original_luma - binary_luma
    return np.clip(128 + d*gain, 0, 255).astype(np.uint8)


def ambiguity_map(y, threshold, width=32.0):
    # bright = near decision boundary; dark = confidently black/white
    d = np.abs(y - threshold)
    a = 1.0 - np.clip(d / width, 0, 1)
    return np.rint(a*255).astype(np.uint8)


def candidate(name, y, threshold, out, aa_width, original_y):
    mask = threshold_mask(y, threshold)
    save_binary(mask, out/f"{name}_binary_rgb.png", out/f"{name}_1bit.png")
    aa = signed_distance_aa(mask, aa_width)
    Image.fromarray(aa, mode="L").save(out/f"{name}_sdf_aa.png")
    b = np.where(mask,255.0,0.0)
    Image.fromarray(difference_visual(original_y,b),mode="L").save(out/f"{name}_difference_x2.png")
    return {
        "name": name,
        "threshold": float(threshold),
        "white_fraction": float(mask.mean()),
        "black_fraction": float((~mask).mean()),
        "mean_abs_projection_change": float(np.mean(np.abs(original_y-b))),
        "p95_abs_projection_change": float(np.percentile(np.abs(original_y-b),95)),
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--output", default="binary_restore")
    ap.add_argument("--mode", choices=["all","otsu","fixed","tv"], default="all")
    ap.add_argument("--fixed-threshold", type=float, default=127.5)
    ap.add_argument("--aa-width", type=float, default=0.85)
    ap.add_argument("--tv-weight", type=float, default=0.035,
                    help="TV denoise weight in normalized 0..1 units; conservative default")
    ap.add_argument("--median-size", type=int, default=0,
                    help="Optional median prefilter size; 0 disables. Use cautiously on thin stripes.")
    args=ap.parse_args()

    out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
    rgb=np.asarray(Image.open(args.image).convert("RGB"),dtype=np.uint8)
    y=luma(rgb)

    if args.median_size and args.median_size > 1:
        y_work=median_filter(y,size=args.median_size,mode="reflect")
    else:
        y_work=y.copy()

    thresholds={
        "fixed127": float(args.fixed_threshold),
        "otsu": float(threshold_otsu(np.clip(np.rint(y_work),0,255).astype(np.uint8))),
        "li": float(threshold_li(y_work)),
        "yen": float(threshold_yen(np.clip(np.rint(y_work),0,255).astype(np.uint8))),
    }

    # TV version is intentionally conservative; it can help broad gray blobs but should never be the
    # only candidate on a high-frequency stripe image.
    tv = denoise_tv_chambolle(y_work/255.0, weight=args.tv_weight, channel_axis=None) * 255.0
    tv_t=float(threshold_otsu(np.clip(np.rint(tv),0,255).astype(np.uint8)))

    results=[]
    if args.mode in ("all","fixed"):
        results.append(candidate("fixed127",y_work,thresholds["fixed127"],out,args.aa_width,y))
    if args.mode in ("all","otsu"):
        results.append(candidate("otsu",y_work,thresholds["otsu"],out,args.aa_width,y))
    if args.mode=="all":
        results.append(candidate("li",y_work,thresholds["li"],out,args.aa_width,y))
        results.append(candidate("yen",y_work,thresholds["yen"],out,args.aa_width,y))
    if args.mode in ("all","tv"):
        results.append(candidate("tv_otsu",tv,tv_t,out,args.aa_width,y))

    Image.fromarray(ambiguity_map(y,thresholds["otsu"]),mode="L").save(out/"otsu_ambiguity_map.png")

    # Threshold comparison figure
    plt.figure(figsize=(11,6))
    plt.hist(y.ravel(),bins=256)
    for name,t in thresholds.items():
        plt.axvline(t,label=f"{name}: {t:.2f}")
    plt.axvline(tv_t,label=f"tv_otsu: {tv_t:.2f}",linestyle="--")
    plt.legend(); plt.xlabel("Luminance"); plt.ylabel("Pixels"); plt.title("Threshold candidates")
    plt.tight_layout(); plt.savefig(out/"thresholds.png",dpi=180); plt.close()

    with open(out/"restore_metrics.json","w") as fh:
        json.dump({
            "image": args.image,
            "width": int(rgb.shape[1]),
            "height": int(rgb.shape[0]),
            "thresholds": thresholds,
            "tv_otsu_threshold": tv_t,
            "tv_weight": args.tv_weight,
            "candidates": results,
        },fh,indent=2)

    with open(out/"README_RESULT.txt","w") as fh:
        fh.write("Inspect otsu_binary_rgb.png and fixed127_binary_rgb.png first.\n")
        fh.write("They contain only exact 0/255 pixels.\n")
        fh.write("Use *_sdf_aa.png if visually smooth edges matter more than literal 2-color pixels.\n")
        fh.write("TV can damage the finest stripes; treat tv_otsu as an alternate candidate, not ground truth.\n")

    print(f"Done: {out}")
    print("Thresholds:", thresholds, "tv_otsu=",tv_t)


if __name__=="__main__":
    main()
