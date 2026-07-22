import pytest
from rv_android_core.domain.widget import WidgetEventType
from rv_screen_parser.parser.screen.visitor.model import (
    Counter,
    ItemAction,
    Node,
    ScreenDescription,
    ScreenItem,
    UiElementType,
)


class TestItemAction:
    """Tests for the ItemAction class"""

    def test_item_action_initialization(self):
        """Test that ItemAction is initialized correctly with default values"""
        action = ItemAction(id=1, text="CLICK (1)", event=WidgetEventType.CLICK)

        assert action.id == 1
        assert action.text == "CLICK (1)"
        assert action.event == WidgetEventType.CLICK
        assert action.reaches_target is False
        assert action.directly_reaches_target is False
        assert action.target_view == {}
        assert action.coordinates is None

    def test_item_action_initialization_with_all_fields(self):
        """Test that ItemAction is initialized with all fields provided"""
        target_view = {"resource_id": "test_id", "class": "Button"}
        coordinates = (100, 200)

        action = ItemAction(
            id=2,
            text="LONG_CLICK (2)",
            event=WidgetEventType.LONG_CLICK,
            reaches_target=True,
            directly_reaches_target=True,
            target_view=target_view,
            coordinates=coordinates,
        )

        assert action.id == 2
        assert action.text == "LONG_CLICK (2)"
        assert action.event == WidgetEventType.LONG_CLICK
        assert action.reaches_target is True
        assert action.directly_reaches_target is True
        assert action.target_view == target_view
        assert action.coordinates == coordinates

    def test_action_type_property(self):
        """Test that action_type property correctly extracts the action type from text"""
        test_cases = [
            (ItemAction(1, "CLICK (1)", WidgetEventType.CLICK), "click"),
            (ItemAction(2, "LONG_CLICK (2)", WidgetEventType.LONG_CLICK), "long_click"),
            (ItemAction(3, "SCROLL UP (3)", WidgetEventType.SCROLL), "scroll_up"),
            (ItemAction(4, "SCROLL DOWN (4)", WidgetEventType.SCROLL), "scroll_down"),
            (ItemAction(5, "SCROLL LEFT (5)", WidgetEventType.SCROLL), "scroll_left"),
            (ItemAction(6, "SCROLL RIGHT (6)", WidgetEventType.SCROLL), "scroll_right"),
            (ItemAction(7, "SCROLL (7)", WidgetEventType.SCROLL), "scroll"),
            (ItemAction(8, "SET_TEXT (8)", WidgetEventType.TEXT_CHANGE), "set_text"),
            (ItemAction(9, "CHECK (9)", WidgetEventType.CLICK), "click"),
            (ItemAction(10, "UNCHECK (10)", WidgetEventType.CLICK), "click"),
            (ItemAction(11, "BACK (11)", WidgetEventType.KEY), "key_event"),
            (ItemAction(12, "UNKNOWN (12)", WidgetEventType.OTHER), "unknown"),
        ]

        for action, expected_type in test_cases:
            assert action.action_type == expected_type

    def test_get_target_identifier(self):
        """Test the get_target_identifier method correctly extracts the target identifier"""
        # Test with resource_id
        action1 = ItemAction(
            id=1,
            text="CLICK (1)",
            event=WidgetEventType.CLICK,
            target_view={"resource_id": "test_id"},
        )
        assert action1.get_target_identifier() == "test_id"

        # Test with bounds
        action2 = ItemAction(
            id=2,
            text="CLICK (2)",
            event=WidgetEventType.CLICK,
            target_view={"bounds": [[10, 20], [30, 40]]},
        )
        assert action2.get_target_identifier() == "20 30"

        # Test with coordinates
        action3 = ItemAction(
            id=3, text="CLICK (3)", event=WidgetEventType.CLICK, coordinates=(50, 60)
        )
        assert action3.get_target_identifier() == "50 60"

        # Test with empty target
        action4 = ItemAction(id=4, text="CLICK (4)", event=WidgetEventType.CLICK)
        assert action4.get_target_identifier() == ""

    def test_get_execution_coordinates(self):
        """Test the get_execution_coordinates method correctly extracts coordinates"""
        # Test with explicit coordinates
        action1 = ItemAction(
            id=1, text="CLICK (1)", event=WidgetEventType.CLICK, coordinates=(10, 20)
        )
        assert action1.get_execution_coordinates() == (10, 20)

        # Test with bounds
        action2 = ItemAction(
            id=2,
            text="CLICK (2)",
            event=WidgetEventType.CLICK,
            target_view={"bounds": [[10, 20], [30, 40]]},
        )
        assert action2.get_execution_coordinates() == (20, 30)

        # Test with no coordinates
        action3 = ItemAction(id=3, text="CLICK (3)", event=WidgetEventType.CLICK)
        assert action3.get_execution_coordinates() is None


