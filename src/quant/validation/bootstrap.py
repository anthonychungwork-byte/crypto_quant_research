"""Block bootstrap for confidence intervals on Sharpe / PF / MaxDD.

Standard i.i.d. bootstrap fails on time-series due to autocorrelation.
Block bootstrap (Politis & Romano, 1994) preserves dependence by resampling
contiguous blocks of returns rather than individual returns.
"""

from __future__ import annotations

import numpy as np


def block_bootstrap_metric(
    returns: np.ndarray,
    metric_fn: object,
    block_size: int = 20,
    n_resamples: int = 1000,
    confidence: float = 0.95,
    random_state: int | None = None,
) -> tuple[float, float]:
    """Compute (low, high) confidence interval for a metric via block bootstrap.

    Args:
        returns: 1-D return series.
        metric_fn: Callable mapping returns array → scalar metric.
        block_size: Length of contiguous block (rule of thumb: n ** (1/3)).
        n_resamples: Number of bootstrap resamples.
        confidence: Coverage level (default 95%).
        random_state: Seed for reproducibility.

    Returns:
        (lower_bound, upper_bound) of the confidence interval.
    """
    raise NotImplementedError("Implement in Stage 3 OOS validation notebook.")
