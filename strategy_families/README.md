# STRATEGY FAMILIES

## Purpose

This directory contains STRATEGY_FAMILY abstractions - memory containers that prevent cross-contamination of findings and reduce overwhelm.

## Why Strategy Families?

**Problem**: Without families, every analysis finding leaks across all strategies, causing:
- "Does this apply to 1000 ORB or 1100 ORB?" confusion
- Re-discovering old findings (wasting API usage)
- Cross-family inference ("L4 works for 1000, so it should work for 1800")
- Overwhelm from tracking multiple contexts simultaneously

**Solution**: Each family is a self-contained memory container. Findings stay inside. No leakage.

## Current Families

### Production Ready:
1. **ORB_L4** - L4_CONSOLIDATION filter (0900, 1000 ORBs)
   - Status: 1000 ORB APPROVED, 0900 ORB MARGINAL
   - Best: 1000 ORB RR=3.0 (+1.277R, survives +50% stress)

2. **ORB_BOTH_LOST** - Sequential failure pattern (1100 ORB)
   - Status: MARGINAL (only survives +25% stress)
   - Expectancy: +0.223R

3. **ORB_RSI** - Momentum exhaustion (1800 ORB)
   - Status: MARGINAL (only survives +25% stress)
   - Expectancy: +0.222R

### Research Only:
4. **ORB_NIGHT** - Night sessions (2300, 0030 ORBs)
   - Status: RESEARCH ONLY - NOT VALIDATED
   - Warning: In-sample findings, likely overfitting

## Critical Rule

**All analysis, validation, and conclusions apply ONLY to the active STRATEGY_FAMILY.**

**Cross-family inference is FORBIDDEN unless explicitly promoted.**

This means:
- ✅ "5min filter works for ORB_L4 (1000 ORB)"
- ❌ "5min filter works for ORB_L4, so it should work for ORB_RSI"
- ❌ "L4 is validated, so all session types should work"

Each family must be validated independently.

## Template Structure

Each family file follows this structure:

1. **Purpose** - What the family exploits (1-2 sentences)
2. **Core Assumption** - Market condition required
3. **Baseline Logic (CANONICAL)** - Truth anchor (no filters here)
4. **Variants** - RR levels / timing only (no new logic)
5. **Status** - APPROVED / MARGINAL / REJECTED / RESEARCH
6. **Conditional Extensions** - Filters (must reference baseline delta)
7. **What This Family Is NOT** - Explicit exclusions
8. **Open Questions** - Known unknowns

## How to Use

### When Researching:
```python
# In research scripts:
ACTIVE_FAMILY = "ORB_L4"

# Assert all setups belong to active family
assert all(
    s["strategy_family"] == ACTIVE_FAMILY
    for s in setups
), "Cross-family contamination detected"
```

### When Validating:
1. Choose ONE family
2. Open its markdown file
3. Work ONLY on that family
4. Document findings in Section 6 (Conditional Extensions) or Section 8 (Open Questions)
5. DO NOT apply findings to other families

### When Adding Findings:
1. Open the family file
2. Add to Section 6 (Conditional Extensions) if validated
3. Add to Section 8 (Open Questions) if speculative
4. Include: filter description, performance delta vs baseline, validation phase

## Benefits

✅ **No more overwhelm** - Work one family at a time
✅ **No more API waste** - Findings persist in one place
✅ **No more cross-contamination** - Clear boundaries
✅ **No more "does this apply to X?"** - Everything scoped to family
✅ **Context persistence** - Always know "what am I working on?"

## Adding New Families

When discovering a new strategy type:

1. Create `strategy_families/NEW_FAMILY.md`
2. Use the template structure above
3. Start with baseline validation (no filters)
4. Add to validated_setups with `strategy_family` column
5. Document in this README

## Cost Model (Canonical)

**All families use the same cost model** (from `pipeline/cost_model.py`):
- MGC: $8.40 RT (commission $2.40 + spread_double $2.00 + slippage $4.00)
- Approval threshold: ExpR >= +0.15R at $8.40 AND survives stress testing

**NO FAMILY-SPECIFIC COST ADJUSTMENTS.** Honesty over outcome.

---

**Last Updated**: 2026-01-27
**Concept Source**: `upgrade.txt` - Strategy Family Abstraction
**Purpose**: Reduce overwhelm, prevent cross-contamination, persist findings
