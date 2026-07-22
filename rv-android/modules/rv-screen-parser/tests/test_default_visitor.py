"""Tests for DefaultTextVisitor.

Node construction contract (verified empirically -- read before adding tests)
============================================================================
``Node`` is decorated with ``@validated_model(["data", "children", "parent"])``,
so positional args map to those fields in order. Both ``Node({...})`` (positional
-> ``data``) and ``Node(data={...}, children=[...])`` (keyword) are valid.

``Node.__init__`` extracts a FIXED set of keys out of ``data`` and then RECOMPUTES
derived properties. As a result, several keys placed inside the ``data`` dict are
silently ignored -- a test that relies on them passes for the wrong reason:

- ``"class"`` is the widget-class key, NOT ``"view_class"``. ``__init__`` reads
  ``raw_data.get("class")``; a ``"view_class"`` key leaves ``node.view_class == ""``.
- ``"children"`` must be a top-level arg (``Node(data, children=[...])`` or
  ``node.children = [...]``). A ``"children"`` key inside ``data`` yields 0 children.
- ``"unique_identifier"`` is a COMPUTED property
  (``f"{view_class}_{resource_id}_{bounds}"``); a data-dict value is ignored. To
  exercise the "already processed" path, seed ``node.unique_identifier`` itself.
- ``"actionable"`` is RECOMPUTED from the capability flags in
  ``_calculate_derived_properties`` (clickable / scrollable / checkable /
  long_clickable / editable). ``{"actionable": True}`` alone gives
  ``actionable == False``; set a capability flag (e.g. ``"clickable": True``).

Tests below that predate this note still use the ignored keys; the ones affected
carry an inline NOTE. New tests (see TestDefaultTextVisitorBranchCoverage) use the
correct keys.
"""

from unittest.mock import MagicMock

from rv_android_core.domain.widget import WidgetEventType
from rv_screen_parser.constants import SystemActionType
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

        # NOTE: passes for the wrong reason -- "actionable" in the data dict is
        # recomputed to False (no capability flag set), so no item is added; the
        # >= assertion is trivially true. See module docstring. A faithful version
        # would set "clickable": True and an actionable child. Covered correctly in
        # TestDefaultTextVisitorBranchCoverage.
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

        # NOTE: this seeds "test_container_123", but node.unique_identifier is a
        # COMPUTED value ("android.widget.LinearLayout__[[0, 0], [0, 0]]"), so the
        # early-return at visit_node is NOT triggered here. It passes only because
        # the node is non-actionable with no children. The real early-return path
        # is covered by test_visit_node_early_return_when_already_processed
        # (which seeds node.unique_identifier). See module docstring.
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

        # NOTE: passes for the wrong reason -- both "actionable" and the in-data
        # "children" are ignored (recomputed / not extracted), so parent_node is
        # non-actionable with 0 children and the "children handle the action"
        # branch is never exercised. A faithful version needs "clickable": True on
        # both nodes and children passed as a kwarg: Node(data=..., children=[...]).
        # See module docstring; correct coverage in TestDefaultTextVisitorBranchCoverage.
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


