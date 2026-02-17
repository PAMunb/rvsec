"""
Unit tests for spatial association between error indicators and input fields.

Tests _find_associated_input_action() and _calculate_association_score() functions
in algorithm_node. These functions map error indicators (from VisualErrorDetector)
to nearby input fields using overlap scoring + widget-type boost + below-field heuristic.
"""

import pytest
from unittest.mock import MagicMock

from rv_screen_parser.screenshot.models import (
    ErrorIndicator,
    DetectionMethod,
    ErrorType,
    BoundingBox,
)

from rv_agent.agent.nodes.algorithm_node import (
    _find_associated_input_action,
    _calculate_association_score,
    SPATIAL_BELOW_FIELD_SCORE,
    SPATIAL_BELOW_FIELD_MAX_PX,
)


def _make_error_indicator(x, y, width, height):
    """Create a real ErrorIndicator for spatial testing."""
    return ErrorIndicator(
        x=x,
        y=y,
        width=width,
        height=height,
        detection_method=DetectionMethod.COLOR,
        confidence=0.9,
        error_type=ErrorType.VALIDATION_ERROR,
    )


def _make_item_action(bounds, view_class="android.widget.EditText", action_type="set_text"):
    """Create a mock ItemAction with bounds and class."""
    action = MagicMock()
    action.target_view = {
        "bounds": bounds,
        "class": view_class,
    }
    action.action_type = action_type
    action.id = 1
    action.text = "some description"
    action.text_input = None
    action.event = MagicMock()
    action.get_execution_coordinates.return_value = (
        (bounds[0][0] + bounds[1][0]) // 2,
        (bounds[0][1] + bounds[1][1]) // 2,
    )
    return action


def _make_screen_item(actions):
    """Create a mock ScreenItem with given actions."""
    item = MagicMock()
    item.actions = actions
    return item


def _make_screen_description(items):
    """Create a mock ScreenDescription with given items."""
    desc = MagicMock()
    desc.items = items
    return desc


def _make_agent(
    spatial_edittext_boost=1.2,
    spatial_spinner_boost=1.1,
    spatial_min_match_threshold=0.1,
):
    """Create a mock agent with spatial config."""
    agent = MagicMock()
    agent.config.spatial_edittext_boost = spatial_edittext_boost
    agent.config.spatial_spinner_boost = spatial_spinner_boost
    agent.config.spatial_min_match_threshold = spatial_min_match_threshold
    return agent


class TestCalculateAssociationScore:
    """Tests for _calculate_association_score."""

    def test_overlap_edittext_boost(self):
        """EditText overlapping with error indicator gets 1.2x boost."""
        # Error indicator at (100, 500, 30, 30) = area around (115, 515)
        error_bbox = BoundingBox(x=100, y=500, width=30, height=30)

        # EditText bounds fully containing the error indicator
        item_bounds = [[90, 490], [200, 540]]
        item_class = "android.widget.EditText"

        agent = _make_agent()
        score = _calculate_association_score(error_bbox, item_bounds, item_class, agent)

        # With full overlap, base IoU should be > 0, and EditText boost = 1.2x
        assert score > 0
        # Compare with generic (no boost) to verify boost applies
        generic_score = _calculate_association_score(
            error_bbox, item_bounds, "android.widget.TextView", agent
        )
        assert score > generic_score

    def test_overlap_spinner_boost(self):
        """Spinner overlapping with error indicator gets 1.1x boost."""
        error_bbox = BoundingBox(x=100, y=500, width=30, height=30)
        item_bounds = [[90, 490], [200, 540]]
        item_class = "android.widget.Spinner"

        agent = _make_agent()
        score = _calculate_association_score(error_bbox, item_bounds, item_class, agent)

        generic_score = _calculate_association_score(
            error_bbox, item_bounds, "android.widget.Button", agent
        )
        assert score > generic_score

    def test_overlap_generic_no_boost(self):
        """Generic component gets no boost (1.0x)."""
        error_bbox = BoundingBox(x=100, y=500, width=30, height=30)
        item_bounds = [[90, 490], [200, 540]]
        item_class = "android.widget.Button"

        agent = _make_agent()
        score = _calculate_association_score(error_bbox, item_bounds, item_class, agent)

        # Score should still be > 0 from overlap
        assert score > 0

    def test_below_field_heuristic(self):
        """Error indicator 50px below EditText, horizontally aligned -> score ~0.7."""
        # EditText from y=400 to y=450
        item_bounds = [[100, 400], [300, 450]]

        # Error indicator at y=460 (10px below), horizontally within EditText x range
        # Error center_y = 460 + 15 = 475, item_bottom = 450
        # 475 > 450 AND 475 < 450 + 100 -> below-field matches
        error_bbox = BoundingBox(x=150, y=460, width=30, height=30)

        agent = _make_agent()
        score = _calculate_association_score(
            error_bbox, item_bounds, "android.widget.EditText", agent
        )

        # Should get at least SPATIAL_BELOW_FIELD_SCORE since there's no overlap
        # but the below-field heuristic fires
        assert score >= SPATIAL_BELOW_FIELD_SCORE

    def test_no_overlap_no_proximity_returns_zero(self):
        """Error far from item returns 0 score."""
        # Error at top of screen
        error_bbox = BoundingBox(x=100, y=10, width=20, height=20)
        # Item at bottom of screen
        item_bounds = [[100, 1800], [300, 1850]]

        agent = _make_agent()
        score = _calculate_association_score(
            error_bbox, item_bounds, "android.widget.EditText", agent
        )

        assert score == 0.0


