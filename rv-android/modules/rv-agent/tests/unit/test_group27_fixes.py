"""
Tests for Group 27 bug fixes (M5, M6, M7).

M5: SuccessorTracker.update_action_availability() invalidates coverage_cache
    after using a cached value, so the next call gets fresh data.
M6: execute_node._record_ui_interaction() uses get_execution_coordinates()
    instead of .coordinates, so bounds-resolved elements are tracked.
M7: parse_node._update_cached_bounds() updates cached screen_desc bounds
    when the keyboard shifts elements without changing the structural hash.
"""

import pytest
from unittest.mock import MagicMock

from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.domain.screen_node import ScreenNode
from rv_agent.strategies.rvagent_strategy.successor_tracker import SuccessorTracker
from rv_agent.agent.nodes.parse_node import _update_cached_bounds

# ---------------------------------------------------------------------------
# M5: coverage_cache invalidation in update_action_availability
# ---------------------------------------------------------------------------


class TestCoverageCacheInvalidation:
    """Verify that update_action_availability() invalidates stale cache entries."""

    def _make_tracker_with_successor(self):
        """Create a SuccessorTracker with one recorded successor mapping."""
        graph = DynamicStateGraph()

        # Create source state with one action
        source_node = ScreenNode(
            screen_hash="state_A",
            activity="TestActivity",
            total_actions=2,
        )
        action_sig = ((100, 200), "click")
        source_node.executed_actions.add(action_sig)
        graph.states["state_A"] = source_node

        # Create successor state with low coverage (1 of 3 actions executed)
        successor_node = ScreenNode(
            screen_hash="state_B",
            activity="TestActivity",
            total_actions=3,
        )
        successor_node.executed_actions.add(((50, 50), "click"))
        graph.states["state_B"] = successor_node

        tracker = SuccessorTracker(graph)
        tracker.record_successor("state_A", action_sig, "state_B")

        return tracker

    def test_cache_invalidated_after_update(self):
        """After update_action_availability, the cache entry for the successor is removed."""
        tracker = self._make_tracker_with_successor()

        # Pre-populate cache
        _ = tracker.get_successor_coverage("state_B")
        assert "state_B" in tracker.coverage_cache

        # Run update_action_availability (uses the cache, then invalidates)
        tracker.update_action_availability("state_A")

        # Cache entry should be gone
        assert "state_B" not in tracker.coverage_cache

    def test_next_lookup_gets_fresh_value(self):
        """After invalidation, the next get_successor_coverage() re-computes from graph."""
        tracker = self._make_tracker_with_successor()

        # First call populates cache
        cov1 = tracker.get_successor_coverage("state_B")
        assert cov1 == pytest.approx(1 / 3, abs=0.01)

        # Run update (invalidates cache)
        tracker.update_action_availability("state_A")

        # Modify the successor node to simulate new actions executed
        successor = tracker.graph.states["state_B"]
        successor.executed_actions.add(((60, 60), "click"))
        successor.executed_actions.add(((70, 70), "click"))

        # Next lookup should reflect updated coverage (3/3)
        cov2 = tracker.get_successor_coverage("state_B")
        assert cov2 == pytest.approx(1.0, abs=0.01)

    def test_cache_invalidated_even_when_not_re_enabled(self):
        """Cache is invalidated even when the action is not re-enabled (at max re-enables)."""
        tracker = self._make_tracker_with_successor()
        action_sig = ((100, 200), "click")
        key = ("state_A", action_sig)

        # Exhaust re-enable count
        tracker.re_enable_counts[key] = tracker.max_re_enables

        # Populate cache
        _ = tracker.get_successor_coverage("state_B")
        assert "state_B" in tracker.coverage_cache

        # Run update — action won't be re-enabled, but cache should still be invalidated
        re_enabled = tracker.update_action_availability("state_A")
        assert re_enabled == 0
        assert "state_B" not in tracker.coverage_cache


# ---------------------------------------------------------------------------
# M6: _record_ui_interaction uses get_execution_coordinates()
# ---------------------------------------------------------------------------