class TestDefaultTextVisitorBranchCoverage:
    """Branch-coverage tests for DefaultTextVisitor edge paths.

    These target control-flow branches not exercised by the happy-path suite
    above: early returns, system-button exclusion, MOP annotation of button
    actions, spinner/radio-group/slider variants, and the system-action lookup.

    NOTE ON THE DATA DICT: Node reads element attributes from the raw view data
    dict, but the class-name key is ``class`` (not ``view_class``) -- see
    Node.__init__. Tests that rely on widget-type dispatch or find_children_by_class
    therefore use ``"class"``. Child nodes must be supplied as the top-level
    ``children=`` kwarg (a "children" key inside data is ignored by Node.__init__).
    """

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.static_info_mock = MagicMock()
        self.visitor = DefaultTextVisitor(self.static_info_mock, "TestActivity")

    def test_visit_node_early_return_when_already_processed(self):
        """visit_node returns immediately when the node id is already tracked.

        Basis Path Testing: exercises the early-return branch (the ``node_id in
        self.processed_parents`` guard) that the existing
        ``test_visit_node_already_processed`` misses because it seeds a literal
        id string rather than the COMPUTED ``unique_identifier`` property.
        """
        child = Node(data={"class": "android.widget.TextView"})
        node = Node(
            data={"class": "android.widget.LinearLayout", "clickable": True},
            children=[child],
        )
        # Seed the REAL computed identifier so the guard actually fires.
        self.visitor.processed_parents.add(node.unique_identifier)

        initial_count = len(self.visitor.items)
        self.visitor.visit_node(node)

        assert len(self.visitor.items) == initial_count

    def test_visit_leaf_node_excludes_system_button(self):
        """visit_leaf_node drops nodes flagged as system navigation buttons.

        Equivalence Partitioning: a resource_id containing 'back' falls in the
        'system button' class, which should_exclude_system_button rejects before
        any item is produced.
        """
        leaf = Node(
            data={
                "class": "android.widget.Button",
                "resource_id": "back_button",
                "clickable": True,
            }
        )
        assert self.visitor.should_exclude_system_button(leaf) is True

        initial_count = len(self.visitor.items)
        self.visitor.visit_leaf_node(leaf)

        assert len(self.visitor.items) == initial_count

    def test_visit_button_annotates_mop_reachability(self):
        """visit_button copies MOP reachability from the matched widget's event.

        Traceability to Requirements: ItemAction.reaches_target /
        directly_reaches_target carry MOP-tracking info (rv-screen-parser
        CLAUDE.md). Here the matched widget exposes a CLICK event whose method
        reaches (but does not directly reach) a monitored operation, so the
        produced CLICK action must reflect reaches_target=True,
        directly_reaches_target=False.
        """
        event = MagicMock()
        event.type = WidgetEventType.CLICK
        event.signature = "sig()"
        widget = MagicMock()
        widget.id = "w1"
        widget.events = [event]

        self.visitor.find_matching_widget = MagicMock(return_value=widget)
        self.visitor._check_method_reaches_target = MagicMock(return_value=True)
        self.visitor._check_method_directly_reaches_target = MagicMock(
            return_value=False
        )

        node = Node(
            data={
                "class": "android.widget.Button",
                "clickable": True,
                "text": "Submit",
            }
        )
        self.visitor.visit_button(node)

        item = self.visitor.items[-1]
        assert len(item.actions) >= 1
        click = item.actions[0]
        assert click.reaches_target is True
        assert click.directly_reaches_target is False

    def test_visit_button_actions_none_defaults_to_empty_list(self):
        """visit_button tolerates get_possible_actions returning None.

        Robustness / Boundary Value: when the action generator yields None, the
        else-branch must substitute an empty list so the ScreenItem is still
        well-formed with actions == [].
        """
        self.visitor.get_possible_actions = MagicMock(return_value=None)

        node = Node(data={"class": "android.widget.Button", "clickable": True})
        self.visitor.visit_button(node)

        item = self.visitor.items[-1]
        assert item.actions == []

    def test_visit_spinner_reports_selected_child_item(self):
        """visit_spinner names the first child as the selected item.

        The spinner's first child supplies the 'with selected item' text. No
        resource_id is set, so find_matching_widget returns None and the
        options branch is skipped, isolating the selected-item path.
        """
        child = Node(data={"class": "android.widget.TextView", "text": "Opt A"})
        node = Node(data={"class": "android.widget.Spinner"}, children=[child])

        self.visitor.visit_spinner(node)

        item = self.visitor.items[-1]
        assert "selected item" in item.base_description
        assert "Opt A" in item.base_description

    def test_visit_spinner_summarizes_more_than_five_options(self):
        """visit_spinner truncates entry lists longer than five options.

        Boundary Value Analysis: with 7 entries (> 5), the description lists the
        first five and appends an 'and N more options' summary.
        """
        widget = MagicMock()
        widget.entries = ["a", "b", "c", "d", "e", "f", "g"]
        self.visitor.find_matching_widget = MagicMock(return_value=widget)

        node = Node(data={"class": "android.widget.Spinner"})
        self.visitor.visit_spinner(node)

        item = self.visitor.items[-1]
        assert "more options" in item.base_description

    def test_visit_radio_group_actionable_with_multiple_buttons(self):
        """visit_radio_group emits a group item plus a single grouped action set.

        Covers both the actionable-group branch (a 'Radio button group' item)
        and the multi-button aggregation branch: one grouped ScreenItem whose
        action count equals the number of radio buttons, with every radio
        button's unique_identifier recorded in processed_parents. One child
        carries text ('Yes') and the other does not, exercising both the
        SELECT-with-text and SELECT-option-N naming branches.
        """
        c1 = Node(
            data={
                "class": "android.widget.RadioButton",
                "text": "Yes",
                "bounds": [[0, 0], [10, 10]],
            }
        )
        c2 = Node(
            data={
                "class": "android.widget.RadioButton",
                "bounds": [[20, 0], [30, 10]],
            }
        )
        node = Node(
            data={"class": "android.widget.RadioGroup", "clickable": True},
            children=[c1, c2],
        )

        self.visitor.visit_radio_group(node)

        grouped = self.visitor.items[-1]
        assert len(grouped.actions) == 2
        assert c1.unique_identifier in self.visitor.processed_parents
        assert c2.unique_identifier in self.visitor.processed_parents

    def test_visit_radio_group_single_button_delegates_to_child(self):
        """visit_radio_group with <=1 radio button visits children individually.

        With a single RadioButton child and a non-actionable group, the
        aggregation branch is skipped and the else-branch dispatches each child
        via accept(), which routes to visit_radio_button and appends an item.
        """
        child = Node(
            data={
                "class": "android.widget.RadioButton",
                "text": "Only",
                "bounds": [[0, 0], [10, 10]],
            }
        )
        node = Node(data={"class": "android.widget.RadioGroup"}, children=[child])

        initial_count = len(self.visitor.items)
        self.visitor.visit_radio_group(node)

        assert len(self.visitor.items) > initial_count

    def test_visit_slider_without_bounds_uses_click_fallback(self):
        """visit_slider falls back to a single CLICK when bounds are unavailable.

        Boundary Value: an empty bounds list makes the DRAG-position path
        unreachable, so exactly one CLICK action is produced and the description
        still reports the current progress percentage.
        """
        node = Node(
            data={
                "class": "android.widget.SeekBar",
                "bounds": [],
                "progress": 50,
                "max": 100,
            }
        )

        self.visitor.visit_slider(node)

        item = self.visitor.items[-1]
        assert len(item.actions) == 1
        assert item.actions[0].event == WidgetEventType.CLICK
        assert item.base_description.startswith("Slider currently at")

    def test_has_action_by_type_returns_true_after_system_injection(self):
        """_has_action_by_type finds an injected system action by its type.

        get_screen_description injects SYSTEM_BACK via
        _ensure_standard_system_actions; the subsequent lookup for the BACK
        system action type must then return True.
        """
        self.visitor.get_screen_description()

        assert self.visitor._has_action_by_type(SystemActionType.BACK) is True
