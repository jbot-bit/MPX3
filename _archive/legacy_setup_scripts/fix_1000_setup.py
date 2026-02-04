import duckdb

# Connect to database
conn = duckdb.connect('data/db/gold.db')

# Check current state
print("Before fix:")
result = conn.execute("SELECT id, orb_time, rr, sl_mode FROM validated_setups WHERE instrument='MGC' AND orb_time='1000' ORDER BY id").fetchall()
for r in result:
    print(f"  ID={r[0]}, ORB={r[1]}, RR={r[2]}, SL={r[3]}")

# Delete all 1000 setups
conn.execute("DELETE FROM validated_setups WHERE instrument='MGC' AND orb_time='1000'")
print("\nDeleted 1000 setups")

# Re-insert the correct setups
from datetime import datetime

conn.execute("""
    INSERT INTO validated_setups (
        id, instrument, orb_time, rr, sl_mode, orb_size_filter,
        win_rate, expected_r, sample_size, notes,
        created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", [
    2, 'MGC', '1000', 8.0, 'FULL', None,
    15.3, 0.378, 516, 'CROWN JEWEL - 15% WR but 8R targets! ~+98R/year',
    datetime.now(), datetime.now()
])

conn.execute("""
    INSERT INTO validated_setups (
        id, instrument, orb_time, rr, sl_mode, orb_size_filter,
        win_rate, expected_r, sample_size, notes,
        created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", [
    7, 'MGC', '1000', 1.0, 'FULL', None,
    32.0, 0.124, 516, '1000 baseline - 1.0 RR target for comparison',
    datetime.now(), datetime.now()
])

# Commit
conn.commit()

# Verify
print("\nAfter fix:")
result = conn.execute("SELECT id, orb_time, rr, sl_mode FROM validated_setups WHERE instrument='MGC' AND orb_time='1000' ORDER BY id").fetchall()
for r in result:
    print(f"  ID={r[0]}, ORB={r[1]}, RR={r[2]}, SL={r[3]}")

conn.close()
print("\nFix applied successfully!")
