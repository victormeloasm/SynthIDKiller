#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
import matplotlib.pyplot as plt

from scipy.ndimage import gaussian_filter
from skimage import color
from skimage.filters import sobel, unsharp_mask
from skimage.restoration import (
    denoise_wavelet,
    denoise_nl_means,
    denoise_tv_chambolle,
    denoise_bilateral,
)
from skimage.metrics import structural_similarity as ssim


PRESETS={
    "conservative":{"strength":0.45,"texture_protection":0.88,"detail_recovery":0.10,"chroma_strength":0.55},
    "balanced":{"strength":0.62,"texture_protection":0.82,"detail_recovery":0.16,"chroma_strength":0.72},
    "aggressive":{"strength":0.78,"texture_protection":0.72,"detail_recovery":0.20,"chroma_strength":0.85},
}


def robust_norm(x,lo=5,hi=95):
    a,b=np.percentile(x,[lo,hi])
    if b<=a:
        return np.zeros_like(x)
    return np.clip((x-a)/(b-a),0,1)


def local_variance(x,sigma=2):
    m=gaussian_filter(x,sigma,mode="reflect")
    m2=gaussian_filter(x*x,sigma,mode="reflect")
    return np.maximum(0,m2-m*m)


def texture_map(L):
    g=sobel(L)
    lv=np.sqrt(local_variance(L,2.0))
    hp1=L-gaussian_filter(L,1.0,mode="reflect")
    hp3=L-gaussian_filter(L,3.0,mode="reflect")
    energy=np.sqrt(gaussian_filter(hp1*hp1,1.5,mode="reflect"))+0.5*np.sqrt(gaussian_filter(hp3*hp3,2.5,mode="reflect"))
    t=np.clip(0.50*robust_norm(g)+0.30*robust_norm(lv)+0.20*robust_norm(energy),0,1)
    # Small blur avoids visible blend boundaries.
    t=gaussian_filter(t,1.2,mode="reflect")
    return np.clip(t,0,1),g,lv


def save_gray_map(a,path,title):
    plt.figure(figsize=(11,8))
    plt.imshow(a,cmap="gray",vmin=0,vmax=1)
    plt.colorbar(); plt.title(title); plt.tight_layout(); plt.savefig(path,dpi=180); plt.close()


def save_removed(original,restored,path,gain=8):
    d=original.astype(np.float64)-restored.astype(np.float64)
    vis=np.clip(128+d*gain,0,255).astype(np.uint8)
    Image.fromarray(vis).save(path)


def gradient_retention(before,after):
    b=color.rgb2gray(before)
    a=color.rgb2gray(after)
    gb=sobel(b); ga=sobel(a)
    ratio=ga/np.maximum(gb,1e-5)
    return np.clip(ratio,0,2)/2.0


def lab_denoisers(rgb, fast=False, chroma_strength=0.72):
    lab=color.rgb2lab(rgb)
    L=lab[...,0]/100.0
    a=(lab[...,1]+128.0)/255.0
    b=(lab[...,2]+128.0)/255.0

    # Robust high-pass MAD noise estimate. This does not require PyWavelets.
    hp_est = L - gaussian_filter(L, 1.0, mode="reflect")
    med = float(np.median(hp_est))
    sigma_L = float(np.median(np.abs(hp_est - med)) / 0.6744897501960817)
    sigma_L=max(sigma_L,0.0025)

    # Wavelet candidate. If PyWavelets is unavailable despite requirements.txt,
    # fall back to a very mild Gaussian estimate so the toolkit still runs.
    try:
        L_wave=denoise_wavelet(
            L,
            sigma=sigma_L,
            method="BayesShrink",
            mode="soft",
            wavelet_levels=4,
            rescale_sigma=True,
            channel_axis=None,
        )
    except Exception:
        L_wave=gaussian_filter(L,0.55,mode="reflect")

    # NLM candidate.
    patch_distance=5 if fast else 7
    h_nlm=max(0.55*sigma_L,0.003)
    L_nlm=denoise_nl_means(
        L,
        h=h_nlm,
        sigma=sigma_L,
        fast_mode=True,
        patch_size=5,
        patch_distance=patch_distance,
        channel_axis=None,
        preserve_range=True,
    )

    # TV candidate.
    tv_weight=np.clip(1.5*sigma_L,0.006,0.035)
    L_tv=denoise_tv_chambolle(L,weight=tv_weight,channel_axis=None)

    # Bilateral candidate.
    sigma_color=np.clip(1.4*sigma_L,0.01,0.08)
    L_bilat=denoise_bilateral(
        L,
        sigma_color=sigma_color,
        sigma_spatial=2.0,
        bins=10000,
        mode="reflect",
        channel_axis=None,
    )

    # Chroma denoise: wavelet + mild NLM-like smooth blend via Gaussian.
    try:
        a_wave=denoise_wavelet(a,method="BayesShrink",mode="soft",rescale_sigma=True,channel_axis=None)
        b_wave=denoise_wavelet(b,method="BayesShrink",mode="soft",rescale_sigma=True,channel_axis=None)
    except Exception:
        a_wave=gaussian_filter(a,0.55,mode="reflect")
        b_wave=gaussian_filter(b,0.55,mode="reflect")
    a_smooth=gaussian_filter(a_wave,0.8,mode="reflect")
    b_smooth=gaussian_filter(b_wave,0.8,mode="reflect")
    a_final=(1-chroma_strength)*a + chroma_strength*a_smooth
    b_final=(1-chroma_strength)*b + chroma_strength*b_smooth

    def rebuild(Lc):
        lab2=np.empty_like(lab)
        lab2[...,0]=np.clip(Lc,0,1)*100.0
        lab2[...,1]=np.clip(a_final,0,1)*255.0-128.0
        lab2[...,2]=np.clip(b_final,0,1)*255.0-128.0
        return np.clip(color.lab2rgb(lab2),0,1)

    return {
        "wavelet":rebuild(L_wave),
        "nlm":rebuild(L_nlm),
        "tv":rebuild(L_tv),
        "bilateral":rebuild(L_bilat),
    },sigma_L


