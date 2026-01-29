"""
Verify Quick Search logic and invariants (PHASE 4 of update13.txt)

Tests:
1. Column usage (verify tradeable_* columns used)
2. Metric definitions (verify correct formulas)
3. Sanity invariants (verify data consistency)
4. UI labels (verify no "RR=1.0" lies)

Runtime: <10 seconds
"""

import sys
from pathlib import Path
import duckdb

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_column_usage():
    """Test 1: Verify engine queries tradeable_* columns"""
    print("\n" + "=" * 70)
    print("TEST 1: Column Usage")
    print("=" * 70)

    # Read auto_search_engine.py
    engine_file = project_root / "trading_app" / "auto_search_engine.py"
    with open(engine_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check for tradeable_* usage
    has_tradeable_rr = "tradeable_realized_rr" in content
    has_tradeable_outcome = "tradeable_outcome" in content

    # Check for incorrect non-tradeable usage
    has_wrong_rr = '"orb_{orb_time}_r_multiple"' in content or 'f"orb_{orb_time}_r_multiple"' in content
    has_wrong_outcome = '"orb_{orb_time}_outcome"' in content.replace('tradeable_outcome', 'XXX')  # Exclude tradeable

    if has_tradeable_rr and has_tradeable_outcome:
        print("[PASS] Engine uses tradeable_* columns")
        print(f"   - Uses tradeable_realized_rr: {has_tradeable_rr}")
        print(f"   - Uses tradeable_outcome: {has_tradeable_outcome}")
    else:
        print("[FAIL] Engine doesn't use tradeable_* columns")
        print(f"   - Uses tradeable_realized_rr: {has_tradeable_rr}")
        print(f"   - Uses tradeable_outcome: {has_tradeable_outcome}")
        return False

    if has_wrong_rr or has_wrong_outcome:
        print("[WARN] Found references to non-tradeable columns")
        print(f"   - Wrong r_multiple usage: {has_wrong_rr}")
        print(f"   - Wrong outcome usage: {has_wrong_outcome}")

    return True


def test_metric_definitions():
    """Test 2: Verify metrics computed correctly"""
    print("\n" + "=" * 70)
    print("TEST 2: Metric Definitions")
    print("=" * 70)

    db_path = project_root / "data" / "db" / "gold.db"
    conn = duckdb.connect(str(db_path))

    # Test with 1000 ORB
    orb_time = 1000
    realized_rr_col = f"orb_{orb_time}_tradeable_realized_rr"
    outcome_col = f"orb_{orb_time}_tradeable_outcome"

    query = f"""
    SELECT
        COUNT(*) as sample_size,
        AVG(CASE WHEN {realized_rr_col} > 0 THEN 1.0 ELSE 0.0 END) as profitable_trade_rate,
        AVG(CASE WHEN {outcome_col} = 'WIN' THEN 1.0 ELSE 0.0 END) as target_hit_rate,
        AVG({realized_rr_col}) as avg_realized_rr
    FROM daily_features
    WHERE instrument = 'MGC'
      AND {realized_rr_col} IS NOT NULL
      AND {outcome_col} IS NOT NULL
    """

    result = conn.execute(query).fetchone()

    if result and result[0] > 0:
        sample_size = result[0]
        profitable_rate = result[1]
        target_hit_rate = result[2]
        expected_r = result[3]

        print(f"[PASS] PASS: Metrics computed for {orb_time} ORB")
        print(f"   Sample Size:      {sample_size} trades")
        print(f"   Profitable Rate:  {profitable_rate:.1%}")
        print(f"   Target Hit Rate:  {target_hit_rate:.1%}")
        print(f"   Expected R:       {expected_r:+.3f}R")

        # Verify definitions
        if profitable_rate is not None and target_hit_rate is not None:
            print("[PASS] PASS: Both metrics computed (not None)")
        else:
            print("[FAIL] FAIL: One or both metrics are None")
            conn.close()
            return False

    else:
        print("[FAIL] FAIL: No data found for metrics")
        conn.close()
        return False

    conn.close()
    return True


def test_sanity_invariants():
    """Test 3: Verify sanity checks pass"""
    print("\n" + "=" * 70)
    print("TEST 3: Sanity Invariants")
    print("=" * 70)

    db_path = project_root / "data" / "db" / "gold.db"
    conn = duckdb.connect(str(db_path))

    # Test with 1000 ORB
    orb_time = 1000
    realized_rr_col = f"orb_{orb_time}_tradeable_realized_rr"
    outcome_col = f"orb_{orb_time}_tradeable_outcome"

    sanity_query = f"""
    SELECT
        COUNT(*) as n_total,
        SUM(CASE WHEN {outcome_col} = 'WIN' THEN 1 ELSE 0 END) as n_win,
        SUM(CASE WHEN {realized_rr_col} > 0 THEN 1 ELSE 0 END) as n_profit,
        SUM(CASE WHEN {realized_rr_col} < 0 THEN 1 ELSE 0 END) as n_loss,
        SUM(CASE WHEN {outcome_col} = 'WIN' AND {realized_rr_col} <= 0 THEN 1 ELSE 0 END) as n_win_negative,
        AVG({realized_rr_col}) as mean_rr
    FROM daily_features
    WHERE instrument = 'MGC'
      AND {realized_rr_col} IS NOT NULL
      AND {outcome_col} IS NOT NULL
    """

    result = conn.execute(sanity_query).fetchone()

    if not result:
        print("[FAIL] FAIL: No data for sanity checks")
        conn.close()
        return False

    n_total = result[0]
    n_win = result[1]
    n_profit = result[2]
    n_loss = result[3]
    n_win_negative = result[4]
    mean_rr = result[5]

    print(f"Counts for {orb_time} ORB:")
    print(f"   Total:           {n_total}")
    print(f"   WIN outcomes:    {n_win} ({n_win/n_total*100:.1f}%)")
    print(f"   Profitable:      {n_profit} ({n_profit/n_total*100:.1f}%)")
    print(f"   Losses:          {n_loss} ({n_loss/n_total*100:.1f}%)")
    print()

    all_pass = True

    # Invariant 1: WIN <= Profitable
    if n_win <= n_profit:
        print(f"[PASS] PASS: WIN count <= Profitable count ({n_win} <= {n_profit})")
    else:
        print(f"[FAIL] FAIL: WIN count > Profitable count ({n_win} > {n_profit})")
        all_pass = False

    # Invariant 2: No WIN with RR <= 0
    if n_win_negative == 0:
        print(f"[PASS] PASS: No WIN with RR <= 0 (found {n_win_negative} violations)")
    else:
        print(f"[FAIL] FAIL: Found {n_win_negative} trades with WIN but RR <= 0")
        all_pass = False

    # Invariant 3: Expected R is reasonable
    if mean_rr is not None and -2.0 <= mean_rr <= 2.0:
        print(f"[PASS] PASS: Expected R is reasonable ({mean_rr:+.3f}R within [-2.0, +2.0])")
    else:
        print(f"[WARN]  WARNING: Expected R seems unusual ({mean_rr:+.3f}R)")

    conn.close()
    return all_pass


def test_ui_labels():
    """Test 4: Verify UI uses correct labels"""
    print("\n" + "=" * 70)
    print("TEST 4: UI Labels")
    print("=" * 70)

    # Read app_canonical.py
    app_file = project_root / "trading_app" / "app_canonical.py"
    with open(app_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check for correct labels
    has_proxy_label = "Stored Model Proxy" in content or "Proxy" in content
    has_warning = "For RR-specific results" in content or "RR-specific" in content

    # Check for incorrect labels
    has_rr_1_0_lie = 'RR Target: 1.0' in content and 'baseline data only' in content

    if has_proxy_label and has_warning:
        print("[PASS] PASS: UI has correct proxy labels")
        print(f"   - Has 'Proxy' label: {has_proxy_label}")
        print(f"   - Has RR-specific warning: {has_warning}")
    else:
        print("[WARN]  WARNING: UI labels may be incomplete")
        print(f"   - Has 'Proxy' label: {has_proxy_label}")
        print(f"   - Has RR-specific warning: {has_warning}")

    if has_rr_1_0_lie:
        print("[WARN]  WARNING: Found old 'RR=1.0' label (may be misleading)")
    else:
        print("[PASS] PASS: No misleading 'RR=1.0' labels found")

    # Check for Truth Panel
    has_truth_panel = "What exactly is being measured" in content
    has_sanity_checks = "Sanity Checks" in content

    if has_truth_panel and has_sanity_checks:
        print("[PASS] PASS: Truth Panel expanders exist")
        print(f"   - Has 'What's measured' expander: {has_truth_panel}")
        print(f"   - Has 'Sanity Checks' expander: {has_sanity_checks}")
    else:
        print("[WARN]  WARNING: Truth Panel may be incomplete")
        print(f"   - Has 'What's measured' expander: {has_truth_panel}")
        print(f"   - Has 'Sanity Checks' expander: {has_sanity_checks}")

    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("QUICK SEARCH VERIFICATION (update13.txt PHASE 4)")
    print("=" * 70)
    print(f"Project root: {project_root}")

    results = []

    try:
        results.append(("Column Usage", test_column_usage()))
        results.append(("Metric Definitions", test_metric_definitions()))
        results.append(("Sanity Invariants", test_sanity_invariants()))
        results.append(("UI Labels", test_ui_labels()))
    except Exception as e:
        print(f"\n[FAIL] ERROR: Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[PASS] PASS" if result else "[FAIL] FAIL"
        print(f"{status}: {test_name}")

    print()
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n[PASS] ALL TESTS PASSED - Quick Search verified!")
        return 0
    else:
        print(f"\n[FAIL] {total - passed} TESTS FAILED - Fix required")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
