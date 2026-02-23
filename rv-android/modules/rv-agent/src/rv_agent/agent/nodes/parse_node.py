"""
Parse UI node for RVAgent workflow.

Captures and parses the current screen UI state.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from rv_agent.agent.rv_agent import RVAgent

from rv_agent import tracking as track
from rv_agent.domain.state import AgentState

logger = logging.getLogger(__name__)


def _update_cached_bounds(cached_desc, fresh_desc):
    """Update cached screen_desc item bounds from a fresh parse.

    When the keyboard appears or disappears, elements shift vertically
    but the structural hash stays the same. Update bounds in the cached
    copy so coordinate-based actions use current positions.
    """
    # Build lookups from widget_id and bounds-center to fresh bounds
    fresh_by_id = {}
    fresh_no_id = []  # (center_x, center_y, bounds) for elements without widget_id
    for item in fresh_desc.items:
        for action in item.actions:
            if not action.target_view:
                continue
            bounds = action.target_view.get("bounds")
            if not bounds or not isinstance(bounds, list) or len(bounds) < 2:
                continue
            # Bounds format: [[x1, y1], [x2, y2]] (nested list from UIAutomator)
            try:
                x1, y1 = bounds[0]
                x2, y2 = bounds[1]
            except (TypeError, ValueError):
                continue
            if action.widget_id:
                fresh_by_id[action.widget_id] = bounds
            else:
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2
                fresh_no_id.append((cx, cy, bounds))

    if not fresh_by_id and not fresh_no_id:
        return

    # Update cached items
    PROXIMITY_THRESHOLD = 50
    updated = 0
    for item in cached_desc.items:
        for action in item.actions:
            if not action.target_view:
                continue
            old_bounds = action.target_view.get("bounds")
            if not old_bounds:
                continue

            if action.widget_id and action.widget_id in fresh_by_id:
                # Match by widget_id
                new_bounds = fresh_by_id[action.widget_id]
                if old_bounds != new_bounds:
                    action.target_view["bounds"] = new_bounds
                    updated += 1
            elif not action.widget_id and fresh_no_id:
                # Fallback: match by coordinate proximity (bounds center)
                # Bounds format: [[x1, y1], [x2, y2]]
                try:
                    ox1, oy1 = old_bounds[0]
                    ox2, oy2 = old_bounds[1]
                except (TypeError, ValueError):
                    continue
                cached_cx = (ox1 + ox2) // 2
                cached_cy = (oy1 + oy2) // 2
                for fx, fy, fresh_bounds in fresh_no_id:
                    if (
                        abs(cached_cx - fx) < PROXIMITY_THRESHOLD
                        and abs(cached_cy - fy) < PROXIMITY_THRESHOLD
                    ):
                        if old_bounds != fresh_bounds:
                            action.target_view["bounds"] = fresh_bounds
                            updated += 1
                        break

    if updated > 0:
        logger.debug(f"Updated {updated} cached element bounds from fresh parse")


def parse_ui_node(agent: "RVAgent", state: AgentState) -> Dict[str, Any]:
    """
    Parse current screen UI and update state.

    Captures the current UI state from the device, parses it into a
    ScreenDescription, and detects external navigation.

    Args:
        agent: RVAgent instance with screen_processor and config
        state: Current agent state

    Returns:
        State updates with screen_hash, activity, description, and UI text
    """
    iteration = state.get("iteration", 0)

    result = agent.screen_processor.parse_current_screen(
        target_package=agent.config.package_name,
        external_navigation_count=state.get("external_navigation_count", 0),
    )

    # Screen description caching: reuse cached value when screen hash is unchanged.
    # parse_current_screen still runs (we need the hash to compare), but the
    # expensive-to-process screen_description is reused from cache on repeat screens.
    screen_desc = result.get("screen_description")
    previous_hash = state.get("previous_screen_hash")
    screen_hash = result["screen_hash"]

    cached = getattr(agent, "_cached_screen_desc", None)
    if screen_hash and screen_hash == previous_hash and cached is not None:
        # Update cached items' bounds from fresh parse: keyboard appearance
        # can shift elements vertically without changing structural hash.
        fresh_desc = result.get("screen_description")
        if fresh_desc and cached:
            _update_cached_bounds(cached, fresh_desc)
        screen_desc = cached
        result["screen_description"] = screen_desc
    else:
        # Update cache with fresh screen_description
        agent._cached_screen_desc = screen_desc

    elements_count = len(screen_desc.items) if screen_desc else 0

    track.parse(
        iter=iteration,
        activity=result["activity"],
        elements=elements_count,
        hash=result["screen_hash"] or "unknown",
    )

    ui_elements_text = result["ui_elements_text"]
    if not ui_elements_text or len(ui_elements_text) < 50:
        logger.warning(f"UI elements text too short: '{ui_elements_text[:100]}'")

    # Register screen elements for UI coverage tracking
    if screen_hash and screen_desc and hasattr(agent, "ui_coverage"):
        try:
            agent.ui_coverage.register_screen_elements(screen_hash, screen_desc)
        except Exception as e:
            logger.warning(f"Failed to register screen elements: {e}")

    # Error detection: capture screenshot when screen hash repeats (same screen after action)
    error_detection_screenshot = None
    if agent.config.error_detection_enabled and screen_hash == previous_hash:
        try:
            error_detection_screenshot = agent.device.take_screenshot()
        except Exception as e:
            logger.warning(f"Screenshot capture for error detection failed: {e}")

    return {
        "current_screen_hash": result["screen_hash"],
        "current_activity": result["activity"],
        "screen_description": result["screen_description"],
        "ui_elements_text": ui_elements_text,
        "is_external": result["is_external"],
        "external_navigation_count": result["external_navigation_count"],
        "ui_xml": result.get("ui_xml", ""),
        "error_detection_screenshot": error_detection_screenshot,
    }
