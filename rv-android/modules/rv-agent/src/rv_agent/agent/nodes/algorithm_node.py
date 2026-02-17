"""
Algorithm node for RVAgent workflow.

Generates actions using the algorithmic exploration strategy.

Includes error recovery: when force_fill_input=True (set by learn_node on
validation error detection), finds the input field closest to the error
indicator using spatial association and generates a fill action.
"""

import logging
from typing import TYPE_CHECKING, Dict, Any, Optional, Tuple

if TYPE_CHECKING:
    from rv_agent.agent.rv_agent import RVAgent

from rv_agent.domain.state import AgentState
from rv_agent.memory.element_id import make_element_id_from_tuple

logger = logging.getLogger(__name__)

# Spatial association constants
SPATIAL_BELOW_FIELD_SCORE = 0.7
SPATIAL_BELOW_FIELD_MAX_PX = 100


def _calculate_association_score(error_bbox, item_bounds, item_class, agent) -> float:
    """Calculate how strongly an error indicator associates with a screen item.

    Uses overlap score (IoU) + widget-type boost + below-field heuristic.

    Args:
        error_bbox: BoundingBox from ErrorIndicator (x, y, width, height)
        item_bounds: Bounds list from target_view, format [[x1,y1],[x2,y2]]
        item_class: Android widget class name (e.g., "android.widget.EditText")
        agent: RVAgent instance with spatial config

    Returns:
        Association score (0.0 if no spatial relationship)
    """
    try:
        # Parse item bounds: [[x1,y1],[x2,y2]]
        if not item_bounds or not isinstance(item_bounds, list) or len(item_bounds) != 2:
            return 0.0
        item_x1, item_y1 = item_bounds[0]
        item_x2, item_y2 = item_bounds[1]
    except (TypeError, IndexError, ValueError):
        return 0.0

    # Error bbox coordinates
    err_x1 = error_bbox.x
    err_y1 = error_bbox.y
    err_x2 = error_bbox.x + error_bbox.width
    err_y2 = error_bbox.y + error_bbox.height

    # Calculate IoU (Intersection over Union)
    inter_x1 = max(err_x1, item_x1)
    inter_y1 = max(err_y1, item_y1)
    inter_x2 = min(err_x2, item_x2)
    inter_y2 = min(err_y2, item_y2)

    inter_area = max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1)
    err_area = error_bbox.width * error_bbox.height
    item_area = max(0, item_x2 - item_x1) * max(0, item_y2 - item_y1)
    union_area = err_area + item_area - inter_area

    overlap_score = inter_area / union_area if union_area > 0 else 0.0

    # Widget-type boost (tiebreaker, not filter)
    boost = 1.0
    if "EditText" in (item_class or ""):
        boost = agent.config.spatial_edittext_boost
    elif "Spinner" in (item_class or ""):
        boost = agent.config.spatial_spinner_boost

    score = overlap_score * boost

    # Below-field heuristic: error indicator positioned below an input field.
    # Fires when: error center_y is within SPATIAL_BELOW_FIELD_MAX_PX below
    # the item's bottom edge AND there is horizontal overlap.
    below_field_score = 0.0
    err_center_y = error_bbox.y + error_bbox.height // 2
    item_bottom = item_y2
    if err_center_y > item_bottom and err_center_y < item_bottom + SPATIAL_BELOW_FIELD_MAX_PX:
        # Check horizontal overlap
        h_inter = max(0, min(err_x2, item_x2) - max(err_x1, item_x1))
        if h_inter > 0:
            below_field_score = SPATIAL_BELOW_FIELD_SCORE * boost

    return max(score, below_field_score)


def _find_associated_input_action(agent, state) -> Optional[Tuple]:
    """Find the input field closest to an error indicator using spatial association.

    Iterates all error indicators and screen items, scoring each pair by
    spatial proximity. Returns the highest-scoring (action, item) pair
    above the minimum threshold, or None if no match.

    Args:
        agent: RVAgent instance with spatial config
        state: Agent state with error_indicators and screen_description

    Returns:
        (action, item) tuple or None if no match above threshold
    """
    error_indicators = state.get("error_indicators")
    if not error_indicators:
        return None

    screen_desc = state.get("screen_description")
    if not screen_desc:
        return None

    best_score = 0.0
    best_action = None
    best_item = None

    for indicator in error_indicators:
        error_bbox = indicator.bbox
        for item in screen_desc.items:
            for action in item.actions:
                if not action.target_view or not action.target_view.get("bounds"):
                    continue
                item_bounds = action.target_view["bounds"]
                item_class = action.target_view.get("class", "")

                score = _calculate_association_score(error_bbox, item_bounds, item_class, agent)

                if score > best_score and score >= agent.config.spatial_min_match_threshold:
                    best_score = score
                    best_action = action
                    best_item = item

    if best_action is None:
        return None

    return (best_action, best_item)


