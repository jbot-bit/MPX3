# STRATEGY FAMILY: ORB_RSI

## 1. Purpose
Exploit momentum exhaustion: when RSI > 70 at 1800 ORB, price is overbought and ORB breakout (especially downward) has higher probability of reversal/continuation.

## 2. Core Assumption
When RSI exceeds 70 at 1800 (18:00 Brisbane time, during London session), momentum is stretched. ORB breakouts in this environment have different probabilities than normal conditions.

## 3. Baseline Logic (CANONICAL)
- Entry: First 1-minute close outside ORB range (18:00-18:05)
- Stop: Opposite side of ORB (full ORB size)
- Target: RR × ORB size (1.5 only - higher RRs not tested)
- Trade lifetime: 4-hour scan window from ORB close
- Cost basis for approval: **$8.40 RT** (commission $2.40 + spread_double $2.00 + slippage $4.00)

**Filter**: RSI(14) must be > 70 at 1800 ORB time.
- RSI calculated on 5-minute closes using Wilder's smoothing
- `rsi_at_orb > 70` (note: column name in database is `rsi_at_orb` not `rsi_at_1800`)

This section is the **truth anchor**.

## 4. Variants (RR / timing only)

### 1800 ORB RR=1.5 (ONLY VARIANT)
- RR=1.5: +0.222R (only survives +25% stress)

No other RR levels tested yet.

## 5. Status
- **BASELINE_MARGINAL**: RR=1.5 (only survives +25% stress, weaker edge)
- Date locked: 2026-01-27
- Evidence file(s): `analysis/baseline_strategy_revalidation.py`, `test_all_7_strategies.py`
- Database ID: 24

## 6. Conditional Extensions (OPTIONAL)

### 5min Confirmation Filter
- Status: **Phase 2 FAILED** (does NOT help)
- Finding: RSI filter already captures momentum, 5min confirmation adds no value
- File: `analysis/research_5min_filter_phase2_walkforward.py`
- Conclusion: DO NOT USE 5min filter with RSI strategies

## 7. What This Family IS NOT
- NOT a pure momentum strategy (trades overbought conditions, not momentum continuation)
- NOT a mean reversion strategy (still trades WITH the ORB breakout, not against it)
- NOT applicable at other times (specifically 1800 ORB only)
- NOT based on session types (L1/L2/L3/L4 - RSI is indicator-based, not session-based)

## 8. Open Questions
- Why RSI > 70 specifically? (would RSI > 65 or > 75 work better?)
- Do higher RR levels (2.0, 2.5, 3.0) work with RSI filter?
- Does RSI < 30 (oversold) work for opposite direction?
- Is there a regime where RSI stops working? (trending vs range-bound)
- Does RSI work at other ORB times (0900, 1000, 1100)?
- Can we combine RSI with session types (L4) for stronger edge?

---

**Last Updated**: 2026-01-27
**Family Owner**: MGC Gold Trading System
**Validation Status**: USE WITH CAUTION (marginal edge, smaller position size recommended)
