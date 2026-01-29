# TRADING INSTRUCTIONS - ALL ACTIVE STRATEGIES
**Generated:** 2026-01-29
**Instrument:** MGC (Micro Gold)
**Status:** 11 ACTIVE Strategies (HONEST - No Lookahead)

---

## 🎯 HOW TO TRADE MGC ORB STRATEGIES

### **Entry Model (B-Entry - Used for ALL Strategies)**

1. **Wait for ORB to form** (5-minute ORB window completes)
2. **Check filter criteria** (if applicable)
3. **Signal:** First 1-minute CLOSE outside ORB range
4. **Entry:** NEXT 1-minute OPEN after signal (NOT the signal candle!)
5. **Stop:** ORB edge (full SL mode) or ORB midpoint (half SL mode)
6. **Target:** Entry ± (RR × Risk)

**Risk Calculation:**
```
Risk = |Entry Price - Stop Price|
Target Distance = RR × Risk
Target Price = Entry ± Target Distance
```

---

## 📊 0900 ORB STRATEGIES (4 variants - ALL SURVIVORS)

### **0900 ORB RR=1.5 (Simple, High Win Rate)**
**Expectancy:** +0.198R | **Win Rate:** 51.2% | **Trades:** 87

**How to Trade:**
1. Wait for 0900 ORB to form (09:00-09:05 local)
2. **NO FILTER** - take all 0900 ORB signals
3. Entry: First 1m close outside ORB → NEXT 1m OPEN
4. Stop: Full ORB edge (if break up, stop at ORB low; if break down, stop at ORB high)
5. Risk: |Entry - Stop|
6. Target: Entry ± (1.5 × Risk)

**Example:**
```
ORB: High 4500.0, Low 4490.0
Signal: 1m close at 4501.0 (ABOVE ORB)
Entry: NEXT 1m open at 4502.0
Stop: 4490.0 (ORB low)
Risk: 4502 - 4490 = 12.0 points
Target: 4502 + (1.5 × 12) = 4520.0
```

---

### **0900 ORB RR=2.0 (Balanced)**
**Expectancy:** +0.170R | **Win Rate:** 41.7% | **Trades:** 86

**How to Trade:**
1. Wait for 0900 ORB to form (09:00-09:05)
2. **NO FILTER** - take all signals
3. Entry: First 1m close outside ORB → NEXT 1m OPEN
4. Stop: Full ORB edge
5. Risk: |Entry - Stop|
6. Target: Entry ± (2.0 × Risk)

**Why RR=2.0:**
- Lower win rate than RR=1.5 (42% vs 51%)
- But larger winners compensate
- Good for trending days

---

### **0900 ORB RR=2.5 (Aggressive)**
**Expectancy:** +0.257R | **Win Rate:** 38.1% | **Trades:** 86

**How to Trade:**
1. Wait for 0900 ORB to form (09:00-09:05)
2. **NO FILTER** - take all signals
3. Entry: First 1m close outside ORB → NEXT 1m OPEN
4. Stop: Full ORB edge
5. Risk: |Entry - Stop|
6. Target: Entry ± (2.5 × Risk)

**Best 0900 Strategy:**
- Highest expectancy (+0.257R)
- Lower win rate (38%) but BIG winners
- Use on days with strong directional bias

---

### **0900 ORB RR=3.0 (Runner)**
**Expectancy:** +0.221R | **Win Rate:** 32.1% | **Trades:** 83

**How to Trade:**
1. Wait for 0900 ORB to form (09:00-09:05)
2. **NO FILTER** - take all signals
3. Entry: First 1m close outside ORB → NEXT 1m OPEN
4. Stop: Full ORB edge
5. Risk: |Entry - Stop|
6. Target: Entry ± (3.0 × Risk)

**Why RR=3.0:**
- Lowest win rate (32%) but HUGE winners
- Best for trending days with follow-through
- Requires patience

---

## 📊 1000 ORB STRATEGIES (3 variants - ALL SURVIVORS)

### **1000 ORB RR=2.0 (Consistent)**
**Expectancy:** +0.166R | **Win Rate:** 43.4% | **Trades:** 99

**How to Trade:**
1. Wait for 1000 ORB to form (10:00-10:05)
2. **NO FILTER** - take all signals
3. Entry: First 1m close outside ORB → NEXT 1m OPEN
4. Stop: Full ORB edge
5. Risk: |Entry - Stop|
6. Target: Entry ± (2.0 × Risk)

**Why 1000 ORB:**
- Later in session (more liquidity)
- Asia session bias established
- Good follow-through

---

### **1000 ORB RR=2.5 (Sweet Spot)**
**Expectancy:** +0.212R | **Win Rate:** 37.0% | **Trades:** 95

