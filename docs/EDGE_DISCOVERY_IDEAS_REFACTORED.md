# Edge Discovery Ideas - Refactored for MPX2_fresh

**Date:** 2026-01-27
**Source:** Ideas extracted from `/check` folder (old research files)
**Status:** Concepts for testing, NOT validated yet
**Philosophy:** These are IDEAS, not truth. Test rigorously before trusting.

---

## Overview

This document extracts promising edge discovery concepts from historical research and refactors them for our current MPX2_fresh infrastructure. All ideas need validation with proper statistical testing before use.

**Key Files Reviewed:**
- `FIND_MASSIVE_MOVE_CONDITIONS.py` - Conditions for massive winners
- `ULTIMATE_UNICORN_FINDER.py` - Comprehensive grid search methodology
- `UNICORN_SETUPS_CORRECTED.md` - Validated high-RR setups
- `UNICORN_TRADES_INVENTORY.md` - Catalog of rare high-edge setups
- `TRADING_PLAYBOOK.md` - ORB correlation strategies

---

## Category 1: Massive Move Prediction (Top 25% Winners)

###  Concept: What Makes a Winner MASSIVE?

**Original Idea** (from FIND_MASSIVE_MOVE_CONDITIONS.py):
- Analyze winners by max_favorable_r (max excursion before exit)
- Compare top 25% (massive) vs bottom 75% (regular) vs losers
- Find conditions that predict BIG moves, not just base hits

**Conditions to Test:**

1. **ORB Size vs ATR Ratio**
   - Hypothesis: Tight ORBs (small size vs ATR) create explosive moves
   - Filter: `orb_size / atr_20 < threshold` (e.g., < 0.15)
   - Rationale: Compressed volatility leads to expansion

2. **Entry Delay (Speed)**
   - Hypothesis: Fast entries (< 2 minutes after ORB) catch momentum
   - Filter: `entry_delay_minutes <= 2`
   - Rationale: Immediate breaks signal strong conviction

3. **Asia Range Expansion**
   - Hypothesis: Larger Asia ranges predict bigger ORB moves
   - Filter: `asia_range > median(asia_range)` or `> 75th percentile`
   - Rationale: High volatility sessions continue momentum

4. **Direction Bias**
   - Hypothesis: UP breaks may produce larger moves than DOWN breaks (MGC uptrend 2024-2026)
   - Filter: Trade UP only
   - Rationale: Instrument-specific trend bias

5. **Fast Winners (Bars to Target)**
   - Hypothesis: Trades that hit target quickly (< 10 bars = 10 minutes) predict quality setups
   - Filter: Backtest and identify conditions where `bars_to_exit <= 10`
   - Rationale: Fast moves indicate strong momentum, not just drift

**Refactored Test Script Idea:**
```python
# analyze_massive_moves.py
#
# 1. Query daily_features for ALL ORB trades with outcomes
# 2. Simulate full execution with RR=10.0 on 1-minute bars
# 3. Track max_favorable_r for each trade
# 4. Segment into massive (top 25%) vs regular (bottom 75%) vs losers
# 5. Compare conditions: orb_size_vs_atr, entry_delay, asia_range, direction
# 6. Output filters that increase "massive mover" probability by 20%+
```

**Database Schema We Have:**
- `daily_features` table has: `asia_high`, `asia_low`, `london_high`, `london_low`, `orb_*_high`, `orb_*_low`
- `bars_1m` table has: 1-minute OHLCV data for full execution simulation
- We can calculate: `orb_size`, `atr_20`, `asia_range`, `london_range`

**What We Need to Add:**
- `entry_delay_minutes` - Time from ORB close to first break (requires 1m bar scan)
- `max_favorable_r` - Max R-multiple reached before exit (requires full simulation)
- `bars_to_exit` - Number of 1m bars to reach target (requires simulation)

---

## Category 2: Grid Search for Unicorn Setups

### Concept: Comprehensive Parameter Sweep

