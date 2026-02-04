"""
Update validated_setups with TCA-corrected edges (realistic $2.50 costs).

Adds 8 edges that pass >= 0.10R post-cost threshold.
"""

import duckdb
from datetime import datetime

DB_PATH = 'gold.db'

# TCA-validated edges (post-cost E[R] >= 0.10R with realistic $2.50 costs)
# Only includes BEST filter for each unique (orb_time, rr, sl_mode) combination
EDGES_TO_ADD = [
    # 1000 ORB edges (L4_CONSOLIDATION is superior to RSI>70 for all RR levels)
    {
        'instrument': 'MGC',
        'orb_time': '1000',
        'rr': 1.5,
        'sl_mode': 'full',
        'win_rate': 69.1,
        'expected_r': 0.257,  # POST-COST (BEST: L4_CONSOLIDATION beats RSI>70 by 0.069R)
        'sample_size': 55,
        'orb_size_filter': None,
        'notes': 'London L4_CONSOLIDATION filter. Backtest: +0.382R, Post-cost (0.125R): +0.257R. EXCELLENT edge. Test WR=69.1% (+16.0%), 55 trades, MEDIUM confidence. TCA validated 2026-01-25 with realistic $2.50 costs.'
    },
    {
        'instrument': 'MGC',
        'orb_time': '1000',
        'rr': 2.0,
        'sl_mode': 'full',
        'win_rate': 69.1,
        'expected_r': 0.215,  # POST-COST (BEST: L4_CONSOLIDATION beats RSI>70 by 0.069R)
        'sample_size': 55,
        'orb_size_filter': None,
        'notes': 'London L4_CONSOLIDATION filter. Backtest: +0.382R, Post-cost (0.167R): +0.215R. EXCELLENT edge. Test WR=69.1% (+16.0%), 55 trades, MEDIUM confidence. TCA validated 2026-01-25.'
    },
    {
        'instrument': 'MGC',
        'orb_time': '1000',
        'rr': 2.5,
        'sl_mode': 'full',
        'win_rate': 69.1,
        'expected_r': 0.132,  # POST-COST
        'sample_size': 55,
        'orb_size_filter': None,
        'notes': 'London L4_CONSOLIDATION filter. Backtest: +0.382R, Post-cost (0.250R): +0.132R. DECENT edge. Test WR=69.1% (+16.0%), 55 trades, MEDIUM confidence. TCA validated 2026-01-25.'
    },
    {
        'instrument': 'MGC',
        'orb_time': '1000',
        'rr': 3.0,
        'sl_mode': 'full',
        'win_rate': 69.1,
        'expected_r': 0.132,  # POST-COST
        'sample_size': 55,
        'orb_size_filter': None,
        'notes': 'London L4_CONSOLIDATION filter. Backtest: +0.382R, Post-cost (0.250R): +0.132R. DECENT edge. Test WR=69.1% (+16.0%), 55 trades, MEDIUM confidence. TCA validated 2026-01-25.'
    },

    # 1800 ORB edges (RSI>70 is the only profitable filter)
    {
        'instrument': 'MGC',
        'orb_time': '1800',
        'rr': 1.5,
        'sl_mode': 'full',
        'win_rate': 62.5,
        'expected_r': 0.125,  # POST-COST
        'sample_size': 32,
        'orb_size_filter': None,
        'notes': 'RSI > 70 filter. Backtest: +0.250R, Post-cost (0.125R): +0.125R. DECENT edge. Test WR=62.5% (+10.6%), 32 trades, MEDIUM confidence. TCA validated 2026-01-25.'
    },

    # 0900 ORB edges (L4_CONSOLIDATION)
    {
        'instrument': 'MGC',
        'orb_time': '0900',
        'rr': 1.5,
        'sl_mode': 'full',
        'win_rate': 62.3,
        'expected_r': 0.120,  # POST-COST
        'sample_size': 53,
        'orb_size_filter': None,
        'notes': 'London L4_CONSOLIDATION filter. Backtest: +0.245R, Post-cost (0.125R): +0.120R. DECENT edge. Test WR=62.3% (+4.5%), 53 trades, MEDIUM confidence. TCA validated 2026-01-25.'
    },
]

def update_validated_setups():
    conn = duckdb.connect(DB_PATH)

    print("=" * 80)
    print("UPDATING VALIDATED_SETUPS WITH TCA-CORRECTED EDGES")
    print("=" * 80)
    print()
    print("Cost model: $2.50 per trade (realistic broker costs)")
    print("Threshold: Post-cost E[R] >= 0.10R")
    print()

    # Clear only MGC entries (preserve NQ/MPL setups)
    mgc_count = conn.execute("SELECT COUNT(*) FROM validated_setups WHERE instrument = 'MGC'").fetchone()[0]

    if mgc_count > 0:
        print(f"Clearing {mgc_count} old MGC entries (preserving NQ/MPL setups)...")
        conn.execute("DELETE FROM validated_setups WHERE instrument = 'MGC'")
        print()

    # Add new edges
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

        # Determine quality
        if exp_r_post_cost >= 0.20:
            quality = 'EXCELLENT'
        elif exp_r_post_cost >= 0.15:
            quality = 'GOOD'
        elif exp_r_post_cost >= 0.10:
            quality = 'DECENT'
        else:
            quality = 'THIN'

        print(f"Adding: {orb} ORB | RR={rr} | {sl.upper()}")
        print(f"  Filter: {filter_desc}")
        print(f"  WR={wr}%, Post-cost E[R]={exp_r_post_cost:+.3f}, n={edge['sample_size']}")
        print(f"  Quality: {quality}")

        # Get next id
        max_id = conn.execute('SELECT COALESCE(MAX(id), 0) FROM validated_setups').fetchone()[0]
        next_id = max_id + 1

        # Insert
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
        print(f"  [OK] Added\n")

    # Verify
    new_count = conn.execute('SELECT COUNT(*) FROM validated_setups').fetchone()[0]

    print("=" * 80)
    print(f"COMPLETE: Added {added} TCA-validated edges")
    print(f"Total validated_setups: {new_count} edges")
    print("=" * 80)
    print()
    print("Breakdown by quality:")

    quality_counts = conn.execute("""
        SELECT
            CASE
                WHEN expected_r >= 0.20 THEN 'EXCELLENT'
                WHEN expected_r >= 0.15 THEN 'GOOD'
                WHEN expected_r >= 0.10 THEN 'DECENT'
                ELSE 'THIN'
            END as quality,
            COUNT(*) as count
        FROM validated_setups
        GROUP BY quality
        ORDER BY
            CASE quality
                WHEN 'EXCELLENT' THEN 1
                WHEN 'GOOD' THEN 2
                WHEN 'DECENT' THEN 3
                ELSE 4
            END
    """).fetchall()

    for quality, count in quality_counts:
        print(f"  {quality}: {count} edges")

    print()
    print("Next steps:")
    print("  1. Update market_scanner.py to apply these filters")
    print("  2. Update trading_app/config.py if needed")
    print("  3. Run test_app_sync.py to verify synchronization")

    conn.close()

if __name__ == '__main__':
    update_validated_setups()
