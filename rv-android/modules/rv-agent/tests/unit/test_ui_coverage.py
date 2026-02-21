"""
Unit tests for UICoverageTracker.

Tests element tracking, annotation, coverage statistics, and exploration suggestions.
"""

import pytest
from unittest.mock import MagicMock, patch
import time

from rv_agent.memory.ui_coverage import UICoverageTracker, UIElementStats


class TestUIElementStats:
    """Test UIElementStats dataclass."""

    def test_coverage_percentage_zero_elements(self):
        """Coverage is 0% with no elements."""
        stats = UIElementStats(total_elements=0, tested_elements=0, untested_elements=0)
        assert stats.coverage_percentage == 0.0

    def test_coverage_percentage_all_tested(self):
        """Coverage is 100% when all tested."""
        stats = UIElementStats(
            total_elements=10, tested_elements=10, untested_elements=0
        )
        assert stats.coverage_percentage == 100.0

    def test_coverage_percentage_half_tested(self):
        """Coverage is 50% when half tested."""
        stats = UIElementStats(
            total_elements=10, tested_elements=5, untested_elements=5
        )
        assert stats.coverage_percentage == 50.0

    def test_discovery_rate_zero_elements(self):
        """Discovery rate is 0 with no elements."""
        stats = UIElementStats(total_elements=0, tested_elements=0, untested_elements=0)
        assert stats.discovery_rate == 0.0

    def test_discovery_rate_calculation(self):
        """Discovery rate calculation."""
        stats = UIElementStats(
            total_elements=10, tested_elements=3, untested_elements=7
        )
        assert stats.discovery_rate == 0.3


class TestUICoverageTrackerInit:
    """Test UICoverageTracker initialization."""

    def test_initialization(self):
        """Tracker initializes with empty collections."""
        tracker = UICoverageTracker()

        assert len(tracker.tested_elements) == 0
        assert len(tracker.action_type_counts) == 0
        assert len(tracker.screen_elements) == 0
        assert len(tracker.first_interactions) == 0
        assert len(tracker.last_interactions) == 0
        assert len(tracker.discovery_timeline) == 0


class TestRecordInteraction:
    """Test record_interaction method."""

    def test_record_new_element(self):
        """Recording new element adds to tested_elements."""
        tracker = UICoverageTracker()

        tracker.record_interaction("element1", "click", "screen1")

        assert "element1" in tracker.tested_elements
        assert tracker.tested_elements["element1"] == 1
        assert "click" in tracker.action_type_counts
        assert "screen1" in tracker.screen_elements
        assert "element1" in tracker.screen_elements["screen1"]

    def test_record_existing_element(self):
        """Recording existing element increments count."""
        tracker = UICoverageTracker()

        tracker.record_interaction("element1", "click")
        tracker.record_interaction("element1", "click")

        assert tracker.tested_elements["element1"] == 2

    def test_record_multiple_action_types(self):
        """Records different action types."""
        tracker = UICoverageTracker()

        tracker.record_interaction("element1", "click")
        tracker.record_interaction("element2", "type")
        tracker.record_interaction("element3", "scroll")

        assert tracker.action_type_counts["click"] == 1
        assert tracker.action_type_counts["type"] == 1
        assert tracker.action_type_counts["scroll"] == 1

    def test_record_temporal_tracking(self):
        """Tracks first and last interaction times."""
        tracker = UICoverageTracker()

        tracker.record_interaction("element1", "click")

        assert "element1" in tracker.first_interactions
        assert "element1" in tracker.last_interactions

    def test_record_discovery_timeline(self):
        """New elements added to discovery timeline."""
        tracker = UICoverageTracker()

        tracker.record_interaction("element1", "click", "screen1")

        assert len(tracker.discovery_timeline) == 1
        assert tracker.discovery_timeline[0]["element_id"] == "element1"


class TestIsElementUntested:
    """Test is_element_untested method."""

    def test_untested_element(self):
        """Untested element returns True."""
        tracker = UICoverageTracker()

        assert tracker.is_element_untested("unknown_element") is True

    def test_tested_element(self):
        """Tested element returns False."""
        tracker = UICoverageTracker()
        tracker.record_interaction("element1", "click")

        assert tracker.is_element_untested("element1") is False

    def test_empty_element_id(self):
        """Empty element ID returns False."""
        tracker = UICoverageTracker()

        assert tracker.is_element_untested("") is False


