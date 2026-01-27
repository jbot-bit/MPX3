# VALIDATION METHODOLOGY - Trading Strategy Approval Framework

## Purpose

This document defines the MANDATORY validation methodology for ALL trading strategies before approval.

**Guiding Principle:** HONESTY OVER OUTCOME

**Reference Documents:**
- CANONICAL_LOGIC.txt (calculation formulas)
- TCA.txt (transaction cost analysis)
- audit.txt (meta-audit principles)
- COST_MODEL_MGC_TRADOVATE.txt (cost specifications)

---

## Approval Requirements

**ALL strategies MUST pass validation at $7.40 RT costs.**

Lower costs may be reported for comparison only, NEVER for approval.

---

## 6-Phase Autonomous Validation Framework

Inspired by test-skill's 21-phase approach, adapted for trading strategies.

### Phase 1: Ground Truth Discovery

**Objective:** Reverse engineer EACH strategy's ACTUAL filter from the database

**NO ASSUMPTIONS. Prove from ground truth data.**

1. Read strategy from `validated_setups` table
2. Parse `notes` field to identify filter type
3. Map filter type to SQL query:
   - `L4_CONSOLIDATION` → `london_type_code = 'L4_CONSOLIDATION'`
   - `BOTH_LOST` → `orb_0900_outcome = 'LOSS' AND orb_1000_outcome = 'LOSS'`
   - `0900_LOSS` → `orb_0900_outcome = 'LOSS'`
   - `REVERSAL` → directional reversal logic
   - `ACTIVE_MARKETS` → `asia_range >= 2.0 AND london_range >= 2.0`
   - `RSI` → `rsi_at_orb > 70`
4. Verify SQL query returns expected trades
5. Document ACTUAL filter used

**Pass Criteria:** Filter successfully reverse-engineered and query returns trades

---

### Phase 2: Data Integrity Validation

**Objective:** Verify database has correct columns and valid data

**Autonomous checks:**

1. **Column Existence:**
   - `orb_{time}_high`, `orb_{time}_low`, `orb_{time}_break_dir`, `orb_{time}_outcome`
   - Filter columns: `london_type_code`, `london_range`, `asia_range`, `rsi_at_orb`, etc.

2. **Data Type Validation:**
   - Prices are FLOAT
   - Break direction is VARCHAR ('UP', 'DOWN', 'NONE')
   - Outcome is VARCHAR ('WIN', 'LOSS', 'NO_TRADE')

3. **Null Handling:**
   - Count NULL values per column
   - Verify NULL handling doesn't corrupt results

4. **Range Validation:**
   - ORB high >= ORB low
   - Break direction consistent with outcome
   - Prices are positive

**Pass Criteria:** All data integrity checks pass

---

### Phase 3: Single-Trade Reconciliation

**Objective:** Verify calculations on individual trades (audit.txt requirement)

**For 5 random trades from the strategy:**

1. **Manual Calculation:**
   - Entry = ORB high (UP) or ORB low (DOWN)
   - Stop = opposite ORB edge
   - Stop distance = |entry - stop|
   - Realized Risk $ = (stop_distance × $10.00) + $7.40
   - Target distance = stop_distance × RR
   - Realized Reward $ = (target_distance × $10.00) - $7.40
   - Realized R = (Realized Reward $ / Realized Risk $) if WIN else (-Realized Risk $ / Realized Risk $)

2. **Database Comparison:**
   - If database stores realized_rr, compare calculated vs stored
   - Tolerance: ±0.001R

3. **Documentation:**
   - Log each trade's calculation
   - Flag any mismatches

**Pass Criteria:** All 5 trades reconcile within tolerance

---

### Phase 4: Statistical Validation

**Objective:** Calculate strategy expectancy using CANONICAL formulas

**Calculations:**

1. **Sample Size Check:**
   - N >= 30 trades (MANDATORY minimum)
   - Confidence increases with sample size

2. **Win Rate:**
   - WR = count(WIN) / count(total_trades)

3. **Expectancy at $7.40 (MANDATORY):**
   ```
   For each trade:
     realized_risk_$ = (stop_distance × $10.00) + $7.40
     realized_reward_$ = (target_distance × $10.00) - $7.40

     If WIN:
       net_pnl = realized_reward_$
     Else:
       net_pnl = -realized_risk_$

     realized_r = net_pnl / realized_risk_$

   Expectancy = avg(realized_r) across all trades
   ```

