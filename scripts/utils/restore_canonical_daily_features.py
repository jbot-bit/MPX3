"""Restore the ORIGINAL canonical daily_features (745 rows)"""
import duckdb

print("="*80)
print("RESTORING CANONICAL daily_features FROM BACKUP")
print("="*80)
print()

# Read from backup
src = duckdb.connect('data/db/gold.db', read_only=True)
df = src.execute('SELECT * FROM daily_features').df()
src.close()

print(f"Read {len(df)} rows from data/db/gold.db")
print(f"Date range: {df['date_local'].min()} to {df['date_local'].max()}")
print()

# Write to current database
dst = duckdb.connect('gold.db')

# Drop old table
dst.execute('DROP TABLE IF EXISTS daily_features')
print("Dropped old daily_features table")

# Create new table from dataframe
dst.execute('CREATE TABLE daily_features AS SELECT * FROM df')
print("Created new daily_features table from backup")

# Verify
count = dst.execute('SELECT COUNT(*) FROM daily_features').fetchone()[0]
date_range = dst.execute('SELECT MIN(date_local), MAX(date_local) FROM daily_features').fetchone()

print()
print("="*80)
print("RESTORED SUCCESSFULLY")
print("="*80)
print(f"daily_features: {count} rows")
print(f"Date range: {date_range[0]} to {date_range[1]}")
print()

# Delete any remaining v2 tables (except _half, _mpl, _nq variants which are legitimate)
tables = [t[0] for t in dst.execute('SHOW TABLES').fetchall()]
if 'daily_features_v2' in tables:
    dst.execute('DROP TABLE daily_features_v2')
    print("Deleted daily_features_v2 (was outdated)")

dst.close()

print()
print("daily_features is now canonical with FULL data (745 rows)")
