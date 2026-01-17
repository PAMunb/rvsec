"""
Parse UI node for RVAgent workflow.

Captures and parses the current screen UI state.
"""

import logging
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from rv_agent.agent.rv_agent import RVAgent

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
    logger.info("DEBUG_TRACE: parse_ui_node ENTER")
    logger.info("PARSE_UI: Parsing screen")

    result = agent.screen_processor.parse_current_screen(
        target_package=agent.config.package_name,
        external_navigation_count=state.get("external_navigation_count", 0)
    )

    ui_elements_text = result["ui_elements_text"]
    logger.info(f"UI elements text length: {len(ui_elements_text)} chars")

    if not ui_elements_text or len(ui_elements_text) < 50:
        logger.warning(f"UI elements text is empty or too short: '{ui_elements_text[:100]}'")

    # Register screen elements for UI coverage tracking (core functionality)
    screen_hash = result["screen_hash"]
    screen_desc = result.get("screen_description")
    if screen_hash and screen_desc and hasattr(agent, 'ui_coverage'):
        try:
            agent.ui_coverage.register_screen_elements(screen_hash, screen_desc)
        except Exception as e:
            logger.warning(f"Failed to register screen elements: {e}")

    # INSTRUMENTATION: Also record to validation collector if present
    if agent.metrics_collector:
        try:
            ui_xml = result.get("ui_xml", "")
            if screen_hash and ui_xml:
                agent.metrics_collector.record_screen_elements(
                    screen_hash=screen_hash,
                    ui_dump=ui_xml
                )
        except Exception as e:
            logger.debug(f"INSTRUMENTATION: Failed to record screen elements: {e}")

    return {
        "current_screen_hash": result["screen_hash"],
        "current_activity": result["activity"],
        "screen_description": result["screen_description"],
        "ui_elements_text": ui_elements_text,
        "is_external": result["is_external"],
        "external_navigation_count": result["external_navigation_count"],
        # INSTRUMENTATION: Raw XML for hit classification in metrics collection
        "ui_xml": result.get("ui_xml", "")
    }
