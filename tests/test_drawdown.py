"""Tests for src/quant/risk/drawdown.py."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant.risk.drawdown import max_drawdown, underwater_duration


class TestMaxDrawdown:
    def test_monotonic_increasing_zero_drawdown(self) -> None:
        equity = pd.Series([100, 110, 120, 130, 140])
        assert max_drawdown(equity) == pytest.approx(0.0)

    def test_known_drawdown_50pct(self) -> None:
        """100 → 50 = 50% drawdown."""
        equity = pd.Series([100, 50])
        assert max_drawdown(equity) == pytest.approx(0.5)

    def test_recovery_then_deeper_drawdown(self) -> None:
        """100 → 80 → 110 → 55 → 110.  Max DD = 50% (from peak 110 to 55)."""
        equity = pd.Series([100, 80, 110, 55, 110])
        assert max_drawdown(equity) == pytest.approx(0.5)


class TestUnderwaterDuration:
    def test_flat_equity_zero_underwater(self) -> None:
        equity = pd.Series([100, 100, 100, 100])
        ud = underwater_duration(equity)
        assert (ud == 0).all()

    def test_simple_drawdown_period(self) -> None:
        """100 → 90 → 95 → 110: underwater for 2 bars, then recovers."""
        equity = pd.Series([100, 90, 95, 110])
        ud = underwater_duration(equity)
        assert ud.tolist() == [0, 1, 2, 0]

    def test_dtype_is_integer(self) -> None:
        equity = pd.Series(np.arange(10.0))
        assert underwater_duration(equity).dtype == np.int64
