"""
Unit tests for ExplorationStrategy base class.

Tests helper methods like _get_action_signature, _has_mop_marker,
_is_direct_mop, and _try_generate_text_input.
"""

import pytest
from unittest.mock import MagicMock, patch

from rv_agent.strategies.base_strategy import ExplorationStrategy
from rv_agent.strategies.dfs_strategy import DFSStrategy
from rv_agent.core.dynamic_state_graph import DynamicStateGraph
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription, ItemAction


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
        action = MagicMock(spec=['id', 'text'])

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
        action = MagicMock(spec=['id', 'text'])

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
            'class': 'android.widget.EditText',
            'bounds': [(100, 200), (400, 300)],
            'resource_id': 'com.example/email_input',
            'content_desc': '',
            'hint': 'Enter email',
            'text': ''
        }

        screen_desc.items = [item]
        return screen_desc

    def test_probability_gate_blocks(self, strategy, screen_desc_with_edittext):
        """Text input not generated when random > probability."""
        screen_desc = screen_desc_with_edittext
        node = MagicMock()
        node.executed_actions = set()

        with patch('random.random', return_value=0.5):  # > 0.2
            result = strategy._try_generate_text_input(screen_desc, node, probability=0.2)

        assert result is None

    def test_email_hint_generates_email(self, strategy):
        """Email hint generates test email."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            'class': 'android.widget.EditText',
            'bounds': [(100, 200), (400, 300)],
            'resource_id': 'email',
            'content_desc': '',
            'hint': '',
            'text': ''
        }
        screen_desc.items = [item]

        node = MagicMock()
        node.executed_actions = set()

        with patch('random.random', return_value=0.1):  # < 0.2
            result = strategy._try_generate_text_input(screen_desc, node, probability=0.2)

        assert result is not None
        assert "test@example.com" in result.text

    def test_password_hint_generates_password(self, strategy):
        """Password hint generates test password."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            'class': 'android.widget.EditText',
            'bounds': [(100, 200), (400, 300)],
            'resource_id': 'password',
            'content_desc': '',
            'hint': '',
            'text': ''
        }
        screen_desc.items = [item]

        node = MagicMock()
        node.executed_actions = set()

        with patch('random.random', return_value=0.1):
            result = strategy._try_generate_text_input(screen_desc, node, probability=0.2)

        assert result is not None
        assert "Test123!" in result.text

    def test_name_hint_generates_username(self, strategy):
        """Name/username hint generates test username."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            'class': 'android.widget.EditText',
            'bounds': [(100, 200), (400, 300)],
            'resource_id': 'username',
            'content_desc': '',
            'hint': '',
            'text': ''
        }
        screen_desc.items = [item]

        node = MagicMock()
        node.executed_actions = set()

        with patch('random.random', return_value=0.1):
            result = strategy._try_generate_text_input(screen_desc, node, probability=0.2)

        assert result is not None
        assert "TestUser" in result.text

    def test_phone_hint_generates_phone(self, strategy):
        """Phone hint generates test phone number."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            'class': 'android.widget.EditText',
            'bounds': [(100, 200), (400, 300)],
            'resource_id': 'phone',
            'content_desc': '',
            'hint': '',
            'text': ''
        }
        screen_desc.items = [item]

        node = MagicMock()
        node.executed_actions = set()

        with patch('random.random', return_value=0.1):
            result = strategy._try_generate_text_input(screen_desc, node, probability=0.2)

        assert result is not None
        assert "5511999999999" in result.text

    def test_search_hint_generates_search(self, strategy):
        """Search hint generates test search text."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            'class': 'android.widget.EditText',
            'bounds': [(100, 200), (400, 300)],
            'resource_id': 'search_box',
            'content_desc': '',
            'hint': '',
            'text': ''
        }
        screen_desc.items = [item]

        node = MagicMock()
        node.executed_actions = set()

        with patch('random.random', return_value=0.1):
            result = strategy._try_generate_text_input(screen_desc, node, probability=0.2)

        assert result is not None
        assert "test" in result.text

    def test_url_hint_generates_url(self, strategy):
        """URL hint generates test URL."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            'class': 'android.widget.EditText',
            'bounds': [(100, 200), (400, 300)],
            'resource_id': 'url_input',
            'content_desc': '',
            'hint': '',
            'text': ''
        }
        screen_desc.items = [item]

        node = MagicMock()
        node.executed_actions = set()

        with patch('random.random', return_value=0.1):
            result = strategy._try_generate_text_input(screen_desc, node, probability=0.2)

        assert result is not None
        assert "https://example.com" in result.text

    def test_number_hint_generates_number(self, strategy):
        """Number hint generates test number."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            'class': 'android.widget.EditText',
            'bounds': [(100, 200), (400, 300)],
            'resource_id': 'number_input',
            'content_desc': '',
            'hint': '',
            'text': ''
        }
        screen_desc.items = [item]

        node = MagicMock()
        node.executed_actions = set()

        with patch('random.random', return_value=0.1):
            result = strategy._try_generate_text_input(screen_desc, node, probability=0.2)

        assert result is not None
        assert "123" in result.text

    def test_message_hint_generates_message(self, strategy):
        """Message hint generates test message."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            'class': 'android.widget.EditText',
            'bounds': [(100, 200), (400, 300)],
            'resource_id': 'comment',
            'content_desc': '',
            'hint': 'note',
            'text': ''
        }
        screen_desc.items = [item]

        node = MagicMock()
        node.executed_actions = set()

        with patch('random.random', return_value=0.1):
            result = strategy._try_generate_text_input(screen_desc, node, probability=0.2)

        assert result is not None
        assert "Test message" in result.text

    def test_generic_hint_generates_default(self, strategy):
        """Unknown hint generates default test text."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            'class': 'android.widget.EditText',
            'bounds': [(100, 200), (400, 300)],
            'resource_id': 'random_field',
            'content_desc': '',
            'hint': '',
            'text': ''
        }
        screen_desc.items = [item]

        node = MagicMock()
        node.executed_actions = set()

        with patch('random.random', return_value=0.1):
            result = strategy._try_generate_text_input(screen_desc, node, probability=0.2)

        assert result is not None
        assert "test123" in result.text

    def test_no_edittext_fields(self, strategy):
        """Returns None when no EditText fields."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            'class': 'android.widget.Button',
            'bounds': [(100, 200), (400, 300)]
        }
        screen_desc.items = [item]

        node = MagicMock()
        node.executed_actions = set()

        with patch('random.random', return_value=0.1):
            result = strategy._try_generate_text_input(screen_desc, node, probability=0.2)

        assert result is None

    def test_autocompletetextview_supported(self, strategy):
        """AutoCompleteTextView is also supported."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            'class': 'android.widget.AutoCompleteTextView',
            'bounds': [(100, 200), (400, 300)],
            'resource_id': 'search',
            'content_desc': '',
            'hint': '',
            'text': ''
        }
        screen_desc.items = [item]

        node = MagicMock()
        node.executed_actions = set()

        with patch('random.random', return_value=0.1):
            result = strategy._try_generate_text_input(screen_desc, node, probability=0.2)

        assert result is not None

    def test_already_executed_edittext_skipped(self, strategy):
        """EditText already executed is skipped."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            'class': 'android.widget.EditText',
            'bounds': [(100, 200), (400, 300)],
            'resource_id': 'email',
            'content_desc': '',
            'hint': '',
            'text': ''
        }
        screen_desc.items = [item]

        # Calculate center: (100+400)/2 = 250, (200+300)/2 = 250
        # Convert to optimized space
        from rv_agent.core import coordinate_utils
        opt_x, opt_y = coordinate_utils.device_to_optimized(
            250, 250,
            (1080, 1920),
            (704, 1248)
        )

        node = MagicMock()
        # Use calculated optimized coordinates
        node.executed_actions = {((opt_x, opt_y), "SET_TEXT")}

        with patch('random.random', return_value=0.1):
            result = strategy._try_generate_text_input(screen_desc, node, probability=0.2)

        assert result is None

    def test_edittext_without_bounds_skipped(self, strategy):
        """EditText without bounds is skipped."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            'class': 'android.widget.EditText',
            'bounds': None,
            'resource_id': 'email',
            'content_desc': '',
            'hint': '',
            'text': ''
        }
        screen_desc.items = [item]

        node = MagicMock()
        node.executed_actions = set()

        with patch('random.random', return_value=0.1):
            result = strategy._try_generate_text_input(screen_desc, node, probability=0.2)

        assert result is None
