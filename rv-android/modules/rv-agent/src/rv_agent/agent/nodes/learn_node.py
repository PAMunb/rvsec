"""
Update memory systems, detect stuck states, and manage recovery strategies.

This module implements the learn node of the RVAgent LangGraph workflow. After each
action execution, learn_node processes the outcome: updates memory systems, records
state transitions, detects validation errors and stuck states, and sets flags that
guide the next iteration's action generation. The node bridges observation (what
happened) and planning (what to do next) by translating evidence into control signals.

### Architectural Decisions:

- Validation error detection runs BEFORE stuck detection so that form validation
  failures (red icons, error borders) are handled by force_fill_input instead of
  being misclassified as stuck states. A 3-way branch handles the cases: (a) screen
  changed -- reset, (b) recovery budget exhausted -- defer to stuck logic, (c)
  budget remaining -- run detection.
- Two-level stuck detection: Level 1 uses a dynamic threshold based on screen
  complexity (more elements = more patience before forcing BACK). Level 2 uses
  StuckRecovery with Backtrack BFS (APE paper) to find unsaturated ancestors, falling
  back to app restart when no ancestor exists.
- Detection vs. action generation separation: learn_node sets flags (force_back_action,
  force_restart_app, force_fill_input) that algorithm_node reads to generate the
  appropriate action. This keeps detection logic in one place and action generation
  in another.
- BACK transition recording builds a navigation graph used by Backtrack BFS.
  Each time BACK causes a screen change, the transition is stored in
  SuccessorTracker.back_successors.

### Role in the System:

- Final node in the LangGraph workflow iteration, executed after execute_node.
- Consumes action execution results and produces state updates for the next iteration.
- Coordinates with MemoryCoordinator for memory updates and summary generation.
- Sets control flags read by decision_node and algorithm_node.

### Integration Points:

- Input: AgentState from execute_node (screen hashes, action info, screenshots).
- Output: Dict of state updates merged into AgentState for the next iteration.
- Dependencies: MemoryCoordinator, SuccessorTracker, StuckRecovery, RewardPropagator,
  VisualErrorDetector, PathBuffer, InputValueGenerator.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from rv_agent.agent.rv_agent import RVAgent

from rv_agent import tracking as track
from rv_agent.domain.state import AgentState
from rv_agent.memory.element_id import make_element_id
from rv_agent.services.error_detection import ValidationErrorResult, VisualErrorDetector

logger = logging.getLogger(__name__)

# After this many consecutive error recovery attempts on the same screen,
# stop detecting and let the normal stuck detection handle it. Prevents
# infinite force_fill_input loops on screens with persistent red decorations.
MAX_ERROR_RECOVERY = 3


def _get_dynamic_stuck_threshold(agent: "RVAgent", state: AgentState) -> int:
    """Calculate stuck threshold based on screen complexity.

    More elements on screen means more iterations allowed before forcing BACK.
    This prevents premature backtracking on complex screens with many
    interactive elements. Counts elements from screen_description.items.

    Args:
        agent: RVAgent instance with BASE_STUCK_THRESHOLD and STUCK_THRESHOLD_FACTOR.
        state: Current agent state with screen_description.

    Returns:
        Dynamic threshold: max(base, num_elements * factor).
    """
    base = getattr(agent, "BASE_STUCK_THRESHOLD", 8)
    factor = getattr(agent, "STUCK_THRESHOLD_FACTOR", 1.5)

    # Count interactive elements from the parsed screen description
    screen_desc = state.get("screen_description")
    num_elements = 0
    if screen_desc is not None:
        items = getattr(screen_desc, "items", None)
        if items is not None:
            num_elements = len(items)

    # Calculate dynamic threshold
    dynamic_threshold = max(base, int(num_elements * factor))

    # Cap below Level 2 threshold so Level 1 (BACK) always fires before Level 2 (restart)
    stuck_recovery = getattr(agent, "stuck_recovery", None)
    if stuck_recovery:
        dynamic_threshold = min(dynamic_threshold, stuck_recovery.max_blocks - 1)

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
    """Update memory systems, detect issues, and prepare for next iteration.

    Process the outcome of the last executed action through six phases: memory
    update, transition recording, validation error detection, stuck state
    detection, continuation check, and result assembly. Sets control flags
    (force_back_action, force_restart_app, force_fill_input) that drive the
    next iteration's action generation in algorithm_node.

    Args:
        agent: RVAgent instance with memory_coordinator, stuck_recovery,
            strategy (with successor_tracker, reward_propagator, path_buffer,
            value_generator), and error_recovery_count state.
        state: Current agent state containing screen hashes, action info,
            error_detection_screenshot, and timing data.

    Returns:
        Dictionary with keys:
        - "recent_action_window" (list): Sliding window of recent actions.
        - "action_history_summary" (str): Human-readable action history.
        - "exploration_summary" (str): Exploration progress summary.
        - "memory_insights" (str): Insights from memory analysis.
        - "navigation_path" (str): Current navigation path description.
        - "visited_states" (list): Updated list of visited state hashes.
        - "state_transitions" (list): Updated state transition log.
        - "previous_screen_hash" (str): Current hash stored for next iteration.
        - "should_continue" (bool): Whether the agent should keep running.
        - "loop_detected" (bool): Always False (legacy key, kept for state schema).
        - "force_back_action" (bool): Set when Level 1 or BFS stuck detected.
        - "force_restart_app" (bool): Set when Level 2 stuck with no ancestor.
        - "force_fill_input" (bool): Set when validation error detected.
        - "error_indicators" (list or None): Visual error indicator data.
    """
    iteration = state.get("iteration", 0)

    # Phase 1: Memory updates and summary generation
    memory_result = agent.memory_coordinator.update_memories(
        current_screen_hash=state.get("current_screen_hash", "unknown"),
        current_activity=state.get("current_activity", "unknown"),
        screen_description=state.get("screen_description"),
        action=state.get("current_action"),
        llm_reasoning=state.get("llm_reasoning", ""),
        iteration=state.get("iteration", 0),
        recent_action_window=state.get("recent_action_window", []),
    )

    summaries = agent.memory_coordinator.generate_summaries(
        action=state.get("current_action"),
        current_activity=state.get("current_activity", "unknown"),
        visited_states=state.get("visited_states", []),
        state_transitions=state.get("state_transitions", []),
    )

    tracking = agent.memory_coordinator.track_state_discovery(
        current_hash=state.get("current_screen_hash"),
        previous_hash=state.get("previous_screen_hash"),
        visited_states=state.get("visited_states", []),
        state_transitions=state.get("state_transitions", []),
    )

    # Phase 2: Transition recording and reward propagation
    _record_back_transition(agent, state)
    _record_action_success(agent, state)
    _propagate_reward(agent, state)
    _invalidate_stale_path_buffer(agent, state)

    # Phase 3: Validation error detection (before stuck detection)
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

    # Skip error detection if last action was stuck recovery BACK —
    # error detection would waste 3 iterations on a screen we're leaving.
    if getattr(agent, "_last_action_was_stuck_back", False):
        agent._last_action_was_stuck_back = False
        screenshot_path = None  # Force Branch (a) — reset counter, clear state
    else:
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
            error_result_updates["error_indicators"] = (
                validation_result.error_indicators
            )

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

    # Phase 4: Two-level stuck state detection
    current_hash = state.get("current_screen_hash")
    force_back = False
    force_restart = False

    # Get current action info for stuck detection logic
    current_action = state.get("current_action", {})
    action_type = (
        current_action.get("action_type", "") if current_action else ""
    ).upper()

    # Check if action was on a checkable element (checkbox, radio, toggle)
    item_action = state.get("current_item_action")
    is_checkable = False
    if item_action and hasattr(item_action, "target_view"):
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
    if (
        current_hash is not None
        and current_hash == agent.last_screen_hash
        and not is_form_action
        and not error_detected
    ):
        agent.stuck_screen_count += 1
        if agent.stuck_screen_count >= dynamic_threshold:
            force_back = True
            agent.stuck_screen_count = 0
            agent._last_action_was_stuck_back = True
    else:
        agent.stuck_screen_count = 0

    agent.last_screen_hash = current_hash

    # Level 2: StuckRecovery check (persistent stuck state)
    stuck_recovery = getattr(agent, "stuck_recovery", None)
    if stuck_recovery and current_hash:
        recovery_action = stuck_recovery.check(
            current_hash, is_form_action=is_form_action
        )
        if is_form_action:
            track.strategy(
                iter=iteration,
                mode="stuck",
                action_type=action_type,
                reason=f"is_form={is_form_action}",
            )

        if recovery_action == "restart":
            # Try Backtrack BFS first
            successor_tracker = getattr(agent.strategy, "successor_tracker", None)
            if successor_tracker:
                bfs_result = successor_tracker.find_nearest_unsaturated(current_hash)
                if bfs_result:
                    unsaturated_target, hop_count = bfs_result
                    logger.info(
                        f"Level 2 stuck: Backtrack BFS found unsaturated state "
                        f"{unsaturated_target[:8]}... ({hop_count} hops)"
                    )
                    # Queue multi-hop BACK in PathBuffer if available
                    path_buffer = getattr(agent.strategy, "path_buffer", None)
                    if path_buffer and hop_count > 1:
                        path_buffer.load_back_actions(hop_count)
                        logger.info(
                            f"Level 2 stuck: Queued {hop_count} BACK actions via PathBuffer"
                        )
                    else:
                        force_back = True
                    agent._last_action_was_stuck_back = True
                    # Track backtrack decision
                    track.backtrack(
                        iter=iteration,
                        from_state=current_hash,
                        to_state=unsaturated_target,
                        reason="bfs_unsaturated",
                        strategy="bfs_stuck",
                        remaining_steps=hop_count,
                    )
                else:
                    logger.warning(
                        "Level 2 stuck: No unsaturated ancestor found -> Forcing RESTART"
                    )
                    force_restart = True
                    stuck_recovery.record_restart()
                    agent._last_action_was_stuck_back = True
                    # Track backtrack failure
                    track.backtrack(
                        iter=iteration,
                        from_state=current_hash,
                        to_state="restart",
                        reason="no_unsaturated",
                    )
            else:
                logger.warning(
                    "Level 2 stuck: No successor_tracker available -> Forcing RESTART"
                )
                force_restart = True
                stuck_recovery.record_restart()
                agent._last_action_was_stuck_back = True

    # Phase 5: Continuation check and tracking
    continuation = agent.memory_coordinator.check_continuation(
        start_time=state.get("start_time"), timeout=state.get("timeout")
    )

    previous_activity = state.get("previous_activity")
    current_activity = state.get("current_activity")
    activity_changed = (
        previous_activity != current_activity and previous_activity is not None
    )

    track.state(
        iter=iteration,
        changed=activity_changed,
        activity_from=previous_activity,
        activity_to=current_activity,
        hash=current_hash,
    )

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

    _track_llm_text_value(agent, state)

    # Phase 6: Assemble result state
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
        "loop_detected": False,
    }

    if force_restart:
        result["force_restart_app"] = True
        # Invalidate screen_desc cache: after app restart the UI state is unknown
        agent._cached_screen_desc = None
    elif force_back:
        result["force_back_action"] = True

    # Merge error detection results into output state
    result.update(error_result_updates)

    # Store current action's signature for next iteration's attribution
    # (one-iteration offset: next iteration's learn_node will attribute
    # success/reward to THIS action, not to whatever action runs next)
    current_action = state.get("current_action")
    current_sig = None
    if current_action:
        x = current_action.get("x")
        y = current_action.get("y")
        action_type = current_action.get("action_type", "CLICK").lower()
        if x is not None and y is not None:
            current_sig = ((x, y), action_type)
    result["previous_action_signature"] = current_sig

    # Store current activity for next iteration's state change tracking
    result["previous_activity"] = state.get("current_activity")

    # NOTE: UI coverage interaction is recorded in execute_node.py
    # using device-space coordinates (not normalized [0,1000))

    return result


def _record_back_transition(agent: "RVAgent", state: AgentState) -> None:
    """Record BACK transitions for Backtrack BFS navigation.

    When a BACK action is executed and the screen changes, record the
    transition in SuccessorTracker.back_successors. This builds a graph
    of where BACK leads from each state, used by Backtrack BFS to find
    paths to unsaturated ancestors.

    Args:
        agent: RVAgent instance with strategy.successor_tracker.
        state: Current agent state with action and hash information.
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

        successor_tracker = getattr(agent.strategy, "successor_tracker", None)
        if successor_tracker:
            successor_tracker.record_back_transition(previous_hash, current_hash)
            logger.debug(
                f"Recorded BACK transition: {previous_hash[:8]}... -> {current_hash[:8]}..."
            )

    except Exception as e:
        logger.warning(f"Failed to record BACK transition: {e}")


