"""Pilot-then-scale scraper for Rightmove London for-sale listings.

Search-results pages carry id/beds/baths/lat-lon/tenure/price/size/type directly in an embedded
__NEXT_DATA__ blob (see rightmove_json.py); listing detail pages carry postcode, exact address and
an EPC graph link in a second, index-referenced blob (__PAGE_MODEL). Both are confirmed present by
a manual pilot fetch against live pages (2026-08-23) -- see PILOT_FINDINGS.md for the raw record.

robots.txt is checked at runtime (not hardcoded) because rules can change between the pilot and
any later scale run.
"""
from __future__ import annotations

import hashlib
import random
import sys
import time
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import LiveScanConfig
from robots import check_allowed
from rightmove_json import extract_listing_fields, parse_listing_graph, parse_search_results

BASE = "https://www.rightmove.co.uk"
SEARCH_PATH = "/property-for-sale/find.html"


def _cache_path(cache_dir: Path, url: str) -> Path:
    return cache_dir / f"{hashlib.sha1(url.encode()).hexdigest()}.html"


def fetch(url: str, cfg: LiveScanConfig, _last_request: list[float]) -> str | None:
    """robots.txt check, rate-limited GET, disk cache. Returns None on any non-2xx or block."""
    cache_dir = cfg.cache_dir
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = _cache_path(cache_dir, url)
    if cached.exists():
        return cached.read_text(encoding="utf-8", errors="replace")

    if not check_allowed(url, cfg.user_agent):
        print(f"BLOCKED by robots.txt: {url}")
        return None

    if _last_request:
        elapsed = time.monotonic() - _last_request[0]
        wait = cfg.rate_limit_s * random.uniform(0.8, 1.2) - elapsed
        if wait > 0:
            time.sleep(wait)

    for attempt in range(cfg.max_retries + 1):
        try:
            resp = requests.get(url, headers={"User-Agent": cfg.user_agent}, timeout=20)
            _last_request[:] = [time.monotonic()]
            if resp.status_code == 200 and resp.text:
                cached.write_text(resp.text, encoding="utf-8")
                return resp.text
            print(f"  non-200 ({resp.status_code}) for {url}")
            return None
        except requests.RequestException as e:
            if attempt == cfg.max_retries:
                print(f"  failed after {cfg.max_retries + 1} attempts: {url} ({e})")
                return None
            time.sleep(cfg.rate_limit_s)
    return None


def _search_url(cfg: LiveScanConfig, index: int = 0) -> str:
    return (
        f"{BASE}{SEARCH_PATH}?searchType=SALE&locationIdentifier={cfg.search_region}"
        f"&insId=1&radius=0.0&index={index}&sortType=6&_includeSSTC=on"
    )


def collect_search_results(cfg: LiveScanConfig, n_needed: int) -> list[dict]:
    """Iterate search-result pages (24 listings/page) up to max_search_pages or n_needed."""
    last_request: list[float] = []
    listings: list[dict] = []
    seen_ids: set[int] = set()
    for page in range(cfg.max_search_pages):
        if len(listings) >= n_needed:
            break
        url = _search_url(cfg, index=page * 24)
        html = fetch(url, cfg, last_request)
        if html is None:
            break
        props = parse_search_results(html)
        if not props:
            print(f"  no properties on search page {page} -- stopping pagination")
            break
        for p in props:
            if p["id"] in seen_ids:
                continue
            seen_ids.add(p["id"])
            listings.append(p)
        print(f"  search page {page}: +{len(props)} listings ({len(listings)} total)")
    return listings[:n_needed]


def enrich_with_listing_page(listing: dict, cfg: LiveScanConfig, last_request: list[float]) -> dict:
    """Fetch one listing's detail page and merge in postcode/exact-address/EPC-link fields."""
    listing_id = listing["id"]
    url = f"{BASE}/properties/{listing_id}"
    html = fetch(url, cfg, last_request)
    if html is None:
        return listing
    arr = parse_listing_graph(html)
    if arr is None:
        print(f"  __PAGE_MODEL not found for listing {listing_id}")
        return listing
    extra = extract_listing_fields(arr)
    merged = dict(listing)
    merged.update({k: v for k, v in extra.items() if k not in merged or merged[k] is None})
    merged.setdefault("postcode", extra.get("postcode"))
    return merged


def run_pilot(cfg: LiveScanConfig) -> list[dict]:
    """Fetch pilot_n listings, report per-field fill rate. Does NOT proceed to scale."""
    print(f"--- Rightmove pilot: {cfg.pilot_n} listings ---")
    search_results = collect_search_results(cfg, cfg.pilot_n)
    last_request: list[float] = []
    enriched = [enrich_with_listing_page(r, cfg, last_request) for r in search_results]

    fields = ["id", "price", "bedrooms", "bathrooms", "propertyType", "postcode",
             "latitude", "longitude", "tenure", "floorAreaSqM", "epcGraphUrl", "displaySize"]
    print("\nField fill rate across pilot sample:")
    for f in fields:
        n_present = sum(1 for r in enriched if r.get(f) not in (None, "", {}))
        print(f"  {f:<16} {n_present}/{len(enriched)}")
    return enriched


def listings_to_frame(listings: list[dict]) -> pd.DataFrame:
    """Flatten the nested price/tenure dicts into a plain tabular DataFrame."""
    rows = []
    for listing in listings:
        row = dict(listing)
        price = row.pop("price", None)
        if isinstance(price, dict):
            row["asking_price"] = price.get("amount")
        tenure = row.pop("tenure", None)
        if isinstance(tenure, dict):
            row["tenure"] = tenure.get("tenureType")
        elif isinstance(tenure, str):
            row["tenure"] = tenure
        row.pop("images", None)
        row.pop("propertyImages", None)
        rows.append(row)
    df = pd.DataFrame(rows)
    df = df.rename(columns={"id": "listing_id"})
    return df


def run_scale(cfg: LiveScanConfig) -> pd.DataFrame:
    """Collect up to target_n listings, enriched with their detail-page fields."""
    print(f"--- Rightmove scale scrape: target {cfg.target_n} listings ---")
    search_results = collect_search_results(cfg, cfg.target_n)
    last_request: list[float] = []
    enriched = []
    for i, r in enumerate(search_results):
        enriched.append(enrich_with_listing_page(r, cfg, last_request))
        if (i + 1) % 20 == 0:
            print(f"  enriched {i + 1}/{len(search_results)}")
    df = listings_to_frame(enriched)
    out_dir = Path("artifacts/live_scan")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "listings_raw.csv"
    df.to_csv(out_path, index=False)
    print(f"Collected {len(df)} listings -> {out_path}")
    return df


if __name__ == "__main__":
    import sys as _sys
    cfg = LiveScanConfig()
    if "--scale" in _sys.argv:
        run_scale(cfg)
    else:
        run_pilot(cfg)
