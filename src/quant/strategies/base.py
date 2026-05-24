"""Abstract base class for strategies.

All concrete strategies must inherit from `Strategy` and implement
`generate_signals`. The base enforces:

1. The signals DataFrame must not contain look-ahead information — the
   signal at time t can only depend on data up to and including t.
2. The strategy must declare its parameter schema via a `StrategyConfig`
   dataclass so the optimizer knows what to search over.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

import pandas as pd


class Signal(Enum):
    """Discrete trading signals."""

    FLAT = 0
    LONG = 1
    SHORT = -1


@dataclass(frozen=True)
class StrategyConfig:
    """Base configuration for strategies. Subclasses extend with parameters."""

    name: str
    timeframe: str  # e.g. "1h", "4h"


class Strategy(ABC):
    """Abstract base for all strategies.

    Subclasses implement `generate_signals` to produce a Series of Signal
    values aligned to the input OHLCV index.
    """

    def __init__(self, config: StrategyConfig) -> None:
        self.config = config

    @abstractmethod
    def generate_signals(self, ohlcv: pd.DataFrame) -> pd.Series:
        """Produce a signal at each bar in `ohlcv`.

        Args:
            ohlcv: OHLCV DataFrame with DatetimeIndex.

        Returns:
            Series of Signal values, indexed identically to ohlcv.

        Invariants enforced by tests/test_no_lookahead.py:
            - signals.iloc[t] must depend ONLY on ohlcv.iloc[:t+1]
            - signals.index == ohlcv.index (no rebasing)
        """
        raise NotImplementedError

    @property
    def name(self) -> str:
        return self.config.name
