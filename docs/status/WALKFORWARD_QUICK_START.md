# Walk-Forward Validation - Quick Start Guide

**5-Minute Guide to Using the Walk-Forward Validation System**

---

## What Is This?

A **real validation system** that tests edges on unseen data to prevent curve-fitting.

**Old way (BROKEN):**
```
Optimize on ALL data → "Validate" calculations → Deploy (CURVE-FIT)
```

**New way (CORRECT):**
```
Test concept → Optimize on training data → Verify on UNSEEN test data → Deploy (ROBUST)
```

---

## Quick Commands

### Run Full Validation (Stages 1-3)

```bash
# Validate 1000 ORB MGC
python scripts/discovery/walkforward_discovery.py --orb 1000 --instrument MGC

# Validate 0900 ORB MGC
python scripts/discovery/walkforward_discovery.py --orb 0900 --instrument MGC

# Validate 1800 ORB MGC
python scripts/discovery/walkforward_discovery.py --orb 1800 --instrument MGC

# Validate 1000 ORB NQ
python scripts/discovery/walkforward_discovery.py --orb 1000 --instrument NQ
```

**What it does:**
1. Tests if concept works (held-out validation data)
2. Finds optimal parameters (training data only)
3. Verifies on unseen test data
4. Saves report to `validation_reports/`

---

## Understanding the Output

### Stage 1: Concept Testing
```
STAGE 1/9: CONCEPT TESTING
  Validation ExpR: +0.12R (53 trades)
  ✅ STAGE 1: PASS
```

**What this means:**
- Edge concept works on held-out data (not optimized)
- Using default parameters (RR=1.5, no filter)
- If this fails, don't waste time optimizing

---

### Stage 2: Parameter Optimization
```
STAGE 2/9: PARAMETER OPTIMIZATION
  Optimal: RR=8.0, Filter=0.112, SL=HALF
  Train ExpR: +0.48R (180 trades)
  ✅ STAGE 2: PASS
```

**What this means:**
- Found best parameters on training data
- Tested 176 configurations (11 RR × 8 filters × 2 SL modes)
- These parameters will be tested on unseen data next

---

### Stage 3: Out-of-Sample Verification
```
STAGE 3/9: OUT-OF-SAMPLE VERIFICATION
  Test ExpR: +0.32R (45 trades)
  Degradation: 33.3%
  ✅ STAGE 3: PASS

This is STRONG evidence the edge is NOT curve-fit.
```

**What this means:**
- Edge WORKS on completely unseen test data
- Degradation of 33% is NORMAL (expected 20-40%)
- Edge is robust (not curve-fit)

**If this stage FAILS:**
```
  Test ExpR: +0.05R (45 trades)
  Degradation: 89.6%
  ❌ STAGE 3: FAIL

Edge fails on unseen data - LIKELY CURVE-FIT
```

**This means:**
- Edge was optimized to training data
- Doesn't generalize to new data
- DO NOT USE IN PRODUCTION

---

## Interpreting Results

### ✅ GOOD (Promotable)
```
Validation ExpR: +0.12R
Training ExpR:   +0.48R
Test ExpR:       +0.32R
Degradation:     33.3%
```

**Why it's good:**
- Test ExpR >= +0.15R (profitable)
- Degradation < 50% (less than half lost)
- Edge works on unseen data

### ❌ BAD (Curve-Fit)
```
Validation ExpR: +0.10R
Training ExpR:   +0.52R
Test ExpR:       +0.05R
Degradation:     90.4%
```

**Why it's bad:**
- Test ExpR < +0.15R (not profitable enough)
- Degradation > 50% (most of edge disappears)
- Edge doesn't work on unseen data

### ⚠️ MARGINAL (Borderline)
```
Validation ExpR: +0.11R
Training ExpR:   +0.35R
Test ExpR:       +0.16R
Degradation:     54.3%
```

**Why it's marginal:**
- Test ExpR barely passes (+0.16R vs +0.15R threshold)
- High degradation (>50%)
- Edge works but is fragile

---

## Data Splits Explained

### 60/20/20 Split

```
├─ 60% TRAIN     ← Optimize parameters HERE
├─ 20% VALIDATION ← Test concept HERE (before optimizing)
└─ 20% TEST       ← Final verification (NEVER seen until Stage 3)
```

**Example (2020-2026 data):**
- Train: 2020-01-01 to 2023-08-15 (1095 days)
- Validation: 2023-08-16 to 2025-01-10 (365 days)
- Test: 2025-01-11 to 2026-01-28 (365 days)

