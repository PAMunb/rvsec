"""
Unit tests for LoopDetector - Detects repetitive action sequences.

Tests verify:
- Consecutive action detection
- Action similarity comparison (type, coordinates, text)
- Spatial loop detection (clicks clustered in same area)
- Action sequence repetition detection
- Configurable thresholds
"""

import pytest
from unittest.mock import MagicMock

from rv_agent.routing.loop_detector import LoopDetector
from rv_agent.config.agent_config import RVAgentConfig


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_config():
    """Create mock RVAgentConfig with loop thresholds."""
    config = MagicMock(spec=RVAgentConfig)
    # Default thresholds by action type
    config.get_loop_threshold.side_effect = lambda action_type: {
        "CLICK": 3,
        "BACK": 5,
        "SCROLL": 4,
        "SET_TEXT": 2,
        "UNKNOWN": 3
    }.get(action_type, 3)
    return config


@pytest.fixture
def detector(mock_config):
    """Create LoopDetector instance."""
    return LoopDetector(config=mock_config)


# =============================================================================
# LoopDetector Initialization Tests
# =============================================================================

class TestLoopDetectorInit:
    """Tests for LoopDetector initialization."""

    def test_init_with_config(self, mock_config):
        """Test initialization with config."""
        detector = LoopDetector(config=mock_config)

        assert detector.config is mock_config
        assert detector.COORDINATE_TOLERANCE == 20
        assert detector.SPATIAL_LOOP_RADIUS == 50
        assert detector.SPATIAL_LOOP_WINDOW == 3
        assert detector.SEQUENCE_MIN_LENGTH == 2
        assert detector.SEQUENCE_REPETITION_THRESHOLD == 3


# =============================================================================
# Action Similarity Tests
# =============================================================================

class TestActionsAreSimilar:
    """Tests for LoopDetector._actions_are_similar()."""

    def test_different_types_not_similar(self, detector):
        """Test that different action types are not similar."""
        a1 = {"action_type": "CLICK", "x": 100, "y": 200}
        a2 = {"action_type": "BACK"}

        assert detector._actions_are_similar(a1, a2) is False

    def test_same_click_coordinates_similar(self, detector):
        """Test that CLICKs at same coordinates are similar."""
        a1 = {"action_type": "CLICK", "x": 100, "y": 200}
        a2 = {"action_type": "CLICK", "x": 100, "y": 200}

        assert detector._actions_are_similar(a1, a2) is True

    def test_click_within_tolerance_similar(self, detector):
        """Test that CLICKs within tolerance are similar."""
        a1 = {"action_type": "CLICK", "x": 100, "y": 200}
        a2 = {"action_type": "CLICK", "x": 115, "y": 210}  # Within 20px tolerance

        assert detector._actions_are_similar(a1, a2) is True

    def test_click_outside_tolerance_not_similar(self, detector):
        """Test that CLICKs outside tolerance are not similar."""
        a1 = {"action_type": "CLICK", "x": 100, "y": 200}
        a2 = {"action_type": "CLICK", "x": 150, "y": 200}  # 50px away

        assert detector._actions_are_similar(a1, a2) is False

    def test_set_text_same_text_similar(self, detector):
        """Test that SET_TEXT with same text are similar."""
        a1 = {"action_type": "SET_TEXT", "text": "hello"}
        a2 = {"action_type": "SET_TEXT", "text": "hello"}

        assert detector._actions_are_similar(a1, a2) is True

    def test_set_text_different_text_not_similar(self, detector):
        """Test that SET_TEXT with different text are not similar."""
        a1 = {"action_type": "SET_TEXT", "text": "hello"}
        a2 = {"action_type": "SET_TEXT", "text": "world"}

        assert detector._actions_are_similar(a1, a2) is False

    def test_back_actions_similar(self, detector):
        """Test that BACK actions are always similar."""
        a1 = {"action_type": "BACK"}
        a2 = {"action_type": "BACK"}

        assert detector._actions_are_similar(a1, a2) is True

    def test_scroll_actions_similar(self, detector):
        """Test that SCROLL actions are similar (type match sufficient)."""
        a1 = {"action_type": "SCROLL", "direction": "up"}
        a2 = {"action_type": "SCROLL", "direction": "down"}

        # Note: Current implementation only checks type for non-CLICK/SET_TEXT
        assert detector._actions_are_similar(a1, a2) is True

    def test_missing_coordinates_handled(self, detector):
        """Test that missing coordinates default to 0."""
        a1 = {"action_type": "CLICK"}  # No x, y
        a2 = {"action_type": "CLICK", "x": 5, "y": 5}  # Within tolerance of (0,0)

        assert detector._actions_are_similar(a1, a2) is True