class TestGetElementTestCount:
    """Test get_element_test_count method."""

    def test_untested_element_count_zero(self):
        """Untested element has count 0."""
        tracker = UICoverageTracker()

        assert tracker.get_element_test_count("unknown") == 0

    def test_tested_element_count(self):
        """Tested element has correct count."""
        tracker = UICoverageTracker()
        tracker.record_interaction("element1", "click")
        tracker.record_interaction("element1", "click")
        tracker.record_interaction("element1", "click")

        assert tracker.get_element_test_count("element1") == 3

    def test_empty_element_id_count(self):
        """Empty element ID returns 0."""
        tracker = UICoverageTracker()

        assert tracker.get_element_test_count("") == 0


class TestGetElementPriority:
    """Test get_element_priority method."""

    def test_untested_high_priority(self):
        """Untested elements have high priority."""
        tracker = UICoverageTracker()

        assert tracker.get_element_priority("unknown") == "high"

    def test_lightly_tested_medium_priority(self):
        """Lightly tested elements have medium priority."""
        tracker = UICoverageTracker()
        tracker.record_interaction("element1", "click")
        tracker.record_interaction("element1", "click")

        assert tracker.get_element_priority("element1") == "medium"

    def test_well_tested_low_priority(self):
        """Well tested elements have low priority."""
        tracker = UICoverageTracker()
        for _ in range(5):
            tracker.record_interaction("element1", "click")

        assert tracker.get_element_priority("element1") == "low"


class TestRegisterScreenElements:
    """Test register_screen_elements method."""

    def test_register_elements_from_screen_desc(self):
        """Registers elements from a ScreenDescription with their types."""
        tracker = UICoverageTracker()

        screen_desc = MagicMock()
        item1 = MagicMock()
        item1.view = {
            "class": "android.widget.Button",
            "bounds": [[50, 100], [150, 300]],
        }
        item2 = MagicMock()
        item2.view = {
            "class": "android.widget.EditText",
            "bounds": [[50, 400], [150, 600]],
        }
        screen_desc.items = [item1, item2]

        tracker.register_screen_elements("screen1", screen_desc)

        assert "screen1" in tracker.screen_elements
        assert len(tracker.screen_elements["screen1"]) == 2
        assert len(tracker.element_types) == 2

    def test_register_elements_stores_component_type(self):
        """Registered elements have correct component type."""
        tracker = UICoverageTracker()

        screen_desc = MagicMock()
        item = MagicMock()
        item.view = {
            "class": "android.widget.Button",
            "bounds": [[100, 200], [300, 400]],
        }
        screen_desc.items = [item]

        tracker.register_screen_elements("screen1", screen_desc)

        # Element type should be the simple class name
        for elem_id, comp_type in tracker.element_types.items():
            assert comp_type == "Button"

    def test_register_empty_screen(self):
        """Registering empty screen creates entry with no elements."""
        tracker = UICoverageTracker()

        screen_desc = MagicMock()
        screen_desc.items = []

        tracker.register_screen_elements("screen1", screen_desc)

        assert "screen1" in tracker.screen_elements
        assert len(tracker.screen_elements["screen1"]) == 0

    def test_register_idempotent(self):
        """Re-registering same screen does not duplicate elements."""
        tracker = UICoverageTracker()

        screen_desc = MagicMock()
        item = MagicMock()
        item.view = {
            "class": "android.widget.Button",
            "bounds": [[100, 200], [300, 400]],
        }
        screen_desc.items = [item]

        tracker.register_screen_elements("screen1", screen_desc)
        tracker.register_screen_elements("screen1", screen_desc)

        assert len(tracker.screen_elements["screen1"]) == 1


class TestGetElementTestCountAndPriority:
    """Test element test count and priority logic (replaces removed annotation methods)."""

    def test_untested_count_zero(self):
        """Untested element returns count 0."""
        tracker = UICoverageTracker()

        assert tracker.get_element_test_count("unknown") == 0

    def test_tested_once_count(self):
        """Tested once returns count 1."""
        tracker = UICoverageTracker()
        tracker.record_interaction("element1", "click")

        assert tracker.get_element_test_count("element1") == 1

    def test_tested_multiple_count(self):
        """Tested multiple times returns correct count."""
        tracker = UICoverageTracker()
        for _ in range(3):
            tracker.record_interaction("element1", "click")

        assert tracker.get_element_test_count("element1") == 3

    def test_well_tested_low_priority(self):
        """Well tested element gets low priority."""
        tracker = UICoverageTracker()
        for _ in range(10):
            tracker.record_interaction("element1", "click")

        assert tracker.get_element_priority("element1") == "low"


