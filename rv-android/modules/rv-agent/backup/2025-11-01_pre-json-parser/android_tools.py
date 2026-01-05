"""
Android interaction tools with coordinate validation and conversion.

Provides LangChain-compatible tools for Android device interaction. Tools
validate coordinates in optimized image space, convert to device space,
and return structured data for processing by the update_memories node.
"""

from typing import Dict, Any
from langchain_core.tools import tool
import logging

logger = logging.getLogger(__name__)


# Global device interface and coordinate converter (set during tool creation)
_device = None
_converter = None


def set_device_interface(device):
    """
    Set global device interface for tools.

    Args:
        device: DeviceInterface instance
    """
    global _device
    _device = device


def set_coordinate_converter(converter):
    """
    Set global coordinate converter for tools.

    Args:
        converter: CoordinateConverter instance
    """
    global _converter
    _converter = converter


@tool
def android_click(element_description: str, x: int, y: int) -> Dict[str, Any]:
    """
    Click on buttons, images, checkboxes, switches, and other clickable UI elements.

    USE FOR: Button, ImageButton, ImageView, CheckBox, Switch, RadioButton, Tab, MenuItem, Icon
    DO NOT USE FOR: EditText (use android_type_text), Spinner (use android_click to open dropdown)

    Args:
        element_description: Human-readable element description
        x: X coordinate in optimized image space
        y: Y coordinate in optimized image space

    Returns:
        Structured result with execution status
    """
    if _device is None:
        logger.error("Device interface not initialized")
        return {
            "success": False,
            "llm_coords": (x, y),
            "description": element_description,
            "action_type": "click",
            "error": "Device not initialized"
        }

    if _converter is None:
        logger.error("Coordinate converter not initialized")
        return {
            "success": False,
            "llm_coords": (x, y),
            "description": element_description,
            "action_type": "click",
            "error": "Converter not initialized"
        }

    try:
        # Validate optimized coordinates
        try:
            _converter.validate_optimized_coords(x, y)
        except ValueError as e:
            logger.warning(f"❌ Coordinate validation failed: {e}")
            return {
                "success": False,
                "llm_coords": (x, y),
                "description": element_description,
                "action_type": "click",
                "error": f"Invalid coordinates: {e}"
            }

        # Convert to device coordinates
        device_x, device_y = _converter.optimized_to_device(x, y)

        # Execute click on device
        success = _device.click(device_x, device_y)

        logger.info(
            f"✅ Click: {element_description} "
            f"opt({x},{y}) → dev({device_x},{device_y}) - "
            f"{'success' if success else 'failed'}"
        )

        return {
            "success": success,
            "llm_coords": (x, y),
            "description": element_description,
            "action_type": "click"
        }

    except Exception as e:
        logger.error(f"Click failed: {e}", exc_info=True)
        return {
            "success": False,
            "llm_coords": (x, y),
            "description": element_description,
            "action_type": "click",
            "error": str(e)
        }


@tool
def android_type_text(element_description: str, x: int, y: int, text: str) -> Dict[str, Any]:
    """
    Type text into text input fields. ALWAYS use this for EditText elements.

    USE FOR: EditText, AutoCompleteTextView, MultiAutoCompleteTextView, any text input field
    DO NOT USE: android_click on EditText elements - use this tool instead

    Args:
        element_description: Human-readable element description (e.g., "Username field")
        x: X coordinate in optimized image space
        y: Y coordinate in optimized image space
        text: Text to type (e.g., "user@example.com", "password123")

    Returns:
        Structured result with text metadata
    """
    if _device is None:
        logger.error("Device interface not initialized")
        return {
            "success": False,
            "llm_coords": (x, y),
            "description": element_description,
            "action_type": "set_text",
            "text": text,
            "error": "Device not initialized"
        }

    if _converter is None:
        logger.error("Coordinate converter not initialized")
        return {
            "success": False,
            "llm_coords": (x, y),
            "description": element_description,
            "action_type": "set_text",
            "text": text,
            "error": "Converter not initialized"
        }

    try:
        # Validate optimized coordinates
        try:
            _converter.validate_optimized_coords(x, y)
        except ValueError as e:
            logger.warning(f"❌ Coordinate validation failed: {e}")
            return {
                "success": False,
                "llm_coords": (x, y),
                "description": element_description,
                "action_type": "set_text",
                "text": text,
                "error": f"Invalid coordinates: {e}"
            }

        # Convert to device coordinates
        device_x, device_y = _converter.optimized_to_device(x, y)

        # Click to focus
        click_success = _device.click(device_x, device_y)
        if not click_success:
            logger.warning(f"Failed to click text field at dev({device_x},{device_y})")
            return {
                "success": False,
                "llm_coords": (x, y),
                "description": element_description,
                "action_type": "set_text",
                "text": text,
                "error": "Click failed"
            }

        # Input text
        input_success = _device.input_text(text)

        logger.info(
            f"✅ Text input: '{text}' into {element_description} "
            f"opt({x},{y}) → dev({device_x},{device_y}) - "
            f"{'success' if input_success else 'failed'}"
        )

        return {
            "success": input_success,
            "llm_coords": (x, y),
            "description": element_description,
            "action_type": "set_text",
            "text": text
        }

    except Exception as e:
        logger.error(f"Text input failed: {e}", exc_info=True)
        return {
            "success": False,
            "llm_coords": (x, y),
            "description": element_description,
            "action_type": "set_text",
            "text": text,
            "error": str(e)
        }


