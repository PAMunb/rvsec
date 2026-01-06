"""
Integration tests for LoopDetector with realistic action sequences.

Tests loop detection patterns, spatial loops, action sequence repetition,
and integration with exploration strategies.
"""

import pytest
from pathlib import Path
from typing import Dict, List, Tuple

from rv_screen_parser.parser.screen.uiautomator.uiautomator_parser import UIAutomator2Parser
from rv_screen_parser.parser.screen.visitor.default_visitor import DefaultTextVisitor
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription

from rv_agent.agent.dynamic_state_graph import DynamicStateGraph, compute_screen_hash_from_description
from rv_agent.routing.loop_detector import LoopDetector
from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.strategies.dfs_strategy import DFSStrategy


pytestmark = pytest.mark.integration


# =============================================================================
# Fixtures
# =============================================================================

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "screenshots"


def load_fixture(app_name: str, screen_num: str) -> Tuple[str, ScreenDescription]:
    """Load a fixture pair."""
    xml_path = FIXTURES_DIR / app_name / f"{screen_num}.uiautomator.xml"
    with open(xml_path, "r") as f:
        xml_content = f.read()

    parser = UIAutomator2Parser(visitor_class=DefaultTextVisitor)
    screen_desc = parser.parse(xml_content, activity=f"com.example.{app_name}.MainActivity")

    return xml_content, screen_desc


@pytest.fixture
def config():
    """Default agent config."""
    return RVAgentConfig.create_default(package_name="com.test.app")


@pytest.fixture
def loop_detector(config):
    """Fresh LoopDetector instance."""
    return LoopDetector(config=config)


@pytest.fixture
def graph():
    """Fresh DynamicStateGraph."""
    return DynamicStateGraph()


@pytest.fixture
def dfs_strategy(graph):
    """DFS strategy."""
    return DFSStrategy(graph=graph)


# =============================================================================
# Basic Loop Detection Tests
# =============================================================================

class TestBasicLoopDetection:
    """Test basic loop detection functionality."""

    def test_no_loop_empty_history(self, loop_detector):
        """No loop with empty history."""
        action = {"action_type": "CLICK", "x": 100, "y": 200}
        is_loop, count, threshold = loop_detector.detect_loop([], action)

        assert is_loop is False
        assert count == 0

    def test_no_loop_single_action(self, loop_detector):
        """No loop with single action in history."""
        history = [{"action_type": "CLICK", "x": 100, "y": 200}]
        current = {"action_type": "CLICK", "x": 300, "y": 400}

        is_loop, count, threshold = loop_detector.detect_loop(history, current)

        assert is_loop is False

    def test_no_loop_different_action_types(self, loop_detector):
        """No loop with different action types."""
        history = [
            {"action_type": "CLICK", "x": 100, "y": 200},
            {"action_type": "SCROLL", "direction": "down"},
        ]
        current = {"action_type": "BACK"}

        is_loop, count, threshold = loop_detector.detect_loop(history, current)

        assert is_loop is False


# =============================================================================
# Repeated Action Detection Tests
# =============================================================================

