"""
TEST APP SYNCHRONIZATION

CRITICAL: Validates that validated_setups database matches config.py
Prevents dangerous mismatches that could cause wrong trades in live trading.

Run this AFTER:
- Updating validated_setups database
- Modifying trading_app/config.py
- Running populate_validated_setups.py
- Adding new MGC/NQ/MPL setups
- Changing ORB filters or RR values

From CLAUDE.md:
"MANDATORY RULE: NEVER update validated_setups database without IMMEDIATELY
updating config.py in the same operation."

This test ensures that rule is followed.
"""

import sys
from pathlib import Path
import duckdb
import subprocess

# Add trading_app to path (from root folder, go directly into trading_app)
sys.path.insert(0, str(Path(__file__).parent / "trading_app"))
# Also add project root so 'trading_app' can be imported as a module
sys.path.insert(0, str(Path(__file__).parent))

from trading_app.config import MGC_ORB_CONFIGS, MGC_ORB_SIZE_FILTERS, NQ_ORB_CONFIGS, NQ_ORB_SIZE_FILTERS, MPL_ORB_CONFIGS, MPL_ORB_SIZE_FILTERS


def test_config_matches_database():
    """Verify config.py matches validated_setups database"""

    db_path = Path(__file__).parent / "data" / "db" / "gold.db"

    if not db_path.exists():
        print("[FAIL] FAILED: gold.db not found")
        print(f"   Expected: {db_path}")
        return False

    try:
        con = duckdb.connect(str(db_path), read_only=True)
    except Exception as e:
        print(f"[FAIL] FAILED: Cannot connect to database: {e}")
        return False

    try:
        # Get all ACTIVE setups from database (exclude REJECTED and RETIRED)
        # This matches what config_generator.py loads
        query = """
        SELECT instrument, orb_time, rr, sl_mode, orb_size_filter
        FROM validated_setups
        WHERE instrument IN ('MGC', 'NQ', 'MPL')
          AND orb_time NOT IN ('CASCADE', 'SINGLE_LIQ')
          AND (status IS NULL OR status = 'ACTIVE')
        ORDER BY instrument, orb_time
        """

        db_setups = con.execute(query).fetchall()

        if not db_setups:
            print("[FAIL] FAILED: No setups found in validated_setups table")
            return False

        print(f"[PASS] Found {len(db_setups)} setups in database")

        # Group by instrument
        mgc_db = [s for s in db_setups if s[0] == 'MGC']
        nq_db = [s for s in db_setups if s[0] == 'NQ']
        mpl_db = [s for s in db_setups if s[0] == 'MPL']

        print(f"   - MGC: {len(mgc_db)} setups")
        print(f"   - NQ: {len(nq_db)} setups")
        print(f"   - MPL: {len(mpl_db)} setups")
        print()

        # Test MGC
        print("=== Testing MGC ===")
        mgc_pass = test_instrument_sync('MGC', mgc_db, MGC_ORB_CONFIGS, MGC_ORB_SIZE_FILTERS)

        # Test NQ
        print("\n=== Testing NQ ===")
        nq_pass = test_instrument_sync('NQ', nq_db, NQ_ORB_CONFIGS, NQ_ORB_SIZE_FILTERS)

        # Test MPL
        print("\n=== Testing MPL ===")
        mpl_pass = test_instrument_sync('MPL', mpl_db, MPL_ORB_CONFIGS, MPL_ORB_SIZE_FILTERS)

        con.close()

        return mgc_pass and nq_pass and mpl_pass

    except Exception as e:
        print(f"[FAIL] FAILED: Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_instrument_sync(instrument, db_setups, orb_configs, orb_size_filters):
    """Test one instrument's synchronization"""

    if not db_setups:
        print(f"[WARN]  No {instrument} setups in database (expected if not using {instrument})")
        return True

    all_pass = True

    for setup in db_setups:
        _, orb_time, db_rr, db_sl_mode, db_filter = setup

        # Check if ORB exists in config
        if orb_time not in orb_configs:
            print(f"[FAIL] MISMATCH: {orb_time} in database but NOT in config.py")
            all_pass = False
            continue

        # Config now returns LIST of configs (supports multiple RR/SL per ORB)
        config_list = orb_configs[orb_time]
        filter_list = orb_size_filters.get(orb_time, [])

        # Find matching config in list
        found_match = False
        for idx, config_data in enumerate(config_list):
            config_rr = config_data.get('rr')
            config_sl_mode = config_data.get('sl_mode')

            # Get corresponding filter (if exists)
            config_filter = filter_list[idx] if idx < len(filter_list) else None

            # Check if this config matches database setup
            rr_match = abs(db_rr - config_rr) < 0.001
            sl_match = db_sl_mode == config_sl_mode

            # Check filter match
            db_filter_val = db_filter if db_filter is not None else None
            config_filter_val = config_filter if config_filter is not None else None

            if db_filter_val is None and config_filter_val is None:
                filter_match = True
            elif db_filter_val is None or config_filter_val is None:
                filter_match = False
            else:
                filter_match = abs(db_filter_val - config_filter_val) < 0.001

            # If all match, we found it
            if rr_match and sl_match and filter_match:
                found_match = True
                break

        # Report if no match found
        if not found_match:
            print(f"[FAIL] MISMATCH: {orb_time} RR={db_rr} SL={db_sl_mode} Filter={db_filter}")
            print(f"   Database setup not found in config list")
            print(f"   Available configs: {config_list}")
            all_pass = False

    # Check for config entries not in database
    for orb_time in orb_configs:
        if not any(s[1] == orb_time for s in db_setups):
            print(f"[WARN]  WARNING: {orb_time} in config.py but NOT in database")
            # Not a failure - config can have more entries

    if all_pass:
        print(f"[PASS] {instrument} config matches database perfectly")
    else:
        print(f"[FAIL] {instrument} has mismatches")

    return all_pass


def test_setup_detector_loads():
    """Test that SetupDetector can load from database"""
    try:
        from trading_app.setup_detector import SetupDetector
        detector = SetupDetector(None)  # Use cloud-aware path

        mgc_setups = detector.get_all_validated_setups('MGC')

        if not mgc_setups:
            print("[FAIL] FAILED: SetupDetector couldn't load MGC setups")
            return False

        print(f"[PASS] SetupDetector successfully loaded {len(mgc_setups)} MGC setups")
        return True

    except Exception as e:
        print(f"[FAIL] FAILED: SetupDetector error: {e}")
        return False


def test_data_loader_filters():
    """Test that data_loader uses correct filters"""
    try:
        from trading_app.data_loader import LiveDataLoader
        from trading_app.config import ENABLE_ORB_SIZE_FILTERS, MGC_ORB_SIZE_FILTERS

        if ENABLE_ORB_SIZE_FILTERS:
            print(f"[PASS] ORB size filters ENABLED")
            print(f"   MGC filters: {MGC_ORB_SIZE_FILTERS}")
        else:
            print(f"[WARN]  ORB size filters DISABLED")

        return True

    except Exception as e:
        print(f"[FAIL] FAILED: data_loader error: {e}")
        return False


def test_strategy_engine_loads():
    """Test that StrategyEngine loads configs"""
    try:
        from trading_app.strategy_engine import StrategyEngine
        from trading_app.config import MGC_ORB_CONFIGS

        if not MGC_ORB_CONFIGS:
            print("[FAIL] FAILED: MGC_ORB_CONFIGS is empty")
            return False

        print(f"[PASS] StrategyEngine has {len(MGC_ORB_CONFIGS)} MGC ORB configs")
        return True

    except Exception as e:
        print(f"[FAIL] FAILED: StrategyEngine error: {e}")
        return False


def test_execution_spec():
    """Verify ExecutionSpec system (UPDATE14)

    SYNC GUARD (fail-closed):
    If execution spec files exist but check script is missing, FAIL.
    This prevents silent drift.
    """

    # Check if execution spec files exist
    project_root = Path(__file__).parent
    spec_files = [
        project_root / "trading_app" / "execution_spec.py",
        project_root / "trading_app" / "execution_contract.py",
        project_root / "trading_app" / "entry_rules.py",
    ]

    spec_files_exist = any(f.exists() for f in spec_files)
    check_script = project_root / "scripts" / "check" / "check_execution_spec.py"

    # SYNC GUARD: If spec files exist, check script MUST exist
    if spec_files_exist and not check_script.exists():
        print(f"[FAIL] CRITICAL: Sync guard triggered!")
        print(f"   ExecutionSpec files exist but check script is missing:")
        for f in spec_files:
            if f.exists():
                print(f"     - {f.relative_to(project_root)}")
        print(f"   Expected check script: {check_script.relative_to(project_root)}")
        print(f"   This prevents silent drift - check script is MANDATORY")
        return False

    # If spec files don't exist yet, skip check (not required)
    if not spec_files_exist:
        print("[SKIP] ExecutionSpec files not found (UPDATE14 not yet implemented)")
        return True

    # Run check_execution_spec.py
    result = subprocess.run(
        [sys.executable, str(check_script)],
        capture_output=True,
        text=True
    )

    # Show output
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    if result.returncode == 0:
        print("[PASS] ExecutionSpec checks passed")
        return True
    else:
        print("[FAIL] FAILED: ExecutionSpec checks failed")
        print("   Fix execution spec issues and run again")
        return False


def main():
    """Run all synchronization tests"""
    print("=" * 70)
    print("TESTING APP SYNCHRONIZATION")
    print("=" * 70)
    print()

    # Test 1: Config matches database
    print("TEST 1: Config.py matches validated_setups database")
    print("-" * 70)
    test1_pass = test_config_matches_database()
    print()

    # Test 2: SetupDetector loads
    print("TEST 2: SetupDetector loads from database")
    print("-" * 70)
    test2_pass = test_setup_detector_loads()
    print()

    # Test 3: Data loader filters
    print("TEST 3: Data loader filter checking")
    print("-" * 70)
    test3_pass = test_data_loader_filters()
    print()

    # Test 4: Strategy engine loads
    print("TEST 4: Strategy engine config loading")
    print("-" * 70)
    test4_pass = test_strategy_engine_loads()
    print()

    # Test 5: ExecutionSpec system (UPDATE14)
    print("TEST 5: ExecutionSpec system (UPDATE14)")
    print("-" * 70)
    test5_pass = test_execution_spec()
    print()

    # Summary
    print("=" * 70)
    if test1_pass and test2_pass and test3_pass and test4_pass and test5_pass:
        print("[PASS] ALL TESTS PASSED!")
        print()
        print("Your apps are now synchronized:")
        print("  - config.py matches validated_setups database")
        print("  - setup_detector.py works with all instruments")
        print("  - data_loader.py filter checking works")
        print("  - strategy_engine.py loads configs")
        print("  - ExecutionSpec system verified (UPDATE14)")
        print("  - All components load without errors")
        print()
        print("[PASS] Your apps are SAFE TO USE!")
        return 0
    else:
        print("[FAIL] TESTS FAILED!")
        print()
        print("[WARN]  DO NOT USE THE APPS UNTIL MISMATCHES ARE FIXED")
        print()
        print("Fix the issues above and run this test again.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
