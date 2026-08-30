# -*- coding: utf-8 -*-
"""Render the markdown tables in blog_post.md as PNGs for upload to Medium."""
from __future__ import annotations
import re
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path("/home/dsi/giladaviv/london_flip_finder")
OUT = ROOT / "figures" / "blog"
OUT.mkdir(parents=True, exist_ok=True)

DEEP, ACCENT, INK, RULE, PANEL = "#104281", "#2a78d6", "#2b2b2b", "#dee4ea", "#f2f6fb"
plt.rcParams["font.family"] = "DejaVu Sans"

md = (ROOT / "blog_post.md").read_text()
blocks, cur = [], []
for line in md.splitlines():
    if line.strip().startswith("|"):
        cur.append(line.strip())
    elif cur:
        blocks.append(cur); cur = []
if cur:
    blocks.append(cur)

def cells(row):
    return [c.strip() for c in row.strip().strip("|").split("|")]

for i, blk in enumerate(blocks, 1):
    head = cells(blk[0])
    body = [cells(r) for r in blk[2:]]           # blk[1] is the --- separator
    ncol, nrow = len(head), len(body) + 1
    wids = [max(len(head[c]), *(len(r[c]) for r in body)) for c in range(ncol)]
    total = sum(wids)
    fw = max(7.0, min(11.0, total * 0.115 + 1.2))
    fh = 0.42 * nrow + 0.25
    fig, ax = plt.subplots(figsize=(fw, fh), dpi=200)
    ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, nrow)
    xs, acc = [], 0.0
    for w in wids:
        xs.append(acc / total); acc += w
    xs.append(1.0)
    pad = 0.012
    for c in range(ncol):
        ax.add_patch(plt.Rectangle((xs[c], nrow - 1), xs[c+1] - xs[c], 1,
                                   facecolor=DEEP, edgecolor="none"))
        left = c == 0
        ax.text(xs[c] + pad if left else xs[c+1] - pad, nrow - 0.5,
                re.sub(r"\*\*(.+?)\*\*", r"\1", head[c]).replace("`", ""),
                ha="left" if left else "right", va="center",
                color="white", fontsize=11, fontweight="bold")
    for r, row in enumerate(body):
        y = nrow - 2 - r
        if r % 2 == 0:
            ax.add_patch(plt.Rectangle((0, y), 1, 1, facecolor=PANEL, edgecolor="none"))
        ax.plot([0, 1], [y + 1, y + 1], color=RULE, lw=0.8)
        for c in range(ncol):
            txt = row[c]
            bold = "**" in txt
            txt = re.sub(r"\*\*(.+?)\*\*", r"\1", txt).replace("`", "")
            left = c == 0
            ax.text(xs[c] + pad if left else xs[c+1] - pad, y + 0.5, txt,
                    ha="left" if left else "right", va="center",
                    color=ACCENT if bold else INK, fontsize=11,
                    fontweight="bold" if bold else "normal")
    fig.savefig(OUT / f"table{i}.png", dpi=200, bbox_inches="tight",
                facecolor="white", pad_inches=0.06)
    plt.close(fig)
    print(f"table{i}.png  {ncol} cols x {len(body)} rows  |  {head[0][:38]}")
