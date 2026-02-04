"""
Add top filtered edges to validated_setups database.

Adds the best performing filters discovered by filter_optimizer.py at their optimal RR levels.
"""

import duckdb
from datetime import datetime

DB_PATH = 'gold.db'

# Top filters at optimal RR levels
FILTERED_EDGES = [
    # 1. 1000 ORB + London L4_CONSOLIDATION (BEST OVERALL)
    {
        'instrument': 'MGC',
        'orb_time': '1000',
        'rr': 8.0,
        'sl_mode': 'full',
        'win_rate': 69.1,
        'expected_r': 0.382,
        'sample_size': 55,
        'orb_size_filter': None,  # No ORB size filter
        'london_type_filter': 'L4_CONSOLIDATION',
        'notes': 'London L4_CONSOLIDATION filter. Test WR=69.1% (+16.0%), E[R]=+0.382 (+0.320R improvement). Validated with 8.7% overfit score. BEST FILTER across all edges.'
    },

    # 2. 0030 ORB + RSI < 40 (SECOND BEST)
    {
        'instrument': 'MGC',
        'orb_time': '0030',
        'rr': 3.0,
        'sl_mode': 'half',
        'win_rate': 60.9,
        'expected_r': 0.217,
        'sample_size': 46,
        'orb_size_filter': None,
        'rsi_filter_max': 40,  # RSI < 40
        'notes': 'RSI < 40 filter. Test WR=60.9% (+13.0%), E[R]=+0.217 (+0.259R improvement). Validated with 9.5% overfit score. Turns losing baseline into winner.'
    },

    # 3. 1000 ORB + RSI > 70 (THIRD BEST)
    {
        'instrument': 'MGC',
        'orb_time': '1000',
        'rr': 5.0,  # Using RR=5.0 as a strong performing level
        'sl_mode': 'full',
        'win_rate': 65.6,
        'expected_r': 0.312,
        'sample_size': 32,
        'orb_size_filter': None,
        'rsi_filter_min': 70,  # RSI > 70
        'notes': 'RSI > 70 filter. Test WR=65.6% (+12.5%), E[R]=+0.312 (+0.250R improvement). Validated with 8.0% overfit score.'
    },

    # 4. 0900 ORB + London L4_CONSOLIDATION
    {
        'instrument': 'MGC',
        'orb_time': '0900',
        'rr': 6.0,
        'sl_mode': 'full',
        'win_rate': 62.3,
        'expected_r': 0.245,
        'sample_size': 53,
        'orb_size_filter': None,
        'london_type_filter': 'L4_CONSOLIDATION',
        'notes': 'London L4_CONSOLIDATION filter. Test WR=62.3% (+4.5%), E[R]=+0.245 (+0.090R improvement). Validated.'
    },

    # 5. 1800 ORB + RSI > 70
    {
        'instrument': 'MGC',
        'orb_time': '1800',
        'rr': 1.5,
        'sl_mode': 'full',
        'win_rate': 62.5,
        'expected_r': 0.250,
        'sample_size': 32,
        'orb_size_filter': None,
        'rsi_filter_min': 70,
        'notes': 'RSI > 70 filter. Test WR=62.5% (+10.6%), E[R]=+0.250 (+0.212R improvement). Validated with 10% overfit score.'
    },

    # 6. 1100 ORB + London L4_CONSOLIDATION
    {
        'instrument': 'MGC',
        'orb_time': '1100',
        'rr': 3.0,
        'sl_mode': 'full',
        'win_rate': 56.4,
        'expected_r': 0.127,
        'sample_size': 55,
        'orb_size_filter': None,
        'london_type_filter': 'L4_CONSOLIDATION',
        'notes': 'London L4_CONSOLIDATION filter. Test WR=56.4% (+3.5%), E[R]=+0.127 (+0.069R improvement). Validated.'
    },
]

def add_filtered_edges():
    conn = duckdb.connect(DB_PATH)

    print("=" * 80)
    print("ADDING FILTERED EDGES TO VALIDATED_SETUPS")
    print("=" * 80)
    print()

    # Check current setups
    current = conn.execute('SELECT COUNT(*) as count FROM validated_setups').fetchone()[0]
    print(f"Current validated_setups: {current} edges")
    print()

    added = 0
    for edge in FILTERED_EDGES:
        orb = edge['orb_time']
        rr = edge['rr']
        sl = edge['sl_mode']
        wr = edge['win_rate']
        exp_r = edge['expected_r']

        # Build filter description
        filters = []
        if edge.get('london_type_filter'):
            filters.append(f"London {edge['london_type_filter']}")
        if edge.get('rsi_filter_min'):
            filters.append(f"RSI > {edge['rsi_filter_min']}")
        if edge.get('rsi_filter_max'):
            filters.append(f"RSI < {edge['rsi_filter_max']}")
        filter_desc = " + ".join(filters)

        print(f"Adding: {orb} ORB | RR={rr} | {sl.upper()}")
        print(f"  Filter: {filter_desc}")
        print(f"  WR={wr}%, E[R]={exp_r:+.3f}, n={edge['sample_size']}")

        # Insert into database
        query = """
            INSERT INTO validated_setups (
                instrument, orb_time, rr, sl_mode,
                win_rate, expected_r, sample_size,
                orb_size_filter, notes,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        conn.execute(query, [
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
    new_count = conn.execute('SELECT COUNT(*) as count FROM validated_setups').fetchone()[0]

    print("=" * 80)
    print(f"COMPLETE: Added {added} filtered edges")
    print(f"Total validated_setups: {new_count} edges (was {current})")
    print("=" * 80)

    conn.close()

if __name__ == '__main__':
    add_filtered_edges()