**How to Trade:**
1. Wait for 1000 ORB to form (10:00-10:05)
2. **NO FILTER** - take all signals
3. Entry: First 1m close outside ORB → NEXT 1m OPEN
4. Stop: Full ORB edge
5. Risk: |Entry - Stop|
6. Target: Entry ± (2.5 × Risk)

**Strong performer:**
- Good balance of win rate and reward
- Consistent expectancy
- Reliable edge

---

### **1000 ORB RR=3.0 (CROWN JEWEL) ⭐**
**Expectancy:** +0.308R | **Win Rate:** 35.9% | **Trades:** 95

**How to Trade:**
1. Wait for 1000 ORB to form (10:00-10:05)
2. **NO FILTER** - take all signals
3. Entry: First 1m close outside ORB → NEXT 1m OPEN
4. Stop: Full ORB edge
5. Risk: |Entry - Stop|
6. Target: Entry ± (3.0 × Risk)

**BEST OVERALL STRATEGY:**
- Highest expectancy (+0.308R)
- Large sample (95 trades)
- Reliable edge with big winners

---

## 📊 1100 ORB STRATEGIES (2 variants - FILTERED, NEWLY RESCUED)

### **1100 ORB RR=2.5 + SMALL_ORB Filter**
**Expectancy:** +0.196R | **Win Rate:** 38.5% | **Trades:** 39

**How to Trade:**
1. Wait for 1100 ORB to form (11:00-11:05)
2. **FILTER CHECK (CRITICAL):**
   ```
   Calculate: ORB_size / ATR_20
   If ratio < 0.15 → TRADE
   If ratio >= 0.15 → SKIP (no edge)
   ```
3. Entry: First 1m close outside ORB → NEXT 1m OPEN
4. Stop: Full ORB edge
5. Risk: |Entry - Stop|
6. Target: Entry ± (2.5 × Risk)

**Example with Filter:**
```
ORB: High 4505.0, Low 4500.0
ORB Size: 5.0 points
ATR(20): 40.0 points
Ratio: 5.0 / 40.0 = 0.125 < 0.15 ✅ PASS

Signal: 1m close at 4506.0 (ABOVE ORB)
Entry: NEXT 1m open at 4507.0
Stop: 4500.0 (ORB low)
Risk: 4507 - 4500 = 7.0 points
Target: 4507 + (2.5 × 7) = 4524.5
```

**Why Filter:**
- Unfiltered 1100 ORB fails (-0.100R)
- SMALL_ORB filter rescues it (+0.196R)
- Only trade tight ORBs (< 15% ATR)

---

### **1100 ORB RR=3.0 + SMALL_ORB Filter (AGGRESSIVE)**
**Expectancy:** +0.246R | **Win Rate:** 35.1% | **Trades:** 37

**How to Trade:**
1. Wait for 1100 ORB to form (11:00-11:05)
2. **FILTER CHECK (CRITICAL):**
   ```
   Calculate: ORB_size / ATR_20
   If ratio < 0.15 → TRADE
   If ratio >= 0.15 → SKIP (no edge)
   ```
3. Entry: First 1m close outside ORB → NEXT 1m OPEN
4. Stop: Full ORB edge
5. Risk: |Entry - Stop|
6. Target: Entry ± (3.0 × Risk)

**Why RR=3.0:**
- Even better expectancy (+0.246R vs +0.196R)
- Lower win rate (35%) but HUGE winners
- Best for trending days

**Why Filter:**
- Unfiltered 1100 ORB RR=3.0 FAILS catastrophically (-0.188R)
- SMALL_ORB filter RESCUES it completely (+0.246R)
- 0.434R improvement from filter alone!

---

## 🔧 CALCULATING ATR(20)

**What is ATR(20)?**
- Average True Range over 20 periods
- Measures typical price movement
- Used for ORB size filter normalization

**How to Calculate:**
```python
# In your platform:
1. Add ATR indicator (period = 20)
2. Read value at ORB formation time
3. Compare ORB size to ATR

# Example:
ATR(20) = 40.0 points
ORB size = 5.0 points
Ratio = 5.0 / 40.0 = 0.125 (12.5%)

If ratio < 15% → TRADE
```

**In Trading View:**
1. Add indicator: ATR (Length=20)
2. At 11:05, read ATR value
3. Calculate: ORB / ATR
4. Trade if < 0.15

---

## 📊 RETIRED STRATEGIES (Keep for Reference)

### **1000 ORB RR=1.5 (MARGINAL)**
**Expectancy:** +0.098R | **Win Rate:** 49.0% | **Trades:** 100
**Status:** RETIRED (borderline survival, may fail in live slippage)

**Why Retired:**
- Expectancy +0.098R (below +0.15R threshold)
- High win rate (49%) but small winners
- Live slippage may push this negative
- **DO NOT TRADE** - use RR=2.0+ instead