def _record_action_success(agent: "RVAgent", state: AgentState) -> None:
    """Record action success for strength-based scoring.

    An action is considered successful if it caused a state transition
    (screen hash changed after execution). Record the result in the
    ScreenNode for the state where the action was executed, updating
    execution counts and success counts used by StrengthScorer.

    Uses previous_action_signature (one-iteration offset correction):
    learn_node runs AFTER execute_node, so the hash comparison measures
    the EFFECT of the previous iteration's action. Success and reward
    must be attributed to previous_action_signature, not the current action.

    TODO(#20): This heuristic has limitations -- actions that change
    internal state without changing UI are marked as failures, and actions
    that open transient dialogs may give false positives.

    Args:
        agent: RVAgent instance with strategy.graph containing ScreenNodes.
        state: Current agent state with previous/current hashes and action info.
    """
    try:
        iteration = state.get("iteration", 0)

        # One-iteration offset fix: attribute success to the previous action
        previous_action_signature = state.get("previous_action_signature")
        if previous_action_signature is None:
            # First iteration — no previous action to attribute success to
            track.attribution(
                iter=iteration,
                action_sig="none",
                success=False,
                reward_type="skipped",
                source="skipped",
            )
            return

        previous_hash = state.get("previous_screen_hash")
        current_hash = state.get("current_screen_hash")

        if not previous_hash or not current_hash:
            return

        # Get the node where the previous action was executed
        graph = getattr(agent.strategy, "graph", None)
        if not graph:
            return

        node = graph.states.get(previous_hash)
        if not node:
            return

        # Success = state changed (hash comparison is correct — it measures
        # the effect of the previous action)
        success = previous_hash != current_hash

        # Record success using previous action's signature
        node.record_action_success(previous_action_signature, success)

        # Track strength using previous action's coords and type
        coords = previous_action_signature[0]
        action_type = previous_action_signature[1]
        executions = node.get_action_execution_count(previous_action_signature)
        successes = node.action_success_counts.get(previous_action_signature, 0)
        strength_val = node.get_action_strength(previous_action_signature)

        track.strength(
            iter=iteration,
            action=action_type,
            coords=coords,
            strength_val=strength_val,
            executions=executions,
            successes=successes,
        )

        track.attribution(
            iter=iteration,
            action_sig=str(previous_action_signature),
            success=success,
            reward_type="transition",
            source="previous",
        )

        logger.debug(
            f"Action success recorded: {previous_action_signature} "
            f"success={success} strength={strength_val:.2f}"
        )

    except Exception as e:
        logger.warning(f"Failed to record action success: {e}")


