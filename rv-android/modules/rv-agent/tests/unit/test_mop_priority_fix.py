"""
Tests for Group 32 fixes (MOP priority + input variation).

Covers three related changes:
(a) directly_reaches_mop gets higher priority (+50) than reaches_mop (+25)
    in TransitionManager._calculate_target_priority()
(b) has_remaining_values() uses mop_max_variations (default 11) when is_mop=True
    instead of max_variations (default 5), so MOP fields get more test cycles
(c) has_remaining_values() emits RVTRACK:INPUT_VAR via track.input_variation()
"""

import logging
from unittest.mock import MagicMock, patch

from rv_agent.strategies.rvagent_strategy.input_value_generator import (
    InputValueGenerator,
)
from rv_agent.services.transition_manager import TransitionManager


# ---------------------------------------------------------------------------
# (a) Priority scoring: directly_reaches_mop > reaches_mop
# ---------------------------------------------------------------------------


class TestMopPriorityScoring:
    """Verify directly_reaches_mop (+50) outranks reaches_mop (+25)."""

    def _make_manager_with_widget(self, directly: bool, indirect: bool) -> TransitionManager:
        """Build a TransitionManager wired so the target widget has the given MOP flags."""
        # Minimal method mock with the two MOP flags
        method = MagicMock()
        method.directly_reaches_mop = directly
        method.reaches_mop = indirect

        # Event whose signature resolves to the method above
        event = MagicMock()
        event.signature = "com.example.Foo.bar()V"

        # Widget with that event
        widget = MagicMock()
        widget.events = [event]

        # Static data wired together
        static_data = MagicMock()
        static_data.windows.widgets = {"w1": widget}
        static_data.classes.methods = {event.signature: method}

        dynamic_graph = MagicMock()
        manager = TransitionManager(static_data, dynamic_graph)
        return manager

    def test_directly_reaches_mop_adds_50(self):
        """directly_reaches_mop flag contributes +50 to target priority."""
        manager = self._make_manager_with_widget(directly=True, indirect=False)
        priority = manager._calculate_target_priority(
            target_id="w99", visited=True, widget_id="w1"
        )
        # visited=True → no +100; directly_reaches_mop → +50
        assert priority == 50

    def test_reaches_mop_adds_25(self):
        """reaches_mop flag (indirect) contributes +25 to target priority."""
        manager = self._make_manager_with_widget(directly=False, indirect=True)
        priority = manager._calculate_target_priority(
            target_id="w99", visited=True, widget_id="w1"
        )
        # visited=True → no +100; reaches_mop only → +25
        assert priority == 25

    def test_directly_reaches_mop_outranks_reaches_mop(self):
        """directly_reaches_mop priority is strictly higher than reaches_mop priority."""
        manager_direct = self._make_manager_with_widget(directly=True, indirect=False)
        manager_indirect = self._make_manager_with_widget(directly=False, indirect=True)

        p_direct = manager_direct._calculate_target_priority(
            target_id="w99", visited=True, widget_id="w1"
        )
        p_indirect = manager_indirect._calculate_target_priority(
            target_id="w99", visited=True, widget_id="w1"
        )
        assert p_direct > p_indirect

    def test_unvisited_bonus_stacks_with_mop_priority(self):
        """Unvisited (+100) and directly_reaches_mop (+50) both contribute."""
        manager = self._make_manager_with_widget(directly=True, indirect=False)
        priority = manager._calculate_target_priority(
            target_id="w99", visited=False, widget_id="w1"
        )
        # unvisited +100 + directly_reaches_mop +50 = 150
        assert priority == 150

    def test_no_widget_gives_only_visited_bonus(self):
        """Without a widget_id, priority comes only from the visited flag."""
        dynamic_graph = MagicMock()
        manager = TransitionManager(None, dynamic_graph)
        priority_unvisited = manager._calculate_target_priority(
            target_id="w99", visited=False, widget_id=None
        )
        priority_visited = manager._calculate_target_priority(
            target_id="w99", visited=True, widget_id=None
        )
        assert priority_unvisited == 100
        assert priority_visited == 0


# ---------------------------------------------------------------------------
# (b) has_remaining_values: mop_max_variations vs max_variations
# ---------------------------------------------------------------------------


