"""
DRAWDOWN ENGINE - Pure Calculation Logic

Calculates drawdown floors, high water marks, and effective capital.
Implements three drawdown models:
- STATIC: Floor never moves
- TRAILING_INTRADAY: Floor trails with real-time balance increases
- TRAILING_EOD: Floor updates only at end of day

CRITICAL: This module is PURE - no state, no I/O, no side effects.
All validation checks included to catch drift/bugs.

Reference: docs/PROP_FIRM_MANAGER_REQUIREMENTS.md (Architecture)
"""

from dataclasses import dataclass, field
from typing import Literal
from enum import Enum


# =============================================================================
# TYPE DEFINITIONS
# =============================================================================

DrawdownModel = Literal['STATIC', 'TRAILING_INTRADAY', 'TRAILING_EOD']
BreachRiskLevel = Literal['SAFE', 'WARNING', 'DANGER', 'CRITICAL']


class DrawdownModelEnum(str, Enum):
    """Enum for drawdown models (for validation)"""
    STATIC = 'STATIC'
    TRAILING_INTRADAY = 'TRAILING_INTRADAY'
    TRAILING_EOD = 'TRAILING_EOD'


# =============================================================================
# INPUT CONTRACT
# =============================================================================

@dataclass(frozen=True)
class DrawdownRequest:
    """
    Input contract for drawdown calculation.

    All fields immutable (frozen=True) to enforce purity.
    """
    drawdown_model: DrawdownModel
    starting_balance: float
    max_drawdown_size: float
    current_balance: float
    high_water_mark: float
    previous_close_balance: float | None = None
    is_intraday: bool = True

    def __post_init__(self):
        """Validate input constraints"""
        # Validate model
        if self.drawdown_model not in [m.value for m in DrawdownModelEnum]:
            raise ValueError(
                f"Invalid drawdown_model: {self.drawdown_model}. "
                f"Must be one of: {[m.value for m in DrawdownModelEnum]}"
            )

        # Validate positive values
        if self.starting_balance <= 0:
            raise ValueError(f"starting_balance must be positive: {self.starting_balance}")

        if self.max_drawdown_size <= 0:
            raise ValueError(f"max_drawdown_size must be positive: {self.max_drawdown_size}")

        if self.current_balance < 0:
            raise ValueError(f"current_balance cannot be negative: {self.current_balance}")

        if self.high_water_mark < self.starting_balance:
            raise ValueError(
                f"high_water_mark ({self.high_water_mark}) cannot be below "
                f"starting_balance ({self.starting_balance})"
            )

        # Validate EOD model requirements
        if self.drawdown_model == 'TRAILING_EOD' and self.previous_close_balance is None:
            raise ValueError(
                "TRAILING_EOD model requires previous_close_balance"
            )

        # Sanity check: current balance shouldn't massively exceed HWM (likely data error)
        if self.current_balance > self.high_water_mark * 10:
            raise ValueError(
                f"current_balance ({self.current_balance}) is 10x higher than HWM "
                f"({self.high_water_mark}) - likely data error"
            )


# =============================================================================
# OUTPUT CONTRACT
# =============================================================================

