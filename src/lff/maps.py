"""Choropleths and the crime-resolution figures for section 8.2.

Kept apart from plots.py because these need geometry, and because they exist to answer a
question the borough-grain data could not even pose: London has 33 boroughs and 4,835 LSOAs,
so a borough choropleth has 33 patches and hides every within-borough contrast. That contrast
is where a crime-price relationship, if there is one, would live.
"""
from __future__ import annotations

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

from .plots import DIVERGING, MUTED, SERIES, style_axis

# Sequential ramps: one hue, light to dark, for continuous magnitude. Blue is the default
# sequential hue; a second sequential context on the same screen takes the next categorical
# slot's hue (orange) as its own one-hue ramp, so the two panels below can never be misread
# as sharing a scale.
#
# The blue steps are the documented ramp. The orange ones were generated rather than picked
# by eye: hue pinned to categorical slot 2 (OKLCH H 40.6) with blue's lightness and chroma
# profile reused, which holds the hue spread to 0.9 degrees against blue's 4.1. Both are
# monotonic in lightness by construction.
SEQ_BLUE = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5",
            "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
SEQ_ORANGE = ["#f9d7cb", "#f2c4b4", "#efb19b", "#e89d83", "#e28969", "#da7550", "#d45e2f",
              "#c54e1c", "#af4517", "#9c390c", "#883008", "#752601", "#611f02"]

BLUES = LinearSegmentedColormap.from_list("lff_blue", SEQ_BLUE)
ORANGES = LinearSegmentedColormap.from_list("lff_orange", SEQ_ORANGE)


def lsoa_price_summary(master: pd.DataFrame, min_sales: int = 5) -> pd.DataFrame:
    """Median price per sqm by LSOA, over LSOAs with enough sales for a median to mean anything.

    Below a handful of transactions an LSOA median is one or two properties, which renders as
    map noise indistinguishable from signal.
    """
    summary = master.groupby("lsoa_code", observed=True).agg(
        median_sqm=("price_per_sqm", "median"),
        sales=("price", "size"),
        borough=("borough", "first"),
    ).reset_index()
    kept = summary[summary["sales"] >= min_sales]
    print(f"LSOA price summary: {len(kept):,} of {len(summary):,} LSOAs with >= {min_sales} sales")
    return kept


def lsoa_crime_summary(lsoa_crime: pd.DataFrame) -> pd.DataFrame:
    """Mean monthly crime per LSOA across the window, plus annualised density per km2."""
    return (
        lsoa_crime.groupby("lsoa_code", observed=True)
        .agg(crime_per_month=("lsoa_crime", "mean"),
             burglary_per_month=("lsoa_crime_burglary", "mean"),
             area_km2=("lsoa_area_km2", "first"))
        .reset_index()
        .assign(crime_density=lambda d: d["crime_per_month"] * 12 / d["area_km2"])
    )


