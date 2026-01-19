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

    Handles stuck state recovery (BACK and RESTART), deadlock detection,
    and delegates to the exploration strategy for action selection.

    Args:
        agent: RVAgent instance with strategy and counters
        state: Current agent state

    Returns:
        State updates with current_action and decision_maker
    """
    logger.info("ALGORITHM: Generating action")

    # Check for app restart override (Level 2 stuck recovery)
    if state.get("force_restart_app", False):
        logger.warning("Level 2 stuck recovery: Generating RESTART_APP action")
        action = {
            "action_type": "RESTART_APP",
            "x": 0,
            "y": 0,
            "text": "",
            "source": "algorithm",
            "reason": "level2_stuck_recovery",
            "package_name": agent.config.package_name
        }
        agent.consecutive_no_action = 0
        return {
            "current_action": action,
            "current_item_action": None,
            "decision_maker": "stuck_recovery",
            "force_restart_app": False
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

    # System actions don't require coordinates - they are triggered by action_type alone
    # KEY_EVENT is how BACK actions come through via WidgetEventType mapping
    action_type = item_action.action_type.upper()
    system_actions = {"BACK", "RESTART_APP", "KEY_EVENT"}

    if action_type in system_actions:
        logger.info(f"Algorithm selected system action: {action_type}")
        action = {
            "action_type": action_type,
            "x": 0,
            "y": 0,
            "text": item_action.text or "",
            "source": "algorithm",
            "id": item_action.id
        }
        agent.consecutive_no_action = 0
        return {
            "current_action": action,
            "current_item_action": item_action,
            "decision_maker": "algorithm"
        }

    # Get coordinates from ItemAction for regular actions
    coords = item_action.get_execution_coordinates()
    if not coords:
        logger.error(
            f"Failed to get coordinates from ItemAction: "
            f"type={action_type}, id={item_action.id}, text={item_action.text[:50] if item_action.text else 'None'}"
        )
        return {
            "current_action": None,
            "decision_path": "end"
        }

    x, y = coords

    # Convert ItemAction to unified action format
    # For SET_TEXT actions, use text_input (actual value to type) not text (description)
    if action_type == "SET_TEXT":
        text_value = item_action.text_input or ""
        if not text_value:
            logger.warning(f"SET_TEXT action has no text_input value, action will fail")
    else:
        text_value = item_action.text or ""

    action = {
        "action_type": action_type,
        "x": x,
        "y": y,
        "text": text_value,
        "source": "algorithm",
        "id": item_action.id
    }

    # Extract swipe/drag data from target_view if available
    # This is needed for SeekBar, ViewPager, and other drag-based interactions
    if item_action.target_view:
        if "swipe_start" in item_action.target_view:
            action["swipe_start"] = item_action.target_view["swipe_start"]
        if "swipe_end" in item_action.target_view:
            action["swipe_end"] = item_action.target_view["swipe_end"]
        if "direction" in item_action.target_view:
            action["direction"] = item_action.target_view["direction"]

    logger.info(f"Algorithm selected: {action_type} at ({x}, {y})" + (f" text='{text_value[:20]}'" if text_value else ""))

    # Reset deadlock counter on successful action
    agent.consecutive_no_action = 0

    return {
        "current_action": action,
        "current_item_action": item_action,
        "decision_maker": "algorithm"
    }
