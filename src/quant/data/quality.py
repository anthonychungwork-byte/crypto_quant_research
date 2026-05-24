"""Data quality checks: missing bars, outliers, timestamp gaps.

Run these on every OHLCV dataset before it enters the splitter. A failed
quality check should halt research — silently working with broken data is
the most expensive bug class in quant research.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class QualityReport:
    """Summary of all quality checks for a single OHLCV dataset."""

    n_bars: int
    n_missing_bars: int
    n_price_outliers: int
    n_zero_volume: int
    has_negative_prices: bool
    has_invalid_ohlc: bool  # high < low, close outside [low, high], etc.

    @property
    def is_clean(self) -> bool:
        """True if no critical issues were detected."""
        return (
            self.n_missing_bars == 0
            and not self.has_negative_prices
            and not self.has_invalid_ohlc
        )

    def summary(self) -> str:
        lines = [
            f"Bars:                {self.n_bars:,}",
            f"Missing bars:        {self.n_missing_bars:,}",
            f"Price outliers (6-sigma): {self.n_price_outliers:,}",
            f"Zero-volume bars:    {self.n_zero_volume:,}",
            f"Negative prices:     {self.has_negative_prices}",
            f"Invalid OHLC:        {self.has_invalid_ohlc}",
            f"Clean:               {self.is_clean}",
        ]
        return "\n".join(lines)


def find_missing_bars(df: pd.DataFrame, expected_freq: str = "1h") -> pd.DatetimeIndex:
    """Return timestamps missing from the expected uniform grid."""
    if df.empty:
        return pd.DatetimeIndex([])
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError(f"Expected DatetimeIndex, got {type(df.index).__name__}")
    expected = pd.date_range(
        start=df.index.min(),
        end=df.index.max(),
        freq=expected_freq,
        tz=df.index.tz,
    )
    return expected.difference(df.index)


def find_price_outliers(df: pd.DataFrame, n_sigma: float = 6.0, window: int = 168) -> pd.DatetimeIndex:
    """Flag bars whose log-return exceeds n_sigma of trailing rolling std."""
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError(f"Expected DatetimeIndex, got {type(df.index).__name__}")
    log_ret = np.log(df["close"]).diff()
    rolling_std = log_ret.rolling(window, min_periods=window // 2).std()
    z = (log_ret - log_ret.rolling(window, min_periods=window // 2).mean()) / rolling_std
    return cast(pd.DatetimeIndex, df.index[(z.abs() > n_sigma) & z.notna()])


def has_invalid_ohlc(df: pd.DataFrame) -> bool:
    """True if any bar has high < low, or close outside [low, high]."""
    high_lt_low = (df["high"] < df["low"]).any()
    close_above_high = (df["close"] > df["high"]).any()
    close_below_low = (df["close"] < df["low"]).any()
    open_above_high = (df["open"] > df["high"]).any()
    open_below_low = (df["open"] < df["low"]).any()
    return bool(high_lt_low or close_above_high or close_below_low or open_above_high or open_below_low)


def quality_report(df: pd.DataFrame, expected_freq: str = "1h") -> QualityReport:
    """Compute the full quality report for an OHLCV DataFrame."""
    return QualityReport(
        n_bars=len(df),
        n_missing_bars=len(find_missing_bars(df, expected_freq)),
        n_price_outliers=len(find_price_outliers(df)),
        n_zero_volume=int((df["volume"] == 0).sum()),
        has_negative_prices=bool((df[["open", "high", "low", "close"]] <= 0).any().any()),
        has_invalid_ohlc=has_invalid_ohlc(df),
    )
