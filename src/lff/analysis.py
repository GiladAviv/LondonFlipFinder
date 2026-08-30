"""Diagnostics and design studies. Sections 12.1, 14.1, 14.3, 14.5-14.6, and the crime
study (8.2). Section 14 skips 14.2 and 14.4; both were removed and the rest were not
renumbered, so cross-references elsewhere keep pointing at the same sections."""
from __future__ import annotations

import numpy as np
import pandas as pd
import xgboost as xgb

from .config import Config
from .crime import LSOA_CRIME_FEATURES
from .features.prior_sale import PRIOR_SALE_FEATURES
from .features.registry import BOROUGH_CRIME_FEATURES, FEATURES
from .metrics import ModelBundle, ResultsRegistry, regression_metrics
from .models import detrend, fit_market_deflator, market_level, retrend
from .split import Splits


def extrapolation_bias(names: list[str], part: pd.DataFrame, split_label: str,
                       splits: Splits, bundles: dict[str, ModelBundle]) -> pd.DataFrame:
    """Mean signed residual per model: the fingerprint of a level error, not of noise.

    A model that merely predicts imprecisely scatters residuals around zero. A model that cannot
    extrapolate a trend sits systematically below the truth, so the MEAN residual -- not its
    absolute value -- is the quantity that separates the two failure modes.
    """
    actual = splits.target(part).to_numpy(dtype=float)
    rows = []
    for name in names:
        if name not in bundles:
            continue
        residuals = actual - bundles[name].predict(splits.features(part))
        rows.append({
            "Model": name,
            f"Mean residual ({split_label})": residuals.mean(),
            "Median residual": float(np.median(residuals)),
            "Under-predicted %": float((residuals > 0).mean() * 100),
        })
    return pd.DataFrame(rows)


def repeat_property_diagnostic(bundle: ModelBundle, splits: Splits,
                               test_eval: pd.DataFrame) -> pd.DataFrame:
    """Split test performance by whether the property also appears in the training data."""
    seen = set(splits.train["fullAddress"])
    is_seen = test_eval["fullAddress"].isin(seen)

    rows = []
    for label, mask in (("Seen in training", is_seen), ("Unseen property", ~is_seen)):
        part = test_eval[mask]
        if part.empty:
            continue
        metrics = regression_metrics(splits.target(part), bundle.predict(splits.features(part)))
        rows.append({"Test subset": label, "Rows": len(part), **metrics})

    frame = pd.DataFrame(rows)
    overlap = is_seen.mean() * 100
    print(f"{overlap:.1f}% of test transactions are properties that also appear in training "
          f"({is_seen.sum():,} of {len(test_eval):,}).")
    if len(frame) == 2:
        gap = frame.loc[0, "MdAPE"] - frame.loc[1, "MdAPE"]
        print(f"MdAPE gap between seen and unseen properties: {gap:+.2f} percentage points.")
    return frame[["Test subset", "Rows", "MdAPE", "MAE", "R2", "within_25pct"]]


def summarise_target_transform(registry: ResultsRegistry) -> pd.DataFrame:
    """Pull the regular vs. market vs. borough rows for a focused comparison -- computed from
    what was actually trained, not hand-typed.

    Both splits are shown, but only the validation column is used to pick a winner below. The
    test column is disclosure, so a reader can see whether the validation-based choice held up.
    """
    val_rows, test_rows = registry.frame("val"), registry.frame("test")
    combos = [
        ("XGBoost", "XGBoost (capped)", "XGBoost detrended-market (capped)",
         "XGBoost detrended-borough (capped)"),
        ("CatBoost", "CatBoost (cleaned)", "CatBoost detrended-market (cleaned)",
         "CatBoost detrended-borough (cleaned)"),
    ]
    rows = []
    for backend, regular, market, borough in combos:
        for label, name in (("regular", regular), ("market-wide", market),
                            ("borough-scaled", borough)):
            val_match = val_rows[val_rows["Model"] == name]
            test_match = test_rows[test_rows["Model"] == name]
            if val_match.empty:
                continue
            row = {"Backend": backend, "Target transform": label,
                   "Validation MdAPE": val_match.iloc[0]["MdAPE"]}
            if not test_match.empty:
                row["Test MdAPE"] = test_match.iloc[0]["MdAPE"]
                row["Test MAE"] = test_match.iloc[0]["MAE"]
            rows.append(row)
    return pd.DataFrame(rows)


