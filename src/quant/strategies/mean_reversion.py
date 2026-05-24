"""Asian Session Extreme Fade — mean reversion strategy.

Per [notebooks/01_hypothesis.ipynb](../../../notebooks/01_hypothesis.ipynb):

  At UTC 13:00 close, if the close is near the Asian range high → SHORT.
  If near the Asian range low → LONG. Entry at UTC 13:00 open
  (next bar after the session-defining bar that closed at 13:00).
  Exit: TP at Asian range midpoint zone, SL at range extreme + buffer,
  or time stop at UTC 13 + time_stop_hours.

Two public methods:
  - generate_signals(ohlcv) — per-bar Series[Signal], for no-lookahead test
  - simulate(ohlcv, cost_model) — full backtest including exits
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from quant.backtest.costs import CostMode, CostModel, get_cost_model
from quant.strategies.base import Signal, Strategy, StrategyConfig


@dataclass(frozen=True)
class MeanReversionConfig(StrategyConfig):
    """Locked Stage 0 parameter space; search ranges in 01_hypothesis.ipynb."""

    min_range_pct: float = 0.010
    extreme_proximity_pct: float = 0.25
    stop_buffer_pct: float = 0.005
    tp_fraction: float = 0.5
    time_stop_hours: int = 6
    session_start_hour: int = 0
    session_end_hour_inclusive: int = 12  # bar with open_time=12 covers 12:00-13:00
    entry_hour: int = 13  # bar with open_time=13 covers 13:00-14:00


class MeanReversionStrategy(Strategy):
    """Asian Session Extreme Fade."""

    config: MeanReversionConfig

    def __init__(self, config: MeanReversionConfig) -> None:
        super().__init__(config)
        self.config = config

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def generate_signals(self, ohlcv: pd.DataFrame) -> pd.Series:
        """Per-bar entry signal. FLAT everywhere except qualifying entry bars."""
        cfg = self.config
        df = self._prep(ohlcv)

        signals = pd.Series(
            Signal.FLAT.value, index=ohlcv.index, dtype=np.int64, name="signal"
        )

        for _, day in df.groupby("date", sort=True):
            entry = self._evaluate_day(day, cfg)
            if entry is None:
                continue
            entry_idx, side = entry
            signals.loc[entry_idx] = int(side.value)  # type: ignore[call-overload]
        return signals

    def simulate(
        self,
        ohlcv: pd.DataFrame,
        cost_model: CostModel | None = None,
    ) -> pd.DataFrame:
        """Full backtest. Returns trades DataFrame."""
        cfg = self.config
        cost = cost_model if cost_model is not None else get_cost_model(CostMode.HORROR)
        df = self._prep(ohlcv)

        trades: list[dict[str, object]] = []
        for _, day in df.groupby("date", sort=True):
            entry = self._evaluate_day(day, cfg)
            if entry is None:
                continue
            entry_idx, side = entry
            trade = self._simulate_trade(day, entry_idx, side, cfg, cost)
            if trade is not None:
                trades.append(trade)

        if not trades:
            return pd.DataFrame(
                columns=[
                    "entry_time",
                    "exit_time",
                    "side",
                    "entry_price",
                    "exit_price",
                    "gross_pct",
                    "cost_pct",
                    "net_pct",
                    "exit_reason",
                    "bars_held",
                ]
            )
        return pd.DataFrame(trades)

    # ─────────────────────────────────────────────────────────────────────────
    # Internals
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _prep(ohlcv: pd.DataFrame) -> pd.DataFrame:
        """Attach 'date' and 'hour' helper columns. Returns a copy."""
        if not isinstance(ohlcv.index, pd.DatetimeIndex):
            raise TypeError(f"Expected DatetimeIndex, got {type(ohlcv.index).__name__}")
        df = ohlcv.copy()
        df["hour"] = ohlcv.index.hour
        df["date"] = ohlcv.index.normalize()
        return df

    @staticmethod
    def _evaluate_day(
        day: pd.DataFrame,
        cfg: MeanReversionConfig,
    ) -> tuple[pd.Timestamp, Signal] | None:
        """Decide whether to enter on this day, and on which side."""
        asian = day[
            (day["hour"] >= cfg.session_start_hour)
            & (day["hour"] <= cfg.session_end_hour_inclusive)
        ]
        # Need full Asian session present
        expected_asian_bars = cfg.session_end_hour_inclusive - cfg.session_start_hour + 1
        if len(asian) < expected_asian_bars:
            return None

        a_high = float(asian["high"].max())
        a_low = float(asian["low"].min())
        a_open_row = asian[asian["hour"] == cfg.session_start_hour]
        a_close_row = asian[asian["hour"] == cfg.session_end_hour_inclusive]
        if a_open_row.empty or a_close_row.empty:
            return None
        a_open = float(a_open_row["open"].iloc[0])
        a_close = float(a_close_row["close"].iloc[0])
        a_range = a_high - a_low

        if a_open <= 0 or a_range <= 0:
            return None
        if a_range / a_open < cfg.min_range_pct:
            return None

        dist_high = (a_high - a_close) / a_range
        dist_low = (a_close - a_low) / a_range
        near_high = dist_high <= cfg.extreme_proximity_pct
        near_low = dist_low <= cfg.extreme_proximity_pct

        # Mutually exclusive: skip ambiguous (both) and trivial (neither)
        if near_high == near_low:
            return None

        entry_row = day[day["hour"] == cfg.entry_hour]
        if entry_row.empty:
            return None
        entry_idx = entry_row.index[0]
        side = Signal.SHORT if near_high else Signal.LONG
        return entry_idx, side

    @staticmethod
    def _simulate_trade(
        day: pd.DataFrame,
        entry_idx: pd.Timestamp,
        side: Signal,
        cfg: MeanReversionConfig,
        cost: CostModel,
    ) -> dict[str, object] | None:
        """Simulate a single trade from entry to exit."""
        # Re-compute Asian levels for stop/TP
        asian = day[
            (day["hour"] >= cfg.session_start_hour)
            & (day["hour"] <= cfg.session_end_hour_inclusive)
        ]
        a_high = float(asian["high"].max())
        a_low = float(asian["low"].min())
        a_range = a_high - a_low

        post = day[day["hour"] >= cfg.entry_hour].sort_index()
        if post.empty:
            return None

        entry_bar = post.iloc[0]
        entry_price = float(entry_bar["open"])

        if side == Signal.SHORT:
            tp = entry_price - cfg.tp_fraction * a_range
            sl = a_high * (1 + cfg.stop_buffer_pct)
        else:
            tp = entry_price + cfg.tp_fraction * a_range
            sl = a_low * (1 - cfg.stop_buffer_pct)

        # Look forward up to time_stop_hours bars (inclusive of entry bar)
        n_lookahead = cfg.time_stop_hours
        lookahead_bars = post.iloc[: n_lookahead + 1]

        exit_price: float | None = None
        exit_reason = ""
        exit_time: pd.Timestamp | None = None

        for i in range(len(lookahead_bars)):
            bar = lookahead_bars.iloc[i]
            bar_high = float(bar["high"])
            bar_low = float(bar["low"])
            bar_time = lookahead_bars.index[i]

            tp_hit = (bar_low <= tp) if side == Signal.SHORT else (bar_high >= tp)
            sl_hit = (bar_high >= sl) if side == Signal.SHORT else (bar_low <= sl)

            if tp_hit and sl_hit:
                # Both touched in same bar: conservatively assume SL (worst case)
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
            # Time stop
            ts_bar = lookahead_bars.iloc[-1]
            exit_price = float(ts_bar["close"])
            exit_reason = "TIME_STOP"
            exit_time = lookahead_bars.index[-1]

        # PnL fraction
        if side == Signal.SHORT:
            gross_pct = (entry_price - exit_price) / entry_price
        else:
            gross_pct = (exit_price - entry_price) / entry_price

        cost_pct = cost.round_trip_cost(is_taker_entry=True, is_taker_exit=True)
        net_pct = gross_pct - cost_pct

        return {
            "entry_time": entry_idx,
            "exit_time": exit_time,
            "side": side.name,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "gross_pct": gross_pct,
            "cost_pct": cost_pct,
            "net_pct": net_pct,
            "exit_reason": exit_reason,
            "bars_held": int((exit_time - entry_idx).total_seconds() / 3600) if exit_time else 0,
        }