---

## ❌ REJECTED STRATEGIES (DO NOT TRADE)

### **1100 ORB (Unfiltered)**
**Status:** REJECTED (all RR variants fail without filter)
- RR=1.5: -0.065R
- RR=2.0: +0.003R (breakeven)

**Why Rejected:**
- Mid-session ORB (11:00)
- Asia session incomplete
- Choppy, no directional bias
- **ONLY works with SMALL_ORB filter**

### **1800 ORB (All variants)**
**Status:** REJECTED (all fail)
- RR=1.5: -0.075R
- RR=2.0: -0.047R
- RR=2.5: -0.101R
- RR=3.0: -0.171R

**Why Rejected:**
- London open (18:00) is choppy
- No follow-through
- High friction impact
- Even filtered versions fail
- **DO NOT TRADE 1800 ORB**

---

## 💰 POSITION SIZING

**Risk Per Trade:** 1-2% of account (conservative)

**Example ($50,000 account, 1% risk):**
```
Account: $50,000
Risk per trade: $500 (1%)

If Risk = 10 points:
Position Size = $500 / (10 points × $10/point) = 5 contracts

If Risk = 20 points:
Position Size = $500 / (20 points × $10/point) = 2.5 → 2 contracts
```

**MGC Contract Specs:**
- Point Value: $10 per point
- Tick Size: $0.10 (1 cent)
- Tick Value: $1.00
- Min Risk: ~$50 (5 points × $10)

---

## 🎯 QUICK REFERENCE TABLE

| Strategy | Exp (R) | WR (%) | Sample | Filter | Status |
|----------|---------|--------|--------|--------|--------|
| 0900 RR=1.5 | +0.198 | 51.2 | 87 | None | ✅ ACTIVE |
| 0900 RR=2.0 | +0.170 | 41.7 | 86 | None | ✅ ACTIVE |
| 0900 RR=2.5 | +0.257 | 38.1 | 86 | None | ✅ ACTIVE |
| 0900 RR=3.0 | +0.221 | 32.1 | 83 | None | ✅ ACTIVE |
| 1000 RR=2.0 | +0.166 | 43.4 | 99 | None | ✅ ACTIVE |
| 1000 RR=2.5 | +0.212 | 37.0 | 95 | None | ✅ ACTIVE |
| 1000 RR=3.0 | +0.308 | 35.9 | 95 | None | ✅ ACTIVE ⭐ |
| 1100 RR=2.5 | +0.196 | 38.5 | 39 | <15% ATR | ✅ ACTIVE |
| 1100 RR=3.0 | +0.246 | 35.1 | 37 | <15% ATR | ✅ ACTIVE |
| 1000 RR=1.5 | +0.098 | 49.0 | 100 | None | ⚠️ RETIRED |
| 1100 (unfilt) | NEG | - | - | - | ❌ REJECTED |
| 1800 (all) | NEG | - | - | - | ❌ REJECTED |

---

## 📝 TRADING CHECKLIST

**Pre-Trade:**
- [ ] ORB has formed (wait full 5 minutes)
- [ ] Check filter (if applicable)
- [ ] ATR calculated (for 1100 strategies)
- [ ] Position size calculated
- [ ] Risk tolerance checked

**Trade Execution:**
- [ ] Signal: 1m CLOSE outside ORB
- [ ] Entry: NEXT 1m OPEN (not signal candle!)
- [ ] Stop order placed immediately
- [ ] Target order placed
- [ ] Record entry price, stop, target

**Post-Trade:**
- [ ] Log outcome (WIN/LOSS)
- [ ] Record actual fill prices
- [ ] Calculate realized R-multiple
- [ ] Note any slippage
- [ ] Review for improvement

---

## 🚀 BEST PRACTICES

1. **ALWAYS wait for NEXT 1m OPEN** after signal (B-Entry model)
2. **NEVER skip the filter** on 1100 strategies (critical!)
3. **Calculate ATR(20)** in advance (ready before 11:00)
4. **Use limit orders** where possible (reduce slippage)
5. **Accept missed trades** (better than forcing bad entries)
6. **Track realized R** (not just win/loss)
7. **Review weekly** (edge degradation monitoring)

---

## 📞 SUPPORT

**Questions?** Review:
- `COMPREHENSIVE_FUNCTION_AUDIT.md` - System overview
- `CANONICAL_LOGIC.txt` - Calculation formulas (lines 76-98)
- `TCA.txt` - Transaction cost analysis
- `COST_MODEL_MGC_TRADOVATE.txt` - Friction specifications

**Generated by:** Claude (Sonnet 4.5)
**Date:** 2026-01-29
**Database:** gold.db (validated_setups table)
**Status:** HONEST - No lookahead bias, all strategies validated
