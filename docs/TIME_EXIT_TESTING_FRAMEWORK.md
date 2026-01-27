# Time-Based Exit Testing Framework

**Purpose:** Explore whether time-based exits add value to existing ORB strategies

**Philosophy:** Most variations will not work. Discovering this is part of the goal.

---

## Core Hypothesis

**Claim:** Some trades that go nowhere for T minutes are likely to continue going nowhere and should be exited early to preserve capital.

**Null Hypothesis:** Time-based exits do not improve expectancy (avg R per trade).

**Test:** Can we reject the null hypothesis with sufficient evidence?

---

## Testing Principles

### 1. Baseline First
- Always establish clean baseline performance
- Baseline = current strategy (entry, stop, target, no time exits)
- All modifications compared against THIS baseline

### 2. Incremental Expansion
- Start with ONE setup/variant
- If it works → test next
- If it fails → understand why before moving on
- Don't test everything at once

### 3. Out-of-Sample Always
- Use data NOT used for development
- 60-90 day window minimum
- Recent data preferred (market evolves)

### 4. Simple Rules Only
- Max 2-3 parameters
- Easy to explain and understand
- If you can't explain it simply, it's too complex

### 5. Statistical Honesty
- Report ALL results (winners and losers)
- If 1 out of 10 tests works, that's probably random
- If 6 out of 10 tests work consistently → maybe real edge
- Small sample sizes = weak evidence

### 6. Clear Stopping Criteria
**When to stop testing:**
- Found consistent improvement across multiple setups → deploy carefully
- Found no improvement after 3 variant tests → likely doesn't work, move on
- Found mixed/inconsistent results → collect more data or abandon

---

## Test Structure

### Phase 1: Single Setup Validation (START HERE)

**Goal:** Does time-exit help on ONE specific setup?

**Setup Selection:**
- Pick a setup you trade frequently
- Must have 30+ trades in OOS window
- Prefer setup with known chop problem

**Suggested:** 1000 ORB (RR=2.5 or 3.0)
- Reason: Grid search suggested this might work
- Known issue: Sometimes choppy, slow to develop

**Test Variants:**
1. Baseline (no time exit)
2. T=20, MFE=0.25R (grid search winner)
3. T=30, MFE=0.25R (more conservative)

**Success Criteria:**
- Variant improves avg R by >= 0.02R (5%+ improvement)
- Invasiveness <= 20% (low interference)
- Consistent across 2+ time periods

**If Phase 1 FAILS:** Stop. Time exits don't work. Move on.

**If Phase 1 SUCCEEDS:** Proceed to Phase 2.

---

### Phase 2: Setup Expansion (Only if Phase 1 succeeds)

**Goal:** Does it work on similar setups?

**Test on:**
- Same ORB time, different RR targets
- Example: 1000 ORB (RR=1.5, 2.0, 2.5, 3.0)

**Use same parameters from Phase 1**
- Don't re-optimize!
- Test if it generalizes

**Success Criteria:**
- Works on 2+ out of 4 RR variants
- Doesn't destroy any variant (no -0.05R+ damage)

**If Phase 2 FAILS:** Time exits are too specific. Use ONLY on Phase 1 setup.

**If Phase 2 SUCCEEDS:** Proceed to Phase 3.

---

### Phase 3: ORB Expansion (Only if Phase 2 succeeds)

**Goal:** Does it work on other ORB times?

**Test on:**
- 0900, 1100, 1800 ORBs (different liquidity profiles)
- Use same RR filter (e.g., RR >= 2.5)

**Use same parameters from Phase 1**
- Still don't re-optimize!

**Success Criteria:**
- Works on 1+ other ORB
- Doesn't destroy 0900 (fast mover - risk is high)

**If Phase 3 FAILS:** Time exits are ORB-specific. Use on proven ORBs only.

**If Phase 3 SUCCEEDS:** Consider broader deployment.

---

### Phase 4: Parameter Robustness (Only if Phase 3 succeeds)

**Goal:** Are parameters robust or fragile?

**Test:**
- T ± 5 minutes (e.g., 15, 20, 25)
- MFE ± 0.05R (e.g., 0.20, 0.25, 0.30)

**Look for:**
- Parameters that work across range (robust)
- Cliff edges where small change destroys edge (fragile = overfit)

**Success Criteria:**
- Performance doesn't collapse with small parameter changes
- Multiple nearby parameter sets work (not just one lucky combination)

**If Phase 4 FAILS:** Parameters are overfit. High risk in live trading.

**If Phase 4 SUCCEEDS:** Consider deployment with confidence.

---

## Metrics to Track

### Primary Metric (Decision-Maker)
**Avg R per trade (delta from baseline)**
- Threshold: >= +0.02R = meaningful improvement
- Threshold: >= +0.05R = strong improvement
- Threshold: <= -0.02R = harmful, reject

