"""Drawdown analysis: peak-to-trough, recovery time, underwater periods."""

from __future__ import annotations

import numpy as np
import pandas as pd


def max_drawdown(equity_curve: pd.Series) -> float:
    """Maximum drawdown as a fraction (0.25 = 25%).

    Args:
        equity_curve: Cumulative equity over time.

    Returns:
        Maximum drawdown as a positive fraction.
    """
    running_max = equity_curve.cummax()
    drawdown = (equity_curve - running_max) / running_max
    return float(abs(drawdown.min()))


def underwater_duration(equity_curve: pd.Series) -> pd.Series:
    """Number of consecutive periods below the prior peak.

    Args:
        equity_curve: Cumulative equity over time.

    Returns:
        Series of underwater duration (in bars) at each timestamp.
    """
    running_max = equity_curve.cummax()
    underwater = equity_curve < running_max
    # Reset counter each time we hit a new peak
    groups = (~underwater).cumsum()
    return underwater.groupby(groups).cumsum().astype(np.int64)
