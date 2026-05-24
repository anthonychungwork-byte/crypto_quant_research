"""Tests for src/quant/validation/deflated_sharpe.py.

Sanity checks on the Bailey & López de Prado (2014) formulas:
  - PSR(observed = benchmark) ≈ 0.5
  - DSR(n_trials > 1) ≤ PSR(observed > 0) — selecting from more trials
    deflates the certainty.
"""

from __future__ import annotations

import pytest

from quant.validation.deflated_sharpe import deflated_sharpe_ratio, probabilistic_sharpe_ratio


class TestProbabilisticSharpe:
    def test_at_benchmark_returns_half(self) -> None:
        """If observed Sharpe == benchmark, P(true > benchmark) = 0.5."""
        psr = probabilistic_sharpe_ratio(
            observed_sharpe=1.0,
            benchmark_sharpe=1.0,
            n_returns=252,
        )
        assert psr == pytest.approx(0.5, abs=1e-6)

    def test_high_observed_gives_high_probability(self) -> None:
        psr = probabilistic_sharpe_ratio(
            observed_sharpe=2.0,
            benchmark_sharpe=0.0,
            n_returns=252,
        )
        assert psr > 0.95

    def test_low_observed_gives_low_probability(self) -> None:
        psr = probabilistic_sharpe_ratio(
            observed_sharpe=0.1,
            benchmark_sharpe=2.0,
            n_returns=252,
        )
        assert psr < 0.05


class TestDeflatedSharpe:
    def test_more_trials_deflate_more(self) -> None:
        """DSR(100 trials) < DSR(10 trials) — selection bias grows with N."""
        kwargs = {
            "observed_sharpe": 1.5,
            "sharpe_std": 0.5,
            "n_returns": 252,
        }
        dsr_10 = deflated_sharpe_ratio(**kwargs, n_trials=10)
        dsr_100 = deflated_sharpe_ratio(**kwargs, n_trials=100)
        assert dsr_100 < dsr_10

    def test_dsr_in_unit_interval(self) -> None:
        """Output is a probability — must be in [0, 1]."""
        dsr = deflated_sharpe_ratio(
            observed_sharpe=1.2,
            sharpe_std=0.4,
            n_trials=50,
            n_returns=500,
        )
        assert 0.0 <= dsr <= 1.0