class TestHasRemainingValuesLimit:
    """Verify has_remaining_values uses the correct limit per is_mop flag."""

    def test_regular_field_exhausted_at_max_variations(self):
        """A non-MOP field with 5 uses (= default max_variations=5) has no remaining values."""
        gen = InputValueGenerator(max_variations=5, mop_max_variations=11)
        eid = "coords:100,200"
        # Simulate 5 tested values
        gen.tested_values[eid] = ["v1", "v2", "v3", "v4", "v5"]

        assert gen.has_remaining_values(eid, is_mop=False) is False

    def test_regular_field_still_has_values_below_max(self):
        """A non-MOP field with 4 uses (below max_variations=5) still has remaining values."""
        gen = InputValueGenerator(max_variations=5, mop_max_variations=11)
        eid = "coords:100,200"
        gen.tested_values[eid] = ["v1", "v2", "v3", "v4"]

        assert gen.has_remaining_values(eid, is_mop=False) is True

    def test_mop_field_still_has_values_after_5_tests(self):
        """A MOP field with 5 uses is NOT exhausted because mop_max_variations=11."""
        gen = InputValueGenerator(max_variations=5, mop_max_variations=11)
        eid = "coords:300,400"
        # 5 tested — below mop limit
        gen.tested_values[eid] = [f"v{i}" for i in range(5)]

        assert gen.has_remaining_values(eid, is_mop=True) is True

    def test_mop_field_exhausted_at_mop_max_variations(self):
        """A MOP field with 11 uses (= mop_max_variations) has no remaining values."""
        gen = InputValueGenerator(max_variations=5, mop_max_variations=11)
        eid = "coords:300,400"
        gen.tested_values[eid] = [f"v{i}" for i in range(11)]

        assert gen.has_remaining_values(eid, is_mop=True) is False

    def test_mop_still_active_at_10(self):
        """A MOP field with 10 uses still has one remaining slot (limit=11)."""
        gen = InputValueGenerator(max_variations=5, mop_max_variations=11)
        eid = "coords:300,400"
        gen.tested_values[eid] = [f"v{i}" for i in range(10)]

        assert gen.has_remaining_values(eid, is_mop=True) is True

    def test_fresh_field_has_remaining_for_both_modes(self):
        """A field with zero tested values has remaining values regardless of is_mop."""
        gen = InputValueGenerator(max_variations=5, mop_max_variations=11)
        eid = "coords:500,600"

        assert gen.has_remaining_values(eid, is_mop=False) is True
        assert gen.has_remaining_values(eid, is_mop=True) is True

    def test_mop_limit_independent_of_max_variations(self):
        """mop_max_variations is used independently of max_variations."""
        gen = InputValueGenerator(max_variations=3, mop_max_variations=7)
        eid = "coords:10,20"
        gen.tested_values[eid] = [f"v{i}" for i in range(3)]

        # 3 uses: regular field exhausted, MOP field not
        assert gen.has_remaining_values(eid, is_mop=False) is False
        assert gen.has_remaining_values(eid, is_mop=True) is True

        gen.tested_values[eid] = [f"v{i}" for i in range(7)]

        # 7 uses: both exhausted
        assert gen.has_remaining_values(eid, is_mop=False) is False
        assert gen.has_remaining_values(eid, is_mop=True) is False


# ---------------------------------------------------------------------------
# (c) RVTRACK:INPUT_VAR emission
# ---------------------------------------------------------------------------


class TestInputVarTracking:
    """Verify has_remaining_values emits RVTRACK:INPUT_VAR when is_mop=True."""

    def test_rvtrack_input_var_emitted_for_mop_field(self, caplog):
        """has_remaining_values with is_mop=True logs an RVTRACK:INPUT_VAR line."""
        gen = InputValueGenerator(max_variations=5, mop_max_variations=11)
        eid = "coords:100,200"
        gen.tested_values[eid] = ["v1", "v2"]

        with caplog.at_level(logging.INFO, logger="rv_agent.tracking"):
            gen.has_remaining_values(eid, is_mop=True)

        assert any("RVTRACK:INPUT_VAR" in r.message for r in caplog.records)

    def test_rvtrack_input_var_not_emitted_for_regular_field(self, caplog):
        """has_remaining_values with is_mop=False does NOT log RVTRACK:INPUT_VAR."""
        gen = InputValueGenerator(max_variations=5, mop_max_variations=11)
        eid = "coords:100,200"
        gen.tested_values[eid] = ["v1", "v2"]

        with caplog.at_level(logging.INFO, logger="rv_agent.tracking"):
            gen.has_remaining_values(eid, is_mop=False)

        assert not any("RVTRACK:INPUT_VAR" in r.message for r in caplog.records)

    def test_rvtrack_input_var_contains_field_id(self, caplog):
        """RVTRACK:INPUT_VAR log includes the field_id."""
        gen = InputValueGenerator(max_variations=5, mop_max_variations=11)
        eid = "coords:777,888"
        gen.tested_values[eid] = []

        with caplog.at_level(logging.INFO, logger="rv_agent.tracking"):
            gen.has_remaining_values(eid, is_mop=True)

        matching = [r.message for r in caplog.records if "RVTRACK:INPUT_VAR" in r.message]
        assert matching, "Expected at least one RVTRACK:INPUT_VAR log line"
        assert eid in matching[0]

    def test_rvtrack_input_var_contains_used_and_limit(self, caplog):
        """RVTRACK:INPUT_VAR log includes used count and limit."""
        gen = InputValueGenerator(max_variations=5, mop_max_variations=11)
        eid = "coords:50,60"
        gen.tested_values[eid] = ["a", "b", "c"]  # 3 used

        with caplog.at_level(logging.INFO, logger="rv_agent.tracking"):
            gen.has_remaining_values(eid, is_mop=True)

        matching = [r.message for r in caplog.records if "RVTRACK:INPUT_VAR" in r.message]
        assert matching
        log_line = matching[0]
        # used=3 and limit=11 should appear in the log
        assert "used=3" in log_line
        assert "limit=11" in log_line

    def test_rvtrack_input_var_emitted_even_when_exhausted(self, caplog):
        """RVTRACK:INPUT_VAR is emitted even when the MOP field is exhausted."""
        gen = InputValueGenerator(max_variations=5, mop_max_variations=11)
        eid = "coords:100,200"
        gen.tested_values[eid] = [f"v{i}" for i in range(11)]  # fully exhausted

        with caplog.at_level(logging.INFO, logger="rv_agent.tracking"):
            result = gen.has_remaining_values(eid, is_mop=True)

        assert result is False
        assert any("RVTRACK:INPUT_VAR" in r.message for r in caplog.records)

    def test_input_variation_function_directly(self, caplog):
        """track.input_variation() emits RVTRACK:INPUT_VAR independently."""
        from rv_agent import tracking as track

        with caplog.at_level(logging.INFO, logger="rv_agent.tracking"):
            track.input_variation(
                iter=0,
                field_id="coords:10,20",
                is_mop=True,
                used=5,
                limit=11,
            )

        matching = [r.message for r in caplog.records if "RVTRACK:INPUT_VAR" in r.message]
        assert matching
        log_line = matching[0]
        assert "is_mop=True" in log_line
        assert "used=5" in log_line
        assert "limit=11" in log_line
