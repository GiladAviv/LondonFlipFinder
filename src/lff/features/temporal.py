"""Calendar position and dwelling-scale ratios. Section 9."""
from __future__ import annotations

import numpy as np
import pandas as pd


def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Calendar position and dwelling-scale ratios -- every value derived from its own row."""
    out = df.sort_values("date").reset_index(drop=True)
    out["month_year_period"] = out["date"].dt.to_period("M")
    out["days_since_start"] = (out["date"] - out["date"].min()).dt.days

    month = out["date"].dt.month
    out["month_sin"] = np.sin(2 * np.pi * month / 12)
    out["month_cos"] = np.cos(2 * np.pi * month / 12)

    # total_rooms == 0 produces +/-inf rather than NaN, so convert explicitly.
    out["avg_room_size"] = (out["floorAreaSqM"] / out["total_rooms"]).replace(
        [np.inf, -np.inf], np.nan
    )
    # Deliberately NOT median-filled. This function runs on the whole table, before the split,
    # so a median here would be computed over validation, calibration and test rows and then
    # baked into a training feature -- textbook leakage. Left as NaN for the same reason crime
    # is (section 7): the GBDTs handle it natively and Ridge imputes inside a pipeline fitted
    # on the training split alone.
    return out
