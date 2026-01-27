"""
CLEANUP validated_setups - Remove Failed Setups
================================================

Following conservative approach (user request #1):
- Remove ALL setups that failed stress tests
- Keep ONLY 1000 RR=1.5 (marginal status)
- Keep 1100 BOTH_LOST (already in DB)

CRITICAL: This modifies validated_setups database.
Following CLAUDE.md protocol:
1. Backup before changes
2. Show what will be removed
3. Execute removal
4. Verify sync with test_app_sync.py
"""

import duckdb
from datetime import datetime
import shutil

DB_PATH = 'gold.db'
BACKUP_PATH = f'gold_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'

print("=" * 80)
print("CLEANUP validated_setups - Remove Failed Setups")
print("=" * 80)
print()

# Backup database first
print("STEP 1: BACKUP DATABASE")
print("-" * 80)
print(f"Creating backup: {BACKUP_PATH}")
shutil.copy2(DB_PATH, BACKUP_PATH)
print("[OK] Backup created")
print()

conn = duckdb.connect(DB_PATH)

# Show current state
print("STEP 2: CURRENT STATE")
print("-" * 80)
current = conn.execute("""
    SELECT id, orb_time, rr, sl_mode, expected_r, sample_size, notes
    FROM validated_setups
    WHERE instrument = 'MGC'
    ORDER BY orb_time, rr
""").fetchall()

print(f"Current MGC setups: {len(current)}")
for s in current:
    setup_id, orb, rr, sl, exp_r, n, notes = s
    filter_name = 'L4' if 'L4_CONSOLIDATION' in notes else 'BOTH_LOST' if 'BOTH_LOST' in notes else 'RSI' if 'RSI' in notes else 'Unknown'
    print(f"  ID {setup_id}: {orb} RR={rr} {filter_name} ExpR={exp_r:+.3f}R N={n}")
print()

# Define setups to REMOVE (failed stress tests)
REMOVE_IDS = [
    25,  # 0900 RR=1.5 L4 - REJECTED (forward +0.020R)
    21,  # 1000 RR=2.0 L4 - REJECTED (regime/cost failed)
    22,  # 1000 RR=2.5 L4 - REJECTED (regime/cost failed)
    23,  # 1000 RR=3.0 L4 - REJECTED (regime/cost failed)
    24,  # 1800 RR=1.5 RSI - REJECTED (not stress-tested, below threshold)
]

# Define setups to KEEP
KEEP_IDS = [
    20,  # 1000 RR=1.5 L4 - MARGINAL (survives +25% cost only)
    26,  # 1100 RR=1.5 BOTH_LOST - EXCELLENT (passed all tests)
]

print("STEP 3: REMOVAL PLAN")
print("-" * 80)
print()
print("REMOVING (failed stress tests):")
for setup_id in REMOVE_IDS:
    setup = next((s for s in current if s[0] == setup_id), None)
    if setup:
        orb, rr, sl, exp_r, n, notes = setup[1:]
        filter_name = 'L4' if 'L4_CONSOLIDATION' in notes else 'RSI' if 'RSI' in notes else 'Unknown'
        reason = ""
        if setup_id == 25:
            reason = "Forward test: +0.020R (FAIL)"
        elif setup_id in [21, 22, 23]:
            reason = "Regime split + cost stress FAIL"
        elif setup_id == 24:
            reason = "Not stress-tested, below threshold"
        print(f"  ID {setup_id}: {orb} RR={rr} {filter_name} - {reason}")
print()

print("KEEPING:")
for setup_id in KEEP_IDS:
    setup = next((s for s in current if s[0] == setup_id), None)
    if setup:
        orb, rr, sl, exp_r, n, notes = setup[1:]
        filter_name = 'L4' if 'L4_CONSOLIDATION' in notes else 'BOTH_LOST' if 'BOTH_LOST' in notes else 'Unknown'
        status = "MARGINAL" if setup_id == 20 else "EXCELLENT"
        print(f"  ID {setup_id}: {orb} RR={rr} {filter_name} - {status}")
print()

# Execute removal
print("STEP 4: EXECUTE REMOVAL")
print("-" * 80)

for setup_id in REMOVE_IDS:
    conn.execute("DELETE FROM validated_setups WHERE id = ?", [setup_id])
    print(f"[OK] Removed ID {setup_id}")

print()

# Verify
print("STEP 5: VERIFY")
print("-" * 80)
remaining = conn.execute("""
    SELECT id, orb_time, rr, expected_r
    FROM validated_setups
    WHERE instrument = 'MGC'
    ORDER BY orb_time, rr
""").fetchall()

print(f"Remaining MGC setups: {len(remaining)}")
for s in remaining:
    print(f"  ID {s[0]}: {s[1]} RR={s[2]} ExpR={s[3]:+.3f}R")
print()

if len(remaining) != len(KEEP_IDS):
    print("[!!] WARNING: Expected {len(KEEP_IDS)} setups, got {len(remaining)}")
else:
    print("[OK] Cleanup successful")

conn.close()

print()
print("=" * 80)
print("NEXT STEP: Add missing 1100 edges")
print("=" * 80)
print()
print("Run: python scripts/audit/add_1100_missing_edges.py")
print("Then: python test_app_sync.py")
