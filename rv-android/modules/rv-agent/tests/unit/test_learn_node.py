"""
Unit tests for learn_node.

Tests memory updates, stuck detection, and UI coverage integration.
"""

import pytest
from unittest.mock import MagicMock, patch

from rv_agent.agent.nodes.learn_node import (
    learn_node,
    _record_ui_coverage,
    _generate_element_id_from_action,
    _find_element_at_coords,
)


class TestGenerateElementIdFromAction:
    """Test _generate_element_id_from_action function."""

    def test_extract_id_from_description(self):
        """Extracts id: pattern from element description."""
        action = {
            "action_type": "CLICK",
            "element_description": "Button id:submit_button at position (100, 200)"
        }
        state = {}

        result = _generate_element_id_from_action(action, state)

        assert result == "id:submit_button"

    def test_extract_id_with_equals(self):
        """Extracts id= pattern from element description."""
        action = {
            "action_type": "CLICK",
            "element_description": "Button id=login_btn"
        }
        state = {}

        result = _generate_element_id_from_action(action, state)

        assert result == "id:login_btn"

    def test_extract_quoted_text(self):
        """Extracts quoted text from description."""
        action = {
            "action_type": "CLICK",
            "element_description": 'Button "Submit Form"'
        }
        state = {}

        result = _generate_element_id_from_action(action, state)

        assert result == 'text:"Submit Form"'

    def test_extract_parenthesized_id(self):
        """Extracts parenthesized text as id."""
        action = {
            "action_type": "CLICK",
            "element_description": "Button (submitBtn) at position (100, 200)"
        }
        state = {}

        result = _generate_element_id_from_action(action, state)

        assert result == "id:submitBtn"

    def test_fallback_to_coordinates(self):
        """Falls back to coordinates when no pattern matches."""
        action = {
            "action_type": "CLICK",
            "coordinates": {"x": 540, "y": 960}
        }
        state = {}

        result = _generate_element_id_from_action(action, state)

        assert result == "coords:540,960:CLICK"

    def test_empty_action(self):
        """Returns empty string for empty action."""
        action = {}
        state = {}

        result = _generate_element_id_from_action(action, state)

        assert result == ""

    def test_no_description_no_coords(self):
        """Returns empty string when no identifying info."""
        action = {"action_type": "BACK"}
        state = {}

        result = _generate_element_id_from_action(action, state)

        assert result == ""

    def test_priority_id_over_text(self):
        """ID pattern takes priority over quoted text."""
        action = {
            "action_type": "CLICK",
            "element_description": 'Button id:btn_submit "Submit"'
        }
        state = {}

        result = _generate_element_id_from_action(action, state)

        assert result == "id:btn_submit"


