"""
Buffer multi-step navigation paths for one-action-per-iteration execution.

Store a sequence of actions (typically BACK actions) to execute one per iteration,
enabling multi-hop navigation to reach specific states. Three planning strategies
fill the buffer with different goals:

1. Strategy A (Backtrack): Navigate to nearest unsaturated ancestor via BACK actions
2. Strategy B (MOP): Navigate to activity with monitored operations via WTG BFS
3. Strategy C (Coverage): Navigate to ancestor with highest exploration potential

The buffer is consumed one action per iteration by the strategy's select_next_action
(Tier 1 in the 5-tier selection). If navigation doesn't work as expected (screen
unchanged after a buffered action), learn_node invalidates the buffer to prevent
executing stale actions.

### Architectural Decisions:

- One-action-per-iteration dispensing: the buffer stores the full path but only
  emits one action per call to get_next_action, allowing learn_node to detect
  unexpected state changes between hops and invalidate stale paths
- Eager invalidation: any evidence that navigation diverged from the plan
  (unchanged screen hash, failed coordinate resolution) clears the entire buffer
  rather than attempting partial recovery

### Role in the System:

- Tier 1 in the 5-tier action selection of RVAgentStrategy: when the buffer has
  pending actions, the strategy unconditionally dispenses from the buffer
- Tier 3 (proactive backtrack) fills the buffer using plan_coverage_path (C),
  plan_mop_path (B), or plan_backtrack_path (A) in priority order
- learn_node and algorithm_node call invalidate methods when navigation fails

### Integration Points:

- Input: SuccessorTracker (backtrack BFS), TransitionManager (WTG path planning),
  UICoverageTracker (coverage scoring)
- Output: ItemAction objects dispensed to RVAgentStrategy.select_next_action
- Tracking: emits RVTRACK:BACKTRACK and RVTRACK:COVERAGE events via tracking module
"""

import logging
from collections import deque
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from rv_agent import tracking as track
from rv_android_core.domain.widget import WidgetEventType
from rv_screen_parser.parser.screen.visitor.model import ItemAction

if TYPE_CHECKING:
    from rv_agent.config.agent_config import RVAgentConfig
    from rv_agent.memory.ui_coverage import UICoverageTracker
    from rv_agent.services.transition_manager import TransitionManager
    from rv_agent.strategies.rvagent_strategy.successor_tracker import SuccessorTracker

logger = logging.getLogger(__name__)

# === PATH BUFFER CONSTANTS ===
PATH_BUFFER_ENABLED = True
MAX_BACKTRACK_HOPS = 8
MAX_COVERAGE_HOPS = 5

# After a resolution failure (WTG action with no coords), skip planning for
# this many iterations to prevent Tier 3 from re-planning the same failed path.
PLAN_COOLDOWN_AFTER_FAILURE = 3

# Mirrors RVAgentStrategy.BACK_ACTION_ID to produce identical BACK actions
BACK_ACTION_ID = 999


