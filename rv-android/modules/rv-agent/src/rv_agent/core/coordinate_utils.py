"""
Coordinate conversion utilities for device ↔ optimized image space transformations.

This module provides pure static functions for bidirectional coordinate conversions
between the actual device screen resolution and the optimized image resolution used
for LLM processing.

All functions are stateless and can be used without instantiation.
"""

from typing import Tuple


def device_to_optimized(
    device_x: int,
    device_y: int,
    device_dimensions: Tuple[int, int],
    optimized_dimensions: Tuple[int, int],
    validate: bool = False
) -> Tuple[int, int]:
    """
    Convert device coordinates to optimized image coordinates.

    Args:
        device_x: X coordinate in device space
        device_y: Y coordinate in device space
        device_dimensions: Device screen size (width, height), e.g., (1080, 1920)
        optimized_dimensions: Optimized image size (width, height), e.g., (704, 1248)
        validate: Whether to validate resulting coordinates are in bounds

    Returns:
        Tuple of (optimized_x, optimized_y)

    Raises:
        ValueError: If validate=True and coordinates are out of bounds

    Example:
        >>> device_to_optimized(540, 960, (1080, 1920), (704, 1248))
        (352, 624)
    """
    device_width, device_height = device_dimensions
    optimized_width, optimized_height = optimized_dimensions

    scale_x = optimized_width / device_width
    scale_y = optimized_height / device_height

    opt_x = int(device_x * scale_x)
    opt_y = int(device_y * scale_y)

    if validate:
        _validate_optimized_coords(opt_x, opt_y, optimized_dimensions)

    return (opt_x, opt_y)


def optimized_to_device(
    optimized_x: int,
    optimized_y: int,
    device_dimensions: Tuple[int, int],
    optimized_dimensions: Tuple[int, int]
) -> Tuple[int, int]:
    """
    Convert optimized image coordinates to device coordinates.

    Args:
        optimized_x: X coordinate in optimized space
        optimized_y: Y coordinate in optimized space
        device_dimensions: Device screen size (width, height), e.g., (1080, 1920)
        optimized_dimensions: Optimized image size (width, height), e.g., (704, 1248)

    Returns:
        Tuple of (device_x, device_y) clamped to device bounds

    Example:
        >>> optimized_to_device(352, 624, (1080, 1920), (704, 1248))
        (540, 960)
    """
    device_width, device_height = device_dimensions
    optimized_width, optimized_height = optimized_dimensions

    scale_x = device_width / optimized_width
    scale_y = device_height / optimized_height

    dev_x = int(optimized_x * scale_x)
    dev_y = int(optimized_y * scale_y)

    # Clamp to device bounds
    dev_x = max(0, min(dev_x, device_width - 1))
    dev_y = max(0, min(dev_y, device_height - 1))

    return (dev_x, dev_y)


def bounds_device_to_optimized(
    bounds: list,
    device_dimensions: Tuple[int, int],
    optimized_dimensions: Tuple[int, int]
) -> list:
    """
    Convert device bounds to optimized bounds.

    Args:
        bounds: Device bounds in format [[x1, y1], [x2, y2]]
        device_dimensions: Device screen size (width, height)
        optimized_dimensions: Optimized image size (width, height)

    Returns:
        Optimized bounds in format [[opt_x1, opt_y1], [opt_x2, opt_y2]]

    Example:
        >>> bounds_device_to_optimized([[100, 200], [500, 600]], (1080, 1920), (704, 1248))
        [[65, 130], [326, 390]]
    """
    if not bounds or len(bounds) != 2:
        return bounds

    x1, y1 = bounds[0]
    x2, y2 = bounds[1]

    opt_x1, opt_y1 = device_to_optimized(x1, y1, device_dimensions, optimized_dimensions)
    opt_x2, opt_y2 = device_to_optimized(x2, y2, device_dimensions, optimized_dimensions)

    return [[opt_x1, opt_y1], [opt_x2, opt_y2]]


def calculate_center_optimized(
    device_bounds: list,
    device_dimensions: Tuple[int, int],
    optimized_dimensions: Tuple[int, int]
) -> Tuple[int, int]:
    """
    Calculate center coordinates in optimized space from device bounds.

    Args:
        device_bounds: Device bounds [[x1, y1], [x2, y2]]
        device_dimensions: Device screen size (width, height)
        optimized_dimensions: Optimized image size (width, height)

    Returns:
        Center coordinates (center_x, center_y) in optimized space

    Example:
        >>> calculate_center_optimized([[100, 200], [500, 600]], (1080, 1920), (704, 1248))
        (195, 260)
    """
    if not device_bounds or len(device_bounds) != 2:
        return (0, 0)

    x1, y1 = device_bounds[0]
    x2, y2 = device_bounds[1]

    # Calculate center in device space first
    center_x_dev = (x1 + x2) // 2
    center_y_dev = (y1 + y2) // 2

    # Convert to optimized space
    return device_to_optimized(center_x_dev, center_y_dev, device_dimensions, optimized_dimensions)


def validate_optimized_coords(
    optimized_x: int,
    optimized_y: int,
    optimized_dimensions: Tuple[int, int]
) -> bool:
    """
    Validate that coordinates are within optimized image bounds.

    Args:
        optimized_x: X coordinate in optimized space
        optimized_y: Y coordinate in optimized space
        optimized_dimensions: Optimized image size (width, height)

    Returns:
        True if coordinates are valid

    Raises:
        ValueError: If coordinates are out of bounds

    Example:
        >>> validate_optimized_coords(352, 624, (704, 1248))
        True
    """
    _validate_optimized_coords(optimized_x, optimized_y, optimized_dimensions)
    return True


def get_scale_factors(
    device_dimensions: Tuple[int, int],
    optimized_dimensions: Tuple[int, int]
) -> dict:
    """
    Calculate scale factors for coordinate conversions.

    Args:
        device_dimensions: Device screen size (width, height)
        optimized_dimensions: Optimized image size (width, height)

    Returns:
        Dictionary with scale factors and dimension information

    Example:
        >>> get_scale_factors((1080, 1920), (704, 1248))
        {
            'to_optimized_x': 0.6519,
            'to_optimized_y': 0.65,
            'to_device_x': 1.5341,
            'to_device_y': 1.5385,
            ...
        }
    """
    device_width, device_height = device_dimensions
    optimized_width, optimized_height = optimized_dimensions

    return {
        "device": {
            "width": device_width,
            "height": device_height,
            "resolution": f"{device_width}x{device_height}"
        },
        "optimized": {
            "width": optimized_width,
            "height": optimized_height,
            "resolution": f"{optimized_width}x{optimized_height}"
        },
        "scales": {
            "to_optimized_x": optimized_width / device_width,
            "to_optimized_y": optimized_height / device_height,
            "to_device_x": device_width / optimized_width,
            "to_device_y": device_height / optimized_height
        }
    }


def _validate_optimized_coords(
    x: int,
    y: int,
    optimized_dimensions: Tuple[int, int]
):
    """
    Internal validation with detailed error message.

    Args:
        x: X coordinate in optimized space
        y: Y coordinate in optimized space
        optimized_dimensions: Optimized image size (width, height)

    Raises:
        ValueError: If coordinates are out of bounds
    """
    optimized_width, optimized_height = optimized_dimensions

    if not (0 <= x <= optimized_width):
        raise ValueError(
            f"X coordinate {x} out of optimized bounds "
            f"[0, {optimized_width}]"
        )

    if not (0 <= y <= optimized_height):
        raise ValueError(
            f"Y coordinate {y} out of optimized bounds "
            f"[0, {optimized_height}]"
        )
