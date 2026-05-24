"""Tabular summary generators for results/tables/."""

from __future__ import annotations

import pandas as pd


def metrics_table(*args: object, **kwargs: object) -> pd.DataFrame:
    """Summary metrics table (PF / Sharpe / MaxDD / DSR). Stub."""
    raise NotImplementedError


def trade_log_table(*args: object, **kwargs: object) -> pd.DataFrame:
    """Trade-by-trade log with entry/exit/PnL. Stub."""
    raise NotImplementedError
