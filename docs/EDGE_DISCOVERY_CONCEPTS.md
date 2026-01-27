# Edge Discovery Concepts - Ideas Only (Logic to be Built from Scratch)

**Date:** 2026-01-27
**Source:** Conceptual ideas extracted from `/check` folder
**Status:** CONCEPTS ONLY - Implementation needs fresh validation
**Philosophy:** Trust the ideas, not the old calculations. Build from scratch.

---

## ⚠️ CRITICAL WARNING

**The files in `/check` contain:**
- ✓ Good conceptual ideas
- ✗ Potentially buggy implementations
- ✗ Possibly incorrect numbers/thresholds
- ✗ May have lookahead bias
- ✗ May use outdated database schema

**This document extracts ONLY the concepts. All implementation must be built fresh with proper validation.**

---

## Concept 1: Identify What Makes Winners "Massive"

### The Idea

Not all winning trades are equal. Some winners hit 2R and stop. Others explode to 10R+. What conditions predict MASSIVE winners?

**Approach:**
1. Simulate all ORB trades with a high RR target (e.g., 10R)
2. Track the maximum favorable excursion (how far did price move in our favor before exit?)
3. Segment winners into:
   - Massive (top 25% by max favorable R)
   - Regular (bottom 75%)
   - Losers
4. Compare the conditions between these groups

**Hypotheses to Test:**

- **ORB Size vs ATR**: Tight ORBs (small relative to ATR) may lead to explosive moves
- **Entry Speed**: Fast entries (immediate break after ORB) may catch better momentum
- **Session Range**: Large Asia/London ranges may predict larger ORB moves
- **Direction**: UP breaks may move further than DOWN breaks (instrument-specific)
- **Time to Target**: Trades that hit target quickly may have better conditions

**What to Measure:**

For each trade, calculate:
- `orb_size` (ORB high - ORB low)
- `orb_size_vs_atr` (ORB size / ATR(20))
- `entry_delay_minutes` (Time from ORB close to first break)
- `asia_range` (Asia high - Asia low)
- `london_range` (London high - London low)
- `max_favorable_r` (Maximum R-multiple reached before exit)
- `bars_to_exit` (Minutes to hit target or stop)

**Questions to Answer:**

- Do massive winners have smaller ORB sizes (more compressed)?
- Do massive winners break out faster (< 2 minutes)?
- Do massive winners occur on high-range Asia days?
- Is there a direction bias (UP vs DOWN)?
- Can we create a filter that increases "massive winner" probability by 20%+?

**Implementation Notes:**

- Simulate on 1-minute bars for precision
- Track max favorable R separately from outcome (a loss can still have high max favorable R)
- Use statistical tests to compare groups (t-test for continuous, chi-square for categorical)
- Require p < 0.05 for significance

---

## Concept 2: Comprehensive Grid Search for Unknown Edges

### The Idea

We've only tested a handful of ORB configurations. What if profitable setups exist at untested times, durations, or parameters?

**Dimensions to Test:**

1. **ORB Time**: Test every hour (00:00, 01:00, ..., 23:00) + 00:30
   - Rationale: Maybe 03:00 or 15:00 have undiscovered edges

2. **ORB Duration**: Test 5, 10, 15, 30, 60 minutes
   - Rationale: Maybe 15-minute ORBs work better than 5-minute

3. **Stop Loss Mode**: Test different stop placements
   - FULL: Stop at opposite ORB edge (maximum risk = full ORB size)
   - HALF: Stop at ORB midpoint (risk = half ORB size)
   - QUARTER: Stop at 25% into ORB from edge (tight stop)
   - THREE_QUARTER: Stop at 75% into ORB from edge (loose stop)

4. **RR Target**: Test 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0
   - Rationale: Some ORBs may work better with 6R targets than 1R

5. **Scan Window**: Scan until 09:00 next day for ALL ORBs
   - Rationale: Overnight moves take 3-8 hours to develop

**Total Configurations:** ~3,000-4,000

