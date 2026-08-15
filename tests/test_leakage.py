"""The checks that matter: every one of these fails if a feature learns to see the future.

Section 17's `run_self_checks` runs the same probes at the end of a notebook run. These are
the versions that run in a second, on a fixture, before anything is trained.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lff.clean import build_rate_curve
from lff.features.market import add_market_features
from lff.features.registry import CATEGORICAL_FEATURES, FEATURE_GROUPS, FEATURES
from lff.features.temporal import add_temporal_features
from lff.split import chronological_split


def test_lagged_market_features_ignore_a_shock_to_their_own_month(master):
    """Multiply the final month's prices by ten. A backward-looking lag cannot move."""
    base = add_temporal_features(master)
    shocked = (base["month_year_period"] == base["month_year_period"].max()).to_numpy()

    probe = base.copy()
    probe.loc[shocked, ["price", "price_per_sqm"]] *= 10

    lag_cols = ["market_median_rolling_3m", "market_median_rolling_12m",
                "lagged_borough_median_sqm"]
    before = add_market_features(base).loc[shocked, lag_cols].reset_index(drop=True)
    after = add_market_features(probe).loc[shocked, lag_cols].reset_index(drop=True)

    for col in lag_cols:
        assert before[col].equals(after[col]), f"{col} moved when its own month was shocked"


def test_rate_curve_never_backfills(cfg):
    """A rate must not be stamped onto dates before it was announced.

    The seed row is set from the last change at or before the window opens; if no such change
    exists the leading days stay NaN. An earlier version called .bfill() here, which propagated
    the first in-window rate backwards over every preceding day.
    """
    changes = pd.DataFrame({
        "Date Changed": ["05 Mar 09", "04 Aug 16"],
        "Rate": [0.50, 0.25],
    })
    daily = build_rate_curve(changes, cfg)

    before_first_change = daily[daily["date"] < "2009-03-05"]
    assert before_first_change["interest_rate"].isna().all(), "rate leaked backwards in time"
    assert daily.loc[daily["date"] == "2009-03-05", "interest_rate"].iloc[0] == 0.50
    assert daily.loc[daily["date"] == "2016-08-03", "interest_rate"].iloc[0] == 0.50
    assert daily.loc[daily["date"] == "2016-08-04", "interest_rate"].iloc[0] == 0.25


def test_splits_are_chronologically_disjoint(master, cfg):
    df = add_market_features(add_temporal_features(master))
    splits = chronological_split(df, cfg)

    assert splits.train["date"].max() <= splits.val["date"].min()
    assert splits.val["date"].max() <= splits.calib["date"].min()
    assert splits.calib["date"].max() <= splits.test["date"].min()
    total = sum(len(p) for p in (splits.train, splits.val, splits.calib, splits.test))
    assert total == len(df), "splits must partition the frame, not sample from it"


def test_encoder_is_fitted_on_training_rows_only(master, cfg):
    """A category that appears only after the training window must fall back to the global
    mean, not acquire a value derived from its own (future) rows."""
    df = add_market_features(add_temporal_features(master))
    splits = chronological_split(df, cfg)

    unseen = pd.DataFrame({c: ["__never_seen__"] for c in CATEGORICAL_FEATURES})
    for col in FEATURES:
        if col not in unseen.columns:
            unseen[col] = np.nan

    encoded = splits.encoder.transform(unseen[FEATURES])
    for col in CATEGORICAL_FEATURES:
        assert encoded[col].iloc[0] == splits.encoder.global_mean_


def test_categorical_levels_are_pinned_from_training(master, cfg):
    df = add_market_features(add_temporal_features(master))
    splits = chronological_split(df, cfg)
    encoded = splits.features(splits.val)
    for col in CATEGORICAL_FEATURES:
        assert encoded[col].dtype == splits.category_dtypes[col]


def test_no_third_party_valuation_columns_among_predictors():
    """The source file carries saleEstimate_* and rentEstimate_* columns -- another model's
    output, and a direct view of the target."""
    banned = ("saleEstimate", "rentEstimate", "price_per_sqm")
    assert not [f for f in FEATURES if f.startswith(banned)]


def test_feature_groups_reference_real_features():
    for group, cols in FEATURE_GROUPS.items():
        missing = set(cols) - set(FEATURES)
        assert not missing, f"ablation group {group!r} names features that do not exist: {missing}"


def test_avg_room_size_is_nan_not_infinite(master):
    """total_rooms == 0 produces +/-inf, which no imputer treats as missing."""
    probe = master.copy()
    probe.loc[probe.index[:5], "total_rooms"] = 0
    out = add_temporal_features(probe)
    assert np.isfinite(out["avg_room_size"].dropna()).all()
    assert out["avg_room_size"].iloc[:5].isna().all()


def test_avg_room_size_is_not_filled_before_the_split(master):
    """Median-filling here would compute the median over validation, calibration and test rows
    and bake it into a training feature."""
    probe = master.copy()
    probe.loc[probe.index[:20], "floorAreaSqM"] = np.nan
    out = add_temporal_features(probe)
    assert out["avg_room_size"].isna().sum() >= 20
