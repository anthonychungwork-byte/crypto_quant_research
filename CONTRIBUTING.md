# Contributing

This is primarily a personal research / portfolio repository. External contributions are welcome only if they preserve the strict SOP described in [METHODOLOGY.md](METHODOLOGY.md).

## Workflow

1. Fork the repo
2. `make all` from a clean clone — env, hooks, lint, type, test all pass
3. Create a feature branch
4. Make changes
5. `make check` locally before pushing
6. Open a PR

## What is in scope

- Engine improvements (faster vectorization, additional cost-model modes, additional metrics)
- New validation modules (e.g. Romano-Wolf step-down, White's Reality Check)
- New base strategies in `src/quant/strategies/` (must include a hypothesis notebook)
- Bug fixes
- Documentation improvements

## What is NOT in scope

- Production parameters for any existing strategy (those are gitignored on purpose)
- Strategies that bypass the 6-stage SOP — for example, a strategy that reports holdout-tuned numbers will be rejected at review
- Changes to `01_hypothesis.ipynb` that retroactively redefine a locked strategy
- Adding `nbstripout` — outputs are intentionally committed

## Code style

- ruff format (configured in `pyproject.toml`)
- ruff lint (run via `make lint`)
- mypy strict (run via `make type`)
- Tests required for any non-trivial logic in `src/quant/`
- No-lookahead test required for any new strategy added to `src/quant/strategies/`

## License

MIT — see [LICENSE](LICENSE). Contributions are accepted under the same license.
