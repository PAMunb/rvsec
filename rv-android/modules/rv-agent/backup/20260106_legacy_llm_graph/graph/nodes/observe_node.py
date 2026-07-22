"""
LangGraph node for screen observation.

Handles capturing the current application state, parsing UI elements,
computing screen hashes, and preparing messages for LLM decision-making.
"""

import time
import logging
from typing import Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage

from rv_agent.domain.state import AgentState
from rv_agent.agent.dynamic_state_graph import compute_screen_hash_from_description
from rv_agent.llm.graph.prompt_builder import create_enhanced_description, format_strategy_guidance

logger = logging.getLogger(__name__)


def observe(state: AgentState) -> Dict[str, Any]:
    """
    Capture current application state and prepare for decision.

    ### Architectural Decisions:
    - Computes structural hash for state identification
    - Integrates static analysis markers when available
    - Queries strategy for exploration guidance
    - Enriches UI description with coverage annotations
    - Optimizes screenshot for LLM consumption

    ### Integration Points:
    - DeviceInterface for screenshot and XML capture
    - ScreenshotOptimizer for dimension-preserving compression
    - ScreenParser for UI element extraction with MOP markers
    - Strategy for priority guidance computation
    - UICoverageTracker for element testing status
    - DynamicStateGraph for state tracking

    Args:
        state: Current agent state

    Returns:
        Updated state with current observation
    """
    device = state['_device']
    parser = state['_parser']
    static_data = state.get('_static_data')
    strategy = state['_strategy']
    graph = state['_graph']
    optimized_dims = state['optimized_dimensions']

    logger.info("="*80)
    logger.info(f"OBSERVE - Iteration {state['iteration']}")
    logger.info("="*80)

    try:
        # Capture screenshot first (returns file path)
        screenshot_path = device.take_screenshot()
        if not screenshot_path:
            logger.error("Failed to capture screenshot")
            return {"should_continue": False}

        # Get UI state (contains xml, activity, etc)
        ui_state = device.get_current_ui_state()
        if not ui_state:
            logger.error("Failed to get UI state")
            return {"should_continue": False}

        xml_hierarchy = ui_state.get('xml', '')
        activity = ui_state.get('current_activity', 'unknown')
        current_package = ui_state.get('foreground_activity', '').split('/')[0] if ui_state.get('foreground_activity') else ''

        # Detect external navigation (outside target app)
        target_package = state['_package_name']
        is_external = current_package and current_package != target_package
        external_count = state['external_navigation_count']

        if is_external:
            external_count += 1
            logger.warning(
                f"EXTERNAL NAVIGATION #{external_count}: "
                f"target={target_package}, current={current_package}"
            )

            # Force relaunch if max attempts exceeded
            if external_count >= 3:
                logger.error(f"Max external navigation (3) reached - relaunching app")
                device.launch_app(target_package)
                time.sleep(2)
                external_count = 0
                # Re-capture state after relaunch
                ui_state = device.get_current_ui_state()
                xml_hierarchy = ui_state.get('xml', '')
                activity = ui_state.get('current_activity', 'unknown')
                is_external = False
        else:
            # Reset counter when back in app
            if external_count > 0:
                logger.info(f"Returned to target app (was external {external_count} times)")
                external_count = 0

        # Optimize screenshot for LLM (pass file path directly)
        from rv_agent.services.screenshot_optimizer import ScreenshotOptimizer
        optimizer = ScreenshotOptimizer()
        optimized_b64 = optimizer.optimize(
            screenshot_path,
            target_size=optimized_dims
        )

        # Parse UI with static analysis integration FIRST
        screen_desc = parser.parse_screen(
            {"hierarchy": xml_hierarchy, "activity": activity},
            static_data=static_data
        )

        # Compute structural hash from parsed ScreenDescription
        screen_hash = compute_screen_hash_from_description(screen_desc)

        logger.info(f"Screen hash: {screen_hash}, Activity: {activity}")

        # Register state in graph
        node = graph.get_or_create_state(screen_hash, activity, screen_desc)

        logger.info(
            f"State: hash={screen_hash}, activity={activity}, "
            f"visit#{node.visit_count}, coverage={node.get_coverage() * 100:.1f}%, "
            f"actions={len(node.executed_actions)}/{node.total_actions}"
        )

        # Get strategy guidance
        guidance = strategy.get_guidance(screen_hash, screen_desc)

        logger.info(f"Strategy: {guidance['exploration_focus']}")
        logger.info(f"   Untested actions: {guidance.get('untested_count', 0)}/{guidance.get('total_count', 0)}")
        if guidance.get('priority_actions'):
            logger.info(f"   Top priorities: {guidance['priority_actions'][:3]}")

        # Build system prompt with guidance
        system_content = build_system_prompt(
            activity=activity,
            screen_hash=screen_hash,
            screen_desc=screen_desc,
            guidance=guidance,
            visit_count=node.visit_count,
            coverage=node.get_coverage() * 100,
            strategy_name=state['strategy_name'],
            converter=state['_converter']
        )

        # Build user message with warning if external
        user_text = "Analyze this screen and choose ONE action to execute."
        if is_external:
            user_text = f"WARNING: You are OUTSIDE the target app ({target_package})!\n" \
                       f"Current: {current_package} (attempt #{external_count}/3)\n" \
                       f"YOU MUST click on the target app icon or use android_back to return!\n\n" + user_text

        # Create messages: system + user with screenshot
        messages = [
            SystemMessage(content=system_content),
            HumanMessage(
                content=[
                    {"type": "text", "text": user_text},
                    {
                        "type": "image_url",
                        "image_url": f"data:image/jpeg;base64,{optimized_b64}"
                    }
                ]
            )
        ]

        return {
            "screenshot_b64": optimized_b64,
            "current_screen_hash": screen_hash,
            "current_activity": activity,
            "screen_description": screen_desc,
            "messages": messages,
            "external_navigation_count": external_count,
            "is_external": is_external
        }

    except Exception as e:
        logger.error(f"Observation failed: {e}", exc_info=True)
        return {
            "should_continue": False
        }


