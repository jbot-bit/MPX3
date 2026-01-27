"""
UPDATE REALIZED_EXPECTANCY COLUMN
==================================

Apps read from realized_expectancy column (not expected_r).
Update with autonomous validator results (6-phase validation, 92 trades, correct L4 filter).
"""

import duckdb
from datetime import date

DB_PATH = 'gold.db'
conn = duckdb.connect(DB_PATH)

print("=" * 80)
print("UPDATING REALIZED_EXPECTANCY WITH AUTONOMOUS VALIDATOR RESULTS")
print("=" * 80)
print()

# Autonomous validator results (from autonomous_strategy_validator.py)
updates = [
    # EXCELLENT (survive +50% stress)
    {'id': 20, 'realized_exp': 0.423, 'sample_size': 92, 'verdict': 'EXCELLENT'},
    {'id': 21, 'realized_exp': 0.708, 'sample_size': 92, 'verdict': 'EXCELLENT'},
    {'id': 22, 'realized_exp': 0.993, 'sample_size': 92, 'verdict': 'EXCELLENT'},
    {'id': 23, 'realized_exp': 1.277, 'sample_size': 92, 'verdict': 'EXCELLENT'},

    # MARGINAL (survive +25% stress only)
    {'id': 24, 'realized_exp': 0.222, 'sample_size': 78, 'verdict': 'MARGINAL'},
    {'id': 25, 'realized_exp': 0.235, 'sample_size': 92, 'verdict': 'MARGINAL'},
    {'id': 26, 'realized_exp': 0.223, 'sample_size': 87, 'verdict': 'MARGINAL'},
]

print("Updating realized_expectancy column...")
print()

for update in updates:
    # Get old value
    old = conn.execute(f"""
        SELECT realized_expectancy
        FROM validated_setups
        WHERE id = {update['id']}
    """).fetchone()[0]

    old_str = f"{old:+.3f}R" if old is not None else "NULL"

    # Update database
    conn.execute("""
        UPDATE validated_setups
        SET
            realized_expectancy = ?,
            sample_size = ?,
            updated_at = ?
        WHERE id = ?
    """, [update['realized_exp'], update['sample_size'], date.today(), update['id']])

    print(f"[OK] ID {update['id']}: {old_str} -> {update['realized_exp']:+.3f}R ({update['verdict']}, N={update['sample_size']})")

print()
print("=" * 80)
print("VERIFICATION")
print("=" * 80)
print()

# Verify updates
result = conn.execute("""
    SELECT id, orb_time, rr, realized_expectancy, sample_size
    FROM validated_setups
    WHERE instrument = 'MGC'
    ORDER BY orb_time, rr
""").fetchall()

print("Updated MGC setups:")
for row in result:
    setup_id, orb_time, rr, realized_exp, n = row
    print(f"ID {setup_id}: {orb_time} RR={rr} ExpR={realized_exp:+.3f}R N={n}")

conn.close()

print()
print("=" * 80)
print("NEXT STEP: Run test_app_sync.py to verify apps use new values")
print("=" * 80)
