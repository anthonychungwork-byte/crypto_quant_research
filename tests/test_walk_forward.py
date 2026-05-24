"""Tests for src/quant/validation/walk_forward.py — window generation only.

The full run_walk_forward path is exercised via the Stage 4 notebook.
"""

from __future__ import annotations

import pandas as pd

from quant.validation.walk_forward import generate_windows


class TestGenerateWindows:
    def test_basic_window_count(self) -> None:
        """4-year span, train=6m, test=1m, step=1m → 42 windows (48-6=42)."""
        start = pd.Timestamp("2022-01-01", tz="UTC")
        end = pd.Timestamp("2026-01-01", tz="UTC")
        windows = generate_windows(start, end, train_months=6, test_months=1, step_months=1)
        # 48 months total, 6 for first train, 1 for first test → first test ends month 7.
        # Last test must end ≤ month 48 → train_start cap = month 41 → 42 windows.
        assert len(windows) == 42

    def test_windows_are_time_ordered(self) -> None:
        start = pd.Timestamp("2022-01-01", tz="UTC")
        end = pd.Timestamp("2024-01-01", tz="UTC")
        windows = generate_windows(start, end)
        for w in windows:
            assert w.train_start < w.train_end
            assert w.train_end == w.test_start
            assert w.test_start < w.test_end

    def test_windows_step_forward(self) -> None:
        start = pd.Timestamp("2022-01-01", tz="UTC")
        end = pd.Timestamp("2024-01-01", tz="UTC")
        windows = generate_windows(start, end, step_months=1)
        for prev, curr in zip(windows[:-1], windows[1:], strict=True):
            assert curr.train_start > prev.train_start

    def test_no_windows_if_span_too_short(self) -> None:
        """If train+test > span, no windows fit."""
        start = pd.Timestamp("2024-01-01", tz="UTC")
        end = pd.Timestamp("2024-03-01", tz="UTC")
        windows = generate_windows(start, end, train_months=6, test_months=1)
        assert windows == []
