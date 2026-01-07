"""
Validation node for RVAgent workflow.

Validates actions before execution. If action is invalid,
substitutes with BACK action instead of cycling to fallback.
"""

import logging
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from rv_agent.agent.rv_agent import RVAgent

from rv_agent.domain.state import AgentState

logger = logging.getLogger(__name__)


def validate_action_node(agent: "RVAgent", state: AgentState) -> Dict[str, Any]:
    """
    Validate action before execution.

    If action is invalid or loop is detected, substitutes with BACK action.
    Always proceeds to execute node (no fallback cycle).

    Args:
        agent: RVAgent instance with routing_manager
        state: Current agent state

    Returns:
        State updates with current_action and loop_detected
    """
    decision_maker = state.get("decision_maker", "unknown")
    logger.info(f"VALIDATE_ACTION: Validating action from {decision_maker}")

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

    return {
        "current_action": validation_result["current_action"],
        "loop_detected": validation_result["loop_detected"],
        "decision_maker": decision_maker
    }
