# 🛡️ PHASE 0 REVISED - Blocker Fixes (No Schema Changes)

**Status:** PLAN READY FOR APPROVAL
**Date:** 2026-01-31
**Guardian:** ON
**Constraints:** NO schema changes, NO destructive deletes, use existing fields only

---

## ✅ APPROVED CONSTRAINTS

1. ✅ NO new columns or tables
2. ✅ NO ALTER TABLE statements
3. ✅ NO DELETE FROM (non-destructive only)
4. ✅ Use existing write paths only (`set_candidate_status()`, etc.)
5. ✅ Use existing fields only (`notes`, `status`, `filter_spec_json`)

---

## 📋 PHASE 0 TASKS

### Task 1: Enforce edge_candidates as Canonical Registry

**Goal:** Stop querying edge_registry, use edge_candidates everywhere

#### 1.1 Fix get_all_candidates() to Query Correct Table

**File:** `trading_app/edge_utils.py`
**Line:** 236
**Current:**
```python
query = "SELECT * FROM edge_registry WHERE 1=1"
```
**Change to:**
```python
query = "SELECT * FROM edge_candidates WHERE 1=1"
```

**Impact:** All code using `get_all_candidates()` will now get correct data (289 candidates instead of 9)

---

#### 1.2 Fix get_candidate_by_id() to Query Correct Table

**File:** `trading_app/edge_utils.py`
**Line:** 262
**Current:**
```python
result = db_connection.execute(
    "SELECT * FROM edge_registry WHERE edge_id = ?",
    [edge_id]
).fetchdf()
```
**Change to:**
```python
result = db_connection.execute(
    "SELECT * FROM edge_candidates WHERE candidate_id = ?",
    [edge_id]  # Note: edge_id param name is misleading, actually candidate_id
).fetchdf()
```

**Also update:** Function signature to accept `candidate_id: int` instead of `edge_id: str`
**Line:** 255-258

**Impact:** Lookups will work for edge_candidates (currently broken)

---

#### 1.3 Update app_canonical.py Filters to Use edge_candidates

**File:** `trading_app/app_canonical.py`

**Change 1: Never-tested filter (line 1860)**
**Current:**
```python
never_tested = get_all_candidates(
    app_state.db_connection,
    status_filter='NEVER_TESTED'
)
```
**Change to:**
```python
never_tested = get_all_candidates(
    app_state.db_connection,
    status_filter='DRAFT'  # Translate: NEVER_TESTED → DRAFT
)
```

**Change 2: Validated filter (line 2975)**
**Current:**
```python
validated = get_all_candidates(
    app_state.db_connection,
    status_filter='VALIDATED'
)
```
**Change to:**
```python
validated = get_all_candidates(
    app_state.db_connection,
    status_filter='APPROVED'  # Translate: VALIDATED → APPROVED
)
```

**Impact:** Filters will return actual candidates (currently return nothing)

---

### Task 2: Status Translation Layer (No Schema Changes)

**Goal:** Normalize status semantics without changing database

#### 2.1 Create Status Translation Helper

**File:** `trading_app/status_translator.py` (NEW - no schema change)
**Location:** Create new file
**Content:**
```python
"""
Status Translation Layer - Normalize edge_registry vs edge_candidates statuses

NO SCHEMA CHANGES - Pure translation between old and new vocabularies
"""

# edge_registry → edge_candidates status mapping
LEGACY_TO_CANONICAL = {
    'NEVER_TESTED': 'DRAFT',
    'TESTED_FAILED': 'REJECTED',
    'VALIDATED': 'APPROVED',
    'PROMOTED': 'PROMOTED',  # Will add to edge_candidates valid statuses
    'RETIRED': 'REJECTED'
}

# edge_candidates → edge_registry status mapping (reverse)
CANONICAL_TO_LEGACY = {v: k for k, v in LEGACY_TO_CANONICAL.items()}


def translate_status_to_canonical(legacy_status: str) -> str:
    """
    Translate edge_registry status → edge_candidates status

    Args:
        legacy_status: Status from edge_registry vocabulary

    Returns:
        Equivalent status in edge_candidates vocabulary
    """
    return LEGACY_TO_CANONICAL.get(legacy_status, legacy_status)


def translate_status_to_legacy(canonical_status: str) -> str:
    """
    Translate edge_candidates status → edge_registry status

    Args:
        canonical_status: Status from edge_candidates vocabulary

    Returns:
        Equivalent status in edge_registry vocabulary
    """
    return CANONICAL_TO_LEGACY.get(canonical_status, canonical_status)


def is_promoted(candidate: dict) -> bool:
    """
    Check if candidate is promoted (canonical way)

    Args:
        candidate: Row from edge_candidates table

    Returns:
        True if promoted to validated_setups
    """
    return candidate.get('promoted_validated_setup_id') is not None
```

