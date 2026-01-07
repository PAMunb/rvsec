"""
Metrics collector for multimodal validation.

Collects LLM action and exploration metrics during agent execution.
"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from .metrics import (
    LLMActionRecord,
    ExplorationRecord,
    SessionMetrics,
    HitClassification,
    ElementBounds,
)
from .hit_classifier import HitClassifier, UIElement, parse_ui_elements_from_dump


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
        """
        self.session = SessionMetrics(
            app_package=app_package,
            agent_mode=agent_mode,
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

        logger.info(
            f"MultimodalMetricsCollector initialized: "
            f"app={app_package}, mode={agent_mode}"
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
            "android_click", "android_long_click", "android_type_text",
            "CLICK", "LONG_CLICK", "TYPE", "SET_TEXT"
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
                "total_tokens": self.session.total_tokens_input + self.session.total_tokens_output,
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

        session.activities_discovered = data["exploration_metrics"]["activities_discovered"]
        session.total_iterations = data["exploration_metrics"]["total_iterations"]

        session.stuck_events = data["stuck_metrics"]["stuck_events"]
        session.stuck_recovered = data["stuck_metrics"]["stuck_recovered"]
        session.stuck_failed = data["stuck_metrics"]["stuck_failed"]

        return session
