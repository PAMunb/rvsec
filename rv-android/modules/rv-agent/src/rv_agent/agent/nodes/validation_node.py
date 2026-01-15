"""
Validation node for RVAgent workflow.

Validates actions before execution. If action is invalid,
substitutes with BACK action instead of cycling to fallback.
"""

import logging
from typing import TYPE_CHECKING, Dict, Any, Tuple

if TYPE_CHECKING:
    from rv_agent.agent.rv_agent import RVAgent

from rv_agent.domain.state import AgentState

logger = logging.getLogger(__name__)

# Screen boundary thresholds (percentage of screen height)
STATUSBAR_Y_PERCENT = 0.05   # Top 5% is status bar
NAVBAR_Y_PERCENT = 0.94      # Bottom 6% is navigation bar


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

    # Check screen boundary for LLM actions (prevent clicking outside app area)
    if decision_maker == "llm" and action:
        device_dims = getattr(agent.screen_processor, 'device_dimensions', (1080, 1920))
        is_outside, reason = _is_outside_app_boundary(action, device_dims)
        if is_outside:
            logger.warning(f"LLM action outside app boundary: {reason} -> executing BACK")
            return {
                "current_action": _create_back_action(f"boundary_violation_{reason}"),
                "loop_detected": True,
                "decision_maker": decision_maker
            }

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


def _is_outside_app_boundary(
    action: Dict[str, Any],
    device_dims: Tuple[int, int]
) -> Tuple[bool, str]:
    """
    Check if action coordinates are outside the app's usable area.

    This prevents LLM from clicking on:
    - Status bar (top ~5% of screen)
    - Navigation bar (bottom ~6% of screen)

    Args:
        action: Action dictionary with x, y coordinates
        device_dims: Device dimensions (width, height)

    Returns:
        Tuple of (is_outside, reason)
    """
    action_type = action.get("action_type", "")

    # Only check coordinate-based actions
    if action_type not in ("CLICK", "LONG_CLICK", "SET_TEXT"):
        return False, ""

    y = action.get("y", 0)
    screen_height = device_dims[1]

    # Check status bar (top of screen)
    if y < screen_height * STATUSBAR_Y_PERCENT:
        return True, "status_bar"

    # Check navigation bar (bottom of screen)
    if y > screen_height * NAVBAR_Y_PERCENT:
        return True, "navigation_bar"

    return False, ""


def _create_back_action(reason: str) -> Dict[str, Any]:
    """Create a BACK action for boundary violation recovery."""
    return {
        "action_type": "BACK",
        "x": 0,
        "y": 0,
        "text": "",
        "source": "validation",
        "reason": reason
    }
