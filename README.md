# Pattern Lab Toolkit 🐸🔬

A forensic + restoration toolkit for images that are *supposed* to have simple, clean raster structure
(e.g. pure black/white optical patterns, flat gradients, test charts) but contain gray/chromatic
microtexture, banding, periodic raster artifacts, or generator/decoder noise.

This toolkit is for **image-quality restoration and forensic measurement**. It does not identify or
remove provenance/watermark systems. The FFT tools work on the residual relative to an inferred
binary model so that the intended spiral/stripe content is not treated as "noise".

## Install

You said you are already inside a `.venv`, so:

```bash
python -m pip install -r requirements.txt
```

## One-command run

```bash
python run_all.py gg.png --output results_gg
```

That runs:

1. `pattern_lab.py` — broad forensic analysis
2. `binary_restore.py` — several black/white restoration candidates
3. `fft_residual_tool.py` — FFT scan of the residual, analysis-only unless you explicitly give notches

## The most important point for a black/white optical image

Do **not** automatically notch the FFT of the original image.

The spiral/stripe pattern itself is highly periodic and therefore produces strong spectral peaks.
Blindly deleting those peaks can destroy the actual picture.

Instead:

1. infer the intended 2-class black/white model;
2. form a residual `R = observed - inferred_binary`;
3. keep a safety band around black/white edges out of the "flat-area" statistics;
4. analyze FFT, entropy, phase periodicity, autocorrelation and compression on that residual;
5. use exact binary reconstruction for the cleanest 2-color result;
6. use SDF antialiasing if you prefer visually smoother curves at the cost of introducing gray pixels
   only along boundaries.

## Files

### `pattern_lab.py`

Measures:

- exact black / exact white / non-binary pixel fractions
- number of distinct RGB values
- grayscale/chroma deviation
- distance to nearest legal binary color
- Shannon entropy R/G/B/luma
- joint RGB entropy
- residual entropy
- horizontal and vertical conditional entropy
- neighbor mutual information
- local entropy map
- zlib and LZMA compressibility
- FFT power spectrum on edge-safe residual patches
- spectral entropy
- strong FFT peak candidates
- autocorrelation
- horizontal/vertical shift correlations
- phase-conditioned entropy for periods 2..64
- permutation-bias-corrected phase mutual information
- radial power profile
- angular anisotropy profile
- GLCM texture statistics on a quantized residual
- wavelet energy by scale (when PyWavelets is installed)
- edge-distance / flat-interior masks

### `binary_restore.py`

Produces several cleaning candidates:

- fixed 127.5 threshold
- Otsu threshold
- Li threshold
- Yen threshold
- optional TV-denoise + Otsu
- exact RGB black/white output
- literal 1-bit PNG output
- SDF-antialiased output: exact black/white interiors, gray only in a narrow edge band
- ambiguity map and difference visualization

For this kind of image, **Otsu / 127.5 are the first candidates to inspect**.

### `fft_residual_tool.py`

Computes an FFT on the **binary-model residual**, not on the original spiral.

First scan only:

```bash
python fft_residual_tool.py gg.png --output fft_scan
```

If you have confirmed a residual-frequency artifact and want to test a narrow restoration notch:

```bash
python fft_residual_tool.py gg.png \
  --output fft_test \
  --notch 64,0,2,0.35
```

Format:

```text
dx,dy,radius,strength
```

The conjugate-symmetric notch is inserted automatically.

Always inspect `removed_residual_component_x20.png`. If it contains recognizable spiral/edge structure,
the notch is attacking legitimate content and should be rejected.

## Recommended workflow for `gg.png`

```bash
python pattern_lab.py gg.png --output gg_analysis

python binary_restore.py gg.png \
  --output gg_restore \
  --mode all

python fft_residual_tool.py gg.png \
  --output gg_fft_residual
```

Then compare:

```text
gg_restore/otsu_binary_rgb.png
gg_restore/fixed127_binary_rgb.png
gg_restore/otsu_sdf_aa.png
gg_restore/tv_otsu_binary_rgb.png
```

### Exact 2-color vs visually smooth

A same-resolution raster cannot simultaneously have mathematically smooth subpixel boundaries and only
two pixel values. If every pixel must be exactly black or white, edges are necessarily pixel-quantized.

- `*_binary_rgb.png` / `*_1bit.png`: literally only black and white.
- `*_sdf_aa.png`: smoother-looking boundaries; gray exists only in a narrow antialiasing band.

For scientific analysis, use the exact binary version.
For visual presentation, the SDF-antialiased version is often nicer.

## Compare multiple images

The real power comes from running *identical parameters* on controls:

- generated image
- mathematically generated black/white control
- real photograph
- control + Gaussian noise
- multiple independent generations of the same prompt

Do not infer a specific source or watermark solely from one FFT peak or one entropy number.


## Mathematical controls

Generate controls matching the uploaded image dimensions:

```bash
python make_controls.py --output controls --width 2048 --height 1117
```

Then run the exact same analyzer on them, e.g.:

```bash
python pattern_lab.py controls/control_binary_spiral.png --output control_spiral_analysis
python pattern_lab.py controls/control_gradient_periodic_16x8.png --output control_periodic_analysis
```

Compare metrics:

```bash
python compare_reports.py \
  results_gg/analysis/metrics.json \
  control_spiral_analysis/metrics.json \
  control_periodic_analysis/metrics.json \
  --output comparison.csv
```

This is the cleanest way to distinguish:
- geometry/content-induced FFT structure,
- ordinary raster/quantization effects,
- deliberately injected periodic contamination,
- and image-specific residual structure.