@dataclass(frozen=True)
class DrawdownResult:
    """
    Output contract for drawdown calculation.

    All fields immutable (frozen=True) to prevent mutation.
    """
    drawdown_floor: float
    effective_capital: float
    distance_to_breach: float
    new_high_water_mark: float
    breach_risk_level: BreachRiskLevel
    calculation_metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        """Validate output constraints (drift detection)"""
        # Check 1: Effective capital must be non-negative
        if self.effective_capital < 0:
            raise ValueError(
                f"DRIFT DETECTED: effective_capital is negative: {self.effective_capital}. "
                f"This indicates a calculation bug in DrawdownEngine."
            )

        # Check 2: Distance to breach equals effective capital (redundancy check)
        if abs(self.distance_to_breach - self.effective_capital) > 0.01:
            raise ValueError(
                f"DRIFT DETECTED: distance_to_breach ({self.distance_to_breach}) != "
                f"effective_capital ({self.effective_capital}). Formula inconsistency."
            )

        # Check 3: Breach risk level must be valid
        valid_levels = ['SAFE', 'WARNING', 'DANGER', 'CRITICAL']
        if self.breach_risk_level not in valid_levels:
            raise ValueError(
                f"Invalid breach_risk_level: {self.breach_risk_level}. "
                f"Must be one of: {valid_levels}"
            )

        # Check 4: Floor must not exceed HWM (sanity check)
        if self.drawdown_floor > self.new_high_water_mark:
            raise ValueError(
                f"DRIFT DETECTED: drawdown_floor ({self.drawdown_floor}) exceeds "
                f"new_high_water_mark ({self.new_high_water_mark})"
            )


# =============================================================================
# CORE CALCULATION FUNCTIONS (PURE)
# =============================================================================

def calculate_drawdown(request: DrawdownRequest) -> DrawdownResult:
    """
    Calculate drawdown floor, effective capital, and breach risk.

    PURE FUNCTION: No side effects, deterministic output.

    Args:
        request: DrawdownRequest with all required inputs

    Returns:
        DrawdownResult with calculated values

    Raises:
        ValueError: If inputs violate constraints or drift detected

    Examples:
        >>> req = DrawdownRequest(
        ...     drawdown_model='STATIC',
        ...     starting_balance=50000,
        ...     max_drawdown_size=2000,
        ...     current_balance=48500,
        ...     high_water_mark=50000
        ... )
        >>> result = calculate_drawdown(req)
        >>> result.drawdown_floor
        48000.0
        >>> result.effective_capital
        500.0
    """
    # Route to appropriate model
    if request.drawdown_model == 'STATIC':
        return _calculate_static(request)
    elif request.drawdown_model == 'TRAILING_INTRADAY':
        return _calculate_trailing_intraday(request)
    elif request.drawdown_model == 'TRAILING_EOD':
        return _calculate_trailing_eod(request)
    else:
        # Should never reach here (caught in __post_init__)
        raise ValueError(f"Unknown drawdown model: {request.drawdown_model}")


def _calculate_static(request: DrawdownRequest) -> DrawdownResult:
    """
    STATIC drawdown model: Floor never moves.

    Used for: Personal accounts (no prop firm rules)

    Logic:
        - Floor = starting_balance - max_drawdown_size
        - HWM never updates
        - Effective capital = current_balance - floor

    Example:
        Starting: $50k, Max DD: $2k
        Floor: $48k (constant)
        Balance at $49k → Eff Capital = $1k
        Balance at $52k → Eff Capital = $4k (floor unchanged)
    """
    drawdown_floor = request.starting_balance - request.max_drawdown_size
    new_high_water_mark = request.high_water_mark  # Never changes

    effective_capital = max(0.0, request.current_balance - drawdown_floor)
    distance_to_breach = effective_capital

    breach_risk_level = _determine_breach_risk_level(distance_to_breach)

    metadata = {
        'model_used': 'STATIC',
        'hwm_updated': False,
        'formula': f'floor = {request.starting_balance} - {request.max_drawdown_size}',
        'floor_constant': True
    }

    result = DrawdownResult(
        drawdown_floor=drawdown_floor,
        effective_capital=effective_capital,
        distance_to_breach=distance_to_breach,
        new_high_water_mark=new_high_water_mark,
        breach_risk_level=breach_risk_level,
        calculation_metadata=metadata
    )

    # Additional validation for STATIC model
    if new_high_water_mark != request.high_water_mark:
        raise ValueError(
            f"DRIFT DETECTED: STATIC model changed HWM from {request.high_water_mark} "
            f"to {new_high_water_mark}"
        )

    return result


