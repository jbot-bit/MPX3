"""
Trading Memory - Living Memory System for Adaptive Intelligence

Maintains 4 types of memory:
1. Episodic - Specific trades with full context
2. Semantic - Patterns and correlations learned from history
3. Working - Current session state and real-time context
4. Procedural - Execution skills and quality tracking

Usage:
    from trading_app.memory import TradingMemory

    memory = TradingMemory()

    # Store a trade
    memory.store_trade(
        date_local='2026-01-25',
        orb_time='0900',
        outcome='WIN',
        r_multiple=2.3,
        asia_travel=1.8,
        lesson_learned='Perfect setup - high Asia travel with clean break'
    )

    # Query similar sessions
    similar = memory.query_similar_sessions(
        asia_travel=1.8,
        london_reversals=2
    )

    # Learn patterns
    patterns = memory.discover_patterns(
        min_confidence=0.7,
        min_sample_size=30
    )
"""

import duckdb
import json
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from trading_app.config import DB_PATH, TZ_LOCAL


class TradingMemory:
    """Living memory system for trading intelligence"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.tz_local = TZ_LOCAL

    # =========================================================================
    # EPISODIC MEMORY: Store and Query Specific Trades
    # =========================================================================

    def store_trade(
        self,
        trade: Optional[Dict] = None,
        date_local: Optional[str] = None,
        orb_time: Optional[str] = None,
        instrument: str = 'MGC',
        outcome: str = 'SKIP',
        r_multiple: Optional[float] = None,  # Theoretical R (without costs)
        realized_rr: Optional[float] = None,  # Realized R (with costs embedded) - PREFERRED
        entry_price: Optional[float] = None,
        exit_price: Optional[float] = None,
        mae: Optional[float] = None,
        mfe: Optional[float] = None,
        asia_travel: Optional[float] = None,
        london_reversals: Optional[int] = None,
        pre_orb_travel: Optional[float] = None,
        liquidity_state: str = 'normal',
        lesson_learned: Optional[str] = None,
        notable: bool = False,
        **kwargs
    ) -> bool:
        """
        Store a trade in episodic memory.

        Can be called with a dict or individual parameters:
            memory.store_trade({'date_local': '2026-01-15', 'orb_time': '0900', ...})
            memory.store_trade(date_local='2026-01-15', orb_time='0900', ...)

        Args:
            trade: Dict with trade data (alternative to individual params)
            date_local: Trading date (YYYY-MM-DD or date object)
            orb_time: ORB time (0900, 1000, 1100, etc.)
            instrument: Instrument (MGC, NQ, MPL)
            outcome: WIN, LOSS, SKIP, BREAKEVEN
            r_multiple: R-multiple achieved (theoretical, without costs) - DEPRECATED
            realized_rr: Realized R-multiple (with costs embedded) - PREFERRED
            lesson_learned: Post-trade insight
            notable: Flag exceptional events
            **kwargs: Additional context (slippage, fill_time_ms, realized_rr, etc.)

        Returns:
            True if stored successfully
        """
        # Handle dict parameter
        if trade is not None:
            date_local = trade.get('date_local')
            orb_time = trade.get('orb_time')
            instrument = trade.get('instrument', 'MGC')
            outcome = trade.get('outcome', 'SKIP')
            r_multiple = trade.get('r_multiple')
            realized_rr = trade.get('realized_rr')  # Preferred over r_multiple
            entry_price = trade.get('entry_price')
            exit_price = trade.get('exit_price')
            mae = trade.get('mae')
            mfe = trade.get('mfe')
            asia_travel = trade.get('asia_travel')
            london_reversals = trade.get('london_reversals')
            pre_orb_travel = trade.get('pre_orb_travel')
            liquidity_state = trade.get('liquidity_state', 'normal')
            lesson_learned = trade.get('lesson_learned')
            notable = trade.get('notable', False)
            # Merge any additional fields from dict
            for k, v in trade.items():
                if k not in ['date_local', 'orb_time', 'instrument', 'outcome', 'r_multiple', 'realized_rr',
                             'entry_price', 'exit_price', 'mae', 'mfe', 'asia_travel',
                             'london_reversals', 'pre_orb_travel', 'liquidity_state',
                             'lesson_learned', 'notable']:
                    kwargs[k] = v

        # Convert date object to string if needed
        if isinstance(date_local, date):
            date_local = date_local.strftime('%Y-%m-%d')

        conn = duckdb.connect(self.db_path)

        # Build session context JSON
        # Store realized_rr in session_context (no schema change needed)
        session_context = {
            'asia_travel': asia_travel,
            'london_reversals': london_reversals,
            'pre_orb_travel': pre_orb_travel,
            'liquidity_state': liquidity_state,
            'realized_rr': realized_rr  # Store realized R (with costs) for analysis
        }
        session_context.update(kwargs)
        session_context_json = json.dumps(session_context)

        # Insert trade
        try:
            conn.execute("""
                INSERT INTO trade_journal (
                    date_local, orb_time, instrument, outcome, r_multiple,
                    entry_price, exit_price, mae, mfe,
                    asia_travel, london_reversals, pre_orb_travel, liquidity_state,
                    session_context, lesson_learned, notable
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                date_local, orb_time, instrument, outcome, r_multiple,
                entry_price, exit_price, mae, mfe,
                asia_travel, london_reversals, pre_orb_travel, liquidity_state,
                session_context_json, lesson_learned, notable
            ])
            conn.close()
            return True
        except Exception as e:
            print(f"[ERROR] Failed to store trade: {e}")
            conn.close()
            return False

    def query_trades(
        self,
        instrument: str = 'MGC',
        orb_time: Optional[str] = None,
        outcome: Optional[str] = None,
        days_back: int = 365,
        limit: int = 100
    ) -> List[Dict]:
        """
        Query trades from episodic memory.

        Args:
            instrument: Filter by instrument
            orb_time: Filter by ORB time
            outcome: Filter by outcome (WIN, LOSS, etc.)
            days_back: Look back N days
            limit: Max results

        Returns:
            List of trade records
        """
        conn = duckdb.connect(self.db_path, read_only=True)

        query = f"""
            SELECT
                id, date_local, orb_time, instrument, outcome, r_multiple,
                asia_travel, london_reversals, pre_orb_travel,
                lesson_learned, notable
            FROM trade_journal
            WHERE instrument = ?
              AND date_local >= CURRENT_DATE - INTERVAL '{days_back} days'
        """
        params = [instrument]

        if orb_time:
            query += " AND orb_time = ?"
            params.append(orb_time)

        if outcome:
            query += " AND outcome = ?"
            params.append(outcome)

        query += " ORDER BY date_local DESC LIMIT ?"
        params.append(limit)

        results = conn.execute(query, params).fetchall()
        conn.close()

        # Convert to list of dicts
        columns = [
            'id', 'date_local', 'orb_time', 'instrument', 'outcome', 'r_multiple',
            'asia_travel', 'london_reversals', 'pre_orb_travel',
            'lesson_learned', 'notable'
        ]
        trades = [dict(zip(columns, row)) for row in results]

        return trades

    def query_similar_sessions(
        self,
        asia_travel: float,
        london_reversals: Optional[int] = None,
        tolerance: float = 0.5,
        instrument: str = 'MGC',
        days_back: int = 730
    ) -> List[Dict]:
        """
        Find sessions with similar market conditions.

        Args:
            asia_travel: Asia session travel
            london_reversals: London reversals count
            tolerance: Match tolerance (e.g., asia_travel ± 0.5)
            instrument: Instrument
            days_back: Look back N days

        Returns:
            List of similar trades with confidence scores
        """
        conn = duckdb.connect(self.db_path, read_only=True)

        query = f"""
            SELECT
                id, date_local, orb_time, outcome, r_multiple,
                asia_travel, london_reversals, pre_orb_travel,
                lesson_learned,
                ABS(asia_travel - ?) as asia_diff
            FROM trade_journal
            WHERE instrument = ?
              AND date_local >= CURRENT_DATE - INTERVAL '{days_back} days'
              AND asia_travel BETWEEN ? AND ?
        """
        params = [
            asia_travel,
            instrument,
            asia_travel - tolerance,
            asia_travel + tolerance
        ]

        if london_reversals is not None:
            query += " AND london_reversals = ?"
            params.append(london_reversals)

        query += " ORDER BY asia_diff ASC LIMIT 20"

        results = conn.execute(query, params).fetchall()
        conn.close()

        # Convert to dicts with confidence scores
        trades = []
        for row in results:
            confidence = 1.0 - (row[9] / tolerance)  # asia_diff index
            confidence = max(0.0, min(1.0, confidence))

            trades.append({
                'id': row[0],
                'date_local': row[1],
                'orb_time': row[2],
                'outcome': row[3],
                'r_multiple': row[4],
                'asia_travel': row[5],
                'london_reversals': row[6],
                'pre_orb_travel': row[7],
                'lesson_learned': row[8],
                'confidence': confidence
            })

        return trades

    # =========================================================================
    # SEMANTIC MEMORY: Learn and Store Patterns
    # =========================================================================

    def store_pattern(
        self,
        pattern_id: str,
        description: str,
        condition_sql: str,
        instruments: str = 'MGC',
        confidence: float = 0.0,
        sample_size: int = 0,
        win_rate: Optional[float] = None,
        avg_rr: Optional[float] = None,
        total_r: Optional[float] = None,
        hypothesis: Optional[str] = None,
        status: str = 'testing'
    ) -> bool:
        """
        Store a learned pattern in semantic memory.

        Args:
            pattern_id: Unique pattern ID (e.g., 'asia_high_london_quiet')
            description: Human-readable pattern description
            condition_sql: SQL WHERE clause to identify pattern
            instruments: Instruments pattern applies to
            confidence: Pattern confidence (0.0-1.0)
            sample_size: Number of trades supporting pattern
            win_rate: Pattern win rate
            avg_rr: Average R-multiple
            total_r: Total R generated
            hypothesis: Why this pattern works
            status: Pattern status (testing, active, degraded, invalidated)

        Returns:
            True if stored successfully
        """
        conn = duckdb.connect(self.db_path)

        try:
            conn.execute("""
                INSERT OR REPLACE INTO learned_patterns (
                    pattern_id, description, condition_sql, instruments,
                    confidence, sample_size, win_rate, avg_rr, total_r,
                    hypothesis, status, discovered_date, last_validated
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_DATE, CURRENT_DATE)
            """, [
                pattern_id, description, condition_sql, instruments,
                confidence, sample_size, win_rate, avg_rr, total_r,
                hypothesis, status
            ])
            conn.close()
            return True
        except Exception as e:
            print(f"[ERROR] Failed to store pattern: {e}")
            conn.close()
            return False

    def query_patterns(
        self,
        status: str = 'active',
        min_confidence: float = 0.7,
        instrument: str = 'MGC'
    ) -> List[Dict]:
        """
        Query learned patterns from semantic memory.

        Args:
            status: Filter by status (active, testing, degraded)
            min_confidence: Minimum confidence threshold
            instrument: Filter by instrument

        Returns:
            List of learned patterns
        """
        conn = duckdb.connect(self.db_path, read_only=True)

        query = """
            SELECT
                pattern_id, description, condition_sql, instruments,
                confidence, sample_size, win_rate, avg_rr, total_r,
                hypothesis, status, discovered_date, last_validated
            FROM learned_patterns
            WHERE status = ?
              AND confidence >= ?
              AND (instruments = ? OR instruments = 'ALL')
            ORDER BY confidence DESC, sample_size DESC
        """

        results = conn.execute(query, [status, min_confidence, instrument]).fetchall()
        conn.close()

        columns = [
            'pattern_id', 'description', 'condition_sql', 'instruments',
            'confidence', 'sample_size', 'win_rate', 'avg_rr', 'total_r',
            'hypothesis', 'status', 'discovered_date', 'last_validated'
        ]
        patterns = [dict(zip(columns, row)) for row in results]

        return patterns

    def learn_patterns(
        self,
        min_confidence: float = 0.7,
        min_sample_size: int = 30,
        days_back: int = 730
    ) -> List[Dict]:
        """
        Learn patterns from trade history (alias for discover_patterns).

        Args:
            min_confidence: Minimum confidence to return pattern
            min_sample_size: Minimum trades to validate pattern
            days_back: Look back N days

        Returns:
            List of learned patterns
        """
        return self.discover_patterns(min_confidence, min_sample_size, days_back)

    def discover_patterns(
        self,
        min_confidence: float = 0.7,
        min_sample_size: int = 30,
        days_back: int = 730
    ) -> List[Dict]:
        """
        Discover new patterns from trade history using basic heuristics.

        This is a simplified pattern discovery - looks for:
        1. High Asia travel + Low London reversals → Strong ORB breaks
        2. Quiet Asia + Active London → Weak ORB breaks
        3. Pre-ORB travel > X → Higher success rate

        Args:
            min_confidence: Minimum confidence to return pattern
            min_sample_size: Minimum trades to validate pattern
            days_back: Look back N days

        Returns:
            List of discovered patterns
        """
        conn = duckdb.connect(self.db_path, read_only=True)

        discovered = []

        # Pattern 1: High Asia travel + Low London reversals
        pattern_1 = conn.execute(f"""
            SELECT
                COUNT(*) as trades,
                SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                AVG(r_multiple) as avg_r,
                SUM(r_multiple) as total_r
            FROM trade_journal
            WHERE asia_travel > 2.0
              AND london_reversals < 3
              AND outcome IN ('WIN', 'LOSS')
              AND date_local >= CURRENT_DATE - INTERVAL '{days_back} days'
        """).fetchone()

        if pattern_1 and pattern_1[0] >= min_sample_size:
            trades, wins, avg_r, total_r = pattern_1
            win_rate = (wins / trades) * 100 if trades > 0 else 0
            confidence = min(1.0, win_rate / 70.0)  # Scale WR to confidence

            if confidence >= min_confidence:
                discovered.append({
                    'pattern_id': 'asia_high_london_quiet',
                    'description': 'High Asia travel (>2.0) + Low London reversals (<3) → Strong ORB breaks',
                    'condition_sql': 'asia_travel > 2.0 AND london_reversals < 3',
                    'confidence': confidence,
                    'sample_size': trades,
                    'win_rate': win_rate,
                    'avg_rr': avg_r,
                    'total_r': total_r,
                    'hypothesis': 'High Asia travel = energy buildup, quiet London = coiling, explosive NY release'
                })

        # Pattern 2: Quiet Asia + Active London (inverse relationship)
        pattern_2 = conn.execute(f"""
            SELECT
                COUNT(*) as trades,
                SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                AVG(r_multiple) as avg_r,
                SUM(r_multiple) as total_r
            FROM trade_journal
            WHERE asia_travel < 1.0
              AND london_reversals > 5
              AND outcome IN ('WIN', 'LOSS')
              AND date_local >= CURRENT_DATE - INTERVAL '{days_back} days'
        """).fetchone()

        if pattern_2 and pattern_2[0] >= min_sample_size:
            trades, wins, avg_r, total_r = pattern_2
            win_rate = (wins / trades) * 100 if trades > 0 else 0
            confidence = min(1.0, (100 - win_rate) / 70.0)  # Low WR = pattern validated

            if win_rate < 45:  # Inverse pattern - low WR confirms
                discovered.append({
                    'pattern_id': 'asia_quiet_london_choppy',
                    'description': 'Quiet Asia (<1.0) + Choppy London (>5 reversals) → Weak ORB breaks',
                    'condition_sql': 'asia_travel < 1.0 AND london_reversals > 5',
                    'confidence': confidence,
                    'sample_size': trades,
                    'win_rate': win_rate,
                    'avg_rr': avg_r,
                    'total_r': total_r,
                    'hypothesis': 'Low Asia energy + choppy London = no directional bias, avoid trades'
                })

        conn.close()
        return discovered

    # =========================================================================
    # WORKING MEMORY: Current Session State
    # =========================================================================

    def update_session_state(
        self,
        date_local: str,
        instrument: str = 'MGC',
        **kwargs
    ) -> bool:
        """
        Update current session state in working memory.

        Args:
            date_local: Trading date (YYYY-MM-DD)
            instrument: Instrument
            **kwargs: Session metrics to update (asia_travel, london_reversals, etc.)

        Returns:
            True if updated successfully
        """
        conn = duckdb.connect(self.db_path)

        # Build SET clause dynamically
        set_parts = ['instrument = ?', 'updated_at = CURRENT_TIMESTAMP']
        params = [instrument]

        for key, value in kwargs.items():
            set_parts.append(f"{key} = ?")
            params.append(value)

        params.append(date_local)

        query = f"""
            INSERT INTO session_state (date_local, {', '.join(kwargs.keys())}, instrument)
            VALUES (?, {', '.join(['?'] * len(kwargs))}, ?)
            ON CONFLICT (date_local) DO UPDATE SET {', '.join(set_parts)}
        """

        try:
            conn.execute(query, [date_local] + list(kwargs.values()) + params)
            conn.close()
            return True
        except Exception as e:
            print(f"[ERROR] Failed to update session state: {e}")
            conn.close()
            return False

    def get_session_state(self, date_local: str) -> Optional[Dict]:
        """Get current session state"""
        conn = duckdb.connect(self.db_path, read_only=True)

        result = conn.execute("""
            SELECT
                date_local, instrument,
                asia_travel, london_reversals, pre_orb_0900_travel,
                liquidity_state, regime, regime_confidence
            FROM session_state
            WHERE date_local = ?
        """, [date_local]).fetchone()
        conn.close()

        if result:
            return {
                'date_local': result[0],
                'instrument': result[1],
                'asia_travel': result[2],
                'london_reversals': result[3],
                'pre_orb_0900_travel': result[4],
                'liquidity_state': result[5],
                'regime': result[6],
                'regime_confidence': result[7]
            }
        return None

    # =========================================================================
    # ANALYSIS: Query Memory for Insights
    # =========================================================================

    def get_recent_performance(
        self,
        orb_time: str,
        instrument: str = 'MGC',
        days_back: int = 30
    ) -> Dict:
        """
        Get recent performance metrics for a specific setup.

        Args:
            orb_time: ORB time
            instrument: Instrument
            days_back: Look back N days

        Returns:
            Performance summary
        """
        conn = duckdb.connect(self.db_path, read_only=True)

        result = conn.execute(f"""
            SELECT
                COUNT(*) as total_trades,
                SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
                AVG(r_multiple) as avg_r,
                SUM(r_multiple) as total_r,
                MAX(date_local) as last_trade_date
            FROM trade_journal
            WHERE instrument = ?
              AND orb_time = ?
              AND date_local >= CURRENT_DATE - INTERVAL '{days_back} days'
              AND outcome IN ('WIN', 'LOSS')
        """, [instrument, orb_time]).fetchone()
        conn.close()

        if result and result[0] > 0:
            total, wins, losses, avg_r, total_r, last_date = result
            win_rate = (wins / total) * 100 if total > 0 else 0

            return {
                'total_trades': total,
                'wins': wins,
                'losses': losses,
                'win_rate': win_rate,
                'avg_r': avg_r,
                'total_r': total_r,
                'last_trade_date': last_date
            }

        return {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0.0,
            'avg_r': 0.0,
            'total_r': 0.0,
            'last_trade_date': None
        }

    def analyze_current_session(
        self,
        date_local: date,
        instrument: str = 'MGC'
    ) -> Dict:
        """
        Analyze current session and provide recommendations based on memory.

        Args:
            date_local: Trading date
            instrument: Instrument

        Returns:
            Analysis with recommendations
        """
        # Convert date to string if needed
        if isinstance(date_local, date):
            date_str = date_local.strftime('%Y-%m-%d')
        else:
            date_str = str(date_local)

        # Get session state from database
        conn = duckdb.connect(self.db_path, read_only=True)

        # Get today's conditions from daily_features
        conditions = conn.execute("""
            SELECT
                asia_high - asia_low as asia_travel,
                london_high, london_low
            FROM daily_features
            WHERE date_local = ?
              AND instrument = ?
        """, [date_str, instrument]).fetchone()

        if not conditions:
            conn.close()
            return {
                'date_local': date_local,
                'instrument': instrument,
                'data_available': False,
                'message': 'No data available for this session',
                'recommendations': []
            }

        asia_travel = conditions[0]

        # Find similar historical sessions
        similar = self.query_similar_sessions(
            asia_travel=asia_travel if asia_travel else 2.0,
            tolerance=0.5,
            instrument=instrument,
            days_back=180
        )

        conn.close()

        # Calculate win rate from similar sessions
        if similar:
            wins = sum(1 for s in similar if s['outcome'] == 'WIN')
            total = len(similar)
            win_rate = (wins / total) * 100 if total > 0 else 0
        else:
            win_rate = 0
            total = 0

        # Generate recommendations
        recommendations = []
        if win_rate > 60:
            recommendations.append('High confidence: Similar conditions have 60%+ win rate')
        elif win_rate > 50:
            recommendations.append('Moderate confidence: Favorable conditions')
        elif total < 5:
            recommendations.append('Limited data: Exercise caution')
        else:
            recommendations.append('Low confidence: Consider skipping')

        return {
            'date_local': date_local,
            'instrument': instrument,
            'data_available': True,
            'asia_travel': asia_travel,
            'similar_sessions': len(similar),
            'win_rate': win_rate,
            'recommendations': recommendations,
            'message': f'Found {len(similar)} similar sessions with {win_rate:.1f}% win rate'
        }


