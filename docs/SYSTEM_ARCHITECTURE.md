# SYSTEM ARCHITECTURE - TRADING SYSTEM
**Date:** 2026-01-26
**Purpose:** Define authoritative sources, ownership boundaries, and drift detection

---

## DESIGN PRINCIPLES

1. **Single Source of Truth** - Every piece of data has exactly ONE authoritative source
2. **Unidirectional Data Flow** - Information flows downstream only (no circular dependencies)
3. **No Silent Divergence** - Mismatches between layers are DETECTABLE and FAIL LOUDLY
4. **No Hard-Coding** - All constants come from authoritative modules
5. **No Duplicated Calculations** - One calculation, many consumers
6. **Assume Human Error** - System must prevent mistakes, not rely on memory

---

## LAYER ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│                    AUTHORITATIVE LAYER                      │
│  (Single sources of truth - READ ONLY for downstream)      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  cost_model.py          validated_setups (DB)              │
│  - Contract specs       - Active strategies                │
│  - Broker costs         - RR values                        │
│  - Realized RR logic    - Filters                          │
│                         - Expectancy                       │
│                                                             │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                    CALCULATION LAYER                        │
│  (Consumes authoritative, produces intermediate results)   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  execution_engine.py                                        │
│  - Imports cost_model                                       │
│  - Simulates trades                                         │
│  - Calculates realized RR per trade                         │
│  - Returns TradeResult with both theoretical + realized     │
│                                                             │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                    AGGREGATION LAYER                        │
│  (Consumes calculations, stores to database)               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  build_daily_features.py                                    │
│  - Calls execution_engine for each ORB                      │
│  - Stores theoretical + realized columns to daily_features  │
│  - NO internal calculations (delegates to execution_engine) │
│                                                             │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                    STORAGE LAYER                            │
│  (Persistent state - queried by apps)                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  daily_features (DB)                                        │
│  - Historical outcomes                                      │
│  - Theoretical RR columns                                   │
│  - Realized RR columns                                      │
│  - One row per (date_local, instrument)                     │
│                                                             │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                        │
│  (Reads from storage, displays to user)                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  config.py                  Trading Apps                    │
│  - Mirrors validated_setups - Query daily_features          │
│  - Used for app logic       - Query validated_setups        │
│  - MUST sync with DB        - Display realized metrics      │
│                             - NO internal calculations      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## OWNERSHIP TABLE

| **Component** | **Owns** | **Consumes** | **Produces** | **Must NOT** |
|---------------|----------|--------------|--------------|--------------|
| **cost_model.py** | Contract specs, broker costs, realized RR formula | Nothing (leaf node) | Realized RR calculations | Hard-code in other files |
| **validated_setups (DB)** | Active strategies, RR targets, filters | Nothing (data entry) | Strategy definitions | Be duplicated in config.py |
| **execution_engine.py** | Trade simulation logic, entry/exit rules | cost_model.py, daily_features (for ORB levels) | TradeResult (with realized RR) | Calculate RR itself (delegates to cost_model) |
| **build_daily_features.py** | Aggregation logic | execution_engine.py, bars_1m/5m | daily_features rows | Duplicate execution logic |
| **daily_features (DB)** | Historical trade outcomes, per-trade realized RR (rr, risk_$, reward_$) | build_daily_features.py writes | Query results for apps | Be manually edited, store strategy-level metrics (expectancy belongs in validated_setups) |
| **config.py** | App-level mirrors of validated_setups | validated_setups (sync required) | Filters for apps | Diverge from validated_setups |
| **Trading Apps** | UI, display logic | daily_features, validated_setups, config.py | User interface | Calculate RR themselves |

---

## CRITICAL ARCHITECTURAL RULE: Trade-Level vs Strategy-Level Metrics

### Per-Trade Metrics (stored in daily_features)
- **realized_rr**: Realized RR for this specific trade
- **realized_risk_dollars**: Risk in dollars (stop + costs)
- **realized_reward_dollars**: Reward in dollars (target - costs)

These are **deterministic** for a single trade - no aggregation needed.

### Strategy-Level Metrics (stored in validated_setups)
- **win_rate**: Percentage of trades that hit target
- **expected_r**: Expectancy = (win_rate × avg_win_R) - (loss_rate × avg_loss_R)
- **sample_size**: Number of trades used to calculate above

These require **aggregation across multiple trades** - cannot be computed per-trade.

### Why Expectancy Doesn't Belong in daily_features

**WRONG (architectural error):**
```sql
-- Storing NULL expectancy on every trade row
orb_1000_realized_expectancy: NULL  -- Trade #1
orb_1000_realized_expectancy: NULL  -- Trade #2
orb_1000_realized_expectancy: NULL  -- Trade #3
```

**CORRECT (strategy-level):**
```sql
-- validated_setups table
instrument: MGC
orb_time: 1000
rr: 1.5
win_rate: 60.3%
realized_expectancy: +0.369R  -- Computed across 526 trades
```

