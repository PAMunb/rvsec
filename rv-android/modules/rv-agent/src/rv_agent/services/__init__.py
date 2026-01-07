"""
Services layer for RV-Agent.

Contains business logic services that coordinate data processing,
coordinate conversion, and UI analysis.

Services:
- screen_analyzer: UI parsing and element formatting (formerly ui/screen_processor)
- vision_service: Image handling and processing (formerly vision/image_handler)
- screenshot_optimizer: Screenshot optimization for LLM
- action_mapper: Coordinate to action mapping
- coordinate_extractor: Extract clickable elements with coordinates
- coordinate_utils: Coordinate manipulation utilities
- prompt_formatter: UI element formatting for LLM prompts
"""

from rv_agent.services.screen_analyzer import ScreenProcessor
from rv_agent.services.vision_service import ImageHandler
from rv_agent.services.screenshot_optimizer import ScreenshotOptimizer
from rv_agent.services.action_mapper import map_coordinates_to_action
from rv_agent.services.coordinate_extractor import extract_clickable_elements_with_coords
from rv_agent.services.prompt_formatter import format_ui_elements_for_llm

__all__ = [
    "ScreenProcessor",
    "ImageHandler",
    "ScreenshotOptimizer",
    "map_coordinates_to_action",
    "extract_clickable_elements_with_coords",
    "format_ui_elements_for_llm",
]
