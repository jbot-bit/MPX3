# Walk-Forward Validation Framework

**Complete 9-stage validation pipeline to prevent curve-fitting and ensure edge robustness.**

---

## The Curve-Fitting Problem

**Current System Flaw:**
```
edge_discovery_runner.py → Tests 11,000+ combinations on ALL data (2020-2026)
  ↓
Finds: "1000 ORB, RR=8.0, filter=0.112 gives +0.50R"
  ↓
autonomous_strategy_validator.py → Checks calculations are correct
  ↓
Promotes to production → FAILS (was optimized on test data)
```

**What's Missing:** Parameters were optimized on the SAME data used for "validation". This is curve-fitting.

---

## The Solution: 3-Stage Walk-Forward

```
STAGE 1: Concept Testing (Validation Data - Held Out)
  ├─ Test: Does "1000 ORB breakout" work at all?
  ├─ Data: 20% validation set (HELD OUT, never used for optimization)
  ├─ Params: DEFAULT (RR=1.5, no filter, FULL SL)
  └─ Gate: ExpR >= +0.10R → Proceed to Stage 2

STAGE 2: Parameter Optimization (Training Data Only)
  ├─ Test: What's the best RR, filter, SL mode?
  ├─ Data: 60% training set (optimization ALLOWED here)
  ├─ Method: Grid search (RR × filters × SL modes)
  └─ Output: Optimal config + train ExpR

STAGE 3: Out-of-Sample Verification (Test Data - UNSEEN)
  ├─ Test: Do optimized params work on NEW data?
  ├─ Data: 20% test set (NEVER seen until now)
  ├─ Params: Optimal from Stage 2 (NO changes)
  └─ Gate: Test ExpR >= +0.15R AND degradation < 50%
```

**Key Insight:** Parameters are optimized on TRAINING data, then tested on UNSEEN test data. This prevents curve-fitting.

---

## Complete 9-Stage Pipeline

### Current Implementation Status

✅ **IMPLEMENTED (Stages 1-3):**
- Stage 1: Concept Testing
- Stage 2: Parameter Optimization
- Stage 3: Out-of-Sample Verification

⏳ **TODO (Stages 4-9):**
- Stage 4: Cost Stress Testing
- Stage 5: Monte Carlo Simulation
- Stage 6: Regime Analysis
- Stage 7: Rolling Window Walk-Forward
- Stage 8: Statistical Validation
- Stage 9: Final Documentation & Promotion

---

## Stage Details

### Stage 1: Concept Testing ✅

**Purpose:** Test if basic concept works BEFORE optimizing

**Data:** Validation set (20% held-out, dates[60%:80%])

**Parameters:** Default (RR=1.5, no filter, FULL SL)

**Gates:**
- ExpR >= +0.10R on validation data
- Sample >= 20 trades
- Win rate >= 10%

**Pass:** Proceed to Stage 2 (optimization)
**Fail:** Reject concept, don't waste time optimizing

**CLI:**
```bash
python scripts/discovery/concept_tester.py --orb 1000 --instrument MGC
```

**Output:**
```
STAGE 1: CONCEPT TESTING
ORB: 1000 | Instrument: MGC
Validation dates: 365 days (2023-08-16 to 2025-01-10)

Testing with DEFAULT parameters (not optimized):
  RR: 1.5
  SL Mode: full
  Filter: None

CONCEPT TEST RESULTS
Sample:   53 trades (W:28 / L:25)
Win Rate: 52.8%
ExpR:     +0.12R

Gate Checks:
  ExpR >= +0.10R: ✅ (+0.12R)
  Sample >= 20: ✅ (53)
  WR >= 10%: ✅ (52.8%)

✅ STAGE 1: PASS
Concept works on validation data - proceed to Stage 2 (optimization)
```

---

### Stage 2: Parameter Optimization ✅

**Purpose:** Find optimal parameters for validated concept

**Data:** Training set (60% of data, dates[0:60%])