**Rule:** If a metric requires win rate, it belongs in `validated_setups`, NOT `daily_features`.

**Note:** `daily_features` has deprecated `orb_XXXX_realized_expectancy` columns (always NULL). These exist due to DuckDB dependency constraints but should be **IGNORED** by all code.

---

## DATA FLOW RULES

### Rule 1: Calculations Flow Downstream Only

```
cost_model.py
    → execution_engine.py
        → build_daily_features.py
            → daily_features (DB)
                → Apps
```

**NO UPSTREAM FLOW ALLOWED.**

### Rule 2: Theoretical vs Realized Separation

- **Theoretical RR**: Calculated in execution_engine (no costs)
- **Realized RR**: Calculated by cost_model (costs embedded)
- **Both stored**: daily_features has BOTH columns
- **Apps display BOTH**: User sees impact of reality

### Rule 3: Database is Source of Truth for Apps

Apps NEVER hard-code:
- ✅ Query `validated_setups` for active strategies
- ✅ Query `daily_features` for historical outcomes
- ❌ Hard-code RR values in config.py (mirror only, with sync test)
- ❌ Calculate RR internally (read from database)

### Rule 4: No Duplicated Constants

**BAD (current state):**
```python
# execution_engine.py
POINT_VALUE = 10.0

# some_other_file.py
POINT_VALUE = 10.0  # ❌ DUPLICATE!
```

**GOOD (after migration):**
```python
# execution_engine.py
from pipeline.cost_model import get_instrument_specs
specs = get_instrument_specs('MGC')
POINT_VALUE = specs['point_value']
```

### Rule 5: Migrations Are Atomic

When changing authoritative source:
1. Update cost_model.py OR validated_setups (never both at once)
2. Run validation tests (detect drift)
3. Update downstream (execution_engine → build_daily_features → daily_features)
4. Run validation tests again
5. Update apps last

---

## ENFORCEMENT MECHANISMS

### Validation Test Suite

**Purpose:** Detect drift automatically, fail loudly

#### Test 1: `test_app_sync.py` (EXISTS)
- **Checks:** config.py vs validated_setups (DB)
- **Frequency:** After ANY config.py or validated_setups change
- **Failure:** BLOCKS deployment

#### Test 2: `test_cost_model_sync.py` (NEEDED)
- **Checks:**
  - execution_engine.py uses cost_model (no hard-coded constants)
  - All instruments in INSTRUMENT_SPECS have COST_MODELS
- **Frequency:** After cost_model.py or execution_engine.py changes
- **Failure:** BLOCKS execution

#### Test 3: `test_realized_rr_sync.py` (NEEDED)
- **Checks:**
  - execution_engine realized RR matches cost_model calculation
  - daily_features realized columns populated for MGC (NULL for NQ/MPL)
- **Frequency:** After build_daily_features.py runs
- **Failure:** BLOCKS apps from using data

#### Test 4: `test_calculation_consistency.py` (NEEDED)
- **Checks:**
  - Same inputs to cost_model → same outputs (deterministic)
  - execution_engine + cost_model = daily_features values
  - No rounding errors or calculation drift
- **Frequency:** Weekly (regression test)
- **Failure:** Alerts for investigation

### Pre-Commit Hook (RECOMMENDED)
```bash
# .git/hooks/pre-commit
python test_app_sync.py || exit 1
python test_cost_model_sync.py || exit 1
```

Prevents commits that break synchronization.

---

## FAILURE MODES & DETECTION

### Failure Mode 1: Config Drift (ALREADY SEEN)
**Symptom:** config.py has old values, validated_setups has new values
**Detection:** test_app_sync.py fails
**Prevention:** NEVER update one without the other
**Recovery:** Update config.py, re-run test

### Failure Mode 2: Hard-Coded Constants
**Symptom:** Different files have different values for POINT_VALUE
**Detection:** test_cost_model_sync.py (grep for hard-coded constants)
**Prevention:** All imports from cost_model.py
**Recovery:** Replace hard-coded values with imports

### Failure Mode 3: Calculation Divergence
**Symptom:** execution_engine calculates RR=1.0, cost_model says RR=0.8
**Detection:** test_realized_rr_sync.py compares outputs
**Prevention:** execution_engine delegates to cost_model
**Recovery:** Remove duplicate calculation

### Failure Mode 4: Silent Database Drift
**Symptom:** daily_features has NULL realized RR for MGC (should be populated)
**Detection:** test_realized_rr_sync.py checks for NULL where not expected
**Prevention:** build_daily_features.py MUST call execution_engine
**Recovery:** Re-run build_daily_features.py

### Failure Mode 5: Stale App Data
**Symptom:** App shows old expectancy, database has new values
**Detection:** User reports incorrect numbers
**Prevention:** Apps query database on every load (no caching)
**Recovery:** Restart app

---

## MIGRATION ORDER (SAFE)

### Phase 1: Authoritative Layer ✅ DONE
1. Create `cost_model.py` (contract specs, costs, realized RR logic)
2. Verify `validated_setups` has correct MGC strategies
3. Create backup (git + database)

