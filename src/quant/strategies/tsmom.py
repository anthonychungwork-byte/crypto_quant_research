"""Time-Series Momentum (TSMOM) strategy.

Per hypothesis v3 ([../../notebooks/01c_hypothesis_v3_tsmom.ipynb]):

  At each weekly rebalance (Monday 00:00 UTC), compute each coin's trailing
  N-week return.  If past return > +threshold, position = LONG. If < -threshold,
  position = SHORT. Otherwise FLAT. Hold one week and re-evaluate.

This strategy treats each asset independently (time-series), unlike cross-sectional
momentum which ranks across the universe.

Reference: Han, Kang, Ryu (2023); Moskowitz, Ooi, Pedersen (2012).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from quant.analytics.momentum import trailing_return, trailing_volatility
from quant.backtest.costs import CostMode, CostModel, get_cost_model
from quant.strategies.base import Signal, Strategy, StrategyConfig

HOURS_PER_WEEK = 168


@dataclass(frozen=True)
class TSMOMConfig(StrategyConfig):
    """Parameter schema for TSMOM."""

    lookback_weeks: int = 4
    signal_threshold: float = 0.02
    vol_target: bool = False
    vol_lookback_weeks: int = 4
    rebalance_dayofweek: int = 0  # Monday
    rebalance_hour_utc: int = 0


class TSMOMStrategy(Strategy):
    """Time-Series Momentum on a single asset.

    For multi-asset backtests, instantiate per coin and aggregate trades.
    """

    config: TSMOMConfig

    def __init__(self, config: TSMOMConfig) -> None:
        super().__init__(config)
        self.config = config

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def generate_signals(self, ohlcv: pd.DataFrame) -> pd.Series:
        """Per-bar Signal. Non-FLAT only at rebalance bars."""
        cfg = self.config
        if not isinstance(ohlcv.index, pd.DatetimeIndex):
            raise TypeError("Expected DatetimeIndex")

        lookback_bars = cfg.lookback_weeks * HOURS_PER_WEEK
        ret = trailing_return(ohlcv["close"], lookback_bars)

        signals = pd.Series(
            Signal.FLAT.value, index=ohlcv.index, dtype=np.int64, name="signal"
        )

        # Only emit signals at rebalance times (e.g., Monday 00:00 UTC)
        is_rebalance = (
            (ohlcv.index.dayofweek == cfg.rebalance_dayofweek)
            & (ohlcv.index.hour == cfg.rebalance_hour_utc)
        )

        long_mask = is_rebalance & (ret > cfg.signal_threshold)
        short_mask = is_rebalance & (ret < -cfg.signal_threshold)

        signals[long_mask] = Signal.LONG.value
        signals[short_mask] = Signal.SHORT.value
        return signals

    def simulate(
        self,
        ohlcv: pd.DataFrame,
        cost_model: CostModel | None = None,
    ) -> pd.DataFrame:
        """Single-asset TSMOM backtest. Returns trades DataFrame.

        Each trade represents holding a position from one rebalance to the next.
        If the signal is unchanged between consecutive rebalances, the position
        is held (no new trade, no extra cost).
        """
        cfg = self.config
        cost = cost_model if cost_model is not None else get_cost_model(CostMode.HORROR)
        if not isinstance(ohlcv.index, pd.DatetimeIndex):
            raise TypeError("Expected DatetimeIndex")

        lookback_bars = cfg.lookback_weeks * HOURS_PER_WEEK
        ret = trailing_return(ohlcv["close"], lookback_bars)

        # Optional volatility scaling
        if cfg.vol_target:
            simple_returns = ohlcv["close"].pct_change()
            vol = trailing_volatility(simple_returns, cfg.vol_lookback_weeks * HOURS_PER_WEEK)
            # Scale = (target / realized) where target = mean vol (median for stability)
            target = vol.median()
            scale = (target / vol).clip(upper=2.0)  # cap leverage at 2x
        else:
            scale = pd.Series(1.0, index=ohlcv.index)

        # Find rebalance times
        rebalance_mask = (
            (ohlcv.index.dayofweek == cfg.rebalance_dayofweek)
            & (ohlcv.index.hour == cfg.rebalance_hour_utc)
        )
        rebalance_bars = ohlcv[rebalance_mask].copy()
        if rebalance_bars.empty:
            return _empty_trades()

        # Build per-rebalance signal
        position_list: list[int] = []
        for ts in rebalance_bars.index:
            r = float(ret.loc[ts]) if ts in ret.index else float("nan")
            if np.isnan(r):
                position_list.append(0)
                continue
            if r > cfg.signal_threshold:
                position_list.append(1)
            elif r < -cfg.signal_threshold:
                position_list.append(-1)
            else:
                position_list.append(0)
        positions = np.array(position_list, dtype=np.int64)
        rebalance_times = rebalance_bars.index

        # Generate trades when position changes
        trades: list[dict[str, object]] = []
        prev_pos = 0
        prev_entry_time: pd.Timestamp | None = None
        prev_entry_price: float = 0.0
        prev_scale: float = 1.0

        for i in range(len(positions)):
            new_pos = int(positions[i])
            now_time = rebalance_times[i]
            now_price = float(rebalance_bars["open"].iloc[i])
            now_scale = float(scale.loc[now_time]) if now_time in scale.index else 1.0
            if np.isnan(now_scale):
                now_scale = 1.0

            if new_pos != prev_pos:
                # Close previous (if any)
                if prev_pos != 0 and prev_entry_time is not None:
                    exit_price = now_price
                    gross = (
                        (exit_price - prev_entry_price) / prev_entry_price
                        if prev_pos == 1
                        else (prev_entry_price - exit_price) / prev_entry_price
                    ) * prev_scale
                    cost_pct = cost.round_trip_cost(is_taker_entry=True, is_taker_exit=True)
                    net = gross - cost_pct
                    trades.append(
                        {
                            "entry_time": prev_entry_time,
                            "exit_time": now_time,
                            "side": "LONG" if prev_pos == 1 else "SHORT",
                            "entry_price": prev_entry_price,
                            "exit_price": exit_price,
                            "gross_pct": gross,
                            "cost_pct": cost_pct,
                            "net_pct": net,
                            "exit_reason": "REBALANCE",
                            "bars_held": int((now_time - prev_entry_time).total_seconds() / 3600),
                        }
                    )
                # Open new
                if new_pos != 0:
                    prev_entry_time = now_time
                    prev_entry_price = now_price
                    prev_scale = now_scale
                else:
                    prev_entry_time = None
                    prev_entry_price = 0.0
                    prev_scale = 1.0
                prev_pos = new_pos

        # Close any final open position at the last rebalance
        if prev_pos != 0 and prev_entry_time is not None:
            last_time = rebalance_times[-1]
            last_price = float(rebalance_bars["open"].iloc[-1])
            if last_time != prev_entry_time:
                gross = (
                    (last_price - prev_entry_price) / prev_entry_price
                    if prev_pos == 1
                    else (prev_entry_price - last_price) / prev_entry_price
                ) * prev_scale
                cost_pct = cost.round_trip_cost(is_taker_entry=True, is_taker_exit=True)
                net = gross - cost_pct
                trades.append(
                    {
                        "entry_time": prev_entry_time,
                        "exit_time": last_time,
                        "side": "LONG" if prev_pos == 1 else "SHORT",
                        "entry_price": prev_entry_price,
                        "exit_price": last_price,
                        "gross_pct": gross,
                        "cost_pct": cost_pct,
                        "net_pct": net,
                        "exit_reason": "EOD",
                        "bars_held": int((last_time - prev_entry_time).total_seconds() / 3600),
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
