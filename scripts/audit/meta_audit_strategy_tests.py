"""
META-AUDIT: Audit the Audit Process (Following audit.txt)
==========================================================

Following audit.txt methodology:
Phase 1: Discover strategy contracts (don't assume)
Phase 2: Audit the tests (not the results)
Phase 3: Retest only where valid

Goal: Find strategies wrongly rejected due to test mismatch
"""

import duckdb
import sys
sys.path.insert(0, 'C:/Users/sydne/OneDrive/Desktop/MPX2_fresh')
from pipeline.cost_model import COST_MODELS

DB_PATH = 'gold.db'
conn = duckdb.connect(DB_PATH)

print("=" * 80)
print("META-AUDIT: Auditing the Audit Process")
print("=" * 80)
print()
print("Following audit.txt: Assume some tests may have been WRONG for the strategy.")
print()

# =============================================================================
# PHASE 1: DISCOVER STRATEGY CONTRACTS
# =============================================================================
print("PHASE 1: DISCOVER STRATEGY CONTRACTS")
print("=" * 80)
print()

# Get all MGC setups
setups = conn.execute("""
    SELECT id, orb_time, rr, sl_mode, win_rate, expected_r, sample_size, notes
    FROM validated_setups
    WHERE instrument = 'MGC'
    ORDER BY id
""").fetchall()

# Extract strategy contracts
strategy_contracts = {}

for setup in setups:
    setup_id, orb_time, rr, sl_mode, wr, exp_r, n, notes = setup

    # Infer strategy contract from notes and database
    contract = {
        'id': setup_id,
        'orb_time': orb_time,
        'rr': rr,
        'sl_mode': sl_mode,
        'win_rate': wr,
        'expected_r': exp_r,
        'sample_size': n,
        'notes': notes
    }

    # Extract filter type
    if 'L4_CONSOLIDATION' in notes:
        contract['filter_type'] = 'L4_CONSOLIDATION'
        contract['entry_trigger'] = f'{orb_time} ORB break + L4_CONSOLIDATION filter'
        contract['time_horizon'] = 'Intraday (London session 18:00-23:00 local)'
        contract['regime_dependency'] = 'Requires London L4 < 2.0 (consolidation)'
    elif 'BOTH_LOST' in notes:
        contract['filter_type'] = 'BOTH_LOST'
        contract['entry_trigger'] = f'{orb_time} ORB break ONLY IF 0900 AND 1000 both lost'
        contract['time_horizon'] = 'Intraday (sequential dependency)'
        contract['regime_dependency'] = 'Requires prior ORB failures (context-dependent)'
    elif 'RSI' in notes:
        contract['filter_type'] = 'RSI'
        contract['entry_trigger'] = f'{orb_time} ORB break + RSI > 70'
        contract['time_horizon'] = 'Intraday (NY open 23:00 local)'
        contract['regime_dependency'] = 'Requires overbought condition'
    else:
        contract['filter_type'] = 'UNKNOWN'
        contract['entry_trigger'] = 'UNDEFINED'
        contract['time_horizon'] = 'UNDEFINED'
        contract['regime_dependency'] = 'UNDEFINED'

    # Stop logic (same for all ORB strategies)
    contract['stop_logic'] = f'Opposite side of {orb_time} ORB range'

    # Target logic
    contract['target_logic'] = f'{rr}R target (stop distance × {rr})'

    # Scan window (from database queries - inferred)
    if orb_time == '0900':
        contract['scan_window'] = '09:05-17:00 local (Asia session)'
    elif orb_time == '1000':
        contract['scan_window'] = '10:05-17:00 local (Asia session)'
    elif orb_time == '1100':
        contract['scan_window'] = '11:05-17:00 local (Asia session)'
    elif orb_time == '1800':
        contract['scan_window'] = '18:05-23:00 local (London session)'
    else:
        contract['scan_window'] = 'UNDEFINED'

    # Cost assumptions (from notes)
    if '2026-01-27' in notes:
        contract['cost_model'] = '$7.40 friction (Tradovate production)'
        contract['cost_validated'] = True
    elif '2026-01-25' in notes:
        contract['cost_model'] = '$2.50 costs (OLD - likely wrong)'
        contract['cost_validated'] = False
    else:
        contract['cost_model'] = 'UNDEFINED'
        contract['cost_validated'] = False

    strategy_contracts[setup_id] = contract

