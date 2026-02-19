"""
Learn node for RVAgent workflow.

Updates memory systems, detects stuck states, and manages recovery strategies.

Key Design Decisions:

1. VALIDATION ERROR DETECTION (before stuck detection)
   When the screen is unchanged and a screenshot is available, checks for visual
   validation errors (red icons, error borders) before assuming the agent is stuck.
   Uses 3-way branching:
     (a) No screenshot (screen changed) -> reset error_recovery_count, clear state
     (b) Screenshot exists, max recovery reached -> skip detection, let stuck logic handle it
     (c) Screenshot exists, count < max -> run detection, set force_fill_input if error found

2. STUCK STATE DETECTION (Two-Level)
   Level 1 - Screen unchanged: After dynamic threshold of unchanged screens, force BACK.
             Threshold = max(BASE_STUCK_THRESHOLD, num_elements * STUCK_THRESHOLD_FACTOR)
             Form actions (SET_TEXT, checkable elements) are excluded from counting.
   Level 2 - StuckRecovery: After max_blocks iterations in same state, try:
     a) Backtrack BFS: Find nearest unsaturated ancestor state
     b) App Restart: Force stop and relaunch if BFS fails

3. BACKTRACK BFS (from APE paper)
   When Level 2 stuck is detected, uses SuccessorTracker.find_nearest_unsaturated()
   to find an ancestor state with unexplored actions. If found, navigates there
   via BACK. If no unsaturated ancestor exists, triggers app restart.

4. BACK TRANSITION RECORDING
   Records where BACK leads from each state. This builds a navigation graph
   that Backtrack BFS uses to find paths to unsaturated ancestors.

5. INTERACTION WITH ALGORITHM_NODE
   - force_back_action=True: Generates BACK action
   - force_restart_app=True: Generates RESTART_APP action
   - force_fill_input=True: Triggers input filling for error recovery
   This maintains separation between detection (learn_node) and action generation.

6. UI COVERAGE TRACKING
   Records which elements were interacted with for coverage metrics.
   Uses proximity matching because LLM clicks may not be exactly at element centers.
"""

import logging
from typing import TYPE_CHECKING, Dict, Any, Optional

if TYPE_CHECKING:
    from rv_agent.agent.rv_agent import RVAgent

from rv_agent.domain.state import AgentState
from rv_agent import tracking as track
from rv_agent.constants import RVAgentConstants
from rv_agent.services.coordinate_utils import device_to_optimized
from rv_agent.services.error_detection import VisualErrorDetector, ValidationErrorResult

logger = logging.getLogger(__name__)

# After this many consecutive error recovery attempts on the same screen,
# stop detecting and let the normal stuck detection handle it. Prevents
# infinite force_fill_input loops on screens with persistent red decorations.
MAX_ERROR_RECOVERY = 3


def _get_dynamic_stuck_threshold(agent: "RVAgent", state: AgentState) -> int:
    """
    Calculate stuck threshold based on screen complexity.

    More elements on screen = more iterations allowed before forcing BACK.
    This prevents premature backtracking on complex screens.

    Args:
        agent: RVAgent instance with BASE_STUCK_THRESHOLD and STUCK_THRESHOLD_FACTOR
        state: Current agent state with available_actions

    Returns:
        Dynamic threshold: max(base, num_elements * factor)
    """
    base = getattr(agent, 'BASE_STUCK_THRESHOLD', 8)
    factor = getattr(agent, 'STUCK_THRESHOLD_FACTOR', 1.5)

    # Get number of available actions (interactive elements)
    available_actions = state.get("available_actions", [])
    num_elements = len(available_actions)

    # Calculate dynamic threshold
    dynamic_threshold = max(base, int(num_elements * factor))

    return dynamic_threshold


def _detect_validation_error(
    agent: "RVAgent", screenshot_path: str
) -> Optional[ValidationErrorResult]:
    """Detect validation errors in a screenshot using visual color analysis.

    Delegate to VisualErrorDetector, which scans for red-colored indicators
    (error icons, border highlights) that suggest form validation failures.
    The caller is responsible for loop protection (MAX_ERROR_RECOVERY) —
    this function only checks the enabled flag and runs detection.

    Args:
        agent: RVAgent instance. Uses agent.config for error_detection_enabled,
            error_detection_confidence, error_max_indicator_size, and
            error_max_indicator_count thresholds.
        screenshot_path: Absolute path to the screenshot image file.

    Returns:
        ValidationErrorResult with detected=True/False and error_indicators
        list if detection ran. None if error detection is disabled in config.
    """
    if not agent.config.error_detection_enabled:
        return None

    detector = VisualErrorDetector()
    return detector.detect(
        screenshot_path,
        confidence_threshold=agent.config.error_detection_confidence,
        max_indicator_size=agent.config.error_max_indicator_size,
        max_indicator_count=agent.config.error_max_indicator_count,
    )


