"""
Strategy Evaluation Helper

Evaluates trade outcomes using MAE/MFE data for any RR and stop configuration.
This module treats the database as a factual record and applies strategy logic separately.
"""

from typing import Tuple, Optional


def evaluate_trade_outcome(
    break_dir: str,
    orb_high: float,
    orb_low: float,
    mae: Optional[float],
    mfe: Optional[float],
    rr: float,
    sl_mode: str = 'FULL'
) -> Tuple[str, float]:
    """
    Evaluate trade outcome for any RR/stop configuration using MAE/MFE data.

    Args:
        break_dir: 'UP' or 'DOWN'
        orb_high: ORB high level
        orb_low: ORB low level
        mae: Maximum Adverse Excursion (points from entry, negative for adverse)
        mfe: Maximum Favorable Excursion (points from entry, positive for favorable)
        rr: Target reward:risk ratio
        sl_mode: 'FULL' (opposite ORB edge) or 'HALF' (ORB midpoint)

    Returns:
        Tuple of (outcome, r_achieved):
            outcome: 'WIN', 'LOSS', or 'NO_TRADE'
            r_achieved: Actual R-multiple achieved (+RR for win, -1.0 for loss)

    Logic:
        - Database stores what price ACTUALLY did (MAE/MFE in points)
        - We check if that price action hit target or stop first
        - Target distance = RR * risk
        - Stop distance = 1R * risk
        - Risk depends on sl_mode (FULL or HALF)

    Example:
        ORB: 2644.2-2645.5 (1.3 pts range)
        Break: UP (entry at 2645.5)
        MAE: -0.4 pts (worst went down 0.4)
        MFE: +3.2 pts (best went up 3.2)

        For RR=1.0, FULL stop:
            Risk = 1.3 pts, Target = +1.3, Stop = -1.3
            Result: WIN (MFE +3.2 > target +1.3)

        For RR=3.0, FULL stop:
            Risk = 1.3 pts, Target = +3.9, Stop = -1.3
            Result: LOSS (MFE +3.2 < target +3.9)
    """
    if break_dir not in ['UP', 'DOWN']:
        return 'NO_TRADE', 0.0

    if mae is None or mfe is None:
        return 'NO_TRADE', 0.0

    orb_size = orb_high - orb_low
    if orb_size <= 0:
        return 'NO_TRADE', 0.0

    # Calculate risk based on stop mode
    if sl_mode == 'HALF':
        risk = orb_size / 2.0
    else:  # FULL
        risk = orb_size

    # Calculate target and stop distances
    target_distance = rr * risk
    stop_distance = risk

    if break_dir == 'UP':
        # LONG: entry at orb_high
        # Target: price needs to go UP by target_distance
        # Stop: price goes DOWN by stop_distance

        # Check if target was hit (MFE positive, >= target)
        target_hit = mfe >= target_distance

        # Check if stop was hit (MAE negative, <= -stop)
        stop_hit = mae <= -stop_distance

        if target_hit and not stop_hit:
            # Target hit first
            return 'WIN', rr
        elif stop_hit and not target_hit:
            # Stop hit first
            return 'LOSS', -1.0
        elif target_hit and stop_hit:
            # Both hit - conservative: assume stop hit first
            return 'LOSS', -1.0
        else:
            # Neither hit - no resolution
            # This happens when trade is still open at scan window end
            # For research purposes, treat as no trade
            return 'NO_TRADE', 0.0

    else:  # DOWN
        # SHORT: entry at orb_low
        # Target: price needs to go DOWN by target_distance (MFE negative)
        # Stop: price goes UP by stop_distance (MAE positive)

        # Check if target was hit (MFE negative, <= -target)
        target_hit = mfe <= -target_distance

        # Check if stop was hit (MAE positive, >= stop)
        stop_hit = mae >= stop_distance

        if target_hit and not stop_hit:
            # Target hit first
            return 'WIN', rr
        elif stop_hit and not target_hit:
            # Stop hit first
            return 'LOSS', -1.0
        elif target_hit and stop_hit:
            # Both hit - conservative: assume stop hit first
            return 'LOSS', -1.0
        else:
            # Neither hit - no resolution
            return 'NO_TRADE', 0.0


def calculate_metrics(outcomes_and_r: list) -> dict:
    """
    Calculate performance metrics from list of (outcome, r_achieved) tuples.

    Args:
        outcomes_and_r: List of (outcome, r_achieved) from evaluate_trade_outcome

    Returns:
        Dict with win_rate, avg_r, total_r, wins, losses, no_trades
    """
    wins = sum(1 for outcome, _ in outcomes_and_r if outcome == 'WIN')
    losses = sum(1 for outcome, _ in outcomes_and_r if outcome == 'LOSS')
    no_trades = sum(1 for outcome, _ in outcomes_and_r if outcome == 'NO_TRADE')

    total_trades = wins + losses  # Exclude no_trades from denominator

    if total_trades == 0:
        return {
            'win_rate': 0.0,
            'avg_r': 0.0,
            'total_r': 0.0,
            'wins': 0,
            'losses': 0,
            'no_trades': no_trades,
            'total_trades': 0
        }

    r_values = [r for outcome, r in outcomes_and_r if outcome in ['WIN', 'LOSS']]
    total_r = sum(r_values)
    avg_r = total_r / total_trades
    win_rate = wins / total_trades

    return {
        'win_rate': win_rate,
        'avg_r': avg_r,
        'total_r': total_r,
        'wins': wins,
        'losses': losses,
        'no_trades': no_trades,
        'total_trades': total_trades
    }
