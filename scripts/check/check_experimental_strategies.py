"""
Validation Script for experimental_strategies Table

Checks for data integrity issues before they hit production:
- Sanity checks on expected_r values (no typos like 2.5R instead of 0.25R)
- Win rate bounds (20-90%)
- Sample size minimums (>= 15 trades)
- Valid filter types
- Valid day_of_week values

Usage:
    python scripts/check/check_experimental_strategies.py

Returns:
    Exit code 0 if all checks pass
    Exit code 1 if any validation fails
"""

import duckdb
import sys
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent.parent.parent / "data" / "db" / "gold.db"

# Validation thresholds
EXPECTED_R_MIN = -1.0  # Minimum expected R (sanity check)
EXPECTED_R_MAX = 2.0   # Maximum expected R (catches typos like 2.5R)
WIN_RATE_MIN = 0.20    # Minimum win rate (20%)
WIN_RATE_MAX = 0.90    # Maximum win rate (90%)
SAMPLE_SIZE_MIN = 15   # Minimum sample size for statistical validity

VALID_FILTER_TYPES = [
    'DAY_OF_WEEK',
    'SESSION_CONTEXT',
    'VOLATILITY_REGIME',
    'COMBINED',
    'MULTI_DAY'
]

VALID_DAYS_OF_WEEK = [
    'Monday',
    'Tuesday',
    'Wednesday',
    'Thursday',
    'Friday',
    None  # Allow NULL for non-day-of-week filters
]


def validate_experimental_strategies():
    """Validate all ACTIVE experimental strategies"""
    con = duckdb.connect(str(DB_PATH))
    issues = []

    try:
        strategies = con.execute("""
            SELECT
                id, instrument, orb_time, rr, filter_type, day_of_week,
                win_rate, expected_r, realized_expectancy, sample_size
            FROM experimental_strategies
            WHERE status = 'ACTIVE'
        """).fetchall()

        if not strategies:
            print("WARNING: No ACTIVE experimental strategies found")
            return (True, [])

        print(f"Validating {len(strategies)} ACTIVE strategies...")
        print("="*70)

        for strat in strategies:
            strat_id, instrument, orb_time, rr, filter_type, day_of_week, win_rate, expected_r, realized_expectancy, sample_size = strat
            strat_name = f"{instrument} {orb_time} RR={rr} {filter_type}"

            # Check expected_r bounds
            if expected_r and (expected_r < EXPECTED_R_MIN or expected_r > EXPECTED_R_MAX):
                issues.append(f"ERROR {strat_name} (ID {strat_id}): expected_r={expected_r:.3f}R outside [{EXPECTED_R_MIN}, {EXPECTED_R_MAX}]")

            # Check win rate bounds
            if win_rate and (win_rate < WIN_RATE_MIN or win_rate > WIN_RATE_MAX):
                issues.append(f"ERROR {strat_name} (ID {strat_id}): win_rate={win_rate:.1%} outside [{WIN_RATE_MIN:.0%}, {WIN_RATE_MAX:.0%}]")

            # Check sample size
            if sample_size and sample_size < SAMPLE_SIZE_MIN:
                issues.append(f"WARNING {strat_name} (ID {strat_id}): sample_size={sample_size} < {SAMPLE_SIZE_MIN}")

            # Check filter type
            if filter_type not in VALID_FILTER_TYPES:
                issues.append(f"ERROR {strat_name} (ID {strat_id}): invalid filter_type '{filter_type}'")

            # Check day_of_week for DAY_OF_WEEK filters
            if filter_type == 'DAY_OF_WEEK' and day_of_week not in VALID_DAYS_OF_WEEK:
                issues.append(f"ERROR {strat_name} (ID {strat_id}): invalid day_of_week '{day_of_week}'")

        print("="*70)
        if issues:
            print(f"\nFound {len(issues)} issues:\n")
            for issue in issues:
                print(issue)
            
            error_count = len([i for i in issues if i.startswith('ERROR')])
            if error_count > 0:
                print(f"\nVALIDATION FAILED - {error_count} critical errors")
                return (False, issues)
            else:
                print(f"\nVALIDATION PASSED (with warnings)")
                return (True, issues)
        else:
            print(f"All checks passed - {len(strategies)} strategies validated")
            return (True, [])

    except Exception as e:
        print(f"ERROR: {e}")
        return (False, [str(e)])
    finally:
        con.close()


if __name__ == "__main__":
    passed, _ = validate_experimental_strategies()
    sys.exit(0 if passed else 1)
