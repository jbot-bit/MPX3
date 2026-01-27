"""Compare daily_features vs daily_features"""
import duckdb

conn = duckdb.connect('gold.db')

print("="*80)
print("COMPARING DAILY_FEATURES TABLES")
print("="*80)
print()

for table in ['daily_features', 'daily_features']:
    count = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
    date_range = conn.execute(f'SELECT MIN(date_local), MAX(date_local) FROM {table}').fetchone()
    print(f"{table}:")
    print(f"  Rows: {count:,}")
    print(f"  Date range: {date_range[0]} to {date_range[1]}")
    print()

conn.close()

print("If daily_features is the renamed table, update:")
print("  - filter_optimizer.py")
print("  - market_scanner.py")
print("  - All scripts to use 'daily_features' instead of 'daily_features'")
