"""Check what columns exist in daily_features"""
import duckdb

conn = duckdb.connect('gold.db')

schema = conn.execute('DESCRIBE daily_features').fetchall()

print("="*80)
print("daily_features SCHEMA")
print("="*80)
print()

for col_name, col_type, *rest in schema:
    print(f"  {col_name:30s} {col_type}")

conn.close()

print()
print("="*80)
print("MISSING COLUMNS CHECK")
print("="*80)
print()

required_cols = ['pre_ny_high', 'pre_ny_low', 'pre_ny_travel']
existing_cols = [col[0] for col in schema]

for col in required_cols:
    if col in existing_cols:
        print(f"  ✓ {col} - EXISTS")
    else:
        print(f"  ✗ {col} - MISSING (filter_optimizer needs this!)")