**Filtering Criteria:**

Only report a configuration as "profitable" if:
- Minimum 100 trades over 2 years (≥7% of days)
- Average R ≥ 0.20 (strong positive expectancy)
- Annual R ≥ 30R/year (meaningful returns)
- Either decent win rate (≥25%) OR high payoff (avg R ≥ 0.30)

**Questions to Answer:**

- Which hours have undiscovered edges?
- Do longer ORB durations (15/30/60min) work better?
- Is HALF SL better than FULL SL for certain times?
- Which RR targets optimize each ORB time?

**Implementation Notes:**

- Use multiprocessing (8 cores) to parallelize
- Save checkpoints every 250 configs (allows early stopping)
- For each config, simulate full execution on 1-minute bars
- Scan until 09:00 next day (critical for capturing overnight moves)
- Report results as CSV ranked by avg_r

**Important:** This is a discovery tool, not validation. Any "unicorns" found need separate validation on held-out data.

---

## Concept 3: Sequential ORB Dependencies

### The Idea

ORBs don't happen in isolation. The outcome of the 09:00 ORB tells you something about market state that's useful for the 10:00 ORB.

**Basic Concept:**

At 10:00, you already know:
- Did the 09:00 ORB break? (YES/NO)
- If it broke, which direction? (UP/DOWN)
- Did it hit target or stop? (WIN/LOSS)

This is **zero-lookahead compliant** because the 09:00 outcome is known before you decide on the 10:00 trade.

**Hypotheses to Test:**

1. **Momentum Continuation**
   - If 09:00 broke UP and WON → Does 10:00 UP have higher WR?
   - If 09:00 + 10:00 both broke UP and WON → Does 11:00 UP have higher WR?
   - Rationale: Strong momentum persists across multiple ORBs

2. **Reversal After Failure**
   - If 09:00 broke UP and LOST → Does 10:00 DOWN have higher WR?
   - If 09:00 LOST, 10:00 WON → Does 11:00 show reversal pattern?
   - Rationale: Failed breakouts trap traders, leading to reversals

3. **Direction-Specific Correlations**
   - Does 09:00 UP WIN predict 10:00 UP specifically (not just "10:00 works better")?
   - Does 09:00 DOWN WIN predict 10:00 DOWN?

**Conditions to Test:**

For 10:00 ORB:
- 10:00 UP after 09:00 WIN (any direction)
- 10:00 UP after 09:00 WIN UP (same direction)
- 10:00 DOWN after 09:00 WIN DOWN
- 10:00 UP after 09:00 LOSS
- 10:00 DOWN after 09:00 LOSS

For 11:00 ORB:
- 11:00 UP after [09:00 WIN + 10:00 WIN] (double continuation)
- 11:00 DOWN after [09:00 LOSS + 10:00 WIN] (reversal)
- 11:00 UP after [09:00 LOSS + 10:00 LOSS] (recovery)

**Questions to Answer:**

- Does momentum continuation exist? (Higher WR for same-direction follows)
- Does reversal pattern exist? (Higher WR for opposite-direction after loss)
- What is the magnitude of improvement? (Need ≥3% WR gain or ≥0.05R avg gain)
- Is it statistically significant? (p < 0.05 required)

**Implementation Notes:**

- Simulate 09:00 ORB first, record outcome
- Simulate 10:00 ORB second, filter by 09:00 outcome
- Simulate 11:00 ORB third, filter by 09:00 + 10:00 outcomes
- Compare filtered performance vs baseline (no filter)
- Use t-test for statistical validation

**Critical:** Only use completed ORB outcomes. Do NOT use future session stats or outcomes that aren't known yet.

---

## Concept 4: Pre-Range Filters (Known Before ORB)

### The Idea

Before the ORB even forms, you can observe how much price moved in the pre-ORB period. High pre-range suggests volatility is present. Low pre-range suggests chop.

**Pre-Range Definitions:**

