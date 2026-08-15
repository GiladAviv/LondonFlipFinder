"""Strictly-lagged market momentum and local price level. Section 9."""
from __future__ import annotations

import pandas as pd


def add_market_features(df: pd.DataFrame) -> pd.DataFrame:
    """Market momentum and localised price level -- both strictly lagged."""
    out = df.copy()

    monthly = (
        out.groupby("month_year_period")["price"].median().sort_index().to_frame("monthly_median")
    )
    # .shift(1) removes the current month *before* the window opens, so a month's own
    # median can never appear among its own predictors.
    shifted = monthly["monthly_median"].shift(1)
    monthly["market_median_rolling_3m"] = shifted.rolling(3, min_periods=1).median()
    monthly["market_median_rolling_12m"] = shifted.rolling(12, min_periods=1).median()

    borough_sqm = (
        out.groupby(["month_year_period", "borough"], observed=True)["price_per_sqm"]
        .median()
        .reset_index()
        .rename(columns={"price_per_sqm": "lagged_borough_median_sqm"})
    )
    # Stamp each month's borough level onto the FOLLOWING month.
    borough_sqm["month_year_period"] = borough_sqm["month_year_period"] + 1

    out = out.merge(
        monthly[["market_median_rolling_3m", "market_median_rolling_12m"]],
        on="month_year_period", how="left",
    )
    out = out.merge(borough_sqm, on=["month_year_period", "borough"], how="left")
    return out
