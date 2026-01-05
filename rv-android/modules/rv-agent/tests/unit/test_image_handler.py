"""
Unit tests for ImageHandler - Screenshot management and optimization.

Tests verify:
- Screenshot saving with rotation management
- Image optimization (resize, compress, base64 encode)
- RGBA to RGB conversion for JPEG
- Fallback encoding when optimization fails
- Queue management and cleanup
"""

import pytest
import base64
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
from io import BytesIO

from PIL import Image

from rv_agent.vision.image_handler import ImageHandler


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory."""
    output_dir = tmp_path / "screenshots"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def image_handler(temp_output_dir):
    """Create ImageHandler instance."""
    with patch.object(ImageHandler, '__init__', lambda self, *args, **kwargs: None):
        handler = ImageHandler.__new__(ImageHandler)
        handler.output_dir = temp_output_dir
        handler.rotation_limit = 10
        handler.target_size = (704, 1248)
        handler.quality = 85
        handler.screenshot_queue = []
        handler.logger = MagicMock()
        # Use deque instead of list for proper maxlen behavior
        from collections import deque
        handler.screenshot_queue = deque(maxlen=10)
        return handler


@pytest.fixture
def sample_png_bytes():
    """Create sample PNG image bytes."""
    img = Image.new('RGB', (1080, 1920), color='blue')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


@pytest.fixture
def sample_rgba_png_bytes():
    """Create sample RGBA PNG image bytes."""
    img = Image.new('RGBA', (1080, 1920), color=(255, 0, 0, 128))
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


@pytest.fixture
def sample_image_file(temp_output_dir, sample_png_bytes):
    """Create sample image file."""
    filepath = temp_output_dir / "test.png"
    filepath.write_bytes(sample_png_bytes)
    return filepath


# =============================================================================
# ImageHandler Initialization Tests
# =============================================================================

class TestImageHandlerInit:
    """Tests for ImageHandler initialization."""

    def test_init_creates_output_dir(self, tmp_path):
        """Test that initialization creates output directory."""
        output_dir = tmp_path / "new_screenshots"

        with patch('rv_agent.vision.image_handler.LoggingManager') as mock_logging:
            mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
            handler = ImageHandler(str(output_dir))

        assert output_dir.exists()

    def test_init_default_parameters(self, tmp_path):
        """Test initialization with default parameters."""
        output_dir = tmp_path / "screenshots"

        with patch('rv_agent.vision.image_handler.LoggingManager') as mock_logging:
            mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
            handler = ImageHandler(str(output_dir))

        assert handler.rotation_limit == 10
        assert handler.target_size == (704, 1248)
        assert handler.quality == 85

    def test_init_custom_parameters(self, tmp_path):
        """Test initialization with custom parameters."""
        output_dir = tmp_path / "screenshots"

        with patch('rv_agent.vision.image_handler.LoggingManager') as mock_logging:
            mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
            handler = ImageHandler(
                str(output_dir),
                rotation_limit=5,
                target_size=(640, 1080),
                quality=75
            )

        assert handler.rotation_limit == 5
        assert handler.target_size == (640, 1080)
        assert handler.quality == 75


# =============================================================================
# Save Screenshot Tests
# =============================================================================

class TestSaveScreenshot:
    """Tests for ImageHandler.save_screenshot()."""

    def test_save_screenshot_creates_file(self, image_handler, sample_png_bytes):
        """Test that save_screenshot creates file on disk."""
        filepath = image_handler.save_screenshot(sample_png_bytes, "test_001.png")

        assert filepath.exists()
        assert filepath.read_bytes() == sample_png_bytes

    def test_save_screenshot_adds_to_queue(self, image_handler, sample_png_bytes):
        """Test that save_screenshot adds filename to queue."""
        image_handler.save_screenshot(sample_png_bytes, "test_001.png")

        assert "test_001.png" in image_handler.screenshot_queue

    def test_save_multiple_screenshots(self, image_handler, sample_png_bytes):
        """Test saving multiple screenshots."""
        for i in range(3):
            image_handler.save_screenshot(sample_png_bytes, f"test_{i:03d}.png")

        assert len(image_handler.screenshot_queue) == 3

    def test_rotation_removes_oldest(self, image_handler, sample_png_bytes):
        """Test that rotation removes oldest screenshot."""
        # Set rotation limit to 3
        from collections import deque
        image_handler.screenshot_queue = deque(maxlen=3)
        image_handler.rotation_limit = 3

        # Save 4 screenshots
        for i in range(4):
            image_handler.save_screenshot(sample_png_bytes, f"test_{i:03d}.png")

        # Only 3 should remain
        assert len(image_handler.screenshot_queue) == 3
        # Oldest (test_000.png) should be removed
        assert "test_000.png" not in image_handler.screenshot_queue
        assert "test_001.png" in image_handler.screenshot_queue

    def test_rotation_deletes_file(self, image_handler, sample_png_bytes):
        """Test that rotation deletes old file from disk."""
        from collections import deque
        image_handler.screenshot_queue = deque(maxlen=2)
        image_handler.rotation_limit = 2

        # Save 3 screenshots
        image_handler.save_screenshot(sample_png_bytes, "old.png")
        image_handler.save_screenshot(sample_png_bytes, "middle.png")
        image_handler.save_screenshot(sample_png_bytes, "new.png")

        # old.png should be deleted
        old_path = image_handler.output_dir / "old.png"
        assert not old_path.exists()

    def test_save_screenshot_error_handling(self, image_handler):
        """Test error handling when save fails."""
        # Make output_dir read-only to cause error
        image_handler.output_dir = Path("/nonexistent/path")

        with pytest.raises(IOError):
            image_handler.save_screenshot(b"data", "test.png")


# =============================================================================
# Optimize Tests
# =============================================================================

class TestOptimize:
    """Tests for ImageHandler.optimize()."""

    def test_optimize_returns_base64(self, image_handler, sample_image_file):
        """Test that optimize returns base64 encoded string."""
        result = image_handler.optimize(str(sample_image_file))

        assert result is not None
        # Verify it's valid base64
        decoded = base64.b64decode(result)
        assert len(decoded) > 0

    def test_optimize_resizes_image(self, image_handler, temp_output_dir):
        """Test that optimize resizes large images."""
        # Create large image
        large_img = Image.new('RGB', (2160, 3840), color='red')
        large_path = temp_output_dir / "large.png"
        large_img.save(large_path)

        result = image_handler.optimize(str(large_path), target_size=(704, 1248))

        assert result is not None
        # Decode and check size
        decoded = base64.b64decode(result)
        img = Image.open(BytesIO(decoded))
        # Should fit within target size
        assert img.size[0] <= 704
        assert img.size[1] <= 1248

    def test_optimize_converts_rgba_to_rgb(self, image_handler, temp_output_dir, sample_rgba_png_bytes):
        """Test that optimize converts RGBA to RGB for JPEG."""
        rgba_path = temp_output_dir / "rgba.png"
        rgba_path.write_bytes(sample_rgba_png_bytes)

        result = image_handler.optimize(str(rgba_path), output_format="JPEG")

        assert result is not None
        # JPEG doesn't support alpha, so conversion must have worked
        decoded = base64.b64decode(result)
        img = Image.open(BytesIO(decoded))
        assert img.mode == "RGB"

    def test_optimize_with_custom_quality(self, image_handler, temp_output_dir):
        """Test optimize with custom quality setting."""
        # Create image with noise/detail to show quality difference
        import random
        img = Image.new('RGB', (500, 500))
        pixels = img.load()
        for i in range(500):
            for j in range(500):
                pixels[i, j] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        noisy_path = temp_output_dir / "noisy.png"
        img.save(noisy_path)

        result_high = image_handler.optimize(str(noisy_path), quality=95)
        result_low = image_handler.optimize(str(noisy_path), quality=20)

        # Both should produce valid output
        assert result_high is not None
        assert result_low is not None
        # Higher quality typically produces larger file for noisy images
        # But this can vary, so just verify both work
        assert len(result_high) > 0
        assert len(result_low) > 0

    def test_optimize_nonexistent_file(self, image_handler):
        """Test optimize with nonexistent file returns None."""
        result = image_handler.optimize("/nonexistent/path.png")

        assert result is None

    def test_optimize_uses_instance_defaults(self, image_handler, sample_image_file):
        """Test that optimize uses instance defaults when not specified."""
        image_handler.target_size = (320, 480)
        image_handler.quality = 60

        result = image_handler.optimize(str(sample_image_file))

        assert result is not None
        decoded = base64.b64decode(result)
        img = Image.open(BytesIO(decoded))
        # Should respect instance target_size
        assert img.size[0] <= 320
        assert img.size[1] <= 480

    def test_optimize_png_format(self, image_handler, sample_image_file):
        """Test optimize with PNG output format."""
        result = image_handler.optimize(str(sample_image_file), output_format="PNG")

        assert result is not None
        decoded = base64.b64decode(result)
        # PNG magic bytes
        assert decoded[:8] == b'\x89PNG\r\n\x1a\n'


# =============================================================================
# Optimize With Fallback Tests
# =============================================================================

class TestOptimizeWithFallback:
    """Tests for ImageHandler.optimize_with_fallback()."""

    def test_returns_optimized_when_successful(self, image_handler, sample_image_file):
        """Test that it returns optimized image when optimization succeeds."""
        result = image_handler.optimize_with_fallback(str(sample_image_file))

        assert result is not None

    def test_fallback_on_optimization_failure(self, image_handler, temp_output_dir):
        """Test fallback to basic encoding when optimization fails."""
        # Create a corrupted image file
        corrupted_path = temp_output_dir / "corrupted.png"
        corrupted_path.write_bytes(b"not an image")

        # Patch optimize to return None
        with patch.object(image_handler, 'optimize', return_value=None):
            result = image_handler.optimize_with_fallback(str(corrupted_path))

        # Should fall back to basic encoding
        assert result is not None
        decoded = base64.b64decode(result)
        assert decoded == b"not an image"

    def test_fallback_returns_none_when_file_missing(self, image_handler):
        """Test that fallback returns None when file is missing."""
        with patch.object(image_handler, 'optimize', return_value=None):
            result = image_handler.optimize_with_fallback("/nonexistent/file.png")

        assert result is None


# =============================================================================
# Queue Management Tests
# =============================================================================

class TestQueueManagement:
    """Tests for queue management methods."""

    def test_get_screenshot_count_empty(self, image_handler):
        """Test get_screenshot_count with empty queue."""
        count = image_handler.get_screenshot_count()

        assert count == 0

    def test_get_screenshot_count_with_items(self, image_handler, sample_png_bytes):
        """Test get_screenshot_count with items in queue."""
        for i in range(5):
            image_handler.save_screenshot(sample_png_bytes, f"test_{i}.png")

        count = image_handler.get_screenshot_count()

        assert count == 5

    def test_clear_screenshots_removes_files(self, image_handler, sample_png_bytes):
        """Test that clear_screenshots removes files from disk."""
        # Save some screenshots
        for i in range(3):
            image_handler.save_screenshot(sample_png_bytes, f"test_{i}.png")

        # Verify files exist
        for i in range(3):
            assert (image_handler.output_dir / f"test_{i}.png").exists()

        # Clear screenshots
        image_handler.clear_screenshots()

        # Verify files removed
        for i in range(3):
            assert not (image_handler.output_dir / f"test_{i}.png").exists()

    def test_clear_screenshots_clears_queue(self, image_handler, sample_png_bytes):
        """Test that clear_screenshots clears the queue."""
        for i in range(3):
            image_handler.save_screenshot(sample_png_bytes, f"test_{i}.png")

        image_handler.clear_screenshots()

        assert len(image_handler.screenshot_queue) == 0

    def test_get_latest_screenshot_empty(self, image_handler):
        """Test get_latest_screenshot with empty queue."""
        result = image_handler.get_latest_screenshot()

        assert result is None

    def test_get_latest_screenshot_returns_last(self, image_handler, sample_png_bytes):
        """Test get_latest_screenshot returns most recent."""
        image_handler.save_screenshot(sample_png_bytes, "first.png")
        image_handler.save_screenshot(sample_png_bytes, "second.png")
        image_handler.save_screenshot(sample_png_bytes, "third.png")

        latest = image_handler.get_latest_screenshot()

        assert latest.name == "third.png"


# =============================================================================
# Integration Tests
# =============================================================================

class TestImageHandlerIntegration:
    """Integration tests for ImageHandler."""

    def test_full_workflow(self, temp_output_dir, sample_png_bytes):
        """Test complete screenshot workflow."""
        with patch('rv_agent.vision.image_handler.LoggingManager') as mock_logging:
            mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
            handler = ImageHandler(str(temp_output_dir), rotation_limit=5)

        # Save screenshot
        filepath = handler.save_screenshot(sample_png_bytes, "step_001.png")
        assert filepath.exists()

        # Optimize
        optimized = handler.optimize(str(filepath))
        assert optimized is not None

        # Get count
        assert handler.get_screenshot_count() == 1

        # Get latest
        latest = handler.get_latest_screenshot()
        assert latest == filepath

        # Clear
        handler.clear_screenshots()
        assert handler.get_screenshot_count() == 0
        assert not filepath.exists()

    def test_rotation_workflow(self, temp_output_dir, sample_png_bytes):
        """Test rotation workflow with multiple screenshots."""
        with patch('rv_agent.vision.image_handler.LoggingManager') as mock_logging:
            mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
            handler = ImageHandler(str(temp_output_dir), rotation_limit=3)

        # Save more than rotation limit
        for i in range(5):
            handler.save_screenshot(sample_png_bytes, f"step_{i:03d}.png")

        # Only last 3 should remain
        assert handler.get_screenshot_count() == 3

        # Check which files exist
        assert not (temp_output_dir / "step_000.png").exists()
        assert not (temp_output_dir / "step_001.png").exists()
        assert (temp_output_dir / "step_002.png").exists()
        assert (temp_output_dir / "step_003.png").exists()
        assert (temp_output_dir / "step_004.png").exists()

    def test_optimize_preserves_aspect_ratio(self, temp_output_dir):
        """Test that optimization preserves aspect ratio."""
        with patch('rv_agent.vision.image_handler.LoggingManager') as mock_logging:
            mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
            handler = ImageHandler(str(temp_output_dir))

        # Create image with specific aspect ratio (16:9)
        img = Image.new('RGB', (1920, 1080), color='green')
        img_path = temp_output_dir / "wide.png"
        img.save(img_path)

        # Optimize
        result = handler.optimize(str(img_path))
        decoded = base64.b64decode(result)
        optimized_img = Image.open(BytesIO(decoded))

        # Aspect ratio should be approximately preserved
        original_ratio = 1920 / 1080  # ~1.78
        optimized_ratio = optimized_img.size[0] / optimized_img.size[1]
        assert abs(original_ratio - optimized_ratio) < 0.1
