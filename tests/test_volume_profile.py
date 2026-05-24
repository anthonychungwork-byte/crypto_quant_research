"""Tests for src/quant/analytics/volume_profile.py."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant.analytics.volume_profile import compute_volume_profile


def _bars(triples: list[tuple[float, float, float]]) -> pd.DataFrame:
    """Build OHLCV-shape DataFrame from (low, high, volume) triples."""
    return pd.DataFrame(
        {
            "open": [t[0] for t in triples],
            "high": [t[1] for t in triples],
            "low": [t[0] for t in triples],
            "close": [t[1] for t in triples],
            "volume": [t[2] for t in triples],
        }
    )


class TestVolumeProfile:
    def test_single_price_bar(self) -> None:
        """All volume at one price → POC=VAH=VAL=that price."""
        bars = _bars([(100.0, 100.0, 50.0)])
        vp = compute_volume_profile(bars, n_buckets=20)
        assert vp.poc_price == pytest.approx(100.0)
        assert vp.vah_price == pytest.approx(100.0)
        assert vp.val_price == pytest.approx(100.0)
        assert vp.total_volume == pytest.approx(50.0)

    def test_bell_shaped_distribution(self) -> None:
        """Bars concentrated around 150 → POC near 150, VA centered there."""
        # 5 bars wider, 5 bars narrower around the center → more vol near 150
        bars = _bars(
            [(100.0, 200.0, 1.0)] * 5
            + [(130.0, 170.0, 5.0)] * 5
            + [(145.0, 155.0, 20.0)] * 5
        )
        vp = compute_volume_profile(bars, n_buckets=50, va_pct=0.70)
        assert 140 < vp.poc_price < 160, f"POC {vp.poc_price} should be near 150"
        # VA should be relatively tight (centered around 150)
        assert vp.val_price < vp.poc_price < vp.vah_price
        assert (vp.vah_price - vp.val_price) < 60

    def test_concentrated_volume(self) -> None:
        """Most volume at a narrow band → tight VA around that band."""
        # 9 bars of low volume across 100-200, 1 bar of huge volume in 150-152
        bars = _bars([(100.0, 200.0, 1.0)] * 9 + [(150.0, 152.0, 1000.0)])
        vp = compute_volume_profile(bars, n_buckets=100, va_pct=0.70)
        # POC near 151
        assert 149 < vp.poc_price < 153
        # VA should be tight around the concentrated bar
        assert (vp.vah_price - vp.val_price) < 20

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            compute_volume_profile(_bars([]))

    def test_rejects_invalid_va_pct(self) -> None:
        bars = _bars([(100.0, 110.0, 10.0)])
        with pytest.raises(ValueError, match="va_pct"):
            compute_volume_profile(bars, va_pct=0.0)
        with pytest.raises(ValueError, match="va_pct"):
            compute_volume_profile(bars, va_pct=1.0)

    def test_va_brackets_poc(self) -> None:
        """VAL <= POC <= VAH always."""
        rng = np.random.default_rng(seed=42)
        bars = pd.DataFrame(
            {
                "open": rng.uniform(100, 110, 50),
                "high": rng.uniform(110, 120, 50),
                "low": rng.uniform(90, 100, 50),
                "close": rng.uniform(100, 110, 50),
                "volume": rng.uniform(1, 100, 50),
            }
        )
        vp = compute_volume_profile(bars)
        assert vp.val_price <= vp.poc_price <= vp.vah_price

    def test_total_volume_preserved(self) -> None:
        """Sum of bucket volumes equals total bar volume."""
        bars = _bars([(100.0, 105.0, 5.0), (102.0, 108.0, 7.0), (104.0, 110.0, 3.0)])
        vp = compute_volume_profile(bars)
        assert vp.total_volume == pytest.approx(15.0, rel=1e-9)
