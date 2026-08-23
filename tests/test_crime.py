"""LSOA-grain crime features: the same time discipline as the borough series, finer geography."""
from __future__ import annotations

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point, box

from lff.crime import CATEGORY_GROUPS, build_crime_features_lsoa
from lff.spatial import add_lsoa


def _crime_frame(months: int = 14, value: int = 10) -> pd.DataFrame:
    """One LSOA, `months` consecutive months, one burglary row and one violence row each."""
    dates = pd.date_range("2010-01-01", periods=months, freq="MS")
    rows = []
    for d in dates:
        rows.append({"lsoa_code": "E01000001", "major_category": "Burglary",
                     "value": value, "year": d.year, "month": d.month})
        rows.append({"lsoa_code": "E01000001", "major_category": "Violence Against the Person",
                     "value": value * 2, "year": d.year, "month": d.month})
    return pd.DataFrame(rows)


def test_lsoa_window_excludes_the_current_month():
    """Identical semantics to the borough series: twelve months behind, never the month itself."""
    agg = build_crime_features_lsoa(_crime_frame()).sort_values("date").reset_index(drop=True)

    assert agg["lsoa_crime_prev_12m"].iloc[:12].isna().all()
    # Month 13 sums months 1-12: (10 burglary + 20 violence) x 12.
    assert agg["lsoa_crime_prev_12m"].iloc[12] == 360
    assert agg["lsoa_crime_burglary_prev_12m"].iloc[12] == 120
    assert agg["lsoa_crime_violence_prev_12m"].iloc[12] == 240


def test_categories_are_split_not_summed():
    agg = build_crime_features_lsoa(_crime_frame(months=1))
    assert agg["lsoa_crime"].iloc[0] == 30
    assert agg["lsoa_crime_burglary"].iloc[0] == 10
    assert agg["lsoa_crime_violence"].iloc[0] == 20
    assert agg["lsoa_crime_disorder"].iloc[0] == 0


def test_uncategorised_offences_land_in_other_rather_than_vanishing():
    frame = pd.DataFrame([{"lsoa_code": "E01000001", "major_category": "Fraud or Forgery",
                           "value": 7, "year": 2010, "month": 1}])
    agg = build_crime_features_lsoa(frame)
    assert agg["lsoa_crime"].iloc[0] == 7
    assert agg["lsoa_crime_other"].iloc[0] == 7


def test_category_groups_are_disjoint():
    seen: set[str] = set()
    for categories in CATEGORY_GROUPS.values():
        assert not seen & set(categories)
        seen |= set(categories)


def test_density_needs_boundaries_and_uses_area():
    bounds = gpd.GeoDataFrame(
        {"LSOA11CD": ["E01000001"]},
        geometry=[box(0, 0, 1000, 1000)],  # 1 km2 in BNG metres
        crs="EPSG:27700",
    )
    agg = build_crime_features_lsoa(_crime_frame(), bounds).sort_values("date")
    assert agg["lsoa_area_km2"].iloc[0] == pytest.approx(1.0)
    row = agg.iloc[12]
    assert row["lsoa_crime_density_prev_12m"] == pytest.approx(row["lsoa_crime_prev_12m"] / 1.0)


def test_add_lsoa_rejects_a_crs_mismatch():
    """Silently joining WGS84 points against BNG polygons would match nothing at all."""
    points = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(-0.12, 51.5)], crs="EPSG:4326")
    bounds = gpd.GeoDataFrame({"LSOA11CD": ["E01000001"]},
                              geometry=[box(0, 0, 1000, 1000)], crs="EPSG:27700")
    with pytest.raises(ValueError, match="CRS mismatch"):
        add_lsoa(points, bounds)


def test_add_lsoa_assigns_the_containing_polygon():
    points = gpd.GeoDataFrame(
        {"id": [1, 2]},
        geometry=[Point(500, 500), Point(1500, 500)],
        crs="EPSG:27700",
    )
    bounds = gpd.GeoDataFrame(
        {"LSOA11CD": ["E01000001", "E01000002"]},
        geometry=[box(0, 0, 1000, 1000), box(1000, 0, 2000, 1000)],
        crs="EPSG:27700",
    )
    joined = add_lsoa(points, bounds)
    assert list(joined["lsoa_code"]) == ["E01000001", "E01000002"]


def test_add_lsoa_leaves_points_outside_every_polygon_unmatched():
    points = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(9_000, 9_000)], crs="EPSG:27700")
    bounds = gpd.GeoDataFrame({"LSOA11CD": ["E01000001"]},
                              geometry=[box(0, 0, 1000, 1000)], crs="EPSG:27700")
    joined = add_lsoa(points, bounds)
    assert joined["lsoa_code"].isna().all()
