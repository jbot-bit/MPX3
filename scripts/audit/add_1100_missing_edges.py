"""
ADD MISSING 1100 EDGES - TCA Validated + Stress Tested
========================================================

Adds 3 missing 1100 ORB edges that passed ALL stress tests:
1. 0900_LOSS (sequential dependency)
2. REVERSAL (sequential dependency)
3. ACTIVE (regime-specific)

Following TCA.txt and CLAUDE.md protocols:
- Use forward-tested values (2025-2026 data)
- Include realistic costs ($7.40 MGC friction)
- Document stress test passage
- Mark as sequential/regime filters for app handling
"""

import duckdb
from datetime import date

DB_PATH = 'gold.db'
conn = duckdb.connect(DB_PATH)

print("=" * 80)
print("ADD MISSING 1100 EDGES - TCA Validated + Stress Tested")
print("=" * 80)
print()

# Get current max ID
max_id = conn.execute('SELECT COALESCE(MAX(id), 0) FROM validated_setups').fetchone()[0]
print(f"Current max ID: {max_id}")
print()

# Define edges (using forward-tested 2025-2026 values)
edges = [
    {
        'instrument': 'MGC',
        'orb_time': '1100',
        'rr': 1.5,
        'sl_mode': 'full',
        'win_rate': 64.5,  # Forward-tested 2025-2026
        'expected_r': 0.448,  # Forward-tested expectancy
        'sample_size': 107,  # 2025-2026 test set size
        'orb_size_filter': None,
        'notes': '0900_LOSS filter (0900 lost any direction). Sequential dependency edge. Forward-tested 2025-2026: +0.448R. Passed temporal/regime/cost stress tests (+50% cost survives). Context-dependent: ONLY trade when 0900 ORB failed. TCA validated 2026-01-27 with $7.40 friction (Tradovate production). REQUIRES sequential filter logic in apps.'
    },
    {
        'instrument': 'MGC',
        'orb_time': '1100',
        'rr': 1.5,
        'sl_mode': 'full',
        'win_rate': 65.2,
        'expected_r': 0.464,
        'sample_size': 66,
        'orb_size_filter': None,
        'notes': 'REVERSAL filter (0900/1000 same direction, 1100 reverses). Sequential dependency edge. Forward-tested 2025-2026: +0.464R. Passed temporal/regime/cost stress tests (+50% cost survives). Context-dependent: ONLY trade when prior trend reverses. TCA validated 2026-01-27 with $7.40 friction (Tradovate production). REQUIRES sequential filter logic in apps.'
    },
    {
        'instrument': 'MGC',
        'orb_time': '1100',
        'rr': 1.5,
        'sl_mode': 'full',
        'win_rate': 60.5,
        'expected_r': 0.349,
        'sample_size': 266,
        'orb_size_filter': None,
        'notes': 'ACTIVE_MARKETS filter (asia_range>=2.0 AND london_range>=2.0). Regime-specific edge. Forward-tested 2025-2026: +0.349R. Passed temporal/regime/cost stress tests (+50% cost survives). Largest sample size (266 trades). TCA validated 2026-01-27 with $7.40 friction (Tradovate production). REQUIRES regime checks in apps.'
    }
]

print("ADDING 3 EDGES:")
print("-" * 80)
print()

for i, edge in enumerate(edges, 1):
    next_id = max_id + i

    # Extract filter name for display
    if '0900_LOSS' in edge['notes']:
        filter_name = '0900_LOSS'
    elif 'REVERSAL' in edge['notes']:
        filter_name = 'REVERSAL'
    elif 'ACTIVE_MARKETS' in edge['notes']:
        filter_name = 'ACTIVE_MARKETS'
    else:
        filter_name = 'UNKNOWN'

    print(f"{i}. ID {next_id}: {edge['orb_time']} ORB RR={edge['rr']} {filter_name}")
    print(f"   Forward-tested: WR={edge['win_rate']:.1f}%, ExpR={edge['expected_r']:+.3f}R, N={edge['sample_size']}")

    # Insert
    query = """
        INSERT INTO validated_setups (
            id, instrument, orb_time, rr, sl_mode,
            win_rate, expected_r, sample_size,
            orb_size_filter, notes,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    try:
        conn.execute(query, [
            next_id,
            edge['instrument'],
            edge['orb_time'],
            edge['rr'],
            edge['sl_mode'],
            edge['win_rate'],
            edge['expected_r'],
            edge['sample_size'],
            edge['orb_size_filter'],
            edge['notes'],
            date.today(),
            date.today()
        ])
        print(f"   [OK] Added")
    except Exception as e:
        print(f"   [FAIL] {e}")

    print()

# Verify
print("=" * 80)
print("VERIFICATION")
print("=" * 80)
print()

final = conn.execute("""
    SELECT id, orb_time, rr, expected_r, sample_size, notes
    FROM validated_setups
    WHERE instrument = 'MGC'
    ORDER BY orb_time, rr
""").fetchall()

print(f"Total MGC setups: {len(final)}")
for s in final:
    setup_id, orb, rr, exp_r, n, notes = s
    # Extract filter type
    if 'BOTH_LOST' in notes:
        filter_name = 'BOTH_LOST'
    elif '0900_LOSS' in notes:
        filter_name = '0900_LOSS'
    elif 'REVERSAL' in notes:
        filter_name = 'REVERSAL'
    elif 'ACTIVE_MARKETS' in notes:
        filter_name = 'ACTIVE'
    elif 'L4_CONSOLIDATION' in notes:
        filter_name = 'L4'
    else:
        filter_name = 'Unknown'

    print(f"  ID {setup_id}: {orb} RR={rr} {filter_name:<12} ExpR={exp_r:+.3f}R (N={n})")

conn.close()

print()
print("=" * 80)
print("NEXT STEP: Update config.py and run test_app_sync.py")
print("=" * 80)
print()
print("WARNING: 1100 edges use SEQUENTIAL and REGIME filters")
print("         Config.py may need updates to handle these")
print()
print("Run: python test_app_sync.py")
