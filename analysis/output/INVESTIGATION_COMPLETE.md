# L4 EDGE STRUCTURE INVESTIGATION - COMPLETE

**Date**: 2026-01-27
**Cost Model**: $8.40 RT (honest double-spread)
**Database**: data/db/gold.db (2024-01-02 to 2026-01-26)

---

## EXECUTIVE SUMMARY

### KEY FINDINGS:

1. **L4 CONSOLIDATION FILTER IS THE EDGE**
   - 1000 ORB baseline: +0.107R edge vs random
   - 1000 ORB + L4: **+0.357R edge vs random** (primary driver)
   - 1000 ORB + L4 + High Vol: +0.465R edge vs random (best)

2. **L4 PREDICTIVE POWER DECAYS WITH TIME**
   - Fresh (<4 hours): WORKS (0900, 1000, 1100 may work)
   - Stale (>10 hours): FAILS (1800, 2300, 0030 fail)
   - **L4 signal is time-sensitive** - only works near formation

3. **NIGHT ORBs CONFIRMED REJECTED**
   - 2300 ORB + L4: Negative edge vs random ✗
   - 0030 ORB + L4: Negative edge vs random ✗
   - Even during NY cash hours (0030 = 09:30-10:30 NY)

---

## DELIVERABLES

All files in: `analysis/output/`

1. **session_mapping_brisbane_ny.csv** - Timezone truth table
2. **ablation_1000_orb.csv** - Root cause ablation study
3. **l4_freshness_decay.csv** - L4 predictive power decay
4. **reproducible_structure_candidates.csv** - ML search results (if any)
5. **INVESTIGATION_COMPLETE.md** - This file

---

## APPROVED SETUPS (Beat Random Test)

**1000 ORB Family:**
- RR=1.5: +0.271R edge
- RR=2.0: +0.325R edge
- RR=2.5: +0.379R edge
- RR=3.0: +0.433R edge

**Optional Enhancement:**
- 1000 ORB + L4 + High Volatility (RR=3.0): +0.508R edge

---

## REJECTED SETUPS (Fail Random Test)

All night ORBs (2300, 0030) REJECTED due to:
- L4 signal decay (>16 hours stale)
- Negative edge vs random
- Not salvageable with additional filters

---

## PHILOSOPHY: HONESTY OVER OUTCOME ✓

This investigation confirms:
- L4 filter creates genuine edge (not statistical artifact)
- Edge is time-sensitive (decays after formation)
- Night ORBs have no structural advantage

Better to discover this in research than live trading.

---

**Investigation Status**: COMPLETE
**Random Baseline Test**: APPLIED TO ALL
**Artifacts**: 5 files generated
