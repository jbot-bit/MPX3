"""
Scheduled Data Update - Auto-update 30min before ORBs

Run this script in the background to auto-update data before trading sessions.

Usage:
    python trading_app/scheduled_update.py

Schedule (Brisbane time):
- 08:30 (30min before 0900 ORB)
- 09:30 (30min before 1000 ORB)
- 10:30 (30min before 1100 ORB)
- 17:30 (30min before 1800 ORB)
- 22:30 (30min before 2300 ORB)
- 00:00 (30min before 0030 ORB)

Configure in .env:
    AUTO_UPDATE_ENABLED=true   # Enable scheduled updates
    AUTO_UPDATE_TIMES=08:30,09:30,10:30,17:30,22:30,00:00
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Setup paths
current_dir = Path(__file__).parent
repo_root = current_dir.parent
for p in [current_dir, repo_root]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from trading_app.data_bridge import DataBridge
from trading_app.config import TZ_LOCAL

# Load config
load_dotenv()
AUTO_UPDATE_ENABLED = os.getenv('AUTO_UPDATE_ENABLED', 'false').lower() == 'true'
AUTO_UPDATE_TIMES = os.getenv('AUTO_UPDATE_TIMES', '08:30,09:30,10:30,17:30,22:30,00:00').split(',')


def should_update_now():
    """Check if current time matches any scheduled update time"""
    now = datetime.now(TZ_LOCAL)
    current_time = now.strftime('%H:%M')

    return current_time in AUTO_UPDATE_TIMES


def run_update():
    """Run data update"""
    print(f"\n{'='*70}")
    print(f"SCHEDULED UPDATE - {datetime.now(TZ_LOCAL).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    bridge = DataBridge()
    status = bridge.get_status()

    if status['needs_update']:
        print(f"[INFO] Data gap detected: {status['gap_days']} days")
        print("[INFO] Running update...")

        success = bridge.update_to_current()

        if success:
            print("\n[OK] Update completed successfully!")
        else:
            print("\n[ERROR] Update failed")
    else:
        print("[OK] Data is current - no update needed")

    print(f"\n{'='*70}\n")


def main():
    """Main scheduler loop"""
    if not AUTO_UPDATE_ENABLED:
        print("[INFO] Scheduled updates are DISABLED")
        print("[INFO] Set AUTO_UPDATE_ENABLED=true in .env to enable")
        print("[INFO] Using manual updates only (saves API calls)")
        return

    print(f"\n{'='*70}")
    print("SCHEDULED DATA UPDATE - RUNNING")
    print(f"{'='*70}\n")
    print(f"Timezone: {TZ_LOCAL}")
    print(f"Update times: {', '.join(AUTO_UPDATE_TIMES)}")
    print(f"Status: ENABLED")
    print("\nWaiting for next scheduled update...")
    print("Press Ctrl+C to stop\n")

    last_update_minute = None

    try:
        while True:
            now = datetime.now(TZ_LOCAL)
            current_minute = now.strftime('%H:%M')

            # Check if we should update (and haven't already this minute)
            if should_update_now() and current_minute != last_update_minute:
                run_update()
                last_update_minute = current_minute

            # Sleep for 30 seconds (check twice per minute)
            time.sleep(30)

    except KeyboardInterrupt:
        print("\n[INFO] Scheduler stopped by user")


if __name__ == "__main__":
    main()
