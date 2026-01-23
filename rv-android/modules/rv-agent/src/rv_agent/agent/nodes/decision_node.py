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

    Checks for forced recovery actions first:
    - force_restart_app: Routes to algorithm for RESTART_APP (Level 2 stuck)
    - force_back_action: Routes to algorithm for BACK (Level 1 stuck)

    Otherwise delegates to routing_manager for mode-based probabilistic routing.

    Args:
        agent: RVAgent instance with routing_manager
        state: Current agent state

    Returns:
        State updates with decision_path and decision_maker
    """
    logger.info("DEBUG_TRACE: decision_router_node ENTER")
    logger.info("DECISION_ROUTER: Routing decision")

    # Check for forced RESTART_APP action (Level 2 stuck - Backtrack BFS failed)
    force_restart = state.get("force_restart_app", False)
    if force_restart:
        logger.warning("force_restart_app=True -> Routing to algorithm for RESTART_APP")
        return {
            "decision_path": "algorithm",
            "decision_maker": "stuck_recovery"
        }

    # Check for forced BACK action (Level 1 stuck - screen unchanged)
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

    # [LLM_TRACE] Log routing decision
    logger.warning(f"[LLM_TRACE] === ROUTING DECISION (iter={iteration}) ===\n"
                  f"[LLM_TRACE] decision_path: {decision_path}\n"
                  f"[LLM_TRACE] === END ROUTING ===")

    return {
        "decision_path": decision_path,
        "decision_maker": decision_path
    }
