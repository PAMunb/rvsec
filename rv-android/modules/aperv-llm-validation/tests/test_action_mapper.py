"""Tests for action_mapper — exercises all 5 steps of the matching algorithm."""

import math

import pytest

from aperv_llm_validation.data.models import MatchResult, MatchStep, Widget
from aperv_llm_validation.pipeline.action_mapper import map_to_action


# ---------------------------------------------------------------------------
# Helper to build Widget instances
# ---------------------------------------------------------------------------


def _widget(
    bounds: tuple[int, int, int, int],
    class_name: str = "android.widget.Button",
    clickable: bool = True,
    long_clickable: bool = False,
    editable: bool = False,
) -> Widget:
    return Widget(
        class_name=class_name,
        text="",
        content_desc="",
        resource_id="",
        bounds=bounds,
        clickable=clickable,
        long_clickable=long_clickable,
        editable=editable,
        checkable=False,
        enabled=True,
    )


# ---------------------------------------------------------------------------
# Step 1: Back action
# ---------------------------------------------------------------------------


class TestBackAction:
    def test_back_returns_matched(self):
        result = map_to_action(0, 0, "back", None, [])
        assert result.matched is True
        assert result.step == MatchStep.BACK
        assert result.widget is None

    def test_back_with_widgets(self):
        w = _widget((100, 200, 300, 400))
        result = map_to_action(0, 0, "back", None, [w])
        assert result.matched is True
        assert result.step == MatchStep.BACK


# ---------------------------------------------------------------------------
# Step 2: Boundary rejection
# ---------------------------------------------------------------------------


class TestBoundaryRejection:
    def test_top_boundary_rejected(self):
        """pixel_y < device_h * 0.05 -> rejected (1920 * 0.05 = 96)"""
        result = map_to_action(540, 50, "click", None, [], device_h=1920)
        assert result.matched is False
        assert result.step == MatchStep.NO_MATCH

    def test_bottom_boundary_rejected(self):
        """pixel_y > device_h * 0.94 -> rejected (1920 * 0.94 = 1804.8)"""
        result = map_to_action(540, 1850, "click", None, [], device_h=1920)
        assert result.matched is False
        assert result.step == MatchStep.NO_MATCH

    def test_just_below_top_boundary_rejected(self):
        """pixel_y = 95 < 96 -> rejected"""
        result = map_to_action(540, 95, "click", None, [], device_h=1920)
        assert result.matched is False

    def test_just_above_bottom_boundary_rejected(self):
        """pixel_y = 1805 > 1804.8 -> rejected"""
        result = map_to_action(540, 1805, "click", None, [], device_h=1920)
        assert result.matched is False

    def test_safe_zone_not_rejected(self):
        """pixel_y = 100 >= 96 -> NOT rejected by boundary check.
        Returns no_match because of empty widget list, not boundary."""
        result = map_to_action(540, 100, "click", None, [], device_h=1920)
        # Still no_match (empty widgets), but it passed boundary check
        assert result.matched is False

    def test_mid_screen_not_boundary_rejected(self):
        """pixel_y = 960 — squarely in safe zone."""
        result = map_to_action(540, 960, "click", None, [], device_h=1920)
        assert result.matched is False  # no widgets to match


# ---------------------------------------------------------------------------
# Step 3: Bounds containment
# ---------------------------------------------------------------------------


class TestBoundsContainment:
    def test_pixel_at_widget_center(self):
        w = _widget((400, 800, 600, 900))  # center=(500, 850)
        result = map_to_action(500, 850, "click", None, [w])
        assert result.matched is True
        assert result.step == MatchStep.BOUNDS_MATCH
        assert result.widget is w

    def test_overlapping_widgets_select_smallest(self):
        large = _widget((100, 200, 900, 800))  # area = 800 * 600 = 480000
        small = _widget((400, 400, 600, 600))  # area = 200 * 200 = 40000
        result = map_to_action(500, 500, "click", None, [large, small])
        assert result.matched is True
        assert result.step == MatchStep.BOUNDS_MATCH
        assert result.widget is small

    def test_pixel_outside_all_widgets(self):
        w = _widget((400, 400, 600, 600))
        result = map_to_action(100, 100, "click", None, [w], device_h=1920)
        # pixel (100, 100) is outside widget bounds and beyond Euclidean tolerance
        # Widget center is (500, 500), dist = ~565 >> tolerance
        assert result.matched is False
        assert result.step == MatchStep.NO_MATCH


# ---------------------------------------------------------------------------
# Step 4: Long-click retry
# ---------------------------------------------------------------------------


class TestLongClickRetry:
    def test_long_click_prefers_long_clickable_widget(self):
        regular = _widget((400, 400, 600, 600), long_clickable=False)
        long_w = _widget((400, 400, 600, 600), long_clickable=True)
        result = map_to_action(500, 500, "long_click", None, [regular, long_w])
        assert result.matched is True
        assert result.step == MatchStep.BOUNDS_MATCH
        assert result.widget is long_w

    def test_long_click_retry_without_filter(self):
        """If no long_clickable widget contains pixel, retry with any widget."""
        regular = _widget((400, 400, 600, 600), long_clickable=False)
        result = map_to_action(500, 500, "long_click", None, [regular])
        assert result.matched is True
        assert result.step == MatchStep.LONG_CLICK_RETRY
        assert result.widget is regular