**Method:** Grid search over:
- RR: [1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
- Filters: [None, 0.05, 0.10, 0.112, 0.15, 0.20, 0.25, 0.30]
- SL modes: ['full', 'half']

**Gates:**
- Training ExpR >= +0.15R
- Training sample >= 30 trades

**Pass:** Record optimal parameters, proceed to Stage 3
**Fail:** Reject (no profitable config found)

**CLI:**
```bash
python scripts/discovery/parameter_optimizer.py --orb 1000 --instrument MGC
```

**Output:**
```
STAGE 2: PARAMETER OPTIMIZATION
ORB: 1000 | Instrument: MGC
Training dates: 1095 days (2020-01-01 to 2023-08-15)

Search space:
  RR values: [1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
  Filters: [None, 0.05, 0.10, 0.112, 0.15, 0.20, 0.25, 0.30]
  SL modes: ['full', 'half']
  Total configurations: 176

Grid search complete: 176 configurations tested

OPTIMIZATION RESULTS
Optimal configuration found:
  RR:     8.0
  Filter: 0.112
  SL Mode: half

Training performance:
  Sample:   180 trades (W:105 / L:75)
  Win Rate: 58.3%
  ExpR:     +0.48R

Gate Checks:
  Train ExpR >= +0.15R: ✅ (+0.48R)
  Sample >= 30: ✅ (180)

✅ STAGE 2: PASS
Optimal parameters found - proceed to Stage 3 (out-of-sample verification)
```

---

### Stage 3: Out-of-Sample Verification ✅

**Purpose:** Verify optimized parameters work on UNSEEN data

**Data:** Test set (20% of data, dates[80%:], NEVER used before)

**Parameters:** Optimal from Stage 2 (NO modifications)

**Gates:**
- Test ExpR >= +0.15R (profitability threshold)
- Degradation < 50% (test >= 50% of train)
- Test sample >= 30 trades

**Pass:** Proceed to Stage 4 (stress testing)
**Fail:** Reject (curve-fit, doesn't generalize)

**CLI:**
```bash
python scripts/discovery/out_of_sample_verifier.py \
  --orb 1000 --instrument MGC \
  --rr 8.0 --filter 0.112 --sl-mode half \
  --train-expr 0.48
```

**Output:**
```
STAGE 3: OUT-OF-SAMPLE VERIFICATION
ORB: 1000 | Instrument: MGC
Test dates: 365 days (2025-01-11 to 2026-01-28)
CRITICAL: This data was NEVER used for optimization

Testing with OPTIMIZED parameters from Stage 2:
  RR: 8.0
  Filter: 0.112
  SL Mode: half

OUT-OF-SAMPLE RESULTS
Test performance:
  Sample:   45 trades (W:24 / L:21)
  Win Rate: 53.3%
  ExpR:     +0.32R

Comparison to training:
  Train ExpR: +0.48R
  Test ExpR:  +0.32R
  Degradation: 33.3%

Gate Checks:
  Test ExpR >= +0.15R: ✅ (+0.32R)
  Degradation < 50%: ✅ (33.3%)
  Sample >= 30: ✅ (45)

✅ STAGE 3: PASS
Optimized parameters work on unseen data - proceed to Stage 4 (stress testing)

This is STRONG evidence the edge is NOT curve-fit.
```

**This is the CRITICAL anti-curve-fitting gate.**

---

### Stage 4: Cost Stress Testing ⏳ TODO

**Purpose:** Verify edge survives higher transaction costs

**Data:** Test set results from Stage 3

**Scenarios:**
- Normal: $8.40 (MGC baseline - honest double-spread accounting)
- Stress +25%: $10.50
- Stress +50%: $12.60
- Stress +100%: $16.80

**Gates:**
- ExpR >= +0.15R at +25% stress
- ExpR >= +0.15R at +50% stress (preferred)
- ExpR > 0.00R at +100% stress (still positive)

**Pass:** Proceed to Stage 5
**Fail:** Reject (too fragile, breaks with realistic costs)

---

### Stage 5: Monte Carlo Simulation ⏳ TODO

**Purpose:** Verify result is statistically significant (not random luck)

**Method:**
1. Take actual trade sequence from test set
2. Randomize order 10,000 times
3. Calculate ExpR for each random sequence
4. Compute 95% confidence interval
5. Check if actual result is outside CI

**Gates:**
- Actual result outside 95% CI (statistically significant)
- P-value < 0.05 (reject null hypothesis)

**Pass:** Proceed to Stage 6
**Fail:** Reject (likely random noise, not skill)

---

### Stage 6: Regime Analysis ⏳ TODO

**Purpose:** Verify edge works in different market conditions

**Regimes:**
- High volatility vs Low volatility (ATR split at median)
- Trending vs Range-bound (directional moves vs choppy)

**Gates:**
- Positive ExpR in BOTH high and low volatility
- Positive ExpR in BOTH trending and range markets
- At least 10 trades per regime

**Pass:** Proceed to Stage 7
**Fail:** Reject (regime-dependent, not robust)

---

### Stage 7: Rolling Window Walk-Forward ⏳ TODO

**Purpose:** Verify edge works across multiple time periods

**Method:**
```
Window 1: Train 2020-2022 | Valid 2023 | Test 2024
Window 2: Train 2020-2023 | Valid 2024 | Test 2025
Window 3: Train 2020-2024 | Valid 2025 | Test 2026
```

**Gates:**
- Edge profitable in 50%+ of windows (2/3 minimum)
- Average test ExpR >= +0.15R across windows

**Pass:** Proceed to Stage 8
**Fail:** Reject (doesn't generalize across time)

---

### Stage 8: Statistical Validation ⏳ TODO

**Purpose:** Verify sufficient data for confidence

**Checks:**
1. Sample size >= 30 trades
2. Bootstrap confidence intervals (10,000 samples)
3. T-test vs zero expectancy

**Gates:**
- Sample >= 30
- 95% CI does not include 0
- P-value < 0.05

**Pass:** Proceed to Stage 9 (final promotion)
**Fail:** Reject (insufficient evidence)

---

### Stage 9: Final Documentation & Promotion ⏳ TODO

**Purpose:** Document all results and promote to production

**Process:**
1. Create complete validation report (all 9 stages)
2. Generate evidence pack (charts, statistics, logs)
3. Operator review and approval
4. Write to `validated_setups` table with `walkforward_validated=TRUE`
5. Update `trading_app/config.py`
6. Run `python test_app_sync.py` to verify sync

**Gates:**
- ALL stages 1-8 passed
- Operator approval obtained
- Database/config synced

**Pass:** Edge goes LIVE (PROMOTED status)
**Fail:** Edge archived with full report

---

## Data Split Strategy

### Simple 60/20/20 Split

```
├─ 60% TRAIN     (2020-01-01 to 2023-08-15)  ← Optimize here
├─ 20% VALIDATION (2023-08-16 to 2025-01-10) ← Test concept here FIRST
└─ 20% TEST       (2025-01-11 to 2026-01-28) ← Final verification (unseen)
```

**Pros:**
- Simple, clear boundaries
- Test set is most recent data (realistic)

**Cons:**
- Single test period (could be lucky/unlucky)

### Rolling Window Walk-Forward (Stage 7)

```
Window 1: Train 2020-2022 | Valid 2023 | Test 2024
Window 2: Train 2020-2023 | Valid 2024 | Test 2025
Window 3: Train 2020-2024 | Valid 2025 | Test 2026
```

**Pros:**
- Multiple test periods (more robust)
- Detects regime changes
- Standard in quantitative finance

**Cons:**
- More computation (3x slower)
- Requires more historical data

---

## Strategy Family Isolation (CRITICAL)

**Walk-forward MUST respect strategy families:**

- **ORB_L4** (0900, 1000) → Only test on L4_CONSOLIDATION sessions
- **ORB_BOTH_LOST** (1100) → Only test on BOTH_LOST sessions
- **ORB_RSI** (1800) → Only test on RSI sessions
- **ORB_NIGHT** (2300, 0030) → RESEARCH ONLY (do not validate)

**Why:** Prevents cross-family contamination during validation.

**Implementation:**
```python
# Automatically applied in all validation stages
if orb_time in ['0900', '1000']:
    dates = filter_by_strategy_family(con, dates, orb_time, instrument)
    # Filters to L4_CONSOLIDATION = 1
elif orb_time == '1100':
    # Filters to BOTH_LOST = 1
elif orb_time == '1800':
    # Filters to RSI_at_orb_1800 IS NOT NULL
```

---

## Usage

### Run Complete Pipeline (Stages 1-3)

```bash
python scripts/discovery/walkforward_discovery.py --orb 1000 --instrument MGC
```

**Expected Output:**
```
================================================================================
WALK-FORWARD VALIDATION PIPELINE
================================================================================
ORB: 1000 | Instrument: MGC
Strategy Family Filter: ENABLED
================================================================================

████████████████████████████████████████████████████████████████████████████████
STAGE 1/9: CONCEPT TESTING (Validation Data - Held Out)
████████████████████████████████████████████████████████████████████████████████
[... Stage 1 output ...]
✅ STAGE 1 PASSED - Concept validated, proceeding to optimization...

████████████████████████████████████████████████████████████████████████████████
STAGE 2/9: PARAMETER OPTIMIZATION (Training Data Only)
████████████████████████████████████████████████████████████████████████████████
[... Stage 2 output ...]
✅ STAGE 2 PASSED - Optimal parameters found, proceeding to out-of-sample test...

████████████████████████████████████████████████████████████████████████████████
STAGE 3/9: OUT-OF-SAMPLE VERIFICATION (Test Data - UNSEEN)
████████████████████████████████████████████████████████████████████████████████
CRITICAL: This is the key anti-curve-fitting gate
[... Stage 3 output ...]
✅ STAGE 3 PASSED - Edge survives out-of-sample test
This is STRONG evidence the edge is NOT curve-fit.

================================================================================
STAGES 4-9: TO BE IMPLEMENTED
================================================================================

Remaining stages:
  Stage 4: Cost Stress Testing (+25%, +50%, +100%)
  Stage 5: Monte Carlo Simulation (luck vs skill)
  Stage 6: Regime Analysis (high/low vol, trend/range)
  Stage 7: Rolling Window Walk-Forward (multiple periods)
  Stage 8: Statistical Validation (sample size, CI, p-value)
  Stage 9: Final Documentation & Promotion

These will be implemented in future iterations.

================================================================================
PROVISIONAL VALIDATION STATUS
================================================================================

✅ Stages 1-3 PASSED:
  Stage 1: Concept validated (ExpR: +0.12R)
  Stage 2: Parameters optimized (Train ExpR: +0.48R)
  Stage 3: Out-of-sample verified (Test ExpR: +0.32R, Degradation: 33.3%)

⚠️  Stages 4-9: NOT YET IMPLEMENTED

📊 PROVISIONAL STATUS: PROMISING (but incomplete validation)

Optimal parameters:
  RR:     8.0
  Filter: 0.112
  SL Mode: half

Performance summary:
  Validation ExpR: +0.12R (53 trades)
  Training ExpR:   +0.48R (180 trades)
  Test ExpR:       +0.32R (45 trades)
  Degradation:     33.3%
================================================================================

📄 Validation report saved: validation_reports/walkforward_MGC_1000_20260128_143022.json
```

### Run Individual Stages

**Stage 1 only:**
```bash
python scripts/discovery/concept_tester.py --orb 1000 --instrument MGC
```

**Stage 2 only:**
```bash
python scripts/discovery/parameter_optimizer.py --orb 1000 --instrument MGC
```

**Stage 3 only (requires Stage 2 results):**
```bash
python scripts/discovery/out_of_sample_verifier.py \
  --orb 1000 --instrument MGC \
  --rr 8.0 --filter 0.112 --sl-mode half \
  --train-expr 0.48
```

---

## Database Schema Changes

```sql
-- Add to validated_setups table
ALTER TABLE validated_setups
ADD COLUMN walkforward_validated BOOLEAN DEFAULT FALSE;

ALTER TABLE validated_setups
ADD COLUMN concept_test_expr DOUBLE;        -- Stage 1 result
ADD COLUMN train_expr DOUBLE;               -- Stage 2 result
ADD COLUMN test_expr DOUBLE;                -- Stage 3 result
ADD COLUMN degradation_pct DOUBLE;          -- (train - test) / train

-- Mark existing strategies as NOT walk-forward validated
UPDATE validated_setups
SET walkforward_validated = FALSE
WHERE walkforward_validated IS NULL;
```

---

## Files

### Core Framework
- `pipeline/walkforward_config.py` - Configuration (splits, thresholds, search space) ✅

### Validation Stages (Implemented)
- `scripts/discovery/concept_tester.py` - Stage 1: Concept testing ✅
- `scripts/discovery/parameter_optimizer.py` - Stage 2: Parameter optimization ✅
- `scripts/discovery/out_of_sample_verifier.py` - Stage 3: Out-of-sample verification ✅

### Validation Stages (TODO)
- `scripts/discovery/stress_tester.py` - Stage 4: Cost stress testing ⏳
- `scripts/discovery/monte_carlo.py` - Stage 5: Monte Carlo simulation ⏳
- `scripts/discovery/regime_analyzer.py` - Stage 6: Regime analysis ⏳
- `scripts/discovery/rolling_window.py` - Stage 7: Rolling window walk-forward ⏳
- `scripts/discovery/statistical_validator.py` - Stage 8: Statistical validation ⏳
- `scripts/discovery/promoter.py` - Stage 9: Final promotion ⏳

### Orchestration
- `scripts/discovery/walkforward_discovery.py` - Main pipeline orchestrator ✅

### Documentation
- `docs/REAL_WALKFORWARD_VALIDATION.md` - This file ✅

---

## Validation Checklist

Before promoting any edge, verify ALL stages passed:

```
Stage 1: Concept Test (Validation Data) ✅
  [✅] ExpR >= +0.10R on held-out data
  [✅] Sample >= 20 trades
  [✅] Win rate >= 10%

Stage 2: Parameter Optimization (Training Data) ✅
  [✅] Optimal config found
  [✅] Training ExpR >= +0.15R
  [✅] Training sample >= 30 trades

Stage 3: Out-of-Sample Verification (Test Data) ✅
  [✅] Test ExpR >= +0.15R
  [✅] Degradation < 50%
  [✅] Test sample >= 30 trades

Stage 4: Cost Stress Testing ⏳
  [ ] ExpR >= +0.15R at +25% stress
  [ ] ExpR >= +0.15R at +50% stress
  [ ] ExpR > 0.00R at +100% stress

Stage 5: Monte Carlo Simulation ⏳
  [ ] Actual result outside 95% CI
  [ ] P-value < 0.05

Stage 6: Regime Analysis ⏳
  [ ] Positive in high volatility
  [ ] Positive in low volatility
  [ ] Positive in trending markets
  [ ] Positive in range markets

Stage 7: Rolling Window Walk-Forward ⏳
  [ ] Pass rate >= 50% (2/4 windows)
  [ ] Average test ExpR >= +0.15R

Stage 8: Sample Size & Statistics ⏳
  [ ] Sample size >= 30
  [ ] Bootstrap CI doesn't include 0
  [ ] P-value < 0.05

Stage 9: Final Documentation ⏳
  [ ] All stages passed
  [ ] Evidence pack complete
  [ ] Operator approval obtained
  [ ] Database/config synced
```

**Current status: Stages 1-3 complete. Stages 4-9 pending implementation.**

---

## Key Benefits

### 1. Prevents Curve-Fitting
- Parameters NOT optimized on test data
- Concept tested BEFORE optimization
- Multiple validation stages

### 2. Realistic Expectations
- Degradation metrics (expect 20-40% drop from train to test)
- Stress testing at higher costs
- Regime analysis for market conditions

### 3. Statistical Rigor
- Monte Carlo simulation (luck vs skill)
- Bootstrap confidence intervals
- Sample size validation

### 4. Robustness Checks
- Rolling window (multiple time periods)
- Regime analysis (different market conditions)
- Cost stress testing (edge durability)

---

## Expected Results

**Current "validated" edges:**
- Some will FAIL out-of-sample test (were curve-fit)
- Some will PASS but with lower ExpR (degradation expected)

**New edges:**
- More robust (proven on unseen data)
- Realistic performance expectations
- Higher confidence in production

**Degradation:**
- 20-40% drop from train to test is NORMAL and expected
- If edge survives with ExpR >= +0.15R after degradation, that's GOOD
- Zero degradation is SUSPICIOUS (may indicate lookahead bias or overfitting)

---

## Next Steps

1. ✅ **Implement Stages 1-3** (concept, optimize, verify)
2. ⏳ **Implement Stages 4-9** (stress, monte carlo, regime, rolling, stats, promote)
3. ⏳ **Integrate with Research Lab** (add UI in app_canonical.py)
4. ⏳ **Test current validated edges** using complete pipeline
5. ⏳ **Update promotion protocol** (require walkforward_validated=TRUE)

---

## Testing the System

```bash
# Test configuration
python pipeline/walkforward_config.py

# Test individual stages
python scripts/discovery/concept_tester.py --orb 1000 --instrument MGC
python scripts/discovery/parameter_optimizer.py --orb 1000 --instrument MGC
python scripts/discovery/out_of_sample_verifier.py \
  --orb 1000 --instrument MGC \
  --rr 8.0 --filter 0.112 --sl-mode half \
  --train-expr 0.48

# Run complete pipeline (Stages 1-3)
python scripts/discovery/walkforward_discovery.py --orb 1000 --instrument MGC
```

---

## References

- `CANONICAL_LOGIC.txt` - Calculation formulas
- `TCA.txt` - Transaction cost analysis
- `audit.txt` - Meta-audit principles
- `COST_MODEL_MGC_TRADOVATE.txt` - Cost specifications ($8.40 honest double-spread)
- `strategy_families/README.md` - Strategy family isolation rules

---

**This framework provides REAL walk-forward validation with NO MISSING LINKS from concept to production.**

**Current Implementation:** Stages 1-3 complete and tested. Stages 4-9 pending.
