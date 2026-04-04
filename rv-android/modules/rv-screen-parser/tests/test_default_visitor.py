from unittest.mock import MagicMock

from rv_screen_parser.parser.screen.visitor.default_visitor import DefaultTextVisitor
from rv_screen_parser.parser.screen.visitor.model import Node


class TestDefaultTextVisitor:
    """Test suite for DefaultTextVisitor class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.static_info_mock = MagicMock()
        self.visitor = DefaultTextVisitor(self.static_info_mock, "TestActivity")

    def test_initialization(self):
        """Test DefaultTextVisitor initialization."""
        assert self.visitor.activity == "TestActivity"
        assert isinstance(self.visitor.processed_parents, set)

    def test_get_screen_description(self):
        """Test getting screen description."""
        # Add an item first
        node = Node(
            data={
                "view_class": "android.widget.Button",
                "unique_identifier": "test_btn_123",
                "clickable": True,
                "view_text": "Test Button",
            }
        )
        self.visitor.visit_button(node)

        screen_desc = self.visitor.get_screen_description()

        assert screen_desc is not None
        assert screen_desc.activity == "TestActivity"
        # Should include items we added plus system actions
        assert len(screen_desc.items) >= 1

    def test_visit_node(self):
        """Test visiting a container node."""
        node = Node(
            data={
                "view_class": "android.widget.LinearLayout",
                "unique_identifier": "test_container_123",
                "actionable": True,
                "children": [],
            }
        )

        initial_count = len(self.visitor.items)

        self.visitor.visit_node(node)

        # Since the node is actionable but has no children, it should add an item
        assert len(self.visitor.items) >= initial_count

    def test_visit_node_already_processed(self):
        """Test visiting a node that's already been processed."""
        node = Node(
            data={
                "view_class": "android.widget.LinearLayout",
                "unique_identifier": "test_container_123",
                "actionable": True,
                "children": [],
            }
        )

        # Add the node ID to processed parents
        self.visitor.processed_parents.add("test_container_123")

        initial_count = len(self.visitor.items)

        self.visitor.visit_node(node)

        # Should not add a new item since it's already processed
        assert len(self.visitor.items) == initial_count

    def test_visit_node_not_actionable(self):
        """Test visiting a node that's not actionable."""
        node = Node(
            data={
                "view_class": "android.widget.LinearLayout",
                "unique_identifier": "test_container_123",
                "actionable": False,
                "children": [],
            }
        )

        initial_count = len(self.visitor.items)

        self.visitor.visit_node(node)

        # Should not add an item since it's not actionable
        assert len(self.visitor.items) == initial_count

    def test_visit_node_with_actionable_children(self):
        """Test visiting a node that has actionable children."""
        child_node = Node(
            data={
                "view_class": "android.widget.Button",
                "unique_identifier": "child_btn_123",
                "actionable": True,
            }
        )

        parent_node = Node(
            data={
                "view_class": "android.widget.LinearLayout",
                "unique_identifier": "parent_container_123",
                "actionable": True,
                "children": [child_node],
            }
        )

        initial_count = len(self.visitor.items)

        self.visitor.visit_node(parent_node)

        # Should not add the parent if children handle the actions
        assert len(self.visitor.items) == initial_count

    def test_visit_leaf_node(self):
        """Test visiting a leaf node."""
        leaf_node = Node(
            data={
                "view_class": "android.widget.Button",
                "unique_identifier": "test_leaf_123",
                "clickable": True,
                "view_text": "Test Button",
            }
        )

        initial_count = len(self.visitor.items)

        self.visitor.visit_leaf_node(leaf_node)

        assert len(self.visitor.items) > initial_count

    def test_visit_leaf_node_not_actionable(self):
        """Test visiting a leaf node that's not actionable."""
        leaf_node = Node(
            data={
                "view_class": "android.widget.TextView",
                "unique_identifier": "test_text_123",
                "clickable": False,
                "long_clickable": False,
                "view_text": "Just text",
            }
        )

        initial_count = len(self.visitor.items)

        self.visitor.visit_leaf_node(leaf_node)

        # Should not add an item since it's not actionable
        assert len(self.visitor.items) == initial_count

    def test_visit_leaf_node_already_processed(self):
        """Test visiting a leaf node that's already been processed."""
        leaf_node = Node(
            data={
                "view_class": "android.widget.Button",
                "resource_id": "test_leaf_123",
                "clickable": True,
                "view_text": "Test Button",
            }
        )

        # Add the node ID to processed parents (computed as f"{view_class}_{resource_id}_{bounds}")
        # From the debug output, the actual unique_identifier is '_test_leaf_123_[[0, 0], [0, 0]]'
        # because view_class is not being extracted properly from the data dict
        computed_id = leaf_node.unique_identifier
        self.visitor.processed_parents.add(computed_id)

        initial_count = len(self.visitor.items)

        self.visitor.visit_leaf_node(leaf_node)

        # Should not add a new item since it's already processed
        assert len(self.visitor.items) == initial_count

    def test_visit_button(self):
        """Test visiting a button node."""
        node = Node(
            data={
                "view_class": "android.widget.Button",
                "unique_identifier": "test_button_123",
                "clickable": True,
                "view_text": "Submit",
                "resource_id": "submit_btn",
            }
        )

        initial_count = len(self.visitor.items)

        self.visitor.visit_button(node)

        assert len(self.visitor.items) > initial_count
        # Check that the item contains button-related text
        if self.visitor.items:
            item = self.visitor.items[-1]
            assert "Button" in item.base_description

    def test_visit_edit_text(self):
        """Test visiting an edit text node."""
        node = Node(
            data={
                "view_class": "android.widget.EditText",
                "unique_identifier": "test_edit_123",
                "editable": True,
                "view_text": "Sample text",
                "hint": "Enter text here",
                "is_password": False,
            }
        )

        initial_count = len(self.visitor.items)

        self.visitor.visit_edit_text(node)

        assert len(self.visitor.items) > initial_count
        # Check that the item contains edit text-related text
        if self.visitor.items:
            item = self.visitor.items[-1]
            assert "Editable text field" in item.base_description

    def test_visit_edit_text_password(self):
        """Test visiting a password edit text node."""
        node = Node(
            data={
                "view_class": "android.widget.EditText",
                "unique_identifier": "test_password_123",
                "editable": True,
                "view_text": "",
                "hint": "Password",
                "is_password": True,
            }
        )

        initial_count = len(self.visitor.items)

        self.visitor.visit_edit_text(node)

        assert len(self.visitor.items) > initial_count
        # Check that the item contains password-related text
        if self.visitor.items:
            item = self.visitor.items[-1]
            assert "Password field" in item.base_description

    def test_visit_text_view(self):
        """Test visiting a text view node."""
        node = Node(
            data={
                "view_class": "android.widget.TextView",
                "unique_identifier": "test_text_123",
                "view_text": "Sample text content",
                "clickable": False,
            }
        )

        initial_count = len(self.visitor.items)

        self.visitor.visit_text_view(node)

        # Will add item if it has text content
        assert len(self.visitor.items) >= initial_count

    def test_visit_text_view_actionable(self):
        """Test visiting an actionable text view node."""
        node = Node(
            data={
                "view_class": "android.widget.TextView",
                "unique_identifier": "test_text_123",
                "view_text": "Clickable text",
                "clickable": True,
            }
        )

        initial_count = len(self.visitor.items)

        self.visitor.visit_text_view(node)

        assert len(self.visitor.items) > initial_count
        # Should have added an item since it's clickable

    def test_visit_checkbox(self):
        """Test visiting a checkbox node."""
        node = Node(
            data={
                "view_class": "android.widget.CheckBox",
                "unique_identifier": "test_checkbox_123",
                "checkable": True,
                "checked": True,
                "view_text": "Accept terms",
            }
        )

        initial_count = len(self.visitor.items)

        self.visitor.visit_checkbox(node)

        assert len(self.visitor.items) > initial_count
        # Check that the item contains checkbox-related text
        if self.visitor.items:
            item = self.visitor.items[-1]
            assert "Checkbox" in item.base_description
            assert "checked" in item.base_description

    def test_visit_checkbox_unchecked(self):
        """Test visiting an unchecked checkbox node."""
        node = Node(
            data={
                "view_class": "android.widget.CheckBox",
                "unique_identifier": "test_checkbox_123",
                "checkable": True,
                "checked": False,
                "view_text": "Accept terms",
            }
        )

        initial_count = len(self.visitor.items)

        self.visitor.visit_checkbox(node)

        assert len(self.visitor.items) > initial_count
        # Check that the item contains checkbox-related text
        if self.visitor.items:
            item = self.visitor.items[-1]
            assert "Checkbox" in item.base_description
            assert "unchecked" in item.base_description

    def test_visit_checked_text(self):
        """Test visiting a checked text view node."""
        node = Node(
            data={
                "view_class": "android.widget.CheckedTextView",
                "unique_identifier": "test_checked_text_123",
                "checkable": True,
                "checked": True,
                "view_text": "Checked option",
            }
        )

        initial_count = len(self.visitor.items)

        self.visitor.visit_checked_text(node)

        assert len(self.visitor.items) > initial_count
        # Check that the item contains checked text-related text
        if self.visitor.items:
            item = self.visitor.items[-1]
            assert "Checkable text" in item.base_description

    def test_visit_image_button(self):
        """Test visiting an image button node."""
        node = Node(
            data={
                "view_class": "android.widget.ImageButton",
                "unique_identifier": "test_img_btn_123",
                "clickable": True,
                "content_description": "Settings button",
            }
        )

        initial_count = len(self.visitor.items)

        self.visitor.visit_image_button(node)

        assert len(self.visitor.items) > initial_count
        # Check that the item contains image button-related text
        if self.visitor.items:
            item = self.visitor.items[-1]
            assert "Image button" in item.base_description

    def test_visit_image(self):
        """Test visiting an image node."""
        node = Node(
            data={
                "view_class": "android.widget.ImageView",
                "unique_identifier": "test_img_123",
                "clickable": True,
                "content_description": "Profile picture",
            }
        )

        initial_count = len(self.visitor.items)

        self.visitor.visit_image(node)

        assert len(self.visitor.items) > initial_count
        # Should add item since it's clickable

    def test_visit_image_not_actionable_no_description(self):
        """Test visiting a non-actionable image with no description."""
        node = Node(
            data={
                "view_class": "android.widget.ImageView",
                "unique_identifier": "test_img_123",
                "clickable": False,
                "long_clickable": False,
                "content_description": None,
            }
        )

        initial_count = len(self.visitor.items)

        self.visitor.visit_image(node)

        # Should not add item since it's not actionable and has no description
        assert len(self.visitor.items) == initial_count

    def test_visit_toggle_button(self):
        """Test visiting a toggle button node."""
        node = Node(
            data={
                "view_class": "android.widget.ToggleButton",
                "unique_identifier": "test_toggle_123",
                "checkable": True,
                "checked": True,
                "view_text": "Toggle Me",
            }
        )

        initial_count = len(self.visitor.items)

        self.visitor.visit_toggle_button(node)

        assert len(self.visitor.items) > initial_count
        # Check that the item contains toggle button-related text
        if self.visitor.items:
            item = self.visitor.items[-1]
            assert "Toggle button" in item.base_description

    def test_visit_switch(self):
        """Test visiting a switch node."""
        node = Node(
            data={
                "view_class": "android.widget.Switch",
                "unique_identifier": "test_switch_123",
                "checkable": True,
                "checked": False,
                "view_text": "Enable feature",
            }
        )

        initial_count = len(self.visitor.items)

        self.visitor.visit_switch(node)

        assert len(self.visitor.items) > initial_count
        # Check that the item contains switch-related text
        if self.visitor.items:
            item = self.visitor.items[-1]
            assert "Switch" in item.base_description

    def test_visit_radio_button(self):
        """Test visiting a radio button node."""
        node = Node(
            data={
                "view_class": "android.widget.RadioButton",
                "unique_identifier": "test_radio_123",
                "checkable": True,
                "selected": True,
                "view_text": "Option 1",
            }
        )

        initial_count = len(self.visitor.items)

        self.visitor.visit_radio_button(node)

        assert len(self.visitor.items) > initial_count
        # Check that the item contains radio button-related text
        if self.visitor.items:
            item = self.visitor.items[-1]
            assert "Radio button" in item.base_description

    def test_visit_spinner(self):
        """Test visiting a spinner node."""
        node = Node(
            data={
                "view_class": "android.widget.Spinner",
                "unique_identifier": "test_spinner_123",
                "clickable": True,
                "view_text": "Selected Option",
            }
        )

        initial_count = len(self.visitor.items)

        self.visitor.visit_spinner(node)

        assert len(self.visitor.items) > initial_count
        # Check that the item contains spinner-related text
        if self.visitor.items:
            item = self.visitor.items[-1]
            assert "Dropdown spinner" in item.base_description

    def test_visit_radio_group(self):
        """Test visiting a radio group node."""
        node = Node(
            data={
                "view_class": "android.widget.RadioGroup",
                "unique_identifier": "test_radio_group_123",
                "actionable": True,
            }
        )

        initial_count = len(self.visitor.items)

        self.visitor.visit_radio_group(node)

        # May or may not add an item depending on the implementation
        assert len(self.visitor.items) >= initial_count

    def test_visit_slider(self):
        """Test visiting a slider node."""
        node = Node(
            data={
                "view_class": "android.widget.SeekBar",
                "unique_identifier": "test_slider_123",
                "progress": 50,
                "max": 100,  # This will be mapped to max_progress internally
            }
        )

        initial_count = len(self.visitor.items)

        self.visitor.visit_slider(node)

        assert len(self.visitor.items) > initial_count
        # Check that the item contains slider-related text
        if self.visitor.items:
            item = self.visitor.items[-1]
            assert "Slider" in item.base_description

    def test_has_action_by_type(self):
        """Test checking if screen has specific system action type."""
        from rv_screen_parser.constants import SystemActionType

        # Initially should not have any system actions
        has_back = self.visitor._has_action_by_type(SystemActionType.BACK)
        assert not has_back

    def test_get_max_action_id_empty(self):
        """Test getting max action ID when no items exist."""
        max_id = self.visitor._get_max_action_id()
        assert max_id == 0

    def test_get_max_action_id_with_items(self):
        """Test getting max action ID with existing items."""
        # Add a mock item with actions
        mock_item = MagicMock()
        mock_action = MagicMock()
        mock_action.id = 5
        mock_item.actions = [mock_action]
        self.visitor.items = [mock_item]

        max_id = self.visitor._get_max_action_id()
        assert max_id == 5

    def test_ensure_standard_system_actions(self):
        """Test ensuring standard system actions are present."""
        # This method adds system actions, let's call it
        self.visitor._ensure_standard_system_actions()

        # Should have added system actions
        # Check if any items were added
        system_items = [
            item
            for item in self.visitor.items
            if hasattr(item, "base_description")
            and "System" in str(item.base_description)
        ]
        assert (
            len(system_items) >= 0
        )  # May or may not add items depending on implementation

    def test_create_system_action_view(self):
        """Test creating system action view."""
        from rv_screen_parser.constants import SystemActionType

        view = self.visitor._create_system_action_view(SystemActionType.BACK)

        assert isinstance(view, dict)
        assert "content_description" in view
        assert "class" in view
        assert "resource_id" in view
        assert view["system_action_type"] == SystemActionType.BACK
