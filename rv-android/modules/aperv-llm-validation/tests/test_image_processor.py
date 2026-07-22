"""Tests for aperv_llm_validation.pipeline.image_processor.

Validates that calculate_resized_dimensions matches Java's ImageProcessor output
and that process_screenshot_bytes produces valid base64-encoded JPEG.
"""

from __future__ import annotations

import base64
import io

import pytest
from PIL import Image

from aperv_llm_validation.pipeline.image_processor import (
    calculate_resized_dimensions,
    process_screenshot_bytes,
    smart_resize,
)


# ---------------------------------------------------------------------------
# calculate_resized_dimensions — must match Java ImageProcessor exactly
# ---------------------------------------------------------------------------


class TestCalculateResizedDimensions:
    """Port of Java ImageProcessorTest for calculateResizedDimensions."""

    def test_portrait_1080x1920_resized_to_562x1000(self):
        """1080x1920 portrait: longest edge 1920 -> 1000, width scales to 562."""
        assert calculate_resized_dimensions(1080, 1920, 1000) == (562, 1000)

    def test_landscape_1920x1080_resized_to_1000x562(self):
        """1920x1080 landscape: longest edge 1920 -> 1000, height scales to 562."""
        assert calculate_resized_dimensions(1920, 1080, 1000) == (1000, 562)

    def test_800x600_no_resize_needed(self):
        """800x600 already fits within 1000px — returned unchanged."""
        assert calculate_resized_dimensions(800, 600, 1000) == (800, 600)

    def test_zero_dimensions_raises_value_error(self):
        """Zero dimensions are invalid and must raise ValueError."""
        with pytest.raises(ValueError):
            calculate_resized_dimensions(0, 0, 1000)

    def test_zero_width_raises_value_error(self):
        with pytest.raises(ValueError):
            calculate_resized_dimensions(0, 1920, 1000)

    def test_zero_height_raises_value_error(self):
        with pytest.raises(ValueError):
            calculate_resized_dimensions(1080, 0, 1000)

    def test_zero_max_edge_raises_value_error(self):
        with pytest.raises(ValueError):
            calculate_resized_dimensions(1080, 1920, 0)

    def test_square_2000x2000_resized_to_1000x1000(self):
        """Square image larger than max: both sides capped at 1000."""
        assert calculate_resized_dimensions(2000, 2000, 1000) == (1000, 1000)

    def test_exactly_max_edge_unchanged(self):
        """1000x500 — longest edge == max_edge, no resize needed."""
        assert calculate_resized_dimensions(1000, 500, 1000) == (1000, 500)

    def test_aspect_ratio_landscape_2000x1000(self):
        """2000x1000 -> scale 0.5 -> 1000x500."""
        assert calculate_resized_dimensions(2000, 1000, 1000) == (1000, 500)

    def test_aspect_ratio_portrait_500x2000(self):
        """500x2000 -> scale 0.5 -> 250x1000."""
        assert calculate_resized_dimensions(500, 2000, 1000) == (250, 1000)

    def test_returns_tuple_of_two_ints(self):
        result = calculate_resized_dimensions(1080, 1920, 1000)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert all(isinstance(v, int) for v in result)


# ---------------------------------------------------------------------------
# smart_resize — Qwen3-VL optimized
# ---------------------------------------------------------------------------


class TestSmartResize:
    """Validate Qwen3-VL smart_resize constraints."""

    def test_1920x1080_divisible_by_32(self):
        new_h, new_w = smart_resize(1920, 1080, factor=32)
        assert new_h % 32 == 0
        assert new_w % 32 == 0

    def test_1080x1920_divisible_by_32(self):
        new_h, new_w = smart_resize(1080, 1920, factor=32)
        assert new_h % 32 == 0
        assert new_w % 32 == 0

    def test_area_within_bounds(self):
        """Output area must be within [min_pixels, max_pixels]."""
        new_h, new_w = smart_resize(1920, 1080, factor=32)
        area = new_h * new_w
        assert area >= 3136, f"Area {area} below min_pixels"
        assert area <= 10_035_200, f"Area {area} above max_pixels"

    def test_small_image_scaled_up(self):
        """Very small image should be scaled up to meet min_pixels."""
        new_h, new_w = smart_resize(10, 10, factor=32)
        assert new_h % 32 == 0
        assert new_w % 32 == 0
        assert new_h * new_w >= 3136

    def test_huge_image_scaled_down(self):
        """Very large image should be scaled down to meet max_pixels."""
        new_h, new_w = smart_resize(10000, 10000, factor=32)
        assert new_h % 32 == 0
        assert new_w % 32 == 0
        assert new_h * new_w <= 10_035_200

    def test_zero_raises_value_error(self):
        with pytest.raises(ValueError):
            smart_resize(0, 1080, factor=32)


# ---------------------------------------------------------------------------
# process_screenshot_bytes — end-to-end encoding
# ---------------------------------------------------------------------------


def _make_test_png(width: int = 100, height: int = 200) -> bytes:
    """Create a minimal test PNG in memory."""
    img = Image.new("RGB", (width, height), color=(128, 64, 32))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestProcessScreenshotBytes:
    """Validate that process_screenshot_bytes produces valid base64 JPEG."""

    def test_produces_valid_base64(self):
        png_bytes = _make_test_png()
        result = process_screenshot_bytes(png_bytes, mode="max_edge")
        # Must decode without error
        decoded = base64.b64decode(result)
        assert len(decoded) > 0

    def test_no_data_uri_prefix(self):
        png_bytes = _make_test_png()
        result = process_screenshot_bytes(png_bytes, mode="max_edge")
        assert not result.startswith("data:")

    def test_output_is_valid_jpeg(self):
        png_bytes = _make_test_png()
        result = process_screenshot_bytes(png_bytes, mode="max_edge")
        jpeg_bytes = base64.b64decode(result)
        img = Image.open(io.BytesIO(jpeg_bytes))
        assert img.format == "JPEG"

    def test_max_edge_resizes_large_image(self):
        """1200x2400 image should be resized so longest edge <= 1000."""
        png_bytes = _make_test_png(1200, 2400)
        result = process_screenshot_bytes(png_bytes, mode="max_edge")
        jpeg_bytes = base64.b64decode(result)
        img = Image.open(io.BytesIO(jpeg_bytes))
        assert max(img.width, img.height) <= 1000

    def test_raw_mode_no_resize(self):
        """Raw mode should preserve original dimensions."""
        png_bytes = _make_test_png(1200, 2400)
        result = process_screenshot_bytes(png_bytes, mode="raw")
        jpeg_bytes = base64.b64decode(result)
        img = Image.open(io.BytesIO(jpeg_bytes))
        assert img.width == 1200
        assert img.height == 2400

    def test_smart_resize_mode(self):
        png_bytes = _make_test_png(1080, 1920)
        result = process_screenshot_bytes(png_bytes, mode="smart_resize")
        jpeg_bytes = base64.b64decode(result)
        img = Image.open(io.BytesIO(jpeg_bytes))
        assert img.width % 32 == 0
        assert img.height % 32 == 0

    def test_empty_bytes_raises(self):
        with pytest.raises(ValueError):
            process_screenshot_bytes(b"", mode="max_edge")

    def test_unknown_mode_raises(self):
        png_bytes = _make_test_png()
        with pytest.raises(ValueError, match="Unknown resize mode"):
            process_screenshot_bytes(png_bytes, mode="unknown")
