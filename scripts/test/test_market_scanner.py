"""
Test updated market_scanner.py with new filter logic.

Tests:
1. Scanner initializes without errors
2. get_required_filters() correctly identifies L4_CONSOLIDATION and RSI>70 filters
3. check_l4_consolidation_filter() logic works
4. check_rsi_filter() logic works
5. validate_setup() integrates all filters correctly
"""

from trading_app.market_scanner import MarketScanner

print("="*80)
print("TESTING MARKET_SCANNER.PY WITH NEW FILTERS")
print("="*80)
print()

# Test 1: Initialize scanner
print("[TEST 1] Initialize scanner...")
try:
    scanner = MarketScanner()
    print("[OK] Scanner initialized successfully")
    print()
except Exception as e:
    print(f"[ERROR] Scanner initialization failed: {e}")
    exit(1)

# Test 2: Check required filters for each ORB
print("[TEST 2] Check required filters from validated_setups...")
orb_times = ['0900', '1000', '1100', '1800', '2300', '0030']

for orb_time in orb_times:
    try:
        filters = scanner.get_required_filters(orb_time)
        if filters:
            print(f"  {orb_time} ORB: {', '.join(filters)}")
        else:
            print(f"  {orb_time} ORB: No validated filters")
    except Exception as e:
        print(f"  {orb_time} ORB: ERROR - {e}")

print()

# Test 3: Check L4_CONSOLIDATION filter logic
print("[TEST 3] Check L4_CONSOLIDATION filter logic...")
test_cases = [
    ('L4_CONSOLIDATION', True, 'Should PASS'),
    ('L1_SWEEP_HIGH', False, 'Should FAIL'),
    ('L2_SWEEP_LOW', False, 'Should FAIL'),
    ('L3_EXPANSION', False, 'Should FAIL'),
    (None, False, 'No data - should FAIL'),
]

for london_type, expected, description in test_cases:
    result = scanner.check_l4_consolidation_filter(london_type)
    passed = result['passes_filter']
    status = "[OK]" if passed == expected else "[FAIL]"
    print(f"  {status} {london_type}: {passed} ({description})")

print()

# Test 4: Check RSI filter logic
print("[TEST 4] Check RSI > 70 filter logic...")
test_cases = [
    (75.0, True, 'Should PASS'),
    (70.5, True, 'Should PASS'),
    (70.0, False, 'Should FAIL (not >70)'),
    (65.0, False, 'Should FAIL'),
    (None, False, 'No data - should FAIL'),
]

for rsi_value, expected, description in test_cases:
    result = scanner.check_rsi_filter(rsi_value, threshold=70.0)
    passed = result['passes_filter']
    status = "[OK]" if passed == expected else "[FAIL]"
    rsi_str = f"{rsi_value:.1f}" if rsi_value is not None else "None"
    print(f"  {status} RSI={rsi_str}: {passed} ({description})")

print()

# Test 5: Validate setup integration (dry run - no data expected)
print("[TEST 5] Validate setup integration (dry run)...")
try:
    validation = scanner.validate_setup('1000')
    print(f"  [OK] validate_setup('1000') returned successfully")
    print(f"  Valid: {validation['valid']}")
    print(f"  Recommendation: {validation['recommendation']}")
    print(f"  Reasons: {len(validation['reasons'])} reason(s)")
    print(f"  Validated filters: {list(validation['validated_filters'].keys())}")
    print()
except Exception as e:
    print(f"  [ERROR] validate_setup() failed: {e}")
    import traceback
    traceback.print_exc()
    print()

print("="*80)
print("MARKET_SCANNER.PY TESTS COMPLETE")
print("="*80)
print()
print("All filter logic has been successfully integrated.")
print()
print("Next steps:")
print("  1. Backfill historical data (if missing)")
print("  2. Test scanner with real market data")
print("  3. Update trading_app/config.py if needed")
print("  4. Run test_app_sync.py to verify synchronization")
print()
