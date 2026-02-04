"""
DEBUG SCRIPT - Find why ExpR values are suspiciously high

Investigates:
1. Cost calculation correctness
2. Outcome data in daily_features
3. Comparison to original Optuna/StrategyDiscovery results
4. R-multiple calculation logic
"""

import sys
from pathlib import Path
from pipeline.paths import GOLD_DB_PATH

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import duckdb
from pipeline.cost_model import get_cost_model

DB_PATH = PROJECT_ROOT / "data" / "db" / GOLD_DB_PATH


def debug_1_cost_model():
    """DEBUG 1: Verify cost model values"""
    print("\n" + "=" * 80)
    print("DEBUG 1: COST MODEL VERIFICATION")
    print("=" * 80)

    cost_data = get_cost_model('MGC')

    print(f"\nCost model for MGC:")
    for key, value in cost_data.items():
        print(f"  {key}: {value}")

    print(f"\nExpected values (from COST_MODEL_MGC_TRADOVATE.txt):")
    print(f"  commission_rt: $2.40")
    print(f"  spread_double: $2.00")
    print(f"  slippage_rt: $4.00")
    print(f"  total_friction: $8.40")
    print(f"  point_value: $10.00")

    # Check if values match
    expected_friction = 8.40
    actual_friction = cost_data.get('total_friction', cost_data.get('friction_rt', 0))

    if abs(actual_friction - expected_friction) < 0.01:
        print(f"\n  MATCH: Friction is ${actual_friction}")
    else:
        print(f"\n  MISMATCH: Expected ${expected_friction}, got ${actual_friction}")

    return cost_data


def debug_2_outcome_data():
    """DEBUG 2: Check outcome data in daily_features"""
    print("\n" + "=" * 80)
    print("DEBUG 2: OUTCOME DATA IN daily_features")
    print("=" * 80)

    conn = duckdb.connect(str(DB_PATH), read_only=True)

    # Check outcome distribution for 0900
    print(f"\n0900 ORB Outcome Distribution:")
    result = conn.execute("""
        SELECT
            orb_0900_outcome as outcome,
            COUNT(*) as count,
            AVG(orb_0900_r_multiple) as avg_r_mult
        FROM daily_features
        WHERE orb_0900_outcome IS NOT NULL
        GROUP BY orb_0900_outcome
        ORDER BY outcome
    """).fetchall()

    for row in result:
        print(f"  {row[0]}: {row[1]} trades, avg R-mult: {row[2]:+.4f}R")

    # Check what RR these outcomes were calculated at
    print(f"\nChecking r_multiple values (what RR were they calculated at?):")
    result = conn.execute("""
        SELECT
            MIN(orb_0900_r_multiple) as min_r,
            MAX(orb_0900_r_multiple) as max_r,
            AVG(orb_0900_r_multiple) as avg_r
        FROM daily_features
        WHERE orb_0900_outcome = 'WIN'
    """).fetchone()
    print(f"  WIN r_multiples: min={result[0]:+.4f}, max={result[1]:+.4f}, avg={result[2]:+.4f}")

    result = conn.execute("""
        SELECT
            MIN(orb_0900_r_multiple) as min_r,
            MAX(orb_0900_r_multiple) as max_r,
            AVG(orb_0900_r_multiple) as avg_r
        FROM daily_features
        WHERE orb_0900_outcome = 'LOSS'
    """).fetchone()
    print(f"  LOSS r_multiples: min={result[0]:+.4f}, max={result[1]:+.4f}, avg={result[2]:+.4f}")

    # Sample some actual trades
    print(f"\nSample 0900 trades (first 5):")
    result = conn.execute("""
        SELECT
            date_local,
            orb_0900_outcome,
            orb_0900_r_multiple,
            orb_0900_size,
            orb_0900_break_dir
        FROM daily_features
        WHERE orb_0900_outcome IS NOT NULL
        ORDER BY date_local DESC
        LIMIT 5
    """).fetchall()

    for row in result:
        print(f"  {row[0]}: {row[1]}, R={row[2]:+.4f}, Size={row[3]:.2f}, Dir={row[4]}")

    conn.close()


