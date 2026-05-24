"""Tests for src/quant/strategies/stretched_vp.py."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant.backtest.costs import CostMode, get_cost_model
from quant.strategies.base import Signal
from quant.strategies.stretched_vp import StretchedVPConfig, StretchedVPStrategy


def _make_day(
    date: str,
    body_low: float,
    body_high: float,
    close: float,
    body_volume: float = 1000.0,
    tail_volume: float = 1.0,
) -> pd.DataFrame:
    """Build a 24-bar UTC day with most volume in body_low..body_high, close at given price.

    The close is the close of the LAST bar (UTC 23). To make close 'stretched',
    we set the last few bars to trade near the close price with tiny volume so
    that the value area stays at the body range.
    """
    timestamps = pd.date_range(date, periods=24, freq="1h", tz="UTC")

    open_ = np.full(24, (body_low + body_high) / 2, dtype=np.float64)
    close_arr = np.full(24, (body_low + body_high) / 2, dtype=np.float64)
    high = np.full(24, body_high, dtype=np.float64)
    low = np.full(24, body_low, dtype=np.float64)
    volume = np.full(24, body_volume / 20, dtype=np.float64)

    # Last 4 bars push the price toward `close` and have low volume
    for i in range(20, 24):
        if close > body_high:
            high[i] = max(close, body_high) * 1.001
            low[i] = body_high
            open_[i] = body_high if i == 20 else close
            close_arr[i] = close
        elif close < body_low:
            high[i] = body_low
            low[i] = min(close, body_low) * 0.999
            open_[i] = body_low if i == 20 else close
            close_arr[i] = close
        else:
            close_arr[i] = close
        volume[i] = tail_volume

    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close_arr, "volume": volume},
        index=timestamps,
    )


def _next_day_drift_toward_poc(date_next: str, start_price: float, target_price: float) -> pd.DataFrame:
    """Build next-day bars that drift from start_price toward target_price."""
    timestamps = pd.date_range(date_next, periods=24, freq="1h", tz="UTC")
    prices = np.linspace(start_price, target_price, 25)[:24]
    return pd.DataFrame(
        {
            "open": prices,
            "high": prices * 1.0005,
            "low": prices * 0.9995,
            "close": prices,
            "volume": np.full(24, 100.0),
        },
        index=timestamps,
    )


class TestStretchedVPEntry:
    def test_short_when_close_stretched_above_vah(self) -> None:
        """Day body 100-110, close 115 (above VAH by ~5%) → next day SHORT."""
        day1 = _make_day("2024-01-01", body_low=100.0, body_high=110.0, close=115.0)
        day2 = _next_day_drift_toward_poc("2024-01-02", start_price=114.0, target_price=105.0)
        ohlcv = pd.concat([day1, day2])

        cfg = StretchedVPConfig(
            name="svp", timeframe="1h",
            min_range_pct=0.01,
            stretched_threshold_pct=0.01,
            time_stop_hours=24,
        )
        trades = StretchedVPStrategy(cfg).simulate(ohlcv)
        assert len(trades) == 1
        assert trades["side"].iloc[0] == "SHORT"

    def test_long_when_close_stretched_below_val(self) -> None:
        """Day body 100-110, close 95 (below VAL) → next day LONG."""
        day1 = _make_day("2024-01-01", body_low=100.0, body_high=110.0, close=95.0)
        day2 = _next_day_drift_toward_poc("2024-01-02", start_price=96.0, target_price=105.0)
        ohlcv = pd.concat([day1, day2])

        cfg = StretchedVPConfig(name="svp", timeframe="1h", stretched_threshold_pct=0.01)
        trades = StretchedVPStrategy(cfg).simulate(ohlcv)
        assert len(trades) == 1
        assert trades["side"].iloc[0] == "LONG"

    def test_no_entry_when_close_inside_va(self) -> None:
        """Body 100-110, close 105 → inside VA → no trade."""
        day1 = _make_day("2024-01-01", body_low=100.0, body_high=110.0, close=105.0)
        day2 = _next_day_drift_toward_poc("2024-01-02", start_price=105.0, target_price=105.0)
        ohlcv = pd.concat([day1, day2])

        cfg = StretchedVPConfig(name="svp", timeframe="1h")
        trades = StretchedVPStrategy(cfg).simulate(ohlcv)
        assert len(trades) == 0

    def test_horror_cost_applied(self) -> None:
        day1 = _make_day("2024-01-01", body_low=100.0, body_high=110.0, close=115.0)
        day2 = _next_day_drift_toward_poc("2024-01-02", start_price=114.0, target_price=105.0)
        ohlcv = pd.concat([day1, day2])

        cfg = StretchedVPConfig(name="svp", timeframe="1h", stretched_threshold_pct=0.01)
        trades = StretchedVPStrategy(cfg).simulate(ohlcv, cost_model=get_cost_model(CostMode.HORROR))
        assert trades["cost_pct"].iloc[0] == pytest.approx(0.0064)


class TestStretchedVPSignals:
    def test_signal_only_on_entry_bar(self) -> None:
        """Signal is FLAT everywhere except the entry bar."""
        day1 = _make_day("2024-01-01", body_low=100.0, body_high=110.0, close=115.0)
        day2 = _next_day_drift_toward_poc("2024-01-02", start_price=114.0, target_price=105.0)
        ohlcv = pd.concat([day1, day2])

        cfg = StretchedVPConfig(name="svp", timeframe="1h", stretched_threshold_pct=0.01)
        sigs = StretchedVPStrategy(cfg).generate_signals(ohlcv)
        non_flat = sigs[sigs != Signal.FLAT.value]
        assert len(non_flat) == 1
        # Entry bar must be in day 2 (next day after qualifying day 1)
        assert non_flat.index[0].normalize() == pd.Timestamp("2024-01-02", tz="UTC")