class TestRecordUiCoverage:
    """Test _record_ui_coverage function."""

    def test_records_interaction_with_ui_coverage(self):
        """Records interaction when ui_coverage is available."""
        # Setup mock agent with screen_description containing elements
        mock_ui_coverage = MagicMock()
        mock_screen_processor = MagicMock()
        mock_screen_processor.ui_coverage = mock_ui_coverage
        mock_screen_processor.device_dimensions = (1080, 1920)

        mock_agent = MagicMock()
        mock_agent.screen_processor = mock_screen_processor

        # Create mock screen description with element at (500, 500) in normalized space
        mock_item = MagicMock()
        mock_item.view = {"bounds": [[490, 910], [590, 1010]]}  # Center at (540, 960) -> (500, 500)

        mock_screen_desc = MagicMock()
        mock_screen_desc.items = [mock_item]

        state = {
            "current_action": {
                "action_type": "CLICK",
                "original_coords": [500, 500]  # Normalized coords matching the element
            },
            "current_screen_hash": "abc123",
            "screen_description": mock_screen_desc
        }

        _record_ui_coverage(mock_agent, state)

        # Should record interaction with coords-based element ID
        mock_ui_coverage.record_interaction.assert_called_once()
        call_kwargs = mock_ui_coverage.record_interaction.call_args.kwargs
        assert call_kwargs["action_type"] == "click"
        assert call_kwargs["screen_hash"] == "abc123"
        assert call_kwargs["success"] is True
        assert "coords:" in call_kwargs["element_id"]

    def test_skips_when_no_ui_coverage(self):
        """Skips recording when ui_coverage is None."""
        mock_screen_processor = MagicMock()
        mock_screen_processor.ui_coverage = None

        mock_agent = MagicMock()
        mock_agent.screen_processor = mock_screen_processor

        state = {
            "current_action": {"action_type": "CLICK"}
        }

        # Should not raise
        _record_ui_coverage(mock_agent, state)

    def test_skips_when_no_action(self):
        """Skips recording when no current_action."""
        mock_ui_coverage = MagicMock()
        mock_screen_processor = MagicMock()
        mock_screen_processor.ui_coverage = mock_ui_coverage

        mock_agent = MagicMock()
        mock_agent.screen_processor = mock_screen_processor

        state = {}

        _record_ui_coverage(mock_agent, state)

        mock_ui_coverage.record_interaction.assert_not_called()

    def test_skips_when_no_element_id(self):
        """Skips recording when cannot generate element_id."""
        mock_ui_coverage = MagicMock()
        mock_screen_processor = MagicMock()
        mock_screen_processor.ui_coverage = mock_ui_coverage

        mock_agent = MagicMock()
        mock_agent.screen_processor = mock_screen_processor

        state = {
            "current_action": {"action_type": "BACK"}  # No coords or description
        }

        _record_ui_coverage(mock_agent, state)

        mock_ui_coverage.record_interaction.assert_not_called()

    def test_handles_exception_gracefully(self):
        """Handles exceptions without crashing."""
        mock_ui_coverage = MagicMock()
        mock_ui_coverage.record_interaction.side_effect = Exception("Test error")

        mock_screen_processor = MagicMock()
        mock_screen_processor.ui_coverage = mock_ui_coverage

        mock_agent = MagicMock()
        mock_agent.screen_processor = mock_screen_processor

        state = {
            "current_action": {
                "action_type": "CLICK",
                "element_description": "Button id:test"
            },
            "current_screen_hash": "abc123"
        }

        # Should not raise
        _record_ui_coverage(mock_agent, state)

    def test_uses_fallback_coords_when_no_proximity_match(self):
        """Uses fallback coordinate-based ID when no proximity match found."""
        mock_ui_coverage = MagicMock()
        mock_screen_processor = MagicMock()
        mock_screen_processor.ui_coverage = mock_ui_coverage

        mock_agent = MagicMock()
        mock_agent.screen_processor = mock_screen_processor

        # Empty screen description (no elements to match)
        mock_screen_desc = MagicMock()
        mock_screen_desc.items = []

        state = {
            "current_action": {
                "action_type": "CLICK",
                "original_coords": [100, 200]  # Normalized coords
            },
            "current_screen_hash": "abc123",
            "screen_description": mock_screen_desc
        }

        _record_ui_coverage(mock_agent, state)

        mock_ui_coverage.record_interaction.assert_called_once()
        call_kwargs = mock_ui_coverage.record_interaction.call_args.kwargs
        # Falls back to coordinate-based ID since no proximity match
        assert call_kwargs["element_id"] == "coords:100,200:CLICK"


