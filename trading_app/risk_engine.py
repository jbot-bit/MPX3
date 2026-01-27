"""
RiskEngine - Risk of Ruin (RoR) calculation and position sizing for prop firm accounts.

Pure calculation module with zero state, zero I/O, deterministic output.

Addresses mastervalid.txt test 4.2:
    "40% win rate, 1.5:1 payoff, 10% risk per trade → RoR ~100%, block/warn user"

Key Concepts:
- Risk of Ruin (RoR): Probability of hitting drawdown limit before profit target
- Effective Capital: Real available capital (from DrawdownEngine)
- Position Sizing: Uses effective capital, not balance
- Kelly Criterion: Optimal bet sizing for edge preservation

Integration:
    DrawdownEngine → effective_capital
           ↓
    RiskEngine → position_size, RoR
           ↓
    MemoryIntegration → enhanced risk insights

Architecture:
    - Pure functional (immutable inputs/outputs)
    - Contract-first (dataclasses with frozen=True)
    - Composable (takes DrawdownResult, outputs RiskResult)
    - AI-ready (can be enhanced by MemoryIntegration)

Usage:
    from trading_app.risk_engine import calculate_risk, RiskRequest
    from trading_app.drawdown_engine import DrawdownResult

    request = RiskRequest(
        effective_capital=500.0,
        risk_percent=0.01,  # 1%
        win_rate=0.55,
        payoff_ratio=2.0,
        stop_distance_points=0.50,
        point_value=10.0
    )

    result = calculate_risk(request)

    if result.risk_level == 'CRITICAL':
        print("DO NOT TRADE - Risk of Ruin too high!")

    print(f"Position Size: {result.position_size} contracts")
    print(f"Risk of Ruin: {result.risk_of_ruin:.2%}")

Author: Claude Sonnet 4.5
Created: 2026-01-26
Module: Prop Firm Manager (Step 1: RiskEngine)
"""

from dataclasses import dataclass, field
from typing import Literal
import math


# =============================================================================
# TYPE DEFINITIONS
# =============================================================================

RiskLevel = Literal['SAFE', 'ACCEPTABLE', 'ELEVATED', 'HIGH', 'CRITICAL']


# =============================================================================
# INPUT/OUTPUT CONTRACTS
# =============================================================================

@dataclass(frozen=True)
class RiskRequest:
    """
    Input contract for risk calculation.

    All values must be positive. Effective capital comes from DrawdownEngine.
    """
    # Capital
    effective_capital: float  # From DrawdownEngine, NOT balance
    risk_percent: float  # e.g., 0.01 for 1%, 0.02 for 2%

    # Setup statistics (from validated_setups)
    win_rate: float  # e.g., 0.55 for 55%
    payoff_ratio: float  # e.g., 2.0 for 2:1 RR

    # Trade parameters
    stop_distance_points: float  # e.g., 0.50 for MGC
    point_value: float  # e.g., 10.0 for MGC ($10/point)

    # Optional: Advanced parameters
    profit_target_multiplier: float = 1.0  # For calculating RoR to profit target
    commission_per_contract: float = 0.0  # Round-trip commission
    slippage_per_contract: float = 0.0  # Expected slippage cost


@dataclass(frozen=True)
class RiskResult:
    """
    Output contract for risk calculation.

    Contains position sizing, Risk of Ruin, Kelly fraction, and risk assessment.
    """
    # Position sizing
    position_size: int  # Number of contracts to trade
    risk_dollars: float  # Dollar risk for this trade
    max_loss: float  # Maximum loss if stopped out (including costs)

    # Risk of Ruin
    risk_of_ruin: float  # Probability of hitting drawdown limit (0.0 to 1.0)
    risk_of_ruin_percent: float  # Same as above, in percentage (0 to 100)
    num_losses_to_ruin: int  # Number of consecutive losses to hit limit

    # Kelly Criterion
    kelly_fraction: float  # Optimal bet size per Kelly (can be negative if no edge)
    kelly_position_size: int  # Position size if using full Kelly
    using_fractional_kelly: bool  # True if actual < Kelly (safer)

    # Risk assessment
    risk_level: RiskLevel  # 'SAFE' | 'ACCEPTABLE' | 'ELEVATED' | 'HIGH' | 'CRITICAL'
    risk_message: str  # Human-readable risk assessment
    warnings: list[str] = field(default_factory=list)

    # Metadata
    calculation_metadata: dict = field(default_factory=dict)


# =============================================================================
# CORE CALCULATION ENGINE
# =============================================================================