class PathBuffer:
    """
    Buffer and dispense multi-step navigation actions one per iteration.

    Store a sequence of ItemAction objects and dispense them one at a time
    via get_next_action(). When the buffer is exhausted, return None so
    the strategy falls back to normal action selection (Tier 2+).

    ### Key Features:

    - Three planning strategies (A/B/C) fill the buffer with different goals
    - One-action-per-iteration dispensing allows mid-path invalidation
    - Eager invalidation clears entire buffer on navigation failure

    ### Integration Points:

    - Input: plan_*() methods called by RVAgentStrategy (Tier 3)
    - Output: get_next_action() called by RVAgentStrategy (Tier 1)
    - Invalidation: invalidate() from learn_node, invalidate_current_path()
      from algorithm_node
    """

    def __init__(
        self,
        transition_manager: Optional["TransitionManager"],
        successor_tracker: "SuccessorTracker",
        ui_coverage_tracker: "UICoverageTracker",
        config: "RVAgentConfig",
    ):
        """
        Initialize PathBuffer.

        Args:
            transition_manager: TransitionManager for WTG-based path planning.
                Can be None if no static analysis data is available.
            successor_tracker: SuccessorTracker for backtrack BFS.
            ui_coverage_tracker: UICoverageTracker for coverage-based planning.
            config: RVAgentConfig with calibration parameters.

        State:
            self._buffer: Ordered list of ItemAction to dispense. Filled by
                plan_*() methods, consumed by get_next_action(), cleared by
                invalidate(). Empty when no buffered navigation is active.
        """
        self.transition_manager = transition_manager
        self.successor_tracker = successor_tracker
        self.ui_coverage_tracker = ui_coverage_tracker
        self.config = config
        self._buffer: List[ItemAction] = []
        self._plan_cooldown: int = 0
        # Activities where MOP path planning failed, mapped to the iteration
        # number when failure occurred. After PLAN_COOLDOWN_AFTER_FAILURE
        # iterations, the entry expires and re-planning is allowed.
        self._mop_path_cooldown: Dict[str, int] = {}

        logger.info(
            f"PathBuffer initialized: "
            f"transition_manager={'enabled' if transition_manager else 'disabled'}, "
            f"max_backtrack_hops={MAX_BACKTRACK_HOPS}, "
            f"max_coverage_hops={MAX_COVERAGE_HOPS}"
        )

    def get_next_action(self) -> Optional[ItemAction]:
        """
        Pop and return the next action from the buffer.

        Returns:
            Next ItemAction from buffer, or None if buffer is empty.
        """
        if not self._buffer:
            return None

        action = self._buffer.pop(0)
        remaining = self.remaining_steps
        logger.debug(f"PathBuffer: dispensing action ({remaining} remaining)")

        # Track buffer completion when last action is dispensed
        if remaining == 0:
            track.path_buffer_completed()

        return action

    def plan_backtrack_path(self, current_hash: str) -> bool:
        """
        Plan a backtrack path to the nearest unsaturated ancestor state.

        Uses SuccessorTracker.find_nearest_unsaturated() to find the target,
        then fills the buffer with the appropriate number of BACK actions.

        Args:
            current_hash: Current state hash to start backtrack from.

        Returns:
            True if a path was planned and buffer filled, False otherwise.
        """
        result = self.successor_tracker.find_nearest_unsaturated(current_hash)
        if result is None:
            logger.debug("PathBuffer: No unsaturated ancestor found for backtrack")
            return False

        target_hash, hop_count = result

        if hop_count > MAX_BACKTRACK_HOPS:
            logger.info(
                f"PathBuffer: Backtrack path too long ({hop_count} hops > "
                f"max {MAX_BACKTRACK_HOPS}), skipping"
            )
            return False

        # Fill buffer with BACK actions
        self._buffer = [_create_back_action() for _ in range(hop_count)]
        track.path_buffer_planned("A")
        track.backtrack(
            iter=0, strategy="A", remaining_steps=hop_count, target_hash=target_hash
        )

        logger.info(
            f"PathBuffer: Planned backtrack path to {target_hash[:8]}... "
            f"({hop_count} BACK actions)"
        )
        return True

    def plan_mop_path(
        self,
        current_activity: Optional[str],
        mop_data,
        possible_actions=None,
        current_iteration: int = 0,
    ) -> bool:
        """
        Plan a path to an activity with monitored operations.

        Uses TransitionManager.plan_path_to_mop_activity() if available to
        find a path from the current activity to one with MOP methods.

        Args:
            current_activity: Current runtime activity name.
            mop_data: MOP/static analysis data for scoring activities.
            possible_actions: Current screen's ItemAction list for coordinate
                resolution of WTG transitions.
            current_iteration: Current exploration iteration number, used for
                cooldown tracking after resolution failures.

        Returns:
            True if a path was planned and buffer filled, False otherwise.
        """
        if not self.transition_manager:
            return False

        if not current_activity:
            return False

        # Skip activities still in cooldown after a previous planning failure
        cooldown_iter = self._mop_path_cooldown.get(current_activity)
        if cooldown_iter is not None:
            remaining = PLAN_COOLDOWN_AFTER_FAILURE - (
                current_iteration - cooldown_iter
            )
            if remaining > 0:
                track.mop_resolve(
                    iter=current_iteration,
                    target_activity=current_activity,
                    resolved=False,
                    cooldown_remaining=remaining,
                    step=0,
                )
                logger.debug(
                    f"PathBuffer: Skipping MOP path for {current_activity} "
                    f"(cooldown: {remaining} iterations remaining)"
                )
                return False
            else:
                # Cooldown expired, allow re-planning
                del self._mop_path_cooldown[current_activity]

        # Use plan_path_to_mop_activity if available on TransitionManager
        plan_method = getattr(
            self.transition_manager, "plan_path_to_mop_activity", None
        )
        if plan_method is None:
            return False

        action_dicts = plan_method(
            current_activity, mop_data, possible_actions=possible_actions
        )
        if not action_dicts:
            # Record cooldown for this activity to prevent immediate re-planning
            self._mop_path_cooldown[current_activity] = current_iteration
            track.mop_resolve(
                iter=current_iteration,
                target_activity=current_activity,
                resolved=False,
                cooldown_remaining=PLAN_COOLDOWN_AFTER_FAILURE,
                step=1,
            )
            logger.info(
                f"PathBuffer: MOP path from {current_activity} unresolvable, "
                f"cooldown={PLAN_COOLDOWN_AFTER_FAILURE} iterations"
            )
            return False

        # Convert action dicts to ItemAction objects
        actions = []
        for action_dict in action_dicts:
            action = _action_dict_to_item_action(action_dict)
            if action:
                actions.append(action)

        if not actions:
            return False

        self._buffer = actions
        track.path_buffer_planned("B")
        track.mop_resolve(
            iter=current_iteration,
            target_activity=current_activity,
            resolved=True,
            cooldown_remaining=0,
            step=1,
        )
        track.backtrack(
            iter=current_iteration,
            strategy="B",
            remaining_steps=len(actions),
            target_hash=None,
        )
        logger.info(f"PathBuffer: Planned MOP path ({len(actions)} actions)")
        return True

    def plan_coverage_path(self, current_hash: str) -> bool:
        """
        Plan a path to the ancestor state with highest exploration potential.

        BFS on SuccessorTracker's back_successors to find reachable ancestor
        states within MAX_COVERAGE_HOPS. Each reachable state is scored by
        exploration_potential = coverage_gap * element_count. The state with
        the highest potential is selected and the buffer is filled with BACK
        actions to reach it.

        Returns False during cold start (< 3 screens in graph) or when no
        reachable state has exploration_potential > 0.

        Args:
            current_hash: Current state hash to start search from.

        Returns:
            True if a path was planned and buffer filled, False otherwise.
        """
        # Cold start guard: need at least 3 screens for meaningful coverage decisions
        if len(self.successor_tracker.graph.states) < 3:
            return False

        # BFS on back_successors, limited to MAX_COVERAGE_HOPS
        best_target: Optional[str] = None
        best_potential: float = 0.0
        best_hops: int = 0

        visited = {current_hash}
        queue: deque[Tuple[str, int]] = deque([(current_hash, 0)])

        while queue:
            state_hash, depth = queue.popleft()

            for back_target in self.successor_tracker.back_successors.get(
                state_hash, []
            ):
                if back_target in visited:
                    continue

                visited.add(back_target)
                hop_count = depth + 1

                # Score this ancestor by exploration potential
                gap = self.ui_coverage_tracker.get_coverage_gap(back_target)
                count = self.ui_coverage_tracker.get_element_count(back_target)
                potential = gap * count

                if potential > best_potential:
                    best_potential = potential
                    best_target = back_target
                    best_hops = hop_count

                # Continue BFS up to MAX_COVERAGE_HOPS
                if hop_count < MAX_COVERAGE_HOPS:
                    queue.append((back_target, hop_count))

        if best_target is None or best_potential <= 0:
            return False

        # Fill buffer with BACK actions
        self._buffer = [_create_back_action() for _ in range(best_hops)]
        track.path_buffer_planned("C")
        track.coverage_navigation(
            iter=0,
            target_hash=best_target,
            exploration_potential=best_potential,
            hops=best_hops,
        )

        logger.info(
            f"PathBuffer: Planned coverage path to {best_target[:8]}... "
            f"({best_hops} BACK actions, potential={best_potential:.1f})"
        )
        return True

    def invalidate_current_path(self) -> None:
        """
        Invalidate the current buffered path due to action resolution failure.

        Called by algorithm_node when a buffered action cannot be resolved to
        coordinates (e.g., WTG-level "Navigate to..." actions with no real UI
        widget). Clears the entire buffer and activates a cooldown that prevents
        Tier 3 from re-planning the same failed path immediately (D8).
        """
        if self._buffer:
            count = len(self._buffer)
            self._buffer.clear()
            self._plan_cooldown = PLAN_COOLDOWN_AFTER_FAILURE
            track.backtrack(
                iter=0,
                strategy="invalidate_failed",
                remaining_steps=count,
                target_hash=None,
            )
            logger.warning(
                f"PathBuffer: Invalidated current path due to resolution failure "
                f"({count} actions discarded, cooldown={self._plan_cooldown})"
            )

    def invalidate(self) -> None:
        """
        Clear the buffer, discarding all planned actions.

        Called by learn_node when navigation didn't work as expected
        (e.g., screen hash unchanged after executing a buffered action).
        """
        if self._buffer:
            count = len(self._buffer)
            self._buffer.clear()
            track.backtrack(
                iter=0, strategy="invalidate", remaining_steps=count, target_hash=None
            )
            logger.warning(f"PathBuffer: Invalidated ({count} actions discarded)")

    def load_back_actions(self, count: int) -> None:
        """Load multiple BACK actions into the buffer for multi-hop navigation.

        Used by Level 2 stuck recovery (BFS) to navigate to an unsaturated
        ancestor state in N iterations instead of N*max_blocks.

        Args:
            count: Number of BACK actions to queue.
        """
        self._buffer = [_create_back_action() for _ in range(count)]
        logger.info(f"PathBuffer: Loaded {count} BACK actions for stuck recovery")

    @property
    def is_cooling_down(self) -> bool:
        """Whether planning is blocked by a post-failure cooldown.

        After invalidate_current_path() (resolution failure), planning is
        blocked for PLAN_COOLDOWN_AFTER_FAILURE iterations so that Tier 3
        does not re-plan the same failed WTG path. The cooldown decrements
        each time this property is checked, so it auto-expires.
        """
        if self._plan_cooldown > 0:
            self._plan_cooldown -= 1
            return True
        return False

    @property
    def is_active(self) -> bool:
        """Whether the buffer has pending actions."""
        return len(self._buffer) > 0

    @property
    def remaining_steps(self) -> int:
        """Number of actions remaining in the buffer."""
        return len(self._buffer)


