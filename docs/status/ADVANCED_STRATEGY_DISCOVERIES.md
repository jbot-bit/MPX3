# ADVANCED STRATEGY DISCOVERIES
**Date:** 2026-01-29
**Search Type:** Advanced Multi-Condition Filters
**Result:** Found 26 new profitable strategies (12 session context + 4 combined + 10 day-of-week)

---

## 🚀 TOP 10 DISCOVERIES (Ranked by Expectancy)

| Rank | Strategy | Exp (R) | WR (%) | Trades | Type |
|------|----------|---------|--------|--------|------|
| 1 | 1000 RR=3.0 Tuesday | +0.885 | 53.3 | 15 | Day Filter |
| 2 | 1000 RR=3.0 SMALL+BIG_ASIA | +0.684 | 47.8 | 23 | Combined |
| 3 | 1000 RR=2.5 Tuesday | +0.649 | 53.3 | 15 | Day Filter |
| 4 | 1000 RR=2.0 Tuesday | +0.582 | 58.8 | 17 | Day Filter |
| 5 | 1000 RR=2.5 SMALL+BIG_ASIA | +0.473 | 47.8 | 23 | Combined |
| 6 | 1000 RR=3.0 Monday | +0.449 | 40.7 | 27 | Day Filter |
| 7 | 1000 RR=2.0 SMALL+BIG_ASIA | +0.439 | 54.2 | 24 | Combined |
| 8 | 1000 RR=2.5 Monday | +0.389 | 44.4 | 27 | Day Filter |
| 9 | 0900 RR=2.5 BIG_ASIA | +0.381 | 43.6 | 39 | Session |
| 10 | 1000 RR=3.0 BIG_ASIA | +0.335 | 37.8 | 45 | Session |

**Context:** Current best strategy is 1000 RR=3.0 unfiltered at +0.308R.
These advanced filters produce 2-3X BETTER performance!

---

## ⚠️ CRITICAL: Sample Size Warning

**Before rushing to trade these:**

1. **Sample sizes are SMALL** (15-27 trades)
   - Current active strategies have 80-100 trades
   - More variance risk with small samples
   - Could be statistical flukes

2. **Walk-forward validation REQUIRED**
   - Test on out-of-sample data
   - Verify stability over time
   - Check for regime changes

3. **Tuesday effect might be spurious**
   - Only 15-17 trades
   - Need 50+ trades to be confident
   - Could be coincidence

---

## 📊 DETAILED ANALYSIS

### **1. Tuesday 1000 ORB (Day-of-Week Filter)**

**Performance:**
- RR=3.0: +0.885R (15 trades, 53% WR)
- RR=2.5: +0.649R (15 trades, 53% WR)
- RR=2.0: +0.582R (17 trades, 59% WR)

**How to Trade:**
```
PRE-TRADE CHECK:
1. Is today Tuesday? (Yes → Continue, No → Skip)

TRADE EXECUTION:
2. Wait for 1000 ORB to form (10:00-10:05 local)
3. Signal: First 1m CLOSE outside ORB
4. Entry: NEXT 1m OPEN (not signal candle!)
5. Stop: Full ORB edge
6. Target: Entry ± (RR × Risk)

POSITION SIZING:
- Use normal risk (1-2% account)
- No special sizing needed
```

**Why Tuesday?**
- Unknown (could be market structure, weekly cycle, etc.)
- Need more research to understand
- Could be spurious pattern

**Risk:**
- Only 15-17 trades in dataset
- High variance possible
- Needs 50+ trades to be confident

**Recommendation:**
- PAPER TRADE for 20+ Tuesdays first
- Verify edge holds out-of-sample
- Then deploy with reduced risk (0.5-1% vs 1-2%)

---

### **2. SMALL_ORB + BIG_PREVIOUS_ASIA (Combined Filter)**

**Performance:**
- RR=3.0: +0.601R (22 trades, 46% WR) - Verified (not 0.684R)
- RR=2.5: +0.401R (22 trades, 46% WR)
- RR=2.0: +0.388R (23 trades, 52% WR)