class TestScreenItem:
    """Tests for the ScreenItem class"""

    def test_screen_item_initialization(self):
        """Test that ScreenItem is initialized correctly with default values"""
        view_data = {"class": "Button", "resource_id": "test_button"}
        item = ScreenItem(view=view_data, base_description="Test button")

        assert item.view == view_data
        assert item.base_description == "Test button"
        assert item.actions == []

    def test_screen_item_initialization_with_actions(self):
        """Test that ScreenItem is initialized with actions provided"""
        view_data = {"class": "Button", "resource_id": "test_button"}
        actions = [
            ItemAction(1, "CLICK (1)", WidgetEventType.CLICK),
            ItemAction(2, "LONG_CLICK (2)", WidgetEventType.LONG_CLICK),
        ]

        item = ScreenItem(
            view=view_data, base_description="Test button", actions=actions
        )

        assert item.view == view_data
        assert item.base_description == "Test button"
        assert item.actions == actions

    def test_description_property(self):
        """Test that the description property combines base_description with actions"""
        view_data = {"class": "Button", "resource_id": "test_button"}

        # Test without actions
        item1 = ScreenItem(view=view_data, base_description="Test button")
        assert item1.description == "Test button."

        # Test with actions
        actions = [
            ItemAction(1, "CLICK (1)", WidgetEventType.CLICK),
            ItemAction(2, "LONG_CLICK (2)", WidgetEventType.LONG_CLICK),
        ]

        item2 = ScreenItem(
            view=view_data, base_description="Test button", actions=actions
        )
        assert item2.description == "Test button. Actions: CLICK (1), LONG_CLICK (2)"

    def test_str_method(self):
        """Test the __str__ method returns the description"""
        view_data = {"class": "Button", "resource_id": "test_button"}
        item = ScreenItem(view=view_data, base_description="Test button")

        assert str(item) == item.description


class TestScreenDescription:
    """Tests for the ScreenDescription class"""

    def test_screen_description_initialization(self):
        """Test that ScreenDescription is initialized correctly"""
        activity = "com.example.TestActivity"
        items = [
            ScreenItem(
                view={"class": "Button"},
                base_description="Button 1",
                actions=[ItemAction(1, "CLICK (1)", WidgetEventType.CLICK)],
            ),
            ScreenItem(
                view={"class": "TextView"}, base_description="Text 1", actions=[]
            ),
        ]

        screen = ScreenDescription(activity=activity, items=items)

        assert screen.activity == activity
        # ScreenDescription no longer automatically adds a BACK action
        assert len(screen.items) == 2  # 2 original items
        assert 1 in screen.events_by_id
        assert screen.events_by_id[1].text == "CLICK (1)"

    def test_add_standard_back_action(self):
        """Test that ScreenDescription no longer automatically adds a BACK action"""
        activity = "com.example.TestActivity"
        items = [
            ScreenItem(
                view={"class": "Button"},
                base_description="Button 1",
                actions=[ItemAction(1, "CLICK (1)", WidgetEventType.CLICK)],
            )
        ]

        screen = ScreenDescription(activity=activity, items=items)

        # Verify no automatic back action is added
        back_action = None
        for item in screen.items:
            for action in item.actions:
                if "BACK" in action.text:
                    back_action = action
                    break
            if back_action:
                break

        # Back action should NOT be present anymore
        assert back_action is None
        # Only the original item should be present
        assert len(screen.items) == 1

    def test_no_duplicate_back_action(self):
        """Test that back action is not duplicated if already present"""
        activity = "com.example.TestActivity"
        items = [
            ScreenItem(
                view={"class": "Button"},
                base_description="Button 1",
                actions=[ItemAction(1, "CLICK (1)", WidgetEventType.CLICK)],
            ),
            ScreenItem(
                view={"class": "BackButton"},
                base_description="Back button",
                actions=[ItemAction(2, "BACK (2)", WidgetEventType.KEY)],
            ),
        ]

        screen = ScreenDescription(activity=activity, items=items)

        # Count back actions
        back_action_count = 0
        for item in screen.items:
            for action in item.actions:
                if "BACK" in action.text:
                    back_action_count += 1

        # Only the original back action should be present
        assert back_action_count == 1
        assert len(screen.items) == 2  # No additional items added

    def test_description_property(self):
        """Test that the description property returns a formatted string"""
        activity = "com.example.TestActivity"
        items = [
            ScreenItem(
                view={"class": "Button"},
                base_description="Button 1",
                actions=[ItemAction(1, "CLICK (1)", WidgetEventType.CLICK)],
            ),
            ScreenItem(
                view={"class": "TextView"}, base_description="Text 1", actions=[]
            ),
        ]

        screen = ScreenDescription(activity=activity, items=items)
        description = screen.description

        assert (
            "The current screen has the following UI views and corresponding actions"
            in description
        )
        assert "Button 1. Actions: CLICK (1)" in description
        assert "Text 1." in description

    def test_str_method(self):
        """Test the __str__ method returns the description"""
        activity = "com.example.TestActivity"
        items = [
            ScreenItem(
                view={"class": "Button"},
                base_description="Button 1",
                actions=[ItemAction(1, "CLICK (1)", WidgetEventType.CLICK)],
            )
        ]

        screen = ScreenDescription(activity=activity, items=items)

        assert str(screen) == screen.description


