"""Deflated Sharpe Ratio (DSR) and Probabilistic Sharpe Ratio (PSR).

References:
    Bailey, D.H. & López de Prado, M. (2014). The Deflated Sharpe Ratio:
    Correcting for Selection Bias, Backtest Overfitting, and Non-Normality.
    Journal of Portfolio Management, 40 (5).

The DSR is the standard correction for the multiple-testing bias inherent
in trying many strategies and reporting the best Sharpe. Without it, naive
Sharpe ratios reported in backtests are routinely 2-3x inflated.

Both PSR and DSR return the probability that the observed Sharpe exceeds
the threshold (PSR) or zero after deflation for trials (DSR).
"""

from __future__ import annotations

import numpy as np
from scipy import stats


def probabilistic_sharpe_ratio(
    observed_sharpe: float,
    benchmark_sharpe: float,
    n_returns: int,
    skewness: float = 0.0,
    kurtosis: float = 3.0,
) -> float:
    """Probabilistic Sharpe Ratio.

    P(true Sharpe > benchmark_sharpe | observed_sharpe, sample stats).

    Args:
        observed_sharpe: Sharpe computed from the return series (annualized).
        benchmark_sharpe: Threshold to test against (annualized).
        n_returns: Number of return observations used to compute Sharpe.
        skewness: Sample skewness of the returns (default 0 = normal).
        kurtosis: Sample kurtosis of the returns (default 3 = normal).

    Returns:
        Probability in [0, 1] that the true Sharpe exceeds benchmark.
    """
    # Bailey & López de Prado eq. (1)
    denom = np.sqrt(
        1.0
        - skewness * observed_sharpe
        + ((kurtosis - 1.0) / 4.0) * observed_sharpe**2
    )
    if denom <= 0:
        return float("nan")
    z = (observed_sharpe - benchmark_sharpe) * np.sqrt(n_returns - 1) / denom
    return float(stats.norm.cdf(z))


def deflated_sharpe_ratio(
    observed_sharpe: float,
    sharpe_std: float,
    n_trials: int,
    n_returns: int,
    skewness: float = 0.0,
    kurtosis: float = 3.0,
) -> float:
    """Deflated Sharpe Ratio.

    P(true Sharpe > 0 | observed_sharpe, having tested n_trials strategies).

    Args:
        observed_sharpe: Best Sharpe from n_trials candidate strategies.
        sharpe_std: Std dev of the Sharpe ratios across the n_trials.
        n_trials: Number of independent strategy variants tested.
        n_returns: Number of return observations used to compute Sharpe.
        skewness: Sample skewness of the winning strategy's returns.
        kurtosis: Sample kurtosis of the winning strategy's returns.

    Returns:
        Probability in [0, 1] that the true Sharpe exceeds 0 after correcting
        for the selection bias of having picked the best of n_trials.
    """
    # Bailey & López de Prado eq. (10)
    # Expected maximum Sharpe under the null (no skill)
    emc = 0.5772156649  # Euler-Mascheroni constant
    max_z = (1.0 - emc) * stats.norm.ppf(1.0 - 1.0 / n_trials) + emc * stats.norm.ppf(
        1.0 - 1.0 / (n_trials * np.e)
    )
    expected_max_sharpe = sharpe_std * max_z

    return probabilistic_sharpe_ratio(
        observed_sharpe=observed_sharpe,
        benchmark_sharpe=expected_max_sharpe,
        n_returns=n_returns,
        skewness=skewness,
        kurtosis=kurtosis,
    )
