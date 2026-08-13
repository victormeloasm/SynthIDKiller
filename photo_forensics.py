#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import lzma
import math
import zlib
from pathlib import Path

import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter, maximum_filter
from skimage import color
from skimage.filters import sobel
from skimage.filters.rank import entropy as rank_entropy
from skimage.morphology import disk
try:
    import pywt
except Exception:
    pywt = None


def entropy_counts(counts):
    counts = np.asarray(counts, dtype=np.float64)
    counts = counts[counts > 0]
    if not len(counts):
        return 0.0
    p = counts / counts.sum()
    return float(-(p * np.log2(p)).sum())


def entropy_u8(x):
    return entropy_counts(np.bincount(np.asarray(x, dtype=np.uint8).ravel(), minlength=256))


def robust_norm(x, lo=5.0, hi=95.0):
    a, b = np.percentile(x, [lo, hi])
    if b <= a:
        return np.zeros_like(x, dtype=np.float64)
    return np.clip((x - a) / (b - a), 0.0, 1.0)


def robust_sigma(x):
    x = np.asarray(x, dtype=np.float64)
    med = np.median(x)
    return float(np.median(np.abs(x - med)) / 0.6744897501960817)


def local_variance(x, sigma=2.0):
    m = gaussian_filter(x, sigma=sigma, mode="reflect")
    m2 = gaussian_filter(x*x, sigma=sigma, mode="reflect")
    return np.maximum(0.0, m2 - m*m)


def make_texture_maps(luma):
    g = sobel(luma)
    lv = np.sqrt(local_variance(luma, sigma=2.0))
    # Multi-scale high-pass energy.
    hp1 = luma - gaussian_filter(luma, 1.0, mode="reflect")
    hp3 = luma - gaussian_filter(luma, 3.0, mode="reflect")
    e = np.sqrt(gaussian_filter(hp1*hp1, 1.5, mode="reflect")) + 0.5*np.sqrt(
        gaussian_filter(hp3*hp3, 2.5, mode="reflect")
    )
    gn = robust_norm(g)
    vn = robust_norm(lv)
    en = robust_norm(e)
    texture = np.clip(0.50*gn + 0.30*vn + 0.20*en, 0, 1)
    flat = np.clip(1.0 - texture, 0, 1)
    return g, lv, hp1, texture, flat


def save_map(data, path, title, cmap="viridis", symmetric=False):
    plt.figure(figsize=(11, 8))
    if symmetric:
        finite = np.asarray(data)[np.isfinite(data)]
        s = np.percentile(np.abs(finite), 99.5) if finite.size else 1.0
        s = max(float(s), 1e-12)
        plt.imshow(data, cmap=cmap, vmin=-s, vmax=s)
    else:
        plt.imshow(data, cmap=cmap)
    plt.colorbar()
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def compression_ratio(b, kind):
    if not b:
        return 0.0
    c = zlib.compress(b, 9) if kind == "zlib" else lzma.compress(b, preset=9)
    return len(c) / len(b)


def flat_patch_fft(residual, flat, patch=128, stride=64, min_flat=0.78):
    h, w = residual.shape
    if h < patch or w < patch:
        return None, None, [], 0
    win = np.outer(np.hanning(patch), np.hanning(patch))
    spectra, autocorrs, stats = [], [], []
    for y in range(0, h-patch+1, stride):
        for x in range(0, w-patch+1, stride):
            f = flat[y:y+patch, x:x+patch]
            score = float(np.mean(f))
            if score < min_flat:
                continue
            r = residual[y:y+patch, x:x+patch].astype(np.float64)
            r = r - np.mean(r)
            rms = float(np.sqrt(np.mean(r*r)))
            rr = r * win
            F = np.fft.fft2(rr)
            P = np.abs(F)**2
            total = float(P.sum())
            if total <= 0:
                continue
            P /= total
            spectra.append(np.fft.fftshift(P))
            ac = np.fft.fftshift(np.fft.ifft2(np.abs(F)**2).real)
            mx = float(np.max(np.abs(ac)))
            if mx:
                ac /= mx
            autocorrs.append(ac)
            stats.append((x, y, score, rms, float(np.std(r)), float(np.mean(np.abs(r)))))
    if not spectra:
        return None, None, [], 0
    return np.mean(spectra, axis=0), np.mean(autocorrs, axis=0), stats, len(spectra)


