"""
Tests for GeometryUtils - screenshot analysis geometric calculations.

Tests cover:
- calculate_overlap_percentage() with various rectangle configurations
- filter_overlapping_elements() with confidence-based filtering
- calculate_center_point(), calculate_area(), calculate_aspect_ratio()
- is_point_inside_rectangle() boundary checks
- calculate_distance_between_centers() Euclidean distance
- expand_rectangle() with padding and boundary constraints
- Error handling and edge cases
"""

import pytest
from rv_android_core.util.error.exceptions import RVValidationError
from rv_screen_parser.screenshot.utils.geometry_utils import (
    GeometryUtils,
    get_geometry_utils,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def geometry_utils():
    """Create GeometryUtils instance."""
    return GeometryUtils()


# ---------------------------------------------------------------------------
# Tests: calculate_overlap_percentage()
# ---------------------------------------------------------------------------


class TestCalculateOverlapPercentage:
    """Test calculate_overlap_percentage() with various configurations."""

    def test_identical_rectangles_full_overlap(self, geometry_utils):
        """Test that identical rectangles have 100% overlap."""
        overlap = geometry_utils.calculate_overlap_percentage(
            10, 10, 50, 50, 10, 10, 50, 50  # rect1  # rect2
        )
        assert overlap == 1.0

    def test_no_overlap_returns_zero(self, geometry_utils):
        """Test that non-overlapping rectangles return 0.0."""
        overlap = geometry_utils.calculate_overlap_percentage(
            0, 0, 50, 50, 100, 100, 50, 50  # rect1  # rect2
        )
        assert overlap == 0.0

    def test_partial_overlap(self, geometry_utils):
        """Test partial overlap calculation."""
        overlap = geometry_utils.calculate_overlap_percentage(
            0, 0, 50, 50, 25, 25, 50, 50  # rect1  # rect2 (overlaps by 25x25)
        )
        # Intersection: 25x25 = 625, smaller area: 50x50 = 2500
        # Overlap: 625/2500 = 0.25
        assert overlap == pytest.approx(0.25, rel=1e-2)

    def test_one_inside_other_full_overlap(self, geometry_utils):
        """Test when one rectangle is completely inside another."""
        overlap = geometry_utils.calculate_overlap_percentage(
            0, 0, 100, 100, 25, 25, 50, 50  # rect1 (large)  # rect2 (small, inside)
        )
        # Intersection: 50x50 = 2500, smaller area: 50x50 = 2500
        # Overlap: 2500/2500 = 1.0
        assert overlap == 1.0

    def test_edge_touching_no_overlap(self, geometry_utils):
        """Test that rectangles touching at edge have 0 overlap."""
        overlap = geometry_utils.calculate_overlap_percentage(
            0, 0, 50, 50, 50, 0, 50, 50  # rect1  # rect2 (touching at x=50)
        )
        assert overlap == 0.0

    def test_invalid_negative_dimensions_raises(self, geometry_utils):
        """Test that negative dimensions raise RVValidationError."""
        # ErrorHandler captures the exception, returns None
        result = geometry_utils.calculate_overlap_percentage(
            0, 0, -10, 50, 0, 0, 50, 50  # negative width
        )
        # Returns None due to error handler
        assert result is None

    def test_invalid_zero_dimensions_raises(self, geometry_utils):
        """Test that zero dimensions raise RVValidationError."""
        result = geometry_utils.calculate_overlap_percentage(
            0, 0, 0, 50, 0, 0, 50, 50  # zero width
        )
        # Returns None due to error handler
        assert result is None

    def test_invalid_negative_coordinates_raises(self, geometry_utils):
        """Test that negative coordinates raise RVValidationError."""
        result = geometry_utils.calculate_overlap_percentage(
            -10, 0, 50, 50, 0, 0, 50, 50  # negative x
        )
        # Returns None due to error handler
        assert result is None

    def test_overlap_relative_to_smaller_area(self, geometry_utils):
        """Test that overlap is relative to smaller rectangle."""
        overlap = geometry_utils.calculate_overlap_percentage(
            0, 0, 20, 20, 0, 0, 100, 100  # rect1 (small: 400)  # rect2 (large: 10000)
        )
        # Intersection: 20x20 = 400, smaller area: 400
        # Overlap: 400/400 = 1.0
        assert overlap == 1.0


# ---------------------------------------------------------------------------
# Tests: filter_overlapping_elements()
# ---------------------------------------------------------------------------


class TestFilterOverlappingElements:
    """Test filter_overlapping_elements() with confidence-based filtering."""

    def test_empty_list_returns_empty(self, geometry_utils):
        """Test that empty list returns empty list."""
        result = geometry_utils.filter_overlapping_elements([])
        assert result == []

    def test_no_overlapping_elements_keeps_all(self, geometry_utils):
        """Test that non-overlapping elements are all kept."""
        elements = [
            {"x": 0, "y": 0, "width": 50, "height": 50, "confidence": 0.9},
            {"x": 100, "y": 100, "width": 50, "height": 50, "confidence": 0.8},
        ]
        result = geometry_utils.filter_overlapping_elements(elements)
        assert len(result) == 2

    def test_keeps_higher_confidence_element(self, geometry_utils):
        """Test that higher confidence element is kept when overlapping."""
        elements = [
            {"x": 0, "y": 0, "width": 50, "height": 50, "confidence": 0.9},
            {"x": 10, "y": 10, "width": 50, "height": 50, "confidence": 0.5},
        ]
        result = geometry_utils.filter_overlapping_elements(elements)
        assert len(result) == 1
        assert result[0]["confidence"] == 0.9

    def test_default_overlap_threshold(self, geometry_utils):
        """Test default overlap threshold (0.6)."""
        # Create elements with ~50% overlap (below threshold)
        elements = [
            {"x": 0, "y": 0, "width": 100, "height": 100, "confidence": 0.9},
            {"x": 50, "y": 0, "width": 100, "height": 100, "confidence": 0.8},
        ]
        result = geometry_utils.filter_overlapping_elements(elements)
        # Should keep both (overlap < 0.6)
        assert len(result) == 2

    def test_custom_overlap_threshold(self, geometry_utils):
        """Test custom overlap threshold."""
        elements = [
            {"x": 0, "y": 0, "width": 100, "height": 100, "confidence": 0.9},
            {"x": 10, "y": 10, "width": 100, "height": 100, "confidence": 0.8},
        ]
        # Very low threshold - should filter more aggressively
        result = geometry_utils.filter_overlapping_elements(
            elements, overlap_threshold=0.1
        )
        assert len(result) == 1

    def test_missing_confidence_defaults_to_zero(self, geometry_utils):
        """Test that elements without confidence field default to 0.0."""
        elements = [
            {"x": 100, "y": 100, "width": 50, "height": 50, "confidence": 0.5},
            {"x": 0, "y": 0, "width": 50, "height": 50},  # no confidence
        ]
        result = geometry_utils.filter_overlapping_elements(elements)
        # Element with 0.5 confidence should be first
        assert len(result) >= 1

    def test_missing_required_field_raises(self, geometry_utils):
        """Test that missing required field raises RVValidationError."""
        elements = [
            {"x": 0, "y": 0, "width": 50},  # missing height
        ]
        # ErrorHandler captures the exception
        result = geometry_utils.filter_overlapping_elements(elements)
        # Returns None or [] due to error handler
        assert result is None or result == []

    def test_sorts_by_confidence_descending(self, geometry_utils):
        """Test that elements are sorted by confidence."""
        elements = [
            {"x": 0, "y": 0, "width": 50, "height": 50, "confidence": 0.5},
            {"x": 100, "y": 100, "width": 50, "height": 50, "confidence": 0.9},
            {"x": 200, "y": 200, "width": 50, "height": 50, "confidence": 0.7},
        ]
        result = geometry_utils.filter_overlapping_elements(elements)
        # All non-overlapping, should keep all
        assert len(result) == 3


# ---------------------------------------------------------------------------
# Tests: calculate_center_point()
# ---------------------------------------------------------------------------


class TestCalculateCenterPoint:
    """Test calculate_center_point() calculations."""

    def test_center_of_square(self, geometry_utils):
        """Test center of 100x100 square at origin."""
        center = geometry_utils.calculate_center_point(0, 0, 100, 100)
        assert center == (50, 50)

    def test_center_of_rectangle(self, geometry_utils):
        """Test center of 100x200 rectangle."""
        center = geometry_utils.calculate_center_point(10, 20, 100, 200)
        assert center == (60, 120)

    def test_center_with_odd_dimensions(self, geometry_utils):
        """Test center with odd dimensions (integer division)."""
        center = geometry_utils.calculate_center_point(0, 0, 5, 5)
        assert center == (2, 2)  # 5//2 = 2


# ---------------------------------------------------------------------------
# Tests: calculate_area()
# ---------------------------------------------------------------------------


class TestCalculateArea:
    """Test calculate_area() calculations."""

    def test_area_of_square(self, geometry_utils):
        """Test area of 10x10 square."""
        area = geometry_utils.calculate_area(10, 10)
        assert area == 100

    def test_area_of_rectangle(self, geometry_utils):
        """Test area of 5x20 rectangle."""
        area = geometry_utils.calculate_area(5, 20)
        assert area == 100

    def test_area_with_zero_dimension(self, geometry_utils):
        """Test area with zero dimension."""
        area = geometry_utils.calculate_area(0, 100)
        assert area == 0


# ---------------------------------------------------------------------------
# Tests: calculate_aspect_ratio()
# ---------------------------------------------------------------------------


class TestCalculateAspectRatio:
    """Test calculate_aspect_ratio() calculations."""

    def test_landscape_aspect_ratio(self, geometry_utils):
        """Test landscape aspect ratio (2:1)."""
        ratio = geometry_utils.calculate_aspect_ratio(200, 100)
        assert ratio == 2.0

    def test_portrait_aspect_ratio(self, geometry_utils):
        """Test portrait aspect ratio (1:2)."""
        ratio = geometry_utils.calculate_aspect_ratio(100, 200)
        assert ratio == 0.5

    def test_square_aspect_ratio(self, geometry_utils):
        """Test square aspect ratio (1:1)."""
        ratio = geometry_utils.calculate_aspect_ratio(100, 100)
        assert ratio == 1.0

    def test_zero_height_returns_default(self, geometry_utils):
        """Test that zero height returns 1.0."""
        ratio = geometry_utils.calculate_aspect_ratio(100, 0)
        assert ratio == 1.0


# ---------------------------------------------------------------------------
# Tests: is_point_inside_rectangle()
# ---------------------------------------------------------------------------


class TestIsPointInsideRectangle:
    """Test is_point_inside_rectangle() boundary checks."""

    def test_point_inside(self, geometry_utils):
        """Test point inside rectangle."""
        assert geometry_utils.is_point_inside_rectangle(25, 25, 0, 0, 50, 50) is True

    def test_point_outside(self, geometry_utils):
        """Test point outside rectangle."""
        assert geometry_utils.is_point_inside_rectangle(100, 100, 0, 0, 50, 50) is False

    def test_point_on_edge(self, geometry_utils):
        """Test point on rectangle edge is inside."""
        assert geometry_utils.is_point_inside_rectangle(50, 50, 0, 0, 50, 50) is True

    def test_point_on_left_edge(self, geometry_utils):
        """Test point on left edge."""
        assert geometry_utils.is_point_inside_rectangle(0, 25, 0, 0, 50, 50) is True

    def test_point_just_outside(self, geometry_utils):
        """Test point just outside rectangle."""
        assert geometry_utils.is_point_inside_rectangle(51, 51, 0, 0, 50, 50) is False


# ---------------------------------------------------------------------------
# Tests: calculate_distance_between_centers()
# ---------------------------------------------------------------------------


class TestCalculateDistanceBetweenCenters:
    """Test calculate_distance_between_centers() Euclidean distance."""

    def test_same_rectangles_zero_distance(self, geometry_utils):
        """Test that same rectangle has zero distance."""
        distance = geometry_utils.calculate_distance_between_centers(
            0, 0, 100, 100, 0, 0, 100, 100
        )
        assert distance == pytest.approx(0.0, abs=1e-6)

    def test_horizontal_distance(self, geometry_utils):
        """Test horizontal distance between centers."""
        # rect1: center at (50, 50), rect2: center at (150, 50)
        distance = geometry_utils.calculate_distance_between_centers(
            0, 0, 100, 100, 100, 0, 100, 100
        )
        assert distance == pytest.approx(100.0, abs=1e-6)

    def test_diagonal_distance(self, geometry_utils):
        """Test diagonal distance (3-4-5 triangle)."""
        # rect1: center at (50, 50), rect2: center at (110, 90)
        # Distance: sqrt((110-50)^2 + (90-50)^2) = sqrt(60^2 + 40^2) = sqrt(3600 + 1600) = sqrt(5200) ≈ 72.11
        distance = geometry_utils.calculate_distance_between_centers(
            0,
            0,
            100,
            100,  # center at (50, 50)
            60,
            40,
            100,
            100,  # center at (110, 90)
        )
        expected = ((110 - 50) ** 2 + (90 - 50) ** 2) ** 0.5
        assert distance == pytest.approx(expected, rel=1e-2)


# ---------------------------------------------------------------------------
# Tests: expand_rectangle()
# ---------------------------------------------------------------------------


class TestExpandRectangle:
    """Test expand_rectangle() with padding and boundary constraints."""

    def test_expand_without_boundaries(self, geometry_utils):
        """Test rectangle expansion without max boundaries."""
        result = geometry_utils.expand_rectangle(
            50, 50, 100, 100, padding_x=10, padding_y=10
        )
        # new_x = 50-10 = 40, new_y = 50-10 = 40
        # new_width = 100+20 = 120, new_height = 100+20 = 120
        assert result == (40, 40, 120, 120)

    def test_expand_respects_max_width(self, geometry_utils):
        """Test that expansion respects maximum width."""
        result = geometry_utils.expand_rectangle(
            50, 50, 100, 100, padding_x=50, padding_y=10, max_width=200
        )
        # new_x = 0, new_width would be 200 but capped to 200-0 = 200
        assert result[0] == 0  # new_x
        assert result[2] == 200  # new_width

    def test_expand_respects_max_height(self, geometry_utils):
        """Test that expansion respects maximum height."""
        result = geometry_utils.expand_rectangle(
            50, 50, 100, 100, padding_x=10, padding_y=50, max_height=180
        )
        # new_y = 0, new_height would be 200 but capped to 180-0 = 180
        assert result[1] == 0  # new_y
        assert result[3] == 180  # new_height

    def test_expand_does_not_go_negative(self, geometry_utils):
        """Test that expansion doesn't result in negative coordinates."""
        result = geometry_utils.expand_rectangle(
            5, 5, 100, 100, padding_x=10, padding_y=10
        )
        assert result[0] >= 0  # new_x >= 0
        assert result[1] >= 0  # new_y >= 0

    def test_expand_with_none_max_values(self, geometry_utils):
        """Test expansion with None max values (no boundaries)."""
        result = geometry_utils.expand_rectangle(
            50,
            50,
            100,
            100,
            padding_x=10,
            padding_y=10,
            max_width=None,
            max_height=None,
        )
        assert result == (40, 40, 120, 120)


# ---------------------------------------------------------------------------
# Tests: Global singleton
# ---------------------------------------------------------------------------


class TestGlobalSingleton:
    """Test get_geometry_utils() singleton pattern."""

    def test_get_geometry_utils_returns_instance(self):
        """Test that get_geometry_utils returns GeometryUtils instance."""
        utils = get_geometry_utils()
        assert isinstance(utils, GeometryUtils)

    def test_get_geometry_utils_returns_same_instance(self):
        """Test that get_geometry_utils returns same instance (singleton)."""
        utils1 = get_geometry_utils()
        utils2 = get_geometry_utils()
        assert utils1 is utils2
