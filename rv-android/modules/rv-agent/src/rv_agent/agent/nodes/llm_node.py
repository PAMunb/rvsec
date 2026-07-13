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

    # Attribute this LLM-decided action in the step trace (INV-AGT-52 `llm`
    # channel). The LLM path bypasses the strategy's scored selection, so the
    # trace row is written here — the analog of _select_priority_action writing
    # at selection time. Only genuine LLM choices are recorded; a null action
    # (validation substitutes BACK downstream) is not an LLM decision.
    if llm_action is not None:
        _record_llm_trace(agent, state, llm_action)

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


def _record_llm_trace(
    agent: "RVAgent", state: AgentState, llm_action: Dict[str, Any]
) -> None:
    """Write the step-trace row for an LLM-decided action, if supported.

    Reads the screen the LLM acted on (activity + state hash) and the chosen
    action, then delegates to the strategy's ``record_llm_decision``. Guarded on
    the strategy exposing the method: non-rvagent strategies (dfs/bfs/greedy)
    and mock strategies have no step trace, so this is a no-op for them.
    """
    strategy = getattr(agent, "strategy", None)
    if not hasattr(strategy, "record_llm_decision"):
        return

    screen_desc = state.get("screen_description")
    activity = getattr(screen_desc, "activity", "") or ""
    state_hash = state.get("current_screen_hash", "") or ""

    action_type = llm_action.get("action_type") or llm_action.get("tool_name") or "LLM"
    coords = (llm_action.get("x", 0), llm_action.get("y", 0))

    try:
        strategy.record_llm_decision(
            iteration=state.get("iteration", 0),
            activity=activity,
            state_hash=state_hash,
            action=f"{action_type}@{coords}",
        )
    except Exception as e:  # trace writing must never break the workflow
        logger.warning(f"Failed to record LLM decision trace: {e}")
