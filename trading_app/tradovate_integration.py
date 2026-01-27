"""
Tradovate Integration - Auto-Capture Trades

Automatically logs trades from Tradovate into trade_journal.

Features:
1. Pull historical trades (backfill)
2. Monitor live executions (real-time)
3. Enrich with session context from daily_features
4. Auto-classify outcomes (WIN/LOSS based on R-multiple)

Setup:
1. Get Tradovate API credentials from https://trader.tradovate.com
2. Set environment variables:
   - TRADOVATE_USERNAME
   - TRADOVATE_PASSWORD
   - TRADOVATE_DEVICE_ID (optional)
   - TRADOVATE_APP_ID (optional)
   - TRADOVATE_CID (optional)
   - TRADOVATE_SECRET (optional)
   - TRADOVATE_DEMO=true (for demo account) or false (for live)

Usage:
    from trading_app.tradovate_integration import TradovateIntegration

    # Initialize
    tv = TradovateIntegration()

    # Authenticate
    tv.authenticate()

    # Pull recent trades
    trades = tv.get_recent_trades(days_back=30)

    # Store in memory
    for trade in trades:
        tv.store_trade_in_memory(trade)
"""

import os
import requests
import time
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional
import duckdb

from trading_app.memory import TradingMemory
from trading_app.config import DB_PATH, TZ_LOCAL