# =============================================================================
# Count Consecutive Actions Tests
# =============================================================================

class TestCountConsecutiveActions:
    """Tests for LoopDetector._count_consecutive_actions()."""

    def test_empty_history_returns_zero(self, detector):
        """Test that empty history returns count of 0."""
        current = {"action_type": "CLICK", "x": 100, "y": 200}

        count = detector._count_consecutive_actions([], current)

        assert count == 0

    def test_no_matches_returns_zero(self, detector):
        """Test that no matching actions returns 0."""
        recent = [
            {"action_type": "BACK"},
            {"action_type": "SCROLL"}
        ]
        current = {"action_type": "CLICK", "x": 100, "y": 200}

        count = detector._count_consecutive_actions(recent, current)

        assert count == 0

    def test_counts_consecutive_matches(self, detector):
        """Test counting consecutive matching actions."""
        recent = [
            {"action_type": "BACK"},
            {"action_type": "CLICK", "x": 100, "y": 200},
            {"action_type": "CLICK", "x": 105, "y": 205}  # Similar
        ]
        current = {"action_type": "CLICK", "x": 102, "y": 202}  # Similar

        count = detector._count_consecutive_actions(recent, current)

        assert count == 2  # Last 2 CLICKs are similar to current

    def test_stops_at_non_match(self, detector):
        """Test that counting stops at first non-matching action."""
        recent = [
            {"action_type": "CLICK", "x": 100, "y": 200},
            {"action_type": "BACK"},  # Breaks sequence
            {"action_type": "CLICK", "x": 102, "y": 202}
        ]
        current = {"action_type": "CLICK", "x": 100, "y": 200}

        count = detector._count_consecutive_actions(recent, current)

        assert count == 1  # Only last CLICK matches

    def test_counts_all_consecutive(self, detector):
        """Test counting when all recent actions match."""
        recent = [
            {"action_type": "BACK"},
            {"action_type": "BACK"},
            {"action_type": "BACK"}
        ]
        current = {"action_type": "BACK"}

        count = detector._count_consecutive_actions(recent, current)

        assert count == 3


# =============================================================================
# Detect Loop Tests
# =============================================================================

class TestDetectLoop:
    """Tests for LoopDetector.detect_loop()."""

    def test_no_loop_below_threshold(self, detector):
        """Test that no loop is detected below threshold."""
        recent = [
            {"action_type": "CLICK", "x": 100, "y": 200},
            {"action_type": "CLICK", "x": 105, "y": 205}
        ]
        current = {"action_type": "CLICK", "x": 102, "y": 202}

        is_loop, count, threshold = detector.detect_loop(recent, current)

        assert is_loop is False
        assert count == 2
        assert threshold == 3  # CLICK threshold

    def test_loop_at_threshold(self, detector):
        """Test that loop is detected at threshold."""
        recent = [
            {"action_type": "CLICK", "x": 100, "y": 200},
            {"action_type": "CLICK", "x": 105, "y": 205},
            {"action_type": "CLICK", "x": 102, "y": 202}
        ]
        current = {"action_type": "CLICK", "x": 100, "y": 200}

        is_loop, count, threshold = detector.detect_loop(recent, current)

        assert is_loop is True
        assert count == 3
        assert threshold == 3

    def test_loop_above_threshold(self, detector):
        """Test that loop is detected above threshold."""
        recent = [
            {"action_type": "BACK"},
            {"action_type": "BACK"},
            {"action_type": "BACK"},
            {"action_type": "BACK"},
            {"action_type": "BACK"}
        ]
        current = {"action_type": "BACK"}

        is_loop, count, threshold = detector.detect_loop(recent, current)

        assert is_loop is True
        assert count == 5
        assert threshold == 5  # BACK threshold

    def test_different_thresholds_by_type(self, detector):
        """Test that different action types have different thresholds."""
        # SET_TEXT has threshold of 2
        recent = [
            {"action_type": "SET_TEXT", "text": "test"},
            {"action_type": "SET_TEXT", "text": "test"}
        ]
        current = {"action_type": "SET_TEXT", "text": "test"}

        is_loop, count, threshold = detector.detect_loop(recent, current)

        assert is_loop is True
        assert threshold == 2

    def test_unknown_action_type(self, detector):
        """Test handling of unknown action type."""
        recent = [
            {"action_type": "UNKNOWN"},
            {"action_type": "UNKNOWN"},
            {"action_type": "UNKNOWN"}
        ]
        current = {"action_type": "UNKNOWN"}

        is_loop, count, threshold = detector.detect_loop(recent, current)

        assert count == 3
        assert threshold == 3


