"""
Learn node for RVAgent workflow.

Updates memory systems, detects stuck states, and manages recovery strategies.

Key Design Decisions:

1. STUCK STATE DETECTION (Two-Level)
   Level 1 - Screen unchanged: After dynamic threshold of unchanged screens, force BACK.
             Threshold = max(BASE_STUCK_THRESHOLD, num_elements * STUCK_THRESHOLD_FACTOR)
             Form actions (SET_TEXT, checkable elements) are excluded from counting.
   Level 2 - StuckRecovery: After max_blocks iterations in same state, try:
     a) Backtrack BFS: Find nearest unsaturated ancestor state
     b) App Restart: Force stop and relaunch if BFS fails

2. BACKTRACK BFS (from APE paper)
   When Level 2 stuck is detected, uses SuccessorTracker.find_nearest_unsaturated()
   to find an ancestor state with unexplored actions. If found, navigates there
   via BACK. If no unsaturated ancestor exists, triggers app restart.

3. BACK TRANSITION RECORDING
   Records where BACK leads from each state. This builds a navigation graph
   that Backtrack BFS uses to find paths to unsaturated ancestors.

4. INTERACTION WITH ALGORITHM_NODE
   - force_back_action=True: Generates BACK action
   - force_restart_app=True: Generates RESTART_APP action
   This maintains separation between detection (learn_node) and action generation.

5. UI COVERAGE TRACKING
   Records which elements were interacted with for coverage metrics.
   Uses proximity matching because LLM clicks may not be exactly at element centers.
"""

import logging
from typing import TYPE_CHECKING, Dict, Any, Optional

if TYPE_CHECKING:
    from rv_agent.agent.rv_agent import RVAgent

from rv_agent.domain.state import AgentState
from rv_agent import tracking as track

logger = logging.getLogger(__name__)


def _get_dynamic_stuck_threshold(agent: "RVAgent", state: AgentState) -> int:
    """
    Calculate stuck threshold based on screen complexity.

    More elements on screen = more iterations allowed before forcing BACK.
    This prevents premature backtracking on complex screens.

    Args:
        agent: RVAgent instance with BASE_STUCK_THRESHOLD and STUCK_THRESHOLD_FACTOR
        state: Current agent state with available_actions

    Returns:
        Dynamic threshold: max(base, num_elements * factor)
    """
    base = getattr(agent, 'BASE_STUCK_THRESHOLD', 8)
    factor = getattr(agent, 'STUCK_THRESHOLD_FACTOR', 1.5)

    # Get number of available actions (interactive elements)
    available_actions = state.get("available_actions", [])
    num_elements = len(available_actions)

    # Calculate dynamic threshold
    dynamic_threshold = max(base, int(num_elements * factor))

    return dynamic_threshold


