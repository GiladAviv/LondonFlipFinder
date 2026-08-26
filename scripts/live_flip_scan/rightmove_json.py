"""Parsing helpers for Rightmove's two embedded-JSON formats.

Search-results pages (/property-for-sale/find.html) embed a plain Next.js `__NEXT_DATA__` blob --
props.pageProps.searchResults.properties is a list of dicts, no indirection.

Listing detail pages (/properties/<id>) embed a *flighted* React Server Components payload
(`window.__PAGE_MODEL = {"data": "[...]"}`): a JSON array where most fields are integers pointing
at another element of the same array, rather than the value itself. `deref` below resolves one
hop; callers chain it for nested paths (e.g. address -> outcode).
"""
from __future__ import annotations

import json
import re
from typing import Any

_NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL)
_PAGE_MODEL_RE = re.compile(r"window\.__PAGE_MODEL\s*=\s*(\{.*?\});", re.DOTALL)


def parse_search_results(html: str) -> list[dict[str, Any]]:
    """List of raw property dicts from a Rightmove search-results page, or [] if not found."""
    m = _NEXT_DATA_RE.search(html)
    if not m:
        return []
    data = json.loads(m.group(1))
    return data["props"]["pageProps"]["searchResults"].get("properties", [])


def parse_listing_graph(html: str) -> list[Any] | None:
    """The raw deref-able array from a listing detail page's __PAGE_MODEL, or None if absent."""
    m = _PAGE_MODEL_RE.search(html)
    if not m:
        return None
    outer = json.loads(m.group(1))
    return json.loads(outer["data"])


def deref(arr: list[Any], ref: Any) -> Any:
    """One hop: an int is an index into arr, anything else is already a value."""
    if isinstance(ref, int) and 0 <= ref < len(arr):
        return arr[ref]
    return ref


def extract_listing_fields(arr: list[Any]) -> dict[str, Any]:
    """Pull the fields the live-scan feature set needs out of a listing's reference graph.

    Field-by-field, not a generic auto-deref: an int under 'bedrooms' is a real count, the same
    shape of int under 'address' is an index, and the schema is the only way to tell them apart.
    """
    root = arr[0]
    pd_idx = root.get("propertyData")
    if pd_idx is None:
        return {}
    prop = deref(arr, pd_idx)

    out: dict[str, Any] = {}

    address = deref(arr, prop.get("address"))
    if isinstance(address, dict):
        outcode = deref(arr, address.get("outcode"))
        incode = deref(arr, address.get("incode"))
        if isinstance(outcode, str) and isinstance(incode, str):
            out["postcode"] = f"{outcode} {incode}"
        display_address = deref(arr, address.get("displayAddress"))
        if isinstance(display_address, str):
            out["displayAddress"] = display_address

    tenure = deref(arr, prop.get("tenure"))
    if isinstance(tenure, dict):
        tenure_type = deref(arr, tenure.get("tenureType"))
        if isinstance(tenure_type, str):
            out["tenure"] = tenure_type

    location = deref(arr, prop.get("location"))
    if isinstance(location, dict):
        lat = deref(arr, location.get("latitude"))
        lon = deref(arr, location.get("longitude"))
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            out["latitude"] = float(lat)
            out["longitude"] = float(lon)

    sizings_ref = prop.get("sizings")
    sizings = deref(arr, sizings_ref)
    if isinstance(sizings, list):
        for s_ref in sizings:
            sizing = deref(arr, s_ref)
            if not isinstance(sizing, dict):
                continue
            unit = deref(arr, sizing.get("unit"))
            min_size = deref(arr, sizing.get("minimumSize"))
            if unit == "sqm" and isinstance(min_size, (int, float)):
                out["floorAreaSqM"] = float(min_size)
                break
            if unit == "sqft" and isinstance(min_size, (int, float)) and "floorAreaSqM" not in out:
                out["floorAreaSqM"] = float(min_size) * 0.092903

    epc_refs = deref(arr, prop.get("epcGraphs"))
    if isinstance(epc_refs, list) and epc_refs:
        epc = deref(arr, epc_refs[0])
        if isinstance(epc, dict):
            url = deref(arr, epc.get("url"))
            if isinstance(url, str):
                out["epcGraphUrl"] = url  # rating letter isn't always a plain field; url as evidence

    for key, out_key in (("bedrooms", "bedrooms"), ("bathrooms", "bathrooms"),
                         ("propertySubType", "propertyType")):
        val = deref(arr, prop.get(key))
        if val is not None and not isinstance(val, (dict, list)):
            out[out_key] = val

    return out
