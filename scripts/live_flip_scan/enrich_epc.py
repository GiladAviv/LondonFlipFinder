"""Fallback for floorAreaSqM / currentEnergyRating from the EPC (Energy Performance Certificate)
register (epc.opendatacommunities.org, free but requires a registered API key -- HTTP Basic Auth
as base64("<email>:<key>")).

Deliberately does NOT fall back tenure from EPC: the certificate's "tenure" field records
occupancy status ("Owner-occupied", "Rented (private)", ...), not legal tenure
(Freehold/Leasehold) -- a different concept from the trained tenure feature. Writing it in would
silently corrupt the column rather than fill a real gap, so tenure is left to whatever the
scraper found (see assemble.py's RIGHTMOVE_TENURE_MAP) or NaN.

Used ONLY to fill gaps the listing itself didn't supply, never to override a scraped value.
Requires the env var LFF_EPC_API_KEY as "<email>:<key>"; if unset, this step is skipped entirely
with a printed warning rather than failing the run -- floorAreaSqM keeps whatever the scraper
found (see scrape_rightmove.py's pilot fill-rate report) and currentEnergyRating stays NaN for
every row, since Rightmove's listing pages expose only an EPC graph *image* link, not a plain
rating letter (rightmove_json.py's epcGraphUrl).
"""
from __future__ import annotations

import base64
import os
import sys
import time
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import LiveScanConfig

EPC_BASE = "https://epc.opendatacommunities.org/api/v1/domestic/search"


def _auth_header(api_key: str) -> dict[str, str]:
    token = base64.b64encode(api_key.encode()).decode()
    return {"Authorization": f"Basic {token}", "Accept": "application/json"}


def _lookup(postcode: str, headers: dict[str, str], cfg: LiveScanConfig) -> dict | None:
    try:
        resp = requests.get(EPC_BASE, params={"postcode": postcode, "size": 5},
                            headers={**headers, "User-Agent": cfg.user_agent}, timeout=15)
    except requests.RequestException as e:
        print(f"  EPC lookup failed for {postcode}: {e}")
        return None
    if resp.status_code != 200:
        return None
    rows = resp.json().get("rows", [])
    return rows[0] if rows else None  # most recent certificate for the postcode


def add_epc_fallback(listings: pd.DataFrame, cfg: LiveScanConfig) -> pd.DataFrame:
    listings = listings.copy()
    for col in ("floorAreaSqM", "tenure", "currentEnergyRating"):
        if col not in listings.columns:
            listings[col] = pd.NA
    listings["epc_used_as_fallback"] = False

    api_key = os.environ.get(cfg.epc_api_key_env)
    if not api_key:
        print(f"WARNING: {cfg.epc_api_key_env} not set -- skipping EPC fallback. "
              f"floorAreaSqM keeps only what the scraper found; currentEnergyRating "
              f"will be NaN for every row.")
        return listings

    headers = _auth_header(api_key)
    for idx, row in listings.iterrows():
        needs_fallback = (
            pd.isna(row.get("floorAreaSqM")) or pd.isna(row.get("currentEnergyRating"))
        )
        if not needs_fallback or pd.isna(row.get("postcode")):
            continue
        cert = _lookup(row["postcode"], headers, cfg)
        time.sleep(0.3)
        if cert is None:
            continue
        used = False
        if pd.isna(row.get("floorAreaSqM")) and cert.get("total-floor-area"):
            listings.at[idx, "floorAreaSqM"] = float(cert["total-floor-area"])
            used = True
        if pd.isna(row.get("currentEnergyRating")) and cert.get("current-energy-rating"):
            listings.at[idx, "currentEnergyRating"] = cert["current-energy-rating"]
            used = True
        if used:
            listings.at[idx, "epc_used_as_fallback"] = True

    n_used = listings["epc_used_as_fallback"].sum()
    print(f"EPC fallback used for {n_used}/{len(listings)} listings")
    return listings