- **PRE_ASIA**: 07:00-09:00 range (known at 09:00 ORB start)
- **PRE_LONDON**: 17:00-18:00 range (known at 18:00 ORB start)
- **PRE_NY**: 23:00-00:30 range (known at 00:30 ORB start)

**Hypothesis:**

High pre-range predicts:
- Better ORB performance (higher WR, higher avg R)
- Continuation of volatility into the ORB period

Low pre-range predicts:
- Worse ORB performance (lower WR, negative avg R)
- Choppy, directionless price action

**Filters to Test:**

For each ORB time, test multiple thresholds:
- PRE_range > 30 ticks (3.0 points)
- PRE_range > 40 ticks (4.0 points)
- PRE_range > 50 ticks (5.0 points)
- PRE_range > 60 ticks (6.0 points)

Compare:
- Trades where PRE_range > threshold
- Trades where PRE_range < threshold
- Baseline (no filter)

**Questions to Answer:**

- What is the optimal threshold for each ORB time?
- Does filtering by PRE_range improve WR by ≥3%?
- Does filtering by PRE_range improve avg R by ≥0.05R?
- Should we skip trades when PRE_range is too low?

**Implementation Notes:**

- Calculate PRE_range from bars_1m for each date
- For each ORB time, segment trades by PRE_range bins
- Compare performance across bins
- Find optimal threshold that maximizes (WR × avg_r)
- Validate with t-test (p < 0.05)

**Critical:** PRE_range must be calculated BEFORE ORB starts. No lookahead.

---

## Concept 5: Extended Scan Windows

### The Idea

Old ORB systems scan for only 1-2 hours after ORB forms. But many moves develop overnight, taking 4-8 hours to reach targets.

**Current Problem:**

If you scan 23:00 ORB only until 00:30 (85 minutes):
- Price breaks out at 23:05
- Drifts sideways until 07:00
- Explodes during Asia open at 09:00
- **If you stopped scanning at 00:30, you missed the 6R winner!**

**Solution:**

Scan ALL ORBs until 09:00 next day.

**Why This Matters:**

- Captures overnight moves that develop slowly
- Critical for high RR targets (6R-10R)
- Especially important for night ORBs (18:00, 23:00, 00:30)

**Implementation:**

For every ORB (0900, 1000, 1100, 1800, 2300, 0030):
- Entry window: Starts at ORB end (e.g., 10:05 for 1000 ORB)
- Scan window: Ends at 09:00 next day
- Track: Did stop hit? Did target hit? When?

**Questions to Answer:**

- How many trades hit target AFTER the old scan window ended?
- What percentage of 6R-10R targets require overnight scanning?
- Does extended scanning improve avg R significantly?

**Implementation Notes:**

- Query bars_1m from ORB end to 09:00 next day
- For each bar, check if stop or target hit
- Record exit time and outcome
- Compare "extended scan" vs "old scan" (85 min or session-end)

**Critical:** Must handle trades that span midnight correctly (date changes at 00:00).

---

## Concept 6: Stop Loss Mode Optimization

### The Idea

Not all ORBs work best with the same stop placement. Some need tight stops (HALF), others need room (FULL).

**Stop Loss Modes:**

1. **FULL**: Stop at opposite ORB edge
   - Risk = Full ORB size
   - Entry to stop = ORB size
   - Best for: ORBs that need room for pullbacks

2. **HALF**: Stop at ORB midpoint
   - Risk = Half ORB size
   - Entry to stop = 0.5 × ORB size
   - Best for: ORBs with tight, directional moves

3. **QUARTER**: Stop at 25% into ORB from entry edge
   - Risk = 0.25 × ORB size
   - Very tight stop
   - Best for: High conviction, low tolerance for whipsaw

4. **THREE_QUARTER**: Stop at 75% into ORB from entry edge
   - Risk = 0.75 × ORB size
   - Loose stop
   - Best for: Choppy ORBs that eventually work

**Hypothesis:**

