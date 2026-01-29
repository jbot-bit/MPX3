# Update7 Implementation Plan - Validation Refactoring

**Status:** PLANNING PHASE
**Scope:** Refactor validation logic to use graded classifications instead of binary PASS/FAIL

---

## Current State

**File:** `trading_app/edge_utils.py`
**Function:** `run_validation_stub()` (lines 823-1000+)

**Current Logic:**
- Returns binary `edge_passes_gates: bool`
- Single PASS/FAIL based on AND conditions:
  - `sample_size >= 30`
  - `expected_r >= 0.15`
  - `(stress_25_pass OR stress_50_pass)`
  - `walk_forward_pass`

**Problem:**
- Binary verdict loses information
- FAIL could mean many things (signal absent, overfit, regime-dependent, etc.)
- Hard to interpret for humans
- Memory routing is binary (re-search or don't)

---

## Required Changes (from update7.txt)

### 1. Classification Layers

Split validation into 4 independent layers:

#### Layer 1: Signal Existence (Binary)
- **Criteria:** `expected_r > 0 AND beats_control == true`
- **Values:** `PRESENT` / `ABSENT`
- **Meaning:** Does the edge have positive expectancy above control?

#### Layer 2: Robustness (Graded)
- **Criteria:** Stress tests + walk-forward results
- **Values:** `NONE` / `FRAGILE` / `ROBUST`
- **Mapping:**
  - `ROBUST`: All 3 pass (stress_25, stress_50, walk_forward)
  - `FRAGILE`: 1-2 pass
  - `NONE`: 0 pass

#### Layer 3: Trade Quality (Informational)
- **Metrics:** MAE, MFE, max_dd, sample_size
- **Values:** `GOOD` / `POOR`
- **Mapping:**
  - `GOOD`: sample_size >= 30 AND max_dd > -3.0
  - `POOR`: Otherwise
- **Note:** Informational only, doesn't block promotion

#### Layer 4: Explainability (Manual Flag)
- **Values:** `YES` / `NO` / `UNCLEAR`
- **Set by:** Human during review
- **Default:** `UNCLEAR`

### 2. Classification Object

Based on Signal + Robustness, classify edge into one of 4 categories:

```python
STRUCTURAL   # Signal ABSENT, Robustness NONE → No edge exists
OVERFIT      # Signal PRESENT, Robustness NONE → Edge exists but fragile
REGIME       # Signal PRESENT, Robustness FRAGILE → Works in some conditions
DATA_LIMITED # Sample size < 30 → Need more data
```

### 3. Memory Routing Rules

Replace binary re-search logic with category-based routing:

- **STRUCTURAL** → Never re-search (no edge found)
- **OVERFIT** → Allow variant searches (try different filters/params)
- **REGIME** → Allow with filters (add regime-specific filters)
- **DATA_LIMITED** → Park and retry later (when more data available)

---

## Implementation Steps

### Step 1: Create Classification Dataclass

**File:** `trading_app/validation_classification.py` (NEW)

```python
from dataclasses import dataclass
from enum import Enum

class SignalStatus(Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"

class RobustnessLevel(Enum):
    ROBUST = "ROBUST"     # All 3 pass
    FRAGILE = "FRAGILE"   # 1-2 pass
    NONE = "NONE"         # 0 pass

class TradeQuality(Enum):
    GOOD = "GOOD"
    POOR = "POOR"

class Explainability(Enum):
    YES = "YES"
    NO = "NO"
    UNCLEAR = "UNCLEAR"

class EdgeClassification(Enum):
    STRUCTURAL = "STRUCTURAL"      # No edge
    OVERFIT = "OVERFIT"           # Edge exists, fragile
    REGIME = "REGIME"             # Edge exists, conditional
    DATA_LIMITED = "DATA_LIMITED"  # Need more data

@dataclass
class ValidationResult:
    """Graded validation result (replaces binary PASS/FAIL)"""

    # 4 Layers
    signal: SignalStatus
    robustness: RobustnessLevel
    trade_quality: TradeQuality
    explainability: Explainability

    # Classification (derived from signal + robustness)
    classification: EdgeClassification

    # Raw metrics (behind dropdown in UI)
    metrics: dict  # {expected_r, sample_size, stress_25, stress_50, etc.}

    # Promotion eligibility (derived)
    can_promote: bool  # True if Signal=PRESENT and Robustness>=FRAGILE

    @classmethod
    def from_metrics(cls, metrics: dict, explainability: Explainability = Explainability.UNCLEAR):
        """Construct ValidationResult from raw metrics"""

        # Layer 1: Signal Existence
        signal = (
            SignalStatus.PRESENT
            if metrics.get('expected_r', 0) > 0 and metrics.get('beats_control', False)
            else SignalStatus.ABSENT
        )

        # Layer 2: Robustness
        stress_25 = metrics.get('stress_test_25') == 'PASS'
        stress_50 = metrics.get('stress_test_50') == 'PASS'
        walk_forward = metrics.get('walk_forward') == 'PASS'

        passed_tests = sum([stress_25, stress_50, walk_forward])

        if passed_tests == 3:
            robustness = RobustnessLevel.ROBUST
        elif passed_tests >= 1:
            robustness = RobustnessLevel.FRAGILE
        else:
            robustness = RobustnessLevel.NONE

        # Layer 3: Trade Quality
        sample_size = metrics.get('sample_size', 0)
        max_dd = metrics.get('max_dd', -999)

        trade_quality = (
            TradeQuality.GOOD
            if sample_size >= 30 and max_dd > -3.0
            else TradeQuality.POOR
        )

        # Classification
        if sample_size < 30:
            classification = EdgeClassification.DATA_LIMITED
        elif signal == SignalStatus.ABSENT:
            classification = EdgeClassification.STRUCTURAL
        elif robustness == RobustnessLevel.NONE:
            classification = EdgeClassification.OVERFIT
        else:  # Signal PRESENT and Robustness >= FRAGILE
            classification = EdgeClassification.REGIME

        # Promotion eligibility
        can_promote = (
            signal == SignalStatus.PRESENT and
            robustness in (RobustnessLevel.FRAGILE, RobustnessLevel.ROBUST)
        )

        return cls(
            signal=signal,
            robustness=robustness,
            trade_quality=trade_quality,
            explainability=explainability,
            classification=classification,
            metrics=metrics,
            can_promote=can_promote
        )
```

### Step 2: Update run_validation_stub()

**File:** `trading_app/edge_utils.py`

**Change:**
```python
# OLD
return {
    'passes': edge_passes_gates,  # Binary
    'metrics': edge_metrics,
    'control': control_result
}

# NEW
from validation_classification import ValidationResult

validation_result = ValidationResult.from_metrics(
    metrics=edge_metrics,
    explainability=Explainability.UNCLEAR  # Default, user can update
)

return {
    'result': validation_result,  # Graded classification
    'control': control_result,
    # Backward compatibility (optional)
    'passes': validation_result.can_promote
}
```

### Step 3: Update UI Display

**File:** `trading_app/app_canonical.py`

**Current (assumed):**
```python
if validation['passes']:
    st.success("✅ VALIDATION PASSED")
else:
    st.error("❌ VALIDATION FAILED")
```

**New:**
```python
result = validation['result']

# 4 colored tiles
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Signal",
        result.signal.value,
        delta=None,
        delta_color="normal" if result.signal == SignalStatus.PRESENT else "inverse"
    )

with col2:
    st.metric(
        "Robustness",
        result.robustness.value,
        delta=None
    )

with col3:
    st.metric(
        "Trade Quality",
        result.trade_quality.value,
        delta=None
    )

with col4:
    st.metric(
        "Explainability",
        result.explainability.value,
        delta=None
    )

# Classification banner
if result.classification == EdgeClassification.STRUCTURAL:
    st.error(f"📊 Classification: **{result.classification.value}** (No edge detected)")
elif result.classification == EdgeClassification.OVERFIT:
    st.warning(f"📊 Classification: **{result.classification.value}** (Edge exists but fragile)")
elif result.classification == EdgeClassification.REGIME:
    st.success(f"📊 Classification: **{result.classification.value}** (Edge conditional)")
elif result.classification == EdgeClassification.DATA_LIMITED:
    st.info(f"📊 Classification: **{result.classification.value}** (Need more data)")

# Raw metrics behind dropdown
with st.expander("📈 Raw Metrics"):
    st.json(result.metrics)

# Promotion eligibility
if result.can_promote:
    st.success("✅ Eligible for promotion")
else:
    st.warning("⚠️ Not eligible for promotion (signal absent or robustness too low)")
```

### Step 4: Update Memory Routing

**File:** `trading_app/edge_utils.py` (or search_memory routing logic)

**Current (assumed):**
```python
if validation_failed:
    add_to_memory(edge_id, status='FAILED')
    # Don't re-search
```

**New:**
```python
classification = validation_result.classification

if classification == EdgeClassification.STRUCTURAL:
    add_to_memory(edge_id, status='STRUCTURAL', allow_research=False)
    # Never re-search

elif classification == EdgeClassification.OVERFIT:
    add_to_memory(edge_id, status='OVERFIT', allow_research=True, allow_variants=True)
    # Allow variant searches (different params)

elif classification == EdgeClassification.REGIME:
    add_to_memory(edge_id, status='REGIME', allow_research=True, require_filters=True)
    # Allow with regime-specific filters

elif classification == EdgeClassification.DATA_LIMITED:
    add_to_memory(edge_id, status='DATA_LIMITED', allow_research=True, retry_after_days=30)
    # Park and retry later
```

### Step 5: Update search_memory Table

**File:** `scripts/migrations/add_classification_to_search_memory.py` (NEW)

```sql
ALTER TABLE search_memory
ADD COLUMN classification VARCHAR;  -- STRUCTURAL, OVERFIT, REGIME, DATA_LIMITED

ALTER TABLE search_memory
ADD COLUMN allow_research BOOLEAN DEFAULT TRUE;

ALTER TABLE search_memory
ADD COLUMN allow_variants BOOLEAN DEFAULT FALSE;

ALTER TABLE search_memory
ADD COLUMN require_filters BOOLEAN DEFAULT FALSE;

ALTER TABLE search_memory
ADD COLUMN retry_after_days INTEGER;
```

---

## Testing Plan

### Test 1: Classification Logic

```python
# Test STRUCTURAL
metrics = {'expected_r': -0.05, 'beats_control': False, 'sample_size': 50}
result = ValidationResult.from_metrics(metrics)
assert result.classification == EdgeClassification.STRUCTURAL
assert result.can_promote == False

# Test OVERFIT
metrics = {'expected_r': 0.25, 'beats_control': True, 'sample_size': 50,
           'stress_test_25': 'FAIL', 'stress_test_50': 'FAIL', 'walk_forward': 'FAIL'}
result = ValidationResult.from_metrics(metrics)
assert result.classification == EdgeClassification.OVERFIT
assert result.can_promote == False

# Test REGIME
metrics = {'expected_r': 0.25, 'beats_control': True, 'sample_size': 50,
           'stress_test_25': 'PASS', 'stress_test_50': 'FAIL', 'walk_forward': 'PASS'}
result = ValidationResult.from_metrics(metrics)
assert result.classification == EdgeClassification.REGIME
assert result.can_promote == True

# Test DATA_LIMITED
metrics = {'expected_r': 0.25, 'beats_control': True, 'sample_size': 15}
result = ValidationResult.from_metrics(metrics)
assert result.classification == EdgeClassification.DATA_LIMITED
assert result.can_promote == False
```

### Test 2: Memory Routing

```python
# Test STRUCTURAL → no re-search
add_classification_to_memory(edge_id, EdgeClassification.STRUCTURAL)
assert can_research(edge_id) == False

# Test OVERFIT → allow variants
add_classification_to_memory(edge_id, EdgeClassification.OVERFIT)
assert can_research(edge_id) == True
assert can_research_variant(edge_id) == True

# Test REGIME → allow with filters
add_classification_to_memory(edge_id, EdgeClassification.REGIME)
assert can_research(edge_id) == True
assert must_add_filters(edge_id) == True
```

---

## Files to Create/Modify

### New Files (2)
1. `trading_app/validation_classification.py` - Classification logic (~150 lines)
2. `scripts/migrations/add_classification_to_search_memory.py` - Migration (~50 lines)

### Modified Files (2)
1. `trading_app/edge_utils.py` - Update run_validation_stub() (~20 lines changed)
2. `trading_app/app_canonical.py` - Update validation UI (~50 lines changed)

**Total:** ~270 lines of new/changed code

---

## Backward Compatibility

**Maintain:**
- `validation['passes']` key for old code (maps to `can_promote`)
- Existing metric keys in `metrics` dict
- Existing database columns

**No breaking changes** - just adds new classification layer on top.

---

## Next Steps

1. ✅ Create implementation plan (this document)
2. ⏳ Get user approval on approach
3. ⏳ Create `validation_classification.py`
4. ⏳ Update `edge_utils.py`
5. ⏳ Update `app_canonical.py` UI
6. ⏳ Create migration script
7. ⏳ Write tests
8. ⏳ Verify end-to-end

---

**Estimated time:** 2-3 hours for full implementation + testing

**User decision needed:** Approve this plan or suggest modifications before proceeding with code changes.
