"""Trailing return / momentum signal utilities.

Used by TSMOM (Time-Series Momentum) and related strategies.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def trailing_return(prices: pd.Series, lookback_bars: int) -> pd.Series:
    """Rolling N-bar return: price[t] / price[t-N] - 1.

    Args:
        prices: Price series indexed by time.
        lookback_bars: Number of bars to look back.

    Returns:
        Series of trailing returns aligned to `prices.index`.
        First `lookback_bars` entries are NaN.
    """
    if lookback_bars <= 0:
        raise ValueError(f"lookback_bars must be positive, got {lookback_bars}")
    return prices / prices.shift(lookback_bars) - 1.0


def trailing_volatility(returns: pd.Series, lookback_bars: int) -> pd.Series:
    """Rolling realized volatility (std of returns) over the past N bars.

    Args:
        returns: Return series (typically log returns or simple returns).
        lookback_bars: Window length.

    Returns:
        Series of rolling std aligned to input.
    """
    if lookback_bars <= 1:
        raise ValueError(f"lookback_bars must be > 1, got {lookback_bars}")
    return returns.rolling(window=lookback_bars, min_periods=lookback_bars).std()


def momentum_signal(
    prices: pd.Series,
    lookback_bars: int,
    threshold: float = 0.0,
) -> pd.Series:
    """Discrete momentum signal: +1 (long) / -1 (short) / 0 (flat).

    Args:
        prices: Price series.
        lookback_bars: Lookback window.
        threshold: Dead-zone width as a fraction (e.g. 0.02 = 2%).
            |trailing_return| < threshold → flat.

    Returns:
        Integer Series (+1/-1/0) aligned to `prices.index`.
    """
    if threshold < 0:
        raise ValueError(f"threshold must be non-negative, got {threshold}")
    ret = trailing_return(prices, lookback_bars)
    sig = pd.Series(np.zeros(len(prices), dtype=np.int64), index=prices.index, name="signal")
    sig[ret > threshold] = 1
    sig[ret < -threshold] = -1
    return sig
