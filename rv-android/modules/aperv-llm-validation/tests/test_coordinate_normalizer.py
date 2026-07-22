"""Tests for aperv_llm_validation.pipeline.coordinate_normalizer.

Validates that qwen_to_pixel matches Java's CoordinateNormalizer.normalize()
output and that pixel_to_qwen is a correct inverse.
"""

from __future__ import annotations

from aperv_llm_validation.pipeline.coordinate_normalizer import (
    pixel_to_qwen,
    qwen_to_pixel,
)


# ---------------------------------------------------------------------------
# qwen_to_pixel — must match Java CoordinateNormalizer.normalize() exactly
# ---------------------------------------------------------------------------


class TestQwenToPixel:
    """Port of Java CoordinateNormalizerTest."""

    def test_center_1080x1920(self):
        """(500, 500) on 1080x1920 -> (540, 960)."""
        assert qwen_to_pixel(500, 500, 1080, 1920) == (540, 960)

    def test_zero_coordinates(self):
        """(0, 0) -> (0, 0) on any device."""
        assert qwen_to_pixel(0, 0, 1080, 1920) == (0, 0)

    def test_max_valid_input_999(self):
        """(999, 999) on 1080x1920 -> (1079, 1918) — within bounds.

        Java: int(999/1000.0 * 1080) = int(1078.92) = 1078
               int(999/1000.0 * 1920) = int(1918.08) = 1918
        """
        px, py = qwen_to_pixel(999, 999, 1080, 1920)
        assert px == 1078
        assert py == 1918

    def test_clamping_over_1000(self):
        """Coordinates > 1000 are clamped to device bounds."""
        px, py = qwen_to_pixel(1500, 1500, 1080, 1920)
        assert px == 1079  # device_w - 1
        assert py == 1919  # device_h - 1

    def test_clamping_negative(self):
        """Negative coordinates are clamped to 0."""
        px, py = qwen_to_pixel(-10, -10, 1080, 1920)
        assert px == 0
        assert py == 0

    def test_different_device_720x1280(self):
        """(500, 500) on 720x1280 -> (360, 640)."""
        assert qwen_to_pixel(500, 500, 720, 1280) == (360, 640)

    def test_over_1000_clamped(self):
        """(1050, 1050) on 1080x1920 -> clamped to (1079, 1919)."""
        px, py = qwen_to_pixel(1050, 1050, 1080, 1920)
        assert px == 1079
        assert py == 1919

    def test_returns_tuple_of_two_ints(self):
        result = qwen_to_pixel(250, 750, 1080, 1920)
        assert isinstance(result, tuple)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# pixel_to_qwen — inverse conversion
# ---------------------------------------------------------------------------


class TestPixelToQwen:
    """Verify inverse conversion from pixels to Qwen coordinates."""

    def test_center_roundtrip(self):
        """(540, 960) on 1080x1920 -> (500, 500)."""
        assert pixel_to_qwen(540, 960, 1080, 1920) == (500, 500)

    def test_origin(self):
        assert pixel_to_qwen(0, 0, 1080, 1920) == (0, 0)

    def test_max_pixel_clamped_to_999(self):
        """Pixel at device edge should produce qwen < 1000."""
        qx, qy = pixel_to_qwen(1079, 1919, 1080, 1920)
        assert 0 <= qx <= 999
        assert 0 <= qy <= 999

    def test_clamping_beyond_device(self):
        """Pixels beyond device bounds are clamped to [0, 999]."""
        qx, qy = pixel_to_qwen(2000, 3000, 1080, 1920)
        assert qx == 999
        assert qy == 999
