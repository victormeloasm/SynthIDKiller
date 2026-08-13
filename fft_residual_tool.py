#!/usr/bin/env python3
"""
FFT residual analyzer / manual restoration test.

Important: the original black/white spiral is itself a powerful frequency pattern.
This script therefore subtracts an inferred binary model first and works on the residual.

It will NOT automatically delete detected peaks. Peak discovery and filtering are deliberately
separate operations because a strong FFT peak is not automatically an artifact.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from scipy.ndimage import distance_transform_edt, maximum_filter
from skimage.filters import threshold_otsu


def parse_notch(s):
    p=[float(x) for x in s.split(",")]
    if len(p)!=4:
        raise argparse.ArgumentTypeError("notch = dx,dy,radius,strength")
    dx,dy,radius,strength=p
    if radius<=0 or not 0<=strength<=1:
        raise argparse.ArgumentTypeError("radius>0 and 0<=strength<=1")
    return dx,dy,radius,strength


def luma(rgb):
    f=rgb.astype(np.float64)
    return .2126*f[...,0]+.7152*f[...,1]+.0722*f[...,2]


def edge_mask(binary,margin):
    b=binary>127
    e=np.zeros_like(b)
    e[:,1:] |= b[:,1:] != b[:,:-1]
    e[:,:-1] |= b[:,1:] != b[:,:-1]
    e[1:,:] |= b[1:,:] != b[:-1,:]
    e[:-1,:] |= b[1:,:] != b[:-1,:]
    d=distance_transform_edt(~e)
    return d>=margin


def spectrum(x):
    x=x.astype(np.float64)-np.mean(x)
    win=np.outer(np.hanning(x.shape[0]),np.hanning(x.shape[1]))
    F=np.fft.fftshift(np.fft.fft2(x*win))
    return F,np.abs(F)**2


def peaks(power,count=80,dc=6):
    h,w=power.shape; cy,cx=h//2,w//2
    yy,xx=np.indices(power.shape)
    p=power.copy()
    p[(xx-cx)**2+(yy-cy)**2<=dc**2]=0
    loc=p==maximum_filter(p,size=5,mode="nearest")
    co=np.argwhere(loc); va=p[loc]; order=np.argsort(va)[::-1]
    out=[]
    for i in order[:count]:
        y,x=co[i]; dx,dy=int(x-cx),int(y-cy); r=math.hypot(dx,dy)
        per=min(h,w)/r if r else float("inf")
        out.append((dx,dy,float(va[i]),float(per)))
    return out


def notch_mask(shape,notches):
    h,w=shape; cy,cx=h//2,w//2
    yy,xx=np.indices(shape); m=np.ones(shape,dtype=np.float64)
    expanded=[]
    seen=set()
    for dx,dy,r,s in notches:
        for item in [(dx,dy,r,s),(-dx,-dy,r,s)]:
            key=tuple(round(v,6) for v in item)
            if key not in seen:
                seen.add(key); expanded.append(item)
    for dx,dy,r,s in expanded:
        d2=(xx-(cx+dx))**2+(yy-(cy+dy))**2
        reject=np.exp(-d2/(2*r*r))
        m *= 1.0-s*reject
    return np.clip(m,0,1),expanded


def save_fft(power,path,title):
    d=np.log1p(power/max(float(np.median(power)),1e-30))
    plt.figure(figsize=(11,8)); plt.imshow(d,cmap="gray"); plt.colorbar(); plt.title(title)
    plt.tight_layout(); plt.savefig(path,dpi=180); plt.close()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--output",default="fft_residual")
    ap.add_argument("--notch",type=parse_notch,action="append",default=[])
    ap.add_argument("--edge-margin",type=float,default=3.0)
    ap.add_argument("--gain",type=float,default=20.0)
    args=ap.parse_args()

    out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
    rgb=np.asarray(Image.open(args.image).convert("RGB"),dtype=np.uint8)
    y=luma(rgb)
    t=float(threshold_otsu(np.clip(np.rint(y),0,255).astype(np.uint8)))
    ideal=np.where(y>t,255.0,0.0)
    residual=y-ideal
    flat=edge_mask(ideal,args.edge_margin)

    # For the global transform, suppress edge-near residual so the intended spiral boundary is not
    # interpreted as an artifact. The resulting FFT is a residual diagnostic, not an FFT of the image.
    r=residual.copy()
    mean=float(r[flat].mean()) if flat.any() else 0.0
    r[~flat]=mean
    F,power=spectrum(r)
    save_fft(power,out/"residual_fft_before.png","Edge-safe binary residual FFT")

    pk=peaks(power)
    with open(out/"residual_spectral_candidates.csv","w",newline="") as fh:
        wr=csv.writer(fh); wr.writerow(["rank","dx","dy","power","approx_period_px"])
        for i,row in enumerate(pk,1): wr.writerow([i,*row])

    Image.fromarray(np.clip(128+r*4,0,255).astype(np.uint8),mode="L").save(out/"edge_safe_residual_x4.png")

    if not args.notch:
        print(f"Scan done: {out}")
        print("No notches applied. Inspect residual_spectral_candidates.csv and residual_fft_before.png.")
        return

    mask,expanded=notch_mask(r.shape,args.notch)
    Fr=np.fft.fftshift(np.fft.fft2(r-r.mean()))
    filtered=np.fft.ifft2(np.fft.ifftshift(Fr*mask)).real+r.mean()
    removed=r-filtered

    # Apply the filtered residual only as a pre-threshold reconstruction, then project back to exact
    # black/white. This avoids leaving periodic grayscale behind in the final 2-color output.
    reconstructed=ideal+filtered
    final=np.where(reconstructed>t,255,0).astype(np.uint8)

    Image.fromarray(final,mode="L").convert("RGB").save(out/"restored_binary_rgb.png")
    Image.fromarray(final,mode="L").convert("1",dither=Image.Dither.NONE).save(out/"restored_1bit.png")
    Image.fromarray(np.clip(128+removed*args.gain,0,255).astype(np.uint8),mode="L").save(out/"removed_residual_component_x20.png")

    plt.figure(figsize=(11,8)); plt.imshow(mask,cmap="gray",vmin=0,vmax=1); plt.colorbar()
    plt.title("Manual residual FFT notch mask"); plt.tight_layout(); plt.savefig(out/"notch_mask.png",dpi=180); plt.close()

    _,after=spectrum(filtered)
    save_fft(after,out/"residual_fft_after.png","Residual FFT after manual notch test")

    with open(out/"notches_used.txt","w") as fh:
        for item in expanded: fh.write(repr(item)+"\n")

    print(f"Filtered test done: {out}")
    print("Inspect removed_residual_component_x20.png before trusting the restoration.")


if __name__=="__main__":
    main()