def build_system_prompt(
    activity: str,
    screen_hash: str,
    screen_desc: Any,
    guidance: Dict[str, Any],
    visit_count: int,
    coverage: float,
    strategy_name: str,
    converter: Any
) -> str:
    """
    Build system prompt with enhanced description and strategy guidance.

    ### Architectural Decisions:
    - Combines coordinate info (WHERE) with strategy guidance (WHAT)
    - Provides explicit coordinates for DOM elements
    - Allows LLM to generate coordinates for visual elements
    - No forcing of coordinate usage - hybrid system
    - Includes MOP markers for prioritization

    Args:
        activity: Current activity name
        screen_hash: Structural hash of screen
        screen_desc: ScreenDescription with UI elements
        guidance: Strategy guidance dictionary
        visit_count: Number of visits to this screen
        coverage: Coverage percentage
        strategy_name: Name of strategy (dfs/bfs)
        converter: CoordinateConverter instance

    Returns:
        System prompt string
    """
    # Generate enhanced description with coordinates
    enhanced_desc = create_enhanced_description(screen_desc, converter)

    # Format strategy guidance
    strategy_text = format_strategy_guidance(guidance)

    # Get counts
    untested = guidance.get('untested_count', 0)
    total = guidance.get('total_count', 0)

    # Build prompt combining both
    prompt = f"""You are an autonomous Android testing agent for security analysis.

CURRENT SCREEN: {screen_hash[:8]}... (Activity: {activity})
VISIT #{visit_count} | Coverage: {coverage:.1f}% ({total - untested}/{total} actions tested)
STRATEGY: {strategy_name.upper()}

{enhanced_desc}

{strategy_text}

INSTRUCTIONS:
1. Analyze the screenshot to understand the current application state
2. Review available UI elements with coordinates above
3. Consider strategy guidance for prioritization
4. You can interact with:
   - Listed elements using their provided coordinates (recommended for precision)
   - Visual elements (buttons, icons) by generating coordinates from screenshot analysis
5. Prioritize elements marked [DM] (directly monitored) or [M] (monitored)
6. All coordinates are in optimized image space ({converter.optimized_width}x{converter.optimized_height})

CRITICAL APP RETENTION RULES:
- STAY WITHIN THE TARGET APPLICATION at all times
- AVOID using android_back or android_home unless absolutely necessary
- If you must go back, prefer clicking visible Back/Cancel buttons over android_back
- Never use android_home during exploration
- Focus on exploring the app's UI elements, not system navigation

Choose ONE action to maximize coverage of monitored operations.
Remaining untested actions: {untested}

Use the available tools to interact with the application.
"""

    return prompt
