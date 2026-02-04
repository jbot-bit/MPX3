#!/usr/bin/env python3
"""
CI GUARD: Status Derivation Consistency Check

Verifies that stored status in validated_setups matches what would be
derived from expected_r and sample_size.

RULE: Status MUST be derived, never stored as source of truth.

Derivation logic:
- ACTIVE: expected_r >= 0.15 AND sample_size >= 30
- REJECTED: expected_r < 0.15 OR sample_size < 30
- RETIRED: Manually set (excluded from check)
- INVALID_NO_DATA: Missing metrics

Run: python scripts/check/check_status_derivation.py
     python scripts/check/check_status_derivation.py --strict  (fail on mismatch)

Exit code 0 = PASS, Exit code 1 = FAIL (mismatches found in strict mode)
"""

import sys
import os
from pathlib import Path

# Add project root to path FIRST
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipeline.paths import GOLD_DB_PATH
from trading_app.status_utils import derive_status, check_status_consistency, MIN_EXPECTED_R, MIN_SAMPLE_SIZE


def get_db_connection():
    """Get database connection."""
    import duckdb

    # Try data/db/gold.db first (canonical)
    db_path = REPO_ROOT / 'data' / 'db' / GOLD_DB_PATH
    if db_path.exists():
        return duckdb.connect(str(db_path), read_only=True)

    # Fallback to root gold.db
    db_path = REPO_ROOT / GOLD_DB_PATH
    if db_path.exists():
        return duckdb.connect(str(db_path), read_only=True)

    raise FileNotFoundError("No gold.db found")


def check_validated_setups():
    """Check status consistency for all validated_setups rows."""
    con = get_db_connection()

    # Get all rows with status info
    rows = con.execute("""
        SELECT
            id,
            instrument,
            orb_time,
            rr,
            status,
            expected_r,
            sample_size
        FROM validated_setups
        ORDER BY instrument, orb_time, rr
    """).fetchall()

    con.close()

    results = {
        'total': len(rows),
        'consistent': 0,
        'mismatches': [],
        'retired': 0,
        'invalid': 0,
    }

    for row in rows:
        id_, instrument, orb_time, rr, stored_status, expected_r, sample_size = row

        is_consistent, derived, message = check_status_consistency(
            stored_status, expected_r, sample_size
        )

        if stored_status == 'RETIRED':
            results['retired'] += 1
            results['consistent'] += 1
        elif is_consistent:
            results['consistent'] += 1
        else:
            results['mismatches'].append({
                'id': id_,
                'instrument': instrument,
                'orb_time': orb_time,
                'rr': rr,
                'stored': stored_status,
                'derived': derived,
                'expected_r': expected_r,
                'sample_size': sample_size,
                'message': message,
            })

    return results


def main():
    strict = '--strict' in sys.argv

    print("=" * 70)
    print("CI GUARD: Status Derivation Consistency Check")
    print("=" * 70)
    print()
    print("Rule: Status MUST be derived from expected_r and sample_size")
    print()
    print(f"Thresholds:")
    print(f"  MIN_EXPECTED_R = {MIN_EXPECTED_R}")
    print(f"  MIN_SAMPLE_SIZE = {MIN_SAMPLE_SIZE}")
    print()
    print(f"Mode: {'STRICT (will fail on mismatch)' if strict else 'WARNING (advisory)'}")
    print()

    try:
        results = check_validated_setups()
    except FileNotFoundError as e:
        print(f"[SKIP] {e}")
        return 0
    except Exception as e:
        print(f"[ERROR] {e}")
        return 1

    print(f"Rows checked: {results['total']}")
    print(f"Consistent: {results['consistent']}")
    print(f"Retired (excluded): {results['retired']}")
    print()

    if results['mismatches']:
        print("=" * 70)
        print(f"{'FAILED' if strict else 'WARNING'}: {len(results['mismatches'])} status mismatch(es)")
        print("=" * 70)
        print()

        for m in results['mismatches']:
            print(f"ID {m['id']}: {m['instrument']} {m['orb_time']} RR={m['rr']}")
            print(f"  Stored: {m['stored']}")
            print(f"  Derived: {m['derived']}")
            print(f"  expected_r: {m['expected_r']}, sample_size: {m['sample_size']}")
            print()

        print("=" * 70)
        print("Status derivation rule:")
        print(f"  ACTIVE = expected_r >= {MIN_EXPECTED_R} AND sample_size >= {MIN_SAMPLE_SIZE}")
        print(f"  REJECTED = expected_r < {MIN_EXPECTED_R} OR sample_size < {MIN_SAMPLE_SIZE}")
        print()
        print("Fix: Update status column to match derived value, or fix underlying metrics.")
        print("See: docs/STATUS_DERIVATION_SSOT.md")
        print("=" * 70)

        if strict:
            return 1
        else:
            print()
            print("Run with --strict to fail on mismatches.")
            return 0

    print("=" * 70)
    print("PASSED: All status values match derivation")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
