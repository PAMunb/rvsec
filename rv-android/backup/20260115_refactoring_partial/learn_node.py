"""
Learn node for RVAgent workflow.

Updates memory systems and detects stuck states.

Key Design Decisions:

1. STUCK STATE DETECTION
   Problem: The agent can get stuck in a state where actions don't change the screen
   (e.g., clicking a disabled button, animation loops, unresponsive dialogs).
   Solution: Track consecutive iterations where screen hash doesn't change.
   After STUCK_THRESHOLD (default: 3) unchanged screens, set force_back_action=True.

2. INTERACTION WITH DECISION_ROUTER
   The learn_node sets force_back_action flag, but doesn't execute BACK directly.
   This maintains separation of concerns:
   - learn_node: DETECTS stuck state, sets flag
   - decision_router: CHECKS flag, routes to algorithm path
   - algorithm_node: GENERATES BACK action when flag is set

   WHY THIS SEPARATION: Keeps each node focused on one responsibility.
   Learn node updates memories, decision_router routes, algorithm_node generates actions.

3. UI COVERAGE TRACKING
   Records which elements were interacted with for coverage metrics.
   Uses proximity matching because LLM clicks may not be exactly at element centers.
   The PROXIMITY_THRESHOLD (150 units in normalized [0,1000) space) accommodates
   typical LLM coordinate variance while avoiding false matches.
"""

import logging
from typing import TYPE_CHECKING, Dict, Any, Optional

if TYPE_CHECKING:
    from rv_agent.agent.rv_agent import RVAgent

from rv_agent.domain.state import AgentState

logger = logging.getLogger(__name__)


def learn_node(agent: "RVAgent", state: AgentState) -> Dict[str, Any]:
    """
    Update memory systems and prepare for next iteration.

    Handles memory updates, summary generation, state tracking,
    stuck state detection, and continuation checks.

    Args:
        agent: RVAgent instance with memory_coordinator and stuck detection
        state: Current agent state

    Returns:
        State updates with memories, summaries, and continuation flags
    """
    logger.info("LEARN: Updating memories")

    # Update memories
    memory_result = agent.memory_coordinator.update_memories(
        current_screen_hash=state.get("current_screen_hash", "unknown"),
        current_activity=state.get("current_activity", "unknown"),
        screen_description=state.get("screen_description"),
        action=state.get("current_action"),
        llm_reasoning=state.get("llm_reasoning", ""),
        iteration=state.get("iteration", 0),
        recent_action_window=state.get("recent_action_window", [])
    )

    # Generate summaries
    summaries = agent.memory_coordinator.generate_summaries(
        action=state.get("current_action"),
        current_activity=state.get("current_activity", "unknown"),
        visited_states=state.get("visited_states", []),
        state_transitions=state.get("state_transitions", [])
    )

    # Track state discovery
    tracking = agent.memory_coordinator.track_state_discovery(
        current_hash=state.get("current_screen_hash"),
        previous_hash=state.get("previous_screen_hash"),
        visited_states=state.get("visited_states", []),
        state_transitions=state.get("state_transitions", [])
    )

    # Stuck state detection and restart recovery
    current_hash = state.get("current_screen_hash")
    stuck_action_override = None
    stuck_count_before = agent.stuck_screen_count

    # Check for restart recovery (extended stuck detection)
    # This uses routing_manager to track consecutive same-state iterations
    # and triggers app restart after MAX_BLOCKS_BEFORE_RESTART iterations
    restart_action = agent.routing_manager.track_state_change(current_hash)
    if restart_action:
        logger.warning("Restart recovery triggered by routing_manager")
        stuck_action_override = restart_action
        agent.stuck_screen_count = 0
    elif current_hash == agent.last_screen_hash:
        agent.stuck_screen_count += 1
        logger.debug(f"Screen unchanged: {agent.stuck_screen_count}/{agent.STUCK_THRESHOLD}")

        if agent.stuck_screen_count >= agent.STUCK_THRESHOLD:
            logger.warning(
                f"Stuck state detected: screen unchanged "
                f"{stuck_count_before}->{agent.stuck_screen_count} iterations -> Forcing BACK"
            )
            stuck_action_override = {
                "action_type": "BACK",
                "reason": "stuck_state_recovery"
            }
            agent.stuck_screen_count = 0
    else:
        if stuck_count_before > 0:
            logger.debug(
                f"Screen changed, resetting stuck counter "
                f"(was {stuck_count_before}, hash: {agent.last_screen_hash[:12]}... -> {current_hash[:12]}...)"
            )
        agent.stuck_screen_count = 0

    agent.last_screen_hash = current_hash

    # Check continuation
    continuation = agent.memory_coordinator.check_continuation(
        start_time=state.get("start_time"),
        timeout=state.get("timeout")
    )

    result = {
        "recent_action_window": memory_result["recent_action_window"],
        "action_history_summary": summaries["action_history_summary"],
        "exploration_summary": summaries["exploration_summary"],
        "memory_insights": summaries["memory_insights"],
        "navigation_path": summaries["navigation_path"],
        "visited_states": tracking["visited_states"],
        "state_transitions": tracking["state_transitions"],
        "previous_screen_hash": state.get("current_screen_hash"),
        "should_continue": continuation["should_continue"],
        "loop_detected": False
    }

    if stuck_action_override:
        action_type = stuck_action_override.get("action_type", "BACK")
        if action_type == "RESTART_APP":
            result["force_restart_action"] = stuck_action_override
        else:
            result["force_back_action"] = True

    # Record UI coverage interaction for element tracking
    _record_ui_coverage(agent, state)

    # INSTRUMENTATION: Record exploration metrics for validation
    # This block can be removed for production
    if agent.metrics_collector:
        try:
            current_action = state.get("current_action", {})
            action_type = current_action.get("action_type", "UNKNOWN") if current_action else "NONE"
            action_source = current_action.get("source", "unknown") if current_action else "none"

            agent.metrics_collector.record_exploration(
                iteration=state.get("iteration", 0),
                activity=state.get("current_activity", "unknown"),
                screen_hash=state.get("current_screen_hash", "unknown"),
                action_type=action_type,
                action_source=action_source,
            )
            logger.debug("INSTRUMENTATION: Recorded exploration metrics")
        except Exception as e:
            logger.warning(f"INSTRUMENTATION: Failed to record exploration metrics: {e}")
    # END INSTRUMENTATION

    return result


