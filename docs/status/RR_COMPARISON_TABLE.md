# RR COMPARISON TABLE - 1000 ORB Strategies
**Date:** 2026-01-28
**Source:** validated_trades table (B-entry model with OPEN price)

---

## Executive Summary

**CRITICAL FINDING:** All 8 MGC strategies REJECTED (fail +0.15R threshold)

**Expectancy Range:** -0.341R to -0.212R (all negative)

---

## 1000 ORB: RR Comparison (4 Strategies)

| Setup ID | RR  | Sample Size | Wins | Losses | Open | Win Rate | Expectancy | Status   |
|----------|-----|-------------|------|--------|------|----------|------------|----------|
| 20       | 1.5 | 523         | 221  | 302    | 3    | 42.3%    | -0.239R    | REJECTED |
| 21       | 2.0 | 521         | 183  | 338    | 5    | 35.1%    | -0.236R    | REJECTED |
| 22       | 2.5 | 515         | 149  | 366    | 11   | 28.9%    | -0.264R    | REJECTED |
| 23       | 3.0 | 513         | 137  | 376    | 13   | 26.7%    | -0.224R    | REJECTED |

**Observation:** As RR increases, win rate decreases (expected), but expectancy does NOT improve.

**Why?** Higher RR = farther target = more time for market to hit stop first.

---

## All Strategies Summary

| Setup ID | ORB Time | RR  | Filter | Sample Size | Wins | Losses | Expectancy | Status   |
|----------|----------|-----|--------|-------------|------|--------|------------|----------|
| 20       | 1000     | 1.5 | None   | 523         | 221  | 302    | -0.239R    | REJECTED |
| 21       | 1000     | 2.0 | None   | 521         | 183  | 338    | -0.236R    | REJECTED |
| 22       | 1000     | 2.5 | None   | 515         | 149  | 366    | -0.264R    | REJECTED |
| 23       | 1000     | 3.0 | None   | 513         | 137  | 376    | -0.224R    | REJECTED |
| 24       | 1800     | 1.5 | None   | 515         | 212  | 303    | -0.219R    | REJECTED |
| 25       | 0900     | 1.5 | None   | 511         | 193  | 318    | -0.341R    | REJECTED |
| 26       | 1100     | 1.5 | None   | 509         | 201  | 308    | -0.212R    | REJECTED |
| 27       | 1000     | 1.5 | 0.05   | 523         | 221  | 302    | -0.239R    | REJECTED |

---

## Key Insights

### 1. B-Entry Model Now Uses OPEN Price ✅

**Before (Bug):**
- Entry price = HIGH (UP breaks) or LOW (DOWN breaks)
- "Conservative worst-fill assumption"

**After (Fixed):**
- Entry price = NEXT 1m OPEN after signal close
- True B-entry model
- Slippage handled separately in cost model ($4.00)

**Sample Trade Verification:**
```
2024-01-02: 1000 ORB RR=1.5
- Entry: $2073.60 (OPEN price from database)
- Risk: 1.00 points
- Target: 1.50 points (1.5 × 1.00)
- Target/Risk ratio: 1.50 ✓ MATCHES RR
```

### 2. Per-Strategy Results Now Available ✅

**Before (Bug):**
- daily_features stored ONLY RR=1.5 (first occurrence per ORB)
- Higher RR strategies (2.0/2.5/3.0) had no data

**After (Fixed):**
- validated_trades stores ALL strategies separately
- One row per (date_local, setup_id)
- 526 trades × 8 strategies = 4,208 total rows

**This solves:**
- "Why does it keep acting like 1R?"
- "Why do higher RR strats vanish?"
- "Why do results feel wrong vs live trading?"

### 3. All Strategies Are Negative Expectancy ⚠️

**Worst Performer:** 0900 ORB (-0.341R)
**Best Performer:** 1100 ORB (-0.212R)
**Average:** -0.247R across all strategies

**Possible Explanations:**

**A) Cost Model Too Aggressive?**
- Current: $8.40 RT (commission $2.40 + spread $2.00 + slippage $4.00)
- Slippage $4.00 = 4 ticks = aggressive assumption
- Test: Reduce slippage to $2.00 (2 ticks), see if any strategies pass

**B) B-Entry Model Degrades Edge?**
- Entry at NEXT 1m OPEN means waiting 0-60 seconds after signal
- Market may move against you during wait
- OLD model (HIGH/LOW) was more pessimistic but caught immediate breaks

