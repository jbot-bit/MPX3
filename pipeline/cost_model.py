#!/usr/bin/env python3
"""
Cost Model - Canonical Realized RR Calculations

Implements CANONICAL_LOGIC.txt methodology with instrument-specific costs.

Current Status:
- MGC: PRODUCTION (real Tradovate broker data)
- NQ: BLOCKED (need specs + cost model)
- MPL: BLOCKED (need specs + cost model)

Based on:
- CANONICAL_LOGIC.txt (lines 62-102: Realized RR Engine)
- COST_MODEL_MGC_TRADOVATE.txt (real broker costs)
"""

from typing import Dict, Optional


# =============================================================================
# INSTRUMENT SPECIFICATIONS
# =============================================================================

INSTRUMENT_SPECS = {
    'MGC': {
        'name': 'Micro Gold',
        'tick_size': 0.10,
        'tick_value': 1.00,  # $ per tick
        'point_value': 10.00,  # $ per point (10 ticks = 1 point)
        'exchange': 'COMEX',
        'status': 'PRODUCTION'
    },
    # NQ and MPL blocked until specs provided
    # 'NQ': {
    #     'name': 'Micro E-mini Nasdaq-100',
    #     'tick_size': 0.25,
    #     'tick_value': 0.50,  # UNVERIFIED - need confirmation
    #     'point_value': 0.50,  # UNVERIFIED - need confirmation
    #     'exchange': 'CME',
    #     'status': 'BLOCKED'
    # },
    # 'MPL': {
    #     'name': 'Micro Platinum',
    #     'tick_size': None,  # UNKNOWN
    #     'tick_value': None,  # UNKNOWN
    #     'point_value': None,  # UNKNOWN
    #     'exchange': 'NYMEX',
    #     'status': 'BLOCKED'
    # }
}


# =============================================================================
# COST MODELS (BROKER-SPECIFIC)
# =============================================================================

COST_MODELS = {
    'MGC': {
        'broker': 'Tradovate',
        'source': 'Real performance report + honest spread accounting',

        # Commission (confirmed from real broker data)
        'commission_rt': 2.40,  # Commission + exchange + NFA fees (round-trip)

        # Spread costs (MANDATORY - market orders always cross spread)
        # HONEST ACCOUNTING: Entry crosses spread + Exit crosses spread = 2 crossings
        'spread_per_cross': 1.00,  # 1 tick per crossing = $1.00
        'spread_double': 2.00,  # Entry + exit = 2 ticks = $2.00 (MANDATORY)

        # Slippage (ADDITIONAL to spread, not a replacement for it)
        # This is pure slippage BEYOND the spread due to volatility, order timing, etc.
        'slippage_rt': 4.00,  # 4 ticks = $4.00 (conservative estimate, BEYOND spread)
        'slippage_ticks': 4,  # For stress testing

        # Total friction (HONEST: commission + double_spread + slippage)
        'total_friction': 8.40,  # 2.40 + 2.00 + 4.00

        # Instrument specs (from INSTRUMENT_SPECS)
        'tick_size': 0.10,
        'tick_value': 1.00,
        'point_value': 10.00,
        'status': 'PRODUCTION'
    },
    # NQ and MPL blocked until cost data provided
    # 'NQ': {
    #     'broker': None,
    #     'source': None,
    #     'commission_rt': None,
    #     'slippage_rt': None,
    #     'spread': None,
    #     'total_friction': None,
    #     'status': 'BLOCKED'
    # },
    # 'MPL': {
    #     'broker': None,
    #     'source': None,
    #     'commission_rt': None,
    #     'slippage_rt': None,
    #     'spread': None,
    #     'total_friction': None,
    #     'status': 'BLOCKED'
    # }
}


# =============================================================================
# STRESS TESTING SCENARIOS
# =============================================================================

SLIPPAGE_STRESS_MULTIPLIERS = {
    'normal': 1.0,  # 4 ticks for MGC
    'moderate': 2.0,  # 8 ticks (fast markets)
    'severe': 3.0,  # 12 ticks (volatile conditions)
    'extreme': 4.0,  # 16 ticks (flash crash)
}


# =============================================================================
# SCOPE LOCK (MANDATORY - Prevents use of unvalidated instruments)
# =============================================================================