def calculate_risk(request: RiskRequest) -> RiskResult:
    """
    Main entry point: Calculate Risk of Ruin and position sizing.

    Validates inputs, calculates position size, RoR, Kelly fraction,
    and assesses overall risk level.

    Args:
        request: RiskRequest with all parameters

    Returns:
        RiskResult with position sizing and risk assessment

    Raises:
        ValueError: If inputs are invalid (negative values, invalid percentages)
    """
    # Validate inputs
    _validate_risk_request(request)

    # Calculate position size
    position_size, risk_dollars = _calculate_position_size(request)

    # Calculate max loss (including costs)
    max_loss = _calculate_max_loss(
        position_size=position_size,
        stop_distance_points=request.stop_distance_points,
        point_value=request.point_value,
        commission_per_contract=request.commission_per_contract,
        slippage_per_contract=request.slippage_per_contract
    )

    # Calculate Risk of Ruin
    ror, num_losses = _calculate_risk_of_ruin(
        effective_capital=request.effective_capital,
        risk_per_trade=max_loss,
        win_rate=request.win_rate,
        payoff_ratio=request.payoff_ratio,
        profit_target_multiplier=request.profit_target_multiplier
    )

    # Calculate Kelly Criterion
    kelly_fraction = _calculate_kelly_fraction(
        win_rate=request.win_rate,
        payoff_ratio=request.payoff_ratio
    )

    kelly_position_size = _kelly_position_size(
        effective_capital=request.effective_capital,
        kelly_fraction=kelly_fraction,
        stop_distance_points=request.stop_distance_points,
        point_value=request.point_value
    )

    using_fractional_kelly = position_size < kelly_position_size

    # Determine risk level
    risk_level = _determine_risk_level(ror, request.risk_percent, kelly_fraction)

    # Generate warnings
    warnings = _generate_warnings(
        request=request,
        ror=ror,
        kelly_fraction=kelly_fraction,
        num_losses=num_losses,
        position_size=position_size
    )

    # Generate risk message
    risk_message = _generate_risk_message(risk_level, ror, num_losses)

    # Build metadata
    metadata = {
        'edge': (request.win_rate * request.payoff_ratio) - (1 - request.win_rate),
        'expected_value_per_dollar': (request.win_rate * request.payoff_ratio) - (1 - request.win_rate),
        'risk_reward_ratio': request.payoff_ratio,
        'win_rate': request.win_rate,
        'effective_capital': request.effective_capital,
        'risk_percent': request.risk_percent,
        'kelly_fraction': kelly_fraction
    }

    return RiskResult(
        position_size=position_size,
        risk_dollars=risk_dollars,
        max_loss=max_loss,
        risk_of_ruin=ror,
        risk_of_ruin_percent=ror * 100,
        num_losses_to_ruin=num_losses,
        kelly_fraction=kelly_fraction,
        kelly_position_size=kelly_position_size,
        using_fractional_kelly=using_fractional_kelly,
        risk_level=risk_level,
        risk_message=risk_message,
        warnings=warnings,
        calculation_metadata=metadata
    )


# =============================================================================
# POSITION SIZING
# =============================================================================

def _calculate_position_size(request: RiskRequest) -> tuple[int, float]:
    """
    Calculate position size based on effective capital and risk percent.

    Formula:
        risk_dollars = effective_capital * risk_percent
        risk_per_contract = stop_distance_points * point_value + commission + slippage
        position_size = floor(risk_dollars / risk_per_contract)

    Args:
        request: RiskRequest

    Returns:
        (position_size, risk_dollars) tuple
    """
    # Calculate risk in dollars
    risk_dollars = request.effective_capital * request.risk_percent

    # Calculate risk per contract
    risk_per_contract = (
        request.stop_distance_points * request.point_value +
        request.commission_per_contract +
        request.slippage_per_contract
    )

    # Position size (floor to avoid over-risking)
    position_size = int(risk_dollars / risk_per_contract)

    # Floor at 0 (can't trade negative contracts)
    position_size = max(0, position_size)

    return position_size, risk_dollars


def _calculate_max_loss(
    position_size: int,
    stop_distance_points: float,
    point_value: float,
    commission_per_contract: float,
    slippage_per_contract: float
) -> float:
    """
    Calculate maximum loss if stopped out (including all costs).

    Formula:
        max_loss = position_size * (stop_distance * point_value + commission + slippage)

    Returns:
        Maximum loss in dollars
    """
    loss_per_contract = (
        stop_distance_points * point_value +
        commission_per_contract +
        slippage_per_contract
    )

    return position_size * loss_per_contract


