# Methodology — Strict Strategy Development SOP

This document codifies the rules followed when developing any new strategy in this repo. Every claim made about a strategy's performance must be traceable to a stage that produced it under these rules.

## Why a rigid SOP

The vast majority of published quant strategies fail in live trading. Three root causes account for most failures:

1. **Look-ahead bias** — future data leaking into signal generation
2. **Multiple testing inflation** — running many candidates, reporting only the winners
3. **Iterative cherry-picking** — tweaking parameters until the test set passes

A SOP that physically prevents these patterns produces more reliable estimates than skill or intent alone. This document defines that SOP.

---

## Stage 0 — Hypothesis

**Required artifact:** `notebooks/01_hypothesis.ipynb` containing a written thesis BEFORE any backtest data is loaded.

A hypothesis must include:
- The market inefficiency being targeted
- The economic / behavioral mechanism producing it
- Prior literature or theoretical support
- Falsifiable predictions

**Rule.** No code that depends on price data may be written until this artifact exists and is committed.

---

## Stage 1 — Data Split

Splits are defined exactly once at project start in `src/quant/data/splitter.py`:

| Set | Fraction | Purpose |
|-----|----------|---------|
| In-Sample (IS) | 60% (earliest) | Parameter search |
| Out-of-Sample 1 (OOS-1) | 20% (middle) | Candidate selection |
| Holdout | 20% (most recent) | Final test — used ONCE |

**Rule.** The Holdout set is referenced exactly once in the entire project lifecycle. Re-running invalidates the result.

A unit test (`tests/test_data_split_integrity.py`) enforces that the split boundaries cannot be changed without an explicit version bump and a new project log entry.

---

## Stage 2 — In-Sample Optimization

Parameter search (grid or Bayesian via Optuna) runs only on IS. The framework records:

- All parameter combinations tested → `results/tables/is_search_log.csv`
- Performance metrics for each (PF, Sharpe, MaxDD, trade count)
- The top 10 candidates selected for Stage 3

**Rule.** Number of combinations tested (`N_trials`) is recorded so the Deflated Sharpe Ratio in Stage 5 uses correct N.

---

## Stage 3 — OOS-1 Validation

The 10 candidates from Stage 2 are evaluated on OOS-1. **One** candidate is selected — no ensembling, no mixing, no parameter averaging.

**Acceptance criterion:** OOS-1 PF must be at least 70% of IS PF. If not, the strategy is declared overfit and the development cycle ends with a postmortem.

---

## Stage 4 — Walk-Forward Robustness

A 6-month rolling window is applied across the full dataset: train on past 6 months, test on next 1 month, advance one month, repeat.

**Acceptance criterion:** At least 80% of test months must produce PF > 1.0.

This stage detects regime overfitting that a static IS/OOS split cannot catch.

---

## Stage 5 — Holdout Final Test

The selected parameter set is evaluated on Holdout. **This run happens exactly once.**

**Acceptance criteria (all must hold):**

| Metric | Threshold |
|--------|-----------|
| Profit Factor | > 1.3 |
| Sharpe Ratio | > 1.0 |
| Max Drawdown | < 30% |
| Deflated Sharpe Ratio | > 0 (Bailey & López de Prado, with N from Stage 2-3) |

Failure at this stage is recorded in `results/POSTMORTEM.md` and the strategy is retired.

---

## Stage 6 — Multi-Coin Robustness

The same strategy with the same parameter set is evaluated across multiple symbols. At least 4 of 6 must pass the Stage 5 thresholds.

A strategy that only works on a single symbol is treated as overfit to that symbol's idiosyncratic history.

---

## Cost Assumptions — HORROR Mode

All headline performance numbers use the conservative cost model:

| Component | Value | Justification |
|-----------|-------|---------------|
| Slippage (market entry) | 0.20% | 95th percentile of observed live-trading slippage |
| Taker fee | 0.12% | Standard exchange rate, no tier discount applied |
| Maker fee (limit) | 0.02% | Standard exchange rate |
| Funding rate | symbol-specific 8h | Realized funding from historical data |

A `BASE` mode (slippage 0.05%) exists for internal debugging but is **never** used for any number presented in reports, READMEs, or external communication.

---

## Red Lines — Strategy Death Conditions

Any of the following terminates the development cycle. The temptation to "tweak just a bit more" is itself the failure mode this SOP prevents.

1. IS → OOS-1 PF drop > 30%
2. Walk-forward: < 80% of months PF > 1.0
3. Holdout: fails any of PF / Sharpe / MaxDD / DSR thresholds
4. Multi-coin: < 4 of 6 pass
5. Any urge to "run holdout one more time"
6. Any urge to "ensemble the failed candidates"

---

## Explicitly Forbidden Practices

- Examining backtest results before writing the hypothesis
- Using future data to compute indicators (look-ahead bias)
- Iteratively tweaking parameters against the holdout
- Substituting metrics (PF fails → report Sharpe instead)
- Ensembling failed candidates to manufacture a passing result
- Re-splitting data after seeing results
- Adding "just one more" symbol to fix a multi-coin failure

---

## References

- Bailey, D.H. & López de Prado, M. (2014). *The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and Non-Normality*. Journal of Portfolio Management.
- López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley.
- Harvey, C. & Liu, Y. (2015). *Backtesting*. Journal of Portfolio Management.
- Romano, J.P. & Wolf, M. (2005). *Stepwise Multiple Testing as Formalized Data Snooping*. Econometrica.