def _propagate_reward(agent: "RVAgent", state: AgentState) -> None:
    """Record action in reward history and propagate reward based on outcome.

    Uses previous_action_signature (one-iteration offset correction):
    the hash comparison measures the effect of the previous action, so
    reward must be attributed to previous_action_signature.

    Determine reward type using priority order and delegate to RewardPropagator
    for N-step backward propagation with gamma discounting:

    1. mop_reached: action has callback_signature (monitored operation triggered).
    2. new_activity: screen changed AND activity not seen before.
    3. new_state: screen changed AND activity already seen.
    4. form_fill: screen unchanged AND action was SET_TEXT/TEXT_CHANGE.
    5. same_state: screen unchanged AND action was not text input.

    Args:
        agent: RVAgent instance with strategy.reward_propagator and strategy.graph.
        state: Current agent state with hashes, action info, and item_action.
    """
    try:
        reward_propagator = getattr(agent.strategy, "reward_propagator", None)
        if not reward_propagator:
            return

        iteration = state.get("iteration", 0)

        # One-iteration offset fix: attribute reward to the previous action
        previous_action_signature = state.get("previous_action_signature")
        if previous_action_signature is None:
            # First iteration — no previous action to record reward for
            return

        previous_hash = state.get("previous_screen_hash")
        current_hash = state.get("current_screen_hash")

        if not previous_hash or not current_hash:
            return

        # Record previous action in reward history
        reward_propagator.record_action(previous_hash, previous_action_signature)

        # Determine reward type using current state observations
        # (callback_signature, activity change, etc. reflect current state)
        current_action = state.get("current_action")
        selected_action = state.get("current_item_action")
        has_mop = (
            selected_action
            and hasattr(selected_action, "callback_signature")
            and selected_action.callback_signature
        )

        if has_mop:
            reward_type = "mop_reached"
        elif previous_hash != current_hash:
            # Screen changed — check if it's a new activity
            current_activity = state.get("current_activity", "")
            visited_activities = getattr(
                agent.strategy, "_get_visited_activities", lambda: set()
            )()
            if current_activity and current_activity not in visited_activities:
                reward_type = "new_activity"
            else:
                reward_type = "new_state"
        else:
            # Screen unchanged — determine based on current action type
            action_type = ""
            if current_action:
                action_type = current_action.get("action_type", "")
            if action_type.upper() in ("SET_TEXT", "TEXT_CHANGE"):
                reward_type = "form_fill"
            else:
                reward_type = "same_state"

        graph = getattr(agent.strategy, "graph", None)
        if graph:
            reward_propagator.propagate(reward_type, graph, iteration=iteration)

        track.attribution(
            iter=iteration,
            action_sig=str(previous_action_signature),
            success=previous_hash != current_hash,
            reward_type=reward_type,
            source="previous",
        )

    except Exception as e:
        logger.warning(f"Failed to propagate reward: {e}")


