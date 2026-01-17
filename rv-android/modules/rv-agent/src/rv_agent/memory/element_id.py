"""
Element ID management for RVAgent.

Centralizes element identification logic to ensure consistency across all components.

IMPORTANT: All components that need to create or compare element IDs MUST use
the functions in this module. Do NOT create element IDs directly with f-strings.

Standard format: "coords:{x},{y}"
- Identifies unique UI elements by their screen position
- Action type is NOT included (use action_signature for action-level tracking)
"""

from typing import Tuple, Optional, Union, Any


def make_element_id(x: int, y: int) -> str:
    """
    Create standardized element ID from coordinates.

    This is the PRIMARY function for creating element IDs. All other code
    should use this function to ensure consistency.

    Format: "coords:{x},{y}"

    Args:
        x: X coordinate
        y: Y coordinate

    Returns:
        Standardized element ID string

    Example:
        >>> make_element_id(540, 340)
        'coords:540,340'
    """
    return f"coords:{x},{y}"


def make_element_id_from_tuple(coords: Union[Tuple[int, int], None]) -> Optional[str]:
    """
    Create standardized element ID from coordinate tuple.

    Use this when you have coordinates as a tuple (common in ItemAction).

    Args:
        coords: Tuple of (x, y) coordinates or None

    Returns:
        Standardized element ID string or None if coords is None

    Example:
        >>> make_element_id_from_tuple((540, 340))
        'coords:540,340'
    """
    if coords is None:
        return None
    x, y = coords
    return make_element_id(int(x), int(y))


def make_element_id_from_action(action: Any) -> Optional[str]:
    """
    Create standardized element ID from an ItemAction or action dict.

    Handles multiple sources of coordinates:
    1. action.coordinates (tuple)
    2. action.get_execution_coordinates() (method)
    3. action.target_view.bounds (calculated center)
    4. action dict with 'x', 'y' keys

    Args:
        action: ItemAction instance or action dictionary

    Returns:
        Standardized element ID string or None if coordinates unavailable

    Example:
        >>> make_element_id_from_action({"x": 540, "y": 340})
        'coords:540,340'
    """
    if action is None:
        return None

    # Handle dict-like actions (from execute_node)
    if isinstance(action, dict):
        x = action.get('x')
        y = action.get('y')
        if x is not None and y is not None:
            return make_element_id(int(x), int(y))
        return None

    # Handle ItemAction with coordinates attribute
    if hasattr(action, 'coordinates') and action.coordinates:
        return make_element_id_from_tuple(action.coordinates)

    # Handle ItemAction with get_execution_coordinates method
    if hasattr(action, 'get_execution_coordinates'):
        coords = action.get_execution_coordinates()
        if coords:
            return make_element_id_from_tuple(coords)

    # Handle ItemAction with target_view bounds
    if hasattr(action, 'target_view') and action.target_view:
        bounds = action.target_view.get('bounds')
        if bounds and isinstance(bounds, list) and len(bounds) == 2:
            try:
                x1, y1 = bounds[0]
                x2, y2 = bounds[1]
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                return make_element_id(center_x, center_y)
            except (TypeError, IndexError, ValueError):
                pass

    return None


def make_element_id_with_widget(widget_id: Optional[str], x: int, y: int) -> str:
    """
    Create element ID preferring widget_id if available, fallback to coordinates.

    Use this when you have both widget_id and coordinates available.

    Args:
        widget_id: Widget resource ID (e.g., "com.app:id/button")
        x: X coordinate
        y: Y coordinate

    Returns:
        Widget ID if available, otherwise coordinate-based ID

    Example:
        >>> make_element_id_with_widget("com.app:id/btn", 540, 340)
        'com.app:id/btn'
        >>> make_element_id_with_widget(None, 540, 340)
        'coords:540,340'
    """
    if widget_id:
        return widget_id
    return make_element_id(x, y)


def parse_element_id(element_id: str) -> Optional[Tuple[int, int]]:
    """
    Parse coordinates from element ID.

    Args:
        element_id: Element ID string

    Returns:
        Tuple of (x, y) coordinates or None if not coordinate-based

    Example:
        >>> parse_element_id('coords:540,340')
        (540, 340)
        >>> parse_element_id('com.app:id/button')
        None
    """
    if not element_id or not element_id.startswith('coords:'):
        return None

    try:
        coords_part = element_id[7:]  # Remove 'coords:' prefix
        # Handle old format with :CLICK suffix
        if ':' in coords_part:
            coords_part = coords_part.split(':')[0]
        x_str, y_str = coords_part.split(',')
        return (int(x_str), int(y_str))
    except (ValueError, IndexError):
        return None


def is_coordinate_based(element_id: str) -> bool:
    """
    Check if element ID is coordinate-based.

    Args:
        element_id: Element ID string

    Returns:
        True if coordinate-based, False otherwise
    """
    return element_id is not None and element_id.startswith('coords:')
