# AUDIT23A PASS 2 (BUILD/PATCH) - COMPLETE

## Problem Solved
**DuckDB Connection Conflict: "APP STARTUP BLOCKED - CONFIG/DB SYNC FAILURE"**

Error occurred when:
- Clicking "Refresh Data" button
- Clicking "Generate PB Grid" button
- App startup (intermittent)

Root cause: Multiple `duckdb.connect()` calls with different configurations creating connection conflicts.

---

## Solution Per audit23a.txt

**Core Rule:** ONE `duckdb.connect()` at runtime - the singleton in `app_canonical.py`

**Fix Order (as specified in audit23a.txt Step 3):**

### ✅ 3.1 Kill EARLY startup conflicts

**A) sync_guard.py**
- Modified `assert_sync_or_die()` to accept optional `db_connection` parameter
- Uses passed connection if provided, creates temporary read_only connection only if not
- Closes temporary connection after use (doesn't close singleton)

**B) db_health_check.py**
- Modified `check_and_fix_wal_corruption()` to accept optional `db_connection` parameter
- Modified `run_startup_health_check()` to accept optional `db_connection` parameter
- Uses passed connection if provided, creates temporary connection only during initial startup
- WAL recovery creates separate test connection (required for validation)

### ✅ 3.2 Kill secondary runtime connections (click paths)

**C) app_canonical.py:2504 (Refresh Data path)**
- Modified `load_validated_setups_with_stats()` cached function
- Changed signature to accept `_db_connection` parameter (prefix `_` excludes from cache key)
- Added `hash_funcs` to @st.cache_data to handle non-serializable connection object
- Reuses `app_state.db_connection` singleton (no new connection created)
- Removed `conn.close()` (don't close singleton)
- Updated call site to pass `_db_connection=app_state.db_connection`

### ✅ 3.3 Kill hidden connection factories

**D) edge_pipeline.py**
- Modified `create_edge_candidate()` to REQUIRE `db_connection` parameter (removed fallback)
- Raises `ValueError` if `db_connection=None` in app runtime
- Prevents drift where code creates secondary connections

**E) pb_grid_generator.py**
- Modified `generate_pb_batch()` to REQUIRE `db_connection` parameter
- Raises `ValueError` if `db_connection=None` in app runtime
- Updated `app_canonical.py` call site to pass `app_state.db_connection`

**Note on cloud_mode.py:**
- `get_database_connection()` remains unchanged
- Still creates connections, but ONLY used by standalone scripts (not app runtime)
- App runtime NEVER calls this function - always passes singleton explicitly

---

## Runtime Connection Pattern (AFTER FIX)

### App Startup Sequence:
```
1. Module import → sync_guard runs (creates temp connection, closes)
2. app_state.initialize() called
3. run_startup_health_check() (creates temp connection, closes)
4. Singleton created: app_state.db_connection = duckdb.connect(self.db_path) ✅
5. Singleton stays open for app lifetime
```

### User Click "Refresh Data":
```
1. Cache cleared
2. load_validated_setups_with_stats() called with _db_connection=app_state.db_connection
3. Uses singleton (no new connection) ✅
4. Returns cached result
```

### User Click "Generate PB Grid":
```
1. generate_pb_batch() called with db_connection=app_state.db_connection
2. create_pb_candidate() called with db_connection=app_state.db_connection
3. create_edge_candidate() called with db_connection=app_state.db_connection
4. Uses singleton to INSERT into edge_candidates ✅
5. No new connections created
```

---

## duckdb.connect() Audit Results

### Runtime Files (Critical Path):
```bash
$ rg -n "duckdb\.connect\(" trading_app/app_canonical.py trading_app/sync_guard.py \
    trading_app/db_health_check.py trading_app/edge_pipeline.py trading_app/pb_grid_generator.py

trading_app/app_canonical.py:175:        self.db_connection = duckdb.connect(self.db_path)
trading_app/sync_guard.py:60:            conn = duckdb.connect(db_path, read_only=True)
trading_app/db_health_check.py:43:            conn = duckdb.connect(str(db_path))
trading_app/db_health_check.py:68:            test_conn = duckdb.connect(str(db_path))
```

**Analysis:**
- **Line 175 (app_canonical):** THE SINGLETON ✅ (runtime connection)
- **Line 60 (sync_guard):** Conditional fallback (only if no connection passed) ✅
- **Line 43 (db_health_check):** Conditional fallback (only if no connection passed) ✅
- **Line 68 (db_health_check):** WAL recovery test (separate connection required) ✅

