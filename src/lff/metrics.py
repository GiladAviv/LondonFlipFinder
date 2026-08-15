"""One metric implementation, one results registry. Section 11."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from .split import Splits


def regression_metrics(y_true, y_pred) -> dict[str, float]:
    """The single metric implementation used everywhere in this notebook."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    ape = np.abs((y_true - y_pred) / y_true)
    return {
        "R2": float(r2_score(y_true, y_pred)),
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "MdAPE": float(np.median(ape) * 100),
        "MAPE": float(np.mean(ape) * 100),
        "within_25pct": float((ape <= 0.25).mean() * 100),
    }


@dataclass
class ModelBundle:
    """A trained model behind one uniform predict() -- the key to comparing like with like."""

    name: str
    trained_on: str
    predict: Callable[[pd.DataFrame], np.ndarray]
    artefacts: dict = field(default_factory=dict)


class ResultsRegistry:
    """Collects every evaluation so the leaderboard is generated, never hand-typed."""

    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(self, bundle: ModelBundle, split: str, metrics: dict[str, float]) -> dict[str, float]:
        self.rows.append({"Model": bundle.name, "Trained on": bundle.trained_on,
                          "Split": split, **metrics})
        return metrics

    def frame(self, split: str | None = None) -> pd.DataFrame:
        df = pd.DataFrame(self.rows)
        if split is not None:
            df = df[df["Split"] == split]
        return df.sort_values("MdAPE").reset_index(drop=True)


def evaluate(bundle: ModelBundle, part: pd.DataFrame, split: str,
             registry: ResultsRegistry, splits: Splits) -> dict[str, float]:
    """Score a bundle on an evaluation frame and record the result."""
    metrics = regression_metrics(splits.target(part), bundle.predict(splits.features(part)))
    registry.add(bundle, split, metrics)
    print(f"{bundle.name:<34}{split:<6}"
          f"MdAPE {metrics['MdAPE']:6.2f}%   MAE \N{POUND SIGN}{metrics['MAE']:>10,.0f}   "
          f"R2 {metrics['R2']:6.3f}")
    return metrics
