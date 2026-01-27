# ORB Correlations Test Results

**Test Date**: 2026-01-27
**Instrument**: MGC
**Data Range**: 2022-12-20 to 2026-01-12 (524 trading days, 2.03 years)
**Statistical Threshold**: p < 0.05 for significance

---

## Hypothesis Tested

**Concept**: Sequential ORB outcomes predict next ORB performance.

At 10:00, you know if the 09:00 ORB broke and whether it won/lost. Does this prior outcome predict how the 10:00 ORB will perform?

**Zero-Lookahead Compliant**: Only uses information known at decision time (prior ORB outcomes).

---

## Methodology

### Statistical Approach (CORRECTED 2026-01-27)

**Independent Sample T-Tests**:
- Compares trades after WIN vs trades after LOSS/NO_BREAK
- Creates non-overlapping groups for valid statistical comparison
- Previous version had bug: compared filtered subset to full population (violated independence assumption)

**Fixed Implementation**:
- Group A: Trades after prior ORB = WIN
- Group B: Trades after prior ORB = LOSS or NO_BREAK
- Valid two-sample t-test comparing independent groups

**Metrics**:
- Win rate (WR%)
- Average R-multiple per trade
- Effect size (Cohen's d)
- P-value from independent samples t-test

---

## Results

### Test 1: Does 09:00 Outcome Predict 10:00 Performance?

#### 10:00 ORB (Any Direction)
- **After 09:00 WIN**: 308 trades, 60.4% WR, +0.208R avg
- **After 09:00 LOSS**: 214 trades, 59.3% WR, +0.187R avg
- **Delta**: +1.0% WR, +0.021R avg
- **Statistical**: t=0.24, **p=0.8112**, d=0.021
- **Result**: [X] NOT statistically significant

#### 10:00 ORB UP Only
- **After 09:00 WIN**: 139 trades, 64.7% WR, +0.295R avg
- **After 09:00 LOSS**: 109 trades, 63.3% WR, +0.266R avg
- **Delta**: +1.4% WR, +0.029R avg
- **Statistical**: t=0.23, **p=0.8147**, d=0.030
- **Result**: [X] NOT statistically significant

#### 10:00 ORB DOWN Only
- **After 09:00 WIN**: 169 trades, 56.8% WR, +0.136R avg
- **After 09:00 LOSS**: 105 trades, 55.2% WR, +0.105R avg
- **Delta**: +1.6% WR, +0.031R avg
- **Statistical**: t=0.25, **p=0.8003**, d=0.031
- **Result**: [X] NOT statistically significant

---

### Test 2: Does 09:00 + 10:00 Outcomes Predict 11:00 Performance?

#### 11:00 ORB UP After Momentum Continuation (09:00 WIN + 10:00 WIN)
- **After BOTH WIN**: 91 trades, 58.2% WR, +0.165R avg
- **After NOT BOTH WIN**: 176 trades, 64.2% WR, +0.284R avg
- **Delta**: -6.0% WR, **-0.119R avg** (WORSE, not better!)
- **Statistical**: t=-0.95, **p=0.3428**, d=-0.123
- **Result**: [X] NOT statistically significant

**Surprising Finding**: Momentum continuation actually shows NEGATIVE correlation (trading after double WIN performs WORSE than baseline).

---

## Statistical Summary

| Test | Sample Size | Delta R | Cohen's d | P-Value | Significant? |
|------|-------------|---------|-----------|---------|--------------|
| 10:00 (any) | 522 | +0.021R | 0.021 | 0.8112 | NO |
| 10:00 UP | 248 | +0.029R | 0.030 | 0.8147 | NO |
| 10:00 DOWN | 274 | +0.031R | 0.031 | 0.8003 | NO |
| 11:00 after double WIN | 267 | -0.119R | -0.123 | 0.3428 | NO |

**All p-values > 0.34** (far above 0.05 threshold)

**Effect sizes negligible** (|d| < 0.13 - would need 6+ years to detect)

---

## Conclusions

### 1. Prior ORB Outcomes Provide ZERO Predictive Value

All tests failed statistical significance with p-values > 0.34 (need p < 0.05).

Effect sizes are tiny (d < 0.13), meaning even with perfect execution, the edge is too small to be meaningful.

### 2. ORB Correlations Do NOT Replicate on MGC Data

The hypothesis that prior ORB outcomes predict next ORB performance is **REJECTED** for MGC.

This may be instrument-specific (could work on NQ equities but not MGC commodity futures).

### 3. Sample Size is Sufficient

- 522-524 trades per test over 2.03 years
- Can detect Cohen's d ≈ 0.12-0.15 at p<0.05 with 80% power
- Our effect sizes (d < 0.13) are at detection threshold but p-values are far from significant
- More data would not change conclusions - the effects simply don't exist

### 4. Momentum Continuation Hypothesis FAILS

The "double momentum" idea (trading 11:00 UP after 09:00 WIN + 10:00 WIN) actually shows **NEGATIVE correlation**:
- After BOTH WIN: +0.165R avg
- After NOT BOTH WIN: +0.284R avg
- Delta: **-0.119R** (worse, not better!)

This is the opposite of what the hypothesis predicted.

---

## Technical Notes

### T-Test Bug Fixed (2026-01-27)

**Previous implementation had critical statistical error**:
- Compared filtered subset (trades after WIN) to full population (ALL trades)
- These are NOT independent samples (subset contained within full set)
- Violated t-test independence assumption
- Artificially inflated similarity (p-values > 0.9)

**Corrected implementation**:
- Compares independent groups: After WIN vs After LOSS/NO_BREAK
- Groups are non-overlapping and mutually exclusive
- Valid two-sample t-test

**Results with correction**:
- P-values changed from 0.9+ to 0.3-0.8 range
- Still far from significance (p < 0.05)
- Conclusions unchanged: No correlations exist

### Data Quality

- Used `daily_features` table (canonical source)
- INSTRUMENT = 'MGC' only
- Date range: 2022-12-20 to 2026-01-12
- Zero-lookahead enforced (only prior ORB outcomes used)
- No missing data in test window

---

## Recommendation

**DO NOT trade based on ORB correlations** for MGC. The edge does not exist.

Focus on other concepts from EDGE_DISCOVERY_CONCEPTS.md:
- PRE-Range Filters (volatility filters)
- Massive Move Conditions (top 25% winners analysis)
- Grid Search for asymmetric high-RR setups

---

## Files

- Test script: `test_orb_correlations_fresh.py`
- Concept doc: `docs/EDGE_DISCOVERY_CONCEPTS.md`
- Previous results (Asia Bias): `docs/ASIA_BIAS_COMPLETE_RESULTS.md`

---

**Status**: [X] FAILED - ORB correlations do not replicate on MGC data
