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

    When force_back_action is set (stuck detection), routes to algorithm
    path which will generate a BACK action. Otherwise delegates to
    routing_manager for mode-based probabilistic routing.

    Args:
        agent: RVAgent instance with routing_manager
        state: Current agent state

    Returns:
        State updates with decision_path and decision_maker
    """
    logger.info("DECISION_ROUTER: Routing decision")

    # Check for forced BACK action from stuck detection
    # Routes to algorithm path which handles BACK generation
    force_back = state.get("force_back_action", False)
    if force_back:
        logger.warning("force_back_action=True -> Routing to algorithm for BACK")
        agent.routing_manager.forced_back_count += 1
        return {
            "decision_path": "algorithm",
            "decision_maker": "stuck_recovery"
        }

    iteration = state.get("iteration", 0)
    decision_path = agent.routing_manager.route_decision(iteration)

    return {
        "decision_path": decision_path,
        "decision_maker": decision_path
    }