class TestLearnNodeIntegration:
    """Test learn_node function with UI coverage integration."""

    def test_learn_node_calls_record_ui_coverage(self):
        """learn_node calls _record_ui_coverage when original_coords available."""
        # Setup comprehensive mock agent
        mock_ui_coverage = MagicMock()
        mock_screen_processor = MagicMock()
        mock_screen_processor.ui_coverage = mock_ui_coverage
        mock_screen_processor.device_dimensions = (1080, 1920)

        mock_memory_coordinator = MagicMock()
        mock_memory_coordinator.update_memories.return_value = {
            "recent_action_window": []
        }
        mock_memory_coordinator.generate_summaries.return_value = {
            "action_history_summary": "",
            "exploration_summary": "",
            "memory_insights": "",
            "navigation_path": ""
        }
        mock_memory_coordinator.track_state_discovery.return_value = {
            "visited_states": [],
            "state_transitions": []
        }
        mock_memory_coordinator.check_continuation.return_value = {
            "should_continue": True
        }

        mock_agent = MagicMock()
        mock_agent.screen_processor = mock_screen_processor
        mock_agent.memory_coordinator = mock_memory_coordinator
        mock_agent.stuck_screen_count = 0
        mock_agent.last_screen_hash = "prev_hash"
        mock_agent.STUCK_THRESHOLD = 3
        mock_agent.metrics_collector = None

        # Create mock screen description with element
        mock_item = MagicMock()
        mock_item.view = {"bounds": [[490, 910], [590, 1010]]}
        mock_screen_desc = MagicMock()
        mock_screen_desc.items = [mock_item]

        state = {
            "current_screen_hash": "new_hash",
            "current_activity": ".MainActivity",
            "current_action": {
                "action_type": "CLICK",
                "original_coords": [500, 500]  # Normalized coords
            },
            "screen_description": mock_screen_desc,
            "iteration": 1
        }

        result = learn_node(mock_agent, state)

        # Verify ui_coverage.record_interaction was called
        mock_ui_coverage.record_interaction.assert_called_once()

    def test_learn_node_continues_on_ui_coverage_error(self):
        """learn_node continues even if ui_coverage fails."""
        mock_screen_processor = MagicMock()
        mock_screen_processor.ui_coverage = None  # No ui_coverage

        mock_memory_coordinator = MagicMock()
        mock_memory_coordinator.update_memories.return_value = {
            "recent_action_window": []
        }
        mock_memory_coordinator.generate_summaries.return_value = {
            "action_history_summary": "",
            "exploration_summary": "",
            "memory_insights": "",
            "navigation_path": ""
        }
        mock_memory_coordinator.track_state_discovery.return_value = {
            "visited_states": [],
            "state_transitions": []
        }
        mock_memory_coordinator.check_continuation.return_value = {
            "should_continue": True
        }

        mock_agent = MagicMock()
        mock_agent.screen_processor = mock_screen_processor
        mock_agent.memory_coordinator = mock_memory_coordinator
        mock_agent.stuck_screen_count = 0
        mock_agent.last_screen_hash = "prev_hash"
        mock_agent.STUCK_THRESHOLD = 3
        mock_agent.metrics_collector = None

        state = {
            "current_screen_hash": "new_hash",
            "current_activity": ".MainActivity",
            "current_action": {"action_type": "CLICK"},
            "iteration": 1
        }

        # Should not raise
        result = learn_node(mock_agent, state)

        assert "should_continue" in result