**Original Idea** (from ULTIMATE_UNICORN_FINDER.py):
- Test EVERY possible ORB configuration systematically
- Dimensions: Time (24 hours), Duration (5/10/15/30/60min), SL mode (FULL/HALF/QUARTER), RR (1-10)
- Extended scan windows (until 09:00 next day for all ORBs)
- Strict filters: avg_r >= 0.25, annual_r >= 40R, min 100 trades

**Parameters to Test:**

| Dimension | Values |
|-----------|--------|
| **ORB Time** | Every hour 00:00-23:00 + 00:30 (25 times) |
| **ORB Duration** | 5, 10, 15, 30, 60 minutes |
| **SL Mode** | FULL (opposite edge), HALF (midpoint), QUARTER (25% into range) |
| **RR Target** | 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0 |
| **Scan Window** | Until 09:00 next day (capture overnight moves) |

**Total Configurations:** 25 times × 5 durations × 3 SL modes × 10 RR targets = **3,750 configurations**

**Filters for "Unicorn" Qualification:**
1. **Frequency**: >= 100 trades over 2 years (7%+ of days)
2. **Profitability**: avg_r >= 0.25 (strong positive expectancy)
3. **Annual Returns**: >= 40R/year (meaningful income)
4. **Win Rate or Payoff**: WR >= 25% OR avg_r >= 0.35 (low WR needs high payoff)

**Refactored Test Script Idea:**
```python
# grid_search_unicorns.py
#
# Use multiprocessing (8 cores) to test 3,750 configurations in parallel
# For each config:
#   1. Query bars_1m to form ORB dynamically
#   2. Detect breakout direction
#   3. Simulate trade with specified SL mode and RR target
#   4. Track until 09:00 next day (extended scan window)
#   5. Record: trades, wins, avg_r, annual_r, median_hold_hours
#
# Output: CSV with all profitable setups ranked by avg_r
# Checkpoint every 250 configs (allows early stopping)
```

**Key Innovation: Extended Scan Windows**

**Problem with Old System:**
- 23:00 ORB scanned only until 00:30 (85 minutes)
- 00:30 ORB scanned only until 02:00 (85 minutes)
- Missed targets that hit 4-8 hours later during Asia open

**Solution:**
- Scan ALL ORBs until 09:00 next day
- Captures overnight moves that develop slowly
- Especially important for high RR targets (6R-10R)

**Expected Results:**
- Find 20-50 "unicorn" setups (avg_r >= 0.25)
- Validate known winners (2300 ORB, 1000 ORB with high RR)
- Discover NEW profitable times/durations/SL modes

---

## Category 3: ORB Correlation Edges

### Concept: Sequential ORB Dependencies

**Original Idea** (from TRADING_PLAYBOOK.md):
- Use completed ORB outcomes as filters for next ORB
- Zero-lookahead: Only use information available at decision time
- Best correlation: 10:00 UP after 09:00 WIN (57.9% WR, +0.16R)

**Validated Correlations to Test on MGC:**

1. **10:00 UP after 09:00 WIN**
   - Condition: 09:00 ORB broke and hit target (WIN)
   - Trade: 10:00 ORB UP breaks only
   - Expected: 57-58% WR (vs 51-55% baseline)
   - Rationale: Momentum continuation

2. **11:00 UP after 09:00 WIN + 10:00 WIN**
   - Condition: Both 09:00 AND 10:00 were WIN trades (same direction)
   - Trade: 11:00 ORB UP breaks only
   - Expected: 57-58% WR
   - Rationale: Strong 3-level momentum

3. **11:00 DOWN after 09:00 LOSS + 10:00 WIN**
   - Condition: 09:00 LOSS, then 10:00 WIN
   - Trade: 11:00 ORB DOWN breaks only
   - Expected: 57-58% WR
   - Rationale: Reversal after failed start

4. **18:00 (Any Direction) after Asia Expansion**
   - Condition: Asia session HIGH and LOW both exceeded prior day's range
   - Trade: 18:00 ORB (both directions)
   - Expected: Higher WR than baseline
   - Rationale: Expanded range indicates high volatility continuation

