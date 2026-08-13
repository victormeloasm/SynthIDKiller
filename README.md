# Pattern Lab Toolkit 🐸🔬
## Raster Pattern Forensics, Entropy Analysis, FFT Residual Inspection, and Binary Image Restoration

Pattern Lab Toolkit is a small research-oriented Python toolkit for studying raster images that are
**expected to have simple, clean structure** but contain unexpected gray levels, chromatic deviations,
periodic microtexture, banding, correlated residuals, or other processing artifacts.

The toolkit was designed around a particularly useful forensic case:

> An image is visually intended to be black and white, but the stored raster contains thousands of
> RGB values and large regions of intermediate gray.

Instead of treating every high-frequency component as noise, Pattern Lab first builds an **inferred
binary model**, separates the observed image into **intended structure + residual**, excludes pixels
near strong black/white boundaries where normal rasterization can dominate, and then analyzes the
remaining residual using several independent measurements:

- Shannon entropy
- conditional entropy
- neighbor mutual information
- phase-conditioned mutual information
- permutation-bias correction
- FFT power spectra
- spectral entropy
- autocorrelation
- shift correlation
- radial and angular spectral profiles
- GLCM texture statistics
- wavelet energy
- zlib/LZMA compressibility
- binary-distance statistics

It also includes multiple restoration candidates for images that truly are supposed to contain only
black and white.

---

# Table of Contents

