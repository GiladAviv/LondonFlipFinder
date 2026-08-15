"""Every figure in the notebook. Each is a pure function of a DataFrame."""
from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap

from .config import Config
from .features.registry import FEATURES
from .metrics import ModelBundle
from .split import Splits

# Validated categorical palette, applied in fixed slot order so a colour always means the
# same thing. Slots 1-3 are safe for every chart form; past three, charts fold to "Other".
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]  # blue, orange, aqua, yellow
MUTED, GRID = "#52514e", "#d9d8d4"

DIVERGING = LinearSegmentedColormap.from_list(
    "blue_grey_red", ["#1c5cab", "#f0efec", "#e34948"]
)

GBP = ticker.FuncFormatter(lambda x, _: f"\N{POUND SIGN}{int(x):,}")


def style_axis(ax, *, currency_y: bool = False, currency_x: bool = False) -> None:
    """Recessive grid and axes so the data marks carry the message."""
    ax.grid(True, linestyle="--", alpha=0.35, color=GRID)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(GRID)
    ax.tick_params(colors=MUTED)
    if currency_y:
        ax.yaxis.set_major_formatter(GBP)
    if currency_x:
        ax.xaxis.set_major_formatter(GBP)


def display_frame(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """95th-percentile clip for plotting only -- models always see untruncated prices."""
    return df[df["price"] <= df["price"].quantile(0.95)].copy()


def plot_property_characteristics(df: pd.DataFrame, cfg: Config) -> None:
    """Physical drivers of price: distribution, scale, asset type, and inter-correlation."""
    vis = display_frame(df, cfg)
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle("Property characteristics and price", fontsize=18, fontweight="bold")

    sns.histplot(vis["price"], bins=40, kde=True, ax=axes[0, 0], color=SERIES[0])
    axes[0, 0].set(title="Price distribution (to 95th percentile)",
                   xlabel="Price", ylabel="Properties")
    style_axis(axes[0, 0], currency_x=True)

    rooms = vis[vis["total_rooms"].between(1, 8)]
    sns.boxplot(data=rooms, x="total_rooms", y="price", ax=axes[0, 1],
                color=SERIES[0], showfliers=False, linewidth=1.2)
    axes[0, 1].set(title="Price by total rooms", xlabel="Bedrooms + living rooms", ylabel="Price")
    style_axis(axes[0, 1], currency_y=True)

    by_type = vis.groupby("propertyType")["price"].median().sort_values(ascending=False).head(10)
    axes[1, 0].barh(by_type.index[::-1], by_type.values[::-1], color=SERIES[0], height=0.7)
    axes[1, 0].set(title="Median price by property type", xlabel="Median price", ylabel="")
    style_axis(axes[1, 0], currency_x=True)

    cols = ["price", "floorAreaSqM", "total_rooms", "bathrooms",
            "distance_to_underground_m", "distance_to_center_m"]
    corr = vis[cols].corr()
    sns.heatmap(corr, annot=True, fmt=".2f", cmap=DIVERGING, center=0, vmin=-1, vmax=1,
                ax=axes[1, 1], square=True, linewidths=2, linecolor="white",
                cbar_kws={"shrink": 0.8})
    axes[1, 1].set_title("Feature correlation")

    plt.tight_layout()
    plt.show()


TUBE_BINS = [0, 250, 500, 750, 1000, 1250, 1500, 2000, 2500, 3000, np.inf]


TUBE_LABELS = ["0-250m", "250-500m", "500-750m", "750m-1km", "1-1.25km",
               "1.25-1.5km", "1.5-2km", "2-2.5km", "2.5-3km", "3km+"]


def plot_tube_premium(df: pd.DataFrame, cfg: Config) -> None:
    """Distance decay: how price falls as the walk to the nearest Underground station lengthens."""
    band = df[["distance_to_underground_m", "price"]].dropna().copy()
    band["distance_group"] = pd.cut(band["distance_to_underground_m"],
                                    bins=TUBE_BINS, labels=TUBE_LABELS)
    means = band.groupby("distance_group", observed=True)["price"].mean()

    fig, ax = plt.subplots(figsize=(13, 5.5))
    ax.bar(means.index.astype(str), means.values, color=SERIES[0], width=0.72)
    ax.set(title="The tube premium: mean price by distance to the nearest station",
           xlabel="Distance to nearest station", ylabel="Mean price")
    ax.tick_params(axis="x", rotation=30)
    style_axis(ax, currency_y=True)
    plt.tight_layout()
    plt.show()


def plot_crime_and_market(df: pd.DataFrame, cfg: Config) -> None:
    """Crime banding, plus price and base rate over time on shared time axis."""
    vis = display_frame(df, cfg)
    vis = vis.dropna(subset=["crime_volume_prev_12m"]).copy()
    vis["crime_level"] = pd.qcut(vis["crime_volume_prev_12m"], q=4,
                                 labels=["Low", "Moderate", "High", "Severe"])

    fig, ax = plt.subplots(figsize=(13, 5))
    sns.boxplot(data=vis, x="crime_level", y="price", ax=ax, color=SERIES[0],
                showfliers=False, linewidth=1.2)
    ax.set(title="Price by neighbourhood crime band (trailing 12-month borough volume)",
           xlabel="Crime band", ylabel="Price")
    style_axis(ax, currency_y=True)
    plt.tight_layout()
    plt.show()

    # Two panels sharing one x-axis -- never twin y-axes. See the note above.
    timeline = df.groupby("month_year").agg(
        price=("price", "median"), interest_rate=("interest_rate", "mean")
    ).reset_index()

    fig, (ax_top, ax_bot) = plt.subplots(
        2, 1, figsize=(13, 8), sharex=True, gridspec_kw={"height_ratios": [2, 1]}
    )
    ax_top.plot(timeline["month_year"], timeline["price"], color=SERIES[0], linewidth=2)
    ax_top.set(title="Median London transaction price", ylabel="Median price")
    style_axis(ax_top, currency_y=True)

    ax_bot.plot(timeline["month_year"], timeline["interest_rate"], color=SERIES[1], linewidth=2)
    ax_bot.set(title="Bank of England base rate", ylabel="Rate (%)", xlabel="")
    style_axis(ax_bot)

    fig.suptitle("Housing market and the cost of borrowing, 2008-2016",
                 fontsize=16, fontweight="bold")
    plt.tight_layout()
    plt.show()


def plot_price_vs_area(df: pd.DataFrame, cfg: Config) -> None:
    """Log-log scale: where 'mega-properties' depart from the standard market trend."""
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.scatter(df["floorAreaSqM"], df["price"], s=6, alpha=0.25,
               color=SERIES[0], edgecolors="none")
    ax.set(xscale="log", yscale="log", xlabel="Floor area (sqm)", ylabel="Price",
           title="Price versus floor area (log-log)")
    ax.xaxis.set_major_formatter(ticker.ScalarFormatter())
    style_axis(ax, currency_y=True)
    plt.tight_layout()
    plt.show()


def plot_price_per_sqm_by_borough(df: pd.DataFrame, cfg: Config) -> None:
    """Unit land value -- strips out the size effect that dominates headline price."""
    per_sqm = df.groupby("borough")["price_per_sqm"].median().sort_values()
    fig, ax = plt.subplots(figsize=(11, 10))
    ax.barh(per_sqm.index, per_sqm.values, color=SERIES[0], height=0.72)
    ax.set(title="Median price per square metre by borough", xlabel="Median price per sqm",
           ylabel="")
    style_axis(ax, currency_x=True)
    plt.tight_layout()
    plt.show()


def plot_leaderboard(board: pd.DataFrame, title: str) -> None:
    """Ranked comparison. One flat hue -- colour must not encode rank."""
    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(16, 6))
    order = board.sort_values("MdAPE", ascending=False)

    ax_left.barh(order["Model"], order["MdAPE"], color=SERIES[0], height=0.68)
    ax_left.set(title="Typical error (MdAPE) - lower is better", xlabel="MdAPE (%)")
    style_axis(ax_left)
    for y, v in enumerate(order["MdAPE"]):
        ax_left.text(v, y, f" {v:.2f}%", va="center", fontsize=9, color=MUTED)

    ax_right.barh(order["Model"], order["MAE"], color=SERIES[0], height=0.68)
    ax_right.set(title="Mean absolute error - lower is better", xlabel="MAE")
    ax_right.set_yticklabels([])
    style_axis(ax_right, currency_x=True)

    fig.suptitle(title, fontsize=16, fontweight="bold")
    plt.tight_layout()
    plt.show()


