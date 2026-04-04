"""
Unit tests for ExplorationStrategy base class.

Tests helper methods like _get_action_signature, _has_mop_marker,
_is_direct_mop, and _try_generate_text_input.
"""

from unittest.mock import MagicMock, patch

import pytest
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.strategies.dfs_strategy import DFSStrategy
from rv_screen_parser.parser.screen.visitor.model import ItemAction, ScreenDescription


class TestGetActionSignature:
    """Test _get_action_signature method."""

    @pytest.fixture
    def strategy(self):
        graph = DynamicStateGraph()
        return DFSStrategy(graph=graph)

    def test_signature_with_bounds(self, strategy):
        """Generate signature from action bounds."""
        action = MagicMock(spec=ItemAction)
        action.bounds = [(100, 200), (300, 400)]
        action.action_type = "click"

        signature = strategy._get_action_signature(action)

        # Center: (100+300)/2=200, (200+400)/2=300
        assert signature == ((200, 300), "click")

    def test_signature_without_bounds(self, strategy):
        """Fallback to (0,0) when no bounds."""
        action = MagicMock(spec=ItemAction)
        action.bounds = None
        action.action_type = "click"

        signature = strategy._get_action_signature(action)

        assert signature == ((0, 0), "click")

    def test_signature_with_empty_bounds(self, strategy):
        """Fallback to (0,0) when bounds is empty list."""
        action = MagicMock(spec=ItemAction)
        action.bounds = []
        action.action_type = "click"

        signature = strategy._get_action_signature(action)

        assert signature == ((0, 0), "click")

    def test_signature_with_incomplete_bounds(self, strategy):
        """Fallback to (0,0) when bounds has only one point."""
        action = MagicMock(spec=ItemAction)
        action.bounds = [(100, 200)]
        action.action_type = "click"

        signature = strategy._get_action_signature(action)

        assert signature == ((0, 0), "click")


class TestHasMopMarker:
    """Test _has_mop_marker method."""

    @pytest.fixture
    def strategy(self):
        graph = DynamicStateGraph()
        return DFSStrategy(graph=graph)

    def test_has_direct_mop(self, strategy):
        """Action with directly_reaches_mop returns True."""
        action = MagicMock(spec=ItemAction)
        action.directly_reaches_mop = True
        action.reaches_mop = False

        assert strategy._has_mop_marker(action) is True

    def test_has_transitive_mop(self, strategy):
        """Action with reaches_mop returns True."""
        action = MagicMock(spec=ItemAction)
        action.directly_reaches_mop = False
        action.reaches_mop = True

        assert strategy._has_mop_marker(action) is True

    def test_has_both_mop(self, strategy):
        """Action with both MOP markers returns True."""
        action = MagicMock(spec=ItemAction)
        action.directly_reaches_mop = True
        action.reaches_mop = True

        assert strategy._has_mop_marker(action) is True

    def test_no_mop(self, strategy):
        """Action without MOP markers returns False."""
        action = MagicMock(spec=ItemAction)
        action.directly_reaches_mop = False
        action.reaches_mop = False

        assert strategy._has_mop_marker(action) is False

    def test_missing_mop_attributes(self, strategy):
        """Action without MOP attributes returns False."""
        action = MagicMock(spec=["id", "text"])

        assert strategy._has_mop_marker(action) is False


class TestIsDirectMop:
    """Test _is_direct_mop method."""

    @pytest.fixture
    def strategy(self):
        graph = DynamicStateGraph()
        return DFSStrategy(graph=graph)

    def test_is_direct_mop_true(self, strategy):
        """Action with directly_reaches_mop returns True."""
        action = MagicMock(spec=ItemAction)
        action.directly_reaches_mop = True

        assert strategy._is_direct_mop(action) is True

    def test_is_direct_mop_false(self, strategy):
        """Action without directly_reaches_mop returns False."""
        action = MagicMock(spec=ItemAction)
        action.directly_reaches_mop = False

        assert strategy._is_direct_mop(action) is False

    def test_missing_direct_mop_attribute(self, strategy):
        """Action without attribute returns False."""
        action = MagicMock(spec=["id", "text"])

        assert strategy._is_direct_mop(action) is False