### Secondary Metrics (Context)
1. **Invasiveness** (% trades exited early)
   - Low: < 15%
   - Medium: 15-30%
   - High: > 30% (usually bad)

2. **Win Rate Change**
   - Small increase OK
   - Large increase + lower avg winner = BAD (exiting winners early)

3. **Avg Winner / Avg Loser**
   - If avg winner drops significantly = BAD
   - If avg loser improves significantly = GOOD

4. **Max Drawdown**
   - Lower is good (but secondary to avg R)

5. **Sample Size**
   - < 20 trades = weak evidence
   - 20-50 trades = moderate evidence
   - > 50 trades = strong evidence

---

## Test Variants (Concrete)

### Variant 1: Time-Only Exit
**Rule:** If minutes >= T → exit at market

**Parameters:**
- T: 30, 45, 60 minutes

**Hypothesis:** Pure time limit cuts dead trades

**Expected:** Probably doesn't work (no progress check = exits random trades)

---

### Variant 2: Progress Gate (Recommended Starting Point)
**Rule:** If minutes >= T AND MFE < threshold → exit at market

**Parameters:**
- T: 20, 30 minutes
- MFE: 0.20, 0.25, 0.30R

**Hypothesis:** Trades with no progress after T minutes are likely chop

**Expected:** Most likely to work (grid search supports this)

---

### Variant 3: Retracement Gate
**Rule:** If minutes >= T AND MFE >= threshold BUT current_progress < (MFE * 0.5) → exit

**Parameters:**
- T: 30 minutes
- MFE: 0.35R
- Retracement: 50% of MFE

**Hypothesis:** Trades that reached target zone but retraced are losing momentum

**Expected:** Probably too complex, unlikely to work consistently

---

### Variant 4: Session-Aware Exit
**Rule:** If approaching session close (< 30 min until close) AND not profitable → exit

**Parameters:**
- Time until close: 30 minutes

**Hypothesis:** Don't hold into illiquid close periods

**Expected:** Might work for specific sessions (e.g., 1800 ORB before NY close)

---

## Recommended Test Sequence

### Week 1: Single Setup Test (Phase 1)

**Setup:** 1000 ORB (RR=2.5)

**Tests:**
1. Baseline (no time exit)
2. Variant 2: T=20, MFE=0.25
3. Variant 2: T=30, MFE=0.25

**Decision Point:**
- If best variant improves by +0.02R+ → Continue to Phase 2
- If no improvement or negative → STOP, time exits don't work

---

### Week 2: RR Expansion (Phase 2) - Only if Week 1 succeeds

**Setups:** 1000 ORB (RR=1.5, 2.0, 2.5, 3.0)