def learn_node(agent: "RVAgent", state: AgentState) -> Dict[str, Any]:
    """
    Update memory systems and prepare for next iteration.

    Handles memory updates, summary generation, state tracking,
    stuck state detection, and continuation checks.

    Args:
        agent: RVAgent instance with memory_coordinator and stuck detection
        state: Current agent state

    Returns:
        State updates with memories, summaries, and continuation flags
    """
    iteration = state.get("iteration", 0)

    # Update memories
    memory_result = agent.memory_coordinator.update_memories(
        current_screen_hash=state.get("current_screen_hash", "unknown"),
        current_activity=state.get("current_activity", "unknown"),
        screen_description=state.get("screen_description"),
        action=state.get("current_action"),
        llm_reasoning=state.get("llm_reasoning", ""),
        iteration=state.get("iteration", 0),
        recent_action_window=state.get("recent_action_window", [])
    )

    # Generate summaries
    summaries = agent.memory_coordinator.generate_summaries(
        action=state.get("current_action"),
        current_activity=state.get("current_activity", "unknown"),
        visited_states=state.get("visited_states", []),
        state_transitions=state.get("state_transitions", [])
    )

    # Track state discovery
    tracking = agent.memory_coordinator.track_state_discovery(
        current_hash=state.get("current_screen_hash"),
        previous_hash=state.get("previous_screen_hash"),
        visited_states=state.get("visited_states", []),
        state_transitions=state.get("state_transitions", [])
    )

    # Record BACK transitions for Backtrack BFS
    _record_back_transition(agent, state)

    # Record action success for strength-based scoring
    _record_action_success(agent, state)

    # Propagate reward based on action outcome
    _propagate_reward(agent, state)

    # --- Validation error detection (before stuck detection) ---
    #
    # WHY 3-way branching:
    # The error_detection_screenshot field is set by parse_node ONLY when the
    # screen hash is unchanged (same UI). Its presence signals "screen didn't
    # change, maybe there's a validation error." Its absence means the screen
    # changed normally, so any previous error state is stale.
    #
    # Branch (a) resets the counter because a screen change means the agent
    # moved past the error — fresh budget for the next error screen.
    #
    # Branch (b) does NOT reset the counter. The screen is still unchanged
    # and we've exhausted recovery attempts. Resetting would create an
    # infinite loop: detect -> force_fill -> same screen -> detect again.
    # Instead we stop detecting and let Level 1/2 stuck recovery handle it
    # (BACK or restart), which actually changes the screen.
    #
    # Branch (c) runs detection while budget remains, giving force_fill_input
    # a chance to fix the validation error (e.g., re-type a form field).
    screenshot_path = state.get("error_detection_screenshot")
    error_detected = False
    error_result_updates = {}

    if screenshot_path is None:
        # Branch (a): Screen changed since last iteration. Reset recovery counter
        # and defensively clear error state to avoid stale force_fill from previous iter.
        agent.error_recovery_count = 0
        error_result_updates["force_fill_input"] = False
        error_result_updates["error_indicators"] = None
    elif agent.error_recovery_count >= MAX_ERROR_RECOVERY:
        # Branch (b): Screen is stuck with a screenshot, but we already tried
        # MAX_ERROR_RECOVERY times. Stop detecting — let normal stuck detection
        # (Level 1/2) take over. Counter stays at current value.
        pass
    else:
        # Branch (c): Screenshot available and recovery budget remaining. Run detection.
        validation_result = _detect_validation_error(agent, screenshot_path)
        if validation_result and validation_result.detected:
            error_detected = True
            agent.error_recovery_count += 1
            agent.stuck_screen_count = 0  # Suppress stuck detection for this iteration

            error_result_updates["force_fill_input"] = True
            error_result_updates["error_indicators"] = validation_result.error_indicators

            track.error(
                iter=iteration,
                indicators_count=len(validation_result.error_indicators),
                confidence=validation_result.confidence,
                method=validation_result.detection_method,
                filtered_by_size=validation_result.filtered_by_size,
                filtered_by_region=validation_result.filtered_by_region,
                filtered_by_count=validation_result.filtered_by_count,
            )
        elif validation_result is not None:
            # Detection ran but found no error — the screen is unchanged for other
            # reasons. Reset counter so future errors on new screens start fresh.
            agent.error_recovery_count = 0

    # Two-level stuck state detection
    current_hash = state.get("current_screen_hash")
    force_back = False
    force_restart = False

    # Get current action info for stuck detection logic
    current_action = state.get("current_action", {})
    action_type = (current_action.get("action_type", "") if current_action else "").upper()

    # Check if action was on a checkable element (checkbox, radio, toggle)
    item_action = state.get("current_item_action")
    is_checkable = False
    if item_action and hasattr(item_action, 'target_view'):
        is_checkable = item_action.target_view.get("checkable", False)

    # Level 1: Screen unchanged detection (quick recovery via BACK)
    # Skip stuck counting for actions that don't change screen hash:
    # - SET_TEXT: filling form fields
    # - Checkable elements: checkbox/radio/toggle state changes
    #
    # Dynamic threshold: more elements = more iterations allowed
    # threshold = max(BASE_STUCK_THRESHOLD, num_elements * STUCK_THRESHOLD_FACTOR)
    dynamic_threshold = _get_dynamic_stuck_threshold(agent, state)

    is_form_action = action_type in ("SET_TEXT", "TEXT_CHANGE") or is_checkable
    if current_hash == agent.last_screen_hash and not is_form_action and not error_detected:
        agent.stuck_screen_count += 1
        if agent.stuck_screen_count >= dynamic_threshold:
            force_back = True
            agent.stuck_screen_count = 0
    else:
        agent.stuck_screen_count = 0

    agent.last_screen_hash = current_hash

    # Level 2: StuckRecovery check (persistent stuck state)
    stuck_recovery = getattr(agent, 'stuck_recovery', None)
    if stuck_recovery and current_hash:
        recovery_action = stuck_recovery.check(current_hash)

        if recovery_action == "restart":
            # Try Backtrack BFS first
            successor_tracker = getattr(agent.strategy, 'successor_tracker', None)
            if successor_tracker:
                bfs_result = successor_tracker.find_nearest_unsaturated(current_hash)
                if bfs_result:
                    unsaturated_target, hop_count = bfs_result
                    logger.info(
                        f"Level 2 stuck: Backtrack BFS found unsaturated state "
                        f"{unsaturated_target[:8]}... ({hop_count} hops) -> Forcing BACK"
                    )
                    force_back = True
                    # Track backtrack decision
                    track.backtrack(
                        iter=iteration,
                        from_state=current_hash,
                        to_state=unsaturated_target,
                        reason="bfs_unsaturated"
                    )
                else:
                    logger.warning(
                        "Level 2 stuck: No unsaturated ancestor found -> Forcing RESTART"
                    )
                    force_restart = True
                    stuck_recovery.record_restart()
                    # Track backtrack failure
                    track.backtrack(
                        iter=iteration,
                        from_state=current_hash,
                        to_state="restart",
                        reason="no_unsaturated"
                    )
            else:
                logger.warning(
                    "Level 2 stuck: No successor_tracker available -> Forcing RESTART"
                )
                force_restart = True
                stuck_recovery.record_restart()

    # Check continuation
    continuation = agent.memory_coordinator.check_continuation(
        start_time=state.get("start_time"),
        timeout=state.get("timeout")
    )

    # Track state changes
    previous_activity = state.get("previous_activity")
    current_activity = state.get("current_activity")
    activity_changed = previous_activity != current_activity and previous_activity is not None

    track.state(
        iter=iteration,
        changed=activity_changed,
        activity_from=previous_activity,
        activity_to=current_activity,
        hash=current_hash
    )

    # Track learning/stuck detection
    stuck_reason = None
    if force_restart:
        stuck_reason = "level2_restart"
    elif force_back:
        stuck_reason = "level1_back"

    track.learn(
        iter=iteration,
        stuck=force_back or force_restart,
        memory_updated=True,
        stuck_reason=stuck_reason,
        error_detected=error_detected,
    )

    # Track LLM-generated text values to prevent repetition via value_generator
    _track_llm_text_value(agent, state)

    result = {
        "recent_action_window": memory_result["recent_action_window"],
        "action_history_summary": summaries["action_history_summary"],
        "exploration_summary": summaries["exploration_summary"],
        "memory_insights": summaries["memory_insights"],
        "navigation_path": summaries["navigation_path"],
        "visited_states": tracking["visited_states"],
        "state_transitions": tracking["state_transitions"],
        "previous_screen_hash": state.get("current_screen_hash"),
        "should_continue": continuation["should_continue"],
        "loop_detected": False
    }

    if force_restart:
        result["force_restart_app"] = True
    elif force_back:
        result["force_back_action"] = True

    # Merge error detection results into output state
    result.update(error_result_updates)

    # NOTE: UI coverage interaction is recorded in execute_node.py
    # using device-space coordinates (not normalized [0,1000))

    return result


