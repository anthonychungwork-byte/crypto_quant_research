"""Smoke test for the grid search runner using a 2x2 grid on synthetic data."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant.optimization.grid_search import grid_search_mean_reversion


@pytest.fixture
def synthetic_year_ohlcv() -> pd.DataFrame:
    """1 year of hourly synthetic data — enough to produce ~10 trades."""
    rng = np.random.default_rng(seed=42)
    n = 24 * 365
    timestamps = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    log_returns = rng.normal(loc=0.0, scale=0.005, size=n)
    close = 50_000.0 * np.exp(np.cumsum(log_returns))
    high = close * (1 + np.abs(rng.normal(0, 0.003, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.003, n)))
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": rng.uniform(10, 100, n)},
        index=timestamps,
    )


class TestGridSearch:
    def test_runs_full_grid(self, synthetic_year_ohlcv: pd.DataFrame) -> None:
        """A small 2x2x2x2x2 = 32 grid runs end-to-end."""
        grid = {
            "min_range_pct": [0.005, 0.010],
            "extreme_proximity_pct": [0.20, 0.30],
            "stop_buffer_pct": [0.005, 0.010],
            "tp_fraction": [0.4, 0.6],
            "time_stop_hours": [4, 6],
        }
        results = grid_search_mean_reversion(synthetic_year_ohlcv, grid)
        assert len(results) == 32
        # Sorted by Sharpe descending
        assert results["sharpe"].is_monotonic_decreasing
        # Each row has the N_trials field set correctly
        assert (results["n_trials"] == 32).all()

    def test_metric_columns_present(self, synthetic_year_ohlcv: pd.DataFrame) -> None:
        grid = {
            "min_range_pct": [0.005],
            "extreme_proximity_pct": [0.20],
            "stop_buffer_pct": [0.005],
            "tp_fraction": [0.5],
            "time_stop_hours": [6],
        }
        results = grid_search_mean_reversion(synthetic_year_ohlcv, grid)
        expected = {"n_trials", "n_trades", "win_rate", "pf", "sharpe", "max_dd", "cagr"}
        assert expected.issubset(set(results.columns))