# =============================================================================
# RISK OF RUIN CALCULATION
# =============================================================================

def _calculate_risk_of_ruin(
    effective_capital: float,
    risk_per_trade: float,
    win_rate: float,
    payoff_ratio: float,
    profit_target_multiplier: float = 1.0
) -> tuple[float, int]:
    """
    Calculate Risk of Ruin (RoR) using the Gambler's Ruin formula.

    Answers: "What's the probability I hit my drawdown limit before my profit target?"

    Formula (Simplified):
        If no edge (expected value <= 0):
            RoR = 1.0 (certain ruin)

        Else:
            loss_ratio = (1 - win_rate) / win_rate
            num_losses_to_ruin = effective_capital / risk_per_trade
            RoR = loss_ratio ^ num_losses_to_ruin

    Args:
        effective_capital: Available capital (from DrawdownEngine)
        risk_per_trade: Dollar risk per trade (max loss)
        win_rate: Probability of winning (0.0 to 1.0)
        payoff_ratio: Reward/Risk ratio (e.g., 2.0 for 2:1)
        profit_target_multiplier: Multiplier for profit target (default 1.0)

    Returns:
        (ror, num_losses_to_ruin) tuple
    """
    # Edge calculation
    edge = (win_rate * payoff_ratio) - (1 - win_rate)

    # If no edge, RoR is 100%
    if edge <= 0:
        num_losses = int(effective_capital / risk_per_trade)
        return 1.0, num_losses

    # If risk per trade is 0, RoR is 0% (no risk)
    if risk_per_trade <= 0:
        return 0.0, 0

    # Calculate number of losses to ruin
    num_losses_to_ruin = effective_capital / risk_per_trade

    # Loss ratio (probability of loss / probability of win)
    loss_ratio = (1 - win_rate) / win_rate

    # Gambler's Ruin formula (simplified)
    # More accurate formula would involve profit target, but this is conservative
    try:
        ror = math.pow(loss_ratio, num_losses_to_ruin)
    except (OverflowError, ValueError):
        # If calculation overflows, clamp to 0.0 or 1.0
        ror = 0.0 if num_losses_to_ruin > 10 else 1.0

    # Clamp between 0 and 1
    ror = max(0.0, min(1.0, ror))

    return ror, int(num_losses_to_ruin)


# =============================================================================
# KELLY CRITERION
# =============================================================================

def _calculate_kelly_fraction(win_rate: float, payoff_ratio: float) -> float:
    """
    Calculate Kelly Criterion fraction.

    Formula:
        kelly = (win_rate * payoff_ratio - (1 - win_rate)) / payoff_ratio

    Or equivalently:
        kelly = (edge) / payoff_ratio

    Returns:
        Kelly fraction (can be negative if no edge)
    """
    edge = (win_rate * payoff_ratio) - (1 - win_rate)

    if payoff_ratio <= 0:
        return 0.0

    kelly = edge / payoff_ratio

    return kelly


def _kelly_position_size(
    effective_capital: float,
    kelly_fraction: float,
    stop_distance_points: float,
    point_value: float
) -> int:
    """
    Calculate position size if using full Kelly.

    Formula:
        kelly_dollars = effective_capital * kelly_fraction
        risk_per_contract = stop_distance_points * point_value
        kelly_position_size = floor(kelly_dollars / risk_per_contract)

    Returns:
        Position size (floor to avoid over-betting)
    """
    if kelly_fraction <= 0:
        return 0

    kelly_dollars = effective_capital * kelly_fraction
    risk_per_contract = stop_distance_points * point_value

    kelly_position_size = int(kelly_dollars / risk_per_contract)

    return max(0, kelly_position_size)


# =============================================================================
# RISK ASSESSMENT
# =============================================================================