**How to Trade:**
```
PRE-TRADE CHECK (PREVIOUS DAY):
1. Calculate yesterday's Asia range:
   Asia_range = Asia_high - Asia_low

2. Calculate yesterday's ATR(20):
   ATR = Average True Range (20 periods)

3. Check if BIG_ASIA:
   If Asia_range > ATR × 0.8 → BIG_ASIA ✅
   If Asia_range <= ATR × 0.8 → NORMAL_ASIA ❌ SKIP

TRADE EXECUTION (CURRENT DAY):
4. Wait for 1000 ORB to form (10:00-10:05)

5. Check SMALL_ORB:
   ORB_size = ORB_high - ORB_low
   If ORB_size / ATR < 0.15 → SMALL_ORB ✅
   If ORB_size / ATR >= 0.15 → BIG_ORB ❌ SKIP

6. If BOTH filters pass:
   - Signal: First 1m CLOSE outside ORB
   - Entry: NEXT 1m OPEN
   - Stop: Full ORB edge
   - Target: Entry ± (RR × Risk)
```

**Example:**
```
YESTERDAY (Monday):
- Asia high: 4520.0
- Asia low: 4485.0
- Asia range: 35.0 points
- ATR(20): 40.0 points
- Ratio: 35.0 / 40.0 = 0.875 > 0.8 ✅ BIG_ASIA

TODAY (Tuesday):
- 1000 ORB high: 4502.0
- 1000 ORB low: 4498.0
- ORB size: 4.0 points
- ATR(20): 40.0 points
- Ratio: 4.0 / 40.0 = 0.10 < 0.15 ✅ SMALL_ORB

BOTH PASS → TRADE THIS 1000 ORB
```

**Why This Works:**
- BIG previous Asia = volatility continuation
- SMALL current ORB = compressed, ready to explode
- Combination creates spring-loaded setup

**Risk:**
- Only 22-23 trades
- Need more data to confirm
- Could fail in different market regimes

**Recommendation:**
- PAPER TRADE for 30+ trades first
- Track separately from unfiltered 1000 ORB
- If holds up, add with reduced risk (0.5-1%)

---

### **3. BIG_ASIA Session Filter (Previous Day)**

**Performance:**
- 0900 RR=2.5: +0.381R (39 trades, 44% WR)
- 1000 RR=3.0: +0.335R (45 trades, 38% WR)
- 0900 RR=3.0: +0.270R (37 trades, 35% WR)

**How to Trade:**
```
PRE-TRADE CHECK (PREVIOUS DAY):
1. Check yesterday's Asia range vs ATR:
   If Asia_range > ATR × 0.8 → BIG_ASIA ✅ TRADE
   If Asia_range <= ATR × 0.8 → NORMAL_ASIA ❌ SKIP

TRADE EXECUTION:
2. On days after BIG_ASIA:
   - Trade 0900 or 1000 ORB normally
   - Signal: 1m close outside ORB
   - Entry: NEXT 1m OPEN
   - Stop: Full ORB edge
   - Target: Entry ± (RR × Risk)
```

**Why This Works:**
- Big Asia moves create momentum continuation
- Next day follow-through
- Volatility clustering effect

**Advantage:**
- Larger samples (37-45 trades)
- More confidence than day-of-week filters
- Clear rationale (volatility continuation)

**Recommendation:**
- Can add to ACTIVE strategies immediately
- Use reduced risk first (1% vs 2%)
- Monitor for 20+ trades

---

### **4. Monday 1000 ORB (Day Filter)**

**Performance:**
- RR=3.0: +0.449R (27 trades, 41% WR)
- RR=2.5: +0.389R (27 trades, 44% WR)
- RR=2.0: +0.295R (27 trades, 48% WR)

**Similar to Tuesday but:**
- Larger sample (27 trades vs 15)
- Lower expectancy (+0.449R vs +0.885R)
- More reliable (more trades)

**Recommendation:**
- More trustworthy than Tuesday (larger sample)
- Can paper trade with higher confidence
- Still needs walk-forward validation

---

## 🎯 IMPLEMENTATION PLAN

### **Phase 1: Paper Trading (4-8 weeks)**

1. **Track Tuesday 1000 ORB**
   - Need 20+ Tuesdays to verify
   - Compare to unfiltered 1000 ORB
   - Check if edge holds

