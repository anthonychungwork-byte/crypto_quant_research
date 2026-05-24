"""Shared pytest fixtures."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def synthetic_ohlcv() -> pd.DataFrame:
    """Deterministic synthetic OHLCV for testing.

    Geometric Brownian motion with weak drift, seeded for reproducibility.
    Hourly bars over ~12 days.
    """
    rng = np.random.default_rng(seed=42)
    n = 300
    timestamps = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")

    log_returns = rng.normal(loc=0.0001, scale=0.005, size=n)
    close = 50_000.0 * np.exp(np.cumsum(log_returns))

    # Construct plausible OHLC from close (bar-level noise ~ 0.1%)
    noise = rng.normal(loc=0.0, scale=0.001, size=n)
    high = close * (1 + np.abs(noise))
    low = close * (1 - np.abs(noise))
    open_ = np.roll(close, 1)
    open_[0] = close[0]

    return pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": rng.uniform(10, 100, size=n),
        },
        index=timestamps,
    )
