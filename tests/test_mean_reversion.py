"""Tests for src/quant/strategies/mean_reversion.py — entry conditions + exit handling."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant.backtest.costs import CostMode, get_cost_model
from quant.strategies.mean_reversion import MeanReversionConfig, MeanReversionStrategy


def _make_day_ohlcv(
    date: str,
    asian_high: float,
    asian_low: float,
    asian_close: float,
    asian_open: float | None = None,
) -> pd.DataFrame:
    """Build one synthetic UTC trading day (24 hourly bars).

    The Asian session (hours 0-12) is shaped so that:
        - max(high) = asian_high
        - min(low) = asian_low
        - close at hour 12 = asian_close
        - open at hour 0 = asian_open (defaults to mid-range)

    Hours 13-23 are filled with bars hovering near asian_close (no SL/TP hit).
    """
    if asian_open is None:
        asian_open = (asian_high + asian_low) / 2

    timestamps = pd.date_range(date, periods=24, freq="1h", tz="UTC")

    open_ = np.full(24, asian_close, dtype=np.float64)
    close = np.full(24, asian_close, dtype=np.float64)
    high = np.full(24, asian_close, dtype=np.float64)
    low = np.full(24, asian_close, dtype=np.float64)
    volume = np.full(24, 100.0, dtype=np.float64)

    # Asian session shaping
    open_[0] = asian_open
    high[6] = asian_high  # mid-session
    low[3] = asian_low
    close[12] = asian_close

    # Ensure each Asian bar's high >= max(open, close, low) and low <= min(open, close, high)
    for i in range(13):
        high[i] = max(high[i], open_[i], close[i])
        low[i] = min(low[i], open_[i], close[i])

    # Post-Asian bars (13-23): flat near close, no breakout
    open_[13:] = asian_close
    close[13:] = asian_close
    high[13:] = asian_close * 1.0005
    low[13:] = asian_close * 0.9995

    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=timestamps,
    )


class TestEntryConditions:
    """Tests for _evaluate_day — direction selection and filter rules."""

    def test_short_entry_when_close_near_high(self) -> None:
        # Asian range: 100-110. Close at 109.5 → very near high → SHORT
        df = _make_day_ohlcv("2024-01-01", asian_high=110.0, asian_low=100.0, asian_close=109.5)
        cfg = MeanReversionConfig(name="mr", timeframe="1h", min_range_pct=0.001, extreme_proximity_pct=0.20)
        strat = MeanReversionStrategy(cfg)
        trades = strat.simulate(df)
        assert len(trades) == 1
        assert trades["side"].iloc[0] == "SHORT"

    def test_long_entry_when_close_near_low(self) -> None:
        df = _make_day_ohlcv("2024-01-01", asian_high=110.0, asian_low=100.0, asian_close=100.5)
        cfg = MeanReversionConfig(name="mr", timeframe="1h", min_range_pct=0.001, extreme_proximity_pct=0.20)
        strat = MeanReversionStrategy(cfg)
        trades = strat.simulate(df)
        assert len(trades) == 1
        assert trades["side"].iloc[0] == "LONG"

    def test_no_entry_when_close_in_middle(self) -> None:
        df = _make_day_ohlcv("2024-01-01", asian_high=110.0, asian_low=100.0, asian_close=105.0)
        cfg = MeanReversionConfig(name="mr", timeframe="1h", min_range_pct=0.001, extreme_proximity_pct=0.20)
        strat = MeanReversionStrategy(cfg)
        trades = strat.simulate(df)
        assert len(trades) == 0

    def test_no_entry_when_range_below_filter(self) -> None:
        """Range too small relative to open → filter skips."""
        df = _make_day_ohlcv(
            "2024-01-01",
            asian_high=100.1,
            asian_low=100.0,
            asian_close=100.1,
            asian_open=100.05,
        )
        cfg = MeanReversionConfig(name="mr", timeframe="1h", min_range_pct=0.01)  # 1% min range
        strat = MeanReversionStrategy(cfg)
        trades = strat.simulate(df)
        assert len(trades) == 0


class TestExitMechanics:
    def test_horror_cost_applied_to_round_trip(self) -> None:
        df = _make_day_ohlcv("2024-01-01", asian_high=110.0, asian_low=100.0, asian_close=109.5)
        cfg = MeanReversionConfig(name="mr", timeframe="1h", min_range_pct=0.001, extreme_proximity_pct=0.20)
        strat = MeanReversionStrategy(cfg)
        trades = strat.simulate(df, cost_model=get_cost_model(CostMode.HORROR))
        assert len(trades) == 1
        # HORROR round-trip cost = 2*slip + 2*taker = 2*0.0020 + 2*0.0012 = 0.0064
        assert trades["cost_pct"].iloc[0] == pytest.approx(0.0064, abs=1e-6)
        assert trades["net_pct"].iloc[0] == pytest.approx(
            trades["gross_pct"].iloc[0] - 0.0064, abs=1e-9
        )

    def test_time_stop_fires_when_no_tp_or_sl(self) -> None:
        """Flat post-Asian bars → time stop must trigger."""
        df = _make_day_ohlcv("2024-01-01", asian_high=110.0, asian_low=100.0, asian_close=109.5)
        cfg = MeanReversionConfig(
            name="mr", timeframe="1h", min_range_pct=0.001, extreme_proximity_pct=0.20, time_stop_hours=4
        )
        strat = MeanReversionStrategy(cfg)
        trades = strat.simulate(df)
        assert len(trades) == 1
        assert trades["exit_reason"].iloc[0] == "TIME_STOP"
