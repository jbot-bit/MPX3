# FINDINGS LOG - NEVER LOSE KNOWLEDGE AGAIN

**Purpose**: Record ALL important findings so we don't re-discover things.

**Rule**: EVERY significant finding goes here IMMEDIATELY.

---

## 2026-01-27 - BASELINE VALIDATION COMPLETE

### Key Finding: ONLY 1000 ORB is EXCELLENT

**What we learned:**
- 1000 ORB L4 (all RR levels) survives +50% cost stress
- 0900 ORB L4 only survives +25% stress (weaker)
- 1100 ORB BOTH_LOST only survives +25% stress (weaker)
- 1800 ORB RSI only survives +25% stress (weaker)

**Classification:**
- **BASELINE_APPROVED (4)**: 1000 ORB RR=1.5/2.0/2.5/3.0
- **BASELINE_MARGINAL (3)**: 0900/1100/1800 ORB RR=1.5
- **BASELINE_REJECTED (0)**: None

**What this means:**
- 1000 ORB is your core edge (robust across regimes, time, and cost stress)
- 0900/1100/1800 are tradable but weaker (use smaller size or skip)

**Data used:**
- Date range: 2024-01-02 to 2026-01-26 (746 days)
- Cost model: $7.40 RT (Tradovate production)
- Validation: 7-phase framework (ground truth, integrity, reconciliation, stats, stress, temporal, regime)

**File**: `analysis/baseline_strategy_revalidation.py`

---

## 2026-01-27 - 5MIN CONFIRMATION FILTER (DO NOT USE YET)

### Key Finding: Works for 1000/1100 ORB, OVERFITS on 0900 ORB

**What we learned:**
- 5min confirmation filter improves 1000 ORB (+0.156R to +0.249R)
- 5min confirmation filter improves 1100 ORB (+0.565R)
- 5min confirmation filter OVERFITS on 0900 ORB (44% retention out-of-sample)
- Does NOT help RSI strategies (momentum already filtered)

**Status**: Phase 2 complete, needs Phase 3-6 before deployment

**DO NOT DEPLOY until:**
- [ ] Phase 3: Regime analysis
- [ ] Phase 4: Stress testing
- [ ] Phase 5: Live paper trading (30+ trades)
- [ ] Phase 6: Production approval

**Files:**
- `analysis/research_5min_confirmation_filter.py`
- `analysis/research_5min_filter_phase1_robustness.py`
- `analysis/research_5min_filter_phase2_walkforward.py`
- `analysis/ADVANCED_FILTER_DATABASE.md`

---

## 2026-01-27 - SESSION TIMING UI

### Key Finding: Users confused about L4 timing

**What we learned:**
- L4_CONSOLIDATION checks PREVIOUS day's sessions
- At 10am Monday, checking Sunday's L4 status
- Users didn't understand this - needed clear UI

**Solution:**
- Added `trading_app/session_timing_helper.py`
- Shows "Yesterday was L4: YES/NO"
- Clear explanation in sidebar

**Status**: DEPLOYED in trading_hub app

**File**: `trading_app/session_timing_helper.py`

---

## 2026-01-27 - DATA RANGE CORRECTION

### Key Finding: We do NOT have 2020-2024 data

**What we learned:**
- Database only has: 2024-01-02 to 2026-01-26
- Initial Phase 2 test used WRONG date ranges (2020-2024 train)
- Corrected to: 2024-2025 H1 (train) vs 2025 H2-2026 (test)

**Impact:**
- Walk-forward test results are correct NOW
- Previous results with 2020 dates were hallucination

**Lesson**: ALWAYS check actual data range before testing

---

## TEMPLATE FOR NEW FINDINGS

**Date**: YYYY-MM-DD

**Finding**: [One sentence summary]

**What we learned:**
- Key point 1
- Key point 2
- Key point 3

**What this means:**
- [Practical implications]

**Status**: [DEPLOYED / IN PROGRESS / NEEDS VALIDATION / REJECTED]

**Files**: [List relevant files]

---

## CRITICAL PRINCIPLES

1. **HONESTY OVER OUTCOME** - Record failures too
2. **FAIL CLOSED** - If unclear, reject
3. **ONE SOURCE OF TRUTH** - Database is canonical
4. **TEST THE TESTS** - Audit the audits
5. **SIMPLE > COMPLEX** - Working system > perfect system

---

**Remember**: Every time you discover something important, ADD IT HERE.
