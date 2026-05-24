"""Position sizing models: fixed fractional, volatility-targeted, Kelly fraction."""

from __future__ import annotations


def fixed_fractional_size(equity: float, risk_per_trade: float, stop_distance: float) -> float:
    """Position size such that hitting stop loses exactly risk_per_trade * equity.

    Args:
        equity: Account equity in quote currency.
        risk_per_trade: Fraction of equity risked per trade (e.g. 0.01 = 1%).
        stop_distance: Stop loss distance as a fraction of entry price.

    Returns:
        Notional position size in quote currency.
    """
    if stop_distance <= 0:
        raise ValueError(f"stop_distance must be positive, got {stop_distance}")
    return (equity * risk_per_trade) / stop_distance


def vol_targeted_size(equity: float, target_vol: float, realized_vol: float) -> float:
    """Position size that targets a constant portfolio volatility.

    Args:
        equity: Account equity.
        target_vol: Annualized volatility target (e.g. 0.15 = 15%).
        realized_vol: Recent realized annualized volatility.

    Returns:
        Notional position size.
    """
    if realized_vol <= 0:
        raise ValueError(f"realized_vol must be positive, got {realized_vol}")
    return equity * (target_vol / realized_vol)
