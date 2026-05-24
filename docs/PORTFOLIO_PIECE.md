# Portfolio Piece — Crypto Quant Research

This repository is a complete demonstration of disciplined quantitative research applied to cryptocurrency markets, built to communicate a specific bar of engineering and statistical rigor.

## What this demonstrates

| Capability | Where to look |
|------------|---------------|
| Methodology design | [METHODOLOGY.md](../METHODOLOGY.md) — 6-stage SOP that structurally prevents overfit |
| Look-ahead bias defense | [tests/test_no_lookahead.py](../tests/test_no_lookahead.py) — programmatic invariant + meta-test |
| Multiple-testing correction | [src/quant/validation/deflated_sharpe.py](../src/quant/validation/deflated_sharpe.py) — Bailey & López de Prado 2014 |
| Production-grade Python | `pyproject.toml`, `pre-commit-config.yaml`, `Makefile` — strict ruff + mypy + pytest |
| Walk-forward framework | [src/quant/validation/walk_forward.py](../src/quant/validation/walk_forward.py) |
| Realistic cost modeling | [src/quant/backtest/costs.py](../src/quant/backtest/costs.py) — HORROR mode (0.20% slippage) |
| Reproducibility | `uv.lock` + `make all` reproduces from scratch |

## How to evaluate (for a hiring manager / client)

1. **Read** [README.md](../README.md) — 5 minutes
2. **Read** [METHODOLOGY.md](../METHODOLOGY.md) — 10 minutes (the SOP)
3. **Read** [tests/test_no_lookahead.py](../tests/test_no_lookahead.py) — the meta-test verifies the verifier
4. **Read** [src/quant/validation/deflated_sharpe.py](../src/quant/validation/deflated_sharpe.py) — Bailey & López de Prado implementation
5. **Browse** [notebooks/](../notebooks/) in order — 01 (hypothesis) → 08 (postmortem)
6. **Run** `make all` — full lint + type + test suite passes from a clean clone

## What's intentionally not here

- Production parameter values (gitignored as `configs/*.prod.yaml`)
- Live trading PnL (gitignored as `results/live_*.csv`)
- Strategies currently deployed against real capital

The engine, methodology, and statistical tooling are open. The alpha is reserved. This balance — open methodology, closed parameters — is the HYBRID IP-protection policy described in `.gitignore`.

## Engagement

Specializations:
- Backtest framework design with look-ahead bias prevention
- Multi-testing correction (DSR, PSR, Romano-Wolf, White's Reality Check)
- Walk-forward validation pipelines
- Live trading bot architecture (real-money deployments on multiple exchanges)
- Cost model calibration from live execution data
- Crypto-specific market microstructure
