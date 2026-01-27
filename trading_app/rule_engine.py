"""
RuleEngine - Prop Firm Rule Checking and Consistency Validation

Pure calculation module for prop firm specific rules (Topstep, MFFU).

Key Rules:
1. Consistency Rule (MFFU): Max day profit <= 50% of total profit
2. Benchmark Days (Topstep): Track days with >= $150 profit
3. Daily Loss Limit (Topstep): Max loss per day (resets at midnight)
4. Contract Limits (MFFU): Position size restrictions
5. Consecutive Loss Limits (Custom): Max consecutive losses allowed

Reference: propfirm.txt, fix.txt

Architecture:
    - Pure functional (immutable inputs/outputs)
    - Contract-first (dataclasses with frozen=True)
    - Composable (takes account state, outputs rule violations)
    - AI-ready (can be enhanced by MemoryIntegration)

Usage:
    from trading_app.rule_engine import check_rules, RuleRequest

    request = RuleRequest(
        account_type='MFFU',
        total_profit=3000.0,
        today_profit=1800.0,
        daily_loss_limit=1000.0,
        today_loss=0.0,
        benchmark_days=4,
        position_size=2,
        contract_limit_mini=5
    )

    result = check_rules(request)

    if result.violations:
        for violation in result.violations:
            print(f"[{violation.severity}] {violation.message}")

Author: Claude Sonnet 4.5
Created: 2026-01-26
Module: Prop Firm Manager (Step 1: RuleEngine)
"""

from dataclasses import dataclass, field
from typing import Literal
from datetime import date


# =============================================================================
# TYPE DEFINITIONS
# =============================================================================

AccountType = Literal['PERSONAL', 'TOPSTEP', 'MFFU']
ViolationSeverity = Literal['INFO', 'WARNING', 'CRITICAL', 'BLOCKING']


# =============================================================================
# INPUT/OUTPUT CONTRACTS
# =============================================================================

@dataclass(frozen=True)
class RuleRequest:
    """
    Input contract for rule checking.

    Contains account state and trade parameters.
    """
    # Account identification
    account_type: AccountType  # 'PERSONAL' | 'TOPSTEP' | 'MFFU'

    # P&L tracking
    total_profit: float  # Cumulative profit since account start
    today_profit: float  # Today's realized profit (can be negative)
    daily_loss_limit: float | None = None  # Topstep: daily loss limit
    today_loss: float = 0.0  # Today's realized loss (negative value)

    # Benchmark tracking (Topstep)
    benchmark_days: int = 0  # Days with >= $150 profit
    benchmark_target: int = 5  # Required benchmark days

    # Position limits (MFFU)
    position_size: int = 0  # Current/proposed position size
    contract_limit_mini: int | None = None
    contract_limit_micro: int | None = None
    is_mini_contract: bool = True  # True for mini, False for micro

    # Consecutive loss tracking
    consecutive_losses: int = 0
    max_consecutive_losses: int = 5

    # Optional: Trade context
    proposed_trade_pnl: float | None = None  # Estimated P&L if trade is taken


@dataclass(frozen=True)
class RuleViolation:
    """
    Single rule violation.

    Severity levels:
    - INFO: Informational (e.g., "1 more benchmark day needed")
    - WARNING: Approaching limit (e.g., "80% of daily loss limit used")
    - CRITICAL: At limit or violated (e.g., "Consistency rule violated")
    - BLOCKING: Hard block, cannot trade (e.g., "Daily loss limit hit")
    """
    rule_name: str  # 'CONSISTENCY_RULE' | 'DAILY_LOSS_LIMIT' | 'CONTRACT_LIMIT' etc.
    severity: ViolationSeverity
    message: str
    current_value: float | int | None = None
    limit_value: float | int | None = None
    recommendation: str | None = None


@dataclass(frozen=True)
class RuleResult:
    """
    Output contract for rule checking.

    Contains all violations and overall trade permission.
    """
    # Trade permission
    can_trade: bool  # True if no BLOCKING violations
    violations: list[RuleViolation] = field(default_factory=list)

    # Prop firm progress
    benchmark_days_progress: str | None = None  # "4/5 days complete"
    consistency_status: str | None = None  # "PASS" | "FAIL" | "N/A"
    daily_loss_remaining: float | None = None  # $ remaining before daily limit

    # Metadata
    calculation_metadata: dict = field(default_factory=dict)


