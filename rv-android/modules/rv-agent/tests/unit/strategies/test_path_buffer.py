"""
Tests for PathBuffer (gh26 Group 6, tasks 6.1-6.2).

Verifies buffered navigation for multi-step path execution:
- Backtrack path planning fills buffer with correct number of BACK actions
- Sequential action retrieval and buffer exhaustion
- Buffer invalidation clears all pending actions
- is_active property reflects buffer state
- Backtrack rejects paths exceeding MAX_BACKTRACK_HOPS
"""

from unittest.mock import MagicMock

from rv_android_core.domain.widget import WidgetEventType
from rv_agent.strategies.rvagent_strategy.path_buffer import (
    PathBuffer,
    MAX_BACKTRACK_HOPS,
    BACK_ACTION_ID,
)


def _make_path_buffer(
    find_nearest_result=None,
    transition_manager=None,
):
    """Create PathBuffer with mocked dependencies.

    Args:
        find_nearest_result: Return value for successor_tracker.find_nearest_unsaturated().
            Tuple of (state_hash, hop_count) or None.
        transition_manager: Optional mock TransitionManager. Defaults to None.
    """
    successor_tracker = MagicMock()
    successor_tracker.find_nearest_unsaturated.return_value = find_nearest_result

    ui_coverage_tracker = MagicMock()
    config = MagicMock()

    return PathBuffer(
        transition_manager=transition_manager,
        successor_tracker=successor_tracker,
        ui_coverage_tracker=ui_coverage_tracker,
        config=config,
    )


class TestPlanBacktrackPath:
    """Test backtrack path planning fills buffer with BACK actions."""

    def test_plan_backtrack_path_3_hops(self):
        """3 BACKs buffered when unsaturated found 3 hops away."""
        buf = _make_path_buffer(find_nearest_result=("target_state", 3))

        result = buf.plan_backtrack_path("current_state")

        assert result is True
        assert buf.remaining_steps == 3
        assert buf.is_active is True

        # All buffered actions should be BACK
        for _ in range(3):
            action = buf.get_next_action()
            assert action is not None
            assert action.event == WidgetEventType.BACK
            assert action.id == BACK_ACTION_ID
            assert action.text == "BACK"

    def test_plan_backtrack_no_unsaturated(self):
        """Returns False when no unsaturated ancestor found."""
        buf = _make_path_buffer(find_nearest_result=None)

        result = buf.plan_backtrack_path("current_state")

        assert result is False
        assert buf.is_active is False
        assert buf.remaining_steps == 0


class TestGetNextActionSequence:
    """Test sequential retrieval and buffer exhaustion."""

    def test_sequential_retrieval(self):
        """Actions retrieved in order, buffer empty after exhaustion."""
        buf = _make_path_buffer(find_nearest_result=("target", 3))
        buf.plan_backtrack_path("current")

        # Retrieve all 3 actions
        actions = []
        for _ in range(3):
            action = buf.get_next_action()
            assert action is not None
            actions.append(action)

        assert len(actions) == 3

        # Buffer should be empty now
        assert buf.get_next_action() is None
        assert buf.is_active is False
        assert buf.remaining_steps == 0

    def test_get_next_action_empty_buffer(self):
        """Returns None from empty buffer."""
        buf = _make_path_buffer()

        assert buf.get_next_action() is None


class TestInvalidateClearsBuffer:
    """Test that invalidate() clears all pending actions."""

    def test_invalidate_clears_buffer(self):
        """Invalidate clears all buffered actions."""
        buf = _make_path_buffer(find_nearest_result=("target", 5))
        buf.plan_backtrack_path("current")

        assert buf.remaining_steps == 5
        assert buf.is_active is True

        buf.invalidate()

        assert buf.remaining_steps == 0
        assert buf.is_active is False
        assert buf.get_next_action() is None

    def test_invalidate_empty_buffer_is_noop(self):
        """Invalidating an empty buffer does nothing."""
        buf = _make_path_buffer()

        buf.invalidate()  # Should not raise

        assert buf.remaining_steps == 0
        assert buf.is_active is False


class TestBufferPriorityOverUntested:
    """Test is_active returns True when buffer has items."""

    def test_is_active_true_when_buffer_has_items(self):
        """is_active returns True when buffer has pending actions."""
        buf = _make_path_buffer(find_nearest_result=("target", 2))
        buf.plan_backtrack_path("current")

        assert buf.is_active is True

    def test_is_active_false_when_buffer_empty(self):
        """is_active returns False when buffer is empty."""
        buf = _make_path_buffer()

        assert buf.is_active is False


class TestBacktrackExceedsMaxHops:
    """Test that backtrack rejects paths exceeding MAX_BACKTRACK_HOPS."""

    def test_12_hops_exceeds_max(self):
        """12 hops > MAX_BACKTRACK_HOPS=8, returns False."""
        buf = _make_path_buffer(find_nearest_result=("far_state", 12))

        result = buf.plan_backtrack_path("current_state")

        assert result is False
        assert buf.is_active is False
        assert buf.remaining_steps == 0

    def test_max_hops_boundary_accepted(self):
        """Exactly MAX_BACKTRACK_HOPS is accepted."""
        buf = _make_path_buffer(
            find_nearest_result=("boundary_state", MAX_BACKTRACK_HOPS)
        )

        result = buf.plan_backtrack_path("current_state")

        assert result is True
        assert buf.remaining_steps == MAX_BACKTRACK_HOPS

    def test_one_over_max_rejected(self):
        """MAX_BACKTRACK_HOPS + 1 is rejected."""
        buf = _make_path_buffer(
            find_nearest_result=("over_state", MAX_BACKTRACK_HOPS + 1)
        )

        result = buf.plan_backtrack_path("current_state")

        assert result is False
        assert buf.is_active is False


class TestPlanMopPath:
    """Test MOP path planning."""

    def test_plan_mop_path_no_transition_manager(self):
        """Returns False when no transition_manager."""
        buf = _make_path_buffer(transition_manager=None)

        result = buf.plan_mop_path("SomeActivity", {})

        assert result is False

    def test_plan_mop_path_no_method(self):
        """Returns False when plan_path_to_mop_activity not available."""
        tm = MagicMock(spec=[])  # Empty spec = no attributes
        buf = _make_path_buffer(transition_manager=tm)

        result = buf.plan_mop_path("SomeActivity", {})

        assert result is False

    def test_plan_mop_path_returns_actions(self):
        """Fills buffer when plan_path_to_mop_activity returns action dicts."""
        tm = MagicMock()
        tm.plan_path_to_mop_activity.return_value = [
            {"action_type": "BACK"},
            {"action_type": "BACK"},
        ]
        buf = _make_path_buffer(transition_manager=tm)

        result = buf.plan_mop_path("SomeActivity", {"some": "data"})

        assert result is True
        assert buf.remaining_steps == 2

    def test_plan_mop_path_empty_result(self):
        """Returns False when plan_path_to_mop_activity returns empty list."""
        tm = MagicMock()
        tm.plan_path_to_mop_activity.return_value = []
        buf = _make_path_buffer(transition_manager=tm)

        result = buf.plan_mop_path("SomeActivity", {})

        assert result is False

    def test_plan_mop_path_none_result(self):
        """Returns False when plan_path_to_mop_activity returns None."""
        tm = MagicMock()
        tm.plan_path_to_mop_activity.return_value = None
        buf = _make_path_buffer(transition_manager=tm)

        result = buf.plan_mop_path("SomeActivity", {})

        assert result is False


class TestPlanCoveragePath:
    """Coverage path tests moved to test_path_buffer_coverage.py."""

