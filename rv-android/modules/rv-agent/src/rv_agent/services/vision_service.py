"""
Image processing and screenshot management for vision-based agent operation.

This module provides utilities for capturing, optimizing, and managing screenshots
during Android application exploration with multimodal language models.
"""

import base64
import logging
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple
from collections import deque

from PIL import Image

from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT


class ImageHandler:
    """
    Manages screenshot capture, optimization, and rotation for vision model processing.

    ### Architectural Decisions:
    - Implements rotation-based screenshot management to control disk usage
    - Uses PIL for image processing with quality-preserving resizing
    - Provides JPEG compression with configurable quality settings
    - Maintains aspect ratio during resizing to preserve UI layout
    - Converts RGBA to RGB for smaller payload size

    ### Role in the System:
    - Captures and optimizes screenshots for multimodal LLM input
    - Manages screenshot storage with automatic rotation
    - Reduces token cost through image optimization
    - Provides base64 encoding for direct LLM consumption
    - Tracks screenshot history for debugging and analysis
    """

    # Image optimization defaults for Qwen3-VL (dimensions must be multiples of 32)
    DEFAULT_TARGET_SIZE = (704, 1248)  # 22×32 by 39×32, ~9:16 aspect ratio
    DEFAULT_QUALITY = 85
    DEFAULT_FORMAT = "JPEG"
    DEFAULT_ROTATION_LIMIT = 10

    def __init__(
        self,
        output_dir: str,
        rotation_limit: int = DEFAULT_ROTATION_LIMIT,
        target_size: Optional[Tuple[int, int]] = None,
        quality: Optional[int] = None,
    ):
        """
        Initialize image handler with output directory and rotation limit.

        Args:
            output_dir: Directory for screenshot storage
            rotation_limit: Maximum number of screenshots before rotation
            target_size: Target image size (width, height), defaults to (704, 1248)
            quality: JPEG compression quality (1-100), defaults to 85
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.rotation_limit = rotation_limit
        self.target_size = target_size or self.DEFAULT_TARGET_SIZE
        self.quality = quality or self.DEFAULT_QUALITY

        # Track screenshot filenames in rotation order
        self.screenshot_queue = deque(maxlen=rotation_limit)

        # Initialize logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_agent.image_handler", {CONTEXT_COMPONENT: "ImageHandler"}
        )

        self.logger.info(
            f"ImageHandler initialized: dir={output_dir}, "
            f"rotation={rotation_limit}, target_size={self.target_size}"
        )

    def save_screenshot(self, screenshot_data: bytes, filename: str) -> Path:
        """
        Save screenshot to disk with rotation management.

        Args:
            screenshot_data: Raw screenshot bytes
            filename: Screenshot filename (without directory)

        Returns:
            Path to saved screenshot file

        Raises:
            IOError: If screenshot cannot be saved
        """
        filepath = self.output_dir / filename

        try:
            # Save screenshot
            with open(filepath, "wb") as f:
                f.write(screenshot_data)

            # Add to rotation queue (automatically removes oldest if at limit)
            if len(self.screenshot_queue) >= self.rotation_limit:
                # Remove oldest screenshot
                oldest = self.screenshot_queue[0]
                oldest_path = self.output_dir / oldest
                if oldest_path.exists():
                    oldest_path.unlink()
                    self.logger.debug(f"Rotated out old screenshot: {oldest}")

            self.screenshot_queue.append(filename)

            self.logger.debug(
                f"Screenshot saved: {filename} "
                f"({len(screenshot_data):,} bytes, queue={len(self.screenshot_queue)})"
            )

            return filepath

        except Exception as e:
            self.logger.error(f"Failed to save screenshot {filename}: {e}")
            raise IOError(f"Screenshot save failed: {e}") from e

    def optimize(
        self,
        image_path: str,
        target_size: Optional[Tuple[int, int]] = None,
        quality: Optional[int] = None,
        output_format: str = DEFAULT_FORMAT,
    ) -> Optional[str]:
        """
        Optimize screenshot for vision model input.

        Args:
            image_path: Path to screenshot file
            target_size: Target (width, height) tuple, uses instance default if None
            quality: JPEG quality 1-100, uses instance default if None
            output_format: Output format (JPEG or PNG)

        Returns:
            Base64 encoded optimized image, or None if optimization fails
        """
        target_size = target_size or self.target_size
        quality = quality or self.quality

        try:
            img_path = Path(image_path)
            if not img_path.exists():
                self.logger.error(f"Screenshot file not found: {image_path}")
                return None

            original_size = img_path.stat().st_size

            # Load image
            img = Image.open(image_path)
            self.logger.debug(
                f"Loaded screenshot: {img.size[0]}x{img.size[1]}, mode={img.mode}"
            )

            # Convert RGBA to RGB for JPEG compression
            if img.mode == "RGBA" and output_format == "JPEG":
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
                self.logger.debug("Converted RGBA to RGB for JPEG compression")

            # Resize maintaining aspect ratio
            img.thumbnail(target_size, Image.Resampling.LANCZOS)
            self.logger.debug(f"Resized to: {img.size[0]}x{img.size[1]}")

            # Encode to bytes
            buffer = BytesIO()
            img.save(buffer, format=output_format, quality=quality, optimize=True)
            encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")

            # Log optimization metrics
            optimized_size = len(encoded)
            reduction = (1 - optimized_size / original_size) * 100

            self.logger.info(
                f"Screenshot optimized: {original_size:,} -> {optimized_size:,} bytes "
                f"({reduction:.1f}% reduction), dimensions: {img.size}"
            )

            return encoded

        except Exception as e:
            self.logger.error(f"Screenshot optimization failed: {e}", exc_info=True)
            return None

    def optimize_with_fallback(self, image_path: str) -> Optional[str]:
        """
        Optimize screenshot with fallback to original encoding.

        If optimization fails, falls back to basic base64 encoding without modifications.

        Args:
            image_path: Path to screenshot file

        Returns:
            Base64 encoded image (optimized or original)
        """
        optimized = self.optimize(image_path)
        if optimized:
            return optimized

        # Fallback to basic encoding
        self.logger.warning("Using fallback encoding without optimization")
        try:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            self.logger.error(f"Fallback encoding failed: {e}")
            return None

    def get_screenshot_count(self) -> int:
        """
        Get current number of screenshots in rotation queue.

        Returns:
            Number of screenshots currently stored
        """
        return len(self.screenshot_queue)

    def clear_screenshots(self):
        """
        Clear all screenshots from rotation queue and disk.

        Removes all screenshot files and clears the rotation queue.
        """
        for filename in list(self.screenshot_queue):
            filepath = self.output_dir / filename
            if filepath.exists():
                filepath.unlink()
                self.logger.debug(f"Deleted screenshot: {filename}")

        self.screenshot_queue.clear()
        self.logger.info("All screenshots cleared")

    def get_latest_screenshot(self) -> Optional[Path]:
        """
        Get path to most recently saved screenshot.

        Returns:
            Path to latest screenshot, or None if no screenshots exist
        """
        if not self.screenshot_queue:
            return None

        latest_filename = self.screenshot_queue[-1]
        return self.output_dir / latest_filename
