"""Data layer: loading, splitting, quality checks."""

from quant.data.splitter import DataSplit, split_time_series

__all__ = ["DataSplit", "split_time_series"]
