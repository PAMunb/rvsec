"""
Learn node for RVAgent workflow.

Updates memory systems, detects stuck states, and manages recovery strategies.

Key Design Decisions:

1. STUCK STATE DETECTION (Two-Level)
   Level 1 - Screen unchanged: After STUCK_THRESHOLD unchanged screens, force BACK.
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

logger = logging.getLogger(__name__)


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
    logger.info("LEARN: Updating memories")

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
    is_form_action = action_type in ("SET_TEXT", "TEXT_CHANGE") or is_checkable
    if current_hash == agent.last_screen_hash and not is_form_action:
        agent.stuck_screen_count += 1
        logger.debug(f"Screen unchanged: {agent.stuck_screen_count}/{agent.STUCK_THRESHOLD}")

        if agent.stuck_screen_count >= agent.STUCK_THRESHOLD:
            logger.warning(
                f"Level 1 stuck: screen unchanged "
                f"{stuck_count_before}->{agent.stuck_screen_count} iterations -> Forcing BACK"
            )
            force_back = True
            agent.stuck_screen_count = 0
    else:
        if stuck_count_before > 0:
            logger.debug(
                f"Screen changed, resetting stuck counter "
                f"(was {stuck_count_before}, hash: {agent.last_screen_hash[:12] if agent.last_screen_hash else 'None'}... -> {current_hash[:12]}...)"
            )
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
                else:
                    logger.warning(
                        f"Level 2 stuck: No unsaturated ancestor found -> Forcing RESTART"
                    )
                    force_restart = True
                    stuck_recovery.record_restart()
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

    # INSTRUMENTATION: Record exploration metrics for validation
    # This block can be removed for production
    if agent.metrics_collector:
        try:
            current_action = state.get("current_action", {})
            action_type = current_action.get("action_type", "UNKNOWN") if current_action else "NONE"
            action_source = current_action.get("source", "unknown") if current_action else "none"

            agent.metrics_collector.record_exploration(
                iteration=state.get("iteration", 0),
                activity=state.get("current_activity", "unknown"),
                screen_hash=state.get("current_screen_hash", "unknown"),
                action_type=action_type,
                action_source=action_source,
            )
            logger.debug("INSTRUMENTATION: Recorded exploration metrics")
        except Exception as e:
            logger.warning(f"INSTRUMENTATION: Failed to record exploration metrics: {e}")
    # END INSTRUMENTATION

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
