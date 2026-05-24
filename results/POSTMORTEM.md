# Postmortem — Failed Hypothesis Log

This document records strategies that failed any gate of the 6-stage SOP.

Each entry documents:
- **Hypothesis** (what we thought would work)
- **Where it died** (stage and metric)
- **Numbers** (without parameter peeking — only Stage results)
- **Lesson** captured

A failed strategy is a successful execution of the methodology: the SOP exists precisely to catch the strategies that would not survive live trading. Three failures here is **not three losses** — it is three correct rejections of strategies that would have lost real money in production.

---

## Index

| # | Hypothesis | Status | Killed at | Headline |
|---|------------|--------|-----------|----------|
| v1 | Asian Session Extreme Fade | RETIRED | Stage 2 | 0/1500 trials profitable |
| v2 | Stretched Volume Profile Fade | RETIRED | Stage 2 | 0/300 trials profitable; best PF 0.92 |
| v3 | Time-Series Momentum (TSMOM) | RETIRED | Stage 4 | Stage 2+3 passed; walk-forward 53% < 80% |

---

## v1 — Asian Session Extreme Fade

**Source**: Original hypothesis. After Asian session close (UTC 13:00), fade prices that closed near the extremes of the Asian range, betting on reversion toward the range midpoint.

**Notebook**: [`notebooks/01_hypothesis.ipynb`](../notebooks/01_hypothesis.ipynb)
**Search log**: [`results/tables/is_search_log.csv`](tables/is_search_log.csv)
**Status**: RETIRED at Stage 2

### Numbers (HORROR cost mode)
- Trials: 1,500
- PF > 1.0: **0 / 1,500 (0%)**
- Sharpe > 0: **0 / 1,500 (0%)**
- Best PF: 0.76
- Best Sharpe: -0.65
- Best MaxDD: 41%

### Pattern observed
Wider range filters reduced losses but never produced profit. The best results came from the strictest filter (only 88 trades), suggesting any edge is too thin to overcome HORROR-mode costs.

### Lesson
Short-term reversal does not work on crypto at H1 — empirically confirms [Yang (2018)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3174421) finding that short-term reversal anomalies fail in crypto markets. Our hypothesis was the wrong direction.

---

## v2 — Stretched Volume Profile Fade