**Refactored Test Script Idea:**
```python
# test_orb_correlations.py
#
# For each trading day:
#   1. Simulate 09:00 ORB → Record outcome (WIN/LOSS)
#   2. Simulate 10:00 ORB → Filter by 09:00 outcome → Record
#   3. Simulate 11:00 ORB → Filter by 09:00 + 10:00 outcome → Record
#   4. Calculate Asia session stats (expanded, consolidation, trending)
#   5. Simulate 18:00 ORB → Filter by Asia session type → Record
#
# Compare filtered performance vs baseline
# Statistical test: t-test, p<0.05 required
```

**Database Schema We Have:**
- `daily_features.orb_0900_outcome` - WIN/LOSS/NONE
- `daily_features.orb_1000_outcome` - WIN/LOSS/NONE
- `daily_features.orb_1100_outcome` - WIN/LOSS/NONE
- `daily_features.asia_high`, `asia_low` - Session ranges

**What We Need to Add:**
- Session type classifier: `asia_session_type` (EXPANDED, CONSOLIDATION, TRENDING, CHOPPY)
- Prior day comparison: `asia_high > prior_asia_high AND asia_low < prior_asia_low` = EXPANDED

---

## Category 4: PRE Block Filters

### Concept: Use Known Information at ORB Open

**Original Idea** (from TRADING_PLAYBOOK.md):
- PRE_ASIA (07:00-09:00 range) known at 09:00 ORB
- PRE_LONDON (17:00-18:00 range) known at 18:00 ORB
- PRE_NY (23:00-00:30 range) known at 00:30 ORB

**Validated Filters:**

1. **09:00 ORB + PRE_ASIA > 50 ticks**
   - Filter: Only trade 09:00 if PRE_ASIA range > 50 ticks (5.0 points)
   - Expected: 52-53% WR (vs 48-49% without filter)
   - Rationale: Volatility present before session open predicts continuation

2. **09:00 ORB + PRE_ASIA < 30 ticks → SKIP**
   - Filter: Do NOT trade 09:00 if PRE_ASIA range < 30 ticks (3.0 points)
   - Expected: Only 40-41% WR (losing filter)
   - Rationale: Low pre-market volatility predicts chop

3. **11:00 UP + PRE_ASIA > 50 ticks**
   - Filter: Trade 11:00 UP breaks if PRE_ASIA > 50 ticks
   - Expected: 55% WR (vs 50% baseline)
   - Rationale: Strong early activity favors continued upward momentum

4. **18:00 DOWN + PRE_LONDON > 40 ticks**
   - Filter: Trade 18:00 DOWN breaks if PRE_LONDON > 40 ticks
   - Expected: 53-54% WR (vs 51-52% baseline)
   - Rationale: High pre-London activity favors DOWN breaks (retracement)

**Refactored Test Script Idea:**
```python
# test_pre_block_filters.py
#
# For each ORB time:
#   1. Calculate PRE block range (07:00-09:00 for 09:00 ORB, etc.)
#   2. Test multiple thresholds: 20, 30, 40, 50, 60 ticks
#   3. Compare performance:
#      - Trades with PRE > threshold
#      - Trades with PRE < threshold
#      - Baseline (no filter)
#   4. Find optimal threshold (maximizes avg_r AND improves WR by 2%+)
#
# Statistical test: t-test, p<0.05 required
```

**Database Schema We Have:**
- `bars_1m` table - Can calculate PRE blocks on any date

**What We Need to Add:**
- PRE block features to `daily_features`:
  - `pre_asia_range` (07:00-09:00)
  - `pre_london_range` (17:00-18:00)
  - `pre_ny_range` (23:00-00:30)

---

## Category 5: Multi-Liquidity Cascade Patterns

### Concept: Sequential Liquidity Sweeps

**Original Idea** (from UNICORN_TRADES_INVENTORY.md):
- Sequential sweep pattern: Asia → London → NY
- Each level traps participants, forced liquidations compound
- Requires gap > 9.5 points between levels (15× performance multiplier!)
- Entry at 23:00 after London level swept with acceptance failure

