# ALL ORB STATUS - Complete Analysis

## MGC 1000 ORB Answer (Your Question)

**SL Mode:** FULL (stop at opposite edge)

**Validated Setups:**
- RR=2.0 | SL=full | WR=43.4% | ExpR=+0.215R | N=99 | **ACTIVE**
- RR=2.5 | SL=full | WR=38.9% | ExpR=+0.132R | N=95 | **ACTIVE**
- RR=3.0 | SL=full | WR=36.8% | ExpR=+0.132R | N=95 | **ACTIVE**
- RR=1.5 | SL=full | WR=49.0% | ExpR=+0.257R | N=100 | **RETIRED** (optimistic costs)
- RR=1.5 | SL=FULL | Filter=0.05 | WR=49.0% | ExpR=+0.250R | N=100 | **RETIRED** (duplicate)

**Historical Data:** 526 days, 518 trades (244 wins, 274 losses)

---

## Complete MGC ORB Status

### ✅ 0900 ORB (Asia Open)
**Historical Performance:** 526 days, 496 trades
- Win Rate: 45.6% (226W/270L)
- Avg R: -0.09R (before costs)
- Avg ORB Size: 2.94 points

**Validated Setups:** 4 ACTIVE
- RR=1.5 | SL=full | WR=52.9% | ExpR=+0.120R | N=87 | **ACTIVE**
- RR=2.0 | SL=full | WR=43.0% | ExpR=+0.000R | N=86 | **ACTIVE**
- RR=2.5 | SL=full | WR=39.5% | ExpR=+0.000R | N=86 | **ACTIVE**
- RR=3.0 | SL=full | WR=33.7% | ExpR=+0.000R | N=83 | **ACTIVE**

**Notes:** London L4_CONSOLIDATION filter applied

---

### ✅ 1000 ORB (Asia Mid)
**Historical Performance:** 526 days, 518 trades
- Win Rate: 47.1% (244W/274L)
- Avg R: -0.06R (before costs)
- Avg ORB Size: 2.82 points

**Validated Setups:** 3 ACTIVE, 2 RETIRED
- RR=2.0 | SL=full | WR=43.4% | ExpR=+0.215R | N=99 | **ACTIVE**
- RR=2.5 | SL=full | WR=38.9% | ExpR=+0.132R | N=95 | **ACTIVE**
- RR=3.0 | SL=full | WR=36.8% | ExpR=+0.132R | N=95 | **ACTIVE**
- RR=1.5 | SL=full | WR=49.0% | ExpR=+0.257R | N=100 | **RETIRED**
- RR=1.5 | SL=FULL | Filter=0.05 | WR=49.0% | ExpR=+0.250R | N=100 | **RETIRED**

**Notes:** London L4_CONSOLIDATION filter applied

---

### ⚠️ 1100 ORB (Asia Late)
**Historical Performance:** 526 days, 497 trades
- Win Rate: 53.3% (265W/232L) ⭐ **BEST WIN RATE**
- Avg R: +0.07R (before costs)
- Avg ORB Size: 4.49 points

**Validated Setups:** 2 ACTIVE, 2 REJECTED
- RR=2.5 | SL=full | Filter=0.15 | WR=38.5% | ExpR=+0.196R | N=39 | **ACTIVE**
- RR=3.0 | SL=full | Filter=0.15 | WR=35.1% | ExpR=+0.246R | N=37 | **ACTIVE**
- RR=1.5 | SL=full | WR=41.5% | ExpR=+0.223R | N=176 | **REJECTED** (negative after costs)
- RR=2.0 | SL=full | WR=37.1% | ExpR=+0.000R | N=167 | **REJECTED** (negative after costs)

**Notes:** RESCUED with SMALL_ORB filter (<0.15 points) - requires ORB size filter to work

---

### ❌ 1800 ORB (London Open)
**Historical Performance:** 525 days, 516 trades
- Win Rate: 53.5% (276W/240L) ⭐ **BEST WIN RATE**
- Avg R: +0.07R (before costs)
- Avg ORB Size: 3.03 points

**Validated Setups:** ALL REJECTED ❌
- RR=1.5 | SL=full | WR=41.6% | ExpR=+0.125R | N=89 | **REJECTED**
- RR=2.0 | SL=full | WR=35.6% | ExpR=+0.000R | N=87 | **REJECTED**
- RR=2.5 | SL=full | WR=28.7% | ExpR=+0.000R | N=80 | **REJECTED**
- RR=3.0 | SL=full | WR=23.1% | ExpR=+0.000R | N=78 | **REJECTED**

**Status:** FAILED - Negative expectancy after $8.40 friction despite 53.5% raw win rate

**Problem:** ORB breaks but doesn't extend far enough to hit higher RR targets before reversing

---

### 🔍 2300 ORB (NY Futures Open)
**Historical Performance:** 525 days, 520 trades
- Win Rate: 48.5% (252W/268L)
- Avg R: -0.03R (before costs)
- Avg ORB Size: 4.49 points

**Validated Setups:** NONE ⚠️

