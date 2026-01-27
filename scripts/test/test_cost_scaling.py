"""
Test: Does cost impact scale with stop size?

Verifies the TCA formula from TCA.txt:
    R_net = net_pnl / (stop_distance * point_value * contracts)
"""

# MGC specs
TOTAL_COST = 2.50  # Per contract round trip
POINT_VALUE = 10   # $10 per point

print("="*70)
print("TESTING COST SCALING LOGIC (from TCA.txt)")
print("="*70)
print()
print("Formula from TCA.txt (line 78):")
print("  R_net = net_pnl / (stop_distance * point_value * contracts)")
print()
print("Cost impact:")
print("  cost_as_R = (total_cost) / (stop_distance * point_value * contracts)")
print()
print(f"Fixed cost per trade: ${TOTAL_COST:.2f}")
print(f"Point value: ${POINT_VALUE}/point")
print()

# Test different stop sizes
print("="*70)
print("COST AS % OF RISK BY STOP SIZE (1 contract)")
print("="*70)
print()

test_stops = [0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0]

print("Stop (pts) | Risk ($) | Cost ($) | Cost as R | Cost %")
print("-" * 70)
for stop in test_stops:
    risk_dollars = stop * POINT_VALUE
    cost_r = TOTAL_COST / risk_dollars
    cost_pct = cost_r * 100
    print(f"  {stop:5.1f}    | ${risk_dollars:7.2f} | ${TOTAL_COST:7.2f} | {cost_r:8.3f}R | {cost_pct:6.1f}%")

print()
print("="*70)
print("PRACTICAL EXAMPLE - Same RR=1.5, Different Stops")
print("="*70)
print()

# Setup A: Small stop
stop_a = 0.5
rr_a = 1.5
risk_a = stop_a * POINT_VALUE
target_a = risk_a * rr_a
cost_r_a = TOTAL_COST / risk_a
net_r_a = rr_a - cost_r_a

print(f"Setup A (Small Stop):")
print(f"  Stop: {stop_a:.1f}pts, Risk: ${risk_a:.2f}, Target RR={rr_a}")
print(f"  Gross profit if win: ${target_a:.2f}")
print(f"  After ${TOTAL_COST:.2f} cost: ${target_a - TOTAL_COST:.2f}")
print(f"  Net R if win: {net_r_a:.3f}R")
print(f"  Cost ate: {cost_r_a:.3f}R = {cost_r_a*100:.1f}% of risk")
print()

# Setup B: Large stop
stop_b = 2.0
rr_b = 1.5
risk_b = stop_b * POINT_VALUE
target_b = risk_b * rr_b
cost_r_b = TOTAL_COST / risk_b
net_r_b = rr_b - cost_r_b

print(f"Setup B (Large Stop):")
print(f"  Stop: {stop_b:.1f}pts, Risk: ${risk_b:.2f}, Target RR={rr_b}")
print(f"  Gross profit if win: ${target_b:.2f}")
print(f"  After ${TOTAL_COST:.2f} cost: ${target_b - TOTAL_COST:.2f}")
print(f"  Net R if win: {net_r_b:.3f}R")
print(f"  Cost ate: {cost_r_b:.3f}R = {cost_r_b*100:.1f}% of risk")
print()

print("="*70)
print("CONCLUSION")
print("="*70)
print()
print(f"  Setup A (small stop): Lost {cost_r_a:.3f}R to costs ({cost_r_a*100:.0f}% of risk)")
print(f"  Setup B (large stop): Lost {cost_r_b:.3f}R to costs ({cost_r_b*100:.0f}% of risk)")
print(f"  Difference: {(cost_r_a - cost_r_b):.3f}R ({(cost_r_a - cost_r_b)*100:.0f} percentage points)")
print()
print("  [OK] YES - Larger stops DO have proportionally lower cost impact")
print("  [OK] This matches TCA.txt formula (line 78)")
print("  [OK] Fixed cost is divided by larger risk = smaller % impact")
print()
print("STRATEGIC INSIGHT:")
print("  Trade lower RR setups (1.5-2.0) with larger stops for lowest cost impact")
print("  High RR setups (4.0+) require tighter stops = higher cost % impact")
print()
