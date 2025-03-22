# tests/llm/service/test_action_generator.py
import pytest
from unittest.mock import MagicMock, patch, ANY

from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.llm.service.action_generator import ActionGenerator
from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.screen.abstract_parser import AbstractScreenParser
from rvandroid.util.logging_manager import LoggingManager
from rvandroid.util.performance_monitor import PerformanceMonitor
from rvandroid.experiment.event_system import EventBus


class TestActionGenerator:
    """
    Tests for the ActionGenerator class which is responsible for transforming
    parsed LLM responses into executable test actions.

    The tests cover:
    - Basic initialization and configuration
    - Action creation from parsed responses
    - Fallback action generation
    - Format conversion between different action representations
    - Edge cases and error handling
    """

    @pytest.fixture
    def mock_event_bus(self):
        """Fixture providing a mock event bus instance"""
        mock = MagicMock(spec=EventBus)
        with patch('rvandroid.experiment.event_system.EventBus.get_instance', return_value=mock):
            yield mock

    @pytest.fixture
    def mock_performance_monitor(self):
        """Fixture providing a mock performance monitor instance"""
        mock = MagicMock(spec=PerformanceMonitor)
        with patch('rvandroid.util.performance_monitor.PerformanceMonitor.get_instance', return_value=mock):
            yield mock

    @pytest.fixture
    def mock_logging_manager(self):
        """Fixture providing a mock logging manager instance"""
        mock = MagicMock(spec=LoggingManager)
        mock_logger = MagicMock()
        mock.get_logger.return_value = mock_logger
        with patch('rvandroid.util.logging_manager.LoggingManager.get_instance', return_value=mock):
            yield mock

    @pytest.fixture
    def mock_configurator(self):
        """Fixture providing a mock component configurator"""
        mock = MagicMock(spec=ComponentConfigurator)
        mock_parser = MagicMock(spec=AbstractScreenParser)
        mock.create_parser.return_value = mock_parser
        return mock

    @pytest.fixture
    def mock_static_data(self):
        """Fixture providing a mock static analysis data instance"""
        return MagicMock(spec=StaticAnalysisData)

    @pytest.fixture
    def action_generator(self, mock_configurator, mock_static_data, mock_event_bus,
                         mock_performance_monitor, mock_logging_manager):
        """Fixture providing an ActionGenerator instance with mocks"""
        return ActionGenerator(mock_configurator, mock_static_data)

    def test_initialization(self, action_generator, mock_configurator, mock_static_data):
        """Test that the ActionGenerator initializes correctly with provided configurations"""
        assert action_generator.config == mock_configurator
        assert action_generator.static_data == mock_static_data
        assert action_generator.parser == mock_configurator.create_parser.return_value
        mock_configurator.create_parser.assert_called_once()

    def test_create_actions_success(self, action_generator):
        """Test that actions are correctly created from parsed data"""
        # Setup
        actions = [{"action_id": "1", "params": {}, "explanation": "Test action"}]
        state = {"activity": "TestActivity", "view_tree": {}}

        # Mock parser parse method to return a screen description with items and actions
        mock_item = MagicMock()
        mock_item.view = {"resource_id": "test_id", "bounds": [[10, 10], [20, 20]]}
        mock_action = MagicMock()
        mock_action.id = "1"
        mock_action.text = "CLICK test button"
        mock_action.target_view = {"resource_id": "test_id", "bounds": [[10, 10], [20, 20]]}
        mock_action.coordinates = (15, 15)
        mock_item.actions = [mock_action]

        mock_screen = MagicMock()
        mock_screen.items = [mock_item]

        action_generator.parser.parse.return_value = mock_screen

        # Execute
        result = action_generator.create_actions(actions, state)

        # Verify
        assert len(result) == 1
        assert result[0]["action_type"] == "click"
        assert result[0]["target"] == "test_id"
        assert "params" in result[0]
        assert "explanation" in result[0]
        assert "coordinates" in result[0]
        action_generator.parser.parse.assert_called_once_with(state, action_generator.static_data)

    def test_create_actions_empty_input(self, action_generator):
        """Test that fallback actions are generated when input actions list is empty"""
        # Setup
        state = {"activity": "TestActivity", "view_tree": {"clickable": True, "enabled": True, "visible": True,
                                                           "bounds": [[10, 10], [20, 20]],
                                                           "resource_id": "test_button"}}

        # Execute
        with patch.object(action_generator, 'generate_fallback_actions') as mock_fallback:
            mock_fallback.return_value = [{"action_type": "click", "target": "test_button", "params": {}}]
            result = action_generator.create_actions([], state)

        # Verify
        mock_fallback.assert_called_once_with(state)
        assert len(result) == 1
        assert result[0]["action_type"] == "click"

    def test_create_actions_parse_error(self, action_generator):
        """Test that fallback actions are generated when parsing fails"""
        # Setup
        actions = [{"action_id": "1", "params": {}, "explanation": "Test action"}]
        state = {"activity": "TestActivity"}

        action_generator.parser.parse.side_effect = Exception("Parse error")

        # Execute
        with patch.object(action_generator, 'generate_fallback_actions') as mock_fallback:
            mock_fallback.return_value = [{"action_type": "scroll", "target": "", "params": {"direction": "DOWN"}}]
            result = action_generator.create_actions(actions, state)

        # Verify
        mock_fallback.assert_called_once_with(state)
        assert len(result) == 1
        assert result[0]["action_type"] == "scroll"

    def test_generate_fallback_actions_with_view_tree(self, action_generator):
        """Test generation of fallback actions when view_tree is available"""
        # Setup
        state = {
            "view_tree": {
                "clickable": True,
                "enabled": True,
                "visible": True,
                "bounds": [[10, 10], [20, 20]],
                "resource_id": "test_id",
                "children": [
                    {
                        "clickable": True,
                        "enabled": True,
                        "visible": True,
                        "bounds": [[30, 30], [40, 40]],
                        "resource_id": "child_id"
                    }
                ]
            }
        }

        # Execute
        result = action_generator.generate_fallback_actions(state)

        # Verify
        assert len(result) > 0
        assert all(isinstance(action, dict) for action in result)
        assert all("action_type" in action for action in result)
        assert all("target" in action for action in result)
        assert all("params" in action for action in result)
        assert all("explanation" in action for action in result)

    def test_generate_fallback_actions_without_view_tree(self, action_generator):
        """Test generation of fallback actions when view_tree is not available"""
        # Setup
        state = {"activity": "TestActivity"}

        # Execute
        result = action_generator.generate_fallback_actions(state)

        # Verify
        assert len(result) == 1
        assert result[0]["action_type"] == "scroll"
        assert result[0]["params"]["direction"] == "DOWN"

    def test_extract_action_type(self, action_generator):
        """Test extraction of action type from action text"""
        test_cases = [
            ("CLICK button", "click"),
            ("LONG_CLICK button", "long_click"),
            ("SCROLL UP list", "scroll_up"),
            ("SCROLL DOWN list", "scroll_down"),
            ("SCROLL LEFT list", "scroll_left"),
            ("SCROLL RIGHT list", "scroll_right"),
            ("SCROLL list", "scroll"),
            ("SET_TEXT field value", "set_text"),
            ("CHECK checkbox", "click"),
            ("UNCHECK checkbox", "click"),
            ("BACK", "key_event"),
            ("RANDOM_ACTION", "unknown")
        ]

        for action_text, expected_type in test_cases:
            assert action_generator._extract_action_type(action_text) == expected_type

    def test_process_params_set_text(self, action_generator):
        """Test parameter processing for SET_TEXT action type"""
        # No text parameter provided
        params = action_generator._process_params("set_text", {})
        assert "text" in params
        assert params["text"] == "test input"

        # Text parameter already provided
        params = action_generator._process_params("set_text", {"text": "hello world"})
        assert params["text"] == "hello world"

    def test_process_params_key_event(self, action_generator):
        """Test parameter processing for KEY_EVENT action type"""
        # No name parameter provided
        params = action_generator._process_params("key_event", {})
        assert "name" in params
        assert params["name"] == "BACK"

        # Name parameter already provided
        params = action_generator._process_params("key_event", {"name": "HOME"})
        assert params["name"] == "HOME"

    def test_process_params_scroll(self, action_generator):
        """Test parameter processing for scroll action types"""
        scroll_types = ["scroll_up", "scroll_down", "scroll_left", "scroll_right"]

        for scroll_type in scroll_types:
            # No direction parameter provided
            params = action_generator._process_params(scroll_type, {})
            assert "direction" in params
            expected_direction = scroll_type.split('_')[1].upper()
            assert params["direction"] == expected_direction

            # Direction parameter already provided
            custom_direction = "CUSTOM"
            params = action_generator._process_params(scroll_type, {"direction": custom_direction})
            assert params["direction"] == custom_direction

    def test_resolve_coordinates_methods(self, action_generator):
        """Test various methods for resolving coordinates"""
        # Setup
        item_action = MagicMock()
        view_data = {"bounds": [[10, 10], [20, 20]]}
        state = {"activity": "TestActivity", "view_tree": {}}
        action_id = "1"

        # Test method 1: Use coordinates from ItemAction
        item_action.coordinates = (15, 15)
        coords = action_generator._resolve_coordinates(item_action, view_data, state, action_id)
        assert coords == (15, 15)

        # Test method 2: Extract from target_view
        item_action.coordinates = None
        item_action.target_view = {"bounds": [[30, 30], [40, 40]]}
        coords = action_generator._resolve_coordinates(item_action, view_data, state, action_id)
        assert coords == (35, 35)

        # Test method 3: Extract from view_data
        item_action.coordinates = None
        item_action.target_view = None
        coords = action_generator._resolve_coordinates(item_action, view_data, state, action_id)
        assert coords == (15, 15)

        # Test method 5: Extract from target string
        # Ensure no other method will succeed by setting everything to None or empty
        item_action.coordinates = None
        item_action.target_view = None
        empty_view_data = {}
        empty_state = {"activity": "TestActivity"}  # No view_tree

        # Mock _get_target to return a string with coordinates
        with patch.object(action_generator, '_get_target', return_value="25 25"):
            coords = action_generator._resolve_coordinates(item_action, empty_view_data, empty_state, action_id)
            assert coords == (25, 25)

    def test_convert_to_droidbot_format(self, action_generator):
        """Test conversion from action_id format to DroidBot format"""
        # Setup
        actions = [{"action_id": "1", "params": {}, "explanation": "Test action"}]
        state = {"activity": "TestActivity"}

        # Create mock screen description
        mock_item = MagicMock()
        mock_item.view = {"resource_id": "test_id", "bounds": [[10, 10], [20, 20]]}
        mock_action = MagicMock()
        mock_action.id = "1"
        mock_action.text = "CLICK test button"
        mock_action.target_view = {"resource_id": "test_id", "bounds": [[10, 10], [20, 20]]}
        mock_action.coordinates = (15, 15)
        mock_item.actions = [mock_action]

        mock_screen = MagicMock()
        mock_screen.items = [mock_item]

        # Execute
        result = action_generator._convert_to_droidbot_format(actions, state, mock_screen)

        # Verify
        assert len(result) == 1
        assert result[0]["action_type"] == "click"
        assert result[0]["target"] == "test_id"
        assert result[0]["explanation"] == "Test action"
        assert result[0]["coordinates"] == (15, 15)

    def test_find_coordinates_for_resource_id(self, action_generator):
        """Test finding coordinates for a given resource ID in the view tree"""
        # Setup
        view_tree = {
            "resource_id": "parent_id",
            "bounds": [[0, 0], [100, 100]],
            "children": [
                {
                    "resource_id": "test_id",
                    "bounds": [[10, 10], [20, 20]]
                },
                {
                    "resource_id": "app:id/test_id_partial",
                    "bounds": [[30, 30], [40, 40]]
                }
            ]
        }

        # Execute - direct match
        coords = action_generator._find_coordinates_for_resource_id(view_tree, "test_id")
        assert coords == (15, 15)

        # Execute - partial match with ID part
        coords = action_generator._find_coordinates_for_resource_id(view_tree, "com.example:id/test_id_partial")
        assert coords == (35, 35)

        # Execute - no match
        coords = action_generator._find_coordinates_for_resource_id(view_tree, "nonexistent_id")
        assert coords is None
