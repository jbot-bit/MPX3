import duckdb

# Check root gold.db
try:
    conn = duckdb.connect('gold.db', read_only=True)
    count = conn.execute('SELECT COUNT(*) FROM validated_setups').fetchone()[0]
    print(f'Root gold.db - validated_setups count: {count}')
    if count > 0:
        print('Sample data:')
        for row in conn.execute('SELECT instrument, orb_time, rr, sl_mode FROM validated_setups LIMIT 10').fetchall():
            print(f'  {row}')
    conn.close()
except Exception as e:
    print(f'Root gold.db error: {e}')

# Check data/gold.db
try:
    conn = duckdb.connect('data/gold.db', read_only=True)
    count = conn.execute('SELECT COUNT(*) FROM validated_setups').fetchone()[0]
    print(f'\ndata/gold.db - validated_setups count: {count}')
    if count > 0:
        print('Sample data:')
        for row in conn.execute('SELECT instrument, orb_time, rr, sl_mode FROM validated_setups LIMIT 10').fetchall():
            print(f'  {row}')
    conn.close()
except Exception as e:
    print(f'data/gold.db error: {e}')

# Check data/db/gold.db
try:
    conn = duckdb.connect('data/db/gold.db', read_only=True)
    count = conn.execute('SELECT COUNT(*) FROM validated_setups').fetchone()[0]
    print(f'\ndata/db/gold.db - validated_setups count: {count}')
    if count > 0:
        print('Sample data:')
        for row in conn.execute('SELECT instrument, orb_time, rr, sl_mode FROM validated_setups LIMIT 10').fetchall():
            print(f'  {row}')
    conn.close()
except Exception as e:
    print(f'data/db/gold.db error: {e}')
