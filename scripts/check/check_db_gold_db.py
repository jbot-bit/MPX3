"""Check data/db/gold.db contents (the big one)"""
import duckdb

conn = duckdb.connect('data/db/gold.db', read_only=True)

print("="*80)
print("CHECKING data/db/gold.db (723MB)")
print("="*80)
print()

tables = [t[0] for t in conn.execute('SHOW TABLES').fetchall()]
print(f"Tables: {', '.join(tables)}")
print()

for table in tables:
    count = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
    print(f"{table}: {count:,} rows")

# Check bars_1m date range if it exists
if 'bars_1m' in tables:
    print()
    print("="*80)
    print("bars_1m DETAILS")
    print("="*80)
    result = conn.execute('''
        SELECT
            MIN(ts_utc) as min_ts,
            MAX(ts_utc) as max_ts,
            COUNT(DISTINCT DATE(ts_utc)) as unique_dates
        FROM bars_1m
        WHERE symbol = 'MGC'
    ''').fetchone()

    if result[0]:
        print(f"Date range: {result[0]} to {result[1]}")
        print(f"Unique dates: {result[2]:,}")

# Check daily_features if it exists
if 'daily_features' in tables:
    print()
    print("="*80)
    print("daily_features DETAILS")
    print("="*80)
    result = conn.execute('''
        SELECT
            MIN(date_local) as min_date,
            MAX(date_local) as max_date,
            COUNT(DISTINCT date_local) as unique_dates
        FROM daily_features
        WHERE instrument = 'MGC'
    ''').fetchone()

    if result[0]:
        print(f"Date range: {result[0]} to {result[1]}")
        print(f"Unique dates: {result[2]:,}")

conn.close()

print()
print("="*80)
print("If this database has data, copy it to the root directory:")
print("  cp data/db/gold.db gold.db")
print("="*80)