def plot_error_diagnostics(bundle: ModelBundle, part: pd.DataFrame, splits: Splits) -> None:
    """Where the error lives: bias against price level, and the shape of the error distribution."""
    actual = splits.target(part).to_numpy(dtype=float)
    predicted = bundle.predict(splits.features(part))
    residuals = actual - predicted
    ape = np.abs(residuals / actual) * 100

    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(16, 6))

    ax_left.scatter(predicted, residuals, s=6, alpha=0.25, color=SERIES[0], edgecolors="none")
    ax_left.axhline(0, color=MUTED, linestyle="--", linewidth=1)
    ax_left.set(title="Residuals against prediction", xlabel="Predicted price",
                ylabel="Actual - predicted")
    style_axis(ax_left, currency_x=True, currency_y=True)

    ax_right.hist(np.clip(ape, 0, 100), bins=50, color=SERIES[0])
    ax_right.axvline(np.median(ape), color=SERIES[1], linewidth=2,
                     label=f"median {np.median(ape):.1f}%")
    ax_right.set(title="Absolute percentage error", xlabel="Absolute percentage error (%)",
                 ylabel="Properties")
    ax_right.legend(frameon=False)
    style_axis(ax_right)

    fig.suptitle(f"Test-set error diagnostics: {bundle.name}", fontsize=16, fontweight="bold")
    plt.tight_layout()
    plt.show()

    print(f"Median absolute percentage error : {np.median(ape):.2f}%")
    print(f"Predicted within 25% of actual   : {(ape <= 25).mean() * 100:.1f}%")
    print(f"Mean residual (bias)             : \N{POUND SIGN}{residuals.mean():,.0f}")


