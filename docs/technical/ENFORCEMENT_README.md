# Canonical Enforcement System

**Automated guards to prevent database duplication and maintain clean repository structure.**

Created: 2026-01-18 (police.txt enforcement)

---

## Overview

This enforcement system ensures:
- ✅ No shadow/duplicate databases outside canonical locations
- ✅ All database connections route through canonical module
- ✅ Single source of truth for all paths and configurations
- ✅ Automated checks on every commit (CI/CD)

## Components

### 1. CANONICAL.json
**Location**: Root directory
**Purpose**: Single source of truth for all canonical paths

Defines:
- Canonical database locations (gold.db, live_data.db, etc.)
- Forbidden database locations (trading_app/*.db, scripts/*.db)
- Connection module (trading_app/cloud_mode.py)
- Documentation paths
- Required files

### 2. trading_app/canonical.py
**Purpose**: Runtime enforcement module

Functions:
- `get_canon_db_path()` - Get canonical database path
- `get_canon_docs()` - Get canonical documentation
- `assert_canonical_environment()` - Runtime validation
- `print_canonical_banner()` - Startup banner

Usage:
```python
from trading_app.canonical import get_canon_db_path, assert_canonical_environment

# Get canonical database path
db_path = get_canon_db_path()

# Validate environment
assert_canonical_environment()
```

### 3. tools/check_no_shadow_dbs.py
**Purpose**: Guard script to detect shadow databases

Checks for:
- Databases in forbidden locations (trading_app/*.db, scripts/*.db)
- Old/backup patterns (_old, _backup, _copy)
- Unexpected databases in root

Usage:
```bash
python tools/check_no_shadow_dbs.py
# Exit code 0 = PASS
# Exit code 1 = FAIL (violations found)
```

### 4. tests/test_canonical_env.py
**Purpose**: Pytest tests for canonical environment

Tests:
- CANONICAL.json structure
- Required files exist
- No shadow databases
- Database connectivity

Usage:
```bash
pytest tests/test_canonical_env.py -v
```

### 5. tests/test_no_hardcoded_db_paths.py
**Purpose**: AST scanning for hardcoded database connections

Tests:
- No hardcoded `duckdb.connect()` in trading_app/
- All code uses canonical connection module
- No deprecated db_router imports

Usage:
```bash
pytest tests/test_no_hardcoded_db_paths.py -v
```

---

## CI/CD Integration

### Pre-commit Hooks (Local)

**Setup:**
```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

**What it does:**
- Runs `check_no_shadow_dbs.py` before each commit
- Blocks commit if violations found
- Auto-fixes trailing whitespace, EOF issues

### GitHub Actions (Automated)

**Workflow**: `.github/workflows/canonical-enforcement.yml`

**Triggers:**
- Push to main/master/mobile/develop branches
- Pull requests
- Manual workflow dispatch

**Jobs:**
1. **check-shadow-databases** - Run guard script
2. **test-canonical-environment** - Run environment tests
3. **test-no-hardcoded-connections** - Run connection tests
4. **verify-canonical-structure** - Check file structure
5. **summary** - Report overall status

**Status Badge** (add to README.md):
```markdown
![Canonical Enforcement](https://github.com/YOUR_USERNAME/YOUR_REPO/actions/workflows/canonical-enforcement.yml/badge.svg)
```

---

## How to Use

### For Developers

**Before committing:**
1. Pre-commit hooks run automatically
2. If violations found, fix them before retrying
3. Never create databases outside root directory
4. Always use `cloud_mode.get_database_connection()`

**When writing new code:**
```python
# ❌ BAD - Hardcoded connection
import duckdb
conn = duckdb.connect("some.db")

# ✅ GOOD - Canonical connection
from trading_app.cloud_mode import get_database_connection
conn = get_database_connection()
```

### For Maintainers

**To add new canonical files:**
1. Update `CANONICAL.json` → `required_files`
2. Commit changes
3. CI/CD will validate on next push

**To modify allowed database locations:**
1. Update `CANONICAL.json` → `databases.allowed_locations`
2. Update `CANONICAL.json` → `databases.forbidden_locations`
3. Test locally: `python tools/check_no_shadow_dbs.py`
4. Commit changes

### Running Tests Locally

```bash
# Run all enforcement tests
pytest tests/test_canonical_env.py tests/test_no_hardcoded_db_paths.py -v

# Run guard script
python tools/check_no_shadow_dbs.py

# Test canonical module
python trading_app/canonical.py
```

---

## Allowed Exceptions

### Database Connections

Hardcoded `duckdb.connect()` is allowed in:
- `trading_app/cloud_mode.py` (canonical module itself)
- Data pipeline scripts (backfill*, ingest*, build_daily_features*)
- Test files (test_*, check_*, audit_*)
- Scripts directory (scripts/*.py)
- Archived code (_archive/*)

### Database Files

Shadow databases allowed in:
- `backups/` directory
- `_archive/` directory

---

## Troubleshooting

### Pre-commit Hook Fails

**Error**: "check-no-shadow-dbs failed"

**Solution**:
1. Run manually: `python tools/check_no_shadow_dbs.py`
2. See which database files are violating
3. Delete shadow databases or move to backups/
4. Retry commit

### Test Failures

**Error**: "test_no_hardcoded_db_paths failed"

**Solution**:
1. Check which file has hardcoded connection
2. Replace with canonical connection:
   ```python
   from trading_app.cloud_mode import get_database_connection
   conn = get_database_connection()
   ```
3. Re-run tests

### GitHub Action Fails

**Error**: "Canonical enforcement failed"

**Solution**:
1. Check workflow logs on GitHub Actions tab
2. Identify which job failed
3. Run that check locally to debug
4. Fix violations and push again

---

## Benefits

### Immediate:
- ✅ Prevents shadow databases automatically
- ✅ Blocks commits with violations
- ✅ Self-documenting (CANONICAL.json)
- ✅ Runtime validation on app startup

### Long-term:
- 🔒 No "which DB is correct?" confusion
- 🔒 No duplicate connection modules
- 🔒 Consistent structure across team
- 🔒 Easy onboarding (clear structure)
- 🔒 Automated enforcement (no human vigilance needed)

---

## Version History

- **1.0.0** (2026-01-18) - Initial enforcement system
  - CANONICAL.json created
  - Guard scripts implemented
  - Tests added
  - CI/CD configured

---

## Related Documentation

- `POLICE_DISCOVERY_REPORT.md` - Discovery phase findings
- `CANONICAL.json` - Single source of truth
- `DATABASE_SCHEMA_SOURCE_OF_TRUTH.md` - Database schema
- `TRADING_PLAYBOOK.md` - Trading rules

---

**Maintained by**: Automated enforcement (police.txt)
**Status**: ✅ Active enforcement
