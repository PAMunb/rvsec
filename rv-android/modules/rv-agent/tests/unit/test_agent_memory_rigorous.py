"""
AgentMemoryManager rigorous unit tests.

Tests action history management, activity visit tracking, navigation path,
exploration summaries, and memory insights generation.
"""

import pytest

from rv_agent.memory.agent_memory import AgentMemoryManager

pytestmark = pytest.mark.unit


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def memory():
    """Fresh AgentMemoryManager instance."""
    return AgentMemoryManager(max_action_history=5, max_navigation_path=5)


@pytest.fixture
def small_memory():
    """AgentMemoryManager with small limits for edge case testing."""
    return AgentMemoryManager(max_action_history=2, max_navigation_path=2)


# =============================================================================
# Initialization Tests
# =============================================================================


class TestAgentMemoryInit:
    """Test AgentMemoryManager initialization."""

    def test_default_initialization(self):
        """Default initialization with default limits."""
        memory = AgentMemoryManager()

        assert memory.max_action_history == 5
        assert memory.max_navigation_path == 5
        assert len(memory.action_history) == 0
        assert len(memory.activity_visits) == 0
        assert len(memory.navigation_path) == 0

    def test_custom_initialization(self, small_memory):
        """Custom initialization with specified limits."""
        assert small_memory.max_action_history == 2
        assert small_memory.max_navigation_path == 2


# =============================================================================
# Record Action Tests
# =============================================================================


class TestRecordAction:
    """Test record_action method."""

    def test_record_single_action(self, memory):
        """Record single action correctly."""
        action = {"action_type": "CLICK", "explanation": "Click button"}

        memory.record_action(action, "MainActivity", success=True)

        assert len(memory.action_history) == 1
        record = memory.action_history[0]
        assert record["action_type"] == "CLICK"
        assert record["explanation"] == "Click button"
        assert record["activity"] == "MainActivity"
        assert record["success"] is True

    def test_record_multiple_actions(self, memory):
        """Record multiple actions maintains order (deque)."""
        for i in range(3):
            memory.record_action(
                {"action_type": f"ACTION_{i}", "explanation": f"Action {i}"},
                "Main",
                success=True,
            )

        assert len(memory.action_history) == 3
        # Deque maintains insertion order
        assert memory.action_history[0]["action_type"] == "ACTION_0"
        assert memory.action_history[2]["action_type"] == "ACTION_2"

    def test_record_action_limit(self, small_memory):
        """Action history respects max_action_history limit."""
        for i in range(5):
            small_memory.record_action(
                {"action_type": f"ACTION_{i}"}, "Main", success=True
            )

        # Should only keep last 2 (max_action_history=2)
        assert len(small_memory.action_history) == 2
        # Oldest should be dropped, newest kept
        assert small_memory.action_history[0]["action_type"] == "ACTION_3"
        assert small_memory.action_history[1]["action_type"] == "ACTION_4"

    def test_record_action_failed(self, memory):
        """Record failed action correctly."""
        memory.record_action({"action_type": "CLICK"}, "Main", success=False)

        assert memory.action_history[0]["success"] is False

    def test_record_action_missing_fields(self, memory):
        """Handle action with missing optional fields."""
        memory.record_action({}, "Main", success=True)

        record = memory.action_history[0]
        assert record["action_type"] == "unknown"
        assert record["explanation"] == ""


# =============================================================================
# Activity Visits Tests
# =============================================================================


class TestActivityVisits:
    """Test activity visit tracking."""

    def test_track_single_activity(self, memory):
        """Track visits to single activity."""
        memory.record_action({"action_type": "CLICK"}, "MainActivity", success=True)
        memory.record_action({"action_type": "CLICK"}, "MainActivity", success=True)
        memory.record_action({"action_type": "CLICK"}, "MainActivity", success=True)

        assert memory.activity_visits["MainActivity"] == 3

    def test_track_multiple_activities(self, memory):
        """Track visits to multiple activities."""
        memory.record_action({"action_type": "CLICK"}, "MainActivity", success=True)
        memory.record_action({"action_type": "CLICK"}, "DetailActivity", success=True)
        memory.record_action({"action_type": "CLICK"}, "MainActivity", success=True)
        memory.record_action({"action_type": "CLICK"}, "SettingsActivity", success=True)

        assert memory.activity_visits["MainActivity"] == 2
        assert memory.activity_visits["DetailActivity"] == 1
        assert memory.activity_visits["SettingsActivity"] == 1


