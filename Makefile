# ─────────────────────────────────────────────────────────────────────────────
# Crypto Quant Research — Makefile
# ─────────────────────────────────────────────────────────────────────────────
# Reproducible workflow: `make all` brings a fresh clone to a fully verified
# state (env synced, lint clean, types clean, tests passing).
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: help install dev sync test test-fast lint format type check clean \
        notebook hooks all stage0 stage1 stage2 stage3 stage4 stage5 stage6

help:  ## Show this help
	@echo "Crypto Quant Research — available commands:"
	@echo ""
	@echo "  Environment:"
	@echo "    install   Install runtime dependencies only"
	@echo "    dev       Install runtime + dev dependencies"
	@echo "    sync      Sync env from pyproject.toml + uv.lock"
	@echo "    hooks     Install pre-commit hooks"
	@echo ""
	@echo "  Quality:"
	@echo "    test      Run pytest with coverage"
	@echo "    test-fast Run pytest skipping slow/integration"
	@echo "    lint      Run ruff linter"
	@echo "    format    Run ruff formatter"
	@echo "    type      Run mypy type checker"
	@echo "    check     lint + type + test (CI equivalent)"
	@echo ""
	@echo "  Research stages:"
	@echo "    stage0    Open hypothesis notebook (Stage 0)"
	@echo "    stage1    Open data quality notebook (Stage 1)"
	@echo "    stage2    Open IS optimization notebook (Stage 2)"
	@echo "    stage3    Open OOS validation notebook (Stage 3)"
	@echo "    stage4    Open walk-forward notebook (Stage 4)"
	@echo "    stage5    Open holdout notebook (Stage 5) — RUN ONCE"
	@echo "    stage6    Open multi-coin notebook (Stage 6)"
	@echo ""
	@echo "  Misc:"
	@echo "    notebook  Launch JupyterLab (all notebooks)"
	@echo "    clean     Remove caches and build artifacts"
	@echo "    all       sync + check (full bootstrap)"

install:
	uv sync --no-dev

dev:
	uv sync

sync:
	uv sync

hooks:
	uv run pre-commit install

test:
	uv run pytest

test-fast:
	uv run pytest -m "not slow and not integration"

lint:
	uv run ruff check src tests

format:
	uv run ruff format src tests notebooks

type:
	uv run mypy src

check: lint type test

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage .hypothesis
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

notebook:
	uv run jupyter lab notebooks/

stage0:
	uv run jupyter lab notebooks/01_hypothesis.ipynb

stage1:
	uv run jupyter lab notebooks/02_data_quality.ipynb

stage2:
	uv run jupyter lab notebooks/03_is_optimization.ipynb

stage3:
	uv run jupyter lab notebooks/04_oos_validation.ipynb

stage4:
	uv run jupyter lab notebooks/05_walkforward.ipynb

stage5:
	uv run jupyter lab notebooks/06_holdout.ipynb

stage6:
	uv run jupyter lab notebooks/07_multicoin.ipynb

all: sync hooks check
	@echo ""
	@echo "[ok] Environment synced"
	@echo "[ok] Pre-commit hooks installed"
	@echo "[ok] Lint / type / test passing"
	@echo ""
	@echo "Ready. Launch research with: make notebook"
	@echo "Or run the full pipeline end-to-end:  bash scripts/run_pipeline.sh"

demo: sync
	@echo "Executing notebooks 02 -> 08 (~10 min if data + grid cached)..."
	bash scripts/run_pipeline.sh
	@echo ""
	@echo "[ok] Demo complete. See results/figures/ and results/tables/"