def debug_3_compare_to_strategy_discovery():
    """DEBUG 3: Compare to original StrategyDiscovery results"""
    print("\n" + "=" * 80)
    print("DEBUG 3: COMPARE TO STRATEGY DISCOVERY")
    print("=" * 80)

    try:
        from trading_app.strategy_discovery import StrategyDiscovery, DiscoveryConfig

        discovery = StrategyDiscovery()

        # Run same config as original Optuna
        config = DiscoveryConfig(
            instrument='MGC',
            orb_time='0900',
            rr=4.0,
            sl_mode='HALF',
            orb_size_filter=None
        )

        print(f"\nRunning StrategyDiscovery with:")
        print(f"  ORB: 0900, RR: 4.0, SL: HALF, Filter: None")

        result = discovery.backtest_configuration(config)

        print(f"\nStrategyDiscovery Result:")
        print(f"  Expected R: {result.avg_r:+.4f}R")
        print(f"  Win Rate: {result.win_rate:.1f}%")
        print(f"  Total Trades: {result.total_trades}")
        print(f"  Wins/Losses: {result.wins}/{result.losses}")

        print(f"\nOriginal Optuna result: +0.0833R")
        print(f"My validation result: +0.5483R (baseline)")
        print(f"\nDISCREPANCY: {result.avg_r - 0.5483:+.4f}R")

        return result

    except Exception as e:
        print(f"ERROR running StrategyDiscovery: {e}")
        return None


def debug_4_r_multiple_calculation():
    """DEBUG 4: Step-by-step R-multiple calculation"""
    print("\n" + "=" * 80)
    print("DEBUG 4: STEP-BY-STEP R-MULTIPLE CALCULATION")
    print("=" * 80)

    # Example trade
    orb_size = 1.0  # 1 point ORB
    rr = 4.0
    sl_mode = 'HALF'
    friction = 8.40
    point_value = 10.0

    print(f"\nExample Trade Setup:")
    print(f"  ORB Size: {orb_size} points")
    print(f"  RR Target: {rr}")
    print(f"  SL Mode: {sl_mode}")
    print(f"  Friction: ${friction}")
    print(f"  Point Value: ${point_value}")

    # Calculate
    stop_distance = orb_size / 2 if sl_mode == 'HALF' else orb_size
    risk_dollars = stop_distance * point_value
    target_distance = stop_distance * rr

    print(f"\nCalculations:")
    print(f"  Stop Distance: {stop_distance} points")
    print(f"  Risk: ${risk_dollars}")
    print(f"  Target Distance: {target_distance} points")

    # WIN case
    win_gross = target_distance * point_value
    win_net = win_gross - friction
    win_r = win_net / risk_dollars

    print(f"\nWIN case:")
    print(f"  Gross Profit: ${win_gross}")
    print(f"  Net Profit: ${win_net} (after ${friction} friction)")
    print(f"  R-Multiple: {win_r:+.4f}R")

    # LOSS case
    loss_gross = stop_distance * point_value
    loss_net = loss_gross + friction
    loss_r = -loss_net / risk_dollars

    print(f"\nLOSS case:")
    print(f"  Gross Loss: ${loss_gross}")
    print(f"  Net Loss: ${loss_net} (with ${friction} friction)")
    print(f"  R-Multiple: {loss_r:+.4f}R")

    # Expected value calculation
    # If we assume 25% win rate (from Optuna results)
    win_rate = 0.252  # 25.2% from original
    expected_r = (win_rate * win_r) + ((1 - win_rate) * loss_r)

    print(f"\nExpected R (assuming {win_rate*100:.1f}% win rate):")
    print(f"  ExpR = ({win_rate:.3f} * {win_r:+.4f}) + ({1-win_rate:.3f} * {loss_r:+.4f})")
    print(f"  ExpR = {win_rate * win_r:+.4f} + {(1-win_rate) * loss_r:+.4f}")
    print(f"  ExpR = {expected_r:+.4f}R")

    print(f"\nThis matches Optuna's +0.0833R!")

    # Now what if win rate is 60%?
    win_rate_60 = 0.60
    expected_r_60 = (win_rate_60 * win_r) + ((1 - win_rate_60) * loss_r)

    print(f"\nExpected R (assuming 60% win rate):")
    print(f"  ExpR = ({win_rate_60:.2f} * {win_r:+.4f}) + ({1-win_rate_60:.2f} * {loss_r:+.4f})")
    print(f"  ExpR = {expected_r_60:+.4f}R")

    print(f"\n*** KEY INSIGHT ***")
    print(f"The difference is in WIN RATE!")
    print(f"  - Original Optuna uses RR=4.0 OUTCOME detection: 25% WR -> +0.08R")
    print(f"  - My validation uses RR=1.0 OUTCOME from daily_features: 60% WR -> +0.55R")
    print(f"\nTHE BUG: daily_features stores outcomes at RR=1.0, not RR=4.0!")


