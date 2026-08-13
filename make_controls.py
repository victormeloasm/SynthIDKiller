#!/usr/bin/env python3
"""
Generate mathematical controls for pattern/entropy experiments.

These images contain no AI-generation pipeline. They are useful as negative/positive controls when
interpreting FFT peaks, entropy, periodicity and compressibility.
"""

from pathlib import Path
import argparse
import numpy as np
from PIL import Image


def save_gray(a, path):
    Image.fromarray(np.clip(np.rint(a),0,255).astype(np.uint8), mode="L").save(path)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",default="controls")
    ap.add_argument("--width",type=int,default=2048)
    ap.add_argument("--height",type=int,default=1117)
    ap.add_argument("--seed",type=int,default=1337)
    args=ap.parse_args()

    out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
    w,h=args.width,args.height
    yy,xx=np.indices((h,w))
    rng=np.random.default_rng(args.seed)

    # Pure binary split.
    split=np.where(xx < w//2,0,255)
    save_gray(split,out/"control_binary_split.png")

    # Pure binary checkerboard.
    checker=((xx//16 + yy//16)&1)*255
    save_gray(checker,out/"control_checker_16.png")

    # Smooth 8-bit gradient.
    grad=xx/(w-1)*255.0
    save_gray(grad,out/"control_gradient.png")

    # Gradient + independent Gaussian raster noise.
    noisy=grad+rng.normal(0,1.0,size=(h,w))
    save_gray(noisy,out/"control_gradient_gaussian_sigma1.png")

    # Gradient + explicitly periodic raster contamination.
    periodic=grad + 1.25*np.sin(2*np.pi*xx/16.0) + 0.75*np.sin(2*np.pi*yy/8.0)
    save_gray(periodic,out/"control_gradient_periodic_16x8.png")

    # Binary concentric chirp / optical control.
    cx,cy=w*.58,h*.48
    r=np.hypot(xx-cx,yy-cy)
    phase=0.0055*r*r + 0.065*r
    rings=np.where(np.sin(phase)>=0,255,0)
    save_gray(rings,out/"control_binary_radial_chirp.png")

    # A binary spiral-like phase field.
    theta=np.arctan2(yy-cy,xx-cx)
    phase2=0.055*r + 4.0*theta + 0.000035*r*r
    spiral=np.where(np.sin(phase2)>=0,255,0)
    save_gray(spiral,out/"control_binary_spiral.png")

    print(f"Controls written to {out}")


if __name__=="__main__":
    main()
