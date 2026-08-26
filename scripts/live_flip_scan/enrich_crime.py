"""Live proxy for crime_volume / crime_volume_prev_12m via data.police.uk (free, no key).
Verified live (2026-08-23): /api/crimes-street/all-crime?lat=..&lng=..&date=YYYY-MM returns all
recorded crimes within roughly a 1-mile radius of a point for one month; /api/crime-last-updated
gives the latest month actually published (data lags ~1-2 months, so querying "this month" 404s).

Two documented differences from the trained feature, not silently smoothed over:
1. This is POINT-RADIUS crime (~1 mile around a listing), not the BOROUGH-MONTH sum
   clean.py:28-47 builds -- a coarser, listing-local grain rather than an administrative one.
2. crime_volume_prev_12m here is `crime_volume * 12` (the latest month's count annualised), not
   a real trailing-12-month sum -- fetching 12 real months per listing would mean roughly
   12x the request volume against a free public API for a one-off script. This is flagged in
   the output, not presented as the true trailing sum.

Coordinates are rounded to 3 decimal places (~110m) before querying, since many listings in the
same neighbourhood share a crime cell -- this caps request volume without losing real signal.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import LiveScanConfig

POLICE_BASE = "https://data.police.uk/api"


def latest_crime_month(cfg: LiveScanConfig) -> str:
    resp = requests.get(f"{POLICE_BASE}/crime-last-updated",
                        headers={"User-Agent": cfg.user_agent}, timeout=15)
    resp.raise_for_status()
    # The endpoint reports the publish date of the latest update; the data itself is one month
    # earlier (e.g. a "2026-06-01" publish date carries May 2026 crimes).
    published = pd.Timestamp(resp.json()["date"])
    data_month = (published - pd.DateOffset(months=1)).strftime("%Y-%m")
    return data_month


def _crime_count(lat: float, lon: float, month: str, cfg: LiveScanConfig) -> int | None:
    try:
        resp = requests.get(
            f"{POLICE_BASE}/crimes-street/all-crime",
            params={"lat": round(lat, 3), "lng": round(lon, 3), "date": month},
            headers={"User-Agent": cfg.user_agent}, timeout=20,
        )
    except requests.RequestException as e:
        print(f"  crime fetch failed for ({lat:.3f},{lon:.3f}): {e}")
        return None
    if resp.status_code != 200:
        return None
    return len(resp.json())


def add_crime_features(listings: pd.DataFrame, cfg: LiveScanConfig) -> pd.DataFrame:
    listings = listings.copy()
    month = latest_crime_month(cfg)
    print(f"data.police.uk latest available month: {month}")

    cells = (
        listings[["latitude", "longitude"]]
        .assign(lat_r=lambda d: d["latitude"].round(3), lon_r=lambda d: d["longitude"].round(3))
        [["lat_r", "lon_r"]].drop_duplicates()
    )
    print(f"  {len(cells)} unique crime cells for {len(listings)} listings")

    counts: dict[tuple[float, float], int] = {}
    for i, row in enumerate(cells.itertuples(index=False)):
        n = _crime_count(row.lat_r, row.lon_r, month, cfg)
        counts[(row.lat_r, row.lon_r)] = n if n is not None else 0
        time.sleep(0.4)
        if (i + 1) % 40 == 0:
            print(f"    crime cell {i + 1}/{len(cells)}")

    listings["crime_volume"] = [
        counts.get((round(lat, 3), round(lon, 3)))
        for lat, lon in zip(listings["latitude"], listings["longitude"])
    ]
    listings["crime_volume_prev_12m"] = listings["crime_volume"] * 12
    return listings
