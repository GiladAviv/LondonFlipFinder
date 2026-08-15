"""Shared fixtures. The sample is 500 rows taken at a fixed stride from the master table,
so it spans the full 2008-2016 window rather than clustering in one month -- the lag and
rolling-window logic under test is meaningless on a single-month slice."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from lff.config import Config

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def master() -> pd.DataFrame:
    """A 500-row slice of the joined master table."""
    return pd.read_parquet(FIXTURES / "master_sample.parquet")


@pytest.fixture(scope="session")
def cfg() -> Config:
    return Config()
