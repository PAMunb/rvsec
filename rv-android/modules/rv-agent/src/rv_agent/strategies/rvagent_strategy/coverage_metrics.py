"""
Coverage Metrics - Unified coverage tracking combining UI and MOP coverage.

Aggregates metrics from multiple sources:
- DynamicStateGraph (states, actions, transitions)
- UICoverageTracker (UI element interactions)
- Own MOP tracking (monitored operations reached)
"""

import logging
from typing import Dict, Any, Set

from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.memory.ui_coverage import UICoverageTracker


logger = logging.getLogger(__name__)


class CoverageMetrics:
    """
    Aggregates and reports comprehensive coverage metrics.

    This class does NOT duplicate data - it queries existing sources
    and adds MOP method tracking.

    Coverage Types:
    1. State Coverage: States discovered / total possible (graph-based)
    2. Action Coverage: Actions executed / total actions (graph-based)
    3. UI Element Coverage: Elements tested / total elements (UI tracker-based)
    4. MOP Coverage: Unique MOP methods reached (own tracking)
    """

    def __init__(
        self,
        graph: DynamicStateGraph,
        ui_coverage: UICoverageTracker
    ):
        """
        Initialize coverage metrics aggregator.

        Args:
            graph: DynamicStateGraph for state/action metrics
            ui_coverage: UICoverageTracker for UI element metrics
        """
        self.graph = graph
        self.ui_coverage = ui_coverage

        # Own tracking: MOP methods reached
        self.mop_methods_reached: Set[str] = set()

        logger.info("CoverageMetrics initialized")

    def record_mop_execution(self, callback_signature: str):
        """
        Record that a MOP method was executed.

        Args:
            callback_signature: Method signature (e.g., "javax.crypto.Cipher.init")
        """
        if callback_signature and callback_signature not in self.mop_methods_reached:
            self.mop_methods_reached.add(callback_signature)
            logger.info(f"New MOP method reached: {callback_signature}")

    def get_mop_count(self) -> int:
        """
        Get number of unique MOP methods reached.

        Returns:
            Count of unique MOP methods
        """
        return len(self.mop_methods_reached)

    def get_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive coverage summary from all sources.

        Returns:
            Dictionary with aggregated metrics
        """
        # Query DynamicStateGraph
        graph_coverage = self.graph.get_coverage_summary()

        # Query UICoverageTracker
        ui_stats = self.ui_coverage.get_overall_statistics()

        # Aggregate
        return {
            # State metrics (from graph)
            "states_discovered": len(self.graph.states),
            "graph_overall_coverage": graph_coverage.get("overall_coverage", 0.0),

            # Action metrics (from graph)
            "total_actions_executed": sum(
                len(node.executed_actions)
                for node in self.graph.states.values()
            ),

            # UI metrics (from UI tracker)
            "ui_elements_discovered": ui_stats.get("total_elements", 0),
            "ui_elements_tested": ui_stats.get("tested_elements", 0),
            "ui_coverage_rate": ui_stats.get("coverage_rate", 0.0),

            # MOP metrics (own tracking)
            "mop_methods_reached": len(self.mop_methods_reached),

            # Transition metrics (from graph)
            "total_transitions": len(self.graph.transitions),
        }

    def get_detailed_metrics(self) -> Dict[str, Any]:
        """
        Get detailed metrics including per-state breakdown.

        Returns:
            Dictionary with detailed metrics
        """
        summary = self.get_summary()

        # Add per-state details
        state_details = []
        for state_hash, node in self.graph.states.items():
            state_details.append({
                "hash": state_hash[:12],
                "activity": node.activity,
                "total_actions": node.total_actions,
                "executed_actions": len(node.executed_actions),
                "coverage": (
                    len(node.executed_actions) / node.total_actions
                    if node.total_actions > 0 else 1.0
                ),
                "visits": node.visit_count,
            })

        return {
            **summary,
            "state_details": state_details,
            "mop_methods_list": sorted(list(self.mop_methods_reached)),
        }

    def get_progress_report(self) -> str:
        """
        Get human-readable progress report.

        Returns:
            Formatted string with coverage report
        """
        metrics = self.get_summary()

        report = [
            "=== Coverage Report ===",
            f"States: {metrics['states_discovered']}",
            f"Graph Coverage: {metrics['graph_overall_coverage']:.1%}",
            f"Actions Executed: {metrics['total_actions_executed']}",
            f"UI Elements: {metrics['ui_elements_tested']}/{metrics['ui_elements_discovered']} "
            f"({metrics['ui_coverage_rate']:.1%})",
            f"MOP Methods: {metrics['mop_methods_reached']}",
            f"Transitions: {metrics['total_transitions']}",
            "=" * 24,
        ]

        return "\n".join(report)

    def reset_mop_tracking(self):
        """Reset MOP method tracking (keep graph/UI data intact)."""
        self.mop_methods_reached.clear()
        logger.info("MOP tracking reset")

    def __repr__(self) -> str:
        """String representation for debugging."""
        metrics = self.get_summary()
        return (
            f"CoverageMetrics(states={metrics['states_discovered']}, "
            f"mop={metrics['mop_methods_reached']}, "
            f"ui_coverage={metrics['ui_coverage_rate']:.1%})"
        )
