"""
Screenshot capture and management utilities.

Provide screenshot file management including unique path generation, image
optimization (PNG to compressed JPEG), validation, and disk space cleanup.
Screenshot files use millisecond-precision timestamps for uniqueness.

### Integration Points:
    - UIAutomator2Adapter uses paths generated here for screenshot storage
    - rv-agent's vision strategy consumes screenshots for LLM analysis
    - cleanup_old_screenshots() prevents disk exhaustion during long experiments
"""

import os
import time
from pathlib import Path

from PIL import Image
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager

from ..constants import SCREENSHOT_DIR, SCREENSHOT_QUALITY


class ScreenshotManager:
    """
    Manages screenshot capture, processing, and storage.

    ### Architectural Decisions:
    - Provides centralized screenshot management
    - Handles file naming and organization
    - Supports image optimization and format conversion
    - Manages screenshot directory structure

    ### Role in the System:
    - Central screenshot handling for testing tools
    - Provides consistent screenshot naming and storage
    - Handles image processing for optimization
    - Supports debugging and analysis workflows
    """

    def __init__(self, screenshot_dir: str = SCREENSHOT_DIR):
        """Initialize screenshot manager and ensure storage directory exists.

        Args:
            screenshot_dir: Directory for storing screenshots. Created if absent.

        State:
            logger: Component logger with ScreenshotManager context.
            screenshot_dir: Path to the screenshot storage directory.
        """
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_uiautomator.utils.screenshot_manager",
            {CONTEXT_COMPONENT: "ScreenshotManager"},
        )

        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        self.logger.debug(
            f"ScreenshotManager initialized with directory: {screenshot_dir}"
        )

    @ErrorHandler.handle_errors(component="ScreenshotManager", phase="path_generation")
    def generate_screenshot_path(
        self, prefix: str = "screenshot", extension: str = "png"
    ) -> str:
        """
        Generate unique screenshot file path.

        Args:
            prefix: Filename prefix
            extension: File extension (without dot)

        Returns:
            Full path to screenshot file
        """
        timestamp = int(time.time() * 1000)  # Millisecond precision
        filename = f"{prefix}_{timestamp}.{extension}"
        return str(self.screenshot_dir / filename)

    @ErrorHandler.handle_errors(
        component="ScreenshotManager", phase="screenshot_optimization"
    )
    def optimize_screenshot(
        self, screenshot_path: str, quality: int = SCREENSHOT_QUALITY
    ) -> bool:
        """
        Optimize screenshot file size and quality.

        Args:
            screenshot_path: Path to screenshot file
            quality: JPEG quality (1-100) for compression

        Returns:
            True if optimization successful
        """
        try:
            if not Path(screenshot_path).exists():
                self.logger.error(f"Screenshot file not found: {screenshot_path}")
                return False

            # Open and optimize image
            with Image.open(screenshot_path) as img:
                # Convert to RGB if necessary (for JPEG)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                # Save with optimization
                optimized_path = screenshot_path.replace(".png", "_optimized.jpg")
                img.save(optimized_path, "JPEG", quality=quality, optimize=True)

                # Replace original if optimization successful
                if Path(optimized_path).exists():
                    os.remove(screenshot_path)
                    os.rename(optimized_path, screenshot_path.replace(".png", ".jpg"))
                    self.logger.debug(f"Screenshot optimized: {screenshot_path}")
                    return True

            return False

        except Exception as e:
            self.logger.error(
                f"Screenshot optimization failed for {screenshot_path}: {e}"
            )
            return False

    @ErrorHandler.handle_errors(
        component="ScreenshotManager", phase="screenshot_validation"
    )
    def validate_screenshot(self, screenshot_path: str) -> bool:
        """
        Validate that screenshot file is valid and accessible.

        Args:
            screenshot_path: Path to screenshot file

        Returns:
            True if screenshot is valid
        """
        try:
            screenshot_file = Path(screenshot_path)

            # Check file exists
            if not screenshot_file.exists():
                self.logger.warning(f"Screenshot file not found: {screenshot_path}")
                return False

            # Check file size
            file_size = screenshot_file.stat().st_size
            if file_size < 1024:  # Less than 1KB indicates likely corruption
                self.logger.warning(
                    f"Screenshot file too small ({file_size} bytes): {screenshot_path}"
                )
                return False

            # Try to open with PIL to validate image
            with Image.open(screenshot_path) as img:
                width, height = img.size
                if width < 100 or height < 100:
                    self.logger.warning(
                        f"Screenshot dimensions too small ({width}x{height}): {screenshot_path}"
                    )
                    return False

            self.logger.debug(f"Screenshot validation passed: {screenshot_path}")
            return True

        except Exception as e:
            self.logger.error(
                f"Screenshot validation failed for {screenshot_path}: {e}"
            )
            return False

    @ErrorHandler.handle_errors(
        component="ScreenshotManager", phase="screenshot_cleanup"
    )
    def cleanup_old_screenshots(self, max_age_hours: int = 24) -> int:
        """
        Clean up old screenshot files to manage disk space.

        Args:
            max_age_hours: Maximum age of screenshots to keep

        Returns:
            Number of files cleaned up
        """
        try:
            if not self.screenshot_dir.exists():
                return 0

            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            cleanup_count = 0

            for screenshot_file in self.screenshot_dir.glob("screenshot_*"):
                try:
                    file_age = current_time - screenshot_file.stat().st_mtime

                    if file_age > max_age_seconds:
                        screenshot_file.unlink()
                        cleanup_count += 1
                        self.logger.debug(
                            f"Cleaned up old screenshot: {screenshot_file}"
                        )

                except Exception as e:
                    self.logger.warning(f"Failed to clean up {screenshot_file}: {e}")

            if cleanup_count > 0:
                self.logger.info(f"Cleaned up {cleanup_count} old screenshots")

            return cleanup_count

        except Exception as e:
            self.logger.error(f"Screenshot cleanup failed: {e}")
            return 0