class TestTryGenerateTextInput:
    """Test _try_generate_text_input method."""

    @pytest.fixture
    def strategy(self):
        graph = DynamicStateGraph()
        return DFSStrategy(graph=graph)

    @pytest.fixture
    def screen_desc_with_edittext(self):
        """Create screen description with EditText."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            "class": "android.widget.EditText",
            "bounds": [(100, 200), (400, 300)],
            "resource_id": "com.example/email_input",
            "content_desc": "",
            "hint": "Enter email",
            "text": "",
        }

        screen_desc.items = [item]
        return screen_desc

    def test_probability_gate_blocks(self, strategy, screen_desc_with_edittext):
        """Text input not generated when random > probability."""
        screen_desc = screen_desc_with_edittext
        node = MagicMock()
        node.executed_actions = set()

        with patch("random.random", return_value=0.5):  # > 0.2
            result = strategy._try_generate_text_input(
                screen_desc, node, probability=0.2
            )

        assert result is None

    def test_email_hint_generates_email(self, strategy):
        """Email hint generates test email."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            "class": "android.widget.EditText",
            "bounds": [(100, 200), (400, 300)],
            "resource_id": "email",
            "content_desc": "",
            "hint": "",
            "text": "",
        }
        screen_desc.items = [item]

        node = MagicMock()
        node.executed_actions = set()

        with patch("random.random", return_value=0.1):  # < 0.2
            result = strategy._try_generate_text_input(
                screen_desc, node, probability=0.2
            )

        assert result is not None
        assert "test@example.com" in result.text

    def test_password_hint_generates_password(self, strategy):
        """Password hint generates test password."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            "class": "android.widget.EditText",
            "bounds": [(100, 200), (400, 300)],
            "resource_id": "password",
            "content_desc": "",
            "hint": "",
            "text": "",
        }
        screen_desc.items = [item]

        node = MagicMock()
        node.executed_actions = set()

        with patch("random.random", return_value=0.1):
            result = strategy._try_generate_text_input(
                screen_desc, node, probability=0.2
            )

        assert result is not None
        assert "Test123!" in result.text

    def test_name_hint_generates_username(self, strategy):
        """Name/username hint generates test username."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            "class": "android.widget.EditText",
            "bounds": [(100, 200), (400, 300)],
            "resource_id": "username",
            "content_desc": "",
            "hint": "",
            "text": "",
        }
        screen_desc.items = [item]

        node = MagicMock()
        node.executed_actions = set()

        with patch("random.random", return_value=0.1):
            result = strategy._try_generate_text_input(
                screen_desc, node, probability=0.2
            )

        assert result is not None
        assert "TestUser" in result.text

    def test_phone_hint_generates_phone(self, strategy):
        """Phone hint generates test phone number."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            "class": "android.widget.EditText",
            "bounds": [(100, 200), (400, 300)],
            "resource_id": "phone",
            "content_desc": "",
            "hint": "",
            "text": "",
        }
        screen_desc.items = [item]

        node = MagicMock()
        node.executed_actions = set()

        with patch("random.random", return_value=0.1):
            result = strategy._try_generate_text_input(
                screen_desc, node, probability=0.2
            )

        assert result is not None
        assert "5511999999999" in result.text

    def test_search_hint_generates_search(self, strategy):
        """Search hint generates test search text."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            "class": "android.widget.EditText",
            "bounds": [(100, 200), (400, 300)],
            "resource_id": "search_box",
            "content_desc": "",
            "hint": "",
            "text": "",
        }
        screen_desc.items = [item]

        node = MagicMock()
        node.executed_actions = set()

        with patch("random.random", return_value=0.1):
            result = strategy._try_generate_text_input(
                screen_desc, node, probability=0.2
            )

        assert result is not None
        assert "test" in result.text

    def test_url_hint_generates_url(self, strategy):
        """URL hint generates test URL."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            "class": "android.widget.EditText",
            "bounds": [(100, 200), (400, 300)],
            "resource_id": "url_input",
            "content_desc": "",
            "hint": "",
            "text": "",
        }
        screen_desc.items = [item]

        node = MagicMock()
        node.executed_actions = set()

        with patch("random.random", return_value=0.1):
            result = strategy._try_generate_text_input(
                screen_desc, node, probability=0.2
            )

        assert result is not None
        assert "https://example.com" in result.text

    def test_number_hint_generates_number(self, strategy):
        """Number hint generates test number."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            "class": "android.widget.EditText",
            "bounds": [(100, 200), (400, 300)],
            "resource_id": "number_input",
            "content_desc": "",
            "hint": "",
            "text": "",
        }
        screen_desc.items = [item]

        node = MagicMock()
        node.executed_actions = set()

        with patch("random.random", return_value=0.1):
            result = strategy._try_generate_text_input(
                screen_desc, node, probability=0.2
            )

        assert result is not None
        assert "123" in result.text

    def test_message_hint_generates_message(self, strategy):
        """Message hint generates test message."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            "class": "android.widget.EditText",
            "bounds": [(100, 200), (400, 300)],
            "resource_id": "comment",
            "content_desc": "",
            "hint": "note",
            "text": "",
        }
        screen_desc.items = [item]

        node = MagicMock()
        node.executed_actions = set()

        with patch("random.random", return_value=0.1):
            result = strategy._try_generate_text_input(
                screen_desc, node, probability=0.2
            )

        assert result is not None
        assert "Test message" in result.text

    def test_generic_hint_generates_default(self, strategy):
        """Unknown hint generates default test text."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            "class": "android.widget.EditText",
            "bounds": [(100, 200), (400, 300)],
            "resource_id": "random_field",
            "content_desc": "",
            "hint": "",
            "text": "",
        }
        screen_desc.items = [item]

        node = MagicMock()
        node.executed_actions = set()

        with patch("random.random", return_value=0.1):
            result = strategy._try_generate_text_input(
                screen_desc, node, probability=0.2
            )

        assert result is not None
        assert "test123" in result.text

    def test_no_edittext_fields(self, strategy):
        """Returns None when no EditText fields."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            "class": "android.widget.Button",
            "bounds": [(100, 200), (400, 300)],
        }
        screen_desc.items = [item]

        node = MagicMock()
        node.executed_actions = set()

        with patch("random.random", return_value=0.1):
            result = strategy._try_generate_text_input(
                screen_desc, node, probability=0.2
            )

        assert result is None

    def test_autocompletetextview_supported(self, strategy):
        """AutoCompleteTextView is also supported."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            "class": "android.widget.AutoCompleteTextView",
            "bounds": [(100, 200), (400, 300)],
            "resource_id": "search",
            "content_desc": "",
            "hint": "",
            "text": "",
        }
        screen_desc.items = [item]

        node = MagicMock()
        node.executed_actions = set()

        with patch("random.random", return_value=0.1):
            result = strategy._try_generate_text_input(
                screen_desc, node, probability=0.2
            )

        assert result is not None

    def test_already_executed_edittext_skipped(self, strategy):
        """EditText already executed is skipped."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            "class": "android.widget.EditText",
            "bounds": [(100, 200), (400, 300)],
            "resource_id": "email",
            "content_desc": "",
            "hint": "",
            "text": "",
        }
        screen_desc.items = [item]

        # Calculate center: (100+400)/2 = 250, (200+300)/2 = 250
        # Convert to optimized space
        from rv_agent.services import coordinate_utils

        opt_x, opt_y = coordinate_utils.device_to_optimized(
            250, 250, (1080, 1920), (704, 1248)
        )

        node = MagicMock()
        # Use calculated optimized coordinates
        node.executed_actions = {((opt_x, opt_y), "SET_TEXT")}

        with patch("random.random", return_value=0.1):
            result = strategy._try_generate_text_input(
                screen_desc, node, probability=0.2
            )

        assert result is None

    def test_edittext_without_bounds_skipped(self, strategy):
        """EditText without bounds is skipped."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            "class": "android.widget.EditText",
            "bounds": None,
            "resource_id": "email",
            "content_desc": "",
            "hint": "",
            "text": "",
        }
        screen_desc.items = [item]

        node = MagicMock()
        node.executed_actions = set()

        with patch("random.random", return_value=0.1):
            result = strategy._try_generate_text_input(
                screen_desc, node, probability=0.2
            )

        assert result is None