- Night ORBs (23:00, 00:30) work better with HALF stops (moves are smaller, tighter stops prevent whipsaw)
- Day ORBs (09:00, 10:00, 11:00) work better with FULL stops (moves are larger, need room)
- Some ORBs may work with QUARTER stops (very tight, high WR)

**Questions to Answer:**

- Which SL mode maximizes avg R for each ORB time?
- Does HALF SL outperform FULL SL for night ORBs by 2×+?
- Can QUARTER stops work (tight risk, high WR)?

**Implementation Notes:**

For each ORB time:
- Test all SL modes (FULL, HALF, QUARTER, THREE_QUARTER)
- Calculate R-multiple based on actual stop distance
- For HALF: R = distance from entry to midpoint
- For QUARTER: R = distance from entry to 25% stop
- Compare avg R across SL modes
- Find optimal mode per ORB time

**Example:**
```
1000 ORB: 2700-2706 (6 points)
Midpoint: 2703
Break UP at 2706.5

FULL stop: 2700 (6.5 points risk = 1R)
HALF stop: 2703 (3.5 points risk = 1R)
QUARTER stop: 2704.5 (2.0 points risk = 1R)

If target is 2R:
- FULL: Target at 2706.5 + (6.5 × 2) = 2719.5
- HALF: Target at 2706.5 + (3.5 × 2) = 2713.5
- QUARTER: Target at 2706.5 + (2.0 × 2) = 2710.5
```

**Critical:** Adjust RR calculations based on actual stop distance, not ORB size.

---

## Concept 7: Asymmetric High-RR Setups

### The Idea

Accept low win rates (15-30%) if payoffs are massive (6R-10R).

**Philosophy:**

- 1 winner at 8R pays for 8 losers
- Only need 12.5% WR to breakeven at 8R
- Anything above 12.5% WR = positive expectancy

**Hypothesis:**

Certain ORBs may work better with high RR targets:
- Win rate drops (harder to hit 8R than 1R)
- But average R increases (8R winners compensate for more losses)
- Net result: Higher avg R than 1R system

**Questions to Test:**

- Does 1000 ORB work better with RR=8.0 than RR=1.0?
- Does 0900 ORB work better with RR=6.0?
- What is the optimal RR for each ORB time?

**Filters for Asymmetric Setups:**

- Small ORB size (≤ 10 points or ≤ 0.15 × ATR)
- Rationale: Tight risk allows larger targets relative to stop

**Implementation:**

For each ORB time:
- Test RR = 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0
- Track: trades, wins, avg_r, annual_r
- Find: Which RR maximizes avg_r?
- Validate: Does high-RR outperform 1R by ≥0.10R avg?

**Example:**

1000 ORB with ORB size ≤ 10 points:
- RR=1.0: 60% WR, +0.20R avg
- RR=8.0: 15% WR, +0.38R avg (BETTER!)

**Critical:** Must use extended scan windows (until 09:00 next day) to capture slow 6R-10R moves.

---

## Concept 8: Multi-Liquidity Cascade Pattern

### The Idea

Sequential liquidity sweeps create forced liquidations. Each level traps participants, creating compound pressure.

**Pattern Structure:**

1. **Asia Session (09:00-17:00)**: Establishes day's high and low
2. **London Session (18:00-23:00)**: Price sweeps above Asia high OR below Asia low (first sweep)
3. **NY Futures Open (23:00)**: Price sweeps back to London level (second sweep)
4. **Acceptance Failure**: Price fails to hold above/below swept level within 3 minutes
5. **Entry**: Enter at swept level with tight stop

**Hypothesis:**

When multiple liquidity levels are swept in sequence:
- Each sweep traps late participants
- Failed acceptance triggers liquidations
- Larger gaps between levels predict stronger moves

**Pattern Detection Logic:**

```
For each date:
  1. Get Asia high/low (09:00-17:00)
  2. Get London high/low (18:00-23:00)
  3. Check if London swept Asia:
     - London high > Asia high (sweep high)
     - London low < Asia low (sweep low)
  4. At 23:00, check if London level re-swept
  5. Check acceptance failure (price closes back below/above within 3 bars)
  6. If all conditions met → ENTRY SIGNAL
```

