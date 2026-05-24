"""No-look-ahead invariant tests.

This is the signature defense of this framework. The premise:

    A correctly-implemented strategy's signal at time t depends only on data
    up to and including time t. Therefore, mutating any data AFTER t must
    leave the signal at t unchanged.

If a strategy peeks at the future — even subtly through `.shift(-1)`, a
poorly-chosen `.rolling(center=True)`, or an aggregation that includes
future bars — the mutated-future test will detect it and fail.

The test suite includes:
  1. A trivially-correct baseline (FLAT always) — must pass.
  2. A correct SMA crossover — must pass.
  3. A DELIBERATELY-BROKEN cheat strategy — must fail.

Test #3 is the meta-test: it verifies the verifier itself works.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant.strategies.base import Signal, Strategy, StrategyConfig
from quant.strategies.mean_reversion import MeanReversionConfig, MeanReversionStrategy
from quant.strategies.stretched_vp import StretchedVPConfig, StretchedVPStrategy
from quant.strategies.tsmom import TSMOMConfig, TSMOMStrategy


class _AlwaysFlatStrategy(Strategy):
    """Trivially correct: always emits FLAT. Has no path to look-ahead."""

    def generate_signals(self, ohlcv: pd.DataFrame) -> pd.Series:
        return pd.Series(
            data=np.full(len(ohlcv), Signal.FLAT.value, dtype=np.int64),
            index=ohlcv.index,
            name="signal",
        )


class _SmaCrossoverStrategy(Strategy):
    """Correctly-implemented SMA crossover (no look-ahead).

    Uses only trailing windows, so signal[t] depends only on close[:t+1].
    """

    def __init__(self, config: StrategyConfig, fast: int = 5, slow: int = 20) -> None:
        super().__init__(config)
        self.fast = fast
        self.slow = slow

    def generate_signals(self, ohlcv: pd.DataFrame) -> pd.Series:
        fast_ma = ohlcv["close"].rolling(self.fast, min_periods=self.fast).mean()
        slow_ma = ohlcv["close"].rolling(self.slow, min_periods=self.slow).mean()
        signal = pd.Series(Signal.FLAT.value, index=ohlcv.index, dtype=np.int64, name="signal")
        signal[fast_ma > slow_ma] = Signal.LONG.value
        signal[fast_ma < slow_ma] = Signal.SHORT.value
        return signal


class _LookAheadCheatStrategy(Strategy):
    """DELIBERATELY BROKEN: uses next bar's close. Must be caught by the invariant test."""

    def generate_signals(self, ohlcv: pd.DataFrame) -> pd.Series:
        # CHEAT: look one bar into the future
        future_close = ohlcv["close"].shift(-1)
        signal = pd.Series(Signal.FLAT.value, index=ohlcv.index, dtype=np.int64, name="signal")
        signal[future_close > ohlcv["close"]] = Signal.LONG.value
        signal[future_close < ohlcv["close"]] = Signal.SHORT.value
        return signal


def _assert_no_lookahead(
    strategy: Strategy,
    ohlcv: pd.DataFrame,
    split_idx: int = 150,
) -> None:
    """Mutate ohlcv[split_idx:] and assert signals[:split_idx] are unchanged.

    Args:
        strategy: Strategy under test.
        ohlcv: Synthetic OHLCV.
        split_idx: The index after which to mutate (must be < len(ohlcv)).

    Raises:
        AssertionError: If signals[:split_idx] change after future mutation,
            indicating look-ahead bias.
    """
    signals_original = strategy.generate_signals(ohlcv)

    # Aggressive future mutation: multiply prices by a large constant.
    # Any strategy that looked forward will produce different signals.
    ohlcv_mutated = ohlcv.copy()
    price_cols = ["open", "high", "low", "close"]
    ohlcv_mutated.loc[ohlcv_mutated.index[split_idx:], price_cols] *= 99.0

    signals_mutated = strategy.generate_signals(ohlcv_mutated)

    pd.testing.assert_series_equal(
        signals_original.iloc[:split_idx],
        signals_mutated.iloc[:split_idx],
        check_names=False,
    )


# ─────────────────────────────────────────────────────────────────────────────
# The invariant tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.no_lookahead
class TestNoLookaheadInvariant:
    """Verify the no-lookahead invariant on each in-repo strategy."""

    def test_always_flat_passes(self, synthetic_ohlcv: pd.DataFrame) -> None:
        """A trivially-correct strategy emits no future-dependent signals."""
        strategy = _AlwaysFlatStrategy(StrategyConfig(name="flat", timeframe="1h"))
        _assert_no_lookahead(strategy, synthetic_ohlcv)

    def test_sma_crossover_passes(self, synthetic_ohlcv: pd.DataFrame) -> None:
        """A correctly-implemented trailing-window strategy passes."""
        strategy = _SmaCrossoverStrategy(StrategyConfig(name="sma", timeframe="1h"))
        _assert_no_lookahead(strategy, synthetic_ohlcv)

    def test_cheat_strategy_is_caught(self, synthetic_ohlcv: pd.DataFrame) -> None:
        """META-TEST: a strategy that uses .shift(-1) MUST fail the invariant.

        This verifies the verifier itself works. Without this, a passing
        no-lookahead test would not be evidence of anything.
        """
        cheat = _LookAheadCheatStrategy(StrategyConfig(name="cheat", timeframe="1h"))
        with pytest.raises(AssertionError):
            _assert_no_lookahead(cheat, synthetic_ohlcv)

    def test_mean_reversion_passes(self, synthetic_ohlcv: pd.DataFrame) -> None:
        """The production Asian-session-fade strategy is causal."""
        strategy = MeanReversionStrategy(
            MeanReversionConfig(name="mean_reversion", timeframe="1h")
        )
        _assert_no_lookahead(strategy, synthetic_ohlcv)

    def test_stretched_vp_passes(self, synthetic_ohlcv: pd.DataFrame) -> None:
        """The Stretched VP strategy is causal (uses prior-day VP only)."""
        strategy = StretchedVPStrategy(
            StretchedVPConfig(name="stretched_vp", timeframe="1h")
        )
        _assert_no_lookahead(strategy, synthetic_ohlcv)

    def test_tsmom_passes(self, synthetic_ohlcv: pd.DataFrame) -> None:
        """TSMOM uses only trailing returns → causal."""
        strategy = TSMOMStrategy(
            TSMOMConfig(name="tsmom", timeframe="1h", lookback_weeks=1, signal_threshold=0.01)
        )
        _assert_no_lookahead(strategy, synthetic_ohlcv, split_idx=200)