def ablation_study(splits: Splits, variants: dict[str, pd.DataFrame],
                   groups: dict[str, list[str]], cfg: Config,
                   val_eval: pd.DataFrame) -> pd.DataFrame:
    """Retrain the winning detrended recipe with each feature group removed in turn.

    Scored on VALIDATION, not test: this study's output feeds a decision (which features to keep,
    and whether the 2008-2016 window is worth its cost), and decisions must never read the test
    set. The models early-stop on validation too, so the absolute level here is optimistic -- but
    every variant carries that bias identically and the gate below consumes only the *delta*.
    """
    train_df = variants["capped"]          # same variant as the winning single model
    deflator = fit_market_deflator(train_df)

    def fit_and_score(name: str, drop: list[str]) -> dict:
        keep = [f for f in FEATURES if f not in drop]

        # The deflator is part of the target transform, not an input feature, so it is always
        # computed from the full feature frame. That keeps the label identical across every
        # variant -- only the model's *inputs* change, which is what an ablation should isolate.
        X_train_full, X_val_full = splits.features(train_df), splits.features(val_eval)
        y_train = detrend(splits.target(train_df), market_level(X_train_full, deflator))
        y_val = detrend(splits.target(val_eval), market_level(X_val_full, deflator))

        model = xgb.XGBRegressor(
            n_estimators=cfg.n_estimators, max_depth=8, learning_rate=0.03,
            subsample=0.8, colsample_bytree=0.8, enable_categorical=True, tree_method="hist",
            objective="reg:absoluteerror", early_stopping_rounds=50,
            random_state=cfg.seed, n_jobs=-1,
        )
        model.fit(X_train_full[keep], y_train,
                  eval_set=[(X_val_full[keep], y_val)], verbose=False)

        predicted = retrend(model.predict(X_val_full[keep]), market_level(X_val_full, deflator))
        metrics = regression_metrics(splits.target(val_eval), predicted)
        print(f"{name:<16}{len(keep):>2} features   MdAPE {metrics['MdAPE']:6.2f}%   "
              f"MAE \N{POUND SIGN}{metrics['MAE']:>10,.0f}")
        return {"Variant": name, "Features": len(keep), **metrics}

    rows = [fit_and_score("Full", [])]
    for group_name, group_features in groups.items():
        rows.append(fit_and_score(f"No {group_name}", group_features))

    frame = pd.DataFrame(rows)
    frame["MdAPE delta"] = frame["MdAPE"] - frame.loc[0, "MdAPE"]
    return frame


def crime_resolution_study(splits: Splits, variants: dict[str, pd.DataFrame], cfg: Config,
                           val_eval: pd.DataFrame,
                           seeds: tuple[int, ...] = (42,)) -> pd.DataFrame:
    """Is the +0.11 pp verdict on crime a verdict on crime, or only on borough-grain crime?

    Same recipe, same rows, same target as `ablation_study` -- the only thing that varies is
    which crime columns are in the feature matrix. Every variant is scored on validation,
    because this decides whether the 2008-2016 window survives and decisions do not read test.

    The frames must already carry the LSOA crime columns; `build_master_table` attaches them
    when it is handed an `lsoa_crime` table.
    """
    base = [f for f in FEATURES if f not in BOROUGH_CRIME_FEATURES]
    lsoa_available = [c for c in LSOA_CRIME_FEATURES if c in variants["capped"].columns]
    if not lsoa_available:
        raise KeyError(
            "No LSOA crime columns in the model frame. Pass lsoa_crime to build_master_table."
        )
    # Every count series at LSOA grain: the all-crime total plus its three category splits.
    # The density column is the one normalised series and is held back for its own design.
    counts = [c for c in lsoa_available if not c.startswith("lsoa_crime_density")]
    # Named columns are filtered through `lsoa_available` too, so a change to
    # LSOA_CRIME_FEATURES drops a design rather than raising a KeyError deep in the fit.
    total = [c for c in lsoa_available if c == "lsoa_crime_prev_12m"]
    density = [c for c in lsoa_available if c.startswith("lsoa_crime_density")]

    designs = {
        "No crime": [],
        "Borough count (status quo)": BOROUGH_CRIME_FEATURES,
        "LSOA total": total,
        "LSOA by category": counts,
        "LSOA + density": [*counts, *density],
        "Borough + LSOA": [*BOROUGH_CRIME_FEATURES, *lsoa_available],
    }

    return _seeded_design_study(splits, variants, cfg, val_eval, base, designs, seeds,
                                baseline="No crime", label="Crime features")