def learn_node(agent: "RVAgent", state: AgentState) -> Dict[str, Any]:
    """
    Update memory systems and prepare for next iteration.

    Handles memory updates, summary generation, state tracking,
    stuck state detection, and continuation checks.

    Args:
        agent: RVAgent instance with memory_coordinator and stuck detection
        state: Current agent state

    Returns:
        State updates with memories, summaries, and continuation flags
    """
    iteration = state.get("iteration", 0)

    # Update memories
    memory_result = agent.memory_coordinator.update_memories(
        current_screen_hash=state.get("current_screen_hash", "unknown"),
        current_activity=state.get("current_activity", "unknown"),
        screen_description=state.get("screen_description"),
        action=state.get("current_action"),
        llm_reasoning=state.get("llm_reasoning", ""),
        iteration=state.get("iteration", 0),
        recent_action_window=state.get("recent_action_window", [])
    )

    # Generate summaries
    summaries = agent.memory_coordinator.generate_summaries(
        action=state.get("current_action"),
        current_activity=state.get("current_activity", "unknown"),
        visited_states=state.get("visited_states", []),
        state_transitions=state.get("state_transitions", [])
    )

    # Track state discovery
    tracking = agent.memory_coordinator.track_state_discovery(
        current_hash=state.get("current_screen_hash"),
        previous_hash=state.get("previous_screen_hash"),
        visited_states=state.get("visited_states", []),
        state_transitions=state.get("state_transitions", [])
    )

    # Record BACK transitions for Backtrack BFS
    _record_back_transition(agent, state)

    # Record action success for strength-based scoring
    _record_action_success(agent, state)

    # Two-level stuck state detection
    current_hash = state.get("current_screen_hash")
    force_back = False
    force_restart = False
    stuck_count_before = agent.stuck_screen_count

    # Get current action info for stuck detection logic
    current_action = state.get("current_action", {})
    action_type = (current_action.get("action_type", "") if current_action else "").upper()

    # Check if action was on a checkable element (checkbox, radio, toggle)
    item_action = state.get("current_item_action")
    is_checkable = False
    if item_action and hasattr(item_action, 'target_view'):
        is_checkable = item_action.target_view.get("checkable", False)

    # Level 1: Screen unchanged detection (quick recovery via BACK)
    # Skip stuck counting for actions that don't change screen hash:
    # - SET_TEXT: filling form fields
    # - Checkable elements: checkbox/radio/toggle state changes
    #
    # Dynamic threshold: more elements = more iterations allowed
    # threshold = max(BASE_STUCK_THRESHOLD, num_elements * STUCK_THRESHOLD_FACTOR)
    dynamic_threshold = _get_dynamic_stuck_threshold(agent, state)

    is_form_action = action_type in ("SET_TEXT", "TEXT_CHANGE") or is_checkable
    if current_hash == agent.last_screen_hash and not is_form_action:
        agent.stuck_screen_count += 1
        if agent.stuck_screen_count >= dynamic_threshold:
            force_back = True
            agent.stuck_screen_count = 0
    else:
        agent.stuck_screen_count = 0

    agent.last_screen_hash = current_hash

    # Level 2: StuckRecovery check (persistent stuck state)
    stuck_recovery = getattr(agent, 'stuck_recovery', None)
    if stuck_recovery and current_hash:
        recovery_action = stuck_recovery.check(current_hash)

        if recovery_action == "restart":
            # Try Backtrack BFS first
            successor_tracker = getattr(agent.strategy, 'successor_tracker', None)
            if successor_tracker:
                unsaturated_target = successor_tracker.find_nearest_unsaturated(current_hash)
                if unsaturated_target:
                    logger.info(
                        f"Level 2 stuck: Backtrack BFS found unsaturated state "
                        f"{unsaturated_target[:8]}... -> Forcing BACK"
                    )
                    force_back = True
                    # Track backtrack decision
                    track.backtrack(
                        iter=iteration,
                        from_state=current_hash,
                        to_state=unsaturated_target,
                        reason="bfs_unsaturated"
                    )
                else:
                    logger.warning(
                        f"Level 2 stuck: No unsaturated ancestor found -> Forcing RESTART"
                    )
                    force_restart = True
                    stuck_recovery.record_restart()
                    # Track backtrack failure
                    track.backtrack(
                        iter=iteration,
                        from_state=current_hash,
                        to_state="restart",
                        reason="no_unsaturated"
                    )
            else:
                logger.warning(
                    f"Level 2 stuck: No successor_tracker available -> Forcing RESTART"
                )
                force_restart = True
                stuck_recovery.record_restart()

    # Check continuation
    continuation = agent.memory_coordinator.check_continuation(
        start_time=state.get("start_time"),
        timeout=state.get("timeout")
    )

    # Track state changes
    previous_activity = state.get("previous_activity")
    current_activity = state.get("current_activity")
    activity_changed = previous_activity != current_activity and previous_activity is not None

    track.state(
        iter=iteration,
        changed=activity_changed,
        activity_from=previous_activity,
        activity_to=current_activity,
        hash=current_hash
    )

    # Track learning/stuck detection
    stuck_reason = None
    if force_restart:
        stuck_reason = "level2_restart"
    elif force_back:
        stuck_reason = "level1_back"

    track.learn(
        iter=iteration,
        stuck=force_back or force_restart,
        memory_updated=True,
        stuck_reason=stuck_reason
    )

    result = {
        "recent_action_window": memory_result["recent_action_window"],
        "action_history_summary": summaries["action_history_summary"],
        "exploration_summary": summaries["exploration_summary"],
        "memory_insights": summaries["memory_insights"],
        "navigation_path": summaries["navigation_path"],
        "visited_states": tracking["visited_states"],
        "state_transitions": tracking["state_transitions"],
        "previous_screen_hash": state.get("current_screen_hash"),
        "should_continue": continuation["should_continue"],
        "loop_detected": False
    }

    if force_restart:
        result["force_restart_app"] = True
    elif force_back:
        result["force_back_action"] = True

    # NOTE: UI coverage interaction is recorded in execute_node.py
    # using device-space coordinates (not normalized [0,1000))

    return result