def _record_back_transition(agent: "RVAgent", state: AgentState) -> None:
    """
    Record BACK transitions for Backtrack BFS navigation.

    When a BACK action is executed and the screen changes, records the
    transition in SuccessorTracker.back_successors. This builds a graph
    of where BACK leads from each state.

    Args:
        agent: RVAgent instance with strategy.successor_tracker
        state: Current agent state with action and hash information
    """
    try:
        current_action = state.get("current_action")
        if not current_action:
            return

        action_type = current_action.get("action_type", "").upper()
        if action_type != "BACK":
            return

        previous_hash = state.get("previous_screen_hash")
        current_hash = state.get("current_screen_hash")

        if not previous_hash or not current_hash:
            return

        if previous_hash == current_hash:
            return

        successor_tracker = getattr(agent.strategy, 'successor_tracker', None)
        if successor_tracker:
            successor_tracker.record_back_transition(previous_hash, current_hash)
            logger.debug(
                f"Recorded BACK transition: {previous_hash[:8]}... -> {current_hash[:8]}..."
            )

    except Exception as e:
        logger.warning(f"Failed to record BACK transition: {e}")


def _record_action_success(agent: "RVAgent", state: AgentState) -> None:
    """
    Record action success/failure for strength-based scoring.

    Success Definition: An action is considered successful if it caused
    a state transition (screen hash changed after execution).

    TODO(#20): This heuristic has limitations — actions that change
    internal state without changing UI are marked as failures, and actions
    that open transient dialogs may give false positives. Future improvements
    could use additional signals (activity change, new elements).

    Args:
        agent: RVAgent instance with strategy and graph
        state: Current agent state with previous/current hashes and action info
    """
    try:
        previous_hash = state.get("previous_screen_hash")
        current_hash = state.get("current_screen_hash")
        current_action = state.get("current_action")
        iteration = state.get("iteration", 0)

        if not previous_hash or not current_hash or not current_action:
            return

        # Get action coordinates
        x = current_action.get("x")
        y = current_action.get("y")
        action_type = current_action.get("action_type", "CLICK")

        if x is None or y is None:
            return

        # Convert to optimized space (same as scorers)
        converter = getattr(agent.strategy, 'converter', None)
        if converter:
            opt_x, opt_y = converter.device_to_optimized(x, y)
        else:
            opt_x, opt_y = device_to_optimized(
                x, y,
                (RVAgentConstants.DEFAULT_DEVICE_WIDTH, RVAgentConstants.DEFAULT_DEVICE_HEIGHT),
                (RVAgentConstants.SCREENSHOT_TARGET_WIDTH, RVAgentConstants.SCREENSHOT_TARGET_HEIGHT)
            )

        action_signature = ((opt_x, opt_y), action_type)

        # Get the node where the action was executed (previous state)
        graph = getattr(agent.strategy, 'graph', None)
        if not graph:
            return

        node = graph.states.get(previous_hash)
        if not node:
            return

        # Success = state changed
        success = previous_hash != current_hash

        # Record success in node
        node.record_action_success(action_signature, success)

        # Track strength
        executions = node.get_action_execution_count(action_signature)
        successes = node.action_success_counts.get(action_signature, 0)
        strength_val = node.get_action_strength(action_signature)

        track.strength(
            iter=iteration,
            action=action_type,
            coords=(x, y),
            strength_val=strength_val,
            executions=executions,
            successes=successes
        )

        logger.debug(
            f"Action success recorded: {action_signature} "
            f"success={success} strength={strength_val:.2f}"
        )

    except Exception as e:
        logger.warning(f"Failed to record action success: {e}")


