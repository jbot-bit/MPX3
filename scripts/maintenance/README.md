# Automated Market Data Update Pipeline

## Overview

Automated daily pipeline to keep market data current without manual intervention.

**Status:** ✅ Implemented (bugs.txt requirement)

---

## Quick Start

### 1. Test the Update Script

**Prerequisites:**
- Close any apps/scripts using `data/db/gold.db` (check with `tasklist | findstr python`)
- Ensure `.env` has valid `DATABENTO_API_KEY`

```bash
# Run test suite
python scripts/maintenance/test_update_script.py

# Run manual update
python scripts/maintenance/update_market_data.py
```

**Expected output:**
```
============================================================
AUTOMATED MARKET DATA UPDATE
============================================================
Current data ends at: 2026-01-XX XX:XX:XX UTC
Update range: 2026-01-XX to 2026-01-29 (Brisbane local)

Running: python pipeline/backfill_databento_continuous.py ...
[backfill output...]

============================================================
UPDATE STATUS
============================================================
Symbol: MGC
Latest bars_1m timestamp: 2026-01-29 XX:XX:XX+00:00
Latest daily_features date: 2026-01-29
Bars added today (2026-01-29): XXX
============================================================

✓ SUCCESS: Market data updated
```

### 2. Set Up Windows Task Scheduler

See **[SCHEDULER_SETUP.md](SCHEDULER_SETUP.md)** for detailed instructions.

**Quick setup (PowerShell as Admin):**

```powershell
# Adjust Python path if needed
$PythonPath = "C:\Users\sydne\AppData\Local\Programs\Python\Python310\python.exe"
$WorkingDir = "C:\Users\sydne\OneDrive\Desktop\MPX3"

$Action = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument "scripts\maintenance\update_market_data.py" `
    -WorkingDirectory $WorkingDir

$Trigger = New-ScheduledTaskTrigger -Daily -At "18:00"

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 10)

Register-ScheduledTask `
    -TaskName "Daily Market Data Update" `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Automated MGC market data update" `
    -Force
```

**Verify:**
```powershell
# Run manually
schtasks /run /tn "Daily Market Data Update"

# Check status
schtasks /query /tn "Daily Market Data Update" /fo list /v | findstr /i "status last"
```

---

## How It Works

### Architecture

```
update_market_data.py
  ├─ 1. Query MAX(ts_utc) from bars_1m
  ├─ 2. Calculate backfill range (max+1min → now)
  ├─ 3. Call backfill_databento_continuous.py
  │     └─ Automatically calls build_daily_features.py
  └─ 4. Print status (verify update)
```

### Key Features

✅ **Incremental updates** - Only backfills new data (from last timestamp + 1 minute)
✅ **Idempotent** - Safe to run multiple times (skips if already current)
✅ **Error handling** - Exit code 1 on failure (Task Scheduler can retry)
✅ **Status reporting** - Shows latest timestamps and bars added
✅ **Automatic features** - build_daily_features.py called by backfill script
✅ **No hardcoded limits** - Removed AVAILABLE_END_UTC cap (handles 422 naturally)

### Data Flow

```
bars_1m (query MAX timestamp)
   │
   ├─ Calculate range: (max+1min, now)
   │
   ├─ Databento API (backfill_databento_continuous.py)
   │     │
   │     ├─ Fetch 1-minute bars
   │     ├─ INSERT OR REPLACE into bars_1m
   │     ├─ Aggregate to bars_5m
   │     └─ Call build_daily_features.py
   │           │
   │           └─ Calculate ORBs, session stats, RSI
   │                 │
   │                 └─ INSERT OR REPLACE into daily_features
   │
   └─ Print status (verify)
```

### Exit Codes

- **0** = Success (data updated or already current)
- **1** = Failure (backfill error, database locked, API error)

Task Scheduler will retry on exit code 1 (up to 3 times, 10-minute intervals).

---

## Files

| File | Purpose |
|------|---------|
| `update_market_data.py` | Main update script (run daily) |
| `test_update_script.py` | Test suite (verify before scheduling) |
| `SCHEDULER_SETUP.md` | Detailed Task Scheduler guide |
| `README.md` | This file |

---

## Changes Made

### Modified Files

1. **pipeline/backfill_databento_continuous.py**
   - Removed hardcoded `AVAILABLE_END_UTC` limit (line 193)
   - Now handles 422 errors naturally (data not available yet)
   - Allows automated updates without manual date cap adjustments

### New Files

1. **scripts/maintenance/update_market_data.py** (150 lines)
   - Queries latest bar timestamp
   - Calculates incremental backfill range
   - Runs backfill subprocess
   - Prints status report

2. **scripts/maintenance/test_update_script.py** (135 lines)
   - Tests timestamp query
   - Tests date range calculation
   - Tests status reporting
   - Tests idempotency

3. **scripts/maintenance/SCHEDULER_SETUP.md** (400+ lines)
   - Complete Task Scheduler guide
   - PowerShell and GUI setup methods
   - Troubleshooting section
   - Monitoring and maintenance

4. **scripts/maintenance/README.md** (This file)
   - Quick start guide
   - Architecture overview
   - Integration documentation

---

## Integration with Existing System

### Compatible With

✅ **Manual backfills** - Can still run `backfill_databento_continuous.py` manually
✅ **Multi-instrument** - Works with MGC (ready for NQ/MPL)
✅ **Existing apps** - No changes to trading apps required
✅ **Database schema** - Uses existing tables (bars_1m, daily_features)
✅ **Config sync** - No impact on validated_setups or config.py

### Testing

After updates, always verify:

```bash
# Verify database updated
python -c "import duckdb; conn = duckdb.connect('data/db/gold.db'); print('Latest:', conn.execute('SELECT MAX(ts_utc) FROM bars_1m WHERE symbol=\"MGC\"').fetchone()[0]); conn.close()"

