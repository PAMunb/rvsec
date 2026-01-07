"""
Decision router node for RVAgent workflow.

Routes decisions between LLM and algorithm paths based on mode and state.
"""

import logging
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from rv_agent.agent.rv_agent import RVAgent

from rv_agent.domain.state import AgentState

logger = logging.getLogger(__name__)


def decision_router_node(agent: "RVAgent", state: AgentState) -> Dict[str, Any]:
    """
    Route decision between LLM and algorithm paths.

    Checks for forced BACK action from stuck state detection, then
    delegates to routing_manager for mode-based decision.

    Args:
        agent: RVAgent instance with routing_manager
        state: Current agent state

    Returns:
        State updates with decision_path and decision_maker
    """
    logger.info("DECISION_ROUTER: Routing decision")

    force_back = state.get("force_back_action", False)
    logger.debug(f"force_back_action = {force_back}")

    # Check for forced BACK action BEFORE routing
    # Stuck state detection sets force_back_action=True to force BACK via algorithm
    if force_back:
        agent.routing_manager.forced_back_count += 1
        current_hash = state.get("current_screen_hash", "UNKNOWN")
        iteration = state.get("iteration", 0)
        logger.warning("force_back_action=True -> Forcing algorithm path for BACK")
        logger.warning(
            f"[AUXILIARY_COUNTER] forced_back++ (now={agent.routing_manager.forced_back_count}) | "
            f"iteration={iteration} | screen_hash={current_hash[:12]}... | "
            f"stuck_count_was={agent.stuck_screen_count} | threshold={agent.STUCK_THRESHOLD} | "
            f"llm_exec={agent.routing_manager.llm_executed} | "
            f"alg_chosen={agent.routing_manager.algorithm_chosen}"
        )
        return {
            "decision_path": "algorithm",
            "decision_maker": "algorithm"
        }

    iteration = state.get("iteration", 0)
    decision_path = agent.routing_manager.route_decision(iteration)

    return {
        "decision_path": decision_path,
        "decision_maker": decision_path
    }
