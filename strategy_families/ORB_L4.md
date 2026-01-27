# STRATEGY FAMILY: ORB_L4

## 1. Purpose
Exploit mean reversion after London consolidation inside Asia range (L4). When London respects Asia boundaries, NY session ORB breakouts have higher probability.

## 2. Core Assumption
When London session stays inside Asia range (L4_CONSOLIDATION), it signals lower volatility and increases probability that ORB breakouts will follow through during NY session.

## 3. Baseline Logic (CANONICAL)
- Entry: First 1-minute close outside ORB range (09:00-09:05 or 10:00-10:05)
- Stop: Opposite side of ORB (full ORB size)
- Target: RR × ORB size (1.5, 2.0, 2.5, or 3.0)
- Trade lifetime: 4-hour scan window from ORB close
- Cost basis for approval: **$8.40 RT** (updated 2026-01-27 for honest double-spread accounting)
  - Commission: $2.40
  - Spread (double): $2.00 (entry + exit)
  - Slippage: $4.00 (additional beyond spread)

**Filter**: Yesterday's London session must have stayed inside Asia range.
- `london_high <= asia_high AND london_low >= asia_low`

This section is the **truth anchor**.

## 4. Variants (RR / timing only)

### 1000 ORB (STRONGEST)
- RR=1.5: +0.423R (survives +50% stress)
- RR=2.0: +0.708R (survives +50% stress)
- RR=2.5: +0.993R (survives +50% stress)
- **RR=3.0: +1.277R (survives +50% stress)** ⭐ BEST

### 0900 ORB (WEAKER)
- RR=1.5: +0.235R (only survives +25% stress)

No new logic allowed.

## 5. Status
- **BASELINE_APPROVED**: 1000 ORB (all 4 RR levels)
- **BASELINE_MARGINAL**: 0900 ORB (RR=1.5 only) - RE-INVESTIGATION NEEDED (see section 5.1)
- Date locked: 2026-01-27
- Evidence file(s):
  - `analysis/baseline_strategy_revalidation.py` (standard validation)
  - `test_all_7_strategies.py` (production testing)
  - `analysis/investigate_l4_edge_structure.py` (root cause investigation)
  - `analysis/output/INVESTIGATION_COMPLETE.md` (final report)
- Database IDs: 20, 21, 22, 23 (1000 ORB), 25 (0900 ORB - pending re-evaluation)

### 5.1 L4 Freshness Decay Discovery (2026-01-27)

**CRITICAL FINDING**: L4 predictive power decays with time since formation.

**Investigation Results** (RR=3.0, vs random baseline):
- **0900 ORB** (2 hours after L4): N=90, **+0.267R edge** [BEATS RANDOM] ✓
- **1000 ORB** (3 hours after L4): N=90, **+0.433R edge** [BEATS RANDOM] ✓
- **1100 ORB** (4 hours after L4): N=90, **+0.150R edge** [BEATS RANDOM] ✓
- **1800 ORB** (11 hours after L4): N=90, **-0.067R edge** [FAILS] ✗
- **2300 ORB** (16 hours after L4): N=90, **-0.027R edge** [FAILS] ✗
- **0030 ORB** (17.5 hours after L4): N=90, **-0.293R edge** [FAILS] ✗

**Key Insights**:
- L4 signal works FRESH (<4 hours): 0900, 1000, 1100 all beat random
- L4 signal fails STALE (>10 hours): 1800, 2300, 0030 all fail random test
- **L4 is time-sensitive** - only works near formation time
- This explains why night ORBs failed despite L4 filter

**Root Cause Analysis** (1000 ORB ablation at RR=3.0):
- Baseline (no filter): +0.035R edge vs random (minimal)
- **+ L4 filter: +0.433R edge vs random** (primary driver)
- + L4 + High Vol: +0.508R edge vs random (best)

**Conclusion**: L4 filter IS the edge, but it expires after ~4 hours.

## 6. Conditional Extensions (OPTIONAL)

### 5min Confirmation Filter
- Requires 5min candle to also close outside ORB within scan window
- Status: **Phase 2 complete, Phase 3 pending** (DO NOT USE YET)
- Performance delta vs baseline:
  - 1000 ORB: +0.156R to +0.249R improvement (robust in walk-forward)
  - 0900 ORB: 44% retention (OVERFITTING - rejected)
- File: `analysis/research_5min_filter_phase2_walkforward.py`

## 7. What This Family Is NOT
- NOT a momentum strategy (relies on consolidation, not trending)
- NOT a breakout failure strategy (trades WITH the breakout, not against it)
- NOT a time-of-day strategy (works at 0900 and 1000, but 1000 is stronger)
- NOT applicable to other session types (L1/L2/L3) - L4 only

## 8. Open Questions
- ✅ ANSWERED: Why is 1000 ORB significantly stronger than 0900 ORB?
  - 1000 ORB is 3 hours after L4 formation (optimal freshness)
  - 0900 ORB is 2 hours after L4 formation (also works, but weaker)
  - 1100 ORB is 4 hours after L4 formation (works but edge degrading)
- ✅ ANSWERED: Why do night ORBs (1800/2300/0030) fail?
  - L4 signal decay - stale after 4 hours
  - 1800 ORB is 11 hours stale, 2300/0030 are 16-17.5 hours stale
- Does L4 pattern work on other instruments (NQ, MPL)?
- Is there a regime where L4 stops working? (trend vs range markets)
- Can we predict L4 days in advance? (forward-looking filter)

### 8.1 Candidate Expansions (Require Full Validation)

Based on L4 freshness decay investigation, two additional ORB times beat random:

**1100 ORB + L4 Filter**:
- Edge: +0.150R vs random (RR=3.0)
- Sample: N=90 trades
- Status: CANDIDATE (needs full 7-phase validation at all RR levels)
- Freshness: 4 hours after L4 (edge degrading but still positive)

**0900 ORB + L4 Filter** (Re-evaluation):
- Edge: +0.267R vs random (RR=3.0) - STRONGER than original validation suggested
- Sample: N=90 trades
- Status: NEEDS RE-VALIDATION (original validation was at RR=1.5 only, may have underestimated)
- Freshness: 2 hours after L4 (fresh signal)

**Next Steps**: Run full 7-phase validation (temporal, regime, walk-forward, stress tests) on both candidates before promoting to production.

---

**Last Updated**: 2026-01-27
**Family Owner**: MGC Gold Trading System
**Validation Status**: PRODUCTION READY (1000 ORB), USE WITH CAUTION (0900 ORB)
