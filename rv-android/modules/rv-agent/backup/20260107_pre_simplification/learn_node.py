"""
Learn node for RVAgent workflow.

Updates memory systems and detects stuck states.
"""

import logging
from typing import TYPE_CHECKING, Dict, Any

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

    # Stuck state detection
    current_hash = state.get("current_screen_hash")
    stuck_action_override = None
    stuck_count_before = agent.stuck_screen_count

    if current_hash == agent.last_screen_hash:
        agent.stuck_screen_count += 1
        logger.debug(f"Screen unchanged: {agent.stuck_screen_count}/{agent.STUCK_THRESHOLD}")

        if agent.stuck_screen_count >= agent.STUCK_THRESHOLD:
            logger.warning(
                f"Stuck state detected: screen unchanged "
                f"{stuck_count_before}->{agent.stuck_screen_count} iterations -> Forcing BACK"
            )
            stuck_action_override = {
                "action_type": "BACK",
                "reason": "stuck_state_recovery"
            }
            agent.stuck_screen_count = 0
    else:
        if stuck_count_before > 0:
            logger.debug(
                f"Screen changed, resetting stuck counter "
                f"(was {stuck_count_before}, hash: {agent.last_screen_hash[:12]}... -> {current_hash[:12]}...)"
            )
        agent.stuck_screen_count = 0

    agent.last_screen_hash = current_hash

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

    if stuck_action_override:
        result["force_back_action"] = True

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
