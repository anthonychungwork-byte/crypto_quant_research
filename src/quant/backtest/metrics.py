"""Performance metrics for a trades DataFrame.

Headline metrics:
  - n_trades, win_rate
  - PF (Profit Factor) — sum(wins) / |sum(losses)|
  - Sharpe (annualized over 365 calendar days)
  - Max Drawdown (peak-to-trough on cumulative equity)
  - CAGR
  - Avg trade pct, median trade pct
  - Avg duration (bars)
  - Exit reason breakdown
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_metrics(trades: pd.DataFrame, annualization: float = 365.0) -> dict[str, float]:
    """Compute standard trading metrics from a trades DataFrame.

    Args:
        trades: DataFrame with columns including 'net_pct', 'entry_time'.
        annualization: Sqrt-of-this is multiplied into Sharpe (default 365 for crypto).

    Returns:
        Dict of metric_name → value. Empty trades return zeroed dict.
    """
    n = len(trades)
    if n == 0:
        return {
            "n_trades": 0,
            "win_rate": 0.0,
            "pf": 0.0,
            "sharpe": 0.0,
            "max_dd": 0.0,
            "cagr": 0.0,
            "avg_trade_pct": 0.0,
            "median_trade_pct": 0.0,
            "gross_return": 0.0,
            "n_wins": 0,
            "n_losses": 0,
        }

    returns = trades["net_pct"].to_numpy()
    wins_mask = returns > 0
    n_wins = int(wins_mask.sum())
    n_losses = int(n - n_wins)

    sum_wins = float(returns[wins_mask].sum())
    sum_losses = float(returns[~wins_mask].sum())
    pf = sum_wins / abs(sum_losses) if sum_losses < 0 else float("inf")

    # Daily-resampled returns for Sharpe / DD computation
    daily = (
        trades.set_index("entry_time")["net_pct"]
        .resample("1D")
        .sum()
        .fillna(0.0)
    )
    sharpe = (
        float((daily.mean() / daily.std()) * np.sqrt(annualization))
        if daily.std() > 0
        else 0.0
    )

    equity = (1.0 + daily).cumprod()
    running_max = equity.cummax()
    drawdown = (equity - running_max) / running_max
    max_dd = float(abs(drawdown.min()))

    n_days = max((daily.index[-1] - daily.index[0]).days, 1)
    years = n_days / 365.0
    cagr = float(equity.iloc[-1] ** (1.0 / years) - 1.0) if years > 0 and equity.iloc[-1] > 0 else 0.0

    return {
        "n_trades": int(n),
        "win_rate": float(n_wins / n),
        "pf": float(pf),
        "sharpe": sharpe,
        "max_dd": max_dd,
        "cagr": cagr,
        "avg_trade_pct": float(returns.mean()),
        "median_trade_pct": float(np.median(returns)),
        "gross_return": float(returns.sum()),
        "n_wins": n_wins,
        "n_losses": n_losses,
    }
