# UPDATE13 IMPLEMENTATION PLAN

**Date**: 2026-01-29
**Goal**: Fix Quick/Auto Search per update13.txt requirements
**Status**: ⏳ IN PROGRESS

---

## KEY FINDING (PHASE 0)

**CRITICAL**: `tradeable_*` columns **DO EXIST** in daily_features!

```
- orb_{time}_tradeable_outcome        ← EXISTS!
- orb_{time}_tradeable_realized_rr    ← EXISTS!
- orb_{time}_tradeable_risk_dollars
- orb_{time}_tradeable_reward_dollars
```

**BUT**: These columns store **SINGLE RR TARGET only** (no RR dimension).

**Comparison**:
- `daily_features`: ONE outcome/RR per ORB time (proxy data)
- `validated_setups`: MULTIPLE RR per ORB time (RR-specific)

---

## PHASE 0 FINDINGS (✅ COMPLETE)

### 1. Column Structure:
```
1000 ORB columns in daily_features:
- orb_1000_outcome              ← Original (limit order entry)
- orb_1000_r_multiple           ← Original realized RR
- orb_1000_tradeable_outcome    ← Tradeable (1st close outside)
- orb_1000_tradeable_realized_rr ← Tradeable realized RR
- orb_1000_stop_price
- orb_1000_risk_ticks
(+ mfe, mae, entry/target prices, etc.)
```

### 2. RR Dimension:
- **daily_features**: NO RR dimension (single RR per ORB)
- **validated_setups**: YES RR dimension (multiple RR per ORB)

### 3. Sample Data (1000 ORB):
```
2026-01-29: LOSS, -1.000R
2026-01-28: WIN,  +1.000R
2026-01-27: LOSS, -1.000R
```

### 4. Validated Setups (MGC):
- Multiple RR targets per ORB time (1.5, 2.0, 2.5, 3.0, 8.0)
- Has win_rate, expected_r, sample_size

---

## CURRENT STATE (WHAT I ALREADY FIXED)

### ✅ Done (UPDATE13 Earlier):
1. Fixed column names: Use `orb_{time}_r_multiple` (not tradeable)
2. Removed RR projection logic
3. Restricted UI to RR=1.0 only
4. Verified data clean (WIN with RR <= 0 bug fixed)

### ❌ Still Wrong:
1. **Using wrong columns!** Should use `tradeable_*` not base `r_multiple`
2. **No Truth Panel** - UI doesn't show what's being measured
3. **Misleading labels** - Says "RR=1.0" but it's proxy data
4. **No sanity checks** - UI doesn't verify invariants
5. **No verification script** - No automated checking

---

## IMPLEMENTATION PLAN

### PHASE 1: Fix Core Logic (✅ PARTIAL, ❌ NEEDS COMPLETION)

#### A. Use Correct Columns (CRITICAL FIX)
**Current (WRONG)**:
```python
realized_rr_col = f"orb_{orb_time}_r_multiple"
outcome_col = f"orb_{orb_time}_outcome"
```

**Should be**:
```python
realized_rr_col = f"orb_{orb_time}_tradeable_realized_rr"
outcome_col = f"orb_{orb_time}_tradeable_outcome"
```

**Why**: `tradeable_*` columns use correct entry rule (1st close outside ORB), not limit order.

#### B. Standardize Metric Names
```python
target_hit_rate := pct(tradeable_outcome == 'WIN')  # Hit profit target
profitable_trade_rate := pct(tradeable_realized_rr > 0)  # Profitable after costs
expected_r := mean(tradeable_realized_rr)  # Average realized R
```

#### C. Label Correctly (NO MORE "RR=1.0")
**Current label**: "RR Target: 1.0 (baseline data only)"
**Should be**: "Stored Model Proxy (from daily_features tradeable columns)"

**Add warning**:
> "These metrics use a single stored model per ORB time. For RR-specific results, use validated_setups or run a full backtest."

---

### PHASE 2: Add Truth Panel (❌ NOT DONE)

Add two expanders in Quick Search results:

#### Expander 1: "What exactly is being measured?"
```
Data Source: daily_features table
Entry Rule: 1st close outside ORB range
Stop Loss: Opposite edge of ORB
Profit Target: Stored model (not RR-specific)

Columns used:
- orb_{time}_tradeable_outcome (WIN = hit target)
- orb_{time}_tradeable_realized_rr (realized R after costs)

Definitions:
- Target Hit Rate: % trades that hit profit target (outcome == 'WIN')
- Profitable Rate: % trades with positive realized R (realized_rr > 0)
- Expected R: Average realized R across all trades
```