1. [Important Scope and Assumptions](#important-scope-and-assumptions)
2. [Repository Layout](#repository-layout)
3. [Requirements](#requirements)
4. [Installation](#installation)
5. [Quick Start](#quick-start)
6. [Recommended Scientific Workflow](#recommended-scientific-workflow)
7. [`run_all.py`](#run_allpy)
8. [`pattern_lab.py`](#pattern_labpy)
9. [Understanding the Forensic Metrics](#understanding-the-forensic-metrics)
10. [Understanding `pattern_lab.py` Outputs](#understanding-pattern_labpy-outputs)
11. [`binary_restore.py`](#binary_restorepy)
12. [Exact Binary vs. Antialiased Restoration](#exact-binary-vs-antialiased-restoration)
13. [`fft_residual_tool.py`](#fft_residual_toolpy)
14. [How to Read FFT Coordinates and Spatial Periods](#how-to-read-fft-coordinates-and-spatial-periods)
15. [How to Test a Manual FFT Notch Safely](#how-to-test-a-manual-fft-notch-safely)
16. [`make_controls.py`](#make_controlspy)
17. [`compare_reports.py`](#compare_reportspy)
18. [Example Workflow for `gg.png`](#example-workflow-for-ggpng)
19. [How to Verify That a Restored Image Is Truly Binary](#how-to-verify-that-a-restored-image-is-truly-binary)
20. [How to Interpret Common Result Patterns](#how-to-interpret-common-result-patterns)
21. [Controls and Experimental Design](#controls-and-experimental-design)
22. [Colored Images and Gradients](#colored-images-and-gradients)
23. [Troubleshooting](#troubleshooting)
24. [Performance Notes](#performance-notes)
25. [Reproducibility](#reproducibility)
26. [Limitations](#limitations)
27. [Suggested Repository Workflow](#suggested-repository-workflow)
28. [Command Cheat Sheet](#command-cheat-sheet)

---

# Important Scope and Assumptions

## What this toolkit is good at

Pattern Lab is especially useful for:

- black/white optical patterns;
- line art;
- thresholded graphics;
- test charts;
- synthetic binary images;
- flat-color diagnostic images;
- smooth gradient controls;
- images where you know what the legal output levels should be;
- images where you want to quantify unexpected raster structure.

The restoration code is strongest when the intended image is genuinely binary.

For example, if the intended signal is:

```text
black = [0, 0, 0]
white = [255, 255, 255]
```

but the actual image contains values such as:

```text
[1, 1, 1]
[253, 254, 253]
[98, 98, 99]
[187, 186, 188]
```

then the toolkit can measure those deviations and reconstruct a clean binary candidate.

## What this toolkit is NOT

This toolkit is **not a provenance classifier** and does not claim that a spectral peak, entropy anomaly,
or periodic residual is a particular watermark or provenance signal.

A repeated pattern can come from many sources:

- resampling;
- decoder architecture;
- upscaling;
- quantization;
- rasterization;
- antialiasing;
- interpolation;
- compression;
- synthetic test geometry;
- generator-specific image processing;
- ordinary post-processing.

A single FFT peak is not enough to identify the cause.

The correct scientific approach is comparison against controls and multiple independent images.

## Critical FFT warning

Never automatically remove strong FFT peaks from the original image just because they are strong.

For optical patterns, spirals, stripes, gratings, checkerboards, and line art, the **real image content is
itself periodic**.

Pattern Lab therefore tries to analyze:

```text
residual = observed image - inferred binary model
```

rather than blindly filtering the original raster.

---

# Repository Layout

The package contains:

```text
pattern_lab_toolkit/
├── README.md
├── requirements.txt
├── run_all.py
├── pattern_lab.py
├── binary_restore.py
├── fft_residual_tool.py
├── make_controls.py
├── compare_reports.py
├── GG_QUICK_NOTES.txt
└── gg_example_outputs/
    ├── otsu_binary_rgb.png
    ├── otsu_1bit.png
    ├── otsu_sdf_aa.png
    ├── otsu_ambiguity_map.png
    ├── restore_metrics.json
    └── thresholds.png
```

## File summary

| File | Purpose |
|---|---|
| `run_all.py` | Runs the main analysis, restoration, and residual FFT scan in one command |
| `pattern_lab.py` | Comprehensive forensic analysis |
| `binary_restore.py` | Generates binary restoration candidates |
| `fft_residual_tool.py` | Analyzes and optionally filters selected frequencies in the binary residual |
| `make_controls.py` | Generates mathematical control images |
| `compare_reports.py` | Combines multiple `metrics.json` files into one comparison CSV |
| `requirements.txt` | Python dependencies |
| `GG_QUICK_NOTES.txt` | Notes from the original example image |
| `gg_example_outputs/` | Example restoration outputs |

---

# Requirements

The toolkit uses:

```text
numpy
scipy
Pillow
matplotlib
scikit-image
PyWavelets
```

The supplied `requirements.txt` can install them all.

A recent CPython version is recommended.

The toolkit has been designed to work with modern Python environments, including systems where the
distribution protects the system interpreter under **PEP 668**.

---

# Installation

## Recommended: use a virtual environment

Do not install the dependencies into the operating system Python if your distribution marks it as an
externally managed environment.

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Upgrade `pip`:

```bash
python -m pip install --upgrade pip
```

Install the dependencies:

```bash
python -m pip install -r requirements.txt
```

Verify the environment:

```bash
python -c "import numpy, scipy, PIL, matplotlib, skimage, pywt; print('Pattern Lab dependencies OK')"
```

Check which interpreter is active:

```bash
which python
```

It should point into the virtual environment, for example:

```text
/home/user/project/.venv/bin/python
```

and not:

```text
/usr/bin/python
```

## If Ubuntu/Debian reports `externally-managed-environment`

That means you are probably outside the virtual environment.

Activate it again:

```bash
source .venv/bin/activate
```

Then:

```bash
python -m pip install -r requirements.txt
```

Avoid using:

```text
--break-system-packages
```

unless you deliberately intend to modify the system Python environment.

---

# Quick Start

Assume the image is called:

```text
gg.png
```

and is in the same directory as the scripts.

Run everything:

```bash
python run_all.py gg.png --output results_gg
```

The result tree will look approximately like:

```text
results_gg/
├── analysis/
│   ├── report.txt
│   ├── metrics.json
│   ├── binary_model.png
│   ├── binary_residual_x4.png
│   ├── binary_residual_heatmap.png
│   ├── luminance_histogram.png
│   ├── distance_to_binary_histogram.png
│   ├── local_artifact_entropy.png
│   ├── flat_residual_fft.png
│   ├── flat_residual_autocorrelation.png
│   ├── spectral_peaks.csv
│   ├── shift_correlations.csv
│   ├── phase_entropy.csv
│   ├── phase_entropy_scan.png
│   ├── radial_power.csv
│   ├── angular_power.csv
│   ├── angular_power.png
│   └── wavelet_energy.csv
├── restore/
│   ├── fixed127_binary_rgb.png
│   ├── fixed127_1bit.png
│   ├── fixed127_sdf_aa.png
│   ├── fixed127_difference_x2.png
│   ├── otsu_binary_rgb.png
│   ├── otsu_1bit.png
│   ├── otsu_sdf_aa.png
│   ├── otsu_difference_x2.png
│   ├── li_binary_rgb.png
│   ├── yen_binary_rgb.png
│   ├── tv_otsu_binary_rgb.png
│   ├── otsu_ambiguity_map.png
│   ├── thresholds.png
│   ├── restore_metrics.json
│   └── README_RESULT.txt
└── fft_residual/
    ├── residual_fft_before.png
    ├── residual_spectral_candidates.csv
    └── edge_safe_residual_x4.png
```

If no manual notch is supplied, `fft_residual_tool.py` performs analysis only.

---

# Recommended Scientific Workflow

A reliable workflow is:

## Step 1 — Inspect the source image

Before filtering anything, ask:

- Is the image supposed to be binary?
- Are intermediate gray levels legitimate?
- Is antialiasing expected?
- Are there gradients?
- Is the content itself periodic?
- Are there thin features near one pixel wide?

If the image is not truly binary, do **not** blindly use binary restoration.

## Step 2 — Run forensic analysis

```bash
python pattern_lab.py gg.png --output gg_analysis
```

Start with:

```text
gg_analysis/report.txt
gg_analysis/metrics.json
gg_analysis/luminance_histogram.png
gg_analysis/distance_to_binary_histogram.png
gg_analysis/binary_residual_heatmap.png
```

## Step 3 — Generate restoration candidates

```bash
python binary_restore.py gg.png --output gg_restore --mode all
```

Compare:

```text
otsu_binary_rgb.png
fixed127_binary_rgb.png
tv_otsu_binary_rgb.png
li_binary_rgb.png
yen_binary_rgb.png
```

For a clean black/white test image, Otsu and fixed 127.5 are usually the first two to compare.

## Step 4 — Inspect the residual FFT

```bash
python fft_residual_tool.py gg.png --output gg_fft
```

This does not modify the image.

Inspect:

```text
gg_fft/residual_fft_before.png
gg_fft/residual_spectral_candidates.csv
gg_fft/edge_safe_residual_x4.png
```

## Step 5 — Run controls

```bash
python make_controls.py --output controls --width 2048 --height 1117
```

Then analyze the controls using the exact same parameters.

## Step 6 — Compare metrics

```bash
python compare_reports.py \
  gg_analysis/metrics.json \
  control_spiral_analysis/metrics.json \
  control_periodic_analysis/metrics.json \
  --output comparison.csv
```

A result becomes much more meaningful when it differs from mathematical controls in a repeatable way.

---

# `run_all.py`

`run_all.py` is the convenience wrapper.

## Usage

```bash
python run_all.py IMAGE --output OUTPUT_DIRECTORY
```

Example:

```bash
python run_all.py gg.png --output results_gg
```

## Arguments

### Positional argument: `image`

Input image path.

Examples:

```bash
python run_all.py gg.png
```

or:

```bash
python run_all.py /home/user/images/test.png
```

### `--output`

Root output directory.

Default:

```text
pattern_lab_results
```

Example:

```bash
python run_all.py gg.png --output experiment_01
```

## What it runs

Internally, the wrapper executes:

```bash
python pattern_lab.py IMAGE --output OUTPUT/analysis
python binary_restore.py IMAGE --output OUTPUT/restore --mode all
python fft_residual_tool.py IMAGE --output OUTPUT/fft_residual
```

It deliberately does **not** automatically apply FFT notches.

---

# `pattern_lab.py`

This is the main forensic analyzer.

## Basic usage

```bash
python pattern_lab.py gg.png --output gg_analysis
```

## Full command-line interface

```text
python pattern_lab.py IMAGE
    [--output DIR]
    [--edge-margin FLOAT]
    [--residual-step FLOAT]
    [--max-period INTEGER]
    [--mi-sample INTEGER]
    [--mi-shuffles INTEGER]
    [--patch INTEGER]
    [--stride INTEGER]
```

---

## `--output`

Output directory.

Default:

```text
pattern_analysis
```

Example:

```bash
python pattern_lab.py gg.png --output run_001
```

---

## `--edge-margin`

Default:

```text
3.0
```

Controls how far a pixel must be from an inferred binary edge before it is considered part of a
relatively flat interior.

Example:

```bash
python pattern_lab.py gg.png \
  --output margin5 \
  --edge-margin 5
```

### Why this matters

Pixels near black/white boundaries naturally contain:

- rasterization errors;
- antialiasing;
- subpixel geometry;
- interpolation;
- edge ringing.

If these pixels dominate the residual analysis, the toolkit can mistake legitimate edge behavior for a
global texture pattern.

A larger margin is more conservative but leaves fewer pixels for analysis.

Typical values:

```text
2–3 px   permissive
4–6 px   conservative
8+ px    only for large, thick patterns
```

For extremely thin stripes, a large margin can eliminate nearly all valid flat pixels.

---

## `--residual-step`

Default:

```text
1.0
```

Controls the quantization step used when converting the floating-point residual into discrete symbols
for entropy calculations.

Example:

```bash
python pattern_lab.py gg.png \
  --residual-step 0.5
```

Smaller values:

- preserve smaller residual differences;
- create more symbols;
- usually increase entropy;
- require more samples for stable mutual-information estimates.

Larger values:

- merge nearby residual levels;
- reduce sensitivity to sub-level differences;
- can improve statistical stability.

Suggested tests:

```text
0.5
1.0
2.0
```

If a pattern appears only at one very specific quantization step, treat it cautiously.

---

## `--max-period`

Default:

```text
64
```

Maximum candidate spatial period tested in the phase-conditioned entropy scan.

Example:

```bash
python pattern_lab.py gg.png \
  --max-period 128
```

The scan evaluates candidate periods:

```text
2, 3, 4, ..., max_period
```

For each candidate period `p`, the pixel is assigned a phase:

```text
phase = (y mod p, x mod p)
```

The code then asks:

> Does knowing this phase reduce uncertainty about the residual?

This is useful for testing repeated pixel-grid structure.

---

## `--mi-sample`

Default:

```text
250000
```

Maximum number of residual pixels sampled for phase mutual-information calculations.

Example:

```bash
python pattern_lab.py gg.png \
  --mi-sample 500000
```

Larger samples improve statistical stability but increase runtime.

---

## `--mi-shuffles`

Default:

```text
3
```

Number of random permutations used to estimate finite-sample mutual-information bias.

Example:

```bash
python pattern_lab.py gg.png \
  --mi-shuffles 10
```

For exploratory work:

```text
3
```

is fast.

For more serious comparison:

```text
10–30
```

is preferable, especially if runtime is acceptable.

The corrected score is approximately:

```text
corrected MI = observed MI - permutation bias
```

This is much safer than interpreting raw mutual information by itself.

---

## `--patch`

Default:

```text
128
```

Preferred FFT patch size.

Example:

```bash
python pattern_lab.py gg.png \
  --patch 256
```

Larger patches:

- give finer frequency resolution;
- require larger flat regions;
- can fail on dense optical patterns.

Smaller patches:

- work better in dense patterns;
- have poorer frequency resolution;
- provide more local measurements.

The code automatically falls back to smaller/more permissive patch settings if the requested patch size
cannot find enough edge-safe regions.

---

## `--stride`

Default:

```text
64
```

Distance between neighboring FFT patch origins.

Smaller stride:

- more overlap;
- more patches;
- greater runtime.

Larger stride:

- faster;
- less redundant sampling.

Example:

```bash
python pattern_lab.py gg.png \
  --patch 128 \
  --stride 32
```

---

# Understanding the Forensic Metrics

This section is the conceptual core of the toolkit.

---

## Exact black and exact white fractions

For each pixel:

```text
exact black = RGB == [0, 0, 0]
exact white = RGB == [255, 255, 255]
```

If an image is supposed to be binary but only a small fraction of pixels are exact black or white, that
is immediately useful information.

Example:

```text
Exact black:     23%
Exact white:     14%
Non-binary:      63%
```

That does **not** prove malicious or hidden structure.

It proves only that the stored raster is not actually a two-color raster.

---

## Number of distinct RGB colors

A true binary RGB image should contain exactly:

```text
2 distinct RGB values
```

typically:

```text
[0, 0, 0]
[255, 255, 255]
```

If a visually black/white image contains thousands of RGB colors, most of those values are intermediate
raster levels.

---

## Chroma spread

For each pixel:

```text
chroma_spread = max(R,G,B) - min(R,G,B)
```

Interpretation:

```text
0       exact grayscale
1–3     tiny channel deviation
large   meaningful chromatic difference
```

If an image contains many non-binary pixels but very small chroma spread, the contamination is mostly
gray rather than strongly colored.

---

## Distance to the nearest legal binary level

For luminance `Y`:

```text
distance = min(Y, 255 - Y)
```

Examples:

```text
Y = 0    -> distance 0
Y = 2    -> distance 2
Y = 127  -> distance 127
Y = 253  -> distance 2
Y = 255  -> distance 0
```

Useful statistics include:

- mean;
- median;
- P90;
- P99.

A low median but high P99 means most pixels are close to legal black/white levels, while a smaller subset
contains substantial intermediate values.

---

## Shannon entropy

For discrete values:

\[
H(X)=-\sum_x p(x)\log_2 p(x)
\]

The toolkit calculates entropy for:

- R;
- G;
- B;
- luminance;
- quantized residual.

Important:

**Higher entropy does not automatically mean more natural.**

A perfectly random noise image can have very high entropy.

A smooth real sky can have relatively low entropy.

Entropy should be interpreted together with spatial structure.

---

## Joint RGB entropy

Instead of treating R/G/B independently, each complete RGB triplet is treated as one symbol.

This measures diversity of actual stored colors.

A binary image has very low joint RGB entropy compared with an image containing thousands of possible
triplets.

---

## Residual entropy

For a binary-intended image:

```text
ideal(x,y) = 0 or 255
residual(x,y) = observed_luminance(x,y) - ideal(x,y)
```

The residual is then quantized.

Residual entropy answers:

> How many bits are required, on average, to describe the residual symbol distribution?

It still does not measure spatial predictability by itself.

That is why the next metrics matter.

---

## Conditional entropy between neighboring pixels

The toolkit measures approximately:

\[
H(X_{n+1}\mid X_n)
\]

for horizontal and vertical neighbors.

If neighboring residual pixels strongly predict each other, conditional entropy falls.

This helps distinguish:

```text
independent pixel noise
```

from:

```text
smooth / correlated / structured residual
```

---

## Neighbor mutual information

Mutual information measures how much knowing one residual pixel tells us about its neighbor.

Conceptually:

\[
I(X;Y)=H(X)+H(Y)-H(X,Y)
\]

Higher neighbor MI means stronger spatial dependence.

If vertical MI is much larger than horizontal MI, the residual may contain directional structure.

---

## Phase-conditioned mutual information

For candidate period `p`:

```text
phase_x = x mod p
phase_y = y mod p
```

The toolkit evaluates whether the residual depends on that repeating phase.

If the same positions inside every `p × p` tile tend to contain similar residual behavior, mutual
information rises.

Example pattern:

```text
period 7  -> low corrected MI
period 8  -> high corrected MI
period 9  -> low corrected MI
```

This is more interesting than a monotonically increasing score.

---

## Why permutation bias correction exists

Mutual information is biased upward when:

- sample count is finite;
- symbol count is large;
- phase count grows with period.

Without correction, large periods can appear artificially impressive simply because they contain more
phase states.

The toolkit randomly permutes phase assignments and estimates the MI expected by chance.

The reported corrected quantity is:

```text
bias-corrected MI = observed MI - null/permutation MI
```

This is one of the most important safeguards in the package.

---

## FFT power spectrum

The 2D Fourier transform decomposes a spatial image into spatial frequencies.

The power spectrum is:

\[
P(u,v)=|F(u,v)|^2
\]

The toolkit analyzes the **residual**, not simply the original optical pattern.

Strong isolated peaks can indicate repeated periodic structure.

But FFT peaks can also be generated by:

- legitimate content;
- sharp edges;
- windowing;
- masks;
- interpolation;
- patch dimensions.

Always compare against controls.

---

## Spectral entropy

After normalizing the FFT power distribution:

\[
p_i=\frac{P_i}{\sum_j P_j}
\]

spectral entropy is computed from the distribution.

The toolkit normalizes the result so that values closer to `1` mean energy is relatively spread across
many frequency bins.

Rough intuition:

```text
near 1.0   broadly distributed spectrum
lower      energy concentrated in fewer frequencies
```

Do not use a universal threshold.

Compare images processed with the same dimensions and parameters.

---

## Autocorrelation

Autocorrelation asks:

> If I shift the residual by some displacement, how similar is it to itself?

Repeated patterns produce repeated peaks or ridges.

Autocorrelation is useful because it expresses periodicity directly in spatial displacement rather than
frequency bins.

---

## Shift correlations

The toolkit measures correlation for horizontal and vertical shifts:

```text
1 px
2 px
3 px
...
max_period px
```

A result such as:

```text
lag 1:  0.95
lag 2:  0.90
lag 4:  0.75
lag 8:  0.45
```

usually suggests a strongly spatially correlated residual.

A localized rise at a specific lag can be evidence of periodic repetition.

---

## Radial power profile

The FFT is averaged by distance from the spectrum center.

This reduces the 2D spectrum to:

```text
frequency radius -> average power
```

Useful for separating:

- low-frequency residual;
- mid-frequency structure;
- high-frequency energy.

---

## Angular power profile

FFT power is grouped by orientation.

This measures anisotropy.

For example, a residual dominated by horizontal line artifacts can create a strong directional spectral
signature.

File:

```text
angular_power.csv
```

Plot:

```text
angular_power.png
```

---

## GLCM texture statistics

The residual is quantized and a Gray-Level Co-occurrence Matrix is calculated.

Metrics include:

```text
contrast
dissimilarity
homogeneity
ASM
energy
correlation
```

These should mainly be used for **comparison between images processed identically**.

Absolute values are much less meaningful than controlled differences.

---

## Wavelet energy

If PyWavelets is available, the toolkit decomposes the residual across scales using a 2D wavelet
transform.

It reports energy in:

```text
approximation
horizontal details
vertical details
diagonal details
```

at multiple scales.

This can help identify whether residual energy is concentrated in:

- fine detail;
- medium-scale texture;
- directional features;
- large smooth deviations.

---

## Compression ratio

The toolkit compresses raw bytes with:

```text
zlib
LZMA
```

and reports:

```text
compressed size / raw size
```

Smaller ratio:

```text
more compressible / more repetitive
```

Larger ratio:

```text
less compressible
```

Again, compression is not a standalone detector.

A mathematically regular image is naturally highly compressible.

---

# Understanding `pattern_lab.py` Outputs

## `report.txt`

Human-readable summary.

Start here.

It includes:

- resolution;
- number of distinct RGB values;
- Otsu threshold;
- exact black/white fractions;
- non-binary fraction;
- grayscale statistics;
- distance to legal binary levels;
- entropy results;
- compression;
- strongest corrected phase periods;
- strongest FFT peaks;
- GLCM results.

---

## `metrics.json`

Machine-readable version of many core statistics.

Use this for:

- automated experiments;
- batch processing;
- notebooks;
- regression testing;
- `compare_reports.py`.

---

## `binary_model.png`

The inferred black/white structure created using Otsu thresholding.

This is not necessarily the final restoration recommendation, but it is the model used for residual
analysis.

---

## `binary_residual_x4.png`

Visualizes:

```text
observed luminance - inferred binary model
```

with gain applied.

Mid-gray represents approximately zero residual.

Deviations away from mid-gray show differences between the stored raster and the inferred binary signal.

---

## `binary_residual_heatmap.png`

Continuous heatmap of the same residual.

Useful for spotting:

- broad gray regions;
- directional artifacts;
- localized corruption;
- edge-associated residuals;
- smooth generator variation.

---

## `luminance_histogram.png`

Histogram of image luminance with Otsu threshold marked.

For a strongly binary image, two major modes near black and white are expected.

---

## `distance_to_binary_histogram.png`

Histogram of:

```text
min(Y, 255-Y)
```

A clean binary file has all mass at zero.

A file with antialiasing has a small tail.

A heavily non-binary file can have substantial mass far from zero.

---

## `local_artifact_entropy.png`

Local entropy of the distance-to-binary field.

This highlights regions where the amount of non-binary contamination changes locally.

It is not ordinary image entropy; it is focused on binary deviation.

---

## `flat_residual_fft.png`

FFT of residual information from regions selected to avoid strong inferred binary edges.

This is one of the most important spectral outputs.

Do not compare its absolute brightness by eye between unrelated runs.

Use peak locations and numerical results.

---

## `flat_residual_autocorrelation.png`

Average residual autocorrelation.

Look for:

- repeated peaks;
- horizontal/vertical ridges;
- regular spacing;
- strong central anisotropy.

---

## `spectral_peaks.csv`

Columns:

```text
rank
dx
dy
power
approx_period_px
```

`dx` and `dy` are offsets from the FFT center.

`approx_period_px` is an approximate spatial period associated with the radial frequency.

Use it as a candidate generator, not as proof.

---

## `shift_correlations.csv`

Columns:

```text
lag_px
horizontal_corr
vertical_corr
```

Useful for identifying directional correlation and repeated spatial scales.

---

## `phase_entropy.csv`

Columns:

```text
period_px
observed_MI_bits
permutation_bias_bits
bias_corrected_MI_bits
corrected_MI_over_residual_entropy
```

The most useful column is usually:

```text
bias_corrected_MI_bits
```

and its normalized form:

```text
corrected_MI_over_residual_entropy
```

Look for local peaks, especially when the same candidate period appears in multiple independent images
but not in appropriate controls.

---

## `phase_entropy_scan.png`

Visual representation of:

- observed MI;
- permutation bias;
- corrected MI.

This makes it easier to see whether a candidate period genuinely rises above the statistical baseline.

---

## `radial_power.csv`

Average FFT power as a function of radial frequency bin.

---

## `angular_power.csv`

Average FFT power as a function of orientation.

---

## `angular_power.png`

Visualization of spectral anisotropy.

---

## `wavelet_energy.csv`

Present when PyWavelets is available.

Columns:

```text
band
scale
energy
energy_fraction
```

Useful primarily for comparative experiments.

---

# `binary_restore.py`

This is the main restoration tool for images that are genuinely supposed to contain only black and
white.

## Basic usage

```bash
python binary_restore.py gg.png \
  --output gg_restore \
  --mode all
```

## Full command interface

```text
python binary_restore.py IMAGE
    [--output DIR]
    [--mode all|otsu|fixed|tv]
    [--fixed-threshold FLOAT]
    [--aa-width FLOAT]
    [--tv-weight FLOAT]
    [--median-size INTEGER]
```

---

## `--mode all`

Runs all supported restoration candidates:

```text
fixed threshold
Otsu
Li
Yen
TV denoise + Otsu
```

Example:

```bash
python binary_restore.py gg.png \
  --output gg_restore \
  --mode all
```

Recommended for initial analysis.

---

## `--mode otsu`

Only the Otsu candidate:

```bash
python binary_restore.py gg.png \
  --output gg_final \
  --mode otsu
```

For the example binary optical image, this is a strong default.

---

## `--mode fixed`

Uses the fixed threshold:

```text
127.5
```

unless overridden.

Example:

```bash
python binary_restore.py gg.png \
  --output fixed_run \
  --mode fixed
```

Custom threshold:

```bash
python binary_restore.py gg.png \
  --output fixed_run \
  --mode fixed \
  --fixed-threshold 130
```

---

## `--mode tv`

Applies conservative total-variation denoising before Otsu thresholding.

Example:

```bash
python binary_restore.py gg.png \
  --output tv_run \
  --mode tv
```

TV can remove smooth noise but can also alter very thin stripes.

It should be treated as an alternate candidate, not automatically as ground truth.

---

## `--fixed-threshold`

Default:

```text
127.5
```

Values:

```text
Y <= threshold -> black
Y > threshold  -> white
```

For an ideal symmetric black/white signal, 127.5 is the exact midpoint.

---

## `--aa-width`

Default:

```text
0.85
```

Controls the width of the signed-distance antialiasing transition.

This affects only the `*_sdf_aa.png` outputs.

Smaller:

```text
sharper edge
```

Larger:

```text
softer antialiased edge
```

Example:

```bash
python binary_restore.py gg.png \
  --output aa_test \
  --mode otsu \
  --aa-width 1.25
```

---

## `--tv-weight`

Default:

```text
0.035
```

TV denoise strength in normalized 0–1 units.

Higher values smooth more aggressively.

For thin optical patterns, aggressive TV can deform the intended geometry.

Use conservative values.

---

## `--median-size`

Default:

```text
0
```

Disabled by default.

Example:

```bash
python binary_restore.py gg.png \
  --output median_test \
  --mode all \
  --median-size 3
```

A median filter can help impulse noise, but it can also damage one-pixel or very thin stripe features.

Do not enable it automatically for dense optical patterns.

---

# Restoration Outputs

For each threshold method `METHOD`, the script can generate:

```text
METHOD_binary_rgb.png
METHOD_1bit.png
METHOD_sdf_aa.png
METHOD_difference_x2.png
```

Examples:

```text
otsu_binary_rgb.png
otsu_1bit.png
otsu_sdf_aa.png
otsu_difference_x2.png
```

---

## `*_binary_rgb.png`

RGB PNG containing only:

```text
[0,0,0]
[255,255,255]
```

This is convenient for software that expects RGB images.

---

## `*_1bit.png`

Literal one-bit image representation.

This is the strictest binary output.

Use it when the scientific requirement is:

> There must be exactly two pixel states.

---

## `*_sdf_aa.png`

Signed-distance antialiased rendering.

It preserves black/white interiors but introduces intermediate gray around boundaries to create smoother
visual curves.

This is meant for visual presentation, not literal two-level analysis.

---

## `*_difference_x2.png`

Visualizes how much the original luminance differs from the chosen binary reconstruction.

Useful for detecting whether thresholding is changing only uncertain edge regions or large interior
structures.

---

## `otsu_ambiguity_map.png`

Bright regions are closer to the Otsu decision boundary and therefore less confidently classified.

Dark regions are strongly black or strongly white.

If ambiguity is concentrated around edges, thresholding is usually stable.

If large flat interiors are bright, the image may not really be binary.

---

## `thresholds.png`

Displays the luminance histogram and the threshold chosen by each method.

This makes Otsu, Li, Yen, fixed threshold, and TV+Otsu easy to compare.

---

## `restore_metrics.json`

Machine-readable restoration summary.

Contains:

- thresholds;
- white fraction;
- black fraction;
- mean absolute projection change;
- P95 projection change;
- TV parameters.

---

# Exact Binary vs. Antialiased Restoration

At fixed raster resolution, you cannot have both:

1. mathematically subpixel-smooth edges;
2. only the exact pixel values `0` and `255`.

An antialiased edge represents partial pixel coverage using intermediate values.

Therefore choose according to purpose.

## Scientific / binary analysis

Use:

```text
otsu_1bit.png
```

or:

```text
otsu_binary_rgb.png
```

## Visual presentation

Use:

```text
otsu_sdf_aa.png
```

This will contain gray values near boundaries.

That is intentional.

---

# `fft_residual_tool.py`

This tool analyzes and optionally filters selected frequencies in the **binary-model residual**.

It does not automatically decide that detected spectral peaks are artifacts.

That distinction is deliberate.

## Scan only

```bash
python fft_residual_tool.py gg.png \
  --output gg_fft
```

Outputs:

```text
residual_fft_before.png
residual_spectral_candidates.csv
edge_safe_residual_x4.png
```

No filtering is performed.

---

## Full command interface

```text
python fft_residual_tool.py IMAGE
    [--output DIR]
    [--notch dx,dy,radius,strength]
    [--edge-margin FLOAT]
    [--gain FLOAT]
```

---

## `--edge-margin`

Default:

```text
3.0
```

Same general purpose as in `pattern_lab.py`: exclude residual near inferred binary boundaries.

---

## `--gain`

Default:

```text
20.0
```

Visualization gain for:

```text
removed_residual_component_x20.png
```

This affects the diagnostic visualization, not the mathematical filtering strength.

---

## `--notch`

Manual Gaussian notch specification:

```text
dx,dy,radius,strength
```

Example:

```bash
python fft_residual_tool.py gg.png \
  --output fft_test \
  --notch 64,0,2,0.35
```

The symmetric counterpart is automatically included.

So:

```text
+64, 0
```

also causes:

```text
-64, 0
```

to be filtered.

This is required for a real-valued spatial reconstruction.

---

# How to Read FFT Coordinates and Spatial Periods

For an image dimension `N`, a frequency offset of approximately `k` bins corresponds to a spatial period
of roughly:

\[
P \approx \frac{N}{k}
\]

for a purely axis-aligned component.

Example:

```text
N = 1024
k = 64
```

then:

\[
P = 1024/64 = 16 \text{ pixels}
\]

For a two-dimensional offset:

```text
(dx, dy)
```

the radial frequency is approximately:

\[
r=\sqrt{dx^2+dy^2}
\]

and the toolkit reports:

\[
P \approx \frac{\min(H,W)}{r}
\]

as a convenient approximate period.

This is useful for ranking candidates, but directional components should still be inspected using `dx`
and `dy`.

---

# How to Test a Manual FFT Notch Safely

## Step 1 — Scan

```bash
python fft_residual_tool.py gg.png \
  --output gg_fft_scan
```

Inspect:

```text
gg_fft_scan/residual_spectral_candidates.csv
```

Suppose a candidate appears at:

```text
dx=64
dy=0
```

## Step 2 — Apply a weak, narrow test

```bash
python fft_residual_tool.py gg.png \
  --output gg_fft_test \
  --notch 64,0,2,0.25
```

Parameters:

```text
dx       64
dy        0
radius    2
strength  0.25
```

## Step 3 — Inspect the removed component

Open:

```text
gg_fft_test/removed_residual_component_x20.png
```

Reject the notch if it contains recognizable legitimate structure such as:

- spiral boundaries;
- stripe shapes;
- subject contours;
- meaningful line detail.

## Step 4 — Compare before and after

Inspect:

```text
residual_fft_before.png
residual_fft_after.png
notch_mask.png
```

A useful notch should reduce the selected residual peak without visibly damaging legitimate image
structure.

## Step 5 — Increase gradually if justified

For example:

```bash
--notch 64,0,2,0.35
```

then:

```bash
--notch 64,0,2,0.45
```

Do not begin with a wide, full-strength notch unless you have a very strong reason.

---

# FFT Filter Outputs

When one or more notches are supplied:

```text
restored_binary_rgb.png
restored_1bit.png
removed_residual_component_x20.png
notch_mask.png
residual_fft_after.png
notches_used.txt
```

## Important design detail

After filtering the residual, the script reconstructs:

```text
binary model + filtered residual
```

and then projects the result back to exact black/white.

Therefore the final restoration remains binary.

---

# `make_controls.py`

This tool generates mathematical controls with known structure.

Controls are essential for serious interpretation.

## Usage

```bash
python make_controls.py \
  --output controls \
  --width 2048 \
  --height 1117
```

## Arguments

### `--output`

Default:

```text
controls
```

### `--width`

Default:

```text
2048
```

### `--height`

Default:

```text
1117
```

### `--seed`

Default:

```text
1337
```

Controls random-number generation for reproducibility.

---

# Generated Controls

## `control_binary_split.png`

One half black, one half white.

Useful for studying:

- clean binary entropy;
- a single large edge;
- edge-mask behavior.

---

## `control_checker_16.png`

Mathematically exact 16-pixel checkerboard.

Useful as a positive control for known periodicity.

A correct FFT/phase pipeline should be able to detect strong regular structure associated with this
geometry.

---

## `control_gradient.png`

Smooth mathematical 8-bit gradient.

Useful for measuring:

- quantization effects;
- entropy of deterministic smooth images;
- behavior of spectral analysis on non-binary content.

---

## `control_gradient_gaussian_sigma1.png`

Gradient plus independent Gaussian noise.

Useful as a reference for:

```text
broadband stochastic noise
```

rather than periodic structure.

---

## `control_gradient_periodic_16x8.png`

Gradient plus explicit sinusoidal contamination:

```text
16 px horizontal component
8 px vertical component
```

This is an important positive control for periodic residual detection.

---

## `control_binary_radial_chirp.png`

Binary radial chirp.

Useful because it contains legitimate frequency-varying periodic geometry.

This demonstrates why FFT peaks from the original content cannot automatically be labeled artifacts.

---

## `control_binary_spiral.png`

Mathematically generated binary spiral-like field.

This is one of the most relevant controls for an optical spiral image.

---

# `compare_reports.py`

Combines multiple `metrics.json` files into a single CSV.

## Usage

```bash
python compare_reports.py \
  run1/metrics.json \
  run2/metrics.json \
  run3/metrics.json \
  --output comparison.csv
```

Example:

```bash
python compare_reports.py \
  results_gg/analysis/metrics.json \
  control_spiral_analysis/metrics.json \
  control_periodic_analysis/metrics.json \
  --output comparison.csv
```

## Why this matters

Human visual inspection is useful, but controlled numerical comparison is stronger.

The comparison CSV can reveal:

- unusually high residual entropy;
- unusually low spectral entropy;
- stronger neighbor correlation;
- stronger compression;
- different chromatic spread;
- different binary-distance statistics;
- different accepted FFT-patch behavior.

Open the CSV in:

- LibreOffice Calc;
- Excel;
- pandas;
- R;
- Jupyter;
- any statistical workflow.

---

# Example Workflow for `gg.png`

Assume:

```text
gg.png
```

is in the current directory.

## 1. Activate the virtual environment

```bash
source .venv/bin/activate
```

or use the correct absolute path to your environment:

```bash
source /home/user/project/.venv/bin/activate
```

Verify:

```bash
which python
```

## 2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

## 3. Run all tools

```bash
python run_all.py gg.png --output results_gg
```

## 4. Read the report

```bash
less results_gg/analysis/report.txt
```

## 5. Inspect the binary candidates

Start with:

```text
results_gg/restore/otsu_binary_rgb.png
results_gg/restore/fixed127_binary_rgb.png
```

If both are almost identical, classification is stable around the midpoint.

## 6. Inspect uncertainty

```text
results_gg/restore/otsu_ambiguity_map.png
```

Ideally, high ambiguity should mainly occur around boundaries.

## 7. Inspect the residual

```text
results_gg/analysis/binary_residual_heatmap.png
results_gg/analysis/binary_residual_x4.png
```

## 8. Inspect frequency structure

```text
results_gg/analysis/flat_residual_fft.png
results_gg/analysis/flat_residual_autocorrelation.png
results_gg/analysis/spectral_peaks.csv
results_gg/analysis/phase_entropy.csv
```

## 9. Verify the clean result

Use:

```text
results_gg/restore/otsu_binary_rgb.png
```

for normal RGB compatibility.

Use:

```text
results_gg/restore/otsu_1bit.png
```

for strict one-bit storage.

---

# How to Verify That a Restored Image Is Truly Binary

Run:

```bash
python - <<'PY'
from PIL import Image
import numpy as np

a = np.array(Image.open("results_gg/restore/otsu_binary_rgb.png").convert("RGB"))

colors = np.unique(a.reshape(-1, 3), axis=0)

print("Distinct colors:", len(colors))
print(colors)
PY
```

Expected output:

```text
Distinct colors: 2
[[  0   0   0]
 [255 255 255]]
```

That is a definitive raster-level check.

Do not rely only on what an image viewer displays.

A viewer may:

- rescale the image;
- antialias it;
- interpolate it;
- display gray pixels on screen even when the underlying PNG is binary.

---

# How to Compare Two Binary Reconstructions Pixel by Pixel

Example: compare Otsu vs fixed 127.5.

```bash
python - <<'PY'
from PIL import Image
import numpy as np

a = np.array(Image.open("results_gg/restore/otsu_binary_rgb.png").convert("L"))
b = np.array(Image.open("results_gg/restore/fixed127_binary_rgb.png").convert("L"))

different = np.count_nonzero(a != b)
total = a.size

print("Different pixels:", different)
print("Fraction:", different / total)
print("Percent:", 100 * different / total)
PY
```

If only a tiny fraction differs, the classification is robust to small threshold changes.

---

# How to Interpret Common Result Patterns

## Case A — High non-binary fraction, but almost all pixels are grayscale

Likely interpretation:

- intermediate gray values dominate;
- chromatic contamination is small;
- antialiasing / interpolation / generative raster variation may be involved.

Check:

```text
chroma_spread_mean
exact_grayscale_fraction
distance_to_binary histogram
```

---

## Case B — Very high neighbor MI and high shift correlation at small lags

Likely interpretation:

The residual is spatially correlated.

This is not independent Gaussian-like pixel noise.

Possible causes include:

- smooth shading;
- blur;
- low-frequency reconstruction error;
- correlated generative texture;
- interpolation.

---

## Case C — Strong corrected MI at one or several periods

Example:

```text
7 px   low
8 px   high
9 px   low
```

Interesting evidence for grid-phase dependence.

Before interpreting it:

1. run mathematical controls;
2. repeat on multiple independent images;
3. change crop or image dimensions when possible;
4. check FFT/autocorrelation;
5. confirm that the peak survives permutation correction.

---

## Case D — Corrected MI slowly increases with period

Be cautious.

This can indicate:

- residual statistical bias;
- under-corrected finite-sample effects;
- broad structure rather than a true tile;
- insufficient sampling.

Do not call it a periodic fingerprint from that result alone.

---

## Case E — Strong FFT peak but weak phase MI

Possible explanations:

- sinusoidal structure whose phase varies spatially;
- content-dependent texture;
- non-stationary artifact;
- directional pattern;
- edge leakage.

FFT and phase analysis test different properties.

---

## Case F — Strong phase MI but no obvious FFT spike

Possible explanations:

- repeated non-sinusoidal tile structure;
- weak periodic modulation spread over harmonics;
- local periodicity that averages out in the global spectrum.

---

## Case G — Low spectral entropy

Energy is concentrated in relatively few frequency bins.

This can indicate strong periodic structure.

But a synthetic optical pattern can naturally have low spectral entropy.

Always analyze the residual and use controls.

---

## Case H — High spectral entropy but periodic candidates still exist

This means the residual is broadly distributed but still contains measurable structured components.

A few periodic components do not need to dominate the total residual energy.

---

## Case I — Restoration changes only edge-adjacent pixels

This is usually a good sign for a genuinely binary image.

It suggests that thresholding mainly resolves:

- antialiasing;
- uncertain border pixels;
- gray interpolation.

---

## Case J — Restoration changes large flat interiors

Investigate carefully.

Possible explanations:

- the image is not actually binary;
- threshold is inappropriate;
- broad shading is part of the intended content;
- the inferred model is wrong.

---

# Controls and Experimental Design

For meaningful forensic conclusions, do not analyze only one image.

A useful experiment includes:

## Negative control

Mathematically exact image with no unexplained raster contamination.

Example:

```text
control_binary_spiral.png
```

## Broadband-noise control

Example:

```text
control_gradient_gaussian_sigma1.png
```

## Periodic positive control

Example:

```text
control_gradient_periodic_16x8.png
```

## Content-matched control

A mathematical image with geometry similar to the subject.

Example:

```text
control_binary_spiral.png
```

## Repeated samples

Generate or acquire several independent images from the same pipeline.

If a suspected period is real and pipeline-related, ask:

- Does its frequency recur?
- Does its phase recur?
- Is the amplitude stable?
- Is it color-dependent?
- Does it survive changes in content?
- Does it survive changes in crop?
- Does it survive resizing?
- Is it absent from mathematical controls?

A robust conclusion should not rely on one image.

---

# Suggested Multi-Run Experiment

Create controls:

```bash
python make_controls.py \
  --output controls \
  --width 2048 \
  --height 1117
```

Analyze the subject:

```bash
python pattern_lab.py gg.png \
  --output subject_analysis \
  --mi-shuffles 10
```

Analyze the spiral control:

```bash
python pattern_lab.py controls/control_binary_spiral.png \
  --output control_spiral_analysis \
  --mi-shuffles 10
```

Analyze the explicit periodic control:

```bash
python pattern_lab.py controls/control_gradient_periodic_16x8.png \
  --output control_periodic_analysis \
  --mi-shuffles 10
```

Analyze Gaussian noise control:

```bash
python pattern_lab.py controls/control_gradient_gaussian_sigma1.png \
  --output control_noise_analysis \
  --mi-shuffles 10
```

Compare:

```bash
python compare_reports.py \
  subject_analysis/metrics.json \
  control_spiral_analysis/metrics.json \
  control_periodic_analysis/metrics.json \
  control_noise_analysis/metrics.json \
  --output experiment_comparison.csv
```

Then compare the detailed CSVs separately:

```text
phase_entropy.csv
spectral_peaks.csv
shift_correlations.csv
wavelet_energy.csv
```

---

# Colored Images and Gradients

This version of the toolkit is **binary-model-oriented**.

That distinction is important.

## What can still be useful on color images

General measurements such as:

- RGB entropy;
- joint RGB entropy;
- compression;
- some spectral analysis;
- control generation;

can still be informative.

However, the core residual model in `pattern_lab.py` is:

```text
observed luminance - inferred black/white image
```

That is not an appropriate physical model for an ordinary photograph or arbitrary full-color artwork.

## Do NOT use `binary_restore.py` on a normal photograph

It will intentionally destroy color and tonal information.

`binary_restore.py` is for images where black/white is the expected signal.

## Smooth gradients

For gradient research, use mathematical gradient controls and a dedicated smooth-baseline residual
analysis rather than binary thresholding.

## Flat-color images

A future color restoration pipeline should ideally:

1. convert RGB to a perceptually useful color space such as Lab;
2. detect flat regions;
3. estimate dominant palette clusters;
4. analyze residual per channel;
5. preserve boundaries;
6. reconstruct colors without flattening legitimate gradients.

That functionality is not implemented in this package yet.

---

# Troubleshooting

## Error: `externally-managed-environment`

Example:

```text
error: externally-managed-environment
```

Cause:

You are using the distribution-managed system Python.

Fix:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Check:

```bash
which python
```

---

## Error: `ModuleNotFoundError: No module named 'skimage'`

Install dependencies inside the active environment:

```bash
python -m pip install -r requirements.txt
```

or specifically:

```bash
python -m pip install scikit-image
```

Verify:

```bash
python -c "import skimage; print(skimage.__version__)"
```

---

## Error: `No module named 'pywt'`

Install:

```bash
python -m pip install PyWavelets
```

---

## Error: input image not found

If `gg.png` is in the same directory:

```bash
python run_all.py gg.png --output results_gg
```

Do not literally type:

```text
/caminho/para/gg.png
```

unless that is an actual path on your system.

Check:

```bash
ls -l gg.png
```

or:

```bash
realpath gg.png
```

---

## Analysis is slow

Reduce:

```text
--mi-sample
--mi-shuffles
--max-period
```

Example fast exploratory run:

```bash
python pattern_lab.py gg.png \
  --output fast_run \
  --mi-sample 100000 \
  --mi-shuffles 2 \
  --max-period 32
```

---

## I want a more statistically stable phase scan

Increase shuffles:

```bash
python pattern_lab.py gg.png \
  --output serious_run \
  --mi-shuffles 20
```

You can also increase the sample size:

```bash
--mi-sample 500000
```

---

## FFT patch analysis finds too few patches

Dense line art can leave very little edge-safe interior.

The analyzer already has fallback behavior.

You can also try:

```bash
--patch 64
--stride 32
--edge-margin 2
```

Example:

```bash
python pattern_lab.py gg.png \
  --output dense_test \
  --patch 64 \
  --stride 32 \
  --edge-margin 2
```

Reducing the edge margin increases coverage but also increases the risk that normal boundary behavior
enters the residual statistics.

---

## The restored image looks gray in my viewer

Check the actual stored pixels.

Viewers may interpolate while zooming.

Run:

```bash
python - <<'PY'
from PIL import Image
import numpy as np

a=np.array(Image.open("otsu_binary_rgb.png").convert("RGB"))
print(np.unique(a.reshape(-1,3),axis=0))
PY
```

If the result is:

```text
[[  0   0   0]
 [255 255 255]]
```

the file itself is clean.

---

## SDF output contains gray pixels

That is expected.

The SDF version is antialiased for visual smoothness.

Use:

```text
*_binary_rgb.png
```

or:

```text
*_1bit.png
```

for strict binary output.

---

## A manual notch removes real line structure

Reject that notch.

The removed-component visualization exists specifically to catch this problem.

A frequency peak is not automatically noise.

---

# Performance Notes

The expensive operations are mainly:

- phase mutual-information scans;
- repeated permutation bias estimates;
- FFT patch aggregation;
- wavelet analysis;
- GLCM;
- large image unique-color calculations.

For large images, exploratory settings can use:

```bash
--mi-sample 100000
--mi-shuffles 2
--max-period 32
```

For final comparison, use higher settings and keep them identical across all images.

---

# Reproducibility

The control generator uses:

```text
--seed 1337
```

by default.

Keep these constant across comparative experiments:

- image dimensions;
- `--edge-margin`;
- `--residual-step`;
- `--max-period`;
- `--mi-sample`;
- `--mi-shuffles`;
- `--patch`;
- `--stride`.

Changing parameters between samples can make numerical comparison misleading.

Record:

```text
Python version
NumPy version
SciPy version
scikit-image version
Pillow version
PyWavelets version
```

Example:

```bash
python - <<'PY'
import sys
import numpy
import scipy
import PIL
import skimage
import pywt

print("Python:", sys.version)
print("NumPy:", numpy.__version__)
print("SciPy:", scipy.__version__)
print("Pillow:", PIL.__version__)
print("scikit-image:", skimage.__version__)
print("PyWavelets:", pywt.__version__)
PY
```

For a publication-quality experiment, save this output with the result set.

---

# Limitations

## The binary model is an assumption

If the intended image contains legitimate gray levels, the inferred binary residual is not a valid
content/noise separation.

## Otsu does not understand semantics

It optimizes a histogram-based threshold.

It does not know what a line, object, face, or symbol is.

## FFT is global or patch-global

Non-stationary artifacts can be difficult to characterize with one spectrum.

## Entropy is content-dependent

Never compare entropy values from radically different images without controls.

## Mutual information depends on discretization

`--residual-step` affects symbolization.

Compare identical settings.

## Masks and windows affect spectra

Even edge-safe residual analysis can produce spectral structure because of:

- masking;
- patch boundaries;
- Hann windows;
- finite image size.

Controls are essential.

## Compression is not a detector

Compressibility is influenced by legitimate structure.

Treat it as one measurement among many.

---

# Suggested Repository Workflow

A clean repository structure might be:

```text
repo/
├── README.md
├── requirements.txt
├── tools/
│   ├── pattern_lab.py
│   ├── binary_restore.py
│   ├── fft_residual_tool.py
│   ├── make_controls.py
│   └── compare_reports.py
├── examples/
│   ├── gg.png
│   └── gg_example_outputs/
├── experiments/
│   ├── run_001/
│   ├── run_002/
│   └── controls/
└── docs/
    └── methodology.md
```

If keeping the current flat layout, that is completely fine; the above is only a suggestion for a
larger repository.

---

# Command Cheat Sheet

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Everything

```bash
python run_all.py gg.png --output results_gg
```

## Forensic analysis only

```bash
python pattern_lab.py gg.png --output gg_analysis
```

## More robust phase MI run

```bash
python pattern_lab.py gg.png \
  --output gg_analysis_robust \
  --mi-shuffles 20 \
  --mi-sample 500000
```

## All binary restoration candidates

```bash
python binary_restore.py gg.png \
  --output gg_restore \
  --mode all
```

## Otsu restoration only

```bash
python binary_restore.py gg.png \
  --output gg_final \
  --mode otsu
```

## Strict final binary file

Use:

```text
gg_final/otsu_1bit.png
```

or RGB-compatible:

```text
gg_final/otsu_binary_rgb.png
```

## FFT residual scan

```bash
python fft_residual_tool.py gg.png \
  --output gg_fft_scan
```

## Weak manual notch test

```bash
python fft_residual_tool.py gg.png \
  --output gg_fft_test \
  --notch 64,0,2,0.25
```

## Generate controls

```bash
python make_controls.py \
  --output controls \
  --width 2048 \
  --height 1117
```

## Analyze mathematical spiral

```bash
python pattern_lab.py \
  controls/control_binary_spiral.png \
  --output control_spiral_analysis
```

## Analyze explicit periodic control

```bash
python pattern_lab.py \
  controls/control_gradient_periodic_16x8.png \
  --output control_periodic_analysis
```

## Compare experiment metrics

```bash
python compare_reports.py \
  results_gg/analysis/metrics.json \
  control_spiral_analysis/metrics.json \
  control_periodic_analysis/metrics.json \
  --output comparison.csv
```

## Verify binary output

```bash
python - <<'PY'
from PIL import Image
import numpy as np

a=np.array(Image.open("results_gg/restore/otsu_binary_rgb.png").convert("RGB"))
colors=np.unique(a.reshape(-1,3),axis=0)

print("Distinct colors:",len(colors))
print(colors)
PY
```

Expected:

```text
Distinct colors: 2
[[  0   0   0]
 [255 255 255]]
```

---

# Practical Interpretation Checklist

Before drawing a conclusion from an image, ask:

- [ ] Is the binary assumption actually valid?
- [ ] How many distinct RGB values are present?
- [ ] What fraction is exact black/white?
- [ ] Is the deviation mostly grayscale or chromatic?
- [ ] Are suspicious residuals inside flat regions or only near edges?
- [ ] Is residual neighbor MI high?
- [ ] Are horizontal and vertical dependencies different?
- [ ] Does the FFT show isolated residual peaks?
- [ ] Does autocorrelation support the same period?
- [ ] Does phase-conditioned MI support the same period?
- [ ] Does the period survive permutation-bias correction?
- [ ] Does it recur across independent images?
- [ ] Is it absent or weaker in mathematical controls?
- [ ] Does changing the crop destroy the effect?
- [ ] Does changing `--residual-step` destroy the effect?
- [ ] Is the effect just a harmonic of known content geometry?
- [ ] Does a proposed notch remove recognizable content?
- [ ] Do Otsu and fixed 127.5 agree closely?
- [ ] Does the strict restored PNG contain exactly two RGB values?

The more independent tests agree, the stronger the conclusion.

---

# Final Notes

Pattern Lab is intentionally conservative about interpretation.

Its job is to answer questions such as:

> Is this visually binary image actually binary at the raster level?

> Where are the intermediate values?

> Are residuals concentrated around boundaries or inside flat regions?

> Are residuals spatially correlated?

> Is there measurable periodic structure?

> Does a candidate period survive bias correction?

> Does the same structure exist in mathematical controls?

> Can the image be reconstructed as an exact two-state raster without unstable threshold decisions?

The toolkit is most useful when the answer comes from **several measurements agreeing**, rather than
from one dramatic-looking FFT image.

For a genuinely black/white source, the cleanest restoration is often not an aggressive frequency
filter at all. Once the two classes are robustly separable, exact binary projection can remove every
intermediate RGB value while preserving the inferred black/white structure.

🐸🔬