# =============================================================================
# CORE RULE ENGINE
# =============================================================================

def check_rules(request: RuleRequest) -> RuleResult:
    """
    Main entry point: Check all prop firm rules.

    Validates inputs, checks account-specific rules, and returns violations.

    Args:
        request: RuleRequest with account state

    Returns:
        RuleResult with violations and trade permission

    Raises:
        ValueError: If inputs are invalid
    """
    # Validate inputs
    _validate_rule_request(request)

    violations = []

    # Check account-specific rules
    if request.account_type == 'MFFU':
        violations.extend(_check_mffu_rules(request))
    elif request.account_type == 'TOPSTEP':
        violations.extend(_check_topstep_rules(request))
    elif request.account_type == 'PERSONAL':
        violations.extend(_check_personal_rules(request))

    # Check universal rules
    violations.extend(_check_consecutive_loss_limit(request))

    # Determine if trading is allowed
    can_trade = not any(v.severity == 'BLOCKING' for v in violations)

    # Build metadata
    metadata = {
        'account_type': request.account_type,
        'total_profit': request.total_profit,
        'today_profit': request.today_profit,
        'violations_count': len(violations),
        'blocking_violations': sum(1 for v in violations if v.severity == 'BLOCKING')
    }

    # Build progress strings
    benchmark_progress = None
    if request.account_type == 'TOPSTEP':
        benchmark_progress = f"{request.benchmark_days}/{request.benchmark_target} days"

    consistency_status = None
    if request.account_type == 'MFFU':
        consistency_status = _get_consistency_status(request)

    daily_loss_remaining = None
    if request.daily_loss_limit:
        daily_loss_remaining = request.daily_loss_limit - abs(request.today_loss)

    return RuleResult(
        can_trade=can_trade,
        violations=violations,
        benchmark_days_progress=benchmark_progress,
        consistency_status=consistency_status,
        daily_loss_remaining=daily_loss_remaining,
        calculation_metadata=metadata
    )


# =============================================================================
# MFFU RULES
# =============================================================================

def _check_mffu_rules(request: RuleRequest) -> list[RuleViolation]:
    """
    Check My Funded Futures (MFFU) specific rules.

    Rules:
    1. Consistency Rule: Max day profit <= 50% of total profit (SOFT WARNING - not blocking)
    2. Contract Limits: Position size restrictions

    CONSISTENCY MATH CLARIFICATION:

    Two different consistency rules exist:

    A) Total-profit based (ongoing ratio check):
       - best_day / total_profit <= 0.50
       - Example: If total = $2,000, today must be <= $1,000 (to stay at 50%)
       - This is what MFFU uses (soft target)

    B) Profit-target based (evaluation phase):
       - max_day_profit = profit_target * 0.50
       - Example: If target = $3,000, best day must be <= $1,500
       - This is the initial qualification rule

    Mode: SOFT WARNING (Mode 2)
    - Violation shows CRITICAL warning (not blocking)
    - Message: "You'll need extra days to regain consistency"
    - Account NOT failed immediately (need more days to dilute the ratio)
    """
    violations = []

    # Rule 1: Consistency Rule (50% rule - SOFT WARNING)
    if request.total_profit > 0:
        max_allowed_day_profit = request.total_profit * 0.50

        if request.today_profit > max_allowed_day_profit:
            # Calculate consistency ratio (today as % of total)
            consistency_ratio = (request.today_profit / (request.total_profit + request.today_profit)) * 100

            violations.append(RuleViolation(
                rule_name='CONSISTENCY_RULE',
                severity='CRITICAL',  # WARNING but not BLOCKING
                message=f"Consistency warning: Today's profit (${request.today_profit:.2f}) exceeds 50% limit (${max_allowed_day_profit:.2f}). Ratio: {consistency_ratio:.1f}%",
                current_value=request.today_profit,
                limit_value=max_allowed_day_profit,
                recommendation="You'll need extra profitable days to regain consistency. Consider smaller positions tomorrow."
            ))

        elif request.today_profit > max_allowed_day_profit * 0.80:
            # Warning at 80% of limit
            violations.append(RuleViolation(
                rule_name='CONSISTENCY_RULE',
                severity='WARNING',
                message=f"Approaching consistency limit: ${request.today_profit:.2f} / ${max_allowed_day_profit:.2f} (80%+)",
                current_value=request.today_profit,
                limit_value=max_allowed_day_profit,
                recommendation="Consider stopping trading to preserve consistency ratio"
            ))

        # Check if proposed trade would violate
        if request.proposed_trade_pnl:
            projected_profit = request.today_profit + request.proposed_trade_pnl

            if projected_profit > max_allowed_day_profit:
                violations.append(RuleViolation(
                    rule_name='CONSISTENCY_RULE',
                    severity='BLOCKING',
                    message=f"Proposed trade would violate consistency: ${projected_profit:.2f} > ${max_allowed_day_profit:.2f}",
                    current_value=projected_profit,
                    limit_value=max_allowed_day_profit,
                    recommendation="DO NOT TAKE THIS TRADE - Would breach 50% rule"
                ))

    # Rule 2: Contract Limits
    if request.contract_limit_mini and request.is_mini_contract:
        if request.position_size > request.contract_limit_mini:
            violations.append(RuleViolation(
                rule_name='CONTRACT_LIMIT',
                severity='BLOCKING',
                message=f"Position size ({request.position_size}) exceeds mini contract limit ({request.contract_limit_mini})",
                current_value=request.position_size,
                limit_value=request.contract_limit_mini,
                recommendation=f"Reduce position to {request.contract_limit_mini} contracts"
            ))

    if request.contract_limit_micro and not request.is_mini_contract:
        if request.position_size > request.contract_limit_micro:
            violations.append(RuleViolation(
                rule_name='CONTRACT_LIMIT',
                severity='BLOCKING',
                message=f"Position size ({request.position_size}) exceeds micro contract limit ({request.contract_limit_micro})",
                current_value=request.position_size,
                limit_value=request.contract_limit_micro,
                recommendation=f"Reduce position to {request.contract_limit_micro} contracts"
            ))

    return violations