# HARD BLOCK: Only MGC is validated and production-ready
# NQ and CL are BLOCKED until contract specs and cost models are validated
# Using wrong multipliers = fake R values = catastrophic losses

PRODUCTION_INSTRUMENTS = ['MGC']  # ONLY validated instruments
BLOCKED_INSTRUMENTS = ['NQ', 'MNQ', 'CL', 'MCL', 'MPL', 'PL']  # Unvalidated (wrong multipliers!)


def validate_instrument_or_block(instrument: str) -> None:
    """
    SCOPE LOCK: Hard-block unvalidated instruments (NQ, CL).

    This is a SAFETY GUARDRAIL to prevent accidental use of instruments
    with unvalidated contract specs. Wrong multipliers = fake R values = losses.

    Args:
        instrument: Instrument symbol to validate

    Raises:
        ValueError: If instrument is blocked (NQ, CL) or unknown

    Example:
        >>> validate_instrument_or_block('MGC')  # OK - passes
        >>> validate_instrument_or_block('NQ')   # ERROR - blocked
        ValueError: BLOCKED INSTRUMENT: NQ is not production-ready...
    """
    instrument_upper = instrument.upper()

    # Check if blocked
    if instrument_upper in BLOCKED_INSTRUMENTS:
        raise ValueError(
            f"BLOCKED INSTRUMENT: {instrument} is not production-ready.\n"
            f"  Reason: Contract specs and cost model not validated\n"
            f"  Risk: Wrong multipliers = fake R values = catastrophic losses\n"
            f"  Production instruments: {PRODUCTION_INSTRUMENTS}\n"
            f"  Blocked instruments: {BLOCKED_INSTRUMENTS}\n"
            f"  To use {instrument}: Validate contract specs, cost model, then update PRODUCTION_INSTRUMENTS list."
        )

    # Check if production-ready
    if instrument_upper not in PRODUCTION_INSTRUMENTS:
        raise ValueError(
            f"UNKNOWN INSTRUMENT: {instrument} is not recognized.\n"
            f"  Production instruments: {PRODUCTION_INSTRUMENTS}\n"
            f"  Blocked instruments: {BLOCKED_INSTRUMENTS}\n"
            f"  Add {instrument} to cost_model.py after validation."
        )

    # Passed all checks
    return


# =============================================================================
# INTEGRITY GATE (MANDATORY - Prevents mathematically impossible trades)
# =============================================================================

# Cost-to-stop threshold: If transaction costs exceed this % of stop distance,
# trade is mathematically unviable (edge is destroyed by friction).
MINIMUM_VIABLE_RISK_THRESHOLD = 0.30  # 30% - from AUDIT1_RESULTS.md


def check_minimum_viable_risk(
    stop_distance_points: float,
    point_value: float,
    total_friction: float
) -> tuple[bool, float, str]:
    """
    INTEGRITY GATE: Check if trade has minimum viable risk (costs < 30% of stop).

    Prevents mathematically impossible trades where transaction costs dominate
    the stop distance, making positive expectancy impossible.

    Rule: If (total_friction / chart_risk_dollars) > 30%, REJECT trade.

    Args:
        stop_distance_points: Stop distance in points
        point_value: Dollar value per point
        total_friction: Total transaction costs (round-trip)

    Returns:
        (is_viable, cost_ratio, message) tuple:
            - is_viable: True if trade passes gate, False if rejected
            - cost_ratio: Fraction of stop consumed by costs (0.0 to 1.0+)
            - message: Human-readable explanation

    Example:
        >>> check_minimum_viable_risk(0.5, 10.0, 8.40)
        (False, 1.68, "REJECTED: Costs ($8.40) are 168% of stop ($5.00) - exceeds 30% limit")

        >>> check_minimum_viable_risk(3.0, 10.0, 8.40)
        (True, 0.28, "PASS: Costs ($8.40) are 28% of stop ($30.00) - within 30% limit")
    """
    if stop_distance_points <= 0:
        return False, 0.0, "REJECTED: Invalid stop distance (must be positive)"

    if point_value <= 0:
        return False, 0.0, "REJECTED: Invalid point value (must be positive)"

    if total_friction < 0:
        return False, 0.0, "REJECTED: Invalid friction (must be non-negative)"

    # Calculate chart risk (before costs)
    chart_risk_dollars = stop_distance_points * point_value

    # Calculate cost ratio
    cost_ratio = total_friction / chart_risk_dollars

    # Check against threshold
    if cost_ratio > MINIMUM_VIABLE_RISK_THRESHOLD:
        return (
            False,
            cost_ratio,
            f"REJECTED: Costs (${total_friction:.2f}) are {cost_ratio:.1%} of stop "
            f"(${chart_risk_dollars:.2f}) - exceeds {MINIMUM_VIABLE_RISK_THRESHOLD:.0%} limit"
        )
    else:
        return (
            True,
            cost_ratio,
            f"PASS: Costs (${total_friction:.2f}) are {cost_ratio:.1%} of stop "
            f"(${chart_risk_dollars:.2f}) - within {MINIMUM_VIABLE_RISK_THRESHOLD:.0%} limit"
        )


# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def get_instrument_specs(instrument: str) -> Dict:
    """
    Get contract specifications for an instrument.

    Args:
        instrument: 'MGC', 'NQ', or 'MPL'

    Returns:
        dict with tick_size, tick_value, point_value, status

    Raises:
        ValueError if instrument not supported or blocked
    """
    # SCOPE LOCK: Hard-block unvalidated instruments
    validate_instrument_or_block(instrument)

    if instrument not in INSTRUMENT_SPECS:
        raise ValueError(
            f"Instrument '{instrument}' not supported. "
            f"Available: {list(INSTRUMENT_SPECS.keys())}"
        )

    specs = INSTRUMENT_SPECS[instrument]

    if specs.get('status') == 'BLOCKED':
        raise ValueError(
            f"Instrument '{instrument}' is BLOCKED. "
            f"Need contract specs and cost model before use."
        )

    return specs


def get_cost_model(instrument: str, stress_level: str = 'normal') -> Dict:
    """
    Get cost model for an instrument with optional stress testing.

    Args:
        instrument: 'MGC', 'NQ', or 'MPL'
        stress_level: 'normal', 'moderate', 'severe', or 'extreme'

    Returns:
        dict with commission_rt, slippage_rt, spread, total_friction

    Raises:
        ValueError if instrument not supported, blocked, or stress_level invalid
    """
    # SCOPE LOCK: Hard-block unvalidated instruments
    validate_instrument_or_block(instrument)

    if instrument not in COST_MODELS:
        raise ValueError(
            f"Cost model for '{instrument}' not defined. "
            f"Available: {list(COST_MODELS.keys())}"
        )

    cost_model = COST_MODELS[instrument].copy()

    if cost_model.get('status') == 'BLOCKED':
        raise ValueError(
            f"Cost model for '{instrument}' is BLOCKED. "
            f"Need real broker data before use."
        )

    # Apply stress multiplier to slippage
    if stress_level not in SLIPPAGE_STRESS_MULTIPLIERS:
        raise ValueError(
            f"Invalid stress_level '{stress_level}'. "
            f"Valid: {list(SLIPPAGE_STRESS_MULTIPLIERS.keys())}"
        )

    multiplier = SLIPPAGE_STRESS_MULTIPLIERS[stress_level]
    base_slippage = cost_model['slippage_rt'] / SLIPPAGE_STRESS_MULTIPLIERS['normal']
    cost_model['slippage_rt'] = base_slippage * multiplier

    # Recalculate total friction (HONEST: commission + double_spread + slippage)
    # Spread is MANDATORY (always 2 crossings), slippage is variable (stress tested)
    cost_model['total_friction'] = (
        cost_model['commission_rt'] +
        cost_model['spread_double'] +  # Always 2 crossings (entry + exit)
        cost_model['slippage_rt']
    )

    cost_model['stress_level'] = stress_level
    cost_model['stress_multiplier'] = multiplier

    return cost_model