class TestRepeatedActionDetection:
    """Test detection of repeated actions."""

    def test_detects_consecutive_same_clicks(self, loop_detector):
        """Detect consecutive clicks at same position."""
        history = [
            {"action_type": "CLICK", "x": 352, "y": 273},
            {"action_type": "CLICK", "x": 352, "y": 273},
            {"action_type": "CLICK", "x": 352, "y": 273},
        ]
        current = {"action_type": "CLICK", "x": 352, "y": 273}

        is_loop, count, threshold = loop_detector.detect_loop(history, current)

        # Should count consecutive clicks
        assert count >= 3

    def test_no_loop_alternating_clicks(self, loop_detector):
        """No consecutive loop with alternating clicks."""
        history = [
            {"action_type": "CLICK", "x": 100, "y": 200},
            {"action_type": "CLICK", "x": 300, "y": 400},
            {"action_type": "CLICK", "x": 100, "y": 200},
        ]
        current = {"action_type": "CLICK", "x": 300, "y": 400}

        is_loop, count, threshold = loop_detector.detect_loop(history, current)

        # Alternating pattern doesn't create consecutive loop
        assert count <= 1

    def test_consecutive_count_breaks_on_different(self, loop_detector):
        """Consecutive count breaks when different action appears."""
        history = [
            {"action_type": "CLICK", "x": 100, "y": 200},
            {"action_type": "SCROLL", "direction": "down"},  # Breaks chain
            {"action_type": "CLICK", "x": 352, "y": 273},
            {"action_type": "CLICK", "x": 352, "y": 273},
        ]
        current = {"action_type": "CLICK", "x": 352, "y": 273}

        is_loop, count, threshold = loop_detector.detect_loop(history, current)

        # Count should be 2 (actions after SCROLL)
        assert count == 2


# =============================================================================
# Spatial Loop Detection Tests
# =============================================================================

class TestSpatialLoopDetection:
    """Test detection of spatial loops (clicks clustered in same area)."""

    def test_detects_spatial_loop(self, loop_detector):
        """Detect clicks clustered in small area."""
        # 3 clicks within 50px radius
        recent = [
            {"action_type": "CLICK", "x": 350, "y": 270},
            {"action_type": "CLICK", "x": 360, "y": 280},
            {"action_type": "CLICK", "x": 355, "y": 275},
        ]

        is_spatial = loop_detector.detect_spatial_loop(recent)

        assert is_spatial is True

    def test_no_spatial_loop_spread_clicks(self, loop_detector):
        """No spatial loop when clicks spread across screen."""
        recent = [
            {"action_type": "CLICK", "x": 100, "y": 200},
            {"action_type": "CLICK", "x": 500, "y": 600},
            {"action_type": "CLICK", "x": 200, "y": 800},
        ]

        is_spatial = loop_detector.detect_spatial_loop(recent)

        assert is_spatial is False

    def test_spatial_loop_ignores_non_clicks(self, loop_detector):
        """Spatial loop detection only considers CLICK actions."""
        recent = [
            {"action_type": "SCROLL", "direction": "down"},
            {"action_type": "CLICK", "x": 350, "y": 270},
            {"action_type": "BACK"},
            {"action_type": "CLICK", "x": 360, "y": 280},
            {"action_type": "SET_TEXT", "text": "test"},
            {"action_type": "CLICK", "x": 355, "y": 275},
        ]

        is_spatial = loop_detector.detect_spatial_loop(recent)

        # Only 3 CLICK actions clustered
        assert is_spatial is True

    def test_no_spatial_loop_insufficient_clicks(self, loop_detector):
        """No spatial loop with less than 3 clicks."""
        recent = [
            {"action_type": "CLICK", "x": 350, "y": 270},
            {"action_type": "CLICK", "x": 360, "y": 280},
        ]

        is_spatial = loop_detector.detect_spatial_loop(recent)

        assert is_spatial is False


# =============================================================================
# Sequence Pattern Detection Tests
# =============================================================================