# =============================================================================
# Spatial Loop Detection Tests
# =============================================================================

class TestDetectSpatialLoop:
    """Tests for LoopDetector.detect_spatial_loop()."""

    def test_no_loop_with_few_clicks(self, detector):
        """Test that spatial loop is not detected with few clicks."""
        recent = [
            {"action_type": "CLICK", "x": 100, "y": 200},
            {"action_type": "CLICK", "x": 102, "y": 202}
        ]

        assert detector.detect_spatial_loop(recent) is False

    def test_no_loop_with_spread_clicks(self, detector):
        """Test that spatial loop is not detected when clicks are spread."""
        recent = [
            {"action_type": "CLICK", "x": 100, "y": 200},
            {"action_type": "CLICK", "x": 500, "y": 600},  # Far away
            {"action_type": "CLICK", "x": 120, "y": 220}
        ]

        assert detector.detect_spatial_loop(recent) is False

    def test_loop_with_clustered_clicks(self, detector):
        """Test that spatial loop is detected when clicks are clustered."""
        recent = [
            {"action_type": "CLICK", "x": 100, "y": 200},
            {"action_type": "CLICK", "x": 110, "y": 210},  # Within 50px
            {"action_type": "CLICK", "x": 120, "y": 220}   # Within 50px
        ]

        assert detector.detect_spatial_loop(recent) is True

    def test_filters_non_click_actions(self, detector):
        """Test that non-CLICK actions are filtered."""
        recent = [
            {"action_type": "BACK"},
            {"action_type": "SCROLL"},
            {"action_type": "CLICK", "x": 100, "y": 200}
        ]

        # Only 1 CLICK, not enough for spatial loop
        assert detector.detect_spatial_loop(recent) is False

    def test_uses_last_n_clicks(self, detector):
        """Test that only last N clicks are considered."""
        recent = [
            {"action_type": "CLICK", "x": 1000, "y": 2000},  # Far away but old
            {"action_type": "CLICK", "x": 100, "y": 200},
            {"action_type": "CLICK", "x": 110, "y": 210},
            {"action_type": "CLICK", "x": 120, "y": 220}
        ]

        # Last 3 clicks are clustered
        assert detector.detect_spatial_loop(recent) is True

    def test_missing_coordinates(self, detector):
        """Test handling of missing coordinates."""
        recent = [
            {"action_type": "CLICK"},  # No x, y - defaults to (0, 0)
            {"action_type": "CLICK", "x": 10, "y": 10},  # Within 50px of origin
            {"action_type": "CLICK", "x": 20, "y": 20}   # Within 50px of origin
        ]

        assert detector.detect_spatial_loop(recent) is True


# =============================================================================
# Action Signature Tests
# =============================================================================

