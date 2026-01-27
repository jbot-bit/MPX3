# Strategy Validator Skill

## Auto-Activation Criteria

This skill AUTO-ACTIVATES when the user:
- Wants to **validate trading strategies**
- Mentions **"validate setups"**, **"test strategies"**, or **"approve strategies"**
- Asks **"are these strategies correct?"** or **"do these strategies work?"**
- Requests **stress testing**, **expectancy calculation**, or **TCA validation**
- Says **"run validation"** or **"audit strategies"**
- Updates `validated_setups` database and needs to verify correctness

## Purpose

Autonomous 6-phase validation framework for trading strategies that ensures:
- GROUND TRUTH verification from database
- CANONICAL formula adherence (CANONICAL_LOGIC.txt)
- Transaction Cost Analysis at production costs ($7.40 RT MGC)
- Statistical significance (min 30 trades)
- Stress testing (+25%, +50% costs)
- HONESTY OVER OUTCOME

## Methodology

### 6-Phase Autonomous Framework

**Phase 1: Ground Truth Discovery**
- Reverse engineer EACH strategy's ACTUAL filter from database
- NO ASSUMPTIONS - prove from ground truth data
- Map filter notes to SQL queries

**Phase 2: Data Integrity Validation**
- Verify database columns exist
- Check for NULL/invalid values
- Validate data types and ranges
- Ensure ORB high >= ORB low

**Phase 3: Single-Trade Reconciliation**
- Manually calculate 5 random trades
- Apply CANONICAL formulas (lines 76-98 of CANONICAL_LOGIC.txt)
- Compare calculated vs stored values (if available)
- Tolerance: ±0.001R

**Phase 4: Statistical Validation**
- Check sample size >= 30 trades (MANDATORY)
- Calculate win rate
- Calculate expectancy at $7.40 (MANDATORY for approval)
- Calculate expectancy at $2.50 (comparison only, NOT for approval)
- Threshold: +0.15R at $7.40

**Phase 5: Stress Testing**
- Test at +25% costs ($9.25)
- Test at +50% costs ($11.10)
- Regime splits (if applicable, using CORRECT regime variable)
- Skip temporal tests (most strategies are regime/context-dependent)

**Phase 6: Iterative Correction & Documentation**
- Loop until validation passes or definitively fails
- Document verdict: EXCELLENT, MARGINAL, WEAK, REJECTED
- Generate summary report

## Approval Thresholds

| Verdict | Criteria | Action |
|---------|----------|--------|
| **EXCELLENT** | ExpR >= +0.15R at $7.40 AND survives +50% stress | APPROVE |
| **MARGINAL** | ExpR >= +0.15R at $7.40 AND survives +25% stress only | APPROVE WITH CAUTION |
| **WEAK** | ExpR >= +0.15R at $7.40 but fails stress tests | CONDITIONAL |
| **REJECTED** | ExpR < +0.15R at $7.40 OR N < 30 | REJECT |

## How to Use

### Automatic Activation

Claude will automatically use this skill when validation is requested.

### Manual Invocation

```bash
python scripts/audit/autonomous_strategy_validator.py
```

### What It Does

1. Reads all strategies from `validated_setups` table
2. For EACH strategy individually:
   - Reverseengineers actual filter from notes
   - Queries ground truth trades from `daily_features`
   - Validates data integrity
   - Reconciles sample trades manually
   - Calculates expectancy at $7.40 (MANDATORY)
   - Runs stress tests (+25%, +50%)
   - Assigns verdict: EXCELLENT/MARGINAL/WEAK/REJECTED
3. Generates comprehensive summary report
4. Documents which strategies to KEEP vs REMOVE

## Output Format

```
VALIDATING: ID {id} | {orb_time} ORB RR={rr} {sl_mode}
==================================================

PHASE 1: Ground Truth Discovery
  Filter: {filter_description}
  [PASS] Found {N} ground truth trades

PHASE 2: Data Integrity Validation
  [PASS] Data integrity checks passed

PHASE 3: Single-Trade Reconciliation
  Trade 1 ({date}): {direction} {outcome}
    Stop: {X} pts | Risk: ${Y}
    Realized R: {+Z}R
  [PASS] Single-trade reconciliation completed

PHASE 4: Statistical Validation
  [PASS] Sample size: {N} >= 30
  Expectancy at $7.40: {+X}R
  Expectancy at $2.50: {+Y}R (comparison only)
  [PASS] Above +0.15R threshold

PHASE 5: Stress Testing
  +25% costs ($9.25): {+X}R
  +50% costs ($11.10): {+Y}R
  [EXCELLENT] Survives +50% stress

VERDICT: EXCELLENT
Reason: Passes $7.40 AND survives +50% stress
```

## Integration Points

### Pre-Validation Requirements

Before running validator:
1. Ensure `daily_features` table is populated
2. Verify `validated_setups` has strategies to test
3. Check `pipeline/cost_model.py` has correct costs ($7.40 MGC)

### Post-Validation Actions

After validation completes:
1. Update `validated_setups` database (remove REJECTED strategies)
2. Update `trading_app/config.py` (sync with database)
3. Run `python test_app_sync.py` (MANDATORY verification)

## Reference Documents

- **CANONICAL_LOGIC.txt** (lines 76-98): Realized RR formulas
- **TCA.txt**: Transaction cost analysis framework
- **audit.txt**: Meta-audit principles (test the tests)
- **COST_MODEL_MGC_TRADOVATE.txt**: $7.40 RT friction specification
- **VALIDATION_METHODOLOGY.md**: Complete validation framework

## Key Principles

1. **HONESTY OVER OUTCOME**: If strategy fails, reject it regardless of past claims
2. **NO ASSUMPTIONS**: Reverse engineer from ground truth data
3. **MANDATORY COSTS**: All validation at $7.40 RT (lower costs for comparison only)
4. **INDIVIDUAL VALIDATION**: Each strategy tested independently
5. **CANONICAL FORMULAS**: Use CANONICAL_LOGIC.txt formulas exactly

## Error Handling

| Error | Action |
|-------|--------|
| Cannot reverse engineer filter | Mark as NEEDS_CONTRACT_DEFINITION |
| Database query fails | Mark as PHASE1_FAIL |
| Data integrity issues | Mark as PHASE2_FAIL |
| Insufficient sample (N<30) | Mark as REJECTED |
| Below +0.15R at $7.40 | Mark as REJECTED |

## Examples

### Example 1: Validating All Strategies

```python
# User: "validate all strategies"
# Claude AUTO-ACTIVATES this skill and runs:
python scripts/audit/autonomous_strategy_validator.py
```

### Example 2: Single Strategy Validation

```python
# User: "Is strategy ID 20 correct?"
# Claude AUTO-ACTIVATES this skill for ID 20 only
```

### Example 3: After Database Update

```python
# User: "I updated validated_setups, verify correctness"
# Claude AUTO-ACTIVATES this skill
```

## Success Criteria

Validation succeeds when:
- All 6 phases complete without errors
- Each strategy receives a definitive verdict
- Summary report shows KEEP vs REMOVE recommendations
- Post-validation checklist completed (database + config + test_app_sync)

## Failure Modes

Validation fails if:
- Cannot connect to database
- `daily_features` table missing or empty
- Cost model not configured correctly
- Unable to reverse engineer any strategy filters

In failure cases, the skill will report the specific error and recommend corrective actions.

---

**REMEMBER: This skill is AUTONOMOUS. It runs all 6 phases without user intervention and provides a definitive answer: KEEP or REMOVE each strategy.**
