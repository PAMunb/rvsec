"""
Unit tests for Group 43: NavigationGuidance error handling (D15).

Design ref: D15 (R3-2 LOW)

Scenarios:
- R3-2-S1: TransitionManager raises KeyError -> logged at ERROR, counter incremented, empty context returned
- R3-2-S2: Multiple errors in sequence -> counter incremented each time
- R3-2-S3: Normal operation -> context returned, no counter increment
"""

import logging
from unittest.mock import MagicMock

import pytest

from rv_agent import tracking as track
from rv_agent.services.navigation_guidance import ExplorationContext, NavigationGuidance
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_screen_desc():
    """Create a mock ScreenDescription for testing."""
    screen_desc = MagicMock(spec=ScreenDescription)
    screen_desc.activity = "com.example.app.MainActivity"
    screen_desc.items = []
    screen_desc.events_by_id = {}
    return screen_desc


@pytest.fixture
def mock_transition_manager():
    """Create a mock TransitionManager that returns valid guidance."""
    tm = MagicMock()
    tm.get_navigation_guidance.return_value = {
        "unvisited_targets": [
            {"target_activity": "com.example.SettingsActivity", "visited": False},
        ],
        "suggested_actions": [],
        "exploration_progress": {"coverage_percent": 25.0},
        "has_static_guidance": True,
    }
    return tm


@pytest.fixture(autouse=True)
def reset_tracking_counters():
    """Reset tracking counters before each test."""
    original_value = track._counters.get("navigation_guidance_error", 0)
    track._counters["navigation_guidance_error"] = 0
    yield
    track._counters["navigation_guidance_error"] = original_value


# =============================================================================
# R3-2-S1: TransitionManager raises KeyError
# =============================================================================


class TestNavigationGuidanceErrorHandling:
    """R3-2-S1: TransitionManager exception -> ERROR log, counter increment, empty context."""

    def test_keyerror_returns_empty_context(self, mock_screen_desc):
        """When TransitionManager raises KeyError, get_context returns ExplorationContext(has_guidance=False)."""
        tm = MagicMock()
        tm.get_navigation_guidance.side_effect = KeyError("missing_window_id")

        guidance = NavigationGuidance(transition_manager=tm)
        context = guidance.get_context(mock_screen_desc)

        assert isinstance(context, ExplorationContext)
        assert context.has_guidance is False
        assert context.unvisited_screens == []
        assert context.suggested_actions == []

    def test_keyerror_increments_counter(self, mock_screen_desc):
        """When TransitionManager raises KeyError, navigation_guidance_error counter increments."""
        tm = MagicMock()
        tm.get_navigation_guidance.side_effect = KeyError("missing_window_id")

        guidance = NavigationGuidance(transition_manager=tm)
        guidance.get_context(mock_screen_desc)

        assert track._counters["navigation_guidance_error"] == 1

    def test_keyerror_logs_at_error_level(self, mock_screen_desc, caplog):
        """When TransitionManager raises KeyError, the message is logged at ERROR level."""
        tm = MagicMock()
        tm.get_navigation_guidance.side_effect = KeyError("missing_window_id")

        guidance = NavigationGuidance(transition_manager=tm)

        with caplog.at_level(
            logging.ERROR, logger="rv_agent.services.navigation_guidance"
        ):
            guidance.get_context(mock_screen_desc)

        error_messages = [
            r.message for r in caplog.records if r.levelno == logging.ERROR
        ]
        assert len(error_messages) == 1
        assert "Error getting context" in error_messages[0]

    def test_runtime_error_returns_empty_context(self, mock_screen_desc):
        """Any exception type (e.g. RuntimeError) also returns empty context."""
        tm = MagicMock()
        tm.get_navigation_guidance.side_effect = RuntimeError("unexpected failure")

        guidance = NavigationGuidance(transition_manager=tm)
        context = guidance.get_context(mock_screen_desc)

        assert context.has_guidance is False
        assert track._counters["navigation_guidance_error"] == 1


# =============================================================================
# R3-2-S2: Multiple errors in sequence
# =============================================================================


class TestNavigationGuidanceMultipleErrors:
    """R3-2-S2: Multiple errors -> counter incremented each time."""

    def test_multiple_errors_increment_counter(self, mock_screen_desc):
        """Each error call increments the counter independently."""
        tm = MagicMock()
        tm.get_navigation_guidance.side_effect = KeyError("bad_key")

        guidance = NavigationGuidance(transition_manager=tm)

        guidance.get_context(mock_screen_desc)
        assert track._counters["navigation_guidance_error"] == 1

        guidance.get_context(mock_screen_desc)
        assert track._counters["navigation_guidance_error"] == 2

        guidance.get_context(mock_screen_desc)
        assert track._counters["navigation_guidance_error"] == 3

    def test_interleaved_success_and_error(
        self, mock_screen_desc, mock_transition_manager
    ):
        """Counter only increments on errors, not on successful calls."""
        # First: success
        guidance_ok = NavigationGuidance(transition_manager=mock_transition_manager)
        guidance_ok.get_context(mock_screen_desc)
        assert track._counters["navigation_guidance_error"] == 0

        # Second: error
        tm_bad = MagicMock()
        tm_bad.get_navigation_guidance.side_effect = ValueError("corrupt data")
        guidance_bad = NavigationGuidance(transition_manager=tm_bad)
        guidance_bad.get_context(mock_screen_desc)
        assert track._counters["navigation_guidance_error"] == 1

        # Third: success again
        guidance_ok.get_context(mock_screen_desc)
        assert track._counters["navigation_guidance_error"] == 1


# =============================================================================
# R3-2-S3: Normal operation
# =============================================================================


class TestNavigationGuidanceNormalOperation:
    """R3-2-S3: Normal operation -> context returned, no counter increment."""

    def test_successful_context_no_counter_increment(
        self, mock_screen_desc, mock_transition_manager
    ):
        """Successful get_context does not increment the error counter."""
        guidance = NavigationGuidance(transition_manager=mock_transition_manager)
        context = guidance.get_context(mock_screen_desc)

        assert context.has_guidance is True
        assert len(context.unvisited_screens) == 1
        assert track._counters["navigation_guidance_error"] == 0

    def test_disabled_guidance_no_counter_increment(self, mock_screen_desc):
        """Disabled guidance (no TransitionManager) returns empty context without incrementing counter."""
        guidance = NavigationGuidance(transition_manager=None)
        context = guidance.get_context(mock_screen_desc)

        assert context.has_guidance is False
        assert track._counters["navigation_guidance_error"] == 0

    def test_successful_context_has_expected_fields(
        self, mock_screen_desc, mock_transition_manager
    ):
        """Successful context contains data from TransitionManager."""
        guidance = NavigationGuidance(transition_manager=mock_transition_manager)
        context = guidance.get_context(mock_screen_desc)

        assert context.has_guidance is True
        assert "SettingsActivity" in context.unvisited_screens[0]
        assert context.coverage_percent == 25.0