def plot_feature_importance(bundle: ModelBundle, top_n: int = 15) -> None:
    """Gain-based importance for the best single tree model."""
    model = bundle.artefacts.get("model")
    if model is None:
        print(f"{bundle.name} has no single underlying tree model to inspect.")
        return

    importance = pd.Series(model.feature_importances_, index=FEATURES).nlargest(top_n)
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.barh(importance.index[::-1], importance.values[::-1], color=SERIES[0], height=0.7)
    ax.set(title=f"What drives price: {bundle.name}", xlabel="Relative importance (gain)")
    style_axis(ax)
    plt.tight_layout()
    plt.show()
    print("Caution: gain importance splits credit arbitrarily between correlated features, and\n"
          "latitude, longitude, borough, outcode and distance-to-centre are all the same signal.")


def plot_ablation(frame: pd.DataFrame) -> None:
    """Validation-MdAPE cost of removing each feature group, relative to the full model."""
    ablated = frame[frame["Variant"] != "Full"].sort_values("MdAPE delta")
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.barh(ablated["Variant"], ablated["MdAPE delta"], color=SERIES[0], height=0.6)
    ax.axvline(0, color=MUTED, linewidth=1)
    ax.set(title="Cost of removing each feature group (validation MdAPE, higher = more valuable)",
          xlabel="MdAPE delta vs. full model (percentage points)")
    style_axis(ax)
    plt.tight_layout()
    plt.show()


def plot_flip_margins(flips: pd.DataFrame, scan: pd.DataFrame, q_safety: float,
                      cfg: Config) -> None:
    """Distribution of the safety margin, and where flags sit against the floor."""
    if flips.empty:
        print("No flip candidates under the current safety constraint.")
        return

    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(16, 6))

    ax_left.hist(flips["margin"], bins=30, color=SERIES[0])
    ax_left.set(title="Margin below the 90% floor", xlabel="Margin", ylabel="Properties")
    style_axis(ax_left, currency_x=True)

    sample = scan.sample(min(len(scan), 4000), random_state=cfg.seed)
    ax_right.scatter(sample["predicted_value"], sample["actual_price"], s=6, alpha=0.25,
                     color=SERIES[0], edgecolors="none", label="Test properties")
    flagged = sample[sample["is_flip"]]
    ax_right.scatter(flagged["predicted_value"], flagged["actual_price"], s=14, alpha=0.9,
                     color=SERIES[1], edgecolors="none", label="Flip candidate")
    line = np.linspace(sample["predicted_value"].min(), sample["predicted_value"].max(), 100)
    ax_right.plot(line, line * q_safety, color=MUTED, linestyle="--", linewidth=1.5,
                  label=f"90% floor (x{q_safety:.2f})")
    ax_right.set(title="Actual price against prediction", xlabel="Predicted value",
                 ylabel="Actual price", xscale="log", yscale="log")
    ax_right.legend(frameon=False, loc="upper left")
    style_axis(ax_right)

    fig.suptitle("Flip scanner output", fontsize=16, fontweight="bold")
    plt.tight_layout()
    plt.show()
