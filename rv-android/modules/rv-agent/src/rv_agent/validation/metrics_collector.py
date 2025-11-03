"""
Metrics collector for offline validation.

Collects comprehensive metrics about agent behavior including actions,
element coverage, exploration patterns, memory usage, and LLM metrics.
"""

import logging
import time
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class IterationMetrics:
    """Metrics for a single iteration."""

    iteration: int
    timestamp: float
    action_type: str
    valid_action: bool
    screen_hash: str
    activity: str
    element_count: int
    element_types: Dict[str, int]
    message_count: int = 0
    tokens_input: int = 0
    tokens_output: int = 0
    llm_time_ms: float = 0.0


@dataclass
class ValidationMetrics:
    """Comprehensive validation metrics."""

    # Basic info
    app_name: str
    start_time: float
    end_time: float = 0.0
    total_iterations: int = 0

    # Action metrics
    actions_by_type: Dict[str, int] = field(default_factory=dict)
    valid_actions: int = 0
    invalid_actions: int = 0

    # Element coverage
    element_types_seen: Set[str] = field(default_factory=set)
    element_type_counts: Dict[str, int] = field(default_factory=dict)
    interactive_elements_total: int = 0

    # Exploration metrics
    unique_screens: Set[str] = field(default_factory=set)
    screen_visits: Dict[str, int] = field(default_factory=dict)
    activities_seen: Set[str] = field(default_factory=set)

    # Memory & graph metrics
    graph_states: int = 0
    graph_transitions: int = 0
    long_term_patterns: int = 0
    short_term_iterations: int = 0

    # LLM metrics
    total_tokens: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_llm_time_ms: float = 0.0
    avg_tokens_per_iteration: float = 0.0
    max_message_count: int = 0

    # Per-iteration data
    iterations: List[IterationMetrics] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'app_name': self.app_name,
            'execution_time_s': self.end_time - self.start_time if self.end_time > 0 else 0,
            'total_iterations': self.total_iterations,

            'actions': {
                'by_type': self.actions_by_type,
                'valid': self.valid_actions,
                'invalid': self.invalid_actions,
                'valid_rate': self.valid_actions / (self.valid_actions + self.invalid_actions)
                              if (self.valid_actions + self.invalid_actions) > 0 else 0.0
            },

            'element_coverage': {
                'types_seen': list(self.element_types_seen),
                'type_counts': self.element_type_counts,
                'interactive_elements': self.interactive_elements_total
            },

            'exploration': {
                'unique_screens': len(self.unique_screens),
                'screen_visits': self.screen_visits,
                'activities': list(self.activities_seen),
                'revisit_rate': (sum(self.screen_visits.values()) - len(self.unique_screens)) /
                               sum(self.screen_visits.values()) if sum(self.screen_visits.values()) > 0 else 0.0
            },

            'memory_graph': {
                'graph_states': self.graph_states,
                'graph_transitions': self.graph_transitions,
                'long_term_patterns': self.long_term_patterns,
                'short_term_iterations': self.short_term_iterations
            },

            'llm': {
                'total_tokens': self.total_tokens,
                'input_tokens': self.total_input_tokens,
                'output_tokens': self.total_output_tokens,
                'avg_tokens_per_iteration': self.avg_tokens_per_iteration,
                'max_message_count': self.max_message_count,
                'total_time_ms': self.total_llm_time_ms,
                'avg_time_per_iteration_ms': self.total_llm_time_ms / self.total_iterations
                                             if self.total_iterations > 0 else 0.0
            }
        }


