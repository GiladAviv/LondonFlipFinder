"""Live proxy for the market-level features, via the UK House Price Index (landregistry.data.gov.uk,
free, no key). Verified live (2026-08-23): /data/ukhpi/region/<slug>/month/<YYYY-MM>.json returns
averagePrice for both the whole-London region and individual boroughs (slug = lowercased,
hyphenated borough name, e.g. "kensington-and-chelsea").

This is an explicit PROXY, not a reproduction: features/market.py:11-27 computes
market_median_rolling_3m/12m and lagged_borough_median_sqm as rolling MEDIANS of this project's
own 2008-2016 sales corpus. UK HPI publishes a mean-based index for a different (much larger,
current) sample. Documented here and again in compare.py's caveat block -- never presented as
equivalent.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import LiveScanConfig

HPI_BASE = "http://landregistry.data.gov.uk/data/ukhpi/region"


# UK HPI's region naming doesn't always match the GLA borough name verbatim -- confirmed live
# (2026-08-23): "Westminster" 404s, "city-of-westminster" is the real slug. Extend this if other
# boroughs turn out to have the same mismatch (fetch_hpi_growth logs a warning per miss).
_SLUG_OVERRIDES = {
    "WESTMINSTER": "city-of-westminster",
}


def _borough_slug(borough: str) -> str:
    override = _SLUG_OVERRIDES.get(borough.strip().upper())
    if override:
        return override
    return borough.strip().lower().replace(" ", "-")


def _fetch_month(slug: str, month: str, cfg: LiveScanConfig) -> dict[str, Any] | None:
    """One HPI reading for one region-slug and one YYYY-MM month, walking backward up to a few
    months if the requested month isn't published yet (HPI lags by ~1-2 months)."""
    url = f"{HPI_BASE}/{slug}/month/{month}.json"
    try:
        resp = requests.get(url, headers={"User-Agent": cfg.user_agent}, timeout=15)
    except requests.RequestException as e:
        print(f"  HPI fetch failed for {slug}/{month}: {e}")
        return None
    if resp.status_code != 200:
        return None
    data = resp.json()
    topic = data.get("result", {}).get("primaryTopic")
    if not isinstance(topic, dict):
        return None
    return topic


def latest_available_month(cfg: LiveScanConfig) -> str:
    """The most recent published UK HPI month for the London region."""
    resp = requests.get(f"{HPI_BASE}/london.json", headers={"User-Agent": cfg.user_agent},
                        timeout=15)
    resp.raise_for_status()
    items = resp.json()["result"]["items"]
    return items[0].rsplit("/", 1)[-1]  # e.g. ".../month/2026-06" -> "2026-06"


def fetch_hpi_growth(boroughs: list[str], reference_month: str, cfg: LiveScanConfig
                     ) -> tuple[dict[str, float], float, float]:
    """For each borough, the price-index ratio (latest / reference_month) -- a pure growth
    factor, not a price level. Also returns the latest and reference London-wide averagePrice."""
    month = latest_available_month(cfg)
    print(f"UK HPI latest available month: {month} (reference: {reference_month})")

    london_latest = _fetch_month("london", month, cfg)
    london_ref = _fetch_month("london", reference_month, cfg)
    london_latest_price = london_latest["averagePrice"] if london_latest else None
    london_ref_price = london_ref["averagePrice"] if london_ref else None

    growth: dict[str, float] = {}
    for borough in boroughs:
        slug = _borough_slug(borough)
        latest = _fetch_month(slug, month, cfg)
        time.sleep(0.3)  # gentle: this is a government API, not the scraped site
        ref = _fetch_month(slug, reference_month, cfg)
        time.sleep(0.3)
        if latest and ref and ref.get("housePriceIndex"):
            growth[borough] = latest["housePriceIndex"] / ref["housePriceIndex"]
        else:
            print(f"  no HPI series for borough slug '{slug}' -- will fall back to London-wide growth")
    return growth, london_latest_price, london_ref_price


def add_hpi_features(
    listings: pd.DataFrame, cfg: LiveScanConfig,
    training_last_borough_sqm: pd.Series, reference_month: str,
) -> pd.DataFrame:
    """market_median_rolling_3m/12m <- current London-wide UK HPI average price (same value for
    both: there is no live 3m/12m rolling window to reproduce, only one current reading).
    lagged_borough_median_sqm <- the pipeline's own last-known borough L/sqm (as of
    reference_month, the training corpus's own end date), scaled by that borough's own HPI
    growth since reference_month. UK HPI does not publish L/sqm directly, so this is a growth
    adjustment applied to a real historical anchor, not an independent live L/sqm estimate.
    """
    listings = listings.copy()
    boroughs = sorted(listings["borough"].dropna().unique())
    growth, london_latest_price, london_ref_price = fetch_hpi_growth(boroughs, reference_month, cfg)
    london_growth = (
        london_latest_price / london_ref_price
        if london_latest_price and london_ref_price else float("nan")
    )

    listings["market_median_rolling_3m"] = london_latest_price
    listings["market_median_rolling_12m"] = london_latest_price

    def borough_sqm(row) -> float:
        borough = row["borough"]
        base_sqm = training_last_borough_sqm.get(borough)
        if base_sqm is None:
            return float("nan")
        factor = growth.get(borough, london_growth)
        return float(base_sqm) * factor

    listings["lagged_borough_median_sqm"] = listings.apply(borough_sqm, axis=1)
    return listings
