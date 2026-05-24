"""TSMOM with cross-asset consensus filter (v4).

At each weekly rebalance:
  1. Compute per-coin TSMOM signal (LONG / SHORT / FLAT) as in v3.
  2. Count consensus: n_long = coins with LONG, n_short = coins with SHORT.
  3. If max(n_long, n_short) >= consensus_threshold → take all per-coin signals.
  4. Otherwise → override all to FLAT (sit out chop regime).

The filter is applied *across* coins at each rebalance time — this is
fundamentally different from per-coin signal logic.

Reference: hypothesis v4
[notebooks/01d_hypothesis_v4_tsmom_consensus.ipynb]
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from quant.analytics.momentum import trailing_return
from quant.backtest.costs import CostMode, CostModel, get_cost_model
from quant.strategies.tsmom import HOURS_PER_WEEK, TSMOMConfig


@dataclass(frozen=True)
class TSMOMConsensusConfig(TSMOMConfig):
    """Extends TSMOM with cross-asset consensus filter."""

    consensus_threshold: int = 4  # min coins agreeing on direction to trade


def simulate_consensus_portfolio(
    ohlcv_dict: dict[str, pd.DataFrame],
    config: TSMOMConsensusConfig,
    cost_model: CostModel | None = None,
) -> pd.DataFrame:
    """Simulate the TSMOM + Consensus strategy across the full universe.

    Unlike single-asset Strategy.simulate, this MUST take the multi-asset
    universe as input because the consensus filter is cross-asset.

    Returns aggregated trades DataFrame with 'symbol' column.
    """
    cost = cost_model if cost_model is not None else get_cost_model(CostMode.HORROR)
    if not ohlcv_dict:
        return _empty_trades()

    # Sanity: align all coins to the same time index
    symbols = sorted(ohlcv_dict.keys())
    sample = ohlcv_dict[symbols[0]]
    if not isinstance(sample.index, pd.DatetimeIndex):
        raise TypeError("Expected DatetimeIndex on all coins")

    lookback_bars = config.lookback_weeks * HOURS_PER_WEEK

    # Compute trailing returns per coin
    returns_per_coin: dict[str, pd.Series] = {}
    for sym in symbols:
        returns_per_coin[sym] = trailing_return(ohlcv_dict[sym]["close"], lookback_bars)

    # Find common rebalance times (Monday 00:00 UTC) — intersect across coins
    if not isinstance(sample.index, pd.DatetimeIndex):
        raise TypeError("Expected DatetimeIndex")
    common_idx: pd.DatetimeIndex = sample.index
    for sym in symbols[1:]:
        other_idx = ohlcv_dict[sym].index
        if isinstance(other_idx, pd.DatetimeIndex):
            common_idx = common_idx.intersection(other_idx)

    if len(common_idx) == 0:
        return _empty_trades()

    rebalance_mask = (
        (common_idx.dayofweek == config.rebalance_dayofweek)
        & (common_idx.hour == config.rebalance_hour_utc)
    )
    rebalance_times = common_idx[rebalance_mask]

    # Track per-coin position state
    positions: dict[str, int] = dict.fromkeys(symbols, 0)
    entry_info: dict[str, tuple[pd.Timestamp, float]] = {}
    all_trades: list[dict[str, object]] = []

    for ts in rebalance_times:
        # Compute raw per-coin signals
        raw_signals: dict[str, int] = {}
        for sym in symbols:
            r = returns_per_coin[sym].get(ts, float("nan"))
            if pd.isna(r):
                raw_signals[sym] = 0
            elif r > config.signal_threshold:
                raw_signals[sym] = 1
            elif r < -config.signal_threshold:
                raw_signals[sym] = -1
            else:
                raw_signals[sym] = 0

        # Consensus check
        n_long = sum(1 for v in raw_signals.values() if v == 1)
        n_short = sum(1 for v in raw_signals.values() if v == -1)
        consensus = max(n_long, n_short)

        if consensus >= config.consensus_threshold:
            target_signals = raw_signals
        else:
            target_signals = dict.fromkeys(symbols, 0)

        # Generate trades for any position changes
        for sym in symbols:
            new_pos = target_signals[sym]
            old_pos = positions[sym]
            if new_pos == old_pos:
                continue
            # Close existing
            if old_pos != 0 and sym in entry_info:
                old_entry_time, old_entry_price = entry_info[sym]
                exit_price = float(ohlcv_dict[sym].loc[ts, "open"])  # type: ignore[arg-type]
                gross = (
                    (exit_price - old_entry_price) / old_entry_price
                    if old_pos == 1
                    else (old_entry_price - exit_price) / old_entry_price
                )
                cost_pct = cost.round_trip_cost(is_taker_entry=True, is_taker_exit=True)
                net = gross - cost_pct
                all_trades.append(
                    {
                        "entry_time": old_entry_time,
                        "exit_time": ts,
                        "side": "LONG" if old_pos == 1 else "SHORT",
                        "entry_price": old_entry_price,
                        "exit_price": exit_price,
                        "gross_pct": gross,
                        "cost_pct": cost_pct,
                        "net_pct": net,
                        "exit_reason": "REBALANCE_OR_CONSENSUS",
                        "bars_held": int((ts - old_entry_time).total_seconds() / 3600),
                        "symbol": sym,
                    }
                )
                del entry_info[sym]
            # Open new
            if new_pos != 0:
                entry_price = float(ohlcv_dict[sym].loc[ts, "open"])  # type: ignore[arg-type]
                entry_info[sym] = (ts, entry_price)
            positions[sym] = new_pos

    if not all_trades:
        return _empty_trades()
    return pd.DataFrame(all_trades)


def _empty_trades() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "entry_time", "exit_time", "side", "entry_price", "exit_price",
            "gross_pct", "cost_pct", "net_pct", "exit_reason", "bars_held", "symbol",
        ]
    )
