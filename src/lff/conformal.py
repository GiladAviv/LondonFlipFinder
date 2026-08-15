"""Split conformal safety bound and the flip scanner. Section 15."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .metrics import ModelBundle
from .split import Splits


def calibrate_conformal(bundle: ModelBundle, part: pd.DataFrame, splits: Splits,
                        alpha: float) -> float:
    """Lower-tail quantile of the actual/predicted ratio -- the safety multiplier."""
    predicted = bundle.predict(splits.features(part))
    ratios = splits.target(part).to_numpy(dtype=float) / predicted
    q = float(np.quantile(ratios, alpha))
    print(f"Calibrated on {len(part):,} properties")
    print(f"Safety multiplier q_{int(alpha * 100)} = {q:.4f}")
    print(f"Interpretation: floor = prediction x {q:.2%}, "
          f"expected to hold for {1 - alpha:.0%} of properties")
    return q


def scan_for_flips(bundle: ModelBundle, part: pd.DataFrame, splits: Splits,
                   q: float) -> pd.DataFrame:
    """Apply the floor to unseen stock and report where price sits below it."""
    predicted = bundle.predict(splits.features(part))
    actual = splits.target(part).to_numpy(dtype=float)
    floor = predicted * q

    scan = pd.DataFrame({
        "borough": part["borough"].to_numpy(),
        "date": part["date"].to_numpy(),
        "predicted_value": predicted,
        "safe_lower_bound": floor,
        "actual_price": actual,
    }, index=part.index)
    scan["is_flip"] = scan["actual_price"] < scan["safe_lower_bound"]
    scan["margin"] = scan["safe_lower_bound"] - scan["actual_price"]
    return scan
