# Academic Crypto Strategy Candidates — Literature Review

**Date**: 2026-05-24
**Source**: QuantPedia (36 crypto research articles) + SSRN papers + arxiv 2025
**Goal**: Identify academically-supported strategies for v3 hypothesis after v1 + v2 reversal failures

---

## 🔑 Key Meta-Finding

**Yang (2018) "Behavioral Anomalies in Cryptocurrency Markets"** tested 20+ classic stock anomalies on crypto and found:

| Anomaly Class | Crypto Result |
|---------------|---------------|
| **Price Momentum** | ✅ **WORKS** — robust, statistically significant |
| Short-term Reversal | ❌ **DOESN'T WORK** at daily frequency |
| Long-term Reversal | ❌ DOESN'T WORK |
| Risk-based factors | ❌ Not significant |

**Implication for us**: v1 (Asian fade) and v2 (Stretched VP fade) were both reversal strategies. The academic literature predicted both would fail. We empirically confirmed Yang's finding on H1 BTC.

**→ Switch to momentum strategies.**

Paper: [Yang (2018) on SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3174421)

---

## 🎯 Top Candidates for v3

### ⭐⭐⭐ Candidate A: Cross-Sectional Momentum (Dobrynskaya 2021)

**Source**: [Dobrynskaya — Cryptocurrency Momentum and Reversal](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3913263) (peer-reviewed, Journal of Alternative Investments)

**Spec**:
- Sample: 2,000 cryptocurrencies (2014-2020)
- **Momentum**: 2-4 week formation period, hold 1 week
- **Reversal**: 1+ month formation, hold 1 week (note: this is LONG-horizon reversal, not daily)
- Cross-sectional: rank top/bottom by return, long top short bottom (or reverse)
- Findings: "Economically large, statistically significant"
- "Faster metabolism" — momentum switches to reversal after ~1 month

**Adapted for our 6-coin universe**:
- At each Monday open, compute trailing 14-day return for each of {BTC, ETH, SOL, AVAX, XRP, BNB}
- Rank: long top 2, short bottom 2 (or long top 1 / short bottom 1)
- Hold 7 days, rebalance next Monday
- Position size: equal $ allocation

**Pros**:
- Academic peer review
- Different mechanism from Shield (cross-sectional, not single-asset)
- HORROR-friendly (weekly rebalance = ~52 trades/yr × 0.64% cost = 33% drag, still OK if edge > 50%/yr)
- Builds reusable multi-asset infrastructure

**Cons**:
- Only 6 coins (paper used 2000, very weak cross-sectional dispersion at N=6)
- Rebalance cost potentially high

**Implementation**: 6-8 hr (multi-asset infrastructure)

---

### ⭐⭐⭐ Candidate B: Bitcoin Overnight + 10-day MAX (QuantPedia 2024)

