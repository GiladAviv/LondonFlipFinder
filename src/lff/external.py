"""Third-party sources fetched at build time and cached under `data/external/`.

Everything in `data/` proper comes from one release archive and is reproduced byte for byte.
These do not: they are pulled live from ONS and DfE, so each fetch records the URL and the
retrieval date in a sidecar JSON, and the run manifest carries those alongside the metrics.
A source that moves or changes shape should be visible in a diff, not silently absorbed.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

from .config import Config

# ONS Open Geography Portal. The 2011 vintage is the one that matches the crime file's
# lsoa_code column -- 2021 LSOAs were re-cut and roughly 10% of codes changed.
LSOA_SERVICE = (
    "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
    "Lower_layer_Super_Output_Areas_Dec_2011_Boundaries_Full_Clipped_BFC_EW_V3_2022/"
    "FeatureServer/0"
)
# Greater London plus a margin. The join is point-in-polygon, so pulling a fringe of
# out-of-London LSOAs costs nothing and guarantees no edge property goes unmatched.
LONDON_BBOX = "-0.55,51.25,0.35,51.72"

GIAS_URL = (
    "https://ea-edubase-api-prod.azurewebsites.net/edubase/downloads/public/"
    "edubasealldata{date}.csv"
)


def _provenance(path: Path, url: str, rows: int) -> None:
    """Record where a cached file came from and when."""
    path.with_suffix(path.suffix + ".source.json").write_text(json.dumps({
        "url": url,
        "retrieved": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "rows": rows,
    }, indent=2))


def read_provenance(cfg: Config) -> dict[str, dict]:
    """Every cached external source, for the run manifest."""
    if not cfg.external_dir.exists():
        return {}
    return {
        p.name.replace(".source.json", ""): json.loads(p.read_text())
        for p in sorted(cfg.external_dir.glob("*.source.json"))
    }


def fetch_lsoa_boundaries(cfg: Config, refresh: bool = False) -> gpd.GeoDataFrame:
    """London LSOA (2011) polygons, projected to BNG.

    Unlocks the crime file at its native resolution: 4,835 LSOAs against the 33 boroughs the
    pipeline currently aggregates them into, a 147x gain that costs one spatial join.
    """
    if cfg.lsoa_boundaries.exists() and not refresh:
        gdf = gpd.read_file(cfg.lsoa_boundaries)
        print(f"LSOA boundaries (cached): {len(gdf):,} areas")
        return gdf

    cfg.external_dir.mkdir(parents=True, exist_ok=True)
    print("Fetching LSOA 2011 boundaries from ONS Open Geography Portal...")

    frames, offset, page = [], 0, 2000
    while True:
        resp = requests.get(f"{LSOA_SERVICE}/query", timeout=300, params={
            "where": "1=1",
            "geometry": LONDON_BBOX,
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "LSOA11CD,LSOA11NM",
            "returnGeometry": "true",
            "outSR": "27700",
            "resultOffset": offset,
            "resultRecordCount": page,
            "f": "geojson",
        })
        resp.raise_for_status()
        chunk = gpd.GeoDataFrame.from_features(resp.json()["features"], crs=cfg.bng)
        if chunk.empty:
            break
        frames.append(chunk)
        print(f"   {sum(len(f) for f in frames):,} areas")
        if len(chunk) < page:
            break
        offset += page

    gdf = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=cfg.bng)
    gdf = gdf.drop_duplicates(subset="LSOA11CD").reset_index(drop=True)
    gdf.to_file(cfg.lsoa_boundaries, driver="GPKG")
    _provenance(cfg.lsoa_boundaries, LSOA_SERVICE, len(gdf))
    print(f"LSOA boundaries: {len(gdf):,} areas cached to {cfg.lsoa_boundaries.name}")
    return gdf


def fetch_gias_schools(cfg: Config, refresh: bool = False) -> pd.DataFrame:
    """DfE Get Information about Schools: URN -> coordinates.

    The local scorecard carries the Ofsted grade and its inspection date but no location;
    GIAS carries the location but not the grade. Joined on URN they give a school-quality
    surface that can be read as of any sale date.
    """
    if cfg.gias_schools.exists() and not refresh:
        df = pd.read_csv(cfg.gias_schools)
        print(f"GIAS schools (cached): {len(df):,} schools")
        return df

    cfg.external_dir.mkdir(parents=True, exist_ok=True)
    columns = ["URN", "EstablishmentName", "Postcode", "Easting", "Northing",
               "PhaseOfEducation (name)", "EstablishmentStatus (name)", "OpenDate", "CloseDate"]

    # GIAS publishes a dated file each day and keeps no "latest" alias; walk back until one
    # resolves rather than pinning a date that will 404 in a month.
    today = pd.Timestamp.now(tz="UTC").normalize()
    last_error: Exception | None = None
    for back in range(0, 14):
        url = GIAS_URL.format(date=(today - pd.Timedelta(days=back)).strftime("%Y%m%d"))
        try:
            resp = requests.get(url, timeout=300)
            resp.raise_for_status()
            path = cfg.external_dir / "gias_raw.csv"
            path.write_bytes(resp.content)
            df = pd.read_csv(path, encoding="latin-1", low_memory=False)
            keep = [c for c in columns if c in df.columns]
            df = df[keep]
            df.to_csv(cfg.gias_schools, index=False)
            path.unlink()
            _provenance(cfg.gias_schools, url, len(df))
            print(f"GIAS schools: {len(df):,} establishments from {url.rsplit('/', 1)[-1]}")
            return df
        except Exception as exc:  # noqa: BLE001 - any failure means try the previous day
            last_error = exc

    raise RuntimeError(f"No GIAS snapshot resolved in the last 14 days: {last_error}")