class TestRecordUiInteractionBoundsResolution:
    """Verify that _record_ui_interaction uses get_execution_coordinates()
    so elements resolved via bounds center are correctly tracked."""

    def test_bounds_resolved_element_tracked(self):
        """When item_action.coordinates is None but bounds provide a center,
        _record_ui_interaction should still track the interaction."""
        from rv_agent.agent.nodes.execute_node import _record_ui_interaction

        # Create a mock ItemAction where coordinates is None but bounds give a center
        item_action = MagicMock()
        item_action.coordinates = None
        item_action.get_execution_coordinates.return_value = (300, 500)
        item_action.target_view = {
            "class": "android.widget.Button",
            "bounds": [[200, 400], [400, 600]],
        }

        # Create mock agent with ui_coverage
        agent = MagicMock()
        agent.ui_coverage.find_nearest_element.return_value = (
            "elem_btn_300_500",
            "Button",
            5.0,
        )

        action = {"action_type": "CLICK", "x": 300, "y": 500, "source": "algorithm"}

        _record_ui_interaction(
            agent=agent,
            action=action,
            action_type="CLICK",
            screen_hash="hash_abc",
            item_action=item_action,
            source="algorithm",
        )

        # get_execution_coordinates() should have been called
        item_action.get_execution_coordinates.assert_called_once()

        # find_nearest_element should be called with the bounds-derived coords
        agent.ui_coverage.find_nearest_element.assert_called_once_with(
            300, 500, "hash_abc"
        )

        # record_interaction should be called
        agent.ui_coverage.record_interaction.assert_called_once()

    def test_explicit_coordinates_still_work(self):
        """When item_action.coordinates is set, they are used (via get_execution_coordinates)."""
        from rv_agent.agent.nodes.execute_node import _record_ui_interaction

        item_action = MagicMock()
        item_action.coordinates = (150, 250)
        item_action.get_execution_coordinates.return_value = (150, 250)
        item_action.target_view = {"class": "android.widget.EditText"}

        agent = MagicMock()
        agent.ui_coverage.find_nearest_element.return_value = (
            "elem_edit_150_250",
            "EditText",
            2.0,
        )

        action = {"action_type": "SET_TEXT", "x": 150, "y": 250, "source": "algorithm"}

        _record_ui_interaction(
            agent=agent,
            action=action,
            action_type="SET_TEXT",
            screen_hash="hash_xyz",
            item_action=item_action,
            source="algorithm",
        )

        item_action.get_execution_coordinates.assert_called_once()
        agent.ui_coverage.find_nearest_element.assert_called_once_with(
            150, 250, "hash_xyz"
        )


# ---------------------------------------------------------------------------
# M7: _update_cached_bounds updates element positions from fresh parse
# ---------------------------------------------------------------------------


class TestUpdateCachedBounds:
    """Verify that _update_cached_bounds syncs bounds from fresh parse into cached screen_desc."""

    def _make_screen_desc(self, bounds_map):
        """Create a mock ScreenDescription with items whose actions have given bounds.

        Args:
            bounds_map: dict of widget_id -> bounds (e.g. {"btn1": [[0, 100], [200, 300]]})
        """
        items = []
        for widget_id, bounds in bounds_map.items():
            action = MagicMock()
            action.widget_id = widget_id
            action.target_view = {"class": "android.widget.Button", "bounds": bounds}

            item = MagicMock()
            item.actions = [action]
            items.append(item)

        desc = MagicMock()
        desc.items = items
        return desc

    def test_bounds_updated_when_different(self):
        """Cached bounds are updated to match fresh parse when they differ."""
        cached = self._make_screen_desc(
            {
                "btn1": [[0, 100], [200, 300]],
                "btn2": [[0, 400], [200, 600]],
            }
        )
        fresh = self._make_screen_desc(
            {
                "btn1": [[0, 50], [200, 250]],  # shifted up by 50px
                "btn2": [[0, 350], [200, 550]],  # shifted up by 50px
            }
        )

        _update_cached_bounds(cached, fresh)

        # Both should be updated
        assert cached.items[0].actions[0].target_view["bounds"] == [[0, 50], [200, 250]]
        assert cached.items[1].actions[0].target_view["bounds"] == [
            [0, 350],
            [200, 550],
        ]

    def test_bounds_unchanged_when_same(self):
        """No updates when bounds are identical between cached and fresh."""
        cached = self._make_screen_desc(
            {
                "btn1": [[0, 100], [200, 300]],
            }
        )
        fresh = self._make_screen_desc(
            {
                "btn1": [[0, 100], [200, 300]],  # same bounds
            }
        )

        _update_cached_bounds(cached, fresh)

        assert cached.items[0].actions[0].target_view["bounds"] == [
            [0, 100],
            [200, 300],
        ]

    def test_no_crash_when_fresh_has_no_bounds(self):
        """If fresh parse has no bounds data, function returns gracefully."""
        cached = self._make_screen_desc(
            {
                "btn1": [[0, 100], [200, 300]],
            }
        )

        # Fresh with no widget_id or bounds
        fresh_action = MagicMock()
        fresh_action.widget_id = None
        fresh_action.target_view = {}
        fresh_item = MagicMock()
        fresh_item.actions = [fresh_action]
        fresh = MagicMock()
        fresh.items = [fresh_item]

        # Should not raise
        _update_cached_bounds(cached, fresh)

        # Cached bounds untouched
        assert cached.items[0].actions[0].target_view["bounds"] == [
            [0, 100],
            [200, 300],
        ]

    def test_partial_update_only_matching_widgets(self):
        """Only widgets present in both cached and fresh are updated."""
        cached = self._make_screen_desc(
            {
                "btn1": [[0, 100], [200, 300]],
                "btn2": [[0, 400], [200, 600]],
            }
        )
        # Fresh only has btn1 (btn2 missing)
        fresh = self._make_screen_desc(
            {
                "btn1": [[0, 50], [200, 250]],
            }
        )

        _update_cached_bounds(cached, fresh)

        # btn1 updated, btn2 unchanged
        assert cached.items[0].actions[0].target_view["bounds"] == [[0, 50], [200, 250]]
        assert cached.items[1].actions[0].target_view["bounds"] == [
            [0, 400],
            [200, 600],
        ]
