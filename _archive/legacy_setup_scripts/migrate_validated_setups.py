"""
Migrate validated_setups table from old schema to new schema
"""
import duckdb
import sys
from datetime import datetime

DB_PATH = "data/db/gold.db"

# Backup first
print("Creating backup...")
conn_read = duckdb.connect(DB_PATH, read_only=True)
backup = conn_read.execute("SELECT * FROM validated_setups").df()
conn_read.close()

print(f"Loaded {len(backup)} setups from old schema")
print(f"Columns: {list(backup.columns)}")

# Drop and recreate with new schema
conn = duckdb.connect(DB_PATH)

print("\nDropping old validated_setups table...")
conn.execute("DROP TABLE IF EXISTS validated_setups")

print("Creating new validated_setups table...")
conn.execute("""
    CREATE TABLE validated_setups (
        id INTEGER PRIMARY KEY,
        instrument VARCHAR NOT NULL,
        orb_time VARCHAR NOT NULL,
        rr DOUBLE NOT NULL,
        sl_mode VARCHAR NOT NULL,
        orb_size_filter DOUBLE,
        win_rate DOUBLE NOT NULL,
        expected_r DOUBLE NOT NULL,
        sample_size INTEGER NOT NULL,
        notes VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

print("Migrating data...")

# Map old columns to new columns
for idx, row in backup.iterrows():
    conn.execute("""
        INSERT INTO validated_setups (
            id, instrument, orb_time, rr, sl_mode,
            orb_size_filter, win_rate, expected_r, sample_size, notes,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        idx + 1,  # id (auto-increment starting from 1)
        row['instrument'],
        row['orb_time'],
        row['rr'],
        row['sl_mode'],
        row['orb_size_filter'] if 'orb_size_filter' in row and row['orb_size_filter'] else None,
        row['win_rate'],
        row['avg_r'],  # avg_r → expected_r
        row['trades'],  # trades → sample_size
        row['notes'] if 'notes' in row else None,
        datetime.now(),
        datetime.now()
    ])

# Verify
count = conn.execute("SELECT COUNT(*) FROM validated_setups").fetchone()[0]
print(f"\nMigration complete: {count} setups migrated")

# Show sample
print("\nSample rows:")
df = conn.execute("SELECT instrument, orb_time, rr, sl_mode, expected_r, sample_size FROM validated_setups LIMIT 5").df()
print(df.to_string())

conn.close()
print("\n✓ Migration successful!")