class TestLearnNodeStuckDetection:
    """Test stuck state detection in learn_node."""

    def test_increments_stuck_count_on_same_hash(self):
        """Increments stuck count when screen unchanged."""
        mock_screen_processor = MagicMock()
        mock_screen_processor.ui_coverage = None

        mock_memory_coordinator = MagicMock()
        mock_memory_coordinator.update_memories.return_value = {"recent_action_window": []}
        mock_memory_coordinator.generate_summaries.return_value = {
            "action_history_summary": "", "exploration_summary": "",
            "memory_insights": "", "navigation_path": ""
        }
        mock_memory_coordinator.track_state_discovery.return_value = {
            "visited_states": [], "state_transitions": []
        }
        mock_memory_coordinator.check_continuation.return_value = {"should_continue": True}

        mock_agent = MagicMock()
        mock_agent.screen_processor = mock_screen_processor
        mock_agent.memory_coordinator = mock_memory_coordinator
        mock_agent.stuck_screen_count = 0
        mock_agent.last_screen_hash = "same_hash"
        mock_agent.STUCK_THRESHOLD = 3
        mock_agent.metrics_collector = None

        state = {"current_screen_hash": "same_hash", "iteration": 1}

        learn_node(mock_agent, state)

        assert mock_agent.stuck_screen_count == 1

    def test_resets_stuck_count_on_new_hash(self):
        """Resets stuck count when screen changes."""
        mock_screen_processor = MagicMock()
        mock_screen_processor.ui_coverage = None

        mock_memory_coordinator = MagicMock()
        mock_memory_coordinator.update_memories.return_value = {"recent_action_window": []}
        mock_memory_coordinator.generate_summaries.return_value = {
            "action_history_summary": "", "exploration_summary": "",
            "memory_insights": "", "navigation_path": ""
        }
        mock_memory_coordinator.track_state_discovery.return_value = {
            "visited_states": [], "state_transitions": []
        }
        mock_memory_coordinator.check_continuation.return_value = {"should_continue": True}

        mock_agent = MagicMock()
        mock_agent.screen_processor = mock_screen_processor
        mock_agent.memory_coordinator = mock_memory_coordinator
        mock_agent.stuck_screen_count = 2
        mock_agent.last_screen_hash = "old_hash"
        mock_agent.STUCK_THRESHOLD = 3
        mock_agent.metrics_collector = None

        state = {"current_screen_hash": "new_hash", "iteration": 1}

        learn_node(mock_agent, state)

        assert mock_agent.stuck_screen_count == 0

    def test_forces_back_on_stuck_threshold(self):
        """Forces BACK action when stuck threshold reached."""
        mock_screen_processor = MagicMock()
        mock_screen_processor.ui_coverage = None

        mock_memory_coordinator = MagicMock()
        mock_memory_coordinator.update_memories.return_value = {"recent_action_window": []}
        mock_memory_coordinator.generate_summaries.return_value = {
            "action_history_summary": "", "exploration_summary": "",
            "memory_insights": "", "navigation_path": ""
        }
        mock_memory_coordinator.track_state_discovery.return_value = {
            "visited_states": [], "state_transitions": []
        }
        mock_memory_coordinator.check_continuation.return_value = {"should_continue": True}

        mock_agent = MagicMock()
        mock_agent.screen_processor = mock_screen_processor
        mock_agent.memory_coordinator = mock_memory_coordinator
        mock_agent.stuck_screen_count = 2  # One below threshold
        mock_agent.last_screen_hash = "stuck_hash"
        mock_agent.STUCK_THRESHOLD = 3
        mock_agent.metrics_collector = None

        state = {"current_screen_hash": "stuck_hash", "iteration": 1}

        result = learn_node(mock_agent, state)

        assert result.get("force_back_action") is True
        assert mock_agent.stuck_screen_count == 0  # Reset after forcing back


