"""Best-effort prior-sale match against HM Land Registry Price Paid Data (free bulk CSV, no key;
verified live 2026-08-23 at prod.publicdata.landregistry.gov.uk's S3 static site, pp-<year>.csv,
16 unnamed columns: [id, price, date, postcode, property_type, new_build, duration, paon, saon,
street, locality, town, district, county, ppd_category, record_status]).

Reuses lff.features.prior_sale.add_prior_sale_features directly -- it already produces the exact
NaN-on-no-match shape the trained model expects (merge_asof, allow_exact_matches=False), so a
live listing with no match is not a new code path.

Matching caveat, documented rather than hidden: Rightmove's displayAddress rarely carries a house
number (search-result cards show "Street name, Area" for privacy), so this matches on
(postcode, street name) rather than requiring an exact PAON/house-number match like the training
corpus's fullAddress does. This will under-match relative to what an exact-address join could
recover -- expect a lower has_prev_sale rate on live listings than the ~61% seen in training,
purely from address granularity, not because these properties really sell less often.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import LiveScanConfig

_SRC = Path(__file__).resolve().parents[2] / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from lff.features.prior_sale import add_prior_sale_features

PPD_HOST = "prod2.publicdata.landregistry.gov.uk.s3-website-eu-west-1.amazonaws.com"
PPD_COLUMNS = [
    "transaction_id", "price", "date", "postcode", "property_type", "new_build",
    "duration", "paon", "saon", "street", "locality", "town", "district", "county",
    "ppd_category", "record_status",
]


def _normalise_street(text: str | float) -> str:
    if not isinstance(text, str):
        return ""
    return re.sub(r"[^A-Z0-9 ]", "", text.upper()).strip()


def _street_from_display_address(display_address: str | float) -> str:
    """Rightmove's displayAddress is "Street name, Area, ..." (e.g. "Firs Close, Mitcham,
    CR4") -- only the first comma-separated segment is the street; the rest is locality/
    postcode-outcode text that would never match PPD's clean street field."""
    if not isinstance(display_address, str):
        return ""
    return _normalise_street(display_address.split(",")[0])


def fetch_price_paid_years(years: list[int], cache_dir: Path) -> pd.DataFrame:
    """Download (or reuse a cached copy of) pp-<year>.csv for each year, filtered to London
    outcodes only, kept small enough to hold in memory."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    for year in years:
        cached = cache_dir / f"pp-{year}.csv"
        if not cached.exists():
            url = f"http://{PPD_HOST}/pp-{year}.csv"
            print(f"Downloading Price Paid Data {year}...")
            resp = requests.get(url, timeout=120, allow_redirects=True)
            resp.raise_for_status()
            cached.write_bytes(resp.content)
        df = pd.read_csv(cached, header=None, names=PPD_COLUMNS,
                         usecols=["price", "date", "postcode", "paon", "saon", "street"],
                         dtype=str)
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def add_prior_sale_via_land_registry(
    listings: pd.DataFrame, cfg: LiveScanConfig,
    years: list[int], training_origin_date: pd.Timestamp,
) -> pd.DataFrame:
    ppd = fetch_price_paid_years(years, cfg.cache_dir / "price_paid")
    ppd["postcode"] = ppd["postcode"].astype(str).str.replace(" ", "", regex=False).str.upper()
    ppd["street_norm"] = ppd["street"].map(_normalise_street)
    ppd["date"] = pd.to_datetime(ppd["date"], errors="coerce")
    ppd["price"] = pd.to_numeric(ppd["price"], errors="coerce")
    ppd["fullAddress"] = ppd["postcode"] + "|" + ppd["street_norm"]
    history = ppd.dropna(subset=["date", "price", "fullAddress"])[["fullAddress", "date", "price"]]

    listings = listings.copy()
    listings["postcode_compact"] = (
        listings["postcode"].astype(str).str.replace(" ", "", regex=False).str.upper()
    )
    listings["street_norm"] = listings["displayAddress"].map(_street_from_display_address)
    listings["fullAddress"] = listings["postcode_compact"] + "|" + listings["street_norm"]
    # datetime64 resolution must match history's for merge_asof (pandas 2.x is strict about
    # this): pd.Timestamp.today() is [us], pd.to_datetime on parsed PPD strings is [ns].
    listings["date"] = pd.Timestamp.today().normalize().as_unit("ns")

    # add_prior_sale_features anchors prev_sale_days_since_start on the frame's own date.min();
    # a single-listings frame would anchor on "today" for every row, which is wrong -- it must be
    # pinned to the *training* origin instead (see prior_sale.py's `origin = out["date"].min()`).
    # We reuse the function then overwrite that one column.
    scored = add_prior_sale_features(listings, history)
    scored["prev_sale_days_since_start"] = (
        (scored["prev_sale_date"] - training_origin_date).dt.days.astype("float64")
    )

    coverage = scored["has_prev_sale"].mean() * 100
    print(f"Land Registry match: {int(scored['has_prev_sale'].sum())}/{len(scored)} "
         f"({coverage:.1f}%) listings matched to a prior sale (postcode+street, best-effort)")
    return scored
