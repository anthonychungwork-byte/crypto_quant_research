"""Tests for src/quant/strategies/tsmom.py."""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant.backtest.costs import CostMode, get_cost_model
from quant.strategies.base import Signal
from quant.strategies.tsmom import TSMOMConfig, TSMOMStrategy


def _make_trending_ohlcv(date: str, n_hours: int, drift_per_hour: float = 0.001) -> pd.DataFrame:
    """Build trending price series with constant drift."""
    timestamps = pd.date_range(date, periods=n_hours, freq="1h", tz="UTC")
    log_returns = np.full(n_hours, drift_per_hour)
    log_returns[0] = 0
    close = 100.0 * np.exp(np.cumsum(log_returns))
    return pd.DataFrame(
        {
            "open": close,
            "high": close * 1.001,
            "low": close * 0.999,
            "close": close,
            "volume": np.full(n_hours, 100.0),
        },
        index=timestamps,
    )


class TestTSMOMSignals:
    def test_long_signal_on_rebalance_when_trending_up(self) -> None:
        """Strongly uptrending prices → LONG signal at Monday 00:00 UTC."""
        # 8 weeks of strong uptrend
        df = _make_trending_ohlcv("2024-01-01", n_hours=8 * 168, drift_per_hour=0.002)
        cfg = TSMOMConfig(name="tsmom", timeframe="1h", lookback_weeks=2, signal_threshold=0.01)
        sigs = TSMOMStrategy(cfg).generate_signals(df)
        non_flat = sigs[sigs != Signal.FLAT.value]
        # Should have at least 1 LONG signal at a Monday 00:00 after lookback
        assert (non_flat == Signal.LONG.value).any()
        # All non-flat signals must be at Monday 00:00 UTC
        for ts in non_flat.index:
            assert ts.dayofweek == 0
            assert ts.hour == 0

    def test_short_signal_when_trending_down(self) -> None:
        df = _make_trending_ohlcv("2024-01-01", n_hours=8 * 168, drift_per_hour=-0.002)
        cfg = TSMOMConfig(name="tsmom", timeframe="1h", lookback_weeks=2, signal_threshold=0.01)
        sigs = TSMOMStrategy(cfg).generate_signals(df)
        non_flat = sigs[sigs != Signal.FLAT.value]
        assert (non_flat == Signal.SHORT.value).any()

    def test_flat_signal_when_no_trend(self) -> None:
        df = _make_trending_ohlcv("2024-01-01", n_hours=8 * 168, drift_per_hour=0.0)
        cfg = TSMOMConfig(name="tsmom", timeframe="1h", lookback_weeks=2, signal_threshold=0.01)
        sigs = TSMOMStrategy(cfg).generate_signals(df)
        # All FLAT (no trend → no signal exceeds threshold)
        assert (sigs == Signal.FLAT.value).all()


class TestTSMOMSimulate:
    def test_uptrend_produces_long_trades(self) -> None:
        df = _make_trending_ohlcv("2024-01-01", n_hours=12 * 168, drift_per_hour=0.0015)
        cfg = TSMOMConfig(name="tsmom", timeframe="1h", lookback_weeks=2, signal_threshold=0.01)
        trades = TSMOMStrategy(cfg).simulate(df, cost_model=get_cost_model(CostMode.HORROR))
        assert len(trades) > 0
        # At least some LONG trades
        assert (trades["side"] == "LONG").any()

    def test_horror_cost_applied(self) -> None:
        df = _make_trending_ohlcv("2024-01-01", n_hours=12 * 168, drift_per_hour=0.0015)
        cfg = TSMOMConfig(name="tsmom", timeframe="1h", lookback_weeks=2, signal_threshold=0.01)
        trades = TSMOMStrategy(cfg).simulate(df, cost_model=get_cost_model(CostMode.HORROR))
        np.testing.assert_allclose(trades["cost_pct"].to_numpy(), 0.0064)

    def test_no_signal_no_trades(self) -> None:
        df = _make_trending_ohlcv("2024-01-01", n_hours=12 * 168, drift_per_hour=0.0)
        cfg = TSMOMConfig(name="tsmom", timeframe="1h", lookback_weeks=2, signal_threshold=0.01)
        trades = TSMOMStrategy(cfg).simulate(df)
        assert len(trades) == 0
