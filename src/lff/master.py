"""Join every source into one chronologically sorted table. Section 7."""
from __future__ import annotations

import json

import pandas as pd

from .config import Config
from .spatial import (
    add_borough,
    add_distance_to_centre,
    add_nearest_distance,
    split_station_networks,
    to_projected_gdf,
)

PIPELINE_VERSION = 4  # bump whenever build_master_table's logic changes


def _cache_key(cfg: Config) -> str:
    """Identity of a cached table: the pipeline logic plus every filter that shaped it."""
    return json.dumps({
        "pipeline_version": PIPELINE_VERSION, "year_min": cfg.year_min, "year_max": cfg.year_max,
        "min_price_per_sqm": cfg.min_price_per_sqm,
    }, sort_keys=True)


def build_master_table(
    cfg: Config,
    houses: pd.DataFrame,
    crime: pd.DataFrame,
    rates: pd.DataFrame,
    stations: pd.DataFrame,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Join houses + stations + boroughs + crime + rates into one chronologically sorted table."""
    key_path = cfg.cache_parquet.with_suffix(".key.json")
    if use_cache and cfg.cache_parquet.exists() and key_path.exists():
        if key_path.read_text() == _cache_key(cfg):
            cached = pd.read_parquet(cfg.cache_parquet)
            print(f"Loaded cached master table: {cached.shape}")
            return cached
        print("Cache key mismatch (pipeline or filters changed) -- rebuilding.")

    underground, heavy_rail = split_station_networks(stations)
    gdf_houses = to_projected_gdf(houses, cfg)
    gdf_underground = to_projected_gdf(underground, cfg)
    gdf_transit = to_projected_gdf(heavy_rail, cfg)
    print(f"Projected {len(gdf_houses):,} properties to {cfg.bng}")

    # Two distinct questions: is this a tube flat, and does it have any rail link at all?
    gdf_houses = add_nearest_distance(
        gdf_houses, gdf_underground, "distance_to_underground_m",
        attach={"station_zone": "station_zone"},
    )
    gdf_houses = add_nearest_distance(gdf_houses, gdf_transit, "distance_to_transit_m")
    gdf_houses = add_distance_to_centre(gdf_houses, cfg)
    gdf_houses = add_borough(gdf_houses, cfg)

    df = pd.DataFrame(gdf_houses.drop(columns="geometry"))
    df["price_per_sqm"] = df["price"] / df["floorAreaSqM"]
    df["month_year"] = df["date"].dt.to_period("M").dt.to_timestamp()
    crime_key = df["month_year"] - pd.DateOffset(months=1)

    df = df.merge(rates, on="date", how="left")
    df = df.assign(_crime_key=crime_key).merge(
        crime, left_on=["_crime_key", "borough"], right_on=["date", "borough"],
        how="left", suffixes=("", "_crime"),
    ).drop(columns=["_crime_key", "date_crime"], errors="ignore")

    # Crime stays NaN where no lagged window exists (e.g. 2008, before 12 months of
    # history accumulate). Median-filling here would inject a statistic computed over the
    # whole period -- including the future -- into early rows. Each model imputes instead:
    # the GBDTs natively, Ridge via a SimpleImputer fitted on the training split only.
    before = len(df)
    df = df[df["borough"] != "NAN"]
    print(f"Dropped {before - len(df):,} properties outside the GLA boundary")

    before = len(df)
    df = df[df["price_per_sqm"] >= cfg.min_price_per_sqm]
    print(f"Ratio filter (>= \N{POUND SIGN}{cfg.min_price_per_sqm:,.0f}/sqm): "
          f"{before:,} -> {len(df):,}")

    before = len(df)
    df = df.drop_duplicates(subset=["date", "floorAreaSqM", "latitude", "longitude", "price"])
    print(f"Deduplication: {before:,} -> {len(df):,}")

    df = df.sort_values("date").reset_index(drop=True)
    cfg.artifact_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cfg.cache_parquet, index=False)
    key_path.write_text(_cache_key(cfg))
    print(f"Master table: {df.shape}  ({df['date'].min():%Y-%m} to {df['date'].max():%Y-%m})")
    return df
