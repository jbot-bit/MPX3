"""
Optimize half-stop edges for primary ORBs (0900, 1000, 1100, 1800).

We tested full stops for these but missed half stops.
This ensures equal coverage for both SL modes.
"""

import subprocess
import sys

# Missing half-stop edges for primary ORBs
MISSING_EDGES = [
    # 0900 ORB (half)
    ('0900', 1.5, 'half'), ('0900', 2.0, 'half'), ('0900', 2.5, 'half'),
    ('0900', 3.0, 'half'), ('0900', 4.0, 'half'), ('0900', 5.0, 'half'),
    ('0900', 6.0, 'half'), ('0900', 8.0, 'half'),

    # 1000 ORB (half)
    ('1000', 1.5, 'half'), ('1000', 2.0, 'half'), ('1000', 2.5, 'half'),
    ('1000', 3.0, 'half'), ('1000', 4.0, 'half'), ('1000', 5.0, 'half'),
    ('1000', 6.0, 'half'), ('1000', 8.0, 'half'),

    # 1100 ORB (half)
    ('1100', 1.5, 'half'), ('1100', 2.0, 'half'), ('1100', 2.5, 'half'),
    ('1100', 3.0, 'half'), ('1100', 4.0, 'half'), ('1100', 5.0, 'half'),
    ('1100', 6.0, 'half'),

    # 1800 ORB (half)
    ('1800', 1.5, 'half'), ('1800', 2.0, 'half'), ('1800', 2.5, 'half'),
    ('1800', 3.0, 'half'), ('1800', 4.0, 'half'),
]

print("="*80)
print("OPTIMIZING MISSING HALF-STOP EDGES")
print("="*80)
print()
print(f"Total missing edges: {len(MISSING_EDGES)}")
print()
print("These edges were not tested in the original optimization run.")
print("Testing now to ensure equal coverage of full vs half stops.")
print()

completed = 0
failed = 0

for orb_time, rr, sl_mode in MISSING_EDGES:
    print(f"[{completed+1}/{len(MISSING_EDGES)}] Optimizing {orb_time} ORB RR={rr} {sl_mode.upper()}...")

    try:
        result = subprocess.run(
            [sys.executable, 'filter_optimizer.py',
             '--orb', orb_time,
             '--rr', str(rr),
             '--sl-mode', sl_mode,
             '--export', f'results/{orb_time}_RR{rr}_{sl_mode}.csv'],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes per edge
        )

        if result.returncode == 0:
            print(f"  [OK] Completed")
            completed += 1
        else:
            print(f"  [ERROR] Failed: {result.stderr[:200]}")
            failed += 1

    except subprocess.TimeoutExpired:
        print(f"  [ERROR] Timeout after 5 minutes")
        failed += 1
    except Exception as e:
        print(f"  [ERROR] {str(e)[:200]}")
        failed += 1

    print()

print("="*80)
print("OPTIMIZATION COMPLETE")
print("="*80)
print()
print(f"Completed: {completed}/{len(MISSING_EDGES)}")
print(f"Failed: {failed}/{len(MISSING_EDGES)}")
print()

if completed > 0:
    print("Next steps:")
    print("  1. Re-run TCA analysis: python tca_professional.py")
    print("  2. Check if any half-stop edges pass >= 0.10R threshold")
    print("  3. Update validated_setups if new edges found")
else:
    print("[ERROR] No edges completed successfully. Check database and backfill data.")
