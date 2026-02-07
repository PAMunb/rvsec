"""
Domain models for screen state tracking.

Contains the core data models for representing UI states and transitions
in the exploration graph.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Set, List, Any, Tuple

# Number of failures before marking action as permanently failed
MAX_FAILURE_ATTEMPTS = 3

logger = logging.getLogger(__name__)


@dataclass
class ScreenNode:
    """
    Node representing a unique UI structure state with coordinate-based action tracking.

    ### Architectural Decisions:
    - Identified by structural hash, not activity name
    - Captures total actions count on first visit
    - Tracks executed actions by coordinates (not IDs) for stability across parsing sessions
    - Tracks execution COUNT per action for continuous exploration prioritization
    - Computes coverage as ratio of executed/total actions
    - Tracks action success for strength-based prioritization

    ### Key Design: Coordinate-Based Tracking
    - Action IDs are non-deterministic across UIAutomator dumps
    - Same UI element can receive different IDs on different parses
    - Coordinates are stable identifiers for the same screen element
    - Solves the "repeated crash action" problem caused by ID instability

    ### Continuous Exploration Design:
    - Tracks how many times each action was executed (not just boolean)
    - Enables prioritizing least-executed actions when all have been tried
    - Algorithm continues until timeout, never stops when "exhausted"

    ### Saturation Tracking:
    - Tracks action success counts for strength calculation
    - Computes saturation rate (actions executed 2+ times / total)
    - Enables backtrack decisions based on state saturation

    ### Role in the System:
    - Represents unique UI state in exploration graph
    - Tracks action execution for coverage computation
    - Provides context for strategy decision-making
    - Records activity name for interpretability
    """

    screen_hash: str
    activity: str
    visit_count: int = 0
    total_actions: int = 0
    executed_actions: Set[Tuple[Tuple[int, int], str]] = field(default_factory=set)
    action_execution_counts: Dict[Tuple[Tuple[int, int], str], int] = field(default_factory=dict)
    # Failed actions tracking: actions that caused crashes/errors
    failed_actions: Set[Tuple[Tuple[int, int], str]] = field(default_factory=set)
    action_failure_counts: Dict[Tuple[Tuple[int, int], str], int] = field(default_factory=dict)
    # Success tracking for strength calculation
    action_success_counts: Dict[Tuple[Tuple[int, int], str], int] = field(default_factory=dict)

    def get_coverage(self) -> float:
        """
        Compute action coverage percentage for this screen.

        Returns:
            Coverage ratio (0.0 to 1.0)
        """
        if self.total_actions == 0:
            return 0.0
        return len(self.executed_actions) / self.total_actions

    def record_action(self, action_signature: Tuple[Tuple[int, int], str]):
        """
        Record action execution by signature (coordinates + action type).
        Increments execution count for continuous exploration prioritization.

        Args:
            action_signature: ((x, y), action_type) tuple identifying the action
        """
        self.executed_actions.add(action_signature)
        self.action_execution_counts[action_signature] = self.action_execution_counts.get(action_signature, 0) + 1

    def get_action_execution_count(self, action_signature: Tuple[Tuple[int, int], str]) -> int:
        """
        Get execution count for an action signature.

        Args:
            action_signature: ((x, y), action_type) tuple to check

        Returns:
            Number of times action was executed (0 if never executed)
        """
        return self.action_execution_counts.get(action_signature, 0)

    def is_action_executed(self, action_signature: Tuple[Tuple[int, int], str]) -> bool:
        """
        Check if action with given signature was already executed.

        Args:
            action_signature: ((x, y), action_type) tuple to check

        Returns:
            True if action was executed, False otherwise
        """
        return action_signature in self.executed_actions

    def record_action_failure(self, action_signature: Tuple[Tuple[int, int], str]):
        """
        Record action failure with tolerance for transient failures.

        The action is marked as permanently failed only after MAX_FAILURE_ATTEMPTS
        consecutive failures. This provides tolerance for transient network issues,
        emulator timeouts, or temporary conditions.

        TODO: Esta funcao NAO esta sendo chamada em nenhum lugar do workflow.
        Os dados de failed_actions estao sempre vazios. Verificar se devemos
        conectar deteccao de falhas (crash, timeout, erro) a esta funcao,
        ou remover o codigo relacionado (FailedActionScorer, is_action_failed, etc).

        Args:
            action_signature: ((x, y), action_type) tuple identifying the action
        """
        current_count = self.action_failure_counts.get(action_signature, 0)
        new_count = current_count + 1
        self.action_failure_counts[action_signature] = new_count

        if new_count >= MAX_FAILURE_ATTEMPTS:
            self.failed_actions.add(action_signature)
            logger.warning(
                f"Action {action_signature} marked as permanently failed "
                f"after {new_count} failures on state {self.screen_hash[:8]}"
            )

    def reset_action_failure(self, action_signature: Tuple[Tuple[int, int], str]):
        """
        Reset failure counter when action succeeds.

        Called when an action that previously failed now succeeds,
        clearing its failure history.

        Args:
            action_signature: ((x, y), action_type) tuple identifying the action
        """
        if action_signature in self.action_failure_counts:
            del self.action_failure_counts[action_signature]

    def is_action_failed(self, action_signature: Tuple[Tuple[int, int], str]) -> bool:
        """
        Check if action has permanently failed.

        Args:
            action_signature: ((x, y), action_type) tuple to check

        Returns:
            True if action has failed MAX_FAILURE_ATTEMPTS times
        """
        return action_signature in self.failed_actions

    def get_action_failure_count(self, action_signature: Tuple[Tuple[int, int], str]) -> int:
        """
        Get current failure count for an action.

        Args:
            action_signature: ((x, y), action_type) tuple to check

        Returns:
            Number of failures recorded (0 if none)
        """
        return self.action_failure_counts.get(action_signature, 0)

    def is_action_saturated(self, action_signature: Tuple[Tuple[int, int], str], threshold: int = 2) -> bool:
        """
        Check if action has been executed at least threshold times.

        An action is "saturated" when it has been sufficiently explored.

        Args:
            action_signature: ((x, y), action_type) tuple to check
            threshold: Minimum execution count to be considered saturated

        Returns:
            True if action executed >= threshold times
        """
        return self.get_action_execution_count(action_signature) >= threshold

    def get_saturation_rate(self, threshold: int = 2) -> float:
        """
        Compute saturation rate for this state.

        Saturation rate = actions executed >= threshold times / total actions

        Args:
            threshold: Minimum execution count to be considered saturated

        Returns:
            Saturation ratio (0.0 to 1.0)
        """
        if self.total_actions == 0:
            return 1.0  # No actions = fully saturated

        saturated_count = sum(
            1 for sig in self.executed_actions
            if self.is_action_saturated(sig, threshold)
        )
        return saturated_count / self.total_actions

    def get_all_action_signatures(self) -> Set[Tuple[Tuple[int, int], str]]:
        """
        Get all known action signatures for this state.

        Returns:
            Set of all action signatures that have been executed
        """
        return set(self.executed_actions)

    def record_action_success(self, action_signature: Tuple[Tuple[int, int], str], success: bool) -> None:
        """
        Record whether an action execution was successful.

        Success is determined by state transition: if the screen changed
        after the action, it was successful.

        Args:
            action_signature: ((x, y), action_type) tuple identifying the action
            success: True if action caused a state transition
        """
        if success:
            self.action_success_counts[action_signature] = (
                self.action_success_counts.get(action_signature, 0) + 1
            )

    def get_action_strength(self, action_signature: Tuple[Tuple[int, int], str]) -> float:
        """
        Compute action strength based on success rate.

        Strength = successes / executions (0.5 if never executed)

        Args:
            action_signature: ((x, y), action_type) tuple to check

        Returns:
            Strength value (0.0 to 1.0), or 0.5 for untested actions
        """
        executions = self.get_action_execution_count(action_signature)
        if executions == 0:
            return 0.5  # Unknown - neutral strength

        successes = self.action_success_counts.get(action_signature, 0)
        return successes / executions


@dataclass
class Transition:
    """
    Represents a state transition with complete action sequence.

    ### Architectural Decisions:
    - Records all actions executed between states
    - Captures multi-step workflows (e.g., form filling)
    - Includes timestamp for temporal analysis
    - Stores both source and destination hashes

    ### Role in the System:
    - Enables transition graph reconstruction
    - Supports temporal analysis of exploration
    - Provides audit trail for debugging
    - Preserves complete workflow sequences
    """

    from_hash: str
    to_hash: str
    action_sequence: List[Dict[str, Any]]
    timestamp: float