class TestGetActionSignature:
    """Tests for LoopDetector._get_action_signature()."""

    def test_type_text_signature(self, detector):
        """Test signature for TYPE_TEXT action."""
        action = {"action_type": "TYPE_TEXT", "text": "hello"}

        sig = detector._get_action_signature(action)

        assert sig == "TYPE"

    def test_set_text_signature(self, detector):
        """Test signature for SET_TEXT action."""
        action = {"action_type": "SET_TEXT", "text": "hello"}

        sig = detector._get_action_signature(action)

        assert sig == "TYPE"

    def test_click_signature_rounds_to_grid(self, detector):
        """Test signature for CLICK action rounds to 50px grid."""
        action = {"action_type": "CLICK", "x": 352, "y": 624}

        sig = detector._get_action_signature(action)

        # 352 -> 350 (round to 50), 624 -> 600
        assert sig == "CLICK:(350,600)"

    def test_long_click_signature(self, detector):
        """Test signature for LONG_CLICK action."""
        action = {"action_type": "LONG_CLICK", "x": 100, "y": 200}

        sig = detector._get_action_signature(action)

        assert sig == "LONG_CLICK:(100,200)"

    def test_scroll_signature_includes_direction(self, detector):
        """Test signature for SCROLL includes direction."""
        action = {"action_type": "SCROLL", "direction": "down"}

        sig = detector._get_action_signature(action)

        assert sig == "SCROLL:down"

    def test_back_signature(self, detector):
        """Test signature for BACK action."""
        action = {"action_type": "BACK"}

        sig = detector._get_action_signature(action)

        assert sig == "BACK"

    def test_unknown_action_signature(self, detector):
        """Test signature for unknown action type."""
        action = {"action_type": "CUSTOM_ACTION"}

        sig = detector._get_action_signature(action)

        assert sig == "CUSTOM_ACTION"

    def test_missing_action_type(self, detector):
        """Test signature when action_type is missing."""
        action = {"x": 100, "y": 200}

        sig = detector._get_action_signature(action)

        assert sig == "UNKNOWN"


# =============================================================================
# Pattern Repetition Tests
# =============================================================================

class TestCheckPatternRepetition:
    """Tests for LoopDetector._check_pattern_repetition()."""

    def test_no_pattern_with_short_list(self, detector):
        """Test that short lists don't have patterns."""
        signatures = ["CLICK:(100,200)", "BACK"]

        found, pattern, count = detector._check_pattern_repetition(
            signatures, pattern_length=2, threshold=3
        )

        assert found is False
        assert pattern == []
        assert count == 0

    def test_detects_repeating_pattern_length_2(self, detector):
        """Test detection of 2-action repeating pattern."""
        signatures = [
            "CLICK:(100,200)", "BACK",
            "CLICK:(100,200)", "BACK",
            "CLICK:(100,200)", "BACK"
        ]

        found, pattern, count = detector._check_pattern_repetition(
            signatures, pattern_length=2, threshold=3
        )

        assert found is True
        assert pattern == ["CLICK:(100,200)", "BACK"]
        assert count == 3

    def test_detects_repeating_pattern_length_3(self, detector):
        """Test detection of 3-action repeating pattern."""
        signatures = [
            "CLICK:(100,200)", "SCROLL:down", "BACK",
            "CLICK:(100,200)", "SCROLL:down", "BACK",
            "CLICK:(100,200)", "SCROLL:down", "BACK"
        ]

        found, pattern, count = detector._check_pattern_repetition(
            signatures, pattern_length=3, threshold=3
        )

        assert found is True
        assert pattern == ["CLICK:(100,200)", "SCROLL:down", "BACK"]
        assert count == 3

    def test_no_pattern_when_different(self, detector):
        """Test that different sequences don't match."""
        signatures = [
            "CLICK:(100,200)", "BACK",
            "CLICK:(300,400)", "SCROLL:up",  # Different
            "CLICK:(100,200)", "BACK"
        ]

        found, pattern, count = detector._check_pattern_repetition(
            signatures, pattern_length=2, threshold=3
        )

        assert found is False


# =============================================================================
# Detect Action Sequence Repetition Tests
# =============================================================================

