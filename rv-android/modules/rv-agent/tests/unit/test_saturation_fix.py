"""
Tests for saturation calculation fix (gh26 Group 1.7).

Verifies that system actions (BACK, RESTART) with coordinates=None are
excluded from total_actions count in DynamicStateGraph.get_or_create_state().
Without this fix, max saturation = N/(N+2), preventing screens with fewer
than 8 real actions from reaching the 80% backtrack threshold.
"""

import pytest
from unittest.mock import MagicMock
from dataclasses import dataclass, field
from typing import Optional, Tuple

from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.domain.screen_node import ScreenNode


@dataclass
class MockAction:
    """Mock action for testing."""

    coordinates: Optional[Tuple[int, int]] = (540, 960)
    event: object = None

    @property
    def coords_for_matching(self):
        if self.coordinates:
            return (self.coordinates, "click")
        return ((0, 0), "key_event")


def _make_screen_desc(real_actions_count: int, system_actions_count: int = 2):
    """Create a mock ScreenDescription with real + system actions.

    Args:
        real_actions_count: Number of regular actions with coordinates
        system_actions_count: Number of system actions with coordinates=None (default 2: BACK + RESTART)
    """
    actions = []
    for i in range(real_actions_count):
        actions.append(MockAction(coordinates=(100 + i * 50, 500)))
    for _ in range(system_actions_count):
        actions.append(MockAction(coordinates=None))

    screen_desc = MagicMock()
    screen_desc.activity = "com.example.TestActivity"
    screen_desc.get_all_actions.return_value = actions
    screen_desc.items = []
    return screen_desc


class TestTotalActionsExcludesSystemActions:
    """Verify total_actions only counts actions with coordinates (non-system)."""

    def test_total_actions_excludes_system_actions(self):
        """Screen with 5 real actions + 2 system actions should have total_actions == 5."""
        graph = DynamicStateGraph()
        screen_desc = _make_screen_desc(real_actions_count=5, system_actions_count=2)

        node = graph.get_or_create_state("hash_a", "TestActivity", screen_desc)

        assert node.total_actions == 5

    def test_back_restart_excluded_from_total_actions(self):
        """BACK and RESTART injected by visitor with coords=None do not inflate total_actions."""
        graph = DynamicStateGraph()
        screen_desc = _make_screen_desc(real_actions_count=3, system_actions_count=2)

        node = graph.get_or_create_state("hash_b", "TestActivity", screen_desc)

        # Should be 3, not 5
        assert node.total_actions == 3

    def test_total_actions_zero_only_system_actions(self):
        """Screen with only system actions has total_actions == 0."""
        graph = DynamicStateGraph()
        screen_desc = _make_screen_desc(real_actions_count=0, system_actions_count=2)

        node = graph.get_or_create_state("hash_c", "TestActivity", screen_desc)

        assert node.total_actions == 0

    def test_total_actions_no_system_actions(self):
        """Screen with no system actions counts all actions."""
        graph = DynamicStateGraph()
        screen_desc = _make_screen_desc(real_actions_count=7, system_actions_count=0)

        node = graph.get_or_create_state("hash_d", "TestActivity", screen_desc)

        assert node.total_actions == 7


class TestSaturationReaches100:
    """Verify saturation can reach 1.0 on small screens."""

    def test_saturation_reaches_1_0_all_non_system_saturated(self):
        """When all non-system actions are executed twice, saturation is 1.0."""
        graph = DynamicStateGraph()
        screen_desc = _make_screen_desc(real_actions_count=3, system_actions_count=2)

        node = graph.get_or_create_state("hash_e", "TestActivity", screen_desc)

        # Execute each real action twice
        for i in range(3):
            sig = ((100 + i * 50, 500), "click")
            node.record_action(sig)
            node.record_action(sig)

        assert node.get_saturation_rate(threshold=2) == 1.0

    def test_small_screen_can_exceed_80_percent_threshold(self):
        """Screen with 4 real actions + 2 system can reach 80% saturation.

        Without fix: max saturation = 4/(4+2) = 66.7% — never reaches 80%.
        With fix: max saturation = 4/4 = 100% — easily reaches 80%.
        """
        graph = DynamicStateGraph()
        screen_desc = _make_screen_desc(real_actions_count=4, system_actions_count=2)

        node = graph.get_or_create_state("hash_f", "TestActivity", screen_desc)

        # Execute 4 actions, each twice
        for i in range(4):
            sig = ((100 + i * 50, 500), "click")
            node.record_action(sig)
            node.record_action(sig)

        saturation = node.get_saturation_rate(threshold=2)
        assert saturation >= 0.8, f"Saturation {saturation} should be >= 0.8"
        assert saturation == 1.0

    def test_partial_saturation_calculation_correct(self):
        """With 5 real actions, 3 saturated → saturation = 3/5 = 0.6."""
        graph = DynamicStateGraph()
        screen_desc = _make_screen_desc(real_actions_count=5, system_actions_count=2)

        node = graph.get_or_create_state("hash_g", "TestActivity", screen_desc)

        # Saturate 3 out of 5
        for i in range(3):
            sig = ((100 + i * 50, 500), "click")
            node.record_action(sig)
            node.record_action(sig)

        assert node.get_saturation_rate(threshold=2) == pytest.approx(0.6)
