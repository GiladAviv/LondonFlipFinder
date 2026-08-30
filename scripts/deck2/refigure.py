"""Re-export the deck figures at a larger font scale for projection legibility.

Same notebook calls, same data, same chart types and colours -- only the font sizes
change, which is the one styling adjustment the brief allows. The two model figures are
redrawn from the DataFrames the full re-run already produced, so no numbers move.
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path("/home/dsi/giladaviv/london_flip_finder")
sys.path.insert(0, str(ROOT / "src"))
FIG = ROOT / "figures"

import pandas as pd  # noqa: E402
from lff.clean import build_crime_features, build_rate_curve, clean_houses  # noqa: E402
from lff.config import Config, set_seeds  # noqa: E402
from lff.conformal import calibrate_conformal, scan_for_flips  # noqa: E402
from lff.crime import build_crime_features_lsoa  # noqa: E402
from lff.external import fetch_lsoa_boundaries  # noqa: E402
from lff.features.market import add_market_features  # noqa: E402
from lff.features.prior_sale import add_prior_sale_features, build_sale_history  # noqa: E402
from lff.features.registry import TARGET  # noqa: E402
from lff.features.temporal import add_temporal_features  # noqa: E402
from lff.ingest import load_raw  # noqa: E402
from lff.maps import plot_crime_and_price_maps, plot_crime_change, plot_crime_within_borough  # noqa: E402
from lff.master import build_master_table  # noqa: E402
from lff.metrics import ResultsRegistry  # noqa: E402
from lff.models import train_all  # noqa: E402
from lff.notebook import apply_notebook_theme  # noqa: E402
from lff.plots import (plot_ablation, plot_crime_and_market, plot_flip_margins,  # noqa: E402
                       plot_leaderboard, plot_price_clip_comparison,
                       plot_price_per_sqm_by_borough, plot_price_vs_area,
                       plot_property_characteristics, plot_tube_premium)
from lff.split import chronological_split, training_variants  # noqa: E402

apply_notebook_theme()
S = 1.85
for key, base in (("font.size", 10), ("axes.titlesize", 12), ("axes.labelsize", 10),
                  ("xtick.labelsize", 9), ("ytick.labelsize", 9), ("legend.fontsize", 9),
                  ("figure.titlesize", 14)):
    plt.rcParams[key] = base * S


def save(stem):
    for i, num in enumerate(plt.get_fignums()):
        f = plt.figure(num)
        name = f"{stem}.png" if len(plt.get_fignums()) == 1 else f"{stem}_{i}.png"
        f.savefig(FIG / name, dpi=200, bbox_inches="tight", facecolor="white")
        print("   ", name, f.get_size_inches(), flush=True)
    plt.close("all")


t0 = time.time()
CONFIG = Config(); set_seeds(CONFIG.seed)
RAW = load_raw(CONFIG)
LSOA_BOUNDS = fetch_lsoa_boundaries(CONFIG)
CRIME_LSOA_RAW = pd.read_csv(CONFIG.crime_csv,
    usecols=["lsoa_code", "major_category", "value", "year", "month"],
    dtype={"lsoa_code": "category", "major_category": "category",
           "value": "int16", "year": "int16", "month": "int8"})
HOUSES = clean_houses(RAW["houses"], CONFIG)
CRIME = build_crime_features(RAW["crime"])
RATES = build_rate_curve(RAW["boe"], CONFIG)
LSOA_CRIME = build_crime_features_lsoa(CRIME_LSOA_RAW, LSOA_BOUNDS)
df_master = build_master_table(CONFIG, HOUSES, CRIME, RATES, RAW["stations"],
                               lsoa_crime=LSOA_CRIME, lsoa_boundaries=LSOA_BOUNDS)
print(f"master {df_master.shape} [{time.time()-t0:.0f}s]", flush=True)

plot_price_clip_comparison(df_master, CONFIG);    save("c18_price_clip")
plot_property_characteristics(df_master, CONFIG); save("c20_property_chars")
plot_tube_premium(df_master, CONFIG);             save("c23a_tube_premium")
plot_crime_and_market(df_master, CONFIG);         save("c23b_crime_and_market")
plot_price_vs_area(df_master, CONFIG);            save("c23c_price_vs_area")
plot_price_per_sqm_by_borough(df_master, CONFIG); save("c23d_borough_sqm")
lsoa_gdf = plot_crime_and_price_maps(df_master, LSOA_CRIME, LSOA_BOUNDS); save("c26_lsoa_maps")
plot_crime_within_borough(lsoa_gdf);              save("c28_within_borough")
plot_crime_change(df_master, LSOA_CRIME);         save("c29_crime_change")
print(f"EDA figures done [{time.time()-t0:.0f}s]", flush=True)

# ablation figure: redraw from the DataFrame the full re-run produced
res = json.loads((ROOT / "scripts/deck2/rerun_results.json").read_text())
plot_ablation(pd.DataFrame(res["ablation"])); save("c60_ablation")

# leaderboard + flip scanner need the fitted bundles
SALE_HISTORY = build_sale_history(RAW["houses"])
df_model = add_market_features(add_temporal_features(df_master))
df_model = add_prior_sale_features(df_model, SALE_HISTORY)
df_model = df_model.dropna(subset=[TARGET, "date"]).reset_index(drop=True)
SPLITS = chronological_split(df_model, CONFIG)
VAL_EVAL = SPLITS.val[SPLITS.val[TARGET] <= CONFIG.price_cap]
CALIB_EVAL = SPLITS.calib[SPLITS.calib[TARGET] <= CONFIG.price_cap]
TEST_EVAL = SPLITS.test[SPLITS.test[TARGET] <= CONFIG.price_cap]
VARIANTS = training_variants(SPLITS, CONFIG)
RESULTS = ResultsRegistry()
BUNDLES = train_all(SPLITS, VARIANTS, CONFIG, VAL_EVAL, RESULTS)
val_board = RESULTS.frame("val")
plot_leaderboard(val_board, "Validation performance, identical evaluation rows")
save("c48_leaderboard")
BEST = BUNDLES[val_board.iloc[0]["Model"]]
Q = calibrate_conformal(BEST, CALIB_EVAL, SPLITS, CONFIG.conformal_alpha)
scan = scan_for_flips(BEST, TEST_EVAL, SPLITS, Q)
flips = scan[scan["is_flip"]].sort_values("margin", ascending=False)
cov = (scan["actual_price"] >= scan["safe_lower_bound"]).mean() * 100
print(f"CHECK q={Q:.6f} coverage={cov:.2f}% flips={len(flips)} "
      f"({len(flips)/len(scan)*100:.2f}%) median_margin={flips['margin'].median():,.0f}",
      flush=True)
plot_flip_margins(flips, scan, Q, CONFIG); save("c73_flip_margins")
print(f"DONE [{time.time()-t0:.0f}s]", flush=True)
