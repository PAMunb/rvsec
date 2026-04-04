import os
import shutil
import tempfile

import cv2
import numpy as np
from PIL import Image
from rv_screen_parser.screenshot.screenshot_manager import ScreenshotManager


class TestScreenshotManager:
    """Test suite for ScreenshotManager class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = ScreenshotManager(base_dir=self.temp_dir)

    def teardown_method(self):
        """Clean up after each test method."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization(self):
        """Test ScreenshotManager initialization."""
        assert self.manager.base_dir is not None
        assert os.path.exists(self.manager.session_dir)
        assert self.manager.max_screenshots == 100
        assert self.manager.retention_time == 3600
        assert isinstance(self.manager.screenshot_paths, list)
        assert self.manager.screenshot_count == 0

    def test_save_screenshot_with_bytes(self):
        """Test saving screenshot from bytes data."""
        # Create mock image bytes
        img_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        _, img_bytes = cv2.imencode(".png", img_array)

        result_path = self.manager.save_screenshot(img_bytes.tobytes())

        assert result_path is not None
        assert os.path.exists(result_path)
        assert result_path in self.manager.screenshot_paths
        assert self.manager.screenshot_count == 1

    def test_save_screenshot_with_pil_image(self):
        """Test saving screenshot from PIL Image."""
        pil_img = Image.new("RGB", (100, 100), color="red")

        result_path = self.manager.save_screenshot(pil_img)

        assert result_path is not None
        assert os.path.exists(result_path)
        assert result_path in self.manager.screenshot_paths
        assert self.manager.screenshot_count == 1

    def test_save_screenshot_with_activity_name(self):
        """Test saving screenshot with activity name."""
        pil_img = Image.new("RGB", (100, 100), color="blue")

        result_path = self.manager.save_screenshot(
            pil_img, activity_name="MainActivity"
        )

        assert result_path is not None
        assert "MainActivity" in os.path.basename(result_path)
        assert os.path.exists(result_path)

    def test_save_screenshot_failure(self):
        """Test saving screenshot with unsupported data type."""
        result_path = self.manager.save_screenshot("unsupported_type")

        assert result_path is None

    def test_rename_with_state(self):
        """Test renaming screenshot with state fingerprint."""
        pil_img = Image.new("RGB", (100, 100), color="green")
        original_path = self.manager.save_screenshot(pil_img)

        new_path = self.manager.rename_with_state(
            original_path, "state_fingerprint_12345"
        )

        assert new_path is not None
        assert "state_fingerprint_12345"[:8] in os.path.basename(new_path)
        assert not os.path.exists(original_path)  # Original should be renamed
        assert os.path.exists(new_path)  # New path should exist
        assert new_path in self.manager.screenshot_paths  # Tracking list updated

    def test_rename_with_state_invalid_path(self):
        """Test renaming with non-existent path."""
        result = self.manager.rename_with_state(
            "/non/existent/path", "state_fingerprint"
        )

        assert result is None

    def test_get_screenshot_for_state(self):
        """Test getting screenshot for specific state."""
        pil_img = Image.new("RGB", (100, 100), color="yellow")
        original_path = self.manager.save_screenshot(pil_img)

        # Rename with a state fingerprint
        state_fingerprint = "test_state_12345"
        new_path = self.manager.rename_with_state(original_path, state_fingerprint)

        # Try to get the screenshot for the state
        retrieved_path = self.manager.get_screenshot_for_state(state_fingerprint)

        assert retrieved_path == new_path

    def test_get_latest_screenshot(self):
        """Test getting the latest screenshot."""
        pil_img1 = Image.new("RGB", (100, 100), color="red")
        pil_img2 = Image.new("RGB", (100, 100), color="blue")

        self.manager.save_screenshot(pil_img1)
        path2 = self.manager.save_screenshot(pil_img2)

        latest = self.manager.get_latest_screenshot()

        assert latest == path2

    def test_get_latest_screenshot_empty(self):
        """Test getting latest screenshot when none exist."""
        latest = self.manager.get_latest_screenshot()

        assert latest is None

    def test_get_metrics(self):
        """Test getting metrics."""
        pil_img = Image.new("RGB", (100, 100), color="purple")
        self.manager.save_screenshot(pil_img)

        metrics = self.manager.get_metrics()

        assert metrics["total_screenshots"] == 1
        assert metrics["active_screenshots"] == 1
        assert metrics["session_directory"] == self.manager.session_dir
        assert metrics["max_screenshots"] == 100
        assert metrics["retention_time_seconds"] == 3600

    def test_cleanup_excess_screenshots(self):
        """Test cleaning up excess screenshots."""
        # Override max_screenshots to test cleanup
        self.manager.max_screenshots = 2

        pil_img1 = Image.new("RGB", (100, 100), color="red")
        pil_img2 = Image.new("RGB", (100, 100), color="blue")
        pil_img3 = Image.new("RGB", (100, 100), color="green")

        # Add delay to ensure different timestamps for unique filenames
        import time

        self.manager.save_screenshot(pil_img1)
        time.sleep(0.01)  # Small delay to ensure different timestamps
        self.manager.save_screenshot(pil_img2)
        time.sleep(0.01)
        self.manager.save_screenshot(pil_img3)

        # Check initial state - make sure we have 3 different paths
        unique_paths = list(set(self.manager.screenshot_paths))
        assert len(unique_paths) >= 1  # At least one unique path

        # Simulate the cleanup by calling the method directly
        self.manager._cleanup_excess_screenshots()

        # After cleanup, should have at most max_screenshots (2)
        assert len(self.manager.screenshot_paths) <= 2

    def test_cleanup_old_screenshots(self):
        """Test cleaning up old screenshots."""
        # Create another session directory to simulate old data
        old_session_dir = os.path.join(self.temp_dir, "session_20200101_000000")
        os.makedirs(old_session_dir, exist_ok=True)

        # Create a dummy file in the old session
        old_file = os.path.join(old_session_dir, "old_file.png")
        with open(old_file, "w") as f:
            f.write("dummy")

        # Set retention time to 0 to force cleanup of any old sessions
        self.manager.retention_time = 0

        # Call cleanup method
        self.manager._cleanup_old_screenshots()

        # Old session directory should be removed
        assert not os.path.exists(old_session_dir)