def _record_ui_coverage(agent: "RVAgent", state: AgentState) -> None:
    """
    Record UI element interaction for coverage tracking.

    Uses proximity matching to find the closest UI element to the clicked
    coordinates, then records that element's ID for proper annotation.

    Args:
        agent: RVAgent instance with screen_processor.ui_coverage
        state: Current agent state with action details
    """
    try:
        # Get ui_coverage from screen_processor
        ui_coverage = getattr(agent.screen_processor, 'ui_coverage', None)
        if not ui_coverage:
            return

        current_action = state.get("current_action")
        if not current_action:
            return

        # Skip non-coordinate actions (like BACK)
        action_type = current_action.get("action_type", "").upper()
        if action_type in ("BACK", "HOME", "SCROLL"):
            return

        screen_hash = state.get("current_screen_hash", "unknown")

        # Get click coordinates (use original_coords which are normalized [0,1000))
        original_coords = current_action.get("original_coords")
        if not original_coords or len(original_coords) != 2:
            return

        click_x, click_y = original_coords

        # Find matching element from screen description
        screen_desc = state.get("screen_description")

        # Get device dimensions from screen_processor (default to 1080x1920)
        device_dims = getattr(agent.screen_processor, 'device_dimensions', (1080, 1920))
        element_id = _find_element_at_coords(screen_desc, click_x, click_y, device_dimensions=device_dims)

        if not element_id:
            # Fallback to coordinate-based ID
            element_id = f"coords:{click_x},{click_y}:CLICK"

        # Record the interaction
        ui_coverage.record_interaction(
            element_id=element_id,
            action_type=action_type.lower(),
            screen_hash=screen_hash,
            success=True
        )

        # INSTRUMENTATION: Log UI coverage recording
        test_count = ui_coverage.get_element_test_count(element_id)
        logger.info(
            f"[INSTRUMENTATION] UI_COVERAGE: {action_type} on {element_id[:50]} "
            f"| count={test_count} | screen={screen_hash[:8]}"
        )

    except Exception as e:
        logger.warning(f"UI_COVERAGE: Failed to record interaction: {e}")


