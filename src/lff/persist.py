"""Run artefacts and the automated self-checks. Sections 16-17."""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .config import Config
from .features.market import add_market_features
from .features.registry import CATEGORICAL_FEATURES, FEATURES, TARGET
from .features.temporal import add_temporal_features
from .metrics import ModelBundle, ResultsRegistry
from .split import Splits


def persist_run(bundle: ModelBundle, q: float, cfg: Config,
                results: ResultsRegistry, splits: Splits) -> Path:
    """Write estimators, metrics and a manifest so a run can be audited or reloaded."""
    cfg.artifact_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "selected_model": bundle.name,
        "trained_on": bundle.trained_on,
        "features": FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "target": TARGET,
        "conformal": {"alpha": cfg.conformal_alpha, "multiplier": q},
        "config": {
            "year_min": cfg.year_min, "year_max": cfg.year_max,
            "price_cap": cfg.price_cap, "min_price_per_sqm": cfg.min_price_per_sqm,
            "luxury_threshold": cfg.luxury_threshold, "seed": cfg.seed,
            "fast_mode": cfg.fast_mode,
        },
        "validation": results.frame("val").to_dict(orient="records"),
        "test": results.frame("test").to_dict(orient="records"),
    }

    manifest_path = cfg.artifact_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str))
    results.frame().to_csv(cfg.artifact_dir / "leaderboard.csv", index=False)
    joblib.dump(
        {"artefacts": bundle.artefacts, "category_dtypes": splits.category_dtypes,
         "encoder": splits.encoder},
        cfg.artifact_dir / "model.joblib",
    )

    for path in sorted(cfg.artifact_dir.iterdir()):
        print(f"   {path.name:<24}{path.stat().st_size / 1e6:8.2f} MB")
    return manifest_path


def run_self_checks(splits: Splits, cfg: Config, bundle: ModelBundle,
                    test_coverage: float, nominal: float,
                    raw: dict[str, pd.DataFrame], master: pd.DataFrame) -> None:
    failures: list[str] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        status = "PASS" if condition else "FAIL"
        print(f"[{status}] {name}" + (f" -- {detail}" if detail else ""))
        if not condition:
            failures.append(name)

    ordered = (
        splits.train["date"].max() <= splits.val["date"].min()
        and splits.val["date"].max() <= splits.calib["date"].min()
        and splits.calib["date"].max() <= splits.test["date"].min()
    )
    check(
        "chronological split integrity",
        ordered,
        f"train ends {splits.train['date'].max():%Y-%m-%d}, "
        f"test starts {splits.test['date'].min():%Y-%m-%d}",
    )

    check(
        "calibration split sits strictly between validation and test",
        ordered,  # same four-way ordering; named separately so a failure here is unambiguous
        f"calib spans {splits.calib['date'].min():%Y-%m-%d} to "
        f"{splits.calib['date'].max():%Y-%m-%d}, "
        "untouched by model fitting or selection",
    )

    all_nan = [c for c in FEATURES if splits.features(splits.train)[c].isna().all()]
    check("no all-NaN feature columns", not all_nan, f"offenders: {all_nan}" if all_nan else
          f"{len(FEATURES)} features carry signal")

    encoded = splits.features(splits.val)
    check(
        "categorical levels pinned from training",
        all(encoded[c].dtype == splits.category_dtypes[c] for c in CATEGORICAL_FEATURES),
        "validation categories use the training level set",
    )

    # Causal test: shock the final month's prices tenfold and re-derive the market features.
    # A feature that legitimately looks only backwards cannot move. Comparing the lag to the
    # contemporaneous median instead would flag coincidental equality as leakage.
    # Re-derive from the pre-market-features frame: df_model already carries these columns,
    # so feeding it back through add_market_features would collide on the merge.
    base = add_temporal_features(master)
    probe = base.copy()
    shocked = (base["month_year_period"] == base["month_year_period"].max()).to_numpy()
    probe.loc[shocked, ["price", "price_per_sqm"]] *= 10
    lag_cols = ["market_median_rolling_3m", "market_median_rolling_12m",
                "lagged_borough_median_sqm"]
    before = add_market_features(base).loc[shocked, lag_cols].reset_index(drop=True)
    after = add_market_features(probe).loc[shocked, lag_cols].reset_index(drop=True)
    unmoved = [c for c in lag_cols if before[c].equals(after[c])]
    check("lagged market features exclude the present", len(unmoved) == len(lag_cols),
          f"{len(unmoved)}/{len(lag_cols)} lag features unmoved by a 10x shock to their own month")

    # Conformal coverage, checked WITHOUT touching test. q10 is refitted on the first 70% of the
    # calibration split and scored on the held-out remainder. Asserting on the full calibration
    # split would be tautological -- q10 is by construction its own empirical 10th percentile --
    # so the split-within-a-split is what makes this a real check rather than an identity.
    calib_sorted = splits.calib[splits.calib[TARGET] <= cfg.price_cap].sort_values("date")
    cut = int(len(calib_sorted) * 0.70)
    calib_fit, calib_hold = calib_sorted.iloc[:cut], calib_sorted.iloc[cut:]
    fit_ratios = (splits.target(calib_fit).to_numpy(dtype=float)
                  / bundle.predict(splits.features(calib_fit)))
    q_hold = float(np.quantile(fit_ratios, cfg.conformal_alpha))
    hold_actual = splits.target(calib_hold).to_numpy(dtype=float)
    hold_floor = bundle.predict(splits.features(calib_hold)) * q_hold
    held_out_coverage = float((hold_actual >= hold_floor).mean() * 100)
    check("conformal coverage within tolerance (calibration holdout)",
          abs(held_out_coverage - nominal) <= 5.0,
          f"{held_out_coverage:.2f}% against a {nominal:.0f}% target, "
          f"on {len(calib_hold):,} rows the multiplier was not fitted on")

    # Test coverage is REPORTED, never asserted: gating the pipeline's pass/fail on a held-out
    # metric would turn the test set into a tuning signal every time a run failed.
    print(f"[INFO] test-set conformal coverage {test_coverage:.2f}% "
          f"against a {nominal:.0f}% target -- reported, not asserted")

    check("raw station table intact", "EASTING" in raw["stations"].columns
          and len(raw["stations"]) > 0, f"{len(raw['stations'])} stations still loaded")

    # Prior-sale features read the property's own past, which is legitimate -- but only while
    # "past" holds. A single row whose matched sale is dated on or after its own sale date
    # would be reading the target, so this is asserted rather than reported.
    if "prev_sale_date" in splits.train.columns:
        # Read the split frames, not `master`: prior-sale features are attached downstream of
        # df_master, so the columns exist only on the modelling frame the splits were cut from.
        modelled = pd.concat([splits.train, splits.val, splits.calib, splits.test])
        matched = modelled[modelled["has_prev_sale"] == 1]
        offending = int((matched["prev_sale_date"] >= matched["date"]).sum())
        check("prior sales strictly precede the row that reads them", offending == 0,
              f"{len(matched):,} rows carry a prior sale, {offending} dated at or after their own")

    check("no target leakage in feature list",
          not any(f.startswith(("saleEstimate", "rentEstimate", "price_per_sqm"))
                  for f in FEATURES),
          "no third-party valuation columns among the predictors")

    print()
    if failures:
        raise AssertionError(f"{len(failures)} self-check(s) failed: {failures}")
    print("All self-checks passed.")
