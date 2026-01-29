# Critical Improvements: Search + Real Validation

**Date:** 2026-01-28
**Priority:** HIGH (Fix these before trading live)

---

## Problem 1: Edge Search is Too Manual ⚠️

**Current State:**
- Research Lab requires manual filter configuration
- Can't search by characteristics ("large and narrow", "tight consolidation")
- Too much friction to explore edge space

**Solution: Semantic Edge Search**
- Pre-defined archetypes (large/narrow, explosive, quiet, etc.)
- Dropdown selection or natural language search
- System translates to filter ranges automatically

**Implementation:** `docs/SEMANTIC_EDGE_SEARCH.md`

**Complexity:** LOW (5-10 minutes to add archetype dropdown)

---

## Problem 2: "Validation" Doesn't Test Anything 🚨 CRITICAL

**Current State (BROKEN):**
```
edge_discovery_live.py → discovers on ALL data (2020-2026)
    ↓
populate_validated_setups.py → writes to database
    ↓
autonomous_strategy_validator.py → checks calculations (not if edge WORKS)
    ↓
Production → edge goes live (NEVER tested on held-out data)
```

**This is curve-fitting. The edge was optimized on data, then "validated" on the SAME data.**

**Real Validation Flow (CORRECT):**
```
Discover on TRAINING data (2020-2024)
    ↓
Test on HELD-OUT data (2025-2026) ← NEVER SEEN DURING DISCOVERY
    ↓
IF passes 50%+ of test windows AND maintains +0.15R:
    Promote to validated_setups
ELSE:
    Reject (curve-fit edge)
```

**Solution: Walk-Forward Validation**
- Train/test splits (multiple windows)
- Test on unseen data before promotion
- Promotion gate: only robust edges reach production
- Degradation monitoring (expect 20-40% ExpR drop)

**Implementation:** `docs/REAL_WALKFORWARD_VALIDATION.md`

**Complexity:** MEDIUM (1-2 hours to implement walkforward discovery)

---

## Implementation Roadmap

### Phase 1: Walk-Forward Validation (CRITICAL - Do First)

**Why:** Currently trading curve-fit edges that fail live.

**Steps:**
1. Create `pipeline/walkforward_config.py` (train/test splits)
2. Create `scripts/discovery/edge_discovery_walkforward.py`
3. Modify Research Lab to require walk-forward before promotion
4. Add promotion gate (only write to validated_setups if passed)

**Time:** 1-2 hours

**Benefit:** Prevents curve-fit edges from reaching production

---

### Phase 2: Semantic Edge Search (UX Improvement)

**Why:** Makes edge discovery faster and more intuitive.

**Steps:**
1. Create `trading_app/edge_archetypes.py` (archetype dictionary)
2. Add archetype dropdown to Research Lab tab
3. Wire up archetype selection to edge_discovery_walkforward.py
4. Optional: Add natural language parsing

**Time:** 30 minutes (archetype dropdown), 1 hour (NLP parsing)

**Benefit:** Faster exploration, less friction

---

## Why Walk-Forward is CRITICAL

### Current System (NO TESTING):
- Edge discovered on 2020-2026 data
- "Validated" on SAME 2020-2026 data
- Goes live → FAILS (was curve-fit)
- **You lose real money on optimized noise**

### Walk-Forward System (REAL TESTING):
- Edge discovered on 2020-2024 (training)
- TESTED on 2025-2026 (held-out, never seen)
- Only promoted if works on unseen data
- **You trade only robust edges proven on new data**

### Example:

**Edge: 1000 ORB, RR=2.5, L4 filter**

**Current System:**
- Discovers on ALL data: ExpR = +0.50R (180 trades)
- Writes to validated_setups
- Goes live → ExpR drops to +0.05R (was curve-fit)

**Walk-Forward System:**
- Discovers on training: ExpR = +0.50R (120 trades, 2020-2024)
- Tests on held-out: ExpR = +0.35R (45 trades, 2025-2026)
- Degraded but still positive → PROMOTE
- Goes live → ExpR stabilizes at +0.30R (robust edge)

**Difference:** +0.30R vs +0.05R → 6x better performance

---

## Integration with Existing System

### Current validated_setups Table:
- Contains 28 strategies (6 MGC, 5 NQ, 6 MPL, rest multi-setup)
- Discovered on ALL historical data
- NOT walk-forward validated
- **Recommendation:** Re-validate with walk-forward before trusting

### Walk-Forward Integration:
```python
# New column in validated_setups
ALTER TABLE validated_setups ADD COLUMN walkforward_validated BOOLEAN DEFAULT FALSE;

# Mark existing strategies as NOT walk-forward validated
UPDATE validated_setups SET walkforward_validated = FALSE;

# Only new edges from edge_discovery_walkforward.py will have TRUE
```

