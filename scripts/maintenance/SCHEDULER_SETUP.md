# Windows Task Scheduler Setup Guide

## Automated Daily Market Data Update

This guide walks through setting up Windows Task Scheduler to run the market data update script automatically every day at 18:00 Brisbane time (after trading session ends).

---

## Prerequisites

1. **Python installed**: Verify path to Python executable
   ```powershell
   # Find Python path
   where python
   # Example output: C:\Users\sydne\AppData\Local\Programs\Python\Python310\python.exe
   ```

2. **Script tested**: Run manual test first
   ```bash
   cd C:\Users\sydne\OneDrive\Desktop\MPX3
   python scripts/maintenance/test_update_script.py
   python scripts/maintenance/update_market_data.py
   ```

3. **Environment configured**: Ensure `.env` has `DATABENTO_API_KEY`

---

## Setup Method 1: PowerShell (Recommended)

**Run PowerShell as Administrator**, then execute:

```powershell
# Set variables
$TaskName = "Daily Market Data Update"
$PythonPath = "C:\Users\sydne\AppData\Local\Programs\Python\Python310\python.exe"
$ScriptPath = "scripts\maintenance\update_market_data.py"
$WorkingDir = "C:\Users\sydne\OneDrive\Desktop\MPX3"

# Create scheduled task
$Action = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument $ScriptPath `
    -WorkingDirectory $WorkingDir

$Trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At "18:00"

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 10)

$Principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType ServiceAccount `
    -RunLevel Highest

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Automated market data update for MGC futures" `
    -Force
```

**Verify creation:**
```powershell
Get-ScheduledTask -TaskName "Daily Market Data Update" | Format-List *
```

---

## Setup Method 2: Task Scheduler GUI

1. **Open Task Scheduler**
   - Press `Win + R`
   - Type `taskschd.msc`
   - Press Enter

2. **Create Basic Task**
   - Click "Create Task" (right panel)
   - Name: `Daily Market Data Update`
   - Description: `Automated market data update for MGC futures`
   - Check: ☑ "Run whether user is logged on or not"
   - Check: ☑ "Run with highest privileges"

3. **Configure Trigger**
   - Tab: "Triggers"
   - Click "New..."
   - Begin the task: `On a schedule`
   - Settings: `Daily`
   - Start: `18:00:00` (6:00 PM)
   - Recur every: `1 days`
   - Click "OK"

4. **Configure Action**
   - Tab: "Actions"
   - Click "New..."
   - Action: `Start a program`
   - Program/script: `C:\Users\sydne\AppData\Local\Programs\Python\Python310\python.exe`
   - Add arguments: `scripts\maintenance\update_market_data.py`
   - Start in: `C:\Users\sydne\OneDrive\Desktop\MPX3`
   - Click "OK"

5. **Configure Settings**
   - Tab: "Settings"
   - Check: ☑ "Allow task to be run on demand"
   - Check: ☑ "Run task as soon as possible after a scheduled start is missed"
   - Check: ☑ "If the task fails, restart every: 10 minutes"
   - Attempts: `3`
   - Check: ☑ "Stop the task if it runs longer than: 30 minutes"
   - If the running task does not end when requested: `Stop the existing instance`
   - Click "OK"

6. **Save Task**
   - Enter password when prompted
   - Click "OK"

---

## Verification

### Test Manual Run

```powershell
# Run the task manually (as test)
schtasks /run /tn "Daily Market Data Update"

# Check last run status
schtasks /query /tn "Daily Market Data Update" /fo list /v | findstr /i "status last"
```

### Check Task History

1. Open Task Scheduler GUI
2. Navigate to "Task Scheduler Library"
3. Find "Daily Market Data Update"
4. Click "History" tab
5. Look for recent run events

### View Output Logs

Task Scheduler captures stdout/stderr. To view:

1. Task Scheduler GUI → Select task
2. "Actions" panel → "View History"
3. Look for Event ID 100 (task started), 102 (task completed)
4. Double-click event → "Actions" tab to see output

**Alternatively, redirect to log file:**

Modify task action arguments:
```
scripts\maintenance\update_market_data.py > logs\update_market_data.log 2>&1
```

(Create `logs/` directory first)

---

## Monitoring

### Check Last Run Status

```powershell
# Query task info
$Task = Get-ScheduledTask -TaskName "Daily Market Data Update"
$TaskInfo = Get-ScheduledTaskInfo -TaskName "Daily Market Data Update"

