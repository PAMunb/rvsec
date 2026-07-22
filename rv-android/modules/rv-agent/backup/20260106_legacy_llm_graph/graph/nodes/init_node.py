"""
LangGraph node for application initialization.

Handles launching the target Android application and preparing
the initial state for exploration.
"""

import time
import logging
from typing import Dict, Any

from rv_agent.domain.state import AgentState

logger = logging.getLogger(__name__)


def init_app(state: AgentState) -> Dict[str, Any]:
    """
    Launch application and capture initial state.

    ### Architectural Decisions:
    - Launches app using package name from config
    - Waits for app to stabilize
    - Captures initial screenshot and activity
    - Does NOT parse UI yet (done in observe)

    ### Integration Points:
    - Uses DeviceInterface for app launch
    - Sets up initial timing for timeout tracking
    - Prepares state for first observe cycle

    Args:
        state: Current agent state

    Returns:
        Updated state with app launched
    """
    device = state['_device']
    package_name = state.get('_package_name', '')

    logger.info(f"Launching application: {package_name}")

    try:
        # Launch application (already waits 2s internally)
        device.launch_app(package_name)

        logger.info("Application launched successfully")

        return {
            "start_time": time.time(),
            "iteration": 0
        }

    except Exception as e:
        logger.error(f"Failed to launch app: {e}", exc_info=True)
        return {
            "should_continue": False,
            "start_time": time.time()
        }