def _propagate_reward(agent: "RVAgent", state: AgentState) -> None:
    """
    Record action in reward history and propagate reward based on outcome.

    Determines reward type using priority order:
    1. mop_reached: action has callback_signature (MOP method triggered)
    2. new_activity: screen changed AND activity not seen before
    3. new_state: screen changed AND activity already seen
    4. form_fill: screen unchanged AND action was SET_TEXT/TEXT_CHANGE
    5. same_state: screen unchanged AND action was not text input
    """
    try:
        reward_propagator = getattr(agent.strategy, 'reward_propagator', None)
        if not reward_propagator:
            return

        previous_hash = state.get("previous_screen_hash")
        current_hash = state.get("current_screen_hash")
        current_action = state.get("current_action")

        if not previous_hash or not current_hash or not current_action:
            return

        x = current_action.get("x")
        y = current_action.get("y")
        action_type = current_action.get("action_type", "CLICK")

        if x is None or y is None:
            return

        # Convert to optimized space (same as _record_action_success)
        converter = getattr(agent.strategy, 'converter', None)
        if converter:
            opt_x, opt_y = converter.device_to_optimized(x, y)
        else:
            opt_x, opt_y = device_to_optimized(
                x, y,
                (RVAgentConstants.DEFAULT_DEVICE_WIDTH, RVAgentConstants.DEFAULT_DEVICE_HEIGHT),
                (RVAgentConstants.SCREENSHOT_TARGET_WIDTH, RVAgentConstants.SCREENSHOT_TARGET_HEIGHT)
            )

        action_signature = ((opt_x, opt_y), action_type)
        reward_propagator.record_action(previous_hash, action_signature)

        # Determine reward type (priority: mop > new_activity > new_state > form_fill > same_state)
        selected_action = state.get("current_item_action")
        has_mop = (
            selected_action
            and hasattr(selected_action, 'callback_signature')
            and selected_action.callback_signature
        )

        if has_mop:
            reward_type = "mop_reached"
        elif previous_hash != current_hash:
            # Screen changed — check if it's a new activity
            current_activity = state.get("current_activity", "")
            visited_activities = getattr(agent.strategy, '_get_visited_activities', lambda: set())()
            if current_activity and current_activity not in visited_activities:
                reward_type = "new_activity"
            else:
                reward_type = "new_state"
        else:
            # Screen unchanged
            if action_type.upper() in ("SET_TEXT", "TEXT_CHANGE"):
                reward_type = "form_fill"
            else:
                reward_type = "same_state"

        graph = getattr(agent.strategy, 'graph', None)
        if graph:
            reward_propagator.propagate(reward_type, graph)

    except Exception as e:
        logger.warning(f"Failed to propagate reward: {e}")