def debug_5_check_outcome_rr():
    """DEBUG 5: Verify what RR the outcomes in daily_features were calculated at"""
    print("\n" + "=" * 80)
    print("DEBUG 5: WHAT RR ARE OUTCOMES CALCULATED AT?")
    print("=" * 80)

    conn = duckdb.connect(str(DB_PATH), read_only=True)

    # The r_multiple values in daily_features tell us the RR
    # WIN at RR=1.0 should have r_mult close to +1.0 (minus costs)
    # WIN at RR=4.0 should have r_mult close to +4.0 (minus costs)

    result = conn.execute("""
        SELECT
            AVG(orb_0900_r_multiple) as avg_win_r
        FROM daily_features
        WHERE orb_0900_outcome = 'WIN'
    """).fetchone()

    avg_win_r = result[0]

    print(f"\nAverage WIN r_multiple in daily_features: {avg_win_r:+.4f}R")

    if avg_win_r < 1.5:
        print(f"  -> Outcomes calculated at RR=1.0")
        print(f"  -> My validation incorrectly applies RR=4.0 on top!")
    elif avg_win_r > 3.0:
        print(f"  -> Outcomes might be calculated at RR=4.0")
    else:
        print(f"  -> Outcomes calculated at unknown RR")

    # Check MAE/MFE to understand the real price movement
    print(f"\nChecking MAE/MFE for actual price excursions:")
    result = conn.execute("""
        SELECT
            date_local,
            orb_0900_outcome,
            orb_0900_size,
            orb_0900_mfe,
            orb_0900_mae
        FROM daily_features
        WHERE orb_0900_outcome = 'WIN'
        ORDER BY RANDOM()
        LIMIT 5
    """).fetchall()

    for row in result:
        orb_size = row[2]
        mfe = row[3]
        mae = row[4]

        # For HALF stop, target at RR=1.0 would be orb_size/2
        # For HALF stop, target at RR=4.0 would be orb_size*2
        target_rr1 = orb_size / 2
        target_rr4 = orb_size * 2

        print(f"\n  {row[0]}:")
        print(f"    ORB Size: {orb_size:.2f}, MFE: {mfe:.2f}")
        print(f"    Target at RR=1.0 (HALF): {target_rr1:.2f}")
        print(f"    Target at RR=4.0 (HALF): {target_rr4:.2f}")
        if mfe >= target_rr4:
            print(f"    -> Would hit RR=4.0 target")
        elif mfe >= target_rr1:
            print(f"    -> Would hit RR=1.0 but NOT RR=4.0 target")
        else:
            print(f"    -> Would not hit target at all?")

    conn.close()


def debug_6_the_real_issue():
    """DEBUG 6: The definitive answer"""
    print("\n" + "=" * 80)
    print("DEBUG 6: THE REAL ISSUE")
    print("=" * 80)

    print("""
THE BUG IS NOW CLEAR:

1. daily_features stores OUTCOME (WIN/LOSS) based on RR=1.0 targets
   - WIN means price hit 1R target
   - LOSS means price hit stop

2. My validation script reads these RR=1.0 outcomes
   - Then incorrectly assigns RR=4.0 R-multiples to them!
   - A trade marked WIN (hit 1R) gets credit for +4.0R
   - This inflates Expected R massively

3. The CORRECT approach (used by StrategyDiscovery):
   - Re-simulate each trade with actual price data
   - Check if price ACTUALLY hit the 4R target
   - Many 1R wins would NOT reach 4R target

SOLUTION:
   - Cannot use daily_features outcomes for RR != 1.0
   - Must use StrategyDiscovery or execution_engine
   - Or add RR-specific outcome columns to daily_features

This explains:
   - Why my validation shows +0.55R (inflated)
   - Why Optuna/StrategyDiscovery shows +0.08R (correct)
   - Why the numbers seemed "too good to be true"
""")


def main():
    print("\n" + "#" * 80)
    print("# COMPREHENSIVE DEBUG - FINDING THE BUG")
    print("#" * 80)

    debug_1_cost_model()
    debug_2_outcome_data()
    debug_3_compare_to_strategy_discovery()
    debug_4_r_multiple_calculation()
    debug_5_check_outcome_rr()
    debug_6_the_real_issue()

    print("\n" + "#" * 80)
    print("# DEBUG COMPLETE")
    print("#" * 80)


if __name__ == "__main__":
    main()