**Impact:** NO schema change, pure code layer

---

#### 2.2 Update edge_candidate_utils.py Valid Statuses

**File:** `trading_app/edge_candidate_utils.py`
**Line:** 205
**Current:**
```python
valid_statuses = ['DRAFT', 'PENDING', 'APPROVED', 'REJECTED']
```
**Change to:**
```python
valid_statuses = ['DRAFT', 'PENDING', 'APPROVED', 'REJECTED', 'PROMOTED']
```

**Impact:** Allow PROMOTED status in edge_candidates (no schema change, just validation)

---

#### 2.3 Update edge_pipeline.py to Set PROMOTED Status

**File:** `trading_app/edge_pipeline.py`
**Line:** 321
**Current:**
```python
conn.execute("""
    UPDATE edge_candidates
    SET promoted_validated_setup_id = ?,
        promoted_by = ?,
        promoted_at = CURRENT_TIMESTAMP
    WHERE candidate_id = ?
""", [setup_id, promoted_by, candidate_id])
```
**Change to:**
```python
conn.execute("""
    UPDATE edge_candidates
    SET promoted_validated_setup_id = ?,
        promoted_by = ?,
        promoted_at = CURRENT_TIMESTAMP,
        status = 'PROMOTED'
    WHERE candidate_id = ?
""", [setup_id, promoted_by, candidate_id])
```

**Impact:** Promoted candidates get PROMOTED status (matches legacy vocabulary)

---

### Task 3: PB Dedupe (Spec-Hash + Existing Fields)

**Goal:** Prevent duplicate creation without schema changes

#### 3.1 Implement Real _candidate_exists() Using Existing Fields

**File:** `trading_app/pb_grid_generator.py`
**Line:** 105-121
**Current:**
```python
def _candidate_exists(edge_id: str) -> bool:
    """
    Check if candidate with given edge_id already exists in edge_candidates.

    Note: Currently simplified to always return False for first-time generation.
          Production implementation would use proper hash-based deduplication.
    """
    # TODO: Implement proper hash-based deduplication
    # Would require storing edge_id hash in edge_candidates table
    # For now, allow all candidates (first-time generation)
    return False
```

**Change to:**
```python
def _candidate_exists(edge_id: str, db_connection) -> bool:
    """
    Check if candidate with given edge_id already exists in edge_candidates.

    Uses spec-hash stored in notes field for deduplication.
    NO SCHEMA CHANGES - uses existing notes VARCHAR field.

    Args:
        edge_id: Deterministic hash of parameters
        db_connection: DuckDB connection

    Returns:
        True if exists, False otherwise
    """
    # Query edge_candidates for matching spec-hash in notes
    # Format: "spec_hash:{edge_id}" in notes field
    result = db_connection.execute("""
        SELECT candidate_id
        FROM edge_candidates
        WHERE notes LIKE ?
        LIMIT 1
    """, [f"%spec_hash:{edge_id}%"]).fetchone()

    return result is not None
```

**Impact:** Real dedupe without schema changes (uses existing notes field)

---

#### 3.2 Store Spec-Hash in Notes Field at Creation

**File:** `trading_app/pb_grid_generator.py`
**Line:** 226-230 (notes building section)
**Current:**
```python
# Build filter_spec (store PB tokens here)
filter_spec = {
    'entry_token': combo['entry_token'],
    'confirm_token': combo['confirm_token'],
    'stop_token': combo['stop_token'],
    'tp_token': combo['tp_token'],
    'sl_mode': combo['stop_token'],  # Map to existing field
    'orb_size_filter': None  # No size filter for base grid
}
```

**Add after line 196 (after edge_id generation):**
```python
# Append spec_hash to notes for deduplication (NO SCHEMA CHANGE)
notes_with_hash = f"spec_hash:{edge_id}\n{hypothesis_text}"
```

**Then update line 244 (create_edge_candidate call):**
**Find:** The line passing `notes` parameter (if exists, or add it)
**Change to:** Pass `notes_with_hash` instead

**Impact:** Spec-hash stored in existing notes field, enables dedupe

---

#### 3.3 Update create_pb_candidate() to Pass db_connection to _candidate_exists()

