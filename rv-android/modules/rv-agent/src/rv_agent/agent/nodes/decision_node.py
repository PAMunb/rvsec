"""
Decision router node for RVAgent workflow.

Routes decisions between LLM and algorithm paths based on mode and state.
"""

import logging
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from rv_agent.agent.rv_agent import RVAgent

from rv_agent.domain.state import AgentState
from rv_agent import tracking as track

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
    iteration = state.get("iteration", 0)
    mode = agent.routing_manager.mode

    # Check for forced RESTART_APP action (Level 2 stuck - Backtrack BFS failed)
    if state.get("force_restart_app", False):
        track.route(iter=iteration, mode=mode, path="algorithm(restart)")
        return {"decision_path": "algorithm", "decision_maker": "stuck_recovery"}

    # Check for forced BACK action (Level 1 stuck - screen unchanged)
    if state.get("force_back_action", False):
        agent.routing_manager.forced_back_count += 1
        track.route(iter=iteration, mode=mode, path="algorithm(back)")
        return {"decision_path": "algorithm", "decision_maker": "stuck_recovery"}

    # Check for error recovery: bypass LLM and route to algorithm for input filling
    if state.get("force_fill_input", False):
        track.route(iter=iteration, mode=mode, path="algorithm(error_recovery)")
        return {"decision_path": "algorithm", "decision_maker": "error_recovery"}

    decision_path = agent.routing_manager.route_decision(iteration)
    track.route(iter=iteration, mode=mode, path=decision_path)

    if decision_path == "algorithm":
        track.strategy(
            iter=iteration,
            mode=mode,
            action_type="algorithm",
            reason="routing_decision",
        )

    return {"decision_path": decision_path, "decision_maker": decision_path}
