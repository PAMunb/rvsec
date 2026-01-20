"""
Calibration metrics collector for scorer priority analysis.

Extracts metrics from agent execution to analyze and calibrate
action scoring weights for optimal exploration coverage.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class RunMetrics:
    """Metrics from a single run."""
    run_id: str
    package_name: str
    seed: int

    # State metrics
    states_discovered: int = 0
    total_transitions: int = 0

    # Action metrics
    total_actions: int = 0
    mop_actions: int = 0
    dm_actions: int = 0  # Directly reaches MOP

    # Coverage metrics
    ui_coverage_percent: float = 0.0
    element_coverage_percent: float = 0.0

    # Per-screen metrics
    screens: List[Dict[str, Any]] = field(default_factory=list)

    # Execution time
    execution_time_seconds: float = 0.0


class CalibrationMetricsCollector:
    """
    Collects metrics from agent execution for calibration analysis.

    Usage:
        collector = CalibrationMetricsCollector()

        # After each run
        metrics = collector.extract_metrics(agent, run_config, execution_time)

        # After all runs
        report = collector.get_calibration_report()
    """

    def __init__(self):
        self.runs: List[RunMetrics] = []
        self.aggregated: Dict[str, Any] = {}

    def extract_metrics(
        self,
        agent,
        run_id: str,
        package_name: str,
        seed: int,
        execution_time: float
    ) -> RunMetrics:
        """
        Extract calibration metrics from an executed agent.

        Args:
            agent: Executed RVAgent instance
            run_id: Unique run identifier
            package_name: App package name
            seed: Random seed used
            execution_time: Execution time in seconds

        Returns:
            RunMetrics with extracted data
        """
        metrics = RunMetrics(
            run_id=run_id,
            package_name=package_name,
            seed=seed,
            execution_time_seconds=execution_time
        )

        try:
            # Extract from dynamic graph
            graph = agent.dynamic_graph
            if graph:
                graph_report = graph.get_transition_graph_report()
                metrics.states_discovered = graph_report.get("total_states", 0)
                metrics.total_transitions = graph_report.get("total_transitions", 0)

                # Extract per-screen metrics
                for state_hash, state in graph.states.items():
                    screen_metrics = {
                        "hash": state_hash[:8],
                        "activity": state.activity,
                        "total_actions": state.total_actions,
                        "executed_actions": len(state.executed_actions),
                        "visit_count": state.visit_count,
                    }

                    # Calculate screen coverage
                    if state.total_actions > 0:
                        screen_metrics["coverage_percent"] = (
                            len(state.executed_actions) / state.total_actions * 100
                        )
                    else:
                        screen_metrics["coverage_percent"] = 0.0

                    metrics.screens.append(screen_metrics)

            # Extract UI coverage from memory coordinator (same source as runner)
            memory = getattr(agent, 'memory_coordinator', None)
            if memory and memory.ui_coverage:
                try:
                    ui_stats = memory.ui_coverage.get_comprehensive_metrics()
                    metrics.ui_coverage_percent = ui_stats.get("element_coverage", 0.0)
                    metrics.element_coverage_percent = ui_stats.get("element_coverage", 0.0)
                except Exception:
                    pass

            # Get total actions from graph states
            if graph:
                metrics.total_actions = sum(
                    len(state.executed_actions) for state in graph.states.values()
                )

            self.runs.append(metrics)

            # Log summary
            logger.warning(
                f"[METRICS] run={run_id} states={metrics.states_discovered} "
                f"actions={metrics.total_actions} ui_cov={metrics.ui_coverage_percent:.1f}% "
                f"elem_cov={metrics.element_coverage_percent:.1f}%"
            )

            # Log per-screen coverage
            low_coverage_screens = [s for s in metrics.screens if s["coverage_percent"] < 60]
            if low_coverage_screens:
                logger.warning(
                    f"[METRICS] low_coverage_screens={len(low_coverage_screens)} "
                    f"(screens with <60% action coverage)"
                )

        except Exception as e:
            logger.error(f"Failed to extract calibration metrics: {e}", exc_info=True)

        return metrics

    def aggregate(self) -> Dict[str, Any]:
        """
        Aggregate metrics across all runs.

        Returns:
            Dictionary with aggregated statistics
        """
        if not self.runs:
            return {}

        # Aggregate by package
        by_package: Dict[str, List[RunMetrics]] = defaultdict(list)
        for run in self.runs:
            by_package[run.package_name].append(run)

        # Calculate aggregates
        total_states = sum(r.states_discovered for r in self.runs)
        total_actions = sum(r.total_actions for r in self.runs)
        avg_ui_coverage = sum(r.ui_coverage_percent for r in self.runs) / len(self.runs)
        avg_elem_coverage = sum(r.element_coverage_percent for r in self.runs) / len(self.runs)

        # Calculate screen coverage distribution
        all_screens = []
        for run in self.runs:
            all_screens.extend(run.screens)

        coverage_distribution = {
            "0-20%": 0,
            "20-40%": 0,
            "40-60%": 0,
            "60-80%": 0,
            "80-100%": 0,
        }

        for screen in all_screens:
            cov = screen["coverage_percent"]
            if cov < 20:
                coverage_distribution["0-20%"] += 1
            elif cov < 40:
                coverage_distribution["20-40%"] += 1
            elif cov < 60:
                coverage_distribution["40-60%"] += 1
            elif cov < 80:
                coverage_distribution["60-80%"] += 1
            else:
                coverage_distribution["80-100%"] += 1

        self.aggregated = {
            "total_runs": len(self.runs),
            "total_states": total_states,
            "total_actions": total_actions,
            "avg_states_per_run": total_states / len(self.runs),
            "avg_actions_per_run": total_actions / len(self.runs),
            "avg_ui_coverage_percent": avg_ui_coverage,
            "avg_element_coverage_percent": avg_elem_coverage,
            "total_screens": len(all_screens),
            "screen_coverage_distribution": coverage_distribution,
            "packages": {
                pkg: {
                    "runs": len(runs),
                    "avg_states": sum(r.states_discovered for r in runs) / len(runs),
                    "avg_ui_coverage": sum(r.ui_coverage_percent for r in runs) / len(runs),
                }
                for pkg, runs in by_package.items()
            },
        }

        return self.aggregated

    def get_calibration_report(self) -> str:
        """
        Generate human-readable metrics report.

        Returns:
            Formatted report string
        """
        agg = self.aggregate()
        if not agg:
            return "No runs collected."

        lines = [
            "=" * 60,
            "EXPERIMENT METRICS REPORT",
            "=" * 60,
            "",
            f"Total runs: {agg['total_runs']}",
            f"Total states discovered: {agg['total_states']}",
            f"Total actions executed: {agg['total_actions']}",
            f"Avg states per run: {agg['avg_states_per_run']:.1f}",
            f"Avg actions per run: {agg['avg_actions_per_run']:.1f}",
            "",
            f"Avg UI coverage: {agg['avg_ui_coverage_percent']:.1f}%",
            f"Avg element coverage: {agg['avg_element_coverage_percent']:.1f}%",
            "",
            "-" * 40,
            "SCREEN COVERAGE DISTRIBUTION",
            "-" * 40,
        ]

        for bucket, count in agg["screen_coverage_distribution"].items():
            pct = count / agg["total_screens"] * 100 if agg["total_screens"] > 0 else 0
            lines.append(f"  {bucket}: {count} screens ({pct:.1f}%)")

        lines.extend([
            "",
            "-" * 40,
            "ANALYSIS",
            "-" * 40,
        ])

        # Identify issues
        issues = []

        if agg["avg_element_coverage_percent"] < 50:
            issues.append(
                f"  - Low element coverage ({agg['avg_element_coverage_percent']:.1f}%) - "
                "consider increasing UntestedScorer weight"
            )

        low_cov_screens = (
            agg["screen_coverage_distribution"]["0-20%"] +
            agg["screen_coverage_distribution"]["20-40%"]
        )
        if low_cov_screens > agg["total_screens"] * 0.3:
            issues.append(
                f"  - {low_cov_screens} screens with <40% coverage - "
                "elements may be filtered incorrectly or transitions happen too fast"
            )

        if issues:
            lines.extend(issues)
        else:
            lines.append("  No major issues detected.")

        lines.extend([
            "",
            "=" * 60,
        ])

        return "\n".join(lines)

    def save_report(self, path: str) -> None:
        """Save calibration report to file."""
        report = self.get_calibration_report()
        with open(path, 'w') as f:
            f.write(report)
        logger.info(f"Calibration report saved to {path}")