def _seeded_design_study(splits: Splits, variants: dict[str, pd.DataFrame], cfg: Config,
                         val_eval: pd.DataFrame, base: list[str],
                         designs: dict[str, list[str]], seeds: tuple[int, ...],
                         baseline: str, label: str) -> pd.DataFrame:
    """Refit one recipe under several feature designs and several seeds; report paired gains.

    A single gradient-boosted fit cannot separate a 0.1 pp effect from run-to-run variation,
    and both studies that use this engine feed decisions rather than descriptions. Each design
    is therefore refit under every seed, and each gain is differenced against the baseline
    *within* its own seed before averaging, so seed-level variation cancels rather than adding.
    """
    train_df = variants["capped"]
    deflator = fit_market_deflator(train_df)

    def frame_for(part: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
        X = part[columns].copy()
        for col, dtype in splits.category_dtypes.items():
            if col in X.columns:
                X[col] = X[col].astype(dtype)
        return X

    # The deflator reads market_median_rolling_3m, which is in `base` for every design, so the
    # label is identical throughout. Only the inputs move.
    X_train_lvl, X_val_lvl = splits.features(train_df), splits.features(val_eval)
    y_train = detrend(splits.target(train_df), market_level(X_train_lvl, deflator))
    y_val = detrend(splits.target(val_eval), market_level(X_val_lvl, deflator))

    per_seed: dict[str, dict[int, float]] = {name: {} for name in designs}
    for seed in seeds:
        for name, extra in designs.items():
            columns = base + extra
            X_train, X_val = frame_for(train_df, columns), frame_for(val_eval, columns)

            model = xgb.XGBRegressor(
                n_estimators=cfg.n_estimators, max_depth=8, learning_rate=0.03,
                subsample=0.8, colsample_bytree=0.8, enable_categorical=True,
                tree_method="hist", objective="reg:absoluteerror", early_stopping_rounds=50,
                random_state=seed, n_jobs=-1,
            )
            model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

            predicted = retrend(model.predict(X_val), market_level(X_val_lvl, deflator))
            metrics = regression_metrics(splits.target(val_eval), predicted)
            per_seed[name][seed] = metrics["MdAPE"]
            print(f"  seed {seed}  {name:<30}{len(extra):>2} cols   "
                  f"MdAPE {metrics['MdAPE']:6.3f}%")

    rows = []
    for name, extra in designs.items():
        scores = np.array([per_seed[name][s] for s in seeds])
        gains = np.array([per_seed[baseline][s] - per_seed[name][s] for s in seeds])
        rows.append({
            label: name,
            "Columns": len(extra),
            "MdAPE mean": scores.mean(),
            "MdAPE sd": scores.std(ddof=1) if len(seeds) > 1 else np.nan,
            f"Gain vs. {baseline.lower()}": gains.mean(),
            "Gain sd": gains.std(ddof=1) if len(seeds) > 1 else np.nan,
            "Seeds won": int((gains > 0).sum()),
            "Seeds": len(seeds),
        })
    return pd.DataFrame(rows)


def prior_sale_study(splits: Splits, variants: dict[str, pd.DataFrame], cfg: Config,
                     val_eval: pd.DataFrame,
                     seeds: tuple[int, ...] = (42,)) -> pd.DataFrame:
    """What does a property's own transaction history buy, measured like any other group?

    Delivered as an ablation rather than asserted, on the same gate and the same protocol as
    the crime study, so the two verdicts are directly comparable.
    """
    available = [c for c in PRIOR_SALE_FEATURES if c in variants["capped"].columns]
    if not available:
        raise KeyError(
            "No prior-sale columns in the model frame. Run add_prior_sale_features first."
        )

    designs = {
        "No prior sale": [],
        "Prior price only": [c for c in ("prev_sale_price", "has_prev_sale") if c in available],
        "Prior price + elapsed": [c for c in (
            "prev_sale_price", "has_prev_sale", "years_since_prev_sale",
            "prev_sale_days_since_start") if c in available],
        "Full prior-sale group": available,
    }
    # FEATURES now carries PRIOR_SALE_ADOPTED, so the base has to have the whole candidate set
    # stripped out of it -- exactly as the crime study strips its own varying columns. Leaving
    # them in would both duplicate columns in the feature matrix and hand the "No prior sale"
    # baseline the very features it is meant to be measured against.
    base = [f for f in FEATURES if f not in PRIOR_SALE_FEATURES]
    return _seeded_design_study(splits, variants, cfg, val_eval, base, designs, seeds,
                                baseline="No prior sale", label="Prior-sale features")
