"""
Unit tests for the ConfigurableTool class.

This module contains comprehensive tests for the ConfigurableTool class
that extends AbstractTool with rich configuration capabilities.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from rv_android_core.tools.configurable_tool import ConfigurableTool
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.app import App


class ConcreteConfigurableTool(ConfigurableTool):
    """Concrete implementation of ConfigurableTool for testing purposes."""

    def __init__(self, name="test_configurable_tool", description="Test description", process_pattern="com.test"):
        super().__init__(name, description, process_pattern)
        self.tool_specific_config_called = False
        self.tool_specific_config_data = None

    def configure_tool_specific(self, config):
        """Test implementation of tool-specific configuration."""
        self.tool_specific_config_called = True
        self.tool_specific_config_data = config.copy() if config else {}

    def execute_tool_specific_logic(self, task, app):
        """Test implementation of tool-specific execution."""
        self.execution_called = True
        self.execution_task = task
        self.execution_app = app


class TestConfigurableToolInitialization:
    """Tests for ConfigurableTool initialization and setup."""

    @patch('rv_android_core.util.error.error_handler.ErrorHandler')
    @patch('rv_android_core.util.logging.manager.LoggingManager')
    def test_init_default_values(self, mock_logging_manager, mock_error_handler):
        """Test ConfigurableTool initialization with default values."""
        # Arrange
        mock_logger = Mock()
        mock_logging_instance = Mock()
        mock_logging_instance.get_logger.return_value = mock_logger
        mock_logging_manager.get_instance.return_value = mock_logging_instance

        mock_error_instance = Mock()
        mock_error_handler.get_instance.return_value = mock_error_instance

        # Act
        tool = ConcreteConfigurableTool()

        # Assert
        assert tool.name == "test_configurable_tool"
        assert tool.description == "Test description"
        assert tool.process_pattern == "com.test"
        assert tool.config == {}
        assert isinstance(tool, AbstractTool)

    @patch('rv_android_core.util.error.error_handler.ErrorHandler')
    @patch('rv_android_core.util.logging.manager.LoggingManager')
    def test_init_custom_values(self, mock_logging_manager, mock_error_handler):
        """Test ConfigurableTool initialization with custom values."""
        # Arrange
        mock_logger = Mock()
        mock_logging_instance = Mock()
        mock_logging_instance.get_logger.return_value = mock_logger
        mock_logging_manager.get_instance.return_value = mock_logging_instance

        mock_error_instance = Mock()
        mock_error_handler.get_instance.return_value = mock_error_instance

        name = "custom_tool"
        description = "Custom description"
        process_pattern = "com.custom.tool"

        # Act
        tool = ConcreteConfigurableTool(name, description, process_pattern)

        # Assert
        assert tool.name == name
        assert tool.description == description
        assert tool.process_pattern == process_pattern
        assert tool.config == {}

    def test_inheritance_structure(self):
        """Test that ConfigurableTool properly inherits from AbstractTool."""
        # Assert
        assert issubclass(ConfigurableTool, AbstractTool)


class TestConfigurableToolConfiguration:
    """Tests for ConfigurableTool configuration management."""

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture providing mocked dependencies."""
        with patch('rv_android_core.util.logging.manager.LoggingManager') as mock_logging, \
                patch('rv_android_core.util.error.error_handler.ErrorHandler') as mock_error:
            mock_logger = Mock()
            mock_logging_instance = Mock()
            mock_logging_instance.get_logger.return_value = mock_logger
            mock_logging.get_instance.return_value = mock_logging_instance

            mock_error_instance = Mock()
            mock_error.get_instance.return_value = mock_error_instance

            yield {
                'logger': mock_logger,
                'error_handler': mock_error_instance
            }

    @pytest.fixture
    def test_tool(self, mock_dependencies):
        """Fixture providing a concrete configurable tool instance."""
        return ConcreteConfigurableTool()

    def test_configure_with_valid_config(self, test_tool, mock_dependencies):
        """Test configuration with valid configuration dictionary."""
        # Arrange
        config = {
            "timeout": 60,
            "retry_count": 3,
            "verbose": True
        }

        with patch.object(test_tool.logger, 'debug') as mock_debug:
            # Act
            test_tool.configure(config)

            # Assert
            assert test_tool.config == config
            assert test_tool.tool_specific_config_called is True
            assert test_tool.tool_specific_config_data == config

            # Verify logging
            mock_debug.assert_called_with(f"Tool {test_tool.name} configured with: {config}")

    def test_configure_with_empty_config(self, test_tool, mock_dependencies):
        """Test configuration with empty dictionary."""
        # Arrange
        config = {}

        with patch.object(test_tool.logger, 'debug') as mock_debug:
            # Act
            test_tool.configure(config)

            # Assert
            assert test_tool.config == {}
            assert test_tool.tool_specific_config_called is True
            assert test_tool.tool_specific_config_data == {}

    def test_configure_with_none_config(self, test_tool, mock_dependencies):
        """Test configuration with None."""
        # Act
        test_tool.configure(None)

        # Assert
        assert test_tool.config == {}
        assert test_tool.tool_specific_config_called is True
        assert test_tool.tool_specific_config_data == {}

    def test_configure_preserves_original_config(self, test_tool, mock_dependencies):
        """Test that configure creates a copy of the configuration."""
        # Arrange
        original_config = {"key": "value"}

        # Act
        test_tool.configure(original_config)
        test_tool.config["new_key"] = "new_value"

        # Assert
        assert "new_key" not in original_config  # Original should be unchanged
        assert original_config == {"key": "value"}

    def test_configure_tool_specific_default_implementation(self, mock_dependencies):
        """Test that default configure_tool_specific does nothing."""
        # Arrange
        tool = ConfigurableTool("test", "desc", "pattern")
        config = {"key": "value"}

        # Act & Assert - Should not raise any exception
        tool.configure_tool_specific(config)