#### Expander 2: "Sanity Checks"
```
Total Trades: 530
WIN outcomes: 318 (60.0%)
Profitable (RR > 0): 318 (60.0%)
Losses (RR < 0): 212 (40.0%)

Invariant checks:
✅ WIN count <= Profitable count (318 <= 318)
✅ No WIN with RR <= 0 (found 0 violations)
✅ Expected R matches mean(realized_rr) (within 0.001)
```

---

### PHASE 3: Data Model / Storage (✅ ALREADY DONE)

Existing tables are sufficient:
- `search_runs` (run metadata)
- `search_candidates` (results with metrics)
- `search_memory` (deduplication)

Fields in `search_candidates`:
- ✅ `target_hit_rate` (exists)
- ✅ `profitable_trade_rate` (exists)
- ✅ `expected_r_proxy` → use `score_proxy` (exists)
- ✅ `rr_target` (exists, set to NULL for proxy mode)

**No migration needed**.

---

### PHASE 4: Verification Script (❌ NOT DONE)

Create `scripts/check/check_quick_search.py`:

```python
"""
Verify Quick Search logic and invariants.
Runtime: <10 seconds
"""

def test_column_usage():
    # Verify engine queries tradeable_* columns
    pass

def test_metric_definitions():
    # Verify target_hit_rate computed from outcome
    # Verify profitable_trade_rate computed from realized_rr
    pass

def test_sanity_invariants():
    # Check: target_hit <= profitable_trade
    # Check: no WIN with RR <= 0
    # Check: expected_r == mean(realized_rr)
    pass

def test_ui_labels():
    # Verify no "RR=1.0" labels
    # Verify "Stored Model Proxy" shown
    pass
```

---

## TODO LIST (PRIORITIZED)

### 🔴 CRITICAL (DO FIRST):

- [ ] **1.1**: Fix column names in `auto_search_engine.py`
  - Change from `orb_{time}_r_multiple` → `orb_{time}_tradeable_realized_rr`
  - Change from `orb_{time}_outcome` → `orb_{time}_tradeable_outcome`
  - Lines: 357-372

- [ ] **1.2**: Update metric names for clarity
  - `target_hit_rate` = pct(tradeable_outcome == 'WIN')
  - `profitable_trade_rate` = pct(tradeable_realized_rr > 0)
  - `expected_r` = mean(tradeable_realized_rr)

- [ ] **1.3**: Fix UI labels in `app_canonical.py`
  - Remove "RR=1.0" label
  - Add "Stored Model Proxy (from daily_features)" label
  - Add warning about RR-specific limitations

### 🟡 HIGH PRIORITY (DO NEXT):

- [ ] **2.1**: Add "What exactly is being measured?" expander
  - Show data source, entry rule, columns used
  - Show metric definitions

- [ ] **2.2**: Add "Sanity Checks" expander
  - Show counts (n_total, n_win, n_profit, n_loss)
  - Run invariant checks with ✅/❌ indicators
  - Highlight any violations in red

### 🟢 MEDIUM PRIORITY (DO AFTER):

- [ ] **4.1**: Create `scripts/check/check_quick_search.py`
  - Test column usage
  - Test metric definitions
  - Test sanity invariants
  - Runtime <10 seconds

- [ ] **4.2**: Update documentation
  - Update UPDATE13_COMPLETE.md with final state
  - Create user guide for Quick Search
  - Document limitations clearly

### 🔵 LOW PRIORITY (OPTIONAL):

- [ ] **3.1**: Add metadata to search_candidates if needed
  - Already sufficient, no changes needed

---

## STOP CONDITIONS

❌ **CANNOT PROCEED** if:
- tradeable_* columns don't exist → VERIFIED: They exist ✅
- No deterministic way to compute outcomes → VERIFIED: Have tradeable_outcome ✅
- RR-specific columns needed → VERIFIED: Not available, use proxy mode ✅

✅ **CAN PROCEED** with current plan.

---

## VERIFICATION COMMANDS

After implementation:

```bash
# 1. Run verification script
python scripts/check/check_quick_search.py

# 2. Test with sample query
python scratchpad/test_search_fixed.py

# 3. Launch app and test UI
streamlit run trading_app/app_canonical.py
```

---

## TIMELINE ESTIMATE

- **Task 1.1-1.3** (Critical): 20 minutes
- **Task 2.1-2.2** (High): 30 minutes
- **Task 4.1-4.2** (Medium): 20 minutes
- **Total**: ~70 minutes (1 hour 10 min)

---

## FILES TO MODIFY

### Must Modify:
1. `trading_app/auto_search_engine.py` (lines 357-372, 371-382)
2. `trading_app/app_canonical.py` (Quick Search UI section)

### Create New:
3. `scripts/check/check_quick_search.py`

### Update:
4. `UPDATE13_COMPLETE.md` (final summary)

---

**Next Step**: Start with Task 1.1 (fix column names).
