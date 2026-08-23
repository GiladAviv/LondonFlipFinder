"""Shared fixtures.

The sample is 500 rows taken at a fixed stride from the master table, so it spans the full
2008-2016 window rather than clustering in one month -- the lag and rolling-window logic under
test is meaningless on a single-month slice.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from lff.config import Config
from lff.features.market import add_market_features
from lff.features.prior_sale import add_prior_sale_features, build_sale_history
from lff.features.temporal import add_temporal_features

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def master() -> pd.DataFrame:
    """A 500-row slice of the joined master table."""
    return pd.read_parquet(FIXTURES / "master_sample.parquet")


@pytest.fixture(scope="session")
def sale_history(master: pd.DataFrame) -> pd.DataFrame:
    """Sale history built from the sample's own rows.

    The real pipeline reads history from the whole 1995-2024 file; here the sample stands in
    for it, which is enough to exercise the merge and keeps the fixture self-contained.
    """
    raw = master[["fullAddress", "date", "price"]].rename(
        columns={"date": "history_date", "price": "history_price"}
    )
    return build_sale_history(raw)


@pytest.fixture(scope="session")
def model_frame(master: pd.DataFrame, sale_history: pd.DataFrame) -> pd.DataFrame:
    """The frame the models actually see: every feature step applied, in pipeline order."""
    frame = add_market_features(add_temporal_features(master))
    return add_prior_sale_features(frame, sale_history)


@pytest.fixture(scope="session")
def cfg() -> Config:
    return Config()