class TestConfigurableToolConfigAccess:
    """Tests for ConfigurableTool configuration access methods."""

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture providing mocked dependencies."""
        with patch('rv_android_core.util.logging.manager.LoggingManager') as mock_logging, \
                patch('rv_android_core.util.error.error_handler.ErrorHandler') as mock_error:
            mock_logger = Mock()
            mock_logging_instance = Mock()
            mock_logging_instance.get_logger.return_value = mock_logger
            mock_logging.get_instance.return_value = mock_logging_instance

            mock_error_instance = Mock()
            mock_error.get_instance.return_value = mock_error_instance

            yield {
                'logger': mock_logger,
                'error_handler': mock_error_instance
            }

    @pytest.fixture
    def configured_tool(self, mock_dependencies):
        """Fixture providing a tool with nested configuration."""
        tool = ConcreteConfigurableTool()
        config = {
            "timeout": 60,
            "llm": {
                "temperature": 0.7,
                "model": "gpt-4",
                "settings": {
                    "max_tokens": 1000
                }
            },
            "verbose": True
        }
        tool.configure(config)
        return tool

    def test_get_config_value_simple_key(self, configured_tool):
        """Test getting configuration value with simple key."""
        # Act & Assert
        assert configured_tool.get_config_value("timeout") == 60
        assert configured_tool.get_config_value("verbose") is True

    def test_get_config_value_with_default(self, configured_tool):
        """Test getting configuration value with default for missing key."""
        # Act & Assert
        assert configured_tool.get_config_value("missing_key", "default_value") == "default_value"
        assert configured_tool.get_config_value("missing_key", 42) == 42
        assert configured_tool.get_config_value("missing_key") is None

    def test_get_config_value_nested_key_dot_notation(self, configured_tool):
        """Test getting nested configuration value using dot notation."""
        # Act & Assert
        assert configured_tool.get_config_value("llm.temperature") == 0.7
        assert configured_tool.get_config_value("llm.model") == "gpt-4"
        assert configured_tool.get_config_value("llm.settings.max_tokens") == 1000

    def test_get_config_value_nested_key_missing(self, configured_tool):
        """Test getting missing nested configuration value."""
        # Act & Assert
        assert configured_tool.get_config_value("llm.missing_key", "default") == "default"
        assert configured_tool.get_config_value("missing.nested.key", "default") == "default"
        assert configured_tool.get_config_value("llm.settings.missing", 100) == 100

    def test_get_config_value_nested_key_invalid_path(self, configured_tool):
        """Test getting configuration value with invalid nested path."""
        # Act & Assert
        assert configured_tool.get_config_value("timeout.invalid", "default") == "default"
        assert configured_tool.get_config_value("verbose.nested.key", "default") == "default"


class TestConfigurableToolConfigModification:
    """Tests for ConfigurableTool configuration modification methods."""

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture providing mocked dependencies."""
        with patch('rv_android_core.util.logging.manager.LoggingManager') as mock_logging, \
                patch('rv_android_core.util.error.error_handler.ErrorHandler') as mock_error:
            mock_logger = Mock()
            mock_logging_instance = Mock()
            mock_logging_instance.get_logger.return_value = mock_logger
            mock_logging.get_instance.return_value = mock_logging_instance

            mock_error_instance = Mock()
            mock_error.get_instance.return_value = mock_error_instance

            yield {
                'logger': mock_logger,
                'error_handler': mock_error_instance
            }

    @pytest.fixture
    def test_tool(self, mock_dependencies):
        """Fixture providing a configurable tool instance."""
        return ConcreteConfigurableTool()

    def test_set_config_value_simple_key(self, test_tool):
        """Test setting configuration value with simple key."""
        # Act
        test_tool.set_config_value("timeout", 120)
        test_tool.set_config_value("verbose", False)

        # Assert
        assert test_tool.get_config_value("timeout") == 120
        assert test_tool.get_config_value("verbose") is False

    def test_set_config_value_nested_key_dot_notation(self, test_tool):
        """Test setting nested configuration value using dot notation."""
        # Act
        test_tool.set_config_value("llm.temperature", 0.5)
        test_tool.set_config_value("llm.settings.max_tokens", 2000)
        test_tool.set_config_value("database.connection.host", "localhost")

        # Assert
        assert test_tool.get_config_value("llm.temperature") == 0.5
        assert test_tool.get_config_value("llm.settings.max_tokens") == 2000
        assert test_tool.get_config_value("database.connection.host") == "localhost"

    def test_set_config_value_creates_nested_structure(self, test_tool):
        """Test that setting nested values creates the required structure."""
        # Act
        test_tool.set_config_value("new.nested.deep.value", "test")

        # Assert
        assert test_tool.config["new"]["nested"]["deep"]["value"] == "test"
        assert isinstance(test_tool.config["new"], dict)
        assert isinstance(test_tool.config["new"]["nested"], dict)
        assert isinstance(test_tool.config["new"]["nested"]["deep"], dict)

    def test_set_config_value_overwrites_non_dict(self, test_tool):
        """Test that setting nested values overwrites non-dict values."""
        # Arrange
        test_tool.set_config_value("existing", "string_value")

        # Act
        test_tool.set_config_value("existing.new_nested", "nested_value")

        # Assert
        assert test_tool.get_config_value("existing.new_nested") == "nested_value"
        assert isinstance(test_tool.config["existing"], dict)

    def test_has_config_simple_key(self, test_tool):
        """Test checking configuration existence with simple key."""
        # Arrange
        test_tool.set_config_value("existing_key", "value")

        # Act & Assert
        assert test_tool.has_config("existing_key") is True
        assert test_tool.has_config("missing_key") is False

    def test_has_config_nested_key_dot_notation(self, test_tool):
        """Test checking nested configuration existence using dot notation."""
        # Arrange
        test_tool.set_config_value("llm.temperature", 0.7)
        test_tool.set_config_value("llm.settings.max_tokens", 1000)

        # Act & Assert
        assert test_tool.has_config("llm.temperature") is True
        assert test_tool.has_config("llm.settings.max_tokens") is True
        assert test_tool.has_config("llm.missing_key") is False
        assert test_tool.has_config("missing.nested.key") is False

    def test_has_config_invalid_nested_path(self, test_tool):
        """Test checking configuration existence with invalid nested path."""
        # Arrange
        test_tool.set_config_value("simple_value", "not_a_dict")

        # Act & Assert
        assert test_tool.has_config("simple_value.nested") is False

    def test_get_config_dict(self, test_tool):
        """Test getting copy of complete configuration dictionary."""
        # Arrange
        original_config = {
            "timeout": 60,
            "llm": {"temperature": 0.7}
        }
        test_tool.configure(original_config)

        # Act
        config_copy = test_tool.get_config_dict()

        # Assert
        assert config_copy == original_config
        assert config_copy is not test_tool.config  # Should be a copy

        # Modify copy and verify original is unchanged
        config_copy["new_key"] = "new_value"
        assert "new_key" not in test_tool.config

    def test_clear_config(self, test_tool, mock_dependencies):
        """Test clearing all configuration values."""
        # Arrange
        test_tool.configure({"key1": "value1", "key2": "value2"})

        with patch.object(test_tool.logger, 'debug') as mock_debug:
            # Act
            test_tool.clear_config()

            # Assert
            assert test_tool.config == {}
            mock_debug.assert_called_with(f"Cleared configuration for tool: {test_tool.name}")


