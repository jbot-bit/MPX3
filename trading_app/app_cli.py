"""
Trading Intelligence Platform - CLI Version

Simple command-line interface. No browser needed.

Usage:
    python trading_app/app_cli.py
"""

import sys
from pathlib import Path
from datetime import datetime

# Setup paths
current_dir = Path(__file__).parent
repo_root = current_dir.parent
for p in [current_dir, repo_root]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from trading_app.market_scanner import MarketScanner
from trading_app.data_bridge import DataBridge
from trading_app.ai_chat import TradingAssistant
from trading_app.edge_tracker import EdgeTracker
from trading_app.config import TZ_LOCAL


def print_header(title):
    """Print section header"""
    print("\n" + "="*70)
    print(title)
    print("="*70 + "\n")


def print_section(title):
    """Print subsection"""
    print("\n" + title)
    print("-"*70)


def main():
    """Main CLI app"""
    print_header("TRADING INTELLIGENCE PLATFORM - CLI")
    now = datetime.now(TZ_LOCAL)
    print(f"Time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}\n")

    # Initialize modules
    print("Initializing modules...")
    scanner = MarketScanner()
    bridge = DataBridge()
    assistant = TradingAssistant()
    tracker = EdgeTracker()
    print("[OK] All modules loaded\n")

    # Menu loop
    while True:
        print_header("MAIN MENU")
        print("1. Market Scanner - Which setups are valid TODAY?")
        print("2. AI Assistant - Ask questions")
        print("3. Edge Tracker - Check edge health")
        print("4. Data Status - Check database health")
        print("5. Quick Analysis - System health + Market regime")
        print("0. Exit")

        choice = input("\nSelect option (0-5): ").strip()

        if choice == "1":
            # Market Scanner
            print_header("MARKET SCANNER")
            print("Scanning market conditions...\n")

            results = scanner.scan_all_setups()

            print(f"Date: {results['date_local']}")
            print(f"Valid Setups: {results['valid_count']}")
            print(f"Caution Setups: {results['caution_count']}")
            print(f"Invalid Setups: {results['invalid_count']}")
            print(f"\nSummary: {results['summary']}")

            if results['valid_setups']:
                print_section("[OK] VALID SETUPS - TAKE THESE TRADES")
                for setup in results['valid_setups']:
                    orb_time = setup['orb_time']
                    orb_size = setup['conditions']['orb_sizes'].get(orb_time)
                    print(f"\n{orb_time} ORB - {setup['confidence']} confidence")
                    print(f"  ORB Size: {orb_size:.3f}" if orb_size else "  ORB Size: Not formed")
                    print("  Reasons:")
                    for reason in setup['reasons']:
                        print(f"    - {reason}")

            if results['caution_setups']:
                print_section("[!] CAUTION SETUPS - Trade with Care")
                for setup in results['caution_setups']:
                    orb_time = setup['orb_time']
                    print(f"\n{orb_time} ORB - {setup['confidence']}")
                    for reason in setup['reasons']:
                        print(f"  - {reason}")

            if results['invalid_setups']:
                print_section("[X] INVALID SETUPS - Skip Today")
                for setup in results['invalid_setups']:
                    print(f"{setup['orb_time']} ORB - {setup['recommendation']}")

            input("\nPress Enter to continue...")

        elif choice == "2":
            # AI Assistant
            print_header("AI ASSISTANT")
            print("Ask questions about performance, edges, patterns, or market regime.")
            print("Type 'back' to return to main menu.\n")

            while True:
                question = input("Question: ").strip()

                if question.lower() == 'back':
                    break

                if not question:
                    continue

                print("\nThinking...\n")
                response = assistant.ask(question)
                print(response)
                print()

        elif choice == "3":
            # Edge Tracker
            print_header("EDGE TRACKER")
            print("Checking edge health...\n")

            status = tracker.get_system_status()

            if status['status'] != 'NO_DATA':
                print(f"System Status: {status['status']}")
                print(f"{status['message']}\n")

                print(f"Total Edges: {status['total_edges']}")
                print(f"  Excellent: {len(status['excellent'])}")
                print(f"  Healthy: {len(status['healthy'])}")
                print(f"  Watch: {len(status['watch'])}")
                print(f"  Degraded: {len(status['degraded'])}")

                if status['degraded']:
                    print(f"\n[!] DEGRADED EDGES: {', '.join(status['degraded'])}")

                if status['excellent']:
                    print(f"[*] BEST PERFORMERS: {', '.join(status['excellent'])}")

                # Show individual edge details
                print_section("INDIVIDUAL EDGE DETAILS")
                for edge in status['edge_health']:
                    health = tracker.check_edge_health(edge['orb_time'])
                    if health['has_baseline']:
                        print(f"\n{edge['orb_time']} ORB - {health['status']}")
                        print(f"  Baseline: WR={health['baseline']['win_rate']:.1f}%, E[R]={health['baseline']['expected_r']:.2f}")

                        if health['performance']['30d']['has_data']:
                            perf = health['performance']['30d']
                            print(f"  Recent (30d): WR={perf['win_rate']:.1f}%, AvgR={perf['avg_r']:.2f}, Trades={perf['total_trades']}")

                        print("  Recommendations:")
                        for rec in health['recommendations']:
                            print(f"    - {rec}")

                # Market regime
                print_section("MARKET REGIME")
                regime = tracker.detect_regime()
                print(f"Regime: {regime['regime']} ({regime['confidence']:.0%} confidence)")
                print(f"{regime['message']}")

            else:
                print("No edge data available. Run edge discovery to populate validated_setups.")

            input("\nPress Enter to continue...")

        elif choice == "4":
            # Data Status
            print_header("DATA STATUS")

            status = bridge.get_status()

            print(f"Last DB Date: {status['last_db_date']}")
            print(f"Current Date: {status['current_date']}")
            print(f"Gap: {status['gap_days']} days")
            print(f"Data Current: {status['data_current']}")
            print(f"Needs Update: {status['needs_update']}")

            if status['needs_update']:
                print(f"\n[!] Data is {status['gap_days']} days behind")
                update = input("\nUpdate data now? (y/n): ").strip().lower()

                if update == 'y':
                    print("\nUpdating data...")
                    success = bridge.update_to_current()
                    if success:
                        print("[OK] Data updated!")
                    else:
                        print("[ERROR] Update failed")
            else:
                print("\n[OK] Data is current")

            input("\nPress Enter to continue...")

        elif choice == "5":
            # Quick Analysis
            print_header("QUICK ANALYSIS")

            print("System Health:")
            print("-"*70)
            response = assistant.ask("system health")
            print(response)

            print("\n\nMarket Regime:")
            print("-"*70)
            response = assistant.ask("market regime")
            print(response)

            input("\nPress Enter to continue...")

        elif choice == "0":
            # Exit
            print("\nExiting. Trade safe! 🎯")
            break

        else:
            print("\n[ERROR] Invalid choice. Please select 0-5.")
            input("\nPress Enter to continue...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted. Exiting...")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
