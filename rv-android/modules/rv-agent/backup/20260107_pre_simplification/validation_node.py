"""
Validation router node for RVAgent workflow.

Validates actions and routes to execution or fallback.
"""

import logging
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from rv_agent.agent.rv_agent import RVAgent

from rv_agent.domain.state import AgentState

logger = logging.getLogger(__name__)


def validation_router_node(agent: "RVAgent", state: AgentState) -> Dict[str, Any]:
    """
    Validate action (from LLM or Algorithm) and route to execution or fallback.

    Both LLM and Algorithm actions are validated using the same loop
    detection logic based on shared dynamic state graph.

    Args:
        agent: RVAgent instance with routing_manager
        state: Current agent state

    Returns:
        State updates with validation_path and loop detection status
    """
    decision_maker = state.get("decision_maker", "unknown")
    logger.info(f"VALIDATION_ROUTER: Validating action from {decision_maker}")

    # Get action from appropriate source
    if decision_maker == "llm":
        action = state.get("llm_action")
    else:
        action = state.get("current_action")

    recent_actions = state.get("recent_action_window", [])

    logger.debug(
        f"VALIDATION: decision_maker={decision_maker}, "
        f"recent_actions_count={len(recent_actions)}, "
        f"action_to_validate={action.get('action_type') if action else None}"
    )

    validation_result = agent.routing_manager.validate_action(
        action=action,
        recent_actions=recent_actions,
        decision_maker=decision_maker
    )

    if validation_result.get("current_action"):
        return {
            "current_action": validation_result["current_action"],
            "validation_path": validation_result["validation_path"],
            "loop_detected": validation_result["loop_detected"],
            "used_fallback": validation_result["used_fallback"],
            "decision_maker": decision_maker
        }
    else:
        return {
            "validation_path": validation_result["validation_path"],
            "loop_detected": validation_result["loop_detected"],
            "used_fallback": validation_result["used_fallback"]
        }