def _track_llm_text_value(agent: "RVAgent", state: AgentState) -> None:
    """
    Record LLM-generated text values in InputValueGenerator to prevent repetition.

    When the LLM generates a SET_TEXT action, the text value is recorded in
    value_generator.tested_values so the algorithm path doesn't re-test it.

    Args:
        agent: RVAgent instance with strategy.value_generator
        state: Current agent state with action and decision_maker info
    """
    try:
        decision_maker = state.get("decision_maker")
        if decision_maker != "llm":
            return

        current_action = state.get("current_action")
        if not current_action:
            return

        action_type = (current_action.get("action_type", "")).upper()
        if action_type not in ("SET_TEXT", "TEXT_CHANGE"):
            return

        text = current_action.get("text", "")
        if not text:
            return

        # Get element ID from item_action or coordinates
        item_action = state.get("current_item_action")
        if item_action and hasattr(item_action, 'widget_id') and item_action.widget_id:
            element_id = item_action.widget_id
        else:
            x = current_action.get("x")
            y = current_action.get("y")
            if x is not None and y is not None:
                element_id = f"({x},{y})"
            else:
                return

        value_generator = getattr(agent.strategy, 'value_generator', None)
        if not value_generator:
            return

        if text not in value_generator.tested_values.get(element_id, []):
            value_generator.tested_values[element_id].append(text)
            logger.debug(f"Tracked LLM text for {element_id}: '{text[:20]}'")

    except Exception as e:
        logger.warning(f"Failed to track LLM text value: {e}")