**Status:** NOT TESTED - Has data but never validated

**Action Needed:** Run autonomous_strategy_validator.py for this ORB

---

### 🔍 0030 ORB (NY Cash Open)
**Historical Performance:** 525 days, 514 trades
- Win Rate: 46.9% (241W/273L)
- Avg R: -0.06R (before costs)
- Avg ORB Size: 4.90 points (largest ORB)

**Validated Setups:** NONE ⚠️

**Status:** NOT TESTED - Has data but never validated

**Action Needed:** Run autonomous_strategy_validator.py for this ORB

---

## Summary By Status

### ACTIVE Setups (9 MGC)
- **0900 ORB:** 4 setups (RR 1.5-3.0)
- **1000 ORB:** 3 setups (RR 2.0-3.0)
- **1100 ORB:** 2 setups (RR 2.5-3.0, requires Filter=0.15)

### RETIRED Setups (2 MGC)
- **1000 ORB:** 2 setups (RR 1.5, optimistic cost assumptions)

### REJECTED Setups (6 MGC)
- **1100 ORB:** 2 setups (RR 1.5-2.0, negative after costs)
- **1800 ORB:** 4 setups (RR 1.5-3.0, all negative after costs)

### NOT TESTED (2 MGC)
- **2300 ORB:** Has 520 trades, never validated
- **0030 ORB:** Has 514 trades, never validated

---

## NQ & MPL Status

**Current Status:** NO DATA in daily_features

**Reason:** `pipeline/build_daily_features.py` only processes MGC

**NQ validated_setups:** 5 setups (but no daily_features to back them)
**MPL validated_setups:** 6 setups (but no daily_features to back them)

**Critical Issue:** NQ and MPL setups in validated_setups table have NO backtested data in daily_features. They were validated using a different process (not documented).

**Action Needed:**
1. Run `build_daily_features.py` for NQ and MPL
2. Re-validate NQ/MPL setups against historical data
3. Or remove NQ/MPL from validated_setups if not properly tested

---

## Key Findings (bugs.txt style)

### 🐛 Bug #1: MGC 2300 and 0030 ORBs Never Validated
**Problem:**
- daily_features has 520+ trades for each ORB
- No validated_setups entries
- Never tested despite having full dataset

**Impact:**
- Missing potential trading opportunities
- Incomplete strategy coverage

**Fix Required:**
```bash
python scripts/audit/autonomous_strategy_validator.py
# Add 2300 and 0030 to validation run
```

---

### 🐛 Bug #2: NQ & MPL Have No Historical Data
**Problem:**
- validated_setups table has 5 NQ + 6 MPL setups
- daily_features table has ZERO NQ/MPL data
- Strategies cannot be verified against historical bars

**Impact:**
- NQ/MPL setups are unverified
- Cannot trust win rates or expectancy values
- Apps display strategies without proof

**Fix Required:**
```bash
# Backfill NQ data
python backfill_databento_continuous.py 2024-01-01 2026-01-15 --symbol NQ

# Build daily features for NQ
python pipeline/build_daily_features.py 2024-01-01 2026-01-15 --instrument NQ

# Repeat for MPL
python backfill_databento_continuous.py 2024-01-01 2026-01-15 --symbol MPL
python pipeline/build_daily_features.py 2024-01-01 2026-01-15 --instrument MPL

# Re-validate
python scripts/audit/autonomous_strategy_validator.py --instrument NQ
python scripts/audit/autonomous_strategy_validator.py --instrument MPL
```

---

### 🐛 Bug #3: Win Rate Display Bug in validated_setups
**Problem:**
- Win rates stored as decimals (0.434 = 43.4%)
- Some entries show as 0.4% when they should be 40%+
- Inconsistent storage format

**Impact:**
- Confusing when querying database directly
- May cause display errors in apps

**Fix Required:**
Check config_generator.py and ensure consistent win_rate formatting.

---

## Recommendations

### Immediate Actions
1. **Validate MGC 2300/0030 ORBs** - Run autonomous_strategy_validator.py
2. **Backfill NQ/MPL data** - Get historical bars and build daily_features
3. **Fix win_rate storage** - Standardize format in validated_setups

### Strategic Questions
1. **Why are 2300/0030 not validated?** - Design decision or oversight?
2. **Should NQ/MPL be removed?** - If no historical data, should they be in validated_setups?
3. **1800 ORB failures** - Can filters rescue this ORB like 1100?

---

## All SL Modes

**MGC:** ALL use SL=full (stop at opposite edge)
**NQ:** ALL use SL=HALF (stop at midpoint)
**MPL:** ALL use SL=FULL (stop at opposite edge)

**Why different?**
- MGC: Larger moves, can afford full stop
- NQ: Tighter ranges, needs smaller stop (half) to avoid getting stopped out
- MPL: Similar to MGC

---

**Generated:** 2026-01-29
**Data Range:** 2024-01-02 to 2026-01-15 (526 days)
**Total MGC Trades:** 3,561 across 6 ORBs