**Pattern Components:**

1. **Asia Session (09:00-17:00)**: Establishes day's range
2. **London Session (18:00-23:00)**: Sweeps Asia high or low (first sweep)
3. **NY Futures Open (23:00)**: Sweeps London level (second sweep)
4. **Acceptance Failure**: Price fails to hold above/below swept level within 3 bars
5. **Gap Size**: Distance between Asia and London levels predicts outcome

**Validated Edge:**
- **Baseline Cascades**: +1.95R avg (9.3% frequency)
- **With Large Gap Filter (>9.5pts)**: +5.36R avg (43% of cascades)

**Refactored Test Script Idea:**
```python
# test_cascade_patterns.py
#
# For each trading day:
#   1. Identify Asia high/low (09:00-17:00)
#   2. Check if London (18:00-23:00) swept Asia level
#   3. Calculate gap between Asia level and London level
#   4. At 23:00: Check if London level re-swept
#   5. Detect acceptance failure (price closes back below/above within 3 bars)
#   6. If all conditions met → Entry at swept level
#   7. Stop at second sweep high/low
#   8. Target at opposite Asia level
#   9. Track performance by gap size bins
#
# Compare:
#   - All cascades vs baseline
#   - Cascades with gap > 9.5pts vs gap < 9.5pts
#   - Statistical test for gap threshold optimality
```

**Database Schema We Have:**
- `daily_features.asia_high`, `asia_low`
- `daily_features.london_high`, `london_low`
- `bars_1m` - For precise sweep detection and entry/exit simulation

**What We Need to Add:**
- Cascade detection logic (sweep identification)
- Gap size calculation
- Acceptance failure detection (3-bar rule)