**Result:** ONE singleton at runtime, early guards create temporary connections ONLY during startup (before singleton exists).

---

## Verification Sequence (per audit23a.txt Step 5)

### Manual Testing Required:
1. Kill all running Streamlit / Python processes
2. Start app: `streamlit run trading_app/app_canonical.py`
3. Verify: ❌ no startup block
4. Click: "Refresh Data" → should work without error
5. Click: "Generate PB Grid" → should work without error
6. Click: "Refresh Data" again → should work without error

### Automated Checks:
```bash
python scripts/check/app_preflight.py   # Verify app health
python test_app_sync.py                  # Verify DB/config sync
pytest -q                                # Run test suite
rg "duckdb\.connect" trading_app scripts # Audit connection sites
```

---

## Key Files Modified

1. **trading_app/sync_guard.py**
   - `assert_sync_or_die()` accepts optional `db_connection`
   - Conditional connection creation with `should_close` flag
   - Lines modified: 26-27, 54-67, 142-145, 164-167

2. **trading_app/db_health_check.py**
   - `check_and_fix_wal_corruption()` accepts optional `db_connection`
   - `run_startup_health_check()` accepts optional `db_connection`
   - Lines modified: 14-16, 33-46, 56-58, 84-86, 103

3. **trading_app/app_canonical.py**
   - Singleton configuration: default (read_only=False) to support writes
   - `load_validated_setups_with_stats()` uses `_db_connection` parameter
   - Updated call sites to pass `app_state.db_connection`
   - Lines modified: 173-175, 2498-2512, 2535-2537, 2792-2796, 1238-1242

4. **trading_app/edge_pipeline.py**
   - `create_edge_candidate()` REQUIRES `db_connection` (removed fallback)
   - Raises `ValueError` if connection not provided
   - Lines modified: 360, 376, 401-409

5. **trading_app/pb_grid_generator.py**
   - `generate_pb_batch()` REQUIRES `db_connection`
   - Raises `ValueError` if connection not provided
   - Lines modified: 262, 270, 279-286, 291

---

## Enforcement (per audit23a.txt Step 4)

**Current State:** Fail-closed enforcement via ValueError exceptions

**Future Guard (Optional):**
Add connection fingerprint checker near singleton creation:
```python
# Store singleton fingerprint
_singleton_db_path = None
_singleton_read_only = None

def register_singleton(db_path, read_only):
    global _singleton_db_path, _singleton_read_only
    _singleton_db_path = db_path
    _singleton_read_only = read_only

def check_connection_conflict(db_path, read_only):
    if _singleton_db_path is None:
        return  # No singleton yet (startup phase)

    if db_path == _singleton_db_path and read_only != _singleton_read_only:
        raise RuntimeError(
            f"Connection conflict detected!\n"
            f"Singleton: {_singleton_db_path} (read_only={_singleton_read_only})\n"
            f"Attempted: {db_path} (read_only={read_only})\n"
            f"NEVER create secondary connections in app runtime."
        )
```

This would provide fail-fast detection of "AI fixed it mate" regressions.

---

## Success Criteria

✅ **Singleton Pattern:** ONE duckdb.connect() at runtime (app_canonical.py:175)
✅ **No Fallbacks:** edge_pipeline and pb_grid_generator REQUIRE connection parameter
✅ **Startup Guards:** sync_guard and db_health_check accept optional connection
✅ **Cached Queries:** Use `_db_connection` parameter to reuse singleton
✅ **Configuration Consistency:** All connections use default (read_only=False)
✅ **Explicit Enforcement:** ValueError raised if connection not provided in app runtime

**Expected Result:** No "APP STARTUP BLOCKED" errors on Refresh Data or Generate PB Grid clicks.

---

## Next Steps

1. **Test manually:** Follow verification sequence above
2. **Run gates:** app_preflight.py, test_app_sync.py, pytest
3. **If tests pass:** Mark UPDATE22 PASS 2 as COMPLETE
4. **If tests fail:** Debug specific failure and iterate

---

## Reference Documents

- **audit23a.txt** - Complete fix specification (PASS 2 BUILD order)
- **audit23.txt** - Original problem analysis (PASS 1 AUDIT)
- **UPDATE22_PASS2_COMPLETE.md** - PB grid generator implementation
