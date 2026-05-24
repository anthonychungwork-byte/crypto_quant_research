"""BTC Overnight + N-day MAX strategy (v5).

Per hypothesis v5 ([../../notebooks/01e_hypothesis_v5_overnight_max.ipynb]):

  On Fri/Mon/Tue at session_close hour UTC: check if BTC at N-day MAX (within
  breakout_proximity_pct of it). If yes, enter LONG at that bar's close and
  hold until next-day session_open hour UTC, then exit at the close of that
  bar.

  Sessions:
    Fri 21:00 UTC → Mon 14:00 UTC (weekend hold)
    Mon 21:00 UTC → Tue 14:00 UTC (overnight)
    Tue 21:00 UTC → Wed 14:00 UTC (overnight)

This is a session-pattern + momentum-filter strategy. No stop loss / TP —
pure time-based exit.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from quant.backtest.costs import CostMode, CostModel, get_cost_model
from quant.strategies.base import Signal, Strategy, StrategyConfig


@dataclass(frozen=True)
class OvernightMAXConfig(StrategyConfig):
    """Parameters for v5 Overnight + N-day MAX."""

    lookback_days: int = 10
    breakout_proximity_pct: float = 0.005
    entry_hour_utc: int = 21
    exit_hour_utc: int = 14
    # Mon=0 .. Sun=6 ; default = Fri / Mon / Tue (per QuantPedia)
    entry_dayofweek: tuple[int, ...] = (4, 0, 1)


# Map entry day → exit day (next NY-morning weekday)
_NEXT_DAY = {
    4: 0,  # Fri → next Mon
    0: 1,  # Mon → next Tue
    1: 2,  # Tue → next Wed
    2: 3,  # Wed → Thu (optional)
    3: 4,  # Thu → Fri (optional)
}


class OvernightMAXStrategy(Strategy):
    """BTC Overnight + N-day MAX session strategy."""

    config: OvernightMAXConfig

    def __init__(self, config: OvernightMAXConfig) -> None:
        super().__init__(config)
        self.config = config

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def generate_signals(self, ohlcv: pd.DataFrame) -> pd.Series:
        """Per-bar signal. LONG only at qualifying entry bars."""
        cfg = self.config
        if not isinstance(ohlcv.index, pd.DatetimeIndex):
            raise TypeError("Expected DatetimeIndex")

        lookback_bars = cfg.lookback_days * 24
        rolling_max = ohlcv["close"].rolling(window=lookback_bars, min_periods=lookback_bars).max()

        signals = pd.Series(Signal.FLAT.value, index=ohlcv.index, dtype=np.int64, name="signal")

        idx = ohlcv.index
        if not isinstance(idx, pd.DatetimeIndex):
            raise TypeError("Expected DatetimeIndex")
        is_entry_time = (
            idx.dayofweek.isin(cfg.entry_dayofweek)
            & (idx.hour == cfg.entry_hour_utc)
        )
        # At entry, signal long if close >= max * (1 - proximity)
        threshold = rolling_max * (1.0 - cfg.breakout_proximity_pct)
        long_mask = is_entry_time & (ohlcv["close"] >= threshold) & rolling_max.notna()
        signals[long_mask] = Signal.LONG.value
        return signals

    def simulate(
        self,
        ohlcv: pd.DataFrame,
        cost_model: CostModel | None = None,
    ) -> pd.DataFrame:
        """Backtest the session strategy. Returns trades DataFrame."""
        cfg = self.config
        cost = cost_model if cost_model is not None else get_cost_model(CostMode.HORROR)
        if not isinstance(ohlcv.index, pd.DatetimeIndex):
            raise TypeError("Expected DatetimeIndex")

        signals = self.generate_signals(ohlcv)
        entry_times = signals[signals == Signal.LONG.value].index

        trades: list[dict[str, object]] = []
        for entry_ts in entry_times:
            entry_dow = entry_ts.dayofweek
            if entry_dow not in _NEXT_DAY:
                continue

            # Find exit bar: next occurrence of (next_dow, exit_hour_utc)
            target_dow = _NEXT_DAY[entry_dow]
            # Search forward up to 5 days for the matching bar
            search_end = entry_ts + pd.Timedelta(days=5)
            forward = ohlcv.loc[entry_ts:search_end]
            forward_idx = forward.index
            if not isinstance(forward_idx, pd.DatetimeIndex):
                continue
            exit_mask = (forward_idx.dayofweek == target_dow) & (forward_idx.hour == cfg.exit_hour_utc)
            exit_candidates = forward[exit_mask]
            if exit_candidates.empty:
                continue
            exit_ts = exit_candidates.index[0]

            entry_price = float(ohlcv.loc[entry_ts, "close"])
            exit_price = float(ohlcv.loc[exit_ts, "close"])

            gross_pct = (exit_price - entry_price) / entry_price
            cost_pct = cost.round_trip_cost(is_taker_entry=True, is_taker_exit=True)
            net_pct = gross_pct - cost_pct

            trades.append(
                {
                    "entry_time": entry_ts,
                    "exit_time": exit_ts,
                    "side": "LONG",
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "gross_pct": gross_pct,
                    "cost_pct": cost_pct,
                    "net_pct": net_pct,
                    "exit_reason": "SESSION_OPEN",
                    "bars_held": int((exit_ts - entry_ts).total_seconds() / 3600),
                }
            )

        if not trades:
            return _empty_trades()
        return pd.DataFrame(trades)


def _empty_trades() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "entry_time", "exit_time", "side", "entry_price", "exit_price",
            "gross_pct", "cost_pct", "net_pct", "exit_reason", "bars_held",
        ]
    )
