"""
Metrics collector for multimodal validation.

Collects LLM action and exploration metrics during agent execution.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .hit_classifier import HitClassifier, parse_ui_elements_from_dump
from .metrics import (
    ElementBounds,
    ExplorationRecord,
    HitClassification,
    LLMActionRecord,
    SessionMetrics,
)

logger = logging.getLogger(__name__)


class MultimodalMetricsCollector:
    """
    Collects metrics during rv-agent multimodal execution.

    Records LLM actions, exploration progress, and calculates hit rates.
    """

    def __init__(
        self,
        app_package: str,
        agent_mode: str,
        timeout_seconds: int = 300,
        seed: int = 0,
        total_activities: int = 0,
        output_dir: Optional[Path] = None,
        strategy: str = "rvagent",
    ):
        """
        Initialize collector.

        Args:
            app_package: Package name of app being tested
            agent_mode: Agent mode (pure_algorithm, llm_only, multimode)
            timeout_seconds: Experiment timeout
            seed: Random seed used
            total_activities: Total activities from static analysis
            output_dir: Directory for saving metrics (optional)
            strategy: Exploration strategy (dfs, bfs, greedy, rvagent)
        """
        self.session = SessionMetrics(
            app_package=app_package,
            agent_mode=agent_mode,
            strategy=strategy,
            timeout_seconds=timeout_seconds,
            seed=seed,
            total_activities=total_activities,
        )

        self.output_dir = output_dir
        self.hit_classifier = HitClassifier()

        # Tracking state
        self._discovered_activities: set = set()
        self._last_screen_hash: str = ""
        self._stuck_counter: int = 0
        self._actions_since_new_activity: int = 0

        # UI element tracking
        self._element_interactions: Dict[str, int] = {}  # element_id -> count
        self._elements_by_screen: Dict[str, set] = (
            {}
        )  # screen_hash -> set of element_ids
        self._component_types: Dict[str, str] = {}  # element_id -> component_type

        logger.info(
            f"MultimodalMetricsCollector initialized: "
            f"app={app_package}, mode={agent_mode}, strategy={strategy}"
        )

    def record_llm_action(
        self,
        iteration: int,
        raw_coords: Tuple[int, int],
        device_coords: Tuple[int, int],
        tool_name: str,
        tool_args: Dict[str, Any],
        latency_ms: float,
        tokens_input: int,
        tokens_output: int,
        parser_strategy: str,
        activity: str,
        screen_hash: str,
        ui_dump: Optional[str] = None,
        target_element_bounds: Optional[Tuple[int, int, int, int]] = None,
    ) -> LLMActionRecord:
        """
        Record an LLM-generated action.

        Args:
            iteration: Current iteration number
            raw_coords: Raw coordinates from LLM [0, 1000)
            device_coords: Converted device pixel coordinates
            tool_name: Tool called (android_click, etc.)
            tool_args: Tool arguments
            latency_ms: LLM response latency
            tokens_input: Input tokens consumed
            tokens_output: Output tokens generated
            parser_strategy: Parser strategy used (native, xml, fallback)
            activity: Current activity name
            screen_hash: Hash of current screen state
            ui_dump: Optional UIAutomator XML dump for hit classification
            target_element_bounds: Optional target element (left, top, right, bottom)

        Returns:
            LLMActionRecord with classification
        """
        # Parse target element if provided
        target_element = None
        if target_element_bounds:
            target_element = ElementBounds(*target_element_bounds)

        # Classify hit if this is a click action and we have UI dump
        hit_classification = HitClassification.EMPTY_MISS
        distance_to_target = 0.0
        distance_to_nearest = 0.0
        hit_element_type = ""

        # Accept both formats: "android_click" and "CLICK"
        click_actions = (
            "android_click",
            "android_long_click",
            "android_type_text",
            "CLICK",
            "LONG_CLICK",
            "TYPE",
            "SET_TEXT",
        )
        if tool_name in click_actions:
            if ui_dump:
                ui_elements = parse_ui_elements_from_dump(ui_dump)
                result = self.hit_classifier.classify(
                    device_coords[0],
                    device_coords[1],
                    target_element,
                    ui_elements,
                )
                hit_classification = result.classification
                distance_to_target = result.distance_to_target
                distance_to_nearest = result.distance_to_nearest
                if result.hit_element:
                    hit_element_type = result.hit_element.element_type

        # Create record
        record = LLMActionRecord(
            iteration=iteration,
            raw_coords=raw_coords,
            device_coords=device_coords,
            target_element=target_element,
            hit_classification=hit_classification,
            distance_to_target=distance_to_target,
            distance_to_nearest=distance_to_nearest,
            hit_element_type=hit_element_type,
            latency_ms=latency_ms,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            tool_name=tool_name,
            tool_args=tool_args,
            parser_strategy=parser_strategy,
            activity=activity,
            screen_hash=screen_hash,
        )

        # Update session metrics
        self.session.llm_actions.append(record)
        self.session.total_llm_calls += 1
        self.session.total_tokens_input += tokens_input
        self.session.total_tokens_output += tokens_output
        self.session.total_latency_ms += latency_ms

        # Update hit counts for click actions
        if tool_name in click_actions:
            self.session.total_clicks += 1
            if hit_classification == HitClassification.HIT:
                self.session.hits += 1
            elif hit_classification == HitClassification.NEAR_MISS:
                self.session.near_misses += 1
            elif hit_classification == HitClassification.UI_MISS:
                self.session.ui_misses += 1
            else:
                self.session.empty_misses += 1

        # Track UI element metrics
        if hit_element_type and tool_name in click_actions:
            element_id = f"{device_coords[0]}:{device_coords[1]}"
            self._element_interactions[element_id] = (
                self._element_interactions.get(element_id, 0) + 1
            )
            self._component_types[element_id] = hit_element_type

            if screen_hash:
                if screen_hash not in self._elements_by_screen:
                    self._elements_by_screen[screen_hash] = set()
                self._elements_by_screen[screen_hash].add(element_id)

        logger.info(
            f"Recorded LLM action: {tool_name} at {device_coords} -> "
            f"{hit_classification.value}"
            f"{f' (element: {hit_element_type})' if hit_element_type else ''}"
        )

        return record

    def record_exploration(
        self,
        iteration: int,
        activity: str,
        screen_hash: str,
        action_type: str,
        action_source: str,
    ) -> ExplorationRecord:
        """
        Record exploration progress.

        Args:
            iteration: Current iteration number
            activity: Current activity name
            screen_hash: Hash of current screen state
            action_type: Type of action (CLICK, BACK, etc.)
            action_source: Source of action (llm, algorithm)

        Returns:
            ExplorationRecord
        """
        # Check if new activity
        is_new_activity = activity not in self._discovered_activities
        if is_new_activity:
            self._discovered_activities.add(activity)
            self._actions_since_new_activity = 0
        else:
            self._actions_since_new_activity += 1

        # Check stuck state
        is_stuck = screen_hash == self._last_screen_hash
        if is_stuck:
            self._stuck_counter += 1
        else:
            # Check if we recovered from stuck
            if self._stuck_counter >= 3:
                self.session.stuck_recovered += 1
            self._stuck_counter = 0

        # Detect stuck event (3+ consecutive same states)
        stuck_detected = self._stuck_counter == 3
        if stuck_detected:
            self.session.stuck_events += 1

        self._last_screen_hash = screen_hash

        # Create record
        record = ExplorationRecord(
            iteration=iteration,
            activity=activity,
            is_new_activity=is_new_activity,
            actions_since_last_new=self._actions_since_new_activity,
            total_activities_discovered=len(self._discovered_activities),
            screen_hash=screen_hash,
            is_stuck=self._stuck_counter >= 3,
            stuck_iterations=self._stuck_counter,
            action_type=action_type,
            action_source=action_source,
        )

        # Update session metrics
        self.session.exploration_records.append(record)
        self.session.activities_discovered = len(self._discovered_activities)
        self.session.total_iterations = iteration

        logger.debug(
            f"Recorded exploration: activity={activity}, "
            f"new={is_new_activity}, stuck={record.is_stuck}"
        )

        return record

    def record_screen_elements(
        self,
        screen_hash: str,
        ui_dump: str,
    ) -> None:
        """
        Record all elements present on a screen for coverage tracking.

        Args:
            screen_hash: Screen state hash
            ui_dump: UIAutomator XML dump
        """
        if not ui_dump:
            return

        ui_elements = parse_ui_elements_from_dump(ui_dump)

        if screen_hash not in self._elements_by_screen:
            self._elements_by_screen[screen_hash] = set()

        for elem in ui_elements:
            # Create element_id from bounds center
            center_x, center_y = elem.bounds.center
            element_id = f"{center_x}:{center_y}"

            self._elements_by_screen[screen_hash].add(element_id)
            if element_id not in self._component_types:
                self._component_types[element_id] = elem.element_type

        logger.debug(
            f"Recorded {len(ui_elements)} elements for screen {screen_hash[:8]}"
        )

    def set_coverage_metrics(self, coverage_metrics: Dict[str, Any]) -> None:
        """
        Set coverage metrics from CoverageTracker.

        Args:
            coverage_metrics: Dictionary with coverage data from CoverageResult.to_dict()
        """
        # Map CoverageResult fields to SessionMetrics fields
        self.session.method_coverage = coverage_metrics.get("method_coverage", 0.0)
        self.session.mop_method_coverage = coverage_metrics.get(
            "reaches_mop_coverage", 0.0
        )
        self.session.direct_mop_method_coverage = coverage_metrics.get(
            "directly_reaches_mop_coverage", 0.0
        )
        self.session.called_methods = coverage_metrics.get("called_methods", 0)
        self.session.total_mop_methods = coverage_metrics.get("total_reaches_mop", 0)
        self.session.called_mop_methods = coverage_metrics.get("called_reaches_mop", 0)
        self.session.total_direct_mop_methods = coverage_metrics.get(
            "total_directly_reaches_mop", 0
        )
        self.session.called_direct_mop_methods = coverage_metrics.get(
            "called_directly_reaches_mop", 0
        )
        self.session.unique_errors = coverage_metrics.get("unique_errors", 0)
        self.session.total_errors = coverage_metrics.get("total_errors", 0)

        logger.info(
            f"Coverage metrics set: method={self.session.method_coverage:.1f}%, "
            f"mop={self.session.mop_method_coverage:.1f}%, "
            f"direct_mop={self.session.direct_mop_method_coverage:.1f}%"
        )

    def set_ui_coverage_from_agent(self, ui_coverage: Dict[str, Any]) -> None:
        """
        Set UI coverage metrics from agent's core UICoverageTracker.

        This receives the comprehensive metrics from the agent's ui_coverage tracker,
        which tracks element discovery and interactions during exploration.

        Args:
            ui_coverage: Dictionary from UICoverageTracker.get_comprehensive_metrics()
        """
        ui = self.session.ui_metrics

        ui.total_unique_elements = ui_coverage.get("total_unique_elements", 0)
        ui.total_interactions = ui_coverage.get("total_interactions", 0)
        # avg_interactions_per_element and element_coverage are calculated properties

        dist = ui_coverage.get("element_distribution", {})
        ui.untested_elements = dist.get("untested", 0)
        ui.tested_once = dist.get("tested_once", 0)
        ui.tested_multiple = dist.get("tested_multiple", 0)
        ui.well_tested = dist.get("well_tested", 0)

        ui.actions_by_component = ui_coverage.get("interactions_by_type", {})
        ui.elements_by_component = ui_coverage.get("elements_by_type", {})
        ui.coverage_by_component = ui_coverage.get("coverage_by_type", {})
        ui.screens_visited = ui_coverage.get("screens_visited", 0)
        ui.elements_per_screen = ui_coverage.get("elements_per_screen", {})
        ui.coverage_per_screen = ui_coverage.get("coverage_per_screen", {})

        logger.info(
            f"UI coverage from agent: {ui.total_unique_elements} elements, "
            f"{ui.element_coverage:.1f}% tested, {ui.screens_visited} screens"
        )

    def finalize(self) -> SessionMetrics:
        """
        Finalize collection and calculate final metrics.

        Returns:
            Complete SessionMetrics
        """
        self.session.end_time = time.time()

        # Check for unrecovered stuck at end
        if self._stuck_counter >= 3:
            self.session.stuck_failed += 1

        # Calculate UI element metrics
        self._calculate_ui_metrics()

        logger.info(
            f"Session finalized: "
            f"hit_rate={self.session.hit_rate:.2%}, "
            f"activity_coverage={self.session.activity_coverage:.2%}, "
            f"duration={self.session.duration_seconds:.1f}s"
        )

        # Save if output dir specified
        if self.output_dir:
            self.save(self.output_dir)

        return self.session

    def _calculate_ui_metrics(self) -> None:
        """Calculate UI element metrics from tracked data."""
        ui = self.session.ui_metrics

        # If UI coverage was already set from agent's UICoverageTracker, preserve it
        if ui.total_unique_elements > 0 or ui.total_interactions > 0:
            logger.info(
                f"UI metrics already set from agent: "
                f"elements={ui.total_unique_elements}, "
                f"interactions={ui.total_interactions}, "
                f"element_coverage={ui.element_coverage:.1f}%"
            )
            return

        # Total unique elements and interactions (fallback for LLM-only mode)
        ui.total_unique_elements = len(self._component_types)
        ui.total_interactions = sum(self._element_interactions.values())

        # Element testing distribution
        for element_id, count in self._element_interactions.items():
            if count == 1:
                ui.tested_once += 1
            elif count <= 3:
                ui.tested_multiple += 1
            else:
                ui.well_tested += 1

        # Untested elements = discovered but never interacted
        interacted_elements = set(self._element_interactions.keys())
        all_elements = set(self._component_types.keys())
        ui.untested_elements = len(all_elements - interacted_elements)

        # Actions by component type
        for element_id, count in self._element_interactions.items():
            comp_type = self._component_types.get(element_id, "Unknown")
            ui.actions_by_component[comp_type] = (
                ui.actions_by_component.get(comp_type, 0) + count
            )

        # Elements by component type
        for element_id, comp_type in self._component_types.items():
            ui.elements_by_component[comp_type] = (
                ui.elements_by_component.get(comp_type, 0) + 1
            )

        # Coverage by component type
        for comp_type in set(self._component_types.values()):
            elements_of_type = [
                eid for eid, ct in self._component_types.items() if ct == comp_type
            ]
            tested_of_type = [
                eid for eid in elements_of_type if eid in self._element_interactions
            ]
            ui.coverage_by_component[comp_type] = {
                "total": len(elements_of_type),
                "tested": len(tested_of_type),
                "coverage": (
                    len(tested_of_type) / len(elements_of_type) * 100
                    if elements_of_type
                    else 0
                ),
            }

        # Per-screen metrics
        ui.screens_visited = len(self._elements_by_screen)
        for screen_hash, elements in self._elements_by_screen.items():
            ui.elements_per_screen[screen_hash[:8]] = len(elements)
            tested = len([e for e in elements if e in self._element_interactions])
            ui.coverage_per_screen[screen_hash[:8]] = (
                tested / len(elements) * 100 if elements else 0
            )

        logger.info(
            f"UI metrics calculated: "
            f"elements={ui.total_unique_elements}, "
            f"interactions={ui.total_interactions}, "
            f"screens={ui.screens_visited}, "
            f"element_coverage={ui.element_coverage:.1f}%"
        )

    def save(self, output_dir: Path) -> Path:
        """
        Save metrics to JSON file.

        Args:
            output_dir: Directory to save to

        Returns:
            Path to saved file
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = (
            f"multimodal_metrics_"
            f"{self.session.app_package}_"
            f"{self.session.agent_mode}_"
            f"{self.session.strategy}_"
            f"seed{self.session.seed}.json"
        )
        filepath = output_dir / filename

        data = self._to_dict()

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"Saved metrics to {filepath}")
        return filepath

    def _to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for serialization."""
        return {
            "session": {
                "app_package": self.session.app_package,
                "agent_mode": self.session.agent_mode,
                "strategy": self.session.strategy,
                "timeout_seconds": self.session.timeout_seconds,
                "seed": self.session.seed,
                "start_time": self.session.start_time,
                "end_time": self.session.end_time,
                "duration_seconds": self.session.duration_seconds,
            },
            "llm_metrics": {
                "total_llm_calls": self.session.total_llm_calls,
                "total_tokens_input": self.session.total_tokens_input,
                "total_tokens_output": self.session.total_tokens_output,
                "total_tokens": self.session.total_tokens_input
                + self.session.total_tokens_output,
                "total_latency_ms": self.session.total_latency_ms,
                "avg_latency_ms": self.session.avg_latency_ms,
                "tokens_per_action": self.session.tokens_per_action,
            },
            "hit_rate_metrics": {
                "total_clicks": self.session.total_clicks,
                "hits": self.session.hits,
                "near_misses": self.session.near_misses,
                "ui_misses": self.session.ui_misses,
                "empty_misses": self.session.empty_misses,
                "hit_rate": self.session.hit_rate,
                "tool_call_rate": self.session.tool_call_rate,
            },
            "exploration_metrics": {
                "total_activities": self.session.total_activities,
                "activities_discovered": self.session.activities_discovered,
                "activity_coverage": self.session.activity_coverage,
                "total_iterations": self.session.total_iterations,
                "actions_per_activity": self.session.actions_per_activity,
            },
            "stuck_metrics": {
                "stuck_events": self.session.stuck_events,
                "stuck_recovered": self.session.stuck_recovered,
                "stuck_failed": self.session.stuck_failed,
                "stuck_recovery_rate": self.session.stuck_recovery_rate,
            },
            "coverage_metrics": {
                "method_coverage": self.session.method_coverage,
                "mop_method_coverage": self.session.mop_method_coverage,
                "direct_mop_method_coverage": self.session.direct_mop_method_coverage,
                "called_methods": self.session.called_methods,
                "total_mop_methods": self.session.total_mop_methods,
                "called_mop_methods": self.session.called_mop_methods,
                "total_direct_mop_methods": self.session.total_direct_mop_methods,
                "called_direct_mop_methods": self.session.called_direct_mop_methods,
                "unique_errors": self.session.unique_errors,
                "total_errors": self.session.total_errors,
                "logcat_file": self.session.logcat_file,
            },
            "llm_actions": [
                {
                    "iteration": a.iteration,
                    "raw_coords": a.raw_coords,
                    "device_coords": a.device_coords,
                    "hit_classification": a.hit_classification.value,
                    "hit_element_type": a.hit_element_type,
                    "distance_to_target": a.distance_to_target,
                    "distance_to_nearest": a.distance_to_nearest,
                    "latency_ms": a.latency_ms,
                    "tokens_input": a.tokens_input,
                    "tokens_output": a.tokens_output,
                    "tool_name": a.tool_name,
                    "parser_strategy": a.parser_strategy,
                    "activity": a.activity,
                }
                for a in self.session.llm_actions
            ],
            "exploration_records": [
                {
                    "iteration": r.iteration,
                    "activity": r.activity,
                    "is_new_activity": r.is_new_activity,
                    "actions_since_last_new": r.actions_since_last_new,
                    "is_stuck": r.is_stuck,
                    "action_type": r.action_type,
                    "action_source": r.action_source,
                }
                for r in self.session.exploration_records
            ],
            "ui_metrics": {
                "total_unique_elements": self.session.ui_metrics.total_unique_elements,
                "total_interactions": self.session.ui_metrics.total_interactions,
                "avg_interactions_per_element": self.session.ui_metrics.avg_interactions_per_element,
                "element_coverage": self.session.ui_metrics.element_coverage,
                "element_distribution": {
                    "untested": self.session.ui_metrics.untested_elements,
                    "tested_once": self.session.ui_metrics.tested_once,
                    "tested_multiple": self.session.ui_metrics.tested_multiple,
                    "well_tested": self.session.ui_metrics.well_tested,
                },
                "actions_by_component": self.session.ui_metrics.actions_by_component,
                "elements_by_component": self.session.ui_metrics.elements_by_component,
                "coverage_by_component": self.session.ui_metrics.coverage_by_component,
                "screens_visited": self.session.ui_metrics.screens_visited,
                "elements_per_screen": self.session.ui_metrics.elements_per_screen,
                "coverage_per_screen": self.session.ui_metrics.coverage_per_screen,
            },
        }

    @classmethod
    def load(cls, filepath: Path) -> "SessionMetrics":
        """
        Load metrics from JSON file.

        Args:
            filepath: Path to JSON file

        Returns:
            SessionMetrics object
        """
        with open(filepath) as f:
            data = json.load(f)

        session = SessionMetrics(
            app_package=data["session"]["app_package"],
            agent_mode=data["session"]["agent_mode"],
            timeout_seconds=data["session"]["timeout_seconds"],
            seed=data["session"]["seed"],
            start_time=data["session"]["start_time"],
            end_time=data["session"]["end_time"],
            total_activities=data["exploration_metrics"]["total_activities"],
        )

        # Restore metrics
        session.total_llm_calls = data["llm_metrics"]["total_llm_calls"]
        session.total_tokens_input = data["llm_metrics"]["total_tokens_input"]
        session.total_tokens_output = data["llm_metrics"]["total_tokens_output"]
        session.total_latency_ms = data["llm_metrics"]["total_latency_ms"]

        session.total_clicks = data["hit_rate_metrics"]["total_clicks"]
        session.hits = data["hit_rate_metrics"]["hits"]
        session.near_misses = data["hit_rate_metrics"]["near_misses"]
        session.ui_misses = data["hit_rate_metrics"]["ui_misses"]
        session.empty_misses = data["hit_rate_metrics"]["empty_misses"]

        session.activities_discovered = data["exploration_metrics"][
            "activities_discovered"
        ]
        session.total_iterations = data["exploration_metrics"]["total_iterations"]

        session.stuck_events = data["stuck_metrics"]["stuck_events"]
        session.stuck_recovered = data["stuck_metrics"]["stuck_recovered"]
        session.stuck_failed = data["stuck_metrics"]["stuck_failed"]

        # Restore coverage metrics if present
        if "coverage_metrics" in data:
            cov = data["coverage_metrics"]
            session.method_coverage = cov.get("method_coverage", 0.0)
            session.mop_method_coverage = cov.get("mop_method_coverage", 0.0)
            session.direct_mop_method_coverage = cov.get(
                "direct_mop_method_coverage", 0.0
            )
            session.called_methods = cov.get("called_methods", 0)
            session.total_mop_methods = cov.get("total_mop_methods", 0)
            session.called_mop_methods = cov.get("called_mop_methods", 0)
            session.total_direct_mop_methods = cov.get("total_direct_mop_methods", 0)
            session.called_direct_mop_methods = cov.get("called_direct_mop_methods", 0)
            session.unique_errors = cov.get("unique_errors", 0)
            session.total_errors = cov.get("total_errors", 0)
            session.logcat_file = cov.get("logcat_file", "")

        # Restore UI metrics if present
        if "ui_metrics" in data:
            ui = data["ui_metrics"]
            session.ui_metrics.total_unique_elements = ui.get(
                "total_unique_elements", 0
            )
            session.ui_metrics.total_interactions = ui.get("total_interactions", 0)
            session.ui_metrics.actions_by_component = ui.get("actions_by_component", {})
            session.ui_metrics.elements_by_component = ui.get(
                "elements_by_component", {}
            )
            session.ui_metrics.coverage_by_component = ui.get(
                "coverage_by_component", {}
            )
            session.ui_metrics.screens_visited = ui.get("screens_visited", 0)
            session.ui_metrics.elements_per_screen = ui.get("elements_per_screen", {})
            session.ui_metrics.coverage_per_screen = ui.get("coverage_per_screen", {})

            dist = ui.get("element_distribution", {})
            session.ui_metrics.untested_elements = dist.get("untested", 0)
            session.ui_metrics.tested_once = dist.get("tested_once", 0)
            session.ui_metrics.tested_multiple = dist.get("tested_multiple", 0)
            session.ui_metrics.well_tested = dist.get("well_tested", 0)

        return session
