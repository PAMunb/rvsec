"""
LLM generate node for RVAgent workflow.

Generates actions using the LLM client with optional navigation guidance.
"""

import logging
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from rv_agent.agent.rv_agent import RVAgent

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
    logger.info("LLM_GENERATE: Calling LLM")

    if not agent.llm_client:
        logger.error("LLM client not available")
        return {
            "llm_action": None,
            "has_tool_calls": False,
            "decision_maker": "llm"
        }

    # Get navigation hint if available
    navigation_hint = ""
    if agent.navigation_guidance and agent.navigation_guidance.is_enabled:
        screen_desc = state.get("screen_description")
        if screen_desc:
            context = agent.navigation_guidance.get_context(screen_desc)
            navigation_hint = agent.navigation_guidance.format_for_llm(context)
            if navigation_hint:
                logger.info(f"LLM_GENERATE: Adding navigation guidance ({len(context.unvisited_screens)} unvisited)")

    # Get screen info for v15 prompt
    screen_line = ""
    screen_hash = state.get("current_screen_hash", "")
    if agent.dynamic_graph and screen_hash:
        screen_line = agent.dynamic_graph.get_screen_line(screen_hash)
        logger.debug(f"LLM_GENERATE: {screen_line}")

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
                "tool_args": first_tool.get("args", {})
            }

            # Normalize to unified format using ActionNormalizer
            if agent.action_normalizer:
                llm_action = agent.action_normalizer.from_llm(raw_action)
                if llm_action:
                    logger.info(
                        f"LLM_GENERATE: Normalized action: {llm_action['action_type']} "
                        f"at ({llm_action['x']}, {llm_action['y']})"
                    )
            else:
                # Fallback if no normalizer (should not happen in production)
                logger.warning("LLM_GENERATE: No ActionNormalizer available")
                llm_action = raw_action

        # Extract reasoning from content if available
        if hasattr(response, "content") and response.content:
            llm_reasoning = response.content[:500]

    if not llm_action:
        logger.warning("LLM_GENERATE: No action extracted from response")

    # Record LLM action metrics for validation
    if agent.metrics_collector and llm_action:
        try:
            ui_xml = state.get("ui_xml", "")
            agent.metrics_collector.record_llm_action(
                iteration=state.get("iteration", 0),
                raw_coords=llm_action.get("original_coords", (0, 0)),
                device_coords=(llm_action.get("x", 0), llm_action.get("y", 0)),
                tool_name=llm_action.get("action_type", "UNKNOWN"),
                tool_args={"text": llm_action.get("text", "")},
                latency_ms=result.get("time_ms", 0),
                tokens_input=result.get("tokens_input", 0),
                tokens_output=result.get("tokens_output", 0),
                parser_strategy=result.get("parse_strategy", "native"),
                activity=state.get("current_activity", "unknown"),
                screen_hash=state.get("current_screen_hash", "unknown"),
                ui_dump=ui_xml,
            )
        except Exception as e:
            logger.warning(f"Failed to record metrics: {e}")

    return {
        "llm_action": llm_action,
        "has_tool_calls": has_tool_calls,
        "llm_reasoning": llm_reasoning,
        "llm_tokens_input": state.get("llm_tokens_input", 0) + result.get("tokens_input", 0),
        "llm_tokens_output": state.get("llm_tokens_output", 0) + result.get("tokens_output", 0),
        "llm_time_ms": state.get("llm_time_ms", 0) + result.get("time_ms", 0),
        "decision_maker": "llm"
    }