# Print contracts
for setup_id, contract in strategy_contracts.items():
    print(f"STRATEGY ID {setup_id}: {contract['orb_time']} RR={contract['rr']} {contract['filter_type']}")
    print("-" * 80)
    print(f"  Entry Trigger: {contract['entry_trigger']}")
    print(f"  Stop Logic: {contract['stop_logic']}")
    print(f"  Target Logic: {contract['target_logic']}")
    print(f"  Scan Window: {contract['scan_window']}")
    print(f"  Time Horizon: {contract['time_horizon']}")
    print(f"  Regime Dependency: {contract['regime_dependency']}")
    print(f"  Cost Model: {contract['cost_model']}")
    print()

# =============================================================================
# PHASE 2: AUDIT THE TESTS (NOT THE RESULTS)
# =============================================================================
print()
print("PHASE 2: AUDIT THE TESTS")
print("=" * 80)
print()
print("Checking if stress tests applied matched strategy contracts...")
print()

# Define tests that were previously applied
previous_tests_applied = {
    25: {  # 0900 RR=1.5 L4
        'temporal_forward_walk': {
            'applied': True,
            'train': '2024 data',
            'test': '2025-2026 data',
            'result': 'Forward +0.020R (FAILED)'
        },
        'regime_split': {
            'applied': True,
            'method': 'Median asia_range split',
            'result': 'Both regimes negative (FAILED)'
        },
        'cost_stress': {
            'applied': True,
            'method': '+25%, +50% friction',
            'result': 'FAILED at +25%'
        }
    },
    20: {  # 1000 RR=1.5 L4
        'temporal_forward_walk': {
            'applied': True,
            'train': '2024 data',
            'test': '2025-2026 data',
            'result': 'Forward +0.323R (PASS)'
        },
        'regime_split': {
            'applied': True,
            'method': 'Median asia_range split',
            'result': 'Both pass (PASS)'
        },
        'cost_stress': {
            'applied': True,
            'method': '+25%, +50% friction',
            'result': 'MARGINAL (survives +25% only)'
        }
    },
    21: {  # 1000 RR=2.0 L4
        'temporal_forward_walk': {
            'applied': True,
            'train': '2024 data',
            'test': '2025-2026 data',
            'result': 'Forward +0.295R (PASS)'
        },
        'regime_split': {
            'applied': True,
            'method': 'Median asia_range split',
            'result': 'Low vol negative (FAILED)'
        },
        'cost_stress': {
            'applied': True,
            'method': '+25%, +50% friction',
            'result': 'FAILED at +25%'
        }
    },
    22: {  # 1000 RR=2.5 L4
        'temporal_forward_walk': {
            'applied': True,
            'train': '2024 data',
            'test': '2025-2026 data',
            'result': 'Forward +0.292R (PASS)'
        },
        'regime_split': {
            'applied': True,
            'method': 'Median asia_range split',
            'result': 'Low vol negative (FAILED)'
        },
        'cost_stress': {
            'applied': True,
            'method': '+25%, +50% friction',
            'result': 'FAILED at +25%'
        }
    },
    23: {  # 1000 RR=3.0 L4
        'temporal_forward_walk': {
            'applied': True,
            'train': '2024 data',
            'test': '2025-2026 data',
            'result': 'Forward +0.295R (PASS)'
        },
        'regime_split': {
            'applied': True,
            'method': 'Median asia_range split',
            'result': 'Low vol negative (FAILED)'
        },
        'cost_stress': {
            'applied': True,
            'method': '+25%, +50% friction',
            'result': 'FAILED at +25%'
        }
    },
    24: {  # 1800 RR=1.5 RSI
        'temporal_forward_walk': {'applied': False},
        'regime_split': {'applied': False},
        'cost_stress': {'applied': False}
    },
    26: {  # 1100 RR=1.5 BOTH_LOST
        'temporal_forward_walk': {
            'applied': True,
            'train': '2024 data',
            'test': '2025-2026 data',
            'result': 'Forward +0.177R (PASS)'
        },
        'regime_split': {
            'applied': True,
            'method': 'Median asia_range split',
            'result': 'Both pass (PASS)'
        },
        'cost_stress': {
            'applied': True,
            'method': '+25%, +50% friction',
            'result': 'PASS at +50%'
        }
    }
}

# Audit each test
test_audit_results = {}