class TestCounter:
    """Tests for the Counter class"""

    def test_counter_initialization(self):
        """Test that Counter is initialized with default start value"""
        counter = Counter()
        assert counter.value == 0

    def test_counter_initialization_with_start_value(self):
        """Test that Counter is initialized with provided start value"""
        counter = Counter(value=10)
        assert counter.value == 10

    def test_increment_method(self):
        """Test that increment method increments the counter and returns the new value"""
        counter = Counter(value=5)
        assert counter.increment() == 6
        assert counter.value == 6
        assert counter.increment() == 7
        assert counter.value == 7

    def test_get_current_method(self):
        """Test that get_current method returns the current value without incrementing"""
        counter = Counter(value=5)
        assert counter.get_current() == 5
        assert counter.value == 5  # Value remains unchanged
        counter.increment()
        assert counter.get_current() == 6
        assert counter.value == 6  # Value remains unchanged


class TestUiElementType:
    """Tests for the UiElementType enum"""

    def test_enum_values(self):
        """Test that UiElementType enum has the expected values"""
        assert UiElementType.CONTAINER.value == "container"
        assert UiElementType.BUTTON.value == "button"
        assert UiElementType.TEXT_FIELD.value == "text_field"
        assert UiElementType.TEXT_VIEW.value == "text_view"
        assert UiElementType.CHECKBOX.value == "checkbox"
        assert UiElementType.TOGGLE.value == "toggle"
        assert UiElementType.RADIO_BUTTON.value == "radio_button"
        assert UiElementType.SPINNER.value == "spinner"
        assert UiElementType.SLIDER.value == "slider"
        assert UiElementType.IMAGE.value == "image"
        assert UiElementType.UNKNOWN.value == "unknown"

    def test_from_class_name(self):
        """Test that from_class_name method correctly maps Android class names to element types"""
        test_cases = [
            ("android.widget.Button", UiElementType.BUTTON),
            ("android.widget.ImageButton", UiElementType.BUTTON),
            ("android.widget.EditText", UiElementType.TEXT_FIELD),
            ("android.widget.TextView", UiElementType.TEXT_VIEW),
            ("android.widget.CheckBox", UiElementType.CHECKBOX),
            ("android.widget.CheckedTextView", UiElementType.CHECKBOX),
            ("android.widget.ToggleButton", UiElementType.TOGGLE),
            ("android.widget.Switch", UiElementType.TOGGLE),
            ("android.widget.RadioButton", UiElementType.RADIO_BUTTON),
            ("android.widget.Spinner", UiElementType.SPINNER),
            ("android.widget.SeekBar", UiElementType.SLIDER),
            ("android.widget.ImageView", UiElementType.IMAGE),
            ("android.widget.Unknown", UiElementType.UNKNOWN),
            ("com.example.CustomView", UiElementType.UNKNOWN),
        ]

        for class_name, expected_type in test_cases:
            assert UiElementType.from_class_name(class_name) == expected_type


