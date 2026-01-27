# Asia Bias Filter Replication Results - Honest Verdict

**Date:** 2026-01-26
**Test:** Replication of myprojectx2 Asia Bias Filter on MPX2_fresh MGC data
**Data Period:** 2024-01-02 to 2026-01-12 (524 days, 2.03 years)
**Philosophy:** Replication first. No modifications. Honest reporting.

---

## Executive Summary

**VERDICT: PARTIAL REPLICATION (+34.5% improvement, NOT statistically significant)**

**myprojectx2 Claim:** +50-100% improvement (e.g., 1000 ORB: +0.40R → +1.13R)

**Our MGC Results:**
- **Baseline**: 523 trades, 60.2% WR, +0.205R
- **Asia Bias Filter**: 367 trades, 63.8% WR, +0.275R
- **Improvement**: **+0.071R (+34.5%)**
- **P-value**: 0.2867 (NOT statistically significant)
- **Cohen's d**: 0.073 (very small effect size)

**Status:** Shows improvement but FAILS statistical significance test. Smaller effect than claimed.

---

## Test Configuration

### Exact Replication Logic (from myprojectx2)

**Market State Classification:**
```
ABOVE: price > prior_day_asia_high -> Trade UP breaks only
BELOW: price < prior_day_asia_low -> Trade DOWN breaks only
INSIDE: asia_low < price < asia_high -> Trade both directions (baseline)
```

**Critical Implementation Detail:**
- For morning ORBs (0900, 1000, 1100): Use **PRIOR DAY** Asia high/low
- Reason: At 10:00, current day's Asia session (09:00-17:00) is still ongoing
- Logic: "Is price above YESTERDAY's Asia high?" → Bullish continuation

**Tested Setup:**
- 1000 ORB (10:00-10:05)
- RR = 1.0 (baseline outcomes from daily_features)
- No stop mode optimization (FULL/HALF not tested)
- No other filters combined

---

## Results: Full Breakdown

### Market State Distribution

| State | Trades | Percentage | Description |
|-------|--------|------------|-------------|
| **ABOVE** | 210 | 40.2% | Price > prior day Asia high |
| **INSIDE** | 182 | 34.8% | Price between prior Asia high/low |
| **BELOW** | 131 | 25.0% | Price < prior day Asia low |

**Good variation** - filter has meaningful segmentation.

---

### Performance by Market State

#### BASELINE (No Filter)

| Metric | Value |
|--------|-------|
| Trades | 523 |
| Win Rate | 60.2% |
| Avg R | **+0.205R** |
| Total R | +107.0R |

---

#### ABOVE (price > prior_day_asia_high, UP breaks only)

| Metric | Value | vs Baseline |
|--------|-------|-------------|
| Trades | 105 | - |
| Win Rate | 65.7% | +5.5% |
| Avg R | **+0.314R** | **+0.110R** |
| Total R | +33.0R | - |

**VERDICT: ✓ WORKS**
- Strongest market state
- +0.110R improvement over baseline
- 65.7% WR (5.5% better than baseline)

---

#### BELOW (price < prior_day_asia_low, DOWN breaks only)

| Metric | Value | vs Baseline |
|--------|-------|-------------|
| Trades | 80 | - |
| Win Rate | 57.5% | -2.7% |
| Avg R | **+0.150R** | **-0.055R** |
| Total R | +12.0R | - |

**VERDICT: ✗ WORSE**
- Weaker market state
- -0.055R degradation vs baseline
- Still profitable (+0.150R) but worse than trading both directions

---

#### INSIDE (asia_low < price < asia_high, both directions)

| Metric | Value | vs Baseline |
|--------|-------|-------------|
| Trades | 182 | - |
| Win Rate | 65.4% | +5.2% |
| Avg R | **+0.308R** | **+0.103R** |
| Total R | +56.0R | - |

**VERDICT: ✓ BETTER**
- Surprisingly strong performance
- +0.103R improvement over baseline
- Trading both directions when price is INSIDE prior Asia range works well

