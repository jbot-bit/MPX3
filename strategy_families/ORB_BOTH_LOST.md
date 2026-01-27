# STRATEGY FAMILY: ORB_BOTH_LOST

## 1. Purpose
Exploit sequential failure pattern: when BOTH 0900 and 1000 ORBs fail, 1100 ORB breakout has higher probability (trapped traders, exhausted false moves).

## 2. Core Assumption
When both early NY ORBs (0900, 1000) false breakout on the same day, the market has exhausted false moves and trapped traders twice. The 1100 ORB represents the TRUE directional move.

## 3. Baseline Logic (CANONICAL)
- Entry: First 1-minute close outside ORB range (11:00-11:05)
- Stop: Opposite side of ORB (full ORB size)
- Target: RR × ORB size (1.5 only - higher RRs not tested)
- Trade lifetime: 4-hour scan window from ORB close
- Cost basis for approval: **$8.40 RT** (commission $2.40 + spread_double $2.00 + slippage $4.00)

**Filter**: BOTH 0900 and 1000 ORBs must have LOST today.
- `orb_0900_outcome = 'LOSS' AND orb_1000_outcome = 'LOSS'`

This section is the **truth anchor**.

## 4. Variants (RR / timing only)

### 1100 ORB RR=1.5 (ONLY VARIANT)
- RR=1.5: +0.223R (only survives +25% stress)

No other RR levels tested yet.

## 5. Status
- **BASELINE_MARGINAL**: RR=1.5 (only survives +25% stress, weaker edge)
- Date locked: 2026-01-27
- Evidence file(s): `analysis/baseline_strategy_revalidation.py`, `test_all_7_strategies.py`
- Database ID: 26

## 6. Conditional Extensions (OPTIONAL)

None tested yet.

**Possible extensions:**
- L2_SWEEP_LOW sub-filter (historical research showed +0.540R)
- L1_SWEEP_HIGH sub-filter (historical research showed +0.453R)
- ML high-confidence filter (historical research showed +0.373R)

Note: These extensions found in `1100_ORB_VALIDATED_SETUPS.md` but not yet validated with current $8.40 cost model.

## 7. What This Family Is NOT
- NOT a standalone ORB strategy (requires 0900/1000 outcome context)
- NOT a time-of-day strategy (specifically depends on sequential pattern)
- NOT a momentum strategy (counter-trend - trades AFTER failures)
- NOT applicable without sequential context (must check earlier ORBs)

## 8. Open Questions
- Why is this edge weaker than L4_CONSOLIDATION? (only survives +25% vs +50%)
- Do higher RR levels (2.0, 2.5, 3.0) work with BOTH_LOST filter?
- Is there a regime where BOTH_LOST stops working?
- Can we predict BOTH_LOST days in advance? (forward-looking)
- Do the L2_SWEEP_LOW/L1_SWEEP_HIGH extensions still work at $8.40?

---

**Last Updated**: 2026-01-27
**Family Owner**: MGC Gold Trading System
**Validation Status**: USE WITH CAUTION (marginal edge, smaller position size recommended)
