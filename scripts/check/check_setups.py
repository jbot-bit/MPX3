import duckdb

conn = duckdb.connect('data/db/gold.db', read_only=True)

print("="*70)
print("DATABASE CONTENTS CHECK")
print("="*70)

# Check validated_setups
count = conn.execute('SELECT COUNT(*) FROM validated_setups').fetchone()[0]
print(f"\nvalidated_setups count: {count}")

if count > 0:
    print("\nFirst 10 setups:")
    rows = conn.execute('''
        SELECT id, instrument, orb_time, rr, sl_mode, win_rate, expected_r, sample_size
        FROM validated_setups
        LIMIT 10
    ''').fetchall()
    for row in rows:
        print(f"  {row[0]}: {row[1]} {row[2]} RR={row[3]} {row[4]} | WR={row[5]:.1%} ExpR={row[6]:+.3f} N={row[7]}")

# Check edge_registry
count2 = conn.execute('SELECT COUNT(*) FROM edge_registry').fetchone()[0]
print(f"\nedge_registry count: {count2}")

if count2 > 0:
    print("\nFirst 5 edges:")
    rows = conn.execute('''
        SELECT edge_id, instrument, orb_time, status
        FROM edge_registry
        LIMIT 5
    ''').fetchall()
    for row in rows:
        print(f"  {row[0]}: {row[1]} {row[2]} - {row[3]}")

# Check validated_trades
count3 = conn.execute('SELECT COUNT(*) FROM validated_trades').fetchone()[0]
print(f"\nvalidated_trades count: {count3}")

conn.close()
