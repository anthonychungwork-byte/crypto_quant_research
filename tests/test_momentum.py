"""Tests for src/quant/analytics/momentum.py."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant.analytics.momentum import momentum_signal, trailing_return, trailing_volatility


class TestTrailingReturn:
    def test_basic_calculation(self) -> None:
        prices = pd.Series([100.0, 110.0, 121.0, 133.1])
        # 1-bar trailing return: ratio - 1
        out = trailing_return(prices, lookback_bars=1)
        # Index 0 is NaN, then (110/100)-1, (121/110)-1, (133.1/121)-1
        assert np.isnan(out.iloc[0])
        assert out.iloc[1] == pytest.approx(0.10)
        assert out.iloc[2] == pytest.approx(0.10)
        assert out.iloc[3] == pytest.approx(0.10)

    def test_longer_lookback(self) -> None:
        prices = pd.Series([100.0, 105.0, 110.0, 115.0])
        out = trailing_return(prices, lookback_bars=3)
        # Index 0-2 NaN, index 3 = 115/100 - 1 = 0.15
        assert np.isnan(out.iloc[0])
        assert np.isnan(out.iloc[2])
        assert out.iloc[3] == pytest.approx(0.15)

    def test_rejects_zero_lookback(self) -> None:
        prices = pd.Series([100.0, 110.0])
        with pytest.raises(ValueError, match="lookback_bars must be positive"):
            trailing_return(prices, lookback_bars=0)


class TestMomentumSignal:
    def test_long_above_threshold(self) -> None:
        # Construct prices where past N-bar return > threshold
        prices = pd.Series([100.0] * 5 + [105.0, 110.0, 115.0])
        sig = momentum_signal(prices, lookback_bars=3, threshold=0.02)
        # At index 7: trailing = 115/100 - 1 = 0.15 > 0.02 → 1
        assert sig.iloc[7] == 1

    def test_short_below_threshold(self) -> None:
        prices = pd.Series([100.0] * 5 + [95.0, 90.0, 85.0])
        sig = momentum_signal(prices, lookback_bars=3, threshold=0.02)
        # At index 7: trailing = 85/100 - 1 = -0.15 < -0.02 → -1
        assert sig.iloc[7] == -1

    def test_flat_within_deadzone(self) -> None:
        prices = pd.Series([100.0] * 5 + [100.5, 101.0, 101.0])
        sig = momentum_signal(prices, lookback_bars=3, threshold=0.05)
        # At index 7: trailing = 101/100 - 1 = 0.01 < 0.05 → 0 (FLAT)
        assert sig.iloc[7] == 0


class TestTrailingVolatility:
    def test_constant_returns_zero_vol(self) -> None:
        # Constant returns → std = 0
        returns = pd.Series([0.01] * 20)
        vol = trailing_volatility(returns, lookback_bars=10)
        # After warmup, all should be 0
        assert vol.iloc[15] == pytest.approx(0.0, abs=1e-9)

    def test_variable_returns_positive_vol(self) -> None:
        rng = np.random.default_rng(seed=42)
        returns = pd.Series(rng.normal(0, 0.01, 100))
        vol = trailing_volatility(returns, lookback_bars=20)
        assert vol.iloc[50] > 0