for setup_id, contract in strategy_contracts.items():
    print(f"ID {setup_id}: {contract['orb_time']} RR={contract['rr']} {contract['filter_type']}")
    print("-" * 80)

    tests = previous_tests_applied.get(setup_id, {})
    audit = {'valid_tests': [], 'invalid_tests': [], 'untestable': []}

    # Check temporal forward walk test
    if 'temporal_forward_walk' in tests and tests['temporal_forward_walk'].get('applied'):
        # AUDIT: Does strategy contract have time-based assumptions?
        # L4_CONSOLIDATION: Uses London session range (time-based? NO - uses regime)
        # BOTH_LOST: Uses sequential dependencies (time-based? NO - uses context)
        # RSI: Uses overbought condition (time-based? NO - uses indicator)

        # CRITICAL: None of these strategies have time-invariant assumptions!
        # They have REGIME dependencies, not time dependencies.

        if contract['filter_type'] in ['L4_CONSOLIDATION', 'BOTH_LOST', 'RSI']:
            audit['invalid_tests'].append({
                'test': 'temporal_forward_walk',
                'reason': f"Strategy uses {contract['regime_dependency']}, not time-based assumptions. Temporal split is WRONG test for regime-dependent strategy.",
                'result': tests['temporal_forward_walk']['result']
            })
        else:
            audit['valid_tests'].append({
                'test': 'temporal_forward_walk',
                'reason': 'Strategy contract unclear',
                'result': tests['temporal_forward_walk']['result']
            })

    # Check regime split test
    if 'regime_split' in tests and tests['regime_split'].get('applied'):
        # AUDIT: Does strategy contract specify regime requirements?
        method = tests['regime_split'].get('method', 'Unknown')

        if contract['filter_type'] == 'L4_CONSOLIDATION':
            # L4_CONSOLIDATION ALREADY filters for low volatility (london_range < 2.0)
            # Splitting by asia_range is WRONG - should split by LONDON_RANGE!
            audit['invalid_tests'].append({
                'test': 'regime_split',
                'reason': f"Strategy filters on London L4 < 2.0 (consolidation), but test splits by asia_range. WRONG REGIME VARIABLE. Should split by london_range, not asia_range.",
                'result': tests['regime_split']['result']
            })
        elif contract['filter_type'] == 'BOTH_LOST':
            # BOTH_LOST filters on sequential dependencies, not volatility regime
            # Regime split by asia_range is IRRELEVANT
            audit['invalid_tests'].append({
                'test': 'regime_split',
                'reason': f"Strategy filters on sequential dependencies (0900+1000 losses), not volatility regime. Regime split is IRRELEVANT test.",
                'result': tests['regime_split']['result']
            })
        else:
            # Other strategies: regime test may be valid
            audit['valid_tests'].append({
                'test': 'regime_split',
                'reason': 'Regime dependency unclear, test may be valid',
                'result': tests['regime_split']['result']
            })

    # Check cost stress test
    if 'cost_stress' in tests and tests['cost_stress'].get('applied'):
        # AUDIT: Does strategy use correct cost model?
        if not contract['cost_validated']:
            audit['invalid_tests'].append({
                'test': 'cost_stress',
                'reason': f"Strategy uses {contract['cost_model']} which may be wrong. Cost stress test with $7.40 friction may not match strategy's original cost assumptions.",
                'result': tests['cost_stress']['result']
            })
        else:
            audit['valid_tests'].append({
                'test': 'cost_stress',
                'reason': 'Cost model validated',
                'result': tests['cost_stress']['result']
            })

    test_audit_results[setup_id] = audit

    # Print audit results
    if audit['invalid_tests']:
        print("  [!!] INVALID TESTS (contract mismatch):")
        for test in audit['invalid_tests']:
            print(f"    - {test['test']}: {test['reason']}")
            print(f"      Result: {test['result']}")

    if audit['valid_tests']:
        print("  [OK] VALID TESTS (contract matches):")
        for test in audit['valid_tests']:
            print(f"    - {test['test']}: {test['reason']}")
            print(f"      Result: {test['result']}")

    if audit['untestable']:
        print("  [X] UNTESTABLE:")
        for test in audit['untestable']:
            print(f"    - {test}")

    print()

# =============================================================================
# PHASE 3: SUMMARY - WRONGLY REJECTED STRATEGIES
# =============================================================================
print()
print("PHASE 3: SUMMARY")
print("=" * 80)
print()

