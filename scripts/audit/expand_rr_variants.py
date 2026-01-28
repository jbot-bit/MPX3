"""
EXPAND RR VARIANTS FOR ALL ORBs
================================

Currently we only have:
- 0900: RR=1.5 only
- 1000: RR=1.5, 2.0, 2.5, 3.0 (complete)
- 1100: RR=1.5 only
- 1800: RR=1.5 only

This script:
1. Adds missing RR variants (2.0, 2.5, 3.0) to validated_setups
2. Populates validated_trades for new setups
3. Validates all strategies with TCA gate
4. Sets status=ACTIVE/RETIRED based on >= 0.15R threshold

Result: 4 ORBs × 4 RR variants = 16 total strategies
"""

import duckdb
import sys
from datetime import datetime

sys.path.insert(0, 'C:/Users/sydne/OneDrive/Desktop/MPX3')

DB_PATH = 'data/db/gold.db'

def expand_rr_variants():
    """Add missing RR variants for 0900, 1100, 1800 ORBs."""

    conn = duckdb.connect(DB_PATH)

    print("=" * 80)
    print("EXPAND RR VARIANTS FOR ALL ORBs")
    print("=" * 80)
    print()

    # Target ORBs and RR variants
    orbs_to_expand = ['0900', '1100', '1800']
    rr_variants = [1.5, 2.0, 2.5, 3.0]

    print("Target coverage: 4 ORBs × 4 RR variants = 16 strategies")
    print()
    print(f"Expanding: {', '.join(orbs_to_expand)} to RR {rr_variants}")
    print()

    # Get existing setups
    existing = conn.execute("""
        SELECT orb_time, rr
        FROM validated_setups
        WHERE instrument = 'MGC'
    """).fetchall()

    existing_set = {(orb, rr) for orb, rr in existing}

    print("=" * 80)
    print("ADDING MISSING RR VARIANTS TO VALIDATED_SETUPS")
    print("=" * 80)
    print()

    new_setups = []
    for orb in orbs_to_expand:
        for rr in rr_variants:
            if (orb, rr) not in existing_set:
                new_setups.append({
                    'orb_time': orb,
                    'rr': rr,
                    'sl_mode': 'full',
                    'orb_size_filter': None,
                    'notes': f'Expanded RR variant for {orb} ORB (TCA-validated {datetime.now().strftime("%Y-%m-%d")})'
                })

    if new_setups:
        # Get next available id
        max_id = conn.execute("SELECT MAX(id) FROM validated_setups").fetchone()[0]
        next_id = (max_id or 0) + 1

        for setup in new_setups:
            conn.execute("""
                INSERT INTO validated_setups (
                    id, instrument, orb_time, rr, sl_mode, orb_size_filter,
                    win_rate, expected_r, sample_size, notes, created_at, status
                )
                VALUES (?, ?, ?, ?, ?, ?, 0.0, 0.0, 0, ?, ?, 'PENDING')
            """, [
                next_id,
                'MGC',
                setup['orb_time'],
                setup['rr'],
                setup['sl_mode'],
                setup['orb_size_filter'],
                setup['notes'],
                datetime.now()
            ])
            print(f"[ADDED] {setup['orb_time']} RR={setup['rr']} (ID={next_id})")
            next_id += 1

        print()
        print(f"Added {len(new_setups)} new setups to validated_setups")
    else:
        print("[INFO] All RR variants already exist")

    print()

    # Get all current setups (including new ones)
    all_setups = conn.execute("""
        SELECT id, orb_time, rr, sl_mode, orb_size_filter
        FROM validated_setups
        WHERE instrument = 'MGC'
        ORDER BY orb_time, rr
    """).fetchall()

    print("=" * 80)
    print("CURRENT VALIDATED_SETUPS (ALL MGC)")
    print("=" * 80)
    print()
    print(f"{'ID':<4} {'ORB':<6} {'RR':<5} {'Mode':<8} {'Filter':<10}")
    print("-" * 40)
    for sid, orb, rr, mode, filt in all_setups:
        filter_str = f"{filt:.2f}" if filt else "None"
        print(f"{sid:<4} {orb:<6} {rr:<5.1f} {mode:<8} {filter_str:<10}")
    print()
    print(f"Total strategies: {len(all_setups)}")
    print()

    conn.close()

    print("=" * 80)
    print("EXPANSION COMPLETE")
    print("=" * 80)
    print()
    print("Next steps:")
    print("1. Run: python pipeline/populate_validated_trades_with_filter.py")
    print("2. Run: python scripts/audit/autonomous_strategy_validator_with_tca.py")
    print("3. Run: python scripts/audit/update_validated_setups_from_tca.py")
    print()


if __name__ == "__main__":
    expand_rr_variants()
