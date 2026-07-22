"""Coordinate normalization between Qwen3-VL [0, 1000) space and device pixels.

Replicates the behavior of APE's CoordinateNormalizer.java (commit b2852dd).
Qwen3-VL returns tap coordinates normalized to [0, 1000) regardless of device
resolution. This module converts between that space and pixel coordinates.

Reference: https://github.com/QwenLM/Qwen3-VL/issues/1486
"""

from __future__ import annotations

from aperv_llm_validation.constants import (
    DEVICE_HEIGHT,
    DEVICE_WIDTH,
    QWEN_COORD_RANGE,
)


def qwen_to_pixel(
    qwen_x: int,
    qwen_y: int,
    device_w: int = DEVICE_WIDTH,
    device_h: int = DEVICE_HEIGHT,
) -> tuple[int, int]:
    """Convert Qwen3-VL normalized coordinates to device pixel coordinates.

    Uses the same formula as Java's CoordinateNormalizer.normalize():
        pixel = int((qwen / 1000.0) * device_dim)
    with clamping to [0, device_dim - 1].
    """
    pixel_x = int((qwen_x / float(QWEN_COORD_RANGE)) * device_w)
    pixel_y = int((qwen_y / float(QWEN_COORD_RANGE)) * device_h)

    pixel_x = max(0, min(pixel_x, device_w - 1))
    pixel_y = max(0, min(pixel_y, device_h - 1))

    return (pixel_x, pixel_y)


def pixel_to_qwen(
    pixel_x: int,
    pixel_y: int,
    device_w: int = DEVICE_WIDTH,
    device_h: int = DEVICE_HEIGHT,
) -> tuple[int, int]:
    """Convert device pixel coordinates to Qwen3-VL normalized [0, 1000) space.

    Inverse of qwen_to_pixel. Result clamped to [0, 999].
    """
    qwen_x = int((pixel_x / device_w) * QWEN_COORD_RANGE)
    qwen_y = int((pixel_y / device_h) * QWEN_COORD_RANGE)

    qwen_x = max(0, min(qwen_x, QWEN_COORD_RANGE - 1))
    qwen_y = max(0, min(qwen_y, QWEN_COORD_RANGE - 1))

    return (qwen_x, qwen_y)
