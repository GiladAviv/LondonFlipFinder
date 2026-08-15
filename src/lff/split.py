"""Chronological partitioning, encoding and training variants. Section 10."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from .config import Config
from .features.registry import CATEGORICAL_FEATURES, FEATURES, TARGET


class SmoothedTargetEncoder:
    """Mean-target encoding with shrinkage toward the global mean. Fitted on training data only."""

    def __init__(self, columns: Sequence[str], smoothing: int = 10):
        self.columns = list(columns)
        self.smoothing = smoothing
        self.mappings_: dict[str, pd.Series] = {}
        self.global_mean_: float = np.nan

    def fit(self, X: pd.DataFrame, y: pd.Series) -> SmoothedTargetEncoder:
        self.global_mean_ = float(y.mean())
        frame = X[self.columns].astype(object).assign(_target=np.asarray(y, dtype=float))
        for col in self.columns:
            stats = frame.groupby(col, observed=True)["_target"].agg(["count", "mean"])
            self.mappings_[col] = (
                (stats["count"] * stats["mean"] + self.smoothing * self.global_mean_)
                / (stats["count"] + self.smoothing)
            )
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        out = X.copy()
        for col in self.columns:
            out[col] = out[col].astype(object).map(self.mappings_[col]).astype(float)
            out[col] = out[col].fillna(self.global_mean_)  # categories unseen in training
        return out.apply(pd.to_numeric, errors="coerce")


@dataclass(frozen=True)
class Splits:
    """Four chronologically ordered frames plus fitted encoders.

    train fits the model. val drives early stopping and model selection. calib is touched by
    nothing else -- it exists purely so conformal calibration never runs on data the model was
    tuned against. test is never used to fit or choose anything; it is read only to report
    performance, in sections 14, 14.1 and 15.
    """

    train: pd.DataFrame
    val: pd.DataFrame
    calib: pd.DataFrame
    test: pd.DataFrame
    category_dtypes: dict
    encoder: SmoothedTargetEncoder

    def features(self, part: pd.DataFrame) -> pd.DataFrame:
        """Feature matrix with training-pinned categorical levels."""
        X = part[FEATURES].copy()
        for col, dtype in self.category_dtypes.items():
            X[col] = X[col].astype(dtype)
        return X

    def target(self, part: pd.DataFrame) -> pd.Series:
        return part[TARGET]


def chronological_split(df: pd.DataFrame, cfg: Config) -> Splits:
    """Split by time into four slices, then fit every encoder on the training slice alone."""
    ordered = df.sort_values("date").reset_index(drop=True)
    n = len(ordered)
    train_end = int(n * cfg.train_frac)
    val_end = train_end + int(n * cfg.val_frac)
    calib_end = val_end + int(n * cfg.calib_frac)

    train = ordered.iloc[:train_end]
    val = ordered.iloc[train_end:val_end]
    calib = ordered.iloc[val_end:calib_end]
    test = ordered.iloc[calib_end:]

    category_dtypes = {
        col: pd.CategoricalDtype(categories=sorted(train[col].dropna().astype(str).unique()))
        for col in CATEGORICAL_FEATURES
    }
    for part in (train, val, calib, test):
        for col in CATEGORICAL_FEATURES:
            part.loc[:, col] = part[col].astype(str)

    encoder = SmoothedTargetEncoder(CATEGORICAL_FEATURES, cfg.target_encoding_smoothing)
    encoder.fit(train[FEATURES], train[TARGET])

    splits = Splits(train, val, calib, test, category_dtypes, encoder)
    for name, part in (("train", train), ("val", val), ("calib", calib), ("test", test)):
        print(f"{name:<6}{len(part):>7,} rows   {part['date'].min():%Y-%m-%d} -> "
              f"{part['date'].max():%Y-%m-%d}")
    return splits


def training_variants(splits: Splits, cfg: Config) -> dict[str, pd.DataFrame]:
    """Three training sets over one fixed evaluation universe."""
    raw = splits.train
    capped = raw[raw[TARGET] <= cfg.price_cap]

    # IsolationForest is fitted on TRAINING rows only and filters TRAINING rows only.
    anomaly_cols = ["floorAreaSqM", "total_rooms", TARGET,
                    "distance_to_underground_m", "lagged_borough_median_sqm"]
    fit_frame = capped[anomaly_cols].dropna()
    forest = IsolationForest(
        n_estimators=100, contamination=cfg.iso_contamination, random_state=cfg.seed, n_jobs=-1
    ).fit(fit_frame)

    # Drop ONLY the rows the forest actually flags. An earlier version kept just the rows that
    # survived `fit_frame`, which silently also deleted every row with a NaN in any anomaly
    # column -- including the whole first month, where lagged_borough_median_sqm does not exist
    # yet. That made "cleaned" mean "anomalies removed AND the front of the window removed", so
    # capped-vs-cleaned was never a clean comparison of anomaly removal alone.
    flagged = fit_frame.index[forest.predict(fit_frame) == -1]
    cleaned = capped.drop(index=flagged)

    variants = {"raw": raw, "capped": capped, "cleaned": cleaned}
    for name, frame in variants.items():
        print(f"{name:<9}{len(frame):>7,} training rows")
    print(f"\nIsolationForest scored {len(fit_frame):,} of {len(capped):,} capped training rows "
          f"({len(capped) - len(fit_frame):,} skipped for missing values, kept as-is) and flagged "
          f"{len(flagged):,} anomalies ({cfg.iso_contamination:.0%} target rate); "
          f"validation and test are untouched.")
    return variants