def _calculate_trailing_intraday(request: DrawdownRequest) -> DrawdownResult:
    """
    TRAILING_INTRADAY drawdown model: Floor trails with balance increases.

    Used for: MFF Rapid plans, prop firms with real-time trailing

    Logic:
        - HWM = max(current HWM, current_balance)
        - Floor = HWM - max_drawdown_size
        - Effective capital = current_balance - floor

    Example (The "Ghost Drawdown"):
        Start: Balance=$50k, HWM=$50k, Floor=$48k, Eff Cap=$2k
        Trade to $51k: HWM=$51k, Floor=$49k, Eff Cap=$2k
        Drop to $50k: HWM=$51k, Floor=$49k, Eff Cap=$1k (SHRUNK!)

    Critical Insight: Even though balance returned to $50k, effective
    capital REDUCED from $2k to $1k because floor trailed up.
    """
    # Update HWM (takes maximum)
    new_high_water_mark = max(request.high_water_mark, request.current_balance)
    hwm_updated = new_high_water_mark > request.high_water_mark

    # Floor trails the HWM
    drawdown_floor = new_high_water_mark - request.max_drawdown_size

    effective_capital = max(0.0, request.current_balance - drawdown_floor)
    distance_to_breach = effective_capital

    breach_risk_level = _determine_breach_risk_level(distance_to_breach)

    metadata = {
        'model_used': 'TRAILING_INTRADAY',
        'hwm_updated': hwm_updated,
        'formula': f'floor = max({request.high_water_mark}, {request.current_balance}) - {request.max_drawdown_size}',
        'previous_hwm': request.high_water_mark,
        'hwm_increase': new_high_water_mark - request.high_water_mark if hwm_updated else 0.0
    }

    result = DrawdownResult(
        drawdown_floor=drawdown_floor,
        effective_capital=effective_capital,
        distance_to_breach=distance_to_breach,
        new_high_water_mark=new_high_water_mark,
        breach_risk_level=breach_risk_level,
        calculation_metadata=metadata
    )

    # Validation: HWM must be monotonic increasing
    if new_high_water_mark < request.high_water_mark:
        raise ValueError(
            f"DRIFT DETECTED: HWM decreased from {request.high_water_mark} "
            f"to {new_high_water_mark} in TRAILING_INTRADAY model"
        )

    return result


def _calculate_trailing_eod(request: DrawdownRequest) -> DrawdownResult:
    """
    TRAILING_EOD drawdown model: Floor updates only at end of day.

    Used for: Topstep standard plans

    Logic:
        DURING TRADING SESSION (is_intraday=True):
            - Floor based on previous close
            - HWM not updated yet

        END OF DAY (is_intraday=False):
            - Update HWM to max(HWM, current_balance)
            - Floor = HWM - max_drawdown_size

    Example:
        Yesterday close: $50k
        Today intraday: Balance goes to $51k
            → Floor still $48k (based on yesterday)
            → Eff Cap = $51k - $48k = $3k

        Today EOD: Balance = $50.5k
            → Update HWM to $50.5k
            → Floor = $50.5k - $2k = $48.5k
            → Tomorrow's floor is $48.5k
    """
    if is_intraday := request.is_intraday:
        # During session: use previous close for floor calculation
        if request.previous_close_balance is None:
            raise ValueError(
                "TRAILING_EOD model requires previous_close_balance for intraday calculation"
            )

        # Floor based on yesterday's close
        base_balance = request.previous_close_balance
        drawdown_floor = base_balance - request.max_drawdown_size

        # HWM not updated during session
        new_high_water_mark = request.high_water_mark
        hwm_updated = False

    else:
        # End of day: update HWM and recalculate floor
        new_high_water_mark = max(request.high_water_mark, request.current_balance)
        hwm_updated = new_high_water_mark > request.high_water_mark

        drawdown_floor = new_high_water_mark - request.max_drawdown_size

    effective_capital = max(0.0, request.current_balance - drawdown_floor)
    distance_to_breach = effective_capital

    breach_risk_level = _determine_breach_risk_level(distance_to_breach)

    metadata = {
        'model_used': 'TRAILING_EOD',
        'hwm_updated': hwm_updated,
        'is_intraday': is_intraday,
        'formula': (
            f"floor = {request.previous_close_balance} - {request.max_drawdown_size} (intraday)"
            if is_intraday
            else f"floor = max({request.high_water_mark}, {request.current_balance}) - {request.max_drawdown_size} (EOD)"
        ),
        'floor_update_pending': is_intraday
    }

    result = DrawdownResult(
        drawdown_floor=drawdown_floor,
        effective_capital=effective_capital,
        distance_to_breach=distance_to_breach,
        new_high_water_mark=new_high_water_mark,
        breach_risk_level=breach_risk_level,
        calculation_metadata=metadata
    )

    # Validation: HWM must be monotonic
    if new_high_water_mark < request.high_water_mark:
        raise ValueError(
            f"DRIFT DETECTED: HWM decreased from {request.high_water_mark} "
            f"to {new_high_water_mark} in TRAILING_EOD model"
        )

    # Validation: During intraday, HWM should not change
    if is_intraday and hwm_updated:
        raise ValueError(
            f"DRIFT DETECTED: HWM updated during intraday in TRAILING_EOD model "
            f"(should only update at EOD)"
        )

    return result


