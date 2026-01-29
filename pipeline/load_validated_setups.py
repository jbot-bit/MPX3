"""
Single Source of Truth: validated_setups Loader
================================================

MANDATORY shared function for loading strategies from validated_setups.
Used by BOTH:
- pipeline/populate_tradeable_metrics.py
- scripts/audit/autonomous_strategy_validator.py

CHECK.TXT REQUIREMENT #6: No duplicated queries.

ENFORCES:
- rr NOT NULL
- rr >= 1.5 by default (unless --allow-low-rr)
- sl_mode NOT NULL
- Prints schema (DESCRIBE validated_setups)
- Prints RR EVIDENCE TABLE

FAIL CLOSED: Aborts if any constraint violated.
"""

import duckdb
from typing import List, Dict


def load_validated_setups(conn, instrument: str = 'MGC', allow_low_rr: bool = False) -> List[Dict]:
    """
    Load strategies from validated_setups table.

    Args:
        conn: DuckDB connection
        instrument: Instrument symbol (default: MGC)
        allow_low_rr: Allow RR < 1.5 (default: False)

    Returns:
        List[dict]: Strategies with keys: id, instrument, orb_time, rr, sl_mode,
                    filter, win_rate, expected_r, sample_size, notes

    Raises:
        RuntimeError: If RR is NULL/invalid or constraints violated
    """

    # STEP 1: Print schema (CHECK.TXT Req #2)
    print("\n" + "="*80)
    print("SCHEMA: validated_setups")
    print("="*80)
    try:
        schema = conn.execute("DESCRIBE validated_setups").fetchall()
        for col in schema:
            col_name, col_type, null_status = col[0], col[1], col[2]
            nullable = "NULL" if null_status == "YES" else "NOT NULL"
            print(f"  {col_name:<25} {col_type:<15} {nullable:<10}")
    except Exception as e:
        raise RuntimeError(f"CRITICAL: Cannot query schema for validated_setups: {e}")
    print("="*80 + "\n")

    # STEP 2: Query strategies
    try:
        rows = conn.execute("""
            SELECT id, instrument, orb_time, rr, sl_mode, orb_size_filter,
                   win_rate, expected_r, sample_size, notes
            FROM validated_setups
            WHERE instrument = ?
            ORDER BY id
        """, [instrument]).fetchall()
    except Exception as e:
        raise RuntimeError(f"CRITICAL: Cannot query validated_setups: {e}")

    if not rows:
        raise RuntimeError(
            f"CRITICAL: No {instrument} strategies found in validated_setups. "
            f"Database may be empty or instrument name incorrect. Aborting."
        )

    # STEP 3: Print RR EVIDENCE TABLE (CHECK.TXT Req #3)
    print("="*80)
    print(f"RR EVIDENCE TABLE (Source: validated_setups)")
    print(f"Instrument: {instrument}")
    print("="*80)
    print(f"{'id':<6} {'orb_time':<10} {'rr':<8} {'sl_mode':<10} {'filter':<12} {'source':<20}")
    print("-"*80)

    strategies = []

    for row in rows:
        id_val, inst, orb_time, rr, sl_mode, filter_val, wr, exp_r, n, notes = row

        # STEP 4: Enforce constraints (CHECK.TXT Req #4)

        # Constraint 1: rr NOT NULL
        if rr is None:
            raise RuntimeError(
                f"CRITICAL: Strategy ID {id_val} (ORB {orb_time}) has NULL RR. "
                f"RR must be defined in validated_setups. Aborting."
            )

        # Constraint 2: rr > 0
        if rr <= 0:
            raise RuntimeError(
                f"CRITICAL: Strategy ID {id_val} (ORB {orb_time}) has invalid RR={rr}. "
                f"RR must be > 0. Aborting."
            )

        # Constraint 3: rr >= 1.5 (unless allow_low_rr flag set)
        if not allow_low_rr and rr < 1.5:
            raise RuntimeError(
                f"CRITICAL: Strategy ID {id_val} (ORB {orb_time}) has RR={rr} < 1.5. "
                f"Use --allow-low-rr flag if intentional. Aborting."
            )

        # Constraint 4: sl_mode NOT NULL
        if not sl_mode:
            raise RuntimeError(
                f"CRITICAL: Strategy ID {id_val} (ORB {orb_time}) has NULL sl_mode. "
                f"sl_mode must be 'full' or 'half'. Aborting."
            )

        # Print evidence
        filter_str = f"{filter_val:.2f}" if filter_val is not None else "None"
        print(f"{id_val:<6} {orb_time:<10} {rr:<8.1f} {sl_mode:<10} {filter_str:<12} {'validated_setups':<20}")

        strategies.append({
            'id': id_val,
            'instrument': inst,
            'orb_time': orb_time,
            'rr': float(rr),
            'sl_mode': sl_mode.lower() if sl_mode else 'full',
            'filter': float(filter_val) if filter_val is not None else None,
            'win_rate': float(wr) if wr is not None else None,
            'expected_r': float(exp_r) if exp_r is not None else None,
            'sample_size': int(n) if n is not None else None,
            'notes': notes
        })

    print("="*80)
    print(f"Total strategies loaded: {len(strategies)}")
    print(f"Unique ORB times: {len(set(s['orb_time'] for s in strategies))}")
    print(f"RR range: {min(s['rr'] for s in strategies):.1f} - {max(s['rr'] for s in strategies):.1f}")
    print("="*80 + "\n")

    return strategies


if __name__ == "__main__":
    # Test the loader
    import sys
    conn = duckdb.connect('data/db/gold.db')

    try:
        strategies = load_validated_setups(conn, instrument='MGC')
        print(f"\n[SUCCESS] Loaded {len(strategies)} MGC strategies")
        print(f"[PASS] All constraints passed (rr NOT NULL, rr >= 1.5, sl_mode NOT NULL)")
    except RuntimeError as e:
        print(f"\n[FAIL] {e}")
        sys.exit(1)
