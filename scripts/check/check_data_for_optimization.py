"""Check if we have historical data needed for filter optimization"""
import duckdb

conn = duckdb.connect('gold.db')

print("="*80)
print("CHECKING DATA AVAILABILITY FOR FILTER OPTIMIZATION")
print("="*80)
print()

# Check tables
tables = [t[0] for t in conn.execute('SHOW TABLES').fetchall()]
print("Tables in gold.db:")
for table in tables:
    print(f"  - {table}")
print()

# Check daily_features
if 'daily_features' in tables:
    count = conn.execute('SELECT COUNT(*) FROM daily_features').fetchone()[0]
    print(f"daily_features: {count:,} rows")

    if count > 0:
        # Check date range
        date_range = conn.execute('''
            SELECT
                MIN(date_local) as min_date,
                MAX(date_local) as max_date
            FROM daily_features
        ''').fetchone()

        print(f"  Date range: {date_range[0]} to {date_range[1]}")
        print()

        print("="*80)
        print("READY TO OPTIMIZE")
        print("="*80)
        print()
        print("Historical data is available.")
        print("You can run: python optimize_primary_half_stops.py")
    else:
        print()
        print("="*80)
        print("NO DATA - BACKFILL REQUIRED")
        print("="*80)
        print()
        print("daily_features table exists but is EMPTY.")
        print("You need to backfill historical data first:")
        print()
        print("  python pipeline/init_db.py")
        print("  python backfill_databento_continuous.py 2024-01-01 2026-01-25")
else:
    print("daily_features: NOT FOUND")
    print()
    print("="*80)
    print("DATABASE NOT INITIALIZED")
    print("="*80)
    print()
    print("You need to initialize the database and backfill data:")
    print()
    print("  python pipeline/init_db.py")
    print("  python backfill_databento_continuous.py 2024-01-01 2026-01-25")

conn.close()
