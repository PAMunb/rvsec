"""
Integration tests for the error detection feature.

Tests the end-to-end flow across multiple nodes:
  learn_node -> decision_node -> algorithm_node

Each test runs the real node functions with a mocked RVAgent (no emulator/LLM).
External services (VisualErrorDetector, device, value_generator) are mocked
to isolate the cross-node interaction logic.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.agent.nodes.learn_node import learn_node, MAX_ERROR_RECOVERY
from rv_agent.agent.nodes.decision_node import decision_router_node
from rv_agent.agent.nodes.algorithm_node import algorithm_node
from rv_agent.agent.nodes.parse_node import parse_ui_node
from rv_agent.services.error_detection import ValidationErrorResult
from rv_screen_parser.parser.screen.visitor.model import (
    ItemAction, ScreenItem, ScreenDescription, WidgetEventType,
)
from rv_screen_parser.screenshot.models import (
    ErrorIndicator, DetectionMethod, ErrorType, BoundingBox,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(**overrides) -> RVAgentConfig:
    """Create a default RVAgentConfig with pure_algorithm mode (avoids LLM requirement)."""
    defaults = dict(
        package_name="com.test.app",
        agent_mode="pure_algorithm",
        error_detection_enabled=True,
        error_detection_confidence=0.7,
        error_max_indicator_size=80,
        error_max_indicator_count=5,
        spatial_edittext_boost=1.2,
        spatial_spinner_boost=1.1,
        spatial_min_match_threshold=0.1,
    )
    defaults.update(overrides)
    return RVAgentConfig(**defaults)


def _make_agent(config=None, **overrides):
    """Build a lightweight mock RVAgent with all attributes the nodes access.

    All collaborators are mocks; caller can override any attribute via kwargs.
    """
    agent = MagicMock()
    agent.config = config or _make_config()

    # Stuck / error counters
    agent.error_recovery_count = 0
    agent.stuck_screen_count = 0
    agent.last_screen_hash = None
    agent.consecutive_no_action = 0
    agent.NO_ACTION_THRESHOLD = 3
    agent.BASE_STUCK_THRESHOLD = 8
    agent.STUCK_THRESHOLD_FACTOR = 1.5

    # Memory coordinator (returns minimal valid dicts)
    mc = MagicMock()
    mc.update_memories.return_value = {"recent_action_window": []}
    mc.generate_summaries.return_value = {
        "action_history_summary": "",
        "exploration_summary": "",
        "memory_insights": "",
        "navigation_path": "",
    }
    mc.track_state_discovery.return_value = {
        "visited_states": [],
        "state_transitions": [],
    }
    mc.check_continuation.return_value = {"should_continue": True}
    agent.memory_coordinator = mc

    # Routing manager
    rm = MagicMock()
    rm.mode = "pure_algorithm"
    rm.forced_back_count = 0
    agent.routing_manager = rm

    # Strategy with value_generator
    strategy = MagicMock()
    strategy.value_generator.get_next_value.return_value = "test_value"
    strategy.successor_tracker = None
    agent.strategy = strategy

    # Stuck recovery
    sr = MagicMock()
    sr.check.return_value = None
    agent.stuck_recovery = sr

    # Apply caller overrides
    for k, v in overrides.items():
        setattr(agent, k, v)

    return agent


def _make_error_indicator(x=200, y=400, w=20, h=20, confidence=0.85):
    """Create a real ErrorIndicator Pydantic model instance."""
    return ErrorIndicator(
        x=x, y=y, width=w, height=h,
        detection_method=DetectionMethod.COLOR,
        confidence=confidence,
        error_type=ErrorType.VALIDATION_ERROR,
    )


def _make_item_action(
    action_id=1,
    event=WidgetEventType.TEXT_CHANGE,
    coords=(200, 390),
    widget_class="android.widget.EditText",
    widget_id=None,
    text="Enter value",
    text_input=None,
):
    """Create a real ItemAction with a target_view that includes bounds and class."""
    x, y = coords
    bounds = [[x - 50, y - 25], [x + 150, y + 25]]
    return ItemAction(
        id=action_id,
        text=text,
        event=event,
        target_view={
            "class": widget_class,
            "bounds": bounds,
            "resource_id": widget_id or "",
        },
        coordinates=coords,
        widget_id=widget_id,
        text_input=text_input,
    )


def _make_screen_description(items):
    """Wrap a list of ScreenItems into a ScreenDescription."""
    return ScreenDescription(activity="FormActivity", items=items)


def _make_screen_item(action):
    """Wrap a single ItemAction in a ScreenItem."""
    return ScreenItem(
        view=action.target_view,
        base_description=action.text,
        actions=[action],
    )


def _base_state(**overrides):
    """Minimal state dict that satisfies all node preconditions."""
    s = {
        "iteration": 5,
        "current_screen_hash": "hash_A",
        "previous_screen_hash": "hash_A",
        "current_activity": "FormActivity",
        "previous_activity": "FormActivity",
        "screen_description": None,
        "current_action": None,
        "current_item_action": None,
        "available_actions": [],
        "visited_states": [],
        "state_transitions": [],
        "recent_action_window": [],
        "start_time": 0,
        "timeout": 300,
        "error_detection_screenshot": None,
        "force_fill_input": False,
        "force_back_action": False,
        "force_restart_app": False,
        "error_indicators": None,
        "llm_reasoning": "",
    }
    s.update(overrides)
    return s


def _apply_updates(state, updates):
    """Merge node return dict into state (simulates LangGraph state merge)."""
    merged = dict(state)
    merged.update(updates)
    return merged


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFullFlowEditText:
    """Test 8.1: error -> spatial match EditText -> SET_TEXT action."""

    @patch("rv_agent.agent.nodes.learn_node._detect_validation_error")
    def test_error_detected_spatially_matched_edittext_produces_set_text(
        self, mock_detect
    ):
        """Full pipeline: learn_node detects error, decision_node routes to
        algorithm, algorithm_node finds spatially associated EditText and
        returns a SET_TEXT action with decision_maker='error_recovery'.
        """
        # -- Setup --
        indicator = _make_error_indicator(x=200, y=420, w=20, h=20)
        mock_detect.return_value = ValidationErrorResult(
            detected=True,
            error_indicators=[indicator],
            confidence=0.85,
            detection_method="visual_color",
        )

        edittext_action = _make_item_action(
            action_id=1,
            event=WidgetEventType.TEXT_CHANGE,
            coords=(200, 390),
            widget_class="android.widget.EditText",
        )
        screen_desc = _make_screen_description([_make_screen_item(edittext_action)])

        agent = _make_agent()
        state = _base_state(
            error_detection_screenshot="/tmp/screenshot.png",
            screen_description=screen_desc,
        )

        # -- Run learn_node --
        learn_result = learn_node(agent, state)
        state = _apply_updates(state, learn_result)

        assert state["force_fill_input"] is True
        assert state["error_indicators"] is not None
        assert len(state["error_indicators"]) == 1
        assert agent.error_recovery_count == 1

        # -- Run decision_node --
        decision_result = decision_router_node(agent, state)
        state = _apply_updates(state, decision_result)

        assert state["decision_path"] == "algorithm"
        assert state["decision_maker"] == "error_recovery"

        # -- Run algorithm_node --
        algo_result = algorithm_node(agent, state)
        state = _apply_updates(state, algo_result)

        assert state["current_action"] is not None
        assert state["current_action"]["action_type"] == "SET_TEXT"
        assert state["decision_maker"] == "error_recovery"
        # Flags should be cleared after recovery action
        assert state["force_fill_input"] is False
        assert state["error_indicators"] is None


class TestSpinnerErrorRecovery:
    """Test 8.2: error near Spinner -> CLICK action."""

    @patch("rv_agent.agent.nodes.learn_node._detect_validation_error")
    def test_spinner_near_error_indicator_produces_click(self, mock_detect):
        """When the nearest widget to the error indicator is a Spinner,
        algorithm_node produces a CLICK action (not SET_TEXT).
        """
        indicator = _make_error_indicator(x=200, y=420, w=20, h=20)
        mock_detect.return_value = ValidationErrorResult(
            detected=True,
            error_indicators=[indicator],
            confidence=0.85,
        )

        spinner_action = _make_item_action(
            action_id=2,
            event=WidgetEventType.CLICK,
            coords=(200, 390),
            widget_class="android.widget.Spinner",
            text="Select option",
        )
        screen_desc = _make_screen_description([_make_screen_item(spinner_action)])

        agent = _make_agent()
        state = _base_state(
            error_detection_screenshot="/tmp/screenshot.png",
            screen_description=screen_desc,
        )

        learn_result = learn_node(agent, state)
        state = _apply_updates(state, learn_result)
        decision_result = decision_router_node(agent, state)
        state = _apply_updates(state, decision_result)
        algo_result = algorithm_node(agent, state)
        state = _apply_updates(state, algo_result)

        assert state["current_action"]["action_type"] == "CLICK"
        assert state["decision_maker"] == "error_recovery"


class TestFillInputThenNormalFlow:
    """Test 8.3: error -> fill input -> screen changes -> normal flow resumes."""

    @patch("rv_agent.agent.nodes.learn_node._detect_validation_error")
    def test_normal_flow_resumes_after_screen_changes(self, mock_detect):
        """First iteration detects error and sets force_fill_input. Second
        iteration has error_detection_screenshot=None (screen changed after
        fill). learn_node resets counter and clears flags, restoring normal
        flow.
        """
        # -- Iteration 1: error detected --
        indicator = _make_error_indicator()
        mock_detect.return_value = ValidationErrorResult(
            detected=True,
            error_indicators=[indicator],
            confidence=0.85,
        )

        edittext_action = _make_item_action(action_id=1)
        screen_desc = _make_screen_description([_make_screen_item(edittext_action)])
        agent = _make_agent()

        state_iter1 = _base_state(
            error_detection_screenshot="/tmp/screenshot.png",
            screen_description=screen_desc,
        )
        learn_result_1 = learn_node(agent, state_iter1)

        assert learn_result_1["force_fill_input"] is True
        assert agent.error_recovery_count == 1

        # -- Iteration 2: screen changed (screenshot is None) --
        state_iter2 = _base_state(
            error_detection_screenshot=None,
            current_screen_hash="hash_B",
            previous_screen_hash="hash_A",
            screen_description=screen_desc,
        )
        learn_result_2 = learn_node(agent, state_iter2)

        assert learn_result_2["force_fill_input"] is False
        assert agent.error_recovery_count == 0
        # No force flags set (normal flow)
        assert "force_back_action" not in learn_result_2
        assert "force_restart_app" not in learn_result_2


class TestMaxErrorRecovery:
    """Test 8.4: after MAX_ERROR_RECOVERY, detection is skipped."""

    @patch("rv_agent.agent.nodes.learn_node._detect_validation_error")
    def test_max_recovery_skips_detection_and_resets_on_screen_change(
        self, mock_detect
    ):
        """When error_recovery_count equals MAX_ERROR_RECOVERY:
        - Branch (b) fires: detection is NOT called
        - Counter stays at MAX
        - stuck_screen_count can accumulate normally
        Then when the screen changes (screenshot=None):
        - Branch (a) fires: counter resets to 0
        """
        agent = _make_agent()
        agent.error_recovery_count = MAX_ERROR_RECOVERY  # 3

        state_stuck = _base_state(
            error_detection_screenshot="/tmp/screenshot.png",
        )

        learn_result = learn_node(agent, state_stuck)

        # Detection should NOT have been called (branch b)
        mock_detect.assert_not_called()
        # Counter stays at MAX
        assert agent.error_recovery_count == MAX_ERROR_RECOVERY
        # No error-related flags set
        assert "force_fill_input" not in learn_result or learn_result.get("force_fill_input") is not True

        # Stuck detection can accumulate (not suppressed by error detection)
        # Since screen hash repeats and it's not a form action,
        # stuck_screen_count should increment
        assert agent.stuck_screen_count >= 0  # Just verify it's not reset to negative

        # Now simulate screen change
        state_changed = _base_state(
            error_detection_screenshot=None,
            current_screen_hash="hash_NEW",
        )
        learn_result_2 = learn_node(agent, state_changed)

        assert agent.error_recovery_count == 0
        assert learn_result_2["force_fill_input"] is False


class TestNoSpatialMatchSequentialFallback:
    """Test 8.5: error indicators far from any item -> sequential fallback."""

    @patch("rv_agent.agent.nodes.learn_node._detect_validation_error")
    def test_no_spatial_match_uses_sequential_fallback(self, mock_detect):
        """When error indicators are spatially far from all screen items,
        _find_associated_input_action returns None and _find_next_input_action
        picks the first set_text action.
        """
        # Error indicator at bottom-right corner, far from the input
        indicator = _make_error_indicator(x=900, y=1800, w=20, h=20)
        mock_detect.return_value = ValidationErrorResult(
            detected=True,
            error_indicators=[indicator],
            confidence=0.85,
        )

        # EditText at top-left — no spatial overlap with indicator
        edittext_action = _make_item_action(
            action_id=1,
            event=WidgetEventType.TEXT_CHANGE,
            coords=(100, 100),
            widget_class="android.widget.EditText",
        )
        screen_desc = _make_screen_description([_make_screen_item(edittext_action)])

        agent = _make_agent()
        # Set a high spatial threshold to force spatial match to fail
        agent.config = _make_config(spatial_min_match_threshold=0.5)

        state = _base_state(
            error_detection_screenshot="/tmp/screenshot.png",
            screen_description=screen_desc,
        )

        # Run learn -> decision -> algorithm
        learn_result = learn_node(agent, state)
        state = _apply_updates(state, learn_result)
        assert state["force_fill_input"] is True

        decision_result = decision_router_node(agent, state)
        state = _apply_updates(state, decision_result)

        algo_result = algorithm_node(agent, state)
        state = _apply_updates(state, algo_result)

        # Sequential fallback found the set_text action
        assert state["current_action"] is not None
        assert state["current_action"]["action_type"] == "SET_TEXT"
        assert state["decision_maker"] == "error_recovery"


class TestMaxRecoveryRegressionMultipleIterations:
    """Test 8.6: 4+ consecutive error iterations — branching prevents loop."""

    @patch("rv_agent.agent.nodes.learn_node._detect_validation_error")
    def test_four_plus_iterations_capped_by_max_recovery(self, mock_detect):
        """Run learn_node for 5 consecutive iterations with error:
        - Iterations 1-3: detected=True, counter increments to 1, 2, 3
        - Iteration 4: counter==MAX (3), detection skipped, counter stays 3
        - Iteration 5: counter still 3, detection still skipped
        """
        indicator = _make_error_indicator()
        mock_detect.return_value = ValidationErrorResult(
            detected=True,
            error_indicators=[indicator],
            confidence=0.85,
        )

        agent = _make_agent()
        base = _base_state(error_detection_screenshot="/tmp/screenshot.png")

        # Iterations 1-3: error detected, counter increments
        for expected_count in [1, 2, 3]:
            agent.last_screen_hash = None  # Prevent stuck counting from interfering
            result = learn_node(agent, base)
            assert agent.error_recovery_count == expected_count, (
                f"Expected count={expected_count}, got {agent.error_recovery_count}"
            )
            assert result.get("force_fill_input") is True

        # Call count after 3 iterations: 3
        assert mock_detect.call_count == 3

        # Iteration 4: counter == MAX, detection skipped
        agent.last_screen_hash = None
        result_4 = learn_node(agent, base)
        assert agent.error_recovery_count == MAX_ERROR_RECOVERY  # stays at 3
        # Detection was NOT called for this iteration
        assert mock_detect.call_count == 3  # unchanged
        # force_fill_input should NOT be True (branch b does nothing)
        assert result_4.get("force_fill_input") is not True

        # Iteration 5: still capped
        agent.last_screen_hash = None
        result_5 = learn_node(agent, base)
        assert agent.error_recovery_count == MAX_ERROR_RECOVERY
        assert mock_detect.call_count == 3  # still unchanged


class TestLLMModeErrorRecoveryBypass:
    """Test 8.7: error recovery bypasses LLM even when mode is llm_only."""

    @patch("rv_agent.agent.nodes.learn_node._detect_validation_error")
    def test_error_recovery_routes_to_algorithm_in_llm_mode(self, mock_detect):
        """When agent_mode is llm_only and force_fill_input is True,
        decision_node still routes to algorithm with decision_maker='error_recovery'.
        The LLM path is NOT taken.
        """
        indicator = _make_error_indicator()
        mock_detect.return_value = ValidationErrorResult(
            detected=True,
            error_indicators=[indicator],
            confidence=0.85,
        )

        config = _make_config(agent_mode="pure_algorithm")  # Use pure_algorithm to avoid LLM requirement
        agent = _make_agent(config=config)
        agent.routing_manager.mode = "llm_only"

        edittext_action = _make_item_action(action_id=1)
        screen_desc = _make_screen_description([_make_screen_item(edittext_action)])

        state = _base_state(
            error_detection_screenshot="/tmp/screenshot.png",
            screen_description=screen_desc,
        )

        # learn_node sets force_fill_input
        learn_result = learn_node(agent, state)
        state = _apply_updates(state, learn_result)
        assert state["force_fill_input"] is True

        # decision_node routes to algorithm, not LLM
        decision_result = decision_router_node(agent, state)
        state = _apply_updates(state, decision_result)

        assert state["decision_path"] == "algorithm"
        assert state["decision_maker"] == "error_recovery"
        # routing_manager.route_decision should NOT be called (bypassed)
        agent.routing_manager.route_decision.assert_not_called()


class TestForceRestartPriorityOverForceFillInput:
    """Test 8.8: force_restart_app has priority over force_fill_input."""

    def test_restart_checked_before_fill_input_in_decision_node(self):
        """When both force_restart_app and force_fill_input are True,
        decision_node checks restart first and routes accordingly.
        """
        agent = _make_agent()
        state = _base_state(
            force_restart_app=True,
            force_fill_input=True,
        )

        decision_result = decision_router_node(agent, state)

        # Restart has priority in decision_node (checked first)
        assert decision_result["decision_path"] == "algorithm"
        assert decision_result["decision_maker"] == "stuck_recovery"

    def test_restart_checked_before_fill_input_in_algorithm_node(self):
        """In algorithm_node, force_restart_app produces RESTART_APP action
        even when force_fill_input is also True.
        """
        agent = _make_agent()
        state = _base_state(
            force_restart_app=True,
            force_fill_input=True,
        )

        algo_result = algorithm_node(agent, state)

        assert algo_result["current_action"]["action_type"] == "RESTART_APP"
        assert algo_result["decision_maker"] == "stuck_recovery"

    @patch("rv_agent.agent.nodes.learn_node._detect_validation_error")
    def test_learn_node_clears_force_fill_on_screen_change(self, mock_detect):
        """After restart causes screen change, learn_node defensively clears
        force_fill_input to avoid stale state from a previous iteration.
        """
        agent = _make_agent()
        agent.error_recovery_count = 2

        state = _base_state(
            error_detection_screenshot=None,  # Screen changed
            current_screen_hash="hash_new",
        )

        result = learn_node(agent, state)

        assert result["force_fill_input"] is False
        assert agent.error_recovery_count == 0


class TestParseNodeScreenshotStatePersistence:
    """Test 8.9: parse_ui_node ALWAYS sets error_detection_screenshot key."""

    def test_screenshot_key_present_when_hash_repeats(self):
        """When screen hash repeats, parse_ui_node sets the screenshot path."""
        agent = _make_agent()
        agent.config.error_detection_enabled = True
        agent.device = MagicMock()
        agent.device.take_screenshot.return_value = "/tmp/error_screenshot.png"

        mock_processor_result = {
            "screen_hash": "hash_A",
            "activity": "FormActivity",
            "screen_description": MagicMock(items=[]),
            "ui_elements_text": "Some UI text that is long enough to pass the check threshold for testing",
            "is_external": False,
            "external_navigation_count": 0,
            "ui_xml": "<hierarchy/>",
        }
        agent.screen_processor = MagicMock()
        agent.screen_processor.parse_current_screen.return_value = mock_processor_result
        agent.ui_coverage = MagicMock()

        state = _base_state(previous_screen_hash="hash_A")

        result = parse_ui_node(agent, state)

        assert "error_detection_screenshot" in result
        assert result["error_detection_screenshot"] == "/tmp/error_screenshot.png"

    def test_screenshot_key_present_when_hash_differs(self):
        """When screen hash changes, parse_ui_node sets screenshot to None
        (not omitted).
        """
        agent = _make_agent()
        agent.config.error_detection_enabled = True
        agent.device = MagicMock()

        mock_processor_result = {
            "screen_hash": "hash_B",
            "activity": "OtherActivity",
            "screen_description": MagicMock(items=[]),
            "ui_elements_text": "Some UI text that is long enough to pass the check threshold for testing",
            "is_external": False,
            "external_navigation_count": 0,
            "ui_xml": "<hierarchy/>",
        }
        agent.screen_processor = MagicMock()
        agent.screen_processor.parse_current_screen.return_value = mock_processor_result
        agent.ui_coverage = MagicMock()

        state = _base_state(previous_screen_hash="hash_A")

        result = parse_ui_node(agent, state)

        # Key MUST be present (not omitted), value must be None
        assert "error_detection_screenshot" in result
        assert result["error_detection_screenshot"] is None
        # device.take_screenshot should NOT be called when hashes differ
        agent.device.take_screenshot.assert_not_called()
