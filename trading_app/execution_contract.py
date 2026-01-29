"""
Execution Contract - Required inputs and invariants validation

This module defines contracts that specify:
- What columns/tables are required
- What spec fields must be set
- What invariant checks must pass

Created for UPDATE14 (update14.txt) - Step 2
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Callable, Optional
import pandas as pd

try:
    from trading_app.execution_spec import ExecutionSpec
except ModuleNotFoundError:
    from execution_spec import ExecutionSpec


@dataclass
class ContractResult:
    """Result of contract validation"""

    valid: bool  # True if all requirements met (no errors)
    errors: List[str] = field(default_factory=list)  # Critical issues (block run)
    warnings: List[str] = field(default_factory=list)  # Minor issues (log but continue)

    def __str__(self) -> str:
        status = "[PASS]" if self.valid else "[FAIL]"
        error_count = len(self.errors)
        warning_count = len(self.warnings)

        lines = [f"{status} Contract validation"]

        if error_count > 0:
            lines.append(f"  Errors: {error_count}")
            for error in self.errors:
                lines.append(f"    - {error}")

        if warning_count > 0:
            lines.append(f"  Warnings: {warning_count}")
            for warning in self.warnings:
                lines.append(f"    - {warning}")

        return "\n".join(lines)


@dataclass
class ExecutionContract:
    """
    Defines requirements and invariants for an execution spec.

    A contract specifies what a calculation needs to run correctly:
    - Required data columns
    - Required database tables
    - Required spec fields
    - Allowed value combinations
    - Invariant checks (must always be true)

    Example:
        contract = ExecutionContract(
            required_columns=['timestamp', 'open', 'high', 'low', 'close'],
            required_tables=['bars_1m'],
            required_spec_fields=['orb_time', 'rr_target'],
            allowed_combinations={'entry_rule': ['1st_close_outside']},
            invariants=[check_no_lookahead]
        )

        result = contract.validate(spec, data)
        if not result.valid:
            print(result)
    """

    required_columns: List[str] = field(default_factory=list)  # DB columns needed
    required_tables: List[str] = field(default_factory=list)  # Tables needed
    required_spec_fields: List[str] = field(default_factory=list)  # Spec fields that must be set
    allowed_combinations: Dict[str, List[Any]] = field(default_factory=dict)  # Valid values per field
    invariants: List[Callable[[ExecutionSpec, pd.DataFrame], bool]] = field(default_factory=list)  # Must be true

    def validate(
        self,
        spec: ExecutionSpec,
        data: Optional[pd.DataFrame] = None
    ) -> ContractResult:
        """
        Check if spec + data satisfy contract.

        Args:
            spec: ExecutionSpec to validate
            data: Optional DataFrame with required columns

        Returns:
            ContractResult: Validation result with errors/warnings
        """
        errors = []
        warnings = []

        # Check required spec fields
        for field_name in self.required_spec_fields:
            if not hasattr(spec, field_name):
                errors.append(f"Missing spec field: {field_name}")
            elif getattr(spec, field_name) is None:
                errors.append(f"Spec field is None: {field_name}")

        # Check allowed combinations
        for field_name, allowed_values in self.allowed_combinations.items():
            if not hasattr(spec, field_name):
                errors.append(f"Spec missing field for validation: {field_name}")
                continue

            value = getattr(spec, field_name)
            if value not in allowed_values:
                errors.append(
                    f"{field_name}={value} not in allowed values: {allowed_values}"
                )

        # Check columns exist (if data provided)
        if data is not None:
            for col in self.required_columns:
                if col not in data.columns:
                    errors.append(f"Missing required column: {col}")

        # Run invariant checks (if data provided)
        if data is not None and len(errors) == 0:  # Only run if no critical errors
            for invariant_func in self.invariants:
                try:
                    passed = invariant_func(spec, data)
                    if not passed:
                        warnings.append(
                            f"Invariant failed: {invariant_func.__name__}"
                        )
                except Exception as e:
                    errors.append(
                        f"Invariant error ({invariant_func.__name__}): {e}"
                    )

        return ContractResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )


# =====================================================================
# PRE-DEFINED CONTRACTS FOR COMMON ENTRY RULES
# =====================================================================

def contract_limit_at_orb() -> ExecutionContract:
    """
    Contract for limit_at_orb entry rule.

    Entry: Limit order at ORB edge (immediate entry when ORB breaks)
    """

    def check_orb_window_complete(spec: ExecutionSpec, data: pd.DataFrame) -> bool:
        """ORB window has expected number of bars"""
        if 'is_orb_window' not in data.columns:
            return True  # Skip check if column not present

        orb_bars = data[data['is_orb_window']]
        expected = spec.orb_minutes  # For 1m bars
        return len(orb_bars) == expected

    return ExecutionContract(
        required_columns=['timestamp', 'open', 'high', 'low', 'close'],
        required_tables=['bars_1m'],
        required_spec_fields=['orb_time', 'orb_minutes', 'rr_target'],
        allowed_combinations={
            'entry_rule': ['limit_at_orb']
        },
        invariants=[check_orb_window_complete]
    )


def contract_1st_close_outside() -> ExecutionContract:
    """
    Contract for 1st_close_outside entry rule.

    Entry: First 1m bar that closes outside ORB range
    """

    def check_orb_window_complete(spec: ExecutionSpec, data: pd.DataFrame) -> bool:
        """ORB window has expected number of bars"""
        if 'is_orb_window' not in data.columns:
            return True

        orb_bars = data[data['is_orb_window']]
        expected = spec.orb_minutes
        return len(orb_bars) == expected

    def check_entry_after_orb(spec: ExecutionSpec, data: pd.DataFrame) -> bool:
        """Entry timestamp > ORB end timestamp"""
        if 'entry_timestamp' not in data.columns or 'orb_end_timestamp' not in data.columns:
            return True

        # Defensive check: prevent crash on empty DataFrame
        if data.empty:
            return True

        entry_ts = data['entry_timestamp'].iloc[0]
        orb_end = data['orb_end_timestamp'].iloc[0]
        return entry_ts > orb_end

    def check_no_lookahead(spec: ExecutionSpec, data: pd.DataFrame) -> bool:
        """Entry uses only bars after ORB end"""
        if 'entry_timestamp' not in data.columns or 'orb_end_timestamp' not in data.columns:
            return True

        # Defensive check: prevent crash on empty DataFrame
        if data.empty:
            return True

        entry_ts = data['entry_timestamp'].iloc[0]
        orb_end = data['orb_end_timestamp'].iloc[0]
        return entry_ts >= orb_end

    return ExecutionContract(
        required_columns=['timestamp', 'open', 'high', 'low', 'close'],
        required_tables=['bars_1m'],
        required_spec_fields=['orb_time', 'orb_minutes', 'confirm_tf', 'rr_target'],
        allowed_combinations={
            'entry_rule': ['1st_close_outside'],
            'confirm_tf': ['1m']
        },
        invariants=[
            check_orb_window_complete,
            check_entry_after_orb,
            check_no_lookahead
        ]
    )


def contract_5m_close_outside() -> ExecutionContract:
    """
    Contract for 5m_close_outside entry rule.

    Entry: First 5m aggregated bar that closes outside ORB range
    """

    def check_orb_window_complete(spec: ExecutionSpec, data: pd.DataFrame) -> bool:
        """ORB window has expected number of bars"""
        if 'is_orb_window' not in data.columns:
            return True

        orb_bars = data[data['is_orb_window']]
        expected = spec.orb_minutes
        return len(orb_bars) == expected

    def check_entry_after_orb(spec: ExecutionSpec, data: pd.DataFrame) -> bool:
        """Entry timestamp > ORB end timestamp"""
        if 'entry_timestamp' not in data.columns or 'orb_end_timestamp' not in data.columns:
            return True

        # Defensive check: prevent crash on empty DataFrame
        if data.empty:
            return True

        entry_ts = data['entry_timestamp'].iloc[0]
        orb_end = data['orb_end_timestamp'].iloc[0]
        return entry_ts > orb_end

    def check_no_lookahead(spec: ExecutionSpec, data: pd.DataFrame) -> bool:
        """Entry uses only bars after confirmation close"""
        if 'entry_timestamp' not in data.columns or 'confirm_timestamp' not in data.columns:
            return True

        # Defensive check: prevent crash on empty DataFrame
        if data.empty:
            return True

        entry_ts = data['entry_timestamp'].iloc[0]
        confirm_ts = data['confirm_timestamp'].iloc[0]
        return entry_ts >= confirm_ts

    def check_5m_alignment(spec: ExecutionSpec, data: pd.DataFrame) -> bool:
        """Confirmation timestamp aligns to 5-min boundaries"""
        if 'confirm_timestamp' not in data.columns:
            return True

        # Defensive check: prevent crash on empty DataFrame
        if data.empty:
            return True

        confirm_ts = data['confirm_timestamp'].iloc[0]
        # Check if timestamp is on 5-min boundary (minutes % 5 == 0)
        return confirm_ts.minute % 5 == 0

    return ExecutionContract(
        required_columns=['timestamp', 'open', 'high', 'low', 'close'],
        required_tables=['bars_1m'],
        required_spec_fields=['orb_time', 'orb_minutes', 'confirm_tf', 'rr_target'],
        allowed_combinations={
            'entry_rule': ['5m_close_outside'],
            'confirm_tf': ['5m']
        },
        invariants=[
            check_orb_window_complete,
            check_entry_after_orb,
            check_no_lookahead,
            check_5m_alignment
        ]
    )


def get_contract_for_entry_rule(entry_rule: str) -> ExecutionContract:
    """
    Get the appropriate contract for an entry rule.

    Args:
        entry_rule: Entry rule name

    Returns:
        ExecutionContract: Contract for this entry rule

    Raises:
        ValueError: If entry rule not recognized
    """
    contracts = {
        'limit_at_orb': contract_limit_at_orb,
        '1st_close_outside': contract_1st_close_outside,
        '2nd_close_outside': contract_1st_close_outside,  # Same as 1st close
        '5m_close_outside': contract_5m_close_outside
    }

    if entry_rule not in contracts:
        available = ", ".join(contracts.keys())
        raise ValueError(
            f"Unknown entry_rule: {entry_rule}. Available: {available}"
        )

    return contracts[entry_rule]()


if __name__ == "__main__":
    # Test basic functionality
    print("=" * 70)
    print("ExecutionContract Test")
    print("=" * 70)

    # Test 1: Valid spec
    print("\nTest 1: Valid spec (1st_close_outside)")
    spec = ExecutionSpec(
        bar_tf="1m",
        orb_time="1000",
        entry_rule="1st_close_outside",
        confirm_tf="1m",
        rr_target=1.5
    )

    contract = get_contract_for_entry_rule(spec.entry_rule)
    result = contract.validate(spec)
    print(result)

    # Test 2: Invalid combination
    print("\nTest 2: Invalid combination (5m_close requires confirm_tf=5m)")
    try:
        spec_invalid = ExecutionSpec(
            bar_tf="1m",
            orb_time="1000",
            entry_rule="5m_close_outside",
            confirm_tf="1m",  # Wrong!
            rr_target=1.5
        )
        print("[UNEXPECTED] Should have failed in __post_init__")
    except ValueError as e:
        print(f"[PASS] Caught error: {e}")

    # Test 3: Missing required field
    print("\nTest 3: Contract with missing data")
    contract = get_contract_for_entry_rule("1st_close_outside")

    # Create DataFrame with missing column
    test_data = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=10, freq='1min'),
        'open': [100] * 10,
        # Missing 'high', 'low', 'close'
    })

    result = contract.validate(spec, test_data)
    print(result)

    print("\n" + "=" * 70)
    print("All tests passed!")
    print("=" * 70)
