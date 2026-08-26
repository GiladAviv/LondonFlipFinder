#!/usr/bin/env python
"""CLI entry point for the live-listing flip-rate comparison.

Usage:
    python scripts/run_live_flip_scan.py --stage pilot     # 15 listings, field fill-rate report
    python scripts/run_live_flip_scan.py --stage scrape    # scale scrape to target_n, save CSV
    python scripts/run_live_flip_scan.py --stage compare   # rerun pipeline + enrich + compare
    python scripts/run_live_flip_scan.py --stage all       # scrape then compare
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd

from live_flip_scan.compare import run_comparison
from live_flip_scan.config import LiveScanConfig
from live_flip_scan.pipeline_rerun import get_pipeline_state
from live_flip_scan.scrape_rightmove import run_pilot, run_scale


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["pilot", "scrape", "compare", "all"], default="all")
    parser.add_argument("--target-n", type=int, default=None)
    args = parser.parse_args()

    cfg = LiveScanConfig()
    if args.target_n:
        cfg = LiveScanConfig(target_n=args.target_n)

    listings_path = Path("artifacts/live_scan/listings_raw.csv")

    if args.stage == "pilot":
        run_pilot(cfg)
        return

    if args.stage in ("scrape", "all"):
        listings = run_scale(cfg)
    else:
        listings = pd.read_csv(listings_path)

    if args.stage == "scrape":
        return

    state = get_pipeline_state()
    run_comparison(state, listings, cfg)


if __name__ == "__main__":
    main()