def ensemble(candidates):
    # Balanced robust average: wavelet and NLM dominate; bilateral/TV are supporting candidates.
    return np.clip(
        0.34*candidates["wavelet"]+
        0.34*candidates["nlm"]+
        0.20*candidates["bilateral"]+
        0.12*candidates["tv"],
        0,1
    )


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--output",default="frog_restore")
    ap.add_argument("--preset",choices=list(PRESETS),default="balanced")
    ap.add_argument("--strength",type=float)
    ap.add_argument("--texture-protection",type=float)
    ap.add_argument("--detail-recovery",type=float)
    ap.add_argument("--chroma-strength",type=float)
    ap.add_argument("--fast",action="store_true")
    args=ap.parse_args()

    cfg=dict(PRESETS[args.preset])
    for name in ["strength","texture_protection","detail_recovery","chroma_strength"]:
        v=getattr(args,name)
        if v is not None:
            cfg[name]=v

    out=Path(args.output); out.mkdir(parents=True,exist_ok=True)

    original_u8=np.asarray(Image.open(args.image).convert("RGB"),dtype=np.uint8)
    rgb=original_u8.astype(np.float64)/255.0
    L=color.rgb2lab(rgb)[...,0]/100.0
    texture,grad,lv=texture_map(L)

    candidates,sigma_L=lab_denoisers(rgb,args.fast,cfg["chroma_strength"])
    den=ensemble(candidates)

    # Continuous texture protection.
    # texture_protection close to 1 -> textured regions drop cleanup rapidly.
    exponent=1.0+5.0*cfg["texture_protection"]
    cleanup=(1.0-np.clip(texture,0,1))**exponent
    cleanup=gaussian_filter(cleanup,1.0,mode="reflect")

    # Limit global strength.
    cleanup=np.clip(cleanup*cfg["strength"],0,1)

    # Residual guard rail:
    # if the ensemble difference aligns strongly with real gradient energy, suppress local cleanup.
    removed0=rgb-den
    rem_luma=color.rgb2gray(np.clip(removed0+0.5,0,1))-0.5
    rem_energy=np.sqrt(gaussian_filter(rem_luma*rem_luma,1.2,mode="reflect"))
    edge_n=robust_norm(grad,10,98)
    rem_n=robust_norm(rem_energy,10,98)
    semantic_risk=np.clip(edge_n*rem_n,0,1)
    cleanup *= (1.0-0.80*semantic_risk)
    cleanup=gaussian_filter(cleanup,0.8,mode="reflect")
    cleanup=np.clip(cleanup,0,1)

    restored=rgb*(1-cleanup[...,None])+den*cleanup[...,None]

    # Mild detail recovery:
    # re-inject a fraction of ORIGINAL fine detail only where cleanup was actually applied.
    # This prevents "detail recovery" from modifying textured regions that were already protected.
    if cfg["detail_recovery"]>0:
        original_base=gaussian_filter(rgb,sigma=(0.7,0.7,0),mode="reflect")
        original_detail=rgb-original_base
        recover=np.clip(cleanup*texture*cfg["detail_recovery"],0,0.18)
        restored=restored+original_detail*recover[...,None]

    restored=np.clip(restored,0,1)
    restored_u8=np.clip(np.rint(restored*255),0,255).astype(np.uint8)

    # Save candidates.
    for name,img in candidates.items():
        Image.fromarray(np.clip(np.rint(img*255),0,255).astype(np.uint8)).save(out/f"candidate_{name}.png")

    final_name=f"restored_{args.preset}.png"
    Image.fromarray(restored_u8).save(out/final_name)
    save_gray_map(texture,out/"texture_mask.png","Texture / edge protection")
    save_gray_map(cleanup,out/"cleanup_weight.png","Applied restoration weight")

    retain=gradient_retention(rgb,restored)
    save_gray_map(retain,out/"detail_retention.png","Local gradient retention (display-normalized)")
    save_removed(original_u8,restored_u8,out/"removed_component_x8.png",gain=8)

    diff=(original_u8.astype(np.float64)-restored_u8.astype(np.float64))
    diff_float=(rgb-restored)*255.0
    rms=float(np.sqrt(np.mean(diff*diff)))
    mae=float(np.mean(np.abs(diff)))
    similarity=float(ssim(original_u8,restored_u8,channel_axis=2,data_range=255))

    # Smooth vs textured change statistics. Use the floating-point restoration delta so
    # sub-level changes in protected texture are still measurable even when PNG quantization
    # rounds them back to the same 8-bit value.
    smooth=texture<np.percentile(texture,30)
    textured=texture>np.percentile(texture,75)
    pixdiff=np.sqrt(np.mean(diff_float*diff_float,axis=2))
    smooth_change=float(np.mean(pixdiff[smooth])) if smooth.any() else 0.0
    texture_change=float(np.mean(pixdiff[textured])) if textured.any() else 0.0

    metrics={
        "image":args.image,
        "preset":args.preset,
        "config":cfg,
        "estimated_luma_sigma":sigma_L,
        "rms_pixel_change":rms,
        "mean_absolute_pixel_change":mae,
        "ssim_vs_original":similarity,
        "mean_cleanup_weight":float(cleanup.mean()),
        "p95_cleanup_weight":float(np.percentile(cleanup,95)),
        "mean_change_smooth_regions":smooth_change,
        "mean_change_textured_regions":texture_change,
        "smooth_to_texture_change_ratio":smooth_change/max(texture_change,1e-12),
        "mean_texture_probability":float(texture.mean()),
    }
    with open(out/"metrics.json","w") as fh:
        json.dump(metrics,fh,indent=2)

    with open(out/"report.txt","w") as fh:
        fh.write("FROG PHOTO RESTORATION REPORT\n"+"="*72+"\n\n")
        fh.write(f"Image: {args.image}\nPreset: {args.preset}\n")
        fh.write(f"Config: {cfg}\n")
        fh.write(f"Estimated luminance sigma: {sigma_L:.8f}\n")
        fh.write(f"RMS pixel change: {rms:.6f}\n")
        fh.write(f"MAE pixel change: {mae:.6f}\n")
        fh.write(f"SSIM vs original: {similarity:.8f}\n")
        fh.write(f"Mean cleanup weight: {cleanup.mean():.6f}\n")
        fh.write(f"P95 cleanup weight: {np.percentile(cleanup,95):.6f}\n")
        fh.write(f"Mean change in smooth regions: {smooth_change:.6f}\n")
        fh.write(f"Mean change in textured regions: {texture_change:.6f}\n")
        fh.write(f"Smooth/textured change ratio: {smooth_change/max(texture_change,1e-12):.6f}\n\n")
        fh.write("Interpretation:\n")
        fh.write("- Larger smooth/textured change ratio means the algorithm preferentially cleaned smoother areas.\n")
        fh.write("- High SSIM alone does not guarantee good restoration; inspect removed_component_x8.png.\n")
        fh.write("- If recognizable subject detail appears in the removed component, use a more conservative preset.\n")

    print(f"Done: {out}")
    print(f"Final: {out/final_name}")
    print(f"SSIM vs original: {similarity:.6f}")
    print(f"Smooth/textured change ratio: {smooth_change/max(texture_change,1e-12):.3f}")


if __name__=="__main__":
    main()