**Test:** Use winning parameters from Week 1 (don't re-optimize!)

**Decision Point:**
- If works on 2+ RR variants → Continue to Phase 3
- If only works on one RR → Use selectively, STOP expansion

---

### Week 3: ORB Expansion (Phase 3) - Only if Week 2 succeeds

**Setups:** 0900, 1100, 1800 ORBs (with RR filter from Week 2)

**Test:** Same parameters as Week 1 winner

**Decision Point:**
- If works on 1+ other ORB → Broader deployment possible
- If only works on 1000 → Use only on 1000 ORB

---

### Week 4: Robustness Check (Phase 4) - Only if Week 3 succeeds

**Test:** Parameter sensitivity
- T ± 5 minutes
- MFE ± 0.05R

**Decision Point:**
- If performance stable → Deploy with confidence
- If performance fragile → Deploy cautiously or abandon

---

## Output Format

### For Each Test:

```
=================================================================
TEST: 1000 ORB (RR=2.5) - Baseline vs T=20, MFE=0.25
=================================================================

DATA:
  Period: 2025-10-15 to 2026-01-12 (90 days)
  Trades: 62

BASELINE:
  Avg R: 0.076R
  Win Rate: 32.3%
  Avg Winner: 1.85R
  Avg Loser: -0.98R
  Max DD: 4.2R

VARIANT (T=20, MFE=0.25):
  Avg R: 0.109R
  Win Rate: 35.5%
  Avg Winner: 1.72R
  Avg Loser: -0.85R
  Max DD: 3.8R
  Time-Exit Trades: 8 (13%)

COMPARISON:
  Delta Avg R: +0.033R (+43%)
  Delta Win Rate: +3.2%
  Delta Avg Winner: -0.13R (slight decrease, OK)
  Delta Avg Loser: +0.13R (improved)
  Delta Max DD: -0.4R (improved)
  Invasiveness: 13% (LOW)

VERDICT: ✅ IMPROVEMENT
  Evidence: Strong (62 trades, +0.033R improvement)
  Mechanism: Cuts chop losses (-0.98R → -0.85R)
  Side Effects: Minimal (13% invasiveness, slight avg winner decrease)

RECOMMENDATION: PROCEED TO PHASE 2 (test on other RR targets)
```

---

## Red Flags (When to Stop)

### 1. No Improvement After 3 Variants
**Example:** Tested T=20/30/45 with MFE=0.25, all show <= +0.01R improvement

**Action:** Time exits don't add value. Stop testing. Move on.

---

### 2. High Invasiveness (>30%) with Low Improvement
**Example:** 40% of trades exit early, but only +0.01R improvement

**Action:** Too much interference for minimal gain. Reject.

---

### 3. Avg Winner Collapse
**Example:** Avg winner drops from 1.8R to 0.9R (50% drop)

**Action:** Exiting winners too early. Reject.

---

### 4. Inconsistent Results Across Similar Setups
**Example:** Works on RR=2.5 (+0.05R) but destroys RR=3.0 (-0.08R)

**Action:** Fragile/unstable. Use ONLY on proven setup or abandon.

---

### 5. Parameter Cliff Edges
**Example:** T=20 works (+0.04R), T=25 fails (-0.02R)

**Action:** Overfit to specific parameter. High risk in live trading.

---

## Statistical Considerations

### Sample Size Requirements

**Minimum:** 20 trades per test
- Reason: Below this, noise dominates signal

**Moderate:** 50 trades per test
- Reason: Can detect +0.03R improvements reliably

**Strong:** 100+ trades per test
- Reason: Can detect +0.01R improvements

### Multiple Testing Problem

**Issue:** If you test 20 variants, 1 will appear to work by chance (p=0.05)

**Solution:**
- Report ALL tests (not just winners)
- Look for consistency across related setups
- Use higher threshold (+0.02R minimum, not +0.01R)
- Out-of-sample validation required

### Time Period Sensitivity

**Test:**
- Split OOS window into 2 halves
- Does variant work in BOTH halves?

**If YES:** More confidence it's real
**If NO:** Might be regime-specific or random

---

## Implementation Requirements

### Data Needed:
1. 1-minute bars (for intraday simulation)
2. Daily features (for ORB ranges, break direction)
3. 60-90 day OOS window

### Code Structure:
```python
def test_variant(setup, variant_params, oos_dates):
    """
    Test one variant against baseline.

    Returns:
        baseline_metrics: dict
        variant_metrics: dict
        comparison: dict with deltas
        verdict: 'IMPROVEMENT' | 'NEUTRAL' | 'HARMFUL'
    """

def run_phase_1():
    """Single setup validation."""
    # Test 1000 ORB (RR=2.5) with 3 variants
    # Return: best_variant or None

def run_phase_2(best_variant_from_phase_1):
    """RR expansion."""
    # Test same variant on RR=1.5, 2.0, 3.0
    # Return: list of working RRs

def run_phase_3(best_variant, working_rrs):
    """ORB expansion."""
    # Test on 0900, 1100, 1800
    # Return: list of working ORBs

def run_phase_4(best_variant):
    """Parameter robustness."""
    # Test T ± 5, MFE ± 0.05
    # Return: robustness score
```

---

## What Success Looks Like

### Best Case:
- Phase 1: +0.05R improvement on 1000 RR=2.5, 13% invasiveness
- Phase 2: Works on RR >= 2.5 (2 out of 3 variants)
- Phase 3: Works on 1000 and 1100 (not 0900)
- Phase 4: Robust to T ± 5 minutes

**Action:** Deploy on proven setups (1000/1100, RR >= 2.5)

---

### Realistic Case:
- Phase 1: +0.03R improvement on 1000 RR=2.5, 15% invasiveness
- Phase 2: Only works on RR=2.5 (not 1.5, 2.0, 3.0)
- STOP at Phase 2

**Action:** Deploy ONLY on 1000 RR=2.5, monitor closely

---

### Likely Case:
- Phase 1: +0.01R improvement (barely positive)
- Test 2 more variants: both show +0.00R or negative
- STOP at Phase 1

**Action:** Time exits don't add value. Move on to other ideas.

---

### Worst Case:
- Phase 1: All variants show negative or neutral
- STOP immediately

**Action:** Time exits hurt. Never use them.

---

## Final Notes

### This is Exploration, Not Optimization

**Goal:** Discover IF time exits work, not to squeeze maximum performance

**Mindset:**
- Expect most things to fail (that's OK!)
- Look for robust, simple, generalizable rules
- Weak/mixed evidence = don't use it
- Strong consistent evidence = consider deployment

### Deployment Checklist (If You Get Here)

Before going live:
1. ✅ Passed all phases with strong evidence
2. ✅ Tested on out-of-sample data
3. ✅ Invasiveness is low (< 20%)
4. ✅ Parameters are robust
5. ✅ Paper traded 20+ trades successfully
6. ✅ Have kill switch criteria (e.g., if -0.03R after 30 trades → disable)

---

**Remember: Most trading ideas don't work. Finding this out quickly and moving on is a skill, not a failure.**

---

**End of Testing Framework**