def spectral_entropy(power, dc_radius=3):
    if power is None:
        return float("nan")
    p = power.copy()
    h, w = p.shape
    cy, cx = h//2, w//2
    yy, xx = np.indices(p.shape)
    p[(xx-cx)**2+(yy-cy)**2 <= dc_radius**2] = 0
    p = p.ravel()
    p = p[p > 0]
    if not len(p):
        return 0.0
    p /= p.sum()
    return float(-(p*np.log2(p)).sum()/np.log2(len(p)))


def radial_profile(power):
    h, w = power.shape
    cy, cx = h//2, w//2
    yy, xx = np.indices(power.shape)
    r = np.hypot(xx-cx, yy-cy).astype(np.int32)
    s = np.bincount(r.ravel(), weights=power.ravel())
    n = np.bincount(r.ravel())
    return s/np.maximum(n,1)


def angular_profile(power, bins=180, min_radius=4):
    h,w=power.shape
    cy,cx=h//2,w//2
    yy,xx=np.indices(power.shape)
    dx,dy=xx-cx,yy-cy
    r=np.hypot(dx,dy)
    theta=(np.arctan2(dy,dx)+np.pi)%np.pi
    m=r>=min_radius
    ids=np.floor(theta[m]/np.pi*bins).astype(int)
    ids=np.clip(ids,0,bins-1)
    s=np.bincount(ids,weights=power[m],minlength=bins)
    n=np.bincount(ids,minlength=bins)
    deg=(np.arange(bins)+0.5)*180/bins
    return deg,s/np.maximum(n,1)


def fft_peaks(power, count=50, dc=4):
    if power is None:
        return []
    p=power.copy()
    h,w=p.shape
    cy,cx=h//2,w//2
    yy,xx=np.indices(p.shape)
    p[(xx-cx)**2+(yy-cy)**2<=dc**2]=0
    loc=p==maximum_filter(p,size=5,mode="nearest")
    coords=np.argwhere(loc); vals=p[loc]
    order=np.argsort(vals)[::-1]
    rows=[]
    for i in order[:count]:
        y,x=coords[i]
        dx,dy=int(x-cx),int(y-cy)
        rr=math.hypot(dx,dy)
        per=min(h,w)/rr if rr else float("inf")
        rows.append((dx,dy,float(vals[i]),float(per)))
    return rows


def shift_corr(residual, mask, max_lag=64):
    rows=[]
    for lag in range(1,max_lag+1):
        mh=(mask[:,:-lag] & mask[:,lag:])
        if mh.sum()>100:
            a=residual[:,:-lag][mh]; b=residual[:,lag:][mh]
            hc=float(np.corrcoef(a,b)[0,1]) if a.std() and b.std() else 0.0
        else:
            hc=float("nan")
        mv=(mask[:-lag,:] & mask[lag:,:])
        if mv.sum()>100:
            a=residual[:-lag,:][mv]; b=residual[lag:,:][mv]
            vc=float(np.corrcoef(a,b)[0,1]) if a.std() and b.std() else 0.0
        else:
            vc=float("nan")
        rows.append((lag,hc,vc))
    return rows


