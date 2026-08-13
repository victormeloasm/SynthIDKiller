# Frog Photo Lab 🐸🔬📷
## Edge-aware photographic raster analysis and restoration

Frog Photo Lab is the photographic companion to the binary Pattern Lab workflow.

The binary case is easy because every valid pixel can be projected onto exactly two known states.
A real photograph is much harder: legitimate texture, fine edges, skin detail, leaves, moss, hair,
fabric, grain, bokeh, and processing artifacts may occupy the same spatial frequencies.

This toolkit therefore **does not treat "high frequency" as synonymous with "noise"**.

Instead, it estimates where the image is smooth, where it contains meaningful texture, how residual
energy behaves across scales and channels, and then uses several conservative denoisers blended through
a texture-protection mask.

The main goal is:

> Reduce broadband raster noise, low-level chroma contamination, correlated microtexture, and smooth-area
> artifacts while preserving real photographic structure.

This toolkit does not identify or target provenance/watermark systems. FFT and entropy diagnostics are
used as generic image-forensics measurements.

---

## Included tools

```text
frog_photo_lab/
├── README.md
├── requirements.txt
├── presets.json
├── photo_forensics.py
├── frog_restore.py
├── run_photo_all.py
└── compare_photo_reports.py
```

### `photo_forensics.py`

Analyzes a photograph without modifying it.

It measures:

- RGB / luminance Shannon entropy
- joint RGB entropy
- estimated luminance/chroma noise using robust MAD statistics
- local variance
- gradient magnitude
- texture/flatness probability
- flat-patch FFT power
- spectral entropy
- autocorrelation
- radial spectral profile
- angular anisotropy
- inter-channel residual correlation
- horizontal / vertical residual shift correlations
- wavelet energy by scale
- local entropy
- flat-patch statistics
- compressibility
- edge-safe residual statistics

Outputs masks and heatmaps so you can see what the algorithm considers smooth or textured.

### `frog_restore.py`

Produces several restoration candidates and a final edge-aware restoration.

It combines:

- wavelet BayesShrink denoising
- non-local means
- total variation denoising
- bilateral filtering
- LAB luminance/chroma separation
- adaptive smooth-region weighting
- texture and edge protection
- residual guard rails
- optional mild detail recovery
- side-by-side metrics
- removed-component visualization

The final output is **not** a global blur. Smooth areas receive more cleanup; textured and edge-rich
areas retain much more of the original.

### `run_photo_all.py`

Runs forensics and restoration in one command.

### `compare_photo_reports.py`

Combines JSON reports from multiple photographs/controls into one CSV for experiments.

---

# Installation

Use a virtual environment.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Verify:

```bash
python - <<'PY'
import numpy, scipy, PIL, matplotlib, skimage, pywt, cv2
print("Frog Photo Lab dependencies OK")
PY
```

If Debian/Ubuntu reports `externally-managed-environment`, you are probably outside the `.venv`.
Activate the virtual environment and install again. Do not modify the system interpreter just to run
this project.

---

# One-command workflow

If your image is called:

```text
frog.png
```

run:

```bash
python run_photo_all.py frog.png --output frog_results
```

This creates:

```text
frog_results/
├── analysis/
└── restore/
```

Start by opening:

```text
frog_results/restore/restored_balanced.png
frog_results/restore/removed_component_x8.png
frog_results/restore/texture_mask.png
frog_results/restore/cleanup_weight.png
frog_results/analysis/report.txt
frog_results/analysis/flat_patch_fft.png
```

---

# Restoration presets

## Conservative

```bash
python frog_restore.py frog.png \
  --output frog_conservative \
  --preset conservative
```

Use when:

- the image already looks good;
- fine texture is important;
- you mainly want to clean bokeh, sky, walls, skin gradients, or other smooth areas.

## Balanced

```bash
python frog_restore.py frog.png \
  --output frog_balanced \
  --preset balanced
```

