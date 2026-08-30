"""Re-run the notebook's own cells to export figures at 200 dpi and recover the numbers
that cell 67's AttributeError left unrecorded (sections 14.6, 15, 16, 17).

Nothing here is new analysis: every call is copied from london_flip_finder.ipynb, in the
notebook's order, with two changes only -- figures are saved instead of shown, and section 15
is executed before the 14.5/14.6 design studies so the missing conformal numbers land early.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path("/home/dsi/giladaviv/london_flip_finder")
sys.path.insert(0, str(ROOT / "src"))
FIGDIR = ROOT / "figures"
FIGDIR.mkdir(exist_ok=True)
OUT = ROOT / "scripts" / "deck2" / "rerun_results.json"
RESULTS_JSON: dict = {}

import geopandas as gpd  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import xgboost as xgb  # noqa: E402

import lff  # noqa: E402
from lff.analysis import (  # noqa: E402
    ablation_study, crime_resolution_study, extrapolation_bias, prior_sale_study,
    repeat_property_diagnostic, summarise_target_transform,
)
from lff.clean import build_crime_features, build_rate_curve, clean_houses  # noqa: E402
from lff.config import Config, set_seeds  # noqa: E402
from lff.conformal import calibrate_conformal, scan_for_flips  # noqa: E402
from lff.crime import build_crime_features_lsoa  # noqa: E402
from lff.external import fetch_lsoa_boundaries  # noqa: E402
from lff.features.market import add_market_features  # noqa: E402
from lff.features.prior_sale import (  # noqa: E402
    add_prior_sale_features, assert_no_lookahead, build_sale_history,
)
from lff.features.registry import (  # noqa: E402
    CATEGORICAL_FEATURES, FEATURE_GROUPS, FEATURES, NUMERIC_FEATURES, TARGET,
)
from lff.features.temporal import add_temporal_features  # noqa: E402
from lff.ingest import ensure_dataset, load_raw  # noqa: E402
from lff.maps import (  # noqa: E402
    plot_crime_and_price_maps, plot_crime_change, plot_crime_within_borough,
)
from lff.master import build_master_table  # noqa: E402
from lff.metrics import ResultsRegistry, evaluate  # noqa: E402
from lff.models import train_all  # noqa: E402
from lff.notebook import apply_notebook_theme  # noqa: E402
from lff.persist import persist_run, run_self_checks  # noqa: E402
from lff.plots import (  # noqa: E402
    plot_ablation, plot_crime_and_market, plot_flip_margins, plot_leaderboard,
    plot_price_clip_comparison, plot_price_per_sqm_by_borough, plot_price_vs_area,
    plot_property_characteristics, plot_tube_premium,
)
from lff.spatial import split_station_networks  # noqa: E402
from lff.split import chronological_split, training_variants  # noqa: E402

apply_notebook_theme()

# The only styling change permitted for projection: larger type. Sizes scale the theme's own
# values; colours, chart types and layout are untouched.
_S = 1.35
for key, base in (("font.size", 10), ("axes.titlesize", 12), ("axes.labelsize", 10),
                  ("xtick.labelsize", 9), ("ytick.labelsize", 9), ("legend.fontsize", 9),
                  ("figure.titlesize", 14)):
    plt.rcParams[key] = base * _S


def save_new_figs(stem: str) -> list[str]:
    """Save every figure created since the last call, at 200 dpi."""
    names = []
    for i, num in enumerate(plt.get_fignums()):
        fig = plt.figure(num)
        name = f"{stem}.png" if len(plt.get_fignums()) == 1 else f"{stem}_{i}.png"
        fig.savefig(FIGDIR / name, dpi=200, bbox_inches="tight", facecolor="white")
        names.append(name)
        print(f"    saved figures/{name}  {fig.get_size_inches()}")
    plt.close("all")
    return names


def stamp(key, value):
    RESULTS_JSON[key] = value
    OUT.write_text(json.dumps(RESULTS_JSON, indent=2, default=str))


t0 = time.time()
print(f"=== lff {lff.__version__} | xgboost {xgb.__version__} ===", flush=True)

# --- cells 6-16: config, load, clean, spatial, master -------------------------------------
CONFIG = Config()
CONFIG.artifact_dir.mkdir(parents=True, exist_ok=True)
set_seeds(CONFIG.seed)
ABLATION_GATE_PP = 0.15
print(f"split {CONFIG.train_frac:.0%}/{CONFIG.val_frac:.0%}/"
      f"{CONFIG.calib_frac:.0%}/{CONFIG.test_frac:.0%}  cap £{CONFIG.price_cap:,.0f}  "
      f"alpha {CONFIG.conformal_alpha}", flush=True)
stamp("config", {"train_frac": CONFIG.train_frac, "val_frac": CONFIG.val_frac,
                 "calib_frac": CONFIG.calib_frac, "test_frac": CONFIG.test_frac,
                 "price_cap": CONFIG.price_cap, "conformal_alpha": CONFIG.conformal_alpha,
                 "seed": CONFIG.seed})

ensure_dataset(CONFIG)
RAW = load_raw(CONFIG)
LSOA_BOUNDS = fetch_lsoa_boundaries(CONFIG)
CRIME_LSOA_RAW = pd.read_csv(
    CONFIG.crime_csv, usecols=["lsoa_code", "major_category", "value", "year", "month"],
    dtype={"lsoa_code": "category", "major_category": "category",
           "value": "int16", "year": "int16", "month": "int8"})

HOUSES = clean_houses(RAW["houses"], CONFIG)
CRIME = build_crime_features(RAW["crime"])
RATES = build_rate_curve(RAW["boe"], CONFIG)
LSOA_CRIME = build_crime_features_lsoa(CRIME_LSOA_RAW, LSOA_BOUNDS)
UNDERGROUND, HEAVY_RAIL = split_station_networks(RAW["stations"])
df_master = build_master_table(CONFIG, HOUSES, CRIME, RATES, RAW["stations"],
                               lsoa_crime=LSOA_CRIME, lsoa_boundaries=LSOA_BOUNDS)
print(f"df_master {df_master.shape}  [{time.time()-t0:.0f}s]", flush=True)

# --- cells 18-29: EDA figures --------------------------------------------------------------
print("\n=== EDA figures ===", flush=True)
plot_price_clip_comparison(df_master, CONFIG);      save_new_figs("c18_price_clip")
plot_property_characteristics(df_master, CONFIG);   save_new_figs("c20_property_chars")
plot_tube_premium(df_master, CONFIG);               save_new_figs("c23a_tube_premium")
plot_crime_and_market(df_master, CONFIG);           save_new_figs("c23b_crime_and_market")
plot_price_vs_area(df_master, CONFIG);              save_new_figs("c23c_price_vs_area")
plot_price_per_sqm_by_borough(df_master, CONFIG);   save_new_figs("c23d_borough_sqm")
lsoa_gdf = plot_crime_and_price_maps(df_master, LSOA_CRIME, LSOA_BOUNDS)
save_new_figs("c26_lsoa_maps")
crime_partial = plot_crime_within_borough(lsoa_gdf);   save_new_figs("c28_within_borough")
crime_differenced = plot_crime_change(df_master, LSOA_CRIME); save_new_figs("c29_crime_change")
stamp("crime_partial", crime_partial)
stamp("crime_differenced", crime_differenced)
print(f"EDA done [{time.time()-t0:.0f}s]", flush=True)

# --- cells 33-38: features, split, variants ------------------------------------------------
SALE_HISTORY = build_sale_history(RAW["houses"])
df_model = add_market_features(add_temporal_features(df_master))
df_model = add_prior_sale_features(df_model, SALE_HISTORY)
df_model = df_model.dropna(subset=[TARGET, "date"]).reset_index(drop=True)
assert_no_lookahead(df_model)
print(f"Modelling table: {df_model.shape}", flush=True)

SPLITS = chronological_split(df_model, CONFIG)
VAL_EVAL = SPLITS.val[SPLITS.val[TARGET] <= CONFIG.price_cap]
CALIB_EVAL = SPLITS.calib[SPLITS.calib[TARGET] <= CONFIG.price_cap]
TEST_EVAL = SPLITS.test[SPLITS.test[TARGET] <= CONFIG.price_cap]
print(f"eval universe: {len(VAL_EVAL):,} val, {len(CALIB_EVAL):,} calib, "
      f"{len(TEST_EVAL):,} test", flush=True)
VARIANTS = training_variants(SPLITS, CONFIG)

# --- cells 40-48: train, bias diagnostic, leaderboard --------------------------------------
print(f"\n=== training [{time.time()-t0:.0f}s] ===", flush=True)
RESULTS = ResultsRegistry()
BUNDLES = train_all(SPLITS, VARIANTS, CONFIG, VAL_EVAL, RESULTS)

_bias_models = ["XGBoost (capped)", "XGBoost detrended-market (capped)", "Ridge (baseline)"]
bias_val = extrapolation_bias(_bias_models, VAL_EVAL, "val", SPLITS, BUNDLES)
print(bias_val.to_string(index=False), flush=True)
stamp("bias_val", bias_val.to_dict("records"))

val_board = RESULTS.frame("val")
plot_leaderboard(val_board, "Validation performance, identical evaluation rows")
save_new_figs("c48_leaderboard")
stamp("val_board", val_board.to_dict("records"))

# --- cell 51: held-out test ----------------------------------------------------------------
BEST_NAME = val_board.iloc[0]["Model"]
BEST = BUNDLES[BEST_NAME]
print(f"\nSelected on validation MdAPE: {BEST_NAME}", flush=True)
for bundle in BUNDLES.values():
    evaluate(bundle, TEST_EVAL, "test", RESULTS, SPLITS)
test_board = RESULTS.frame("test")
comparison = (val_board[["Model", "MdAPE", "MAE"]]
              .merge(test_board[["Model", "MdAPE", "MAE"]], on="Model",
                     suffixes=(" (val)", " (test)")))
comparison["MdAPE drift"] = comparison["MdAPE (test)"] - comparison["MdAPE (val)"]
comparison = comparison.sort_values("MdAPE (test)").reset_index(drop=True)
print(comparison.to_string(index=False), flush=True)
stamp("best_name", BEST_NAME)
stamp("test_board", test_board.to_dict("records"))
stamp("comparison", comparison.to_dict("records"))

# --- cell 54: repeat-property diagnostic ---------------------------------------------------
rp = repeat_property_diagnostic(BEST, SPLITS, TEST_EVAL)
print(rp.to_string(index=False), flush=True)
stamp("repeat_property", rp.to_dict("records"))

# --- cell 57: target transform -------------------------------------------------------------
tc = summarise_target_transform(RESULTS)
print(tc.to_string(index=False), flush=True)
stamp("transform_comparison", tc.to_dict("records"))

# --- cells 71-73: SECTION 15, the numbers the notebook never recorded ----------------------
print(f"\n=== SECTION 15 conformal [{time.time()-t0:.0f}s] ===", flush=True)
Q_SAFETY = calibrate_conformal(BEST, CALIB_EVAL, SPLITS, CONFIG.conformal_alpha)
scan = scan_for_flips(BEST, TEST_EVAL, SPLITS, Q_SAFETY)
flips = scan[scan["is_flip"]].sort_values("margin", ascending=False)
coverage = (scan["actual_price"] >= scan["safe_lower_bound"]).mean() * 100
target = (1 - CONFIG.conformal_alpha) * 100
print(f"Q_SAFETY           : {Q_SAFETY:.6f}")
print(f"Target confidence  : {target:.2f}%")
print(f"Actual coverage    : {coverage:.2f}%   ({coverage - target:+.2f} pp)")
print(f"Properties scanned : {len(scan):,}")
print(f"Flip candidates    : {len(flips):,} ({len(flips)/len(scan)*100:.2f}%)")
print(f"Median margin      : £{flips['margin'].median():,.0f}", flush=True)
stamp("section15", {
    "q_safety": float(Q_SAFETY), "target": float(target), "coverage": float(coverage),
    "coverage_gap": float(coverage - target), "n_scanned": int(len(scan)),
    "n_flips": int(len(flips)), "flip_rate": float(len(flips)/len(scan)*100),
    "median_margin": float(flips["margin"].median()),
    "top10": flips.head(10).to_dict("records"),
})
plot_flip_margins(flips, scan, Q_SAFETY, CONFIG); save_new_figs("c73_flip_margins")

# --- cells 76-78: persist and self-checks --------------------------------------------------
persist_run(BEST, Q_SAFETY, CONFIG, RESULTS, SPLITS)
try:
    run_self_checks(SPLITS, CONFIG, BEST, coverage, target, RAW, df_master)
    stamp("self_checks", "passed")
except Exception as exc:  # recorded, not swallowed
    print(f"SELF-CHECKS RAISED: {type(exc).__name__}: {exc}", flush=True)
    stamp("self_checks", f"{type(exc).__name__}: {exc}")

# --- cell 60: feature-group ablation -------------------------------------------------------
print(f"\n=== SECTION 14.5 ablation [{time.time()-t0:.0f}s] ===", flush=True)
ablation = ablation_study(SPLITS, VARIANTS, FEATURE_GROUPS, CONFIG, VAL_EVAL)
plot_ablation(ablation); save_new_figs("c60_ablation")
print(ablation.to_string(index=False), flush=True)
stamp("ablation", ablation.to_dict("records"))

# --- cell 63: crime resolution study -------------------------------------------------------
print(f"\n=== SECTION 14.5 crime resolution [{time.time()-t0:.0f}s] ===", flush=True)
CRIME_SEEDS = (42, 43, 44, 45, 46)
crime_designs = crime_resolution_study(SPLITS, VARIANTS, CONFIG, VAL_EVAL, seeds=CRIME_SEEDS)
print(crime_designs.to_string(index=False), flush=True)
stamp("crime_designs", crime_designs.to_dict("records"))
stamp("crime_noise_floor", float(crime_designs["MdAPE sd"].mean()))

# --- cell 67: prior-sale study (the cell that broke the notebook run) ----------------------
print(f"\n=== SECTION 14.6 prior sale [{time.time()-t0:.0f}s] ===", flush=True)
try:
    prior_sale_designs = prior_sale_study(SPLITS, VARIANTS, CONFIG, VAL_EVAL, seeds=(42, 43, 44))
    print(prior_sale_designs.to_string(index=False), flush=True)
    stamp("prior_sale_designs", prior_sale_designs.to_dict("records"))
except Exception as exc:
    import traceback
    traceback.print_exc()
    stamp("prior_sale_designs", f"FAILED {type(exc).__name__}: {exc}")

print(f"\n=== DONE in {time.time()-t0:.0f}s ===", flush=True)
