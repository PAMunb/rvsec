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
