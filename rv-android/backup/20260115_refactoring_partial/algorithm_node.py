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

    # Check for restart override - force app restart
    force_restart = state.get("force_restart_action")
    if force_restart:
        logger.warning(
            f"Restart recovery: Generating RESTART_APP action "
            f"(restart_count={agent.routing_manager.restart_count})"
        )
        action = {
            "action_type": "RESTART_APP",
            "package_name": force_restart.get("package_name"),
            "x": 0,
            "y": 0,
            "text": "",
            "source": "stuck_recovery",
            "reason": force_restart.get("reason", "restart_recovery")
        }
        agent.consecutive_no_action = 0
        return {
            "current_action": action,
            "current_item_action": None,
            "decision_maker": "stuck_recovery",
            "force_restart_action": None
        }

    # Check for stuck state override - force BACK action
    if state.get("force_back_action", False):
        agent.routing_manager.forced_back_count += 1
        logger.warning(
            f"Stuck recovery: Generating BACK action "
            f"(forced_back_count={agent.routing_manager.forced_back_count})"
        )
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
            "decision_maker": "stuck_recovery",
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

    # System actions (BACK, HOME) don't require coordinates
    action_type = item_action.action_type.upper()
    if action_type in ("BACK", "HOME"):
        action = {
            "action_type": action_type,
            "x": 0,
            "y": 0,
            "text": "",
            "source": "algorithm",
            "id": item_action.id,
            "reason": "strategy_selected"
        }
        logger.info(f"Algorithm selected: {action_type} (system action)")
        agent.consecutive_no_action = 0
        return {
            "current_action": action,
            "current_item_action": item_action,
            "decision_maker": "algorithm"
        }

    # Get coordinates from ItemAction
    coords = item_action.get_execution_coordinates()
    if not coords:
        # If no coordinates available, use BACK as fallback
        logger.warning(
            f"No coordinates for {action_type}, using BACK as fallback"
        )
        action = {
            "action_type": "BACK",
            "x": 0,
            "y": 0,
            "text": "",
            "source": "algorithm",
            "id": item_action.id,
            "reason": "no_coordinates_fallback"
        }
        agent.consecutive_no_action = 0
        return {
            "current_action": action,
            "current_item_action": None,
            "decision_maker": "algorithm"
        }

    x, y = coords

    # Convert ItemAction to unified action format
    action = {
        "action_type": action_type,
        "x": x,
        "y": y,
        "text": item_action.text_input or item_action.text or "",
        "source": "algorithm",
        "id": item_action.id
    }

    # Add swipe coordinates for SCROLL actions
    if action_type == "SCROLL" and item_action.target_view:
        swipe_start = item_action.target_view.get("swipe_start")
        swipe_end = item_action.target_view.get("swipe_end")
        if swipe_start and swipe_end:
            action["swipe_start"] = swipe_start
            action["swipe_end"] = swipe_end
            action["direction"] = "down"  # Default for vertical scroll up (reveal below)

    logger.info(f"Algorithm selected: {action['action_type']} at ({x}, {y})")

    # Reset deadlock counter on successful action
    agent.consecutive_no_action = 0

    return {
        "current_action": action,
        "current_item_action": item_action,
        "decision_maker": "algorithm"
    }