def _determine_breach_risk_level(distance_to_breach: float) -> BreachRiskLevel:
    """
    Determine breach risk level based on distance to floor.

    Thresholds (from architecture):
        < $100: CRITICAL (imminent breach)
        < $500: DANGER (very risky)
        < $1000: WARNING (caution zone)
        >= $1000: SAFE (comfortable cushion)

    Args:
        distance_to_breach: Distance from current balance to floor

    Returns:
        BreachRiskLevel enum value
    """
    if distance_to_breach < 100:
        return 'CRITICAL'
    elif distance_to_breach < 500:
        return 'DANGER'
    elif distance_to_breach < 1000:
        return 'WARNING'
    else:
        return 'SAFE'


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def calculate_ghost_drawdown_effect(
    starting_balance: float,
    max_drawdown_size: float,
    peak_balance: float,
    current_balance: float
) -> dict:
    """
    Calculate the "Ghost Drawdown" effect for education/visualization.

    Shows how effective capital shrinks even if balance returns to starting point.

    Args:
        starting_balance: Initial account balance
        max_drawdown_size: Maximum allowed drawdown
        peak_balance: Highest balance reached
        current_balance: Current balance (after peak)

    Returns:
        Dict with ghost drawdown analysis

    Example:
        >>> effect = calculate_ghost_drawdown_effect(
        ...     starting_balance=50000,
        ...     max_drawdown_size=2000,
        ...     peak_balance=51900,
        ...     current_balance=50000
        ... )
        >>> effect['effective_capital_initial']
        2000.0
        >>> effect['effective_capital_after_peak']
        100.0
        >>> effect['ghost_effect']
        'Effective capital reduced by $1900 despite returning to starting balance'
    """
    # Initial state
    initial_floor = starting_balance - max_drawdown_size
    initial_eff_cap = starting_balance - initial_floor

    # After reaching peak
    peak_floor = peak_balance - max_drawdown_size
    eff_cap_after_peak = current_balance - peak_floor

    # Calculate ghost effect
    ghost_reduction = initial_eff_cap - eff_cap_after_peak

    return {
        'starting_balance': starting_balance,
        'max_drawdown_size': max_drawdown_size,
        'peak_balance': peak_balance,
        'current_balance': current_balance,
        'initial_floor': initial_floor,
        'initial_effective_capital': initial_eff_cap,
        'peak_floor': peak_floor,
        'effective_capital_after_peak': max(0.0, eff_cap_after_peak),
        'ghost_reduction': ghost_reduction,
        'ghost_effect_pct': (ghost_reduction / initial_eff_cap * 100) if initial_eff_cap > 0 else 0,
        'ghost_effect': (
            f"Effective capital reduced by ${ghost_reduction:.2f} "
            f"despite returning to starting balance"
        )
    }


