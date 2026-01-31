# PASS 1 — PHASE 3B AUDIT REPORT

**Date:** 2026-01-31
**Mode:** CODE GUARDIAN (ENFORCED)
**Protocol:** FAIL-CLOSED

---

## P1.1 — Authority Files Check

| File | Status |
|------|--------|
| CLAUDE.md | EXISTS |
| GUARDIAN.md | EXISTS |
| APP_COMPLETE_SURVEY.md | EXISTS |
| CANONICAL_LOGIC.txt | EXISTS |

**Result:** ALL AUTHORITY FILES PRESENT ✓

---

## P1.2 — Target Issue Verification

### ID 1 (HIGH): DataBridge subprocess shell=True + no timeout

**File:** `trading_app/data_bridge.py`
**Function:** `run_backfill()`, `build_features()`
**Lines:** 160-166, 183-189, 235-241

**Code excerpts:**
```python
# Line 160-166 (databento backfill)
result = subprocess.run(
    cmd,
    cwd=str(self.root_dir),
    capture_output=True,
    text=True,
    shell=True  # Use shell on Windows for proper Python resolution
)

# Line 183-189 (projectx backfill)
result = subprocess.run(
    cmd,
    cwd=str(self.root_dir),
    capture_output=True,
    text=True,
    shell=True  # Use shell on Windows for proper Python resolution
)

# Line 235-241 (feature build per-day)
result = subprocess.run(
    cmd,
    cwd=str(self.root_dir),
    capture_output=True,
    text=True,
    shell=True  # Use shell on Windows
)
```

**Risk:** `shell=True` can cause argument parsing issues; no timeout means hung process blocks app indefinitely; stderr only shown on failure.

**Fix intent:** Replace `shell=True` with `shell=False`, use `sys.executable`, add timeout (300s), surface stderr to logs.

---

### ID 2 (HIGH): edge_utils.py dynamic SQL without orb_time allowlist

**File:** `trading_app/edge_utils.py`
**Function:** `run_real_validation()`
**Lines:** 502-508

**Code excerpt:**
```python
query = f"""
    SELECT date_local, orb_{orb_time}_size, orb_{orb_time}_break_dir, atr_20
    FROM daily_features
    WHERE instrument = ?
    {date_filter}
    AND orb_{orb_time}_outcome IS NOT NULL
    ORDER BY date_local
"""
```

**Risk:** `orb_time` comes from database (`edge['orb_time']`). If malicious value stored, SQL injection via column name interpolation.

**Valid orb_time values (from config.py:45-52):**
```
0900, 1000, 1100, 1800, 2300, 0030
```

**Fix intent:** Add explicit allowlist validation before interpolation; fail-closed with exception if invalid.

---

### ID 3 (MEDIUM): utils.py JOURNAL_TABLE interpolation

**File:** `trading_app/utils.py`
**Functions:** `log_to_journal()`, `get_recent_journal_entries()`
**Lines:** 12, 70, 86, 124, 132

**Code excerpts:**
```python
# Line 12
from config import DB_PATH, JOURNAL_TABLE, TZ_LOCAL

# Line 70
con.execute(f"""
    CREATE TABLE IF NOT EXISTS {JOURNAL_TABLE} (

# Line 86
con.execute(f"""
    INSERT INTO {JOURNAL_TABLE}

# Line 124
WHERE table_name = '{JOURNAL_TABLE}'

# Line 132
SELECT * FROM {JOURNAL_TABLE}
```

**Source:** JOURNAL_TABLE is hardcoded in config.py:181 as `"live_journal"` (not from env/user input).

**Risk:** Lower risk since hardcoded, but blindly interpolated into DDL/DML. Vulnerable if config ever changes to env var.

**Fix intent:** Add allowlist validation before interpolation; fail-closed if invalid.

---

### ID 4 (MEDIUM): app_canonical.py preflight subprocess no timeout

**File:** `trading_app/app_canonical.py`
**Function:** `_run_app_preflight_once()`
**Lines:** 110-115

**Code excerpt:**
```python
p = subprocess.run(
    ["python", "scripts/check/app_preflight.py"],
    capture_output=True,
    text=True,
    env={**os.environ, "PYTHONUTF8": "1"},
)
```

**Risk:** No timeout - app startup can hang indefinitely if preflight script hangs.

