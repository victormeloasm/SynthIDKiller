#!/usr/bin/env python3
"""
Comprehensive pattern / entropy / residual forensic analyzer.

For binary-looking images, the script estimates an intended black/white model and analyzes the
deviation from that model. Edge pixels are treated separately so normal antialiasing / boundary
geometry does not dominate flat-region statistics.

This is analysis only: it does not identify or target provenance/watermark systems.
"""

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

from scipy.ndimage import (
    distance_transform_edt,
    gaussian_filter,
    maximum_filter,
)
from skimage.filters import threshold_otsu
from skimage.filters.rank import entropy as rank_entropy
from skimage.morphology import disk
from skimage.feature import graycomatrix, graycoprops

try:
    import pywt
except Exception:
    pywt = None


def entropy_counts(counts):
    counts = np.asarray(counts, dtype=np.float64)
    counts = counts[counts > 0]
    if counts.size == 0:
        return 0.0
    p = counts / counts.sum()
    return float(-(p * np.log2(p)).sum())


def entropy_u8(x):
    return entropy_counts(np.bincount(np.asarray(x, dtype=np.uint8).ravel(), minlength=256))


def compression_ratio(data: bytes, kind="zlib"):
    if not data:
        return 0.0
    if kind == "zlib":
        comp = zlib.compress(data, level=9)
    else:
        comp = lzma.compress(data, preset=9)
    return len(comp) / len(data)


def save_heatmap(data, path, title, cmap="viridis", symmetric=False):
    a = np.asarray(data)
    plt.figure(figsize=(11, 8))
    if symmetric:
        finite = a[np.isfinite(a)]
        s = np.percentile(np.abs(finite), 99.5) if finite.size else 1.0
        s = max(float(s), 1e-12)
        plt.imshow(a, cmap=cmap, vmin=-s, vmax=s)
    else:
        plt.imshow(a, cmap=cmap)
    plt.colorbar()
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def binary_model(luma, threshold):
    return np.where(luma > threshold, 255.0, 0.0)


def edge_safe_mask(binary, edge_margin):
    b = binary > 127
    edge = np.zeros_like(b, dtype=bool)
    edge[:, 1:] |= b[:, 1:] != b[:, :-1]
    edge[:, :-1] |= b[:, 1:] != b[:, :-1]
    edge[1:, :] |= b[1:, :] != b[:-1, :]
    edge[:-1, :] |= b[1:, :] != b[:-1, :]
    distance = distance_transform_edt(~edge)
    return distance >= edge_margin, distance, edge


def quantize_residual(residual, step=1.0, clip=127.0):
    q = np.rint(np.clip(residual, -clip, clip) / step).astype(np.int32)
    values, inverse = np.unique(q, return_inverse=True)
    return q, values, inverse.reshape(q.shape)


def conditional_neighbor_entropy(symbol_map, valid, horizontal=True):
    if horizontal:
        a, b = symbol_map[:, :-1], symbol_map[:, 1:]
        m = valid[:, :-1] & valid[:, 1:]
    else:
        a, b = symbol_map[:-1, :], symbol_map[1:, :]
        m = valid[:-1, :] & valid[1:, :]
    a = a[m].astype(np.int64)
    b = b[m].astype(np.int64)
    if len(a) == 0:
        return 0.0, 0.0, 0.0
    ns = max(int(a.max()), int(b.max())) + 1
    ha = entropy_counts(np.bincount(a, minlength=ns))
    hb = entropy_counts(np.bincount(b, minlength=ns))
    pair = a * ns + b
    hab = entropy_counts(np.bincount(pair))
    hbgivena = hab - ha
    mi = max(0.0, hb - hbgivena)
    return hb, hbgivena, mi


def discrete_mi(a, b):
    a = np.asarray(a, dtype=np.int64)
    b = np.asarray(b, dtype=np.int64)
    if len(a) == 0:
        return 0.0
    _, a = np.unique(a, return_inverse=True)
    _, b = np.unique(b, return_inverse=True)
    nb = int(b.max()) + 1
    ha = entropy_counts(np.bincount(a))
    hb = entropy_counts(np.bincount(b))
    joint = a * nb + b
    hj = entropy_counts(np.bincount(joint))
    return max(0.0, ha + hb - hj)


