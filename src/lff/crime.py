"""Crime at its native resolution.

`build_crime_features` in clean.py sums the raw file to borough-months: 33 areas. The file
carries `lsoa_code` -- 4,835 areas, a 147x finer geography that the aggregation throws away.
Section 14.5 measured borough crime at +0.11 pp of validation MdAPE and concluded crime does
not earn the 2008-2016 window it forces. That conclusion is only sound if crime was given a
fair test, and three things about the borough version make it not one:

* **Resolution.** Averaging over a whole borough mixes Hampstead with Kilburn. Whatever
  relationship exists between local safety and local price is largely a *within*-borough
  effect, and a borough mean is precisely the statistic that removes it.
* **Count, not rate.** A populous borough records more crime mechanically. LSOAs are built to
  hold roughly 1,500 residents each, so an LSOA count is already close to a per-capita rate --
  the normalisation the borough series never had. Area still varies about tenfold, so density
  per km2 is offered separately: it measures a different thing (busy places attract theft)
  and the ablation can say whether either matters.
* **One series.** Summing burglary together with drug offences assumes a buyer prices them
  identically. Splitting them costs nothing and lets the data disagree.

A caveat that shapes the design: LSOA-months are sparse. Total crime averages about 12 per
LSOA-month and burglary about 2, so a single month is mostly noise. The trailing 12-month
window is the measure to trust here, and it is the one the feature set leads with.
"""
from __future__ import annotations

import geopandas as gpd
import pandas as pd

# The categories a buyer might plausibly price differently, kept apart from each other.
# Everything outside these three lands in "other" rather than being silently dropped.
CATEGORY_GROUPS = {
    "burglary": ["Burglary"],
    "violence": ["Violence Against the Person", "Sexual Offences", "Robbery"],
    "disorder": ["Criminal Damage", "Drugs"],
}


def build_crime_features_lsoa(
    df: pd.DataFrame, boundaries: gpd.GeoDataFrame | None = None
) -> pd.DataFrame:
    """LSOA-month crime: total and per category, each with a strictly-historical 12-month sum.

    Mirrors `build_crime_features` exactly in its time handling -- `closed='left'` excludes the
    current month, so every window is backward-looking -- and differs only in grain.
    """
    out = df.copy()
    out["date"] = pd.to_datetime(
        out["year"].astype(str) + "-" + out["month"].astype(str) + "-01"
    )

    group = pd.Series("other", index=out.index, dtype=object)
    for name, categories in CATEGORY_GROUPS.items():
        group[out["major_category"].isin(categories)] = name
    out["category_group"] = group

    totals = (
        out.groupby(["date", "lsoa_code"], observed=True)["value"]
        .sum()
        .reset_index()
        .rename(columns={"value": "lsoa_crime"})
    )
    # Reindex to the full group list: unstack only emits columns that appear in the data, so a
    # period or subset with no drug offences would silently drop lsoa_crime_disorder and change
    # the feature schema underneath the model.
    all_groups = [*CATEGORY_GROUPS, "other"]
    by_category = (
        out.groupby(["date", "lsoa_code", "category_group"], observed=True)["value"]
        .sum()
        .unstack("category_group", fill_value=0)
        .reindex(columns=all_groups, fill_value=0)
        .reset_index()
    )
    agg = totals.merge(by_category, on=["date", "lsoa_code"], how="left")
    agg = agg.rename(columns={name: f"lsoa_crime_{name}" for name in all_groups})

    series = ["lsoa_crime"] + [f"lsoa_crime_{name}" for name in CATEGORY_GROUPS]
    agg = agg.sort_values(["lsoa_code", "date"])
    for col in series:
        agg[f"{col}_prev_12m"] = agg.groupby("lsoa_code", observed=True)[col].transform(
            lambda s: s.rolling(window=12, closed="left").sum()
        )

    if boundaries is not None:
        area = boundaries.assign(lsoa_area_km2=boundaries.geometry.area / 1e6)
        agg = agg.merge(
            area[["LSOA11CD", "lsoa_area_km2"]].rename(columns={"LSOA11CD": "lsoa_code"}),
            on="lsoa_code", how="left",
        )
        # Density is a genuinely different signal from the count: LSOAs hold a near-constant
        # population, so the count tracks risk-per-resident while density tracks footfall.
        agg["lsoa_crime_density_prev_12m"] = agg["lsoa_crime_prev_12m"] / agg["lsoa_area_km2"]

    agg["lsoa_code"] = agg["lsoa_code"].astype(str)
    print(f"LSOA crime: {len(agg):,} LSOA-months, {agg['lsoa_code'].nunique():,} LSOAs, "
          f"{len(CATEGORY_GROUPS) + 1} category groups")
    print(f"   median crime per LSOA-month: {agg['lsoa_crime'].median():.0f} total, "
          f"{agg['lsoa_crime_burglary'].median():.0f} burglary "
          f"-- sparse, which is why the 12-month window leads")
    return agg


LSOA_CRIME_FEATURES = [
    "lsoa_crime_prev_12m",
    "lsoa_crime_burglary_prev_12m",
    "lsoa_crime_violence_prev_12m",
    "lsoa_crime_disorder_prev_12m",
    "lsoa_crime_density_prev_12m",
]
