"""Cost model for backtesting.

Two modes are defined:

  HORROR  — conservative, the only mode used for headline numbers.
            Slippage 0.20%, taker 0.12%, maker 0.02%. Derived from the
            95th percentile of observed live trading slippage.

  BASE    — optimistic, internal-debug only. Slippage 0.05%.
            Never used in any externally-reported number.

The asymmetry exists because real-world execution is closer to HORROR than
BASE, and BASE-mode results have repeatedly failed to reproduce in live
trading. Reports in this repo always use HORROR.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CostMode(Enum):
    HORROR = "horror"
    BASE = "base"


@dataclass(frozen=True)
class CostModel:
    """Per-trade cost components, all expressed as fractions (0.001 = 10 bps)."""

    slippage_fraction: float
    taker_fee_fraction: float
    maker_fee_fraction: float
    mode: CostMode

    def round_trip_cost(self, is_taker_entry: bool = True, is_taker_exit: bool = True) -> float:
        """Total cost for one round trip (entry + exit), as fraction of notional.

        Args:
            is_taker_entry: Whether entry crosses the spread (market order).
            is_taker_exit: Whether exit crosses the spread.

        Returns:
            Total round-trip cost fraction. Multiply by notional for $ cost.
        """
        entry_fee = self.taker_fee_fraction if is_taker_entry else self.maker_fee_fraction
        exit_fee = self.taker_fee_fraction if is_taker_exit else self.maker_fee_fraction
        # Slippage applies to both entry and exit if they are market orders.
        slip_entry = self.slippage_fraction if is_taker_entry else 0.0
        slip_exit = self.slippage_fraction if is_taker_exit else 0.0
        return entry_fee + exit_fee + slip_entry + slip_exit


_HORROR = CostModel(
    slippage_fraction=0.0020,
    taker_fee_fraction=0.0012,
    maker_fee_fraction=0.0002,
    mode=CostMode.HORROR,
)

_BASE = CostModel(
    slippage_fraction=0.0005,
    taker_fee_fraction=0.0012,
    maker_fee_fraction=0.0002,
    mode=CostMode.BASE,
)


def get_cost_model(mode: CostMode = CostMode.HORROR) -> CostModel:
    """Return the cost model for the requested mode.

    Default is HORROR. Callers must explicitly pass CostMode.BASE to opt into
    the optimistic mode, and the resulting numbers must never appear in any
    externally-facing report.
    """
    if mode == CostMode.HORROR:
        return _HORROR
    if mode == CostMode.BASE:
        return _BASE
    raise ValueError(f"Unknown cost mode: {mode}")
