"""
Property-based tests for coordinate_utils using Hypothesis.
"""
import pytest
from hypothesis import given, strategies as st
from rv_agent.services import coordinate_utils

# Define standard dimensions for tests
DEVICE_DIMS = (1080, 1920)
OPTIMIZED_DIMS = (704, 1248)

# Define strategies for generating coordinates within the device dimensions
device_x_strategy = st.integers(min_value=0, max_value=DEVICE_DIMS[0] - 1)
device_y_strategy = st.integers(min_value=0, max_value=DEVICE_DIMS[1] - 1)

optimized_x_strategy = st.integers(min_value=0, max_value=OPTIMIZED_DIMS[0] - 1)
optimized_y_strategy = st.integers(min_value=0, max_value=OPTIMIZED_DIMS[1] - 1)


@pytest.mark.hypothesis
class TestCoordinateUtilsHypothesis:
    """Property-based tests for coordinate utility functions."""

    @given(x=device_x_strategy, y=device_y_strategy)
    def test_device_to_optimized_bounds(self, x, y):
        """Ensures converted coordinates are within the optimized bounds."""
        opt_x, opt_y = coordinate_utils.device_to_optimized(x, y, DEVICE_DIMS, OPTIMIZED_DIMS)
        
        assert 0 <= opt_x < OPTIMIZED_DIMS[0]
        assert 0 <= opt_y < OPTIMIZED_DIMS[1]

    @given(x=optimized_x_strategy, y=optimized_y_strategy)
    def test_optimized_to_device_bounds(self, x, y):
        """Ensures converted coordinates are within the device bounds."""
        dev_x, dev_y = coordinate_utils.optimized_to_device(x, y, DEVICE_DIMS, OPTIMIZED_DIMS)
        
        assert 0 <= dev_x < DEVICE_DIMS[0]
        assert 0 <= dev_y < DEVICE_DIMS[1]

    @given(x=device_x_strategy, y=device_y_strategy)
    def test_roundtrip_conversion_is_close(self, x, y):
        """
        Tests the round-trip conversion property.
        device -> optimized -> device should result in coordinates close to the original.
        """
        opt_x, opt_y = coordinate_utils.device_to_optimized(x, y, DEVICE_DIMS, OPTIMIZED_DIMS)
        roundtrip_x, roundtrip_y = coordinate_utils.optimized_to_device(opt_x, opt_y, DEVICE_DIMS, OPTIMIZED_DIMS)

        # The conversion involves integer truncation, so we expect a small error margin.
        # A tolerance of 2 pixels is generally acceptable for this kind of scaling.
        assert abs(roundtrip_x - x) <= 2
        assert abs(roundtrip_y - y) <= 2

    @given(
        x1=device_x_strategy,
        y1=device_y_strategy,
        x2=device_x_strategy,
        y2=device_y_strategy,
    )
    def test_bounds_conversion_center_is_consistent(self, x1, y1, x2, y2):
        """
        Tests that the center of converted bounds is close to the converted center of the original bounds.
        """
        # Ensure x1 <= x2 and y1 <= y2 for valid bounds
        min_x, max_x = min(x1, x2), max(x1, x2)
        min_y, max_y = min(y1, y2), max(y1, y2)
        
        device_bounds = [[min_x, min_y], [max_x, max_y]]

        # 1. Calculate center in optimized space directly
        center_opt = coordinate_utils.calculate_center_optimized(device_bounds, DEVICE_DIMS, OPTIMIZED_DIMS)

        # 2. Convert bounds to optimized space and calculate center there
        opt_bounds = coordinate_utils.bounds_device_to_optimized(device_bounds, DEVICE_DIMS, OPTIMIZED_DIMS)
        opt_center_x = (opt_bounds[0][0] + opt_bounds[1][0]) // 2
        opt_center_y = (opt_bounds[0][1] + opt_bounds[1][1]) // 2

        # They should be very close (allowing for rounding differences)
        assert abs(center_opt[0] - opt_center_x) <= 2
        assert abs(center_opt[1] - opt_center_y) <= 2