def _determine_risk_level(
    ror: float,
    risk_percent: float,
    kelly_fraction: float
) -> RiskLevel:
    """
    Determine overall risk level based on RoR, risk %, and Kelly.

    Levels:
        CRITICAL: RoR > 50% OR no edge OR risk > 5%
        HIGH: RoR > 20% OR risk > 3%
        ELEVATED: RoR > 10% OR risk > 2%
        ACCEPTABLE: RoR > 5% OR risk > 1%
        SAFE: RoR <= 5% AND risk <= 1%

    Returns:
        RiskLevel
    """
    # CRITICAL: No edge (Kelly <= 0)
    if kelly_fraction <= 0:
        return 'CRITICAL'

    # CRITICAL: RoR > 50%
    if ror > 0.50:
        return 'CRITICAL'

    # CRITICAL: Risk > 5%
    if risk_percent > 0.05:
        return 'CRITICAL'

    # HIGH: RoR > 20%
    if ror > 0.20:
        return 'HIGH'

    # HIGH: Risk > 3%
    if risk_percent > 0.03:
        return 'HIGH'

    # ELEVATED: RoR > 10%
    if ror > 0.10:
        return 'ELEVATED'

    # ELEVATED: Risk > 2%
    if risk_percent > 0.02:
        return 'ELEVATED'

    # ACCEPTABLE: RoR > 5%
    if ror > 0.05:
        return 'ACCEPTABLE'

    # ACCEPTABLE: Risk > 1%
    if risk_percent > 0.01:
        return 'ACCEPTABLE'

    # SAFE: Everything else
    return 'SAFE'


def _generate_warnings(
    request: RiskRequest,
    ror: float,
    kelly_fraction: float,
    num_losses: int,
    position_size: int
) -> list[str]:
    """
    Generate risk warnings based on request parameters and calculated risk.

    Returns:
        List of warning strings
    """
    warnings = []

    # No edge warning
    if kelly_fraction <= 0:
        warnings.append("NO EDGE: Expected value is negative. Do not trade this setup.")

    # High RoR warning (mastervalid.txt 4.2)
    if ror > 0.50:
        warnings.append(f"RISK OF RUIN TOO HIGH: {ror:.1%} probability of account breach.")

    # Risk percent too high
    if request.risk_percent > 0.05:
        warnings.append(f"RISK TOO HIGH: {request.risk_percent:.1%} risk per trade exceeds 5% limit.")

    # Low effective capital warning
    if request.effective_capital < 500:
        warnings.append(f"LOW CAPITAL: ${request.effective_capital:.2f} effective capital. Consider skipping trade.")

    # Few losses to ruin
    if num_losses <= 3:
        warnings.append(f"DANGER: Only {num_losses} consecutive losses until account breach.")

    # Position size is 0
    if position_size == 0:
        warnings.append("CANNOT TRADE: Effective capital too low for even 1 contract.")

    # Win rate too low
    if request.win_rate < 0.40:
        warnings.append(f"LOW WIN RATE: {request.win_rate:.1%} win rate may not be sustainable.")

    return warnings


def _generate_risk_message(risk_level: RiskLevel, ror: float, num_losses: int) -> str:
    """
    Generate human-readable risk message.

    Returns:
        Risk message string
    """
    if risk_level == 'CRITICAL':
        return f"DO NOT TRADE - Risk of Ruin: {ror:.1%}, {num_losses} losses to breach"
    elif risk_level == 'HIGH':
        return f"HIGH RISK - Risk of Ruin: {ror:.1%}, {num_losses} losses to breach"
    elif risk_level == 'ELEVATED':
        return f"ELEVATED RISK - Risk of Ruin: {ror:.1%}, {num_losses} losses to breach"
    elif risk_level == 'ACCEPTABLE':
        return f"ACCEPTABLE RISK - Risk of Ruin: {ror:.1%}, {num_losses} losses to breach"
    else:  # SAFE
        return f"SAFE - Risk of Ruin: {ror:.1%}, {num_losses} losses to breach"


# =============================================================================
# VALIDATION
# =============================================================================

def _validate_risk_request(request: RiskRequest) -> None:
    """
    Validate RiskRequest inputs.

    Raises:
        ValueError: If any input is invalid
    """
    if request.effective_capital < 0:
        raise ValueError(f"effective_capital must be >= 0, got {request.effective_capital}")

    if request.risk_percent < 0 or request.risk_percent > 1.0:
        raise ValueError(f"risk_percent must be between 0 and 1.0, got {request.risk_percent}")

    if request.win_rate < 0 or request.win_rate > 1.0:
        raise ValueError(f"win_rate must be between 0 and 1.0, got {request.win_rate}")

    if request.payoff_ratio < 0:
        raise ValueError(f"payoff_ratio must be >= 0, got {request.payoff_ratio}")

    if request.stop_distance_points < 0:
        raise ValueError(f"stop_distance_points must be >= 0, got {request.stop_distance_points}")

    if request.point_value <= 0:
        raise ValueError(f"point_value must be > 0, got {request.point_value}")

    if request.profit_target_multiplier < 0:
        raise ValueError(f"profit_target_multiplier must be >= 0, got {request.profit_target_multiplier}")

    if request.commission_per_contract < 0:
        raise ValueError(f"commission_per_contract must be >= 0, got {request.commission_per_contract}")

    if request.slippage_per_contract < 0:
        raise ValueError(f"slippage_per_contract must be >= 0, got {request.slippage_per_contract}")


