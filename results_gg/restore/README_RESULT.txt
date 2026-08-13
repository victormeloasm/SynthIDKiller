Inspect otsu_binary_rgb.png and fixed127_binary_rgb.png first.
They contain only exact 0/255 pixels.
Use *_sdf_aa.png if visually smooth edges matter more than literal 2-color pixels.
TV can damage the finest stripes; treat tv_otsu as an alternate candidate, not ground truth.
