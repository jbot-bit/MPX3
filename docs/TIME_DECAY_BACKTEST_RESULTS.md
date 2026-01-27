# Time-Decay Backtest Results - HONEST VERDICT

**Date:** 2026-01-26
**OOS Window:** 2025-10-15 to 2026-01-12 (90 days)
**Total Trades:** 371
**Philosophy:** HONESTY OVER OUTCOME

---

## Executive Summary

**VERDICT: ❌ DO NOT USE TIME-DECAY (OVERALL)**

**Overall Impact:**
- Baseline: **0.120R** avg per trade
- Time-decay: **0.080R** avg per trade
- **Delta: -0.040R (-33.5%)** ← LOSES MONEY

**Why It Fails:**
- Exits winners too early (avg winner drops from 1.746R to 0.867R)
- Highly invasive (61.5% of trades exit via time-decay)
- Blanket approach doesn't work - each ORB behaves differently

---

## Detailed Metrics

### Baseline (No Time-Decay)

| Metric | Value |
|--------|-------|
| Total Trades | 371 |
| Total R | +44.46R |
| Avg R | **0.120R** |
| Max DD | 14.11R |
| Win Rate | 40.4% |
| Avg Winner | 1.746R |
| Avg Loser | -0.984R |
| Payoff Ratio | 1.77 |

### Time-Decay

| Metric | Value |
|--------|-------|
| Total Trades | 371 |
| Total R | +29.57R |
| Avg R | **0.080R** |
| Max DD | 10.53R ← LOWER (good!) |
| Win Rate | 43.9% ← HIGHER (but...) |
| Avg Winner | 0.867R ← **MUCH LOWER (bad!)** |
| Avg Loser | -0.537R ← LOWER (good!) |
| Payoff Ratio | 1.61 ← LOWER |
| Time-Decay Exits | **61.5%** ← VERY HIGH |

### Comparison

| Metric | Delta |
|--------|-------|
| Total R | -14.90R (-33.5%) |
| Avg R | **-0.040R (-33.5%)** ← LOSES MONEY |
| Max DD | -3.58R (IMPROVES) |
| Win Rate | +3.5% (IMPROVES) |

**Key Insight:**
- Win rate goes UP (+3.5%)
- But average winner COLLAPSES (1.746R → 0.867R)
- **Net effect: LOSES MONEY**

---

## Per-ORB Breakdown (Critical!)

### 0900 ORB (RR=1.5) - ❌ **DISASTER**

| Metric | Baseline | Time-Decay | Delta |
|--------|----------|------------|-------|
| Avg R | 0.357R | 0.078R | **-0.278R (-78%)** |
| Win Rate | 54.8% | 46.8% | -8.0% |
| Time-Decay Exits | - | **73%** | - |

**Verdict:** **NEVER USE ON 0900 ORB**
- Loses -0.278R per trade (destroys edge!)
- 73% invasiveness (exits almost every trade early)
- 0900 is a fast mover - time-decay kills it

---

### 1000 ORB (RR=1.5) - ✅ **NEUTRAL**

| Metric | Baseline | Time-Decay | Delta |
|--------|----------|------------|-------|
| Avg R | 0.048R | 0.052R | **+0.004R (+8%)** |
| Win Rate | 43.5% | 45.2% | +1.7% |
| Time-Decay Exits | - | 55% | - |

**Verdict:** SLIGHTLY BETTER (but negligible)
- Minimal improvement (+0.004R)
- Not worth the 55% invasiveness

---

### 1000 ORB (RR=2.0) - ❌ **WORSE**

| Metric | Baseline | Time-Decay | Delta |
|--------|----------|------------|-------|
| Avg R | 0.114R | 0.068R | **-0.046R (-40%)** |
| Win Rate | 38.7% | 41.9% | +3.2% |
| Time-Decay Exits | - | 60% | - |

**Verdict:** WORSE
- Loses -0.046R per trade
- Exits winners too early

---

### 1000 ORB (RR=2.5) - ✅ **BETTER**

| Metric | Baseline | Time-Decay | Delta |
|--------|----------|------------|-------|
| Avg R | 0.076R | 0.125R | **+0.049R (+65%)** |
| Win Rate | 32.3% | 40.3% | +8.0% |
| Time-Decay Exits | - | 61% | - |

**Verdict:** **BETTER (only one that works!)**
- Gains +0.049R per trade
- Higher RR needs more time, time-decay cuts chop losses

---

### 1000 ORB (RR=3.0) - ✅ **BETTER**

| Metric | Baseline | Time-Decay | Delta |
|--------|----------|------------|-------|
| Avg R | 0.074R | 0.121R | **+0.047R (+64%)** |
| Win Rate | 29.0% | 40.3% | +11.3% |
| Time-Decay Exits | - | 65% | - |

**Verdict:** **BETTER**
- Gains +0.047R per trade
- High RR benefits from early chop exits

---

### 1800 ORB (RR=1.5) - ❌ **WORSE**

| Metric | Baseline | Time-Decay | Delta |
|--------|----------|------------|-------|
| Avg R | 0.050R | 0.034R | **-0.017R (-33%)** |
| Win Rate | 44.3% | 49.2% | +4.9% |
| Time-Decay Exits | - | 56% | - |

**Verdict:** WORSE
- Loses -0.017R per trade
- Not as bad as 0900, but still negative

---

## Critical Insights

### 1. RR Target Matters More Than ORB Time

**Pattern:**
- Low RR (1.5R, 2.0R): TIME-DECAY HURTS
- High RR (2.5R, 3.0R): TIME-DECAY HELPS

