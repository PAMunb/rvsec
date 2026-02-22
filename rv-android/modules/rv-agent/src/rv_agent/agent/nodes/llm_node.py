"""
LLM generate node for RVAgent workflow.

Generates actions using the LLM client with optional navigation guidance.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from rv_agent.agent.rv_agent import RVAgent

from rv_agent import tracking as track
from rv_agent.domain.state import AgentState

logger = logging.getLogger(__name__)


def llm_generate_node(agent: "RVAgent", state: AgentState) -> Dict[str, Any]:
    """
    Generate action using LLM with navigation guidance.

    Args:
        agent: RVAgent instance with llm_client and navigation_guidance
        state: Current agent state

    Returns:
        State updates with llm_action and token metrics
    """
    iteration = state.get("iteration", 0)

    if not agent.llm_client:
        logger.error("LLM client not available")
        return {"llm_action": None, "has_tool_calls": False, "decision_maker": "llm"}

    # Get navigation hint if available
    navigation_hint = ""
    if agent.navigation_guidance and agent.navigation_guidance.is_enabled:
        screen_desc = state.get("screen_description")
        if screen_desc:
            context = agent.navigation_guidance.get_context(screen_desc)
            navigation_hint = agent.navigation_guidance.format_for_llm(context)

    # Get screen info for v15 prompt
    screen_line = ""
    screen_hash = state.get("current_screen_hash", "")
    if agent.dynamic_graph and screen_hash:
        screen_line = agent.dynamic_graph.get_screen_line(screen_hash)

    result = agent.llm_client.generate_action(
        screen_description=state.get("screen_description"),
        screenshot_b64=state.get("screenshot_b64", ""),
        ui_elements_text=state.get("ui_elements_text", ""),
        iteration=state.get("iteration", 0),
        last_action_summary=state.get("action_history_summary"),
        navigation_hint=navigation_hint,
        screen_line=screen_line,
    )

    # Extract action from LLM response and normalize to unified format
    llm_action = None
    has_tool_calls = False
    llm_reasoning = ""

    response = result.get("response")
    if response and result.get("success", False):
        # Extract tool calls from AIMessage
        tool_calls = getattr(response, "tool_calls", []) or []
        has_tool_calls = len(tool_calls) > 0

        if tool_calls:
            # Extract first tool call
            first_tool = tool_calls[0]
            raw_action = {
                "tool_name": first_tool.get("name", ""),
                "tool_args": first_tool.get("args", {}),
            }

            # Normalize to unified format using ActionNormalizer
            if agent.action_normalizer:
                llm_action = agent.action_normalizer.from_llm(raw_action)
            else:
                llm_action = raw_action

        # Extract reasoning from content if available
        if hasattr(response, "content") and response.content:
            llm_reasoning = response.content[:500]

    # Track LLM call metrics
    track.llm(
        iter=iteration,
        tokens_in=result.get("tokens_input", 0),
        tokens_out=result.get("tokens_output", 0),
        time_ms=result.get("time_ms", 0),
        tool_calls=1 if has_tool_calls else 0,
        success=llm_action is not None,
    )

    logger.debug("[RVTRACK:LLM] cleared current_item_action=None")

    return {
        "llm_action": llm_action,
        "has_tool_calls": has_tool_calls,
        "llm_reasoning": llm_reasoning,
        "llm_tokens_input": state.get("llm_tokens_input", 0)
        + result.get("tokens_input", 0),
        "llm_tokens_output": state.get("llm_tokens_output", 0)
        + result.get("tokens_output", 0),
        "llm_time_ms": state.get("llm_time_ms", 0) + result.get("time_ms", 0),
        "decision_maker": "llm",
        "current_item_action": None,  # Clear stale value from algorithm iterations
    }
