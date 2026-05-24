"""Backtest engine: applies a strategy's signals to OHLCV and produces trades + PnL.

Implementation deferred until Stage 1+. The engine will:
  - Consume a Strategy and OHLCV
  - Produce a TradeLog (entry/exit timestamps, side, prices, PnL)
  - Apply the CostModel (HORROR by default) to net PnL
  - Be tested against tests/test_no_lookahead.py to confirm temporal integrity
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class BacktestResult:
    """Container for backtest output."""

    trades: pd.DataFrame
    equity_curve: pd.Series
    metrics: dict[str, float]


def run_backtest(*args: object, **kwargs: object) -> BacktestResult:
    """Run a backtest. Signature TBD post-Stage 0."""
    raise NotImplementedError("Implement after Stage 0.")
