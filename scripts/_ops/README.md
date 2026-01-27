# Operations Scripts - Asia 47-48 Recovery

**Purpose**: Historical recovery scripts from Asia ORB candidates 47-48 promotion and architecture fix.

These scripts are **archived for reference only** and should not be run again unless a similar recovery situation occurs.

---

## Context

During the promotion of Asia ORB candidates 47-48 to production (2026-01-21), we encountered and fixed a critical architectural flaw in config_generator.py that prevented multiple validated setups per ORB time.

### Timeline

1. **Initial promotion** - Promoted candidates 47-48 successfully
2. **Test failure** - test_app_sync.py failed due to config architecture assuming single setup per ORB
3. **Wrong fix** - Deleted candidate 48 to satisfy broken test (MISTAKE)
4. **Architecture fix** - Updated config_generator.py to return lists per ORB time
5. **Recovery** - Restored candidate 48, both candidates now in production

---

## Scripts in this directory

### Promotion Phase

- `approve_47_48.py` - Approved candidates 47-48 in edge_candidates
- `preflight_47_48.py` - Pre-flight checks before promotion
- `fix_47_48_manifest.py` - Fixed JSON structure to match edge_pipeline requirements
- `check_manifest_simple.py` - Verified manifest fields present
- `check_47_48_manifest.py` - Alternative manifest checker
- `promote_47_48.py` - Attempted promotion via edge_pipeline.py (failed due to schema mismatch)
- `promote_47_48_direct.py` - Direct promotion bypassing edge_pipeline (succeeded)

### Wrong Fix Phase (MISTAKE)

- `keep_only_candidate_47.py` - Deleted candidate 48 (WRONG - should not have done this)
- `remove_old_mgc_1000_setup.py` - Removed old RR=8.0 setup

### Recovery Phase (CORRECT)

- `restore_candidate_48.py` - Restored candidate 48 after realizing architecture mistake

---

## What was learned

1. **Multiple setups per ORB are valid** - Different RR/SL combinations are legitimate strategies
2. **Never delete data to satisfy tests** - Fix the test or architecture, not the data
3. **Database is source of truth** - Tests validate reality, don't force reality to match assumptions
4. **Architecture must support the data model** - Config generator needed to return lists, not single values

---

## Current state

**✅ FIXED**: Both candidates 47 and 48 are in validated_setups
**✅ FIXED**: Architecture supports multiple setups per ORB time
**✅ VERIFIED**: All guardrail tests pass

---

## If you need to run similar recovery

1. **Don't** - These are one-time recovery scripts
2. If you must, understand the full context first
3. Reference the architecture fix documentation: `research/quick_asia/ARCHITECTURE_FIX_MULTIPLE_SETUPS.md`
4. Run guardrail tests first: `python tests/test_multi_setup_orb_detection.py`

---

**Last updated**: 2026-01-21
**Status**: Archived for reference
