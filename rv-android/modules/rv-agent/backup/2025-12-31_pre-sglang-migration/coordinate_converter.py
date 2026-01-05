"""
Bidirectional coordinate conversion between device and optimized image spaces.

Provides utilities for converting coordinates between the actual device screen
resolution and the optimized image resolution used for LLM processing.
"""

from typing import Tuple


class CoordinateConverter:
    """
    Bidirectional coordinate converter for device ↔ optimized image spaces.

    ### Architectural Decisions:
    - Stateless conversions (no internal state)
    - Integer rounding for pixel precision
    - Bounds validation on optimized coordinates
    - Handles both single points and bounding boxes

    ### Role in the System:
    - Used by prompt builder to convert bounds to optimized space
    - Used by action mapper to convert LLM coords to device space
    - Centralizes conversion logic for consistency
    - Provides validation for optimized coordinate bounds

    ### Integration Points:
    - prompt_builder: Convert device bounds → optimized coords for description
    - action_mapper: Convert LLM coords → device coords for execution
    - android_tools: Validate optimized coords before execution
    """

    def __init__(
        self,
        device_dimensions: Tuple[int, int],
        optimized_dimensions: Tuple[int, int]
    ):
        """
        Initialize coordinate converter.

        Args:
            device_dimensions: Device screen size (width, height), e.g., (1080, 1920)
            optimized_dimensions: Optimized image size (width, height), e.g., (728, 1288)
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

        ### Use Case:
        Converting UIAutomator bounds to optimized coordinates for LLM prompt.

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

        ### Use Case:
        Converting LLM-generated coordinates to device space for action execution.

        Args:
            optimized_x: X coordinate in optimized space (0 to optimized_width)
            optimized_y: Y coordinate in optimized space (0 to optimized_height)

        Returns:
            Tuple of (device_x, device_y) clamped to device bounds
        """
        dev_x = int(optimized_x * self.scale_to_device_x)
        dev_y = int(optimized_y * self.scale_to_device_y)

        # Clamp to device bounds
        dev_x = max(0, min(dev_x, self.device_width - 1))
        dev_y = max(0, min(dev_y, self.device_height - 1))

        return (dev_x, dev_y)

    def bounds_device_to_optimized(
        self,
        bounds: list
    ) -> list:
        """
        Convert device bounds to optimized bounds.

        ### Use Case:
        Converting UIAutomator bounds [[x1,y1],[x2,y2]] for enhanced description.

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

    def calculate_center_optimized(
        self,
        device_bounds: list
    ) -> Tuple[int, int]:
        """
        Calculate center coordinates in optimized space from device bounds.

        ### Use Case:
        Computing center point for enhanced description from UIAutomator bounds.

        Args:
            device_bounds: Device bounds [[x1, y1], [x2, y2]]

        Returns:
            Center coordinates (center_x, center_y) in optimized space
        """
        if not device_bounds or len(device_bounds) != 2:
            return (0, 0)

        x1, y1 = device_bounds[0]
        x2, y2 = device_bounds[1]

        # Calculate center in device space first
        center_x_dev = (x1 + x2) // 2
        center_y_dev = (y1 + y2) // 2

        # Convert to optimized space
        return self.device_to_optimized(center_x_dev, center_y_dev)

    def validate_optimized_coords(
        self,
        optimized_x: int,
        optimized_y: int
    ) -> bool:
        """
        Validate that coordinates are within optimized image bounds.

        ### Use Case:
        Validating LLM-generated coordinates before execution.

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
        """
        Get information about configured dimensions.

        Returns:
            Dictionary with dimension information for logging/debugging
        """
        return {
            "device": {
                "width": self.device_width,
                "height": self.device_height,
                "resolution": f"{self.device_width}x{self.device_height}"
            },
            "optimized": {
                "width": self.optimized_width,
                "height": self.optimized_height,
                "resolution": f"{self.optimized_width}x{self.optimized_height}"
            },
            "scales": {
                "to_optimized_x": f"{self.scale_to_optimized_x:.4f}",
                "to_optimized_y": f"{self.scale_to_optimized_y:.4f}",
                "to_device_x": f"{self.scale_to_device_x:.4f}",
                "to_device_y": f"{self.scale_to_device_y:.4f}"
            }
        }