class TestDetectActionSequenceRepetition:
    """Tests for LoopDetector.detect_action_sequence_repetition()."""

    def test_no_repetition_with_short_history(self, detector):
        """Test that short history returns no repetition."""
        recent = [
            {"action_type": "CLICK", "x": 100, "y": 200},
            {"action_type": "BACK"}
        ]

        found, pattern, count = detector.detect_action_sequence_repetition(recent)

        assert found is False
        assert pattern == []
        assert count == 0

    def test_detects_2_action_repetition(self, detector):
        """Test detection of 2-action sequence repetition."""
        recent = [
            {"action_type": "CLICK", "x": 100, "y": 200},
            {"action_type": "BACK"},
            {"action_type": "CLICK", "x": 100, "y": 200},
            {"action_type": "BACK"},
            {"action_type": "CLICK", "x": 100, "y": 200},
            {"action_type": "BACK"}
        ]

        found, pattern, count = detector.detect_action_sequence_repetition(recent)

        assert found is True
        assert len(pattern) == 2
        assert count == 3

    def test_detects_3_action_repetition(self, detector):
        """Test detection of 3-action sequence repetition."""
        recent = [
            {"action_type": "CLICK", "x": 100, "y": 200},
            {"action_type": "SCROLL", "direction": "down"},
            {"action_type": "BACK"},
            {"action_type": "CLICK", "x": 100, "y": 200},
            {"action_type": "SCROLL", "direction": "down"},
            {"action_type": "BACK"},
            {"action_type": "CLICK", "x": 100, "y": 200},
            {"action_type": "SCROLL", "direction": "down"},
            {"action_type": "BACK"}
        ]

        found, pattern, count = detector.detect_action_sequence_repetition(recent)

        assert found is True
        assert len(pattern) >= 2  # At least 2-action pattern

    def test_no_repetition_with_variety(self, detector):
        """Test that varied actions don't trigger repetition."""
        recent = [
            {"action_type": "CLICK", "x": 100, "y": 200},
            {"action_type": "BACK"},
            {"action_type": "SCROLL", "direction": "up"},
            {"action_type": "CLICK", "x": 300, "y": 400},
            {"action_type": "SET_TEXT", "text": "test"},
            {"action_type": "CLICK", "x": 500, "y": 600}
        ]

        found, pattern, count = detector.detect_action_sequence_repetition(recent)

        assert found is False


# =============================================================================
# Integration Tests
# =============================================================================

class TestLoopDetectorIntegration:
    """Integration tests for LoopDetector."""

    def test_full_loop_detection_flow(self, detector):
        """Test complete loop detection with realistic action sequence."""
        # Simulate agent clicking same button repeatedly
        recent = []
        for i in range(5):
            recent.append({"action_type": "CLICK", "x": 540, "y": 960})

        current = {"action_type": "CLICK", "x": 540, "y": 960}

        is_loop, count, threshold = detector.detect_loop(recent, current)

        assert is_loop is True
        assert count == 5

    def test_combined_detections(self, detector):
        """Test running multiple detection methods on same history."""
        recent = [
            {"action_type": "CLICK", "x": 100, "y": 200},
            {"action_type": "CLICK", "x": 105, "y": 205},
            {"action_type": "CLICK", "x": 110, "y": 210}
        ]
        current = {"action_type": "CLICK", "x": 100, "y": 200}

        # Basic loop detection
        is_loop, count, threshold = detector.detect_loop(recent, current)

        # Spatial loop detection
        is_spatial = detector.detect_spatial_loop(recent)

        # Both should detect the loop
        assert is_loop is True
        assert is_spatial is True

    def test_realistic_exploration_no_loop(self, detector):
        """Test that normal exploration doesn't trigger loops."""
        recent = [
            {"action_type": "CLICK", "x": 100, "y": 200},
            {"action_type": "SCROLL", "direction": "down"},
            {"action_type": "CLICK", "x": 300, "y": 400},
            {"action_type": "BACK"},
            {"action_type": "CLICK", "x": 500, "y": 600}
        ]
        current = {"action_type": "CLICK", "x": 700, "y": 800}

        is_loop, _, _ = detector.detect_loop(recent, current)
        is_spatial = detector.detect_spatial_loop(recent)
        is_sequence, _, _ = detector.detect_action_sequence_repetition(recent)

        assert is_loop is False
        assert is_spatial is False
        assert is_sequence is False
