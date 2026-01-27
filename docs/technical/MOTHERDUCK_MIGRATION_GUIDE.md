# MotherDuck Migration Guide

## What's Been Done

### ✅ Completed Steps:

1. **Backup Created**: `backups/20260118_0106/`
   - All database files backed up with SHA256 verification
   - 692.81 MB total (gold.db, live_data.db, trades.db, trading_app.db)

2. **Pre-Migration Audits Passed**:
   - audit_master.py: 38/38 tests (100%)
   - test_app_sync.py: All tests passed
   - Output saved: `audit_pre_migration.log`

3. **Schema Consolidated**:
   - `bars_1m`: Merged MGC/MPL/NQ → 1,397,853 rows (3 instruments)
   - `bars_5m`: Merged MGC/MPL/NQ → 320,534 rows (3 instruments)
   - Old tables archived with timestamp: `_archive_20260118_0106_*`

4. **Infrastructure Created**:
   - `trading_app/db_router.py` - Cloud/local database router
   - `scripts/migrate_to_motherduck.py` - Migration script (ready to run)
   - `.env` updated with MOTHERDUCK_TOKEN placeholder
   - WAL self-healing implemented for cache DB

---

## What's Left (When You're Ready)

### Phase 1: Get MotherDuck Token

1. Go to https://motherduck.com/
2. Sign up or log in
3. Navigate to: Settings → Access Tokens
4. Create a new token
5. Copy the token

### Phase 2: Configure Token

Edit `.env` file:
```bash
# Change this line:
MOTHERDUCK_TOKEN=

# To this:
MOTHERDUCK_TOKEN=your_actual_token_here

# Keep CLOUD_MODE=0 for now (we'll test first)
CLOUD_MODE=0
```

### Phase 3: Test Connection

```bash
python scripts/test_motherduck_connection.py
```

Expected output:
```
[OK] Connected successfully!
[OK] Database 'projectx_prod' is ready
```

### Phase 4: Run Migration

```bash
python scripts/migrate_to_motherduck.py
```

This will:
- Connect to MotherDuck
- Create `projectx_prod` database
- Migrate 4 persistent tables:
  - bars_1m (1.4M rows)
  - bars_5m (320K rows)
  - daily_features (745 rows)
  - validated_setups (19 rows)
- Verify row counts match exactly
- Create dataset catalog
- Generate `migration_report.json` and `migration_report.txt`

**CRITICAL**: Migration will STOP if any row count mismatch is detected.

### Phase 5: Switch to Cloud Mode

After successful migration, edit `.env`:
```bash
CLOUD_MODE=1
```

Now your apps will:
- Read historical data from MotherDuck
- Write cache data to local `live_data.db`
- Work on phone with PC off

### Phase 6: Verify Cloud Mode

```bash
python trading_app/db_router.py
```

Expected output:
```
Data source: MotherDuck
Status: healthy
Tables checked: 4
```

---

## How Database Router Works

### Local Mode (CLOUD_MODE=0)
- All data read from `gold.db`
- Cache written to `live_data.db`
- PC must be on for apps to work

### Cloud Mode (CLOUD_MODE=1)
- Historical data read from MotherDuck
- Cache written to local `live_data.db`
- Apps work on phone even with PC off
- Fallback to local if MotherDuck unavailable

### Table Routing

**Persistent tables** (MotherDuck when CLOUD_MODE=1):
- bars_1m
- bars_5m
- daily_features
- validated_setups

**Cache tables** (always local):
- live_bars (recent bars)
- live_journal (trading decisions)
- ml_predictions
- ml_performance

---

## Adding New Instruments (MPL/NQ Data Updates)

Your bars tables now support multiple instruments, but you need to rebuild daily_features for MPL/NQ:

```bash
# Rebuild daily_features for all instruments
python build_daily_features.py 2024-01-02 2026-01-15

# Or per instrument (if you add backfill scripts)
python scripts/build_daily_features_mpl.py
python scripts/build_daily_features_nq.py
```

Then re-run migration to sync to MotherDuck:
```bash
python scripts/migrate_to_motherduck.py
```

---

## Emergency Rollback

If anything goes wrong:

### Option 1: Switch back to local mode
```bash
# In .env
CLOUD_MODE=0
```

### Option 2: Restore from backup
```bash
# Delete current gold.db
rm gold.db

# Restore from backup
cp backups/20260118_0106/gold.db ./gold.db

# Verify
python audit_master.py
```

---

## Files Created

### Scripts:
- `scripts/backup_databases.py` - Backup utility
- `scripts/consolidate_bars_only.py` - Schema consolidation
- `scripts/migrate_to_motherduck.py` - Migration script
- `scripts/test_motherduck_connection.py` - Connection test

### Infrastructure:
- `trading_app/db_router.py` - Database router (ONLY file that calls duckdb.connect())

### Documentation:
- `MOTHERDUCK_MIGRATION_GUIDE.md` - This file
- `consolidation_report.txt` - Bars consolidation log (when generated)
- `migration_report.txt` - Migration log (when generated)
- `migration_report.json` - Migration metadata (when generated)

### Backups:
- `backups/20260118_0106/MANIFEST.txt` - Backup manifest with checksums

---

## Safety Features

1. **Row Count Verification**: Migration stops if counts don't match
2. **Timestamp Range Checks**: Validates data ranges after migration
3. **Automatic Backups**: Always backup before destructive operations
4. **WAL Self-Healing**: Cache DB auto-recovers from corruption
5. **Fallback Mode**: If MotherDuck fails, falls back to local
6. **Audit Trail**: All operations logged with timestamps

---

## Current Status Summary

```
✅ Backups created and verified
✅ Pre-migration audits passed (38/38 tests)
✅ Bars tables consolidated (MGC, MPL, NQ unified)
✅ Database router created with cloud/local switching
✅ WAL self-healing implemented
✅ Migration script ready

⏸️ Waiting for MotherDuck token
⏸️ Migration to cloud (run when ready)
⏸️ Post-migration audits (after cloud migration)
```

**Next Action**: Get MotherDuck token and run Phase 2-6 when you're ready to enable mobile access.

**Current Mode**: Local (CLOUD_MODE=0) - everything works as before

---

## Questions?

- Test connection: `python scripts/test_motherduck_connection.py`
- Check router: `python trading_app/db_router.py`
- Verify local data: `python audit_master.py`
- Check sync: `python test_app_sync.py`
