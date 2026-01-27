"""Check what's in validated_setups table"""
import duckdb

conn = duckdb.connect('gold.db')

print("="*80)
print("VALIDATED_SETUPS TABLE")
print("="*80)
print()

# Get schema
schema = conn.execute('DESCRIBE validated_setups').fetchall()
print("Schema:")
for col in schema:
    print(f"  {col[0]:30s} {col[1]}")
print()

# Get all rows
rows = conn.execute('''
    SELECT
        orb_time, rr, sl_mode, win_rate, expected_r,
        sample_size, orb_size_filter, notes
    FROM validated_setups
    ORDER BY orb_time, rr
''').fetchall()

print(f"Total edges: {len(rows)}")
print()

for i, row in enumerate(rows, 1):
    orb, rr, sl, wr, exp_r, n, size_filter, notes = row
    print(f"{i}. {orb} ORB | RR={rr} | {sl.upper()}")
    print(f"   WR={wr}%, E[R]={exp_r:.3f}, n={n}, Size filter={size_filter}")

    # Extract filter from notes
    if 'L4_CONSOLIDATION' in notes:
        print(f"   Filter: London L4_CONSOLIDATION")
    elif 'RSI > 70' in notes:
        print(f"   Filter: RSI > 70")
    else:
        print(f"   Filter: Unknown")

    print()

conn.close()