def _find_next_input_action(state) -> Optional[Tuple]:
    """Sequential fallback: find the first set_text action on the current screen.

    Iterates through all screen items and returns the first action
    with action_type == "set_text". Used when spatial association
    finds no match.

    Args:
        state: Agent state with screen_description

    Returns:
        (action, item) tuple or None if no set_text action found
    """
    screen_desc = state.get("screen_description")
    if not screen_desc:
        return None

    for item in screen_desc.items:
        for action in item.actions:
            if action.action_type == "set_text":
                return (action, item)

    return None


def _build_error_recovery_action(agent, matched_action, state) -> Optional[Dict[str, Any]]:
    """Build the unified action dict for error recovery.

    For set_text actions, generates a text value using the value generator.
    For click actions (Spinner), returns a CLICK action with coordinates.

    Args:
        agent: RVAgent instance with strategy.value_generator
        matched_action: ItemAction from spatial/sequential match
        state: Agent state (for context)

    Returns:
        Unified action dict or None if coordinates unavailable
    """
    coords = matched_action.get_execution_coordinates()
    if not coords:
        return None

    x, y = coords
    action_type = matched_action.action_type.upper()

    if action_type == "SET_TEXT":
        # Generate text value via value_generator
        element_id = matched_action.widget_id or make_element_id_from_tuple(
            matched_action.coordinates
        )
        is_mop = getattr(matched_action, "reaches_mop", False) or getattr(
            matched_action, "directly_reaches_mop", False
        )
        text_value = agent.strategy.value_generator.get_next_value(
            element_id, is_mop=is_mop
        )
        if not text_value:
            text_value = "test"
    else:
        text_value = matched_action.text or ""

    return {
        "action_type": action_type,
        "x": x,
        "y": y,
        "text": text_value,
        "source": "algorithm",
        "reason": "error_recovery",
        "id": matched_action.id,
    }


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

    # Error recovery: fill input field when validation error detected.
    # Spatial association maps the error indicator to the nearest input field.
    # Falls back to sequential search if no spatial match is found.
    if state.get("force_fill_input"):
        match = _find_associated_input_action(agent, state)
        if match is None:
            match = _find_next_input_action(state)

        if match:
            matched_action, matched_item = match
            recovery_action = _build_error_recovery_action(agent, matched_action, state)
            if recovery_action:
                logger.info(
                    f"Error recovery: {recovery_action['action_type']} at "
                    f"({recovery_action['x']}, {recovery_action['y']})"
                )
                agent.consecutive_no_action = 0
                return {
                    "current_action": recovery_action,
                    "current_item_action": matched_action,
                    "decision_maker": "error_recovery",
                    "force_fill_input": False,
                    "error_indicators": None,
                }

        # No actionable field found — clear flags before falling through.
        # LangGraph state persists unless overwritten, so omitting the clear
        # would leave force_fill_input=True for the next iteration.
        logger.info("Error recovery: no actionable field found, resuming normal flow")
        # Flags are cleared via the result dict; the normal flow below runs.
        # We merge the clear into the final result at the end of the function.
        _error_recovery_clear = {"force_fill_input": False, "error_indicators": None}
    else:
        _error_recovery_clear = {}

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
        result = {
            "current_action": action,
            "current_item_action": None,
            "decision_maker": "algorithm"
        }
        result.update(_error_recovery_clear)
        return result

    screen_hash = state.get("current_screen_hash")
    screen_desc = state.get("screen_description")

    item_action = agent.strategy.select_next_action(screen_hash, screen_desc)

    if not item_action:
        agent.consecutive_no_action += 1
        logger.warning(
            f"No action available from strategy "
            f"(consecutive_no_action={agent.consecutive_no_action}/{agent.NO_ACTION_THRESHOLD})"
        )
        result = {
            "current_action": None,
            "decision_path": "end"
        }
        result.update(_error_recovery_clear)
        return result

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
        result = {
            "current_action": action,
            "current_item_action": item_action,
            "decision_maker": "algorithm"
        }
        result.update(_error_recovery_clear)
        return result

    # Get coordinates from ItemAction for regular actions
    coords = item_action.get_execution_coordinates()
    if not coords:
        logger.error(
            f"Failed to get coordinates from ItemAction: "
            f"type={action_type}, id={item_action.id}, text={item_action.text[:50] if item_action.text else 'None'}"
        )
        result = {
            "current_action": None,
            "decision_path": "end"
        }
        result.update(_error_recovery_clear)
        return result

    x, y = coords

    # Convert ItemAction to unified action format
    # For SET_TEXT actions, use text_input (actual value to type) not text (description)
    if action_type == "SET_TEXT":
        text_value = item_action.text_input or ""
        if not text_value:
            logger.warning("SET_TEXT action has no text_input value, action will fail")
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

    msg = f"Algorithm selected: {action_type} at ({x}, {y})"
    if text_value:
        msg += f" text='{text_value[:20]}'"
    logger.info(msg)

    # Reset deadlock counter on successful action
    agent.consecutive_no_action = 0

    result = {
        "current_action": action,
        "current_item_action": item_action,
        "decision_maker": "algorithm"
    }
    result.update(_error_recovery_clear)
    return result
