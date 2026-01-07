"""
Algorithm node for RVAgent workflow.

Generates actions using the algorithmic exploration strategy.
"""

import logging
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from rv_agent.agent.rv_agent import RVAgent

from rv_agent.domain.state import AgentState

logger = logging.getLogger(__name__)


def algorithm_node(agent: "RVAgent", state: AgentState) -> Dict[str, Any]:
    """
    Generate action using algorithmic strategy.

    Handles stuck state recovery, deadlock detection, and delegates
    to the exploration strategy for action selection.

    Args:
        agent: RVAgent instance with strategy and counters
        state: Current agent state

    Returns:
        State updates with current_action and decision_maker
    """
    logger.info("ALGORITHM: Generating action")

    # Check for stuck state override - force BACK action
    if state.get("force_back_action", False):
        logger.warning("Forcing BACK action due to stuck state detection")
        action = {
            "action_type": "BACK",
            "x": 0,
            "y": 0,
            "text": "",
            "source": "algorithm",
            "reason": "stuck_state_recovery"
        }
        agent.consecutive_no_action = 0
        return {
            "current_action": action,
            "current_item_action": None,
            "decision_maker": "algorithm",
            "force_back_action": False
        }

    # Check for deadlock (consecutive iterations without action)
    if agent.consecutive_no_action >= agent.NO_ACTION_THRESHOLD:
        logger.error(
            f"DEADLOCK DETECTED: {agent.consecutive_no_action} iterations "
            f"without action -> forcing BACK to escape"
        )
        action = {
            "action_type": "BACK",
            "x": 0,
            "y": 0,
            "text": "",
            "source": "algorithm",
            "reason": "deadlock_escape"
        }
        agent.consecutive_no_action = 0
        return {
            "current_action": action,
            "current_item_action": None,
            "decision_maker": "algorithm"
        }

    screen_hash = state.get("current_screen_hash")
    screen_desc = state.get("screen_description")

    item_action = agent.strategy.select_next_action(screen_hash, screen_desc)

    if not item_action:
        agent.consecutive_no_action += 1
        logger.warning(
            f"No action available from strategy "
            f"(consecutive_no_action={agent.consecutive_no_action}/{agent.NO_ACTION_THRESHOLD})"
        )
        return {
            "current_action": None,
            "decision_path": "end"
        }

    # Get coordinates from ItemAction
    coords = item_action.get_execution_coordinates()
    if not coords:
        logger.error("Failed to get coordinates from ItemAction")
        return {
            "current_action": None,
            "decision_path": "end"
        }

    x, y = coords

    # Convert ItemAction to unified action format
    action = {
        "action_type": item_action.action_type.upper(),
        "x": x,
        "y": y,
        "text": item_action.text or "",
        "source": "algorithm",
        "id": item_action.id
    }

    logger.info(f"Algorithm selected: {action['action_type']} at ({x}, {y})")

    # Reset deadlock counter on successful action
    agent.consecutive_no_action = 0

    return {
        "current_action": action,
        "current_item_action": item_action,
        "decision_maker": "algorithm"
    }
