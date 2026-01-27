# Strategy Archive - Historical Record

**Created**: 2026-01-26
**Purpose**: Preserve historical strategy state for audit, rollback, and evolution tracking
**Status**: ARCHIVE ONLY - DO NOT USE IN PRODUCTION

---

## ⚠️ CRITICAL WARNING

**This archive contains OLD strategy records that have been superseded.**

### DO NOT:
- Query `validated_setups_archive` in production systems
- Use archived strategies for live trading decisions
- Load archived RR values, filters, or parameters
- Compare current performance to archived expectations

### DO:
- Use `validated_setups` table ONLY (current active strategies)
- Query archive for historical research/analysis explicitly
- Document rollback decisions if reverting to archived strategy
- Track strategy evolution over time

---

## What Is Archived

### Archived Records (IDs 1-6)
**Version**: `pre-stress-test` (2026-01-16 scan window bug fix era)
**Reason**: Replaced by stress-tested execution modes with conservative assumptions

| Archive ID | Original ID | ORB  | RR  | SL   | Expected R | Replaced By ID | Notes |
|------------|-------------|------|-----|------|------------|----------------|-------|
| 1          | 1           | 0030 | 3.0 | HALF | +0.254R    | 105            | NY ORB with extended scan |
| 2          | 2           | 0900 | 6.0 | FULL | +0.198R    | 100            | Asymmetric Asia ORB (6R targets) |
| 3          | 3           | 1000 | 8.0 | FULL | +0.378R    | 101            | CROWN JEWEL (8R targets) |
| 4          | 4           | 1100 | 3.0 | FULL | +0.215R    | 102            | Mid-morning ORB |
| 5          | 5           | 1800 | 1.5 | FULL | +0.274R    | 103            | London open ORB |
| 6          | 6           | 2300 | 1.5 | HALF | +0.403R    | 104            | BEST OVERALL with filter |

**Total archived performance**: ~+600R/year (optimistic assumptions)

### Current Records (IDs 100-105)
**Version**: `stress-tested-execution-modes` (2026-01-26)
**Reason**: Conservative +0.5 tick adverse slippage, realistic fill assumptions

**Total current performance**: +31.1R/year (conservative assumptions)

---

## Why These Differ

### Archived Strategies (Pre-Stress-Test)
- **Assumptions**: Optimistic limit fills at exact ORB edge
- **RR Values**: High (6.0, 8.0 for some setups)
- **Performance**: +600R/year estimated
- **Status**: Unproven under realistic slippage

### Current Strategies (Stress-Tested)
- **Assumptions**: +0.5 tick adverse slippage on LIMIT fills
- **RR Values**: Conservative (2.0-3.0)
- **Performance**: +31.1R/year verified
- **Status**: Stress-tested, robust, ready for paper trading

**Key Insight**: Conservative approach preferred. Better to underestimate than overestimate.

---

## Archive Schema

```sql
CREATE TABLE validated_setups_archive (
    -- Original validated_setups columns
    id INTEGER NOT NULL,
    instrument VARCHAR NOT NULL,
    orb_time VARCHAR NOT NULL,
    rr DOUBLE,
    sl_mode VARCHAR NOT NULL,
    orb_size_filter DOUBLE,
    win_rate DOUBLE NOT NULL,
    expected_r DOUBLE NOT NULL,
    real_expected_r DOUBLE,
    sample_size INTEGER NOT NULL,
    notes VARCHAR,

    -- Archive metadata
    archive_id INTEGER PRIMARY KEY,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    archived_reason VARCHAR NOT NULL,
    replaced_by_id INTEGER,  -- Links to current validated_setups ID
    version_tag VARCHAR,      -- e.g., "pre-stress-test"
    original_created_at TIMESTAMP,
    original_updated_at TIMESTAMP
);
```

---

## How To Query Archive (Research Only)

### View All Archived Strategies
```sql
SELECT
    archive_id,
    id as original_id,
    orb_time,
    rr,
    expected_r,
    replaced_by_id,
    version_tag,
    archived_reason
FROM validated_setups_archive
ORDER BY archive_id;
```

### Compare Old vs New
```sql
SELECT
    a.orb_time,
    a.rr as old_rr,
    a.expected_r as old_expected_r,
    v.rr as new_rr,
    v.expected_r as new_expected_r,
    (v.expected_r - a.expected_r) * 250 as annual_r_change
FROM validated_setups_archive a
JOIN validated_setups v ON v.id = a.replaced_by_id
WHERE a.version_tag = 'pre-stress-test'
ORDER BY a.orb_time;
```