**Source**: [Axia Futures YT — "Stretched Volume Profile Strategy In Crypto"](https://www.youtube.com/watch?v=MUv2GfGAW_I) (Brannigan Barrett methodology). At UTC 23:00, compute the day's Volume Profile; if close stretched beyond Value Area, fade next day to Point of Control.

**Notebook**: [`notebooks/01b_hypothesis_v2_stretched_vp.ipynb`](../notebooks/01b_hypothesis_v2_stretched_vp.ipynb)
**Search log**: [`results/tables/is_search_log_v2_stretched_vp.csv`](tables/is_search_log_v2_stretched_vp.csv)
**Status**: RETIRED at Stage 2

### Numbers (HORROR cost mode)
- Trials: 300
- PF > 1.0: **0 / 300 (0%)**
- Sharpe > 0: **0 / 300 (0%)**
- Best PF: **0.92** (improvement from v1's 0.76)
- Best Sharpe: -0.10 (close to break-even)
- Best MaxDD: **8.3%** (significantly better risk control than v1)

### Pattern observed
Tightest filter (threshold 2.5%) produced best results with only 19 trades over 2.85 years. Edge appears to exist but at a level absorbed entirely by the 0.64% HORROR round-trip cost. With BASE mode (0.05% slip), v2 would likely have been marginally profitable.

### Lesson
This was a real prop-trader's strategy from a credible source (Axia Futures). Failure here is more informative than v1: confirms that discretionary prop trader edges depend on cost structures we cannot replicate with retail HORROR assumptions. The strategy is not wrong — it's just too marginal to survive our realistic costs.

This is the key insight Yang (2018) implies: most crypto anomalies, when costs are honest, vanish.

---

## v3 — Time-Series Momentum (TSMOM)

**Source**: [Han, Kang, Ryu (2023) — Time-Series and Cross-Sectional Momentum in the Cryptocurrency Market](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4675565), rooted in Moskowitz, Ooi, Pedersen (2012). For each of 6 coins independently: long if trailing N-week return > +threshold, short if < -threshold, flat otherwise. Weekly rebalance.

**Notebook**: [`notebooks/01c_hypothesis_v3_tsmom.ipynb`](../notebooks/01c_hypothesis_v3_tsmom.ipynb)
**Search log**: [`results/tables/is_search_log_v3_tsmom.csv`](tables/is_search_log_v3_tsmom.csv)
**Walk-forward**: [`results/tables/walkforward_v3_tsmom.csv`](tables/walkforward_v3_tsmom.csv)
**Chosen config**: [`data/processed/chosen_config_v3_tsmom.json`](../data/processed/chosen_config_v3_tsmom.json)
**Status**: RETIRED at Stage 4

### Stage 2 — IS grid (30 trials × 6 coins)
- PF > 1.0: **30 / 30 (100%)** ✅
- PF > 1.3: 24 / 30
- Sharpe > 0: 30 / 30 (100%)
- Sharpe > 1.0: 4 / 30
- Best PF: 2.29, Sharpe 1.16, MaxDD 39%
- **Stage 2 PASS**

### Stage 3 — OOS-1 validation (top 10 candidates)
- Candidates passing 70%-PF-retention gate: **9 / 10** ✅
- Chosen config: lookback=4 weeks, signal_threshold=2%, vol_target=False
- **OOS-1 PF 2.11, Sharpe 1.32, MaxDD 13.5%, CAGR 93%**
- PF retention: 1.14× (OOS outperformed IS — strong sign of robustness)
- **Stage 3 PASS**

### Stage 4 — Walk-forward (45 monthly windows on full data)
- Profitable months: **24 / 45 (53%)**
- Required: ≥ 80%
- **Stage 4 FAIL**

### Pattern observed
Performance bimodal: a handful of strong-trend months (2022 H2 crypto winter selloff, 2023 banking rally, 2024 ETF approval, 2024 Nov post-election) produced PF > 10. Many quiet months had PF < 1 due to whipsaws around no clear trend.

Aggregate IS+OOS metrics looked stellar because the big trend months dominated. Walk-forward revealed that **most of the time, the strategy is whipsawing modestly**.

### Lesson
TSMOM has a real edge on crypto (as Han et al predicted), but the edge is **regime-conditional** — it only manifests during clear trending periods. A follower of this strategy would experience long stretches of small losses (6-12 months) interspersed with occasional huge wins.

Per-month profitability of 53% is genuinely insufficient for client-following use even though aggregate Sharpe looks good. The bar exists because aggregate metrics can hide regime fragility.

**Crucial decision per SOP**: not tweaking parameters or relaxing acceptance criteria. Strategy retired. Possible v4 directions:
- Add regime filter (e.g., only trade when realized volatility expanding or when ADX shows trend)
- Combine with mean-reversion signal during ranging regimes
- These would be NEW hypotheses with their own Stage 0 lockdown, not "v3 tweaks"

---

## Cross-Cutting Lessons

1. **HORROR cost mode is the binding constraint** — v1 and v2 both have detectable edges at BASE cost, but neither survives 0.64% round-trip. This is exactly why HORROR is the rule.

2. **Crypto reversal does not work at H1** — three different reversal mechanisms (v1 fade, v2 fade, plus academic literature) all confirm Yang's finding.

3. **Crypto momentum exists but is regime-conditional** — v3 confirmed academic TSMOM finding but walk-forward exposed that the edge is concentrated in trend regimes, not steady-state.

4. **Walk-forward is necessary** — v3 would have looked like a winner if we'd stopped at Stage 3. The 80% monthly-profitable bar is unconventionally strict but it's what separates "robust" from "lucky in IS/OOS aggregate".

5. **No parameter peeking, ever** — three failures, zero post-hoc parameter tweaking, three new hypotheses written from scratch. Methodology > any specific strategy.

---

## What this repository proves

The fact that three different academically-supported and intuitively-reasonable hypotheses all failed at progressively later stages — and that each failure was clearly diagnosed — demonstrates exactly what a quant research framework is supposed to do: **kill bad strategies before they kill capital**.

For any future strategy added to this repo, the same 6-stage process applies. The framework is reusable across all asset classes and signal types.
