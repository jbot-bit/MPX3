"""
Add TCA-validated edges to validated_setups database.

Only adds edges that pass Transaction Cost Analysis (>= 0.10R post-cost).
"""

import duckdb
from datetime import datetime

DB_PATH = 'gold.db'

# TCA-validated edges (post-cost E[R] >= 0.10R)
EDGES_TO_ADD = [
    {
        'instrument': 'MGC',
        'orb_time': '1000',
        'rr': 1.5,
        'sl_mode': 'full',
        'win_rate': 69.1,
        'expected_r': 0.182,  # POST-COST
        'sample_size': 55,
        'orb_size_filter': None,
        'notes': 'London L4_CONSOLIDATION filter. Backtest: +0.382R, Post-cost (0.20R): +0.182R. SOLID edge. Test WR=69.1% (+16.0%), 55 trades, MEDIUM confidence. TCA validated 2026-01-25.'
    },
    {
        'instrument': 'MGC',
        'orb_time': '1000',
        'rr': 2.0,
        'sl_mode': 'full',
        'win_rate': 69.1,
        'expected_r': 0.115,  # POST-COST
        'sample_size': 55,
        'orb_size_filter': None,
        'notes': 'London L4_CONSOLIDATION filter. Backtest: +0.382R, Post-cost (0.27R): +0.115R. DECENT edge. Test WR=69.1% (+16.0%), 55 trades, MEDIUM confidence. TCA validated 2026-01-25.'
    },
    {
        'instrument': 'MGC',
        'orb_time': '1000',
        'rr': 1.5,
        'sl_mode': 'full',
        'win_rate': 65.6,
        'expected_r': 0.112,  # POST-COST
        'sample_size': 32,
        'orb_size_filter': None,
        'notes': 'RSI > 70 filter. Backtest: +0.312R, Post-cost (0.20R): +0.112R. DECENT edge. Test WR=65.6% (+12.5%), 32 trades, MEDIUM confidence. TCA validated 2026-01-25.'
    },
]

def add_edges():
    conn = duckdb.connect(DB_PATH)

    print("=" * 80)
    print("ADDING TCA-VALIDATED EDGES TO VALIDATED_SETUPS")
    print("=" * 80)
    print()
    print("Edges pass TCA threshold: Post-cost E[R] >= 0.10R")
    print("Cost assumption: $4.00 per trade (commission + slippage)")
    print()

    # Check current count
    current_count = conn.execute('SELECT COUNT(*) FROM validated_setups').fetchone()[0]
    print(f"Current validated_setups: {current_count} edges")
    print()

    added = 0
    for edge in EDGES_TO_ADD:
        orb = edge['orb_time']
        rr = edge['rr']
        sl = edge['sl_mode']
        wr = edge['win_rate']
        exp_r_post_cost = edge['expected_r']

        # Extract filter from notes
        if 'L4_CONSOLIDATION' in edge['notes']:
            filter_desc = 'London L4_CONSOLIDATION'
        elif 'RSI > 70' in edge['notes']:
            filter_desc = 'RSI > 70'
        else:
            filter_desc = 'Unknown filter'

        print(f"Adding: {orb} ORB | RR={rr} | {sl.upper()}")
        print(f"  Filter: {filter_desc}")
        print(f"  WR={wr}%, Post-cost E[R]={exp_r_post_cost:+.3f}, n={edge['sample_size']}")

        # Get next id
        max_id = conn.execute('SELECT COALESCE(MAX(id), 0) FROM validated_setups').fetchone()[0]
        next_id = max_id + 1

        # Insert into database
        query = """
            INSERT INTO validated_setups (
                id, instrument, orb_time, rr, sl_mode,
                win_rate, expected_r, sample_size,
                orb_size_filter, notes,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        conn.execute(query, [
            next_id,
            edge['instrument'],
            edge['orb_time'],
            edge['rr'],
            edge['sl_mode'],
            edge['win_rate'],
            edge['expected_r'],
            edge['sample_size'],
            edge.get('orb_size_filter'),
            edge['notes'],
            datetime.now(),
            datetime.now()
        ])

        added += 1
        print(f"  [OK] Added to validated_setups")
        print()

    # Check new count
    new_count = conn.execute('SELECT COUNT(*) FROM validated_setups').fetchone()[0]

    print("=" * 80)
    print(f"COMPLETE: Added {added} TCA-validated edges")
    print(f"Total validated_setups: {new_count} edges (was {current_count})")
    print("=" * 80)
    print()
    print("Next step: Update market_scanner.py to apply these filters in real-time")

    conn.close()

if __name__ == '__main__':
    add_edges()