### Track Strategy Evolution
```sql
SELECT
    orb_time,
    version_tag,
    rr,
    expected_r,
    archived_at,
    archived_reason
FROM validated_setups_archive
WHERE orb_time = '1000'
ORDER BY archived_at DESC;
```

---

## Rollback Procedure (If Needed)

**IMPORTANT**: Only rollback if current strategies fail in paper/live trading.

### Step 1: Verify Failure
- Paper trade results significantly worse than expected
- Multiple consecutive losing days
- Clear systematic issue (not random variance)

### Step 2: Analyze Archive
- Compare archived vs current parameters
- Understand what changed (RR, execution mode, filters)
- Check if archived strategy addresses current issue

### Step 3: Test Rollback (Backtest First)
```sql
-- DO NOT run this in production without testing!
-- Example: Restore 1000 ORB from archive
UPDATE validated_setups
SET
    rr = 8.0,
    expected_r = 0.378,
    notes = 'ROLLED BACK from stress-test to pre-stress-test (archive_id=3)'
WHERE id = 101;
```

### Step 4: Document Rollback
- Update notes field with rollback reason
- Archive the stress-tested version before rolling back
- Track rollback in git commit message

---

## Files Related To Archive

### Archive Files
- `create_validated_setups_archive.sql` - Archive table schema
- `archive_old_strategies.sql` - INSERT statements for archived records
- `STRATEGY_ARCHIVE_README.md` - This file (documentation)
- `validated_setups_snapshot_before_archive.csv` - Pre-archive snapshot

### Production Files (DO NOT MODIFY BASED ON ARCHIVE)
- `validated_setups` table - Current active strategies
- `trading_app/config.py` - Loads from validated_setups (NOT archive)
- `strategies/execution_engine.py` - Uses current strategies only
- `test_app_sync.py` - Validates current strategies only

---

## Archive History Log

### 2026-01-26: Initial Archive Creation
- **Archived**: IDs 1-6 (MGC single-ORB strategies)
- **Reason**: Replaced by stress-tested execution modes
- **Version Tag**: `pre-stress-test`
- **Records**: 6 MGC ORBs with optimistic assumptions
- **Kept Active**: IDs 7-8 (CASCADE, SINGLE_LIQ multi-setup strategies)
- **New Active**: IDs 100-105 (stress-tested MGC ORBs)

### Future Archive Events
- Document all future archival events here
- Include: date, archived IDs, reason, version tag
- Link to git commit with detailed changes

---

## Verification Commands

### Check Archive Integrity
```bash
python -c "
import duckdb
con = duckdb.connect('data/db/gold.db', read_only=True)

# Verify archive exists and has correct records
archive_count = con.execute('SELECT COUNT(*) FROM validated_setups_archive').fetchone()[0]
print(f'Archive records: {archive_count}')

# Verify validated_setups unchanged (19 rows: 6 MGC, 5 NQ, 6 MPL, 2 MGC multi)
current_count = con.execute('SELECT COUNT(*) FROM validated_setups').fetchone()[0]
print(f'Current records: {current_count}')

# Show link integrity
links = con.execute('''
    SELECT a.archive_id, a.id as old_id, a.replaced_by_id as new_id, v.id
    FROM validated_setups_archive a
    LEFT JOIN validated_setups v ON v.id = a.replaced_by_id
''').df()
print(links)

con.close()
"
```

### Verify Production Uses Current (Not Archive)
```bash
# Should show 0 matches - archive should NEVER be queried in production
grep -r "validated_setups_archive" strategies/ trading_app/ --exclude="*.md"
```

---

## Project Documentation Updates

Updated the following files to reference this archive:
- `CLAUDE.md` - Added archive warning
- `PROJECT_STATUS.md` - Documents archive creation
- `trading_app/config.py` - Comments clarify source is validated_setups (not archive)

---

## Questions?

### "Why did performance drop from +600R to +31R?"
**Answer**: Conservative assumptions. Archived strategies used optimistic limit fills. Current strategies model +0.5 tick adverse slippage (queue effects, imperfect fills). Better to underestimate.

### "Can we use RR=8.0 from archive instead of RR=2.0?"
**Answer**: Not recommended. RR=8.0 was based on optimistic assumptions. Stress testing showed MARKET execution works better for 1000 ORB. Use current RR=2.0.

### "Should we roll back to archived strategies?"
**Answer**: Only if paper trading shows systematic issues. Random variance is expected. Need 30+ trades minimum to evaluate.

### "How do I add new archive records?"
**Answer**: See `archive_old_strategies.sql` for template. Always document reason, version tag, and replacement ID.

---

**Last Updated**: 2026-01-26
**Maintainer**: Strategy evolution tracking
**Status**: HISTORICAL REFERENCE ONLY - DO NOT USE IN PRODUCTION
