"""
UPDATE VALIDATED EXPECTANCY VALUES
===================================

Updates validated_setups with new expectancy values from autonomous validator.
All strategies passed at $7.40 mandatory costs.
"""

import duckdb
from datetime import date

DB_PATH = 'gold.db'
conn = duckdb.connect(DB_PATH)

print("=" * 80)
print("UPDATING VALIDATED_SETUPS WITH NEW EXPECTANCY VALUES")
print("=" * 80)
print()

# Validation results from autonomous validator
updates = [
    # EXCELLENT (survive +50% stress)
    {'id': 20, 'exp_740': 0.423, 'exp_25': 0.359, 'exp_50': 0.303, 'sample_size': 92, 'verdict': 'EXCELLENT'},
    {'id': 21, 'exp_740': 0.708, 'exp_25': 0.631, 'exp_50': 0.563, 'sample_size': 92, 'verdict': 'EXCELLENT'},
    {'id': 22, 'exp_740': 0.993, 'exp_25': 0.903, 'exp_50': 0.824, 'sample_size': 92, 'verdict': 'EXCELLENT'},
    {'id': 23, 'exp_740': 1.277, 'exp_25': 1.175, 'exp_50': 1.084, 'sample_size': 92, 'verdict': 'EXCELLENT'},

    # MARGINAL (survive +25% stress only)
    {'id': 24, 'exp_740': 0.222, 'exp_25': 0.158, 'exp_50': 0.101, 'sample_size': 78, 'verdict': 'MARGINAL'},
    {'id': 25, 'exp_740': 0.235, 'exp_25': 0.177, 'exp_50': 0.127, 'sample_size': 92, 'verdict': 'MARGINAL'},
    {'id': 26, 'exp_740': 0.223, 'exp_25': 0.157, 'exp_50': 0.099, 'sample_size': 87, 'verdict': 'MARGINAL'},
]

for update in updates:
    # Update notes to include validation results
    current = conn.execute(f"SELECT notes FROM validated_setups WHERE id = {update['id']}").fetchone()[0]

    # Append validation results to notes
    new_notes = f"{current} | AUTONOMOUS VALIDATION 2026-01-27: {update['verdict']} at $7.40 ({update['exp_740']:+.3f}R), +25% ({update['exp_25']:+.3f}R), +50% ({update['exp_50']:+.3f}R), N={update['sample_size']}."

    # Update database
    conn.execute("""
        UPDATE validated_setups
        SET
            expected_r = ?,
            sample_size = ?,
            notes = ?,
            updated_at = ?
        WHERE id = ?
    """, [update['exp_740'], update['sample_size'], new_notes, date.today(), update['id']])

    print(f"[OK] Updated ID {update['id']}: ExpR={update['exp_740']:+.3f}R ({update['verdict']})")

print()
print("=" * 80)
print("VERIFICATION")
print("=" * 80)
print()

# Verify updates
result = conn.execute("""
    SELECT id, orb_time, rr, expected_r, sample_size
    FROM validated_setups
    WHERE instrument = 'MGC'
    ORDER BY orb_time, rr
""").fetchall()

for row in result:
    print(f"ID {row[0]}: {row[1]} RR={row[2]} ExpR={row[3]:+.3f}R N={row[4]}")

conn.close()

print()
print("=" * 80)
print("NEXT STEP: Run test_app_sync.py to verify config sync")
print("=" * 80)