def _find_element_at_coords(
    screen_desc,
    click_x: int,
    click_y: int,
    device_dimensions: tuple = (1080, 1920)
) -> Optional[str]:
    """
    Find the UI element closest to the click coordinates using proximity matching.

    This solves the coordinate matching problem where LLM clicks may not be
    exactly at element centers. We find the nearest element and return its ID
    in the same format used by annotate_screen_elements.

    Args:
        screen_desc: ScreenDescription object with items
        click_x: Click X coordinate in normalized [0, 1000) space
        click_y: Click Y coordinate in normalized [0, 1000) space
        device_dimensions: Device screen dimensions (width, height)

    Returns:
        Element ID string matching annotate_screen_elements format, or None
    """
    if not screen_desc or not hasattr(screen_desc, 'items') or not screen_desc.items:
        return None

    device_width, device_height = device_dimensions
    best_match = None
    min_distance = float('inf')

    for item in screen_desc.items:
        bounds = item.view.get('bounds')
        if not (bounds and len(bounds) == 2 and len(bounds[0]) == 2 and len(bounds[1]) == 2):
            continue

        # Calculate element center in device pixels
        device_center_x = (bounds[0][0] + bounds[1][0]) // 2
        device_center_y = (bounds[0][1] + bounds[1][1]) // 2

        # Convert to normalized [0, 1000) space (same as screen_analyzer)
        norm_x = int((device_center_x / device_width) * 1000)
        norm_y = int((device_center_y / device_height) * 1000)

        # Calculate Euclidean distance in normalized space
        distance = ((click_x - norm_x) ** 2 + (click_y - norm_y) ** 2) ** 0.5

        if distance < min_distance:
            min_distance = distance
            best_match = (norm_x, norm_y, item)

    # Only accept matches within a reasonable threshold (150 units in normalized space)
    # This corresponds to ~15% of screen dimension (accommodates LLM coordinate variance)
    PROXIMITY_THRESHOLD = 150

    if best_match and min_distance <= PROXIMITY_THRESHOLD:
        norm_x, norm_y, item = best_match

        # Generate element ID in the same format as annotate_screen_elements
        # Primary: use coordinates (matches _generate_element_id in ui_coverage.py)
        element_id = f"coords:{norm_x},{norm_y}:CLICK"

        logger.debug(
            f"[INSTRUMENTATION] PROXIMITY_MATCH: click({click_x},{click_y}) -> "
            f"element({norm_x},{norm_y}) distance={min_distance:.1f}"
        )

        return element_id

    logger.debug(
        f"[INSTRUMENTATION] NO_PROXIMITY_MATCH: click({click_x},{click_y}) "
        f"min_distance={min_distance:.1f} > threshold={PROXIMITY_THRESHOLD}"
    )
    return None


def _generate_element_id_from_action(action: Dict[str, Any], state: AgentState) -> str:
    """
    Generate consistent element ID from action for coverage tracking.

    Uses coordinates and element description to create a unique identifier
    that matches the format used by annotate_screen_elements.

    Args:
        action: Action dictionary with coordinates and description
        state: Agent state with screen context

    Returns:
        Element identifier string or empty string if cannot generate
    """
    # Try to get element description from action
    element_desc = action.get("element_description", "")

    # If we have a description with id:, text:, or desc:, use it
    if element_desc:
        import re

        # Extract ID
        id_match = re.search(r'id[=:](\w+)', element_desc, re.IGNORECASE)
        if id_match:
            return f"id:{id_match.group(1)}"

        # Extract quoted text
        text_match = re.search(r'"([^"]+)"', element_desc)
        if text_match:
            return f'text:"{text_match.group(1)}"'

        # Extract parenthesized text (common in descriptions like "Button (submit)")
        paren_match = re.search(r'\(([^)]+)\)', element_desc)
        if paren_match:
            return f'id:{paren_match.group(1)}'

    # Fallback: use coordinates + action type as identifier
    # CRITICAL: Use original_coords (normalized [0,1000)) to match screen_analyzer format
    # The screen description uses normalized coords, so we must use the same space
    original_coords = action.get("original_coords")
    if original_coords and len(original_coords) == 2:
        x, y = original_coords
        action_type = action.get("action_type", "CLICK")
        return f"coords:{x},{y}:{action_type}"

    # Fallback to device coords if no original_coords available
    coords = action.get("coordinates")
    if coords:
        x, y = coords.get("x", 0), coords.get("y", 0)
    else:
        x = action.get("x")
        y = action.get("y")

    if x is not None and y is not None:
        action_type = action.get("action_type", "CLICK")
        return f"coords:{x},{y}:{action_type}"

    return ""