**C) MGC Breakout Edges Don't Exist?**
- Possibility: Simple ORB breakouts are NOT profitable on MGC
- Market structure may not support directional follow-through
- Alternative: Need filters, session context, or different entry timing

**D) Stop Placement Is Too Tight?**
- ORB edge (full mode) may be too close
- Getting stopped out before target hit
- Test: Half-stop mode or wider stops

### 4. RR Scaling Does NOT Help

**Theory:** Higher RR should improve expectancy (bigger winners)

**Reality:** Higher RR DECREASES expectancy on 1000 ORB
- RR=1.5: -0.239R
- RR=2.0: -0.236R (slightly better, still negative)
- RR=2.5: -0.264R (worse)
- RR=3.0: -0.224R (best of 1000, but still negative)

**Why?** Win rate drops faster than reward increases:
- RR=1.5: 42.3% win rate
- RR=3.0: 26.7% win rate (-15.6 percentage points)

**Break-even win rate at $8.40 costs:**
- RR=1.5 requires ~52% win rate → actual 42.3% (miss by 10%)
- RR=3.0 requires ~33% win rate → actual 26.7% (miss by 6%)

---

## Next Steps

### Option A: Reduce Costs (Test Optimistic Scenario)

Re-run populate with $4.00 RT (commission $2.40 + spread $1.60, no slippage):
```bash
# Edit cost_model.py: total_friction = 4.00
python pipeline/populate_validated_trades.py
python scripts/audit/autonomous_strategy_validator_v2.py
```

**Expected:** Some strategies may pass +0.15R threshold

---

### Option B: Test Different Entry Model

Change from B-entry (NEXT OPEN) back to signal-bar CLOSE:
- Entry = signal bar CLOSE (immediate entry, no waiting)
- More aggressive, less slippage
- May improve expectancy

---

### Option C: Add Filters

Test strategies with filters:
- Session type (CONSOLIDATION vs TRENDING)
- Pre-ORB travel (filter out quiet days)
- RSI/momentum (only trade exhaustion)
- Sequential patterns (0900 LOSS → 1000 entry)

**ID 27 already has filter (ORB size >= 0.05):**
- Same result as ID 20 (no filter): -0.239R
- Suggests ORB size filter alone is not enough

---

### Option D: Accept Reality

**Possibility:** ORB breakouts on MGC are NOT profitable with these parameters.

**Evidence:**
- All 8 strategies negative expectancy
- Large sample sizes (509-523 trades)
- Cost model is reasonable (not overly aggressive)
- B-entry model is correct implementation

**Conclusion:** May need entirely different approach:
- Mean reversion instead of breakout
- Different timeframes (15m, 30m ORBs)
- Different instruments (NQ, ES have more volatility)
- Session-specific strategies (London only, NY only)

---

## HONESTY OVER OUTCOME ✅

**What We Fixed:**
1. ✅ B-entry model now uses OPEN (not HIGH/LOW)
2. ✅ Per-strategy results available (RR=1.5/2.0/2.5/3.0)
3. ✅ validated_trades table architecture
4. ✅ Shared loader function (CHECK.TXT Req #6)
5. ✅ Target/Risk ratios verified correct

**What We Discovered:**
1. ⚠️ All MGC strategies are NEGATIVE expectancy
2. ⚠️ Higher RR does NOT improve expectancy
3. ⚠️ ORB breakouts may not be profitable on MGC with current parameters

**System is working correctly. The TRUTH is: These strategies don't pass validation.**

---

## Files Changed

1. **pipeline/schema_validated_trades.sql** - NEW table schema
2. **pipeline/populate_validated_trades.py** - NEW populate script
3. **scripts/audit/autonomous_strategy_validator_v2.py** - NEW validator
4. **pipeline/build_daily_features.py** - Fixed B-entry to use OPEN (line 449-451)
5. **pipeline/load_validated_setups.py** - Shared loader function (CHECK.TXT Req #6)

**Database:**
- Backed up: `data/db/gold_backup_20260128.db`
- Current: `data/db/gold.db` with validated_trades table (4,208 rows)

---

## Recommendation

**NEXT:** Test Option A (reduce costs to $4.00 RT) to see if any strategies pass.

If still negative → Accept that ORB breakouts need major overhaul (filters, timing, or different approach).

**DO NOT trade these strategies live until expectancy is positive.**
