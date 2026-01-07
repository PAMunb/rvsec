"""
Bidirectional coordinate conversion for Qwen3-VL vision model.

Provides utilities for converting coordinates between:
- Device space: Original screen resolution (e.g., 1080x1920)
- Optimized space: What the model "sees" (e.g., 704x1248)
- Qwen3-VL normalized space: [0, 1000) coordinates

Based on validation from rvsec-vision-llm benchmark (2,847 tests).
"""

from dataclasses import dataclass
from typing import Tuple


# Qwen3-VL optimized dimensions (must be multiples of 32)
QWEN3_VL_WIDTH = 704   # 22 x 32
QWEN3_VL_HEIGHT = 1248  # 39 x 32

# Common device resolutions
DEVICE_1080P = (1080, 1920)
DEVICE_1440P = (1440, 2560)
DEVICE_720P = (720, 1280)


@dataclass
class CoordinateSpace:
    """Represents a coordinate space with dimensions."""
    width: int
    height: int

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height


# Pre-defined spaces
QWEN3_VL_SPACE = CoordinateSpace(QWEN3_VL_WIDTH, QWEN3_VL_HEIGHT)
DEVICE_1080P_SPACE = CoordinateSpace(1080, 1920)


class CoordinateConverter:
    """
    Bidirectional coordinate converter for Qwen3-VL.

    The model processes images in an optimized resolution (704x1248).
    When coordinates appear in prompts or responses, they need to be
    converted between device and optimized spaces.

    Usage:
        converter = CoordinateConverter(device_dims=(1080, 1920))

        # For prompts: convert device coords to what model expects
        opt_x, opt_y = converter.device_to_optimized(540, 960)

        # For responses: convert model output to device coords
        dev_x, dev_y = converter.optimized_to_device(352, 624)
    """

    def __init__(
        self,
        device_dimensions: Tuple[int, int] = DEVICE_1080P,
        optimized_dimensions: Tuple[int, int] = (QWEN3_VL_WIDTH, QWEN3_VL_HEIGHT)
    ):
        """
        Initialize coordinate converter.

        Args:
            device_dimensions: Device screen (width, height), e.g., (1080, 1920)
            optimized_dimensions: Optimized image (width, height), default Qwen3-VL
        """
        self.device_width, self.device_height = device_dimensions
        self.optimized_width, self.optimized_height = optimized_dimensions

        # Pre-compute scale factors
        self.scale_to_optimized_x = self.optimized_width / self.device_width
        self.scale_to_optimized_y = self.optimized_height / self.device_height
        self.scale_to_device_x = self.device_width / self.optimized_width
        self.scale_to_device_y = self.device_height / self.optimized_height

    def device_to_optimized(
        self,
        device_x: int,
        device_y: int,
        validate: bool = False
    ) -> Tuple[int, int]:
        """
        Convert device coordinates to optimized image coordinates.

        Use this when building prompts with UI element positions.
        The model will "see" these coordinates in the optimized image.

        Args:
            device_x: X coordinate in device space (0 to device_width)
            device_y: Y coordinate in device space (0 to device_height)
            validate: Whether to validate resulting coordinates are in bounds

        Returns:
            Tuple of (optimized_x, optimized_y)

        Raises:
            ValueError: If validate=True and coordinates are out of bounds
        """
        opt_x = int(device_x * self.scale_to_optimized_x)
        opt_y = int(device_y * self.scale_to_optimized_y)

        if validate:
            self._validate_optimized_coords(opt_x, opt_y)

        return (opt_x, opt_y)

    def optimized_to_device(
        self,
        optimized_x: int,
        optimized_y: int
    ) -> Tuple[int, int]:
        """
        Convert optimized image coordinates to device coordinates.

        Use this when processing model responses.
        The model outputs coordinates in the optimized space it "sees".

        Args:
            optimized_x: X coordinate in optimized space
            optimized_y: Y coordinate in optimized space

        Returns:
            Tuple of (device_x, device_y) clamped to device bounds
        """
        dev_x = int(optimized_x * self.scale_to_device_x)
        dev_y = int(optimized_y * self.scale_to_device_y)

        # Clamp to device bounds
        dev_x = max(0, min(dev_x, self.device_width - 1))
        dev_y = max(0, min(dev_y, self.device_height - 1))

        return (dev_x, dev_y)

    def bounds_device_to_optimized(self, bounds: list) -> list:
        """
        Convert device bounds to optimized bounds.

        Args:
            bounds: Device bounds in format [[x1, y1], [x2, y2]]

        Returns:
            Optimized bounds in format [[opt_x1, opt_y1], [opt_x2, opt_y2]]
        """
        if not bounds or len(bounds) != 2:
            return bounds

        x1, y1 = bounds[0]
        x2, y2 = bounds[1]

        opt_x1, opt_y1 = self.device_to_optimized(x1, y1)
        opt_x2, opt_y2 = self.device_to_optimized(x2, y2)

        return [[opt_x1, opt_y1], [opt_x2, opt_y2]]

    def bounds_to_optimized(
        self,
        x1: int, y1: int, x2: int, y2: int
    ) -> Tuple[int, int, int, int]:
        """
        Convert device bounds to optimized space.

        Args:
            x1, y1: Top-left corner in device space
            x2, y2: Bottom-right corner in device space

        Returns:
            (opt_x1, opt_y1, opt_x2, opt_y2) in optimized space
        """
        opt_x1, opt_y1 = self.device_to_optimized(x1, y1)
        opt_x2, opt_y2 = self.device_to_optimized(x2, y2)
        return (opt_x1, opt_y1, opt_x2, opt_y2)

    def calculate_center_optimized(self, device_bounds: list) -> Tuple[int, int]:
        """
        Calculate center coordinates in optimized space from device bounds.

        Args:
            device_bounds: Device bounds [[x1, y1], [x2, y2]]

        Returns:
            Center coordinates (center_x, center_y) in optimized space
        """
        if not device_bounds or len(device_bounds) != 2:
            return (0, 0)

        x1, y1 = device_bounds[0]
        x2, y2 = device_bounds[1]

        center_x_dev = (x1 + x2) // 2
        center_y_dev = (y1 + y2) // 2

        return self.device_to_optimized(center_x_dev, center_y_dev)

    def validate_optimized_coords(
        self,
        optimized_x: int,
        optimized_y: int
    ) -> bool:
        """
        Validate that coordinates are within optimized image bounds.

        Args:
            optimized_x: X coordinate in optimized space
            optimized_y: Y coordinate in optimized space

        Returns:
            True if coordinates are valid

        Raises:
            ValueError: If coordinates are out of bounds
        """
        self._validate_optimized_coords(optimized_x, optimized_y)
        return True

    def _validate_optimized_coords(self, x: int, y: int):
        """
        Internal validation with detailed error message.

        Args:
            x: X coordinate in optimized space
            y: Y coordinate in optimized space

        Raises:
            ValueError: If coordinates are out of bounds
        """
        if not (0 <= x <= self.optimized_width):
            raise ValueError(
                f"X coordinate {x} out of optimized bounds "
                f"[0, {self.optimized_width}]"
            )

        if not (0 <= y <= self.optimized_height):
            raise ValueError(
                f"Y coordinate {y} out of optimized bounds "
                f"[0, {self.optimized_height}]"
            )

    def get_dimensions_info(self) -> dict:
        """Get information about configured dimensions."""
        return {
            "device": f"{self.device_width}x{self.device_height}",
            "optimized": f"{self.optimized_width}x{self.optimized_height}",
            "scale_to_opt": f"({self.scale_to_optimized_x:.3f}, {self.scale_to_optimized_y:.3f})",
            "scale_to_dev": f"({self.scale_to_device_x:.3f}, {self.scale_to_device_y:.3f})",
        }


