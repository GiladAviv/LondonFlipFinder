"""Score live listings through the trained model + conformal scanner, and compare the resulting
flip rate against the test-set flip rate. Prints the mandatory asking-vs-sold caveat next to the
headline numbers -- generated from what the run actually did, not hand-written prose."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

_SRC = Path(__file__).resolve().parents[2] / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from lff.conformal import scan_for_flips
from lff.notebook import apply_notebook_theme

sys.path.insert(0, str(Path(__file__).resolve().parent))
from assemble import build_live_feature_frame
from config import LiveScanConfig
from pipeline_rerun import PipelineState


def training_last_borough_sqm(pipeline_state: PipelineState) -> pd.Series:
    """The pipeline's own last-known (end-of-training-window) borough L/sqm level, used as the
    real historical anchor the UK HPI growth proxy scales (see enrich_hpi.py)."""
    test = pipeline_state.splits.test.sort_values("date")
    return test.groupby("borough", observed=True)["lagged_borough_median_sqm"].last()


def run_comparison(pipeline_state: PipelineState, listings: pd.DataFrame, cfg: LiveScanConfig):
    last_sqm = training_last_borough_sqm(pipeline_state)
    live_features = build_live_feature_frame(listings, cfg, pipeline_state, last_sqm)

    X_live = pipeline_state.splits.features(live_features)
    predicted = pipeline_state.best.predict(X_live)
    print(f"\nPredicted price range: £{predicted.min():,.0f} - £{predicted.max():,.0f} "
         f"(median £{pd.Series(predicted).median():,.0f})")

    live_scan = scan_for_flips(pipeline_state.best, live_features, pipeline_state.splits,
                               pipeline_state.q_safety)
    live_scan = live_scan.rename(columns={"actual_price": "asking_price"})
    live_flip_rate = live_scan["is_flip"].mean() * 100

    fallback_cols = {
        "market_median_rolling_3m/12m, lagged_borough_median_sqm": "UK HPI proxy (see enrich_hpi.py)",
        "crime_volume, crime_volume_prev_12m": "data.police.uk, point-radius not borough-sum; "
                                               "prev_12m is the latest month annualised, not a real 12m sum",
        "distance_to_underground_m/transit_m": "2008-2016 TfL network only (no Elizabeth Line etc.)",
    }
    epc_fallback_n = int(live_features.get("epc_used_as_fallback", pd.Series(dtype=bool)).sum())
    prior_matched_n = int(live_features["has_prev_sale"].sum())

    print("\n" + "=" * 78)
    print("CAVEAT -- read before interpreting the numbers below:")
    print("=" * 78)
    print(
        "  The model and its conformal floor are calibrated on COMPLETED SALE PRICES\n"
        "  (2008-2016 Land Registry). The 'live' figure below scores CURRENT ASKING\n"
        "  PRICES scraped from Rightmove. These are not the same distribution -- asking\n"
        "  prices are set by sellers/agents and sit above eventual sold prices on\n"
        "  average, with no correction fitted here for that gap (the notebook's own\n"
        "  limitations section names this exact gap and scopes it out of this dataset).\n"
        "  A lower live flip-rate than the test-set rate is the expected direction of\n"
        "  bias from this alone, independent of any real difference in how the 2026\n"
        "  market is priced relative to 2008-2016. Treat this as a directional sanity\n"
        "  check, not a like-for-like statistical claim."
    )
    print("\n  Live-data proxies used in place of the trained features:")
    for cols, note in fallback_cols.items():
        print(f"    {cols}: {note}")
    print(f"    floorAreaSqM / tenure / currentEnergyRating: EPC register fallback used for "
         f"{epc_fallback_n}/{len(live_features)} listings")
    print(f"    prev_sale_price etc.: Land Registry postcode+street match, "
         f"{prior_matched_n}/{len(live_features)} listings matched")
    print("=" * 78)

    print(f"\nTest-set flip rate:  {pipeline_state.test_flip_rate:.2f}%  "
         f"({len(pipeline_state.test_scan):,} properties)")
    print(f"Live-listing flip rate: {live_flip_rate:.2f}%  ({len(live_scan):,} listings)")
    print(f"Delta: {live_flip_rate - pipeline_state.test_flip_rate:+.2f} pp")

    out_dir = Path("artifacts/live_scan")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = out_dir / f"live_scan_{stamp}.csv"
    live_scan.to_csv(csv_path, index=False)
    print(f"\nScored listings -> {csv_path}")

    apply_notebook_theme()
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.bar(["Test set\n(sold prices)", "Live listings\n(asking prices)"],
          [pipeline_state.test_flip_rate, live_flip_rate], color=["#4C72B0", "#DD8452"])
    ax.set_ylabel("Flip-candidate rate (%)")
    ax.set_title("Flip rate: held-out test set vs. live Rightmove listings")
    fig.tight_layout()
    plot_path = out_dir / "flip_rate_comparison.png"
    fig.savefig(plot_path, dpi=110)
    print(f"Plot -> {plot_path}")

    return live_scan, live_flip_rate
