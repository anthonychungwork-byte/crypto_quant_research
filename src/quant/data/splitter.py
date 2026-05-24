"""Time-series data splitter: IS / OOS-1 / Holdout.

Split boundaries are defined once at project start and treated as immutable
for the remainder of the project lifecycle. A unit test enforces that any
change to the split must be accompanied by an explicit version bump.

The split policy is **time-ordered**, never random — random splits leak
information across boundaries in time-series and are forbidden.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class DataSplit:
    """Immutable container for the three time-ordered subsets.

    Attributes:
        is_data: In-sample data (earliest 60%). Used for parameter search.
        oos1_data: OOS-1 data (middle 20%). Used for candidate selection.
        holdout_data: Holdout data (most recent 20%). Used EXACTLY once.
        is_range: (start, end) timestamps of IS partition.
        oos1_range: (start, end) timestamps of OOS-1 partition.
        holdout_range: (start, end) timestamps of Holdout partition.
    """

    is_data: pd.DataFrame
    oos1_data: pd.DataFrame
    holdout_data: pd.DataFrame
    is_range: tuple[pd.Timestamp, pd.Timestamp]
    oos1_range: tuple[pd.Timestamp, pd.Timestamp]
    holdout_range: tuple[pd.Timestamp, pd.Timestamp]

    def __post_init__(self) -> None:
        # Enforce time-ordering invariant. Any violation means the split is
        # corrupt and downstream results would be invalid.
        if not (self.is_range[1] <= self.oos1_range[0] <= self.oos1_range[1] <= self.holdout_range[0]):
            raise ValueError(
                f"Split ranges are not strictly time-ordered. "
                f"IS={self.is_range}, OOS1={self.oos1_range}, HOLDOUT={self.holdout_range}"
            )


def split_time_series(
    df: pd.DataFrame,
    is_frac: float = 0.60,
    oos1_frac: float = 0.20,
    holdout_frac: float = 0.20,
    timestamp_col: str | None = None,
) -> DataSplit:
    """Split a time-series DataFrame into IS / OOS-1 / Holdout.

    Args:
        df: Time-series data, sorted ascending by timestamp.
        is_frac: Fraction for in-sample (default 0.60).
        oos1_frac: Fraction for out-of-sample 1 (default 0.20).
        holdout_frac: Fraction for holdout (default 0.20).
        timestamp_col: Name of timestamp column. If None, uses the index.

    Returns:
        DataSplit with the three partitions.

    Raises:
        ValueError: If fractions don't sum to 1.0 (within float tolerance),
            or if data is not sorted by timestamp.
    """
    total = is_frac + oos1_frac + holdout_frac
    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"Fractions must sum to 1.0, got {total}")

    timestamps = df[timestamp_col] if timestamp_col else pd.Series(df.index)
    if not timestamps.is_monotonic_increasing:
        raise ValueError("DataFrame must be sorted ascending by timestamp")

    n = len(df)
    is_end = int(n * is_frac)
    oos1_end = is_end + int(n * oos1_frac)

    is_data = df.iloc[:is_end].copy()
    oos1_data = df.iloc[is_end:oos1_end].copy()
    holdout_data = df.iloc[oos1_end:].copy()

    return DataSplit(
        is_data=is_data,
        oos1_data=oos1_data,
        holdout_data=holdout_data,
        is_range=(_first_ts(is_data, timestamp_col), _last_ts(is_data, timestamp_col)),
        oos1_range=(_first_ts(oos1_data, timestamp_col), _last_ts(oos1_data, timestamp_col)),
        holdout_range=(_first_ts(holdout_data, timestamp_col), _last_ts(holdout_data, timestamp_col)),
    )


def _first_ts(df: pd.DataFrame, col: str | None) -> pd.Timestamp:
    return pd.Timestamp(df[col].iloc[0] if col else df.index[0])


def _last_ts(df: pd.DataFrame, col: str | None) -> pd.Timestamp:
    return pd.Timestamp(df[col].iloc[-1] if col else df.index[-1])