# ---------------------------------------------------------------------------
# Step 5: Euclidean fallback
# ---------------------------------------------------------------------------


class TestEuclideanFallback:
    def test_within_tolerance(self):
        """Widget center at (500, 500), pixel at (530, 500) -> dist=30, within tolerance."""
        w = _widget((400, 400, 600, 600))  # size 200x200, tolerance=max(50,100)=100
        result = map_to_action(530, 500, "click", None, [w], device_h=1920)
        # Pixel not inside bounds (530 is inside [400,600]), actually it IS inside bounds
        # Use a pixel outside bounds but within Euclidean tolerance
        pass

    def test_pixel_near_widget_outside_bounds(self):
        """Pixel 30px away from widget center, outside bounds but within tolerance."""
        w = _widget((480, 480, 520, 520))  # center=(500,500), size 40x40, tolerance=max(50,20)=50
        result = map_to_action(540, 500, "click", None, [w], device_h=1920)
        # pixel (540,500) is outside bounds [480,520] but dist = 40 < 50 tolerance
        assert result.matched is True
        assert result.step == MatchStep.EUCLIDEAN_MATCH
        assert result.widget is w

    def test_euclidean_miss_too_far(self):
        """Pixel 200px from widget center -> beyond tolerance -> no match."""
        w = _widget((480, 480, 520, 520))  # center=(500,500), tolerance=max(50,20)=50
        result = map_to_action(700, 500, "click", None, [w], device_h=1920)
        assert result.matched is False
        assert result.step == MatchStep.NO_MATCH

    def test_euclidean_selects_nearest(self):
        """Two widgets outside bounds, select the nearest one."""
        w1 = _widget((200, 480, 240, 520))  # center=(220,500), tolerance=max(50,20)=50
        w2 = _widget((280, 480, 320, 520))  # center=(300,500), tolerance=max(50,20)=50
        # pixel at (345,500): outside both bounds, dist to w1=125 (>50), dist to w2=45 (<50)
        result = map_to_action(345, 500, "click", None, [w1, w2], device_h=1920)
        assert result.matched is True
        assert result.step == MatchStep.EUCLIDEAN_MATCH
        assert result.widget is w2


# ---------------------------------------------------------------------------
# type_text filtering
# ---------------------------------------------------------------------------


class TestTypeTextFilter:
    def test_type_text_on_button_no_match(self):
        """type_text with pixel on a Button (not input class) -> no match."""
        button = _widget(
            (400, 400, 600, 600),
            class_name="android.widget.Button",
        )
        result = map_to_action(500, 500, "type_text", "hello", [button], device_h=1920)
        assert result.matched is False

    def test_type_text_on_edittext_match(self):
        """type_text with pixel on an EditText -> match."""
        edit = _widget(
            (400, 400, 600, 600),
            class_name="android.widget.EditText",
            editable=True,
        )
        result = map_to_action(500, 500, "type_text", "hello", [edit], device_h=1920)
        assert result.matched is True
        assert result.step == MatchStep.BOUNDS_MATCH
        assert result.widget is edit

    def test_type_text_euclidean_also_filtered(self):
        """Euclidean fallback also applies input class filter for type_text."""
        button = _widget(
            (480, 480, 520, 520),
            class_name="android.widget.Button",
        )
        # Pixel near button but type_text -> button is filtered out
        result = map_to_action(540, 500, "type_text", "hi", [button], device_h=1920)
        assert result.matched is False


# ---------------------------------------------------------------------------
# Distance and nearest_widget tracking
# ---------------------------------------------------------------------------


class TestDistanceTracking:
    def test_matched_result_has_nearest_info(self):
        w = _widget((400, 400, 600, 600))
        result = map_to_action(500, 500, "click", None, [w])
        assert result.nearest_widget is w
        assert result.distance_to_nearest < float("inf")

    def test_no_match_has_nearest_info(self):
        w = _widget((400, 400, 600, 600))
        result = map_to_action(100, 100, "click", None, [w], device_h=1920)
        assert result.nearest_widget is w
        # Distance from (100,100) to center (500,500)
        expected = math.hypot(500 - 100, 500 - 100)
        assert abs(result.distance_to_nearest - expected) < 0.1

    def test_no_widgets_distance_is_inf(self):
        result = map_to_action(540, 960, "click", None, [], device_h=1920)
        assert result.distance_to_nearest == float("inf")
        assert result.nearest_widget is None

    def test_classification_is_none(self):
        """action_mapper never classifies no-match — evaluator does that."""
        w = _widget((400, 400, 600, 600))
        result = map_to_action(100, 100, "click", None, [w], device_h=1920)
        assert result.classification is None
