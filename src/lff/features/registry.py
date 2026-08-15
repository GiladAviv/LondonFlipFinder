"""The feature contract: what the models see, and how the groups ablate."""
from __future__ import annotations

FEATURES = [
    "floorAreaSqM", "total_rooms", "avg_room_size", "bathrooms",
    "distance_to_underground_m", "distance_to_transit_m", "station_zone",
    "distance_to_center_m", "latitude", "longitude",
    "crime_volume", "crime_volume_prev_12m", "interest_rate",
    "propertyType", "tenure", "borough", "outcode", "currentEnergyRating",
    "days_since_start", "month_sin", "month_cos",
    "market_median_rolling_3m", "market_median_rolling_12m", "lagged_borough_median_sqm",
]


CATEGORICAL_FEATURES = ["propertyType", "tenure", "borough", "outcode", "currentEnergyRating"]


# The borough-grain crime series. Named separately because section 8.2 swaps it out for the
# LSOA-grain equivalent to test whether the ablation's verdict on crime is a verdict on crime
# or only on the resolution it was measured at.
BOROUGH_CRIME_FEATURES = ["crime_volume", "crime_volume_prev_12m"]


# Feature groups for the ablation study in section 14.5.
FEATURE_GROUPS = {
    "crime": BOROUGH_CRIME_FEATURES,
    "transport": ["distance_to_underground_m", "distance_to_transit_m", "station_zone"],
    "macro": ["interest_rate"],
    "market lags": ["market_median_rolling_3m", "market_median_rolling_12m",
                    "lagged_borough_median_sqm"],
}


NUMERIC_FEATURES = [f for f in FEATURES if f not in CATEGORICAL_FEATURES]


TARGET = "price"