### Migration Plan:
1. Keep existing validated_setups (for historical reference)
2. Mark them as `walkforward_validated = FALSE`
3. Run walk-forward validation on existing edges
4. If they pass → set `walkforward_validated = TRUE`
5. If they fail → archive or reject
6. Going forward: ONLY promote edges that pass walk-forward

---

## Strategy Family Isolation (CRITICAL REMINDER)

**Walk-forward validation MUST respect strategy families:**

- ORB_L4 (0900, 1000 ORBs) → Train/test ONLY on L4 family
- ORB_BOTH_LOST (1100 ORB) → Train/test ONLY on BOTH_LOST family
- ORB_RSI (1800 ORB) → Train/test ONLY on RSI family

**Do NOT cross-validate between families:**
- ❌ WRONG: Discover L4 edge, test on RSI sessions
- ✅ CORRECT: Discover L4 edge, test on L4 sessions (held-out time period)

**Each family is a memory container. Findings stay inside.**

---

## Expected Degradation (Normal)

### Train ExpR vs Test ExpR:

**Healthy Degradation (20-40%):**
- Train: +0.50R → Test: +0.35R (30% drop)
- Interpretation: Edge is robust, expected degradation

**Suspicious (< 10%):**
- Train: +0.50R → Test: +0.48R (4% drop)
- Interpretation: Too good to be true, likely curve-fit or lucky

**Failed (> 60%):**
- Train: +0.50R → Test: +0.15R (70% drop)
- Interpretation: Edge barely survives, reject

**Reversed (negative test ExpR):**
- Train: +0.50R → Test: -0.10R
- Interpretation: Complete curve-fit, definitely reject

---

## Testing the Walk-Forward System

### Validation Test (Before Going Live):

```python
# Test on known-good edge (0900 RR=1.5)
results = run_walkforward_validation(
    conn=conn,
    orb_time='0900',
    filters={'orb_size_filter': 0.05}  # L4 filter
)

print(results['decision'])  # Should be 'PROMOTE'
print(results['avg_test_expr'])  # Should be +0.15R or better
print(results['pass_rate'])  # Should be 50%+ (2/4 windows)
```

### What to Expect:
- **Pass rate:** 50-75% (2-3 out of 4 windows)
- **Avg test ExpR:** +0.15R to +0.35R (degraded from train)
- **Decision:** PROMOTE if passes, REJECT if fails

### Red Flags:
- Pass rate = 100% (too good, likely overfit)
- Test ExpR = Train ExpR (no degradation, suspicious)
- Pass rate < 50% (edge doesn't generalize)

---

## Cost Considerations

### Walk-Forward Validation is FREE:
- Uses existing daily_features data (already in database)
- No additional API calls required
- Just runs execution_engine on different date ranges

### No Downside:
- Same data, different analysis
- Prevents curve-fit edges (saves trading losses)
- Worth the 1-2 hours of implementation

---

## Files to Create/Modify

### New Files:
1. `pipeline/walkforward_config.py` - Train/test window definitions
2. `scripts/discovery/edge_discovery_walkforward.py` - Walk-forward discovery
3. `trading_app/edge_archetypes.py` - Semantic search archetypes
4. `docs/SEMANTIC_EDGE_SEARCH.md` - ✅ Created
5. `docs/REAL_WALKFORWARD_VALIDATION.md` - ✅ Created

### Modified Files:
1. `trading_app/app_canonical.py` - Add archetype dropdown + walk-forward UI
2. `pipeline/populate_validated_setups.py` - Add walkforward_validated column
3. `scripts/audit/autonomous_strategy_validator.py` - Check walkforward_validated flag

---

## Next Actions

### Immediate (Do Today):
1. **Read** `docs/REAL_WALKFORWARD_VALIDATION.md` (understand walk-forward flow)
2. **Decide:** Re-validate existing 28 strategies or start fresh?
3. **Implement:** Walk-forward discovery script (1-2 hours)

### Short-Term (This Week):
4. Run walk-forward on existing MGC strategies
5. Mark passing strategies as `walkforward_validated = TRUE`
6. Archive failing strategies (curve-fit edges)

### Medium-Term (Next Sprint):
7. Add archetype search to Research Lab (30 min)
8. Integrate walk-forward into production workflow
9. Document promotion gate in CLAUDE.md

---

## Summary

**You identified TWO critical issues:**

1. **Edge search too manual** → Semantic search with archetypes (LOW priority)
2. **"Validation" doesn't test** → Walk-forward on held-out data (CRITICAL priority)

**Walk-forward validation is the MOST IMPORTANT FIX in the entire system.**

Without it, you're trading curve-fit edges that will fail live.

With it, you only trade robust edges proven on unseen data.

**Recommendation:** Implement walk-forward validation BEFORE trading any edge live.

---

**Last Updated:** 2026-01-28
**Priority:** CRITICAL (walk-forward), HIGH (semantic search)
**Complexity:** MEDIUM (1-2 hours for walk-forward)
**Dependencies:** None (uses existing daily_features data)