# =============================================================================
# TOPSTEP RULES
# =============================================================================

def _check_topstep_rules(request: RuleRequest) -> list[RuleViolation]:
    """
    Check Topstep specific rules.

    Rules:
    1. Daily Loss Limit: Max loss per day
    2. Benchmark Days: Track days with >= $150 profit
    """
    violations = []

    # Rule 1: Daily Loss Limit
    if request.daily_loss_limit:
        current_loss = abs(request.today_loss)

        if current_loss >= request.daily_loss_limit:
            violations.append(RuleViolation(
                rule_name='DAILY_LOSS_LIMIT',
                severity='BLOCKING',
                message=f"Daily loss limit hit: ${current_loss:.2f} / ${request.daily_loss_limit:.2f}",
                current_value=current_loss,
                limit_value=request.daily_loss_limit,
                recommendation="STOP TRADING - Daily loss limit reached"
            ))

        elif current_loss > request.daily_loss_limit * 0.80:
            # Warning at 80% of limit
            violations.append(RuleViolation(
                rule_name='DAILY_LOSS_LIMIT',
                severity='WARNING',
                message=f"Approaching daily loss limit: ${current_loss:.2f} / ${request.daily_loss_limit:.2f} (80%+)",
                current_value=current_loss,
                limit_value=request.daily_loss_limit,
                recommendation="Consider stopping trading to preserve daily limit"
            ))

        # Check if proposed trade would violate
        if request.proposed_trade_pnl and request.proposed_trade_pnl < 0:
            projected_loss = current_loss + abs(request.proposed_trade_pnl)

            if projected_loss > request.daily_loss_limit:
                violations.append(RuleViolation(
                    rule_name='DAILY_LOSS_LIMIT',
                    severity='BLOCKING',
                    message=f"Proposed trade would exceed daily loss limit: ${projected_loss:.2f} > ${request.daily_loss_limit:.2f}",
                    current_value=projected_loss,
                    limit_value=request.daily_loss_limit,
                    recommendation="DO NOT TAKE THIS TRADE - Would breach daily loss limit"
                ))

    # Rule 2: Benchmark Days Progress
    if request.benchmark_days < request.benchmark_target:
        remaining = request.benchmark_target - request.benchmark_days

        # Info if today could be a benchmark day
        if request.today_profit >= 150:
            violations.append(RuleViolation(
                rule_name='BENCHMARK_DAY',
                severity='INFO',
                message=f"Today qualifies as benchmark day! ({request.benchmark_days + 1}/{request.benchmark_target})",
                current_value=request.today_profit,
                limit_value=150.0,
                recommendation=f"{remaining - 1} more days needed" if remaining > 1 else "Last benchmark day needed!"
            ))
        else:
            violations.append(RuleViolation(
                rule_name='BENCHMARK_DAY',
                severity='INFO',
                message=f"Benchmark progress: {request.benchmark_days}/{request.benchmark_target} days (${150 - request.today_profit:.2f} more needed today)",
                current_value=request.today_profit,
                limit_value=150.0,
                recommendation=f"{remaining} more benchmark days needed"
            ))

    return violations


