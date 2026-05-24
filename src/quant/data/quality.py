"""Data quality checks: missing bars, outliers, timestamp gaps."""

from __future__ import annotations

import pandas as pd


def check_missing_bars(df: pd.DataFrame, expected_freq: str = "1h") -> pd.DataFrame:
    """Identify gaps in time-series at the expected frequency.

    Args:
        df: OHLCV DataFrame with DatetimeIndex.
        expected_freq: Pandas frequency string (default '1h').

    Returns:
        DataFrame of missing timestamps.
    """
    raise NotImplementedError("Implement in Stage 1 (data quality notebook).")


def check_price_outliers(df: pd.DataFrame, n_sigma: float = 6.0) -> pd.DataFrame:
    """Flag bars where return exceeds n_sigma of rolling std.

    Args:
        df: OHLCV DataFrame.
        n_sigma: Threshold in standard deviations.

    Returns:
        DataFrame of flagged outlier bars.
    """
    raise NotImplementedError("Implement in Stage 1 (data quality notebook).")