4. **Comparison Expectancy at $2.50:**
   - Calculate for reference only
   - NOT used for approval

**Pass Criteria:**
- N >= 30
- Expectancy at $7.40 >= +0.15R

---

### Phase 5: Stress Testing

**Objective:** Test strategy robustness under adverse conditions

**Tests:**

1. **Cost Stress:**
   - +25% costs: $9.25 RT
   - +50% costs: $11.10 RT
   - Recalculate expectancy at each level
   - **EXCELLENT:** Survives +50% (ExpR >= +0.15R)
   - **MARGINAL:** Survives +25% only
   - **WEAK:** Fails both stress tests

2. **Regime Split (if applicable):**
   - **L4_CONSOLIDATION:** Split by london_range (low vs moderate within <2.0 threshold)
   - **ACTIVE_MARKETS:** Already filters by regime, test subsets
   - **Sequential strategies:** No regime split (context-dependent, not regime-dependent)
   - Must use CORRECT regime variable for strategy type

3. **Temporal Validation (ONLY if time-dependent):**
   - Most ORB strategies are regime/context-dependent, NOT time-dependent
   - Skip temporal tests unless strategy has explicit time-based assumptions

**Pass Criteria:**
- At minimum: Pass $7.40 + survive +25% stress
- Preferably: Pass $7.40 + survive +50% stress

---

### Phase 6: Iterative Correction & Documentation

**Objective:** Loop until validation passes or strategy definitively fails

**Correction Loop:**

1. If Phase 1 fails → Cannot reverse engineer filter → **NEEDS_CONTRACT_DEFINITION**
2. If Phase 2 fails → Data integrity issue → Fix database, re-run Phase 2
3. If Phase 3 fails → Calculation mismatch → Debug formula, re-run Phase 3
4. If Phase 4 fails → Below threshold or insufficient sample → **REJECTED**
5. If Phase 5 fails → Weak or marginal rating → Document and decide

**Documentation Requirements:**

For each strategy, document:
- Filter type and SQL query
- Sample size
- Expectancy at $7.40, +25%, +50%
- Expectancy at $2.50 (comparison)
- Verdict: EXCELLENT, MARGINAL, WEAK, or REJECTED
- Reason for verdict

**Final Output:**

```
STRATEGY: {orb_time} ORB RR={rr} {filter_type}
Ground Truth Trades: {N}
Expectancy at $7.40: {exp_740:+.3f}R
  +25% stress: {exp_25:+.3f}R
  +50% stress: {exp_50:+.3f}R
Comparison at $2.50: {exp_250:+.3f}R

VERDICT: {EXCELLENT|MARGINAL|WEAK|REJECTED}
REASON: {explanation}
```

---

## Approval Thresholds

| Verdict | Criteria | Action |
|---------|----------|--------|
| **EXCELLENT** | ExpR >= +0.15R at $7.40 AND survives +50% stress | APPROVE - Add to validated_setups |
| **MARGINAL** | ExpR >= +0.15R at $7.40 AND survives +25% stress only | APPROVE WITH CAUTION - Monitor closely |
| **WEAK** | ExpR >= +0.15R at $7.40 but fails stress tests | CONDITIONAL - Approve only if user accepts risk |
| **REJECTED** | ExpR < +0.15R at $7.40 OR N < 30 | REJECT - Remove from validated_setups |

---

## Implementation Checklist

- [ ] Phase 1: Reverse engineer all strategy filters
- [ ] Phase 2: Validate data integrity
- [ ] Phase 3: Reconcile 5 random trades per strategy
- [ ] Phase 4: Calculate expectancy at $7.40 (MANDATORY)
- [ ] Phase 5: Run stress tests (+25%, +50%)
- [ ] Phase 6: Document results and verdicts
- [ ] Update validated_setups database
- [ ] Update config.py (MANDATORY sync)
- [ ] Run test_app_sync.py (MANDATORY verification)

---

## References

- **CANONICAL_LOGIC.txt lines 76-98:** Realized RR formulas
- **TCA.txt:** Transaction cost analysis framework
- **audit.txt:** Meta-audit principles (test the tests)
- **COST_MODEL_MGC_TRADOVATE.txt:** $7.40 RT friction specification

---

**REMEMBER: HONESTY OVER OUTCOME.**

If a strategy fails validation, it MUST be removed, regardless of past performance claims.