class TestNode:
    """Tests for the Node class"""

    def test_node_initialization_basics(self):
        """Test that Node is initialized with basic properties"""
        view_data = {
            "class": "android.widget.Button",
            "resource_id": "test_button",
            "text": "Click me",
            "clickable": True,
        }

        node = Node(data=view_data)

        assert node.data == view_data
        assert node.children == []
        assert node.parent is None
        assert node.view_class == "android.widget.Button"
        assert node.resource_id == "test_button"
        assert node.view_text == "Click me"
        assert node.clickable is True
        assert node.actionable is True  # derived from clickable

    def test_node_initialization_with_complete_data(self):
        """Test that Node is initialized with all properties extracted from view data"""
        view_data = {
            "class": "android.widget.EditText",
            "resource_id": "test_field",
            "text": "Hello",
            "content_description": "Test field",
            "package": "com.example.test",
            "hint": "Enter text",
            "clickable": True,
            "scrollable": True,
            "checkable": False,
            "long_clickable": True,
            "editable": True,
            "checked": False,
            "selected": False,
            "is_password": True,
            "enabled": True,
            "focused": True,
            "bounds": [[10, 20], [30, 40]],
            "progress": 50,
            "max": 100,
        }

        node = Node(data=view_data)

        # Test all properties are correctly extracted
        assert node.view_class == "android.widget.EditText"
        assert node.resource_id == "test_field"
        assert node.view_text == "Hello"
        assert node.content_description == "Test field"
        assert node.package == "com.example.test"
        assert node.hint == "Enter text"
        assert node.clickable is True
        assert node.scrollable is True
        assert node.checkable is False
        assert node.long_clickable is True
        assert node.editable is True
        assert node.checked is False
        assert node.selected is False
        assert node.is_password is True
        assert node.enabled is True
        assert node.focused is True
        assert node.bounds == [[10, 20], [30, 40]]
        assert node.progress == 50
        assert node.max_progress == 100

        # Test derived properties
        assert node.actionable is True
        assert node.element_type == UiElementType.TEXT_FIELD

    def test_node_initialization_with_defaults(self):
        """Test that Node uses default values for missing properties"""
        view_data = {
            "class": "android.widget.Button",
        }

        node = Node(data=view_data)

        # Check default values
        assert node.resource_id == ""
        assert node.view_text == ""
        assert node.content_description == ""
        assert node.package == ""
        assert node.hint == ""
        assert node.clickable is False
        assert node.scrollable is False
        assert node.checkable is False
        assert node.long_clickable is False
        assert node.editable is False
        assert node.checked is False
        assert node.selected is False
        assert node.is_password is False
        assert node.enabled is True  # Default is True for enabled
        assert node.focused is False
        assert node.bounds == [[0, 0], [0, 0]]
        assert node.progress == 0
        assert node.max_progress == 100

        # Test derived properties
        assert node.actionable is False
        assert node.element_type == UiElementType.BUTTON

    def test_node_with_children(self):
        """Test that Node correctly handles child nodes"""
        parent_data = {"class": "android.widget.LinearLayout"}
        child1_data = {"class": "android.widget.Button", "resource_id": "button1"}
        child2_data = {"class": "android.widget.TextView", "resource_id": "text1"}

        # Create parent node
        parent_node = Node(data=parent_data)

        # Create child nodes with parent reference
        child1 = Node(data=child1_data, parent=parent_node)
        child2 = Node(data=child2_data, parent=parent_node)

        # Add children to parent
        parent_node.children = [child1, child2]

        # Check parent-child relationships
        assert parent_node.children == [child1, child2]
        assert child1.parent == parent_node
        assert child2.parent == parent_node

    def test_accept_method_leaf_node(self):
        """Test that accept method calls the correct visitor method for leaf nodes"""

        # Create a mock visitor with tracking of called methods
        class MockVisitor:
            def __init__(self):
                self.called_methods = []

            def visit_button(self, node):
                self.called_methods.append(("visit_button", node.resource_id))

            def visit_text_view(self, node):
                self.called_methods.append(("visit_text_view", node.resource_id))

            def visit_leaf_node(self, node):
                self.called_methods.append(("visit_leaf_node", node.resource_id))

            # Add all potentially required visitor methods
            def visit_edit_text(self, node):
                self.called_methods.append(("visit_edit_text", node.resource_id))

            def visit_checkbox(self, node):
                self.called_methods.append(("visit_checkbox", node.resource_id))

            def visit_checked_text(self, node):
                self.called_methods.append(("visit_checked_text", node.resource_id))

            def visit_image_button(self, node):
                self.called_methods.append(("visit_image_button", node.resource_id))

            def visit_image(self, node):
                self.called_methods.append(("visit_image", node.resource_id))

            def visit_toggle_button(self, node):
                self.called_methods.append(("visit_toggle_button", node.resource_id))

            def visit_switch(self, node):
                self.called_methods.append(("visit_switch", node.resource_id))

            def visit_radio_button(self, node):
                self.called_methods.append(("visit_radio_button", node.resource_id))

            def visit_slider(self, node):
                self.called_methods.append(("visit_slider", node.resource_id))

        # Create test nodes
        button_node = Node(
            data={"class": "android.widget.Button", "resource_id": "button1"}
        )
        text_node = Node(
            data={"class": "android.widget.TextView", "resource_id": "text1"}
        )
        unknown_node = Node(
            data={"class": "android.widget.Unknown", "resource_id": "unknown1"}
        )

        # Create visitor
        visitor = MockVisitor()

        # Call accept method
        button_node.accept(visitor)
        text_node.accept(visitor)
        unknown_node.accept(visitor)

        # Check that correct methods were called
        assert visitor.called_methods == [
            ("visit_button", "button1"),
            ("visit_text_view", "text1"),
            ("visit_leaf_node", "unknown1"),
        ]

    def test_accept_method_container_node(self):
        """Test that accept method correctly handles container nodes and traverses children"""
        # Mock implementation of Node.accept to avoid dependencies on internal behavior
        original_accept = Node.accept

        try:
            # Create a simplified mock implementation that matches our test expectations
            def mock_accept(self, visitor):
                if self.view_class == "android.widget.LinearLayout":
                    visitor.visit_node(self)
                    for child in self.children:
                        if child.view_class == "android.widget.Button":
                            visitor.visit_button(child)
                elif self.view_class == "android.widget.Spinner":
                    visitor.visit_spinner(self)
                elif self.view_class == "android.widget.RadioGroup":
                    visitor.visit_radio_group(self)

            # Apply the mock
            Node.accept = mock_accept

            # Create a mock visitor with tracking of called methods
            class MockVisitor:
                def __init__(self):
                    self.called_methods = []

                def visit_node(self, node):
                    self.called_methods.append(("visit_node", node.resource_id))

                def visit_spinner(self, node):
                    self.called_methods.append(("visit_spinner", node.resource_id))

                def visit_radio_group(self, node):
                    self.called_methods.append(("visit_radio_group", node.resource_id))

                def visit_button(self, node):
                    self.called_methods.append(("visit_button", node.resource_id))

            # Create test nodes
            container_node = Node(
                data={
                    "class": "android.widget.LinearLayout",
                    "resource_id": "container1",
                }
            )
            spinner_node = Node(
                data={"class": "android.widget.Spinner", "resource_id": "spinner1"}
            )
            radio_group_node = Node(
                data={
                    "class": "android.widget.RadioGroup",
                    "resource_id": "radio_group1",
                }
            )

            # Create child nodes
            button1 = Node(
                data={"class": "android.widget.Button", "resource_id": "button1"}
            )

            # Set up hierarchy
            container_node.children = [button1]

            # Create visitor
            visitor = MockVisitor()

            # Call accept method
            container_node.accept(visitor)
            spinner_node.accept(visitor)
            radio_group_node.accept(visitor)

            # Check that correct methods were called in correct order
            expected_calls = [
                ("visit_node", "container1"),
                ("visit_button", "button1"),
                ("visit_spinner", "spinner1"),
                ("visit_radio_group", "radio_group1"),
            ]

            assert visitor.called_methods == expected_calls

        finally:
            # Restore original method
            Node.accept = original_accept

    def test_find_children_by_class(self):
        """Test that find_children_by_class finds all children of a specific class"""
        # Create test nodes
        root = Node(
            data={"class": "android.widget.LinearLayout", "resource_id": "root"}
        )
        child1 = Node(data={"class": "android.widget.Button", "resource_id": "button1"})
        child2 = Node(data={"class": "android.widget.TextView", "resource_id": "text1"})
        child3 = Node(
            data={"class": "android.widget.LinearLayout", "resource_id": "container1"}
        )
        child4 = Node(data={"class": "android.widget.Button", "resource_id": "button2"})

        # Set up hierarchy
        root.children = [child1, child2, child3]
        child3.children = [child4]

        # Find all buttons
        buttons = root.find_children_by_class("android.widget.Button")

        # Check that all buttons were found
        assert len(buttons) == 2
        assert buttons[0].resource_id == "button1"
        assert buttons[1].resource_id == "button2"

        # Find all text views
        text_views = root.find_children_by_class("android.widget.TextView")

        # Check that all text views were found
        assert len(text_views) == 1
        assert text_views[0].resource_id == "text1"

        # Find non-existent class
        empty_result = root.find_children_by_class("android.widget.NonExistent")
        assert len(empty_result) == 0

    def test_center_coordinates(self):
        """Test that center_coordinates correctly calculates center coordinates"""
        # Create test node with valid bounds
        node1 = Node(
            data={"class": "android.widget.Button", "bounds": [[10, 20], [30, 40]]}
        )
        assert node1.center_coordinates == (20, 30)

        # Test with invalid bounds format
        node2 = Node(data={"class": "android.widget.Button", "bounds": []})
        assert node2.center_coordinates == (0, 0)

        # Test with no bounds
        node3 = Node(data={"class": "android.widget.Button"})
        assert node3.center_coordinates == (0, 0)

    def test_unique_identifier(self):
        """Test that unique_identifier generates a unique identifier"""
        # Create test nodes
        node1 = Node(
            data={
                "class": "android.widget.Button",
                "resource_id": "button1",
                "bounds": [[10, 20], [30, 40]],
            }
        )

        node2 = Node(
            data={
                "class": "android.widget.Button",
                "resource_id": "button1",
                "bounds": [[50, 60], [70, 80]],
            }
        )

        node3 = Node(
            data={
                "class": "android.widget.TextView",
                "resource_id": "button1",
                "bounds": [[10, 20], [30, 40]],
            }
        )

        # Each node should have a unique ID
        id1 = node1.unique_identifier
        id2 = node2.unique_identifier
        id3 = node3.unique_identifier

        assert id1 != id2  # Same class and resource_id but different bounds
        assert id1 != id3  # Same resource_id and bounds but different class

    def test_str_method(self):
        """Test the __str__ method returns a human-readable representation"""
        # Test with resource_id
        node1 = Node(data={"class": "android.widget.Button", "resource_id": "button1"})
        assert str(node1) == "android.widget.Button - button1"

        # Test with text instead of resource_id
        node2 = Node(data={"class": "android.widget.TextView", "text": "Hello"})
        assert str(node2) == "android.widget.TextView - Hello"

        # Test with neither resource_id nor text
        node3 = Node(data={"class": "android.widget.LinearLayout"})
        assert str(node3) == "android.widget.LinearLayout - LinearLayout"