# =============================================================================
# Navigation Path Tests
# =============================================================================


class TestNavigationPath:
    """Test navigation path tracking."""

    def test_navigation_path_starts_empty(self, memory):
        """Navigation path starts empty."""
        assert len(memory.navigation_path) == 0

    def test_navigation_path_adds_activity(self, memory):
        """Navigation path adds new activities."""
        memory.record_action({"action_type": "CLICK"}, "MainActivity", success=True)

        assert memory.navigation_path == ["MainActivity"]

    def test_navigation_path_no_duplicate_consecutive(self, memory):
        """Navigation path ignores consecutive same activity."""
        memory.record_action({"action_type": "CLICK"}, "MainActivity", success=True)
        memory.record_action({"action_type": "CLICK"}, "MainActivity", success=True)
        memory.record_action({"action_type": "CLICK"}, "MainActivity", success=True)

        # Should only have one entry
        assert memory.navigation_path == ["MainActivity"]

    def test_navigation_path_sequence(self, memory):
        """Navigation path tracks activity sequence."""
        memory.record_action({}, "Main", success=True)
        memory.record_action({}, "Detail", success=True)
        memory.record_action({}, "Settings", success=True)

        assert memory.navigation_path == ["Main", "Detail", "Settings"]

    def test_navigation_path_limit(self, small_memory):
        """Navigation path respects max_navigation_path limit."""
        for activity in ["A1", "A2", "A3", "A4", "A5"]:
            small_memory.record_action({}, activity, success=True)

        # Should only keep last 2 (max_navigation_path=2)
        assert len(small_memory.navigation_path) == 2
        assert small_memory.navigation_path == ["A4", "A5"]


# =============================================================================
# Action History Summary Tests
# =============================================================================


class TestActionHistorySummary:
    """Test get_action_history_summary method."""

    def test_empty_history_summary(self, memory):
        """Empty history returns appropriate message."""
        summary = memory.get_action_history_summary()

        assert "No previous actions" in summary

    def test_single_action_summary(self, memory):
        """Single action formatted correctly."""
        memory.record_action(
            {"action_type": "CLICK", "explanation": "Tap login button"},
            "Main",
            success=True,
        )

        summary = memory.get_action_history_summary()

        assert "Recent actions (1)" in summary
        assert "1. CLICK at (0, 0): Tap login button" in summary

    def test_multiple_actions_summary(self, memory):
        """Multiple actions formatted with numbers."""
        memory.record_action(
            {"action_type": "CLICK", "explanation": "Click A"}, "M", success=True
        )
        memory.record_action(
            {"action_type": "SCROLL", "explanation": "Scroll down"}, "M", success=True
        )
        memory.record_action(
            {"action_type": "SET_TEXT", "explanation": "Enter text"}, "M", success=True
        )

        summary = memory.get_action_history_summary()

        assert "Recent actions (3)" in summary
        assert "1. CLICK at (0, 0): Click A" in summary
        assert "2. SCROLL at (0, 0): Scroll down" in summary
        assert "3. SET_TEXT at (0, 0): Enter text" in summary

    def test_failed_action_marker(self, memory):
        """Failed actions marked with [FAILED]."""
        memory.record_action(
            {"action_type": "CLICK", "explanation": "Failed"}, "M", success=False
        )

        summary = memory.get_action_history_summary()

        assert "[FAILED]" in summary


# =============================================================================
# Exploration Summary Tests
# =============================================================================


class TestExplorationSummary:
    """Test get_exploration_summary method."""

    def test_exploration_summary_basic(self, memory):
        """Exploration summary includes key metrics."""
        memory.record_action({}, "MainActivity", success=True)
        memory.record_action({}, "DetailActivity", success=True)

        visited_states = ["hash1", "hash2", "hash3"]
        transitions = [("hash1", "hash2"), ("hash2", "hash3")]

        summary = memory.get_exploration_summary(visited_states, transitions)

        assert "Exploration Progress" in summary
        assert "Unique screens visited: 3" in summary
        assert "State transitions discovered: 2" in summary
        assert "Activities explored: 2" in summary

    def test_exploration_summary_empty(self, memory):
        """Exploration summary with no exploration."""
        summary = memory.get_exploration_summary([], [])

        assert "Unique screens visited: 0" in summary
        assert "State transitions discovered: 0" in summary
        assert "Activities explored: 0" in summary