**File:** `trading_app/pb_grid_generator.py`
**Line:** 185
**Current:**
```python
if _candidate_exists(edge_id):
    logger.info(f"Skipping duplicate: {name}")
    return None
```
**Change to:**
```python
if _candidate_exists(edge_id, db_connection):
    logger.info(f"Skipping duplicate: {name}")
    return None
```

**Impact:** Dedupe actually works (queries database)

---

### Task 4: Fix drift_monitor to Canonical Sources

**Goal:** Production monitoring uses correct table and status vocabulary

#### 4.1 Update drift_monitor.py to Query edge_candidates

**File:** `trading_app/drift_monitor.py`
**Line:** 225
**Current:**
```python
SELECT edge_id FROM edge_registry WHERE status = 'PROMOTED'
```
**Change to:**
```python
SELECT candidate_id, name
FROM edge_candidates
WHERE promoted_validated_setup_id IS NOT NULL
```

**Impact:** Monitoring actually finds promoted candidates (currently finds nothing)

---

#### 4.2 Import Status Translator in drift_monitor.py

**File:** `trading_app/drift_monitor.py`
**Line:** (top of file, after existing imports)
**Add:**
```python
from status_translator import is_promoted
```

**Then update usage:**
**Line:** 225 (replace query with helper)
```python
# Use canonical promoted check
promoted_candidates = [
    c for c in all_candidates
    if is_promoted(c)
]
```

**Impact:** Monitoring uses canonical promoted definition

---

### Task 5: Mark Duplicates Non-Destructively

**Goal:** Hide duplicates from worklists without deleting data

#### 5.1 Create Duplicate Marking Script (Uses Existing Write Paths)

**File:** `scripts/cleanup/mark_duplicate_candidates.py` (NEW)
**Location:** Create new file
**Content:**
```python
"""
Mark Duplicate Candidates as REJECTED (Non-Destructive)

Uses existing write path: set_candidate_status()
NO DELETES, NO SCHEMA CHANGES
"""

import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from trading_app.cloud_mode import get_database_connection
from trading_app.edge_candidate_utils import set_candidate_status
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_duplicates():
    """
    Find duplicate candidates by spec_hash in notes field

    Returns:
        List of (candidate_id, spec_hash) tuples for duplicates (keep first, mark rest)
    """
    conn = get_database_connection(read_only=True)

    # Find candidates with spec_hash in notes
    result = conn.execute("""
        SELECT
            candidate_id,
            created_at_utc,
            REGEXP_EXTRACT(notes, 'spec_hash:([a-f0-9]+)', 1) as spec_hash
        FROM edge_candidates
        WHERE notes LIKE '%spec_hash:%'
        ORDER BY spec_hash, created_at_utc
    """).fetchdf()

    conn.close()

    if result.empty:
        return []

    # Group by spec_hash, mark all but first as duplicates
    duplicates_to_mark = []

    for spec_hash in result['spec_hash'].unique():
        group = result[result['spec_hash'] == spec_hash]

        if len(group) > 1:
            # Keep first (oldest), mark rest as duplicates
            first_id = group.iloc[0]['candidate_id']
            duplicate_ids = group.iloc[1:]['candidate_id'].tolist()

            logger.info(f"spec_hash {spec_hash[:8]}... has {len(duplicate_ids)} duplicates")
            logger.info(f"  Keeping: candidate_id={first_id}")
            logger.info(f"  Marking as duplicates: {duplicate_ids}")

            for dup_id in duplicate_ids:
                duplicates_to_mark.append((dup_id, spec_hash))

    return duplicates_to_mark


def mark_duplicates(duplicates_to_mark):
    """
    Mark duplicates as REJECTED using existing write path

    Args:
        duplicates_to_mark: List of (candidate_id, spec_hash) tuples
    """
    for candidate_id, spec_hash in duplicates_to_mark:
        try:
            set_candidate_status(
                candidate_id=candidate_id,
                status='REJECTED',
                notes=f"Duplicate of spec_hash:{spec_hash[:16]}... (auto-marked)",
                actor='dedupe_script'
            )
            logger.info(f"✓ Marked candidate {candidate_id} as REJECTED (duplicate)")
        except Exception as e:
            logger.error(f"✗ Failed to mark candidate {candidate_id}: {e}")


def main():
    """Mark all duplicate candidates as REJECTED"""

    logger.info("="*60)
    logger.info("DUPLICATE MARKING SCRIPT (Non-Destructive)")
    logger.info("="*60)

    # Find duplicates
    logger.info("\n1. Finding duplicates...")
    duplicates_to_mark = find_duplicates()

    if not duplicates_to_mark:
        logger.info("✓ No duplicates found")
        return

    logger.info(f"\nFound {len(duplicates_to_mark)} duplicates to mark")

    # Confirm before marking
    response = input(f"\nMark {len(duplicates_to_mark)} duplicates as REJECTED? (yes/no): ")

    if response.lower() != 'yes':
        logger.info("Aborted by user")
        return

    # Mark duplicates (uses existing write path)
    logger.info("\n2. Marking duplicates...")
    mark_duplicates(duplicates_to_mark)

    logger.info("\n" + "="*60)
    logger.info("COMPLETE")
    logger.info("="*60)
    logger.info(f"Marked {len(duplicates_to_mark)} duplicates as REJECTED")
    logger.info("Duplicates are now hidden from default filters (status=REJECTED)")
    logger.info("Original data preserved - no deletions performed")


if __name__ == "__main__":
    main()
```

