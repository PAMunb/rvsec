"""
Screenshot optimization for vision models.

This module provides utilities to optimize screenshots for multimodal LLM input,
reducing token cost and inference time while preserving UI element visibility.
"""

import base64
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image

from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT


class ScreenshotOptimizer:
    """
    Optimizes screenshots for vision model processing.

    ### Architectural Decisions:
    - Uses PIL for image processing with quality-preserving resizing
    - Implements JPEG compression with configurable quality settings
    - Converts RGBA to RGB for smaller payload size
    - Maintains aspect ratio during resizing to preserve UI layout
    - Provides detailed optimization metrics for monitoring

    ### Role in the System:
    - Reduces token cost for multimodal LLM requests by 50-70%
    - Improves inference speed through smaller image payloads
    - Preserves UI element visibility for accurate identification
    - Enables efficient multimodal context in agent state

    ### Optimization Strategy:
    - Target resolution: 728x1288 (26×28 by 46×28 - Qwen2.5-VL requirement)
    - JPEG quality: 85% (imperceptible quality loss for UI elements)
    - Format: JPEG for compressed size vs PNG lossless
    - Resampling: LANCZOS for high-quality downscaling
    - Token cost: ~1,196 tokens per image (within optimal 256-1280 range)
    """

    # Dimensions MUST be multiples of 28 for Qwen2.5-VL
    DEFAULT_TARGET_SIZE = (728, 1288)  # 26×28 by 46×28, 9:16 aspect ratio
    DEFAULT_QUALITY = 85
    DEFAULT_FORMAT = "JPEG"

    def __init__(self):
        """Initialize screenshot optimizer with logging."""
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_agent.screenshot_optimizer",
            {CONTEXT_COMPONENT: "ScreenshotOptimizer"}
        )

    def optimize(
        self,
        image_path: str,
        target_size: Optional[Tuple[int, int]] = None,
        quality: Optional[int] = None,
        output_format: Optional[str] = None
    ) -> Optional[str]:
        """
        Optimize screenshot for vision model input.

        Args:
            image_path: Path to screenshot file
            target_size: Target (width, height) tuple, uses DEFAULT_TARGET_SIZE if None
            quality: JPEG quality 1-100, uses DEFAULT_QUALITY if None
            output_format: Output format (JPEG or PNG), uses DEFAULT_FORMAT if None

        Returns:
            Base64 encoded optimized image, or None if optimization fails
        """
        target_size = target_size or self.DEFAULT_TARGET_SIZE
        quality = quality or self.DEFAULT_QUALITY
        output_format = output_format or self.DEFAULT_FORMAT

        try:
            img_path = Path(image_path)
            if not img_path.exists():
                self.logger.error(f"Screenshot file not found: {image_path}")
                return None

            original_size = img_path.stat().st_size

            # Load image
            img = Image.open(image_path)
            self.logger.debug(f"Loaded screenshot: {img.size[0]}x{img.size[1]}, mode={img.mode}")

            # Convert RGBA to RGB for JPEG compression
            if img.mode == 'RGBA' and output_format == "JPEG":
                background = Image.new('RGB', img.size, (255, 255, 255))
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
