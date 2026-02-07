"""
Parse UI node for RVAgent workflow.

Captures and parses the current screen UI state.
"""

import logging
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from rv_agent.agent.rv_agent import RVAgent

from rv_agent.domain.state import AgentState
from rv_agent import tracking as track

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
        external_navigation_count=state.get("external_navigation_count", 0)
    )

    screen_desc = result.get("screen_description")
    elements_count = len(screen_desc.items) if screen_desc else 0

    track.parse(
        iter=iteration,
        activity=result["activity"],
        elements=elements_count,
        hash=result["screen_hash"] or "unknown"
    )

    ui_elements_text = result["ui_elements_text"]
    if not ui_elements_text or len(ui_elements_text) < 50:
        logger.warning(f"UI elements text too short: '{ui_elements_text[:100]}'")

    # Register screen elements for UI coverage tracking
    screen_hash = result["screen_hash"]
    if screen_hash and screen_desc and hasattr(agent, 'ui_coverage'):
        try:
            agent.ui_coverage.register_screen_elements(screen_hash, screen_desc)
        except Exception as e:
            logger.warning(f"Failed to register screen elements: {e}")

    return {
        "current_screen_hash": result["screen_hash"],
        "current_activity": result["activity"],
        "screen_description": result["screen_description"],
        "ui_elements_text": ui_elements_text,
        "is_external": result["is_external"],
        "external_navigation_count": result["external_navigation_count"],
        "ui_xml": result.get("ui_xml", "")
    }