@tool
def android_long_click(element_description: str, x: int, y: int) -> Dict[str, Any]:
    """
    Long press on UI elements to open context menus or trigger long-press actions.

    USE FOR: Opening context menus, triggering alternative actions, copy/paste operations

    Args:
        element_description: Human-readable element description
        x: X coordinate in optimized image space
        y: Y coordinate in optimized image space

    Returns:
        Structured result
    """
    if _device is None:
        logger.error("Device interface not initialized")
        return {
            "success": False,
            "llm_coords": (x, y),
            "description": element_description,
            "action_type": "long_click",
            "error": "Device not initialized"
        }

    if _converter is None:
        logger.error("Coordinate converter not initialized")
        return {
            "success": False,
            "llm_coords": (x, y),
            "description": element_description,
            "action_type": "long_click",
            "error": "Converter not initialized"
        }

    try:
        # Validate optimized coordinates
        try:
            _converter.validate_optimized_coords(x, y)
        except ValueError as e:
            logger.warning(f"❌ Coordinate validation failed: {e}")
            return {
                "success": False,
                "llm_coords": (x, y),
                "description": element_description,
                "action_type": "long_click",
                "error": f"Invalid coordinates: {e}"
            }

        # Convert to device coordinates
        device_x, device_y = _converter.optimized_to_device(x, y)

        # Execute long click
        success = _device.long_click(device_x, device_y)

        logger.info(
            f"✅ Long click: {element_description} "
            f"opt({x},{y}) → dev({device_x},{device_y}) - "
            f"{'success' if success else 'failed'}"
        )

        return {
            "success": success,
            "llm_coords": (x, y),
            "description": element_description,
            "action_type": "long_click"
        }

    except Exception as e:
        logger.error(f"Long click failed: {e}", exc_info=True)
        return {
            "success": False,
            "llm_coords": (x, y),
            "description": element_description,
            "action_type": "long_click",
            "error": str(e)
        }


@tool
def android_swipe(direction: str, distance: str = "medium") -> Dict[str, Any]:
    """
    Swipe/scroll screen in specified direction to reveal more content.

    USE FOR: Scrolling lists, revealing hidden content, navigating multi-page views
    DO NOT USE: For clicking elements - use android_click instead

    Args:
        direction: Swipe direction - "up", "down", "left", "right"
        distance: Swipe distance - "short", "medium", "long" (default: "medium")

    Returns:
        Structured result
    """
    if _device is None:
        logger.error("Device interface not initialized")
        return {
            "success": False,
            "action_type": "swipe",
            "direction": direction,
            "distance": distance,
            "error": "Device not initialized"
        }

    try:
        # Validate direction
        valid_directions = ['up', 'down', 'left', 'right']
        if direction not in valid_directions:
            error_msg = f"Invalid direction '{direction}'. Use: {', '.join(valid_directions)}"
            logger.warning(f"❌ {error_msg}")
            return {
                "success": False,
                "action_type": "swipe",
                "direction": direction,
                "distance": distance,
                "error": error_msg
            }

        # Validate distance
        valid_distances = ['short', 'medium', 'long']
        if distance not in valid_distances:
            error_msg = f"Invalid distance '{distance}'. Use: {', '.join(valid_distances)}"
            logger.warning(f"❌ {error_msg}")
            return {
                "success": False,
                "action_type": "swipe",
                "direction": direction,
                "distance": distance,
                "error": error_msg
            }

        # Execute swipe on device
        success = _device.swipe(direction, distance)

        logger.info(
            f"↔️ Swipe: {direction} ({distance}) - "
            f"{'success' if success else 'failed'}"
        )

        return {
            "success": success,
            "action_type": "swipe",
            "direction": direction,
            "distance": distance
        }

    except Exception as e:
        logger.error(f"Swipe failed: {e}", exc_info=True)
        return {
            "success": False,
            "action_type": "swipe",
            "direction": direction,
            "distance": distance,
            "error": str(e)
        }


@tool
def android_back() -> Dict[str, Any]:
    """
    Press device back button to navigate back or close dialogs/menus.

    USE FOR: Going back to previous screen, closing dialogs, dismissing keyboards

    Returns:
        Structured result
    """
    if _device is None:
        logger.error("Device interface not initialized")
        return {
            "success": False,
            "action_type": "back",
            "error": "Device not initialized"
        }

    try:
        success = _device.back()

        logger.info(f"🏠 Back button - {'success' if success else 'failed'}")

        return {
            "success": success,
            "action_type": "back"
        }

    except Exception as e:
        logger.error(f"Back button failed: {e}", exc_info=True)
        return {
            "success": False,
            "action_type": "back",
            "error": str(e)
        }


@tool
def android_home() -> Dict[str, Any]:
    """
    Press device home button to return to home screen.

    USE FOR: Exiting application, returning to launcher (use sparingly)

    Returns:
        Structured result
    """
    if _device is None:
        logger.error("Device interface not initialized")
        return {
            "success": False,
            "action_type": "home",
            "error": "Device not initialized"
        }

    try:
        success = _device.home()

        logger.info(f"🏠 Home button - {'success' if success else 'failed'}")

        return {
            "success": success,
            "action_type": "home"
        }

    except Exception as e:
        logger.error(f"Home button failed: {e}", exc_info=True)
        return {
            "success": False,
            "action_type": "home",
            "error": str(e)
        }


def create_android_tools():
    """
    Create Android interaction tools with coordinate validation.

    ### Architectural Decisions:
    - Tools validate coordinates in optimized space
    - Tools convert coordinates to device space
    - Tools execute actions and return structured data
    - Update_memories node handles action mapping and memory updates

    Returns:
        List of LangChain Tool instances for LLM binding
    """
    return [
        android_click,
        android_type_text,
        android_long_click,
        android_swipe,
        android_back,
        android_home
    ]
