"""Volume Profile computation.

The Volume Profile of a set of bars is the distribution of traded volume
across price levels. Three derived points are commonly used:

  - POC (Point of Control): price level with maximum traded volume.
  - VAH (Value Area High): upper boundary of the value area.
  - VAL (Value Area Low):  lower boundary of the value area.

The "value area" is the contiguous range around POC that contains
`va_pct` (typically 70%) of total volume — i.e., the price range where
"value" was established during the session.

This implementation distributes each bar's volume *linearly* across its
own [low, high] range. With H1 bars over 24 hours per UTC day, this is a
standard approximation when tick data is unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class VolumeProfile:
    """Result of `compute_volume_profile`."""

    poc_price: float
    vah_price: float
    val_price: float
    total_volume: float
    bucket_centers: np.ndarray
    bucket_volumes: np.ndarray
    overall_low: float
    overall_high: float

    @property
    def value_area_width_pct(self) -> float:
        """VA width as fraction of POC."""
        if self.poc_price <= 0:
            return 0.0
        return float((self.vah_price - self.val_price) / self.poc_price)


def compute_volume_profile(
    bars: pd.DataFrame,
    n_buckets: int = 50,
    va_pct: float = 0.70,
) -> VolumeProfile:
    """Compute Volume Profile from a DataFrame of OHLCV bars.

    Args:
        bars: DataFrame with columns ``high``, ``low``, ``volume``.
            Index irrelevant.
        n_buckets: Number of equal-width price buckets between
            min(low) and max(high).
        va_pct: Fraction of total volume defining the value area
            (default 0.70).

    Returns:
        VolumeProfile with POC / VAH / VAL plus the underlying
        bucket distribution.

    Raises:
        ValueError: If `bars` is empty or has zero total volume.
    """
    if bars.empty:
        raise ValueError("Cannot compute VP from empty bars")
    if not (0.0 < va_pct < 1.0):
        raise ValueError(f"va_pct must be in (0, 1), got {va_pct}")

    overall_low = float(bars["low"].min())
    overall_high = float(bars["high"].max())

    # Degenerate case: all bars at single price.
    if overall_high <= overall_low:
        total = float(bars["volume"].sum())
        return VolumeProfile(
            poc_price=overall_low,
            vah_price=overall_low,
            val_price=overall_low,
            total_volume=total,
            bucket_centers=np.array([overall_low]),
            bucket_volumes=np.array([total]),
            overall_low=overall_low,
            overall_high=overall_high,
        )

    bucket_edges = np.linspace(overall_low, overall_high, n_buckets + 1)
    bucket_centers = 0.5 * (bucket_edges[:-1] + bucket_edges[1:])
    bucket_volumes = np.zeros(n_buckets, dtype=np.float64)

    lows = bars["low"].to_numpy(dtype=np.float64)
    highs = bars["high"].to_numpy(dtype=np.float64)
    vols = bars["volume"].to_numpy(dtype=np.float64)

    for bl, bh, bv in zip(lows, highs, vols, strict=True):
        if bv <= 0:
            continue
        if bh <= bl:
            # single price; assign to bucket containing bl
            idx = min(int((bl - overall_low) / (overall_high - overall_low) * n_buckets), n_buckets - 1)
            bucket_volumes[idx] += bv
            continue
        bar_range = bh - bl
        # vectorised overlap calculation
        overlap_low = np.maximum(bl, bucket_edges[:-1])
        overlap_high = np.minimum(bh, bucket_edges[1:])
        overlap = np.maximum(overlap_high - overlap_low, 0.0)
        bucket_volumes += bv * (overlap / bar_range)

    total_volume = float(bucket_volumes.sum())
    if total_volume <= 0:
        raise ValueError("Total volume is zero; check input bars")

    poc_idx = int(np.argmax(bucket_volumes))
    poc_price = float(bucket_centers[poc_idx])

    # Expand VA from POC, greedy on neighbour volume
    va_target = va_pct * total_volume
    cum = float(bucket_volumes[poc_idx])
    low_idx = poc_idx
    high_idx = poc_idx
    while cum < va_target:
        can_up = high_idx < n_buckets - 1
        can_down = low_idx > 0
        if not (can_up or can_down):
            break
        if not can_down:
            high_idx += 1
            cum += float(bucket_volumes[high_idx])
        elif not can_up:
            low_idx -= 1
            cum += float(bucket_volumes[low_idx])
        else:
            up_vol = float(bucket_volumes[high_idx + 1])
            down_vol = float(bucket_volumes[low_idx - 1])
            if up_vol >= down_vol:
                high_idx += 1
                cum += up_vol
            else:
                low_idx -= 1
                cum += down_vol

    val_price = float(bucket_edges[low_idx])
    vah_price = float(bucket_edges[high_idx + 1])

    return VolumeProfile(
        poc_price=poc_price,
        vah_price=vah_price,
        val_price=val_price,
        total_volume=total_volume,
        bucket_centers=bucket_centers,
        bucket_volumes=bucket_volumes,
        overall_low=overall_low,
        overall_high=overall_high,
    )
