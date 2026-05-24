"""Tests for src/quant/validation/bootstrap.py."""

from __future__ import annotations

import numpy as np
import pytest

from quant.validation.bootstrap import block_bootstrap_metric, bootstrap_sharpe_ci


class TestBlockBootstrap:
    def test_mean_ci_contains_true_mean(self) -> None:
        """Bootstrap CI for the mean should contain the population mean most of the time."""
        rng = np.random.default_rng(seed=42)
        returns = rng.normal(loc=0.001, scale=0.01, size=500)
        point, low, high = block_bootstrap_metric(
            returns=returns,
            metric_fn=lambda r: float(r.mean()),
            block_size=20,
            n_resamples=500,
            random_state=42,
        )
        # Point estimate equals sample mean
        assert point == pytest.approx(returns.mean())
        # CI should bracket the point estimate
        assert low <= point <= high

    def test_ci_widens_with_lower_confidence(self) -> None:
        """A 99% CI must be at least as wide as a 90% CI."""
        rng = np.random.default_rng(seed=0)
        returns = rng.normal(0, 0.01, size=300)

        def metric(r: np.ndarray) -> float:
            return float(r.mean())

        _, lo_90, hi_90 = block_bootstrap_metric(returns, metric, n_resamples=300, confidence=0.90, random_state=1)
        _, lo_99, hi_99 = block_bootstrap_metric(returns, metric, n_resamples=300, confidence=0.99, random_state=1)
        assert (hi_99 - lo_99) >= (hi_90 - lo_90)

    def test_rejects_block_size_too_large(self) -> None:
        returns = np.array([0.01, 0.02, 0.03])
        with pytest.raises(ValueError, match="block_size"):
            block_bootstrap_metric(returns, lambda r: 0.0, block_size=10)


class TestBootstrapSharpe:
    def test_returns_point_and_ci(self) -> None:
        rng = np.random.default_rng(seed=7)
        returns = rng.normal(loc=0.002, scale=0.015, size=500)
        point, lo, hi = bootstrap_sharpe_ci(returns, n_resamples=200, random_state=7)
        assert lo <= point <= hi
        # Daily Sharpe for these positive-drift returns should be > 0
        assert point > 0
