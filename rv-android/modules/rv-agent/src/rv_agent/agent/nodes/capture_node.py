"""
Capture screenshot node for RVAgent workflow.

Captures and optimizes screenshots for LLM consumption.
"""

import logging
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from rv_agent.agent.rv_agent import RVAgent

from rv_agent.domain.state import AgentState

logger = logging.getLogger(__name__)


def capture_screenshot_node(agent: "RVAgent", state: AgentState) -> Dict[str, Any]:
    """
    Capture and optimize screenshot for LLM.

    Args:
        agent: RVAgent instance with device and image_handler
        state: Current agent state

    Returns:
        State updates with screenshot_b64
    """
    logger.info("CAPTURE_SCREENSHOT: Capturing screen")

    try:
        screenshot_path = agent.device.take_screenshot()
        screenshot_b64 = agent.image_handler.optimize(
            image_path=screenshot_path, quality=90
        )

        if not screenshot_b64:
            logger.error("Screenshot optimization failed")
            return {"screenshot_b64": "", "decision_path": "end"}

        logger.info("Screenshot captured and optimized")
        return {"screenshot_b64": screenshot_b64}

    except Exception as e:
        logger.error(f"Screenshot capture failed: {e}", exc_info=True)
        return {"screenshot_b64": "", "decision_path": "end"}