class TestSequencePatternDetection:
    """Test detection of action sequence patterns."""

    def test_detects_repeating_pattern(self, loop_detector):
        """Detect A-B-A-B-A-B pattern."""
        recent = [
            {"action_type": "CLICK", "x": 100, "y": 200},
            {"action_type": "BACK"},
            {"action_type": "CLICK", "x": 100, "y": 200},
            {"action_type": "BACK"},
            {"action_type": "CLICK", "x": 100, "y": 200},
            {"action_type": "BACK"},
        ]

        is_rep, pattern, count = loop_detector.detect_action_sequence_repetition(recent)

        # Pattern [CLICK, BACK] repeats 3 times
        assert is_rep is True
        assert count >= 3

    def test_detects_three_action_pattern(self, loop_detector):
        """Detect A-B-C-A-B-C-A-B-C pattern."""
        recent = []
        for _ in range(3):
            recent.extend([
                {"action_type": "CLICK", "x": 100, "y": 200},
                {"action_type": "SCROLL", "direction": "down"},
                {"action_type": "BACK"},
            ])

        is_rep, pattern, count = loop_detector.detect_action_sequence_repetition(recent)

        assert is_rep is True

    def test_no_pattern_with_variation(self, loop_detector):
        """No pattern when actions vary."""
        recent = [
            {"action_type": "CLICK", "x": 100, "y": 200},
            {"action_type": "SCROLL", "direction": "down"},
            {"action_type": "CLICK", "x": 300, "y": 400},
            {"action_type": "SET_TEXT", "text": "test"},
            {"action_type": "BACK"},
            {"action_type": "CLICK", "x": 500, "y": 600},
        ]

        is_rep, pattern, count = loop_detector.detect_action_sequence_repetition(recent)

        assert is_rep is False


# =============================================================================
# Integration with Real Fixtures Tests
# =============================================================================

