"""A property's own transaction history.

The source file is a price *history*: 418,201 rows covering 137,760 unique addresses. Once the
exact duplicates are removed 314,895 distinct sales remain, and 66.0% of addresses still record
two or more of them. The pipeline treats every row as an independent transaction and uses none
of that structure, even though 61.1% of in-window sales have an earlier sale of the same
property somewhere in the file.

The omission is expensive. Predicting a sale as nothing more than its own previous price scaled
by a crude market index -- no model, no features, one line of arithmetic -- lands at 15.64%
MdAPE against the full seventeen-model pipeline's 13.30%. Prior price is the strongest signal
in the dataset and it is also the one a flipper actually reasons with: what did this cost last
time, and what has the market done since.

The features are causally clean by construction -- they read only sales strictly before the row
being predicted -- but "strictly before" is doing real work here, and three things could break
it, so each is handled explicitly:

* **Duplicates.** 102,527 rows of the raw file (24.5%) are exact (address, date, price)
  repeats. Left in, a property appears to sell several times on one day and an as-of merge can
  return the row it is supposed to be predicting.
* **Same-day records.** A further ~800 address-date pairs carry conflicting prices. These are
  collapsed to their median before anything else looks at them.
* **The window.** History is read from the *whole* file, 1995-2024, not from the modelling
  window. A 2009 sale's previous sale is often in 2003, and clipping the history to 2008-2016
  first would silently discard most of the signal.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Everything the module constructs -- the candidate set the section 14.6 ablation ranges over.
PRIOR_SALE_FEATURES = [
    "prev_sale_price",
    "log_prev_sale_price",
    "years_since_prev_sale",
    "prev_sale_days_since_start",
    "n_prior_sales",
    "has_prev_sale",
]

# The four the ablation actually justified: +0.913 pp of validation MdAPE, winning all three
# seeds. Carrying all six scores +0.894 pp, so log_prev_sale_price and n_prior_sales earn
# nothing -- a tree splits on order, and the log of a feature it already has is the same
# ordering. Prior price alone is worth +0.453 pp; the elapsed-time pair doubles that, which is
# the point: a price is only interpretable against how long ago it was paid.
PRIOR_SALE_ADOPTED = [
    "prev_sale_price",
    "has_prev_sale",
    "years_since_prev_sale",
    "prev_sale_days_since_start",
]


def build_sale_history(houses_raw: pd.DataFrame) -> pd.DataFrame:
    """One row per (address, date) across the full 1995-2024 file, prices reconciled.

    Takes the *raw* house frame, before `clean_houses` restricts it to the modelling window.
    """
    history = houses_raw[["fullAddress", "history_date", "history_price"]].copy()
    history = history.rename(columns={"history_date": "date", "history_price": "price"})
    history["date"] = pd.to_datetime(history["date"])
    history = history.dropna(subset=["fullAddress", "date", "price"])

    before = len(history)
    history = history.drop_duplicates(subset=["fullAddress", "date", "price"])
    print(f"Sale history: {before:,} rows -> {len(history):,} after exact duplicates "
          f"({before - len(history):,} removed, {(before - len(history)) / before:.1%})")

    # Conflicting prices for one address on one day: take the median rather than pick a side.
    conflicts = history.duplicated(subset=["fullAddress", "date"]).sum()
    if conflicts:
        history = (history.groupby(["fullAddress", "date"], as_index=False)["price"]
                   .median())
        print(f"   {conflicts:,} same-day price conflicts collapsed to their median")

    history = history.sort_values(["date", "fullAddress"]).reset_index(drop=True)
    per_address = history.groupby("fullAddress").size()
    print(f"   {len(history):,} sales across {len(per_address):,} addresses; "
          f"{(per_address >= 2).mean():.1%} of addresses sold more than once "
          f"({history['date'].min():%Y} to {history['date'].max():%Y})")
    return history


def _count_prior_sales(target: pd.DataFrame, history: pd.DataFrame) -> np.ndarray:
    """How many sales of this address precede this row's date, strictly.

    A binary search per address rather than a self-join: the history has 300k+ rows and a
    cross-join against the model frame would be quadratic in the repeat-sale addresses.
    """
    dates_by_address = {
        address: group["date"].to_numpy()
        for address, group in history.groupby("fullAddress", sort=False)
    }
    counts = np.zeros(len(target), dtype=np.int32)
    for i, (address, when) in enumerate(
        zip(target["fullAddress"].to_numpy(), target["date"].to_numpy())
    ):
        known = dates_by_address.get(address)
        if known is not None:
            # side="left" excludes a sale on the same day, matching allow_exact_matches=False.
            counts[i] = np.searchsorted(known, when, side="left")
    return counts


def add_prior_sale_features(df: pd.DataFrame, history: pd.DataFrame) -> pd.DataFrame:
    """Attach each property's own most recent earlier sale.

    `allow_exact_matches=False` is what makes this safe: a sale on the same day as the row
    being predicted is the row being predicted, and matching it would be a direct read of the
    target.
    """
    out = df.sort_values("date").reset_index(drop=True)
    prior = history.rename(columns={"date": "prev_sale_date", "price": "prev_sale_price"})
    prior = prior.sort_values("prev_sale_date")

    merged = pd.merge_asof(
        out,
        prior,
        left_on="date",
        right_on="prev_sale_date",
        by="fullAddress",
        direction="backward",
        allow_exact_matches=False,
    )

    merged["has_prev_sale"] = merged["prev_sale_price"].notna().astype(int)
    merged["log_prev_sale_price"] = np.log1p(merged["prev_sale_price"])
    merged["years_since_prev_sale"] = (
        (merged["date"] - merged["prev_sale_date"]).dt.days / 365.25
    )
    # Elapsed days on the same clock as days_since_start, so a tree can compare the two
    # directly and infer how much market movement sits between the sales. Deliberately not
    # pre-multiplied by an index computed from this dataset -- that index would be built from
    # rows the model has not earned the right to see.
    origin = out["date"].min()
    merged["prev_sale_days_since_start"] = (
        (merged["prev_sale_date"] - origin).dt.days.astype("float64")
    )
    merged["n_prior_sales"] = _count_prior_sales(out, history)

    coverage = merged["has_prev_sale"].mean()
    gap = merged.loc[merged["has_prev_sale"] == 1, "years_since_prev_sale"]
    print(f"Prior-sale features: {merged['has_prev_sale'].sum():,} of {len(merged):,} rows "
          f"({coverage:.1%}) have an earlier sale of the same property")
    if len(gap):
        print(f"   years since that sale: median {gap.median():.1f} "
              f"(p10 {gap.quantile(0.1):.1f}, p90 {gap.quantile(0.9):.1f})")
    return merged


def assert_no_lookahead(df: pd.DataFrame) -> None:
    """Every prior sale must predate the row that reads it. Cheap enough to always run."""
    matched = df[df["has_prev_sale"] == 1]
    if matched.empty:
        return
    offending = (matched["prev_sale_date"] >= matched["date"]).sum()
    if offending:
        raise AssertionError(
            f"{offending:,} rows carry a prior sale dated at or after their own sale date"
        )
    if (matched["years_since_prev_sale"] <= 0).any():
        raise AssertionError("non-positive years_since_prev_sale survived the merge")
