# STRATEGY FAMILY: ORB_NIGHT

## 1. Purpose
Explore night session ORBs (2300, 0030) for potential edges that don't exist in day sessions. Night markets have different liquidity, volatility, and participant profiles.

## 2. Core Assumption
Night ORBs (2300 Brisbane = 23:00, 0030 Brisbane = 00:30 next day) may have different behavior than day ORBs due to:
- Lower liquidity (thinner order books)
- Different participant mix (algo-heavy, fewer retail)
- NY session closing effects (2300) or Asia opening effects (0030)

## 3. Baseline Logic (CANONICAL)
- Entry: First 1-minute close outside ORB range (23:00-23:05 or 00:30-00:35)
- Stop: Opposite side of ORB (full ORB size)
- Target: RR × ORB size (tested 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 8.0, 10.0)
- Trade lifetime: 4-hour scan window from ORB close
- Cost basis for approval: **$8.40 RT** (commission $2.40 + spread_double $2.00 + slippage $4.00)

**Filter**: None (baseline), plus extensive ML/regime/sequential testing.

This section is the **truth anchor**.

## 4. Variants (RR / timing only)

### 2300 ORB (RESEARCH ONLY - NOT VALIDATED)
**Baseline (no filters):**
- RR=2.0: +0.162R (N=522)
- RR=3.0: +0.549R (N=522)

**Best filters found (IN-SAMPLE - NOT VALIDATED):**
- pre_ny_range_high + RR=3.0: +0.791R (N=130)
- L4_CONSOLIDATION + RR=3.0: +0.646R (N=90)

### 0030 ORB (RESEARCH ONLY - NOT VALIDATED)
**Baseline (no filters):**
- RR=2.0: +0.101R (N=523)
- RR=3.0: +0.468R (N=523)

**Best filters found (IN-SAMPLE - NOT VALIDATED):**
- ny_range_high + RR=3.0: +0.870R (N=131)
- london_range_high + RR=3.0: +0.678R (N=131)

**ML Top Features:**
- 2300 ORB: london_range, asia_range, rsi_at_0030
- 0030 ORB: ny_range, orb_size, rsi_at_0030

## 5. Status
- **REJECTED** (final investigation complete)
- Date tested: 2026-01-27
- Evidence files:
  - `analysis/research_night_orb_comprehensive.py` (Phase 1-2: ML discovery)
  - `analysis/validate_night_orb_baselines.py` (Phase 4: Standard validation - PASSED)
  - `analysis/brutal_stress_test_night_orbs.py` (Brutal stress test - FAILED random test)
  - `analysis/investigate_l4_edge_structure.py` (Root cause investigation - CONFIRMED REJECTION)
  - `analysis/output/INVESTIGATION_COMPLETE.md` (Final report)
- Database IDs: None (never promoted to validated_setups)

**FINAL VERDICT: REJECTED**

**Why Night ORBs Fail:**

1. **L4 Signal Decay** (ROOT CAUSE):
   - L4 consolidation filter works <4 hours after formation (0900/1000/1100)
   - L4 signal is STALE at night ORBs (>16 hours after London close)
   - 2300 ORB: 16 hours stale → -0.027R edge vs random
   - 0030 ORB: 17.5 hours stale → -0.293R edge vs random

2. **Random Entry Comparison Test** (VETO GATE):
   - 2300 ORB: +0.514R vs random +0.612R = -0.099R edge [FAIL]
   - 0030 ORB: +0.436R vs random +0.632R = -0.196R edge [FAIL]
   - ORB timing adds NO value - positive expectancy was RR=3.0 math, not skill

3. **Even L4 Filter Doesn't Help**:
   - 2300 ORB + L4: Negative edge vs random
   - 0030 ORB + L4: Negative edge vs random
   - Not salvageable with additional filters

**Key Insight from Investigation:**
- 0030 ORB occurs during NY cash hours (09:30-10:30 NY time)
- This proves thin liquidity is NOT the reason for failure
- The real reason: L4 predictive power decays with time since formation
- By 2300/0030 Brisbane time, L4 signal is too old to be useful

## 6. Conditional Extensions (OPTIONAL)

**NOT APPLICABLE** - Family REJECTED at baseline level.

No filters can salvage night ORBs because the root cause is L4 signal decay (>16 hours stale).

## 7. What This Family Is NOT
- NOT validated (REJECTED after full investigation)
- NOT suitable for trading (no edge vs random entry)
- NOT salvageable with filters (L4 signal too stale)
- NOT a liquidity issue (0030 = NY cash hours, still fails)

## 8. Open Questions
- ✅ ANSWERED: Do night ORBs have genuine edges? NO - fail random entry test
- ✅ ANSWERED: Are results curve-fit? N/A - never reached production
- ✅ ANSWERED: Why do night ORBs fail? L4 signal decay (>16 hours stale)
- ✅ ANSWERED: Can filters improve baseline? NO - even L4 filter negative vs random
- ✅ ANSWERED: Is it a liquidity issue? NO - 0030 = NY cash hours, still fails

---

**Last Updated**: 2026-01-27 (INVESTIGATION COMPLETE)
**Family Owner**: MGC Gold Trading System
**Validation Status**: ❌ REJECTED - NOT PRODUCTION READY

**HONESTY OVER OUTCOME**: Night ORBs looked promising (147-151% out-of-sample retention), but failed random entry comparison test. L4 signal decay investigation revealed root cause: L4 predictive power expires after 4 hours. Better to discover this in research than live trading.