def main():
    """Demo usage"""
    memory = TradingMemory()

    print("\n" + "="*70)
    print("TRADING MEMORY - Demo")
    print("="*70 + "\n")

    # Store a demo trade
    print("[1] Storing a demo trade...")
    trade_id = memory.store_trade(
        date_local='2026-01-24',
        orb_time='0900',
        outcome='WIN',
        r_multiple=2.3,
        asia_travel=1.8,
        london_reversals=2,
        lesson_learned='Perfect setup - high Asia travel with clean break'
    )
    print(f"  ✅ Stored trade ID: {trade_id}\n")

    # Query recent trades
    print("[2] Querying recent trades...")
    trades = memory.query_trades(orb_time='0900', days_back=30, limit=5)
    print(f"  Found {len(trades)} trades\n")

    # Discover patterns
    print("[3] Discovering patterns...")
    patterns = memory.discover_patterns(min_confidence=0.6, min_sample_size=20)
    print(f"  Found {len(patterns)} patterns\n")
    for pattern in patterns:
        print(f"  Pattern: {pattern['pattern_id']}")
        print(f"    {pattern['description']}")
        print(f"    Confidence: {pattern['confidence']:.2f}")
        print(f"    Sample size: {pattern['sample_size']}")
        print(f"    Win rate: {pattern['win_rate']:.1f}%\n")

    print("="*70)
    print("Demo complete!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
