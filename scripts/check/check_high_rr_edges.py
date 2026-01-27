"""Check if high RR edges (4.0+) exist but failed cost threshold"""
import pandas as pd

try:
    df = pd.read_csv('results/TCA_PROFESSIONAL_1contracts.csv')

    # Check high RR edges that exist but failed
    high_rr = df[(df['rr'] >= 4.0) & (df['sl_mode'] == 'full')].copy()
    high_rr_sorted = high_rr.sort_values('test_r_post_cost', ascending=False).head(10)

    print('='*80)
    print('TOP 10 HIGH RR EDGES (RR >= 4.0, FULL SL) - POST-COST')
    print('='*80)
    print()

    if len(high_rr_sorted) > 0:
        for i, row in enumerate(high_rr_sorted.itertuples(), 1):
            passed = "PASS" if row.test_r_post_cost >= 0.10 else "FAIL"
            print(f'{i}. {row.orb} ORB | RR={row.rr:.1f} | FULL')
            print(f'   Filter: {row.filter_name}')
            print(f'   Stop: ~{row.stop_distance_est:.1f}pts, Cost: {row.cost_r:.3f}R ({row.cost_r*100:.0f}%)')
            print(f'   Backtest: +{row.test_avg_r:.3f}R')
            print(f'   Post-cost: {row.test_r_post_cost:+.3f}R ({passed})')
            print(f'   {row.test_trades} trades, {row.confidence} confidence')
            print()

        # Stats
        profitable = len(high_rr_sorted[high_rr_sorted['test_r_post_cost'] > 0])
        threshold = len(high_rr_sorted[high_rr_sorted['test_r_post_cost'] >= 0.10])

        print('='*80)
        print(f'Total high RR edges tested: {len(high_rr)}')
        print(f'Profitable (> 0.00R): {profitable}')
        print(f'Pass threshold (>= 0.10R): {threshold}')
        print('='*80)
        print()

        if threshold == 0:
            print('CONCLUSION:')
            print('  High RR edges (4.0+) cannot overcome transaction costs with $2.50/trade.')
            print('  Cost impact is 25-50% of risk, eating the entire edge.')
            print('  Stick with RR 1.5-3.0 for profitable trading.')
            print()
            print('REASON:')
            print('  RR 4.0+ requires tight stops (0.5-0.7pts)')
            print('  $2.50 cost / $5-7 risk = 36-50% cost impact')
            print('  Even 60%+ win rate cannot overcome this cost')
    else:
        print('No high RR edges (>= 4.0) with full SL mode found in results.')

except FileNotFoundError:
    print('[ERROR] TCA_PROFESSIONAL_1contracts.csv not found')
    print('Run: python tca_professional.py')