def calculate_realized_rr(
    instrument: str,
    stop_distance_points: float,
    rr_theoretical: float,
    stress_level: str = 'normal'
) -> Dict:
    """
    Calculate realized RR using canonical logic (CANONICAL_LOGIC.txt lines 76-98).

    CANONICAL FORMULAS (MANDATORY):
    - Realized_Risk_$ = (|Pe - Psl| × PointValue) + TotalFriction
    - Realized_Reward_$ = (|Ptp - Pe| × PointValue) - TotalFriction
    - Realized_RR = Realized_Reward_$ / Realized_Risk_$

    Costs INCREASE risk (added to stop).
    Costs REDUCE reward (subtracted from target).

    Args:
        instrument: 'MGC', 'NQ', or 'MPL'
        stop_distance_points: Stop distance in points (e.g., ORB size)
        rr_theoretical: Target RR ratio (e.g., 1.5 means target = 1.5 × stop)
        stress_level: 'normal', 'moderate', 'severe', or 'extreme'

    Returns:
        dict with:
            - realized_rr: Realized risk/reward ratio
            - realized_risk_dollars: Risk in dollars (including costs)
            - realized_reward_dollars: Reward in dollars (net of costs)
            - theoretical_rr: Input theoretical RR
            - delta_rr: realized_rr - theoretical_rr
            - delta_pct: Percentage change
            - stop_points: Stop distance
            - target_points: Target distance
            - instrument: Instrument name
            - stress_level: Applied stress level
            - costs: Cost model used

    Raises:
        ValueError if instrument blocked or invalid parameters
    """
    # Validate inputs
    if stop_distance_points <= 0:
        raise ValueError("stop_distance_points must be positive")

    if rr_theoretical <= 0:
        raise ValueError("rr_theoretical must be positive")

    # Get specs and costs
    specs = get_instrument_specs(instrument)
    costs = get_cost_model(instrument, stress_level)

    point_value = specs['point_value']
    total_friction = costs['total_friction']

    # INTEGRITY GATE (MANDATORY): Check minimum viable risk
    # Prevents mathematically impossible trades where costs dominate stop
    is_viable, cost_ratio, gate_message = check_minimum_viable_risk(
        stop_distance_points=stop_distance_points,
        point_value=point_value,
        total_friction=total_friction
    )

    if not is_viable:
        raise ValueError(
            f"INTEGRITY GATE REJECTION: {gate_message}\n"
            f"  Instrument: {instrument}\n"
            f"  Stop: {stop_distance_points:.3f} points (${stop_distance_points * point_value:.2f})\n"
            f"  Costs: ${total_friction:.2f}\n"
            f"  Cost Ratio: {cost_ratio:.1%} (limit: {MINIMUM_VIABLE_RISK_THRESHOLD:.0%})\n"
            f"  Trade is mathematically unviable - edge destroyed by friction."
        )

    # Target distance = RR × stop distance (theoretical)
    target_distance_points = rr_theoretical * stop_distance_points

    # CANONICAL LOGIC: Costs embedded in risk/reward
    realized_risk_dollars = (stop_distance_points * point_value) + total_friction
    realized_reward_dollars = (target_distance_points * point_value) - total_friction

    # Handle edge case: reward becomes negative (costs exceed target)
    if realized_reward_dollars <= 0:
        realized_rr = 0.0  # Edge fails immediately
    else:
        realized_rr = realized_reward_dollars / realized_risk_dollars

    # Calculate deltas
    delta_rr = realized_rr - rr_theoretical
    delta_pct = (delta_rr / rr_theoretical) * 100

    return {
        'realized_rr': realized_rr,
        'realized_risk_dollars': realized_risk_dollars,
        'realized_reward_dollars': realized_reward_dollars,
        'theoretical_rr': rr_theoretical,
        'delta_rr': delta_rr,
        'delta_pct': delta_pct,
        'stop_points': stop_distance_points,
        'target_points': target_distance_points,
        'instrument': instrument,
        'stress_level': stress_level,
        'costs': costs
    }


def calculate_expectancy(
    win_rate: float,
    realized_rr: float,
    avg_loss_r: float = 1.0
) -> float:
    """
    Calculate expectancy with realized RR (CANONICAL_LOGIC.txt line 136).

    Expectancy = (WinRate × AvgWin_R) - (LossRate × AvgLoss_R)

    Args:
        win_rate: Win rate as decimal (e.g., 0.60 for 60%)
        realized_rr: Realized risk/reward ratio
        avg_loss_r: Average loss in R (default 1.0 = full stop hit)

    Returns:
        Expectancy in R-multiples

    Note:
        Assumes AvgWin = Realized_RR (full target hit).
        Costs already embedded in realized_rr.
    """
    if not 0 <= win_rate <= 1.0:
        raise ValueError("win_rate must be between 0 and 1")

    loss_rate = 1.0 - win_rate
    expectancy_r = (win_rate * realized_rr) - (loss_rate * avg_loss_r)
    return expectancy_r


