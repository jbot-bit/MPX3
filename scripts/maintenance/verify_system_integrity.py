#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Full System Integrity Verification (PHASE 4)
Comprehensive "human brain" logic sweep across all layers

Usage:
    python scripts/maintenance/verify_system_integrity.py

Exit codes:
    0 = All integrity checks pass
    1 = Integrity violations found
"""

import sys
import io
import os
from pathlib import Path
from datetime import datetime, timedelta
import duckdb
from zoneinfo import ZoneInfo

# Fix Unicode output on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def verify_ingestion_layer(db_path: str, symbol: str = 'MGC'):
    """
    Verify ingestion layer integrity.

    Checks:
    - No duplicates (from PHASE 3)
    - No gaps in recent data
    - WAL/connection safety in scripts
    """
    print("\n" + "="*60)
    print("1. INGESTION LAYER")
    print("="*60)

    conn = None
    all_pass = True

    try:
        conn = duckdb.connect(db_path, read_only=True)

        # Check duplicates
        dupes = conn.execute("""
            SELECT COUNT(*) FROM (
                SELECT ts_utc, COUNT(*) as cnt
                FROM bars_1m
                WHERE symbol = ?
                GROUP BY ts_utc
                HAVING COUNT(*) > 1
            )
        """, [symbol]).fetchone()[0]

        if dupes > 0:
            print(f"  ❌ FAIL: {dupes} duplicate timestamps found")
            all_pass = False
        else:
            print("  ✅ PASS: No duplicate timestamps")

        # Check recent data completeness (last 3 days)
        tz_brisbane = ZoneInfo("Australia/Brisbane")
        cutoff = datetime.now(tz_brisbane).date() - timedelta(days=3)

        daily_bars = conn.execute("""
            SELECT
                DATE_TRUNC('day', ts_utc AT TIME ZONE 'Australia/Brisbane') as day,
                COUNT(*) as bars
            FROM bars_1m
            WHERE symbol = ?
            AND DATE_TRUNC('day', ts_utc AT TIME ZONE 'Australia/Brisbane') >= ?
            GROUP BY day
            ORDER BY day DESC
        """, [symbol, cutoff]).fetchall()

        issues = []
        for day, bars in daily_bars:
            # Weekdays should have ~1000+ bars, weekends can be light
            if bars < 100 and day.weekday() < 5:
                issues.append(f"{day}: only {bars} bars")

        if issues:
            print(f"  ⚠️  WARNING: {len(issues)} days with low bar counts")
            for issue in issues:
                print(f"     - {issue}")
        else:
            print(f"  ✅ PASS: Recent data completeness OK ({len(daily_bars)} days)")

        # Check WAL/connection safety (code inspection - manual for now)
        print("  ℹ️  INFO: WAL/connection safety requires code inspection")
        print("     - Verify try/finally patterns in backfill scripts")

    finally:
        if conn:
            conn.close()

    return all_pass


def verify_feature_layer(db_path: str, symbol: str = 'MGC'):
    """
    Verify feature layer integrity.

    Checks:
    - daily_features tracks bars_1m (within 0-1 day lag)
    - ORB columns exist and are populated
    """
    print("\n" + "="*60)
    print("2. FEATURE LAYER")
    print("="*60)

    conn = None
    all_pass = True

    try:
        conn = duckdb.connect(db_path, read_only=True)

        # Get latest timestamps
        latest_bar_ts = conn.execute("""
            SELECT MAX(ts_utc) FROM bars_1m WHERE symbol = ?
        """, [symbol]).fetchone()[0]

        latest_feat_date = conn.execute("""
            SELECT MAX(date_local) FROM daily_features WHERE instrument = ?
        """, [symbol]).fetchone()[0]

        # Convert bar timestamp to Brisbane date
        from zoneinfo import ZoneInfo
        tz_brisbane = ZoneInfo("Australia/Brisbane")
        bar_date = latest_bar_ts.astimezone(tz_brisbane).date()

        # Expected: features should be within 0-2 days of bars
        # (0 = same day, 1 = yesterday, 2 = day before)
        lag_days = (bar_date - latest_feat_date).days if latest_feat_date else 999

        if lag_days <= 2:
            print(f"  ✅ PASS: daily_features lag = {lag_days} days (acceptable)")
            print(f"     Latest bars: {bar_date}")
            print(f"     Latest features: {latest_feat_date}")
        else:
            print(f"  ❌ FAIL: daily_features lag = {lag_days} days (too old)")
            print(f"     Latest bars: {bar_date}")
            print(f"     Latest features: {latest_feat_date}")
            all_pass = False

        # Check ORB columns exist and are populated
        orb_times = ['0900', '1000', '1100', '1800', '2300', '0030']

        for orb_time in orb_times:
            # Check if columns exist (by trying to query them)
            try:
                result = conn.execute(f"""
                    SELECT
                        COUNT(*) as total,
                        COUNT(orb_{orb_time}_high) as populated
                    FROM daily_features
                    WHERE instrument = ?
                    AND date_local >= ?
                """, [symbol, latest_feat_date - timedelta(days=7) if latest_feat_date else None]).fetchone()

                total, populated = result
                pct = (populated / total * 100) if total > 0 else 0

                if pct >= 80:
                    print(f"  ✅ PASS: orb_{orb_time} populated {populated}/{total} ({pct:.1f}%)")
                else:
                    print(f"  ⚠️  WARNING: orb_{orb_time} sparse {populated}/{total} ({pct:.1f}%)")

            except Exception as e:
                print(f"  ❌ FAIL: orb_{orb_time} columns missing or invalid")
                all_pass = False

    finally:
        if conn:
            conn.close()

    return all_pass


def verify_validation_layer(db_path: str, symbol: str = 'MGC'):
    """
    Verify validation/truth layer integrity.

    Checks:
    - ACTIVE strategies have sufficient sample size
    - ACTIVE strategies have positive expected_r
    - ACTIVE strategies have backing daily_features coverage
    """
    print("\n" + "="*60)
    print("3. VALIDATION/TRUTH LAYER")
    print("="*60)

    conn = None
    all_pass = True

    try:
        conn = duckdb.connect(db_path, read_only=True)

        # Get ACTIVE strategies for MGC
        active_strategies = conn.execute("""
            SELECT
                id,
                instrument,
                orb_time,
                rr,
                sl_mode,
                orb_size_filter,
                win_rate,
                expected_r,
                sample_size
            FROM validated_setups
            WHERE instrument = ?
            AND status = 'ACTIVE'
            ORDER BY orb_time, rr
        """, [symbol]).fetchall()

        if not active_strategies:
            print(f"  ⚠️  WARNING: No ACTIVE strategies found for {symbol}")
            return True  # Not a failure, just no strategies yet

        print(f"  ℹ️  INFO: Found {len(active_strategies)} ACTIVE strategies for {symbol}")

        # Verify each strategy
        issues = []

        for strat in active_strategies:
            strat_id, instrument, orb_time, rr, sl_mode, filt, wr, exp_r, sample = strat

            # Check sample size (minimum 30 trades)
            if sample < 30:
                issues.append(f"Strategy {strat_id} ({orb_time} RR={rr}): sample={sample} < 30")

            # Check expected_r threshold (minimum 0.15R)
            if exp_r < 0.15:
                issues.append(f"Strategy {strat_id} ({orb_time} RR={rr}): expected_r={exp_r:.3f} < 0.15")

            # Check daily_features coverage
            # For a strategy to be valid, we need sufficient historical data
            min_date_required = datetime.now().date() - timedelta(days=365)  # 1 year minimum

            coverage = conn.execute("""
                SELECT COUNT(*) FROM daily_features
                WHERE instrument = ?
                AND date_local >= ?
            """, [symbol, min_date_required]).fetchone()[0]

            if coverage < 200:  # ~200 trading days per year
                issues.append(f"Strategy {strat_id} ({orb_time} RR={rr}): only {coverage} days of data (need 200+)")

        if issues:
            print(f"  ❌ FAIL: {len(issues)} strategy validation issues:")
            for issue in issues[:5]:  # Show first 5
                print(f"     - {issue}")
            all_pass = False
        else:
            print(f"  ✅ PASS: All {len(active_strategies)} ACTIVE strategies validated")

    finally:
        if conn:
            conn.close()

    return all_pass


def verify_app_layer(db_path: str):
    """
    Verify app layer integrity.

    Checks:
    - app_canonical.py exists
    - config_generator.py exists
    - Apps distinguish ACTIVE vs non-ACTIVE strategies (code grep)
    """
    print("\n" + "="*60)
    print("4. APP LAYER")
    print("="*60)

    all_pass = True

    # Check app_canonical.py
    app_canonical_path = Path("trading_app/app_canonical.py")
    if app_canonical_path.exists():
        print("  ✅ PASS: app_canonical.py exists")

        # Check for ACTIVE status filtering (grep for "status = 'ACTIVE'" or similar)
        with open(app_canonical_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if "status = 'ACTIVE'" in content or 'status="ACTIVE"' in content:
                print("  ✅ PASS: app_canonical filters by status='ACTIVE'")
            else:
                print("  ⚠️  WARNING: app_canonical may not filter by ACTIVE status")
    else:
        print("  ❌ FAIL: app_canonical.py not found")
        all_pass = False

    # Check config_generator.py
    config_gen_path = Path("tools/config_generator.py")
    if config_gen_path.exists():
        print("  ✅ PASS: config_generator.py exists")

        # Check for ACTIVE filtering
        with open(config_gen_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if "status = 'ACTIVE'" in content or 'status="ACTIVE"' in content or 'STATUS.ACTIVE' in content:
                print("  ✅ PASS: config_generator filters by ACTIVE status")
            else:
                print("  ⚠️  WARNING: config_generator may not filter by ACTIVE status")
    else:
        print("  ⚠️  WARNING: config_generator.py not found")

    return all_pass


def print_system_state(db_path: str, symbol: str = 'MGC'):
    """
    Print comprehensive system state report.
    """
    print("\n" + "="*60)
    print("5. SYSTEM STATE REPORT")
    print("="*60)

    conn = None

    try:
        conn = duckdb.connect(db_path, read_only=True)

        # Latest bars timestamp
        latest_bar_ts = conn.execute("""
            SELECT MAX(ts_utc) FROM bars_1m WHERE symbol = ?
        """, [symbol]).fetchone()[0]

        # Convert to Brisbane
        from zoneinfo import ZoneInfo
        tz_brisbane = ZoneInfo("Australia/Brisbane")
        latest_bar_brisbane = latest_bar_ts.astimezone(tz_brisbane)

        print(f"\n📊 Data Currency:")
        print(f"   Latest bars_1m: {latest_bar_ts} UTC")
        print(f"                   {latest_bar_brisbane} Brisbane")

        # Latest daily_features
        latest_feat_date = conn.execute("""
            SELECT MAX(date_local) FROM daily_features WHERE instrument = ?
        """, [symbol]).fetchone()[0]

        print(f"   Latest daily_features: {latest_feat_date}")

        # ACTIVE strategies
        active_strategies = conn.execute("""
            SELECT orb_time, rr, expected_r, sample_size
            FROM validated_setups
            WHERE instrument = ?
            AND status = 'ACTIVE'
            ORDER BY orb_time, rr
        """, [symbol]).fetchall()

        print(f"\n📈 Active Strategies ({len(active_strategies)} total):")
        if active_strategies:
            for orb_time, rr, exp_r, sample in active_strategies:
                print(f"   - {orb_time} RR={rr}: ExpR={exp_r:.3f}, N={sample}")
        else:
            print("   (none)")

        # Database size
        db_size_mb = Path(db_path).stat().st_size / (1024**2)
        bar_count = conn.execute("""
            SELECT COUNT(*) FROM bars_1m WHERE symbol = ?
        """, [symbol]).fetchone()[0]

        print(f"\n💾 Database:")
        print(f"   Path: {db_path}")
        print(f"   Size: {db_size_mb:.1f} MB")
        print(f"   Bars: {bar_count:,}")

    finally:
        if conn:
            conn.close()


def main():
    """Main execution flow."""
    try:
        # Change to project root
        project_root = Path(__file__).parent.parent.parent
        os.chdir(project_root)

        db_path = "data/db/gold.db"
        symbol = "MGC"

        print("="*60)
        print("SYSTEM INTEGRITY VERIFICATION (PHASE 4)")
        print("="*60)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Working directory: {os.getcwd()}")
        print(f"Database: {db_path}")
        print(f"Symbol: {symbol}")
        print("="*60)

        all_pass = True

        # Run all verification checks
        if not verify_ingestion_layer(db_path, symbol):
            all_pass = False

        if not verify_feature_layer(db_path, symbol):
            all_pass = False

        if not verify_validation_layer(db_path, symbol):
            all_pass = False

        if not verify_app_layer(db_path):
            all_pass = False

        # Print system state (always)
        print_system_state(db_path, symbol)

        # Final verdict
        print("\n" + "="*60)
        if all_pass:
            print("✅ ALL INTEGRITY CHECKS PASSED")
            print("="*60)
            return 0
        else:
            print("❌ INTEGRITY VIOLATIONS FOUND")
            print("="*60)
            print("\nAction required: Fix violations before production use")
            return 1

    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
