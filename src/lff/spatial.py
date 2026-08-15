"""Projection, nearest-neighbour and point-in-polygon joins. Section 6."""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from shapely.geometry import Point

from .config import Config


def to_projected_gdf(df: pd.DataFrame, cfg: Config) -> gpd.GeoDataFrame:
    """Build a metric (EPSG:27700) GeoDataFrame from whichever coordinate columns exist."""
    lookup = {str(c).lower().strip(): c for c in df.columns}

    easting, northing = lookup.get("easting"), lookup.get("northing")
    if easting and northing:
        clean = df.dropna(subset=[easting, northing]).copy()
        geometry = gpd.points_from_xy(clean[easting], clean[northing])
        return gpd.GeoDataFrame(clean, geometry=geometry, crs=cfg.bng)

    lat = next((lookup[k] for k in ("latitude", "lat", "y") if k in lookup), None)
    lon = next((lookup[k] for k in ("longitude", "lon", "lng", "x") if k in lookup), None)
    if lat and lon:
        clean = df.dropna(subset=[lat, lon]).copy()
        geometry = gpd.points_from_xy(clean[lon], clean[lat])
        return gpd.GeoDataFrame(clean, geometry=geometry, crs=cfg.wgs84).to_crs(cfg.bng)

    raise KeyError(f"No coordinate columns found. Available: {list(df.columns)}")


def parse_zone(value) -> float:
    """TfL fare zones arrive as '1', '2,3', '6,7' or '-1'. Take the innermost real zone."""
    text = str(value).strip()
    zones = [float(part) for part in text.split(",") if part.strip().lstrip("-").isdigit()]
    zones = [z for z in zones if z > 0]          # '-1' marks stations outside the zonal system
    return min(zones) if zones else np.nan


def split_station_networks(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separate the 2022 snapshot into networks that actually served the modelling window.

    Positive selection on the Underground/Overground/DLR flags keeps shared stations such as
    Paddington while dropping Elizabeth-Line-only stops (opened 2022) and Croydon tram stops.
    """
    stations = df.copy()
    stations["station_zone"] = stations["Zone"].map(parse_zone)

    def flagged(column: str) -> pd.Series:
        return stations[column].astype(str).str.strip().str.lower().eq("yes")

    underground = flagged("London Underground")
    heavy_rail = underground | flagged("London Overground") | flagged("DLR")

    excluded = len(stations) - int(heavy_rail.sum())
    print(f"Stations: {underground.sum()} Underground, {heavy_rail.sum()} heavy rail "
          f"({excluded} Elizabeth-only/tram stops excluded as post-window or non-rail)")
    return stations[underground], stations[heavy_rail]


def add_nearest_distance(
    gdf: gpd.GeoDataFrame, reference: gpd.GeoDataFrame, column: str,
    attach: dict[str, str] | None = None,
) -> gpd.GeoDataFrame:
    """Distance in metres to the closest point in `reference`, via a k-d tree.

    `attach` maps reference columns onto new output columns, carrying attributes of the nearest
    neighbour across (the fare zone of the closest station, for instance) at no extra cost.
    """
    if gdf.crs != reference.crs:
        raise ValueError(f"CRS mismatch: {gdf.crs} vs {reference.crs}")
    tree = cKDTree(np.c_[reference.geometry.x.values, reference.geometry.y.values])
    distances, neighbour = tree.query(np.c_[gdf.geometry.x.values, gdf.geometry.y.values], k=1)

    out = gdf.copy()
    out[column] = distances
    for source, destination in (attach or {}).items():
        out[destination] = reference[source].to_numpy()[neighbour]
    return out


def add_borough(gdf: gpd.GeoDataFrame, cfg: Config) -> gpd.GeoDataFrame:
    """Point-in-polygon join onto the GLA borough boundaries."""
    boroughs = gpd.read_file(cfg.boroughs_shp)
    if boroughs.crs is None or boroughs.crs.to_string() != cfg.bng:
        boroughs = boroughs.to_crs(cfg.bng)

    joined = gpd.sjoin(
        gdf.drop(columns=["index_right", "index_left", "NAME", "borough"], errors="ignore"),
        boroughs[["NAME", "geometry"]],
        how="left",
        predicate="within",
    )
    joined = joined.rename(columns={"NAME": "borough"})
    joined = joined.drop(columns=["index_right"], errors="ignore")
    joined["borough"] = joined["borough"].astype(str).str.upper().str.strip()

    unmatched = (joined["borough"] == "NAN").sum()
    print(f"Borough join: {len(joined) - unmatched:,} matched, "
          f"{unmatched:,} outside GLA boundaries")
    return joined


def add_lsoa(gdf: gpd.GeoDataFrame, boundaries: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Point-in-polygon join onto LSOA (2011) boundaries -- the crime file's native grain.

    Same shape as `add_borough`, against 4,835 polygons instead of 33.
    """
    if gdf.crs != boundaries.crs:
        raise ValueError(f"CRS mismatch: {gdf.crs} vs {boundaries.crs}")

    joined = gpd.sjoin(
        gdf.drop(columns=["index_right", "index_left", "LSOA11CD", "lsoa_code"],
                 errors="ignore"),
        boundaries[["LSOA11CD", "geometry"]],
        how="left",
        predicate="within",
    )
    joined = joined.rename(columns={"LSOA11CD": "lsoa_code"})
    joined = joined.drop(columns=["index_right"], errors="ignore")

    # A property on a boundary line can match two polygons; keep the first and note it.
    duplicated = joined.index.duplicated()
    if duplicated.any():
        print(f"   {duplicated.sum():,} properties matched two LSOA polygons "
              f"(boundary-line coordinates); keeping the first")
        joined = joined[~duplicated]

    unmatched = joined["lsoa_code"].isna().sum()
    print(f"LSOA join: {len(joined) - unmatched:,} matched, {unmatched:,} unmatched")
    return joined


def add_distance_to_centre(gdf: gpd.GeoDataFrame, cfg: Config) -> gpd.GeoDataFrame:
    """Straight-line metres to Charing Cross, the conventional centre of London."""
    centre = (
        gpd.GeoSeries([Point(-0.1281, 51.5080)], crs=cfg.wgs84).to_crs(cfg.bng).iloc[0]
    )
    out = gdf.copy()
    out["distance_to_center_m"] = np.hypot(
        out.geometry.x.values - centre.x, out.geometry.y.values - centre.y
    )
    return out