# =============================================================================
# Scrollable Container Detection Tests
# =============================================================================


class TestDetectScrollableContainers:
    """Test _detect_scrollable_containers method."""

    @pytest.fixture
    def strategy(self):
        graph = DynamicStateGraph()
        return DFSStrategy(graph=graph)

    def test_detect_recycler_view(self, strategy):
        """Detects RecyclerView as vertical scrollable."""
        screen_desc = MagicMock(spec=ScreenDescription)
        item = MagicMock()
        item.view = {
            "class": "androidx.recyclerview.widget.RecyclerView",
            "bounds": [[0, 100], [1080, 1800]],
            "scrollable": True,
            "resource_id": "list_container",
        }
        screen_desc.items = [item]

        scrollables = strategy._detect_scrollable_containers(screen_desc)

        assert len(scrollables) == 1
        assert scrollables[0]["scrollable_type"] == "RecyclerView"
        assert scrollables[0]["direction"] == "vertical"
        assert scrollables[0]["center"] == (540, 950)

    def test_detect_horizontal_scroll_view(self, strategy):
        """Detects HorizontalScrollView as horizontal scrollable."""
        screen_desc = MagicMock(spec=ScreenDescription)
        item = MagicMock()
        item.view = {
            "class": "android.widget.HorizontalScrollView",
            "bounds": [[0, 500], [1080, 700]],
            "scrollable": True,
            "resource_id": "horizontal_container",
        }
        screen_desc.items = [item]

        scrollables = strategy._detect_scrollable_containers(screen_desc)

        assert len(scrollables) == 1
        assert scrollables[0]["scrollable_type"] == "HorizontalScrollView"
        assert scrollables[0]["direction"] == "horizontal"

    def test_detect_list_view(self, strategy):
        """Detects ListView as vertical scrollable."""
        screen_desc = MagicMock(spec=ScreenDescription)
        item = MagicMock()
        item.view = {
            "class": "android.widget.ListView",
            "bounds": [[0, 200], [1080, 1600]],
            "scrollable": True,
            "resource_id": "list_view",
        }
        screen_desc.items = [item]

        scrollables = strategy._detect_scrollable_containers(screen_desc)

        assert len(scrollables) == 1
        assert scrollables[0]["scrollable_type"] == "ListView"
        assert scrollables[0]["direction"] == "vertical"

    def test_detect_scroll_view(self, strategy):
        """Detects ScrollView as vertical scrollable."""
        screen_desc = MagicMock(spec=ScreenDescription)
        item = MagicMock()
        item.view = {
            "class": "android.widget.ScrollView",
            "bounds": [[0, 100], [1080, 1900]],
            "scrollable": True,
            "resource_id": "scroll_view",
        }
        screen_desc.items = [item]

        scrollables = strategy._detect_scrollable_containers(screen_desc)

        assert len(scrollables) == 1
        assert scrollables[0]["scrollable_type"] == "ScrollView"
        assert scrollables[0]["direction"] == "vertical"

    def test_detect_nested_scroll_view(self, strategy):
        """Detects NestedScrollView as vertical scrollable."""
        screen_desc = MagicMock(spec=ScreenDescription)
        item = MagicMock()
        item.view = {
            "class": "androidx.core.widget.NestedScrollView",
            "bounds": [[0, 100], [1080, 1900]],
            "scrollable": True,
            "resource_id": "nested_scroll",
        }
        screen_desc.items = [item]

        scrollables = strategy._detect_scrollable_containers(screen_desc)

        assert len(scrollables) == 1
        assert scrollables[0]["scrollable_type"] == "NestedScrollView"
        assert scrollables[0]["direction"] == "vertical"

    def test_detect_view_pager(self, strategy):
        """Detects ViewPager as horizontal scrollable."""
        screen_desc = MagicMock(spec=ScreenDescription)
        item = MagicMock()
        item.view = {
            "class": "androidx.viewpager.widget.ViewPager",
            "bounds": [[0, 200], [1080, 800]],
            "scrollable": True,
            "resource_id": "view_pager",
        }
        screen_desc.items = [item]

        scrollables = strategy._detect_scrollable_containers(screen_desc)

        assert len(scrollables) == 1
        assert scrollables[0]["scrollable_type"] == "ViewPager"
        assert scrollables[0]["direction"] == "horizontal"

    def test_detect_by_scrollable_attribute(self, strategy):
        """Detects scrollable by attribute when type not recognized."""
        screen_desc = MagicMock(spec=ScreenDescription)
        item = MagicMock()
        item.view = {
            "class": "com.custom.ScrollableWidget",
            "bounds": [[0, 100], [1080, 1800]],
            "scrollable": True,
            "resource_id": "custom_scroll",
        }
        screen_desc.items = [item]

        scrollables = strategy._detect_scrollable_containers(screen_desc)

        assert len(scrollables) == 1
        assert scrollables[0]["scrollable_type"] == "scrollable"
        assert scrollables[0]["direction"] == "vertical"

    def test_skip_small_containers(self, strategy):
        """Skips containers smaller than 100x100."""
        screen_desc = MagicMock(spec=ScreenDescription)
        item = MagicMock()
        item.view = {
            "class": "android.widget.ScrollView",
            "bounds": [[0, 0], [50, 50]],  # Too small
            "scrollable": True,
            "resource_id": "tiny_scroll",
        }
        screen_desc.items = [item]

        scrollables = strategy._detect_scrollable_containers(screen_desc)

        assert len(scrollables) == 0

    def test_no_scrollables_detected(self, strategy):
        """Returns empty list when no scrollable containers."""
        screen_desc = MagicMock(spec=ScreenDescription)
        item = MagicMock()
        item.view = {
            "class": "android.widget.Button",
            "bounds": [[100, 100], [300, 200]],
            "scrollable": False,
            "resource_id": "btn",
        }
        screen_desc.items = [item]

        scrollables = strategy._detect_scrollable_containers(screen_desc)

        assert len(scrollables) == 0

    def test_multiple_scrollables(self, strategy):
        """Detects multiple scrollable containers."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item1 = MagicMock()
        item1.view = {
            "class": "android.widget.ListView",
            "bounds": [[0, 100], [540, 900]],
            "scrollable": True,
            "resource_id": "list1",
        }

        item2 = MagicMock()
        item2.view = {
            "class": "android.widget.HorizontalScrollView",
            "bounds": [[0, 950], [1080, 1100]],
            "scrollable": True,
            "resource_id": "horizontal1",
        }

        screen_desc.items = [item1, item2]

        scrollables = strategy._detect_scrollable_containers(screen_desc)

        assert len(scrollables) == 2


# =============================================================================
# Scroll Action Generation Tests
# =============================================================================


class TestTryGenerateScrollAction:
    """Test _try_generate_scroll_action method."""

    @pytest.fixture
    def strategy(self):
        graph = DynamicStateGraph()
        return DFSStrategy(graph=graph)

    @pytest.fixture
    def mock_node(self):
        node = MagicMock()
        node.screen_hash = "test_hash"
        return node

    def test_generates_scroll_when_scrollable_exists(self, strategy, mock_node):
        """Generates scroll action when scrollable container exists."""
        screen_desc = MagicMock(spec=ScreenDescription)
        item = MagicMock()
        item.view = {
            "class": "android.widget.RecyclerView",
            "bounds": [[0, 100], [1080, 1800]],
            "scrollable": True,
            "resource_id": "list",
        }
        screen_desc.items = [item]

        scrolled_positions = set()

        with patch("random.random", return_value=0.1):
            action = strategy._try_generate_scroll_action(
                screen_desc, mock_node, scrolled_positions, probability=0.3
            )

        assert action is not None
        assert action.text == "SWIPE (vertical)"
        assert "swipe_start" in action.target_view
        assert "swipe_end" in action.target_view

    def test_no_scroll_when_probability_fails(self, strategy, mock_node):
        """Returns None when probability check fails."""
        screen_desc = MagicMock(spec=ScreenDescription)
        item = MagicMock()
        item.view = {
            "class": "android.widget.RecyclerView",
            "bounds": [[0, 100], [1080, 1800]],
            "scrollable": True,
            "resource_id": "list",
        }
        screen_desc.items = [item]

        scrolled_positions = set()

        with patch("random.random", return_value=0.9):
            action = strategy._try_generate_scroll_action(
                screen_desc, mock_node, scrolled_positions, probability=0.3
            )

        assert action is None

    def test_no_scroll_when_no_scrollables(self, strategy, mock_node):
        """Returns None when no scrollable containers."""
        screen_desc = MagicMock(spec=ScreenDescription)
        item = MagicMock()
        item.view = {
            "class": "android.widget.Button",
            "bounds": [[100, 100], [300, 200]],
            "scrollable": False,
            "resource_id": "btn",
        }
        screen_desc.items = [item]

        scrolled_positions = set()

        with patch("random.random", return_value=0.1):
            action = strategy._try_generate_scroll_action(
                screen_desc, mock_node, scrolled_positions, probability=0.3
            )

        assert action is None

    def test_no_scroll_when_already_scrolled(self, strategy, mock_node):
        """Returns None when container already scrolled."""
        screen_desc = MagicMock(spec=ScreenDescription)
        item = MagicMock()
        item.view = {
            "class": "android.widget.RecyclerView",
            "bounds": [[0, 100], [1080, 1800]],
            "scrollable": True,
            "resource_id": "list",
        }
        screen_desc.items = [item]

        # Mark as already scrolled
        container_id = f"list|[[0, 100], [1080, 1800]]"
        scrolled_positions = {("test_hash", container_id, "vertical")}

        with patch("random.random", return_value=0.1):
            action = strategy._try_generate_scroll_action(
                screen_desc, mock_node, scrolled_positions, probability=0.3
            )

        assert action is None

    def test_scroll_marks_position_as_scrolled(self, strategy, mock_node):
        """Scroll action marks position in scrolled_positions set."""
        screen_desc = MagicMock(spec=ScreenDescription)
        item = MagicMock()
        item.view = {
            "class": "android.widget.RecyclerView",
            "bounds": [[0, 100], [1080, 1800]],
            "scrollable": True,
            "resource_id": "list",
        }
        screen_desc.items = [item]

        scrolled_positions = set()

        with patch("random.random", return_value=0.1):
            action = strategy._try_generate_scroll_action(
                screen_desc, mock_node, scrolled_positions, probability=0.3
            )

        assert action is not None
        assert len(scrolled_positions) == 1

    def test_horizontal_scroll_coordinates(self, strategy, mock_node):
        """Horizontal scroll generates correct swipe coordinates."""
        screen_desc = MagicMock(spec=ScreenDescription)
        item = MagicMock()
        item.view = {
            "class": "android.widget.HorizontalScrollView",
            "bounds": [[0, 500], [1080, 700]],
            "scrollable": True,
            "resource_id": "horizontal",
        }
        screen_desc.items = [item]

        scrolled_positions = set()

        with patch("random.random", return_value=0.1):
            action = strategy._try_generate_scroll_action(
                screen_desc, mock_node, scrolled_positions, probability=0.3
            )

        assert action is not None
        assert action.text == "SWIPE (horizontal)"
        # Horizontal: start_x > end_x (swipe left)
        start_x = action.target_view["swipe_start"][0]
        end_x = action.target_view["swipe_end"][0]
        assert start_x > end_x
