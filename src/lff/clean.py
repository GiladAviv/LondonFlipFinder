"""Per-source cleaning and feature construction. Lifted from section 5."""
from __future__ import annotations

import pandas as pd

from .config import Config


def clean_houses(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Normalise the price-history file and restrict it to the modelling window."""
    out = df.copy()
    out["date"] = pd.to_datetime(out["history_date"])
    out = out.rename(columns={"history_price": "price"})
    out = out[out["date"].dt.year.between(cfg.year_min, cfg.year_max)]
    out["postcode"] = out["postcode"].astype(str).str.replace(" ", "", regex=False).str.upper()

    # Scale of the dwelling. Kept NaN-aware: the gradient-boosted models consume NaN natively.
    out["total_rooms"] = out["bedrooms"] + out["livingRooms"]

    before = len(out)
    out = out.dropna(subset=["floorAreaSqM", "total_rooms"], how="all")
    out = out.drop(columns=["history_date"])
    print(f"Houses: {before:,} rows in {cfg.year_min}-{cfg.year_max} -> "
          f"{len(out):,} with size data")
    return out.reset_index(drop=True)


def build_crime_features(df: pd.DataFrame) -> pd.DataFrame:
    """Borough-month crime totals plus a leakage-safe 12-month trailing sum."""
    out = df.copy()
    out["date"] = pd.to_datetime(
        out["year"].astype(str) + "-" + out["month"].astype(str) + "-01"
    )
    agg = (
        out.groupby(["date", "borough"], observed=True)["value"]
        .sum()
        .reset_index()
        .rename(columns={"value": "crime_volume"})
        .sort_values(["borough", "date"])
    )
    # closed='left' excludes the current month, so the window is strictly historical.
    agg["crime_volume_prev_12m"] = agg.groupby("borough", observed=True)["crime_volume"].transform(
        lambda s: s.rolling(window=12, closed="left").sum()
    )
    agg["borough"] = agg["borough"].astype(str).str.upper().str.strip()
    print(f"Crime: {len(agg):,} borough-months, {agg['borough'].nunique()} boroughs")
    return agg


def build_rate_curve(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Expand sparse Bank Rate changes into a daily series covering the modelling window."""
    changes = df.copy()
    changes["date"] = pd.to_datetime(changes["Date Changed"], format="%d %b %y")
    changes = changes.rename(columns={"Rate": "interest_rate"}).sort_values("date")

    calendar = pd.DataFrame(
        {"date": pd.date_range(f"{cfg.year_min}-01-01", f"{cfg.year_max}-12-31", freq="D")}
    )
    daily = calendar.merge(changes[["date", "interest_rate"]], on="date", how="left")

    # Seed row 0 from the last change at or before the window opens, THEN forward-fill only.
    # An earlier version called .bfill() here, which propagated the first in-window rate
    # *backwards* over every preceding day -- stamping a rate onto dates before it had been
    # announced. Forward-fill alone cannot look ahead. Where no prior rate exists the leading
    # days stay NaN, which each model imputes from training data, rather than being filled
    # from the future.
    prior = changes.loc[changes["date"] <= calendar["date"].iloc[0], "interest_rate"]
    if not prior.empty:
        daily.loc[daily.index[0], "interest_rate"] = prior.iloc[-1]
    daily["interest_rate"] = daily["interest_rate"].ffill()

    print(
        f"Rates: {len(daily):,} days, "
        f"{daily['interest_rate'].min():.2f}% - {daily['interest_rate'].max():.2f}%"
    )
    return daily
