"""Paths, tunables and seeding. Lifted from notebook section 2."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


def resolve_data_dir() -> Path:
    """Locate the dataset directory: env var, then Colab Drive, then a local ./data folder."""
    env = os.environ.get("LFF_DATA_DIR")
    if env:
        return Path(env).expanduser()
    if "google.colab" in sys.modules:  # pragma: no cover - Colab only
        from google.colab import drive

        drive.mount("/content/drive")
        return Path("/content/drive/MyDrive/data_for_ds_project")
    return Path.cwd() / "data" / "data_for_ds_project"


@dataclass(frozen=True)
class Config:
    """Every tunable in the project. Frozen so a stage cannot mutate it by accident."""

    data_dir: Path = field(default_factory=resolve_data_dir)
    artifact_dir: Path = field(default_factory=lambda: Path.cwd() / "artifacts")
    dataset_url: str = (
        "https://github.com/GiladAviv/LondonFlipFinder/releases/download/v1.0.0/"
        "data_for_ds_project-20260629T125106Z-3-001.zip"
    )

    # Coordinate reference systems. BNG is metric, which makes distances interpretable.
    wgs84: str = "EPSG:4326"
    bng: str = "EPSG:27700"

    # Row filters
    year_min: int = 2008
    year_max: int = 2016
    min_price_per_sqm: float = 1_500.0   # drops symbolic transfers / data-entry errors
    price_cap: float = 4_000_000.0       # boundary of the "standard" market
    iso_contamination: float = 0.02      # IsolationForest anomaly rate (training data only)

    # Splitting and modelling. Four chronological slices: train fits the model, val drives
    # early stopping, model selection and every design decision in section 14, calib is touched
    # by nothing except conformal calibration (so q_10 is never computed on data the model was
    # tuned against), and test is read for reporting only -- never to fit or choose anything.
    # test_frac is the remainder.
    train_frac: float = 0.60
    val_frac: float = 0.15
    calib_frac: float = 0.10
    luxury_threshold: float = 1_000_000.0
    target_encoding_smoothing: int = 10
    conformal_alpha: float = 0.10        # -> 90% lower bound
    seed: int = 42
    fast_mode: bool = field(default_factory=lambda: os.environ.get("LFF_FAST_MODE") == "1")

    # --- derived paths -------------------------------------------------------
    @property
    def houses_csv(self) -> Path:
        return self.data_dir / "kaggle_london_house_price_data.csv"

    @property
    def crime_csv(self) -> Path:
        return self.data_dir / "london_crime_by_lsoa.csv"

    @property
    def boe_csv(self) -> Path:
        return self.data_dir / "Bank Rate history and data  Bank of England Database.csv"

    @property
    def stations_csv(self) -> Path:
        return self.data_dir / "TFL Entry and Exit Data" / "Geodata" / "Stations_20220221.csv"

    @property
    def boroughs_shp(self) -> Path:
        return self.data_dir / "London_Wards" / "Boroughs" / "London_Borough_Excluding_MHW.shp"

    @property
    def cache_parquet(self) -> Path:
        return self.artifact_dir / "master_table.parquet"

    @property
    def required_files(self) -> list[Path]:
        return [self.houses_csv, self.crime_csv, self.boe_csv, self.stations_csv, self.boroughs_shp]

    # --- iteration budgets ---------------------------------------------------
    @property
    def n_estimators(self) -> int:
        return 120 if self.fast_mode else 1000

    @property
    def n_expert_estimators(self) -> int:
        return 100 if self.fast_mode else 600

    @property
    def catboost_iterations(self) -> int:
        return 120 if self.fast_mode else 1000

    @property
    def test_frac(self) -> float:
        return 1.0 - self.train_frac - self.val_frac - self.calib_frac


def set_seeds(seed: int) -> None:
    """Make the run reproducible."""
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)