**Impact:** Duplicates marked as REJECTED (non-destructive), hidden from worklists

---

#### 5.2 Update UI Filters to Exclude REJECTED by Default

**File:** `trading_app/app_research_lab.py`
**Line:** 104-110 (load_candidates function)
**Current:**
```python
sql = """
    SELECT
        candidate_id, created_at_utc, instrument, name, hypothesis_text,
        status, test_window_start, test_window_end,
        metrics_json, filter_spec_json, notes
    FROM edge_candidates
    WHERE 1=1
"""
```
**Change to:**
```python
sql = """
    SELECT
        candidate_id, created_at_utc, instrument, name, hypothesis_text,
        status, test_window_start, test_window_end,
        metrics_json, filter_spec_json, notes
    FROM edge_candidates
    WHERE status != 'REJECTED'  -- Hide duplicates by default
"""
```

**Also add optional filter:**
**Line:** 109-110 (after status_filter check)
**Add:**
```python
# Allow explicit viewing of rejected candidates
if status_filter == "REJECTED":
    sql = sql.replace("WHERE status != 'REJECTED'", "WHERE status = 'REJECTED'")
```

**Impact:** Duplicates hidden from default view, but still queryable

---

## 📊 FILE/LINE CHANGES SUMMARY

### Files to Modify (8 files)

| File | Lines | Change Type | Risk |
|------|-------|-------------|------|
| `trading_app/edge_utils.py` | 236, 262, 255-258 | Query table change | LOW |
| `trading_app/app_canonical.py` | 1860, 2975 | Status translation | LOW |
| `trading_app/status_translator.py` | NEW | Translation layer | NONE (new file) |
| `trading_app/edge_candidate_utils.py` | 205 | Add valid status | LOW |
| `trading_app/edge_pipeline.py` | 321 | Set PROMOTED status | LOW |
| `trading_app/pb_grid_generator.py` | 105-121, 185, 196, 244 | Implement dedupe | MEDIUM |
| `trading_app/drift_monitor.py` | 225 + imports | Query canonical table | LOW |
| `trading_app/app_research_lab.py` | 104-110 | Hide rejected by default | LOW |

### Files to Create (2 files)

| File | Purpose | Risk |
|------|---------|------|
| `trading_app/status_translator.py` | Status translation layer | NONE (new code) |
| `scripts/cleanup/mark_duplicate_candidates.py` | Non-destructive duplicate marking | NONE (user-initiated script) |

---

## ✅ VALIDATION CHECKLIST

After Phase 0 completion, verify:

- [ ] `get_all_candidates()` returns 289 candidates (not 9)
- [ ] `app_canonical.py` filters return actual candidates
- [ ] `drift_monitor.py` finds promoted candidates
- [ ] PB grid generator skips duplicates (run twice, should skip 144 on second run)
- [ ] Duplicate marking script marks ~288 duplicates as REJECTED
- [ ] UI hides REJECTED candidates by default
- [ ] No schema changes made (run `DESCRIBE edge_candidates` - should be identical)

---

## 🚨 CONSTRAINTS MET

- ✅ NO new columns or tables
- ✅ NO ALTER TABLE statements
- ✅ NO DELETE FROM statements
- ✅ Uses existing write paths only (`set_candidate_status()`)
- ✅ Uses existing fields only (`notes`, `status`, `filter_spec_json`)
- ✅ Non-destructive duplicate marking (REJECTED status)
- ✅ Pure code changes (no schema modifications)

---

## 📋 APPROVAL REQUIRED

**Phase 0 revised plan ready. Proceed with implementation?**

**Changes:** 8 files modified, 2 files created, 0 schema changes

**Once approved, I will implement all changes in exact order shown above.**

---

**END OF PHASE 0 REVISED PLAN**
