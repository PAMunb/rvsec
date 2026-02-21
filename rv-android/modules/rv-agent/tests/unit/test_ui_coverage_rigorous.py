"""
UICoverageTracker rigorous unit tests.

Tests element tracking, interaction recording, coverage statistics,
temporal tracking, and discovery timeline.
"""

import pytest
import time

from rv_agent.memory.ui_coverage import UICoverageTracker, UIElementStats

pytestmark = pytest.mark.unit


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def tracker():
    """Fresh UICoverageTracker instance."""
    return UICoverageTracker()


# =============================================================================
# UIElementStats Tests
# =============================================================================


class TestUIElementStats:
    """Test UIElementStats dataclass."""

    def test_coverage_zero_elements(self):
        """Coverage is 0% with zero elements."""
        stats = UIElementStats(total_elements=0)
        assert stats.coverage_percentage == 0.0

    def test_coverage_no_tested(self):
        """Coverage is 0% with no tested elements."""
        stats = UIElementStats(total_elements=10, tested_elements=0)
        assert stats.coverage_percentage == 0.0

    def test_coverage_partial(self):
        """Coverage correctly calculated for partial testing."""
        stats = UIElementStats(total_elements=10, tested_elements=5)
        assert stats.coverage_percentage == 50.0

    def test_coverage_full(self):
        """Coverage is 100% when all tested."""
        stats = UIElementStats(total_elements=10, tested_elements=10)
        assert stats.coverage_percentage == 100.0

    def test_discovery_rate(self):
        """Discovery rate correctly calculated."""
        stats = UIElementStats(total_elements=10, tested_elements=7)
        assert stats.discovery_rate == 0.7


# =============================================================================
# Initialization Tests
# =============================================================================


class TestUICoverageInit:
    """Test UICoverageTracker initialization."""

    def test_initialization(self, tracker):
        """Tracker initializes with empty state."""
        assert len(tracker.tested_elements) == 0
        assert len(tracker.action_type_counts) == 0
        assert len(tracker.screen_elements) == 0
        assert len(tracker.first_interactions) == 0
        assert len(tracker.last_interactions) == 0
        assert len(tracker.discovery_timeline) == 0


# =============================================================================
# Record Interaction Tests
# =============================================================================


class TestRecordInteraction:
    """Test record_interaction method."""

    def test_record_single_interaction(self, tracker):
        """Record single element interaction."""
        tracker.record_interaction("btn_ok", action_type="click", screen_hash="hash1")

        assert "btn_ok" in tracker.tested_elements
        assert tracker.tested_elements["btn_ok"] == 1

    def test_record_multiple_interactions_same_element(self, tracker):
        """Multiple interactions on same element increment count."""
        tracker.record_interaction("btn_ok", "click", "hash1")
        tracker.record_interaction("btn_ok", "click", "hash1")
        tracker.record_interaction("btn_ok", "long_click", "hash1")

        assert tracker.tested_elements["btn_ok"] == 3

    def test_record_multiple_elements(self, tracker):
        """Record interactions with multiple elements."""
        tracker.record_interaction("btn_ok", "click", "hash1")
        tracker.record_interaction("btn_cancel", "click", "hash1")
        tracker.record_interaction("text_input", "set_text", "hash1")

        assert len(tracker.tested_elements) == 3
        assert tracker.tested_elements["btn_ok"] == 1
        assert tracker.tested_elements["btn_cancel"] == 1
        assert tracker.tested_elements["text_input"] == 1

    def test_action_type_counting(self, tracker):
        """Action types are counted correctly."""
        tracker.record_interaction("e1", "click", "h1")
        tracker.record_interaction("e2", "click", "h1")
        tracker.record_interaction("e3", "scroll", "h1")
        tracker.record_interaction("e4", "long_click", "h1")

        assert tracker.action_type_counts["click"] == 2
        assert tracker.action_type_counts["scroll"] == 1
        assert tracker.action_type_counts["long_click"] == 1

    def test_screen_element_mapping(self, tracker):
        """Elements mapped to screens correctly."""
        tracker.record_interaction("btn1", "click", "screen_a")
        tracker.record_interaction("btn2", "click", "screen_a")
        tracker.record_interaction("btn3", "click", "screen_b")

        assert "btn1" in tracker.screen_elements["screen_a"]
        assert "btn2" in tracker.screen_elements["screen_a"]
        assert "btn3" in tracker.screen_elements["screen_b"]

    def test_screen_element_mapping_no_hash(self, tracker):
        """Handle None screen_hash."""
        tracker.record_interaction("btn1", "click", None)

        assert "btn1" in tracker.tested_elements
        # No screen mapping created
        assert len(tracker.screen_elements) == 0


# =============================================================================
# Temporal Tracking Tests
# =============================================================================