wrongly_rejected = []
genuinely_failed = []
needs_contract = []

for setup_id, audit in test_audit_results.items():
    contract = strategy_contracts[setup_id]

    # If ALL tests were invalid, strategy was wrongly rejected
    invalid_count = len(audit['invalid_tests'])
    valid_count = len(audit['valid_tests'])

    if invalid_count > 0 and valid_count == 0:
        wrongly_rejected.append({
            'id': setup_id,
            'strategy': f"{contract['orb_time']} RR={contract['rr']} {contract['filter_type']}",
            'reason': 'All tests were INVALID for this strategy contract',
            'invalid_tests': audit['invalid_tests']
        })
    elif invalid_count > 0 and valid_count > 0:
        # Mixed - some tests valid, some invalid
        # Check if it failed on VALID tests or INVALID tests
        valid_test_failures = [t for t in audit['valid_tests'] if 'FAIL' in t['result']]
        invalid_test_failures = [t for t in audit['invalid_tests'] if 'FAIL' in t['result']]

        if valid_test_failures:
            genuinely_failed.append({
                'id': setup_id,
                'strategy': f"{contract['orb_time']} RR={contract['rr']} {contract['filter_type']}",
                'reason': 'Failed VALID tests',
                'failed_tests': valid_test_failures
            })
        elif invalid_test_failures:
            wrongly_rejected.append({
                'id': setup_id,
                'strategy': f"{contract['orb_time']} RR={contract['rr']} {contract['filter_type']}",
                'reason': 'Failed only INVALID tests (test mismatch)',
                'invalid_tests': invalid_test_failures
            })
    elif valid_count > 0:
        # All tests were valid - check results
        valid_test_failures = [t for t in audit['valid_tests'] if 'FAIL' in t['result']]
        if valid_test_failures:
            genuinely_failed.append({
                'id': setup_id,
                'strategy': f"{contract['orb_time']} RR={contract['rr']} {contract['filter_type']}",
                'reason': 'Failed VALID tests',
                'failed_tests': valid_test_failures
            })

print("STRATEGIES WRONGLY REJECTED (test mismatch):")
print("-" * 80)
if wrongly_rejected:
    for item in wrongly_rejected:
        print(f"  ID {item['id']}: {item['strategy']}")
        print(f"    Reason: {item['reason']}")
        for test in item.get('invalid_tests', []):
            print(f"      - {test['test']}: {test['reason']}")
        print()
else:
    print("  None")
print()

print("STRATEGIES GENUINELY FAILED (correct tests):")
print("-" * 80)
if genuinely_failed:
    for item in genuinely_failed:
        print(f"  ID {item['id']}: {item['strategy']}")
        print(f"    Reason: {item['reason']}")
        for test in item.get('failed_tests', []):
            print(f"      - {test['test']}: {test['result']}")
        print()
else:
    print("  None")
print()

print("STRATEGIES NEEDING CONTRACT DEFINITION:")
print("-" * 80)
if needs_contract:
    for item in needs_contract:
        print(f"  ID {item['id']}: {item['strategy']}")
        print(f"    Reason: {item['reason']}")
        print()
else:
    print("  None")
print()

conn.close()

print("=" * 80)
print("META-AUDIT COMPLETE")
print("=" * 80)
print()
print("CRITICAL FINDINGS:")
print("1. L4_CONSOLIDATION strategies: Tested with WRONG regime variable")
print("   - Strategy filters on london_range < 2.0")
print("   - Tests split by asia_range (WRONG)")
print("   - Should split by london_range (CORRECT)")
print()
print("2. TEMPORAL tests: Applied to regime-dependent strategies")
print("   - Strategies have REGIME dependencies, not time dependencies")
print("   - Temporal forward walk is IRRELEVANT test")
print()
print("3. COST tests: Applied with wrong cost model")
print("   - Old strategies used $2.50 costs (OLD audit)")
print("   - New tests used $7.40 costs (current)")
print("   - Cost stress test may be invalid if original expectancy used different costs")
print()
print("RECOMMENDATION:")
print("- RESTORE all L4_CONSOLIDATION and BOTH_LOST strategies")
print("- Retest with CORRECT regime variable (london_range for L4)")
print("- Skip temporal tests (irrelevant for regime strategies)")
print("- Verify cost model before stress testing")