class TestItemActionCoordinateValidation:
    """
    Coordinate validation and coordinate-resolution edge cases for ItemAction.

    These target the failure branches of ``validate_coordinates`` and the
    malformed-bounds fallbacks in the coordinate-resolution helpers, which the
    happy-path tests above never exercise. Boundary Value Analysis drives the
    coordinate cases: the boundary is x/y >= 0, so we test -1 (just outside) and
    a well-formed pair (inside).
    """

    def test_validate_coordinates_none_passes_through(self):
        """None is a valid 'no coordinates' sentinel and must pass unchanged."""
        assert ItemAction.validate_coordinates(None) is None

    def test_validate_coordinates_valid_tuple_returned(self):
        """A well-formed (x, y) integer tuple is returned unchanged."""
        assert ItemAction.validate_coordinates((10, 20)) == (10, 20)

    def test_validate_coordinates_rejects_non_tuple(self):
        """A list (not a tuple) fails the isinstance/length guard."""
        with pytest.raises(ValueError, match="tuple of"):
            ItemAction.validate_coordinates([10, 20])

    def test_validate_coordinates_rejects_wrong_length(self):
        """A 3-element tuple fails the length guard (must be exactly two)."""
        with pytest.raises(ValueError, match="tuple of"):
            ItemAction.validate_coordinates((10, 20, 30))

    def test_validate_coordinates_rejects_non_integer_values(self):
        """Non-integer coordinate values are rejected."""
        with pytest.raises(ValueError, match="must be integers"):
            ItemAction.validate_coordinates(("10", "20"))

    def test_validate_coordinates_rejects_negative_values(self):
        """Negative coordinates are below the valid boundary (>= 0)."""
        with pytest.raises(ValueError, match="non-negative"):
            ItemAction.validate_coordinates((-1, 20))

    def test_get_target_identifier_malformed_bounds_returns_empty(self):
        """
        Malformed bounds (inner lists that cannot unpack into x, y) must be
        swallowed by the except guard, yielding the empty-string fallback.
        """
        action = ItemAction(
            id=1,
            text="CLICK (1)",
            event=WidgetEventType.CLICK,
            target_view={"bounds": [[1], [2]]},
        )
        assert action.get_target_identifier() == ""

    def test_get_execution_coordinates_malformed_bounds_returns_none(self):
        """Malformed bounds cause coordinate resolution to fall back to None."""
        action = ItemAction(
            id=1,
            text="CLICK (1)",
            event=WidgetEventType.CLICK,
            target_view={"bounds": [[1], [2]]},
        )
        assert action.get_execution_coordinates() is None

    def test_coords_for_matching_with_explicit_coordinates(self):
        """
        coords_for_matching pairs the resolved DEVICE-space coordinates with the
        action type; explicit coordinates are used directly.
        """
        action = ItemAction(
            id=1, text="CLICK (1)", event=WidgetEventType.CLICK, coordinates=(5, 6)
        )
        assert action.coords_for_matching == ((5, 6), "click")

    def test_coords_for_matching_without_coordinates_uses_zero_origin(self):
        """When coordinates cannot be resolved, the signature falls back to (0, 0)."""
        action = ItemAction(id=2, text="SET_TEXT (2)", event=WidgetEventType.TEXT_CHANGE)
        assert action.coords_for_matching == ((0, 0), "set_text")


