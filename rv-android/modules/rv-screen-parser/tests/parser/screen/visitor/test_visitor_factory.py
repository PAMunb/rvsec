from unittest.mock import MagicMock, patch

import pytest

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.visitor.abstract_visitor import AbstractScreenVisitor
from rvandroid.parser.screen.visitor.basic_visitor import BasicTextVisitor
from rvandroid.parser.screen.visitor.default_visitor import DefaultTextVisitor
from rvandroid.parser.screen.visitor.enhanced_visitor import EnhancedTextVisitor
from rvandroid.parser.screen.visitor.visitor_factory import VisitorFactory


class TestVisitorFactory:
    """Test suite for the VisitorFactory class."""

    @pytest.fixture(autouse=True)
    def setup_logging(self):
        """Fixture to set up logging and suppress log messages during tests"""
        with patch('rvandroid.util.logging.manager.LoggingManager') as mock_logging_manager:
            mock_logger = MagicMock()
            mock_logging_manager.get_instance.return_value = mock_logging_manager
            mock_logging_manager.get_logger.return_value = mock_logger
            yield

    @pytest.fixture
    def static_data(self):
        """Fixture for mock static analysis data."""
        # Create more complete mock with required components
        from rvandroid.domain.classes import Classes
        from rvandroid.domain.window import Windows
        from rvandroid.domain.wtg import WindowTransitionGraph

        mock_classes = MagicMock(spec=Classes)
        mock_windows = MagicMock(spec=Windows)
        mock_wtg = MagicMock(spec=WindowTransitionGraph)

        # Configure windows mock to return None for get_window
        mock_windows.get_window.return_value = None

        mock_static_data = MagicMock(spec=StaticAnalysisData)
        mock_static_data.classes = mock_classes
        mock_static_data.windows = mock_windows
        mock_static_data.wtg = mock_wtg

        return mock_static_data

    def test_create_default_visitor(self, static_data):
        """Test creating a visitor with the default type."""
        activity = "com.example.TestActivity"

        visitor = VisitorFactory.create(static_data=static_data, activity=activity)

        assert isinstance(visitor, DefaultTextVisitor)
        assert visitor.activity == activity
        assert visitor.static_info == static_data

    def test_create_basic_visitor(self, static_data):
        """Test creating a visitor with the 'basic' type."""
        activity = "com.example.TestActivity"

        visitor = VisitorFactory.create("basic", static_data, activity)

        assert isinstance(visitor, BasicTextVisitor)
        assert visitor.activity == activity
        assert visitor.static_info == static_data

    def test_create_detailed_visitor(self, static_data):
        """Test creating a visitor with the 'detailed' type."""
        activity = "com.example.TestActivity"

        visitor = VisitorFactory.create("detailed", static_data, activity)

        assert isinstance(visitor, EnhancedTextVisitor)
        assert visitor.activity == activity
        assert visitor.static_info == static_data

    def test_create_with_invalid_type(self, static_data):
        """Test creating a visitor with an invalid type raises ValueError."""
        with pytest.raises(ValueError) as excinfo:
            VisitorFactory.create("invalid_type", static_data, "com.example.TestActivity")

        assert "Unknown visitor type" in str(excinfo.value)
        assert "invalid_type" in str(excinfo.value)
        assert "Options:" in str(excinfo.value)

    def test_create_with_additional_kwargs(self, static_data):
        """Test creating a visitor with additional kwargs."""
        activity = "com.example.TestActivity"

        # Mock the DefaultTextVisitor.__init__ to verify kwargs are passed through
        with patch('rvandroid.parser.screen.visitor.default_visitor.DefaultTextVisitor.__init__') as mock_init:
            mock_init.return_value = None  # __init__ returns None

            VisitorFactory.create(
                static_data=static_data,
                activity=activity,
                custom_param="test_value"
            )

            # Verify the custom parameter was passed through
            mock_init.assert_called_once()
            _, kwargs = mock_init.call_args
            assert kwargs.get("custom_param") == "test_value"

    def test_get_visitor_class(self):
        """Test getting a visitor class."""
        visitor_class = VisitorFactory.get_visitor_class("basic")
        assert visitor_class == BasicTextVisitor

        visitor_class = VisitorFactory.get_visitor_class("default")
        assert visitor_class == DefaultTextVisitor

        visitor_class = VisitorFactory.get_visitor_class("detailed")
        assert visitor_class == EnhancedTextVisitor

    def test_get_visitor_class_invalid_type(self):
        """Test getting a visitor class with an invalid type raises ValueError."""
        with pytest.raises(ValueError) as excinfo:
            VisitorFactory.get_visitor_class("invalid_type")

        assert "Unknown visitor type" in str(excinfo.value)
        assert "invalid_type" in str(excinfo.value)

    def test_register_visitor_type(self):
        """Test registering a new visitor type."""

        # Create a proper visitor class that inherits from AbstractScreenVisitor
        class TestVisitor(AbstractScreenVisitor):
            def visit_node(self, node): pass

            def visit_leaf_node(self, node): pass

            def visit_button(self, node): pass

            def visit_edit_text(self, node): pass

            def visit_text_view(self, node): pass

            def visit_checkbox(self, node): pass

            def visit_checked_text(self, node): pass

            def visit_toggle_button(self, node): pass

            def visit_switch(self, node): pass

            def visit_image_button(self, node): pass

            def visit_image(self, node): pass

            def visit_radio_button(self, node): pass

            def visit_radio_group(self, node): pass

            def visit_spinner(self, node): pass

            def visit_slider(self, node): pass

        # Register the visitor type
        VisitorFactory.register_visitor_type("test_visitor", TestVisitor)

        # Verify the visitor type was registered
        available_types = VisitorFactory.get_available_types()
        assert "test_visitor" in available_types
        assert available_types["test_visitor"] == TestVisitor

        # Verify we can get the visitor class
        assert VisitorFactory.get_visitor_class("test_visitor") == TestVisitor

        # Clean up: remove the test visitor type
        if "test_visitor" in VisitorFactory._REGISTRY:
            del VisitorFactory._REGISTRY["test_visitor"]

    def test_register_visitor_type_invalid_class(self):
        """Test registering a visitor type with a class that is not a subclass of AbstractScreenVisitor."""
        # Try to register an invalid class
        with pytest.raises(TypeError) as excinfo:
            VisitorFactory.register_visitor_type("invalid_class", MagicMock)

        assert "must be a subclass of AbstractScreenVisitor" in str(excinfo.value)

    def test_get_available_types(self):
        """Test getting available visitor types."""
        available_types = VisitorFactory.get_available_types()

        # Verify the default visitor types are available
        assert "basic" in available_types
        assert "default" in available_types
        assert "detailed" in available_types

        assert available_types["basic"] == BasicTextVisitor
        assert available_types["default"] == DefaultTextVisitor
        assert available_types["detailed"] == EnhancedTextVisitor

    def test_get_available_types_names(self):
        """Test getting available visitor type names."""
        available_type_names = VisitorFactory.get_available_types_names()

        # Verify the default visitor types are included
        assert "basic" in available_type_names
        assert "default" in available_type_names
        assert "detailed" in available_type_names

    def test_registry_modification_safety(self):
        """Test that modifying the returned registry doesn't affect the original."""
        original_registry = VisitorFactory.get_available_types()
        modified_registry = VisitorFactory.get_available_types()

        # Add a fake visitor type to the copy
        modified_registry["fake_visitor"] = MagicMock()

        # Verify the original registry wasn't affected
        after_registry = VisitorFactory.get_available_types()
        assert "fake_visitor" not in after_registry
        assert set(original_registry.keys()) == set(after_registry.keys())

    # If the factory uses a singleton pattern, verify that behavior
    def test_registry_contains_default_types(self):
        """Test that the registry contains the default visitor types."""
        # Get available types from the factory
        available_types = VisitorFactory.get_available_types()

        # Verify the registry contains the default types
        assert "basic" in available_types
        assert "default" in available_types
        assert "detailed" in available_types

        # Verify the types are mapped to the correct classes
        assert available_types["basic"] == BasicTextVisitor
        assert available_types["default"] == DefaultTextVisitor
        assert available_types["detailed"] == EnhancedTextVisitor

    # Test subclass creation with inheritance
    def test_custom_visitor_subclass(self, static_data):
        """Test creating and registering a custom visitor subclass."""

        # Create a custom visitor subclass
        class CustomVisitor(AbstractScreenVisitor):
            def visit_node(self, node): pass

            def visit_leaf_node(self, node): pass

            def visit_button(self, node): pass

            def visit_edit_text(self, node): pass

            def visit_text_view(self, node): pass

            def visit_checkbox(self, node): pass

            def visit_checked_text(self, node): pass

            def visit_toggle_button(self, node): pass

            def visit_switch(self, node): pass

            def visit_image_button(self, node): pass

            def visit_image(self, node): pass

            def visit_radio_button(self, node): pass

            def visit_radio_group(self, node): pass

            def visit_spinner(self, node): pass

            def visit_slider(self, node): pass

        # Register the custom visitor
        VisitorFactory.register_visitor_type("custom", CustomVisitor)

        # Create a visitor using the custom type
        visitor = VisitorFactory.create("custom", static_data, "com.example.TestActivity")

        # Verify the visitor was created correctly
        assert isinstance(visitor, CustomVisitor)

        # Clean up: remove the custom visitor type
        if "custom" in VisitorFactory._REGISTRY:
            del VisitorFactory._REGISTRY["custom"]
