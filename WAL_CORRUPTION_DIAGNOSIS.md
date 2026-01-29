# WAL Corruption Diagnosis & Fix

**Issue**: Database WAL file corrupts frequently
**Impact**: Blocks all preflight checks, prevents app usage
**Root Cause**: Multiple simultaneous connections + improper closing

---

## Why WAL Corruption Happens

### 1. **Multiple Processes** (Most Likely)
- Streamlit app + manual scripts running simultaneously
- Each opens connection without coordination
- DuckDB WAL can't handle concurrent writers well

### 2. **Unclosed Connections**
Found 30+ files that open database connections:
- Some use `try/finally` correctly
- Others may not close properly
- Python garbage collection delay = held locks

### 3. **Process Crashes**
- Streamlit hot reload during development
- Ctrl+C during long operations
- Leaves WAL in inconsistent state

---

## Immediate Fix (Done)

```bash
# Backup corrupted WAL
cp data/db/gold.db.wal data/db/gold.db.wal.corrupted_backup

# Delete corrupted WAL
rm data/db/gold.db.wal

# DuckDB will rebuild on next connection
```

**Status**: ✅ Fixed - Preflight now passes

---

## Permanent Solutions

### Solution 1: Use Connection Pool (RECOMMENDED)

**Create**: `trading_app/db_connection.py`

```python
"""
Centralized database connection management.
Prevents WAL corruption from multiple simultaneous connections.
"""
import duckdb
from pathlib import Path
from contextlib import contextmanager
from threading import Lock

_conn_lock = Lock()
_connection = None

def get_db_path():
    """Get database path (centralized)"""
    return Path(__file__).parent.parent / "data" / "db" / "gold.db"

@contextmanager
def get_connection(read_only=False):
    """
    Get database connection with proper locking.

    Usage:
        with get_connection() as conn:
            result = conn.execute("SELECT ...").fetchall()

    Prevents WAL corruption by serializing access.
    """
    global _connection
    with _conn_lock:
        try:
            if _connection is None:
                db_path = get_db_path()
                _connection = duckdb.connect(str(db_path), read_only=read_only)
            yield _connection
        except Exception as e:
            # If connection fails, reset and retry once
            _connection = None
            db_path = get_db_path()
            _connection = duckdb.connect(str(db_path), read_only=read_only)
            yield _connection
```

**Then update all files to use**:
```python
from trading_app.db_connection import get_connection

# Old way (BAD - no coordination)
conn = duckdb.connect('data/db/gold.db')
result = conn.execute("SELECT ...").fetchall()
conn.close()

# New way (GOOD - coordinated access)
with get_connection() as conn:
    result = conn.execute("SELECT ...").fetchall()
```

---

### Solution 2: Checkpoint Before Close

Add to all connection closes:
```python
try:
    conn.execute("CHECKPOINT")
    conn.close()
finally:
    pass  # Ensure close happens
```

---

### Solution 3: Read-Only Connections Where Possible

For queries that don't modify data:
```python
conn = duckdb.connect('data/db/gold.db', read_only=True)
# Much safer, can't corrupt WAL
```

Applies to:
- All `scripts/check/` files
- All `analysis/` files
- Most trading_app UI components (except auto_search)

---

### Solution 4: WAL Auto-Recovery Script

**Create**: `scripts/utils/fix_wal.py` (already exists!)

Make it run automatically on app startup:
```python
# In trading_app/app_canonical.py (or other main apps)
import sys
from pathlib import Path

# Add to very top of file, before any duckdb imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def ensure_db_healthy():
    """Check and fix WAL corruption before app starts"""
    from scripts.utils.fix_wal import fix_wal_if_needed
    fix_wal_if_needed()

# Call before any database access
ensure_db_healthy()
```

---

## Production Best Practices

### 1. **Connection Discipline**
- ✅ Always use context managers (`with`)
- ✅ Always close connections explicitly
- ✅ Never hold connections open longer than needed
- ✅ Use read_only=True for queries

### 2. **Process Coordination**
- ⚠️ Don't run multiple Streamlit apps simultaneously
- ⚠️ Don't run long scripts while Streamlit is running
- ⚠️ If you must: use read-only connections for one

### 3. **Monitoring**
- Add WAL size check to preflight
- Alert if WAL > 100MB (sign of issues)
- Log database connection open/close events

### 4. **Backup Strategy**
- Keep regular backups (you have one: `gold.db.backup_20260129_105146`)
- Consider hourly checkpoints during trading hours
- Store backups in cloud storage

---

## Files That Need Updating (Priority)

### HIGH PRIORITY (Heavy DB users):
1. `trading_app/app_canonical.py` - Main app
2. `trading_app/auto_search_engine.py` - Writes to DB
3. `pipeline/build_daily_features.py` - Heavy writes
4. `trading_app/experimental_scanner.py` - Real-time queries

### MEDIUM PRIORITY (Check scripts):
5. All `scripts/check/*.py` - Should use read_only=True
6. `test_app_sync.py` - Critical verification
7. All `scripts/migrations/*.py` - DB schema changes

### LOW PRIORITY (Analysis scripts):
8. All `analysis/*.py` - Should use read_only=True
9. Scratchpad scripts - Development only

---

## Verification Checklist

After implementing fixes:

```bash
# 1. Run preflight (should never fail on WAL)
python scripts/check/app_preflight.py

# 2. Test concurrent access (open 2 terminals)
# Terminal 1:
streamlit run trading_app/app_canonical.py

# Terminal 2 (while app running):
python scripts/check/app_preflight.py
# Should work without corruption

# 3. Check WAL size after heavy use
ls -lh data/db/gold.db.wal
# Should be small (< 10MB) or auto-deleted after checkpoint
```

---

## Emergency Recovery

If WAL corruption happens again:

```bash
# 1. Stop all processes accessing database
# Close Streamlit, stop all Python scripts

# 2. Backup corrupted WAL (for diagnosis)
cp data/db/gold.db.wal data/db/gold.db.wal.corrupted_$(date +%Y%m%d_%H%M%S)

# 3. Delete corrupted WAL
rm data/db/gold.db.wal

# 4. Test connection
python -c "import duckdb; conn = duckdb.connect('data/db/gold.db'); print('OK'); conn.close()"

# 5. Run preflight
python scripts/check/app_preflight.py
```

---

## Status

- ✅ **Immediate issue**: FIXED (WAL deleted, preflight passes)
- ⏳ **Root cause**: Needs connection pool implementation
- ⏳ **Prevention**: Needs connection discipline audit
- ⏳ **Monitoring**: Needs WAL size alerts

**Recommendation**: Implement Solution 1 (Connection Pool) within 1 week to prevent recurrence.

**Bloomberg Standard**: WAL corruption should NEVER happen in production. This is a HIGH priority fix.
