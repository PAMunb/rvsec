"""Image processing pipeline — resize and encode screenshots for LLM consumption.

Replicates the behavior of APE's ImageProcessor.java (commit b2852dd) with an
additional smart_resize mode optimized for Qwen3-VL's vision encoder.
"""

from __future__ import annotations

import base64
import io
import math
from pathlib import Path

from PIL import Image

from aperv_llm_validation.constants import (
    JPEG_QUALITY,
    MAX_EDGE_PX,
    SMART_RESIZE_FACTOR,
    SMART_RESIZE_MAX_PIXELS,
    SMART_RESIZE_MIN_PIXELS,
)


def calculate_resized_dimensions(
    orig_w: int, orig_h: int, max_edge: int = MAX_EDGE_PX
) -> tuple[int, int]:
    """Calculate new dimensions preserving aspect ratio with longest edge <= max_edge.

    Replicates Java's ImageProcessor.calculateResizedDimensions() behavior:
    if both dimensions already fit, returns original size unchanged.

    Raises ValueError for zero or negative dimensions (Python-idiomatic guard
    replacing Java's silent pass-through on invalid input).
    """
    if orig_w <= 0 or orig_h <= 0:
        raise ValueError(
            f"Dimensions must be positive: got ({orig_w}, {orig_h})"
        )
    if max_edge <= 0:
        raise ValueError(f"max_edge must be positive: got {max_edge}")

    if orig_w <= max_edge and orig_h <= max_edge:
        return (orig_w, orig_h)

    scale = max_edge / max(orig_w, orig_h)
    new_w = max(1, round(orig_w * scale))
    new_h = max(1, round(orig_h * scale))
    return (new_w, new_h)


def smart_resize(
    height: int,
    width: int,
    factor: int = SMART_RESIZE_FACTOR,
    min_pixels: int = SMART_RESIZE_MIN_PIXELS,
    max_pixels: int = SMART_RESIZE_MAX_PIXELS,
) -> tuple[int, int]:
    """Qwen3-VL optimized resize: dimensions divisible by factor, area in [min, max].

    The vision encoder patches images into factor x factor blocks. Dimensions that
    are exact multiples of factor avoid padding waste and produce deterministic
    token counts.

    Returns (new_height, new_width) — note height-first order matching the
    convention used by Qwen3-VL's preprocessor.
    """
    if height <= 0 or width <= 0:
        raise ValueError(
            f"Dimensions must be positive: got ({height}, {width})"
        )

    # If current area exceeds max, scale down preserving aspect ratio
    area = height * width
    if area > max_pixels:
        scale = math.sqrt(max_pixels / area)
        height = int(height * scale)
        width = int(width * scale)

    # If current area is below min, scale up preserving aspect ratio
    area = height * width
    if area < min_pixels:
        scale = math.sqrt(min_pixels / area)
        height = int(math.ceil(height * scale))
        width = int(math.ceil(width * scale))

    # Round to nearest multiple of factor
    new_h = max(factor, round(height / factor) * factor)
    new_w = max(factor, round(width / factor) * factor)

    # Rounding up can push area above max — if so, round down instead
    if new_h * new_w > max_pixels:
        new_h = max(factor, (height // factor) * factor)
        new_w = max(factor, (width // factor) * factor)

    return (new_h, new_w)


def process_screenshot_with_dims(
    png_path: str | Path, mode: str = "max_edge"
) -> tuple[str, int, int]:
    """Read PNG, resize, JPEG quality 80, return (base64, resized_width, resized_height)."""
    png_path = Path(png_path)
    png_bytes = png_path.read_bytes()
    return process_screenshot_bytes_with_dims(png_bytes, mode=mode)


def process_screenshot(
    png_path: str | Path, mode: str = "max_edge"
) -> str:
    """Read a PNG file, resize, compress to JPEG, and return base64 string.

    Args:
        png_path: path to the PNG screenshot file
        mode: "max_edge" (longest edge <= 1000), "smart_resize" (Qwen3-VL
              optimized), or "raw" (no resize, just JPEG compress + encode)

    Returns:
        Base64-encoded JPEG string (no data URI prefix).
    """
    png_path = Path(png_path)
    png_bytes = png_path.read_bytes()
    return process_screenshot_bytes(png_bytes, mode=mode)


def process_screenshot_bytes(
    png_bytes: bytes, mode: str = "max_edge"
) -> str:
    """Resize and encode screenshot bytes to base64 JPEG.

    Args:
        png_bytes: raw PNG (or any Pillow-readable format) bytes
        mode: "max_edge", "smart_resize", or "raw"

    Returns:
        Base64-encoded JPEG string (no data URI prefix).

    Raises:
        ValueError: if png_bytes is empty or mode is unknown
    """
    if not png_bytes:
        raise ValueError("Input bytes must not be empty")

    img = Image.open(io.BytesIO(png_bytes))
    img = img.convert("RGB")  # JPEG requires RGB

    if mode == "max_edge":
        new_w, new_h = calculate_resized_dimensions(
            img.width, img.height, MAX_EDGE_PX
        )
        if (new_w, new_h) != (img.width, img.height):
            img = img.resize((new_w, new_h), Image.LANCZOS)

    elif mode == "smart_resize":
        new_h, new_w = smart_resize(img.height, img.width)
        if (new_w, new_h) != (img.width, img.height):
            img = img.resize((new_w, new_h), Image.LANCZOS)

    elif mode == "raw":
        pass  # no resize

    else:
        raise ValueError(f"Unknown resize mode: {mode!r}")

    # Compress to JPEG and base64-encode
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY)
    jpeg_bytes = buf.getvalue()

    return base64.b64encode(jpeg_bytes).decode("ascii")


def process_screenshot_bytes_with_dims(
    png_bytes: bytes, mode: str = "max_edge"
) -> tuple[str, int, int]:
    """Resize, encode, and return (base64, resized_width, resized_height)."""
    if not png_bytes:
        raise ValueError("Input bytes must not be empty")

    img = Image.open(io.BytesIO(png_bytes))
    img = img.convert("RGB")

    if mode == "max_edge":
        new_w, new_h = calculate_resized_dimensions(img.width, img.height, MAX_EDGE_PX)
        if (new_w, new_h) != (img.width, img.height):
            img = img.resize((new_w, new_h), Image.LANCZOS)
    elif mode == "smart_resize":
        new_h, new_w = smart_resize(img.height, img.width)
        if (new_w, new_h) != (img.width, img.height):
            img = img.resize((new_w, new_h), Image.LANCZOS)
    elif mode == "raw":
        pass
    else:
        raise ValueError(f"Unknown resize mode: {mode!r}")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY)
    jpeg_bytes = buf.getvalue()

    return base64.b64encode(jpeg_bytes).decode("ascii"), img.width, img.height