class TestFixtureIntegration:
    """Test loop detection with real fixture data."""

    def test_exploration_actions_not_loop(self, loop_detector, dfs_strategy, graph):
        """Normal exploration should not trigger loop."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        # Collect actions from DFS exploration
        action_history = []

        for i in range(5):
            action = dfs_strategy.select_next_action(screen_hash, screen_desc)
            if action is None:
                break

            coords = action.get_execution_coordinates()
            if coords:
                action_dict = {
                    "action_type": "CLICK",
                    "x": coords[0],
                    "y": coords[1]
                }
                action_history.append(action_dict)

        # DFS selects different actions, should not be loop
        if len(action_history) >= 2:
            current = action_history[-1]
            history = action_history[:-1]

            is_loop, count, threshold = loop_detector.detect_loop(history, current)

            # Normal exploration shouldn't trigger loop
            assert count < threshold

    def test_stuck_scenario_with_fixture_coords(self, loop_detector):
        """Test stuck scenario using coordinates from fixture."""
        _, screen_desc = load_fixture("cryptoapp", "001")

        actions = screen_desc.get_all_actions()
        if not actions:
            pytest.skip("No actions in fixture")

        first_action = actions[0]
        coords = first_action.get_execution_coordinates()

        if coords:
            # Simulate being stuck clicking same button
            history = [
                {"action_type": "CLICK", "x": coords[0], "y": coords[1]}
                for _ in range(5)
            ]
            current = {"action_type": "CLICK", "x": coords[0], "y": coords[1]}

            is_loop, count, threshold = loop_detector.detect_loop(history, current)

            # Should detect as potential loop
            assert count >= 5


# =============================================================================
# Coordinate Tolerance Tests
# =============================================================================

class TestCoordinateTolerance:
    """Test coordinate tolerance in action comparison."""

    def test_within_tolerance_is_similar(self, loop_detector):
        """Clicks within tolerance are considered similar."""
        history = [
            {"action_type": "CLICK", "x": 350, "y": 270},
            {"action_type": "CLICK", "x": 355, "y": 275},  # Within 20px
            {"action_type": "CLICK", "x": 360, "y": 280},  # Within 20px of prev
        ]
        current = {"action_type": "CLICK", "x": 358, "y": 278}

        is_loop, count, threshold = loop_detector.detect_loop(history, current)

        # All clicks within tolerance should count as consecutive
        assert count >= 2

    def test_outside_tolerance_not_similar(self, loop_detector):
        """Clicks outside tolerance are different."""
        history = [
            {"action_type": "CLICK", "x": 100, "y": 200},
        ]
        current = {"action_type": "CLICK", "x": 200, "y": 300}  # >20px away

        is_loop, count, threshold = loop_detector.detect_loop(history, current)

        assert count == 0


# =============================================================================
# Action Type Specific Tests
# =============================================================================

class TestActionTypeSpecific:
    """Test loop detection for specific action types."""

    def test_set_text_compares_text_content(self, loop_detector):
        """SET_TEXT compares text content, not coordinates."""
        history = [
            {"action_type": "SET_TEXT", "text": "hello", "x": 100, "y": 200},
            {"action_type": "SET_TEXT", "text": "hello", "x": 100, "y": 200},
        ]
        current = {"action_type": "SET_TEXT", "text": "hello", "x": 100, "y": 200}

        is_loop, count, threshold = loop_detector.detect_loop(history, current)

        # Same text should count as consecutive
        assert count == 2

    def test_set_text_different_text_not_similar(self, loop_detector):
        """SET_TEXT with different text not similar."""
        history = [
            {"action_type": "SET_TEXT", "text": "hello", "x": 100, "y": 200},
        ]
        current = {"action_type": "SET_TEXT", "text": "world", "x": 100, "y": 200}

        is_loop, count, threshold = loop_detector.detect_loop(history, current)

        assert count == 0

    def test_back_actions_similar(self, loop_detector):
        """BACK actions are similar regardless of other fields."""
        history = [
            {"action_type": "BACK"},
            {"action_type": "BACK"},
        ]
        current = {"action_type": "BACK"}

        is_loop, count, threshold = loop_detector.detect_loop(history, current)

        assert count == 2

    def test_scroll_actions_similar(self, loop_detector):
        """SCROLL actions are similar by type."""
        history = [
            {"action_type": "SCROLL", "direction": "down"},
            {"action_type": "SCROLL", "direction": "down"},
        ]
        current = {"action_type": "SCROLL", "direction": "down"}

        is_loop, count, threshold = loop_detector.detect_loop(history, current)

        assert count == 2


# =============================================================================
# Threshold Tests
# =============================================================================

class TestThreshold:
    """Test loop threshold behavior."""

    def test_below_threshold_not_loop(self, loop_detector, config):
        """Below threshold count doesn't trigger loop."""
        # Get threshold for CLICK
        threshold = config.get_loop_threshold("CLICK")

        # Create history just below threshold
        history = [
            {"action_type": "CLICK", "x": 352, "y": 273}
            for _ in range(threshold - 2)
        ]
        current = {"action_type": "CLICK", "x": 352, "y": 273}

        is_loop, count, _ = loop_detector.detect_loop(history, current)

        assert is_loop is False

    def test_at_threshold_is_loop(self, loop_detector, config):
        """At threshold count triggers loop."""
        threshold = config.get_loop_threshold("CLICK")

        history = [
            {"action_type": "CLICK", "x": 352, "y": 273}
            for _ in range(threshold)
        ]
        current = {"action_type": "CLICK", "x": 352, "y": 273}

        is_loop, count, returned_threshold = loop_detector.detect_loop(history, current)

        assert is_loop is True
        assert count >= threshold
        assert returned_threshold == threshold


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestEdgeCases:
    """Test loop detector edge cases."""

    def test_empty_current_action(self, loop_detector):
        """Handle empty current action."""
        history = [{"action_type": "CLICK", "x": 100, "y": 200}]
        current = {}

        is_loop, count, threshold = loop_detector.detect_loop(history, current)

        # Should handle gracefully
        assert isinstance(is_loop, bool)

    def test_missing_coordinates(self, loop_detector):
        """Handle action missing coordinates."""
        history = [{"action_type": "CLICK"}]  # No coords
        current = {"action_type": "CLICK"}

        is_loop, count, threshold = loop_detector.detect_loop(history, current)

        # Should handle gracefully (compare with default 0,0)
        assert isinstance(is_loop, bool)

    def test_long_history(self, loop_detector):
        """Handle long action history."""
        history = [
            {"action_type": "CLICK", "x": i * 50, "y": i * 50}
            for i in range(100)
        ]
        current = {"action_type": "CLICK", "x": 5000, "y": 5000}

        is_loop, count, threshold = loop_detector.detect_loop(history, current)

        # Should handle without performance issues
        assert count == 0  # Current is different from last in history