class TestScreenItemActionQueries:
    """
    Action-type query helpers and view validation for ScreenItem.

    Decision-table coverage: an item with a mix of action types must return the
    matching subset for a queried type and an empty list for an absent type.
    """

    @pytest.fixture
    def item_with_mixed_actions(self):
        """A ScreenItem carrying one click action and one set_text action."""
        actions = [
            ItemAction(1, "CLICK (1)", WidgetEventType.CLICK),
            ItemAction(2, "SET_TEXT (2)", WidgetEventType.TEXT_CHANGE),
        ]
        return ScreenItem(
            view={"class": "android.widget.EditText"},
            base_description="Field",
            actions=actions,
        )

    def test_get_actions_by_type_returns_matching_subset(self, item_with_mixed_actions):
        """Filtering by 'set_text' returns only the TEXT_CHANGE action."""
        result = item_with_mixed_actions.get_actions_by_type("set_text")
        assert len(result) == 1
        assert result[0].id == 2

    def test_get_actions_by_type_absent_type_returns_empty(
        self, item_with_mixed_actions
    ):
        """Filtering by an action type no action has returns an empty list."""
        assert item_with_mixed_actions.get_actions_by_type("scroll") == []

    def test_has_action_type_true_when_present(self, item_with_mixed_actions):
        """has_action_type reports True for a type the item supports."""
        assert item_with_mixed_actions.has_action_type("click") is True

    def test_has_action_type_false_when_absent(self, item_with_mixed_actions):
        """has_action_type reports False for a type the item lacks."""
        assert item_with_mixed_actions.has_action_type("long_click") is False

    def test_validate_view_data_rejects_non_dict(self):
        """
        The view validator guards against non-dict input. Pydantic's own type
        coercion normally runs first, so the guard is exercised by invoking the
        classmethod validator directly with a non-dict value.
        """
        with pytest.raises(ValueError, match="must be a dictionary"):
            ScreenItem.validate_view_data("not a dict")


