"""
Coordinate converter unit tests.

Tests coordinate conversion between device, optimized, and Qwen spaces.
"""

import pytest


pytestmark = pytest.mark.unit


class TestCoordinateConverter:
    """Test CoordinateConverter class."""

    def test_create_default(self):
        """Create converter with default dimensions."""
        from rv_agent.services.coordinate_converter import CoordinateConverter

        converter = CoordinateConverter()

        assert converter.device_width == 1080
        assert converter.device_height == 1920
        assert converter.optimized_width == 704
        assert converter.optimized_height == 1248

    def test_create_custom(self):
        """Create converter with custom dimensions."""
        from rv_agent.services.coordinate_converter import CoordinateConverter

        converter = CoordinateConverter(
            device_dimensions=(1440, 2560),
            optimized_dimensions=(720, 1280)
        )

        assert converter.device_width == 1440
        assert converter.device_height == 2560
        assert converter.optimized_width == 720
        assert converter.optimized_height == 1280

    def test_device_to_optimized_center(self):
        """Convert device center to optimized center."""
        from rv_agent.services.coordinate_converter import CoordinateConverter

        converter = CoordinateConverter()

        # Device center: 540, 960
        opt_x, opt_y = converter.device_to_optimized(540, 960)

        # Should be approximately optimized center: 352, 624
        assert 350 <= opt_x <= 354
        assert 622 <= opt_y <= 626

    def test_device_to_optimized_origin(self):
        """Convert device origin to optimized origin."""
        from rv_agent.services.coordinate_converter import CoordinateConverter

        converter = CoordinateConverter()
        opt_x, opt_y = converter.device_to_optimized(0, 0)

        assert opt_x == 0
        assert opt_y == 0

    def test_device_to_optimized_corner(self):
        """Convert device corner to optimized corner."""
        from rv_agent.services.coordinate_converter import CoordinateConverter

        converter = CoordinateConverter()
        opt_x, opt_y = converter.device_to_optimized(1079, 1919)

        # Should be near optimized corner
        assert opt_x <= 704
        assert opt_y <= 1248

    def test_optimized_to_device_center(self):
        """Convert optimized center to device center."""
        from rv_agent.services.coordinate_converter import CoordinateConverter

        converter = CoordinateConverter()

        # Optimized center: 352, 624
        dev_x, dev_y = converter.optimized_to_device(352, 624)

        # Should be approximately device center: 540, 960
        assert 538 <= dev_x <= 542
        assert 958 <= dev_y <= 962

    def test_roundtrip_conversion(self):
        """Device -> Optimized -> Device is approximately identity."""
        from rv_agent.services.coordinate_converter import CoordinateConverter

        converter = CoordinateConverter()

        original_x, original_y = 540, 960
        opt_x, opt_y = converter.device_to_optimized(original_x, original_y)
        back_x, back_y = converter.optimized_to_device(opt_x, opt_y)

        # Should be close to original (within rounding error)
        assert abs(back_x - original_x) <= 2
        assert abs(back_y - original_y) <= 2

    def test_bounds_device_to_optimized(self):
        """Convert device bounds to optimized bounds."""
        from rv_agent.services.coordinate_converter import CoordinateConverter

        converter = CoordinateConverter()

        device_bounds = [[100, 200], [300, 400]]
        opt_bounds = converter.bounds_device_to_optimized(device_bounds)

        assert len(opt_bounds) == 2
        assert len(opt_bounds[0]) == 2
        assert len(opt_bounds[1]) == 2

        # Optimized bounds should be smaller
        assert opt_bounds[1][0] < 300
        assert opt_bounds[1][1] < 400

    def test_calculate_center_optimized(self):
        """Calculate center of bounds in optimized space."""
        from rv_agent.services.coordinate_converter import CoordinateConverter

        converter = CoordinateConverter()

        device_bounds = [[0, 0], [1080, 1920]]
        center_x, center_y = converter.calculate_center_optimized(device_bounds)

        # Center should be approximately optimized center
        assert 350 <= center_x <= 354
        assert 622 <= center_y <= 626

    def test_get_dimensions_info(self):
        """Get dimensions info returns dict."""
        from rv_agent.services.coordinate_converter import CoordinateConverter

        converter = CoordinateConverter()
        info = converter.get_dimensions_info()

        assert "device" in info
        assert "optimized" in info
        assert "1080x1920" in info["device"]
        assert "704x1248" in info["optimized"]


