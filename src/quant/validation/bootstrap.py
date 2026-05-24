"""Block bootstrap for confidence intervals on time-series metrics.

Standard i.i.d. bootstrap fails on time-series due to autocorrelation in returns.
Block bootstrap (Politis & Romano, 1994, *The Stationary Bootstrap*) preserves
the dependence structure by resampling contiguous blocks rather than individual
observations.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np


def block_bootstrap_metric(
    returns: np.ndarray,
    metric_fn: Callable[[np.ndarray], float],
    block_size: int = 20,
    n_resamples: int = 1000,
    confidence: float = 0.95,
    random_state: int | None = None,
) -> tuple[float, float, float]:
    """Compute (point estimate, lower CI bound, upper CI bound) via block bootstrap.

    Args:
        returns: 1-D return series.
        metric_fn: Callable mapping returns array → scalar metric.
        block_size: Length of contiguous block.
            Rule of thumb: n ** (1/3) for daily data.
        n_resamples: Number of bootstrap resamples.
        confidence: Coverage level (default 0.95 = 95%).
        random_state: Seed for reproducibility.

    Returns:
        (point_estimate, lower_bound, upper_bound).
    """
    if len(returns) < block_size:
        raise ValueError(f"returns length {len(returns)} < block_size {block_size}")
    if not (0 < confidence < 1):
        raise ValueError(f"confidence must be in (0, 1), got {confidence}")

    rng = np.random.default_rng(random_state)
    n = len(returns)
    n_blocks = (n + block_size - 1) // block_size  # ceiling division

    point = float(metric_fn(returns))
    estimates = np.empty(n_resamples, dtype=np.float64)
    for i in range(n_resamples):
        # Pick n_blocks random start indices, then concatenate blocks
        starts = rng.integers(0, n - block_size + 1, size=n_blocks)
        resampled = np.concatenate([returns[s : s + block_size] for s in starts])[:n]
        estimates[i] = metric_fn(resampled)

    alpha = (1.0 - confidence) / 2.0
    lower = float(np.quantile(estimates, alpha))
    upper = float(np.quantile(estimates, 1.0 - alpha))
    return point, lower, upper


def bootstrap_sharpe_ci(
    returns: np.ndarray,
    annualization: float = 365.0,
    block_size: int = 20,
    n_resamples: int = 1000,
    confidence: float = 0.95,
    random_state: int | None = None,
) -> tuple[float, float, float]:
    """Convenience: bootstrap CI specifically for annualized Sharpe."""

    def sharpe(r: np.ndarray) -> float:
        if r.std() <= 0:
            return 0.0
        return float((r.mean() / r.std()) * np.sqrt(annualization))

    return block_bootstrap_metric(
        returns=returns,
        metric_fn=sharpe,
        block_size=block_size,
        n_resamples=n_resamples,
        confidence=confidence,
        random_state=random_state,
    )