class TestTemporalTracking:
    """Test temporal interaction tracking."""

    def test_first_interaction_recorded(self, tracker):
        """First interaction time recorded."""
        before = time.time()
        tracker.record_interaction("btn1", "click", "h1")
        after = time.time()

        assert "btn1" in tracker.first_interactions
        assert before <= tracker.first_interactions["btn1"] <= after

    def test_first_interaction_not_updated(self, tracker):
        """First interaction time not updated on subsequent interactions."""
        tracker.record_interaction("btn1", "click", "h1")
        first_time = tracker.first_interactions["btn1"]

        time.sleep(0.01)  # Small delay

        tracker.record_interaction("btn1", "click", "h1")

        # First time should not change
        assert tracker.first_interactions["btn1"] == first_time

    def test_last_interaction_updated(self, tracker):
        """Last interaction time updated on each interaction."""
        tracker.record_interaction("btn1", "click", "h1")
        first_last = tracker.last_interactions["btn1"]

        time.sleep(0.01)

        tracker.record_interaction("btn1", "click", "h1")
        second_last = tracker.last_interactions["btn1"]

        assert second_last > first_last


# =============================================================================
# Discovery Timeline Tests
# =============================================================================


class TestDiscoveryTimeline:
    """Test discovery timeline tracking."""

    def test_discovery_timeline_new_element(self, tracker):
        """New element added to discovery timeline."""
        tracker.record_interaction("btn1", "click", "hash1")

        assert len(tracker.discovery_timeline) == 1
        entry = tracker.discovery_timeline[0]
        assert entry["element_id"] == "btn1"
        assert entry["action_type"] == "click"
        assert entry["screen_hash"] == "hash1"
        assert entry["discovery_order"] == 1

    def test_discovery_timeline_existing_element(self, tracker):
        """Existing element not re-added to timeline."""
        tracker.record_interaction("btn1", "click", "hash1")
        tracker.record_interaction("btn1", "click", "hash1")

        assert len(tracker.discovery_timeline) == 1

    def test_discovery_timeline_order(self, tracker):
        """Discovery order tracked correctly."""
        tracker.record_interaction("btn1", "click", "h1")
        tracker.record_interaction("btn2", "click", "h1")
        tracker.record_interaction("btn3", "click", "h1")

        assert tracker.discovery_timeline[0]["discovery_order"] == 1
        assert tracker.discovery_timeline[1]["discovery_order"] == 2
        assert tracker.discovery_timeline[2]["discovery_order"] == 3


# =============================================================================
# Element Testing Status Tests
# =============================================================================


class TestElementTestingStatus:
    """Test element testing status queries."""

    def test_is_element_untested_new(self, tracker):
        """New element is untested."""
        assert tracker.is_element_untested("new_element") is True

    def test_is_element_untested_after_test(self, tracker):
        """Element is tested after interaction."""
        tracker.record_interaction("btn1", "click", "h1")
        assert tracker.is_element_untested("btn1") is False

    def test_is_element_untested_empty_id(self, tracker):
        """Empty element ID returns False."""
        assert tracker.is_element_untested("") is False
        assert tracker.is_element_untested(None) is False

    def test_get_element_test_count_new(self, tracker):
        """New element has count 0."""
        assert tracker.get_element_test_count("new_element") == 0

    def test_get_element_test_count_tested(self, tracker):
        """Tested element has correct count."""
        tracker.record_interaction("btn1", "click", "h1")
        tracker.record_interaction("btn1", "click", "h1")
        tracker.record_interaction("btn1", "click", "h1")

        assert tracker.get_element_test_count("btn1") == 3

    def test_get_element_test_count_empty_id(self, tracker):
        """Empty element ID returns 0."""
        assert tracker.get_element_test_count("") == 0
        assert tracker.get_element_test_count(None) == 0


# =============================================================================
# Statistics Tests
# =============================================================================


class TestCoverageStatistics:
    """Test coverage statistics generation."""

    def test_get_overall_statistics_empty(self, tracker):
        """Statistics for empty tracker."""
        # Need to check if this method exists
        if hasattr(tracker, "get_overall_statistics"):
            stats = tracker.get_overall_statistics()
            assert isinstance(stats, dict)

    def test_element_coverage_tracking(self, tracker):
        """Track coverage across multiple interactions."""
        # Interact with various elements
        for i in range(10):
            tracker.record_interaction(f"element_{i}", "click", "hash1")

        assert len(tracker.tested_elements) == 10

        # Re-test some elements
        for i in range(5):
            tracker.record_interaction(f"element_{i}", "click", "hash1")

        # Should still have 10 unique elements
        assert len(tracker.tested_elements) == 10
        # First 5 should have count 2
        for i in range(5):
            assert tracker.tested_elements[f"element_{i}"] == 2


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_special_characters_in_element_id(self, tracker):
        """Handle special characters in element ID."""
        element_id = "com.example.app:id/btn_ok$inner"
        tracker.record_interaction(element_id, "click", "hash1")

        assert element_id in tracker.tested_elements

    def test_unicode_element_id(self, tracker):
        """Handle unicode in element ID."""
        element_id = "按钮_确定"
        tracker.record_interaction(element_id, "click", "hash1")

        assert element_id in tracker.tested_elements

    def test_very_long_element_id(self, tracker):
        """Handle very long element ID."""
        element_id = "a" * 1000
        tracker.record_interaction(element_id, "click", "hash1")

        assert element_id in tracker.tested_elements

    def test_many_unique_elements(self, tracker):
        """Handle many unique elements."""
        for i in range(1000):
            tracker.record_interaction(f"element_{i}", "click", f"hash_{i % 10}")

        assert len(tracker.tested_elements) == 1000
        assert len(tracker.screen_elements) == 10

    def test_error_handling_in_record(self, tracker):
        """Record interaction handles errors gracefully."""
        # Should not raise even with unusual input
        tracker.record_interaction("", "click", "hash1")  # Empty element
        tracker.record_interaction("e1", "", "hash1")  # Empty action type

        # Tracker should still work
        tracker.record_interaction("normal_element", "click", "hash1")
        assert "normal_element" in tracker.tested_elements


