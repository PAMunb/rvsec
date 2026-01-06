"""
LangGraph node for learning and memory updates.

Handles processing action results, updating memory systems,
and recording state transitions.
"""

import time
import json
import logging
from typing import Dict, Any

from rv_agent.domain.state import AgentState
from rv_agent.services.action_mapper import map_coordinates_to_action

logger = logging.getLogger(__name__)


def update_memories(state: AgentState) -> Dict[str, Any]:
    """
    Map LLM action to ScreenItem/ItemAction and update memories.

    ### Architectural Decisions:
    - Handles coordinate conversion from optimized to device space
    - Maps coordinates to ScreenItem using bounds lookup
    - Selects appropriate ItemAction from ScreenItem.actions
    - Updates all memory systems in centralized location
    - Captures next state after action execution

    ### Integration Points:
    - ActionMapper for coordinate -> action resolution
    - DynamicStateGraph for state tracking
    - LongTermMemory, ShortTermMemory, UICoverageTracker
    - DeviceInterface for next state capture
    - Strategy for transition recording

    Args:
        state: Current agent state

    Returns:
        Updated state with incremented iteration
    """
    logger.info("UPDATE_MEMORIES - Processing action result")

    # Extract tool call result from last message
    last_msg = state['messages'][-1]
    tool_result = extract_tool_result(last_msg)

    if not tool_result:
        logger.warning("No tool result found in last message")
        return {"iteration": state['iteration'] + 1}

    if not tool_result.get('success'):
        # Tool failed, just log and continue
        logger.warning(f"Tool execution failed: {tool_result.get('error', 'Unknown error')}")
        return {"iteration": state['iteration'] + 1}

    logger.info(f"Tool executed: {tool_result.get('action_type', 'unknown')}")

    # Get dependencies
    graph = state['_graph']
    long_term = state['_long_term']
    short_term = state['_short_term']
    ui_coverage = state['_ui_coverage']
    strategy = state['_strategy']
    current_hash = state['current_screen_hash']

    # Check if action has coordinates (some actions like back/home don't)
    llm_coords = tool_result.get('llm_coords')
    action_type = tool_result.get('action_type', 'click')

    if llm_coords:
        try:
            # Map LLM coordinates to action ID
            action_id = map_coordinates_to_action(
                llm_coords=llm_coords,
                action_type=action_type,
                screen_description=state['screen_description'],
                optimized_dims=state['optimized_dimensions'],
                device_dims=state['device_dimensions']
            )

            logger.info(f"Mapped to action_id: {action_id}")

            # Get action details for memory recording
            action = state['screen_description'].get_action_by_id(action_id)
            action_text = action.text if action else f"{action_type} (id:{action_id})"

            # Update graph with executed action
            graph.record_action(current_hash, action_id)

            # Update memories
            # Note: to_state will be captured in next observe cycle
            long_term.record_action(
                action_id=action_id,
                action_text=action_text,
                action_type=action_type,
                success=True,  # Tool succeeded
                from_state=current_hash,
                to_state=None  # Will be set in next iteration
            )

            # Record iteration in short term memory
            state_dict = {
                'activity': state['current_activity'],
                'hash_screen': current_hash
            }
            action_dict = {
                'action_id': action_id,
                'action_type': action_type,
                'element_id': action_text
            }
            short_term.record_iteration(state_dict, [action_dict])
            ui_coverage.record_interaction(action_id, current_hash)

            logger.info(f"Memories updated for action {action_id}")

        except ValueError as e:
            logger.warning(f"Action mapping failed: {e}")
            # Continue anyway - the action was executed even if we can't map it

    else:
        # System action (back, home) - no coordinate mapping needed
        logger.info(f"System action: {action_type}")

        # Record system action in short term memory
        state_dict = {
            'activity': state['current_activity'],
            'hash_screen': current_hash
        }
        action_dict = {
            'action_id': None,
            'action_type': action_type,
            'element_id': f'system_{action_type}'
        }
        short_term.record_iteration(state_dict, [action_dict])

    # Wait for UI to settle after action
    time.sleep(1)

    # Capture next state for transition recording (optional)
    # The next observe() will handle full state capture

    return {"iteration": state['iteration'] + 1}


def extract_tool_result(message: Any) -> Dict[str, Any]:
    """
    Extract tool result from message.

    Args:
        message: Message object from LangGraph

    Returns:
        Tool result dictionary or empty dict
    """
    # LangGraph stores tool results in message.content
    # The exact structure depends on LangChain/LangGraph version

    try:
        if hasattr(message, 'content'):
            content = message.content
            if isinstance(content, dict):
                return content
            elif isinstance(content, str):
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    return {}

        # Fallback: check for tool_calls attribute
        if hasattr(message, 'tool_calls') and message.tool_calls:
            # Return result from first tool call
            return message.tool_calls[0].get('output', {})

        return {}

    except Exception as e:
        logger.warning(f"Failed to extract tool result: {e}")
        return {}
