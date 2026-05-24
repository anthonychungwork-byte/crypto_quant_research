"""Binance USDT-margined futures OHLCV loader.

Fetches historical 1h klines via Binance's public REST API (no auth required)
and persists to parquet. Idempotent — re-running with an existing parquet
returns the cached data unless `force=True`.

Why Binance futures (not spot, not WEEX)?
  - Futures venue matches the live trading instrument class (USDT-perp).
  - Public + free + no auth → fully reproducible by anyone cloning the repo.
  - WEEX prices track Binance within ~0.05% via arbitrage; using Binance
    keeps the data source portable while preserving the relevant market
    microstructure.
"""

from __future__ import annotations

import time
from pathlib import Path

import httpx
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential
from tqdm import tqdm

BINANCE_FUTURES_KLINES_URL = "https://fapi.binance.com/fapi/v1/klines"
MAX_BARS_PER_REQUEST = 1500  # Binance futures cap

_INTERVAL_TO_MS: dict[str, int] = {
    "1m": 60_000,
    "5m": 5 * 60_000,
    "15m": 15 * 60_000,
    "30m": 30 * 60_000,
    "1h": 60 * 60_000,
    "2h": 2 * 60 * 60_000,
    "4h": 4 * 60 * 60_000,
    "1d": 24 * 60 * 60_000,
}

_KLINE_COLUMNS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "trades",
    "taker_buy_base",
    "taker_buy_quote",
    "ignore",
]


@retry(stop=stop_after_attempt(5), wait=wait_exponential(min=1, max=30))
def _fetch_batch(
    client: httpx.Client,
    symbol: str,
    interval: str,
    start_ms: int,
    end_ms: int,
) -> list[list[object]]:
    """Fetch a single batch of up to MAX_BARS_PER_REQUEST klines."""
    params: dict[str, str | int] = {
        "symbol": symbol,
        "interval": interval,
        "startTime": start_ms,
        "endTime": end_ms,
        "limit": MAX_BARS_PER_REQUEST,
    }
    response = client.get(BINANCE_FUTURES_KLINES_URL, params=params, timeout=30.0)
    response.raise_for_status()
    return response.json()  # type: ignore[no-any-return]


def fetch_binance_klines(
    symbol: str,
    interval: str,
    start: str,
    end: str,
) -> pd.DataFrame:
    """Fetch all klines between [start, end) from Binance USDT-margined futures.

    Args:
        symbol: e.g. "BTCUSDT".
        interval: One of "1m", "5m", "15m", "30m", "1h", "2h", "4h", "1d".
        start: Start datetime as ISO-8601 string, interpreted as UTC.
        end: End datetime as ISO-8601 string, interpreted as UTC.

    Returns:
        DataFrame with DatetimeIndex (UTC) and columns:
        open, high, low, close, volume, quote_volume, trades.
    """
    if interval not in _INTERVAL_TO_MS:
        raise ValueError(f"Unsupported interval: {interval}")

    interval_ms = _INTERVAL_TO_MS[interval]
    start_ms = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    end_ms = int(pd.Timestamp(end, tz="UTC").timestamp() * 1000)

    total_bars_estimate = (end_ms - start_ms) // interval_ms
    progress = tqdm(total=total_bars_estimate, desc=f"{symbol} {interval}", unit="bars")

    all_rows: list[list[object]] = []
    cursor = start_ms
    with httpx.Client() as client:
        while cursor < end_ms:
            batch = _fetch_batch(client, symbol, interval, cursor, end_ms)
            if not batch:
                break
            all_rows.extend(batch)
            progress.update(len(batch))
            # Advance cursor past the last fetched bar.
            # Binance returns open_time as int but typed as object in our list signature.
            last_open_ms = int(batch[-1][0])  # type: ignore[call-overload]
            cursor = last_open_ms + interval_ms
            # Polite: avoid hammering even though the public limit is generous
            time.sleep(0.05)
    progress.close()

    if not all_rows:
        raise RuntimeError(f"No data returned for {symbol} {interval} [{start}, {end})")

    df = pd.DataFrame(all_rows, columns=_KLINE_COLUMNS)
    # Convert numeric columns from strings
    numeric_cols = ["open", "high", "low", "close", "volume", "quote_volume"]
    df[numeric_cols] = df[numeric_cols].astype(float)
    df["trades"] = df["trades"].astype(int)

    df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df.set_index("timestamp")
    df = df[["open", "high", "low", "close", "volume", "quote_volume", "trades"]]

    # Drop any duplicates from boundary overlaps; keep first occurrence.
    df = df[~df.index.duplicated(keep="first")]
    df = df.sort_index()

    return df


def download_to_parquet(
    symbol: str,
    interval: str,
    start: str,
    end: str,
    out_dir: Path | str,
    force: bool = False,
) -> Path:
    """Fetch klines and write to parquet, returning the path.

    Idempotent: if the target file exists and `force=False`, fetching is
    skipped and the existing file path is returned.

    Args:
        symbol: e.g. "BTCUSDT".
        interval: e.g. "1h".
        start: Start ISO datetime (UTC).
        end: End ISO datetime (UTC).
        out_dir: Directory to write parquet into.
        force: If True, re-download and overwrite even if cached.

    Returns:
        Path to the written parquet file.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{symbol}_{interval}.parquet"

    if out_path.exists() and not force:
        return out_path

    df = fetch_binance_klines(symbol, interval, start, end)
    df.to_parquet(out_path, compression="snappy")
    return out_path


def load_ohlcv_parquet(path: Path | str) -> pd.DataFrame:
    """Load a previously-downloaded OHLCV parquet."""
    return pd.read_parquet(path)


def load_symbol_set(symbols: list[str], data_dir: Path | str, interval: str = "1h") -> dict[str, pd.DataFrame]:
    """Load OHLCV data for multiple symbols from a directory."""
    data_dir = Path(data_dir)
    return {
        symbol: load_ohlcv_parquet(data_dir / f"{symbol}_{interval}.parquet")
        for symbol in symbols
    }