# =============================================================================
# PERSONAL ACCOUNT RULES
# =============================================================================

def _check_personal_rules(request: RuleRequest) -> list[RuleViolation]:
    """
    Check personal account rules (minimal - no prop firm restrictions).
    """
    violations = []

    # Personal accounts have no special rules, but could add:
    # - Self-imposed daily loss limits
    # - Risk management alerts
    # - Profit targets

    return violations


# =============================================================================
# UNIVERSAL RULES
# =============================================================================

def _check_consecutive_loss_limit(request: RuleRequest) -> list[RuleViolation]:
    """
    Check consecutive loss limit (applies to all account types).
    """
    violations = []

    if request.consecutive_losses >= request.max_consecutive_losses:
        violations.append(RuleViolation(
            rule_name='CONSECUTIVE_LOSS_LIMIT',
            severity='BLOCKING',
            message=f"Consecutive loss limit hit: {request.consecutive_losses} / {request.max_consecutive_losses}",
            current_value=request.consecutive_losses,
            limit_value=request.max_consecutive_losses,
            recommendation="STOP TRADING - Take a break and review your strategy"
        ))

    elif request.consecutive_losses >= request.max_consecutive_losses - 1:
        violations.append(RuleViolation(
            rule_name='CONSECUTIVE_LOSS_LIMIT',
            severity='WARNING',
            message=f"Approaching consecutive loss limit: {request.consecutive_losses} / {request.max_consecutive_losses}",
            current_value=request.consecutive_losses,
            limit_value=request.max_consecutive_losses,
            recommendation="Next loss will hit consecutive loss limit"
        ))

    return violations


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_consistency_status(request: RuleRequest) -> str:
    """
    Get consistency status for MFFU accounts.

    Returns:
        Status string with percentage (e.g., "PASS (35%)" or "WARN (52%)")
    """
    if request.total_profit <= 0:
        return 'N/A (No profit yet)'

    # Calculate today's profit as % of total
    total_with_today = request.total_profit + request.today_profit
    today_ratio = (request.today_profit / total_with_today) * 100 if total_with_today > 0 else 0

    max_allowed = request.total_profit * 0.50

    if request.today_profit > max_allowed:
        return f'WARN ({today_ratio:.0f}% - Over 50% limit)'
    elif request.today_profit > max_allowed * 0.80:
        return f'CAUTION ({today_ratio:.0f}% - Near limit)'
    else:
        return f'PASS ({today_ratio:.0f}%)'


# =============================================================================
# VALIDATION
# =============================================================================

def _validate_rule_request(request: RuleRequest) -> None:
    """
    Validate RuleRequest inputs.

    Raises:
        ValueError: If any input is invalid
    """
    if request.account_type not in ['PERSONAL', 'TOPSTEP', 'MFFU']:
        raise ValueError(f"Invalid account_type: {request.account_type}")

    if request.daily_loss_limit and request.daily_loss_limit < 0:
        raise ValueError(f"daily_loss_limit must be >= 0, got {request.daily_loss_limit}")

    if request.benchmark_days < 0:
        raise ValueError(f"benchmark_days must be >= 0, got {request.benchmark_days}")

    if request.benchmark_target < 0:
        raise ValueError(f"benchmark_target must be >= 0, got {request.benchmark_target}")

    if request.position_size < 0:
        raise ValueError(f"position_size must be >= 0, got {request.position_size}")

    if request.consecutive_losses < 0:
        raise ValueError(f"consecutive_losses must be >= 0, got {request.consecutive_losses}")

    if request.max_consecutive_losses <= 0:
        raise ValueError(f"max_consecutive_losses must be > 0, got {request.max_consecutive_losses}")


# =============================================================================
# TESTING & EXAMPLES
# =============================================================================

