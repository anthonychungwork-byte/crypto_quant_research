"""Walk-forward validation: rolling train/test windows across the full series.

Detects regime-overfit that a static IS/OOS split cannot catch. Default
configuration: train on 6 months, test on next 1 month, advance by 1 month.

Acceptance criterion per METHODOLOGY.md Stage 4:
    >= 80% of test windows must produce PF > 1.0
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class WalkForwardWindow:
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp


@dataclass(frozen=True)
class WalkForwardResult:
    windows: list[WalkForwardWindow]
    per_window_metrics: pd.DataFrame
    pct_profitable: float


def generate_windows(
    data_start: pd.Timestamp,
    data_end: pd.Timestamp,
    train_months: int = 6,
    test_months: int = 1,
    step_months: int = 1,
) -> list[WalkForwardWindow]:
    """Generate a list of rolling train/test windows. Stub — impl in Stage 4."""
    raise NotImplementedError("Implement in Stage 4 walk-forward notebook.")


def run_walk_forward(*args: object, **kwargs: object) -> WalkForwardResult:
    """Execute walk-forward across all windows. Stub — impl in Stage 4."""
    raise NotImplementedError("Implement in Stage 4 walk-forward notebook.")
