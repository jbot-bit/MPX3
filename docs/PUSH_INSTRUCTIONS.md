# How to Apply Changes to MPX2 Repo

The git histories between replitx2 and MPX2 are incompatible, so direct push won't work.

## Option 1: Apply Patches (Recommended)

1. Clone the MPX2 repo fresh:
   ```bash
   cd ~/Desktop
   git clone https://github.com/jbot-bit/MPX2.git
   cd MPX2
   ```

2. Copy the patch files:
   ```bash
   cp ../replitx2/patches/*.patch .
   ```

3. Apply patches in order:
   ```bash
   git am 0001-Consolidate-to-daily_features_v2-as-canonical-table.patch
   git am 0002-Fix-research-logic-to-properly-evaluate-multi-RR-str.patch
   ```

4. Push to GitHub:
   ```bash
   git push origin main
   # OR
   git push origin restore-edge-pipeline
   ```

## Option 2: Manual Copy (If patches fail)

1. Clone MPX2 repo
2. Manually copy these files from replitx2 to MPX2:

**New files:**
- `trading_app/strategy_evaluation.py`
- `docs/MIGRATION_V2_COMPLETE.md`
- `IMPLEMENTATION_SUMMARY.md`

**Modified files:**
- `trading_app/research_runner.py`
- `trading_app/strategy_discovery.py`
- `pipeline/build_daily_features.py` (renamed from build_daily_features_v2.py)
- `pipeline/wipe_mgc.py`
- `pipeline/check_db.py`
- `pipeline/validate_data.py`
- `analysis/export_csv.py`
- `analysis/query_features.py`
- `workflow/journal.py`
- `workflow/daily_update.py`
- `audits/audit_complete_accuracy.py`
- `CLAUDE.md`

**Archived:**
- Move old `pipeline/build_daily_features.py` to `_archive/deprecated/build_daily_features_v1_deprecated.py`
- Delete `pipeline/build_daily_features_v2.py` (now renamed to build_daily_features.py)

3. Commit and push:
   ```bash
   git add -A
   git commit -m "Migrate to daily_features_v2 and fix multi-RR strategy evaluation"
   git push origin main
   ```

## Option 3: Create Bundle (Alternative)

If you want to preserve full git history:

```bash
cd replitx2
git bundle create mpx2-changes.bundle 5a025ab..HEAD
# Copy bundle file to MPX2 repo
cd ../MPX2
git fetch ../replitx2/mpx2-changes.bundle
git merge FETCH_HEAD
```

## Patch Files Created

Located in: `C:\Users\sydne\OneDrive\Desktop\replitx2\patches\`

- `0001-Consolidate-to-daily_features_v2-as-canonical-table.patch`
- `0002-Fix-research-logic-to-properly-evaluate-multi-RR-str.patch`

## What's in the Changes

**Commit 1 (6b04b49):**
- Consolidated to single daily_features_v2 table
- Updated 15 files
- Eliminated v1/v2 confusion

**Commit 2 (9fc4143):**
- Fixed multi-RR strategy evaluation
- Created strategy_evaluation.py
- Now uses MAE/MFE for accurate results

See `IMPLEMENTATION_SUMMARY.md` for full details.