def _record_back_transition(agent: "RVAgent", state: AgentState) -> None:
    """
    Record BACK transitions for Backtrack BFS navigation.

    When a BACK action is executed and the screen changes, records the
    transition in SuccessorTracker.back_successors. This builds a graph
    of where BACK leads from each state.

    Args:
        agent: RVAgent instance with strategy.successor_tracker
        state: Current agent state with action and hash information
    """
    try:
        current_action = state.get("current_action")
        if not current_action:
            return

        action_type = current_action.get("action_type", "").upper()
        if action_type != "BACK":
            return

        previous_hash = state.get("previous_screen_hash")
        current_hash = state.get("current_screen_hash")

        if not previous_hash or not current_hash:
            return

        if previous_hash == current_hash:
            return

        successor_tracker = getattr(agent.strategy, 'successor_tracker', None)
        if successor_tracker:
            successor_tracker.record_back_transition(previous_hash, current_hash)
            logger.debug(
                f"Recorded BACK transition: {previous_hash[:8]}... -> {current_hash[:8]}..."
            )

    except Exception as e:
        logger.warning(f"Failed to record BACK transition: {e}")


def _record_action_success(agent: "RVAgent", state: AgentState) -> None:
    """
    Record action success/failure for strength-based scoring.

    Success Definition: An action is considered successful if it caused
    a state transition (screen hash changed after execution).

    TODO: This heuristic has limitations:
    - Actions that change internal state without changing UI are marked as failures
    - Actions that open transient dialogs may give false positives
    Future improvements could use additional signals (activity change, new elements).

    Args:
        agent: RVAgent instance with strategy and graph
        state: Current agent state with previous/current hashes and action info
    """
    try:
        previous_hash = state.get("previous_screen_hash")
        current_hash = state.get("current_screen_hash")
        current_action = state.get("current_action")
        iteration = state.get("iteration", 0)

        if not previous_hash or not current_hash or not current_action:
            return

        # Get action coordinates
        x = current_action.get("x")
        y = current_action.get("y")
        action_type = current_action.get("action_type", "CLICK")

        if x is None or y is None:
            return

        # Convert to optimized space (same as scorers)
        converter = getattr(agent.strategy, 'converter', None)
        if converter:
            opt_x, opt_y = converter.device_to_optimized(x, y)
        else:
            opt_x = int(x * 704 / 1080)
            opt_y = int(y * 1248 / 1920)

        action_signature = ((opt_x, opt_y), action_type)

        # Get the node where the action was executed (previous state)
        graph = getattr(agent.strategy, 'graph', None)
        if not graph:
            return

        node = graph.states.get(previous_hash)
        if not node:
            return

        # Success = state changed
        success = previous_hash != current_hash

        # Record success in node
        node.record_action_success(action_signature, success)

        # Track strength
        executions = node.get_action_execution_count(action_signature)
        successes = node.action_success_counts.get(action_signature, 0)
        strength_val = node.get_action_strength(action_signature)

        track.strength(
            iter=iteration,
            action=action_type,
            coords=(x, y),
            strength_val=strength_val,
            executions=executions,
            successes=successes
        )

        logger.debug(
            f"Action success recorded: {action_signature} "
            f"success={success} strength={strength_val:.2f}"
        )

    except Exception as e:
        logger.warning(f"Failed to record action success: {e}")