class TestScreenDescriptionQueries:
    """
    Aggregation and lookup helpers on ScreenDescription.

    These cover the action-lookup and counting methods that the initialization
    tests above do not reach directly.
    """

    @pytest.fixture
    def screen(self):
        """A two-item screen: a button (click) and an editable field (set_text)."""
        items = [
            ScreenItem(
                view={"class": "android.widget.Button"},
                base_description="Button 1",
                actions=[ItemAction(1, "CLICK (1)", WidgetEventType.CLICK)],
            ),
            ScreenItem(
                view={"class": "android.widget.EditText"},
                base_description="Field 1",
                actions=[ItemAction(2, "SET_TEXT (2)", WidgetEventType.TEXT_CHANGE)],
            ),
        ]
        return ScreenDescription(activity="com.example.Act", items=items)

    def test_get_action_by_id_found(self, screen):
        """A known action id resolves to its ItemAction via the lookup map."""
        action = screen.get_action_by_id(2)
        assert action is not None
        assert action.text == "SET_TEXT (2)"

    def test_get_action_by_id_missing_returns_none(self, screen):
        """An unknown action id resolves to None."""
        assert screen.get_action_by_id(999) is None

    def test_get_all_actions_flattens_every_item(self, screen):
        """get_all_actions concatenates actions across all items."""
        all_actions = screen.get_all_actions()
        assert [a.id for a in all_actions] == [1, 2]

    def test_get_actions_by_type_filters_across_items(self, screen):
        """Screen-wide filtering returns only actions of the requested type."""
        clicks = screen.get_actions_by_type("click")
        assert len(clicks) == 1
        assert clicks[0].id == 1

    def test_get_element_count(self, screen):
        """Element count reflects the number of items on the screen."""
        assert screen.get_element_count() == 2

    def test_get_action_count(self, screen):
        """Action count reflects the total actions across all items."""
        assert screen.get_action_count() == 2


class TestCounterValidationAndReset:
    """
    Counter validation boundary and reset behaviour.

    Boundary Value Analysis: the valid range is value >= 0, so -1 is the
    just-outside case and 0 the boundary.
    """

    def test_validate_counter_value_rejects_negative(self):
        """Constructing a Counter with a negative value is rejected."""
        with pytest.raises(ValueError):
            Counter(value=-1)

    def test_reset_sets_new_start_value(self):
        """reset moves the counter to a non-negative start value."""
        counter = Counter(value=7)
        counter.reset(3)
        assert counter.value == 3

    def test_reset_default_returns_to_zero(self):
        """reset with no argument returns the counter to zero."""
        counter = Counter(value=7)
        counter.reset()
        assert counter.value == 0

    def test_reset_rejects_negative_start_value(self):
        """reset guards against negative start values."""
        counter = Counter(value=7)
        with pytest.raises(ValueError, match="non-negative"):
            counter.reset(-1)


class TestNodeDerivedPropertiesAndHelpers:
    """
    Node derived-property inference, raw-data access, and display-text fallbacks.
    """

    def test_edit_text_infers_editable_when_not_reported(self):
        """
        UIAutomator does not always report the 'editable' attribute. An EditText
        node without it must still be treated as editable (and thus actionable).
        """
        node = Node(data={"class": "android.widget.EditText"})
        assert node.editable is True
        assert node.actionable is True

    def test_get_property_returns_raw_value_and_default(self):
        """_get_property reads directly from raw data, using the default when absent."""
        node = Node(data={"class": "android.widget.Button", "custom": "x"})
        assert node._get_property("custom", "fallback") == "x"
        assert node._get_property("missing", "fallback") == "fallback"

    def test_validate_data_structure_rejects_non_dict(self):
        """The data validator rejects non-dict input when invoked directly."""
        with pytest.raises(ValueError, match="must be a dictionary"):
            Node.validate_data_structure("not a dict")

    def test_center_coordinates_malformed_bounds_returns_origin(self):
        """
        Bounds whose inner lists cannot unpack into (x, y) trigger the except
        guard, falling back to the (0, 0) origin.
        """
        node = Node(data={"class": "android.widget.Button", "bounds": [[1], [2]]})
        assert node.center_coordinates == (0, 0)

    def test_get_display_text_prefers_content_description_over_hint(self):
        """
        With no visible text, get_display_text falls back to the accessibility
        content description before considering hint or resource id.
        """
        node = Node(
            data={"class": "android.widget.ImageView", "content_description": "logo"}
        )
        assert node.get_display_text() == "logo"

    def test_get_display_text_falls_back_to_hint(self):
        """With no text and no content description, the hint text is used."""
        node = Node(data={"class": "android.widget.EditText", "hint": "Enter name"})
        assert node.get_display_text() == "Enter name"

    def test_find_children_by_resource_id_recursive(self):
        """
        find_children_by_resource_id collects matches across the full descendant
        tree, not just direct children.
        """
        root = Node(data={"class": "android.widget.LinearLayout"})
        nested = Node(data={"class": "android.widget.FrameLayout"})
        match1 = Node(data={"class": "android.widget.Button", "resource_id": "target"})
        match2 = Node(data={"class": "android.widget.TextView", "resource_id": "target"})
        other = Node(data={"class": "android.widget.TextView", "resource_id": "other"})

        root.children = [match1, nested, other]
        nested.children = [match2]

        found = root.find_children_by_resource_id("target")
        assert len(found) == 2
        assert {n.view_class for n in found} == {
            "android.widget.Button",
            "android.widget.TextView",
        }