def calculate_position_size(
    account_equity: float,
    risk_pct: float,
    realized_risk_dollars: float
) -> int:
    """
    Calculate position size using realized risk (CANONICAL_LOGIC.txt line 107-112).

    PositionSize = (AccountEquity × Risk%) / Realized_Risk_$

    Args:
        account_equity: Account equity in dollars
        risk_pct: Risk percentage as decimal (e.g., 0.01 for 1%)
        realized_risk_dollars: Realized risk per contract (from calculate_realized_rr)

    Returns:
        Number of contracts (rounded down)
    """
    if account_equity <= 0:
        raise ValueError("account_equity must be positive")

    if not 0 < risk_pct < 1.0:
        raise ValueError("risk_pct must be between 0 and 1")

    if realized_risk_dollars <= 0:
        raise ValueError("realized_risk_dollars must be positive")

    risk_amount = account_equity * risk_pct
    position_size = int(risk_amount / realized_risk_dollars)

    return max(position_size, 0)  # Floor at 0


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_supported_instruments() -> list:
    """Get list of production-ready instruments."""
    return [
        instr for instr, specs in INSTRUMENT_SPECS.items()
        if specs.get('status') == 'PRODUCTION'
    ]


def get_blocked_instruments() -> list:
    """Get list of blocked instruments (need specs/costs)."""
    return [
        instr for instr, specs in INSTRUMENT_SPECS.items()
        if specs.get('status') == 'BLOCKED'
    ]


def is_instrument_ready(instrument: str) -> bool:
    """Check if instrument is production-ready."""
    return (
        instrument in INSTRUMENT_SPECS and
        INSTRUMENT_SPECS[instrument].get('status') == 'PRODUCTION' and
        instrument in COST_MODELS and
        COST_MODELS[instrument].get('status') == 'PRODUCTION'
    )


# =============================================================================
# MAIN (FOR TESTING)
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("COST MODEL - INSTRUMENT STATUS")
    print("=" * 70)
    print()

    print("Production-Ready:")
    for instr in get_supported_instruments():
        specs = INSTRUMENT_SPECS[instr]
        costs = COST_MODELS[instr]
        print(f"  {instr}: {specs['name']}")
        print(f"    Point Value: ${specs['point_value']:.2f}")
        print(f"    Total Friction: ${costs['total_friction']:.2f} (RT)")
        print(f"    Broker: {costs['broker']}")
        print()

    blocked = get_blocked_instruments()
    if blocked:
        print("Blocked (Need Specs/Costs):")
        for instr in blocked:
            print(f"  {instr}: {INSTRUMENT_SPECS[instr]['name']}")
        print()

    # Test MGC calculation
    print("=" * 70)
    print("TEST: MGC 1000 ORB RR=1.5 (Normal Conditions)")
    print("=" * 70)
    print()

    result = calculate_realized_rr(
        instrument='MGC',
        stop_distance_points=2.824,  # Avg 1000 ORB size
        rr_theoretical=1.5,
        stress_level='normal'
    )

    print(f"Stop: {result['stop_points']:.3f} points (${result['realized_risk_dollars']:.2f})")
    print(f"Target: {result['target_points']:.3f} points (${result['realized_reward_dollars']:.2f})")
    print()
    print(f"Theoretical RR: {result['theoretical_rr']:.3f}")
    print(f"Realized RR: {result['realized_rr']:.3f}")
    print(f"Delta: {result['delta_rr']:+.3f} ({result['delta_pct']:+.1f}%)")
    print()

    # Test expectancy
    win_rate = 0.691  # 69.1% from validation
    expectancy = calculate_expectancy(win_rate, result['realized_rr'])
    print(f"Win Rate: {win_rate*100:.1f}%")
    print(f"Expectancy: {expectancy:+.3f}R")
    print()

    # Test position sizing
    account_equity = 50000
    risk_pct = 0.01  # 1%
    position_size = calculate_position_size(
        account_equity,
        risk_pct,
        result['realized_risk_dollars']
    )
    print(f"Account: ${account_equity:,.0f}")
    print(f"Risk: {risk_pct*100:.1f}% (${account_equity*risk_pct:,.0f})")
    print(f"Position Size: {position_size} contracts")
    print()
