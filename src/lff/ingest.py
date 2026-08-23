"""Dataset acquisition and raw reads. Lifted from notebook sections 3-4."""
from __future__ import annotations

import time
import zipfile

import pandas as pd

from .config import Config


def ensure_dataset(cfg: Config) -> None:
    """Download + extract the release archive unless every required file is already present."""
    missing = [p for p in cfg.required_files if not p.exists()]
    if not missing:
        print(f"All {len(cfg.required_files)} required inputs present in {cfg.data_dir}")
        return

    print(f"Missing {len(missing)} input(s); fetching the dataset archive...")
    for p in missing:
        print(f"   - {p.relative_to(cfg.data_dir) if cfg.data_dir in p.parents else p}")

    import requests  # local import: only needed on the download path

    target_root = cfg.data_dir.parent
    target_root.mkdir(parents=True, exist_ok=True)
    archive = target_root / "dataset.zip"

    with requests.get(cfg.dataset_url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        done = 0
        with open(archive, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
                done += len(chunk)
                if total:
                    print(f"\r   {done / 1e6:7.1f} / {total / 1e6:.1f} MB", end="")
    print("\n   extracting...")
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(target_root)
    archive.unlink()

    still_missing = [p for p in cfg.required_files if not p.exists()]
    if still_missing:
        raise FileNotFoundError(
            "Dataset archive did not contain the expected files. Missing:\n  "
            + "\n  ".join(str(p) for p in still_missing)
        )
    print(f"Dataset ready in {cfg.data_dir}")


HOUSE_COLUMNS = [
    "fullAddress", "postcode", "outcode", "latitude", "longitude",
    "bathrooms", "bedrooms", "livingRooms", "floorAreaSqM",
    "tenure", "propertyType", "currentEnergyRating", "history_date", "history_price",
]


CRIME_DTYPES = {"borough": "category", "value": "int32", "year": "int16", "month": "int8"}


def load_raw(cfg: Config) -> dict[str, pd.DataFrame]:
    """Read every input we actually model on. Returns plain DataFrames, no side effects."""
    started = time.time()

    houses = pd.read_csv(cfg.houses_csv, usecols=HOUSE_COLUMNS)
    crime = pd.read_csv(cfg.crime_csv, usecols=list(CRIME_DTYPES), dtype=CRIME_DTYPES)
    boe = pd.read_csv(cfg.boe_csv)
    stations = pd.read_csv(cfg.stations_csv)

    raw = {"houses": houses, "crime": crime, "boe": boe, "stations": stations}

    print(f"Loaded {len(raw)} sources in {time.time() - started:.1f}s")
    for name, frame in raw.items():
        mem = frame.memory_usage(deep=True).sum() / 1e6
        print(f"   {name:<10} {len(frame):>12,} rows x {frame.shape[1]:>2} cols  ({mem:6.0f} MB)")
    return raw