Recommended first run.

## Aggressive

```bash
python frog_restore.py frog.png \
  --output frog_aggressive \
  --preset aggressive
```

Use only when visible raster noise is strong.

Always inspect the removed-component image before preferring this result.

---

# Important outputs

## `restored_balanced.png`

Main restored image.

## `candidate_wavelet.png`

Wavelet BayesShrink candidate.

Useful for fine broadband noise.

## `candidate_nlm.png`

Non-local-means candidate.

Often effective in smooth regions while preserving repeated local structure.

## `candidate_tv.png`

Total-variation candidate.

Good at smooth piecewise regions, but can become "cartoon-like" if pushed too far.

## `candidate_bilateral.png`

Edge-preserving local smoothing candidate.

## `texture_mask.png`

Bright = strong texture / edge protection.

Dark = smoother region.

## `cleanup_weight.png`

Bright = the final blend is allowed to use more denoised information.

Dark = preserve more of the original.

This is one of the most important diagnostic images.

## `removed_component_x8.png`

Amplified difference:

```text
original - restored
```

A good restoration usually shows low-level noise, smooth-area microtexture, and very little recognizable
semantic structure.

If you can clearly recognize eyes, toes, leaf veins, individual scales, hairs, letters, or hard object
boundaries in this map, the restoration is too aggressive.

## `detail_retention.png`

Map of local gradient retention.

## `metrics.json`

Numerical before/after measurements.

---

# Forensic workflow

Run:

```bash
python photo_forensics.py frog.png --output frog_forensics
```

Important files:

```text
report.txt
metrics.json
texture_probability.png
flat_probability.png
gradient_magnitude.png
local_variance.png
highpass_residual.png
flat_patch_fft.png
flat_patch_autocorrelation.png
radial_power.csv
angular_power.csv
shift_correlations.csv
wavelet_energy.csv
patch_statistics.csv
```

---

# How the photograph model works

A real photo is modeled conceptually as:

```text
observed = scene_structure + legitimate_texture + unwanted_residual
```

The difficult part is that the last two terms overlap.

The toolkit therefore estimates local structure using several independent cues.

## Gradient magnitude

Strong gradients generally indicate edges or detailed texture.

## Local variance

High local variance often indicates:

- texture;
- edges;
- foliage;
- skin detail;
- fur;
- fabric;
- line structure.

Low variance more often indicates:

- bokeh;
- sky;
- walls;
- smooth gradients;
- flat painted regions.

## Multi-scale residual

The image is compared with Gaussian baselines at multiple scales.

A feature that survives only at very fine scales is treated differently from a coherent large edge.

## Texture probability

The gradient and local-variance measurements are robustly normalized and combined.

This produces a continuous map:

```text
0.0  very smooth
1.0  strongly textured / edge-rich
```

## Cleanup weight

The restoration strength is approximately the inverse of texture probability, with additional guard
rails.

That is why the tool can clean a blurred forest background more strongly than detailed amphibian skin.

---

# Why LAB is used

The program separates:

```text
L*  luminance / structure
a*  green-red chroma
b*  blue-yellow chroma
```

Chroma noise can often be reduced more aggressively than luminance noise without destroying perceived
detail.

The final conversion is returned to sRGB.

---

# Noise estimation

The analyzer uses robust high-pass / wavelet statistics.

A common robust estimate is based on the median absolute deviation:

```text
sigma ~= median(|x - median(x)|) / 0.6745
```

The estimate is restricted toward smooth regions when possible.

This is deliberately an estimate, not a claim about physical sensor noise.

Generated, processed, compressed, or resampled images can contain correlated residuals that violate an
independent Gaussian-noise model.

---

# FFT analysis

The FFT analysis is run primarily on **flat patches**, not the whole photograph.

Why?

A global FFT of a photograph is dominated by real objects and edges.

Flat-region analysis gives periodic raster structure a better chance to appear without confusing it with
tree bark, moss, scales, or leaf edges.

