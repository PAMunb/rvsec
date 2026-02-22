"""
Execute node for RVAgent workflow.

Executes actions on the device. All actions are expected to be in unified
format with coordinates already in device space (from ActionNormalizer).
"""

import logging
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from rv_agent.agent.rv_agent import RVAgent

from rv_agent import tracking as track
from rv_agent.domain.state import AgentState
from rv_agent.memory.element_id import make_element_id_from_action

logger = logging.getLogger(__name__)


def _record_ui_interaction(
    agent: "RVAgent",
    action: Dict[str, Any],
    action_type: str,
    screen_hash: str,
    item_action: Any,
    source: str,
) -> None:
    """
    Record UI interaction for coverage tracking.

    Unified recording point for both algorithm and LLM actions.
    All coordinates use device pixel space (INV-AGT-40), matching
    register_screen_elements() and find_nearest_element().

    Args:
        agent: RVAgent instance with ui_coverage tracker
        action: Action dictionary with device-space coordinates
        action_type: Type of action (CLICK, SET_TEXT, etc.)
        screen_hash: Current screen hash
        item_action: ItemAction instance (available for algorithm actions)
        source: Action source ("algorithm", "llm", "validation")
    """
    element_id = None
    component_type = None

    # For algorithm actions, use device-space coordinates directly
    if source == "algorithm" and item_action:
        if item_action.target_view:
            comp_class = item_action.target_view.get("class", "")
            component_type = comp_class.split(".")[-1] if comp_class else "Unknown"

        # Use device coordinates for proximity matching (INV-AGT-40)
        coords = item_action.get_execution_coordinates()
        if coords:
            device_x, device_y = coords

            match = agent.ui_coverage.find_nearest_element(
                device_x, device_y, screen_hash
            )
            if match:
                element_id, matched_type, distance = match
                if not component_type:
                    component_type = matched_type
                logger.debug(
                    f"Recording algorithm interaction: {element_id} ({component_type}, dist={distance:.1f}px)"
                )
            else:
                # No match - create element_id from device coords
                from rv_agent.memory.element_id import make_element_id

                element_id = make_element_id(device_x, device_y)
                logger.debug(
                    f"Recording algorithm interaction (no match): {element_id}"
                )

    # For LLM actions, use device-space coordinates
    elif source == "llm":
        # Action dict has device-space x, y (converted by ActionNormalizer.from_llm)
        x = action.get("x")
        y = action.get("y")

        if x is not None and y is not None:
            # Try to find nearest registered element in device space
            match = agent.ui_coverage.find_nearest_element(x, y, screen_hash)
            if match:
                element_id, component_type, distance = match
                logger.debug(
                    f"Recording LLM interaction: {element_id} ({component_type}, dist={distance:.1f}px)"
                )
            else:
                # No match found - use device coordinates directly
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
            component_type=component_type,
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
    action = state.get("current_action")
    iteration = state.get("iteration", 0)

    if not action:
        logger.warning("No action to execute")
        return {"action_executed": None}

    source = action.get("source", "unknown")
    action_type = action.get("action_type", "UNKNOWN")
    coords = (action.get("x"), action.get("y"))

    track.execution(iter=iteration, action=action_type, coords=coords, source=source)

    # Pre-marking for LLM actions: Record action in graph BEFORE execution
    # This ensures the action is marked as executed even if the app crashes
    screen_hash = state.get("current_screen_hash", "")
    if source == "llm" and screen_hash and agent.dynamic_graph:
        x, y = coords
        if x is not None and y is not None:
            action_sig = ((x, y), action_type)
            # Resolve widget_class from the matched ItemAction (set by
            # validation_node) which carries the real target_view with class.
            # LLM action dicts have no target_view, so without this the
            # widget_class is always "" and widget-aware saturation (Group 17)
            # falls back to DEFAULT_SATURATION_THRESHOLD for all widgets.
            matched_item = state.get("current_item_action")
            if matched_item and getattr(matched_item, "target_view", None):
                llm_widget_class = matched_item.target_view.get("class", "")
            else:
                llm_widget_class = action.get("target_view", {}).get("class", "")
            agent.dynamic_graph.record_action(
                screen_hash, action_sig, widget_class=llm_widget_class
            )

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
        has_ui_cov = hasattr(agent, "ui_coverage") and agent.ui_coverage is not None
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
        "action_success": result.get("success", False),
    }
