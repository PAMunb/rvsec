"""
Execute node for RVAgent workflow.

Executes actions on the device.
"""

import logging
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from rv_agent.agent.rv_agent import RVAgent

from rv_agent.domain.state import AgentState

logger = logging.getLogger(__name__)


def execute_node(agent: "RVAgent", state: AgentState) -> Dict[str, Any]:
    """
    Execute action on device.

    Handles coordinate conversion based on action source (LLM vs algorithm)
    and records transitions in the strategy.

    Args:
        agent: RVAgent instance with tool_executor and strategy
        state: Current agent state

    Returns:
        State updates with action_executed and success status
    """
    logger.info("EXECUTE: Executing action")

    action = state.get("current_action")

    if not action:
        logger.warning("No action to execute")
        return {"action_executed": None}

    # LLM actions use optimized image space (704x1248) and need conversion
    # Algorithm actions already use device space (1080x1920)
    decision_maker = state.get("decision_maker", "unknown")
    convert_coords = (decision_maker == "llm")

    logger.debug(f"Executing action from {decision_maker}, convert_coords={convert_coords}")

    result = agent.tool_executor.execute_action(action, convert_coordinates=convert_coords)

    # Record transition if action succeeded
    if result.get("success"):
        prev_hash = state.get("previous_screen_hash")
        current_hash = state.get("current_screen_hash", "")
        item_action = state.get("current_item_action")

        if prev_hash and item_action:
            agent.strategy.record_transition(prev_hash, current_hash, item_action)
            logger.debug(f"Recorded transition: {prev_hash[:8]} -> {current_hash[:8]}")

    normalized_action = result.get("action_executed")

    return {
        "current_action": normalized_action,
        "action_executed": normalized_action,
        "action_success": result.get("success", False)
    }
