"""Grid search runner — Stage 2 in-sample optimization.

Iterates all combinations of a parameter grid, simulates each, records metrics,
returns a sorted DataFrame. The total trial count `N_trials` must match the
value pre-committed in the hypothesis notebook so that Stage 5's Deflated
Sharpe Ratio uses the correct N.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict
from itertools import product
from pathlib import Path
from typing import Any

import pandas as pd
from tqdm import tqdm

from quant.backtest.costs import CostMode, get_cost_model
from quant.backtest.metrics import compute_metrics
from quant.strategies.mean_reversion import MeanReversionConfig, MeanReversionStrategy
from quant.strategies.stretched_vp import StretchedVPConfig, StretchedVPStrategy


def grid_search_mean_reversion(
    ohlcv: pd.DataFrame,
    param_grid: Mapping[str, Iterable[Any]],
    base_config: MeanReversionConfig | None = None,
    cost_mode: CostMode = CostMode.HORROR,
    output_csv: Path | str | None = None,
) -> pd.DataFrame:
    """Grid search over MeanReversionConfig parameters.

    Args:
        ohlcv: OHLCV data to backtest on (usually the IS partition).
        param_grid: Mapping of parameter name → iterable of candidate values.
            Each key must be a field of MeanReversionConfig.
        base_config: Starting config; parameters in param_grid override.
            Defaults to a fresh MeanReversionConfig.
        cost_mode: HORROR (default, required for all reported numbers) or BASE.
        output_csv: Optional path to write the full search log.

    Returns:
        DataFrame with one row per parameter combination, sorted by Sharpe desc.
        Columns: all grid params + all metrics from compute_metrics.
    """
    base = base_config or MeanReversionConfig(name="mean_reversion", timeframe="1h")
    cost = get_cost_model(cost_mode)

    keys = list(param_grid.keys())
    combos = list(product(*[list(param_grid[k]) for k in keys]))
    n_trials = len(combos)

    rows: list[dict[str, Any]] = []
    for combo in tqdm(combos, total=n_trials, desc="Grid search"):
        overrides = dict(zip(keys, combo, strict=True))
        cfg = MeanReversionConfig(**{**asdict(base), **overrides})
        strat = MeanReversionStrategy(cfg)
        trades = strat.simulate(ohlcv, cost_model=cost)
        metrics = compute_metrics(trades)
        rows.append({**overrides, **metrics})

    df = pd.DataFrame(rows).sort_values("sharpe", ascending=False).reset_index(drop=True)
    df.insert(0, "n_trials", n_trials)

    if output_csv:
        Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_csv, index=False)

    return df


def grid_search_stretched_vp(
    ohlcv: pd.DataFrame,
    param_grid: Mapping[str, Iterable[Any]],
    base_config: StretchedVPConfig | None = None,
    cost_mode: CostMode = CostMode.HORROR,
    output_csv: Path | str | None = None,
) -> pd.DataFrame:
    """Grid search over StretchedVPConfig parameters. Same shape as the MR runner."""
    base = base_config or StretchedVPConfig(name="stretched_vp", timeframe="1h")
    cost = get_cost_model(cost_mode)

    keys = list(param_grid.keys())
    combos = list(product(*[list(param_grid[k]) for k in keys]))
    n_trials = len(combos)

    rows: list[dict[str, Any]] = []
    for combo in tqdm(combos, total=n_trials, desc="Stretched VP grid"):
        overrides = dict(zip(keys, combo, strict=True))
        cfg = StretchedVPConfig(**{**asdict(base), **overrides})
        strat = StretchedVPStrategy(cfg)
        trades = strat.simulate(ohlcv, cost_model=cost)
        metrics = compute_metrics(trades)
        rows.append({**overrides, **metrics})

    df = pd.DataFrame(rows).sort_values("sharpe", ascending=False).reset_index(drop=True)
    df.insert(0, "n_trials", n_trials)

    if output_csv:
        Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_csv, index=False)

    return df