The program averages normalized patch spectra rather than allowing one patch to dominate simply because
it has more energy.

No frequency is automatically deleted because it is strong.

---

# Entropy

The analyzer reports ordinary histogram entropy and residual/texture measurements.

Remember:

- a natural photo can have high entropy;
- random noise can also have high entropy;
- a smooth sky can have low entropy;
- periodic structured noise can be highly predictable spatially despite a broad histogram.

Entropy must be interpreted together with:

- autocorrelation;
- FFT;
- local variance;
- wavelets;
- channel correlation;
- controls.

---

# Recommended experiment

Run the same image through all presets:

```bash
python frog_restore.py frog.png --output conservative --preset conservative
python frog_restore.py frog.png --output balanced --preset balanced
python frog_restore.py frog.png --output aggressive --preset aggressive
```

Compare:

```text
restored_balanced.png
removed_component_x8.png
metrics.json
```

The best result is not automatically the strongest one.

For photography, detail retention matters.

---

# Batch comparison

After analyzing several images:

```bash
python compare_photo_reports.py \
  run1/metrics.json \
  run2/metrics.json \
  run3/metrics.json \
  --output comparison.csv
```

This is useful for comparing:

- multiple independent generations;
- photographs from different sources;
- mathematical controls;
- before/after restoration;
- different restoration presets.

---

# Advanced `frog_restore.py` options

```text
--preset conservative|balanced|aggressive
--strength FLOAT
--texture-protection FLOAT
--detail-recovery FLOAT
--chroma-strength FLOAT
--patch-size INTEGER
--fast
```

CLI values override the preset.

Example:

```bash
python frog_restore.py frog.png \
  --output custom \
  --preset balanced \
  --strength 0.55 \
  --texture-protection 0.90 \
  --chroma-strength 0.75
```

---

# Fast mode

Non-local means can be expensive on large images.

Use:

```bash
python frog_restore.py frog.png \
  --output fast_run \
  --preset balanced \
  --fast
```

Fast mode reduces NLM search complexity.

---

# How to judge the result

A good photo restoration should satisfy several conditions simultaneously:

1. Smooth regions look cleaner.
2. Fine real texture remains visible.
3. Object boundaries remain sharp.
4. Chroma noise decreases without color bleeding.
5. The removed-component visualization does not resemble a recognizable copy of the subject.
6. Gradient retention remains high in texture/edge regions.
7. The restored image does not acquire large halos or plastic-looking surfaces.

There is no universal numerical threshold for a "perfect" restoration.

---

# Very important limitation

The program cannot know the true uncorrupted original photograph.

It produces conservative restoration candidates from the observed raster.

Therefore:

```text
restoration != recovery of mathematically guaranteed ground truth
```

The safest workflow is always to preserve the original file and treat the restored image as a derived
version.

---

# Suggested command for the frog photograph

Start here:

```bash
python run_photo_all.py frog.png \
  --output frog_results \
  --preset balanced
```

Then inspect:

```text
frog_results/restore/restored_balanced.png
frog_results/restore/removed_component_x8.png
frog_results/restore/texture_mask.png
frog_results/restore/cleanup_weight.png
frog_results/analysis/report.txt
```

If the removed component contains too much real texture:

```bash
python frog_restore.py frog.png \
  --output frog_safer \
  --preset conservative
```

If the smooth background is still visibly dirty:

```bash
python frog_restore.py frog.png \
  --output frog_stronger \
  --preset aggressive
```

Compare all three rather than assuming aggressive is better.

---

# Research warning

Do not interpret one entropy number, one FFT peak, or one autocorrelation ridge as proof of a specific
hidden mechanism.

Use repeated samples and controls.

The toolkit is deliberately designed to expose multiple independent measurements so conclusions can be
based on convergence of evidence rather than a single dramatic plot.

🐸🔬


---

# Additional Advanced Tools

