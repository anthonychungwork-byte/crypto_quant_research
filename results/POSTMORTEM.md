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
| v4 | TSMOM + Cross-Asset Consensus Filter | RETIRED | Stage 4 | Stage 2+3 passed; walk-forward **20%** (worse than v3) |
| v5 | BTC Overnight + N-day MAX | RETIRED | Stage 3 | Best IS PF 5.56 / Sharpe 1.52; OOS PF 0.18-0.71 — wildly overfit |

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

## v4 — TSMOM + Cross-Asset Consensus Filter

**Source**: Hypothesis introduced to address v3 walk-forward failure. Only trade per-coin TSMOM signals when ≥ N of 6 coins agree on direction. New mechanism, fresh Stage 0 lock.

**Notebook**: [`notebooks/01d_hypothesis_v4_tsmom_consensus.ipynb`](../notebooks/01d_hypothesis_v4_tsmom_consensus.ipynb)
**Search log**: [`results/tables/is_search_log_v4_tsmom_consensus.csv`](tables/is_search_log_v4_tsmom_consensus.csv)
**Walk-forward**: [`results/tables/walkforward_v4_tsmom_consensus.csv`](tables/walkforward_v4_tsmom_consensus.csv)
**Chosen config**: [`data/processed/chosen_config_v4_tsmom_consensus.json`](../data/processed/chosen_config_v4_tsmom_consensus.json)
**Status**: RETIRED at Stage 4

### Stage 2 — IS grid (27 trials × 6 coins, HORROR cost)
- PF > 1.0: **27 / 27 (100%)** ✅
- PF > 1.3: 21 / 27
- Sharpe > 0: 27 / 27
- Sharpe > 1.0: 0 / 27 (notably lower than v3's 4/30)
- Best PF: 2.03 (lookback=4, threshold=5%, consensus=4)
- Best Sharpe: 0.99 (lookback=4, threshold=0%, consensus=3)

### Stage 3 — OOS-1 validation (top 10)
- Pass 70%-retention: **6 / 10** ✅
- Chosen: lookback=4w, threshold=2%, consensus=4
- **OOS PF 2.25, Sharpe 1.16, MaxDD 6.96%** (lowest DD of any candidate strategy!)
- PF retention 1.25× (better than IS)

### Stage 4 — Walk-forward (35 active monthly windows)
- Profitable months: **7 / 35 (20%)** — WORSE than v3
- Required: ≥ 80%
- **Stage 4 FAIL** ❌

### Pattern observed
The consensus filter behaved counter to hypothesis. Rather than smoothing performance across regimes, it CONCENTRATED trading into the strongest trend regimes (when most coins agreed) — those few months produced the strong aggregate numbers, but most months had zero trades or single bad trades.

The consensus filter is conceptually "wait for trend confirmation". In practice that means "miss the start of trends + sit out the chop + still take losses at trend ends".

### Lesson
- Two consecutive momentum strategies (v3 pure, v4 filtered) both failed walk-forward.
- TSMOM-family on crypto H1 + HORROR cost appears to be fundamentally regime-fragile at the monthly granularity we measure.
- Per v4's pre-commitment: no v5 may attempt another TSMOM tweak. Any v5 must use a fundamentally different mechanism (e.g., breakout, calendar-effect, pairs).
- Important: v4's OOS MaxDD of 7% was the LOWEST of any candidate. The absolute risk profile is excellent. The walk-forward bar is what killed it — and that bar is doing its job (catching strategies whose aggregate good performance is regime-luck).

---

## v5 — BTC Overnight + N-day MAX

**Source**: [QuantPedia (2024) — How To Profitably Trade Bitcoin's Overnight Sessions](https://quantpedia.com/how-to-profitably-trade-bitcoins-overnight-sessions/). Enter BTC long at Fri/Mon/Tue 22:00 UTC when at N-day high, exit next morning at 14:00 UTC. Single-asset, time-of-day, momentum-filtered breakout.

**Notebook**: [`notebooks/01e_hypothesis_v5_overnight_max.ipynb`](../notebooks/01e_hypothesis_v5_overnight_max.ipynb)
**Search log**: [`results/tables/is_search_log_v5_overnight_max.csv`](tables/is_search_log_v5_overnight_max.csv)
**Status**: RETIRED at Stage 3

### Stage 2 — IS grid (108 trials)
- PF > 1.0: **96 / 108 (89%)** ✅
- PF > 1.3: 58 / 108
- Sharpe > 1.0: **12 / 108** ✅
- Best PF: **5.56** (lookback=10d, prox=0%, entry=22, exit=14)
- Best Sharpe: **1.52**
- Best MaxDD: **1.4%** (lowest across all 5 strategies)
- Win rate at top: 67-73%
- **Stage 2 PASS** (best metrics across all 5 strategies)

### Stage 3 — OOS-1 validation (top 10)
- Pass 70%-retention: **0 / 10** ❌
- OOS PF range: 0.18 - 0.71 (all losing)
- OOS Sharpe range: -3.36 to -0.88
- Average retention: 0.08 (92% drop from IS)
- **Stage 3 catastrophic FAIL**

### Pattern observed
The strategy ENTRY criteria (Fri/Mon/Tue at 22:00 UTC at 10-day MAX) only fired 13-17 times over 2.5 years of IS data. With such few samples, the 67-73% win rate that produced PF 4-5 is well within range of statistical noise. OOS over a much shorter period (~10 months) had only 4-5 entries, and they happened to land in losing periods.

This is **textbook small-sample overfitting**: high IS metrics driven by lucky coincidence in a tiny sample, completely failing to generalize. The Stage 3 OOS gate is designed precisely for this.

### Lesson
- Strategy specs that fire very few times per year are vulnerable to apparent edge being statistical noise.
- Even when an external party (QuantPedia) reports excellent results on a strategy, the OOS gate must be respected.
- The QuantPedia 9-year backtest may have benefited from a different cost regime or specific historical periods that don't generalize.
- Specifically: their reported results were "in-sample pre-Oct 2021 and OOS-tested Oct 2021 - Oct 2024" — but their OOS may have benefited from the 2023-2024 bull run, which our OOS-1 (Jul 2024 - May 2025) doesn't cover the same way.

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
