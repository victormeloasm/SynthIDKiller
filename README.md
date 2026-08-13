# Frog Photo Lab 🐸🔬📷

**A research-oriented toolkit for photographic raster forensics, smooth-region residual analysis, edge-aware denoising, periodic artifact inspection, and conservative image restoration.**

Frog Photo Lab is designed for the difficult case where an image is a **real photograph or a photo-like raster**, so high-frequency content cannot simply be treated as noise.

A frog's skin, moss, leaves, bark, fabric, hair, eye texture, small specular highlights, and thin edges can occupy the same frequency ranges as processing artifacts. A global blur, a broad FFT notch, or an aggressive denoiser can therefore make an image look "cleaner" while actually destroying legitimate detail.

This toolkit takes the opposite approach:

> **Estimate where the image is smooth, estimate where meaningful detail is likely to exist, analyze residual behavior primarily in smooth regions, and apply restoration much more strongly where the risk of destroying real texture is low.**

The package contains independent tools for:

- photographic forensics;
- smooth-region FFT analysis;
- entropy and residual statistics;
- spatial autocorrelation;
- directional correlation;
- multi-scale wavelet energy;
- adaptive edge/texture masks;
- LAB-based luminance/chroma processing;
- multiple denoising candidates;
- ensemble restoration;
- manual periodic residual experiments;
- synthetic control-image generation;
- preset comparison;
- batch metric comparison.

---

# Table of Contents