class MetricsCollector:
    """
    Collects comprehensive validation metrics.

    Tracks:
    - Action distribution and validity
    - UI element coverage
    - Exploration patterns
    - Memory and graph statistics
    - LLM token usage and timing
    """

    def __init__(self, app_name: str):
        """
        Initialize metrics collector.

        Args:
            app_name: Name of app being validated
        """
        self.metrics = ValidationMetrics(
            app_name=app_name,
            start_time=time.time()
        )

        logger.info(f"MetricsCollector initialized for: {app_name}")

    def record_iteration(
        self,
        iteration: int,
        action_type: str,
        valid_action: bool,
        screen_hash: str,
        activity: str,
        element_count: int,
        element_types: Dict[str, int],
        message_count: int = 0,
        tokens_input: int = 0,
        tokens_output: int = 0,
        llm_time_ms: float = 0.0
    ):
        """
        Record metrics for a single iteration.

        Args:
            iteration: Iteration number
            action_type: Type of action executed
            valid_action: Whether action was valid
            screen_hash: Structural hash of current screen
            activity: Current activity name
            element_count: Total UI elements
            element_types: Distribution of element types
            message_count: Number of messages in LLM context
            tokens_input: Input tokens used
            tokens_output: Output tokens generated
            llm_time_ms: LLM inference time in milliseconds
        """
        # Create iteration metrics
        iter_metrics = IterationMetrics(
            iteration=iteration,
            timestamp=time.time(),
            action_type=action_type,
            valid_action=valid_action,
            screen_hash=screen_hash,
            activity=activity,
            element_count=element_count,
            element_types=element_types,
            message_count=message_count,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            llm_time_ms=llm_time_ms
        )

        self.metrics.iterations.append(iter_metrics)
        self.metrics.total_iterations += 1

        # Update action metrics
        self.metrics.actions_by_type[action_type] = \
            self.metrics.actions_by_type.get(action_type, 0) + 1

        if valid_action:
            self.metrics.valid_actions += 1
        else:
            self.metrics.invalid_actions += 1

        # Update element coverage
        for elem_type in element_types:
            self.metrics.element_types_seen.add(elem_type)
            self.metrics.element_type_counts[elem_type] = \
                self.metrics.element_type_counts.get(elem_type, 0) + element_types[elem_type]

        # Update exploration metrics
        self.metrics.unique_screens.add(screen_hash)
        self.metrics.screen_visits[screen_hash] = \
            self.metrics.screen_visits.get(screen_hash, 0) + 1
        self.metrics.activities_seen.add(activity)

        # Update LLM metrics
        self.metrics.total_input_tokens += tokens_input
        self.metrics.total_output_tokens += tokens_output
        self.metrics.total_tokens += tokens_input + tokens_output
        self.metrics.total_llm_time_ms += llm_time_ms
        self.metrics.max_message_count = max(self.metrics.max_message_count, message_count)

        if self.metrics.total_iterations > 0:
            self.metrics.avg_tokens_per_iteration = \
                self.metrics.total_tokens / self.metrics.total_iterations

    def record_memory_stats(
        self,
        graph_states: int,
        graph_transitions: int,
        long_term_patterns: int,
        short_term_iterations: int
    ):
        """
        Record memory and graph statistics.

        Args:
            graph_states: Number of states in dynamic graph
            graph_transitions: Number of transitions in dynamic graph
            long_term_patterns: Number of patterns in long-term memory
            short_term_iterations: Number of iterations in short-term memory
        """
        self.metrics.graph_states = graph_states
        self.metrics.graph_transitions = graph_transitions
        self.metrics.long_term_patterns = long_term_patterns
        self.metrics.short_term_iterations = short_term_iterations

    def finalize(self):
        """Finalize metrics collection."""
        self.metrics.end_time = time.time()

        logger.info(f"Metrics finalized for {self.metrics.app_name}")
        logger.info(f"  Duration: {self.metrics.end_time - self.metrics.start_time:.1f}s")
        logger.info(f"  Iterations: {self.metrics.total_iterations}")
        logger.info(f"  Valid actions: {self.metrics.valid_actions}/{self.metrics.total_iterations}")
        logger.info(f"  Unique screens: {len(self.metrics.unique_screens)}")
        logger.info(f"  Total tokens: {self.metrics.total_tokens}")

    def get_metrics(self) -> ValidationMetrics:
        """Get current metrics."""
        return self.metrics

    def get_action_distribution(self) -> Dict[str, float]:
        """
        Get action distribution as percentages.

        Returns:
            Dictionary mapping action types to percentages
        """
        total = sum(self.metrics.actions_by_type.values())
        if total == 0:
            return {}

        return {
            action: (count / total) * 100
            for action, count in self.metrics.actions_by_type.items()
        }

    def get_element_coverage_rate(self) -> float:
        """
        Get element coverage rate.

        Returns:
            Percentage of interactive elements covered
        """
        if self.metrics.interactive_elements_total == 0:
            return 0.0

        # This is a rough estimate since we don't track individual element IDs
        # Just return percentage of element types seen
        return len(self.metrics.element_types_seen) / max(len(self.metrics.element_type_counts), 1) * 100

    def get_context_growth_rate(self) -> List[int]:
        """
        Get message count growth over iterations.

        Returns:
            List of message counts per iteration
        """
        return [iter.message_count for iter in self.metrics.iterations]

    def get_token_usage_per_iteration(self) -> List[int]:
        """
        Get token usage per iteration.

        Returns:
            List of total tokens per iteration
        """
        return [iter.tokens_input + iter.tokens_output for iter in self.metrics.iterations]
