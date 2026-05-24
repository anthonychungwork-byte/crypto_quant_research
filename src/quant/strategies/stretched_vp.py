"""Stretched Volume Profile strategy.

Per hypothesis v2 ([../../notebooks/01b_hypothesis_v2_stretched_vp.ipynb]):

  At UTC 23:00 of each day, compute the day's volume profile.
  - If the day's close is stretched > stretched_threshold_pct ABOVE VAH:
        next day's first bar → enter SHORT at the open.
        TP at POC, SL at day-high + buffer, time stop after N hours.
  - If close is stretched > stretched_threshold_pct BELOW VAL:
        symmetric LONG.
  - Otherwise: no trade.

Thesis: stretched closes reflect short-term liquidity dislocation; the
next-day session brings fresh liquidity that re-anchors price toward the
value area.

Two public methods (matching the Strategy interface):
  - generate_signals(ohlcv) — per-bar Signal, for no-lookahead test
  - simulate(ohlcv, cost_model) — full backtest with TP/SL/time stop
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import numpy as np
import pandas as pd

from quant.analytics.volume_profile import compute_volume_profile
from quant.backtest.costs import CostMode, CostModel, get_cost_model
from quant.strategies.base import Signal, Strategy, StrategyConfig


@dataclass(frozen=True)
class StretchedVPConfig(StrategyConfig):
    """Parameter schema for Stretched VP. Locked grid in Stage 0 hypothesis."""

    min_range_pct: float = 0.010
    stretched_threshold_pct: float = 0.010
    stop_buffer_pct: float = 0.010
    time_stop_hours: int = 24
    va_pct: float = 0.70
    n_buckets: int = 50


class StretchedVPStrategy(Strategy):
    """Stretched Volume Profile fade strategy."""

    config: StretchedVPConfig

    def __init__(self, config: StretchedVPConfig) -> None:
        super().__init__(config)
        self.config = config

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def generate_signals(self, ohlcv: pd.DataFrame) -> pd.Series:
        """Per-bar entry signal. Non-FLAT only at the first bar of a qualifying day."""
        cfg = self.config
        if not isinstance(ohlcv.index, pd.DatetimeIndex):
            raise TypeError("Expected DatetimeIndex")
        df = ohlcv.copy()
        df["date"] = ohlcv.index.normalize()

        signals = pd.Series(Signal.FLAT.value, index=ohlcv.index, dtype=np.int64, name="signal")

        dates = sorted(df["date"].unique())
        for i, d in enumerate(dates[:-1]):
            next_date = dates[i + 1]
            day_bars = df[df["date"] == d]
            evaluation = self._evaluate_day(day_bars, cfg)
            if evaluation is None:
                continue
            side, _, _, _ = evaluation
            next_day_bars = df[df["date"] == next_date]
            if next_day_bars.empty:
                continue
            entry_idx = next_day_bars.index[0]
            signals.loc[entry_idx] = int(side.value)
        return signals

    def simulate(
        self,
        ohlcv: pd.DataFrame,
        cost_model: CostModel | None = None,
    ) -> pd.DataFrame:
        """Full backtest. Returns trades DataFrame."""
        cfg = self.config
        cost = cost_model if cost_model is not None else get_cost_model(CostMode.HORROR)
        if not isinstance(ohlcv.index, pd.DatetimeIndex):
            raise TypeError("Expected DatetimeIndex")
        df = ohlcv.copy()
        df["date"] = ohlcv.index.normalize()

        trades: list[dict[str, object]] = []
        dates = sorted(df["date"].unique())
        for i, d in enumerate(dates[:-1]):
            day_bars = df[df["date"] == d]
            evaluation = self._evaluate_day(day_bars, cfg)
            if evaluation is None:
                continue
            side, poc, day_high, day_low = evaluation

            next_date = dates[i + 1]
            next_day = df[df["date"] >= next_date].sort_index()
            if next_day.empty:
                continue
            entry_bar = next_day.iloc[0]
            entry_time = next_day.index[0]
            entry_price = float(entry_bar["open"])

            # TP / SL definition
            if side == Signal.SHORT:
                tp = poc
                sl = day_high * (1.0 + cfg.stop_buffer_pct)
            else:
                tp = poc
                sl = day_low * (1.0 - cfg.stop_buffer_pct)

            time_stop_cutoff = entry_time + timedelta(hours=cfg.time_stop_hours)
            lookahead = next_day[next_day.index <= time_stop_cutoff]

            exit_price: float | None = None
            exit_reason = ""
            exit_time: pd.Timestamp | None = None

            for j in range(len(lookahead)):
                bar = lookahead.iloc[j]
                bar_high = float(bar["high"])
                bar_low = float(bar["low"])
                bar_time = lookahead.index[j]

                tp_hit = (bar_low <= tp) if side == Signal.SHORT else (bar_high >= tp)
                sl_hit = (bar_high >= sl) if side == Signal.SHORT else (bar_low <= sl)

                if tp_hit and sl_hit:
                    # Same-bar ambiguous: conservative = SL first
                    exit_price = sl
                    exit_reason = "SL_AMBIG"
                    exit_time = bar_time
                    break
                if sl_hit:
                    exit_price = sl
                    exit_reason = "SL"
                    exit_time = bar_time
                    break
                if tp_hit:
                    exit_price = tp
                    exit_reason = "TP"
                    exit_time = bar_time
                    break

            if exit_price is None:
                ts_bar = lookahead.iloc[-1]
                exit_price = float(ts_bar["close"])
                exit_reason = "TIME_STOP"
                exit_time = lookahead.index[-1]

            gross_pct = (
                (entry_price - exit_price) / entry_price
                if side == Signal.SHORT
                else (exit_price - entry_price) / entry_price
            )
            cost_pct = cost.round_trip_cost(is_taker_entry=True, is_taker_exit=True)
            net_pct = gross_pct - cost_pct

            trades.append(
                {
                    "entry_time": entry_time,
                    "exit_time": exit_time,
                    "side": side.name,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "gross_pct": gross_pct,
                    "cost_pct": cost_pct,
                    "net_pct": net_pct,
                    "exit_reason": exit_reason,
                    "bars_held": int((exit_time - entry_time).total_seconds() / 3600) if exit_time else 0,
                }
            )

        if not trades:
            return pd.DataFrame(
                columns=[
                    "entry_time", "exit_time", "side", "entry_price", "exit_price",
                    "gross_pct", "cost_pct", "net_pct", "exit_reason", "bars_held",
                ]
            )
        return pd.DataFrame(trades)

    # ─────────────────────────────────────────────────────────────────────────
    # Internal
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _evaluate_day(
        day_bars: pd.DataFrame,
        cfg: StretchedVPConfig,
    ) -> tuple[Signal, float, float, float] | None:
        """Return (side, poc, day_high, day_low) if day qualifies; else None."""
        if len(day_bars) < 6:  # need reasonable intraday coverage
            return None

        day_high = float(day_bars["high"].max())
        day_low = float(day_bars["low"].min())
        day_open = float(day_bars["open"].iloc[0])
        if day_open <= 0:
            return None
        if (day_high - day_low) / day_open < cfg.min_range_pct:
            return None

        close = float(day_bars["close"].iloc[-1])
        try:
            vp = compute_volume_profile(day_bars, n_buckets=cfg.n_buckets, va_pct=cfg.va_pct)
        except ValueError:
            return None

        # Stretched above VAH → expect fade back down (SHORT)
        if vp.vah_price > 0 and close > vp.vah_price * (1.0 + cfg.stretched_threshold_pct):
            return Signal.SHORT, vp.poc_price, day_high, day_low
        # Stretched below VAL → expect fade back up (LONG)
        if vp.val_price > 0 and close < vp.val_price * (1.0 - cfg.stretched_threshold_pct):
            return Signal.LONG, vp.poc_price, day_high, day_low
        return None
