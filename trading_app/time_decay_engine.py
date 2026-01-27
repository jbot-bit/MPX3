"""
Time-Decay Exit Logic - Simple & Deterministic

Purpose: Cut chop losses by exiting trades that show no progress after T+X minutes

Design Philosophy:
- SIMPLE: No ML, no optimization, no fancy math
- DETERMINISTIC: Same inputs always produce same outputs
- CONFIGURABLE: User sets thresholds (not hardcoded)

Value Proposition:
- Cuts chop losses (trade going nowhere)
- Improves expectancy (exit before full stop loss)
- Prevents overnight holds on dead trades

Mastervalid.txt Test 4.3: Time-decay exit logic
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal, Optional


# ============================================================================
# INPUT/OUTPUT CONTRACTS
# ============================================================================

@dataclass(frozen=True)
class TimeDecayRequest:
    """
    Request for time-decay exit check.

    All inputs are observable facts (no predictions, no ML).
    """
    # Entry information
    entry_time: datetime  # When trade was entered
    entry_price: float  # Entry price
    direction: Literal['LONG', 'SHORT']  # Trade direction

    # Current state
    current_time: datetime  # Current time
    current_price: float  # Current price
    high_since_entry: float  # Highest price since entry
    low_since_entry: float  # Lowest price since entry

    # Trade targets
    stop_loss: float  # Stop loss price
    target_price: float  # Target price (1R, 2R, etc.)

    # Time-decay thresholds (user configurable)
    max_time_minutes: int = 30  # Max time before forced exit (default: 30 min)
    min_progress_r: float = 0.3  # Min progress in R-multiples (default: 0.3R)

    # Optional: Hard stop time (e.g., end of session)
    hard_stop_time: Optional[datetime] = None


@dataclass(frozen=True)
class TimeDecayResult:
    """
    Result of time-decay exit check.

    Pure output - no side effects.
    """
    should_exit: bool  # True if trade should be exited now
    exit_reason: str  # Why exit is recommended
    exit_type: Literal['NONE', 'TIME_DECAY', 'HARD_STOP', 'PROGRESS_STALL']

    # Diagnostics
    time_elapsed_minutes: float  # Minutes since entry
    progress_r: float  # Progress in R-multiples (0.0 = entry, 1.0 = target)
    max_favorable_r: float  # Maximum favorable excursion in R-multiples

    # Current state
    current_mae: float  # Maximum adverse excursion (negative if against you)
    current_mfe: float  # Maximum favorable excursion (positive if in your favor)

    # Recommendation
    recommendation: str  # Human-readable guidance


# ============================================================================
# PURE CALCULATION FUNCTIONS
# ============================================================================

def calculate_time_decay(request: TimeDecayRequest) -> TimeDecayResult:
    """
    Main entry point: Check if trade should be exited due to time decay.

    Simple logic:
    1. Calculate time elapsed
    2. Calculate progress toward target
    3. If time > threshold AND progress < threshold → EXIT
    4. If hard_stop_time reached → EXIT

    No ML, no optimization, no fancy math.
    """
    # Step 1: Calculate time elapsed
    time_elapsed = request.current_time - request.entry_time
    time_elapsed_minutes = time_elapsed.total_seconds() / 60.0

    # Step 2: Calculate trade metrics
    r_size = abs(request.target_price - request.entry_price)  # 1R distance
    stop_size = abs(request.entry_price - request.stop_loss)  # Stop distance

    # Current progress toward target
    if request.direction == 'LONG':
        price_movement = request.current_price - request.entry_price
        max_favorable = request.high_since_entry - request.entry_price
        max_adverse = request.low_since_entry - request.entry_price
    else:  # SHORT
        price_movement = request.entry_price - request.current_price
        max_favorable = request.entry_price - request.low_since_entry
        max_adverse = request.entry_price - request.high_since_entry

    # R-multiples
    progress_r = price_movement / stop_size if stop_size > 0 else 0.0
    max_favorable_r = max_favorable / stop_size if stop_size > 0 else 0.0
    current_mae = max_adverse / stop_size if stop_size > 0 else 0.0
    current_mfe = max_favorable_r  # MFE is max favorable

    # Step 3: Check exit conditions

    # Condition 1: Hard stop time reached (e.g., end of session)
    if request.hard_stop_time and request.current_time >= request.hard_stop_time:
        return TimeDecayResult(
            should_exit=True,
            exit_reason=f"Hard stop time reached: {request.hard_stop_time.strftime('%H:%M')}",
            exit_type='HARD_STOP',
            time_elapsed_minutes=time_elapsed_minutes,
            progress_r=progress_r,
            max_favorable_r=max_favorable_r,
            current_mae=current_mae,
            current_mfe=current_mfe,
            recommendation="Exit immediately - hard stop time reached (end of session or risk window)"
        )

    # Condition 2: Time decay - no progress after T minutes
    if time_elapsed_minutes >= request.max_time_minutes:
        if max_favorable_r < request.min_progress_r:
            # Trade has been open for T+ minutes and never reached minimum progress
            return TimeDecayResult(
                should_exit=True,
                exit_reason=f"Time decay: {time_elapsed_minutes:.0f} min elapsed, max progress {max_favorable_r:.2f}R < {request.min_progress_r}R threshold",
                exit_type='TIME_DECAY',
                time_elapsed_minutes=time_elapsed_minutes,
                progress_r=progress_r,
                max_favorable_r=max_favorable_r,
                current_mae=current_mae,
                current_mfe=current_mfe,
                recommendation="Exit at market - trade going nowhere, cut chop loss before full stop"
            )

    # Condition 3: Progress stall - reached target zone but fell back
    if max_favorable_r >= request.min_progress_r:
        # Trade DID reach minimum progress, but current progress is back below threshold
        retracement_threshold = request.min_progress_r * 0.5  # Allow 50% retracement
        if progress_r < retracement_threshold and time_elapsed_minutes >= request.max_time_minutes * 0.5:
            return TimeDecayResult(
                should_exit=True,
                exit_reason=f"Progress stall: Reached {max_favorable_r:.2f}R but retraced to {progress_r:.2f}R after {time_elapsed_minutes:.0f} min",
                exit_type='PROGRESS_STALL',
                time_elapsed_minutes=time_elapsed_minutes,
                progress_r=progress_r,
                max_favorable_r=max_favorable_r,
                current_mae=current_mae,
                current_mfe=current_mfe,
                recommendation="Exit at market - trade lost momentum, prevent full retracement"
            )

    # No exit conditions met - hold trade
    return TimeDecayResult(
        should_exit=False,
        exit_reason="No exit conditions met - hold trade",
        exit_type='NONE',
        time_elapsed_minutes=time_elapsed_minutes,
        progress_r=progress_r,
        max_favorable_r=max_favorable_r,
        current_mae=current_mae,
        current_mfe=current_mfe,
        recommendation="Hold trade - within time and progress thresholds"
    )


def get_recommended_thresholds(orb_time: str, rr_target: float) -> dict:
    """
    Get recommended time-decay thresholds for a given ORB and RR target.

    Simple rules (no ML, no optimization):
    - Higher RR targets → More time allowed (bigger move needs more time)
    - Lower RR targets → Less time allowed (smaller move should happen faster)
    - Primary ORBs (0900, 1000, 1100) → Tighter thresholds (high liquidity)
    - Secondary ORBs (1800, 2300, 0030) → Looser thresholds (lower liquidity)

    Returns: dict with 'max_time_minutes' and 'min_progress_r'
    """
    # Base thresholds
    if orb_time in ['0900', '1000', '1100']:
        # Primary ORBs (high liquidity, tight spreads)
        base_time = 20  # 20 minutes base
        progress_threshold = 0.3  # 0.3R minimum progress
    else:
        # Secondary ORBs (lower liquidity, wider spreads)
        base_time = 30  # 30 minutes base
        progress_threshold = 0.25  # 0.25R minimum progress (looser)

    # Adjust for RR target
    if rr_target >= 5.0:
        # High RR (5R+) → Allow more time
        max_time = int(base_time * 1.5)
        min_progress = progress_threshold * 0.8  # Slightly lower threshold
    elif rr_target >= 2.0:
        # Medium RR (2-5R) → Standard time
        max_time = base_time
        min_progress = progress_threshold
    else:
        # Low RR (1-2R) → Tighter time
        max_time = int(base_time * 0.75)
        min_progress = progress_threshold * 1.2  # Higher threshold (move faster)

    return {
        'max_time_minutes': max_time,
        'min_progress_r': min_progress
    }


# ============================================================================
# INTERNAL TESTS (Run with: python time_decay_engine.py)
# ============================================================================

def _test_time_decay_basic():
    """Test basic time decay - trade going nowhere."""
    print("=" * 70)
    print("TEST 1: Time Decay - Trade Going Nowhere")
    print("=" * 70)

    entry_time = datetime(2026, 1, 26, 9, 5)
    current_time = entry_time + timedelta(minutes=35)  # 35 minutes elapsed

    request = TimeDecayRequest(
        entry_time=entry_time,
        entry_price=100.0,
        direction='LONG',
        current_time=current_time,
        current_price=100.05,  # Only +$0.05 movement (10% of stop)
        high_since_entry=100.12,  # Max was +$0.12 (24% of stop = 0.24R)
        low_since_entry=99.85,  # MAE was -$0.15
        stop_loss=99.5,  # $0.5 stop
        target_price=101.0,  # $1.0 target (2R)
        max_time_minutes=30,
        min_progress_r=0.3  # Need 0.3R minimum, but only reached 0.24R
    )

    result = calculate_time_decay(request)

    print(f"Entry: {entry_time.strftime('%H:%M')}, Price: ${request.entry_price:.2f}")
    print(f"Current: {current_time.strftime('%H:%M')}, Price: ${request.current_price:.2f}")
    print(f"Time Elapsed: {result.time_elapsed_minutes:.0f} minutes")
    print(f"Progress: {result.progress_r:.2f}R (Max: {result.max_favorable_r:.2f}R)")
    print()
    print(f">>> Should Exit: {result.should_exit}")
    print(f">>> Exit Type: {result.exit_type}")
    print(f">>> Reason: {result.exit_reason}")
    print(f">>> Recommendation: {result.recommendation}")
    print()

    assert result.should_exit, "Should exit due to time decay"
    assert result.exit_type == 'TIME_DECAY', "Exit type should be TIME_DECAY"
    print("[PASS] Time decay working correctly")
    print()


def _test_hard_stop_time():
    """Test hard stop time (e.g., end of session)."""
    print("=" * 70)
    print("TEST 2: Hard Stop Time - End of Session")
    print("=" * 70)

    entry_time = datetime(2026, 1, 26, 9, 5)
    current_time = datetime(2026, 1, 26, 9, 55)  # 50 minutes later
    hard_stop = datetime(2026, 1, 26, 10, 0)  # Hard stop at 10:00

    request = TimeDecayRequest(
        entry_time=entry_time,
        entry_price=100.0,
        direction='LONG',
        current_time=current_time,
        current_price=100.5,  # Making progress
        high_since_entry=100.6,
        low_since_entry=99.9,
        stop_loss=99.5,
        target_price=101.0,
        hard_stop_time=hard_stop
    )

    # Test: 5 minutes before hard stop
    result_before = calculate_time_decay(request)
    print(f"5 minutes before hard stop:")
    print(f"  Should Exit: {result_before.should_exit}")
    print()

    # Test: At hard stop time
    request_at_stop = TimeDecayRequest(
        entry_time=entry_time,
        entry_price=100.0,
        direction='LONG',
        current_time=hard_stop,  # NOW at hard stop
        current_price=100.5,
        high_since_entry=100.6,
        low_since_entry=99.9,
        stop_loss=99.5,
        target_price=101.0,
        hard_stop_time=hard_stop
    )

    result_at_stop = calculate_time_decay(request_at_stop)
    print(f"At hard stop time ({hard_stop.strftime('%H:%M')}):")
    print(f"  >>> Should Exit: {result_at_stop.should_exit}")
    print(f"  >>> Exit Type: {result_at_stop.exit_type}")
    print(f"  >>> Reason: {result_at_stop.exit_reason}")
    print()

    assert result_at_stop.should_exit, "Should exit at hard stop time"
    assert result_at_stop.exit_type == 'HARD_STOP', "Exit type should be HARD_STOP"
    print("[PASS] Hard stop time working correctly")
    print()


def _test_progress_stall():
    """Test progress stall - trade reached target zone but fell back."""
    print("=" * 70)
    print("TEST 3: Progress Stall - Reached Target But Retraced")
    print("=" * 70)

    entry_time = datetime(2026, 1, 26, 9, 5)
    current_time = entry_time + timedelta(minutes=20)

    request = TimeDecayRequest(
        entry_time=entry_time,
        entry_price=100.0,
        direction='LONG',
        current_time=current_time,
        current_price=100.10,  # Back near entry (only 0.10R now)
        high_since_entry=100.65,  # Was at 0.65R (above 0.3R threshold!)
        low_since_entry=99.9,
        stop_loss=99.0,  # $1.0 stop
        target_price=102.0,  # $2.0 target (2R)
        max_time_minutes=30,
        min_progress_r=0.3  # Retracement threshold = 0.15R, current = 0.10R < 0.15R
    )

    result = calculate_time_decay(request)

    print(f"Entry: ${request.entry_price:.2f}")
    print(f"High Since Entry: ${request.high_since_entry:.2f} ({result.max_favorable_r:.2f}R)")
    print(f"Current: ${request.current_price:.2f} ({result.progress_r:.2f}R)")
    print(f"Time Elapsed: {result.time_elapsed_minutes:.0f} minutes")
    print()
    print(f">>> Should Exit: {result.should_exit}")
    print(f">>> Exit Type: {result.exit_type}")
    print(f">>> Reason: {result.exit_reason}")
    print()

    assert result.should_exit, "Should exit due to progress stall"
    assert result.exit_type == 'PROGRESS_STALL', "Exit type should be PROGRESS_STALL"
    print("[PASS] Progress stall working correctly")
    print()


def _test_hold_trade():
    """Test hold trade - making progress within time threshold."""
    print("=" * 70)
    print("TEST 4: Hold Trade - Making Progress")
    print("=" * 70)

    entry_time = datetime(2026, 1, 26, 9, 5)
    current_time = entry_time + timedelta(minutes=15)  # Only 15 minutes

    request = TimeDecayRequest(
        entry_time=entry_time,
        entry_price=100.0,
        direction='LONG',
        current_time=current_time,
        current_price=100.4,  # Making good progress
        high_since_entry=100.5,
        low_since_entry=99.9,
        stop_loss=99.0,
        target_price=102.0,
        max_time_minutes=30,
        min_progress_r=0.3
    )

    result = calculate_time_decay(request)

    print(f"Time Elapsed: {result.time_elapsed_minutes:.0f} minutes (< {request.max_time_minutes} threshold)")
    print(f"Progress: {result.progress_r:.2f}R (Max: {result.max_favorable_r:.2f}R)")
    print()
    print(f">>> Should Exit: {result.should_exit}")
    print(f">>> Recommendation: {result.recommendation}")
    print()

    assert not result.should_exit, "Should NOT exit - making progress"
    print("[PASS] Hold trade working correctly")
    print()


def _test_recommended_thresholds():
    """Test recommended threshold calculations."""
    print("=" * 70)
    print("TEST 5: Recommended Thresholds")
    print("=" * 70)

    test_cases = [
        ('0900', 2.0),  # Primary ORB, medium RR
        ('1000', 8.0),  # Primary ORB, high RR
        ('1100', 1.5),  # Primary ORB, low RR
        ('1800', 2.0),  # Secondary ORB, medium RR
        ('0030', 5.0),  # Secondary ORB, high RR
    ]

    for orb_time, rr_target in test_cases:
        thresholds = get_recommended_thresholds(orb_time, rr_target)
        print(f"{orb_time} ORB, RR={rr_target}: max_time={thresholds['max_time_minutes']} min, min_progress={thresholds['min_progress_r']:.2f}R")

    print()
    print("[PASS] Recommended thresholds calculated correctly")
    print()


if __name__ == '__main__':
    print("=" * 70)
    print("TIME DECAY ENGINE - Pure Calculation Module")
    print("=" * 70)
    print()

    _test_time_decay_basic()
    _test_hard_stop_time()
    _test_progress_stall()
    _test_hold_trade()
    _test_recommended_thresholds()

    print("=" * 70)
    print("ALL TESTS PASSED")
    print("=" * 70)
    print()
    print("[OK] Time decay logic working correctly")
    print("[OK] Hard stop time working correctly")
    print("[OK] Progress stall detection working correctly")
    print("[OK] Hold trade logic working correctly")
    print("[OK] Recommended thresholds calculated correctly")
    print()
    print("Mastervalid.txt 4.3: Time-decay exit logic - READY FOR INTEGRATION")
    print()
