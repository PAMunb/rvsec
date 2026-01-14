"""
Analyzer for multimodal validation metrics.

Aggregates metrics across sessions and performs statistical analysis.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import statistics

from .metrics import SessionMetrics, HitClassification
from .collector import MultimodalMetricsCollector


logger = logging.getLogger(__name__)


@dataclass
class AggregatedMetrics:
    """Aggregated metrics across multiple sessions."""

    # Group info
    agent_mode: str = ""
    app_packages: List[str] = field(default_factory=list)
    num_sessions: int = 0

    # Hit rate
    hit_rate_mean: float = 0.0
    hit_rate_std: float = 0.0
    hit_rate_values: List[float] = field(default_factory=list)

    # Activity coverage
    coverage_mean: float = 0.0
    coverage_std: float = 0.0
    coverage_values: List[float] = field(default_factory=list)

    # Latency
    latency_mean: float = 0.0
    latency_std: float = 0.0
    latency_p50: float = 0.0
    latency_p95: float = 0.0
    latency_values: List[float] = field(default_factory=list)

    # Tokens
    tokens_per_action_mean: float = 0.0
    tokens_per_action_std: float = 0.0

    # Actions per activity
    actions_per_activity_mean: float = 0.0
    actions_per_activity_std: float = 0.0

    # Stuck recovery
    stuck_recovery_rate_mean: float = 0.0

    # Tool call rate
    tool_call_rate_mean: float = 0.0

    # Hit classification breakdown
    hits_total: int = 0
    near_misses_total: int = 0
    ui_misses_total: int = 0
    empty_misses_total: int = 0


class MultimodalAnalyzer:
    """
    Analyzes multimodal validation metrics.

    Aggregates results across sessions and compares different modes.
    """

    def __init__(self):
        """Initialize analyzer."""
        self.sessions: List[SessionMetrics] = []

    def add_session(self, session: SessionMetrics) -> None:
        """Add a session to analyze."""
        self.sessions.append(session)
        logger.debug(f"Added session: {session.app_package} ({session.agent_mode})")

    def load_sessions(self, metrics_dir: Path) -> int:
        """
        Load all session metrics from directory.

        Args:
            metrics_dir: Directory containing JSON metric files

        Returns:
            Number of sessions loaded
        """
        metrics_dir = Path(metrics_dir)
        count = 0

        for filepath in metrics_dir.glob("multimodal_metrics_*.json"):
            try:
                session = MultimodalMetricsCollector.load(filepath)
                self.sessions.append(session)
                count += 1
            except Exception as e:
                logger.warning(f"Failed to load {filepath}: {e}")

        logger.info(f"Loaded {count} sessions from {metrics_dir}")
        return count

    def aggregate_by_mode(self) -> Dict[str, AggregatedMetrics]:
        """
        Aggregate metrics grouped by agent mode.

        Returns:
            Dictionary mapping mode to aggregated metrics
        """
        # Group sessions by mode
        by_mode: Dict[str, List[SessionMetrics]] = {}
        for session in self.sessions:
            mode = session.agent_mode
            if mode not in by_mode:
                by_mode[mode] = []
            by_mode[mode].append(session)

        # Aggregate each group
        results = {}
        for mode, sessions in by_mode.items():
            results[mode] = self._aggregate_sessions(sessions, mode)

        return results

    def aggregate_by_app(self) -> Dict[str, AggregatedMetrics]:
        """
        Aggregate metrics grouped by app package.

        Returns:
            Dictionary mapping app to aggregated metrics
        """
        by_app: Dict[str, List[SessionMetrics]] = {}
        for session in self.sessions:
            app = session.app_package
            if app not in by_app:
                by_app[app] = []
            by_app[app].append(session)

        results = {}
        for app, sessions in by_app.items():
            results[app] = self._aggregate_sessions(sessions, app)

        return results

    def _aggregate_sessions(
        self, sessions: List[SessionMetrics], group_name: str
    ) -> AggregatedMetrics:
        """Aggregate a list of sessions into summary metrics."""
        if not sessions:
            return AggregatedMetrics()

        agg = AggregatedMetrics(
            agent_mode=group_name,
            app_packages=list(set(s.app_package for s in sessions)),
            num_sessions=len(sessions),
        )

        # Collect values
        hit_rates = [s.hit_rate for s in sessions]
        coverages = [s.activity_coverage for s in sessions]
        latencies = [s.avg_latency_ms for s in sessions if s.avg_latency_ms > 0]
        tokens_per_action = [s.tokens_per_action for s in sessions if s.tokens_per_action > 0]
        actions_per_activity = [
            s.actions_per_activity for s in sessions
            if s.actions_per_activity < float('inf')
        ]
        stuck_recovery = [s.stuck_recovery_rate for s in sessions]
        tool_call_rates = [s.tool_call_rate for s in sessions]

        # Hit rate
        agg.hit_rate_values = hit_rates
        if hit_rates:
            agg.hit_rate_mean = statistics.mean(hit_rates)
            agg.hit_rate_std = statistics.stdev(hit_rates) if len(hit_rates) > 1 else 0.0

        # Coverage
        agg.coverage_values = coverages
        if coverages:
            agg.coverage_mean = statistics.mean(coverages)
            agg.coverage_std = statistics.stdev(coverages) if len(coverages) > 1 else 0.0

        # Latency
        agg.latency_values = latencies
        if latencies:
            agg.latency_mean = statistics.mean(latencies)
            agg.latency_std = statistics.stdev(latencies) if len(latencies) > 1 else 0.0
            sorted_latencies = sorted(latencies)
            agg.latency_p50 = sorted_latencies[len(sorted_latencies) // 2]
            agg.latency_p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)]

        # Tokens per action
        if tokens_per_action:
            agg.tokens_per_action_mean = statistics.mean(tokens_per_action)
            agg.tokens_per_action_std = (
                statistics.stdev(tokens_per_action) if len(tokens_per_action) > 1 else 0.0
            )

        # Actions per activity
        if actions_per_activity:
            agg.actions_per_activity_mean = statistics.mean(actions_per_activity)
            agg.actions_per_activity_std = (
                statistics.stdev(actions_per_activity) if len(actions_per_activity) > 1 else 0.0
            )

        # Stuck recovery
        if stuck_recovery:
            agg.stuck_recovery_rate_mean = statistics.mean(stuck_recovery)

        # Tool call rate
        if tool_call_rates:
            agg.tool_call_rate_mean = statistics.mean(tool_call_rates)

        # Hit classification totals
        agg.hits_total = sum(s.hits for s in sessions)
        agg.near_misses_total = sum(s.near_misses for s in sessions)
        agg.ui_misses_total = sum(s.ui_misses for s in sessions)
        agg.empty_misses_total = sum(s.empty_misses for s in sessions)

        return agg

    def compare_modes(
        self, mode_a: str, mode_b: str
    ) -> Dict[str, Any]:
        """
        Compare two modes statistically.

        Args:
            mode_a: First mode to compare
            mode_b: Second mode to compare

        Returns:
            Dictionary with comparison results
        """
        aggregated = self.aggregate_by_mode()

        if mode_a not in aggregated or mode_b not in aggregated:
            return {"error": f"Mode not found: {mode_a} or {mode_b}"}

        agg_a = aggregated[mode_a]
        agg_b = aggregated[mode_b]

        # Calculate effect sizes (Cliff's Delta approximation)
        def cliff_delta(values_a: List[float], values_b: List[float]) -> float:
            """Calculate Cliff's Delta effect size."""
            if not values_a or not values_b:
                return 0.0

            n_greater = 0
            n_less = 0
            for a in values_a:
                for b in values_b:
                    if a > b:
                        n_greater += 1
                    elif a < b:
                        n_less += 1

            n_total = len(values_a) * len(values_b)
            if n_total == 0:
                return 0.0

            return (n_greater - n_less) / n_total

        def interpret_cliff_delta(d: float) -> str:
            """Interpret Cliff's Delta magnitude."""
            abs_d = abs(d)
            if abs_d < 0.147:
                return "negligible"
            elif abs_d < 0.33:
                return "small"
            elif abs_d < 0.474:
                return "medium"
            else:
                return "large"

        # Compare hit rates
        hit_rate_delta = cliff_delta(agg_a.hit_rate_values, agg_b.hit_rate_values)

        # Compare coverage
        coverage_delta = cliff_delta(agg_a.coverage_values, agg_b.coverage_values)

        # Compare latency (negative is better for mode_a)
        latency_delta = cliff_delta(agg_b.latency_values, agg_a.latency_values)

        return {
            "mode_a": mode_a,
            "mode_b": mode_b,
            "samples_a": agg_a.num_sessions,
            "samples_b": agg_b.num_sessions,
            "hit_rate": {
                "mean_a": agg_a.hit_rate_mean,
                "mean_b": agg_b.hit_rate_mean,
                "cliff_delta": hit_rate_delta,
                "effect_size": interpret_cliff_delta(hit_rate_delta),
                "winner": mode_a if hit_rate_delta > 0 else mode_b,
            },
            "coverage": {
                "mean_a": agg_a.coverage_mean,
                "mean_b": agg_b.coverage_mean,
                "cliff_delta": coverage_delta,
                "effect_size": interpret_cliff_delta(coverage_delta),
                "winner": mode_a if coverage_delta > 0 else mode_b,
            },
            "latency": {
                "mean_a": agg_a.latency_mean,
                "mean_b": agg_b.latency_mean,
                "cliff_delta": latency_delta,
                "effect_size": interpret_cliff_delta(latency_delta),
                "winner": mode_a if latency_delta > 0 else mode_b,
            },
        }

    def generate_report(self, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Generate comprehensive analysis report.

        Args:
            output_path: Optional path to save report JSON

        Returns:
            Report dictionary
        """
        by_mode = self.aggregate_by_mode()
        by_app = self.aggregate_by_app()

        report = {
            "summary": {
                "total_sessions": len(self.sessions),
                "modes": list(by_mode.keys()),
                "apps": list(by_app.keys()),
            },
            "by_mode": {
                mode: {
                    "num_sessions": agg.num_sessions,
                    "hit_rate": {
                        "mean": agg.hit_rate_mean,
                        "std": agg.hit_rate_std,
                    },
                    "coverage": {
                        "mean": agg.coverage_mean,
                        "std": agg.coverage_std,
                    },
                    "latency": {
                        "mean": agg.latency_mean,
                        "p50": agg.latency_p50,
                        "p95": agg.latency_p95,
                    },
                    "tokens_per_action": agg.tokens_per_action_mean,
                    "actions_per_activity": agg.actions_per_activity_mean,
                    "stuck_recovery_rate": agg.stuck_recovery_rate_mean,
                    "hit_breakdown": {
                        "hits": agg.hits_total,
                        "near_misses": agg.near_misses_total,
                        "ui_misses": agg.ui_misses_total,
                        "empty_misses": agg.empty_misses_total,
                    },
                }
                for mode, agg in by_mode.items()
            },
            "by_app": {
                app: {
                    "num_sessions": agg.num_sessions,
                    "hit_rate_mean": agg.hit_rate_mean,
                    "coverage_mean": agg.coverage_mean,
                }
                for app, agg in by_app.items()
            },
        }

        # Add mode comparisons if multiple modes
        modes = list(by_mode.keys())
        if len(modes) >= 2:
            comparisons = []
            for i, mode_a in enumerate(modes):
                for mode_b in modes[i + 1:]:
                    comparison = self.compare_modes(mode_a, mode_b)
                    comparisons.append(comparison)
            report["comparisons"] = comparisons

        if output_path:
            output_path = Path(output_path)
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2)
            logger.info(f"Report saved to {output_path}")

        return report

    def print_summary(self) -> None:
        """Print summary to console."""
        by_mode = self.aggregate_by_mode()

        print("\n" + "=" * 60)
        print("MULTIMODAL VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Total sessions: {len(self.sessions)}")
        print()

        for mode, agg in by_mode.items():
            print(f"\n--- {mode.upper()} ({agg.num_sessions} sessions) ---")
            print(f"  Hit Rate:     {agg.hit_rate_mean:.1%} ± {agg.hit_rate_std:.1%}")
            print(f"  Coverage:     {agg.coverage_mean:.1%} ± {agg.coverage_std:.1%}")
            print(f"  Latency:      {agg.latency_mean:.0f}ms (p50={agg.latency_p50:.0f}, p95={agg.latency_p95:.0f})")
            print(f"  Tokens/Action: {agg.tokens_per_action_mean:.0f}")
            print(f"  Actions/Activity: {agg.actions_per_activity_mean:.1f}")
            print(f"  Stuck Recovery: {agg.stuck_recovery_rate_mean:.1%}")
            print(f"  Hit Breakdown: {agg.hits_total} hits, {agg.near_misses_total} near, "
                  f"{agg.ui_misses_total} UI, {agg.empty_misses_total} empty")

        print("\n" + "=" * 60)
