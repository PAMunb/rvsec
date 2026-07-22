"""
Unit tests for TransitionManager.

Tests integration of static WTG with dynamic exploration graph.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.services.transition_manager import TransitionManager
from rv_android_core.domain.static import StaticAnalysisData
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription
from rv_static_analysis.parser.static.static_analysis_parser import parse_file

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def fixtures_path():
    """Path to test fixtures."""
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def static_analysis_path(fixtures_path):
    """Path to static analysis fixtures."""
    return fixtures_path / "static_analysis" / "cryptoapp"


@pytest.fixture
def static_data(static_analysis_path) -> StaticAnalysisData:
    """Load real static analysis data from unified JSON."""
    json_file = str(static_analysis_path / "cryptoapp.apk.json")
    return parse_file(json_file, "br.unb.cic.cryptoapp")


@pytest.fixture
def dynamic_graph():
    """Create empty dynamic state graph."""
    return DynamicStateGraph()


@pytest.fixture
def transition_manager(static_data, dynamic_graph):
    """Create TransitionManager with static data."""
    return TransitionManager(static_data, dynamic_graph)


# =============================================================================
# Test: Initialization
# =============================================================================


class TestTransitionManagerInit:
    """Test TransitionManager initialization."""

    def test_init_with_static_data(self, static_data, dynamic_graph):
        """Manager initializes with static data."""
        manager = TransitionManager(static_data, dynamic_graph)

        assert manager.static_data is static_data
        assert manager.dynamic_graph is dynamic_graph
        assert manager.wtg is not None

    def test_init_without_static_data(self, dynamic_graph):
        """Manager initializes gracefully without static data."""
        manager = TransitionManager(None, dynamic_graph)

        assert manager.static_data is None
        assert manager.wtg is None
        assert manager.dynamic_graph is dynamic_graph

    def test_visited_activities_initially_empty(self, transition_manager):
        """Visited activities starts empty."""
        assert len(transition_manager._visited_activities) == 0


# =============================================================================
# Test: Window ID Mapping
# =============================================================================


class TestWindowIdMapping:
    """Test activity to window ID mapping."""

    def test_find_window_id_for_main_activity(self, transition_manager):
        """Find window ID for MainActivity."""
        window_id = transition_manager.find_window_id_for_activity(
            "br.unb.cic.cryptoapp.MainActivity"
        )

        assert window_id is not None

    def test_find_window_id_for_cipher_activity(self, transition_manager):
        """Find window ID for CipherActivity."""
        window_id = transition_manager.find_window_id_for_activity(
            "br.unb.cic.cryptoapp.cipher.CipherActivity"
        )

        assert window_id is not None

    def test_caching_window_id(self, transition_manager):
        """Window ID mapping is cached."""
        activity = "br.unb.cic.cryptoapp.MainActivity"

        # First call
        window_id1 = transition_manager.find_window_id_for_activity(activity)

        # Should be cached
        assert activity in transition_manager._activity_to_window_id

        # Second call returns same value
        window_id2 = transition_manager.find_window_id_for_activity(activity)

        assert window_id1 == window_id2

    def test_no_window_id_for_unknown_activity(self, transition_manager):
        """No window ID for unknown activity."""
        window_id = transition_manager.find_window_id_for_activity(
            "com.unknown.UnknownActivity"
        )

        assert window_id is None


# =============================================================================
# Test: Activity Tracking
# =============================================================================


class TestActivityTracking:
    """Test activity visit tracking."""

    def test_mark_activity_visited(self, transition_manager):
        """Mark activity as visited."""
        activity = "br.unb.cic.cryptoapp.MainActivity"

        transition_manager.mark_activity_visited(activity)

        assert activity in transition_manager._visited_activities

    def test_multiple_activities_visited(self, transition_manager):
        """Track multiple visited activities."""
        activities = [
            "br.unb.cic.cryptoapp.MainActivity",
            "br.unb.cic.cryptoapp.cipher.CipherActivity",
        ]

        for activity in activities:
            transition_manager.mark_activity_visited(activity)

        assert len(transition_manager._visited_activities) == 2
        for activity in activities:
            assert activity in transition_manager._visited_activities


# =============================================================================
# Test: Navigation Targets
# =============================================================================


class TestNavigationTargets:
    """Test unvisited target retrieval."""

    def test_get_unvisited_targets_from_main(self, transition_manager):
        """Get unvisited targets from MainActivity."""
        targets = transition_manager.get_unvisited_targets(
            "br.unb.cic.cryptoapp.MainActivity"
        )

        # MainActivity should have transitions to other activities
        assert isinstance(targets, list)

    def test_unvisited_targets_sorted_by_priority(self, transition_manager):
        """Targets are sorted by priority (descending)."""
        targets = transition_manager.get_unvisited_targets(
            "br.unb.cic.cryptoapp.MainActivity"
        )

        if len(targets) >= 2:
            # Verify sorted by priority descending
            for i in range(len(targets) - 1):
                assert targets[i]["priority"] >= targets[i + 1]["priority"]

    def test_visited_targets_have_lower_priority(self, transition_manager):
        """Visited targets have lower priority than unvisited."""
        # Mark an activity as visited
        transition_manager.mark_activity_visited(
            "br.unb.cic.cryptoapp.cipher.CipherActivity"
        )

        targets = transition_manager.get_unvisited_targets(
            "br.unb.cic.cryptoapp.MainActivity"
        )

        # Find visited and unvisited targets
        visited_targets = [t for t in targets if t.get("visited")]
        unvisited_targets = [t for t in targets if not t.get("visited")]

        if visited_targets and unvisited_targets:
            # All unvisited should have higher priority than visited
            max_visited_priority = max(t["priority"] for t in visited_targets)
            min_unvisited_priority = min(t["priority"] for t in unvisited_targets)

            assert min_unvisited_priority > max_visited_priority

    def test_no_targets_without_wtg(self, dynamic_graph):
        """No targets when WTG is not available."""
        manager = TransitionManager(None, dynamic_graph)

        targets = manager.get_unvisited_targets("com.example.MainActivity")

        assert targets == []


# =============================================================================
# Test: Navigation Guidance
# =============================================================================


class TestNavigationGuidance:
    """Test comprehensive navigation guidance."""

    def test_get_navigation_guidance(self, transition_manager):
        """Get navigation guidance for current screen."""
        # Create mock screen description
        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.items = []
        screen_desc.events_by_id = {}

        guidance = transition_manager.get_navigation_guidance(
            "br.unb.cic.cryptoapp.MainActivity", screen_desc
        )

        assert "unvisited_targets" in guidance
        assert "suggested_actions" in guidance
        assert "exploration_progress" in guidance
        assert "has_static_guidance" in guidance

    def test_guidance_marks_activity_visited(self, transition_manager):
        """Getting guidance marks activity as visited."""
        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.items = []
        screen_desc.events_by_id = {}

        activity = "br.unb.cic.cryptoapp.MainActivity"

        transition_manager.get_navigation_guidance(activity, screen_desc)

        assert activity in transition_manager._visited_activities

    def test_exploration_progress_includes_metrics(self, transition_manager):
        """Exploration progress includes coverage metrics."""
        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.items = []
        screen_desc.events_by_id = {}

        guidance = transition_manager.get_navigation_guidance(
            "br.unb.cic.cryptoapp.MainActivity", screen_desc
        )

        progress = guidance["exploration_progress"]
        assert "total_windows" in progress
        assert "visited_activities" in progress
        assert "coverage_percent" in progress


# =============================================================================
# Test: Exploration Summary
# =============================================================================


class TestExplorationSummary:
    """Test exploration summary."""

    def test_get_exploration_summary(self, transition_manager):
        """Get exploration summary."""
        # Visit some activities
        transition_manager.mark_activity_visited("br.unb.cic.cryptoapp.MainActivity")
        transition_manager.mark_activity_visited(
            "br.unb.cic.cryptoapp.cipher.CipherActivity"
        )

        summary = transition_manager.get_exploration_summary()

        assert "visited_activities" in summary
        assert "visited_count" in summary
        assert "dynamic_states" in summary
        assert "dynamic_transitions" in summary
        assert "avg_coverage" in summary

        assert summary["visited_count"] == 2

    def test_summary_includes_static_coverage(self, transition_manager):
        """Summary includes static window coverage."""
        summary = transition_manager.get_exploration_summary()

        assert "total_static_windows" in summary
        assert "static_coverage_percent" in summary


# =============================================================================
# Test: Priority Calculation
# =============================================================================


class TestPriorityCalculation:
    """Test target priority calculation."""

    def test_unvisited_has_higher_base_priority(self, transition_manager):
        """Unvisited targets get +100 priority."""
        # Calculate for unvisited
        priority_unvisited = transition_manager._calculate_target_priority(
            target_id="1395", visited=False, widget_id=None
        )

        # Calculate for visited
        priority_visited = transition_manager._calculate_target_priority(
            target_id="1395", visited=True, widget_id=None
        )

        assert priority_unvisited > priority_visited
        assert priority_unvisited - priority_visited == 100