# =============================================================================
# Memory Insights Tests
# =============================================================================


class TestMemoryInsights:
    """Test get_memory_insights method."""

    def test_memory_insights_single_activity(self, memory):
        """Memory insights for single activity."""
        memory.record_action({}, "MainActivity", success=True)
        memory.record_action({}, "MainActivity", success=True)

        insights = memory.get_memory_insights("MainActivity")

        assert "Memory Insights" in insights
        assert "'MainActivity' visited 2 time(s)" in insights
        assert "Total activities explored: 1" in insights
        assert "discover new activities" in insights

    def test_memory_insights_multiple_activities(self, memory):
        """Memory insights suggest least visited activity."""
        memory.record_action({}, "MainActivity", success=True)
        memory.record_action({}, "MainActivity", success=True)
        memory.record_action({}, "MainActivity", success=True)
        memory.record_action({}, "DetailActivity", success=True)
        memory.record_action({}, "SettingsActivity", success=True)

        insights = memory.get_memory_insights("MainActivity")

        assert "Total activities explored: 3" in insights
        # Should suggest DetailActivity or SettingsActivity (both 1 visit)
        assert "consider exploring" in insights

    def test_memory_insights_current_is_least_visited(self, memory):
        """Don't suggest current activity even if least visited."""
        memory.record_action({}, "MainActivity", success=True)
        memory.record_action({}, "MainActivity", success=True)
        memory.record_action({}, "DetailActivity", success=True)

        insights = memory.get_memory_insights("DetailActivity")

        # Should not suggest DetailActivity since it's current
        assert (
            "'DetailActivity'" not in insights
            or "consider exploring" not in insights.split("DetailActivity")[1]
        )


# =============================================================================
# Navigation Path Summary Tests
# =============================================================================


class TestNavigationPathSummary:
    """Test get_navigation_path method."""

    def test_navigation_path_empty(self, memory):
        """Navigation path with no activities."""
        path = memory.get_navigation_path()

        assert "Starting exploration" in path

    def test_navigation_path_single(self, memory):
        """Navigation path with single activity."""
        memory.record_action({}, "MainActivity", success=True)

        path = memory.get_navigation_path()

        assert "Navigation Path:" in path
        assert "MainActivity" in path

    def test_navigation_path_sequence(self, memory):
        """Navigation path shows activity sequence."""
        memory.record_action({}, "Main", success=True)
        memory.record_action({}, "Detail", success=True)
        memory.record_action({}, "Settings", success=True)

        path = memory.get_navigation_path()

        assert "Main → Detail → Settings" in path


# =============================================================================
# Clear Memory Tests
# =============================================================================


class TestClearMemory:
    """Test clear method."""

    def test_clear_all_memory(self, memory):
        """Clear resets all memory state."""
        # Populate memory
        memory.record_action({"action_type": "CLICK"}, "Main", success=True)
        memory.record_action({"action_type": "SCROLL"}, "Detail", success=True)

        memory.clear()

        assert len(memory.action_history) == 0
        assert len(memory.activity_visits) == 0
        assert len(memory.navigation_path) == 0


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_activity_name(self, memory):
        """Handle empty activity name."""
        memory.record_action({}, "", success=True)

        assert "" in memory.activity_visits
        assert memory.navigation_path == [""]

    def test_special_characters_in_activity(self, memory):
        """Handle special characters in activity name."""
        activity = "com.example.app/.MainActivity$InnerClass"
        memory.record_action({}, activity, success=True)

        assert activity in memory.activity_visits

    def test_unicode_in_explanation(self, memory):
        """Handle unicode characters in explanation."""
        memory.record_action(
            {"action_type": "CLICK", "explanation": "点击按钮 🔘"}, "Main", success=True
        )

        summary = memory.get_action_history_summary()
        assert "点击按钮" in summary

    def test_very_long_explanation(self, memory):
        """Handle very long explanation text."""
        long_text = "A" * 1000
        memory.record_action(
            {"action_type": "CLICK", "explanation": long_text}, "Main", success=True
        )

        summary = memory.get_action_history_summary()
        assert long_text in summary

    def test_rapid_activity_changes(self, memory):
        """Handle rapid activity changes."""
        for i in range(100):
            memory.record_action({}, f"Activity_{i % 10}", success=True)

        # Should handle without error
        assert len(memory.activity_visits) == 10
        assert len(memory.navigation_path) == memory.max_navigation_path