def validate_drawdown_consistency(
    request: DrawdownRequest,
    result: DrawdownResult
) -> list[str]:
    """
    Validate consistency between request and result (drift detection).

    Returns list of validation errors (empty if valid).

    This is called by ValidationEngine to catch drift/bugs.
    """
    errors = []

    # Check 1: Effective capital must be non-negative
    if result.effective_capital < 0:
        errors.append(
            f"Effective capital is negative: {result.effective_capital}"
        )

    # Check 2: HWM must be >= starting balance
    if result.new_high_water_mark < request.starting_balance:
        errors.append(
            f"HWM ({result.new_high_water_mark}) below starting balance "
            f"({request.starting_balance})"
        )

    # Check 3: HWM must be monotonic increasing
    if result.new_high_water_mark < request.high_water_mark:
        errors.append(
            f"HWM decreased from {request.high_water_mark} to "
            f"{result.new_high_water_mark}"
        )

    # Check 4: Floor must not exceed current balance (unless breached)
    if result.drawdown_floor > request.current_balance and result.effective_capital != 0:
        errors.append(
            f"Floor ({result.drawdown_floor}) exceeds balance "
            f"({request.current_balance}) but effective capital not zero"
        )

    # Check 5: Distance to breach equals effective capital
    if abs(result.distance_to_breach - result.effective_capital) > 0.01:
        errors.append(
            f"Distance to breach ({result.distance_to_breach}) != "
            f"effective capital ({result.effective_capital})"
        )

    # Check 6: Breach risk level matches distance
    expected_level = _determine_breach_risk_level(result.distance_to_breach)
    if result.breach_risk_level != expected_level:
        errors.append(
            f"Breach risk level mismatch: got {result.breach_risk_level}, "
            f"expected {expected_level} for distance {result.distance_to_breach}"
        )

    # Check 7: Model-specific validations
    if request.drawdown_model == 'STATIC':
        if result.new_high_water_mark != request.high_water_mark:
            errors.append(
                f"STATIC model changed HWM (should be constant)"
            )

    elif request.drawdown_model == 'TRAILING_EOD':
        if request.is_intraday and result.new_high_water_mark != request.high_water_mark:
            errors.append(
                f"TRAILING_EOD model updated HWM during intraday (should wait until EOD)"
            )

    return errors


# =============================================================================
# MODULE TESTING (for verification)
# =============================================================================

