"""
Unit tests for the coordinate_utils service.
"""
import pytest
from rv_agent.services import coordinate_utils

# Define standard dimensions for tests
DEVICE_DIMS = (1080, 1920)
OPTIMIZED_DIMS = (704, 1248)

class TestCoordinateUtils:
    """Test suite for coordinate utility functions."""

    # --- Tests for device_to_optimized ---

    def test_device_to_optimized(self):
        """Test basic device to optimized conversion."""
        # Center point
        opt_x, opt_y = coordinate_utils.device_to_optimized(540, 960, DEVICE_DIMS, OPTIMIZED_DIMS)
        assert (opt_x, opt_y) == (352, 624)
        
        # Origin
        opt_x, opt_y = coordinate_utils.device_to_optimized(0, 0, DEVICE_DIMS, OPTIMIZED_DIMS)
        assert (opt_x, opt_y) == (0, 0)

    def test_device_to_optimized_with_validation_success(self):
        """Test successful validation."""
        opt_x, opt_y = coordinate_utils.device_to_optimized(540, 960, DEVICE_DIMS, OPTIMIZED_DIMS, validate=True)
        assert (opt_x, opt_y) == (352, 624)

    def test_device_to_optimized_with_validation_failure(self):
        """Test validation failure for out-of-bounds coordinates."""
        # A device_x that results in opt_x < 0
        with pytest.raises(ValueError, match="X coordinate -1 out of optimized bounds"):
            coordinate_utils.device_to_optimized(-2, 960, DEVICE_DIMS, OPTIMIZED_DIMS, validate=True)
            
        # A device_y that results in opt_y > optimized_height
        with pytest.raises(ValueError, match="Y coordinate 1249 out of optimized bounds"):
            coordinate_utils.device_to_optimized(540, 1922, DEVICE_DIMS, OPTIMIZED_DIMS, validate=True)

    # --- Tests for optimized_to_device ---

    def test_optimized_to_device(self):
        """Test basic optimized to device conversion."""
        # Center point
        dev_x, dev_y = coordinate_utils.optimized_to_device(352, 624, DEVICE_DIMS, OPTIMIZED_DIMS)
        assert (dev_x, dev_y) == (540, 960)

        # Origin
        dev_x, dev_y = coordinate_utils.optimized_to_device(0, 0, DEVICE_DIMS, OPTIMIZED_DIMS)
        assert (dev_x, dev_y) == (0, 0)

    def test_optimized_to_device_clamping(self):
        """Test that results are clamped to device dimensions."""
        # Values outside the optimized space
        dev_x, dev_y = coordinate_utils.optimized_to_device(800, 1400, DEVICE_DIMS, OPTIMIZED_DIMS)
        assert dev_x == DEVICE_DIMS[0] - 1
        assert dev_y == DEVICE_DIMS[1] - 1
        
        # Negative values
        dev_x, dev_y = coordinate_utils.optimized_to_device(-10, -10, DEVICE_DIMS, OPTIMIZED_DIMS)
        assert dev_x == 0
        assert dev_y == 0

    # --- Tests for bounds_device_to_optimized ---

    def test_bounds_device_to_optimized(self):
        """Test bounds conversion."""
        bounds = [[100, 200], [500, 600]]
        opt_bounds = coordinate_utils.bounds_device_to_optimized(bounds, DEVICE_DIMS, OPTIMIZED_DIMS)
        assert opt_bounds == [[65, 130], [325, 390]]

    @pytest.mark.parametrize("invalid_bounds", [None, [], [[1, 1]]])
    def test_bounds_device_to_optimized_invalid_input(self, invalid_bounds):
        """Test that invalid bounds are returned as is."""
        assert coordinate_utils.bounds_device_to_optimized(invalid_bounds, DEVICE_DIMS, OPTIMIZED_DIMS) == invalid_bounds

    # --- Tests for calculate_center_optimized ---

    def test_calculate_center_optimized(self):
        """Test center calculation."""
        bounds = [[100, 200], [500, 600]]
        # Device center: (300, 400)
        # Optimized equivalent: (195, 260)
        center_x, center_y = coordinate_utils.calculate_center_optimized(bounds, DEVICE_DIMS, OPTIMIZED_DIMS)
        assert (center_x, center_y) == (195, 260)

    @pytest.mark.parametrize("invalid_bounds", [None, [], [[1, 1]]])
    def test_calculate_center_optimized_invalid_input(self, invalid_bounds):
        """Test that invalid bounds return (0, 0)."""
        assert coordinate_utils.calculate_center_optimized(invalid_bounds, DEVICE_DIMS, OPTIMIZED_DIMS) == (0, 0)

    # --- Tests for validate_optimized_coords ---

    def test_validate_optimized_coords_success(self):
        """Test successful validation of coordinates."""
        assert coordinate_utils.validate_optimized_coords(352, 624, OPTIMIZED_DIMS) is True

    def test_validate_optimized_coords_failure(self):
        """Test validation failure for out-of-bounds coordinates."""
        with pytest.raises(ValueError, match="X coordinate 800 out of optimized bounds"):
            coordinate_utils.validate_optimized_coords(800, 600, OPTIMIZED_DIMS)
        
        with pytest.raises(ValueError, match="Y coordinate 1300 out of optimized bounds"):
            coordinate_utils.validate_optimized_coords(300, 1300, OPTIMIZED_DIMS)
            
        with pytest.raises(ValueError, match="X coordinate -1 out of optimized bounds"):
            coordinate_utils.validate_optimized_coords(-1, 600, OPTIMIZED_DIMS)

        with pytest.raises(ValueError, match="Y coordinate -1 out of optimized bounds"):
            coordinate_utils.validate_optimized_coords(300, -1, OPTIMIZED_DIMS)

    # --- Tests for get_scale_factors ---

    def test_get_scale_factors(self):
        """Test the calculation of scale factors."""
        scales = coordinate_utils.get_scale_factors(DEVICE_DIMS, OPTIMIZED_DIMS)
        
        assert scales["device"]["width"] == 1080
        assert scales["optimized"]["height"] == 1248
        assert scales["scales"]["to_optimized_x"] == 704 / 1080
        assert scales["scales"]["to_device_y"] == 1920 / 1248
