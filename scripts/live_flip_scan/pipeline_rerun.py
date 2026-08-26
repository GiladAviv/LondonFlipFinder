"""In-process rerun of the trained pipeline: BEST model, Splits, conformal multiplier, and the
current test-set flip rate. Mirrors london_flip_finder.ipynb sections 1-15 exactly.

artifacts/manifest.json is NOT used as ground truth here -- it predates the prior-sale features
(lff.features.registry.FEATURES has 28 entries; the persisted manifest has 24) and was built with
fast_mode=true. This rerun is the current ground truth; it always trains at full fidelity.
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import geopandas as gpd
import pandas as pd

from lff.clean import build_crime_features, build_rate_curve, clean_houses
from lff.config import Config, set_seeds
from lff.conformal import calibrate_conformal, scan_for_flips
from lff.crime import build_crime_features_lsoa
from lff.external import fetch_lsoa_boundaries
from lff.features.market import add_market_features
from lff.features.prior_sale import add_prior_sale_features, assert_no_lookahead, build_sale_history
from lff.features.registry import TARGET
from lff.features.temporal import add_temporal_features
from lff.ingest import ensure_dataset, load_raw
from lff.master import build_master_table
from lff.metrics import ModelBundle, ResultsRegistry
from lff.models import train_all
from lff.spatial import split_station_networks, to_projected_gdf
from lff.split import Splits, chronological_split, training_variants


@dataclass(frozen=True)
class PipelineState:
    cfg: Config
    best: ModelBundle
    splits: Splits
    q_safety: float
    test_flip_rate: float
    test_scan: pd.DataFrame
    training_origin_date: pd.Timestamp
    underground_gdf: gpd.GeoDataFrame
    heavy_rail_gdf: gpd.GeoDataFrame


def get_pipeline_state() -> PipelineState:
    """Rebuild the modelling table, run the full model bake-off, and calibrate the conformal
    floor -- everything a live-listing scan needs. Always full fidelity (LFF_FAST_MODE unset),
    since there is no trustworthy shortcut: the persisted artifacts predate the current feature
    set (see module docstring)."""
    import os
    os.environ.pop("LFF_FAST_MODE", None)

    cfg = Config()
    cfg.artifact_dir.mkdir(parents=True, exist_ok=True)
    set_seeds(cfg.seed)
    print(f"fast_mode={cfg.fast_mode} (must be False for a trustworthy rerun)")

    ensure_dataset(cfg)
    raw = load_raw(cfg)
    lsoa_bounds = fetch_lsoa_boundaries(cfg)
    crime_lsoa_raw = pd.read_csv(
        cfg.crime_csv,
        usecols=["lsoa_code", "major_category", "value", "year", "month"],
        dtype={"lsoa_code": "category", "major_category": "category",
               "value": "int16", "year": "int16", "month": "int8"},
    )

    houses = clean_houses(raw["houses"], cfg)
    crime = build_crime_features(raw["crime"])
    rates = build_rate_curve(raw["boe"], cfg)
    lsoa_crime = build_crime_features_lsoa(crime_lsoa_raw, lsoa_bounds)
    underground, heavy_rail = split_station_networks(raw["stations"])
    underground_gdf = to_projected_gdf(underground, cfg)
    heavy_rail_gdf = to_projected_gdf(heavy_rail, cfg)

    df_master = build_master_table(cfg, houses, crime, rates, raw["stations"],
                                   lsoa_crime=lsoa_crime, lsoa_boundaries=lsoa_bounds)

    sale_history = build_sale_history(raw["houses"])
    df_model = add_market_features(add_temporal_features(df_master))
    df_model = add_prior_sale_features(df_model, sale_history)
    df_model = df_model.dropna(subset=[TARGET, "date"]).reset_index(drop=True)
    assert_no_lookahead(df_model)
    training_origin_date = df_model["date"].min()

    splits = chronological_split(df_model, cfg)
    val_eval = splits.val[splits.val[TARGET] <= cfg.price_cap]
    calib_eval = splits.calib[splits.calib[TARGET] <= cfg.price_cap]
    test_eval = splits.test[splits.test[TARGET] <= cfg.price_cap]

    variants = training_variants(splits, cfg)
    results = ResultsRegistry()
    started = time.time()
    bundles = train_all(splits, variants, cfg, val_eval, results)
    print(f"Bake-off: {len(bundles)} models trained in {time.time() - started:.0f}s")

    val_board = results.frame("val")
    best_name = val_board.iloc[0]["Model"]
    best = bundles[best_name]
    print(f"Selected on validation MdAPE: {best_name}")

    q_safety = calibrate_conformal(best, calib_eval, splits, cfg.conformal_alpha)
    test_scan = scan_for_flips(best, test_eval, splits, q_safety)
    test_flip_rate = float(test_scan["is_flip"].mean() * 100)

    coverage = (test_scan["actual_price"] >= test_scan["safe_lower_bound"]).mean() * 100
    target = (1 - cfg.conformal_alpha) * 100
    print(f"\nTest-set coverage: {coverage:.2f}% (target {target:.2f}%)")
    print(f"Test-set flip rate: {test_flip_rate:.2f}% ({len(test_scan):,} properties)")

    return PipelineState(cfg, best, splits, q_safety, test_flip_rate, test_scan,
                         training_origin_date, underground_gdf, heavy_rail_gdf)


if __name__ == "__main__":
    state = get_pipeline_state()
    print(f"\ntraining_origin_date = {state.training_origin_date}")
    print(f"Q_SAFETY = {state.q_safety:.4f}")
