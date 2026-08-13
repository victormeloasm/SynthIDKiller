#!/usr/bin/env python3
"""Generate photographic/raster controls for forensic comparison."""

from pathlib import Path
import argparse
import numpy as np
from PIL import Image


def save(a,path):
    Image.fromarray(np.clip(np.rint(a*255),0,255).astype(np.uint8)).save(path)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",default="photo_controls")
    ap.add_argument("--width",type=int,default=2048)
    ap.add_argument("--height",type=int,default=1117)
    ap.add_argument("--seed",type=int,default=1337)
    args=ap.parse_args()
    out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
    w,h=args.width,args.height; rng=np.random.default_rng(args.seed)
    yy,xx=np.indices((h,w))
    X=xx/max(w-1,1); Y=yy/max(h-1,1)

    grad=np.stack([X,0.25+0.65*Y,0.15+0.55*(1-X)],axis=-1)
    save(grad,out/"gradient_rgb.png")

    gaussian=np.clip(grad+rng.normal(0,1/255,size=grad.shape),0,1)
    save(gaussian,out/"gradient_rgb_gaussian_sigma1.png")

    periodic=grad.copy()
    p=(1.4*np.sin(2*np.pi*xx/16)+0.8*np.sin(2*np.pi*yy/8))/255
    periodic=np.clip(periodic+p[...,None],0,1)
    save(periodic,out/"gradient_rgb_periodic_16x8.png")

    # Correlated channel residual.
    common=rng.normal(0,1/255,size=(h,w,1))
    corr=np.clip(grad+common*np.array([1.0,0.85,0.92])[None,None,:],0,1)
    save(corr,out/"gradient_rgb_correlated_noise.png")

    # Smooth bokeh-like control made from deterministic Gaussian blobs.
    base=np.zeros((h,w,3),dtype=np.float64)
    base[:]=np.array([0.10,0.22,0.08])
    for _ in range(40):
        cx=rng.uniform(0,w); cy=rng.uniform(0,h); sig=rng.uniform(30,180)
        amp=rng.uniform(0.03,0.22)
        col=np.array([rng.uniform(.5,1),rng.uniform(.65,1),rng.uniform(.35,.8)])
        blob=np.exp(-((xx-cx)**2+(yy-cy)**2)/(2*sig*sig))*amp
        base += blob[...,None]*col
    save(np.clip(base,0,1),out/"synthetic_bokeh_clean.png")
    save(np.clip(base+rng.normal(0,1/255,size=base.shape),0,1),out/"synthetic_bokeh_gaussian_sigma1.png")

    print(f"Controls written to {out}")

if __name__=="__main__":
    main()
