"""Tests for src/quant/data/splitter.py.

Ensures the IS / OOS-1 / Holdout split is:
  - Time-ordered (no leakage across boundaries)
  - Sized correctly per the declared fractions
  - Immutable (frozen dataclass)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant.data.splitter import DataSplit, split_time_series


@pytest.fixture
def linear_time_series() -> pd.DataFrame:
    """1000-bar series with monotonically increasing 'price' for predictability."""
    timestamps = pd.date_range("2024-01-01", periods=1000, freq="1h", tz="UTC")
    return pd.DataFrame(
        {"close": np.arange(1000, dtype=np.float64)},
        index=timestamps,
    )


class TestSplitTimeSeries:
    def test_default_fractions_sum_correctly(self, linear_time_series: pd.DataFrame) -> None:
        split = split_time_series(linear_time_series)
        assert len(split.is_data) == 600
        assert len(split.oos1_data) == 200
        assert len(split.holdout_data) == 200
        assert (
            len(split.is_data) + len(split.oos1_data) + len(split.holdout_data)
            == len(linear_time_series)
        )

    def test_time_ordering_preserved(self, linear_time_series: pd.DataFrame) -> None:
        split = split_time_series(linear_time_series)
        # IS ends before OOS1 starts, OOS1 ends before Holdout starts
        assert split.is_range[1] < split.oos1_range[0]
        assert split.oos1_range[1] < split.holdout_range[0]

    def test_no_data_overlap(self, linear_time_series: pd.DataFrame) -> None:
        split = split_time_series(linear_time_series)
        is_idx = set(split.is_data.index)
        oos1_idx = set(split.oos1_data.index)
        holdout_idx = set(split.holdout_data.index)
        assert len(is_idx & oos1_idx) == 0
        assert len(oos1_idx & holdout_idx) == 0
        assert len(is_idx & holdout_idx) == 0

    def test_fractions_must_sum_to_one(self, linear_time_series: pd.DataFrame) -> None:
        with pytest.raises(ValueError, match=r"must sum to 1\.0"):
            split_time_series(linear_time_series, is_frac=0.5, oos1_frac=0.2, holdout_frac=0.2)

    def test_unsorted_input_rejected(self) -> None:
        timestamps = pd.date_range("2024-01-01", periods=10, freq="1h", tz="UTC")
        df = pd.DataFrame({"close": np.arange(10)}, index=timestamps[::-1])
        with pytest.raises(ValueError, match="sorted ascending"):
            split_time_series(df)

    def test_split_is_immutable(self, linear_time_series: pd.DataFrame) -> None:
        """DataSplit is a frozen dataclass — direct attribute assignment is forbidden."""
        split = split_time_series(linear_time_series)
        with pytest.raises((AttributeError, Exception)):
            split.is_data = pd.DataFrame()  # type: ignore[misc]

    def test_corrupt_ranges_rejected(self) -> None:
        """Constructing a DataSplit with out-of-order ranges must fail."""
        empty = pd.DataFrame()
        t0 = pd.Timestamp("2024-01-01")
        t1 = pd.Timestamp("2024-02-01")
        t2 = pd.Timestamp("2024-03-01")
        # IS range AFTER holdout range — should raise
        with pytest.raises(ValueError, match="time-ordered"):
            DataSplit(
                is_data=empty,
                oos1_data=empty,
                holdout_data=empty,
                is_range=(t2, t2),
                oos1_range=(t1, t1),
                holdout_range=(t0, t0),
            )
