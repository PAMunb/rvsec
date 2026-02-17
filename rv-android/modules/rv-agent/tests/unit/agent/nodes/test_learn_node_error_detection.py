"""
Unit tests for validation error detection integration in learn_node.

Tests the 3-way branching logic:
  (a) No screenshot (screen changed) -> reset counter, defensive clear
  (b) Screenshot exists but max recovery reached -> skip detection
  (c) Screenshot exists and count < max -> run detection

Also tests the detection disabled path and counter reset on no-error-found.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from rv_agent.agent.nodes.learn_node import (
    learn_node,
    _detect_validation_error,
    MAX_ERROR_RECOVERY,
)
from rv_agent.services.error_detection import ValidationErrorResult


def _make_mock_agent(
    error_detection_enabled=True,
    error_recovery_count=0,
    stuck_screen_count=0,
    last_screen_hash="prev_hash",
):
    """Create a mock agent with the standard memory coordinator stubs."""
    mock_memory_coordinator = MagicMock()
    mock_memory_coordinator.update_memories.return_value = {
        "recent_action_window": []
    }
    mock_memory_coordinator.generate_summaries.return_value = {
        "action_history_summary": "",
        "exploration_summary": "",
        "memory_insights": "",
        "navigation_path": "",
    }
    mock_memory_coordinator.track_state_discovery.return_value = {
        "visited_states": [],
        "state_transitions": [],
    }
    mock_memory_coordinator.check_continuation.return_value = {
        "should_continue": True
    }

    mock_config = MagicMock()
    mock_config.error_detection_enabled = error_detection_enabled
    mock_config.error_detection_confidence = 0.7
    mock_config.error_max_indicator_size = 80
    mock_config.error_max_indicator_count = 5

    mock_agent = MagicMock()
    mock_agent.memory_coordinator = mock_memory_coordinator
    mock_agent.config = mock_config
    mock_agent.stuck_screen_count = stuck_screen_count
    mock_agent.last_screen_hash = last_screen_hash
    mock_agent.error_recovery_count = error_recovery_count
    mock_agent.BASE_STUCK_THRESHOLD = 8
    mock_agent.STUCK_THRESHOLD_FACTOR = 1.5
    mock_agent.metrics_collector = None

    return mock_agent


def _make_state(
    current_screen_hash="new_hash",
    error_detection_screenshot=None,
    iteration=1,
    current_action=None,
):
    """Create a minimal state dict for learn_node."""
    state = {
        "current_screen_hash": current_screen_hash,
        "current_activity": ".MainActivity",
        "iteration": iteration,
        "error_detection_screenshot": error_detection_screenshot,
    }
    if current_action is not None:
        state["current_action"] = current_action
    return state


class TestDetectValidationErrorFunction:
    """Tests for the _detect_validation_error private function."""

    def test_detection_disabled_returns_none(self):
        """When error_detection_enabled=False, returns None immediately."""
        agent = _make_mock_agent(error_detection_enabled=False)

        result = _detect_validation_error(agent, "/tmp/screenshot.png")

        assert result is None

    @patch("rv_agent.agent.nodes.learn_node.VisualErrorDetector")
    def test_detection_enabled_calls_detector(self, MockDetectorClass):
        """When enabled, creates VisualErrorDetector and calls detect()."""
        mock_indicator = MagicMock()
        mock_result = ValidationErrorResult(
            detected=True,
            error_indicators=[mock_indicator],
            confidence=0.8,
            detection_method="visual_color",
        )
        MockDetectorClass.return_value.detect.return_value = mock_result

        agent = _make_mock_agent(error_detection_enabled=True)

        result = _detect_validation_error(agent, "/tmp/screenshot.png")

        assert result is mock_result
        MockDetectorClass.return_value.detect.assert_called_once_with(
            "/tmp/screenshot.png",
            confidence_threshold=0.7,
            max_indicator_size=80,
            max_indicator_count=5,
        )


class TestLearnNodeErrorDetection:
    """Tests for the 3-way error detection branching in learn_node."""

    @patch("rv_agent.agent.nodes.learn_node._detect_validation_error")
    def test_screenshot_available_error_detected(self, mock_detect):
        """Branch (c): screenshot exists, error detected -> set force_fill, increment counter."""
        mock_indicator = MagicMock()
        mock_detect.return_value = ValidationErrorResult(
            detected=True,
            error_indicators=[mock_indicator],
            confidence=0.8,
            detection_method="visual_color",
        )

        agent = _make_mock_agent(error_recovery_count=0)
        state = _make_state(
            error_detection_screenshot="/tmp/screenshot.png",
            current_screen_hash="same_hash",
        )
        # Set last_screen_hash = current_screen_hash so stuck detection would
        # normally fire (but error detection should suppress it)
        agent.last_screen_hash = "same_hash"

        result = learn_node(agent, state)

        # Error recovery counter incremented
        assert agent.error_recovery_count == 1
        # Stuck screen count reset (error detection suppresses stuck)
        assert agent.stuck_screen_count == 0
        # force_fill_input set
        assert result["force_fill_input"] is True
        # error_indicators populated
        assert result["error_indicators"] == [mock_indicator]

    @patch("rv_agent.agent.nodes.learn_node._detect_validation_error")
    def test_no_screenshot_screen_changed_resets_counter(self, mock_detect):
        """Branch (a): no screenshot (screen changed) -> reset counter, defensive clear."""
        agent = _make_mock_agent(error_recovery_count=2)
        state = _make_state(
            error_detection_screenshot=None,
            current_screen_hash="new_hash",
        )
        agent.last_screen_hash = "old_hash"

        result = learn_node(agent, state)

        # Counter reset
        assert agent.error_recovery_count == 0
        # Defensive clear
        assert result["force_fill_input"] is False
        assert result["error_indicators"] is None
        # Detection NOT called
        mock_detect.assert_not_called()

    @patch("rv_agent.agent.nodes.learn_node._detect_validation_error")
    def test_max_error_recovery_reached_skips_detection(self, mock_detect):
        """Branch (b): screenshot exists but max recovery reached -> skip detection."""
        agent = _make_mock_agent(error_recovery_count=MAX_ERROR_RECOVERY)
        state = _make_state(
            error_detection_screenshot="/tmp/screenshot.png",
            current_screen_hash="same_hash",
        )
        agent.last_screen_hash = "same_hash"

        result = learn_node(agent, state)

        # Detection NOT called
        mock_detect.assert_not_called()
        # Counter stays at max
        assert agent.error_recovery_count == MAX_ERROR_RECOVERY
        # force_fill_input NOT set in result
        assert "force_fill_input" not in result or result.get("force_fill_input") is not True

    @patch("rv_agent.agent.nodes.learn_node._detect_validation_error")
    def test_screen_changes_after_max_recovery_resets(self, mock_detect):
        """Branch (a): no screenshot, counter was at max -> reset to 0."""
        agent = _make_mock_agent(error_recovery_count=MAX_ERROR_RECOVERY)
        state = _make_state(
            error_detection_screenshot=None,
            current_screen_hash="new_hash",
        )
        agent.last_screen_hash = "old_hash"

        result = learn_node(agent, state)

        # Counter resets
        assert agent.error_recovery_count == 0
        # Defensive clear
        assert result["force_fill_input"] is False
        assert result["error_indicators"] is None
        # Detection NOT called
        mock_detect.assert_not_called()

    @patch("rv_agent.agent.nodes.learn_node._detect_validation_error")
    def test_screenshot_exists_no_error_found_resets_counter(self, mock_detect):
        """Branch (c): screenshot exists, detection runs but no error -> reset counter."""
        mock_detect.return_value = ValidationErrorResult(
            detected=False,
            error_indicators=[],
            confidence=0.0,
            detection_method="visual_color",
        )

        agent = _make_mock_agent(error_recovery_count=1)
        state = _make_state(
            error_detection_screenshot="/tmp/screenshot.png",
            current_screen_hash="same_hash",
        )
        agent.last_screen_hash = "same_hash"

        result = learn_node(agent, state)

        # Counter resets since no error found
        assert agent.error_recovery_count == 0
        # force_fill_input NOT set
        assert "force_fill_input" not in result or result.get("force_fill_input") is not True

    @patch("rv_agent.agent.nodes.learn_node._detect_validation_error")
    def test_track_learn_called_with_error_detected_true(self, mock_detect):
        """When error detected, track.learn receives error_detected=True."""
        mock_indicator = MagicMock()
        mock_detect.return_value = ValidationErrorResult(
            detected=True,
            error_indicators=[mock_indicator],
            confidence=0.85,
            detection_method="visual_color",
        )

        agent = _make_mock_agent(error_recovery_count=0)
        state = _make_state(
            error_detection_screenshot="/tmp/screenshot.png",
            current_screen_hash="new_hash",
        )
        agent.last_screen_hash = "old_hash"

        with patch("rv_agent.agent.nodes.learn_node.track") as mock_track:
            result = learn_node(agent, state)

            # Find the track.learn call
            learn_calls = mock_track.learn.call_args_list
            assert len(learn_calls) == 1
            _, kwargs = learn_calls[0]
            assert kwargs.get("error_detected") is True

    @patch("rv_agent.agent.nodes.learn_node._detect_validation_error")
    def test_track_error_called_on_detection(self, mock_detect):
        """When error detected, track.error is called with indicator metadata."""
        mock_indicator = MagicMock()
        mock_detect.return_value = ValidationErrorResult(
            detected=True,
            error_indicators=[mock_indicator],
            confidence=0.85,
            detection_method="visual_color",
            filtered_by_size=2,
            filtered_by_region=1,
            filtered_by_count=False,
        )

        agent = _make_mock_agent(error_recovery_count=0)
        state = _make_state(
            error_detection_screenshot="/tmp/screenshot.png",
            current_screen_hash="new_hash",
        )
        agent.last_screen_hash = "old_hash"

        with patch("rv_agent.agent.nodes.learn_node.track") as mock_track:
            result = learn_node(agent, state)

            # track.error called with correct args
            mock_track.error.assert_called_once_with(
                iter=1,
                indicators_count=1,
                confidence=0.85,
                method="visual_color",
                filtered_by_size=2,
                filtered_by_region=1,
                filtered_by_count=False,
            )

    @patch("rv_agent.agent.nodes.learn_node._detect_validation_error")
    def test_detection_disabled_no_state_changes(self, mock_detect):
        """When detection disabled, no error-related keys in result."""
        mock_detect.return_value = None  # disabled

        agent = _make_mock_agent(error_detection_enabled=False)
        state = _make_state(
            error_detection_screenshot="/tmp/screenshot.png",
            current_screen_hash="new_hash",
        )
        agent.last_screen_hash = "old_hash"

        result = learn_node(agent, state)

        # No error-related keys added
        assert "force_fill_input" not in result
        assert "error_indicators" not in result