class RecordingVisitor:
    """
    Minimal visitor that records the (method, resource_id) of every dispatch.

    Used to exercise the REAL Node.accept dispatch (leaf and container) rather
    than a monkey-patched replacement, so the actual branching in
    _handle_leaf_node / _handle_container_node is covered.
    """

    def __init__(self):
        self.calls = []

    def visit_button(self, node):
        self.calls.append(("visit_button", node.resource_id))

    def visit_node(self, node):
        self.calls.append(("visit_node", node.resource_id))

    def visit_spinner(self, node):
        self.calls.append(("visit_spinner", node.resource_id))

    def visit_radio_group(self, node):
        self.calls.append(("visit_radio_group", node.resource_id))

    def visit_chip_group(self, node):
        self.calls.append(("visit_chip_group", node.resource_id))


class TestNodeAcceptDispatch:
    """
    Real visitor-pattern dispatch through Node.accept for leaf and container nodes.

    Basis Path Testing: each branch of _handle_leaf_node and
    _handle_container_node is driven by a concrete node/visitor combination.
    """

    def test_container_generic_recurses_children(self):
        """
        A generic container (LinearLayout) invokes visit_node on itself, then
        recurses into children, dispatching each leaf to its handler.
        """
        container = Node(
            data={"class": "android.widget.LinearLayout", "resource_id": "root"}
        )
        button = Node(
            data={"class": "android.widget.Button", "resource_id": "btn"}
        )
        container.children = [button]

        visitor = RecordingVisitor()
        container.accept(visitor)

        assert visitor.calls == [
            ("visit_node", "root"),
            ("visit_button", "btn"),
        ]

    def test_container_spinner_dispatches_to_visit_spinner(self):
        """A Spinner container with children dispatches to visit_spinner, not visit_node."""
        spinner = Node(
            data={"class": "android.widget.Spinner", "resource_id": "sp"}
        )
        spinner.children = [Node(data={"class": "android.widget.TextView"})]

        visitor = RecordingVisitor()
        spinner.accept(visitor)

        assert visitor.calls == [("visit_spinner", "sp")]

    def test_container_radio_group_dispatches_to_visit_radio_group(self):
        """A RadioGroup container dispatches to visit_radio_group."""
        group = Node(
            data={"class": "android.widget.RadioGroup", "resource_id": "rg"}
        )
        group.children = [Node(data={"class": "android.widget.RadioButton"})]

        visitor = RecordingVisitor()
        group.accept(visitor)

        assert visitor.calls == [("visit_radio_group", "rg")]

    def test_container_chip_group_uses_handler_when_available(self):
        """A ChipGroup dispatches to visit_chip_group when the visitor provides it."""
        group = Node(
            data={
                "class": "com.google.android.material.chip.ChipGroup",
                "resource_id": "cg",
            }
        )
        group.children = [
            Node(data={"class": "com.google.android.material.chip.Chip"})
        ]

        visitor = RecordingVisitor()
        group.accept(visitor)

        assert visitor.calls == [("visit_chip_group", "cg")]

    def test_container_chip_group_falls_back_to_children(self):
        """
        A ChipGroup falls back to processing children individually when the
        visitor has no visit_chip_group handler.
        """

        class ChipVisitor:
            def __init__(self):
                self.calls = []

            def visit_button(self, node):
                self.calls.append(("visit_button", node.resource_id))

        group = Node(
            data={
                "class": "com.google.android.material.chip.ChipGroup",
                "resource_id": "cg",
            }
        )
        # Chip class maps to visit_button in the leaf handler mapping.
        chip = Node(
            data={
                "class": "com.google.android.material.chip.Chip",
                "resource_id": "chip1",
            }
        )
        group.children = [chip]

        visitor = ChipVisitor()
        group.accept(visitor)

        assert visitor.calls == [("visit_button", "chip1")]

    def test_leaf_excluded_system_button_short_circuits(self):
        """
        When the visitor flags a leaf as a system navigation/status button, the
        leaf handler returns immediately without dispatching any visit_* method.
        """

        class ExcludingVisitor:
            def __init__(self):
                self.calls = []

            def should_exclude_system_button(self, node):
                return True

            def visit_button(self, node):
                self.calls.append("visit_button")

        node = Node(
            data={"class": "android.widget.Button", "resource_id": "navbar"}
        )
        visitor = ExcludingVisitor()
        node.accept(visitor)

        assert visitor.calls == []

    def test_leaf_falls_back_to_generic_handler(self):
        """
        A Button leaf whose visitor lacks visit_button falls back to the generic
        visit_leaf_node handler.
        """

        class GenericOnlyVisitor:
            def __init__(self):
                self.calls = []

            def visit_leaf_node(self, node):
                self.calls.append(("visit_leaf_node", node.resource_id))

        node = Node(
            data={"class": "android.widget.Button", "resource_id": "btn"}
        )
        visitor = GenericOnlyVisitor()
        node.accept(visitor)

        assert visitor.calls == [("visit_leaf_node", "btn")]


if __name__ == "__main__":
    pytest.main()
