"""Spatial features for live listings, reusing lff.spatial directly rather than reimplementing
its k-d tree / point-in-polygon joins.

KNOWN LIMITATION (documented here, surfaced again in compare.py's caveat block): the station
GeoDataFrames passed in were filtered by lff.spatial.split_station_networks to the network that
existed 2008-2016 (spatial.py:41-59). Any post-2016 station -- the Elizabeth Line, any DLR/
Overground extension -- is invisible to distance_to_underground_m/distance_to_transit_m here, so
a genuinely well-connected 2026 property can look artificially far from transit.
"""
from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

_SRC = Path(__file__).resolve().parents[2] / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from lff.config import Config
from lff.spatial import add_borough, add_distance_to_centre, add_nearest_distance, to_projected_gdf


def add_spatial_features(
    listings: pd.DataFrame, cfg: Config,
    underground_gdf: gpd.GeoDataFrame, heavy_rail_gdf: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """listings must have latitude/longitude columns. Returns listings + the spatial feature
    columns the model needs: distance_to_underground_m, distance_to_transit_m, station_zone,
    distance_to_center_m, borough, outcode."""
    listings = listings.copy()
    listings["outcode"] = (
        listings["postcode"].astype(str).str.strip().str.split().str[0].str.upper()
    )

    gdf = to_projected_gdf(listings, cfg)
    gdf = add_nearest_distance(gdf, underground_gdf, "distance_to_underground_m",
                               attach={"station_zone": "station_zone"})
    gdf = add_nearest_distance(gdf, heavy_rail_gdf, "distance_to_transit_m")
    gdf = add_distance_to_centre(gdf, cfg)
    gdf = add_borough(gdf, cfg)

    missing_borough = gdf["borough"].isna().sum()
    if missing_borough:
        print(f"WARNING: {missing_borough} listing(s) fell outside every borough polygon "
              f"(likely just outside Greater London) -- borough will be NaN for those rows")

    return pd.DataFrame(gdf.drop(columns="geometry"))
