"""
Domain models for screen state tracking in the exploration graph.

Provide the core data structures for representing UI states (ScreenNode) and
state transitions (Transition) used by the DynamicStateGraph and RVAgentStrategy.
ScreenNode tracks action execution by coordinate-based signatures rather than
volatile UIAutomator IDs, enabling stable coverage tracking across parsing sessions.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set, Tuple

logger = logging.getLogger(__name__)

# Saturation threshold for single-action widgets (Button, ImageButton, etc.)
DEFAULT_SATURATION_THRESHOLD = 2

# Multi-value widgets: each interaction can produce different input/state,
# so they need more executions before being considered "saturated" (D8 Bug #4).
# Uses simple class name (after last ".") from android.widget.* hierarchy.
MULTI_VALUE_WIDGETS = frozenset(
    {
        # Text input — each interaction can use different text
        "EditText",
        "TextInputEditText",
        "AppCompatEditText",
        "AutoCompleteTextView",
        "AppCompatAutoCompleteTextView",
        "MultiAutoCompleteTextView",
        # Dropdown selection — multiple items to choose from
        "Spinner",
        "AppCompatSpinner",
        # Continuous range — different positions to try
        "SeekBar",
        "AppCompatSeekBar",
        "RatingBar",
        "AppCompatRatingBar",
        # Numeric selection
        "NumberPicker",
    }
)


@dataclass
class ScreenNode:
    """
    Represent a unique UI structure state with coordinate-based action tracking.

    Each ScreenNode corresponds to a distinct screen layout identified by structural
    hash (not activity name). It tracks which actions have been executed, how many
    times, and whether they caused state transitions -- providing the data needed
    for coverage computation, action ranking, and backtrack decisions.

    ### Architectural Decisions:

    - Coordinate-based tracking: action IDs are non-deterministic across UIAutomator
      dumps (same element can receive different IDs on different parses). Coordinates
      are stable identifiers, solving the "repeated crash action" problem caused by
      ID instability.
    - Continuous exploration: tracks execution COUNT per action (not just boolean),
      enabling least-executed prioritization when all actions have been tried. The
      algorithm continues until timeout, never stops when "exhausted".
    - Saturation tracking: tracks action success counts for strength calculation and
      computes saturation rate using per-widget thresholds, enabling proactive
      backtrack decisions based on state saturation.
    - Widget-aware saturation: multi-value widgets (EditText, Spinner, SeekBar) use
      a higher configurable threshold than single-action widgets (Button), ensuring
      the agent explores diverse input combinations before declaring saturation (D8).

    ### Role in the System:

    - Represents unique UI state in DynamicStateGraph
    - Tracks action execution for coverage computation in RVAgentStrategy
    - Provides strength and saturation metrics for ActionRanker scorers
    - Records activity name for interpretability in tracking logs

    Attributes:
        screen_hash: Structural hash identifying the unique screen layout.
        activity: Android activity name for interpretability.
        visit_count: Number of times the agent visited this state.
        total_actions: Total available actions captured on first visit.
        executed_actions: Set of action signatures that have been executed at
            least once. Each signature is ((x, y), action_type).
        action_execution_counts: Execution count per action signature for
            continuous exploration prioritization.
        action_success_counts: Success count per action signature. An action
            is "successful" when it causes a state transition.
        action_cumulative_reward: Per-action cumulative reward from N-step
            reward propagation via RewardPropagator.
        action_widget_classes: Maps action signatures to their Android widget
            class name (e.g., "android.widget.EditText"). Used by
            _effective_threshold() to apply per-widget saturation thresholds.
        multi_value_threshold: Configurable saturation threshold for multi-value
            widgets. Set from RVAgentConfig.multi_value_saturation_threshold.
    """

    screen_hash: str
    activity: str
    visit_count: int = 0
    total_actions: int = 0
    executed_actions: Set[Tuple[Tuple[int, int], str]] = field(default_factory=set)
    action_execution_counts: Dict[Tuple[Tuple[int, int], str], int] = field(
        default_factory=dict
    )
    action_success_counts: Dict[Tuple[Tuple[int, int], str], int] = field(
        default_factory=dict
    )
    action_cumulative_reward: Dict[Tuple[Tuple[int, int], str], float] = field(
        default_factory=dict
    )
    action_widget_classes: Dict[Tuple[Tuple[int, int], str], str] = field(
        default_factory=dict
    )
    multi_value_threshold: int = 4

    def get_coverage(self) -> float:
        """Compute action coverage ratio for this screen.

        Returns:
            Coverage ratio (0.0 to 1.0). Returns 0.0 when no actions exist.
        """
        if self.total_actions == 0:
            return 0.0
        return len(self.executed_actions) / self.total_actions

    def record_action(
        self,
        action_signature: Tuple[Tuple[int, int], str],
        widget_class: str = "",
    ):
        """Record action execution and increment its execution count.

        Args:
            action_signature: ((x, y), action_type) tuple identifying the action.
            widget_class: Android widget class name (e.g., "android.widget.EditText").
                Stored on first recording for per-widget saturation thresholds (D8).
        """
        self.executed_actions.add(action_signature)
        self.action_execution_counts[action_signature] = (
            self.action_execution_counts.get(action_signature, 0) + 1
        )
        if widget_class and action_signature not in self.action_widget_classes:
            self.action_widget_classes[action_signature] = widget_class

    def get_action_execution_count(
        self, action_signature: Tuple[Tuple[int, int], str]
    ) -> int:
        """Get execution count for an action signature.

        Args:
            action_signature: ((x, y), action_type) tuple to check.

        Returns:
            Number of times the action was executed (0 if never executed).
        """
        return self.action_execution_counts.get(action_signature, 0)

    def is_action_executed(self, action_signature: Tuple[Tuple[int, int], str]) -> bool:
        """Check if action with given signature was already executed.

        Args:
            action_signature: ((x, y), action_type) tuple to check.

        Returns:
            True if action was executed at least once.
        """
        return action_signature in self.executed_actions

    def _effective_threshold(
        self, action_signature: Tuple[Tuple[int, int], str]
    ) -> int:
        """Get saturation threshold for an action based on its widget type.

        Multi-value widgets (EditText, Spinner, SeekBar, etc.) use
        multi_value_threshold because each interaction can produce different
        input/state. Single-action widgets use DEFAULT_SATURATION_THRESHOLD (D8).

        Args:
            action_signature: ((x, y), action_type) tuple to look up.

        Returns:
            Saturation threshold for this action's widget type.
        """
        widget_class = self.action_widget_classes.get(action_signature, "")
        simple_name = widget_class.rsplit(".", 1)[-1] if widget_class else ""
        if simple_name in MULTI_VALUE_WIDGETS:
            return self.multi_value_threshold
        return DEFAULT_SATURATION_THRESHOLD

    def is_action_saturated(
        self, action_signature: Tuple[Tuple[int, int], str], threshold: int = 0
    ) -> bool:
        """Check if action has been executed at least threshold times.

        An action is "saturated" when it has been sufficiently explored and
        further executions are unlikely to yield new state transitions.

        Args:
            action_signature: ((x, y), action_type) tuple to check.
            threshold: Minimum execution count. If 0 (default), uses
                per-widget threshold from _effective_threshold().

        Returns:
            True if action executed >= threshold times.
        """
        if threshold == 0:
            threshold = self._effective_threshold(action_signature)
        return self.get_action_execution_count(action_signature) >= threshold

    # System action types that should not count toward saturation.
    # These actions (BACK, RESTART, unknown) are not real UI widgets —
    # including them inflates the saturated count above total_actions (D8).
    SYSTEM_ACTION_TYPES = frozenset({"back", "restart", "unknown"})

    def get_saturation_rate(self) -> float:
        """Compute saturation rate for this state using per-widget thresholds.

        Saturation rate = real saturated actions / total actions.
        System actions (BACK, RESTART, unknown) are excluded from the numerator
        because they are not real UI widgets and would inflate the ratio (D8).
        Multi-value widgets (EditText, Spinner, SeekBar) use a higher threshold
        than single-action widgets (Button) to ensure diverse input exploration.

        Returns:
            Saturation ratio (0.0 to 1.0).
        """
        if self.total_actions == 0:
            return 1.0  # No actions = fully saturated

        saturated_count = sum(
            1
            for sig in self.executed_actions
            if sig[1] not in self.SYSTEM_ACTION_TYPES and self.is_action_saturated(sig)
        )
        return min(1.0, saturated_count / self.total_actions)

    def get_all_action_signatures(self) -> Set[Tuple[Tuple[int, int], str]]:
        """Get all known action signatures for this state.

        Returns:
            Set of all action signatures that have been executed.
        """
        return set(self.executed_actions)

    def record_action_success(
        self, action_signature: Tuple[Tuple[int, int], str], success: bool
    ) -> None:
        """Record whether an action execution caused a state transition.

        Success is determined by screen hash change: if the screen changed
        after executing the action, it is considered successful. Only
        successful executions increment the success counter.

        Args:
            action_signature: ((x, y), action_type) tuple identifying the action.
            success: True if action caused a state transition.
        """
        if success:
            self.action_success_counts[action_signature] = (
                self.action_success_counts.get(action_signature, 0) + 1
            )

    def get_action_strength(
        self, action_signature: Tuple[Tuple[int, int], str]
    ) -> float:
        """Compute action strength as success rate (successes / executions).

        Untested actions return 0.5 (neutral strength) so they are neither
        penalized nor boosted by StrengthScorer before first execution.

        Args:
            action_signature: ((x, y), action_type) tuple to check.

        Returns:
            Strength value (0.0 to 1.0), or 0.5 for untested actions.
        """
        executions = self.get_action_execution_count(action_signature)
        if executions == 0:
            return 0.5  # Unknown - neutral strength

        successes = self.action_success_counts.get(action_signature, 0)
        return successes / executions


@dataclass
class Transition:
    """Represent a state transition with the complete action sequence between states.

    Record all actions executed between two screen states, preserving multi-step
    workflows (e.g., form filling followed by submit). Used by DynamicStateGraph
    for transition graph reconstruction and temporal analysis of exploration.

    Attributes:
        from_hash: Structural hash of the source screen state.
        to_hash: Structural hash of the destination screen state.
        action_sequence: Ordered list of action dictionaries executed between
            states. Each dict contains action type, coordinates, and metadata.
        timestamp: Unix timestamp when the transition was recorded.
    """

    from_hash: str
    to_hash: str
    action_sequence: List[Dict[str, Any]]
    timestamp: float
