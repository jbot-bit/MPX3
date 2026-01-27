"""
STRATEGY RECOMMENDER
Analyzes current market state and recommends best setup
"""

def recommend_strategy(con, instrument, now_local, orb_name, config, orb_data):
    """
    Analyze current conditions and return recommendation

    Returns:
        {
            'confidence': 'HIGH' | 'MEDIUM' | 'LOW',
            'recommendation': 'TRADE' | 'SKIP' | 'WAIT',
            'reason': str,
            'bias': 'UP' | 'DOWN' | 'NEUTRAL',
            'priority': int (1-5, 1=highest)
        }
    """

    date_str = now_local.strftime("%Y-%m-%d")

    # Default
    result = {
        'confidence': 'MEDIUM',
        'recommendation': 'TRADE',
        'reason': 'Baseline edge',
        'bias': 'NEUTRAL',
        'priority': 3
    }

    # Check filters
    filter_fn = config.get("filter_fn")

    # =====================================================================
    # MGC SPECIFIC LOGIC (CANONICAL)
    # =====================================================================
    if instrument == "MGC":

        # 09:00 - High WR baseline
        if orb_name == "0900":
            result['confidence'] = 'HIGH'
            result['recommendation'] = 'TRADE'
            result['reason'] = '63.3% WR • +0.266R avg • Baseline'
            result['priority'] = 3

        # 10:00 - Best Asia ORB (with MAX_STOP filter)
        elif orb_name == "1000":
            result['confidence'] = 'HIGH'
            result['recommendation'] = 'TRADE'
            result['reason'] = '33.5% WR • +0.342R avg • Best Asia'
            result['priority'] = 1

            # Check MAX_STOP filter
            if orb_data and orb_data["size"] * 10 > 100:
                result['confidence'] = 'LOW'
                result['recommendation'] = 'SKIP'
                result['reason'] = f'ORB too wide ({orb_data["size"]*10:.0f}T > 100T)'
                result['priority'] = 5

        # 11:00 - SAFEST (highest WR)
        elif orb_name == "1100":
            result['confidence'] = 'HIGH'
            result['recommendation'] = 'TRADE'
            result['reason'] = '64.9% WR • +0.299R avg • SAFEST'
            result['priority'] = 2

        # 18:00 - 2ND BEST (but paper trade first)
        elif orb_name == "1800":
            result['confidence'] = 'MEDIUM'
            result['recommendation'] = 'TRADE'
            result['reason'] = '71.3% WR • +0.425R avg • PAPER FIRST'
            result['priority'] = 2

        # 23:00 - STRONG NIGHT SETUP (RR 1.0, HALF SL)
        elif orb_name == "2300":
            result['confidence'] = 'HIGH'
            result['recommendation'] = 'TRADE'
            result['reason'] = '69.3% WR • +0.387R avg • ~+100R/yr'
            result['priority'] = 1

        # 00:30 - ASIA TRANSITION (RR 1.0, HALF SL)
        elif orb_name == "0030":
            result['confidence'] = 'HIGH'
            result['recommendation'] = 'TRADE'
            result['reason'] = '61.6% WR • +0.231R avg • ~+60R/yr'
            result['priority'] = 1

    # =====================================================================
    # MNQ SPECIFIC LOGIC
    # =====================================================================
    elif instrument == "MNQ":

        # Check ORB size for most setups
        if filter_fn == "check_orb_size" and orb_data:
            ticks_per_point = 4
            orb_size_ticks = orb_data["size"] * ticks_per_point
            max_ticks = config.get("max_ticks", 50)

            if orb_size_ticks <= max_ticks:
                result['confidence'] = 'HIGH'
                result['recommendation'] = 'TRADE'
                result['reason'] = f'[OK] Compressed: {orb_size_ticks:.0f}T < {max_ticks}T'
                result['priority'] = 1
            else:
                result['confidence'] = 'LOW'
                result['recommendation'] = 'SKIP'
                result['reason'] = f'Too wide: {orb_size_ticks:.0f}T > {max_ticks}T'
                result['priority'] = 5

        # 11:00 - Best MNQ ORB
        if orb_name == "1100" and result['recommendation'] == 'TRADE':
            result['reason'] = f'{result["reason"]} • +0.26R avg • BEST'
            result['priority'] = 1

        # 23:00 - Always skip
        if orb_name == "2300":
            result['confidence'] = 'LOW'
            result['recommendation'] = 'SKIP'
            result['reason'] = 'Loses -0.15R • Skip this'
            result['priority'] = 5

        # 00:30 - Best MNQ night ORB
        if orb_name == "0030":
            result['confidence'] = 'HIGH'
            result['reason'] = '+0.29R • 57.5% WR • Best night'
            result['priority'] = 1

    return result