def wavelet_energy(x, level=4):
    if pywt is None:
        return []
    ml=pywt.dwtn_max_level(x.shape,"db2")
    level=max(1,min(level,ml))
    coeffs=pywt.wavedec2(x,"db2",level=level)
    energies=[]
    total=float(np.sum(coeffs[0]**2))
    for d in coeffs[1:]:
        total += sum(float(np.sum(c*c)) for c in d)
    ea=float(np.sum(coeffs[0]**2))
    energies.append(("A",level,ea,ea/max(total,1e-30)))
    for i,(ch,cv,cd) in enumerate(coeffs[1:],1):
        scale=level-i+1
        for name,c in [("H",ch),("V",cv),("D",cd)]:
            e=float(np.sum(c*c))
            energies.append((name,scale,e,e/max(total,1e-30)))
    return energies


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--output",default="photo_forensics")
    ap.add_argument("--patch",type=int,default=128)
    ap.add_argument("--stride",type=int,default=64)
    ap.add_argument("--flat-threshold",type=float,default=0.78)
    ap.add_argument("--max-lag",type=int,default=64)
    args=ap.parse_args()

    out=Path(args.output); out.mkdir(parents=True,exist_ok=True)

    rgb_u8=np.asarray(Image.open(args.image).convert("RGB"),dtype=np.uint8)
    rgb=rgb_u8.astype(np.float64)/255.0
    h,w,_=rgb.shape
    lab=color.rgb2lab(rgb)
    L=lab[...,0]/100.0

    grad,lv,hp,texture,flat=make_texture_maps(L)

    # Use the smoothest 20% for robust residual estimates.
    cutoff=np.percentile(flat,80)
    flat_mask=flat>=cutoff
    if flat_mask.sum()<1000:
        flat_mask=flat>=np.percentile(flat,70)

    hp_sigma=robust_sigma(hp[flat_mask])

    # LAB chroma residual estimates.
    a_hp=lab[...,1]-gaussian_filter(lab[...,1],1.0,mode="reflect")
    b_hp=lab[...,2]-gaussian_filter(lab[...,2],1.0,mode="reflect")
    a_sigma=robust_sigma(a_hp[flat_mask])
    b_sigma=robust_sigma(b_hp[flat_mask])

    power,ac,patch_stats,patch_count=flat_patch_fft(
        hp,flat,args.patch,args.stride,args.flat_threshold
    )
    if patch_count==0:
        power,ac,patch_stats,patch_count=flat_patch_fft(
            hp,flat,64,32,max(0.60,args.flat_threshold-0.15)
        )

    specH=spectral_entropy(power)
    shifts=shift_corr(hp,flat_mask,args.max_lag)
    wav=wavelet_energy(hp)

    # Entropies
    ent={}
    for c,name in enumerate(["R","G","B"]):
        ent[name]=entropy_u8(rgb_u8[...,c])
    luma_u8=np.clip(np.rint(L*255),0,255).astype(np.uint8)
    ent["Luma"]=entropy_u8(luma_u8)

    packed=(rgb_u8[...,0].astype(np.uint32)<<16)|(rgb_u8[...,1].astype(np.uint32)<<8)|rgb_u8[...,2].astype(np.uint32)
    _,counts=np.unique(packed,return_counts=True)
    joint=entropy_counts(counts)

    hpq=np.clip(np.rint((hp-hp.min())/max(hp.max()-hp.min(),1e-12)*255),0,255).astype(np.uint8)
    local_ent=rank_entropy(hpq,disk(5))

    hp_rgb=rgb-gaussian_filter(rgb,sigma=(1.0,1.0,0),mode="reflect")
    residual_corr=np.corrcoef(hp_rgb[flat_mask].reshape(-1,3).T)

    save_map(texture,out/"texture_probability.png","Texture / edge probability")
    save_map(flat,out/"flat_probability.png","Smooth-region probability")
    save_map(grad,out/"gradient_magnitude.png","Luminance gradient magnitude")
    save_map(lv,out/"local_variance.png","Local luminance standard deviation")
    save_map(hp,out/"highpass_residual.png","Luminance high-pass residual",cmap="seismic",symmetric=True)
    save_map(local_ent,out/"local_entropy.png","Local entropy of normalized high-pass residual")

    if power is not None:
        save_map(np.log1p(power/max(float(np.median(power)),1e-30)),out/"flat_patch_fft.png","Average normalized FFT of smooth patches",cmap="gray")
        save_map(ac,out/"flat_patch_autocorrelation.png","Average autocorrelation of smooth-patch residual",cmap="seismic",symmetric=True)

        rp=radial_profile(power)
        with open(out/"radial_power.csv","w",newline="") as fh:
            wr=csv.writer(fh); wr.writerow(["radius_bin","mean_power"]); wr.writerows(enumerate(rp))

        deg,ang=angular_profile(power)
        with open(out/"angular_power.csv","w",newline="") as fh:
            wr=csv.writer(fh); wr.writerow(["angle_deg","mean_power"]); wr.writerows(zip(deg,ang))
        plt.figure(figsize=(11,6)); plt.plot(deg,ang)
        plt.xlabel("Orientation (degrees)"); plt.ylabel("Mean power"); plt.title("Smooth-patch spectral anisotropy")
        plt.tight_layout(); plt.savefig(out/"angular_power.png",dpi=180); plt.close()

        pk=fft_peaks(power)
        with open(out/"spectral_peaks.csv","w",newline="") as fh:
            wr=csv.writer(fh); wr.writerow(["rank","dx","dy","power","approx_period_px"])
            for i,row in enumerate(pk,1): wr.writerow([i,*row])
    else:
        pk=[]

    with open(out/"shift_correlations.csv","w",newline="") as fh:
        wr=csv.writer(fh); wr.writerow(["lag_px","horizontal_corr","vertical_corr"]); wr.writerows(shifts)

    with open(out/"wavelet_energy.csv","w",newline="") as fh:
        wr=csv.writer(fh); wr.writerow(["band","scale","energy","energy_fraction"]); wr.writerows(wav)

    with open(out/"patch_statistics.csv","w",newline="") as fh:
        wr=csv.writer(fh); wr.writerow(["x","y","mean_flat_probability","residual_rms","residual_std","mean_abs_residual"])
        wr.writerows(patch_stats)

    metrics={
        "image":args.image,
        "width":w,"height":h,
        "distinct_rgb_colors":int(len(np.unique(rgb_u8.reshape(-1,3),axis=0))),
        "entropy_bits":ent,
        "joint_rgb_entropy_bits_per_pixel":joint,
        "flat_mask_fraction":float(flat_mask.mean()),
        "estimated_luma_highpass_sigma_0to1":hp_sigma,
        "estimated_lab_a_highpass_sigma":a_sigma,
        "estimated_lab_b_highpass_sigma":b_sigma,
        "normalized_spectral_entropy":specH,
        "accepted_flat_fft_patches":patch_count,
        "flat_residual_channel_correlation":residual_corr.tolist(),
        "rgb_zlib_ratio":compression_ratio(rgb_u8.tobytes(),"zlib"),
        "rgb_lzma_ratio":compression_ratio(rgb_u8.tobytes(),"lzma"),
        "mean_texture_probability":float(texture.mean()),
        "mean_flat_probability":float(flat.mean()),
    }
    with open(out/"metrics.json","w") as fh:
        json.dump(metrics,fh,indent=2)

    with open(out/"report.txt","w") as fh:
        fh.write("FROG PHOTO FORENSICS REPORT\n"+"="*72+"\n\n")
        fh.write(f"Image: {args.image}\nResolution: {w} x {h}\n")
        fh.write(f"Distinct RGB colors: {metrics['distinct_rgb_colors']:,}\n\n")
        fh.write("ENTROPY\n"+"-"*72+"\n")
        for k,v in ent.items(): fh.write(f"{k}: {v:.8f} bits/sample\n")
        fh.write(f"Joint RGB: {joint:.8f} bits/pixel\n\n")
        fh.write("ROBUST SMOOTH-REGION RESIDUAL ESTIMATES\n"+"-"*72+"\n")
        fh.write(f"Luma high-pass sigma [0..1]: {hp_sigma:.10f}\n")
        fh.write(f"LAB a* high-pass sigma: {a_sigma:.8f}\n")
        fh.write(f"LAB b* high-pass sigma: {b_sigma:.8f}\n")
        fh.write(f"Smoothest-mask fraction: {flat_mask.mean():.4%}\n")
        fh.write(f"Accepted FFT patches: {patch_count}\n")
        fh.write(f"Normalized spectral entropy: {specH:.8f}\n\n")
        fh.write("FLAT-REGION RGB HIGH-PASS CORRELATION\n"+"-"*72+"\n")
        fh.write(np.array2string(residual_corr,precision=8))
        fh.write("\n\nTOP FFT CANDIDATES\n"+"-"*72+"\n")
        for i,(dx,dy,pwr,per) in enumerate(pk[:20],1):
            fh.write(f"{i:02d}: dx={dx:+4d} dy={dy:+4d} period~{per:.4f}px power={pwr:.10e}\n")
        fh.write("\nInterpretation warning: strong peaks are generic spectral candidates, not source/provenance identification.\n")

    print(f"Done: {out}")
    print(f"Resolution: {w}x{h}")
    print(f"Estimated smooth-region luma high-pass sigma: {hp_sigma:.6f}")
    print(f"Accepted flat FFT patches: {patch_count}")
    print(f"Spectral entropy: {specH:.6f}")


if __name__=="__main__":
    main()
