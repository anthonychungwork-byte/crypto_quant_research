# Crypto Quant Research

> A rigorous, methodology-first framework for quantitative cryptocurrency strategy research, designed to surface real edge while structurally preventing the most common research pitfalls.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Typed: mypy](https://img.shields.io/badge/typed-mypy-blue.svg)](https://mypy-lang.org/)

## What this is

A research framework demonstrating disciplined quantitative methodology applied to crypto markets. The engine, validation pipeline, and reporting layer are open source. Production parameters and live PnL are intentionally withheld.

**Why this exists.** Most published quant research demos suffer from look-ahead bias, multiple testing inflation, or undisclosed parameter mining. This repo enforces a strict 6-stage discipline at the framework level — including unit tests that fail if look-ahead is introduced.

## Methodology

This project follows a **strict 6-stage strategy development SOP** (see [METHODOLOGY.md](METHODOLOGY.md)):

```
Stage 0  Hypothesis             written before any data is loaded
Stage 1  Data split             IS / OOS-1 / Holdout (locked at project start)
Stage 2  In-sample optimization grid / Bayesian search on IS only
Stage 3  OOS-1 validation       10 candidates → 1 selection
Stage 4  Walk-forward           6-month rolling train/test
Stage 5  Holdout test           run EXACTLY once
Stage 6  Multi-coin robustness  ≥4 of 6 symbols must pass
```

Strategies that fail to clear any gate are documented in [results/POSTMORTEM.md](results/POSTMORTEM.md) — failures are part of the methodology, not omissions.

## Quick start

```bash
# Clone and bootstrap
git clone https://github.com/anthonychungwork-byte/crypto_quant_research.git
cd crypto_quant_research

# Full environment + quality checks (≈ 2 min on first run)
make all

# Launch research notebooks
make notebook
```

## Architecture

```
src/quant/
├── data/          Loading, splitting, quality checks
├── strategies/    Pluggable strategy implementations
├── backtest/      Engine, cost models, execution simulation
├── validation/    Walk-forward, deflated Sharpe, bootstrap
├── risk/          Position sizing, drawdown analysis
└── reporting/     Plots, tables, summary generation

notebooks/         Narrative research log (01-08, one per stage)
configs/           Strategy parameters (example values only)
tests/             Unit tests, including no-lookahead invariants
results/           Figures, tables, postmortems
docs/              Portfolio piece summary
```

## Key technical features

| Feature | Why it matters |
|---------|----------------|
| **Look-ahead bias unit tests** | Programmatic invariant — no future data leaks into signal generation, even by accident |
| **Deflated Sharpe Ratio** | Bailey & López de Prado (2014); corrects Sharpe for the number of strategies tested |
| **HORROR cost mode** | 0.20% slippage + 0.12% taker fees; the only mode used for headline numbers |
| **Walk-forward framework** | 6-month rolling train/test, not a single static split |
| **Multi-coin robustness gate** | At least 4 of 6 symbols must pass — defends against single-symbol overfit |
| **Reproducible environment** | uv lockfile + Makefile — `make all` reproduces from scratch |
| **Pre-commit hooks** | ruff, mypy, nbstripout, large-file detection enforced before commit |

## What's intentionally NOT in this repo

To balance portfolio transparency with IP protection:

- ❌ Production parameter values — `configs/*.prod.yaml` (gitignored)
- ❌ Live trading PnL — `results/live_*.csv` (gitignored)
- ❌ Raw market data — `data/raw/` (gitignored, too large for repo)
- ❌ Strategies currently deployed to capital

Everything that demonstrates **methodology, engineering, and statistical rigor** is open. The framework can be cloned and applied to any strategy — that is the deliverable.

## Tech stack

- **Python 3.12+** with full type annotations (mypy strict)
- **pandas / numpy / pyarrow** — data manipulation, parquet I/O
- **scipy / statsmodels** — statistical tests, hypothesis testing
- **plotly / matplotlib / seaborn** — visualization
- **pytest + hypothesis** — testing, including property-based
- **ruff + mypy + pre-commit** — code quality enforcement
- **uv** — dependency management and Python version pinning

## Status

| Stage | Status |
|-------|--------|
| 0 — Hypothesis | ✅ Locked: Asian Session Extreme Fade (BTCUSDT, 1h) |
| 1 — Data + Split | ✅ 37,225 bars × 6 symbols, 0 missing, split persisted |
| 2 — IS Grid Search | 🔄 1,500-trial grid in progress |
| 3 — OOS Validation | ⏳ |
| 4 — Walk-Forward | ⏳ |
| 5 — Holdout | ⏳ (single shot) |
| 6 — Multi-Coin | ⏳ |
| 8 — Postmortem | ⏳ |

## License

MIT — see [LICENSE](LICENSE).

## Author

**Anthony Chung** — quantitative developer specializing in crypto market microstructure and disciplined research workflows. Available for freelance quant engineering engagements.