**Key Variables:**

- **Gap Size**: Distance between Asia level and London level
- Hypothesis: Larger gaps (>9 points) predict stronger moves
- Test thresholds: 5, 7, 9, 11, 15 points

**Implementation:**

- Detect pattern on daily_features (has asia_high/low, london_high/low)
- Simulate entry at 23:00 if pattern detected
- Entry at swept level ± 0.1 points
- Stop at second sweep high/low
- Target at opposite Asia level
- Track performance by gap size bins

**Questions to Answer:**

- What is the base edge (all cascades)?
- Does gap size filter improve edge?
- What is optimal gap threshold?
- How frequent is pattern (% of days)?

**Critical Notes:**

- This is RARE (estimated 5-10% of days)
- High variance (some huge winners, many small losses)
- Position sizing: 0.10-0.25% risk ONLY
- Not suitable for daily trading (too infrequent)

---

## Concept 9: Time-Based Segmentation

### The Idea

Market behavior may change based on day of week, session position, or holiday proximity.

**Segmentations to Test:**

1. **Day of Week**
   - Segment by: Monday, Tuesday, Wednesday, Thursday, Friday
   - Hypothesis: Monday/Friday may have different behavior (weekend gaps, position rolls)
   - Question: Do certain ORBs work better on specific days?

2. **Early vs Late in Session**
   - 09:00 = Early Asia, 10:00 = Mid Asia, 11:00 = Late Asia
   - Hypothesis: Early session ORBs catch more momentum
   - Question: Does 09:00 outperform 11:00?

3. **Session Transition**
   - 09:00 = Asia open, 18:00 = London open, 23:00 = NY open
   - Hypothesis: Opens have liquidity surges
   - Question: Do "open" ORBs work better than "mid-session" ORBs?

4. **Holiday Proximity**
   - Flag days before/after major US holidays
   - Hypothesis: Thin liquidity around holidays
   - Question: Should we skip ORBs on pre/post-holiday days?

**Implementation:**

- Add `day_of_week` to daily_features (1=Mon, 5=Fri)
- Add `is_pre_holiday`, `is_post_holiday` flags
- Segment all ORB trades by these variables
- Compare performance across segments
- Use chi-square test for categorical differences

**Questions to Answer:**

- Do any days have 5%+ higher WR?
- Should we skip certain days?
- Is there a consistent pattern?

**Critical:** These may be weak effects or false positives. Require strong statistical significance (p < 0.01 due to multiple testing).

---

## Concept 10: Volatility Regime Filters

### The Idea

Market volatility changes day-to-day. High volatility days may behave differently than low volatility days.

**Regime Classifications:**

1. **ATR Percentile**
   - Calculate ATR(20) for each day
   - Rank into percentiles (0-20%, 20-40%, ..., 80-100%)
   - Hypothesis: High ATR days (top 20%) have better ORB performance

2. **Asia Range Percentile**
   - Calculate Asia range (high - low)
   - Rank into percentiles
   - Hypothesis: Large Asia range predicts larger ORB moves

3. **Session Range Comparison**
   - Calculate: london_range / asia_range
   - Hypothesis: When London > Asia, it signals trend continuation

4. **Pre-Move Travel**
   - Calculate: Distance from session open to ORB start
   - Hypothesis: Strong early moves predict continuation

**Implementation:**

- Add volatility features to daily_features:
  - `atr_20` (20-day ATR)
  - `atr_percentile` (0-100)
  - `asia_range` (asia_high - asia_low)
  - `asia_range_percentile` (0-100)
  - `london_asia_ratio` (london_range / asia_range)

- For each ORB time, segment by volatility regime
- Compare performance across regimes
- Find: Which regime has highest avg_r?

**Questions to Answer:**

- Do high volatility days have better ORB performance?
- Should we skip ORB trades on low volatility days?
- What is optimal ATR percentile threshold?