## `periodic_residual_filter.py`

This is an **optional manual experiment** for narrow-band periodic artifacts in photographs.

It analyzes a high-pass luminance residual weighted toward smooth regions.

Scan only:

```bash
python periodic_residual_filter.py frog.png \
  --output frog_periodic_scan
```

Inspect:

```text
frog_periodic_scan/spectral_candidates.csv
frog_periodic_scan/smooth_residual_fft.png
frog_periodic_scan/smooth_blend_mask.png
frog_periodic_scan/highpass_residual_x8.png
```

No frequencies are removed unless you explicitly provide a notch.

Example manual test:

```bash
python periodic_residual_filter.py frog.png \
  --output frog_periodic_test \
  --notch 64,0,2,0.25
```

The format is:

```text
dx,dy,radius,strength
```

A conjugate-symmetric counterpart is inserted automatically.

The result is blended primarily into smooth regions so that high-texture areas remain strongly
protected.

Always inspect:

```text
removed_periodic_component_x20.png
```

If it contains recognizable photographic structure, reject the notch.

This tool is intended for generic raster/processing artifact experiments, not automatic source or
provenance identification.

---

## `make_photo_controls.py`

Generates controlled synthetic images for validating the photographic forensic pipeline.

```bash
python make_photo_controls.py \
  --output photo_controls \
  --width 2048 \
  --height 1117
```

Generated controls include:

```text
gradient_rgb.png
gradient_rgb_gaussian_sigma1.png
gradient_rgb_periodic_16x8.png
gradient_rgb_correlated_noise.png
synthetic_bokeh_clean.png
synthetic_bokeh_gaussian_sigma1.png
```

These are useful for checking whether a metric responds to:

- independent Gaussian noise;
- correlated channel noise;
- known 8/16-pixel periodic contamination;
- perfectly clean smooth gradients;
- clean bokeh-like low-frequency content.

Run `photo_forensics.py` on every control with the same settings used on the real photograph.

---

## `run_presets.py`

Runs all three restoration presets and creates a comparison contact sheet.

```bash
python run_presets.py frog.png \
  --output frog_presets \
  --fast
```

It creates:

```text
frog_presets/
├── conservative/
├── balanced/
├── aggressive/
├── preset_metrics.csv
└── preset_contact_sheet.jpg
```

This is the easiest way to decide how much cleanup is visually acceptable.

The strongest preset is not necessarily the best preset.

---

# Example results included in this ZIP

The `example_frog_results/` directory contains a smoke test performed on the supplied 2048×1117 frog
photograph.

The forensic run measured approximately:

```text
Distinct RGB colors:                  541,466
Luminance entropy:                    7.649 bits/sample
Joint RGB entropy:                   17.725 bits/pixel
Smooth-region high-pass sigma:        0.00473 (normalized luminance)
Flat-patch normalized spectral H:     0.98773
Accepted smooth FFT patches:          256
```

The smooth-region high-pass RGB residual showed strong inter-channel correlation, around 0.84–0.86 in
the example. That means the residual is not well described as independent per-channel white noise.

The balanced restoration smoke test produced approximately:

```text
SSIM vs original:                     0.99824
RMS 8-bit pixel change:               0.382
Mean absolute 8-bit pixel change:     0.141
Mean cleanup weight:                  0.272
Smooth/textured change ratio:        35.6
```

The final ratio is particularly useful: the floating-point restoration changed smooth regions much more
than strongly textured regions, which is the intended behavior of the texture guard rail.

These values are not universal quality thresholds. They simply document the included example run.

---

# Recommended first command for a real photograph

```bash
python run_photo_all.py frog.png \
  --output frog_results \
  --preset balanced \
  --fast
```

Then, if you want all restoration strengths:

```bash
python run_presets.py frog.png \
  --output frog_presets \
  --fast
```

For the most conservative scientific comparison, keep the original image unchanged and treat every
restored output as a derived artifact.
