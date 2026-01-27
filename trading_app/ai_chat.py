"""
AI Trading Assistant - Chat Interface with Memory

Provides intelligent trading insights using:
1. Trade history (episodic memory)
2. Learned patterns (semantic memory)
3. Current session context (working memory)
4. Edge health monitoring

Usage:
    from trading_app.ai_chat import TradingAssistant

    assistant = TradingAssistant()

    # Ask questions
    response = assistant.ask("How did 0900 ORB perform last 30 days?")
    response = assistant.ask("Find sessions similar to today")
    response = assistant.ask("What patterns have I learned?")
"""

from datetime import date, datetime
from typing import Dict, Optional

from trading_app.memory import TradingMemory
from trading_app.edge_tracker import EdgeTracker
from trading_app.market_scanner import MarketScanner
from trading_app.config import TZ_LOCAL


class TradingAssistant:
    """AI trading assistant with contextual memory"""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize trading assistant.

        Args:
            db_path: Optional database path (for testing)
        """
        self.db_path = db_path
        self.memory = TradingMemory(db_path=db_path) if db_path else TradingMemory()
        self.edge_tracker = EdgeTracker(db_path=db_path) if db_path else EdgeTracker()
        self.scanner = MarketScanner(db_path=db_path) if db_path else MarketScanner()
        self.tz_local = TZ_LOCAL

    def get_performance_summary(self, orb_time: str, days_back: int = 30) -> str:
        """Get performance summary for a specific ORB"""
        perf = self.memory.get_recent_performance(orb_time, days_back=days_back)

        if perf['total_trades'] == 0:
            return f"No trades recorded for {orb_time} ORB in last {days_back} days."

        response = f"""
**{orb_time} ORB Performance (Last {days_back} Days)**

Total Trades: {perf['total_trades']}
Wins: {perf['wins']} | Losses: {perf['losses']}
Win Rate: {perf['win_rate']:.1f}%
Avg R-Multiple: {perf['avg_r']:.2f}
Total R: {perf['total_r']:+.1f}R
Last Trade: {perf['last_trade_date']}
"""
        return response.strip()

    def get_edge_health_summary(self, orb_time: str) -> str:
        """Get edge health analysis"""
        health = self.edge_tracker.check_edge_health(orb_time)

        if not health['has_baseline']:
            return f"No baseline data found for {orb_time} ORB."

        status_emoji = {
            'EXCELLENT': '[++]',
            'HEALTHY': '[OK]',
            'WATCH': '[!]',
            'DEGRADED': '[X]',
            'INSUFFICIENT_DATA': '[...]'
        }

        emoji = status_emoji.get(health['status'], '[?]')

        response = f"""
**{emoji} {orb_time} ORB Edge Health: {health['status']}**

Baseline Performance:
- Win Rate: {health['baseline']['win_rate']:.1f}%
- Expected R: {health['baseline']['expected_r']:.2f}

Recent Performance (30 days):
"""

        if health['performance']['30d']['has_data']:
            perf = health['performance']['30d']
            changes = health['changes']
            response += f"""- Win Rate: {perf['win_rate']:.1f}% ({changes['wr_30d']:+.1f}% change)
- Avg R: {perf['avg_r']:.2f} ({changes['er_30d']:+.1f}% change)
- Trades: {perf['total_trades']}

Recommendations:
"""
            for rec in health['recommendations']:
                response += f"- {rec}\n"
        else:
            response += "- Insufficient recent data\n"

        return response.strip()

    def get_system_health_summary(self) -> str:
        """Get system-wide edge health"""
        status = self.edge_tracker.get_system_status()

        if status['status'] == 'NO_DATA':
            return "No edge data available in system."

        status_emoji = {
            'EXCELLENT': '[++]',
            'HEALTHY': '[OK]',
            'CAUTION': '[!]',
            'DEGRADED': '[X]'
        }

        emoji = status_emoji.get(status['status'], '[?]')

        response = f"""
**{emoji} System Health: {status['status']}**

{status['message']}

Total Edges: {status['total_edges']}
- Excellent: {len(status['excellent'])}
- Healthy: {len(status['healthy'])}
- Watch: {len(status['watch'])}
- Degraded: {len(status['degraded'])}
"""

        if status['degraded']:
            response += f"\n[!] DEGRADED EDGES: {', '.join(status['degraded'])}"

        if status['excellent']:
            response += f"\n[*] BEST PERFORMERS: {', '.join(status['excellent'])}"

        return response.strip()

    def get_regime_summary(self) -> str:
        """Get current market regime"""
        regime = self.edge_tracker.detect_regime()

        regime_emoji = {
            'TRENDING': '[^]',
            'RANGE_BOUND': '[=]',
            'VOLATILE': '[*]',
            'QUIET': '[-]',
            'UNKNOWN': '[?]'
        }

        emoji = regime_emoji.get(regime['regime'], '[?]')

        response = f"""
