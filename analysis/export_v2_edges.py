"""
Export V2 Analysis Results - Zero Lookahead Edges
==================================================
Exports all honest V2 edge analysis to CSV, JSON, and Markdown formats.

Usage:
  python export_v2_edges.py
  python export_v2_edges.py --output-dir exports

Exports:
- Overall ORB performance by time
- ORB performance by direction
- PRE block filtered edges
- ORB correlation edges
- Best edges summary
"""

import duckdb
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass, asdict


@dataclass
class EdgeStats:
    """Statistics for a trading edge"""
    setup: str
    orb_time: str
    direction: str
    condition: str
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    avg_r: float
    total_r: float
    median_r: float
    best_r: float
    worst_r: float
    edge_type: str  # "baseline", "pre_block", "correlation"


class V2EdgeExporter:
    """Export V2 zero-lookahead edges"""

    def __init__(self, db_path: str = "gold.db"):
        self.con = duckdb.connect(db_path, read_only=True)
        self.edges = []

    def calculate_edge_stats(self, orb_time: str, condition: str, params: List) -> Dict:
        """Calculate comprehensive statistics for an edge"""
        query = f"""
            WITH trades AS (
                SELECT
                    orb_{orb_time}_outcome as outcome,
                    orb_{orb_time}_r_multiple as r_multiple
                FROM daily_features
                WHERE orb_{orb_time}_outcome IN ('WIN', 'LOSS')
                  AND {condition}
            )
            SELECT
                COUNT(*) as total_trades,
                SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
                AVG(r_multiple) as avg_r,
                SUM(r_multiple) as total_r,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY r_multiple) as median_r,
                MAX(r_multiple) as best_r,
                MIN(r_multiple) as worst_r
            FROM trades
        """

        result = self.con.execute(query, params).fetchone()

        if not result or result[0] == 0:
            return None

        total, wins, losses, avg_r, total_r, median_r, best_r, worst_r = result

        return {
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": wins / total if total else 0,
            "avg_r": avg_r or 0,
            "total_r": total_r or 0,
            "median_r": median_r or 0,
            "best_r": best_r or 0,
            "worst_r": worst_r or 0,
        }

    def export_baseline_edges(self):
        """Export baseline ORB performance (no filters)"""
        print("Exporting baseline edges...")

        for orb_time in ["0900", "1000", "1100", "1800", "2300", "0030"]:
            # Overall (any direction)
            stats = self.calculate_edge_stats(orb_time, "1=1", [])
            if stats and stats["total_trades"] >= 10:
                self.edges.append(EdgeStats(
                    setup=f"{orb_time} Overall",
                    orb_time=orb_time,
                    direction="ANY",
                    condition="No filter",
                    edge_type="baseline",
                    **stats
                ))

            # By direction
            for direction in ["UP", "DOWN"]:
                stats = self.calculate_edge_stats(
                    orb_time,
                    f"orb_{orb_time}_break_dir = ?",
                    [direction]
                )
                if stats and stats["total_trades"] >= 10:
                    self.edges.append(EdgeStats(
                        setup=f"{orb_time} {direction}",
                        orb_time=orb_time,
                        direction=direction,
                        condition="No filter",
                        edge_type="baseline",
                        **stats
                    ))

    def export_pre_block_edges(self):
        """Export PRE block filtered edges"""
        print("Exporting PRE block edges...")

        # 09:00 with PRE_ASIA filters
        for threshold in [30, 50]:
            for operator, op_str in [(">", "gt"), ("<", "lt")]:
                stats = self.calculate_edge_stats(
                    "0900",
                    f"(pre_asia_range / 0.1) {operator} ?",
                    [threshold]
                )
                if stats and stats["total_trades"] >= 10:
                    self.edges.append(EdgeStats(
                        setup=f"0900 PRE_ASIA {op_str} {threshold}t",
                        orb_time="0900",
                        direction="ANY",
                        condition=f"PRE_ASIA {operator} {threshold} ticks",
                        edge_type="pre_block",
                        **stats
                    ))

        # 11:00 UP with PRE_ASIA > 50 ticks
        stats = self.calculate_edge_stats(
            "1100",
            "orb_1100_break_dir = 'UP' AND (pre_asia_range / 0.1) > 50",
            []
        )
        if stats and stats["total_trades"] >= 10:
            self.edges.append(EdgeStats(
                setup="1100 UP PRE_ASIA > 50t",
                orb_time="1100",
                direction="UP",
                condition="PRE_ASIA > 50 ticks",
                edge_type="pre_block",
                **stats
            ))

        # 11:00 DOWN with PRE_ASIA > 50 ticks
        stats = self.calculate_edge_stats(
            "1100",
            "orb_1100_break_dir = 'DOWN' AND (pre_asia_range / 0.1) > 50",
            []
        )
        if stats and stats["total_trades"] >= 10:
            self.edges.append(EdgeStats(
                setup="1100 DOWN PRE_ASIA > 50t",
                orb_time="1100",
                direction="DOWN",
                condition="PRE_ASIA > 50 ticks",
                edge_type="pre_block",
                **stats
            ))

        # 18:00 with PRE_LONDON filters
        for direction in ["UP", "DOWN"]:
            stats = self.calculate_edge_stats(
                "1800",
                f"orb_1800_break_dir = ? AND (pre_london_range / 0.1) > 40",
                [direction]
            )
            if stats and stats["total_trades"] >= 10:
                self.edges.append(EdgeStats(
                    setup=f"1800 {direction} PRE_LONDON > 40t",
                    orb_time="1800",
                    direction=direction,
                    condition="PRE_LONDON > 40 ticks",
                    edge_type="pre_block",
                    **stats
                ))

        # 00:30 with PRE_NY filters
        for direction in ["UP", "DOWN"]:
            stats = self.calculate_edge_stats(
                "0030",
                f"orb_0030_break_dir = ? AND (pre_ny_range / 0.1) > 40",
                [direction]
            )
            if stats and stats["total_trades"] >= 10:
                self.edges.append(EdgeStats(
                    setup=f"0030 {direction} PRE_NY > 40t",
                    orb_time="0030",
                    direction=direction,
                    condition="PRE_NY > 40 ticks",
                    edge_type="pre_block",
                    **stats
                ))

    def export_correlation_edges(self):
        """Export ORB correlation edges"""
        print("Exporting ORB correlation edges...")

        # 10:00 after 09:00 outcome
        for prev_outcome in ["WIN", "LOSS"]:
            for direction in ["UP", "DOWN"]:
                stats = self.calculate_edge_stats(
                    "1000",
                    f"orb_1000_break_dir = ? AND orb_0900_outcome = ?",
                    [direction, prev_outcome]
                )
                if stats and stats["total_trades"] >= 10:
                    self.edges.append(EdgeStats(
                        setup=f"1000 {direction} after 0900 {prev_outcome}",
                        orb_time="1000",
                        direction=direction,
                        condition=f"After 09:00 {prev_outcome}",
                        edge_type="correlation",
                        **stats
                    ))

        # 11:00 after 09:00 + 10:00 outcomes
        for orb_09 in ["WIN", "LOSS"]:
            for orb_10 in ["WIN", "LOSS"]:
                for direction in ["UP", "DOWN"]:
                    stats = self.calculate_edge_stats(
                        "1100",
                        f"orb_1100_break_dir = ? AND orb_0900_outcome = ? AND orb_1000_outcome = ?",
                        [direction, orb_09, orb_10]
                    )
                    if stats and stats["total_trades"] >= 10:
                        self.edges.append(EdgeStats(
                            setup=f"1100 {direction} after 0900 {orb_09} + 1000 {orb_10}",
                            orb_time="1100",
                            direction=direction,
                            condition=f"After 09:00 {orb_09} + 10:00 {orb_10}",
                            edge_type="correlation",
                            **stats
                        ))

    def export_to_csv(self, output_dir: Path):
        """Export edges to CSV"""
        csv_path = output_dir / f"v2_edges_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'setup', 'orb_time', 'direction', 'condition', 'edge_type',
                'total_trades', 'wins', 'losses', 'win_rate', 'avg_r', 'total_r',
                'median_r', 'best_r', 'worst_r'
            ])
            writer.writeheader()

            for edge in self.edges:
                row = asdict(edge)
                row['win_rate'] = f"{row['win_rate']:.4f}"
                row['avg_r'] = f"{row['avg_r']:.4f}"
                row['total_r'] = f"{row['total_r']:.2f}"
                row['median_r'] = f"{row['median_r']:.4f}"
                row['best_r'] = f"{row['best_r']:.2f}"
                row['worst_r'] = f"{row['worst_r']:.2f}"
                writer.writerow(row)

        print(f"[OK] CSV exported: {csv_path}")
        return csv_path

    def export_to_json(self, output_dir: Path):
        """Export edges to JSON"""
        json_path = output_dir / f"v2_edges_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        export_data = {
            "metadata": {
                "export_date": datetime.now().isoformat(),
                "total_edges": len(self.edges),
                "database": "gold.db",
                "table": "daily_features",
                "method": "zero_lookahead_v2"
            },
            "edges": [asdict(edge) for edge in self.edges]
        }

        with open(json_path, 'w') as f:
            json.dump(export_data, f, indent=2)

        print(f"[OK] JSON exported: {json_path}")
        return json_path

    def export_to_markdown(self, output_dir: Path):
        """Export edges to Markdown summary"""
        md_path = output_dir / f"v2_edges_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        with open(md_path, 'w') as f:
            f.write("# V2 Edge Analysis - Zero Lookahead\n\n")
            f.write(f"**Export Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Total Edges:** {len(self.edges)}\n\n")
            f.write("**Method:** Zero Lookahead V2 (100% reproducible in live trading)\n\n")
            f.write("---\n\n")

            # Best edges (WR > 54%, Avg R > 0.10, N >= 20)
            best_edges = [
                e for e in self.edges
                if e.win_rate > 0.54 and e.avg_r > 0.10 and e.total_trades >= 20
            ]
            best_edges.sort(key=lambda x: x.avg_r, reverse=True)

            f.write("## Best Edges (WR > 54%, Avg R > 0.10, N >= 20)\n\n")
            f.write("| Setup | Trades | WR | Avg R | Total R | Type |\n")
            f.write("|-------|--------|----|----|---------|------|\n")

            for edge in best_edges:
                f.write(f"| {edge.setup} | {edge.total_trades} | {edge.win_rate:.1%} | "
                       f"{edge.avg_r:+.2f} | {edge.total_r:+.1f} | {edge.edge_type} |\n")

            if not best_edges:
                f.write("*No edges meet criteria*\n")

            f.write("\n---\n\n")

            # By category
            for edge_type in ["baseline", "pre_block", "correlation"]:
                category_edges = [e for e in self.edges if e.edge_type == edge_type]
                if not category_edges:
                    continue

                category_edges.sort(key=lambda x: x.avg_r, reverse=True)

                f.write(f"## {edge_type.replace('_', ' ').title()} Edges\n\n")
                f.write("| Setup | Trades | Win% | Avg R | Total R |\n")
                f.write("|-------|--------|------|-------|--------|\n")

                for edge in category_edges:
                    f.write(f"| {edge.setup} | {edge.total_trades} | {edge.win_rate:.1%} | "
                           f"{edge.avg_r:+.2f} | {edge.total_r:+.1f} |\n")

                f.write("\n")

        print(f"[OK] Markdown exported: {md_path}")
        return md_path

    def export_all(self, output_dir: str = "exports"):
        """Export all edges to all formats"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        print("\n" + "="*80)
        print("V2 EDGE EXPORT - ZERO LOOKAHEAD")
        print("="*80)

        # Collect all edges
        self.export_baseline_edges()
        self.export_pre_block_edges()
        self.export_correlation_edges()

        print(f"\nTotal edges collected: {len(self.edges)}")

        # Export to all formats
        csv_path = self.export_to_csv(output_path)
        json_path = self.export_to_json(output_path)
        md_path = self.export_to_markdown(output_path)

        print("\n" + "="*80)
        print("EXPORT COMPLETE")
        print("="*80)
        print(f"\nCSV:      {csv_path}")
        print(f"JSON:     {json_path}")
        print(f"Markdown: {md_path}")
        print("\n" + "="*80 + "\n")

    def close(self):
        self.con.close()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Export V2 zero-lookahead edges")
    parser.add_argument("--output-dir", default="exports", help="Output directory for exports")
    args = parser.parse_args()

    exporter = V2EdgeExporter()
    try:
        exporter.export_all(args.output_dir)
    finally:
        exporter.close()


if __name__ == "__main__":
    main()