def phase_mi_scan(symbol_map, valid, periods, sample_max, shuffles, seed=1337):
    rng = np.random.default_rng(seed)
    yy, xx = np.indices(symbol_map.shape)
    ys, xs = np.nonzero(valid)
    symbols = symbol_map[valid].astype(np.int32)

    if len(symbols) > sample_max:
        idx = rng.choice(len(symbols), size=sample_max, replace=False)
        ys = ys[idx]
        xs = xs[idx]
        symbols = symbols[idx]

    rows = []
    for p in periods:
        phase = (ys % p) * p + (xs % p)
        observed = discrete_mi(symbols, phase)
        nulls = []
        for _ in range(shuffles):
            shuffled = rng.permutation(phase)
            nulls.append(discrete_mi(symbols, shuffled))
        null_mean = float(np.mean(nulls)) if nulls else 0.0
        corrected = max(0.0, observed - null_mean)
        h = entropy_counts(np.bincount(symbols))
        normalized = corrected / h if h > 0 else 0.0
        rows.append((p, observed, null_mean, corrected, normalized))
    return rows


def patch_spectrum(residual, flat_mask, patch=128, stride=64, min_flat=0.92):
    h, w = residual.shape
    if h < patch or w < patch:
        return None, None, 0
    win = np.outer(np.hanning(patch), np.hanning(patch))
    psds, acs = [], []
    for y in range(0, h - patch + 1, stride):
        for x in range(0, w - patch + 1, stride):
            m = flat_mask[y:y+patch, x:x+patch]
            if m.mean() < min_flat:
                continue
            r = residual[y:y+patch, x:x+patch].copy()
            # Fill the small number of excluded edge-near pixels with the flat-region mean.
            mean = float(r[m].mean()) if m.any() else 0.0
            r[~m] = mean
            r -= r.mean()
            r *= win
            F = np.fft.fft2(r)
            P = np.abs(F) ** 2
            total = P.sum()
            if total <= 0:
                continue
            P /= total
            psds.append(np.fft.fftshift(P))
            ac = np.fft.fftshift(np.fft.ifft2(np.abs(F) ** 2).real)
            mx = np.max(np.abs(ac))
            if mx:
                ac /= mx
            acs.append(ac)
    if not psds:
        return None, None, 0
    return np.mean(psds, axis=0), np.mean(acs, axis=0), len(psds)


def spectral_entropy(power, dc_radius=3):
    if power is None:
        return float("nan")
    p = power.copy()
    cy, cx = np.array(p.shape) // 2
    yy, xx = np.indices(p.shape)
    p[(xx-cx)**2 + (yy-cy)**2 <= dc_radius**2] = 0
    p = p.ravel()
    p = p[p > 0]
    if p.size == 0:
        return 0.0
    p = p / p.sum()
    H = -(p * np.log2(p)).sum()
    return float(H / np.log2(len(p)))


def fft_peaks(power, count=60, dc_radius=4, local=5):
    if power is None:
        return []
    p = power.copy()
    h, w = p.shape
    cy, cx = h // 2, w // 2
    yy, xx = np.indices(p.shape)
    p[(xx-cx)**2 + (yy-cy)**2 <= dc_radius**2] = 0
    lm = p == maximum_filter(p, size=local, mode="nearest")
    coords = np.argwhere(lm)
    vals = p[lm]
    order = np.argsort(vals)[::-1]
    rows = []
    for i in order[:count]:
        y, x = coords[i]
        dx, dy = int(x-cx), int(y-cy)
        r = math.hypot(dx, dy)
        period = min(h, w) / r if r else float("inf")
        rows.append((dx, dy, float(vals[i]), float(period)))
    return rows


