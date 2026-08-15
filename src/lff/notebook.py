"""Presentation setup for the notebook: theme, display width, warning filters."""
from __future__ import annotations

import warnings

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def apply_notebook_theme() -> None:
    """Chart theme, frame display width and the two warning filters the notebook relies on."""
    # Narrow, intentional warning filters -- not a blanket silence.
    warnings.filterwarnings("ignore", category=FutureWarning, module="seaborn")
    warnings.filterwarnings("ignore", message=".*is_sparse is deprecated.*")

    sns.set_theme(style="whitegrid")
    plt.rcParams["figure.dpi"] = 110
    pd.set_option("display.width", 160)
    pd.set_option("display.max_columns", 60)