def example_mffu_consistency_rule():
    """
    Example: MFFU consistency rule (50% rule).

    Scenario: Total profit $3000, today profit $1800 (60% - VIOLATION)
    """
    request = RuleRequest(
        account_type='MFFU',
        total_profit=3000.0,
        today_profit=1800.0,  # 60% of total - VIOLATES 50% rule
        position_size=2,
        contract_limit_mini=5
    )

    result = check_rules(request)

    print("=" * 70)
    print("MFFU CONSISTENCY RULE TEST")
    print("=" * 70)
    print(f"Total Profit: ${request.total_profit:.2f}")
    print(f"Today Profit: ${request.today_profit:.2f}")
    print(f"Max Allowed: ${request.total_profit * 0.50:.2f} (50%)")
    print()
    print(f"Can Trade: {result.can_trade}")
    print(f"Consistency Status: {result.consistency_status}")
    print(f"Violations: {len(result.violations)}")
    print()

    for violation in result.violations:
        print(f"[{violation.severity}] {violation.rule_name}")
        print(f"  {violation.message}")
        if violation.recommendation:
            print(f"  -> {violation.recommendation}")
        print()

    # With soft warning, can_trade should be True (CRITICAL but not BLOCKING)
    assert result.can_trade, "Should allow trading (soft warning mode)"
    assert 'WARN' in result.consistency_status, "Should show WARN status"
    assert len(result.violations) == 1, "Should have 1 violation"
    assert result.violations[0].severity == 'CRITICAL', "Should be CRITICAL severity"
    print("[PASS] MFFU consistency rule working (soft warning mode)")


def example_topstep_daily_loss_limit():
    """
    Example: Topstep daily loss limit.

    Scenario: Daily loss limit $1000, current loss $950 (95% - WARNING)
    """
    request = RuleRequest(
        account_type='TOPSTEP',
        total_profit=2000.0,
        today_profit=-950.0,
        today_loss=-950.0,
        daily_loss_limit=1000.0,
        benchmark_days=3,
        benchmark_target=5
    )

    result = check_rules(request)

    print("=" * 70)
    print("TOPSTEP DAILY LOSS LIMIT TEST")
    print("=" * 70)
    print(f"Daily Loss Limit: ${request.daily_loss_limit:.2f}")
    print(f"Today Loss: ${abs(request.today_loss):.2f}")
    print(f"Remaining: ${result.daily_loss_remaining:.2f}")
    print()
    print(f"Can Trade: {result.can_trade}")
    print(f"Benchmark Progress: {result.benchmark_days_progress}")
    print(f"Violations: {len(result.violations)}")
    print()

    for violation in result.violations:
        print(f"[{violation.severity}] {violation.rule_name}")
        print(f"  {violation.message}")
        if violation.recommendation:
            print(f"  -> {violation.recommendation}")
        print()

    assert result.can_trade, "Should be able to trade (not at limit yet)"
    assert any(v.severity == 'WARNING' for v in result.violations), "Should have warning"
    print("[PASS] Topstep daily loss limit working")


def example_personal_account():
    """
    Example: Personal account (no prop firm rules).

    Scenario: Just consecutive loss tracking
    """
    request = RuleRequest(
        account_type='PERSONAL',
        total_profit=-500.0,
        today_profit=-200.0,
        consecutive_losses=4,
        max_consecutive_losses=5
    )

    result = check_rules(request)

    print("=" * 70)
    print("PERSONAL ACCOUNT TEST")
    print("=" * 70)
    print(f"Consecutive Losses: {request.consecutive_losses} / {request.max_consecutive_losses}")
    print()
    print(f"Can Trade: {result.can_trade}")
    print(f"Violations: {len(result.violations)}")
    print()

    for violation in result.violations:
        print(f"[{violation.severity}] {violation.rule_name}")
        print(f"  {violation.message}")
        if violation.recommendation:
            print(f"  -> {violation.recommendation}")
        print()

    assert result.can_trade, "Should be able to trade (not at limit yet)"
    print("[PASS] Personal account rules working")


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("RULE ENGINE - Pure Calculation Module")
    print("=" * 70 + "\n")

    # Run tests
    example_mffu_consistency_rule()
    print("\n")
    example_topstep_daily_loss_limit()
    print("\n")
    example_personal_account()

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED")
    print("=" * 70 + "\n")
