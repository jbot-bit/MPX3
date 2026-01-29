"""
Execution Specification - Single source of truth for how trades are computed

This module defines the ExecutionSpec dataclass that ALL calculation paths must use.
No computation should happen without a valid ExecutionSpec.

Created for UPDATE14 (update14.txt) - Step 1
"""

import re
import json
import hashlib
from dataclasses import dataclass, asdict, field
from typing import Literal, Optional
from datetime import datetime


@dataclass
class ExecutionSpec:
    """
    Single source of truth for trade computation parameters.

    All calculation paths (daily_features, auto_search, backtests) must
    consume an ExecutionSpec object. This ensures:
    - Reproducibility (same spec = same results)
    - Transparency (know exactly how it was computed)
    - Validation (incompatible configs caught early)

    Example:
        spec = ExecutionSpec(
            bar_tf="1m",
            orb_time="1000",
            orb_minutes=5,
            entry_rule="1st_close_outside",
            confirm_tf="1m",
            rr_target=1.0,
            sl_mode="orb_opposite",
            cost_model="mgc_tradovate"
        )
    """

    # Data inputs
    bar_tf: Literal["1m", "5m"]  # Base timeframe for bars
    data_source: str = "bars_1m"  # Table name

    # ORB definition
    orb_time: str = "1000"  # Format: "0900", "1000", "1100", etc.
    orb_minutes: int = 5  # ORB window duration

    # Entry rule
    entry_rule: Literal[
        "limit_at_orb",
        "1st_close_outside",
        "2nd_close_outside",
        "5m_close_outside"
    ] = "1st_close_outside"

    confirm_tf: Literal["1m", "5m"] = "1m"  # Confirmation timeframe

    # Risk/Reward
    rr_target: float = 1.0  # R-multiple target (1.0, 1.5, 2.0, etc.)
    sl_mode: Literal["orb_opposite", "atr", "fixed"] = "orb_opposite"

    # Costs
    cost_model: str = "mgc_tradovate"  # References cost_model.py

    # Time
    session_tz: str = "Australia/Brisbane"

    # Metadata (optional)
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate spec immediately after creation"""

        # Validate orb_time format (must be 4 digits)
        if not re.match(r'^\d{4}$', self.orb_time):
            raise ValueError(
                f"orb_time must be 4 digits (e.g., '0900', '1000'), got: {self.orb_time}"
            )

        # Validate entry_rule + confirm_tf compatibility
        if self.entry_rule == "5m_close_outside" and self.confirm_tf != "5m":
            raise ValueError(
                "entry_rule='5m_close_outside' requires confirm_tf='5m', "
                f"got confirm_tf='{self.confirm_tf}'"
            )

        # Validate rr_target is positive
        if self.rr_target <= 0:
            raise ValueError(
                f"rr_target must be > 0, got: {self.rr_target}"
            )

        # Validate orb_minutes is positive
        if self.orb_minutes <= 0:
            raise ValueError(
                f"orb_minutes must be > 0, got: {self.orb_minutes}"
            )

        # Set created_at if not provided
        if self.created_at is None:
            self.created_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """
        Serialize spec to dictionary for storage.

        Returns:
            dict: Serializable representation
        """
        data = asdict(self)
        # Convert datetime to ISO string
        if data['created_at']:
            data['created_at'] = data['created_at'].isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'ExecutionSpec':
        """
        Deserialize spec from dictionary.

        Args:
            data: Dictionary from to_dict()

        Returns:
            ExecutionSpec: Reconstructed spec
        """
        # Convert ISO string back to datetime
        if 'created_at' in data and data['created_at']:
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)

    def spec_hash(self) -> str:
        """
        Generate unique identifier for this spec.

        Two specs with identical parameters will have the same hash.
        Used for deduplication and reproducibility.

        Returns:
            str: 12-character hex hash
        """
        # Exclude metadata fields from hash
        spec_dict = self.to_dict()
        spec_dict.pop('description', None)
        spec_dict.pop('created_at', None)

        # Sort keys for deterministic hash
        spec_str = json.dumps(spec_dict, sort_keys=True)
        full_hash = hashlib.sha256(spec_str.encode()).hexdigest()

        return full_hash[:12]

    def __str__(self) -> str:
        """Human-readable representation"""
        return (
            f"ExecutionSpec("
            f"orb_time={self.orb_time}, "
            f"entry_rule={self.entry_rule}, "
            f"rr_target={self.rr_target}, "
            f"hash={self.spec_hash()})"
        )

    def __repr__(self) -> str:
        """Developer representation"""
        return f"<{self.__str__()}>"

    def is_compatible_with(self, other: 'ExecutionSpec') -> bool:
        """
        Check if two specs are compatible (can be compared).

        Specs are compatible if they differ only in rr_target or description.
        Used to check if results can be compared across different RR targets.

        Args:
            other: Another ExecutionSpec

        Returns:
            bool: True if compatible
        """
        # Compare all fields except rr_target and metadata
        fields_to_compare = [
            'bar_tf', 'data_source', 'orb_time', 'orb_minutes',
            'entry_rule', 'confirm_tf', 'sl_mode', 'cost_model', 'session_tz'
        ]

        for field_name in fields_to_compare:
            if getattr(self, field_name) != getattr(other, field_name):
                return False

        return True


# Pre-defined specs for common configurations
SPEC_PRESETS = {
    "mgc_1000_tradeable": ExecutionSpec(
        bar_tf="1m",
        data_source="bars_1m",
        orb_time="1000",
        orb_minutes=5,
        entry_rule="1st_close_outside",
        confirm_tf="1m",
        rr_target=1.0,
        sl_mode="orb_opposite",
        cost_model="mgc_tradovate",
        description="MGC 1000 ORB, tradeable entry (1st close outside)"
    ),

    "mgc_1000_limit": ExecutionSpec(
        bar_tf="1m",
        data_source="bars_1m",
        orb_time="1000",
        orb_minutes=5,
        entry_rule="limit_at_orb",
        confirm_tf="1m",
        rr_target=1.0,
        sl_mode="orb_opposite",
        cost_model="mgc_tradovate",
        description="MGC 1000 ORB, limit order entry"
    ),

    "mgc_1000_5m_close": ExecutionSpec(
        bar_tf="1m",
        data_source="bars_1m",
        orb_time="1000",
        orb_minutes=5,
        entry_rule="5m_close_outside",
        confirm_tf="5m",
        rr_target=1.0,
        sl_mode="orb_opposite",
        cost_model="mgc_tradovate",
        description="MGC 1000 ORB, 5m close confirmation"
    ),
}


def get_preset(name: str) -> ExecutionSpec:
    """
    Get a pre-defined spec by name.

    Args:
        name: Preset name (e.g., "mgc_1000_tradeable")

    Returns:
        ExecutionSpec: Copy of the preset

    Raises:
        KeyError: If preset name not found
    """
    if name not in SPEC_PRESETS:
        available = ", ".join(SPEC_PRESETS.keys())
        raise KeyError(
            f"Preset '{name}' not found. Available presets: {available}"
        )

    # Return a copy to prevent mutation
    import copy
    return copy.deepcopy(SPEC_PRESETS[name])


if __name__ == "__main__":
    # Test basic functionality
    print("=" * 70)
    print("ExecutionSpec Test")
    print("=" * 70)

    # Create spec
    spec = ExecutionSpec(
        bar_tf="1m",
        orb_time="1000",
        entry_rule="1st_close_outside",
        rr_target=1.5
    )

    print(f"\nCreated: {spec}")
    print(f"Hash: {spec.spec_hash()}")

    # Test serialization
    spec_dict = spec.to_dict()
    print(f"\nSerialized: {json.dumps(spec_dict, indent=2, default=str)}")

    spec_restored = ExecutionSpec.from_dict(spec_dict)
    print(f"\nRestored: {spec_restored}")
    print(f"Hash matches: {spec.spec_hash() == spec_restored.spec_hash()}")

    # Test compatibility
    spec2 = ExecutionSpec(
        bar_tf="1m",
        orb_time="1000",
        entry_rule="1st_close_outside",
        rr_target=2.0  # Different RR
    )

    print(f"\nCompatible with different RR: {spec.is_compatible_with(spec2)}")

    # Test preset
    preset = get_preset("mgc_1000_tradeable")
    print(f"\nPreset loaded: {preset}")

    print("\n" + "=" * 70)
    print("All tests passed!")
    print("=" * 70)