**{emoji} Market Regime: {regime['regime']}**

Confidence: {regime['confidence']:.0%}

{regime['message']}
"""

        if 'metrics' in regime:
            metrics = regime['metrics']
            response += f"""
Recent Metrics:
- Avg Asia Travel: {metrics['avg_asia_travel']:.2f} pts
- Avg London Range: {metrics['avg_london_range']:.2f} pts
- Avg NY Range: {metrics['avg_ny_range']:.2f} pts
"""

        return response.strip()

    def get_learned_patterns_summary(self) -> str:
        """Get learned patterns from memory"""
        patterns = self.memory.query_patterns(min_confidence=0.6)

        if not patterns:
            return "No learned patterns found. Run pattern discovery to learn from historical trades."

        response = "**Learned Trading Patterns:**\n\n"

        for i, pattern in enumerate(patterns[:5], 1):  # Top 5 patterns
            response += f"{i}. **{pattern['pattern_id']}**\n"
            response += f"   {pattern['description']}\n"
            response += f"   Confidence: {pattern['confidence']:.0%} | "
            response += f"Sample: {pattern['sample_size']} trades | "
            response += f"WR: {pattern['win_rate']:.1f}%\n"
            if pattern['hypothesis']:
                response += f"   Hypothesis: {pattern['hypothesis']}\n"
            response += "\n"

        return response.strip()

    def analyze_today(self) -> str:
        """Analyze today's market conditions"""
        # Get market scanner results
        scan_results = self.scanner.scan_all_setups()

        response = f"""
**Today's Analysis - {scan_results['date_local']}**

Valid Setups: {scan_results['valid_count']}
Caution Setups: {scan_results['caution_count']}
Invalid Setups: {scan_results['invalid_count']}

Summary: {scan_results['summary']}
"""

        # Add regime context
        regime = self.edge_tracker.detect_regime()
        response += f"\n\nMarket Regime: {regime['regime']} ({regime['confidence']:.0%} confidence)"
        response += f"\n{regime['message']}"

        return response.strip()

    def ask(self, question: str) -> str:
        """
        Process natural language questions.

        Supported questions:
        - "How did [ORB] perform recently?"
        - "Edge health for [ORB]"
        - "System health"
        - "Market regime"
        - "Learned patterns"
        - "Analyze today"
        """
        q = question.lower()

        # Performance queries
        if "perform" in q or "performance" in q:
            for orb in ['0900', '1000', '1100', '1800', '2300', '0030']:
                if orb in q:
                    return self.get_performance_summary(orb)
            return "Please specify which ORB (e.g., '0900 ORB performance')"

        # Edge health queries
        if "edge" in q or "health" in q:
            if "system" in q or "all" in q:
                return self.get_system_health_summary()
            for orb in ['0900', '1000', '1100', '1800', '2300', '0030']:
                if orb in q:
                    return self.get_edge_health_summary(orb)
            return self.get_system_health_summary()

        # Regime queries
        if "regime" in q or "market condition" in q:
            return self.get_regime_summary()

        # Pattern queries
        if "pattern" in q or "learned" in q:
            return self.get_learned_patterns_summary()

        # Today's analysis
        if "today" in q or "current" in q or "analyze" in q:
            return self.analyze_today()

        # Default - show help
        return """
**AI Trading Assistant - Available Commands:**

- "How did 0900 ORB perform recently?"
- "Edge health for 1100 ORB"
- "System health"
- "Market regime"
- "Learned patterns"
- "Analyze today"

Ask me anything about your trading performance, edge health, or market conditions!
"""


def main():
    """Demo usage"""
    assistant = TradingAssistant()

    print("\n" + "="*70)
    print("AI TRADING ASSISTANT - Demo")
    print("="*70 + "\n")

    # Demo questions
    questions = [
        "System health",
        "Market regime",
        "Analyze today"
    ]

    for q in questions:
        print(f"Q: {q}\n")
        response = assistant.ask(q)
        print(response)
        print("\n" + "-"*70 + "\n")

    print("="*70)
    print("Demo complete!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