**Source**: [QuantPedia — How To Profitably Trade Bitcoin's Overnight Sessions](https://quantpedia.com/how-to-profitably-trade-bitcoins-overnight-sessions/) — Cyril Dujava, Nov 2024

**Spec** (verbatim from paper):
- **Trigger**: Bitcoin at 10-day MAX at session close
- **Entry windows**:
  - Friday close → Monday open (weekend hold)
  - Monday close → Tuesday open (overnight hold)
  - Tuesday close → Wednesday open (overnight hold)
- **Exit**: Morning open at 10 AM EST after each hold
- **Hold duration**: 12-65 hours
- **Data**: hourly BTC from Gemini, 2015-2024

**Reported performance**:
- IS (pre-Oct 2021): Strong positive return, excellent Sharpe, low MaxDD
- OOS (post-Oct 2021): Attractive return, still excellent Sharpe
- "Most returns happen overnight, not daytime"

**Pros**:
- Very specific spec (easy to implement)
- Single-asset (BTC only initially)
- Momentum-based (aligns with Yang's finding)
- Out-of-sample tested by QuantPedia
- Compatible with our existing single-asset framework
- HORROR-friendly (max 3 entries per week × 0.64% = ~10% annual cost drag)

**Cons**:
- Time-of-day filter very specific to US session — does it work on 24/7 crypto via UTC?
- Limited to BTC initially

**Implementation**: 3-4 hr (single-asset, reuses 80% of framework)

---

### ⭐⭐ Candidate C: MAX Lookback Strategy (Bitcoin)

**Source**: [QuantPedia — Revisiting Trend-following and Mean-reversion in Bitcoin](https://quantpedia.com/revisiting-trend-following-and-mean-reversion-strategies-in-bitcoin/) — Sona Beluska, 2024 (based on original 2022 paper)

**Spec**:
- **Entry**: Buy BTC when price reaches N-day MAX
- **Lookback options tested**: 10, 20, 30, 40, 50 days
- **Exit**: Reset when no longer at MAX (or hold N days)

**Reported performance**:
- MAX strategy: "Higher returns and lower drawdown" vs MIN (mean reversion)
- MAX remains effective OOS (Feb 2022 - Aug 2024)
- MIN strategy fails OOS — confirms Yang's reversal finding

**Pros**:
- Simplest spec (1 parameter: lookback)
- Direct trend-following (different from Shield's range-breakout)
- HORROR-friendly (medium-frequency)

**Cons**:
- Very simple, low edge expected
- Already widely known → arbitrage risk

**Implementation**: 2-3 hr (trivial single-asset)

---

### ⭐⭐ Candidate D: Day of Week Effect

**Source**: [QuantPedia — The Day of the Week Effect](https://quantpedia.com/the-day-of-the-week-effect-in-the-crypto-currency-market/)

**Spec**: Crypto markets show statistically significant differential returns on specific days of week.

**Pros**: Trivially simple, can layer on top of other strategies
**Cons**: Likely weak edge, unclear specifics
**Implementation**: 1-2 hr

---

### ⭐ Candidate E: Adaptive Multi-Agent Bitcoin (arxiv 2025)

**Source**: [arxiv 2510.08068 — An Adaptive Multi Agent Bitcoin Trading System](https://arxiv.org/pdf/2510.08068)

**Spec**: ML-based multi-agent (quantitative + sentiment agents) adaptive to market regime.

**Reported**: 30% over buy-and-hold in bull, 15% overall, sentiment agent saved sideways markets

**Pros**: Recent (2025), claims strong performance
**Cons**: ML-heavy, less interpretable, requires sentiment data we don't have
**Implementation**: 15-20 hr (too complex for v3)

---

## 📚 Other Notable QuantPedia Crypto Strategies (FYI, not picked)

| Strategy | Reason not picked |
|----------|------------------|
| Dual Momentum Gold + Bitcoin | Needs gold data, more complex setup |
| Cryptocurrency Volatility Index | Indicator, not a strategy |
| Bitcoin Exchange Reserves Predict Returns | Needs on-chain data we don't have |
| Google Trends Sentiment | Needs sentiment scraping |
| Arbitrage Across Exchanges | Needs multi-exchange data + latency |
| Multi-Timeframe Trend | Could be interesting follow-up to C |
| Calendar Effects | Layer-on, not standalone |

Full list available at `axia_research/` and via QuantPedia's [Cryptocurrency Trading Research](https://quantpedia.com/cryptocurrency-trading-research/) hub.

---

## 🎯 Recommendation

**Top pick: Candidate B (Bitcoin Overnight + 10-day MAX)**

Reasoning:
1. Most **specific** spec (low ambiguity = low implementation risk)
2. **Momentum-based** (aligns with Yang's "what works in crypto")
3. **OOS-tested** by QuantPedia (independent validation)
4. **3-4 hr** implementation (fastest of viable candidates)
5. Single-asset framework reuse = max code reuse
6. Pure OHLCV — no extra data needed

If B fails, **Candidate A (Cross-sectional Momentum)** is natural next step — builds new multi-asset infrastructure that's reusable for future strategies.

**Avoid**: any reversal-based strategy on H1 / daily (Yang says they don't work, we confirmed twice).

---

## Files in this research

- `axia_research/ANALYSIS_SUMMARY.md` — Axia YT analysis (futures-heavy, less relevant for crypto)
- `axia_research/transcripts/` — 15 Axia transcripts
- `docs/ACADEMIC_RESEARCH_CANDIDATES.md` — this file
