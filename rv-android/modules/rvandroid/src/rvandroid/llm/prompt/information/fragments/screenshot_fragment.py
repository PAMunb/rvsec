"""Screenshot information fragment for the prompt system.

This module defines a specialized fragment for processing and describing screenshots
from the application state.
"""

import os
from typing import Any, Dict, Optional

from rv_android_core.llm.constants import StateEntry
from rv_android_core.llm.prompt.information.base_fragment import InformationFragment
from rv_android_core.parser.screen.visitor.model import ScreenItem


class ScreenshotFragment(InformationFragment):
    """Fragment for processing and describing screenshots.
    
    This fragment extracts screenshot information from the state and converts it 
    to a format usable in prompts, either as a description or embedded image.
    """

    def __init__(
            self,
            name: str = "screenshot",
            priority: int = 600,
            include_image: bool = True
    ):
        """Initialize the screenshot fragment.
        
        Args:
            name: The name of the fragment (default: "screenshot").
            priority: The priority of the fragment (default: 150).
            include_image: Whether to include the actual image (default: True).
        """
        super().__init__(name, priority)
        self.include_image = include_image

    def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate screenshot information from the application state.
        
        Args:
            state: The current application state.
            context: Additional context information.
            
        Returns:
            A dictionary containing screenshot information.
        """
        if not state:
            return {}

        screenshot_path = state.get("screenshot_path")

        if not screenshot_path or not os.path.exists(screenshot_path):
            self.logger.debug(f"Screenshot not found at path: {screenshot_path}")
            return {}

        result = {}

        if StateEntry.SCREENSHOT_INFO in state:
            screenshot_info = state[StateEntry.SCREENSHOT_INFO]
            if "error_indicators" in screenshot_info:
                for error_indicator in screenshot_info["error_indicators"]:
                    confidence = error_indicator.get("confidence", 0)
                    if confidence >= 0.8 and "associated_item" in error_indicator:
                        item: ScreenItem = error_indicator["associated_item"]
                        item.base_description += " [ERR]"

        # # Extract metadata
        # result["timestamp"] = state.get("timestamp", "")
        #
        # # Get screen dimensions if available
        # if "screen" in state and "size" in state["screen"]:
        #     result["dimensions"] = state["screen"]["size"]

        self.logger.debug(f"Generated screenshot information from {screenshot_path}")
        return result

    def should_include(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> bool:
        """Determine if screenshot information should be included.
        
        Args:
            state: The current application state.
            context: Additional context information.
            
        Returns:
            True if screenshot information should be included, False otherwise.
        """
        # Check if model_capabilities in context indicates image support
        if context and "model_capabilities" in context:
            capabilities = context.get("model_capabilities", {})
            if not capabilities.get("supports_images", True):
                self.logger.debug("Model does not support images, excluding screenshot data")
                return False

        # Check if screenshot is available
        screenshot_path = state.get("screenshot_path")
        if not screenshot_path or not os.path.exists(screenshot_path):
            return False

        return True