**Why:**
- Low RR targets are quick hits (15-20 min)
- Time-decay exits before target reached
- High RR targets need more time (45+ min)
- Time-decay cuts chop losses, winners still have time

**Actionable:**
- Don't use blanket time-decay
- ONLY use on RR >= 2.5 setups

---

### 2. 0900 ORB is Special (Fast Mover)

**0900 Results:**
- Baseline: 0.357R (BEST of all ORBs!)
- Time-decay: 0.078R (DESTROYED)
- Delta: -0.278R (-78%!)

**Why 0900 is Different:**
- Highest liquidity of the day
- Fastest moves (NY open energy)
- Winners develop quickly (10-15 min)
- Time-decay exits too early

**Recommendation:**
- **NEVER use time-decay on 0900 ORB**
- Let it run - it's your best edge

---

### 3. Win Rate Increase is Misleading

**What Happened:**
- Win rate: 40.4% → 43.9% (+3.5%)
- Avg winner: 1.746R → 0.867R (-50%!)

**Why:**
- Time-decay exits small winners early (+0.2R, +0.3R)
- Misses big winners (exits at +0.5R instead of +1.5R+)
- "Win" count goes up, but profit goes down

**Lesson:**
- Don't chase win rate
- Focus on avg R and payoff ratio

---

### 4. Invasiveness is Too High

**61.5% of trades exit via time-decay**

**What This Means:**
- System overrides your edge 6 out of 10 trades
- You're not trading YOUR setup anymore
- You're trading a "time-decay modified" version

**Is This OK?**
- NO - if it loses money (-0.040R)
- MAYBE - if it made money significantly
- Your edge is in the ORB break, not time management

---

## Recommendations

### ❌ DON'T USE: Blanket Time-Decay

**Reason:** Loses -0.040R per trade overall (-33.5%)

**Impact:** On 100 trades/year:
- Lose -4R
- If 1R = $500 → Lose **$2,000/year**

---

### ⚠️ MAYBE USE: Selective Time-Decay (High RR Only)

**Approach:** Use time-decay ONLY on:
- 1000 ORB with RR >= 2.5
- (Maybe other high RR setups after testing)

**Expected Impact:**
- 1000 (RR=2.5): +0.049R
- 1000 (RR=3.0): +0.047R
- Average: +0.048R per high-RR trade

**If You Trade 30 High-RR Trades/Year:**
- Gain +1.44R
- If 1R = $500 → Gain **$720/year**

**Worth It?**
- MAYBE - test this separately
- Create a "time_decay_high_rr_only.py" variant
- Backtest just high RR setups

---

### ✅ DEFINITELY DON'T USE: Time-Decay on 0900 ORB

**Reason:** Loses -0.278R per trade (-78%!)

**Impact:** On 60 trades/year (0900 only):
- Lose -16.68R
- If 1R = $500 → Lose **$8,340/year**

**Conclusion:** 0900 is a fast mover. Let it run!

---

## What You Learned

### 1. One-Size-Fits-All Doesn't Work

**Each ORB has different characteristics:**
- 0900: Fast, high win rate → Don't exit early
- 1000: Slower, mixed results → Selective use only
- 1800: Lower liquidity → Don't exit early

**Lesson:** Customize thresholds per ORB, or don't use at all

---

### 2. High RR Targets Need Different Logic

**Low RR (1.5R, 2.0R):**
- Quick hits (15-20 min)
- Time-decay exits too early

**High RR (2.5R+):**
- Slower development (30-45 min)
- Time-decay cuts chop losses
- Winners still have time to reach target

**Lesson:** If using time-decay, ONLY use on high RR setups

---

### 3. Test Before Deploy (You Did It Right!)

**What Would Have Happened Without Testing:**
- You implement time-decay
- Lose -0.040R per trade
- Lose -$2,000+ per year
- Wonder why your edge disappeared

**What Actually Happened:**
- You backtested first
- Discovered it hurts expectancy
- **SAVED $2,000+/year by NOT using it**

**Lesson:** ALWAYS backtest before live trading

---

## Final Verdict

**OVERALL:** ❌ **SKIP TIME-DECAY**

**Specific Recommendations:**

1. **NEVER use on 0900 ORB** (-0.278R disaster)
2. **MAYBE use on 1000 RR>=2.5** (+0.048R selective benefit)
3. **DON'T use on 1800 ORB** (-0.017R negative)
4. **DON'T use blanket approach** (-0.040R overall)

**If You Want to Experiment:**
- Create selective version (high RR only)
- Test 1000 RR=2.5 and RR=3.0 separately
- Monitor results for 30 trades
- If still positive, keep it
- If goes negative, kill it

**Conservative Recommendation:**
- **DON'T USE** - your edge is already good (0.120R baseline)
- Focus on execution, not exit timing
- Let winners run (especially 0900)

---

## Appendix: Why Did I Build This?

**Hypothesis:** Time-decay cuts chop losses, improves expectancy

**Test Result:** WRONG (overall)
- It does cut chop losses (avg loser: -0.984R → -0.537R)
- But also cuts winners (avg winner: 1.746R → 0.867R)
- **Net effect: LOSES MONEY**

**Lesson Learned:**
- Don't optimize exit timing
- Optimize entry quality
- Your edge is in the ORB break, not time management

**Was It Worth Building?**
- YES - we learned what DOESN'T work
- Saved $2,000+/year by NOT using it
- Backtesting prevented real losses

**HONESTY OVER OUTCOME: This feature doesn't work. Don't use it.**

---

**End of Backtest Results**