---

### ASIA BIAS FILTER (ABOVE + BELOW combined)

| Metric | Value | vs Baseline |
|--------|-------|-------------|
| Trades | 367 | -156 (-29.8%) |
| Win Rate | 63.8% | +3.5% |
| Avg R | **+0.275R** | **+0.071R** |
| Total R | +101.0R | -6.0R |
| Improvement | **+34.5%** | - |

**Statistical Tests:**
- T-statistic: 1.07
- P-value: **0.2867** (> 0.05, NOT significant)
- Cohen's d: 0.073 (very small effect size)

**VERDICT: ⚠️ PARTIAL REPLICATION**
- Shows +34.5% improvement (decent)
- BUT NOT statistically significant (p=0.29)
- Effect size is small (Cohen's d=0.073)
- Trades reduced by 30% for marginal gain

---

## Critical Findings

### 1. INSIDE Category Outperforms

**Unexpected Result:** INSIDE (both directions) performs BETTER than baseline (+0.103R).

**Possible Interpretations:**
- When price is between prior Asia high/low, ORBs have cleaner breakouts
- Consolidation setup (price hasn't committed to direction yet)
- More "fair value" trading opportunities

**Implication:** Filtering OUT INSIDE trades may be wrong approach for MGC.

---

### 2. BELOW Category Underperforms

**Asymmetry:** ABOVE works (+0.110R), BELOW doesn't (-0.055R).

**Possible Explanations:**
- MGC has upward drift (gold in uptrend 2024-2026)
- Bearish setups less reliable than bullish in gold
- Sample size for BELOW smaller (80 trades vs 105 for ABOVE)

**Implication:** If implementing filter, may want ABOVE-only (skip BELOW).

---

### 3. Statistical Significance Missing

**P-value = 0.2867** means 28.67% chance this improvement is random noise.

**Standard Threshold:** p < 0.05 (5% chance of randomness)

**Our Result:** Fails by ~6x margin

**Possible Reasons:**
1. Sample size (367 filtered trades) may not be enough
2. True effect is smaller than myprojectx2's +50-100%
3. Instrument differences (NQ vs MGC)
4. RR target differences (myprojectx2 uses RR=8.0, we test RR=1.0)
5. Stop mode differences (they use FULL/HALF, we don't test that)

---

## Comparison to myprojectx2 Claim

| Metric | myprojectx2 Claim | Our MGC Result | Match? |
|--------|-------------------|----------------|--------|
| **Improvement** | +50-100% | **+34.5%** | ⚠️ PARTIAL |
| **Example** | +0.40R → +1.13R | +0.205R → +0.275R | ⚠️ SMALLER |
| **Statistical Significance** | Not reported | **p=0.29 (FAIL)** | ✗ MISSING |
| **Best Market State** | ABOVE/BELOW | **ABOVE (+0.110R)** | ✓ MATCHES |
| **Filter Implementation** | ABOVE + BELOW | ABOVE + BELOW | ✓ MATCHES |

**Key Difference:** myprojectx2 shows +50-100% improvement, we show +34.5% with NO statistical significance.

---

## Possible Reasons for Discrepancy

### 1. RR Target Differences

**myprojectx2:**
- Best setup: 1000 ORB **RR=8.0**
- Asia_bias=ABOVE: +1.131R

**Our Test:**
- Used RR=1.0 outcomes (baseline from daily_features)
- Asia_bias filter: +0.275R

**Hypothesis:** Asia Bias filter may work BETTER with higher RR targets (6.0-8.0).

**Test Needed:** Backtest 1000 ORB with RR=6.0 or 8.0, then apply Asia Bias filter.

---

### 2. Stop Mode Differences

**myprojectx2:**
- 10AM uses **FULL stops** (from asia_session_complete_analysis.md)
- Best setup: 10AM 6R FULL extended

**Our Test:**
- Used outcomes regardless of stop mode
- Did NOT optimize FULL vs HALF

**Hypothesis:** Asia Bias filter may work BETTER with FULL stops (wider initial stop).

**Test Needed:** Backtest 1000 ORB with FULL stops, then apply Asia Bias filter.

---

### 3. Instrument Differences

**myprojectx2:** NQ (Nasdaq E-mini) + MGC tested

**Our Test:** MGC only

**Observation:**
- MGC may have different microstructure than NQ
- Gold (commodity) vs Tech index (equities)
- Upward drift in MGC 2024-2026 (bullish period)

**Hypothesis:** Asia Bias filter may work BETTER on NQ than MGC.

---

### 4. Price Measurement Differences

**myprojectx2:** Likely uses actual price at ORB open (10:00 bar open price)

**Our Test:** Uses ORB midpoint (orb_high + orb_low) / 2 as proxy

**Hypothesis:** Using exact 10:00 open price may give cleaner classification.

**Test Needed:** Re-run with actual 10:00 bar open price (requires bars_1m query).

---

### 5. Time Period Differences

**myprojectx2:** 2024-01-02 to 2026-01-10 (2.03 years)

**Our Test:** 2024-01-02 to 2026-01-12 (2.03 years, nearly identical)

**Observation:** Time periods are very similar, unlikely to explain difference.

---

## Honest Verdict

### What We Found

**Positive:**
1. ✓ Asia Bias filter shows +34.5% improvement (+0.071R)
2. ✓ ABOVE market state works well (+0.110R improvement)
3. ✓ Win rate improves (63.8% vs 60.2%)
4. ✓ Trade frequency reduced by 30% (156 fewer trades, more selective)

**Negative:**
1. ✗ NOT statistically significant (p=0.29, need p<0.05)
2. ✗ Effect size is small (Cohen's d=0.073)
3. ✗ Smaller improvement than myprojectx2 claim (+34.5% vs +50-100%)
4. ✗ BELOW market state WORSE than baseline (-0.055R)
5. ✗ INSIDE market state outperforms both ABOVE and BELOW (unexpected)

### Classification

**PARTIAL REPLICATION:**
- Shows improvement direction (✓)
- Effect size smaller than claimed (⚠️)
- Statistical significance missing (✗)

**NOT a full replication** of myprojectx2's +50-100% improvement.

---

## Recommended Next Steps

### OPTION 1: Test with Higher RR Targets (MOST LIKELY)

**Hypothesis:** Asia Bias filter works BETTER with RR=6-8 (myprojectx2's setup).

**Action:**
1. Backtest 1000 ORB with RR=6.0 and RR=8.0
2. Apply Asia Bias filter to those results
3. Check if improvement increases to +50-100%

**Expected:** May find +0.40R → +1.13R improvement at higher RR.

**Priority:** HIGH (most likely explanation for discrepancy)

---

### OPTION 2: Test ABOVE-Only Filter

**Hypothesis:** ABOVE works (+0.110R), BELOW doesn't (-0.055R). Use ABOVE-only.

**Action:**
1. Backtest filter that trades ABOVE UP breaks + INSIDE trades
2. Skip BELOW DOWN breaks entirely
3. Compare to baseline

**Expected:** May improve results by avoiding BELOW losses.

**Priority:** MEDIUM (quick test, low risk)

---

### OPTION 3: Test with FULL Stops

**Hypothesis:** FULL stops (wider) work better with Asia Bias filter.

**Action:**
1. Implement FULL vs HALF stop logic
2. Test 1000 ORB with FULL stops
3. Apply Asia Bias filter

**Expected:** May match myprojectx2's results more closely.

**Priority:** MEDIUM (infrastructure needed)

---

### OPTION 4: Use Exact 10:00 Open Price

**Hypothesis:** ORB midpoint is imprecise, use actual 10:00 bar open.

**Action:**
1. Query bars_1m for 10:00 bar open price
2. Classify market state using exact price
3. Re-run backtest

**Expected:** May get cleaner market state classification.

**Priority:** LOW (marginal improvement expected)

---

### OPTION 5: Accept Partial Replication

**Decision:** +34.5% improvement (even if not significant) may be worth using.

**Risk-Adjusted Approach:**
1. Use Asia Bias filter in live trading
2. Track results over 30-60 trades
3. If goes negative → kill filter
4. If stays positive → continue using

**Expected:** Real-world validation will determine if filter is real or noise.

**Priority:** LOW (risky without statistical significance)

---

## What NOT To Do

### ❌ DO NOT "Optimize" the Filter

**Temptation:** Adjust thresholds, add parameters, combine with other filters.

**Why NOT:**
- Destroys replication
- Introduces overfitting
- Loses connection to myprojectx2's validated work

**Correct Approach:** Test EXACT replication first, THEN consider modifications.

---

### ❌ DO NOT Ignore Statistical Significance

**Temptation:** "34.5% improvement is good enough, let's use it!"

**Why NOT:**
- p=0.29 means 29% chance it's random noise
- May disappear in future data
- Risk of false positive

**Correct Approach:** Either get p<0.05 OR forward-test carefully.

---

### ❌ DO NOT Mix with Other Filters Yet

**Temptation:** Combine Asia Bias + volatility regimes + time-decay.

**Why NOT:**
- Can't isolate what works
- Interaction effects unknown
- Destroys replication

**Correct Approach:** Test Asia Bias in isolation first.

---

## Conclusions

### Primary Conclusion

**Asia Bias Filter shows +34.5% improvement on MGC 1000 ORB but is NOT statistically significant.**

This is a **PARTIAL replication** of myprojectx2's +50-100% claim.

---

### Secondary Findings

1. **ABOVE market state WORKS** (+0.110R improvement)
2. **BELOW market state FAILS** (-0.055R degradation)
3. **INSIDE market state OUTPERFORMS** (+0.103R improvement, unexpected)
4. **Asymmetry exists** (bullish setups better than bearish for MGC 2024-2026)

---

### Most Likely Explanation for Discrepancy

**RR Target Differences:**
- myprojectx2 uses RR=6-8 (large targets)
- We tested RR=1.0 (baseline outcomes)
- Asia Bias filter likely amplifies edge at higher RR targets

**Next Step:** Test 1000 ORB with RR=6.0 or 8.0 + Asia Bias filter.

---

### Honest Assessment

**Is the Asia Bias Filter real?**
- ✓ Shows improvement direction (+34.5%)
- ✓ ABOVE market state works (+0.110R)
- ✗ NOT statistically significant (p=0.29)
- ✗ Smaller than myprojectx2 claim

**Should we use it?**
- NOT YET (needs more validation)
- Test with higher RR targets first
- Get statistical significance OR forward-test carefully

**Trust level:** MEDIUM (suggestive but not conclusive)

---

## Data Quality Notes

**Sample Size:** 523 trades (2.03 years) is decent but not huge.

**Market Period:** 2024-2026 includes gold uptrend (bullish bias).

**Data Integrity:** All trades from daily_features table (validated source).

**Zero-Lookahead:** Uses PRIOR DAY Asia range (no lookahead bias).

---

## Appendix: Statistical Details

### T-Test Results

```
Baseline R-values: 523 trades, mean=+0.205R, std=1.00R
Filtered R-values: 367 trades, mean=+0.275R, std=1.02R

T-statistic: 1.07
P-value: 0.2867
Degrees of freedom: 888

Conclusion: FAIL to reject null hypothesis (no difference)
```

### Effect Size (Cohen's d)

```
Cohen's d = (mean_filtered - mean_baseline) / pooled_std
Cohen's d = (0.275 - 0.205) / 0.96
Cohen's d = 0.073

Classification: VERY SMALL effect (d < 0.2)
```

### Confidence Interval (95%)

```
Delta Avg R: +0.071R
95% CI: [-0.059R, +0.201R]

Interpretation: True effect could be anywhere from -0.059R to +0.201R
                Includes ZERO (no effect) within confidence interval
```

---

**End of Asia Bias Replication Results**
