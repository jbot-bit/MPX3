"""Check what was in ORIGINAL database before I touched it"""
import duckdb

# Check the backup database that I copied FROM
conn = duckdb.connect('data/db/gold.db', read_only=True)

print("="*80)
print("ORIGINAL DATABASE STATE (data/db/gold.db)")
print("="*80)
print()

for table in ['daily_features', 'daily_features']:
    try:
        count = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
        date_range = conn.execute(f'SELECT MIN(date_local), MAX(date_local) FROM {table}').fetchone()
        print(f'{table}:')
        print(f'  Rows: {count}')
        print(f'  Date range: {date_range[0]} to {date_range[1]}')
        print()
    except Exception as e:
        print(f'{table}: NOT FOUND ({e})')
        print()

conn.close()

# Check current database
conn = duckdb.connect('gold.db', read_only=True)

print("="*80)
print("CURRENT DATABASE STATE (gold.db)")
print("="*80)
print()

tables = [t[0] for t in conn.execute('SHOW TABLES').fetchall()]
print(f"All tables: {', '.join([t for t in tables if 'daily_features' in t])}")
print()

for table in ['daily_features', 'daily_features']:
    if table in tables:
        count = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
        date_range = conn.execute(f'SELECT MIN(date_local), MAX(date_local) FROM {table}').fetchone()
        print(f'{table}:')
        print(f'  Rows: {count}')
        print(f'  Date range: {date_range[0]} to {date_range[1]}')
        print()
    else:
        print(f'{table}: NOT FOUND (correctly deleted)')
        print()

conn.close()
