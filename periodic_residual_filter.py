#!/usr/bin/env python3
"""
Manual narrow-band periodic artifact test for photographs.

The script intentionally does NOT auto-delete detected FFT peaks.
You explicitly provide notch locations after forensic inspection.

Filtering is performed on a high-pass luminance residual and blended mostly into smooth regions,
while high-texture/edge regions are protected.
"""

from __future__ import annotations
import argparse, csv, math
from pathlib import Path
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter, maximum_filter
from skimage import color
from skimage.filters import sobel


def parse_notch(s):
    vals=[float(x) for x in s.split(",")]
    if len(vals)!=4:
        raise argparse.ArgumentTypeError("notch must be dx,dy,radius,strength")
    dx,dy,radius,strength=vals
    if radius<=0 or not 0<=strength<=1:
        raise argparse.ArgumentTypeError("radius > 0 and strength in [0,1]")
    return dx,dy,radius,strength


def robust_norm(x):
    a,b=np.percentile(x,[5,95])
    return np.clip((x-a)/max(b-a,1e-12),0,1)


def texture_map(L):
    grad=sobel(L)
    hp=L-gaussian_filter(L,1.0,mode="reflect")
    energy=np.sqrt(gaussian_filter(hp*hp,2.0,mode="reflect"))
    return np.clip(0.65*robust_norm(grad)+0.35*robust_norm(energy),0,1)


def notch_mask(shape, notches):
    h,w=shape; cy,cx=h//2,w//2
    yy,xx=np.indices(shape)
    m=np.ones(shape,dtype=np.float64)
    expanded=[]; seen=set()
    for dx,dy,r,s in notches:
        for item in [(dx,dy,r,s),(-dx,-dy,r,s)]:
            key=tuple(round(v,6) for v in item)
            if key in seen: continue
            seen.add(key); expanded.append(item)
    for dx,dy,r,s in expanded:
        d2=(xx-(cx+dx))**2+(yy-(cy+dy))**2
        reject=np.exp(-d2/(2*r*r))
        m *= 1-s*reject
    return np.clip(m,0,1),expanded


def peaks(power,count=60,dc=8):
    p=power.copy(); h,w=p.shape; cy,cx=h//2,w//2
    yy,xx=np.indices(p.shape)
    p[(xx-cx)**2+(yy-cy)**2<=dc**2]=0
    loc=p==maximum_filter(p,size=5,mode="nearest")
    coords=np.argwhere(loc); vals=p[loc]; order=np.argsort(vals)[::-1]
    rows=[]
    for i in order[:count]:
        y,x=coords[i]; dx,dy=int(x-cx),int(y-cy)
        r=math.hypot(dx,dy); period=min(h,w)/r if r else float("inf")
        rows.append((dx,dy,float(vals[i]),float(period)))
    return rows


def save_map(a,path,title,cmap="gray"):
    plt.figure(figsize=(11,8)); plt.imshow(a,cmap=cmap); plt.colorbar(); plt.title(title)
    plt.tight_layout(); plt.savefig(path,dpi=180); plt.close()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--output",default="periodic_cleanup")
    ap.add_argument("--baseline-sigma",type=float,default=6.0)
    ap.add_argument("--notch",type=parse_notch,action="append",default=[])
    ap.add_argument("--max-blend",type=float,default=0.65)
    args=ap.parse_args()

    out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
    u8=np.asarray(Image.open(args.image).convert("RGB"),dtype=np.uint8)
    rgb=u8.astype(np.float64)/255
    lab=color.rgb2lab(rgb); L=lab[...,0]/100
    tex=texture_map(L); smooth=(1-tex)**4
    smooth=gaussian_filter(smooth,1.0,mode="reflect")

    base=gaussian_filter(L,args.baseline_sigma,mode="reflect")
    residual=L-base

    # Scan a windowed smooth-weighted residual.
    work=residual*smooth
    win=np.outer(np.hanning(L.shape[0]),np.hanning(L.shape[1]))
    F=np.fft.fftshift(np.fft.fft2((work-work.mean())*win))
    power=np.abs(F)**2
    pk=peaks(power)
    with open(out/"spectral_candidates.csv","w",newline="") as fh:
        wr=csv.writer(fh); wr.writerow(["rank","dx","dy","power","approx_period_px"])
        for i,row in enumerate(pk,1): wr.writerow([i,*row])
    save_map(np.log1p(power/max(float(np.median(power)),1e-30)),out/"smooth_residual_fft.png","Smooth-weighted residual FFT")
    save_map(smooth,out/"smooth_blend_mask.png","Smooth-region blend mask")

    if not args.notch:
        Image.fromarray(np.clip(128+residual*255*8,0,255).astype(np.uint8)).save(out/"highpass_residual_x8.png")
        print(f"Analysis done: {out}")
        print("No notch applied. Inspect spectral_candidates.csv first.")
        return

    mask,expanded=notch_mask(L.shape,args.notch)
    Fr=np.fft.fftshift(np.fft.fft2(residual-residual.mean()))
    filtered=np.fft.ifft2(np.fft.ifftshift(Fr*mask)).real+residual.mean()
    removed=residual-filtered

    # Reconstruct only luminance, and only where smooth-mask allows it.
    filtered_L=base+filtered
    blend=np.clip(smooth*args.max_blend,0,1)
    newL=L*(1-blend)+filtered_L*blend

    lab2=lab.copy(); lab2[...,0]=np.clip(newL,0,1)*100
    restored=np.clip(color.lab2rgb(lab2),0,1)
    out_u8=np.clip(np.rint(restored*255),0,255).astype(np.uint8)

    Image.fromarray(out_u8).save(out/"restored_manual_periodic.png")
    Image.fromarray(np.clip(128+removed*255*20,0,255).astype(np.uint8)).save(out/"removed_periodic_component_x20.png")
    save_map(mask,out/"notch_mask.png","Manual FFT notch mask")
    with open(out/"notches_used.txt","w") as fh:
        for n in expanded: fh.write(repr(n)+"\n")
    print(f"Filtered test written to {out}")
    print("Inspect removed_periodic_component_x20.png before trusting the result.")


if __name__=="__main__":
    main()