def _create_back_action() -> ItemAction:
    """
    Create a BACK navigation action.

    Mirrors RVAgentStrategy._create_back_action() to produce identical
    BACK actions for buffered navigation.

    Returns:
        ItemAction configured as BACK navigation action.
    """
    return ItemAction(
        id=BACK_ACTION_ID,
        text="BACK",
        event=WidgetEventType.BACK,
        reaches_target=False,
        directly_reaches_target=False,
        target_view={"system_action": True, "class": "SystemAction_BACK"},
        coordinates=None,
        text_input=None,
    )


def _action_dict_to_item_action(action_dict: dict) -> Optional[ItemAction]:
    """
    Convert an action dict (from TransitionManager) to an ItemAction.

    Args:
        action_dict: Dictionary with action information. Expected keys:
            - action_type: "BACK" or event type string
            - coordinates: Optional (x, y) tuple
            - widget_id: Optional widget identifier
            - text: Optional descriptive text

    Returns:
        ItemAction or None if conversion fails.
    """
    try:
        action_type = action_dict.get("action_type", "BACK")

        if action_type == "BACK":
            return _create_back_action()

        # Reject non-BACK actions with no coordinates — they will fail
        # coordinate resolution downstream and waste iterations.
        coords = action_dict.get("coordinates")
        if coords is None:
            logger.warning(
                f"PathBuffer: Rejecting action with no coordinates: "
                f"{action_dict.get('text', 'unknown')}"
            )
            return None

        # For non-BACK actions, create from dict
        return ItemAction(
            id=action_dict.get("action_id", 0),
            text=action_dict.get("text", ""),
            event=WidgetEventType.CLICK,
            reaches_target=action_dict.get("reaches_target", False),
            directly_reaches_target=action_dict.get("directly_reaches_target", False),
            target_view=action_dict.get("target_view", {}),
            coordinates=coords,
            text_input=None,
        )
    except Exception as e:
        logger.warning(f"PathBuffer: Failed to convert action dict: {e}")
        return None
