"""
Action mapping from LLM coordinates to ScreenDescription actions.

Maps visual coordinates from LLM analysis to executable actions in the
ScreenDescription model, handling coordinate conversion and action selection.
"""

import logging
from typing import Optional, Tuple

from rv_screen_parser.parser.screen.visitor.model import ItemAction, ScreenDescription

logger = logging.getLogger(__name__)


def map_coordinates_to_action(
    llm_coords: Tuple[int, int],
    action_type: str,
    screen_description: ScreenDescription,
    optimized_dims: Tuple[int, int],
    device_dims: Tuple[int, int],
) -> int:
    """
    Map LLM coordinates and action type to ItemAction ID.

    ### Architectural Decisions:
    - Converts coordinates from optimized to device space
    - Uses bounding box intersection for element identification
    - Selects action from ScreenItem.actions based on type
    - Falls back to first action if specific type not found
    - Returns action.id for tracking
    - Validates bounds to prevent out-of-range errors

    ### Mapping Steps:
    1. Convert coordinates: optimized → device space
    2. Find ScreenItem: device coords → item.view['bounds']
    3. Select ItemAction: item.actions filtered by action_type
    4. Return action.id for tracking

    Args:
        llm_coords: Coordinates in optimized image space
        action_type: Requested action type (click, long_click, set_text, etc.)
        screen_description: Parsed UI with items and actions
        optimized_dims: Optimized screenshot dimensions (e.g., 728x1288)
        device_dims: Device screen dimensions (e.g., 1080x1920)

    Returns:
        ItemAction.id for the selected action

    Raises:
        ValueError: If no element found at coordinates or no action available
    """
    llm_x, llm_y = llm_coords

    # Step 1: Convert coordinates from optimized to device space
    scale_x = device_dims[0] / optimized_dims[0]
    scale_y = device_dims[1] / optimized_dims[1]
    device_x = int(llm_x * scale_x)
    device_y = int(llm_y * scale_y)

    # Validate bounds
    if not (0 <= device_x < device_dims[0] and 0 <= device_y < device_dims[1]):
        logger.warning(
            f"Converted coords out of bounds: ({device_x}, {device_y}) "
            f"for device dims {device_dims}"
        )
        # Clamp to valid range
        device_x = max(0, min(device_x, device_dims[0] - 1))
        device_y = max(0, min(device_y, device_dims[1] - 1))
        logger.warning(f"Clamped to: ({device_x}, {device_y})")

    # Step 2: Find ScreenItem containing coordinates
    containing_items = []
    for item in screen_description.items:
        bounds = item.view.get("bounds")
        if not bounds or not isinstance(bounds, list) or len(bounds) != 2:
            continue

        # bounds format: [[x1, y1], [x2, y2]]
        x1, y1 = bounds[0]
        x2, y2 = bounds[1]

        if x1 <= device_x <= x2 and y1 <= device_y <= y2:
            area = (x2 - x1) * (y2 - y1)
            containing_items.append((item, area))

    if not containing_items:
        raise ValueError(
            f"No element found at coordinates ({device_x}, {device_y}) "
            f"(from LLM coords {llm_coords})"
        )

    # Choose smallest containing element (most specific)
    target_item, _ = min(containing_items, key=lambda x: x[1])

    # Step 3: Select ItemAction from target_item.actions
    if not target_item.actions:
        raise ValueError(
            f"Element has no actions: {target_item.base_description} "
            f"at coords ({device_x}, {device_y})"
        )

    # Filter by action type
    matching_actions = [
        action for action in target_item.actions if action.action_type == action_type
    ]

    # Fallback to first action if no match
    selected_action = (
        matching_actions[0] if matching_actions else target_item.actions[0]
    )

    # Log the mapping
    logger.info(
        f"Mapped coords ({llm_x},{llm_y}) → device ({device_x},{device_y}) → "
        f"action_id={selected_action.id} ({selected_action.action_type}: "
        f"{selected_action.text or target_item.base_description})"
    )

    # Step 4: Return action.id
    logger.info(
        f"🎯 Action mapping complete: "
        f"LLM({llm_x},{llm_y}) → Device({device_x},{device_y}) → "
        f"Item[{target_item.base_description}] → "
        f"Action#{selected_action.id}[{selected_action.action_type}]"
    )
    return selected_action.id


def get_action_by_id(
    action_id: int, screen_description: ScreenDescription
) -> Optional[ItemAction]:
    """
    Retrieve ItemAction by ID from ScreenDescription.

    ### Architectural Decisions:
    - Performs linear search through all items
    - Returns first matching action
    - Used for action verification and logging

    Args:
        action_id: Action ID to find
        screen_description: Parsed screen description

    Returns:
        ItemAction if found, None otherwise
    """
    for item in screen_description.items:
        for action in item.actions:
            if action.id == action_id:
                return action
    return None


def get_device_coordinates(
    llm_coords: Tuple[int, int],
    optimized_dims: Tuple[int, int],
    device_dims: Tuple[int, int],
) -> Tuple[int, int]:
    """
    Convert LLM coordinates to device coordinates.

    Useful for direct device interaction when bypassing ScreenDescription.

    Args:
        llm_coords: Coordinates in optimized image space
        optimized_dims: Optimized screenshot dimensions
        device_dims: Device screen dimensions

    Returns:
        Tuple of (device_x, device_y) with bounds validation
    """
    llm_x, llm_y = llm_coords

    scale_x = device_dims[0] / optimized_dims[0]
    scale_y = device_dims[1] / optimized_dims[1]

    device_x = int(llm_x * scale_x)
    device_y = int(llm_y * scale_y)

    # Clamp to valid range
    device_x = max(0, min(device_x, device_dims[0] - 1))
    device_y = max(0, min(device_y, device_dims[1] - 1))

    return (device_x, device_y)
