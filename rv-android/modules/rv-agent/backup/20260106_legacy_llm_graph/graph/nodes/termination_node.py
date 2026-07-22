"""
LangGraph node for termination check.

Handles checking whether exploration should continue or terminate
based on timeout and other criteria.
"""

import time
import logging

from rv_agent.domain.state import AgentState

logger = logging.getLogger(__name__)


def check_termination(state: AgentState) -> str:
    """
    Check termination criteria and route workflow.

    ### Architectural Decisions:
    - Only checks timeout criterion
    - No plateau detection or other heuristics
    - Simple time-based termination

    ### Termination Criteria:
    - Timeout exceeded

    Args:
        state: Current agent state

    Returns:
        "observe" to continue, "END" to terminate
    """
    elapsed = time.time() - state['start_time']
    timeout = state['timeout']
    remaining = timeout - elapsed

    logger.info(f"Time: {elapsed:.1f}s / {timeout}s (remaining: {remaining:.1f}s)")

    if elapsed >= timeout:
        logger.info("Timeout reached - terminating exploration")
        return "END"

    if not state.get('should_continue', True):
        logger.info("Stop flag set - terminating exploration")
        return "END"

    logger.info("Continuing to next observation...")
    return "observe"