**Key points:**
- Test data is most recent (realistic for production)
- Test data NEVER used until Stage 3 (prevents curve-fitting)
- Validation data used BEFORE optimization (tests concept first)

---

## Configuration

### Change Thresholds

Edit `pipeline/walkforward_config.py`:

```python
THRESHOLDS = {
    'stage_1_concept': {
        'min_expr': 0.10,   # Lower this for more lenient concept test
        'min_sample': 20,
        'min_wr': 0.10
    },
    'stage_2_optimization': {
        'min_expr': 0.15,
        'min_sample': 30
    },
    'stage_3_out_of_sample': {
        'min_expr': 0.15,          # Raise this for stricter promotion gate
        'max_degradation': 0.50,   # Lower this to reject edges with high degradation
        'min_sample': 30
    }
}
```

### Change Search Space

Edit `pipeline/walkforward_config.py`:

```python
def get_search_space(orb_time: str) -> Dict:
    return {
        'rr_values': [1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
        'filters': [None, 0.05, 0.10, 0.112, 0.15, 0.20, 0.25, 0.30],
        'sl_modes': ['full', 'half']
    }
```

### Change Cost Models

Edit `pipeline/walkforward_config.py`:

```python
COST_MODELS = {
    'MGC': {
        'base_friction': 8.40,  # Change this for different MGC costs
        'stress_25': 10.50,
        'stress_50': 12.60,
        'stress_100': 16.80
    }
}
```

---

## Common Issues

### "No dates pass strategy family filter"

**Cause:** Strategy family columns (l4_consolidation, both_lost, rsi_at_0030) don't exist in database yet.

**Solution:** System falls back to using ALL dates. This is OK for now.

**To fix permanently:** Populate strategy family filters in `daily_features` table.

---

### "Insufficient data for rolling windows"

**Cause:** Database doesn't have enough data (need 730+ days).

**Solution:** This only affects Stage 7 (not implemented yet). Stages 1-3 work fine.

---

### "Test sample too small"

**Cause:** Not enough trades in test period (< 30).

**Solutions:**
- Use more historical data
- Lower `THRESHOLDS['stage_3_out_of_sample']['min_sample']` (risky)
- Wait for more data to accumulate

---

## Advanced Usage

### Run Individual Stages

```bash
# Test concept only (Stage 1)
python scripts/discovery/concept_tester.py --orb 1000 --instrument MGC

# Optimize parameters only (Stage 2)
python scripts/discovery/parameter_optimizer.py --orb 1000 --instrument MGC

# Verify on test data (Stage 3 - requires Stage 2 results)
python scripts/discovery/out_of_sample_verifier.py \
  --orb 1000 --instrument MGC \
  --rr 8.0 --filter 0.112 --sl-mode half \
  --train-expr 0.48
```

### Disable Strategy Family Filtering

```bash
python scripts/discovery/walkforward_discovery.py \
  --orb 1000 --instrument MGC \
  --no-family-filter
```

**Use this if:**
- Strategy family columns don't exist yet
- Testing on non-family-specific edges
- Debugging data issues

---

## What's Next?

### Immediate
1. Test current edges with walkforward system
2. Compare results to current validation
3. Identify curve-fit edges

### Short-Term
4. Implement Stages 4-9 (stress testing, monte carlo, etc.)
5. Add UI to Research Lab
6. Integrate with edge discovery

### Long-Term
7. Auto-validation on schedule
8. Alert system for edge degradation
9. Production deployment protocol

---

## Help

**Full Documentation:**
- `docs/REAL_WALKFORWARD_VALIDATION.md` - Complete system overview
- `WALKFORWARD_IMPLEMENTATION_COMPLETE.md` - Implementation details

**Quick Reference:**
- This file (WALKFORWARD_QUICK_START.md)

**Files:**
- `pipeline/walkforward_config.py` - Configuration
- `scripts/discovery/walkforward_discovery.py` - Main pipeline
- `scripts/discovery/concept_tester.py` - Stage 1
- `scripts/discovery/parameter_optimizer.py` - Stage 2
- `scripts/discovery/out_of_sample_verifier.py` - Stage 3

---

## TL;DR

```bash
# Run this to validate an edge:
python scripts/discovery/walkforward_discovery.py --orb 1000 --instrument MGC

# If Stage 3 PASSES → Edge is robust (not curve-fit)
# If Stage 3 FAILS → Edge is curve-fit (don't use)
```

**That's it. The system does the rest.**
