"""Unit coverage for the pieces with real edge cases: zone parsing, crime windows, metrics,
the conformal bound and the flip scan."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lff.clean import build_crime_features
from lff.conformal import calibrate_conformal, scan_for_flips
from lff.metrics import ModelBundle, ResultsRegistry, regression_metrics
from lff.spatial import parse_zone


class TestParseZone:
    """TfL fare zones arrive as '1', '2,3', '6,7' or '-1'."""

    @pytest.mark.parametrize("raw,expected", [
        ("1", 1.0),
        ("2,3", 2.0),        # innermost real zone
        ("6,7", 6.0),
        (" 4 ", 4.0),
        (1, 1.0),
    ])
    def test_returns_innermost_zone(self, raw, expected):
        assert parse_zone(raw) == expected

    @pytest.mark.parametrize("raw", ["-1", "", "n/a", None, np.nan])
    def test_non_zonal_stations_are_nan(self, raw):
        assert np.isnan(parse_zone(raw))


def test_crime_rolling_window_excludes_the_current_month():
    """closed='left' is what makes the 12-month sum strictly historical.

    The window needs twelve observations *behind* the current month, so the first twelve
    months are all NaN and month thirteen is the first to carry a value -- the sum of months
    one to twelve, with its own month excluded.
    """
    months = pd.DataFrame({
        "year": [2010] * 12 + [2011] * 1 + [2010] * 2,
        "month": list(range(1, 13)) + [1] + [1, 2],
        "borough": ["CAMDEN"] * 13 + ["BRENT"] * 2,
        "value": [100] * 12 + [999] + [7, 7],
    })
    agg = build_crime_features(months).sort_values(["borough", "date"])
    camden = agg[agg["borough"] == "CAMDEN"].reset_index(drop=True)

    assert camden["crime_volume_prev_12m"].iloc[:12].isna().all()
    assert camden["crime_volume_prev_12m"].iloc[12] == 1200
    # Its own month contributes to crime_volume but never to the trailing window.
    assert camden["crime_volume"].iloc[12] == 999


def test_crime_boroughs_are_normalised_for_joining():
    frame = pd.DataFrame({"year": [2010], "month": [1], "borough": ["  camden "], "value": [5]})
    assert build_crime_features(frame)["borough"].iloc[0] == "CAMDEN"


class TestRegressionMetrics:
    def test_perfect_prediction(self):
        m = regression_metrics([100.0, 200.0], [100.0, 200.0])
        assert m["MdAPE"] == 0.0
        assert m["MAE"] == 0.0
        assert m["R2"] == 1.0
        assert m["within_25pct"] == 100.0

    def test_mdape_is_the_median_not_the_mean(self):
        """One catastrophic error must not move the headline metric -- that is the point of
        preferring a median over MAPE on a long-tailed price distribution."""
        actual = [100.0, 100.0, 100.0, 100.0, 100.0]
        pred = [110.0, 110.0, 110.0, 110.0, 1000.0]
        m = regression_metrics(actual, pred)
        assert m["MdAPE"] == pytest.approx(10.0)
        assert m["MAPE"] > m["MdAPE"]

    def test_within_25pct_boundary_is_inclusive(self):
        m = regression_metrics([100.0, 100.0], [75.0, 125.0])
        assert m["within_25pct"] == 100.0


def test_results_registry_sorts_by_mdape_and_filters_by_split():
    registry = ResultsRegistry()
    worse = ModelBundle("worse", "capped", lambda X: np.zeros(len(X)))
    better = ModelBundle("better", "capped", lambda X: np.zeros(len(X)))
    registry.add(worse, "val", {"MdAPE": 20.0})
    registry.add(better, "val", {"MdAPE": 10.0})
    registry.add(worse, "test", {"MdAPE": 5.0})

    board = registry.frame("val")
    assert list(board["Model"]) == ["better", "worse"]
    assert len(registry.frame("test")) == 1
    assert len(registry.frame()) == 3


class _Splits:
    """Minimal stand-in: the conformal functions only need target() and features()."""

    def target(self, part):
        return part["price"]

    def features(self, part):
        return part[["x"]]


def _bundle(factor: float) -> ModelBundle:
    return ModelBundle("stub", "capped", lambda X: X["x"].to_numpy(dtype=float) * factor)


def test_conformal_multiplier_is_the_lower_tail_quantile():
    """q_10 is the 10th percentile of actual/predicted, so 90% of ratios sit above it."""
    part = pd.DataFrame({"x": np.arange(1, 101, dtype=float)})
    part["price"] = part["x"] * np.linspace(0.5, 1.5, 100)
    q = calibrate_conformal(_bundle(1.0), part, _Splits(), 0.10)

    ratios = part["price"] / part["x"]
    assert q == pytest.approx(float(np.quantile(ratios, 0.10)))
    assert (ratios >= q).mean() >= 0.89


def test_scan_flags_exactly_the_rows_below_the_floor():
    part = pd.DataFrame({
        "x": [100.0, 100.0, 100.0],
        "price": [95.0, 60.0, 100.0],
        "borough": ["CAMDEN"] * 3,
        "date": pd.to_datetime(["2016-01-01"] * 3),
    })
    scan = scan_for_flips(_bundle(1.0), part, _Splits(), q=0.75)

    assert list(scan["safe_lower_bound"]) == [75.0, 75.0, 75.0]
    assert list(scan["is_flip"]) == [False, True, False]
    assert scan["margin"].iloc[1] == pytest.approx(15.0)


def test_scan_preserves_the_index_of_the_scored_frame():
    """The scan is joined back to property rows downstream, so the index must survive."""
    part = pd.DataFrame({
        "x": [100.0, 100.0],
        "price": [50.0, 200.0],
        "borough": ["CAMDEN", "BRENT"],
        "date": pd.to_datetime(["2016-01-01", "2016-02-01"]),
    }, index=[7, 42])
    assert list(scan_for_flips(_bundle(1.0), part, _Splits(), 0.9).index) == [7, 42]
