"""Walk-forward validation: rolling train/test windows across the full series.

Detects regime overfit that a static IS/OOS split cannot catch. For each window
we apply the *single* parameter set chosen in Stage 3 to the test segment —
we are not re-optimizing per window. The acceptance criterion is whether the
single chosen configuration produces PF > 1.0 in a consistent fraction of
test months.

Per METHODOLOGY.md Stage 4: at least 80% of test months must produce PF > 1.0.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from dateutil.relativedelta import relativedelta
from tqdm import tqdm

from quant.backtest.costs import CostMode, get_cost_model
from quant.backtest.metrics import compute_metrics
from quant.strategies.mean_reversion import MeanReversionConfig, MeanReversionStrategy


@dataclass(frozen=True)
class WalkForwardWindow:
    train_start: pd.Timestamp
    train_end: pd.Timestamp  # exclusive (test starts here)
    test_start: pd.Timestamp
    test_end: pd.Timestamp  # exclusive


@dataclass(frozen=True)
class WalkForwardResult:
    windows: list[WalkForwardWindow]
    per_window_metrics: pd.DataFrame
    pct_profitable: float
    threshold_pct: float
    passes: bool


def generate_windows(
    data_start: pd.Timestamp,
    data_end: pd.Timestamp,
    train_months: int = 6,
    test_months: int = 1,
    step_months: int = 1,
) -> list[WalkForwardWindow]:
    """Generate rolling train/test windows over [data_start, data_end).

    Inputs are assumed to be tz-aware UTC pd.Timestamp instances.
    """
    windows: list[WalkForwardWindow] = []
    train_start = data_start
    while True:
        train_end = train_start + relativedelta(months=train_months)
        test_start = train_end
        test_end = test_start + relativedelta(months=test_months)
        if test_end > data_end:
            break
        windows.append(
            WalkForwardWindow(
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
            )
        )
        train_start = train_start + relativedelta(months=step_months)
    return windows


def run_walk_forward(
    ohlcv: pd.DataFrame,
    config: MeanReversionConfig,
    train_months: int = 6,
    test_months: int = 1,
    step_months: int = 1,
    threshold_pf: float = 1.0,
    threshold_pct: float = 0.80,
    cost_mode: CostMode = CostMode.HORROR,
) -> WalkForwardResult:
    """Run walk-forward on a single locked configuration."""
    if not isinstance(ohlcv.index, pd.DatetimeIndex):
        raise TypeError(f"Expected DatetimeIndex, got {type(ohlcv.index).__name__}")

    cost = get_cost_model(cost_mode)
    strat = MeanReversionStrategy(config)

    windows = generate_windows(
        data_start=ohlcv.index.min(),
        data_end=ohlcv.index.max(),
        train_months=train_months,
        test_months=test_months,
        step_months=step_months,
    )

    rows: list[dict[str, object]] = []
    for win in tqdm(windows, desc="Walk-forward"):
        test_slice = ohlcv.loc[win.test_start : win.test_end - pd.Timedelta(hours=1)]
        if len(test_slice) == 0:
            continue
        trades = strat.simulate(test_slice, cost_model=cost)
        metrics = compute_metrics(trades)
        rows.append(
            {
                "window_start": win.test_start,
                "window_end": win.test_end,
                **metrics,
            }
        )

    per_window = pd.DataFrame(rows)
    if len(per_window) == 0:
        return WalkForwardResult(
            windows=windows,
            per_window_metrics=per_window,
            pct_profitable=0.0,
            threshold_pct=threshold_pct,
            passes=False,
        )

    profitable = (per_window["pf"] > threshold_pf).sum()
    pct = float(profitable / len(per_window))
    return WalkForwardResult(
        windows=windows,
        per_window_metrics=per_window,
        pct_profitable=pct,
        threshold_pct=threshold_pct,
        passes=pct >= threshold_pct,
    )