def shift_correlations(residual, valid, max_shift=64):
    rows = []
    r = residual.astype(np.float64)
    for lag in range(1, max_shift + 1):
        # Horizontal
        m = valid[:, :-lag] & valid[:, lag:]
        if m.sum() > 100:
            a, b = r[:, :-lag][m], r[:, lag:][m]
            ch = float(np.corrcoef(a, b)[0, 1]) if a.std() and b.std() else 0.0
        else:
            ch = float("nan")
        # Vertical
        m = valid[:-lag, :] & valid[lag:, :]
        if m.sum() > 100:
            a, b = r[:-lag, :][m], r[lag:, :][m]
            cv = float(np.corrcoef(a, b)[0, 1]) if a.std() and b.std() else 0.0
        else:
            cv = float("nan")
        rows.append((lag, ch, cv))
    return rows


def radial_profile(power):
    h, w = power.shape
    cy, cx = h // 2, w // 2
    yy, xx = np.indices(power.shape)
    r = np.hypot(xx-cx, yy-cy).astype(np.int32)
    sums = np.bincount(r.ravel(), weights=power.ravel())
    counts = np.bincount(r.ravel())
    return sums / np.maximum(counts, 1)


def angular_profile(power, bins=180, min_radius=5):
    h, w = power.shape
    cy, cx = h // 2, w // 2
    yy, xx = np.indices(power.shape)
    dx, dy = xx-cx, yy-cy
    radius = np.hypot(dx, dy)
    theta = (np.arctan2(dy, dx) + np.pi) % np.pi  # orientation modulo pi
    mask = radius >= min_radius
    ids = np.floor(theta[mask] / np.pi * bins).astype(int)
    ids = np.clip(ids, 0, bins-1)
    sums = np.bincount(ids, weights=power[mask], minlength=bins)
    counts = np.bincount(ids, minlength=bins)
    means = sums / np.maximum(counts, 1)
    degrees = (np.arange(bins) + 0.5) * 180.0 / bins
    return degrees, means