### Phase 2: Calculation Layer ✅ DONE
1. Update `execution_engine.py` to import cost_model
2. Add realized RR fields to TradeResult
3. Test: execution_engine produces realized RR correctly

### Phase 3: Aggregation Layer 🚧 IN PROGRESS
1. Update `build_daily_features.py` to call execution_engine
2. Add schema migration (24 realized RR columns)
3. Run migration (add columns to daily_features)
4. Rebuild daily_features for MGC (745 days)
5. Test: daily_features has realized RR populated

### Phase 4: Storage Layer 📋 TODO
1. Add realized RR columns to validated_setups (optional)
2. Update validated_setups with Phase 1 analysis results
3. Test: validated_setups has correct realized expectancy

### Phase 5: Application Layer 📋 TODO
1. Update config.py to include realized RR (mirror validated_setups)
2. Update trading apps to display realized metrics
3. Test: test_app_sync.py passes
4. Test: Apps display correct realized RR

### Phase 6: Enforcement Layer 📋 TODO
1. Create test_cost_model_sync.py
2. Create test_realized_rr_sync.py
3. Create test_calculation_consistency.py
4. Run all tests, verify PASS
5. Add pre-commit hook (optional)

### Phase 7: Validation 📋 TODO
1. Run full backtest with realized RR
2. Compare results to Phase 1 analysis (should match)
3. Verify no calculation drift
4. Mark as production-ready

---

## ADDING NEW INSTRUMENTS (NQ/MPL)

When ready to add NQ or MPL, follow this sequence:

### Step 1: Authoritative Layer
1. Add contract specs to cost_model.py INSTRUMENT_SPECS
2. Add cost model to cost_model.py COST_MODELS
3. Mark status='PRODUCTION'

### Step 2: Validation
1. Run test_cost_model_sync.py (verify no errors)
2. Run Phase 1 analysis (theoretical vs realized RR)
3. Verify edges survive reality

### Step 3: Database
1. Add strategies to validated_setups
2. Rebuild daily_features for new instrument
3. Verify realized RR columns populated

### Step 4: Apps
1. Update config.py with new instrument
2. Run test_app_sync.py
3. Update apps to handle new instrument

**NEVER skip steps. NEVER assume downstream will work.**

---

## CONTRACT DEFINITIONS

### Cost Model Contract
```python
# cost_model.py provides:
get_instrument_specs(instrument: str) -> dict
    # Returns: tick_size, tick_value, point_value, status

get_cost_model(instrument: str, stress_level: str) -> dict
    # Returns: commission_rt, slippage_rt, spread, total_friction

calculate_realized_rr(instrument, stop_points, rr_theoretical, stress_level) -> dict
    # Returns: realized_rr, realized_risk_$, realized_reward_$, delta_rr, delta_pct
```

### Execution Engine Contract
```python
# execution_engine.py provides:
simulate_orb_trade(...) -> TradeResult
    # Returns: TradeResult with theoretical + realized RR fields
    # Delegates realized RR calculation to cost_model
```

### Build Daily Features Contract
```python
# build_daily_features.py provides:
build_features_for_day(date_local: date) -> None
    # Calls execution_engine for each ORB
    # Stores results to daily_features (theoretical + realized columns)
    # NO internal calculations (pure aggregation)
```

---

## CHECKLIST FOR CHANGES

Before changing ANY authoritative source:

- [ ] Identify what layer owns this data
- [ ] Check if change affects downstream consumers
- [ ] Run relevant validation tests BEFORE change
- [ ] Make change to authoritative source
- [ ] Run validation tests AFTER change
- [ ] Update downstream consumers if tests fail
- [ ] Re-run validation tests until PASS
- [ ] Update documentation
- [ ] Git commit with clear description

**NEVER commit if validation tests fail.**

---

## CRITICAL REMINDERS

1. **cost_model.py is authoritative for RR calculations** - NO other file calculates realized RR
2. **validated_setups is authoritative for strategies** - config.py is a MIRROR only
3. **execution_engine delegates to cost_model** - NO hard-coded formulas
4. **build_daily_features delegates to execution_engine** - NO duplicate logic
5. **Apps read from database** - NO hard-coded values

**If you find duplicate calculations, DELETE them. If you find hard-coded constants, REPLACE with imports.**

---

## ARCHITECTURE REVIEW QUESTIONS

When reviewing code, ask:

1. Does this file calculate something that should come from an authoritative source?
2. Does this file hard-code a value that exists in cost_model or validated_setups?
3. Does this file duplicate logic from another layer?
4. If the authoritative source changes, will this file automatically update?
5. Is there a validation test that would catch drift in this relationship?

**If answer to #4 is NO, the architecture is broken.**

---

**Status:** Phase 3 in progress (Aggregation Layer)
**Next:** Update build_daily_features.py, run schema migration, rebuild features
**Blockers:** None (MGC cost model ready)
**NQ/MPL:** Blocked until contract specs + cost models provided