# =============================================================================
# TESTING & EXAMPLES
# =============================================================================

def example_mastervalid_4_2():
    """
    Example from mastervalid.txt test 4.2:
    "40% win rate, 1.5:1 payoff, 10% risk per trade → RoR ~100%, block/warn user"

    Expected: Risk level CRITICAL, warnings generated
    """
    request = RiskRequest(
        effective_capital=2000.0,
        risk_percent=0.10,  # 10% risk per trade (DANGEROUS)
        win_rate=0.40,
        payoff_ratio=1.5,
        stop_distance_points=0.50,
        point_value=10.0
    )

    result = calculate_risk(request)

    print("=" * 70)
    print("MASTERVALID.TXT TEST 4.2: Risk of Ruin Shield")
    print("=" * 70)
    print(f"Effective Capital: ${result.calculation_metadata['effective_capital']:.2f}")
    print(f"Risk Per Trade: {request.risk_percent:.1%}")
    print(f"Win Rate: {request.win_rate:.1%}")
    print(f"Payoff Ratio: {request.payoff_ratio:.1f}:1")
    print()
    print(f"Position Size: {result.position_size} contracts")
    print(f"Risk Dollars: ${result.risk_dollars:.2f}")
    print(f"Max Loss: ${result.max_loss:.2f}")
    print()
    print(f"Risk of Ruin: {result.risk_of_ruin_percent:.1f}%")
    print(f"Losses to Ruin: {result.num_losses_to_ruin}")
    print(f"Kelly Fraction: {result.kelly_fraction:.3f}")
    print()
    print(f"Risk Level: {result.risk_level}")
    print(f"Risk Message: {result.risk_message}")
    print()

    if result.warnings:
        print("WARNINGS:")
        for warning in result.warnings:
            print(f"  - {warning}")

    print()

    # Verify test passes
    assert result.risk_level == 'CRITICAL', "Test 4.2 FAILED: Risk level should be CRITICAL"
    assert len(result.warnings) > 0, "Test 4.2 FAILED: Should have warnings"
    assert result.risk_of_ruin > 0.50, "Test 4.2 FAILED: RoR should be > 50%"

    print("[PASS] mastervalid.txt test 4.2: Risk of Ruin shield working")


def example_safe_trade():
    """
    Example of a SAFE trade:
    - 1% risk per trade
    - 55% win rate
    - 2:1 payoff
    - Comfortable effective capital
    """
    request = RiskRequest(
        effective_capital=2000.0,
        risk_percent=0.01,  # 1% risk per trade
        win_rate=0.55,
        payoff_ratio=2.0,
        stop_distance_points=0.50,
        point_value=10.0
    )

    result = calculate_risk(request)

    print("=" * 70)
    print("EXAMPLE: SAFE TRADE")
    print("=" * 70)
    print(f"Effective Capital: ${result.calculation_metadata['effective_capital']:.2f}")
    print(f"Risk Per Trade: {request.risk_percent:.1%}")
    print(f"Win Rate: {request.win_rate:.1%}")
    print(f"Payoff Ratio: {request.payoff_ratio:.1f}:1")
    print()
    print(f"Position Size: {result.position_size} contracts")
    print(f"Risk Dollars: ${result.risk_dollars:.2f}")
    print(f"Max Loss: ${result.max_loss:.2f}")
    print()
    print(f"Risk of Ruin: {result.risk_of_ruin_percent:.3f}%")
    print(f"Losses to Ruin: {result.num_losses_to_ruin}")
    print(f"Kelly Fraction: {result.kelly_fraction:.3f}")
    print(f"Kelly Position: {result.kelly_position_size} contracts")
    print(f"Using Fractional Kelly: {result.using_fractional_kelly}")
    print()
    print(f"Risk Level: {result.risk_level}")
    print(f"Risk Message: {result.risk_message}")
    print()

    if result.warnings:
        print("WARNINGS:")
        for warning in result.warnings:
            print(f"  - {warning}")
    else:
        print("NO WARNINGS - Trade is safe")

    print()


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("RISK ENGINE - Pure Calculation Module")
    print("=" * 70 + "\n")

    # Run mastervalid.txt test 4.2
    example_mastervalid_4_2()

    print("\n")

    # Run safe trade example
    example_safe_trade()

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED")
    print("=" * 70 + "\n")
