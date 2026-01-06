"""
LLM generate node for RVAgent workflow.

Generates actions using the LLM client.
"""

import logging
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from rv_agent.agent.rv_agent import RVAgent

from rv_agent.domain.state import AgentState

logger = logging.getLogger(__name__)


def llm_generate_node(agent: "RVAgent", state: AgentState) -> Dict[str, Any]:
    """
    Generate action using LLM.

    Args:
        agent: RVAgent instance with llm_client
        state: Current agent state

    Returns:
        State updates with llm_action and token metrics
    """
    logger.info("LLM_GENERATE: Calling LLM")

    if not agent.llm_client:
        logger.error("LLM client not available")
        return {
            "llm_action": None,
            "has_tool_calls": False,
            "validation_path": "algorithm_fallback"
        }

    result = agent.llm_client.generate_action(
        screen_description=state.get("screen_description"),
        screenshot_b64=state.get("screenshot_b64", ""),
        ui_elements_text=state.get("ui_elements_text", ""),
        iteration=state.get("iteration", 0),
        last_action_summary=state.get("action_history_summary")
    )

    return {
        "llm_action": result.get("action"),
        "has_tool_calls": result.get("has_tool_calls", False),
        "llm_reasoning": result.get("reasoning", ""),
        "llm_tokens_input": state.get("llm_tokens_input", 0) + result.get("tokens_input", 0),
        "llm_tokens_output": state.get("llm_tokens_output", 0) + result.get("tokens_output", 0),
        "llm_time_ms": state.get("llm_time_ms", 0) + result.get("time_ms", 0),
        "decision_maker": "llm"
    }
