"""Combine every enrichment module's output into a DataFrame shaped exactly like FEATURES, so it
can be passed straight to Splits.features() and bundle.predict()."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_SRC = Path(__file__).resolve().parents[2] / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from lff.features.registry import FEATURES

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import LiveScanConfig
from enrich_crime import add_crime_features
from enrich_epc import add_epc_fallback
from enrich_hpi import add_hpi_features
from enrich_land_registry import add_prior_sale_via_land_registry
from enrich_spatial import add_spatial_features

# BoE Bank Rate as of the date this script was last run/updated -- hardcoded rather than fetched,
# since a single scalar is not worth another external dependency. Update the value and the date
# comment together if this script is reused much later.
CURRENT_INTEREST_RATE = 4.00   # BoE Bank Rate effective 2025-08-07 (last cut in the published
                               # series as of this script's writing, 2026-08-23)
INTEREST_RATE_AS_OF = "2025-08-07 (fetch https://www.bankofengland.co.uk/monetary-policy/the-interest-rate-bank-rate to refresh)"

# Rightmove's propertySubType vocabulary ("Apartment", "Flat", ...) does not overlap at all with
# the training corpus's propertyType vocabulary ("Purpose Built Flat", "Terraced", ...) --
# without this mapping, category_dtypes casting (split.py:84-90) would silently turn every live
# listing's propertyType into an unseen category (NaN), discarding a real, informative feature.
# Ambiguous Rightmove labels ("House", "Town House") are left unmapped (NaN) rather than guessed,
# since a wrong guess (e.g. assuming mid-terrace for a generic "House") would bias worse than
# admitting the type is unknown.
RIGHTMOVE_PROPERTY_TYPE_MAP = {
    "Flat": "Flat/Maisonette",
    "Apartment": "Flat/Maisonette",
    "Maisonette": "Flat/Maisonette",
    "Studio": "Flat/Maisonette",
    "Ground Flat": "Flat/Maisonette",
    "Penthouse": "Flat/Maisonette",
    "Terraced": "Terraced",
    "Semi-Detached": "Semi-Detached House",
    "End of Terrace": "End Terrace House",
    "Detached": "Detached House",
}

# Same problem, same fix: Rightmove's tenure.tenureType is upper-snake-case ("LEASEHOLD",
# "SHARE_OF_FREEHOLD"); the training corpus uses title case ("Leasehold", "Shared"). Without this,
# every live listing's tenure would also silently cast to NaN.
RIGHTMOVE_TENURE_MAP = {
    "LEASEHOLD": "Leasehold",
    "FREEHOLD": "Freehold",
    "SHARE_OF_FREEHOLD": "Shared",
}


def build_live_feature_frame(
    listings: pd.DataFrame, cfg: LiveScanConfig,
    pipeline_state,  # scripts.live_flip_scan.pipeline_rerun.PipelineState
    training_last_borough_sqm: pd.Series,
) -> pd.DataFrame:
    scrape_date = pd.Timestamp.today().normalize()
    reference_month = pipeline_state.splits.test["date"].max().strftime("%Y-%m")

    df = listings.copy()
    print(f"\n=== Enrichment: {len(df)} listings ===")

    unmapped = sorted(set(df["propertyType"].dropna()) - set(RIGHTMOVE_PROPERTY_TYPE_MAP))
    if unmapped:
        print(f"  propertyType values with no training-vocabulary mapping (left NaN): {unmapped}")
    df["propertyType"] = df["propertyType"].map(RIGHTMOVE_PROPERTY_TYPE_MAP)

    unmapped_tenure = sorted(set(df["tenure"].dropna()) - set(RIGHTMOVE_TENURE_MAP))
    if unmapped_tenure:
        print(f"  tenure values with no training-vocabulary mapping (left NaN): {unmapped_tenure}")
    df["tenure"] = df["tenure"].map(RIGHTMOVE_TENURE_MAP)

    print("\n-- spatial (lff.spatial) --")
    df = add_spatial_features(df, pipeline_state.cfg, pipeline_state.underground_gdf,
                              pipeline_state.heavy_rail_gdf)

    print("\n-- UK HPI market level --")
    df = add_hpi_features(df, cfg, training_last_borough_sqm, reference_month)

    print("\n-- data.police.uk crime --")
    df = add_crime_features(df, cfg)

    print("\n-- EPC register fallback --")
    df = add_epc_fallback(df, cfg)

    print("\n-- Land Registry Price Paid Data prior-sale match --")
    years = sorted({scrape_date.year, scrape_date.year - 1, scrape_date.year - 2})
    df = add_prior_sale_via_land_registry(df, cfg, years, pipeline_state.training_origin_date)

    # Trivially-derivable features.
    df["livingRooms"] = 1  # not exposed by the scraper; assumed present, not fetched -- flagged
    df["total_rooms"] = df["bedrooms"] + df["livingRooms"]
    df["avg_room_size"] = (df["floorAreaSqM"] / df["total_rooms"]).replace([np.inf, -np.inf], np.nan)
    df["month_sin"] = np.sin(2 * np.pi * scrape_date.month / 12)
    df["month_cos"] = np.cos(2 * np.pi * scrape_date.month / 12)
    df["days_since_start"] = (scrape_date - pipeline_state.training_origin_date).days
    df["interest_rate"] = CURRENT_INTEREST_RATE
    print(f"\ninterest_rate = {CURRENT_INTEREST_RATE}% (hardcoded, as of {INTEREST_RATE_AS_OF})")

    df["date"] = scrape_date
    print("\nWARNING: 'price' below is the scraped ASKING price, not a sold price -- see the "
         "caveat block in compare.py before interpreting any comparison against the test set.")
    df["price"] = df["asking_price"]

    missing = [c for c in FEATURES if c not in df.columns]
    if missing:
        raise KeyError(f"assembled frame is missing required columns: {missing}")

    print("\n-- Fill-rate per feature --")
    for col in FEATURES:
        n = df[col].notna().sum()
        print(f"  {col:<28} {n}/{len(df)}")

    return df
