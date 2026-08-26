"""Tunables for the live-listing scrape and enrichment, kept out of the training pipeline's own
Config since this is a one-off script, not a maintained package feature."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class LiveScanConfig:
    user_agent: str = (
        "LondonFlipFinder-research/0.1 (+contact: giladaviv987@gmail.com; "
        "one-off academic comparison, low-volume)"
    )
    rate_limit_s: float = 1.2          # floor delay between requests; jittered +/-20% at call time
    pilot_n: int = 15
    target_n: int = 200                # within the agreed 100-300 range
    max_search_pages: int = 25         # hard request-volume ceiling, independent of target_n
    site: str = "rightmove"            # "rightmove" | "zoopla"
    search_region: str = "REGION%5E87490"  # Rightmove's London region identifier (URL-encoded)
    cache_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent / "cache")
    max_retries: int = 2
    epc_api_key_env: str = "LFF_EPC_API_KEY"
