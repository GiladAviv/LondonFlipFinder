"""Prior-sale features read the past and only the past."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lff.features.prior_sale import (
    add_prior_sale_features,
    assert_no_lookahead,
    build_sale_history,
)


def _raw(rows: list[tuple[str, str, float]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["fullAddress", "history_date", "history_price"])


def test_history_drops_exact_duplicates():
    """A quarter of the real file is exact repeats; left in, one sale looks like several."""
    raw = _raw([("A", "2010-01-01", 100.0)] * 3 + [("A", "2012-01-01", 150.0)])
    history = build_sale_history(raw)
    assert len(history) == 2


def test_history_collapses_same_day_price_conflicts():
    raw = _raw([("A", "2010-01-01", 100.0), ("A", "2010-01-01", 200.0)])
    history = build_sale_history(raw)
    assert len(history) == 1
    assert history["price"].iloc[0] == 150.0


def test_prior_sale_never_matches_the_row_it_predicts():
    """The same address selling on the same day is the target, not a predictor."""
    raw = _raw([("A", "2010-01-01", 100.0), ("A", "2014-01-01", 200.0)])
    history = build_sale_history(raw)
    target = pd.DataFrame({
        "fullAddress": ["A", "A"],
        "date": pd.to_datetime(["2010-01-01", "2014-01-01"]),
    })
    out = add_prior_sale_features(target, history)

    # The 2010 sale is the first on record: nothing precedes it.
    assert out.loc[0, "has_prev_sale"] == 0
    assert pd.isna(out.loc[0, "prev_sale_price"])
    # The 2014 sale sees 2010, and not itself.
    assert out.loc[1, "has_prev_sale"] == 1
    assert out.loc[1, "prev_sale_price"] == 100.0
    assert_no_lookahead(out)


def test_most_recent_prior_sale_wins():
    raw = _raw([("A", "2000-01-01", 50.0), ("A", "2005-01-01", 80.0),
                ("A", "2012-01-01", 200.0)])
    history = build_sale_history(raw)
    target = pd.DataFrame({"fullAddress": ["A"], "date": pd.to_datetime(["2010-06-01"])})
    out = add_prior_sale_features(target, history)
    assert out.loc[0, "prev_sale_price"] == 80.0
    assert out.loc[0, "n_prior_sales"] == 2  # 2000 and 2005, not 2012


def test_addresses_do_not_borrow_each_others_history():
    raw = _raw([("A", "2000-01-01", 50.0), ("B", "2001-01-01", 999.0)])
    history = build_sale_history(raw)
    target = pd.DataFrame({"fullAddress": ["B"], "date": pd.to_datetime(["2010-01-01"])})
    out = add_prior_sale_features(target, history)
    assert out.loc[0, "prev_sale_price"] == 999.0


def test_years_since_prev_sale_is_positive_and_correct():
    raw = _raw([("A", "2010-01-01", 100.0)])
    history = build_sale_history(raw)
    target = pd.DataFrame({"fullAddress": ["A"], "date": pd.to_datetime(["2014-01-01"])})
    out = add_prior_sale_features(target, history)
    assert out.loc[0, "years_since_prev_sale"] == pytest.approx(4.0, abs=0.01)


def test_n_prior_sales_excludes_the_same_day():
    raw = _raw([("A", "2010-01-01", 100.0), ("A", "2012-01-01", 150.0),
                ("A", "2014-01-01", 200.0)])
    history = build_sale_history(raw)
    target = pd.DataFrame({
        "fullAddress": ["A"] * 3,
        "date": pd.to_datetime(["2010-01-01", "2012-01-01", "2014-01-01"]),
    })
    out = add_prior_sale_features(target, history)
    assert list(out["n_prior_sales"]) == [0, 1, 2]


def test_assert_no_lookahead_catches_a_future_match():
    frame = pd.DataFrame({
        "has_prev_sale": [1],
        "date": pd.to_datetime(["2010-01-01"]),
        "prev_sale_date": pd.to_datetime(["2012-01-01"]),
        "years_since_prev_sale": [-2.0],
    })
    with pytest.raises(AssertionError, match="at or after"):
        assert_no_lookahead(frame)


def test_history_spans_the_whole_file_not_the_modelling_window():
    """A 2009 sale's previous sale is often pre-2008; clipping first would lose it."""
    raw = _raw([("A", "2003-01-01", 60.0), ("A", "2009-01-01", 120.0)])
    history = build_sale_history(raw)
    target = pd.DataFrame({"fullAddress": ["A"], "date": pd.to_datetime(["2009-01-01"])})
    out = add_prior_sale_features(target, history)
    assert out.loc[0, "prev_sale_price"] == 60.0
    assert out.loc[0, "log_prev_sale_price"] == pytest.approx(np.log1p(60.0))