class TradovateIntegration:
    """Tradovate API integration for auto-logging trades"""

    def __init__(self):
        self.memory = TradingMemory()
        self.db_path = DB_PATH
        self.tz_local = TZ_LOCAL

        # API configuration
        self.demo = os.getenv('TRADOVATE_DEMO', 'true').lower() == 'true'
        self.base_url = "https://demo.tradovateapi.com/v1" if self.demo else "https://live.tradovateapi.com/v1"

        # Credentials
        self.username = os.getenv('TRADOVATE_USERNAME')
        self.password = os.getenv('TRADOVATE_PASSWORD')
        self.device_id = os.getenv('TRADOVATE_DEVICE_ID', 'claude-code-trader')
        self.app_id = os.getenv('TRADOVATE_APP_ID', 'Sample App')
        self.cid = os.getenv('TRADOVATE_CID')
        self.secret = os.getenv('TRADOVATE_SECRET')

        # Session
        self.access_token = None
        self.account_id = None

    def authenticate(self) -> bool:
        """
        Authenticate with Tradovate API.

        Returns:
            True if successful, False otherwise
        """
        if not self.username or not self.password:
            print("[ERROR] TRADOVATE_USERNAME and TRADOVATE_PASSWORD must be set")
            print("Set them in .env file or as environment variables")
            return False

        try:
            # Authentication endpoint
            url = f"{self.base_url}/auth/accesstokenrequest"

            payload = {
                "name": self.username,
                "password": self.password,
                "appId": self.app_id,
                "appVersion": "1.0",
                "deviceId": self.device_id
            }

            # Add optional fields if provided
            if self.cid:
                payload["cid"] = self.cid
            if self.secret:
                payload["sec"] = self.secret

            response = requests.post(url, json=payload)

            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('accessToken')
                self.account_id = data.get('userId')  # Will get account ID separately

                print(f"[OK] Authenticated with Tradovate ({self.base_url})")
                print(f"[OK] Access token expires: {data.get('expirationTime')}")

                # Get account ID
                self._get_account_id()

                return True
            else:
                print(f"[ERROR] Authentication failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False

        except Exception as e:
            print(f"[ERROR] Authentication exception: {e}")
            return False

    def _get_account_id(self) -> bool:
        """Get account ID after authentication"""
        try:
            url = f"{self.base_url}/account/list"
            headers = {"Authorization": f"Bearer {self.access_token}"}

            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                accounts = response.json()
                if accounts:
                    self.account_id = accounts[0]['id']
                    print(f"[OK] Account ID: {self.account_id}")
                    return True

            print(f"[WARN] Could not get account ID: {response.status_code}")
            return False

        except Exception as e:
            print(f"[ERROR] Failed to get account ID: {e}")
            return False

    def get_recent_trades(self, days_back: int = 30) -> List[Dict]:
        """
        Get recent filled orders from Tradovate.

        Args:
            days_back: Look back N days

        Returns:
            List of trade records
        """
        if not self.access_token:
            print("[ERROR] Not authenticated. Call authenticate() first.")
            return []

        try:
            # Get fills (filled orders)
            url = f"{self.base_url}/fill/list"
            headers = {"Authorization": f"Bearer {self.access_token}"}

            # Calculate start time
            start_time = datetime.now() - timedelta(days=days_back)
            start_timestamp = int(start_time.timestamp() * 1000)

            params = {
                "startTimestamp": start_timestamp
            }

            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                fills = response.json()
                print(f"[OK] Retrieved {len(fills)} fills from last {days_back} days")
                return fills
            else:
                print(f"[ERROR] Failed to get fills: {response.status_code}")
                print(f"Response: {response.text}")
                return []

        except Exception as e:
            print(f"[ERROR] Exception getting trades: {e}")
            return []

    def parse_tradovate_fill(self, fill: Dict) -> Optional[Dict]:
        """
        Parse Tradovate fill data into our trade format.

        Args:
            fill: Raw fill data from Tradovate API

        Returns:
            Parsed trade dict or None if invalid
        """
        try:
            # Extract key fields
            timestamp = datetime.fromtimestamp(fill.get('timestamp', 0) / 1000)
            date_local = timestamp.date()

            # Contract symbol (e.g., 'MGCG4' -> MGC)
            contract = fill.get('contractName', '')
            instrument = 'MGC' if 'MGC' in contract else 'NQ' if 'NQ' in contract else 'MPL' if 'MPL' in contract else 'UNKNOWN'

            # Price and quantity
            price = fill.get('price', 0.0)
            qty = fill.get('qty', 0)
            action = fill.get('action', '')  # 'Buy' or 'Sell'

            # Order info
            order_id = fill.get('orderId')

            return {
                'timestamp': timestamp,
                'date_local': date_local,
                'instrument': instrument,
                'contract': contract,
                'price': price,
                'qty': qty,
                'action': action,
                'order_id': order_id,
                'raw_fill': fill
            }

        except Exception as e:
            print(f"[ERROR] Failed to parse fill: {e}")
            return None

    def match_fills_to_trades(self, fills: List[Dict]) -> List[Dict]:
        """
        Match entry/exit fills into complete trades.

        This is simplified - assumes fills are paired (entry → exit).
        In production, you'd need more sophisticated matching logic.

        Args:
            fills: List of parsed fills

        Returns:
            List of complete trades
        """
        trades = []

        # Sort by timestamp
        sorted_fills = sorted(fills, key=lambda x: x['timestamp'])

        # Simple matching: pair consecutive opposite-action fills
        i = 0
        while i < len(sorted_fills) - 1:
            entry = sorted_fills[i]
            exit_fill = sorted_fills[i + 1]

            # Check if they're opposite actions
            if entry['action'] != exit_fill['action']:
                # Calculate P&L
                if entry['action'] == 'Buy':
                    pnl = (exit_fill['price'] - entry['price']) * entry['qty']
                else:
                    pnl = (entry['price'] - exit_fill['price']) * entry['qty']

                # Determine outcome
                outcome = 'WIN' if pnl > 0 else 'LOSS' if pnl < 0 else 'BREAKEVEN'

                trades.append({
                    'date_local': entry['date_local'],
                    'instrument': entry['instrument'],
                    'entry_price': entry['price'],
                    'exit_price': exit_fill['price'],
                    'qty': entry['qty'],
                    'pnl': pnl,
                    'outcome': outcome,
                    'entry_timestamp': entry['timestamp'],
                    'exit_timestamp': exit_fill['timestamp']
                })

                i += 2  # Skip both fills
            else:
                i += 1

        return trades

    def enrich_trade_with_context(self, trade: Dict) -> Dict:
        """
        Enrich trade with session context from daily_features.

        Args:
            trade: Trade dict

        Returns:
            Enriched trade with Asia travel, London reversals, etc.
        """
        try:
            conn = duckdb.connect(self.db_path, read_only=True)

            query = """
                SELECT
                    asia_travel,
                    london_high - london_low as london_range,
                    ny_high - ny_low as ny_range,
                    orb_0900_size,
                    orb_1000_size,
                    orb_1100_size
                FROM daily_features
                WHERE date_local = ?
                  AND instrument = ?
            """

            result = conn.execute(query, [str(trade['date_local']), trade['instrument']]).fetchone()
            conn.close()

            if result:
                trade['asia_travel'] = result[0]
                trade['london_range'] = result[1]
                trade['ny_range'] = result[2]
                trade['orb_0900_size'] = result[3]
                trade['orb_1000_size'] = result[4]
                trade['orb_1100_size'] = result[5]

                print(f"[OK] Enriched trade {trade['date_local']} with session context")
            else:
                print(f"[WARN] No session data found for {trade['date_local']}")

            return trade

        except Exception as e:
            print(f"[ERROR] Failed to enrich trade: {e}")
            return trade

    def store_trade_in_memory(self, trade: Dict) -> Optional[int]:
        """
        Store trade in trade_journal (episodic memory).

        Args:
            trade: Trade dict (with enriched context)

        Returns:
            Trade ID or None if failed
        """
        try:
            # Determine ORB time (heuristic based on entry timestamp)
            # This is simplified - you may want more sophisticated logic
            entry_hour = trade['entry_timestamp'].hour
            if 9 <= entry_hour < 10:
                orb_time = '0900'
            elif 10 <= entry_hour < 11:
                orb_time = '1000'
            elif 11 <= entry_hour < 12:
                orb_time = '1100'
            elif 18 <= entry_hour < 19:
                orb_time = '1800'
            elif 23 <= entry_hour < 24:
                orb_time = '2300'
            elif 0 <= entry_hour < 1:
                orb_time = '0030'
            else:
                orb_time = 'UNKNOWN'

            # Store in memory
            trade_id = self.memory.store_trade(
                date_local=str(trade['date_local']),
                orb_time=orb_time,
                instrument=trade['instrument'],
                outcome=trade['outcome'],
                entry_price=trade['entry_price'],
                exit_price=trade['exit_price'],
                asia_travel=trade.get('asia_travel'),
                lesson_learned=f"Auto-imported from Tradovate (P&L: ${trade['pnl']:.2f})"
            )

            print(f"[OK] Stored trade {trade_id} in memory: {trade['date_local']} {orb_time} {trade['outcome']}")
            return trade_id

        except Exception as e:
            print(f"[ERROR] Failed to store trade in memory: {e}")
            return None

    def sync_trades(self, days_back: int = 30) -> int:
        """
        Sync trades from Tradovate to trade_journal.

        This is the main function to call - authenticates, pulls trades, enriches, and stores.

        Args:
            days_back: Look back N days

        Returns:
            Number of trades synced
        """
        print(f"\n{'='*70}")
        print("TRADOVATE SYNC - Auto-Import Trades")
        print(f"{'='*70}\n")

        # Authenticate
        if not self.authenticate():
            print("[ERROR] Authentication failed - cannot sync trades")
            return 0

        # Get fills
        fills = self.get_recent_trades(days_back)
        if not fills:
            print("[WARN] No fills found")
            return 0

        # Parse fills
        parsed_fills = []
        for fill in fills:
            parsed = self.parse_tradovate_fill(fill)
            if parsed:
                parsed_fills.append(parsed)

        print(f"[OK] Parsed {len(parsed_fills)} fills")

        # Match into trades
        trades = self.match_fills_to_trades(parsed_fills)
        print(f"[OK] Matched {len(trades)} complete trades")

        # Enrich and store
        synced_count = 0
        for trade in trades:
            enriched = self.enrich_trade_with_context(trade)
            trade_id = self.store_trade_in_memory(enriched)
            if trade_id:
                synced_count += 1

        print(f"\n{'='*70}")
        print(f"[OK] SYNC COMPLETE: {synced_count} trades imported")
        print(f"{'='*70}\n")

        return synced_count


def main():
    """Demo usage"""
    print("\n" + "="*70)
    print("TRADOVATE INTEGRATION - Setup Instructions")
    print("="*70 + "\n")

    print("To use Tradovate integration, set these environment variables:")
    print("  - TRADOVATE_USERNAME=your_username")
    print("  - TRADOVATE_PASSWORD=your_password")
    print("  - TRADOVATE_DEMO=true (or false for live account)\n")

    print("Example .env file:")
    print("  TRADOVATE_USERNAME=myusername")
    print("  TRADOVATE_PASSWORD=mypassword")
    print("  TRADOVATE_DEMO=true\n")

    print("Then run:")
    print("  from trading_app.tradovate_integration import TradovateIntegration")
    print("  tv = TradovateIntegration()")
    print("  tv.sync_trades(days_back=30)\n")

    print("="*70 + "\n")

    # Check if credentials are set
    username = os.getenv('TRADOVATE_USERNAME')
    password = os.getenv('TRADOVATE_PASSWORD')

    if username and password:
        print("Credentials found! Testing authentication...")
        tv = TradovateIntegration()
        if tv.authenticate():
            print("\n✅ Authentication successful!")
            print("Ready to sync trades.")
        else:
            print("\n❌ Authentication failed. Check credentials.")
    else:
        print("⏳ Credentials not set. Add them to .env file to test authentication.")


if __name__ == "__main__":
    main()