class TestFindElementAtCoords:
    """Test _find_element_at_coords proximity matching function."""

    def _create_mock_screen_desc(self, items_data):
        """Create mock screen description with items."""
        mock_screen = MagicMock()
        mock_items = []
        for bounds in items_data:
            mock_item = MagicMock()
            mock_item.view = {"bounds": bounds}
            mock_items.append(mock_item)
        mock_screen.items = mock_items
        return mock_screen

    def test_finds_exact_match(self):
        """Finds element when click is exactly at element center."""
        # Element at device coords (540, 960) -> normalized (500, 500)
        screen_desc = self._create_mock_screen_desc([
            [[490, 910], [590, 1010]]  # Center at (540, 960)
        ])

        result = _find_element_at_coords(screen_desc, 500, 500, device_dimensions=(1080, 1920))

        assert result == "coords:500,500:CLICK"

    def test_finds_closest_element(self):
        """Finds closest element when click is not exactly at center."""
        # Element 1 at (540, 960) -> normalized (500, 500)
        # Element 2 at (270, 480) -> normalized (250, 250)
        screen_desc = self._create_mock_screen_desc([
            [[490, 910], [590, 1010]],  # Center at (540, 960) -> (500, 500)
            [[220, 430], [320, 530]]    # Center at (270, 480) -> (250, 250)
        ])

        # Click at (520, 510) - closer to element 1 (500, 500)
        result = _find_element_at_coords(screen_desc, 520, 510, device_dimensions=(1080, 1920))

        assert result == "coords:500,500:CLICK"

    def test_returns_none_when_beyond_threshold(self):
        """Returns None when click is too far from any element."""
        # Element at normalized (100, 100)
        screen_desc = self._create_mock_screen_desc([
            [[58, 144], [158, 240]]  # Center at (108, 192) -> ~(100, 100)
        ])

        # Click at (800, 800) - very far from element
        result = _find_element_at_coords(screen_desc, 800, 800, device_dimensions=(1080, 1920))

        assert result is None

    def test_returns_none_for_empty_screen(self):
        """Returns None for screen with no items."""
        mock_screen = MagicMock()
        mock_screen.items = []

        result = _find_element_at_coords(mock_screen, 500, 500)

        assert result is None

    def test_returns_none_for_none_screen(self):
        """Returns None when screen_desc is None."""
        result = _find_element_at_coords(None, 500, 500)

        assert result is None

    def test_skips_elements_with_invalid_bounds(self):
        """Skips elements with invalid bounds format."""
        mock_screen = MagicMock()

        # Mix of valid and invalid bounds
        valid_item = MagicMock()
        valid_item.view = {"bounds": [[490, 910], [590, 1010]]}

        invalid_item1 = MagicMock()
        invalid_item1.view = {"bounds": None}

        invalid_item2 = MagicMock()
        invalid_item2.view = {"bounds": [[100]]}  # Incomplete bounds

        invalid_item3 = MagicMock()
        invalid_item3.view = {}  # No bounds at all

        mock_screen.items = [invalid_item1, invalid_item2, valid_item, invalid_item3]

        result = _find_element_at_coords(mock_screen, 500, 500, device_dimensions=(1080, 1920))

        # Should find the valid element
        assert result == "coords:500,500:CLICK"

    def test_proximity_threshold(self):
        """Tests that proximity threshold of 150 units is respected."""
        # Element at (500, 500) in normalized space
        screen_desc = self._create_mock_screen_desc([
            [[490, 910], [590, 1010]]  # Center at (540, 960) -> (500, 500)
        ])

        # Click at (640, 500) - distance = 140, within threshold of 150
        result1 = _find_element_at_coords(screen_desc, 640, 500, device_dimensions=(1080, 1920))
        assert result1 is not None

        # Click at (660, 500) - distance = 160, beyond threshold of 150
        result2 = _find_element_at_coords(screen_desc, 660, 500, device_dimensions=(1080, 1920))
        assert result2 is None

    def test_selects_closest_among_multiple_nearby(self):
        """When multiple elements are within threshold, selects closest."""
        # Element 1 at (300, 300)
        # Element 2 at (350, 350)
        # Element 3 at (400, 400)
        screen_desc = self._create_mock_screen_desc([
            [[270, 526], [378, 634]],   # Center at (324, 580) -> (300, 302)
            [[324, 595], [432, 703]],   # Center at (378, 649) -> (350, 338)
            [[378, 672], [486, 780]]    # Center at (432, 726) -> (400, 378)
        ])

        # Click at (355, 340) - closest to element 2 (350, 338)
        result = _find_element_at_coords(screen_desc, 355, 340, device_dimensions=(1080, 1920))

        assert result == "coords:350,338:CLICK"


