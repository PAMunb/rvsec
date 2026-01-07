"""
Unit tests for coordinate conversion functionality based on the Qwen3-VL coordinate system discovery.
"""
import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, Any

from rv_agent.services.coordinate_converter import CoordinateConverter, denormalize_qwen_coords, is_normalized_coords


class TestCoordinateConverter:
    """Test suite for coordinate conversion functionality."""

    def test_coordinate_converter_initialization(self):
        """Test coordinate converter initialization with device and optimized dimensions."""
        converter = CoordinateConverter(
            device_dimensions=(1080, 1920),
            optimized_dimensions=(704, 1248)
        )

        assert converter.device_width == 1080
        assert converter.device_height == 1920
        assert converter.optimized_width == 704
        assert converter.optimized_height == 1248

        # Check scale factors
        expected_scale_x = 704 / 1080  # ~0.652
        expected_scale_y = 1248 / 1920  # ~0.650

        assert abs(converter.scale_to_optimized_x - expected_scale_x) < 0.001
        assert abs(converter.scale_to_optimized_y - expected_scale_y) < 0.001

    def test_device_to_optimized_conversion(self):
        """Test conversion from device coordinates to optimized coordinates."""
        converter = CoordinateConverter(
            device_dimensions=(1080, 1920),
            optimized_dimensions=(704, 1248)
        )

        # Test corner cases
        x_opt, y_opt = converter.device_to_optimized(0, 0)
        assert x_opt == 0
        assert y_opt == 0

        # Test center of screen
        x_opt, y_opt = converter.device_to_optimized(540, 960)  # Half of 1080x1920
        expected_x = int(540 * (704 / 1080))  # ~352
        expected_y = int(960 * (1248 / 1920))  # ~624
        assert x_opt == expected_x
        assert y_opt == expected_y

        # Test full screen edges
        x_opt, y_opt = converter.device_to_optimized(1080, 1920)
        assert x_opt == 704
        assert y_opt == 1248

    def test_optimized_to_device_conversion(self):
        """Test conversion from optimized coordinates to device coordinates."""
        converter = CoordinateConverter(
            device_dimensions=(1080, 1920),
            optimized_dimensions=(704, 1248)
        )

        # Test corner cases
        x_dev, y_dev = converter.optimized_to_device(0, 0)
        assert x_dev == 0
        assert y_dev == 0

        # Test center of optimized screen
        x_dev, y_dev = converter.optimized_to_device(352, 624)  # Half of 704x1248
        expected_x = int(352 * (1080 / 704))  # ~540
        expected_y = int(624 * (1920 / 1248))  # ~960
        assert x_dev == expected_x
        assert y_dev == expected_y

        # Test full optimized screen edges
        x_dev, y_dev = converter.optimized_to_device(704, 1248)
        # Note: The optimized_to_device method clamps to device bounds
        assert x_dev == 1079  # 1080 - 1 due to clamping
        assert y_dev == 1919  # 1920 - 1 due to clamping

    def test_round_trip_conversion_accuracy(self):
        """Test that converting device->optimized->device maintains accuracy."""
        converter = CoordinateConverter(
            device_dimensions=(1080, 1920),
            optimized_dimensions=(704, 1248)
        )

        # Test various coordinates
        test_coords = [
            (0, 0),
            (100, 200),
            (540, 960),  # Center
            (270, 480),  # Quarter
        ]

        for x_dev, y_dev in test_coords:
            # Convert to optimized and back
            x_opt, y_opt = converter.device_to_optimized(x_dev, y_dev)
            x_back, y_back = converter.optimized_to_device(x_opt, y_opt)

            # Allow for small rounding errors due to integer conversion
            assert abs(x_back - x_dev) <= 2  # Allow up to 2 pixel difference
            assert abs(y_back - y_dev) <= 2

    def test_qwen3_vl_coordinate_normalization(self):
        """Test Qwen3-VL specific coordinate normalization [0, 1000) to pixels."""
        # Test the conversion from normalized [0, 1000) to pixel coordinates
        # Based on the discovery from the documentation

        # Test example from the documentation
        raw_x, raw_y = 499, 547
        pixel_x, pixel_y = denormalize_qwen_coords(raw_x, raw_y)

        expected_x = int((499 / 1000) * 1080)  # ~539
        expected_y = int((547 / 1000) * 1920)  # ~1050
        assert pixel_x == expected_x
        assert pixel_y == expected_y

        # Test edge cases
        pixel_x, pixel_y = denormalize_qwen_coords(0, 0)
        assert pixel_x == 0 and pixel_y == 0

        pixel_x, pixel_y = denormalize_qwen_coords(999, 999)
        assert pixel_x == int((999 / 1000) * 1080) and pixel_y == int((999 / 1000) * 1920)

    def test_qwen3_vl_denormalization_out_of_range(self):
        """Test Qwen3-VL denormalization with out-of-range values (should return original)."""
        # Test out of range values - should return original values
        pixel_x, pixel_y = denormalize_qwen_coords(1000, 500)  # x at boundary
        assert pixel_x == 1000 and pixel_y == 500

        pixel_x, pixel_y = denormalize_qwen_coords(500, 1000)  # y at boundary
        assert pixel_x == 500 and pixel_y == 1000

        pixel_x, pixel_y = denormalize_qwen_coords(-1, 500)  # negative x
        assert pixel_x == -1 and pixel_y == 500

        pixel_x, pixel_y = denormalize_qwen_coords(1500, 500)  # x too large
        assert pixel_x == 1500 and pixel_y == 500

    def test_coordinate_converter_with_different_dimensions(self):
        """Test coordinate converter with different screen dimensions."""
        converter = CoordinateConverter(
            device_dimensions=(720, 1280),  # Different device dimensions
            optimized_dimensions=(480, 854)  # Corresponding optimized dimensions
        )

        # Test conversion
        x_opt, y_opt = converter.device_to_optimized(360, 640)  # Half of device
        expected_x = int(360 * (480 / 720))  # 360 * (2/3) = 240
        expected_y = int(640 * (854 / 1280))  # 640 * (854/1280) = ~427
        assert x_opt == expected_x
        assert y_opt == expected_y

    def test_coordinate_converter_edge_cases(self):
        """Test coordinate converter with edge cases."""
        converter = CoordinateConverter(
            device_dimensions=(1080, 1920),
            optimized_dimensions=(704, 1248)
        )

        # Test negative coordinates (should handle gracefully)
        x_opt, y_opt = converter.device_to_optimized(-10, -20)
        assert x_opt < 0
        assert y_opt < 0

        # Test coordinates beyond device bounds
        x_opt, y_opt = converter.device_to_optimized(2000, 3000)
        assert x_opt > converter.optimized_width
        assert y_opt > converter.optimized_height

    def test_coordinate_converter_bounds_functions(self):
        """Test bounds conversion functions."""
        converter = CoordinateConverter(
            device_dimensions=(1080, 1920),
            optimized_dimensions=(704, 1248)
        )

        # Test bounds conversion
        device_bounds = [[100, 200], [300, 400]]  # [top-left, bottom-right]
        optimized_bounds = converter.bounds_device_to_optimized(device_bounds)

        expected_opt_x1 = int(100 * (704 / 1080))  # ~65
        expected_opt_y1 = int(200 * (1248 / 1920))  # ~130
        expected_opt_x2 = int(300 * (704 / 1080))  # ~195
        expected_opt_y2 = int(400 * (1248 / 1920))  # ~260

        assert optimized_bounds[0][0] == expected_opt_x1
        assert optimized_bounds[0][1] == expected_opt_y1
        assert optimized_bounds[1][0] == expected_opt_x2
        assert optimized_bounds[1][1] == expected_opt_y2

    def test_coordinate_converter_center_calculation(self):
        """Test center calculation from bounds."""
        converter = CoordinateConverter(
            device_dimensions=(1080, 1920),
            optimized_dimensions=(704, 1248)
        )

        # Test center calculation from device bounds
        device_bounds = [[100, 200], [300, 400]]  # [top-left, bottom-right]
        center_x, center_y = converter.calculate_center_optimized(device_bounds)

        # Center in device space: (100+300)/2, (200+400)/2 = (200, 300)
        expected_center_x = int(200 * (704 / 1080))  # ~130
        expected_center_y = int(300 * (1248 / 1920))  # ~195

        assert center_x == expected_center_x
        assert center_y == expected_center_y

    def test_is_normalized_coords_function(self):
        """Test the function that checks if coordinates are normalized."""
        # Test normalized coordinates (within [0, 1000))
        assert is_normalized_coords(499, 547) is True
        assert is_normalized_coords(0, 0) is True
        assert is_normalized_coords(999, 999) is True

        # Test non-normalized coordinates (outside [0, 1000))
        assert is_normalized_coords(1000, 500) is False  # x at boundary
        assert is_normalized_coords(500, 1000) is False  # y at boundary
        assert is_normalized_coords(-1, 500) is False    # negative x
        assert is_normalized_coords(500, -1) is False    # negative y
        assert is_normalized_coords(1500, 500) is False  # x too large
        assert is_normalized_coords(500, 1500) is False  # y too large

    def test_real_world_coordinate_conversion(self):
        """Test coordinate conversion with real-world examples from the documentation."""
        converter = CoordinateConverter(
            device_dimensions=(1080, 1920),
            optimized_dimensions=(704, 1248)
        )

        # Example from documentation: Target (device): (540, 1054)
        device_x, device_y = 540, 1054

        # Convert to optimized space for model processing
        opt_x, opt_y = converter.device_to_optimized(device_x, device_y)

        # Convert back to device space (simulating model response processing)
        back_x, back_y = converter.optimized_to_device(opt_x, opt_y)

        # Should be close to original (allowing for integer rounding)
        assert abs(back_x - device_x) <= 2
        assert abs(back_y - device_y) <= 2

    def test_qwen3_vl_specific_example(self):
        """Test the specific Qwen3-VL example from the documentation."""
        # Raw normalized coordinates from Qwen3-VL: (499, 547)
        raw_x, raw_y = 499, 547

        # Convert to pixel coordinates using the denormalization function
        pixel_x, pixel_y = denormalize_qwen_coords(raw_x, raw_y, 1080, 1920)

        # Expected: (499/1000 * 1080, 547/1000 * 1920) = (539, 1050)
        expected_x = int((499 / 1000) * 1080)
        expected_y = int((547 / 1000) * 1920)

        assert pixel_x == expected_x
        assert pixel_y == expected_y

        # This should be close to target (540, 1054) - distance of ~4 pixels
        distance = ((pixel_x - 540)**2 + (pixel_y - 1054)**2)**0.5
        assert distance <= 10  # Should be very close