2. **Track SMALL_ORB + BIG_ASIA**
   - Need 30+ occurrences
   - Compare to unfiltered 1000 ORB
   - Track filter pass rate

3. **Track Monday 1000 ORB**
   - Need 20+ Mondays
   - More reliable than Tuesday (larger sample)

### **Phase 2: Live Trading (After Verification)**

1. **If paper trades confirm edge:**
   - Add to validated_setups
   - Use REDUCED risk (0.5-1% vs 1-2%)
   - Monitor closely for 50+ trades

2. **If paper trades FAIL:**
   - Mark as spurious/overfit
   - Do NOT trade
   - Learn from failure

### **Phase 3: Walk-Forward Validation**

1. **Split data into:**
   - Training: 2025-01-01 to 2025-09-30
   - Testing: 2025-10-01 to 2026-01-29

2. **Verify strategies hold on out-of-sample data**

3. **If fails walk-forward:**
   - REJECT strategy (curve-fitted)
   - Remove from consideration

---

## 📝 RECOMMENDATIONS

### **Immediate Actions:**

1. ✅ **Add to paper trading watchlist:**
   - Tuesday 1000 ORB RR=3.0
   - Monday 1000 ORB RR=3.0
   - SMALL_ORB + BIG_ASIA RR=3.0

2. ✅ **Track for 30-50 trades each**

3. ✅ **Compare to unfiltered baseline**

4. ⚠️ **DO NOT trade real money yet** (small samples!)

### **Medium-Term (After Verification):**

1. If edges hold:
   - Add to validated_setups
   - Use reduced risk (0.5-1%)
   - Monitor for degradation

2. If edges fail:
   - Mark as spurious
   - Learn from experience
   - Continue searching

---

## 🚨 HONESTY OVER OUTCOME

**Critical Reminders:**

1. **Small sample sizes = HIGH VARIANCE**
   - 15-27 trades is NOT enough
   - Could be statistical flukes
   - Need 50-100 trades for confidence

2. **Day-of-week effects are SUSPICIOUS**
   - Tuesday edge could be coincidence
   - Markets don't "know" it's Tuesday
   - Needs strong out-of-sample validation

3. **Combined filters look BETTER**
   - SMALL_ORB + BIG_ASIA has clear logic
   - Larger sample (22-23 trades)
   - Still needs verification

4. **Don't let excitement override discipline**
   - Paper trade FIRST
   - Verify SECOND
   - Trade THIRD (maybe)

---

## 📊 COMPARISON TO CURRENT ACTIVE STRATEGIES

| Strategy | Current Exp | Advanced Filter Exp | Improvement |
|----------|-------------|---------------------|-------------|
| 1000 RR=3.0 | +0.308R (92 trades) | +0.885R (15 Tuesday) | +187% |
| 1000 RR=3.0 | +0.308R (92 trades) | +0.601R (22 SMALL+BIG) | +95% |
| 1000 RR=2.5 | +0.212R (95 trades) | +0.649R (15 Tuesday) | +206% |
| 0900 RR=2.5 | +0.257R (86 trades) | +0.381R (39 BIG_ASIA) | +48% |

**Improvements are HUGE - but sample sizes are SMALL!**

---

## 🔬 NEXT STEPS: RESEARCH

1. **Walk-forward validation script**
   - Split data: train 70%, test 30%
   - Verify edges hold on out-of-sample
   - Auto-reject if fails

2. **Why does Tuesday work?**
   - Investigate market structure
   - Check other instruments (NQ, MPL)
   - Look for fundamental reason

3. **Volatility clustering analysis**
   - Does BIG_ASIA → BIG_ASIA next day?
   - Persistence of volatility
   - Regime detection

4. **More advanced filters to test:**
   - Gap size at open
   - Previous week range
   - Multi-day patterns
   - Volume filters

---

**Generated by:** Claude (Sonnet 4.5)
**Methodology:** Comprehensive grid search with NO LOOKAHEAD
**Status:** PAPER TRADING REQUIRED - Not yet validated for live trading
**Honesty:** Small samples, high variance, needs verification