def _invalidate_stale_path_buffer(agent: "RVAgent", state: AgentState) -> None:
    """Invalidate PathBuffer if the screen did not change after a buffered action.

    When the PathBuffer is active (executing a multi-hop plan), each action
    should produce a screen change. If the current hash equals the previous hash,
    the navigation did not work (e.g., BACK had no effect on a root screen).
    Continuing the buffered plan would waste iterations, so clear it.

    Args:
        agent: RVAgent instance with strategy that may have path_buffer.
        state: Current agent state with previous/current hash info.
    """
    try:
        path_buffer = getattr(agent.strategy, "path_buffer", None)
        if path_buffer is None:
            return

        if not path_buffer.is_active:
            return

        current_hash = state.get("current_screen_hash")
        previous_hash = state.get("previous_screen_hash")

        if current_hash and previous_hash and current_hash == previous_hash:
            path_buffer.invalidate()
            logger.warning(
                "PathBuffer invalidated: screen unchanged after buffered action "
                f"(hash={current_hash[:8]}...)"
            )

    except Exception as e:
        logger.warning(f"Failed to check path buffer invalidation: {e}")


def _track_llm_text_value(agent: "RVAgent", state: AgentState) -> None:
    """Record LLM-generated text values in InputValueGenerator to prevent repetition.

    When the LLM generates a SET_TEXT action, record the text value in
    value_generator.tested_values so the algorithm path does not re-test it.
    Uses widget_id as element key when available, falls back to coordinates.

    Args:
        agent: RVAgent instance with strategy.value_generator.
        state: Current agent state with action and decision_maker info.
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
        if item_action and hasattr(item_action, "widget_id") and item_action.widget_id:
            element_id = item_action.widget_id
        else:
            x = current_action.get("x")
            y = current_action.get("y")
            if x is not None and y is not None:
                element_id = make_element_id(x, y)
            else:
                return

        value_generator = getattr(agent.strategy, "value_generator", None)
        if not value_generator:
            return

        if text not in value_generator.tested_values.get(element_id, []):
            value_generator.tested_values[element_id].append(text)
            logger.debug(f"Tracked LLM text for {element_id}: '{text[:20]}'")

    except Exception as e:
        logger.warning(f"Failed to track LLM text value: {e}")
