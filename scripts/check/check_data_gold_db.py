"""Check data/gold.db contents"""
import duckdb

conn = duckdb.connect('data/gold.db', read_only=True)

print("="*80)
print("CHECKING data/gold.db")
print("="*80)
print()

tables = [t[0] for t in conn.execute('SHOW TABLES').fetchall()]
print(f"Tables: {', '.join(tables)}")
print()

for table in tables:
    count = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
    print(f"{table}: {count:,} rows")

# Check daily_features date range if it exists
if 'daily_features' in tables:
    print()
    result = conn.execute('''
        SELECT
            MIN(date_local) as min_date,
            MAX(date_local) as max_date,
            COUNT(DISTINCT date_local) as unique_dates
        FROM daily_features
    ''').fetchone()

    if result[0]:
        print(f"daily_features date range: {result[0]} to {result[1]}")
        print(f"Unique dates: {result[2]:,}")

conn.close()
