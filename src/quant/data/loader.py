"""Parquet data loading utilities."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_ohlcv_parquet(path: Path | str) -> pd.DataFrame:
    """Load OHLCV (open/high/low/close/volume) parquet file.

    Args:
        path: Path to parquet file.

    Returns:
        DataFrame with DatetimeIndex (UTC) and columns: open, high, low, close, volume.
    """
    raise NotImplementedError("Implement after Stage 0 hypothesis is locked.")


def load_symbol_set(symbols: list[str], data_dir: Path | str) -> dict[str, pd.DataFrame]:
    """Load OHLCV data for multiple symbols.

    Args:
        symbols: List of symbol names (e.g. ['BTCUSDT', 'ETHUSDT']).
        data_dir: Directory containing per-symbol parquet files.

    Returns:
        Dict mapping symbol → OHLCV DataFrame.
    """
    raise NotImplementedError("Implement after Stage 0 hypothesis is locked.")