1. [Project Goals](#project-goals)
2. [What Frog Photo Lab Does Not Assume](#what-frog-photo-lab-does-not-assume)
3. [Package Contents](#package-contents)
4. [Requirements](#requirements)
5. [Installation](#installation)
6. [Quick Start](#quick-start)
7. [Recommended Workflow](#recommended-workflow)
8. [`run_photo_all.py`](#run_photo_allpy)
9. [`photo_forensics.py`](#photo_forensicspy)
10. [Understanding the Forensic Model](#understanding-the-forensic-model)
11. [Entropy Measurements](#entropy-measurements)
12. [Smooth-Region Residual Estimation](#smooth-region-residual-estimation)
13. [Texture and Flatness Maps](#texture-and-flatness-maps)
14. [FFT Analysis](#fft-analysis)
15. [Autocorrelation and Shift Correlation](#autocorrelation-and-shift-correlation)
16. [Wavelet Analysis](#wavelet-analysis)
17. [Channel Correlation](#channel-correlation)
18. [Compression Measurements](#compression-measurements)
19. [`photo_forensics.py` Output Files](#photo_forensicspy-output-files)
20. [`frog_restore.py`](#frog_restorepy)
21. [How the Restoration Pipeline Works](#how-the-restoration-pipeline-works)
22. [Restoration Candidates](#restoration-candidates)
23. [Texture Protection and Cleanup Weight](#texture-protection-and-cleanup-weight)
24. [Residual Guard Rail](#residual-guard-rail)
25. [LAB Color Processing](#lab-color-processing)
26. [Detail Recovery](#detail-recovery)
27. [Restoration Presets](#restoration-presets)
28. [`frog_restore.py` Output Files](#frog_restorepy-output-files)
29. [How to Judge a Restoration](#how-to-judge-a-restoration)
30. [`run_presets.py`](#run_presetspy)
31. [`periodic_residual_filter.py`](#periodic_residual_filterpy)
32. [Why Periodic Filtering Is Manual](#why-periodic-filtering-is-manual)
33. [FFT Notch Coordinates](#fft-notch-coordinates)
34. [Spatial Period Conversion](#spatial-period-conversion)
35. [Manual Periodic Artifact Workflow](#manual-periodic-artifact-workflow)
36. [How to Inspect the Removed Component](#how-to-inspect-the-removed-component)
37. [8-bit Quantization and Sub-LSB Changes](#8-bit-quantization-and-sub-lsb-changes)
38. [`make_photo_controls.py`](#make_photo_controlspy)
39. [Synthetic Controls](#synthetic-controls)
40. [`compare_photo_reports.py`](#compare_photo_reportspy)
41. [`quick_run.sh`](#quick_runsh)
42. [`presets.json`](#presetsjson)
43. [Example Frog Workflow](#example-frog-workflow)
44. [Verification After Periodic Filtering](#verification-after-periodic-filtering)
45. [Performance and Runtime](#performance-and-runtime)
46. [Reproducibility](#reproducibility)
47. [Troubleshooting](#troubleshooting)
48. [Interpretation Guide](#interpretation-guide)
49. [Common Mistakes](#common-mistakes)
50. [Known Limitations](#known-limitations)
51. [Suggested Research Methodology](#suggested-research-methodology)
52. [Command Reference](#command-reference)
53. [Final Notes](#final-notes)

---

# Project Goals

Frog Photo Lab tries to answer questions such as:

- How complex is the stored raster?
- How much entropy exists in luminance and RGB channels?
- Do smooth regions contain measurable high-frequency residual structure?
- Is that residual approximately independent, correlated, directional, or periodic?
- Are residual fluctuations correlated across RGB channels?
- Does the same spatial period recur in FFT, autocorrelation, or shift-correlation measurements?
- Can smooth regions be cleaned without destroying detailed objects?
- Does a denoiser remove mostly low-level residual, or does it begin removing recognizable scene structure?
- Can a narrow periodic component be isolated experimentally without using a broad destructive filter?
- How does the same analysis behave on mathematical controls with known noise?

The central rule is:

> **No single metric is treated as proof of a specific cause.**

A spectral peak is a spectral peak.  
A correlation is a correlation.  
An entropy value is an entropy value.

Source attribution requires controls, repeated samples, and independent evidence.

---

# What Frog Photo Lab Does Not Assume

A real photograph is not a binary image.

The toolkit does **not** assume that:

```text
high frequency = noise
```

or that:

```text
smooth = fake
```

or that:

```text
periodic = removable
```

or that:

```text
low entropy = bad
```

or that:

```text
high entropy = natural
```

Natural images contain enormous amounts of structure.

Examples:

- a frog's skin can be highly textured;
- foliage produces broadband high-frequency energy;
- defocused bokeh can be very smooth;
- tree trunks can generate directional structure;
- repeated leaves can generate frequency peaks;
- resampling can create periodic components;
- sharpening can produce halos and high-frequency ringing;
- denoisers can create artificial smoothness.

This is why the toolkit separates **measurement** from **restoration** and why the periodic filter does not automatically delete detected FFT peaks.

---

# Package Contents

The ZIP contains:

```text
frog_photo_lab/
├── README.md
├── requirements.txt
├── presets.json
├── quick_run.sh
├── run_photo_all.py
├── run_presets.py
├── photo_forensics.py
├── frog_restore.py
├── periodic_residual_filter.py
├── make_photo_controls.py
├── compare_photo_reports.py
└── example_frog_results/
    ├── analysis/
    └── restore/
```

## Tool summary

| File | Purpose |
|---|---|
| `photo_forensics.py` | Main non-destructive photographic analysis |
| `frog_restore.py` | Adaptive photographic restoration |
| `periodic_residual_filter.py` | Manual narrow-band periodic residual experiment |
| `run_photo_all.py` | Forensics + restoration in one command |
| `run_presets.py` | Runs conservative, balanced, and aggressive restoration presets |
| `make_photo_controls.py` | Generates synthetic control images |
| `compare_photo_reports.py` | Combines multiple JSON reports into a CSV |
| `quick_run.sh` | Convenience launcher |
| `presets.json` | Human-readable preset definitions |
| `requirements.txt` | Python dependencies |
| `example_frog_results/` | Example output from a frog photograph |

---

# Requirements

The package declares:

```text
numpy>=2.0
scipy>=1.14
Pillow>=11.0
matplotlib>=3.9
scikit-image>=0.25
PyWavelets>=1.7
opencv-python-headless>=4.10
```

Python 3.10+ is recommended.

A recent Python 3.13/3.14 environment should also work as long as wheels are available for the dependencies.

---

# Installation

## Recommended: virtual environment

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Upgrade pip:

```bash
python -m pip install --upgrade pip
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Verify imports:

```bash
python - <<'PY'
import numpy
import scipy
import PIL
import matplotlib
import skimage
import pywt
import cv2

print("NumPy:", numpy.__version__)
print("SciPy:", scipy.__version__)
print("Pillow:", PIL.__version__)
print("Matplotlib:", matplotlib.__version__)
print("scikit-image:", skimage.__version__)
print("PyWavelets:", pywt.__version__)
print("OpenCV:", cv2.__version__)
print("Frog Photo Lab dependencies OK")
PY
```

---

# Debian / Ubuntu and PEP 668

If you see:

```text
error: externally-managed-environment
```

you are probably using the distribution-managed Python interpreter instead of your virtual environment.

Activate your environment again:

```bash
source .venv/bin/activate
```

Then check:

```bash
which python
```

Expected:

```text
/home/user/project/.venv/bin/python
```

Not:

```text
/usr/bin/python
```

Then install:

```bash
python -m pip install -r requirements.txt
```

Avoid modifying the system interpreter with `--break-system-packages` just to run this toolkit.

---

# Quick Start

Assume the image is:

```text
frog.png
```

and is in the current directory.

Run the main workflow:

```bash
python run_photo_all.py frog.png \
  --output frog_results \
  --preset balanced \
  --fast
```

The two main result directories are:

```text
frog_results/analysis/
frog_results/restore/
```

Start by opening:

```text
frog_results/analysis/report.txt
frog_results/analysis/flat_patch_fft.png
frog_results/analysis/flat_patch_autocorrelation.png

frog_results/restore/restored_balanced.png
frog_results/restore/removed_component_x8.png
frog_results/restore/texture_mask.png
frog_results/restore/cleanup_weight.png
frog_results/restore/report.txt
```

---

# Recommended Workflow

A careful workflow is:

## 1. Preserve the original

Never overwrite the source photograph.

Keep:

```text
original.png
```

and write every derived artifact to a separate directory.

## 2. Run forensics first

```bash
python photo_forensics.py frog.png \
  --output frog_forensics
```

Read:

```text
frog_forensics/report.txt
frog_forensics/metrics.json
```

Inspect:

```text
texture_probability.png
flat_probability.png
highpass_residual.png
flat_patch_fft.png
flat_patch_autocorrelation.png
```

## 3. Run a conservative or balanced restoration

```bash
python frog_restore.py frog.png \
  --output frog_restore_balanced \
  --preset balanced \
  --fast
```

## 4. Inspect what was removed

Open:

```text
removed_component_x8.png
```

This is essential.

If the removed component contains obvious real objects, the restoration is too aggressive.

## 5. Compare all presets if necessary

```bash
python run_presets.py frog.png \
  --output frog_preset_comparison \
  --fast
```

## 6. Only investigate periodic filtering if the forensics justify it

```bash
python periodic_residual_filter.py \
  frog_restore_balanced/restored_balanced.png \
  --output periodic_scan
```

Do not apply a notch before inspecting:

```text
periodic_scan/spectral_candidates.csv
periodic_scan/smooth_residual_fft.png
```

---

# `run_photo_all.py`

`run_photo_all.py` is the primary convenience wrapper.

## Syntax

```text
python run_photo_all.py IMAGE
    [--output DIRECTORY]
    [--preset conservative|balanced|aggressive]
    [--fast]
```

## Positional argument

### `image`

Input image path.

Example:

```bash
python run_photo_all.py frog.png
```

## `--output`

Default:

```text
frog_photo_results
```

Example:

```bash
python run_photo_all.py frog.png \
  --output experiment_01
```

## `--preset`

Choices:

```text
conservative
balanced
aggressive
```

Default:

```text
balanced
```

## `--fast`

Uses the faster restoration configuration.

The main difference is reduced NLM search complexity.

Example:

```bash
python run_photo_all.py frog.png \
  --output frog_results \
  --preset balanced \
  --fast
```

## What it actually executes

The wrapper runs:

```bash
python photo_forensics.py IMAGE --output OUTPUT/analysis
```

and then:

```bash
python frog_restore.py IMAGE \
  --output OUTPUT/restore \
  --preset PRESET
```

If `--fast` was given, it is forwarded to `frog_restore.py`.

---

# `photo_forensics.py`

This script performs **non-destructive analysis**.

It does not produce a restored photograph.

## Syntax

```text
python photo_forensics.py IMAGE
    [--output DIRECTORY]
    [--patch INTEGER]
    [--stride INTEGER]
    [--flat-threshold FLOAT]
    [--max-lag INTEGER]
```

## Example

```bash
python photo_forensics.py frog.png \
  --output frog_analysis
```

---

# `--output`

Default:

```text
photo_forensics
```

---

# `--patch`

Default:

```text
128
```

Controls the square FFT patch size.

A patch of:

```text
128 × 128
```

is used by default.

Larger patches improve frequency resolution but require larger sufficiently smooth regions.

Example:

```bash
python photo_forensics.py frog.png \
  --output fft256 \
  --patch 256
```

---

# `--stride`

Default:

```text
64
```

Controls the distance between neighboring FFT patch origins.

For:

```text
patch = 128
stride = 64
```

patches overlap by 50%.

Smaller stride:

- more overlapping patches;
- more computation;
- more samples.

Larger stride:

- less computation;
- fewer samples.

---

# `--flat-threshold`

Default:

```text
0.78
```

Controls which candidate patches are considered smooth enough for the FFT aggregation.

A patch must have a mean flatness probability above this threshold.

If no patch passes, the script automatically tries a fallback using:

```text
patch = 64
stride = 32
flat threshold = max(0.60, original_threshold - 0.15)
```

---

# `--max-lag`

Default:

```text
64
```

Maximum horizontal and vertical pixel displacement tested in residual shift correlation.

Example:

```bash
python photo_forensics.py frog.png \
  --output lag128 \
  --max-lag 128
```

---

# Understanding the Forensic Model

The conceptual model is:

```text
observed photograph
    =
scene structure
    +
legitimate photographic texture
    +
processing / raster residual
```

The problem is that the last two components overlap.

There is no oracle that tells the program:

```text
this pixel is texture
this pixel is noise
```

Instead, Frog Photo Lab estimates a **continuous texture probability** using:

- luminance gradient magnitude;
- local luminance variance;
- fine high-pass energy;
- slightly larger-scale high-pass energy.

The inverse becomes a smooth-region probability.

This is then used to choose which image regions contribute most strongly to residual analysis.

---

# Luminance Conversion

The image is converted from sRGB to CIELAB:

```text
RGB -> LAB
```

The luminance-like LAB component is:

```text
L*
```

The code normalizes:

```text
L = L* / 100
```

to roughly:

```text
0.0 ... 1.0
```

This gives a useful structural channel that is separated from chromatic components.

---

# Entropy Measurements

The analyzer computes ordinary Shannon entropy for:

```text
R
G
B
Luma
```

For discrete symbols:

\[
H(X)=-\sum_x p(x)\log_2 p(x)
\]

Entropy answers:

> How diverse is the symbol distribution?

It does **not** answer:

> Is this image natural?

or:

> Is this noise?

Examples:

- independent noise can have very high entropy;
- a clean blue sky can have lower entropy;
- grass can have high entropy;
- a deterministic periodic signal can have relatively low spatial uncertainty.

This is why entropy is only one measurement.

---

# Joint RGB Entropy

Each RGB triplet is packed into one symbol.

Conceptually:

```text
R << 16 | G << 8 | B
```

The analyzer calculates entropy over complete RGB colors.

This gives a measure of stored color diversity.

---

# Smooth-Region Residual Estimation

The core fine residual is approximately:

```text
HP = L - GaussianBlur(L, sigma=1)
```

The smoothest 20% of pixels according to the flatness map are used to obtain robust residual estimates.

The script computes a MAD-based scale estimate:

\[
\sigma \approx
\frac{\mathrm{median}(|x-\mathrm{median}(x)|)}
{0.67448975}
\]

This is robust against isolated strong deviations.

Important:

> The result is an empirical high-pass residual scale estimate.

It is not necessarily physical camera sensor noise.

A processed or generated image can contain:

- correlated residuals;
- interpolation texture;
- sharpening;
- denoising artifacts;
- quantization;
- resampling;
- decoder structure.

Those do not follow a simple independent Gaussian sensor-noise model.

---

# Chroma Residual Estimation

The program separately estimates high-pass residual scales for:

```text
LAB a*
LAB b*
```

using:

```text
channel - GaussianBlur(channel, sigma=1)
```

followed by the same robust MAD estimate.

This is useful because chromatic noise can behave very differently from luminance detail.

---

# Texture and Flatness Maps

The texture model combines three measurements.

## Gradient magnitude

Computed using Sobel:

```text
gradient = sobel(L)
```

Strong edges tend to increase this signal.

## Local standard deviation

The code estimates local variance through:

```text
E[x²] - E[x]²
```

and then takes the square root.

High local variation often indicates:

- foliage;
- skin texture;
- edges;
- hair;
- fabric;
- gravel;
- bark;
- small line structure.

## Multi-scale high-pass energy

The program calculates residuals at approximately:

```text
sigma = 1
sigma = 3
```

and combines local energy from both.

## Final texture probability

After robust percentile normalization, the approximate combination is:

```text
texture
    =
0.50 × normalized gradient
+
0.30 × normalized local variation
+
0.20 × normalized high-pass energy
```

Then:

```text
flat = 1 - texture
```

Both maps are continuous from approximately:

```text
0.0 ... 1.0
```

---

# FFT Analysis

A global FFT of a photograph is often dominated by real scene content.

Examples:

- tree trunks;
- horizon lines;
- leaf repetition;
- object edges;
- texture orientation.

Frog Photo Lab therefore computes FFT statistics over **smooth candidate patches**.

For each accepted patch:

1. extract the luminance high-pass residual;
2. remove the patch mean;
3. multiply by a 2D Hann window;
4. compute the 2D FFT;
5. calculate power:
   \[
   P=|F|^2
   \]
6. normalize the patch power by its total power;
7. shift DC to the center;
8. average normalized spectra across accepted patches.

Normalization prevents one unusually energetic patch from dominating the entire result.

---

# Why a Hann Window Is Used

Finite patch boundaries create spectral leakage.

The Hann window reduces hard boundary discontinuities before the FFT.

It does not eliminate all window-related effects.

Controls are still necessary.

---

# Spectral Entropy

The analyzer removes a small central DC region and normalizes the remaining FFT power:

\[
p_i=\frac{P_i}{\sum P}
\]

Then calculates entropy and normalizes by the maximum possible entropy for the number of bins.

Interpretation:

```text
closer to 1.0
    -> power broadly distributed

lower
    -> power more concentrated
```

There is no universal threshold separating "clean" from "dirty."

Use matched controls.

---

# Spectral Peaks

The analyzer finds local maxima outside the central FFT region.

Output:

```text
spectral_peaks.csv
```

Columns:

```text
rank
dx
dy
power
approx_period_px
```

`dx` and `dy` are frequency-bin offsets from the FFT center.

The reported `approx_period_px` uses a radial approximation based on the patch size.

For precise interpretation of axis-aligned components, use the appropriate image or patch dimension directly.

---

# Autocorrelation and Shift Correlation

FFT and autocorrelation describe related aspects of repeated structure.

## Patch autocorrelation

For each accepted patch:

```text
AC = IFFT(|FFT(patch)|²)
```

The result is centered and normalized.

The script then averages autocorrelations.

Output:

```text
flat_patch_autocorrelation.png
```

A repeated texture may create:

- repeated peaks;
- ridges;
- regular spacing;
- directional structure.

---

# Shift Correlation

The analyzer independently measures direct correlation of the high-pass residual after shifts of:

```text
1 px
2 px
...
max_lag px
```

for both:

```text
horizontal
vertical
```

Output:

```text
shift_correlations.csv
```

This is useful because an FFT candidate can be checked against a direct spatial-domain measurement.

---

# Wavelet Analysis

The high-pass luminance residual is decomposed with a 2D `db2` wavelet transform.

The program records energy in:

```text
A = approximation
H = horizontal detail
V = vertical detail
D = diagonal detail
```

at multiple scales.

Output:

```text
wavelet_energy.csv
```

Use wavelet energy to compare how residual energy is distributed across:

- fine scales;
- medium scales;
- orientations.

This is particularly useful across matched control images.

---

# Channel Correlation

The analyzer computes an RGB high-pass residual:

```text
RGB - GaussianBlur(RGB, sigma≈1)
```

inside the smooth-region mask.

It then calculates the 3×3 correlation matrix.

Example structure:

```text
[[1.00, 0.85, 0.86],
 [0.85, 1.00, 0.84],
 [0.86, 0.84, 1.00]]
```

Strong correlation means the residual is not behaving like three independent channel-noise processes.

Possible reasons include:

- luminance-dominated processing residual;
- shared interpolation;
- sharpening;
- decoder/raster processing;
- correlated image synthesis artifacts;
- common post-processing.

The metric does not identify the cause by itself.

---

# Compression Measurements

The analyzer records:

```text
zlib compressed size / raw size
LZMA compressed size / raw size
```

for RGB bytes.

More regular or redundant data tends to compress better.

However, real photographs already contain enormous structural redundancy.

Compression is therefore a comparative metric, not a detector.

---

# `photo_forensics.py` Output Files

A typical output directory contains:

```text
report.txt
metrics.json
texture_probability.png
flat_probability.png
gradient_magnitude.png
local_variance.png
highpass_residual.png
local_entropy.png
flat_patch_fft.png
flat_patch_autocorrelation.png
radial_power.csv
angular_power.csv
angular_power.png
spectral_peaks.csv
shift_correlations.csv
wavelet_energy.csv
patch_statistics.csv
```

---

# `report.txt`

Human-readable summary.

Contains:

- image dimensions;
- distinct RGB color count;
- entropy;
- smooth-region residual estimates;
- accepted patch count;
- spectral entropy;
- RGB residual correlation;
- top FFT candidates.

---

# `metrics.json`

Machine-readable metrics.

Useful for:

- scripts;
- notebooks;
- batch experiments;
- `compare_photo_reports.py`.

---

# `texture_probability.png`

Bright regions indicate stronger texture/edge probability.

These regions should usually be protected more strongly during restoration.

---

# `flat_probability.png`

Bright regions indicate smoother candidate areas.

These are especially useful for residual statistics and FFT analysis.

---

# `gradient_magnitude.png`

Sobel luminance gradient.

Useful for identifying strong scene structure.

---

# `local_variance.png`

Local luminance standard deviation.

Useful for distinguishing flat bokeh-like regions from detailed texture.

---

# `highpass_residual.png`

Fine luminance residual:

```text
L - GaussianBlur(L)
```

Displayed using a signed heatmap.

This image contains both legitimate detail and unwanted residual.

Do not interpret it as a "noise map."

---

# `local_entropy.png`

Local entropy of a normalized version of the high-pass residual.

Useful for spatial comparison.

---

# `flat_patch_fft.png`

Average normalized FFT power from accepted smooth patches.

This is one of the central forensic outputs.

---

# `flat_patch_autocorrelation.png`

Average autocorrelation of accepted smooth patches.

---

# `radial_power.csv`

Radially averaged FFT power.

Useful for measuring how energy changes with spatial frequency magnitude.

---

# `angular_power.csv`

FFT power grouped by orientation.

Useful for directional anisotropy.

---

# `angular_power.png`

Plot of spectral power by orientation.

---

# `spectral_peaks.csv`

Strong local maxima in the smooth-patch FFT.

Use these as candidate frequencies for investigation.

Do not automatically filter them.

---

# `shift_correlations.csv`

Direct horizontal and vertical residual correlations for each pixel lag.

---

# `wavelet_energy.csv`

Residual energy by wavelet band and scale.

---

# `patch_statistics.csv`

One row per accepted FFT patch.

Columns:

```text
x
y
mean_flat_probability
residual_rms
residual_std
mean_abs_residual
```

This lets you study spatial variation rather than relying only on global averages.

---

# `frog_restore.py`

This is the main photographic restoration tool.

It creates multiple candidate denoisers and blends them conservatively through a texture-aware mask.

## Syntax

```text
python frog_restore.py IMAGE
    [--output DIRECTORY]
    [--preset conservative|balanced|aggressive]
    [--strength FLOAT]
    [--texture-protection FLOAT]
    [--detail-recovery FLOAT]
    [--chroma-strength FLOAT]
    [--fast]
```

---

# Basic Example

```bash
python frog_restore.py frog.png \
  --output frog_restore \
  --preset balanced \
  --fast
```

---

# `--preset`

Choices:

```text
conservative
balanced
aggressive
```

Default:

```text
balanced
```

---

# `--strength`

Overrides the preset's global restoration strength.

The final cleanup weight is multiplied by this value.

Example:

```bash
python frog_restore.py frog.png \
  --output custom \
  --preset balanced \
  --strength 0.50
```

---

# `--texture-protection`

Overrides how rapidly cleanup falls as texture probability rises.

Larger values protect textured regions more strongly.

Example:

```bash
--texture-protection 0.92
```

---

# `--detail-recovery`

Controls conservative re-injection of fine original detail.

This only acts where:

- texture exists;
- cleanup was actually applied.

The implementation intentionally avoids sharpening untouched textured areas.

---

# `--chroma-strength`

Controls how much denoised LAB chroma is used.

Higher values reduce more color variation.

Example:

```bash
--chroma-strength 0.80
```

Use caution on images where tiny color variations are semantically important.

---

# `--fast`

Reduces NLM search complexity.

The output remains based on the same overall restoration design.

---

# How the Restoration Pipeline Works

Conceptually:

```text
RGB input
   ↓
convert to LAB
   ↓
estimate texture probability
   ↓
produce multiple luminance denoise candidates
   ↓
produce chroma-denoised channels
   ↓
rebuild RGB candidates
   ↓
weighted candidate ensemble
   ↓
calculate cleanup mask
   ↓
residual/edge guard rail
   ↓
blend original and denoised candidate
   ↓
optional local detail recovery
   ↓
8-bit RGB output
```

---

# Restoration Candidates

The program generates four intermediate restoration candidates.

## Wavelet candidate

Uses:

```text
BayesShrink
soft thresholding
```

on luminance.

The estimated luminance residual scale is passed to the wavelet denoiser.

If PyWavelets is unavailable at runtime, the code has a mild Gaussian fallback so the rest of the pipeline can still execute, although installing the declared dependencies is strongly recommended.

---

# NLM candidate

Uses non-local means.

NLM searches for similar local patches.

This can preserve repeated local structure better than a simple blur.

The implementation uses:

```text
patch_size = 5
patch_distance = 7
```

or:

```text
patch_distance = 5
```

in fast mode.

---

# TV candidate

Uses total-variation denoising.

TV is useful for smooth piecewise regions but can become cartoon-like if overused.

For this reason it receives a relatively small weight in the ensemble.

---

# Bilateral candidate

Uses bilateral denoising.

This smooths based on both:

- spatial distance;
- intensity similarity.

It is used as an edge-aware supporting candidate.

---

# Ensemble Weights

The current luminance/color ensemble is approximately:

```text
34% wavelet
34% NLM
20% bilateral
12% TV
```

This prevents the final result from depending completely on one denoising family.

---

# LAB Color Processing

The RGB image is converted to LAB:

```text
L*
a*
b*
```

Luminance and chroma are processed separately.

The `a*` and `b*` channels are normalized internally and denoised more simply using a wavelet + mild Gaussian combination.

The final LAB image is converted back to sRGB.

---

# Texture Protection and Cleanup Weight

The cleanup mask is based on:

```text
(1 - texture_probability) ^ exponent
```

where:

```text
exponent = 1 + 5 × texture_protection
```

Then it is blurred slightly to avoid visible blend transitions.

Finally:

```text
cleanup *= global strength
```

Therefore:

- smooth areas can receive substantial restoration;
- textured areas quickly approach zero cleanup.

---

# Residual Guard Rail

A denoiser can still propose an unsafe change near real edges.

The toolkit therefore estimates a semantic-risk-like map using:

```text
edge energy × removed-component energy
```

If the proposed change is strong in a region that is also strongly edge-like, cleanup is reduced.

Conceptually:

```text
cleanup *= 1 - 0.80 × risk
```

This is one of the most important protection mechanisms.

---

# Detail Recovery

After restoration, the script calculates a fine-detail component from the **original** image.

A small fraction is re-injected only where both:

- the image is textured;
- cleanup actually happened.

This avoids indiscriminate sharpening.

The detail-recovery mask is capped conservatively.

---

# Restoration Presets

The package defines:

## Conservative

```json
{
  "strength": 0.45,
  "texture_protection": 0.88,
  "detail_recovery": 0.10,
  "chroma_strength": 0.55
}
```

Use when:

- preserving detail is the highest priority;
- the image already looks good;
- artifacts are mostly visible in very smooth areas.

---

## Balanced

```json
{
  "strength": 0.62,
  "texture_protection": 0.82,
  "detail_recovery": 0.16,
  "chroma_strength": 0.72
}
```

Recommended starting point.

---

## Aggressive

```json
{
  "strength": 0.78,
  "texture_protection": 0.72,
  "detail_recovery": 0.20,
  "chroma_strength": 0.85
}
```

Use only when stronger cleanup is justified.

Always inspect the removed component.

---

# `frog_restore.py` Output Files

Typical output:

```text
candidate_wavelet.png
candidate_nlm.png
candidate_tv.png
candidate_bilateral.png
restored_balanced.png
texture_mask.png
cleanup_weight.png
detail_retention.png
removed_component_x8.png
metrics.json
report.txt
```

The restored filename changes with the preset.

Examples:

```text
restored_conservative.png
restored_balanced.png
restored_aggressive.png
```

---

# `candidate_wavelet.png`

Wavelet-based candidate before adaptive final blending.

---

# `candidate_nlm.png`

NLM candidate.

---

# `candidate_tv.png`

TV candidate.

---

# `candidate_bilateral.png`

Bilateral candidate.

---

# `texture_mask.png`

Bright:

```text
more texture / stronger protection
```

Dark:

```text
smoother / safer to modify
```

---

# `cleanup_weight.png`

Bright:

```text
use more of the denoised ensemble
```

Dark:

```text
preserve more original pixels
```

This is a more direct representation of actual restoration strength than the raw texture mask.

---

# `removed_component_x8.png`

Displays:

```text
original - restored
```

with gain:

```text
×8
```

centered around gray.

This is one of the most important quality-control outputs.

A good result should mostly show low-amplitude residual rather than a recognizable reconstruction of the subject.

---

# `detail_retention.png`

Measures local gradient retention.

It is a diagnostic visualization, not a perceptual ground-truth metric.

---

# `metrics.json`

Contains:

```text
preset
configuration
estimated luminance sigma
RMS pixel change
mean absolute pixel change
SSIM vs original
mean cleanup weight
P95 cleanup weight
mean change in smooth regions
mean change in textured regions
smooth/textured change ratio
mean texture probability
```

---

# `report.txt`

Human-readable restoration summary.

---

# How to Judge a Restoration

Never select a restoration only because:

```text
it looks smoother
```

or:

```text
the residual got smaller
```

A high-quality result should satisfy several conditions.

## 1. Smooth areas improve

Examples:

- bokeh;
- sky;
- defocused foliage;
- walls;
- broad smooth gradients.

## 2. Detailed objects remain intact

Examples:

- eye edges;
- skin texture;
- toes;
- scales;
- hair;
- leaf veins;
- fine moss;
- text.

## 3. No obvious plastic look

Over-denoising often creates:

- waxy surfaces;
- flat skin;
- melted texture;
- unnatural local uniformity.

## 4. No halos

Look around:

- high-contrast edges;
- bright specular highlights;
- object silhouettes.

## 5. The removed component is not a recognizable photograph

This is critical.

If `removed_component_x8.png` contains a clear copy of:

- the subject;
- object boundaries;
- meaningful texture;

reduce restoration strength.

---

# `run_presets.py`

Runs all three presets.

## Syntax

```text
python run_presets.py IMAGE
    [--output DIRECTORY]
    [--fast]
```

Example:

```bash
python run_presets.py frog.png \
  --output frog_presets \
  --fast
```

Creates:

```text
frog_presets/
├── conservative/
├── balanced/
├── aggressive/
├── preset_metrics.csv
└── preset_contact_sheet.jpg
```

---

# `preset_metrics.csv`

Makes numerical comparison easier.

Includes:

```text
preset
estimated_luma_sigma
rms_pixel_change
mean_absolute_pixel_change
ssim_vs_original
mean_cleanup_weight
p95_cleanup_weight
mean_change_smooth_regions
mean_change_textured_regions
smooth_to_texture_change_ratio
```

---

# `preset_contact_sheet.jpg`

Stacks:

```text
original
conservative
balanced
aggressive
```

for quick visual inspection.

Use the full-resolution PNG outputs for final evaluation.

---

# `periodic_residual_filter.py`

This is an advanced, manual tool for investigating **specific narrow-band periodic residual components**.

It intentionally does not perform automatic peak deletion.

## Syntax

```text
python periodic_residual_filter.py IMAGE
    [--output DIRECTORY]
    [--baseline-sigma FLOAT]
    [--notch dx,dy,radius,strength]
    [--max-blend FLOAT]
```

---

# Analysis-Only Example

```bash
python periodic_residual_filter.py \
  restored_balanced.png \
  --output periodic_scan
```

Without `--notch`, the script only performs a scan.

Outputs:

```text
spectral_candidates.csv
smooth_residual_fft.png
smooth_blend_mask.png
highpass_residual_x8.png
```

---

# `--baseline-sigma`

Default:

```text
6.0
```

The script constructs a smooth luminance baseline:

```text
base = GaussianBlur(L, sigma=baseline_sigma)
```

and residual:

```text
residual = L - base
```

A larger baseline sigma makes the residual contain progressively larger-scale detail.

---

# Smooth-Region Weighting

The periodic tool computes its own texture estimate and creates approximately:

```text
smooth = (1 - texture) ^ 4
```

This strongly favors smooth regions.

The spectral scan is performed on:

```text
residual × smooth mask
```

rather than on raw photograph luminance.

---

# Why Periodic Filtering Is Manual

A photograph may naturally contain strong periodic or quasi-periodic components.

Examples:

- fences;
- building windows;
- fabric;
- leaves;
- brick;
- stripes;
- ripples;
- repeated texture.

Therefore:

```text
strong FFT peak != artifact
```

The script requires explicit notch coordinates.

This preserves the separation between:

```text
candidate detection
```

and:

```text
destructive modification
```

---

# FFT Notch Coordinates

A notch is specified as:

```text
dx,dy,radius,strength
```

Example:

```bash
--notch 88,0,2,0.25
```

means:

```text
dx       = +88 frequency bins
dy       =   0 frequency bins
radius   =   2 bins
strength = 0.25
```

The conjugate counterpart:

```text
-88,0
```

is automatically inserted.

For a real-valued spatial image, conjugate symmetry must be respected.

---

# Strength

```text
0.0
```

means no suppression.

```text
1.0
```

means the center of the Gaussian notch is fully suppressed.

Intermediate values provide partial attenuation.

Example:

```bash
--notch 88,0,2,0.20
```

is much more conservative than:

```bash
--notch 88,0,2,1.00
```

---

# Radius

The radius controls spectral width.

A narrow notch:

```text
radius = 1–2
```

targets a small frequency neighborhood.

A wide notch removes more nearby frequencies and therefore carries much greater risk of destroying legitimate image structure.

In general:

> Increase depth before increasing width when the target frequency is well confirmed.

---

# Spatial Period Conversion

For an image width:

```text
W
```

an axis-aligned horizontal-frequency offset:

```text
dx
```

corresponds approximately to a spatial period:

\[
P_x=\frac{W}{|dx|}
\]

if:

```text
dy = 0
```

For image height:

```text
H
```

a vertical-frequency offset:

```text
dy
```

corresponds to:

\[
P_y=\frac{H}{|dy|}
\]

if:

```text
dx = 0
```

## Example

For:

```text
width = 2816
dx = 88
```

the horizontal spatial period is:

\[
2816/88=32
\]

pixels.

This is more precise than using a generic radial period estimate for an axis-aligned peak in a non-square image.

---

# Diagonal Frequency Components

For a diagonal peak:

```text
(dx, dy)
```

both axes matter.

The radial bin distance is:

\[
r=\sqrt{dx^2+dy^2}
\]

but a single "period" becomes less intuitive because the pattern has orientation.

Treat diagonal candidates more cautiously than clean axis-aligned peaks.

---

# Manual Periodic Artifact Workflow

## Step 1 — Start from the conservative restoration

Recommended:

```text
restored_balanced.png
```

rather than the unprocessed original.

The balanced stage has already reduced broad residual while preserving texture.

## Step 2 — Scan only

```bash
python periodic_residual_filter.py \
  restore/restored_balanced.png \
  --output periodic_scan
```

## Step 3 — Inspect candidates

Read:

```text
periodic_scan/spectral_candidates.csv
```

Open:

```text
periodic_scan/smooth_residual_fft.png
```

## Step 4 — Select one well-supported candidate

Prefer:

- isolated;
- symmetric;
- repeated across related analysis;
- supported by autocorrelation or shift-correlation;
- located in smooth-region residual;
- not obviously explained by scene geometry.

## Step 5 — Test weakly

Example:

```bash
python periodic_residual_filter.py \
  restore/restored_balanced.png \
  --output periodic_test \
  --notch 88,0,2,0.20 \
  --max-blend 0.60
```

## Step 6 — Inspect the removed component

Open:

```text
removed_periodic_component_x20.png
```

## Step 7 — Reject unsafe notches

Reject if the removed component contains recognizable:

- eyes;
- skin bumps;
- toes;
- moss;
- leaf edges;
- branches;
- object contours.

## Step 8 — Increase depth gradually

If the removed component is almost a pure periodic field, test:

```text
0.20
0.40
0.60
1.00
```

while keeping radius fixed.

## Step 9 — Re-run forensics on the restored output

This is crucial.

The current periodic script's:

```text
smooth_residual_fft.png
spectral_candidates.csv
```

are generated from the **pre-filter scan**.

They are not a post-filter verification.

Therefore run:

```bash
python photo_forensics.py \
  periodic_test/restored_manual_periodic.png \
  --output periodic_verify
```

Then compare the new metrics against the balanced input.

---

# Periodic Filter Outputs

When no notch is supplied:

```text
spectral_candidates.csv
smooth_residual_fft.png
smooth_blend_mask.png
highpass_residual_x8.png
```

When a notch is supplied:

```text
restored_manual_periodic.png
removed_periodic_component_x20.png
notch_mask.png
notches_used.txt
spectral_candidates.csv
smooth_residual_fft.png
smooth_blend_mask.png
```

---

# `smooth_blend_mask.png`

Bright:

```text
more of the filtered residual may be used
```

Dark:

```text
protect the original
```

Detailed objects should generally be dark.

---

# `smooth_residual_fft.png`

FFT of the **smooth-weighted residual before filtering**.

Important:

> This is not an after-filter spectrum.

Re-run `photo_forensics.py` on the result for post-filter verification.

---

# `spectral_candidates.csv`

Candidate FFT peaks from the smooth-weighted residual.

---

# `notch_mask.png`

Shows the multiplicative spectral filter.

White:

```text
frequency retained
```

Dark:

```text
frequency attenuated
```

Very small dark dots are expected for narrow notches.

---

# `notches_used.txt`

Records actual notch tuples after automatic conjugate-symmetric expansion.

Example:

```text
(88.0, 0.0, 2.0, 0.4)
(-88.0, -0.0, 2.0, 0.4)
```

---

# `removed_periodic_component_x20.png`

Visualizes the periodic residual component removed by the notch.

Gain:

```text
×20
```

Gray means approximately zero.

For a clean single-frequency removal, this may look like a low-amplitude sinusoidal stripe field.

This is a safety diagnostic.

---

# `restored_manual_periodic.png`

Final RGB8 result after:

1. filtering the luminance residual;
2. reconstructing luminance;
3. blending through the smooth-region mask;
4. converting LAB back to RGB;
5. rounding to 8-bit values.

---

# 8-bit Quantization and Sub-LSB Changes

This point is important.

The periodic filter operates internally in floating-point.

A mathematically valid correction may be smaller than one 8-bit intensity level.

Example:

```text
original 8-bit equivalent = 120.00
correction               = -0.23
new floating value       = 119.77
```

When rounded:

```text
round(119.77) = 120
```

the final RGB8 PNG remains unchanged at that pixel.

Therefore two different notch strengths can produce different floating-point residuals but the same final 8-bit image.

This is normal quantization behavior.

It does not mean the FFT filter calculation failed.

---

# Why `max-blend` Matters

The filtered luminance is blended through:

```text
blend = smooth_mask × max_blend
```

Default:

```text
0.65
```

Even a full-strength notch is not necessarily applied at full strength to every pixel.

In strongly textured regions:

```text
smooth ≈ 0
```

so the filtered component has little influence.

---

# `make_photo_controls.py`

Generates synthetic controls for forensic validation.

## Syntax

```text
python make_photo_controls.py
    [--output DIRECTORY]
    [--width INTEGER]
    [--height INTEGER]
    [--seed INTEGER]
```

Defaults:

```text
output = photo_controls
width  = 2048
height = 1117
seed   = 1337
```

Example:

```bash
python make_photo_controls.py \
  --output controls \
  --width 2816 \
  --height 1536 \
  --seed 1337
```

Match control dimensions to the photograph whenever possible.

---

# Synthetic Controls

## `gradient_rgb.png`

Clean deterministic RGB gradient.

Use as a smooth low-frequency negative control.

---

# `gradient_rgb_gaussian_sigma1.png`

The same gradient plus independent Gaussian noise with approximately:

```text
sigma = 1/255
```

per channel.

Use as a broadband stochastic-noise reference.

---

# `gradient_rgb_periodic_16x8.png`

Gradient plus known periodic contamination:

```text
16 px horizontal sinusoid
8 px vertical sinusoid
```

Use as a positive control for FFT periodic detection.

---

# `gradient_rgb_correlated_noise.png`

Gradient plus a common random field injected into RGB with channel scaling.

Use as a positive control for inter-channel residual correlation.

---

# `synthetic_bokeh_clean.png`

Deterministic smooth bokeh-like field built from Gaussian blobs.

Useful as a content-shape control for smooth photographic backgrounds.

---

# `synthetic_bokeh_gaussian_sigma1.png`

The bokeh-like control plus Gaussian noise.

Useful for testing smooth-region noise estimates.

---

# Control Workflow

Generate controls:

```bash
python make_photo_controls.py \
  --output controls \
  --width 2816 \
  --height 1536
```

Analyze clean bokeh:

```bash
python photo_forensics.py \
  controls/synthetic_bokeh_clean.png \
  --output control_bokeh_clean
```

Analyze noisy bokeh:

```bash
python photo_forensics.py \
  controls/synthetic_bokeh_gaussian_sigma1.png \
  --output control_bokeh_noise
```

Analyze periodic gradient:

```bash
python photo_forensics.py \
  controls/gradient_rgb_periodic_16x8.png \
  --output control_periodic
```

Then compare JSON metrics.

---

# `compare_photo_reports.py`

Combines multiple JSON reports into one CSV.

## Syntax

```text
python compare_photo_reports.py REPORT1 REPORT2 ...
    [--output FILE.csv]
```

Example:

```bash
python compare_photo_reports.py \
  frog_analysis/metrics.json \
  control_bokeh_clean/metrics.json \
  control_bokeh_noise/metrics.json \
  control_periodic/metrics.json \
  --output comparison.csv
```

The script recursively flattens dictionary values.

Lists are stored as JSON strings.

This makes the result convenient for:

- pandas;
- Excel;
- LibreOffice;
- R;
- Jupyter;
- statistical workflows.

---

# `quick_run.sh`

Convenience shell launcher.

## Usage

```bash
./quick_run.sh IMAGE [OUTPUT_DIRECTORY]
```

Example:

```bash
./quick_run.sh frog.png frog_results
```

Internally it runs approximately:

```bash
python run_photo_all.py IMAGE \
  --output OUTPUT \
  --preset balanced \
  --fast
```

If no active virtual environment is detected, it prints a warning and installation guidance.

---

# `presets.json`

Contains the restoration preset values in human-readable JSON.

It is useful for:

- documentation;
- experiments;
- external tooling;
- recording configuration.

The actual current preset dictionary is also defined inside `frog_restore.py`.

If modifying presets for research, record exactly which values were used.

---

# Example Frog Workflow

Assume:

```text
frog.png
```

## Stage 1 — Full analysis + balanced restoration

```bash
python run_photo_all.py frog.png \
  --output frog_results \
  --preset balanced \
  --fast
```

## Stage 2 — Inspect forensics

```bash
less frog_results/analysis/report.txt
```

Open:

```text
frog_results/analysis/texture_probability.png
frog_results/analysis/flat_probability.png
frog_results/analysis/flat_patch_fft.png
frog_results/analysis/flat_patch_autocorrelation.png
```

## Stage 3 — Inspect the restored image

Open:

```text
frog_results/restore/restored_balanced.png
```

## Stage 4 — Inspect what the denoiser removed

Open:

```text
frog_results/restore/removed_component_x8.png
```

## Stage 5 — Check adaptive masking

Open:

```text
frog_results/restore/texture_mask.png
frog_results/restore/cleanup_weight.png
```

A detailed frog and foreground should generally receive much less cleanup than a defocused background.

## Stage 6 — Scan remaining periodic residual

```bash
python periodic_residual_filter.py \
  frog_results/restore/restored_balanced.png \
  --output frog_periodic_scan
```

## Stage 7 — Read candidates

```bash
head -30 frog_periodic_scan/spectral_candidates.csv
```

## Stage 8 — Test one candidate conservatively

For a hypothetical confirmed peak:

```bash
python periodic_residual_filter.py \
  frog_results/restore/restored_balanced.png \
  --output frog_periodic_test \
  --notch 88,0,2,0.20 \
  --max-blend 0.60
```

## Stage 9 — Inspect removed periodic component

```text
frog_periodic_test/removed_periodic_component_x20.png
```

## Stage 10 — Verify after filtering

```bash
python photo_forensics.py \
  frog_periodic_test/restored_manual_periodic.png \
  --output frog_periodic_verify
```

Compare:

```text
frog_results/analysis/metrics.json
frog_periodic_verify/metrics.json
```

---

# Verification After Periodic Filtering

Do not rely on the original scan plot.

Re-run the analyzer.

Compare:

## FFT

```text
flat_patch_fft.png
spectral_peaks.csv
```

## Autocorrelation

```text
flat_patch_autocorrelation.png
```

## Shift correlation

```text
shift_correlations.csv
```

## Residual scale

```text
estimated_luma_highpass_sigma_0to1
```

## Channel correlation

```text
flat_residual_channel_correlation
```

## Texture preservation

Run `frog_restore.py` metrics and visually inspect the subject.

---

# Comparing Two Images Pixel by Pixel

Example:

```bash
python - <<'PY'
from PIL import Image
import numpy as np

a = np.asarray(
    Image.open("before.png").convert("RGB"),
    dtype=np.float64,
)

b = np.asarray(
    Image.open("after.png").convert("RGB"),
    dtype=np.float64,
)

d = b - a

print("Different pixels:", np.count_nonzero(np.any(d != 0, axis=2)))
print("RMS:", np.sqrt(np.mean(d*d)))
print("MAE:", np.mean(np.abs(d)))
print("Maximum absolute channel change:", np.max(np.abs(d)))
PY
```

This is useful when a correction is visually subtle.

---

# Performance and Runtime

The most expensive operations are generally:

- non-local means;
- large-image unique-color counting;
- repeated FFT patch analysis;
- wavelet transforms;
- local entropy;
- LZMA compression.

For fast iteration use:

```bash
--fast
```

on restoration.

---

# Memory Use

Large RGB arrays are stored as floating-point during restoration.

For a high-resolution image, several candidate arrays may coexist.

Expect noticeably higher memory use than the original PNG file size.

For example, an RGB float64 array requires approximately:

\[
W\times H\times3\times8
\]

bytes before additional working arrays.

---

# Reproducibility

Record:

```text
Python version
NumPy version
SciPy version
Pillow version
scikit-image version
PyWavelets version
OpenCV version
```

Command:

```bash
python - <<'PY'
import sys
import numpy, scipy, PIL, skimage, pywt, cv2

print("Python:", sys.version)
print("NumPy:", numpy.__version__)
print("SciPy:", scipy.__version__)
print("Pillow:", PIL.__version__)
print("scikit-image:", skimage.__version__)
print("PyWavelets:", pywt.__version__)
print("OpenCV:", cv2.__version__)
PY
```

Also record:

- original file hash;
- image dimensions;
- command line;
- preset;
- every overridden parameter.

Hash example:

```bash
sha256sum frog.png
```

---

# Experimental Directory Layout

Recommended:

```text
experiment/
├── originals/
│   └── frog.png
├── run_001/
│   ├── analysis/
│   └── restore/
├── periodic_scan/
├── periodic_test_020/
├── periodic_test_040/
├── periodic_test_100/
├── controls/
└── comparison/
```

This avoids accidentally overwriting earlier runs.

---

# Troubleshooting

## `externally-managed-environment`

Activate your virtual environment:

```bash
source .venv/bin/activate
```

---

# `ModuleNotFoundError: No module named 'skimage'`

Install:

```bash
python -m pip install scikit-image
```

or all requirements:

```bash
python -m pip install -r requirements.txt
```

---

# `ModuleNotFoundError: No module named 'pywt'`

Install:

```bash
python -m pip install PyWavelets
```

---

# Image path not found

If the file is in the same directory:

```bash
python run_photo_all.py frog.png
```

Check:

```bash
ls -l frog.png
```

---

# Very slow NLM

Use:

```bash
--fast
```

Example:

```bash
python frog_restore.py frog.png \
  --output fast \
  --preset balanced \
  --fast
```

---

# `flat_patch_fft.png` was not created

The photograph may not contain enough sufficiently smooth patches at the current settings.

Try:

```bash
python photo_forensics.py frog.png \
  --output relaxed \
  --patch 64 \
  --stride 32 \
  --flat-threshold 0.65
```

---

# Restoration looks too smooth

Use:

```bash
--preset conservative
```

or override:

```bash
--strength 0.35
```

and/or:

```bash
--texture-protection 0.95
```

---

# Background still looks noisy

Try the aggressive preset, but inspect the removed component:

```bash
python frog_restore.py frog.png \
  --output stronger \
  --preset aggressive \
  --fast
```

---

# Removed component contains real subject detail

Stop increasing strength.

Use:

```text
conservative
```

or raise texture protection.

---

# FFT peak remains after periodic filtering

Remember:

```text
smooth_residual_fft.png
```

inside the periodic tool is the **pre-filter scan**.

Run:

```bash
python photo_forensics.py restored_manual_periodic.png \
  --output verify
```

for a true post-filter measurement.

---

# Increasing notch strength does not change RGB8 output

This can happen because the floating-point correction remains below the 8-bit rounding threshold.

See:

[8-bit Quantization and Sub-LSB Changes](#8-bit-quantization-and-sub-lsb-changes)

---

# Interpretation Guide

## High channel entropy

Means the value distribution is diverse.

Does not prove naturalness.

---

# High joint RGB entropy

Means many RGB combinations occur.

Expected in complex photographs.

---

# High RGB residual correlation

Means high-pass fluctuations are shared across channels.

This argues against a model of completely independent channel noise.

It does not identify the source.

---

# High spectral entropy

Means FFT energy is broadly distributed.

A narrow periodic component can still exist on top of a high-entropy spectrum.

---

# Isolated symmetric FFT peaks

Potential periodic candidates.

Require:

- control comparison;
- scene interpretation;
- spatial-domain confirmation;
- removal-component inspection.

---

# Repeated peaks at harmonic frequencies

Can indicate:

- non-sinusoidal periodic structure;
- raster grid structure;
- legitimate repeated geometry;
- interpolation or processing.

Do not automatically notch all harmonics.

---

# Strong lag correlation at 1–4 pixels

Often indicates smooth/correlated residual.

---

# Local correlation peaks at specific larger lags

Potential periodic spacing.

Cross-check FFT.

---

# Smooth/textured change ratio > 1

Means the restoration changed smooth regions more than textured regions.

This is generally aligned with the intended design.

A very high value is not automatically better.

It may simply mean textured regions were almost untouched.

---

# SSIM close to 1

Means the restored image is structurally very similar to the original according to SSIM.

This is useful but insufficient.

A bad localized artifact can coexist with high global SSIM.

Always inspect output images.

---

# Common Mistakes

## Mistake 1 — Running FFT on the whole photograph and deleting the largest peaks

This can remove real scene geometry.

Use smooth-region residual analysis.

---

# Mistake 2 — Treating the high-pass residual as "noise"

High-pass residual includes legitimate fine texture.

---

# Mistake 3 — Choosing aggressive because it looks smoother

Smoothness is not equivalent to restoration quality.

---

# Mistake 4 — Increasing notch radius too quickly

A wide notch removes nearby legitimate frequencies.

Prefer a narrow radius and incremental depth.

---

# Mistake 5 — Adding every detected FFT candidate

Candidate detection is not artifact identification.

Test one at a time.

---

# Mistake 6 — Ignoring the removed-component visualization

This is one of the strongest safety checks available in the toolkit.

---

# Mistake 7 — Comparing metrics from images with different dimensions or parameters

FFT bins, patch statistics, and residual distributions may not be directly comparable.

Use matched settings.

---

# Mistake 8 — Interpreting one image as universal pipeline behavior

Use repeated independent samples and controls.

---

# Known Limitations

## No ground-truth original

The toolkit only sees the observed raster.

It cannot mathematically recover information that has already been irreversibly lost.

---

# Texture classification is heuristic

The texture map is based on:

- gradients;
- local variance;
- high-pass energy.

It is not semantic segmentation.

---

# NLM can be expensive

Especially on large photographs.

---

# TV can oversmooth

This is why it has a smaller ensemble weight.

---

# LAB conversion is not lossless under finite precision

Round-trip RGB/LAB/RGB can introduce tiny changes.

---

# Output is RGB8

The current restoration and periodic filter save standard 8-bit images.

Sub-LSB floating-point corrections can disappear during rounding.

---

# Periodic filter scan is pre-filter

The periodic tool does not automatically produce an after-filter FFT report.

Use `photo_forensics.py` for verification.

---

# No automatic periodic artifact classifier

This is intentional.

Automatically deciding that a frequency is "junk" can damage real photographs.

---

# Controls are synthetic

Mathematical controls help establish baseline behavior, but they do not perfectly reproduce every real camera or generative pipeline.

---

# Suggested Research Methodology

A strong experiment should include:

## 1. Multiple independent target images

Not just one photograph.

## 2. Same dimensions where possible

Especially for FFT comparisons.

## 3. Clean mathematical controls

Examples:

```text
clean gradient
clean bokeh
```

## 4. Noise positive controls

Examples:

```text
Gaussian noise
correlated channel noise
known periodic 8/16 px contamination
```

## 5. Identical analyzer settings

Keep:

```text
patch
stride
flat-threshold
max-lag
```

constant.

## 6. Independent evidence

A candidate period is more interesting if supported by:

- FFT;
- autocorrelation;
- shift correlation;
- repeated samples.

## 7. Removal validation

After a notch:

- inspect removed component;
- verify post-filter spectrum;
- compare pixel differences;
- confirm scene detail remains.

---

# Command Reference

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

---

# Quick full run

```bash
python run_photo_all.py frog.png \
  --output frog_results \
  --preset balanced \
  --fast
```

---

# Forensics only

```bash
python photo_forensics.py frog.png \
  --output frog_analysis
```

---

# Larger FFT patches

```bash
python photo_forensics.py frog.png \
  --output frog_fft256 \
  --patch 256 \
  --stride 128
```

---

# More permissive smooth patches

```bash
python photo_forensics.py frog.png \
  --output frog_relaxed \
  --flat-threshold 0.65
```

---

# Conservative restoration

```bash
python frog_restore.py frog.png \
  --output conservative \
  --preset conservative \
  --fast
```

---

# Balanced restoration

```bash
python frog_restore.py frog.png \
  --output balanced \
  --preset balanced \
  --fast
```

---

# Aggressive restoration

```bash
python frog_restore.py frog.png \
  --output aggressive \
  --preset aggressive \
  --fast
```

---

# Custom restoration

```bash
python frog_restore.py frog.png \
  --output custom \
  --preset balanced \
  --strength 0.55 \
  --texture-protection 0.90 \
  --detail-recovery 0.12 \
  --chroma-strength 0.75 \
  --fast
```

---

# Run all presets

```bash
python run_presets.py frog.png \
  --output preset_comparison \
  --fast
```

---

# Periodic scan only

```bash
python periodic_residual_filter.py \
  balanced/restored_balanced.png \
  --output periodic_scan
```

---

# Weak narrow periodic test

```bash
python periodic_residual_filter.py \
  balanced/restored_balanced.png \
  --output periodic_test_020 \
  --notch 88,0,2,0.20 \
  --max-blend 0.60
```

---

# Strong narrow periodic test

```bash
python periodic_residual_filter.py \
  balanced/restored_balanced.png \
  --output periodic_test_100 \
  --notch 88,0,2,1.00 \
  --max-blend 0.90
```

Only do this after the low-strength removed-component test indicates that the selected component does not contain recognizable scene detail.

---

# Verify filtered image

```bash
python photo_forensics.py \
  periodic_test_100/restored_manual_periodic.png \
  --output periodic_test_100_verify
```

---

# Generate photo controls

```bash
python make_photo_controls.py \
  --output controls \
  --width 2816 \
  --height 1536 \
  --seed 1337
```

---

# Analyze correlated-noise control

```bash
python photo_forensics.py \
  controls/gradient_rgb_correlated_noise.png \
  --output control_correlated
```

---

# Analyze periodic control

```bash
python photo_forensics.py \
  controls/gradient_rgb_periodic_16x8.png \
  --output control_periodic
```

---

# Compare JSON metrics

```bash
python compare_photo_reports.py \
  frog_analysis/metrics.json \
  control_correlated/metrics.json \
  control_periodic/metrics.json \
  --output comparison.csv
```

---

# Quick shell launcher

```bash
./quick_run.sh frog.png frog_results
```

---

# Recommended First-Time Sequence

If you do not know where to start, use exactly this sequence:

```bash
# 1. Activate environment
source .venv/bin/activate

# 2. Install
python -m pip install -r requirements.txt

# 3. Full balanced run
python run_photo_all.py frog.png \
  --output frog_results \
  --preset balanced \
  --fast

# 4. Compare all restoration presets
python run_presets.py frog.png \
  --output frog_presets \
  --fast

# 5. Scan the balanced output for periodic residual candidates
python periodic_residual_filter.py \
  frog_results/restore/restored_balanced.png \
  --output periodic_scan
```

At this point, **stop and inspect the data** before applying any notch.

---

# Final Notes

Frog Photo Lab is deliberately conservative.

The difficult part of photographic restoration is not finding something that can be smoothed.

The difficult part is deciding:

> **What can be changed without destroying real information?**

The toolkit therefore emphasizes:

- smooth-region analysis;
- multiple independent statistics;
- conservative adaptive blending;
- removed-component inspection;
- matched controls;
- manual verification of narrow periodic candidates.

A successful restoration is not the image with the smallest residual.

It is the image that removes a defensible amount of unwanted raster structure while preserving the photographic information that matters.

🐸🔬📷
