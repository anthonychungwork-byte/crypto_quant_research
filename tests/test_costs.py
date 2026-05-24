"""Tests for src/quant/backtest/costs.py.

Verifies HORROR / BASE mode produce correct round-trip costs and that the
default mode is HORROR (the anti-cheating guarantee).
"""

from __future__ import annotations

import pytest

from quant.backtest.costs import CostMode, get_cost_model


class TestCostModel:
    def test_default_mode_is_horror(self) -> None:
        """No argument → must return HORROR mode (anti-cheating default)."""
        assert get_cost_model().mode == CostMode.HORROR

    def test_horror_round_trip_taker_both_sides(self) -> None:
        """Both sides taker: 2*slip + 2*taker = 2*0.0020 + 2*0.0012 = 0.0064."""
        model = get_cost_model(CostMode.HORROR)
        cost = model.round_trip_cost(is_taker_entry=True, is_taker_exit=True)
        assert cost == pytest.approx(0.0064)

    def test_horror_maker_entry_taker_exit(self) -> None:
        """Maker entry (no slip): maker + taker + slip_exit = 0.0002 + 0.0012 + 0.0020."""
        model = get_cost_model(CostMode.HORROR)
        cost = model.round_trip_cost(is_taker_entry=False, is_taker_exit=True)
        assert cost == pytest.approx(0.0002 + 0.0012 + 0.0020)

    def test_base_mode_cheaper_than_horror(self) -> None:
        """BASE slippage (0.05%) < HORROR slippage (0.20%)."""
        base = get_cost_model(CostMode.BASE)
        horror = get_cost_model(CostMode.HORROR)
        assert base.round_trip_cost() < horror.round_trip_cost()

    def test_horror_slippage_at_documented_value(self) -> None:
        """README + METHODOLOGY claim HORROR slippage is 0.20%."""
        assert get_cost_model(CostMode.HORROR).slippage_fraction == pytest.approx(0.0020)