**Note:** Uses list args (good), no shell=True (good), fail-closed on error via `st.stop()` (good).

**Fix intent:** Add `timeout=30`, catch `TimeoutExpired` with clear error message.

---

### ID 5 (MEDIUM): data_bridge.py feature rebuild loop no timeout/progress

**File:** `trading_app/data_bridge.py`
**Function:** `build_features()`
**Lines:** 229-248

**Code excerpt:**
```python
current = start_date
while current <= end_date:
    date_str = current.isoformat()
    cmd = ['python', str(self.features_script), date_str]
    print(f"[CMD] {' '.join(cmd)}")

    result = subprocess.run(
        cmd,
        cwd=str(self.root_dir),
        capture_output=True,
        text=True,
        shell=True  # Use shell on Windows
    )
    # ... continues on error ...
    current += timedelta(days=1)
```

**Risk:** Sequential per-day calls with no per-call timeout; no progress visibility beyond print.

**Fix intent:** Add timeout per call (60s), add progress visibility (day X of Y).

---

### ID 6 (MEDIUM): ai_memory.py uses $N placeholders

**File:** `trading_app/ai_memory.py`
**Functions:** `save_message()`, `load_session_history()`, `search_history()`, etc.
**Lines:** 54, 67-69, 98-100, 107-108, 142, 175

**Code excerpt:**
```python
conn.execute("""
    INSERT INTO ai_chat_history (session_id, role, content, context_data, instrument, tags)
    VALUES ($1, $2, $3, $4, $5, $6)
""", [session_id, role, content, json.dumps(context_data or {}), instrument, tags or []])
```

**Analysis:**
- Uses `get_database_connection()` from `cloud_mode.py`
- This can return MotherDuck (cloud) or local DuckDB
- MotherDuck uses PostgreSQL-style `$N` placeholders
- DuckDB accepts BOTH `?` and `$N` placeholders

**Risk:** LOW - This is actually **intentionally compatible** with both local and cloud modes. DuckDB accepts both styles.

**Fix intent:** **SKIP** - No change needed. The `$N` style works correctly for both DuckDB and MotherDuck.

---

### ID 7 (LOW): redesign_components.py "Next step rail" not accessible

**File:** `trading_app/redesign_components.py`
**Function:** `render_next_step_rail()`
**Lines:** 229-240

**Code excerpt:**
```python
<div style="
    ...
    cursor: pointer;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
">
    {rail['action']} {rail['icon']}
</div>
```

**Risk:** Has `cursor: pointer` (looks clickable) but is NOT a real button/link. NOT keyboard accessible (no tabindex, no onclick). Visually misleading.

**Fix intent:** Either convert to `st.button()` for real functionality, OR remove `cursor: pointer` if purely informational.

---

## P1.3 — Constraints Check

| Constraint | Planned Fixes | Status |
|------------|---------------|--------|
| No schema/tables | None add tables | ✓ SAFE |
| No new DB write paths | None add writes | ✓ SAFE |
| No trading math changes | None touch math | ✓ SAFE |
| No execution/cost logic | None touch execution | ✓ SAFE |
| No pipeline output changes | None change outputs | ✓ SAFE |

**All planned fixes are within constraints.**

---

## PASS 2 Change Plan (Ordered)

| Priority | ID | File | Change |
|----------|-----|------|--------|
| 1 | ID 1 + ID 5 | trading_app/data_bridge.py | shell=False, sys.executable, timeouts, progress |
| 2 | ID 2 | trading_app/edge_utils.py | ORB_TIME allowlist validation |
| 3 | ID 3 | trading_app/utils.py | JOURNAL_TABLE allowlist validation |
| 4 | ID 4 | trading_app/app_canonical.py | 30s timeout on preflight subprocess |
| 5 | ID 6 | trading_app/ai_memory.py | **SKIP** - works correctly as-is |
| 6 | ID 7 | trading_app/redesign_components.py | Remove cursor:pointer or convert to button |

**Total files to modify:** 5 (data_bridge, edge_utils, utils, app_canonical, redesign_components)

---

## Gate Scripts Verified

| Script | Status |
|--------|--------|
| scripts/check/app_preflight.py | EXISTS |
| scripts/check/check_time_literals.py | EXISTS |
| test_app_sync.py | EXISTS |

---

**PASS 1 COMPLETE.**

**Proceed to PASS 2?**
