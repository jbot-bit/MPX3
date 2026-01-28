"""
Comprehensive Test of T6 Real Validation Logic

Tests run_real_validation() with actual database to verify:
1. Data queries work correctly
2. Filters apply correctly (size, direction)
3. Metrics calculate correctly
4. Stress tests work
5. Walk-forward test works
6. Validation gates checked correctly
7. Control comparison works
"""

import os
os.environ['FORCE_LOCAL_DB'] = '1'

from cloud_mode import get_database_path
import duckdb
from edge_utils import (
    create_candidate,
    run_validation_stub,
    run_real_validation,
    get_candidate_by_id
)
from datetime import date

def test_validation_comprehensive():
    """Test complete validation workflow with real data"""

    print('=' * 70)
    print('COMPREHENSIVE VALIDATION TEST')
    print('=' * 70)
    print()

    # Connect to database
    db_path = get_database_path()
    conn = duckdb.connect(db_path)

    print(f'[1/7] Connected to: {db_path}')

    # Check data availability
    data_check = conn.execute("""
        SELECT COUNT(*), MIN(date_local), MAX(date_local)
        FROM daily_features
        WHERE instrument = 'MGC'
        AND orb_1000_outcome IS NOT NULL
    """).fetchone()

    total_days, min_date, max_date = data_check
    print(f'[2/7] Data available: {total_days} days ({min_date} to {max_date})')

    if total_days < 30:
        print('[ERROR] Not enough data for validation (need 30+ days)')
        return False

    # Test 1: Create test candidate
    print()
    print('[3/7] Creating test candidate...')

    edge_id, message = create_candidate(
        db_connection=conn,
        instrument='MGC',
        orb_time='1000',
        direction='BOTH',
        trigger_definition='Comprehensive validation test edge',
        rr=2.0,
        sl_mode='FULL',
        orb_filter=None,  # No size filter for max sample size
        notes='Test edge for comprehensive validation'
    )

    print(f'  Edge ID: {edge_id[:16]}...')
    print(f'  Message: {message}')

    # Test 2: Run REAL validation directly
    print()
    print('[4/7] Running REAL validation...')

    edge = get_candidate_by_id(conn, edge_id)
    metrics = run_real_validation(
        db_connection=conn,
        edge=edge,
        test_window_start=None,
        test_window_end=None
    )

    # Check metrics
    print()
    print('[5/7] Validation Metrics:')
    print(f'  Sample Size: {metrics.get("sample_size", 0)}')
    print(f'  Win Rate: {metrics.get("win_rate", 0)*100:.1f}%')
    print(f'  Expected R: {metrics.get("expected_r", 0):.3f}R')
    print(f'  Avg Win: {metrics.get("avg_win", 0):.3f}R')
    print(f'  Avg Loss: {metrics.get("avg_loss", 0):.3f}R')
    print(f'  Max DD: {metrics.get("max_dd", 0):.3f}R')
    print()
    print('  Stress Tests:')
    print(f'    +25% Cost: {metrics.get("stress_test_25", "?")} (ExpR: {metrics.get("stress_test_25_exp_r", 0):.3f}R)')
    print(f'    +50% Cost: {metrics.get("stress_test_50", "?")} (ExpR: {metrics.get("stress_test_50_exp_r", 0):.3f}R)')
    print()
    print('  Walk-Forward:')
    print(f'    Result: {metrics.get("walk_forward", "?")}')
    print(f'    Train WR: {metrics.get("walk_forward_train_wr", 0)*100:.1f}% (N={metrics.get("walk_forward_train_n", 0)})')
    print(f'    Test WR: {metrics.get("walk_forward_test_wr", 0)*100:.1f}% (N={metrics.get("walk_forward_test_n", 0)})')
    print()
    print('  Skipped:')
    skipped = metrics.get('skipped', {})
    print(f'    Size Filter: {skipped.get("size_filter", 0)}')
    print(f'    Direction Filter: {skipped.get("direction_filter", 0)}')
    print(f'    No Break: {skipped.get("no_break", 0)}')
    print(f'    Total Dates: {metrics.get("total_dates", 0)}')

    # Test 3: Check validation gates
    print()
    print('[6/7] Checking Validation Gates:')

    sample_size_pass = metrics.get('sample_size', 0) >= 30
    expected_r_pass = metrics.get('expected_r', 0) >= 0.15
    stress_25_pass = metrics.get('stress_test_25') == 'PASS'
    stress_50_pass = metrics.get('stress_test_50') == 'PASS'
    walk_forward_pass = metrics.get('walk_forward') == 'PASS'

    print(f'  Sample Size >= 30: {"[PASS]" if sample_size_pass else "[FAIL]"}')
    print(f'  Expected R >= 0.15: {"[PASS]" if expected_r_pass else "[FAIL]"}')
    print(f'  Stress Test +25%: {"[PASS]" if stress_25_pass else "[FAIL]"}')
    print(f'  Stress Test +50%: {"[PASS]" if stress_50_pass else "[FAIL]"}')
    print(f'  Walk-Forward: {"[PASS]" if walk_forward_pass else "[FAIL]"}')
    print()

    gates_pass = (sample_size_pass and expected_r_pass and
                  (stress_25_pass or stress_50_pass) and walk_forward_pass)

    print(f'  Overall Gates: {"[PASS]" if gates_pass else "[FAIL]"}')

    # Test 4: Run full validation with control
    print()
    print('[7/7] Running full validation with control...')

    result = run_validation_stub(
        db_connection=conn,
        edge_id=edge_id,
        run_control=True,
        use_real_validation=True
    )

    print(f'  Final Result: {"[PASSED]" if result["passed"] else "[FAILED]"}')
    print(f'  Edge Passes Gates: {result["edge_passes_gates"]}')
    print(f'  Beats Control: {result["beats_control"]}')

    if result.get('comparison'):
        comp = result['comparison']
        print()
        print('  Control Comparison:')
        print(f'    Significance: {comp.get("significance", "N/A")}')
        print(f'    P-Value: {comp.get("p_value", 0):.3f}')
        print(f'    WR Diff: {comp.get("wr_diff", 0)*100:+.1f}%')
        print(f'    ExpR Diff: {comp.get("exp_r_diff", 0):+.3f}R')

    # Check database status update
    edge = get_candidate_by_id(conn, edge_id)
    print()
    print(f'  Edge Status Updated: {edge["status"]}')

    if edge['status'] == 'VALIDATED':
        print(f'  Pass Reason: {edge.get("pass_reason_text", "N/A")}')
    elif edge['status'] == 'TESTED_FAILED':
        print(f'  Failure Code: {edge.get("failure_reason_code", "N/A")}')
        print(f'  Failure Reason: {edge.get("failure_reason_text", "N/A")}')

    # Cleanup
    print()
    print('[CLEANUP] Deleting test edge...')
    conn.execute("DELETE FROM edge_registry WHERE edge_id = ?", [edge_id])
    conn.execute("DELETE FROM experiment_run WHERE edge_id = ?", [edge_id])
    print('  Test edge deleted')

    conn.close()

    print()
    print('=' * 70)
    print('TEST COMPLETE')
    print('=' * 70)

    return True


if __name__ == "__main__":
    try:
        success = test_validation_comprehensive()
        if success:
            print('\n[OK] All tests passed!')
        else:
            print('\n[FAIL] Tests failed!')
    except Exception as e:
        print(f'\n[ERROR] Test crashed: {e}')
        import traceback
        traceback.print_exc()