def plot_crime_and_price_maps(master: pd.DataFrame, lsoa_crime: pd.DataFrame,
                              boundaries: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Two choropleths at LSOA grain: what a place costs, and how much crime it records."""
    price = lsoa_price_summary(master)
    crime = lsoa_crime_summary(lsoa_crime)
    gdf = (
        boundaries.rename(columns={"LSOA11CD": "lsoa_code"})
        .merge(price, on="lsoa_code", how="inner")
        .merge(crime, on="lsoa_code", how="left")
    )

    fig, (left, right) = plt.subplots(1, 2, figsize=(16, 8))

    # Quantile classing, not equal-interval: both distributions are heavily right-skewed and
    # equal intervals would drop nearly every LSOA into the lightest class.
    gdf.plot(column="median_sqm", cmap=BLUES, scheme="quantiles", k=7, ax=left,
             linewidth=0, legend=True,
             legend_kwds={"loc": "lower right", "fontsize": 8, "frameon": False,
                          "title": "\N{POUND SIGN}/sqm"})
    left.set_title("Median price per square metre", fontsize=13, fontweight="bold")

    gdf.plot(column="crime_density", cmap=ORANGES, scheme="quantiles", k=7, ax=right,
             linewidth=0, legend=True,
             legend_kwds={"loc": "lower right", "fontsize": 8, "frameon": False,
                          "title": "crimes/km\N{SUPERSCRIPT TWO}/yr"})
    right.set_title("Crime density", fontsize=13, fontweight="bold")

    for ax in (left, right):
        ax.set_axis_off()

    fig.suptitle(f"London at LSOA grain: {len(gdf):,} areas, not 33 boroughs",
                 fontsize=16, fontweight="bold")
    plt.tight_layout()
    plt.show()

    print("Both maps run darkest in the centre. That is the confound the next figure removes: "
          "central London is simultaneously the most expensive and the most crime-recording "
          "part of the city, so a raw crime-price correlation largely measures centrality.")
    return gdf


def plot_crime_within_borough(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """The partial relationship: price against crime, with borough differences removed.

    A scatter of raw LSOA price against raw LSOA crime is confounded by everything "where"
    encodes, centrality above all. Subtracting each borough's own mean from both variables
    leaves the within-borough contrast, which is the comparison a buyer actually faces: two
    streets in the same borough, one safer than the other.
    """
    frame = gdf[["lsoa_code", "borough", "median_sqm", "crime_density"]].dropna().copy()
    frame["log_sqm"] = np.log(frame["median_sqm"])
    frame["log_crime"] = np.log(frame["crime_density"].clip(lower=1))

    for col in ("log_sqm", "log_crime"):
        frame[f"{col}_demeaned"] = frame[col] - frame.groupby("borough")[col].transform("mean")

    fig, (raw, partial) = plt.subplots(1, 2, figsize=(15, 6))

    raw.scatter(frame["log_crime"], frame["log_sqm"], s=9, alpha=0.35,
                color=SERIES[0], edgecolors="none")
    r_raw = frame["log_crime"].corr(frame["log_sqm"])
    raw.set(title=f"Raw, across all boroughs (r = {r_raw:+.2f})",
            xlabel="log crime density", ylabel="log median \N{POUND SIGN}/sqm")
    style_axis(raw)

    partial.scatter(frame["log_crime_demeaned"], frame["log_sqm_demeaned"], s=9, alpha=0.35,
                    color=SERIES[1], edgecolors="none")
    r_within = frame["log_crime_demeaned"].corr(frame["log_sqm_demeaned"])
    partial.set(title=f"Within borough, both variables de-meaned (r = {r_within:+.2f})",
                xlabel="log crime density, minus borough mean",
                ylabel="log \N{POUND SIGN}/sqm, minus borough mean")
    style_axis(partial)

    for ax, x, y in ((raw, frame["log_crime"], frame["log_sqm"]),
                     (partial, frame["log_crime_demeaned"], frame["log_sqm_demeaned"])):
        fit = np.polyfit(x, y, 1)
        line = np.linspace(x.min(), x.max(), 50)
        ax.plot(line, np.polyval(fit, line), color=MUTED, linestyle="--", linewidth=1.5)

    fig.suptitle("Does crime price into London property?", fontsize=16, fontweight="bold")
    plt.tight_layout()
    plt.show()

    print(f"Across boroughs r = {r_raw:+.2f}; within borough r = {r_within:+.2f}.")
    return frame


def plot_crime_change(master: pd.DataFrame, lsoa_crime: pd.DataFrame,
                      early: tuple[int, int] = (2008, 2010),
                      late: tuple[int, int] = (2014, 2016)) -> pd.DataFrame:
    """Change against change: does an LSOA whose crime fell see its prices rise faster?

    The strongest of the three views. Differencing removes every time-invariant feature of a
    place -- architecture, parks, distance to the centre, reputation -- which no
    cross-sectional scatter can separate from crime.
    """
    price = master.copy()
    price["year"] = price["date"].dt.year

    def window(df: pd.DataFrame, span: tuple[int, int], col: str, value: str) -> pd.DataFrame:
        sub = df[df["year"].between(*span)]
        return (sub.groupby("lsoa_code", observed=True)[col]
                .agg(["median", "size"])
                .rename(columns={"median": value, "size": f"n_{value}"})
                .reset_index())

    p_early = window(price, early, "price_per_sqm", "sqm_early")
    p_late = window(price, late, "price_per_sqm", "sqm_late")

    crime = lsoa_crime.copy()
    crime["year"] = crime["date"].dt.year
    c_early = window(crime, early, "lsoa_crime", "crime_early")
    c_late = window(crime, late, "lsoa_crime", "crime_late")

    frame = (p_early.merge(p_late, on="lsoa_code")
             .merge(c_early, on="lsoa_code").merge(c_late, on="lsoa_code"))
    # Both windows need enough sales for a median to be a median, not one transaction.
    frame = frame[(frame["n_sqm_early"] >= 5) & (frame["n_sqm_late"] >= 5)]
    frame = frame[frame["crime_early"] > 0]

    frame["price_growth"] = frame["sqm_late"] / frame["sqm_early"] - 1
    frame["crime_change"] = frame["crime_late"] / frame["crime_early"] - 1

    fig, ax = plt.subplots(figsize=(11, 7))
    scatter = ax.scatter(frame["crime_change"] * 100, frame["price_growth"] * 100,
                         s=18, alpha=0.55, c=frame["crime_change"] * 100,
                         cmap=DIVERGING, edgecolors="none")
    fit = np.polyfit(frame["crime_change"], frame["price_growth"], 1)
    line = np.linspace(frame["crime_change"].min(), frame["crime_change"].max(), 50)
    ax.plot(line * 100, np.polyval(fit, line) * 100, color=MUTED, linestyle="--", linewidth=1.8)

    r = frame["crime_change"].corr(frame["price_growth"])
    ax.set(title=f"LSOA change, {early[0]}-{early[1]} to {late[0]}-{late[1]}  "
                 f"(r = {r:+.2f}, n = {len(frame):,})",
           xlabel="Change in monthly crime (%)",
           ylabel="Growth in median \N{POUND SIGN}/sqm (%)")
    ax.axvline(0, color=MUTED, linewidth=0.8, alpha=0.5)
    style_axis(ax)
    fig.colorbar(scatter, ax=ax, label="crime change (%)", shrink=0.8)

    fig.suptitle("Differenced view: time-invariant features of a place cancel out",
                 fontsize=15, fontweight="bold")
    plt.tight_layout()
    plt.show()

    print(f"Correlation between crime change and price growth: r = {r:+.2f} over "
          f"{len(frame):,} LSOAs.")
    return frame


def plot_error_by_lsoa(scan: pd.DataFrame, master: pd.DataFrame,
                       boundaries: gpd.GeoDataFrame, min_rows: int = 5) -> gpd.GeoDataFrame:
    """Where the model is wrong, geographically.

    Signed percentage error, so the ramp is diverging: blue where the model under-values, red
    where it over-values, neutral grey at zero. A sequential ramp would hide the sign, which
    is the whole diagnostic.
    """
    joined = scan.join(master[["lsoa_code"]], how="left")
    joined["signed_pct"] = (
        (joined["actual_price"] - joined["predicted_value"]) / joined["actual_price"] * 100
    )
    by_lsoa = (
        joined.groupby("lsoa_code", observed=True)["signed_pct"]
        .agg(["median", "size"])
        .rename(columns={"median": "median_error", "size": "rows"})
        .reset_index()
    )
    by_lsoa = by_lsoa[by_lsoa["rows"] >= min_rows]

    gdf = boundaries.rename(columns={"LSOA11CD": "lsoa_code"}).merge(
        by_lsoa, on="lsoa_code", how="inner"
    )
    bound = float(np.nanpercentile(np.abs(gdf["median_error"]), 95))

    fig, ax = plt.subplots(figsize=(11, 9))
    gdf.plot(column="median_error", cmap=DIVERGING, vmin=-bound, vmax=bound, ax=ax,
             linewidth=0, legend=True,
             legend_kwds={"label": "median signed error (%)", "shrink": 0.6})
    ax.set_axis_off()
    ax.set_title(f"Median signed error by LSOA, held-out test set "
                 f"({len(gdf):,} areas with >= {min_rows} sales)",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.show()

    worst = gdf.reindex(gdf["median_error"].abs().sort_values(ascending=False).index).head(5)
    print("Largest median errors by LSOA:")
    for _, row in worst.iterrows():
        print(f"   {row['lsoa_code']}  {row['median_error']:+6.1f}%  ({int(row['rows'])} sales)")
    return gdf
