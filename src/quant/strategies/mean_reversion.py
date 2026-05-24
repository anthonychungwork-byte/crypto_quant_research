"""Mean reversion strategy — implementation deferred until Stage 0 hypothesis is locked.

Per METHODOLOGY.md Stage 0: no code that depends on price data may be written
until the hypothesis artifact (notebooks/01_hypothesis.ipynb) is committed.
This file is the placeholder that will be filled in once the hypothesis
specifies entry/exit logic, lookback windows, and timing rules.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from quant.strategies.base import Signal, Strategy, StrategyConfig


@dataclass(frozen=True)
class MeanReversionConfig(StrategyConfig):
    """Mean reversion parameters — exact schema set during Stage 0."""

    lookback_bars: int = 24
    entry_z_threshold: float = 2.0
    exit_z_threshold: float = 0.5


class MeanReversionStrategy(Strategy):
    """Mean reversion — implementation TBD post-hypothesis."""

    def generate_signals(self, ohlcv: pd.DataFrame) -> pd.Series:
        raise NotImplementedError(
            "Implement after Stage 0 hypothesis is locked and committed."
        )
        _ = Signal.FLAT  # suppress unused-import warning until impl lands
