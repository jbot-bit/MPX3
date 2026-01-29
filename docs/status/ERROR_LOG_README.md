# Error Logging

All trading apps now automatically log errors to a file that gets cleared each time you start an app.

## Error Log Location

```
app_errors.txt
```

This file is in the project root directory.

## How It Works

1. **On app startup**: The error log file is cleared and initialized
2. **When errors occur**: Full error details are written to the file, including:
   - Timestamp
   - Error type
   - Error message
   - Full stack trace
   - Context (which part of the app failed)
3. **File is rewritten**: Each time you start an app, the old errors are cleared

## Which Apps Have Error Logging

The following apps automatically log errors:
- `trading_app/app_simple.py` - Main trading app
- `trading_app/app_canonical.py` - Canonical trading system
- `trading_app/app_trading_terminal.py` - Trading terminal

## Example Error Log Entry

```
============================================================
[2026-01-28 14:23:45] ERROR
Context: Market scanner
============================================================

Type: KeyError
Message: 'orb_0900_size'

Traceback:
Traceback (most recent call last):
  File "C:\Users\...\market_scanner.py", line 123, in scan_all_setups
    orb_size = data['orb_0900_size']
KeyError: 'orb_0900_size'
```

## What Gets Logged

Errors are logged from these critical sections:
- App initialization (database connection, session state setup)
- Market scanner operations
- Edge tracker operations
- Data updates
- Tradovate sync
- AI assistant queries

## Viewing the Error Log

### Option 1: Command Line
```bash
# View entire log
cat app_errors.txt

# View last 20 lines
tail -n 20 app_errors.txt

# Watch for new errors in real-time
tail -f app_errors.txt
```

### Option 2: Text Editor
Simply open `app_errors.txt` in any text editor (Notepad, VS Code, etc.)

### Option 3: PowerShell (Windows)
```powershell
# View entire log
Get-Content app_errors.txt

# View last 20 lines
Get-Content app_errors.txt -Tail 20
```

## Troubleshooting

If errors are NOT being logged:
1. Check that the file exists: `ls app_errors.txt`
2. Check file permissions (should be writable)
3. Look for console output: `✓ Error log initialized: app_errors.txt`

If the file is too large:
- Delete it manually: `rm app_errors.txt` (it will be recreated on next app start)
- Or keep the most recent errors: `tail -n 100 app_errors.txt > temp.txt && mv temp.txt app_errors.txt`

## Integration

To add error logging to other apps:

```python
from trading_app.error_logger import initialize_error_log, log_error

# At app startup (clears old errors)
initialize_error_log()

# In try/except blocks
try:
    # your code
    result = do_something()
except Exception as e:
    log_error(e, context="Doing something")
    st.error(f"Operation failed: {e}")
    st.info("Check app_errors.txt for details")
```

## Context Manager Style

For automatic error logging with minimal code:

```python
from trading_app.error_logger import ErrorLoggerContext

with ErrorLoggerContext("Loading database"):
    conn = duckdb.connect(db_path)
    # Any error here is automatically logged
```
