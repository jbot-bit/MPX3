# Project Conventions

**Purpose:** MPX3 (Gold futures trading system) specific conventions and patterns.

**Scope:** This repository only. Do not generalize to other projects.

---

## Database Management

### gold.db Location
- **Canonical path:** `data/db/gold.db` (NOT root directory)
- **Reason:** cloud_mode.py expects this structure for local/cloud switching (line 131)
- **Migration:** If gold.db in root, move to `data/db/` and update .env DUCKDB_PATH

**Exception:** Old projects may have gold.db in root. Check cloud_mode.py first.

### Database Verification Protocol
When working with copied/migrated databases:
1. Check modification timestamps (keep NEWER with correct values)
2. Compare validated_setups sample sizes against CLAUDE.md documented values
3. Verify historical data range (bars_1m: MIN/MAX ts_utc per symbol)
4. Run `python test_app_sync.py` (MANDATORY)
5. Trust database if values match CLAUDE.md exactly

### Database Version Trust Heuristic
- **Trust:** Database with smaller N if values match CLAUDE.md stress-tested results
- **Distrust:** Database with larger N but different expectancy values
- **Reason:** Larger N may use outdated filters or non-stress-tested parameters
- **Ground truth:** CLAUDE.md documented values are authoritative

**Example from 2026-01-27 audit:**
- MPX3: n=53/55/32, ExpR matches CLAUDE.md → TRUSTED
- MPX2_fresh: n=92/78, ExpR differs → REJECTED

---

## Critical File Synchronization

### MANDATORY: test_app_sync.py
**Run ALWAYS after:**
- Updating validated_setups database
- Modifying trading_app/config.py
- Copying databases between projects
- Adding new strategies or changing RR values

**Rule from CLAUDE.md:**
> "NEVER update validated_setups database without IMMEDIATELY updating config.py in the same operation."

**Consequence of skipping:** Wrong filters in production = REAL MONEY LOSSES

---

## Environment Configuration

### .env Critical Variables
- `FORCE_LOCAL_DB=1` → Forces local gold.db (prevents MotherDuck cloud connection)
- `CLOUD_MODE=0` → Disables cloud mode
- `DUCKDB_PATH=gold.db` → Database path (verify matches actual location)

**Cloud mode detection logic (cloud_mode.py:27-43):**
- Checks FORCE_LOCAL_DB first (override)
- Then CLOUD_MODE setting
- Then Streamlit cloud env vars
- Defaults to LOCAL if none set

**Audit rule:** Always verify cloud_mode.py hardcoded paths match .env configuration.

---

## User Interaction Patterns

### Numbered Option Selection
When presenting multiple options to user (Option A/B/C or 1/2/3):
- **If user responds with number:** Execute that option immediately
- **No re-confirmation needed** (user already chose)
- **Exception:** If option involves data deletion, production changes, or irreversible actions → Confirm first
- **Rationale:** User explicitly selected, re-asking is redundant friction

**Examples:**
- ✅ User says "1" for "Option 1: Auto-execute setup optimization" → Execute immediately
- ✅ User says "2" for "Option 2: Use approach B" → Use approach B immediately
- ⚠️ User says "1" for "Option 1: Delete all logs" → Confirm: "This will delete all logs. Proceed? (y/n)"

**Scope:** This repo, all non-destructive options
**Learned:** 2026-01-27 setup optimization session (HIGH confidence)

---

## Auto-Applied Rules (High Confidence)

These rules were auto-learned from session corrections and explicitly stated by user:

### 2026-01-27: Database Path Validation
- User corrected: .env DUCKDB_PATH must match cloud_mode.py expectations
- Scope: This repo (cloud_mode.py line 131 hardcodes `data/db/gold.db`)
- Rule: Check both .env and cloud_mode.py when database path issues occur

---

## Staged Rules (Pending Review)

See `skills/_memory_log.md` for medium/low confidence learnings awaiting approval.
