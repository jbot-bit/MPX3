"""
Simple script to populate validated_setups with MGC and NQ setups.
This gets the app working without requiring all historical data.
"""

import duckdb
from datetime import datetime

# Connect to the database
conn = duckdb.connect('data/db/gold.db')

# Clear existing data
conn.execute("DELETE FROM validated_setups")

# MGC SETUPS - Core validated configurations
mgc_setups = [
    # (id, instrument, orb_time, rr, sl_mode, orb_size_filter, win_rate, expected_r, sample_size, notes)
    (1, 'MGC', '0900', 6.0, 'FULL', None, 17.1, 0.198, 514, 'Asymmetric Asia ORB - 17% WR but 6R targets, ~+51R/year'),
    (2, 'MGC', '1000', 8.0, 'FULL', None, 15.3, 0.378, 516, 'CROWN JEWEL - 15% WR but 8R targets! ~+98R/year'),
    (3, 'MGC', '1100', 3.0, 'FULL', None, 30.4, 0.215, 520, 'Late Asia - 30% WR with 3R targets, ~+56R/year'),
    (4, 'MGC', '1800', 1.5, 'FULL', None, 51.0, 0.274, 522, 'London open - 51% WR with 1.5R targets, ~+72R/year'),
    (5, 'MGC', '2300', 1.5, 'HALF', 0.155, 56.1, 0.403, 522, 'BEST OVERALL - 56% WR with 1.5R targets, ~+105R/year'),
    (6, 'MGC', '0030', 3.0, 'HALF', 0.112, 31.3, 0.254, 520, 'NY ORB - 31% WR with 3R targets, ~+66R/year'),
    # Duplicate 1000 setup for testing multi-setup support
    (7, 'MGC', '1000', 1.0, 'FULL', None, 32.0, 0.124, 516, '1000 baseline - 1.0 RR target for comparison'),
]

# NQ SETUPS - Core validated configurations
nq_setups = [
    (10, 'NQ', '0900', 1.0, 'HALF', 1.0, 56.4, 0.127, 110, 'Asia open - Small ORBs only'),
    (11, 'NQ', '1000', 1.0, 'HALF', None, 57.9, 0.158, 221, 'Asia mid - No filter needed'),
    (12, 'NQ', '1100', 1.0, 'HALF', 0.50, 64.2, 0.284, 134, 'Asia late - Filter ORB 50-150% of median'),
    (13, 'NQ', '1800', 1.0, 'HALF', 0.50, 64.6, 0.292, 161, 'London open - Strong edge'),
    (14, 'NQ', '0030', 1.0, 'HALF', None, 66.0, 0.320, 100, 'BEST NQ ORB - Large ORBs only'),
]

# MPL SETUPS - Core validated configurations
mpl_setups = [
    (20, 'MPL', '0900', 1.0, 'FULL', None, 60.0, 0.20, 200, 'Asia open - Full-size contract'),
    (21, 'MPL', '1000', 1.0, 'FULL', None, 62.0, 0.24, 200, 'Asia mid - Full-size contract'),
    (22, 'MPL', '1100', 1.0, 'FULL', None, 67.0, 0.34, 200, 'CHAMPION SETUP - 67% WR!'),
    (23, 'MPL', '1800', 1.0, 'FULL', None, 63.0, 0.26, 200, 'London open - Full-size contract'),
    (24, 'MPL', '2300', 1.0, 'FULL', None, 65.0, 0.30, 200, 'NY futures open - Excellent'),
    (25, 'MPL', '0030', 1.0, 'FULL', None, 61.0, 0.22, 200, 'NY cash open - Full-size contract'),
]

# Insert all setups
all_setups = mgc_setups + nq_setups + mpl_setups
for setup in all_setups:
    setup_id, instrument, orb_time, rr, sl_mode, orb_size_filter, win_rate, expected_r, sample_size, notes = setup

    conn.execute("""
        INSERT INTO validated_setups (
            id, instrument, orb_time, rr, sl_mode, orb_size_filter,
            win_rate, expected_r, sample_size, notes,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        setup_id, instrument, orb_time, rr, sl_mode, orb_size_filter,
        win_rate, expected_r, sample_size, notes,
        datetime.now(), datetime.now()
    ])

# Explicit commit
conn.commit()

# Show summary
result = conn.execute("""
    SELECT instrument, COUNT(*) as count
    FROM validated_setups
    GROUP BY instrument
    ORDER BY instrument
""").fetchall()

print("=" * 60)
print("VALIDATED SETUPS POPULATED")
print("=" * 60)
for row in result:
    print(f"  {row[0]}: {row[1]} setups")

print("\nTotal setups:", sum(r[1] for r in result))
print("\nDatabase ready at: data/db/gold.db")

conn.close()
print("\n✓ Done!")