def denormalize_qwen_coords(
    x: int | float,
    y: int | float,
    image_width: int = 1080,
    image_height: int = 1920,
) -> Tuple[int, int]:
    """
    Convert Qwen3-VL [0, 1000) normalized coordinates to pixel coordinates.

    Qwen3-VL uses a normalized coordinate system where both x and y are in [0, 1000).
    See: https://github.com/QwenLM/Qwen3-VL/issues/1486

    CRITICAL: This conversion is essential when using visual grounding mode.
    Without it, hit rate drops from ~58% to ~3.6%.

    Args:
        x: X coordinate in [0, 1000) range
        y: Y coordinate in [0, 1000) range
        image_width: Target image width
        image_height: Target image height

    Returns:
        Tuple of (pixel_x, pixel_y)
    """
    if 0 <= x < 1000 and 0 <= y < 1000:
        pixel_x = int((x / 1000) * image_width)
        pixel_y = int((y / 1000) * image_height)
        return pixel_x, pixel_y
    return int(x), int(y)


def is_normalized_coords(x: int | float, y: int | float) -> bool:
    """
    Check if coordinates appear to be in Qwen3-VL normalized [0, 1000) space.

    Args:
        x: X coordinate
        y: Y coordinate

    Returns:
        True if coordinates appear to be normalized
    """
    return 0 <= x < 1000 and 0 <= y < 1000


# Default converter for 1080p devices
default_converter = CoordinateConverter()


def device_to_optimized(x: int, y: int) -> Tuple[int, int]:
    """Quick conversion using default 1080p converter."""
    return default_converter.device_to_optimized(x, y)


def optimized_to_device(x: int, y: int) -> Tuple[int, int]:
    """Quick conversion using default 1080p converter."""
    return default_converter.optimized_to_device(x, y)
