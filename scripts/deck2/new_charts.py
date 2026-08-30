# -*- coding: utf-8 -*-
"""Three new deck figures, built only from numbers already stated on their slides.

Palette matches src/lff/plots.py so they sit alongside the notebook figures.
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path("/home/dsi/giladaviv/london_flip_finder")
OUT = ROOT / "figures"
ACCENT, DEEP, MUTED, GRID = "#2a78d6", "#104281", "#5a6675", "#dee4ea"
ORANGE = "#eb6834"
S = 1.85
for k, b in (("font.size", 10), ("axes.titlesize", 12), ("axes.labelsize", 10),
             ("xtick.labelsize", 9), ("ytick.labelsize", 9), ("legend.fontsize", 9)):
    plt.rcParams[k] = b * S
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["axes.edgecolor"] = GRID
plt.rcParams["axes.grid"] = False

# ---------------------------------------------------------------- slide 8: cleaning funnel
fig, ax = plt.subplots(figsize=(11, 4.6))
labels = ["Raw sale-history rows", "After exact duplicates\nremoved (24.5 %)",
          "In-window houses\nwith size data"]
vals = [418201, 314895, 79815]
bars = ax.barh(range(3), vals, color=[MUTED, ACCENT, DEEP], height=0.6)
ax.set_yticks(range(3)); ax.set_yticklabels(labels)
ax.invert_yaxis()
ax.set_xlabel("Rows")
ax.set_title("Cleaning: what each step removes", loc="left", color=DEEP, fontweight="bold")
for i, v in enumerate(vals):
    ax.text(v + 6000, i, f"{v:,}", va="center", fontsize=11 * 1.5, color=DEEP,
            fontweight="bold")
ax.set_xlim(0, 470000)
ax.xaxis.set_major_formatter(
    matplotlib.ticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
for side in ("top", "right"):
    ax.spines[side].set_visible(False)
fig.tight_layout()
fig.savefig(OUT / "new_cleaning_funnel.png", dpi=200, bbox_inches="tight", facecolor="white")
plt.close(fig)
print("new_cleaning_funnel.png")

# ---------------------------------------------------------------- slide 16: repeat-sale share
fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
ax = axes[0]
ax.pie([66.0, 34.0], colors=[ACCENT, GRID], startangle=90,
       wedgeprops=dict(width=0.42, edgecolor="white", linewidth=2))
ax.text(0, 0, "66.0 %", ha="center", va="center", fontsize=13 * 1.6,
        color=DEEP, fontweight="bold")
ax.set_title("Addresses that sold\nmore than once", color=DEEP, fontweight="bold")
ax = axes[1]
ax.pie([61.1, 38.9], colors=[DEEP, GRID], startangle=90,
       wedgeprops=dict(width=0.42, edgecolor="white", linewidth=2))
ax.text(0, 0, "61.1 %", ha="center", va="center", fontsize=13 * 1.6,
        color=DEEP, fontweight="bold")
ax.set_title("In-window sales with\nan earlier sale", color=DEEP, fontweight="bold")
fig.suptitle("The file is a repeat-sales panel", color=DEEP, fontweight="bold",
             fontsize=14 * 1.5, y=1.02)
fig.tight_layout()
fig.savefig(OUT / "new_repeat_share.png", dpi=200, bbox_inches="tight", facecolor="white")
plt.close(fig)
print("new_repeat_share.png")

# ---------------------------------------------------------------- slide 33: coverage scorecard
fig, ax = plt.subplots(figsize=(11, 3.9))
names = ["Calibration holdout\n(1,775 rows)", "Held-out test\n(8,859 rows)"]
cov = [88.39, 86.61]
ax.barh(range(2), cov, color=[ACCENT, DEEP], height=0.5)
ax.axvline(90, color=ORANGE, lw=2.5, ls="--", zorder=5)
ax.text(90.35, 0.5, "90 %\ntarget", color=ORANGE, fontweight="bold",
        fontsize=11 * 1.5, va="center", ha="left", linespacing=1.3)
ax.set_yticks(range(2)); ax.set_yticklabels(names)
ax.invert_yaxis()
ax.set_xlim(80, 93)
ax.set_xlabel("Empirical coverage (%)")
ax.set_title("The floor holds close to its target on data it never saw",
             loc="left", color=DEEP, fontweight="bold")
for i, v in enumerate(cov):
    ax.text(v - 0.35, i, f"{v:.2f} %", va="center", ha="right", color="white",
            fontweight="bold", fontsize=11 * 1.5)
for side in ("top", "right"):
    ax.spines[side].set_visible(False)
fig.tight_layout()
fig.savefig(OUT / "new_coverage.png", dpi=200, bbox_inches="tight", facecolor="white")
plt.close(fig)
print("new_coverage.png")