def run_module_tests() -> bool:
    """
    Run basic module tests to verify calculations.

    Returns True if all tests pass, False otherwise.

    These tests implement mastervalid.txt scenarios.
    """
    print("=" * 70)
    print("DrawdownEngine Module Tests")
    print("=" * 70)

    all_passed = True

    # Test 1: STATIC model
    print("\nTest 1: STATIC model")
    try:
        req = DrawdownRequest(
            drawdown_model='STATIC',
            starting_balance=50000,
            max_drawdown_size=2000,
            current_balance=48500,
            high_water_mark=50000
        )
        result = calculate_drawdown(req)

        assert result.drawdown_floor == 48000
        assert result.effective_capital == 500
        assert result.new_high_water_mark == 50000  # Unchanged

        print("[PASS] STATIC model calculations correct")
    except AssertionError as e:
        print(f"[FAIL] {e}")
        all_passed = False

    # Test 2: TRAILING_INTRADAY - Ghost Drawdown (mastervalid.txt 4.1)
    print("\nTest 2: TRAILING_INTRADAY - Ghost Drawdown")
    try:
        # Initial state
        req1 = DrawdownRequest(
            drawdown_model='TRAILING_INTRADAY',
            starting_balance=50000,
            max_drawdown_size=2000,
            current_balance=50000,
            high_water_mark=50000
        )
        result1 = calculate_drawdown(req1)
        assert result1.effective_capital == 2000  # Initial

        # Balance goes to $51,900
        req2 = DrawdownRequest(
            drawdown_model='TRAILING_INTRADAY',
            starting_balance=50000,
            max_drawdown_size=2000,
            current_balance=51900,
            high_water_mark=result1.new_high_water_mark
        )
        result2 = calculate_drawdown(req2)
        assert result2.new_high_water_mark == 51900
        assert result2.drawdown_floor == 49900

        # Balance drops back to $50,000
        req3 = DrawdownRequest(
            drawdown_model='TRAILING_INTRADAY',
            starting_balance=50000,
            max_drawdown_size=2000,
            current_balance=50000,
            high_water_mark=result2.new_high_water_mark
        )
        result3 = calculate_drawdown(req3)

        # CRITICAL TEST: Effective capital should be $100, NOT $2000
        assert result3.effective_capital == 100, f"Expected 100, got {result3.effective_capital}"
        assert result3.drawdown_floor == 49900  # Floor stayed at peak

        print("[PASS] Ghost Drawdown calculation correct (mastervalid.txt 4.1)")
    except AssertionError as e:
        print(f"[FAIL] {e}")
        all_passed = False

    # Test 3: TRAILING_EOD - Intraday vs EOD
    print("\nTest 3: TRAILING_EOD - Intraday vs EOD")
    try:
        # Intraday: Floor based on previous close
        req_intraday = DrawdownRequest(
            drawdown_model='TRAILING_EOD',
            starting_balance=50000,
            max_drawdown_size=2000,
            current_balance=51000,  # Up $1k intraday
            high_water_mark=50000,
            previous_close_balance=50000,
            is_intraday=True
        )
        result_intraday = calculate_drawdown(req_intraday)

        assert result_intraday.drawdown_floor == 48000  # Based on previous close
        assert result_intraday.new_high_water_mark == 50000  # Not updated yet
        assert result_intraday.effective_capital == 3000  # 51000 - 48000

        # EOD: Update HWM and floor
        req_eod = DrawdownRequest(
            drawdown_model='TRAILING_EOD',
            starting_balance=50000,
            max_drawdown_size=2000,
            current_balance=50500,  # Close at $50.5k
            high_water_mark=50000,
            previous_close_balance=50000,
            is_intraday=False
        )
        result_eod = calculate_drawdown(req_eod)

        assert result_eod.new_high_water_mark == 50500  # Updated
        assert result_eod.drawdown_floor == 48500  # New floor for tomorrow

        print("[PASS] TRAILING_EOD intraday/EOD logic correct")
    except AssertionError as e:
        print(f"[FAIL] {e}")
        all_passed = False

    # Test 4: Breach risk levels
    print("\nTest 4: Breach risk levels")
    try:
        assert _determine_breach_risk_level(50) == 'CRITICAL'
        assert _determine_breach_risk_level(250) == 'DANGER'
        assert _determine_breach_risk_level(750) == 'WARNING'
        assert _determine_breach_risk_level(1500) == 'SAFE'

        print("[PASS] Breach risk level thresholds correct")
    except AssertionError as e:
        print(f"[FAIL] {e}")
        all_passed = False

    # Test 5: Ghost drawdown effect calculation
    print("\nTest 5: Ghost drawdown effect")
    try:
        effect = calculate_ghost_drawdown_effect(
            starting_balance=50000,
            max_drawdown_size=2000,
            peak_balance=51900,
            current_balance=50000
        )

        assert effect['initial_effective_capital'] == 2000
        assert effect['effective_capital_after_peak'] == 100
        assert effect['ghost_reduction'] == 1900

        print("[PASS] Ghost drawdown effect calculation correct")
    except AssertionError as e:
        print(f"[FAIL] {e}")
        all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
    print("=" * 70)

    return all_passed


if __name__ == "__main__":
    # Run module tests when executed directly
    success = run_module_tests()
    exit(0 if success else 1)