class TestGetScreenCoverageStats:
    """Test get_screen_coverage_stats method."""

    def test_unknown_screen_empty_stats(self):
        """Unknown screen returns empty stats."""
        tracker = UICoverageTracker()

        stats = tracker.get_screen_coverage_stats("unknown")

        assert stats.total_elements == 0

    def test_screen_with_elements(self):
        """Screen with elements returns correct stats."""
        tracker = UICoverageTracker()

        # Record some interactions
        tracker.record_interaction("element1", "click", "screen1")
        tracker.record_interaction("element2", "click", "screen1")

        stats = tracker.get_screen_coverage_stats("screen1")

        assert stats.total_elements == 2
        assert stats.tested_elements == 2


class TestGetExplorationSuggestions:
    """Test get_exploration_suggestions method."""

    def test_unknown_screen_suggestions(self):
        """Unknown screen suggests exploration."""
        tracker = UICoverageTracker()

        suggestions = tracker.get_exploration_suggestions("unknown")

        assert len(suggestions) == 1
        assert suggestions[0]["suggestion"] == "explore_new_screen"

    def test_untested_element_suggestions(self):
        """Suggests untested elements first."""
        tracker = UICoverageTracker()

        # Add elements to screen but don't test them
        tracker.screen_elements["screen1"] = {"element1", "element2"}

        suggestions = tracker.get_exploration_suggestions("screen1")

        assert len(suggestions) >= 1
        assert suggestions[0]["suggestion"] == "test_untested_element"
        assert suggestions[0]["priority"] == "high"

    def test_lightly_tested_suggestions(self):
        """Suggests lightly tested elements when all tested."""
        tracker = UICoverageTracker()

        # Record interactions for all elements
        tracker.record_interaction("element1", "click", "screen1")
        tracker.record_interaction("element2", "click", "screen1")
        tracker.record_interaction("element2", "click", "screen1")

        suggestions = tracker.get_exploration_suggestions("screen1")

        # Should suggest the one with fewer tests
        if suggestions:
            assert any(
                s.get("suggestion")
                in ["retest_lightly_tested", "explore_different_actions"]
                for s in suggestions
            )

    def test_all_well_tested_suggestions(self):
        """Suggests different actions when all well tested."""
        tracker = UICoverageTracker()

        # Test elements many times
        for _ in range(10):
            tracker.record_interaction("element1", "click", "screen1")
            tracker.record_interaction("element2", "click", "screen1")

        suggestions = tracker.get_exploration_suggestions("screen1")

        assert any(
            s.get("suggestion") == "explore_different_actions" for s in suggestions
        )


class TestGetOverallStatistics:
    """Test get_overall_statistics method."""

    def test_empty_statistics(self):
        """Empty tracker returns zero stats."""
        tracker = UICoverageTracker()

        stats = tracker.get_overall_statistics()

        assert stats["total_unique_elements"] == 0
        assert stats["total_interactions"] == 0
        assert stats["total_screens"] == 0

    def test_statistics_after_interactions(self):
        """Stats reflect recorded interactions."""
        tracker = UICoverageTracker()

        tracker.record_interaction("element1", "click", "screen1")
        tracker.record_interaction("element2", "type", "screen1")
        tracker.record_interaction("element1", "click", "screen2")

        stats = tracker.get_overall_statistics()

        assert stats["total_unique_elements"] == 2
        assert stats["total_interactions"] == 3
        assert stats["total_screens"] == 2
        assert "click" in stats["action_distribution"]
        assert "type" in stats["action_distribution"]


class TestResetCoverage:
    """Test reset_coverage method."""

    def test_reset_clears_all_data(self):
        """Reset clears all tracking data."""
        tracker = UICoverageTracker()

        # Record some data
        tracker.record_interaction("element1", "click", "screen1")
        tracker.record_interaction("element2", "type", "screen2")

        # Verify data exists
        assert len(tracker.tested_elements) > 0

        # Reset
        tracker.reset_coverage()

        # Verify all cleared
        assert len(tracker.tested_elements) == 0
        assert len(tracker.action_type_counts) == 0
        assert len(tracker.screen_elements) == 0
        assert len(tracker.first_interactions) == 0
        assert len(tracker.last_interactions) == 0
        assert len(tracker.discovery_timeline) == 0