class TestDenormalizeQwenCoords:
    """Test denormalize_qwen_coords function."""

    def test_center_normalized(self):
        """Convert normalized center (500, 500) to pixel center."""
        from rv_agent.services.coordinate_converter import denormalize_qwen_coords

        pixel_x, pixel_y = denormalize_qwen_coords(500, 500, 1080, 1920)

        # Should be center of image
        assert pixel_x == 540
        assert pixel_y == 960

    def test_origin_normalized(self):
        """Convert normalized origin (0, 0) to pixel origin."""
        from rv_agent.services.coordinate_converter import denormalize_qwen_coords

        pixel_x, pixel_y = denormalize_qwen_coords(0, 0, 1080, 1920)

        assert pixel_x == 0
        assert pixel_y == 0

    def test_corner_normalized(self):
        """Convert normalized corner (999, 999) to pixel corner."""
        from rv_agent.services.coordinate_converter import denormalize_qwen_coords

        pixel_x, pixel_y = denormalize_qwen_coords(999, 999, 1080, 1920)

        # Should be near but not at corner
        assert pixel_x >= 1070
        assert pixel_y >= 1910

    def test_passthrough_large_values(self):
        """Values >= 1000 are passed through."""
        from rv_agent.services.coordinate_converter import denormalize_qwen_coords

        pixel_x, pixel_y = denormalize_qwen_coords(1500, 2000, 1080, 1920)

        # Should pass through unchanged
        assert pixel_x == 1500
        assert pixel_y == 2000

    def test_default_dimensions(self):
        """Uses default 1080x1920 if not specified."""
        from rv_agent.services.coordinate_converter import denormalize_qwen_coords

        pixel_x, pixel_y = denormalize_qwen_coords(500, 500)

        assert pixel_x == 540
        assert pixel_y == 960


class TestIsNormalizedCoords:
    """Test is_normalized_coords function."""

    def test_normalized_coords(self):
        """Values in [0, 1000) are normalized."""
        from rv_agent.services.coordinate_converter import is_normalized_coords

        assert is_normalized_coords(0, 0)
        assert is_normalized_coords(500, 500)
        assert is_normalized_coords(999, 999)

    def test_not_normalized_large(self):
        """Values >= 1000 are not normalized."""
        from rv_agent.services.coordinate_converter import is_normalized_coords

        assert not is_normalized_coords(1000, 500)
        assert not is_normalized_coords(500, 1000)
        assert not is_normalized_coords(1080, 1920)

    def test_not_normalized_negative(self):
        """Negative values are not normalized."""
        from rv_agent.services.coordinate_converter import is_normalized_coords

        assert not is_normalized_coords(-1, 500)
        assert not is_normalized_coords(500, -1)


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    def test_device_to_optimized_function(self):
        """Module-level device_to_optimized works."""
        from rv_agent.services.coordinate_converter import device_to_optimized

        opt_x, opt_y = device_to_optimized(540, 960)

        assert 350 <= opt_x <= 354
        assert 622 <= opt_y <= 626

    def test_optimized_to_device_function(self):
        """Module-level optimized_to_device works."""
        from rv_agent.services.coordinate_converter import optimized_to_device

        dev_x, dev_y = optimized_to_device(352, 624)

        assert 538 <= dev_x <= 542
        assert 958 <= dev_y <= 962


class TestConstants:
    """Test module constants."""

    def test_qwen3_vl_dimensions(self):
        """Qwen3-VL dimensions are correct."""
        from rv_agent.services.coordinate_converter import QWEN3_VL_WIDTH, QWEN3_VL_HEIGHT

        # Must be multiples of 32 for Qwen3-VL
        assert QWEN3_VL_WIDTH == 704
        assert QWEN3_VL_HEIGHT == 1248
        assert QWEN3_VL_WIDTH % 32 == 0
        assert QWEN3_VL_HEIGHT % 32 == 0

    def test_device_presets(self):
        """Device presets are defined."""
        from rv_agent.services.coordinate_converter import (
            DEVICE_1080P,
            DEVICE_1440P,
            DEVICE_720P,
        )

        assert DEVICE_1080P == (1080, 1920)
        assert DEVICE_1440P == (1440, 2560)
        assert DEVICE_720P == (720, 1280)
