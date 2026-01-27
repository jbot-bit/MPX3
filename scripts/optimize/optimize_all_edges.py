"""
Batch optimize filters for all 41 viable edges (excluding RR=1.0)

Runs filter optimizer for each ORB at each discovered RR level.
"""

import subprocess
import sys
from datetime import datetime

# All viable edges (excluding RR=1.0)
EDGES = [
    # 0030 ORB (half SL)
    ('0030', 1.5, 'half'), ('0030', 2.0, 'half'), ('0030', 2.5, 'half'),
    ('0030', 3.0, 'half'), ('0030', 4.0, 'half'), ('0030', 6.0, 'half'),

    # 0900 ORB (full SL)
    ('0900', 1.5, 'full'), ('0900', 2.0, 'full'), ('0900', 2.5, 'full'),
    ('0900', 3.0, 'full'), ('0900', 4.0, 'full'), ('0900', 5.0, 'full'),
    ('0900', 6.0, 'full'), ('0900', 8.0, 'full'),

    # 1000 ORB (full SL)
    ('1000', 1.5, 'full'), ('1000', 2.0, 'full'), ('1000', 2.5, 'full'),
    ('1000', 3.0, 'full'), ('1000', 4.0, 'full'), ('1000', 5.0, 'full'),
    ('1000', 6.0, 'full'), ('1000', 8.0, 'full'),

    # 1100 ORB (full SL)
    ('1100', 1.5, 'full'), ('1100', 2.0, 'full'), ('1100', 2.5, 'full'),
    ('1100', 3.0, 'full'), ('1100', 4.0, 'full'), ('1100', 5.0, 'full'),
    ('1100', 6.0, 'full'),

    # 1800 ORB (full SL)
    ('1800', 1.5, 'full'), ('1800', 2.0, 'full'), ('1800', 2.5, 'full'),
    ('1800', 3.0, 'full'), ('1800', 4.0, 'full'),

    # 2300 ORB (half SL)
    ('2300', 1.5, 'half'), ('2300', 2.0, 'half'), ('2300', 2.5, 'half'),
    ('2300', 3.0, 'half'), ('2300', 4.0, 'half'), ('2300', 5.0, 'half'),
    ('2300', 6.0, 'half'),
]

def main():
    print("=" * 80)
    print("BATCH FILTER OPTIMIZATION - ALL 41 VIABLE EDGES")
    print("=" * 80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total edges to optimize: {len(EDGES)}")
    print()

    successful = 0
    failed = 0
    failed_edges = []

    for i, (orb, rr, sl_mode) in enumerate(EDGES, 1):
        print(f"\n[{i}/{len(EDGES)}] Optimizing {orb} ORB | RR={rr} | SL={sl_mode}")
        print("-" * 80)

        try:
            # Run filter optimizer
            result = subprocess.run(
                ['python', 'filter_optimizer.py',
                 '--orb', orb,
                 '--rr', str(rr),
                 '--sl-mode', sl_mode,
                 '--export', f'results/{orb}_RR{rr}_{sl_mode}.csv'],
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout per edge
            )

            if result.returncode == 0:
                print(f"[OK] {orb} RR={rr} {sl_mode} - Optimization complete")
                successful += 1
            else:
                print(f"[ERROR] {orb} RR={rr} {sl_mode} - Failed (exit code {result.returncode})")
                print(result.stderr[:200])
                failed += 1
                failed_edges.append((orb, rr, sl_mode))

        except subprocess.TimeoutExpired:
            print(f"[ERROR] {orb} RR={rr} {sl_mode} - Timeout (> 2 minutes)")
            failed += 1
            failed_edges.append((orb, rr, sl_mode))
        except Exception as e:
            print(f"[ERROR] {orb} RR={rr} {sl_mode} - Exception: {e}")
            failed += 1
            failed_edges.append((orb, rr, sl_mode))

    # Summary
    print("\n" + "=" * 80)
    print("BATCH OPTIMIZATION COMPLETE")
    print("=" * 80)
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Successful: {successful}/{len(EDGES)}")
    print(f"Failed: {failed}/{len(EDGES)}")

    if failed_edges:
        print("\nFailed edges:")
        for orb, rr, sl_mode in failed_edges:
            print(f"  - {orb} RR={rr} {sl_mode}")

    print(f"\nResults saved to: results/")

    return 0 if failed == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