class TestConfigurableToolExecution:
    """Tests for ConfigurableTool execution functionality."""

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture providing mocked dependencies."""
        with patch('rv_android_core.util.logging.manager.LoggingManager') as mock_logging, \
                patch('rv_android_core.util.error.error_handler.ErrorHandler') as mock_error:
            mock_logger = Mock()
            mock_logging_instance = Mock()
            mock_logging_instance.get_logger.return_value = mock_logger
            mock_logging.get_instance.return_value = mock_logging_instance

            mock_error_instance = Mock()
            mock_error.get_instance.return_value = mock_error_instance

            yield {
                'logger': mock_logger,
                'error_handler': mock_error_instance
            }

    @pytest.fixture
    def test_tool(self, mock_dependencies):
        """Fixture providing a configurable tool instance."""
        return ConcreteConfigurableTool()

    @pytest.fixture
    def mock_app(self):
        """Fixture providing a mock App instance."""
        app = Mock(spec=App)
        app.name = "test.apk"
        return app

    def test_execute_with_configuration(self, test_tool, mock_app, mock_dependencies):
        """Test execution with configuration logging."""
        # Arrange
        config = {"timeout": 60, "verbose": True}
        test_tool.configure(config)
        task = Mock()

        with patch.object(test_tool, 'kill_related_processes'), \
                patch.object(test_tool.logger, 'info') as mock_info, \
                patch('rv_android_core.tools.abstract_tool.AbstractTool.execute') as mock_super_execute:
            # Act
            test_tool.execute(task, mock_app)

            # Assert
            mock_info.assert_called_with(f"Executing {test_tool.name} with configuration: {config}")
            mock_super_execute.assert_called_once_with(task, mock_app)

    def test_execute_without_configuration(self, test_tool, mock_app, mock_dependencies):
        """Test execution without configuration (default)."""
        # Arrange
        task = Mock()

        with patch.object(test_tool, 'kill_related_processes'), \
                patch.object(test_tool.logger, 'info') as mock_info, \
                patch('rv_android_core.tools.abstract_tool.AbstractTool.execute') as mock_super_execute:
            # Act
            test_tool.execute(task, mock_app)

            # Assert
            mock_info.assert_called_with(f"Executing {test_tool.name} with default configuration")
            mock_super_execute.assert_called_once_with(task, mock_app)

    def test_execute_tool_specific_logic_default_implementation(self, test_tool, mock_app, mock_dependencies):
        """Test default implementation of execute_tool_specific_logic."""
        # Arrange
        task = Mock()

        # Create a tool that uses the default implementation
        default_tool = ConfigurableTool("default_tool", "Default description", "com.default")

        with patch.object(default_tool.logger, 'info') as mock_info:
            # Act
            default_tool.execute_tool_specific_logic(task, mock_app)

            # Assert
            mock_info.assert_called_with(f"Executing {default_tool.name} tool for app: {mock_app.name}")

    def test_get_tool_info_includes_configuration(self, test_tool):
        """Test get_tool_info includes configuration information."""
        # Arrange
        config = {"timeout": 60, "llm": {"temperature": 0.7}}
        test_tool.configure(config)

        # Act
        info = test_tool.get_tool_info()

        # Assert
        assert info["name"] == test_tool.name
        assert info["description"] == test_tool.description
        assert info["process_pattern"] == test_tool.process_pattern
        assert info["configuration"] == config
        assert info["configurable"] is True

    def test_get_tool_info_no_configuration(self, test_tool):
        """Test get_tool_info with no configuration."""
        # Act
        info = test_tool.get_tool_info()

        # Assert
        assert info["configuration"] == {}
        assert info["configurable"] is True
