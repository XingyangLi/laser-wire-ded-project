#!/usr/bin/env python3
"""Radiograph next to a calibration y-projection, centerline slice and iso-surface.

    python3 make_comparison.py cal08
    python3 make_comparison.py cal32 results/calibration/taosun03
writes <dir>/<tag>_vs_radiograph.png from the three figure files in that
directory. The radiograph is read from the same directory, or from this
script's directory when the figures live in a subdirectory.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

here = Path(__file__).resolve().parent
root = here
if len(sys.argv) > 2:
    root = Path(sys.argv[2]).expanduser().resolve()
tag = sys.argv[1] if len(sys.argv) > 1 else "cal03b"
radio_path = root / "radiograph.png"
if not radio_path.is_file():
    radio_path = here / "radiograph.png"
radio = mpimg.imread(radio_path)
proj = mpimg.imread(root / f"{tag}_projection.png")
iso = mpimg.imread(root / f"{tag}_iso_alpha.png")
side = mpimg.imread(root / f"{tag}_side_alpha_T.png")

fig, ax = plt.subplots(2, 2, figsize=(12.5, 9.0))
ax[0, 0].imshow(radio, cmap="gray")
ax[0, 0].set_title("Radiograph (trailing side on the left)")
ax[0, 1].imshow(proj)
ax[0, 1].set_title(f"{tag}, metal summed along y")
ax[1, 0].imshow(side)
ax[1, 0].set_title("Centerline slice, alpha and T")
ax[1, 1].imshow(iso)
ax[1, 1].set_title("alpha.metal = 0.5")
for a in ax.ravel():
    a.axis("off")
fig.tight_layout()
dest = root / f"{tag}_vs_radiograph.png"
fig.savefig(dest, dpi=140, bbox_inches="tight")
print("wrote", dest)