def glcm_metrics(residual, valid):
    vals = residual[valid]
    if vals.size < 100:
        return {}
    lo, hi = np.percentile(vals, [1, 99])
    if hi <= lo:
        hi = lo + 1
    q = np.clip((residual - lo) * 15.0 / (hi-lo), 0, 15).astype(np.uint8)
    # Use a central manageable crop for GLCM.
    h, w = q.shape
    y1, y2 = max(0, h//2-256), min(h, h//2+256)
    x1, x2 = max(0, w//2-256), min(w, w//2+256)
    crop = q[y1:y2, x1:x2]
    glcm = graycomatrix(
        crop,
        distances=[1, 2, 4, 8],
        angles=[0, np.pi/4, np.pi/2, 3*np.pi/4],
        levels=16,
        symmetric=True,
        normed=True,
    )
    return {
        name: float(np.mean(graycoprops(glcm, name)))
        for name in ["contrast", "dissimilarity", "homogeneity", "ASM", "energy", "correlation"]
    }


def wavelet_metrics(residual, level=4):
    if pywt is None:
        return None
    max_level = pywt.dwtn_max_level(residual.shape, "db2")
    level = max(1, min(level, max_level))
    coeffs = pywt.wavedec2(residual, "db2", level=level)
    rows = []
    total = sum(float(np.sum(c*c)) for c in [coeffs[0]])
    for detail in coeffs[1:]:
        total += sum(float(np.sum(c*c)) for c in detail)
    approx_e = float(np.sum(coeffs[0]**2))
    rows.append(("approx", level, approx_e, approx_e/max(total, 1e-30)))
    for idx, (ch, cv, cd) in enumerate(coeffs[1:], start=1):
        scale = level - idx + 1
        for name, c in [("H", ch), ("V", cv), ("D", cd)]:
            e = float(np.sum(c*c))
            rows.append((name, scale, e, e/max(total, 1e-30)))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--output", default="pattern_analysis")
    ap.add_argument("--edge-margin", type=float, default=3.0)
    ap.add_argument("--residual-step", type=float, default=1.0)
    ap.add_argument("--max-period", type=int, default=64)
    ap.add_argument("--mi-sample", type=int, default=250000)
    ap.add_argument("--mi-shuffles", type=int, default=3)
    ap.add_argument("--patch", type=int, default=128)
    ap.add_argument("--stride", type=int, default=64)
    args = ap.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    im = Image.open(args.image).convert("RGB")
    rgb = np.asarray(im, dtype=np.uint8)
    f = rgb.astype(np.float64)
    h, w, _ = rgb.shape
    luma = 0.2126*f[...,0] + 0.7152*f[...,1] + 0.0722*f[...,2]

    threshold = float(threshold_otsu(np.clip(np.rint(luma), 0, 255).astype(np.uint8)))
    ideal = binary_model(luma, threshold)
    residual = luma - ideal

    flat_mask, edge_distance, edge = edge_safe_mask(ideal, args.edge_margin)
    # Keep outer border away from FFT/neighbor calculations.
    flat_mask[:4,:] = flat_mask[-4:,:] = False
    flat_mask[:,:4] = flat_mask[:,-4:] = False

    total = h*w
    exact_black = np.all(rgb == 0, axis=2)
    exact_white = np.all(rgb == 255, axis=2)
    non_binary = ~(exact_black | exact_white)
    distinct = int(len(np.unique(rgb.reshape(-1,3), axis=0)))
    chroma_spread = rgb.max(axis=2).astype(np.int16) - rgb.min(axis=2).astype(np.int16)
    nearest_binary_distance = np.minimum(luma, 255-luma)

    entropies = {
        "R": entropy_u8(rgb[...,0]),
        "G": entropy_u8(rgb[...,1]),
        "B": entropy_u8(rgb[...,2]),
        "luma": entropy_u8(np.clip(np.rint(luma),0,255).astype(np.uint8)),
    }
    packed = (rgb[...,0].astype(np.uint32)<<16) | (rgb[...,1].astype(np.uint32)<<8) | rgb[...,2].astype(np.uint32)
    _, counts = np.unique(packed, return_counts=True)
    joint_rgb_entropy = entropy_counts(counts)

    q, qvals, symbols = quantize_residual(residual, args.residual_step)
    residual_entropy = entropy_counts(np.bincount(symbols[flat_mask]))
    h_h, h_h_cond, h_h_mi = conditional_neighbor_entropy(symbols, flat_mask, True)
    h_v, h_v_cond, h_v_mi = conditional_neighbor_entropy(symbols, flat_mask, False)

    phase_rows = phase_mi_scan(
        symbols, flat_mask, range(2, args.max_period+1),
        args.mi_sample, args.mi_shuffles
    )

    # Dense optical patterns may have no 128x128 patch with >92% edge-safe pixels.
    # Fall back gradually rather than silently losing the spectral section.
    fft_patch_used = args.patch
    fft_min_flat_used = 0.92
    power, autocorr, patch_count = patch_spectrum(
        residual, flat_mask, patch=fft_patch_used, stride=args.stride, min_flat=fft_min_flat_used
    )
    if patch_count == 0:
        for candidate_patch, candidate_flat in [
            (max(64, args.patch // 2), 0.80),
            (max(64, args.patch // 2), 0.65),
            (64, 0.55),
        ]:
            power, autocorr, patch_count = patch_spectrum(
                residual, flat_mask,
                patch=candidate_patch,
                stride=max(32, candidate_patch // 2),
                min_flat=candidate_flat,
            )
            if patch_count:
                fft_patch_used = candidate_patch
                fft_min_flat_used = candidate_flat
                break

    # Last-resort diagnostic: transform the edge-safe residual with edge-near pixels filled by
    # the flat-residual mean. This is explicitly marked as a fallback because the mask/fill can
    # influence the spectrum.
    fft_fallback_global = False
    if patch_count == 0:
        rr = residual.copy()
        fill = float(rr[flat_mask].mean()) if flat_mask.any() else 0.0
        rr[~flat_mask] = fill
        rr -= rr.mean()
        win = np.outer(np.hanning(rr.shape[0]), np.hanning(rr.shape[1]))
        F = np.fft.fftshift(np.fft.fft2(rr * win))
        power = np.abs(F) ** 2
        total_power = power.sum()
        if total_power > 0:
            power /= total_power
        autocorr = np.fft.fftshift(np.fft.ifft2(np.abs(np.fft.fft2(rr * win)) ** 2).real)
        mx = np.max(np.abs(autocorr))
        if mx:
            autocorr /= mx
        fft_fallback_global = True

    spec_entropy = spectral_entropy(power)
    peaks = fft_peaks(power)
    shifts = shift_correlations(residual, flat_mask, args.max_period)

    rgb_bytes = rgb.tobytes()
    residual_flat = q[flat_mask]
    offset = int(residual_flat.min()) if residual_flat.size else 0
    shifted = residual_flat - offset
    if shifted.size and shifted.max() <= 255:
        residual_bytes = shifted.astype(np.uint8).tobytes()
    else:
        residual_bytes = shifted.astype(np.uint16).tobytes()

    glcm = glcm_metrics(residual, flat_mask)
    wave = wavelet_metrics(residual)

    # Images
    Image.fromarray(np.where(ideal>127,255,0).astype(np.uint8), mode="L").save(out/"binary_model.png")
    residual_vis = np.clip(128 + residual*4, 0, 255).astype(np.uint8)
    Image.fromarray(residual_vis, mode="L").save(out/"binary_residual_x4.png")
    save_heatmap(edge_distance, out/"edge_distance.png", "Distance to nearest inferred binary edge")
    save_heatmap(residual, out/"binary_residual_heatmap.png", "Observed - inferred binary", cmap="seismic", symmetric=True)

    # Histograms
    plt.figure(figsize=(11,6))
    plt.hist(luma.ravel(), bins=256)
    plt.axvline(threshold, linestyle="--")
    plt.title(f"Luminance histogram — Otsu threshold {threshold:.2f}")
    plt.xlabel("Luminance")
    plt.ylabel("Pixels")
    plt.tight_layout()
    plt.savefig(out/"luminance_histogram.png", dpi=180)
    plt.close()

    plt.figure(figsize=(11,6))
    plt.hist(nearest_binary_distance.ravel(), bins=128)
    plt.title("Distance to nearest legal binary level (0 or 255)")
    plt.xlabel("Absolute luma distance")
    plt.ylabel("Pixels")
    plt.tight_layout()
    plt.savefig(out/"distance_to_binary_histogram.png", dpi=180)
    plt.close()

    # Local entropy of distance-to-binary, not of the spiral itself.
    dist_u8 = np.clip(np.rint(nearest_binary_distance*2),0,255).astype(np.uint8)
    local_ent = rank_entropy(dist_u8, disk(6))
    save_heatmap(local_ent, out/"local_artifact_entropy.png", "Local entropy of distance-to-binary")

    if power is not None:
        save_heatmap(np.log1p(power / max(np.median(power),1e-30)), out/"flat_residual_fft.png", "Flat-interior residual FFT", cmap="gray")
        save_heatmap(autocorr, out/"flat_residual_autocorrelation.png", "Flat-interior residual autocorrelation", cmap="seismic", symmetric=True)

        rp = radial_profile(power)
        with open(out/"radial_power.csv","w",newline="") as fh:
            wr = csv.writer(fh); wr.writerow(["radius_bin","mean_power"])
            wr.writerows(enumerate(rp))
        deg, ang = angular_profile(power)
        with open(out/"angular_power.csv","w",newline="") as fh:
            wr = csv.writer(fh); wr.writerow(["angle_deg","mean_power"])
            wr.writerows(zip(deg,ang))
        plt.figure(figsize=(11,6)); plt.plot(deg,ang); plt.xlabel("Orientation (deg)"); plt.ylabel("Mean power")
        plt.title("Residual spectral anisotropy"); plt.tight_layout(); plt.savefig(out/"angular_power.png",dpi=180); plt.close()

    with open(out/"spectral_peaks.csv","w",newline="") as fh:
        wr=csv.writer(fh); wr.writerow(["rank","dx","dy","power","approx_period_px"])
        for i,row in enumerate(peaks,1): wr.writerow([i,*row])

    with open(out/"shift_correlations.csv","w",newline="") as fh:
        wr=csv.writer(fh); wr.writerow(["lag_px","horizontal_corr","vertical_corr"]); wr.writerows(shifts)

    with open(out/"phase_entropy.csv","w",newline="") as fh:
        wr=csv.writer(fh)
        wr.writerow(["period_px","observed_MI_bits","permutation_bias_bits","bias_corrected_MI_bits","corrected_MI_over_residual_entropy"])
        wr.writerows(phase_rows)

    pp=np.array([r[0] for r in phase_rows])
    obs=np.array([r[1] for r in phase_rows])
    bias=np.array([r[2] for r in phase_rows])
    corr=np.array([r[3] for r in phase_rows])
    plt.figure(figsize=(12,7))
    plt.plot(pp,obs,label="Observed MI")
    plt.plot(pp,bias,label="Permutation bias")
    plt.plot(pp,corr,label="Bias-corrected MI")
    plt.xlabel("Candidate period (px)"); plt.ylabel("bits")
    plt.title("Phase-conditioned residual information")
    plt.legend(); plt.grid(alpha=.25); plt.tight_layout()
    plt.savefig(out/"phase_entropy_scan.png",dpi=190); plt.close()

    if wave is not None:
        with open(out/"wavelet_energy.csv","w",newline="") as fh:
            wr=csv.writer(fh); wr.writerow(["band","scale","energy","energy_fraction"]); wr.writerows(wave)

    metrics = {
        "image": args.image,
        "width": w,
        "height": h,
        "pixels": total,
        "distinct_rgb_colors": distinct,
        "otsu_threshold": threshold,
        "exact_black_pixels": int(exact_black.sum()),
        "exact_black_fraction": float(exact_black.mean()),
        "exact_white_pixels": int(exact_white.sum()),
        "exact_white_fraction": float(exact_white.mean()),
        "non_binary_pixels": int(non_binary.sum()),
        "non_binary_fraction": float(non_binary.mean()),
        "exact_grayscale_fraction": float(np.all(rgb[...,0:1] == rgb[...,1:], axis=2).mean()),
        "chroma_spread_mean": float(chroma_spread.mean()),
        "chroma_spread_p99": float(np.percentile(chroma_spread,99)),
        "nearest_binary_distance_mean": float(nearest_binary_distance.mean()),
        "nearest_binary_distance_p50": float(np.percentile(nearest_binary_distance,50)),
        "nearest_binary_distance_p90": float(np.percentile(nearest_binary_distance,90)),
        "nearest_binary_distance_p99": float(np.percentile(nearest_binary_distance,99)),
        "channel_entropies_bits": entropies,
        "joint_rgb_entropy_bits_per_pixel": joint_rgb_entropy,
        "flat_interior_fraction": float(flat_mask.mean()),
        "residual_entropy_bits_per_symbol": residual_entropy,
        "horizontal_neighbor_conditional_entropy": h_h_cond,
        "horizontal_neighbor_MI": h_h_mi,
        "vertical_neighbor_conditional_entropy": h_v_cond,
        "vertical_neighbor_MI": h_v_mi,
        "normalized_spectral_entropy": spec_entropy,
        "accepted_fft_patches": patch_count,
        "fft_patch_used": fft_patch_used,
        "fft_min_flat_used": fft_min_flat_used,
        "fft_fallback_global": fft_fallback_global,
        "raw_rgb_zlib_ratio": compression_ratio(rgb_bytes,"zlib"),
        "raw_rgb_lzma_ratio": compression_ratio(rgb_bytes,"lzma"),
        "residual_zlib_ratio": compression_ratio(residual_bytes,"zlib"),
        "residual_lzma_ratio": compression_ratio(residual_bytes,"lzma"),
        "glcm": glcm,
        "pywavelets_available": pywt is not None,
    }
    with open(out/"metrics.json","w") as fh:
        json.dump(metrics, fh, indent=2)

    ranked = sorted(phase_rows, key=lambda r:r[3], reverse=True)
    with open(out/"report.txt","w") as fh:
        fh.write("PATTERN LAB REPORT\n"+"="*72+"\n\n")
        fh.write(f"Resolution: {w} x {h}\n")
        fh.write(f"Distinct RGB values: {distinct:,}\n")
        fh.write(f"Otsu threshold: {threshold:.3f}\n")
        fh.write(f"Exact black: {exact_black.mean():.4%}\n")
        fh.write(f"Exact white: {exact_white.mean():.4%}\n")
        fh.write(f"Non-binary pixels: {non_binary.mean():.4%}\n")
        fh.write(f"Exact grayscale pixels: {metrics['exact_grayscale_fraction']:.4%}\n")
        fh.write(f"Mean distance to nearest 0/255: {nearest_binary_distance.mean():.6f}\n")
        fh.write(f"P90 distance to nearest 0/255: {np.percentile(nearest_binary_distance,90):.6f}\n")
        fh.write(f"P99 distance to nearest 0/255: {np.percentile(nearest_binary_distance,99):.6f}\n\n")
        fh.write("ENTROPY\n"+"-"*72+"\n")
        for k,v in entropies.items(): fh.write(f"{k}: {v:.8f} bits/sample\n")
        fh.write(f"Joint RGB: {joint_rgb_entropy:.8f} bits/pixel\n")
        fh.write(f"Flat residual entropy: {residual_entropy:.8f} bits/symbol\n")
        fh.write(f"Horizontal H(next|prev): {h_h_cond:.8f}; MI={h_h_mi:.8f}\n")
        fh.write(f"Vertical H(next|prev): {h_v_cond:.8f}; MI={h_v_mi:.8f}\n")
        fh.write(f"Normalized spectral entropy: {spec_entropy:.8f}\n")
        fh.write(f"FFT patches: {patch_count}; patch={fft_patch_used}; min_flat={fft_min_flat_used:.2f}; global_fallback={fft_fallback_global}\n\n")
        fh.write("COMPRESSION\n"+"-"*72+"\n")
        fh.write(f"RGB zlib/raw: {metrics['raw_rgb_zlib_ratio']:.8f}\n")
        fh.write(f"RGB lzma/raw: {metrics['raw_rgb_lzma_ratio']:.8f}\n")
        fh.write(f"Residual zlib/raw: {metrics['residual_zlib_ratio']:.8f}\n")
        fh.write(f"Residual lzma/raw: {metrics['residual_lzma_ratio']:.8f}\n\n")
        fh.write("TOP BIAS-CORRECTED PHASE PERIODS\n"+"-"*72+"\n")
        for p,o,b,c,n in ranked[:15]:
            fh.write(f"{p:3d}px observed={o:.8f} bias={b:.8f} corrected={c:.8f} normalized={n:.6%}\n")
        fh.write("\nTOP FLAT-RESIDUAL FFT PEAKS\n"+"-"*72+"\n")
        for i,(dx,dy,pwr,per) in enumerate(peaks[:20],1):
            fh.write(f"{i:02d}: dx={dx:+4d} dy={dy:+4d} period~{per:.4f}px power={pwr:.10e}\n")
        if glcm:
            fh.write("\nGLCM\n"+"-"*72+"\n")
            for k,v in glcm.items(): fh.write(f"{k}: {v:.8f}\n")
        if pywt is None:
            fh.write("\nPyWavelets unavailable at runtime; wavelet section skipped.\n")

    print(f"Done: {out}")
    print(f"Resolution: {w}x{h} | distinct RGB: {distinct:,}")
    print(f"Exact black: {exact_black.mean():.2%} | exact white: {exact_white.mean():.2%} | non-binary: {non_binary.mean():.2%}")
    print(f"Otsu threshold: {threshold:.2f}")
    print(f"Accepted flat FFT patches: {patch_count}")
    print("Top corrected phase periods:")
    for p,o,b,c,n in ranked[:8]:
        print(f"  {p:2d}px corrected MI={c:.6g} bits ({n:.4%} of residual entropy)")


if __name__ == "__main__":
    main()
