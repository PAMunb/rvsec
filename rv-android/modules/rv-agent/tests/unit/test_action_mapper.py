"""
Unit tests for the action_mapper service.
"""

import pytest
from rv_agent.services import action_mapper
from rv_screen_parser.parser.screen.visitor.model import (
    ScreenDescription,
    ScreenItem,
    ItemAction,
)
from rv_android_core.domain.widget import WidgetEventType

# Define standard dimensions for tests
DEVICE_DIMS = (1080, 1920)
OPTIMIZED_DIMS = (720, 1280)


@pytest.fixture
def mock_screen_description():
    """Creates a mock ScreenDescription for testing."""
    screen = ScreenDescription(activity="TestActivity", items=[])

    # Item 1: A button
    action1 = ItemAction(id=101, event=WidgetEventType.CLICK, text="OK", target_view={})
    item1 = ScreenItem(
        base_description="OK button",
        view={"bounds": [[100, 200], [300, 400]]},  # Area: 200*200 = 40000
        actions=[action1],
    )

    # Item 2: An input field with two actions
    action2_click = ItemAction(
        id=201, event=WidgetEventType.CLICK, text="Username", target_view={}
    )
    action2_input = ItemAction(
        id=202, event=WidgetEventType.TEXT_CHANGE, text="Username", target_view={}
    )
    item2 = ScreenItem(
        base_description="Username input",
        view={"bounds": [[100, 500], [900, 700]]},  # Area: 800*200 = 160000
        actions=[action2_click, action2_input],
    )

    # Item 3: An item with no actions
    item3 = ScreenItem(
        base_description="Image", view={"bounds": [[0, 0], [100, 100]]}, actions=[]
    )

    screen.items = [item1, item2, item3]
    return screen


class TestActionMapper:
    """Test suite for action mapping functions."""

    # --- Tests for get_device_coordinates ---
    def test_get_device_coordinates(self):
        """Test simple coordinate conversion."""
        # Center of optimized space
        llm_coords = (360, 640)
        dev_x, dev_y = action_mapper.get_device_coordinates(
            llm_coords, OPTIMIZED_DIMS, DEVICE_DIMS
        )
        assert (dev_x, dev_y) == (540, 960)

    def test_get_device_coordinates_clamping(self):
        """Test that coordinates are clamped to device bounds."""
        llm_coords = (800, 1400)  # Outside optimized dims
        dev_x, dev_y = action_mapper.get_device_coordinates(
            llm_coords, OPTIMIZED_DIMS, DEVICE_DIMS
        )
        assert dev_x == DEVICE_DIMS[0] - 1
        assert dev_y == DEVICE_DIMS[1] - 1

    # --- Tests for get_action_by_id ---
    def test_get_action_by_id_success(self, mock_screen_description):
        """Test finding an action by its ID."""
        action = action_mapper.get_action_by_id(202, mock_screen_description)
        assert action is not None
        assert action.id == 202
        assert action.action_type == "set_text"

    def test_get_action_by_id_not_found(self, mock_screen_description):
        """Test that it returns None if ID is not found."""
        action = action_mapper.get_action_by_id(999, mock_screen_description)
        assert action is None

    # --- Tests for map_coordinates_to_action ---
    def test_map_coordinates_to_action_success(self, mock_screen_description):
        """Test successful mapping of coords to a specific action."""
        # Coords that map to the center of Item 2 (Username input)
        # Device center: (500, 600) -> Optimized: (333, 400)
        llm_coords = (333, 400)
        action_id = action_mapper.map_coordinates_to_action(
            llm_coords, "set_text", mock_screen_description, OPTIMIZED_DIMS, DEVICE_DIMS
        )
        assert action_id == 202  # Should find the 'set_text' action

    def test_map_coordinates_to_action_fallback(self, mock_screen_description):
        """Test that it falls back to the first action if type doesn't match."""
        # Coords for Item 2, but request a non-existent action type
        llm_coords = (333, 400)
        action_id = action_mapper.map_coordinates_to_action(
            llm_coords, "swipe", mock_screen_description, OPTIMIZED_DIMS, DEVICE_DIMS
        )
        # Should fall back to the first action of the item (click, id 201)
        assert action_id == 201

    def test_map_coordinates_to_action_no_element(self, mock_screen_description):
        """Test that a ValueError is raised if no element is at the coordinates."""
        # These coords are outside any element
        llm_coords = (700, 1200)
        with pytest.raises(ValueError, match="No element found at coordinates"):
            action_mapper.map_coordinates_to_action(
                llm_coords,
                "click",
                mock_screen_description,
                OPTIMIZED_DIMS,
                DEVICE_DIMS,
            )

    def test_map_coordinates_to_action_no_actions(self, mock_screen_description):
        """Test that a ValueError is raised if the found element has no actions."""
        # Coords for Item 3 (Image)
        # Device center: (50, 50) -> Optimized: (33, 33)
        llm_coords = (33, 33)
        with pytest.raises(ValueError, match="Element has no actions"):
            action_mapper.map_coordinates_to_action(
                llm_coords,
                "click",
                mock_screen_description,
                OPTIMIZED_DIMS,
                DEVICE_DIMS,
            )

    def test_map_coordinates_to_action_chooses_smallest_element(
        self, mock_screen_description
    ):
        """Test that the smallest overlapping element is chosen."""
        # Add an overlapping item that is smaller than item 2
        small_item_action = ItemAction(
            id=401, event=WidgetEventType.CLICK, text="inner", target_view={}
        )
        small_item = ScreenItem(
            base_description="Inner button",
            view={"bounds": [[450, 550], [550, 650]]},  # Area: 100*100 = 10000
            actions=[small_item_action],
        )
        mock_screen_description.items.append(small_item)

        # Coords for the center of the small item
        # Device center: (500, 600) -> Optimized: (333, 400)
        llm_coords = (333, 400)
        action_id = action_mapper.map_coordinates_to_action(
            llm_coords, "click", mock_screen_description, OPTIMIZED_DIMS, DEVICE_DIMS
        )
        # Should choose the action from the smaller item (401), not the larger one (201)
        assert action_id == 401

    def test_map_coordinates_out_of_bounds_clamping(
        self, mock_screen_description, caplog
    ):
        """Test that out-of-bounds coordinates are clamped and a warning is logged."""
        # These LLM coords will map to a device coord that is out of bounds
        llm_coords = (800, 100)  # x=800 -> device_x = 1200 > 1080

        # We expect it to fail after clamping, because the clamped coord (1079, 150) is not in any element
        with pytest.raises(ValueError, match="No element found at coordinates"):
            action_mapper.map_coordinates_to_action(
                llm_coords,
                "click",
                mock_screen_description,
                OPTIMIZED_DIMS,
                DEVICE_DIMS,
            )

        # Check that the warning for clamping was logged
        assert "Converted coords out of bounds" in caplog.text
        assert "Clamped to" in caplog.text

    def test_map_coordinates_handles_malformed_bounds(self, mock_screen_description):
        """Test that items with malformed bounds are skipped."""
        # Add an item with bad bounds
        mock_screen_description.items[0].view["bounds"] = "not a list"

        # Use coordinates that would have hit the original item 1
        # Device (200, 300) -> Opt (133, 200)
        llm_coords = (133, 200)

        # This should now fail to find an element, as the only one in range is malformed
        with pytest.raises(ValueError, match="No element found at coordinates"):
            action_mapper.map_coordinates_to_action(
                llm_coords,
                "click",
                mock_screen_description,
                OPTIMIZED_DIMS,
                DEVICE_DIMS,
            )