---

## Implementation Priority

### Tier 1: Start Here (Highest Confidence)

1. **ORB Correlations** (Concept 3)
   - Zero-lookahead compliant
   - Conceptually sound (momentum/reversal)
   - Easy to implement

2. **PRE-Range Filters** (Concept 4)
   - Zero-lookahead compliant
   - Simple logic
   - Quick to test

3. **Extended Scan Windows** (Concept 5)
   - Critical infrastructure improvement
   - Affects all ORBs
   - No risk of overfitting

### Tier 2: Test After Tier 1 Validates

4. **Stop Loss Mode Optimization** (Concept 6)
   - Changes risk calculation
   - May significantly improve night ORBs
   - Medium implementation effort

5. **Asymmetric High-RR Setups** (Concept 7)
   - Requires extended scan windows first
   - Potentially high-value
   - Medium implementation effort

6. **Massive Move Conditions** (Concept 1)
   - Requires full simulation infrastructure
   - Good for understanding edge quality
   - Medium-high implementation effort

### Tier 3: Research / Exploratory

7. **Grid Search** (Concept 2)
   - Comprehensive but time-intensive
   - Discovery tool, not validation
   - High computational cost

8. **Cascade Patterns** (Concept 8)
   - Rare pattern (low frequency)
   - Complex detection logic
   - High implementation effort

9. **Time Segmentation** (Concept 9)
   - May be weak effects
   - Risk of false positives
   - Low implementation effort

10. **Volatility Regimes** (Concept 10)
    - Overlap with PRE-range filters
    - May be redundant
    - Medium implementation effort

---

## Critical Implementation Rules

### 1. ✅ Zero-Lookahead Enforcement

**Can Use:**
- Prior ORB outcomes (09:00 outcome known at 10:00)
- PRE-range (calculated before ORB starts)
- Historical session patterns
- ATR calculated on prior bars

**Cannot Use:**
- Future ORB outcomes (10:00 outcome to filter 10:00)
- Completed session stats before session ends
- Max favorable R (only known after exit)
- Next day's data

### 2. ✅ Statistical Validation Required

- T-test for mean comparisons (baseline vs filtered)
- P-value < 0.05 for single tests
- P-value < 0.01 for multiple tests (Bonferroni correction)
- Minimum sample size: 50 trades per condition
- Cohen's d > 0.2 for meaningful effect size

### 3. ✅ Honest Reporting

- Document ALL tests, not just successes
- Report p-values, sample sizes, effect sizes
- If a test fails, document as FAILED
- No cherry-picking parameters or time periods

### 4. ✅ Overfitting Prevention

- Use simple rules (2-3 conditions max)
- Avoid optimizing on same data you test on
- Use walk-forward validation or train/test split
- More parameters = more overfitting risk

### 5. ✅ Database Schema Requirements

**Must Have:**
- `bars_1m` table with 1-minute OHLCV data
- `daily_features` table with session ranges
- `orb_*_outcome` columns for sequential filters

**Must Add (as needed):**
- `pre_asia_range`, `pre_london_range`, `pre_ny_range`
- `atr_20`, `atr_percentile`
- `day_of_week`, `is_pre_holiday`, `is_post_holiday`
- `max_favorable_r`, `bars_to_exit` (for Concept 1)

---

## Next Steps

1. **Choose ONE concept from Tier 1** to implement first
2. **Build from scratch** - Do not copy old logic
3. **Validate database schema** - Ensure bars_1m and daily_features have required data
4. **Write test script** with proper statistical validation
5. **Run test** and document results honestly
6. **If successful** (p < 0.05, meaningful effect), move to next concept
7. **If failed** (p > 0.05), document and try different concept

**Recommended Starting Point:** Concept 3 (ORB Correlations) - Highest confidence, simplest logic.

---

**Last Updated:** 2026-01-27
**Status:** Conceptual ideas only - Implementation TBD
**Warning:** DO NOT trust calculations from old files. Build fresh.