Write-Host "Last Run Time: $($TaskInfo.LastRunTime)"
Write-Host "Last Result: $($TaskInfo.LastTaskResult)"
Write-Host "Next Run Time: $($TaskInfo.NextRunTime)"
Write-Host "Number of Missed Runs: $($TaskInfo.NumberOfMissedRuns)"
```

### Success/Failure Codes

- **0** = Success
- **1** = Failure (script error)
- **0x41301** = Task is currently running
- **0x800710E0** = Task not scheduled to run

### Email Notifications (Optional)

To get email alerts on failure:

1. Task Properties → "Actions" tab
2. Add new action: "Send an e-mail"
3. Configure SMTP settings
4. Trigger: "On an event" → Task Scheduler → Event ID 103 (task failed)

**Note:** Windows 10/11 deprecated email actions. Use PowerShell script wrapper instead:

```powershell
# wrapper.ps1
$Result = & python scripts\maintenance\update_market_data.py
if ($LASTEXITCODE -ne 0) {
    Send-MailMessage `
        -To "your@email.com" `
        -From "scheduler@yourpc.com" `
        -Subject "Market Data Update Failed" `
        -Body "Exit code: $LASTEXITCODE" `
        -SmtpServer "smtp.gmail.com"
}
exit $LASTEXITCODE
```

---

## Troubleshooting

### Task Runs But Script Fails

**Symptom:** Task shows success (0x0) but data not updated

**Solutions:**

1. **Check working directory**
   - Ensure "Start in" is set to project root
   - Script needs access to `.env` file

2. **Check environment variables**
   - Task Scheduler may not inherit user environment
   - Add explicit path in task action:
     ```
     cmd /c "cd C:\Users\sydne\OneDrive\Desktop\MPX3 && python scripts\maintenance\update_market_data.py"
     ```

3. **Check Python path**
   - Verify Python executable path is correct
   - Use full path, not just `python`

4. **Check permissions**
   - Ensure user has read/write access to `data/db/gold.db`
   - Run task as administrator

### Task Doesn't Run at Scheduled Time

**Solutions:**

1. **Check task is enabled**
   ```powershell
   Get-ScheduledTask -TaskName "Daily Market Data Update" | Select State
   ```
   Should show `Ready` (not `Disabled`)

2. **Check trigger is enabled**
   - Open task properties → "Triggers" tab
   - Ensure trigger checkbox is checked

3. **Check PC is on at scheduled time**
   - Enable "Wake computer to run this task" in settings
   - Or adjust schedule to when PC is typically on

4. **Check Task Scheduler service is running**
   ```powershell
   Get-Service -Name "Schedule" | Select Status
   ```
   Should show `Running`

### Permission Errors

**Symptom:** "Access denied" or permission errors

**Solutions:**

1. **Run task as administrator**
   - Task properties → "Run with highest privileges"

2. **Grant database access**
   - Ensure user has write access to `data/db/` directory
   - Check file permissions on `gold.db`

---

## Maintenance

### Update Script Path

If project moves:

```powershell
# Get task
$Task = Get-ScheduledTask -TaskName "Daily Market Data Update"

# Update action
$Task.Actions[0].WorkingDirectory = "C:\NEW\PATH\TO\MPX3"

# Save
Set-ScheduledTask -InputObject $Task
```

### Change Schedule Time

```powershell
# Create new trigger (daily at 20:00 instead of 18:00)
$NewTrigger = New-ScheduledTaskTrigger -Daily -At "20:00"

# Update task
Set-ScheduledTask -TaskName "Daily Market Data Update" -Trigger $NewTrigger
```

### Disable Task Temporarily

```powershell
Disable-ScheduledTask -TaskName "Daily Market Data Update"

# Re-enable later
Enable-ScheduledTask -TaskName "Daily Market Data Update"
```

### Delete Task

```powershell
Unregister-ScheduledTask -TaskName "Daily Market Data Update" -Confirm:$false
```

---

## Testing Checklist

Before trusting automation:

- [ ] Script runs successfully from command line
- [ ] Test script passes (`test_update_script.py`)
- [ ] Manual task run succeeds (schtasks /run)
- [ ] Task history shows success (Event ID 102)
- [ ] Database timestamps updated after run
- [ ] Apps display updated data
- [ ] Idempotency verified (run twice, no errors)
- [ ] Failure handling works (simulate error, verify exit code 1)
- [ ] Task auto-retries on failure (check settings)

---

## Production Readiness

Once verified:

1. **Monitor for 1 week** - Check daily that task runs successfully
2. **Set up alerts** - PowerShell script wrapper with email on failure
3. **Document schedule** - Add to project README or operations doc
4. **Backup strategy** - Ensure `gold.db` is backed up regularly
5. **Update CLAUDE.md** - Add note about automated updates

---

## Integration with Existing Workflow

**Before automation:**
- Manual: Run `python pipeline/backfill_databento_continuous.py` when needed

**After automation:**
- Automatic: Data updates daily at 18:00
- Manual: Only needed for historical backfills or recovery

**Coexistence:**
- Manual backfills still work (idempotent)
- Automated task detects current data and skips if up-to-date
- No conflicts between manual and automated runs

---

## Future Enhancements

- **Multi-instrument support**: Update MGC, NQ, MPL in single run
- **Slack/Discord notifications**: Webhook on success/failure
- **Metrics logging**: Track bars added, processing time
- **Smart scheduling**: Run more frequently during trading hours
- **Health checks**: Pre-flight check Databento API status
- **Auto-archive**: Move old data (>2 years) to archive database

---

## Support

**If task fails consistently:**

1. Run manual test: `python scripts/maintenance/test_update_script.py`
2. Check Task Scheduler history for error messages
3. Verify `.env` file has valid `DATABENTO_API_KEY`
4. Check Databento API status: https://status.databento.com
5. Review script output in Task Scheduler event logs
6. Test backfill manually: `python pipeline/backfill_databento_continuous.py 2026-01-28 2026-01-29`

**For help:**
- Check `bugs.txt` for known issues
- Review `CLAUDE.md` for project guidelines
- Run `python test_app_sync.py` to verify database integrity
