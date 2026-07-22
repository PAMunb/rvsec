"""
Unit tests for saturation fixes (gh26 Group 16 tasks 16.1-16.3).

(a) get_saturation_rate() excludes system actions from numerator
(b) Single record_action call produces count=1 (no double recording)
(c) PathBuffer invalidation on failed action makes is_active return False
"""

from unittest.mock import MagicMock

import pytest
from rv_agent.domain.screen_node import ScreenNode
from rv_agent.strategies.rvagent_strategy.path_buffer import PathBuffer


class TestSystemActionExclusion:
    """(a) get_saturation_rate() excludes system actions from numerator."""

    def test_system_actions_excluded_from_saturation_numerator(self):
        """ScreenNode with 3 real + 2 system actions: saturation = real / total."""
        node = ScreenNode(screen_hash="test", activity="test")
        node.total_actions = 3

        # 3 real actions, each executed 2x (saturated)
        for i in range(3):
            sig = ((100 + i * 100, 500), "click")
            node.record_action(sig)
            node.record_action(sig)

        # 2 system actions (BACK, RESTART) — should be excluded
        back_sig = ((0, 0), "back")
        restart_sig = ((0, 0), "restart")
        node.record_action(back_sig)
        node.record_action(back_sig)
        node.record_action(restart_sig)
        node.record_action(restart_sig)

        rate = node.get_saturation_rate()
        # 3 real saturated / 3 total = 1.0 (system actions excluded)
        assert rate == 1.0

    def test_system_actions_do_not_inflate_saturation(self):
        """System actions don't count toward saturated_count."""
        node = ScreenNode(screen_hash="test", activity="test")
        node.total_actions = 2

        # 1 real action saturated
        real_sig = ((200, 400), "click")
        node.record_action(real_sig)
        node.record_action(real_sig)

        # 1 system action also executed 2x
        back_sig = ((0, 0), "back")
        node.record_action(back_sig)
        node.record_action(back_sig)

        rate = node.get_saturation_rate()
        # Only 1 real action saturated / 2 total = 0.5
        assert rate == pytest.approx(0.5)


class TestNoDoubleRecording:
    """(b) Single record_action call produces count=1."""

    def test_single_record_produces_count_1(self):
        """One call to record_action results in count=1."""
        node = ScreenNode(screen_hash="test", activity="test")
        sig = ((100, 200), "click")

        node.record_action(sig)

        assert node.get_action_execution_count(sig) == 1
        assert sig in node.executed_actions

    def test_two_records_produce_count_2(self):
        """Two calls to record_action results in count=2."""
        node = ScreenNode(screen_hash="test", activity="test")
        sig = ((100, 200), "click")

        node.record_action(sig)
        node.record_action(sig)

        assert node.get_action_execution_count(sig) == 2

    def test_different_actions_tracked_independently(self):
        """Different action signatures tracked separately."""
        node = ScreenNode(screen_hash="test", activity="test")
        sig_a = ((100, 200), "click")
        sig_b = ((300, 400), "set_text")

        node.record_action(sig_a)
        node.record_action(sig_a)
        node.record_action(sig_b)

        assert node.get_action_execution_count(sig_a) == 2
        assert node.get_action_execution_count(sig_b) == 1


class TestPathBufferInvalidation:
    """(c) PathBuffer invalidation on failed action makes is_active False."""

    def _make_buffer(self):
        """Create PathBuffer with mock dependencies."""
        return PathBuffer(
            transition_manager=None,
            successor_tracker=MagicMock(),
            ui_coverage_tracker=MagicMock(),
            config=MagicMock(),
        )

    def test_invalidate_clears_active_state(self):
        """After invalidate(), is_active returns False."""
        buffer = self._make_buffer()

        # Simulate an active buffer with planned actions
        buffer._buffer = [MagicMock(), MagicMock()]
        buffer._strategy_name = "test"
        assert buffer.is_active

        buffer.invalidate()

        assert not buffer.is_active
        assert len(buffer._buffer) == 0

    def test_invalidate_on_empty_buffer_is_safe(self):
        """Invalidating an empty buffer is a no-op."""
        buffer = self._make_buffer()

        assert not buffer.is_active

        buffer.invalidate()

        assert not buffer.is_active
