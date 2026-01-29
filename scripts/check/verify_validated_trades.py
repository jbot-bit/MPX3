"""Verify validated_trades table has correct data."""
import duckdb

conn = duckdb.connect('data/db/gold.db')

# Sample 10 trades showing entry price, risk/target points, and RR verification
print('\n' + '=' * 90)
print('SAMPLE TRADES: Entry Price Verification')
print('=' * 90 + '\n')
print(f"{'Date':<12} {'ID':<4} {'ORB':<5} {'RR':<5} {'Entry':<8} {'Risk':<7} {'Target':<8} {'Ratio':<7} {'Outcome':<8}")
print('-' * 90)

rows = conn.execute('''
    SELECT vt.date_local, vt.setup_id, vt.orb_time, vs.rr,
           vt.entry_price, vt.risk_points, vt.target_points, vt.outcome
    FROM validated_trades vt
    JOIN validated_setups vs ON vt.setup_id = vs.id
    WHERE vt.outcome != 'NO_TRADE'
      AND vt.entry_price IS NOT NULL
    ORDER BY vt.date_local
    LIMIT 10
''').fetchall()

all_match = True
for row in rows:
    date_local, setup_id, orb_time, rr, entry, risk, target, outcome = row
    ratio = target / risk if (risk and risk > 0 and target is not None) else 0
    entry_str = f'{entry:.2f}' if entry is not None else 'None'
    risk_str = f'{risk:.2f}' if risk is not None else 'None'
    target_str = f'{target:.2f}' if target is not None else 'None'
    print(f'{str(date_local):<12} {setup_id:<4} {orb_time:<5} {rr:<5.1f} {entry_str:<8} {risk_str:<7} {target_str:<8} {ratio:<7.2f} {outcome:<8}')

    # Verify ratio matches RR
    if abs(ratio - rr) > 0.01:
        print(f'  [WARNING] Target/Risk ratio {ratio:.2f} != RR {rr:.1f}')
        all_match = False

print('\n' + '=' * 90)
if all_match:
    print('[SUCCESS] Target/Risk Ratio Verification: All ratios match configured RR values')
else:
    print('[WARNING] Some ratios do not match configured RR')
print('=' * 90)

conn.close()
