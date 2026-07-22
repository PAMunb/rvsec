"""
Execute node for RVAgent workflow.

Executes actions on the device. All actions are expected to be in unified
format with coordinates already in device space (from ActionNormalizer).
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

    All actions are in unified format with device coordinates:
    - LLM actions: Normalized by ActionNormalizer.from_llm() in llm_node
    - Algorithm actions: Already in device space from strategy

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

    source = action.get("source", "unknown")
    action_type = action.get("action_type", "UNKNOWN")
    logger.debug(f"Executing {action_type} from {source}")

    result = agent.tool_executor.execute_action(action)

    # Record transition if action succeeded
    if result.get("success"):
        prev_hash = state.get("previous_screen_hash")
        current_hash = state.get("current_screen_hash", "")
        item_action = state.get("current_item_action")

        if prev_hash and item_action:
            agent.strategy.record_transition(prev_hash, current_hash, item_action)
            logger.debug(f"Recorded transition: {prev_hash[:8]} -> {current_hash[:8]}")

    executed_action = result.get("action_executed")

    return {
        "current_action": executed_action,
        "action_executed": executed_action,
        "action_success": result.get("success", False)
    }
