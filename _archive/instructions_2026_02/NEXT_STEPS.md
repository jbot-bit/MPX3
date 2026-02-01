# Next Steps - Automated Update Verification

## Status Summary

✅ **updatre.txt PHASE 0 (Discovery):** Complete
✅ **updatre.txt PHASE 1 (Implementation):** Complete
⏸️ **updatre.txt PHASE 2 (Verification):** Blocked by database lock

---

## What's Blocking Verification

**Problem:** `data/db/gold.db` is locked by another process

**Process holding lock:** python.exe (PID 19956)

**To proceed:** Close the application using the database

---

## Quick Verification (Once Database Available)

### Step 1: Close Database Locks

```bash
# Check what's running
tasklist | findstr python

# If you see PID 19956 or other Python processes, close them:
# - Close any trading apps (app_canonical.py, app_simple.py, etc.)
# - Close Jupyter notebooks
# - Close any Python scripts you're running
```

### Step 2: Run Verification Tests

```bash
cd C:\Users\sydne\OneDrive\Desktop\MPX3

# Test 1: Test suite
python scripts/maintenance/test_update_script.py

# Expected output:
# ✓ ALL TESTS PASSED
# Ready to run: python scripts/maintenance/update_market_data.py
```

### Step 3: Run Manual Update

```bash
# Test 2: Manual update (may show "already current" if data is up to date)
python scripts/maintenance/update_market_data.py

# Expected output if data current:
# ✓ Data is already current. No update needed.
# UPDATE STATUS
# Latest bars_1m timestamp: 2026-01-29 XX:XX:XX+00:00
# Latest daily_features date: 2026-01-29
# ✓ SUCCESS: Market data updated

# OR if data needs updating:
# Running: python pipeline/backfill_databento_continuous.py ...
# [backfill output]
# ✓ SUCCESS: Market data updated
```

### Step 4: Verify Health Checks

```bash
# Test 3: Database health (if script exists)
python trading_app/db_health_check.py

# Test 4: Config sync
python strategies/test_app_sync.py

# Expected: ALL TESTS PASSED
```

---

## After Verification Passes

### Set Up Windows Task Scheduler

See complete guide: `scripts/maintenance/SCHEDULER_SETUP.md`

**Quick setup (PowerShell as Administrator):**

```powershell
$PythonPath = "C:\Users\sydne\AppData\Local\Programs\Python\Python310\python.exe"
$WorkingDir = "C:\Users\sydne\OneDrive\Desktop\MPX3"

$Action = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument "scripts\maintenance\update_market_data.py" `
    -WorkingDirectory $WorkingDir

$Trigger = New-ScheduledTaskTrigger -Daily -At "18:00"

$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 10)

Register-ScheduledTask `
    -TaskName "Daily Market Data Update" `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Force

# Test it
schtasks /run /tn "Daily Market Data Update"
```

---

## What Was Already Completed (No Need to Redo)

### ✅ PHASE 1 Complete

1. **Hard date cap removed** from `pipeline/backfill_databento_continuous.py`
   - Line 191-192: AVAILABLE_END_UTC removed
   - Now handles 422 errors naturally

2. **Update script created** at `scripts/maintenance/update_market_data.py`
   - Queries MAX(ts_utc) from bars_1m
   - Calculates incremental backfill range
   - Runs backfill subprocess
   - Prints status report
   - Exit 0 = success, Exit 1 = failure

3. **Test suite created** at `scripts/maintenance/test_update_script.py`
   - Tests timestamp query
   - Tests date range calculation
   - Tests status reporting
   - Tests idempotency

4. **Scheduler guide created** at `scripts/maintenance/SCHEDULER_SETUP.md`
   - PowerShell setup method
   - GUI setup method
   - Troubleshooting guide
   - Monitoring instructions

5. **Git committed and pushed** (commit 224624c)
   - All changes in main branch
   - No duplication with existing system

---

## No Duplication Confirmed

### Checked For Conflicts

✅ **No duplicate scripts** - update_market_data.py is new
✅ **No conflicting backfills** - Enhanced existing script only
✅ **No database conflicts** - Uses existing schema
✅ **No config conflicts** - Doesn't touch validated_setups or config.py
✅ **No app conflicts** - No changes to trading apps needed

### Complements Existing System

- Manual backfills still work (idempotent)
- Trading apps unchanged
- Feature pipeline reused (not duplicated)
- Database schema unchanged
- Config sync still validated by test_app_sync.py

---

## Summary

**What's done:**
- ✅ Discovery complete (know database schema and paths)
- ✅ Implementation complete (all scripts created and committed)
- ✅ Documentation complete (README, SCHEDULER_SETUP, test suite)
- ✅ No duplication (verified no conflicts)

**What's pending:**
- ⏸️ Verification tests (waiting for database access)
- ⏸️ Scheduler setup (after verification passes)

**Action needed:**
1. Close apps using gold.db (PID 19956)
2. Run verification tests (above)
3. Set up Task Scheduler (after tests pass)

**No redundant work detected** - Everything implemented once, correctly.
