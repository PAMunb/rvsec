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
from rv_agent.memory.element_id import make_element_id_from_action, make_element_id_from_tuple

logger = logging.getLogger(__name__)


def _record_ui_interaction(
    agent: "RVAgent",
    action: Dict[str, Any],
    action_type: str,
    screen_hash: str,
    item_action: Any,
    source: str
) -> None:
    """
    Record UI interaction for coverage tracking.

    Unified recording point for both algorithm and LLM actions.

    For algorithm actions: Uses ItemAction to get precise element_id and component_type.
    For LLM actions: Uses proximity matching to find nearest registered element.

    Args:
        agent: RVAgent instance with ui_coverage tracker
        action: Action dictionary with coordinates
        action_type: Type of action (CLICK, SET_TEXT, etc.)
        screen_hash: Current screen hash
        item_action: ItemAction instance (available for algorithm actions)
        source: Action source ("algorithm", "llm", "validation")
    """
    element_id = None
    component_type = None

    # For algorithm actions, use ItemAction directly
    if source == "algorithm" and item_action:
        element_id = item_action.widget_id or make_element_id_from_tuple(item_action.coordinates)
        if item_action.target_view:
            comp_class = item_action.target_view.get('class', '')
            component_type = comp_class.split('.')[-1] if comp_class else 'Unknown'
        logger.debug(f"Recording algorithm interaction: {element_id} ({component_type})")

    # For LLM actions, use proximity matching
    elif source == "llm":
        x = action.get('x')
        y = action.get('y')
        if x is not None and y is not None:
            # Try to find nearest registered element
            match = agent.ui_coverage.find_nearest_element(x, y, screen_hash)
            if match:
                element_id, component_type, distance = match
                logger.debug(f"Recording LLM interaction: {element_id} ({component_type}, dist={distance:.1f}px)")
            else:
                # No match found - use action coordinates directly
                element_id = make_element_id_from_action(action)
                component_type = "Unknown"
                logger.debug(f"Recording LLM interaction (no match): {element_id}")

    # For validation/recovery actions (BACK, etc.), skip detailed tracking
    else:
        element_id = make_element_id_from_action(action)
        component_type = "SystemAction"

    # Record the interaction
    if element_id:
        agent.ui_coverage.record_interaction(
            element_id=element_id,
            action_type=action_type,
            screen_hash=screen_hash,
            success=True,
            component_type=component_type
        )


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

    # Record transition and interaction if action succeeded
    if result.get("success"):
        prev_hash = state.get("previous_screen_hash")
        current_hash = state.get("current_screen_hash", "")
        item_action = state.get("current_item_action")

        if prev_hash and item_action:
            agent.strategy.record_transition(prev_hash, current_hash, item_action)
            logger.debug(f"Recorded transition: {prev_hash[:8]} -> {current_hash[:8]}")

        # Record interaction for UI coverage tracking (ALL modes)
        # Unified tracking point for both algorithm and LLM actions
        has_ui_cov = hasattr(agent, 'ui_coverage') and agent.ui_coverage is not None
        if has_ui_cov:
            try:
                _record_ui_interaction(
                    agent, action, action_type, current_hash, item_action, source
                )
            except Exception as e:
                logger.warning(f"Failed to record UI interaction: {e}")

    executed_action = result.get("action_executed")

    return {
        "current_action": executed_action,
        "action_executed": executed_action,
        "action_success": result.get("success", False)
    }
