#!/usr/bin/env python3
"""Radiograph next to the cal03 y-projection and iso-surface."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

root = Path("/home/xingyang/laser-wire-ded-project/results/calibration")
radio = mpimg.imread(root / "radiograph.png")
proj = mpimg.imread(root / "cal03b_projection.png")
iso = mpimg.imread(root / "cal03b_iso_alpha.png")
side = mpimg.imread(root / "cal03b_side_alpha_T.png")

fig, ax = plt.subplots(2, 2, figsize=(12.5, 9.0))
ax[0, 0].imshow(radio, cmap="gray")
ax[0, 0].set_title("Radiograph (trailing side on the left)")
ax[0, 1].imshow(proj)
ax[0, 1].set_title("cal03 at 0.70 s, metal summed along y")
ax[1, 0].imshow(side)
ax[1, 0].set_title("Centerline slice, alpha and T")
ax[1, 1].imshow(iso)
ax[1, 1].set_title("alpha.metal = 0.5")
for a in ax.ravel():
    a.axis("off")
fig.tight_layout()
dest = root / "cal03b_vs_radiograph.png"
fig.savefig(dest, dpi=140, bbox_inches="tight")
print("wrote", dest)