**Critical Notes:**
- **Rare** (9.3% of days = 2-3 per month)
- **High variance** (19-27% WR, large payoffs)
- **Position sizing**: 0.10-0.25% risk ONLY (don't overtrade!)
- **Not suitable for daily trading** (too infrequent)

---

## Category 6: Asymmetric High-RR Setups

### Concept: Low Win Rate, Huge Payoffs

**Original Idea** (from UNICORN_SETUPS_CORRECTED.md):
- Accept low win rates (15-30%) if RR targets are massive (6R-10R)
- Extended scan windows (until 09:00 next day) required
- Tight ORB filters to control risk

**Validated Asymmetric Setups:**

1. **1000 ORB - RR=8.0 (FULL SL)**
   - Win Rate: 15.3% (only 1 in 7 wins!)
   - Avg R: +0.378R
   - Annual R: ~+98R/year
   - Filter: ORB size ≤ 10 points (100 ticks)
   - Rationale: Small ORBs → tight risk, 8R targets capture explosive moves

2. **0900 ORB - RR=6.0 (FULL SL)**
   - Win Rate: 17.1%
   - Avg R: +0.198R
   - Annual R: ~+51R/year
   - Rationale: Early Asia breakouts develop overnight

3. **0030 ORB - RR=3.0 (HALF SL)**
   - Win Rate: 31.3%
   - Avg R: +0.254R
   - Annual R: ~+66R/year
   - Filter: ORB size ≤ 0.112 × ATR(20)
   - Rationale: NY session power with tighter stop

**Key Innovation: HALF SL vs FULL SL**

**Night ORBs (23:00, 00:30):**
- HALF SL (stop at midpoint) outperforms FULL SL by 2-3×
- Example: 2300 ORB HALF SL RR=1.5: +0.403R vs FULL SL RR=1.0: +0.165R
- Rationale: Night moves are smaller, tighter stops prevent whipsaw

**Day ORBs (09:00, 10:00, 11:00):**
- FULL SL (stop at opposite edge) works better
- Rationale: Day moves are larger, need room for pullbacks

**Refactored Test Script Idea:**
```python
# test_asymmetric_high_rr.py
#
# For each ORB time (0900, 1000, 1100, 1800, 2300, 0030):
#   For RR in [3.0, 4.0, 5.0, 6.0, 8.0, 10.0]:
#     For SL_mode in ['FULL', 'HALF']:
#       1. Simulate full execution on bars_1m
#       2. Scan until 09:00 next day (extended window)
#       3. Track: trades, win_rate, avg_r, annual_r
#       4. Apply ORB size filter (test thresholds: 0.10-0.15 × ATR)
#       5. Record best configuration per ORB time
#
# Output: Ranked list of asymmetric setups (RR >= 3.0)
# Filter: Only keep if avg_r >= 0.15 AND annual_r >= 30R
```

**Expected Results:**
- Validate 1000 ORB RR=8.0 on our MGC data
- Discover new high-RR setups at untested times (e.g., 1800 ORB RR=5.0?)
- Confirm HALF SL superiority for night ORBs

---

## Category 7: Time-Based Filters & Session Context

### Concept: Market Behavior Changes by Time

**Ideas from Old Research:**

1. **Day of Week Effects**
   - Hypothesis: Monday/Friday may have different behavior than mid-week
   - Filter: Segment by day_of_week (Monday=1, Friday=5)
   - Rationale: Weekend gap risk, position rollovers

2. **Time Decay Within Session**
   - Hypothesis: ORBs early in session outperform late ORBs
   - Filter: Compare 09:00 vs 10:00 vs 11:00 (all Asia session)
   - Rationale: Early breakouts have more time to develop

3. **Session Transition Windows**
   - Hypothesis: ORBs at session transitions (18:00, 23:00, 00:30) have unique behavior
   - Filter: Classify ORBs as "session open" vs "session mid" vs "session close"
   - Rationale: Liquidity surges at opens, exhaustion at closes

4. **Holiday Proximity**
   - Hypothesis: Days before/after US holidays may have reduced participation
   - Filter: Flag days within 1 day of major holidays
   - Rationale: Thin liquidity, different participant mix

**Refactored Test Script Idea:**
```python
# test_time_filters.py
#
# Segment ALL ORB trades by:
#   - day_of_week (1-5)
#   - time_within_session (early/mid/late)
#   - session_type (open/mid/close)
#   - holiday_proximity (before/after/none)
#
# Compare performance across segments
# Find: Which days/times have 5%+ higher WR or 0.05R+ better avg_r
#
# Statistical test: Chi-square for categorical, t-test for continuous
```

**Database Schema We Have:**
- `daily_features.date_local` - Can extract day of week

**What We Need to Add:**
- `day_of_week` column (1-5)
- `is_pre_holiday`, `is_post_holiday` flags
- `session_type` classifier

---

## Category 8: Volatility Regime Filters

### Concept: Trade Differently in Different Market Conditions

**Ideas:**

1. **ATR Percentile Ranking**
   - Hypothesis: High ATR days (top 25%) have different ORB behavior than low ATR days (bottom 25%)
   - Filter: Segment by `atr_20_percentile` (0-100)
   - Rationale: High volatility = larger moves, low volatility = chop

2. **Asia Travel Distance**
   - Hypothesis: Large Asia ranges predict larger ORB moves
   - Filter: `asia_range > 75th percentile` vs `asia_range < 25th percentile`
   - Rationale: Momentum continuation

3. **London-Asia Range Ratio**
   - Hypothesis: When London range > Asia range, it signals trend continuation
   - Filter: `london_range / asia_range > 1.2`
   - Rationale: Expansion into new session indicates strong momentum

4. **Pre-Move Travel**
   - Hypothesis: How far price traveled before ORB predicts breakout quality
   - Filter: `pre_orb_travel` (distance from session open to ORB start)
   - Rationale: Strong early moves predict continuation

**Refactored Test Script Idea:**
```python
# test_volatility_regimes.py
#
# For each ORB time:
#   1. Calculate ATR percentile (rolling 20-day window)
#   2. Segment trades into quintiles (0-20%, 20-40%, ..., 80-100%)
#   3. Compare performance across quintiles
#   4. Find: Which volatility regime has best avg_r
#
# Repeat for:
#   - Asia range percentile
#   - London/Asia ratio
#   - Pre-move travel distance
#
# Output: Filters that improve avg_r by 0.05R+ or WR by 3%+
```

**Database Schema We Have:**
- `daily_features.asia_high`, `asia_low` - Can calculate Asia range
- `daily_features.london_high`, `london_low` - Can calculate London range
- Can compute ATR(20) from bars_5m

**What We Need to Add:**
- `atr_20` to daily_features
- `pre_orb_travel` (session open to ORB start distance)
- `volatility_regime` classifier (HIGH/MEDIUM/LOW)

---

## Priority Ranking for Implementation

### Tier 1: High Priority (Test First)

1. **ORB Correlation Edges** (Category 3)
   - Reason: Already validated in old playbook, quick to test
   - Expected: 5-7% WR improvement, +0.05-0.10R gain
   - Effort: LOW (simple conditions, existing data)

2. **PRE Block Filters** (Category 4)
   - Reason: Zero-lookahead, easy to implement
   - Expected: Filter out 20-30% of losing trades
   - Effort: LOW (just need to add PRE range calculations)

3. **Asymmetric High-RR Setups** (Category 6)
   - Reason: Potential for +50-100R/year per setup
   - Expected: Validate 1000 ORB RR=8.0 on our data
   - Effort: MEDIUM (requires full execution simulation with extended scan)

### Tier 2: Medium Priority (Test After Tier 1)

4. **Massive Move Conditions** (Category 1)
   - Reason: Understand what makes winners BIG
   - Expected: Identify filters for top 25% performers
   - Effort: MEDIUM (requires simulation to track max_favorable_r)

5. **Grid Search for Unicorns** (Category 2)
   - Reason: Comprehensive search for unknown edges
   - Expected: Find 5-10 new profitable setups
   - Effort: HIGH (3,750 configurations, 15-30 minutes compute time)

### Tier 3: Low Priority (Research / Exploratory)

6. **Multi-Liquidity Cascades** (Category 5)
   - Reason: Rare (9.3% frequency), complex to detect
   - Expected: +1.95R avg but only 2-3 per month
   - Effort: HIGH (complex pattern recognition)

7. **Time-Based Filters** (Category 7)
   - Reason: May not have strong effects (speculative)
   - Expected: Small improvements (2-3% WR gain)
   - Effort: LOW (simple segmentation)

8. **Volatility Regime Filters** (Category 8)
   - Reason: Overlap with PRE block filters
   - Expected: Marginal improvements
   - Effort: MEDIUM (need to add ATR and regime classifiers)

---

## Implementation Roadmap

### Phase 1: Quick Wins (Week 1)

**Goal:** Test validated ideas that require minimal new infrastructure

1. **Test ORB Correlations** (Category 3)
   - Script: `test_orb_correlations_mgc.py`
   - Uses existing `daily_features.orb_*_outcome` columns
   - Expected runtime: 5 minutes
   - Output: Filtered WR and avg_r for each correlation pattern

2. **Test PRE Block Filters** (Category 4)
   - Script: `test_pre_block_filters_mgc.py`
   - Add PRE range calculations to daily_features
   - Expected runtime: 10 minutes
   - Output: Optimal thresholds for each ORB time

### Phase 2: High-RR Setups (Week 2)

**Goal:** Validate asymmetric setups with extended scan windows

3. **Test Asymmetric High-RR** (Category 6)
   - Script: `test_asymmetric_high_rr_mgc.py`
   - Full execution simulation on bars_1m
   - Scan until 09:00 next day
   - Expected runtime: 30 minutes
   - Output: Validated high-RR setups ranked by annual_r

### Phase 3: Deep Analysis (Week 3)

**Goal:** Understand what makes winners MASSIVE

4. **Analyze Massive Move Conditions** (Category 1)
   - Script: `analyze_massive_moves_mgc.py`
   - Simulate all trades with max_favorable_r tracking
   - Segment into massive vs regular vs losers
   - Expected runtime: 30 minutes
   - Output: Filters for top 25% performers

### Phase 4: Comprehensive Search (Week 4)

**Goal:** Find unknown unicorns through grid search

5. **Run Grid Search** (Category 2)
   - Script: `grid_search_unicorns_mgc.py`
   - Test 3,750 configurations with multiprocessing
   - Expected runtime: 15-30 minutes (8 cores)
   - Output: All profitable setups ranked by avg_r

### Phase 5: Advanced Patterns (Week 5+)

**Goal:** Research rare but high-edge patterns

6. **Test Cascade Patterns** (Category 5)
   - Script: `test_cascade_patterns_mgc.py`
   - Complex pattern recognition
   - Expected runtime: 20 minutes
   - Output: Cascade performance by gap size

7. **Test Time/Volatility Filters** (Categories 7-8)
   - Scripts: `test_time_filters_mgc.py`, `test_volatility_regimes_mgc.py`
   - Exploratory analysis
   - Expected runtime: 10-15 minutes each
   - Output: Marginal filter improvements

---

## Critical Reminders

### 1. ⚠️ Test Rigorously

- **Require p < 0.05** for statistical significance
- Use t-tests for mean comparisons, chi-square for categorical
- **Minimum sample size**: 50 trades per condition
- **Bonferroni correction** for multiple hypothesis testing

### 2. ⚠️ Zero-Lookahead Enforcement

- Only use information available AT decision time
- **Cannot use**:
  - Future ORB outcomes (e.g., 11:00 outcome to filter 10:00)
  - Completed session stats before session ends
  - Max favorable R before trade closes
- **Can use**:
  - Prior ORB outcomes (09:00 outcome known at 10:00)
  - PRE block ranges (known at ORB start)
  - Historical session patterns

### 3. ⚠️ Honest Reporting

- Report ALL tests, not just successful ones
- **Do not cherry-pick** time periods or parameters
- If a test fails (p > 0.05), document it as FAILED
- Small effect sizes (Cohen's d < 0.2) are not meaningful

### 4. ⚠️ Overfitting Risk

- **Do not optimize** parameters on the same data you test on
- Use walk-forward validation or train/test split
- Simple rules (2-3 conditions) better than complex (10+ conditions)
- More parameters = more overfitting risk

### 5. ⚠️ Position Sizing

- **Rare high-edge setups** (cascades, asymmetric): Risk 0.10-0.25% only
- **Daily high-frequency setups** (ORB correlations): Risk 0.25-0.50%
- **Never** risk >2% total across all positions

---

## Expected Outcomes

### Realistic Expectations

**If successful, these edge discovery methods should:**
- Find 5-10 new validated setups with avg_r >= 0.10
- Improve existing ORB strategies by 5-10% (filter out losers)
- Increase system-wide annual R by 30-50R/year

**What NOT to expect:**
- "Holy grail" setup with 80% WR and +2.0R avg (doesn't exist)
- Every idea will work (most will fail, that's normal)
- Instant profitability (edges are small, compound slowly)

### Success Criteria

**A new edge is "validated" if:**
1. ✓ Statistical significance: p < 0.05
2. ✓ Effect size meaningful: Delta avg_r >= +0.05R OR WR improvement >= 3%
3. ✓ Sample size adequate: >= 50 trades minimum
4. ✓ Zero-lookahead compliant: Only uses known information
5. ✓ Replicable: Can be executed in real-time without discretion

---

## Conclusion

This document provides a comprehensive refactored roadmap for edge discovery using ideas from historical research. All concepts require rigorous testing before trust.

**Next Steps:**
1. Start with Tier 1 (ORB Correlations + PRE Blocks)
2. Validate with proper statistical testing
3. Document results honestly (including failures)
4. Move to Tier 2 only after Tier 1 is validated

**Remember:** These are ideas, not validated edges. Test rigorously. Report honestly. Trust the process.

---

**Last Updated:** 2026-01-27
**Status:** Ideas extracted from `/check` folder, awaiting validation
**Priority:** Start with Tier 1 (Categories 3-4)