class TestFindAssociatedInputAction:
    """Tests for _find_associated_input_action."""

    def test_empty_indicators_returns_none(self):
        """Empty error_indicators -> None."""
        agent = _make_agent()
        state = {"error_indicators": [], "screen_description": MagicMock()}

        result = _find_associated_input_action(agent, state)

        assert result is None

    def test_no_indicators_key_returns_none(self):
        """Missing error_indicators -> None."""
        agent = _make_agent()
        state = {"screen_description": MagicMock()}

        result = _find_associated_input_action(agent, state)

        assert result is None

    def test_no_screen_description_returns_none(self):
        """Missing screen_description -> None."""
        agent = _make_agent()
        indicator = _make_error_indicator(100, 500, 30, 30)
        state = {"error_indicators": [indicator]}

        result = _find_associated_input_action(agent, state)

        assert result is None

    def test_overlapping_edittext_returns_set_text(self):
        """Error indicator overlapping EditText -> returns (action, item) with set_text type."""
        indicator = _make_error_indicator(100, 500, 30, 30)

        action = _make_item_action(
            bounds=[[90, 490], [200, 540]],
            view_class="android.widget.EditText",
            action_type="set_text",
        )
        item = _make_screen_item([action])
        screen_desc = _make_screen_description([item])

        agent = _make_agent()
        state = {
            "error_indicators": [indicator],
            "screen_description": screen_desc,
        }

        result = _find_associated_input_action(agent, state)

        assert result is not None
        returned_action, returned_item = result
        assert returned_action == action
        assert returned_item == item

    def test_overlapping_spinner_returns_click(self):
        """Error indicator overlapping Spinner -> returns (action, item) with click type."""
        indicator = _make_error_indicator(100, 500, 30, 30)

        action = _make_item_action(
            bounds=[[90, 490], [200, 540]],
            view_class="android.widget.Spinner",
            action_type="click",
        )
        item = _make_screen_item([action])
        screen_desc = _make_screen_description([item])

        agent = _make_agent()
        state = {
            "error_indicators": [indicator],
            "screen_description": screen_desc,
        }

        result = _find_associated_input_action(agent, state)

        assert result is not None
        returned_action, returned_item = result
        assert returned_action.action_type == "click"

    def test_no_spatial_match_returns_none(self):
        """No items match above threshold -> None."""
        indicator = _make_error_indicator(100, 10, 20, 20)

        action = _make_item_action(
            bounds=[[100, 1800], [300, 1850]],
            view_class="android.widget.EditText",
            action_type="set_text",
        )
        item = _make_screen_item([action])
        screen_desc = _make_screen_description([item])

        agent = _make_agent()
        state = {
            "error_indicators": [indicator],
            "screen_description": screen_desc,
        }

        result = _find_associated_input_action(agent, state)

        assert result is None

    def test_multiple_indicators_highest_wins(self):
        """Two indicators, one closer to EditText -> highest-scoring match."""
        # Indicator 1: far from the EditText
        indicator_far = _make_error_indicator(800, 100, 20, 20)
        # Indicator 2: overlapping the EditText
        indicator_close = _make_error_indicator(100, 500, 30, 30)

        action = _make_item_action(
            bounds=[[90, 490], [200, 540]],
            view_class="android.widget.EditText",
            action_type="set_text",
        )
        item = _make_screen_item([action])
        screen_desc = _make_screen_description([item])

        agent = _make_agent()
        state = {
            "error_indicators": [indicator_far, indicator_close],
            "screen_description": screen_desc,
        }

        result = _find_associated_input_action(agent, state)

        # Should find the close indicator's match
        assert result is not None
        returned_action, _ = result
        assert returned_action == action

    def test_item_with_no_target_view_skipped(self):
        """Item where target_view has no bounds -> skipped gracefully."""
        indicator = _make_error_indicator(100, 500, 30, 30)

        action_no_bounds = MagicMock()
        action_no_bounds.target_view = None
        action_no_bounds.action_type = "set_text"

        action_with_bounds = _make_item_action(
            bounds=[[90, 490], [200, 540]],
            view_class="android.widget.EditText",
            action_type="set_text",
        )

        item1 = _make_screen_item([action_no_bounds])
        item2 = _make_screen_item([action_with_bounds])
        screen_desc = _make_screen_description([item1, item2])

        agent = _make_agent()
        state = {
            "error_indicators": [indicator],
            "screen_description": screen_desc,
        }

        result = _find_associated_input_action(agent, state)

        # Should find the action with bounds, skipping the one without
        assert result is not None
        returned_action, _ = result
        assert returned_action == action_with_bounds