# Verify app sync (if strategies changed)
python test_app_sync.py

# Verify apps work
python trading_app/app_canonical.py
```

---

## Troubleshooting

### Database Locked Error

**Error:** `IO Error: Cannot open file ... The process cannot access the file`

**Solution:**
```bash
# Check for running Python processes
tasklist | findstr python

# Close trading apps or other scripts using gold.db
# Then re-run update script
```

### Backfill Fails (Exit Code 1)

**Possible causes:**
1. Databento API key invalid/expired (check `.env`)
2. Databento API down (check https://status.databento.com)
3. Network connectivity issue
4. Data already current (not an error - script will skip)

**Debug:**
```bash
# Run backfill manually with date range
python pipeline/backfill_databento_continuous.py 2026-01-28 2026-01-29

# Check Databento API status
curl https://api.databento.com/v0/metadata/list_schemas
```

### Task Scheduler Not Running

**Solution:**
```powershell
# Check if task is enabled
Get-ScheduledTask -TaskName "Daily Market Data Update" | Select State

# Enable if disabled
Enable-ScheduledTask -TaskName "Daily Market Data Update"

# Check Task Scheduler service
Get-Service -Name "Schedule" | Select Status
```

### Data Not Updating

**Checklist:**
- [ ] Task shows success (0x0) in Task Scheduler history
- [ ] Working directory set to project root
- [ ] `.env` file accessible from working directory
- [ ] Python path correct in task action
- [ ] User has write permissions on `data/db/gold.db`

**Manual test:**
```bash
cd C:\Users\sydne\OneDrive\Desktop\MPX3
python scripts/maintenance/update_market_data.py
```

---

## Schedule

**Default:** Daily at 18:00 Brisbane time (after trading session ends)

**Rationale:**
- Gold futures close ~17:00 Brisbane
- Databento typically processes data within 30-60 minutes
- 18:00 run ensures full day's data available
- Before next trading day analysis (09:00 next day)

**Adjust if needed:**
```powershell
# Change to 20:00
$NewTrigger = New-ScheduledTaskTrigger -Daily -At "20:00"
Set-ScheduledTask -TaskName "Daily Market Data Update" -Trigger $NewTrigger
```

---

## Monitoring

### Daily Check (Manual)

```bash
# Quick status check
python -c "import duckdb; conn = duckdb.connect('data/db/gold.db'); print('bars_1m:', conn.execute('SELECT MAX(ts_utc) FROM bars_1m WHERE symbol=\"MGC\"').fetchone()[0]); print('daily_features:', conn.execute('SELECT MAX(date_local) FROM daily_features WHERE instrument=\"MGC\"').fetchone()[0]); conn.close()"
```

### Weekly Check (Scheduled Task History)

```powershell
# Check last 7 days of runs
Get-ScheduledTask -TaskName "Daily Market Data Update" | Get-ScheduledTaskInfo | Select LastRunTime, LastTaskResult, NextRunTime, NumberOfMissedRuns
```

### Alert on Failure (Optional)

Create wrapper script with email notification:

```powershell
# wrapper.ps1
$Result = & python scripts\maintenance\update_market_data.py
if ($LASTEXITCODE -ne 0) {
    Send-MailMessage `
        -To "your@email.com" `
        -From "mpx3@scheduler.local" `
        -Subject "Market Data Update Failed" `
        -Body "Exit code: $LASTEXITCODE. Check logs." `
        -SmtpServer "smtp.gmail.com" `
        -Port 587 `
        -UseSsl `
        -Credential (Get-Credential)
}
exit $LASTEXITCODE
```

---

## Future Enhancements

### Planned

- [ ] Multi-instrument support (MGC, NQ, MPL in one run)
- [ ] Metrics logging (bars added, processing time)
- [ ] Health check pre-flight (Databento API status)
- [ ] Smart retry logic (exponential backoff)

### Considered

- [ ] Slack/Discord webhook notifications
- [ ] Dashboard for update status
- [ ] Auto-archive old data (>2 years)
- [ ] Multiple daily runs (after session close + overnight)

---

## Support

**Before reporting issues:**

1. Run test suite: `python scripts/maintenance/test_update_script.py`
2. Check Task Scheduler history for error messages
3. Verify `.env` has valid `DATABENTO_API_KEY`
4. Check Databento API status: https://status.databento.com
5. Test manual backfill: `python pipeline/backfill_databento_continuous.py 2026-01-28 2026-01-29`

**Common fixes:**
- Database locked → Close trading apps
- API error → Check `.env` credentials
- Permission error → Run task as administrator
- Path error → Verify working directory in task settings

---

## Completion Status

✅ **Implemented (bugs.txt requirement)**

| Requirement | Status | Notes |
|-------------|--------|-------|
| Query MAX timestamp from bars_1m | ✅ Done | `get_latest_bar_timestamp()` |
| Backfill incrementally from max+1min → now | ✅ Done | `calculate_backfill_range()` |
| Build daily_features for new dates | ✅ Done | Called by backfill script |
| Exit non-zero on failure | ✅ Done | Exit code 1 on errors |
| Status check at end | ✅ Done | `print_status()` shows timestamps |
| Windows Task Scheduler setup | ✅ Done | See SCHEDULER_SETUP.md |

**Ready for production use.**

---

## Reference

- **CLAUDE.md** - Project guidelines and architecture
- **bugs.txt** - Original requirement specification
- **pipeline/backfill_databento_continuous.py** - Backfill implementation
- **pipeline/build_daily_features.py** - Feature calculation
- **test_app_sync.py** - Database/config sync verification
