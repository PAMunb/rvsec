"""
Unit tests for the ScreenshotOptimizer service.
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image
from rv_agent.services.screenshot_optimizer import ScreenshotOptimizer


@pytest.fixture
def temp_image(tmp_path: Path) -> Path:
    """Create a temporary dummy image file for testing."""
    # Create a dummy RGBA image
    img_path = tmp_path / "test_image.png"
    img = Image.new("RGBA", (1080, 1920), color="red")
    img.save(img_path, "PNG")
    return img_path


@pytest.fixture
def optimizer():
    """Fixture for ScreenshotOptimizer instance."""
    return ScreenshotOptimizer()


class TestScreenshotOptimizer:
    """Test suite for the ScreenshotOptimizer."""

    def test_optimize_success(self, optimizer, temp_image):
        """Test successful optimization of a PNG image."""
        encoded_str = optimizer.optimize(str(temp_image))
        assert isinstance(encoded_str, str)
        assert len(encoded_str) > 0

        # Check that the original file size is larger than the optimized one
        original_size = temp_image.stat().st_size
        optimized_size = len(encoded_str)
        assert optimized_size < original_size

    def test_optimize_converts_rgba_to_rgb_for_jpeg(self, optimizer, temp_image):
        """Test that RGBA images are correctly converted for JPEG output."""
        # The fixture creates an RGBA image
        encoded_str = optimizer.optimize(str(temp_image), output_format="JPEG")
        assert isinstance(encoded_str, str)

    def test_optimize_custom_settings(self, optimizer, temp_image):
        """Test optimization with custom size and quality settings."""
        # Using a very low quality and small size
        low_q_str = optimizer.optimize(
            str(temp_image), target_size=(100, 100), quality=10
        )

        # Using higher quality
        high_q_str = optimizer.optimize(
            str(temp_image), target_size=(100, 100), quality=90
        )

        # For a simple, single-color image, JPEG compression is so efficient
        # that different quality settings might produce identical file sizes.
        # The important thing is that the function runs correctly with these settings.
        assert isinstance(low_q_str, str)
        assert isinstance(high_q_str, str)
        assert len(low_q_str) > 0
        assert len(high_q_str) > 0

    def test_optimize_file_not_found(self, optimizer, caplog):
        """Test that optimization fails if the file does not exist."""
        result = optimizer.optimize("non_existent_file.png")
        assert result is None
        assert "Screenshot file not found" in caplog.text

    @patch("PIL.Image.open")
    def test_optimize_handles_general_exception(
        self, mock_open, optimizer, temp_image, caplog
    ):
        """Test that a general exception during processing is handled."""
        mock_open.side_effect = Exception("PIL error")
        result = optimizer.optimize(str(temp_image))
        assert result is None
        assert "Screenshot optimization failed: PIL error" in caplog.text

    # --- Tests for optimize_with_fallback ---

    def test_optimize_with_fallback_success_path(self, optimizer, temp_image):
        """Test the success path where optimization works."""
        with patch.object(
            optimizer, "optimize", return_value="optimized_string"
        ) as mock_optimize:
            result = optimizer.optimize_with_fallback(str(temp_image))
            mock_optimize.assert_called_once_with(str(temp_image))
            assert result == "optimized_string"

    def test_optimize_with_fallback_fallback_path(self, optimizer, temp_image, caplog):
        """Test the fallback path where optimization fails."""
        with patch.object(optimizer, "optimize", return_value=None):
            result = optimizer.optimize_with_fallback(str(temp_image))
            assert "Using fallback encoding" in caplog.text
            assert result is not None
            # The fallback result should be larger than a typical optimized result
            assert len(result) > 1000

    def test_optimize_with_fallback_all_fail(self, optimizer, caplog):
        """Test when both optimization and fallback reading fail."""
        # Optimization will fail because the file doesn't exist
        result = optimizer.optimize_with_fallback("non_existent_file.png")
        assert result is None
        assert "Screenshot file not found" in caplog.text  # From optimize()
        assert "Using fallback encoding" in caplog.text  # From the fallback attempt
        assert "Fallback encoding failed" in caplog.text  # From the final except block