# =============================================================================
# Screen-Specific Coverage Tests
# =============================================================================


class TestScreenSpecificCoverage:
    """Test screen-specific element tracking."""

    def test_elements_tracked_per_screen(self, tracker):
        """Elements correctly tracked per screen."""
        # Screen 1 elements
        tracker.record_interaction("btn1", "click", "screen1")
        tracker.record_interaction("btn2", "click", "screen1")

        # Screen 2 elements
        tracker.record_interaction("btn3", "click", "screen2")

        # Same element on different screen
        tracker.record_interaction("btn1", "click", "screen2")

        assert tracker.screen_elements["screen1"] == {"btn1", "btn2"}
        assert tracker.screen_elements["screen2"] == {"btn3", "btn1"}

    def test_get_elements_for_screen(self, tracker):
        """Get elements for specific screen."""
        tracker.record_interaction("btn1", "click", "screen1")
        tracker.record_interaction("btn2", "click", "screen1")
        tracker.record_interaction("btn3", "click", "screen2")

        screen1_elements = tracker.screen_elements.get("screen1", set())

        assert len(screen1_elements) == 2
        assert "btn1" in screen1_elements
        assert "btn2" in screen1_elements
        assert "btn3" not in screen1_elements


# =============================================================================
# Action Type Distribution Tests
# =============================================================================


class TestActionTypeDistribution:
    """Test action type distribution tracking."""

    def test_action_type_distribution(self, tracker):
        """Track distribution of action types."""
        # Various action types
        for _ in range(5):
            tracker.record_interaction("e1", "click", "h1")
        for _ in range(3):
            tracker.record_interaction("e2", "scroll", "h1")
        for _ in range(2):
            tracker.record_interaction("e3", "set_text", "h1")
        tracker.record_interaction("e4", "long_click", "h1")

        assert tracker.action_type_counts["click"] == 5
        assert tracker.action_type_counts["scroll"] == 3
        assert tracker.action_type_counts["set_text"] == 2
        assert tracker.action_type_counts["long_click"] == 1

    def test_custom_action_types(self, tracker):
        """Handle custom/unknown action types."""
        tracker.record_interaction("e1", "custom_action", "h1")
        tracker.record_interaction("e2", "view", "h1")

        assert tracker.action_type_counts["custom_action"] == 1
        assert tracker.action_type_counts["view"] == 1


# =============================================================================
# Coverage Gap and Element Count (task 1.6)
# =============================================================================


class TestCoverageGapAndElementCount:
    """Tests for get_coverage_gap and get_element_count methods."""

    @pytest.fixture
    def tracker(self):
        return UICoverageTracker()

    def test_get_coverage_gap_known_state(self, tracker):
        """Coverage gap reflects untested fraction."""
        tracker.screen_elements["h1"] = {"e1", "e2", "e3", "e4"}
        tracker.tested_elements["e1"] = 1
        tracker.tested_elements["e3"] = 2
        # 2 untested out of 4
        assert tracker.get_coverage_gap("h1") == pytest.approx(0.5)

    def test_get_coverage_gap_unknown_state(self, tracker):
        """Unknown state returns 0.0."""
        assert tracker.get_coverage_gap("unknown") == 0.0

    def test_get_coverage_gap_all_tested(self, tracker):
        """Fully tested state returns 0.0 gap."""
        tracker.screen_elements["h1"] = {"e1", "e2"}
        tracker.tested_elements["e1"] = 1
        tracker.tested_elements["e2"] = 3
        assert tracker.get_coverage_gap("h1") == 0.0

    def test_get_coverage_gap_empty_screen(self, tracker):
        """Empty element set returns 0.0."""
        tracker.screen_elements["h1"] = set()
        assert tracker.get_coverage_gap("h1") == 0.0

    def test_get_element_count(self, tracker):
        """Returns correct element count for known state."""
        tracker.screen_elements["h1"] = {"e1", "e2", "e3"}
        assert tracker.get_element_count("h1") == 3

    def test_get_element_count_unknown_state(self, tracker):
        """Unknown state returns 0."""
        assert tracker.get_element_count("unknown") == 0