class TestUICoverageFullScreen:
    """Test that UI coverage tracks ALL elements on a screen."""

    def _create_mock_agent_with_coverage(self):
        """Create mock agent with real UICoverageTracker."""
        from rv_agent.memory.ui_coverage import UICoverageTracker

        ui_coverage = UICoverageTracker()
        mock_screen_processor = MagicMock()
        mock_screen_processor.ui_coverage = ui_coverage

        mock_agent = MagicMock()
        mock_agent.screen_processor = mock_screen_processor

        return mock_agent, ui_coverage

    def _create_screen_with_elements(self, element_bounds_list):
        """Create mock screen description with multiple elements."""
        mock_screen = MagicMock()
        mock_items = []
        for bounds in element_bounds_list:
            mock_item = MagicMock()
            mock_item.view = {"bounds": bounds}
            mock_items.append(mock_item)
        mock_screen.items = mock_items
        return mock_screen

    def test_track_all_screen_elements_after_multiple_interactions(self):
        """Test that interacting with all elements marks them all as tested."""
        mock_agent, ui_coverage = self._create_mock_agent_with_coverage()

        # Create screen with 4 elements at different positions
        element_bounds = [
            [[0, 0], [216, 384]],      # Center: (108, 192) -> normalized: (100, 100)
            [[432, 0], [648, 384]],    # Center: (540, 192) -> normalized: (500, 100)
            [[0, 768], [216, 1152]],   # Center: (108, 960) -> normalized: (100, 500)
            [[432, 768], [648, 1152]]  # Center: (540, 960) -> normalized: (500, 500)
        ]
        mock_screen = self._create_screen_with_elements(element_bounds)

        screen_hash = "test_full_screen"

        # First, annotate the screen to track elements
        ui_description = """=== CLICKABLE ELEMENTS ===
1. Button 'A' at position (100, 100)
2. Button 'B' at position (500, 100)
3. Button 'C' at position (100, 500)
4. Button 'D' at position (500, 500)"""

        annotated = ui_coverage.annotate_screen_elements(ui_description, screen_hash)

        # Verify initial state: all untested
        stats = ui_coverage.get_screen_coverage_stats(screen_hash)
        assert stats.total_elements == 4
        assert stats.untested_elements == 4
        assert stats.tested_elements == 0

        # Simulate clicking on each element (using normalized coords)
        click_positions = [(100, 100), (500, 100), (100, 500), (500, 500)]

        for click_x, click_y in click_positions:
            # Find closest element and record interaction
            element_id = _find_element_at_coords(mock_screen, click_x, click_y)
            if element_id:
                ui_coverage.record_interaction(element_id, "click", screen_hash)

        # Verify final state: all tested
        stats = ui_coverage.get_screen_coverage_stats(screen_hash)
        assert stats.tested_elements == 4, f"Expected 4 tested, got {stats.tested_elements}"
        assert stats.untested_elements == 0, f"Expected 0 untested, got {stats.untested_elements}"
        assert stats.coverage_percentage == 100.0

    def test_partial_screen_coverage(self):
        """Test tracking when only some elements are interacted with."""
        mock_agent, ui_coverage = self._create_mock_agent_with_coverage()

        # Create screen with 4 elements
        element_bounds = [
            [[0, 0], [216, 384]],      # (100, 100)
            [[432, 0], [648, 384]],    # (500, 100)
            [[0, 768], [216, 1152]],   # (100, 500)
            [[432, 768], [648, 1152]]  # (500, 500)
        ]
        mock_screen = self._create_screen_with_elements(element_bounds)

        screen_hash = "partial_screen"

        # Annotate screen
        ui_description = """1. Button 'A' at position (100, 100)
2. Button 'B' at position (500, 100)
3. Button 'C' at position (100, 500)
4. Button 'D' at position (500, 500)"""

        ui_coverage.annotate_screen_elements(ui_description, screen_hash)

        # Only interact with 2 out of 4 elements
        for click_x, click_y in [(100, 100), (500, 500)]:
            element_id = _find_element_at_coords(mock_screen, click_x, click_y)
            if element_id:
                ui_coverage.record_interaction(element_id, "click", screen_hash)

        # Verify partial coverage
        stats = ui_coverage.get_screen_coverage_stats(screen_hash)
        assert stats.tested_elements == 2
        assert stats.untested_elements == 2
        assert stats.coverage_percentage == 50.0

    def test_repeated_interactions_same_element(self):
        """Test that repeated interactions increment count but not element count."""
        mock_agent, ui_coverage = self._create_mock_agent_with_coverage()

        element_bounds = [[[0, 0], [216, 384]]]  # Single element at (100, 100)
        mock_screen = self._create_screen_with_elements(element_bounds)

        screen_hash = "single_element"
        ui_description = "1. Button at position (100, 100)"

        ui_coverage.annotate_screen_elements(ui_description, screen_hash)

        # Click same element 5 times
        element_id = _find_element_at_coords(mock_screen, 100, 100)
        for _ in range(5):
            ui_coverage.record_interaction(element_id, "click", screen_hash)

        # Verify: 1 tested element, but count is 5
        stats = ui_coverage.get_screen_coverage_stats(screen_hash)
        assert stats.tested_elements == 1
        test_count = ui_coverage.get_element_test_count(element_id)
        assert test_count == 5, f"Expected 5 interactions, got {test_count}"
