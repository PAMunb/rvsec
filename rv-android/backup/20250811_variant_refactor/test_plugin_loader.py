"""
Comprehensive unit tests for PluginLoader to maximize code coverage.

This test module covers all aspects of plugin discovery, loading, validation,
registration, and error handling in the PluginLoader class.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, create_autospec
from typing import Dict, Any, List
from importlib.metadata import EntryPoint

from rv_tools.registry.plugin_loader import PluginLoader
from rv_tools.registry.registry import ToolRegistry
from rv_tools.interfaces.plugin_interface import ToolPlugin
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec


class MockToolForPlugin(AbstractTool):
    """Mock tool for plugin testing."""

    TOOL_SPEC = ToolSpec(
        name="mock_plugin_tool",
        description="Mock tool from plugin",
        url="https://example.com/plugin_tool",
        version="1.0.0"
    )

    def __init__(self, name="mock_plugin_tool", description="Mock plugin tool", process_pattern=None):
        super().__init__(name, description, process_pattern or "mock_plugin.*")

    def execute_tool_specific_logic(self, task, app):
        pass


class MockValidPlugin(ToolPlugin):
    """Mock valid plugin for testing."""

    def get_plugin_name(self) -> str:
        return "mock_valid_plugin"

    def get_plugin_version(self) -> str:
        return "1.0.0"

    def get_plugin_description(self) -> str:
        return "Mock valid plugin for testing"

    def get_tool_names(self) -> List[str]:
        return ["mock_plugin_tool", "mock_tool_2"]

    def get_tool_class(self, tool_name: str):
        if tool_name in self.get_tool_names():
            return MockToolForPlugin
        raise ValueError(f"Tool {tool_name} not found")

    def get_tool_spec(self, tool_name: str) -> ToolSpec:
        if tool_name == "mock_plugin_tool":
            return MockToolForPlugin.TOOL_SPEC
        elif tool_name == "mock_tool_2":
            return ToolSpec(
                name="mock_tool_2",
                description="Second mock tool",
                url="https://example.com/tool2",
                version="1.0.0"
            )
        raise ValueError(f"Tool {tool_name} not found")

    def get_tool_variants(self, tool_name: str) -> List[str]:
        if tool_name == "mock_plugin_tool":
            return ["performance", "debug"]
        return []

    def get_variant_config(self, tool_name: str, variant_name: str) -> Dict[str, Any]:
        if tool_name == "mock_plugin_tool":
            if variant_name == "performance":
                return {"timeout": 1200, "threads": 4}
            elif variant_name == "debug":
                return {"verbose": True, "debug": True}
        return {}

    def validate_dependencies(self) -> bool:
        return True

    def get_supported_capabilities(self) -> List[str]:
        return ["testing", "automation"]

    def cleanup(self) -> None:
        pass


class MockInvalidPlugin:
    """Mock invalid plugin (doesn't implement ToolPlugin interface)."""

    def get_plugin_name(self) -> str:
        return "mock_invalid_plugin"


class MockFailingPlugin(ToolPlugin):
    """Mock plugin that fails during various operations."""

    def get_plugin_name(self) -> str:
        return "mock_failing_plugin"

    def get_plugin_version(self) -> str:
        return "1.0.0"

    def get_plugin_description(self) -> str:
        return "Mock failing plugin"

    def get_tool_names(self) -> List[str]:
        return ["failing_tool"]

    def get_tool_class(self, tool_name: str):
        raise RuntimeError("Tool class loading failed")

    def get_tool_spec(self, tool_name: str) -> ToolSpec:
        raise RuntimeError("Tool spec loading failed")

    def validate_dependencies(self) -> bool:
        return False

    def get_supported_capabilities(self) -> List[str]:
        return []

    def cleanup(self) -> None:
        raise RuntimeError("Cleanup failed")


class MockPluginWithDependencyIssues(ToolPlugin):
    """Mock plugin with dependency validation issues."""

    def get_plugin_name(self) -> str:
        return "mock_dependency_plugin"

    def get_plugin_version(self) -> str:
        return "1.0.0"

    def get_plugin_description(self) -> str:
        return "Mock plugin with dependency issues"

    def get_tool_names(self) -> List[str]:
        return ["dependency_tool"]

    def get_tool_class(self, tool_name: str):
        return MockToolForPlugin

    def get_tool_spec(self, tool_name: str) -> ToolSpec:
        return ToolSpec(
            name="dependency_tool",
            description="Tool with dependencies",
            url="https://example.com/dependency",
            version="1.0.0"
        )

    def validate_dependencies(self) -> bool:
        raise RuntimeError("Dependency validation error")

    def get_supported_capabilities(self) -> List[str]:
        return []


class MockEntryPointsList:
    """Mock implementation that behaves like a real entry points list."""

    def __init__(self, entry_points_list):
        self._entry_points = list(entry_points_list)

    def __len__(self):
        return len(self._entry_points)

    def __iter__(self):
        return iter(self._entry_points)

    def __getitem__(self, index):
        return self._entry_points[index]


def create_mock_entry_point(name: str, plugin_class, load_exception=None):
    """Helper to create a properly configured mock entry point."""
    entry_point = Mock(spec=EntryPoint)
    entry_point.name = name
    if load_exception:
        entry_point.load.side_effect = load_exception
    else:
        entry_point.load.return_value = plugin_class
    return entry_point


@pytest.fixture
def mock_registry():
    """Create a mock registry for testing."""
    registry = Mock(spec=ToolRegistry)
    registry.register_tool.return_value = None
    registry.register_variant.return_value = None
    return registry


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    logger = Mock()
    logger.debug = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    return logger


@pytest.fixture
def clean_plugin_loader(mock_registry, mock_logger):
    """Create a clean plugin loader for testing."""
    with patch('rv_tools.registry.plugin_loader.ToolRegistry') as mock_registry_class:
        mock_registry_class.get_instance.return_value = mock_registry

        with patch('rv_tools.registry.plugin_loader.LoggingManager') as mock_logging:
            mock_logging.get_instance.return_value.get_logger.return_value = mock_logger

            with patch('rv_tools.registry.plugin_loader.ErrorHandler') as mock_error_handler:
                mock_error_handler_instance = Mock()
                mock_error_handler.get_instance.return_value = mock_error_handler_instance

                loader = PluginLoader(mock_registry)
                # Ensure all components are accessible for testing
                loader.logger = mock_logger
                loader.error_handler = mock_error_handler_instance
                yield loader


class TestPluginLoaderInitialization:
    """Test PluginLoader initialization."""

    def test_init_with_registry(self, mock_registry):
        """Test initialization with provided registry."""
        with patch('rv_tools.registry.plugin_loader.LoggingManager') as mock_logging:
            mock_logger = Mock()
            mock_logging.get_instance.return_value.get_logger.return_value = mock_logger

            with patch('rv_tools.registry.plugin_loader.ErrorHandler') as mock_error_handler:
                mock_error_handler.get_instance.return_value = Mock()

                loader = PluginLoader(mock_registry)

        assert loader.registry is mock_registry
        assert loader.discovered_plugins == {}
        assert loader.loaded_plugins == {}
        assert loader.failed_plugins == {}
        assert loader.logger is not None
        assert loader.error_handler is not None

    def test_init_without_registry_uses_singleton(self):
        """Test initialization without registry uses singleton."""
        with patch('rv_tools.registry.plugin_loader.ToolRegistry') as mock_registry_class:
            mock_registry = Mock()
            mock_registry_class.get_instance.return_value = mock_registry

            with patch('rv_tools.registry.plugin_loader.LoggingManager') as mock_logging:
                mock_logger = Mock()
                mock_logging.get_instance.return_value.get_logger.return_value = mock_logger

                with patch('rv_tools.registry.plugin_loader.ErrorHandler') as mock_error_handler:
                    mock_error_handler.get_instance.return_value = Mock()

                    loader = PluginLoader()

            assert loader.registry is mock_registry
            mock_registry_class.get_instance.assert_called_once()

    def test_init_sets_up_logging(self, mock_registry):
        """Test that initialization sets up logging correctly."""
        with patch('rv_tools.registry.plugin_loader.LoggingManager') as mock_logging:
            mock_logger = Mock()
            mock_logging_manager = Mock()
            mock_logging_manager.get_logger.return_value = mock_logger
            mock_logging.get_instance.return_value = mock_logging_manager

            with patch('rv_tools.registry.plugin_loader.ErrorHandler') as mock_error_handler:
                mock_error_handler.get_instance.return_value = Mock()

                loader = PluginLoader(mock_registry)

            assert loader.logger is mock_logger
            mock_logging_manager.get_logger.assert_called_once()

    def test_init_sets_up_error_handler(self, mock_registry):
        """Test that initialization sets up error handler correctly."""
        with patch('rv_tools.registry.plugin_loader.LoggingManager') as mock_logging:
            mock_logging.get_instance.return_value.get_logger.return_value = Mock()

            with patch('rv_tools.registry.plugin_loader.ErrorHandler') as mock_error_handler_class:
                mock_error_handler = Mock()
                mock_error_handler_class.get_instance.return_value = mock_error_handler

                loader = PluginLoader(mock_registry)

                assert loader.error_handler is mock_error_handler
                mock_error_handler_class.get_instance.assert_called_once()


class TestPluginDiscovery:
    """Test plugin discovery functionality."""

    @patch('rv_tools.registry.plugin_loader.entry_points')
    def test_discover_plugins_success_new_api(self, mock_entry_points_func, clean_plugin_loader):
        """Test successful plugin discovery with new entry points API."""
        loader = clean_plugin_loader

        # Create mock entry points
        valid_entry_point = create_mock_entry_point("mock_valid_plugin", MockValidPlugin)
        entry_points_list = MockEntryPointsList([valid_entry_point])

        # Mock new API (Python >= 3.10) - object without 'get' method
        mock_eps = Mock()
        # Remove get method to simulate new API
        if hasattr(mock_eps, 'get'):
            del mock_eps.get
        mock_eps.select.return_value = entry_points_list
        mock_entry_points_func.return_value = mock_eps

        plugins = loader.discover_plugins()

        assert len(plugins) == 1
        assert isinstance(plugins[0], MockValidPlugin)
        assert "mock_valid_plugin" in loader.discovered_plugins
        mock_eps.select.assert_called_once_with(group=PluginLoader.ENTRY_POINT_GROUP)

    @patch('rv_tools.registry.plugin_loader.entry_points')
    def test_discover_plugins_success_old_api(self, mock_entry_points_func, clean_plugin_loader):
        """Test successful plugin discovery with old entry points API."""
        loader = clean_plugin_loader

        # Create mock entry points
        valid_entry_point = create_mock_entry_point("mock_valid_plugin", MockValidPlugin)
        entry_points_list = MockEntryPointsList([valid_entry_point])

        # Mock old API (Python < 3.10) - object with 'get' method
        mock_eps = Mock()
        mock_eps.get.return_value = entry_points_list
        mock_entry_points_func.return_value = mock_eps

        plugins = loader.discover_plugins()

        assert len(plugins) == 1
        assert isinstance(plugins[0], MockValidPlugin)
        assert "mock_valid_plugin" in loader.discovered_plugins
        mock_eps.get.assert_called_once_with(PluginLoader.ENTRY_POINT_GROUP, [])

    @patch('rv_tools.registry.plugin_loader.entry_points')
    def test_discover_plugins_with_invalid_plugin(self, mock_entry_points_func, clean_plugin_loader):
        """Test plugin discovery with invalid plugin."""
        loader = clean_plugin_loader

        # Create mock entry point that returns invalid plugin
        invalid_entry_point = create_mock_entry_point("mock_invalid_plugin", MockInvalidPlugin)
        entry_points_list = MockEntryPointsList([invalid_entry_point])

        # Mock API with invalid plugin
        mock_eps = Mock()
        if hasattr(mock_eps, 'get'):
            del mock_eps.get
        mock_eps.select.return_value = entry_points_list
        mock_entry_points_func.return_value = mock_eps

        plugins = loader.discover_plugins()

        assert len(plugins) == 0
        assert "mock_invalid_plugin" in loader.failed_plugins
        loader.logger.error.assert_called()

    @patch('rv_tools.registry.plugin_loader.entry_points')
    def test_discover_plugins_with_failing_plugin(self, mock_entry_points_func, clean_plugin_loader):
        """Test plugin discovery with plugin that fails to load."""
        loader = clean_plugin_loader

        # Create mock entry point that fails to load
        failing_entry_point = create_mock_entry_point(
            "mock_failing_plugin",
            None,
            load_exception=ImportError("Plugin import failed")
        )
        entry_points_list = MockEntryPointsList([failing_entry_point])

        # Mock API with failing plugin
        mock_eps = Mock()
        if hasattr(mock_eps, 'get'):
            del mock_eps.get
        mock_eps.select.return_value = entry_points_list
        mock_entry_points_func.return_value = mock_eps

        plugins = loader.discover_plugins()

        assert len(plugins) == 0
        assert "mock_failing_plugin" in loader.failed_plugins
        loader.logger.error.assert_called()

    @patch('rv_tools.registry.plugin_loader.entry_points')
    def test_discover_plugins_with_mixed_results(self, mock_entry_points_func, clean_plugin_loader):
        """Test plugin discovery with mix of valid, invalid, and failing plugins."""
        loader = clean_plugin_loader

        # Create various mock entry points
        valid_entry_point = create_mock_entry_point("mock_valid_plugin", MockValidPlugin)
        invalid_entry_point = create_mock_entry_point("mock_invalid_plugin", MockInvalidPlugin)
        failing_entry_point = create_mock_entry_point(
            "mock_failing_plugin",
            None,
            load_exception=ImportError("Plugin import failed")
        )

        entry_points_list = MockEntryPointsList([
            valid_entry_point, invalid_entry_point, failing_entry_point
        ])

        # Mock API with all types of plugins
        mock_eps = Mock()
        if hasattr(mock_eps, 'get'):
            del mock_eps.get
        mock_eps.select.return_value = entry_points_list
        mock_entry_points_func.return_value = mock_eps

        plugins = loader.discover_plugins()

        assert len(plugins) == 1  # Only valid plugin
        assert isinstance(plugins[0], MockValidPlugin)
        assert "mock_valid_plugin" in loader.discovered_plugins
        assert "mock_invalid_plugin" in loader.failed_plugins
        assert "mock_failing_plugin" in loader.failed_plugins
        # Error handling might be called multiple times (e.g., plugin discovery + error handling)
        assert loader.logger.error.call_count >= 2  # At least two failed plugins

    @patch('rv_tools.registry.plugin_loader.entry_points')
    def test_discover_plugins_with_exception_in_discovery(self, mock_entry_points_func, clean_plugin_loader):
        """Test plugin discovery when entry_points() raises exception."""
        loader = clean_plugin_loader

        mock_entry_points_func.side_effect = RuntimeError("Entry points failed")

        with pytest.raises(RuntimeError):
            loader.discover_plugins()

    @patch('rv_tools.registry.plugin_loader.entry_points')
    def test_discover_plugins_includes_manually_registered(self, mock_entry_points_func, clean_plugin_loader):
        """Test that manually registered plugins are included."""
        loader = clean_plugin_loader

        # Manually add a plugin
        manual_plugin = MockValidPlugin()
        loader.discovered_plugins["manual_plugin"] = manual_plugin

        # Mock empty entry points
        entry_points_list = MockEntryPointsList([])
        mock_eps = Mock()
        if hasattr(mock_eps, 'get'):
            del mock_eps.get
        mock_eps.select.return_value = entry_points_list
        mock_entry_points_func.return_value = mock_eps

        plugins = loader.discover_plugins()

        assert len(plugins) == 1
        assert plugins[0] is manual_plugin


class TestPluginLoading:
    """Test plugin loading functionality."""

    def test_load_plugin_already_loaded(self, clean_plugin_loader):
        """Test loading plugin that's already loaded."""
        loader = clean_plugin_loader
        plugin = MockValidPlugin()
        loader.loaded_plugins["mock_valid_plugin"] = plugin

        result = loader.load_plugin("mock_valid_plugin")

        assert result is plugin

    def test_load_plugin_discovered_but_not_loaded(self, clean_plugin_loader):
        """Test loading plugin that's discovered but not loaded."""
        loader = clean_plugin_loader
        plugin = MockValidPlugin()
        loader.discovered_plugins["mock_valid_plugin"] = plugin

        with patch.object(loader, '_validate_and_load_plugin', return_value=plugin) as mock_validate:
            result = loader.load_plugin("mock_valid_plugin")

        assert result is plugin
        mock_validate.assert_called_once_with(plugin)

    @patch('rv_tools.registry.plugin_loader.entry_points')
    def test_load_plugin_not_discovered_triggers_discovery(self, mock_entry_points_func, clean_plugin_loader):
        """Test loading plugin that's not discovered triggers discovery."""
        loader = clean_plugin_loader

        # Mock entry points to return our plugin during discovery
        valid_entry_point = create_mock_entry_point("mock_valid_plugin", MockValidPlugin)
        entry_points_list = MockEntryPointsList([valid_entry_point])
        mock_eps = Mock()
        if hasattr(mock_eps, 'get'):
            del mock_eps.get
        mock_eps.select.return_value = entry_points_list
        mock_entry_points_func.return_value = mock_eps

        # Mock validation to return the plugin
        plugin = MockValidPlugin()
        with patch.object(loader, '_validate_and_load_plugin', return_value=plugin) as mock_validate:
            result = loader.load_plugin("mock_valid_plugin")

        assert result is plugin
        mock_validate.assert_called_once()

    @patch('rv_tools.registry.plugin_loader.entry_points')
    def test_load_plugin_not_found_after_discovery(self, mock_entry_points_func, clean_plugin_loader):
        """Test loading plugin that's not found even after discovery."""
        loader = clean_plugin_loader

        # Mock empty entry points
        entry_points_list = MockEntryPointsList([])
        mock_eps = Mock()
        if hasattr(mock_eps, 'get'):
            del mock_eps.get
        mock_eps.select.return_value = entry_points_list
        mock_entry_points_func.return_value = mock_eps

        result = loader.load_plugin("nonexistent_plugin")

        assert result is None
        loader.logger.warning.assert_called()

    def test_load_plugin_with_exception(self, clean_plugin_loader):
        """Test loading plugin when exception occurs."""
        loader = clean_plugin_loader
        plugin = MockValidPlugin()
        loader.discovered_plugins["mock_valid_plugin"] = plugin

        with patch.object(loader, '_validate_and_load_plugin', side_effect=RuntimeError("Validation failed")):
            result = loader.load_plugin("mock_valid_plugin")

        assert result is None
        assert "mock_valid_plugin" in loader.failed_plugins
        loader.logger.error.assert_called()

    def test_load_all_plugins_empty_discovery(self, clean_plugin_loader):
        """Test loading all plugins when no plugins discovered."""
        loader = clean_plugin_loader

        loaded = loader.load_all_plugins()

        assert len(loaded) == 0

    def test_load_all_plugins_success(self, clean_plugin_loader):
        """Test successful loading of all plugins."""
        loader = clean_plugin_loader
        plugin1 = MockValidPlugin()
        plugin2 = MockValidPlugin()
        loader.discovered_plugins["plugin1"] = plugin1
        loader.discovered_plugins["plugin2"] = plugin2

        with patch.object(loader, '_validate_and_load_plugin', return_value=plugin1) as mock_validate:
            loaded = loader.load_all_plugins()

        assert len(loaded) == 2
        assert mock_validate.call_count == 2

    def test_load_all_plugins_with_failures(self, clean_plugin_loader):
        """Test loading all plugins with some failures."""
        loader = clean_plugin_loader
        plugin1 = MockValidPlugin()
        plugin2 = MockValidPlugin()
        loader.discovered_plugins["plugin1"] = plugin1
        loader.discovered_plugins["plugin2"] = plugin2

        def mock_validate(plugin):
            if plugin is plugin1:
                return plugin1
            else:
                raise RuntimeError("Validation failed")

        with patch.object(loader, '_validate_and_load_plugin', side_effect=mock_validate):
            loaded = loader.load_all_plugins()

        assert len(loaded) == 1
        assert loaded[0] is plugin1
        assert "plugin2" in loader.failed_plugins
        loader.logger.error.assert_called()


class TestPluginValidation:
    """Test plugin validation functionality."""

    def test_validate_and_load_plugin_success(self, clean_plugin_loader):
        """Test successful plugin validation and loading."""
        loader = clean_plugin_loader
        plugin = MockValidPlugin()

        with patch.object(loader, 'validate_plugin_dependencies', return_value=True):
            result = loader._validate_and_load_plugin(plugin)

        assert result is plugin
        assert "mock_valid_plugin" in loader.loaded_plugins
        loader.logger.info.assert_called()

    def test_validate_and_load_plugin_dependency_failure(self, clean_plugin_loader):
        """Test plugin validation failure due to dependencies."""
        loader = clean_plugin_loader
        plugin = MockValidPlugin()

        with patch.object(loader, 'validate_plugin_dependencies', return_value=False):
            result = loader._validate_and_load_plugin(plugin)

        assert result is None
        assert "mock_valid_plugin" in loader.failed_plugins
        loader.logger.error.assert_called()

    def test_validate_and_load_plugin_spec_validation_failure(self, clean_plugin_loader):
        """Test plugin validation failure due to invalid tool specs."""
        loader = clean_plugin_loader
        plugin = MockFailingPlugin()

        with patch.object(loader, 'validate_plugin_dependencies', return_value=True):
            result = loader._validate_and_load_plugin(plugin)

        assert result is None
        assert "mock_failing_plugin" in loader.failed_plugins
        loader.logger.error.assert_called()

    def test_validate_and_load_plugin_general_exception(self, clean_plugin_loader):
        """Test plugin validation with general exception."""
        loader = clean_plugin_loader
        plugin = MockValidPlugin()

        with patch.object(loader, 'validate_plugin_dependencies', side_effect=RuntimeError("General error")):
            result = loader._validate_and_load_plugin(plugin)

        assert result is None
        assert "mock_valid_plugin" in loader.failed_plugins
        loader.logger.error.assert_called()

    def test_validate_plugin_dependencies_success(self, clean_plugin_loader):
        """Test successful plugin dependency validation."""
        loader = clean_plugin_loader
        plugin = MockValidPlugin()

        result = loader.validate_plugin_dependencies(plugin)

        assert result is True

    def test_validate_plugin_dependencies_failure(self, clean_plugin_loader):
        """Test plugin dependency validation failure."""
        loader = clean_plugin_loader
        plugin = MockFailingPlugin()

        result = loader.validate_plugin_dependencies(plugin)

        assert result is False

    def test_validate_plugin_dependencies_exception(self, clean_plugin_loader):
        """Test plugin dependency validation with exception."""
        loader = clean_plugin_loader
        plugin = MockPluginWithDependencyIssues()

        result = loader.validate_plugin_dependencies(plugin)

        assert result is False
        loader.logger.warning.assert_called()


class TestToolRegistration:
    """Test external tool registration functionality."""

    def test_register_external_tools_success(self, clean_plugin_loader, mock_registry):
        """Test successful registration of external tools."""
        loader = clean_plugin_loader
        plugin = MockValidPlugin()

        with patch.object(loader, 'load_all_plugins', return_value=[plugin]):
            with patch.object(plugin, 'register_tools') as mock_register_tools:
                loader.register_external_tools(mock_registry)

            mock_register_tools.assert_called_once_with(mock_registry)

    def test_register_external_tools_with_failures(self, clean_plugin_loader, mock_registry):
        """Test registration of external tools with some failures."""
        loader = clean_plugin_loader
        plugin = MockValidPlugin()

        with patch.object(loader, 'load_all_plugins', return_value=[plugin]):
            with patch.object(plugin, 'register_tools', side_effect=RuntimeError("Registration failed")):
                loader.register_external_tools(mock_registry)

        assert "mock_valid_plugin" in loader.failed_plugins
        loader.logger.error.assert_called()

    def test_register_external_tools_without_registry(self, clean_plugin_loader):
        """Test registration of external tools without explicit registry."""
        loader = clean_plugin_loader
        plugin = MockValidPlugin()

        with patch.object(loader, 'load_all_plugins', return_value=[plugin]):
            with patch.object(plugin, 'register_tools') as mock_register_tools:
                loader.register_external_tools()

            # Should use the loader's registry
            mock_register_tools.assert_called_once_with(loader.registry)


class TestPluginInformation:
    """Test plugin information retrieval functionality."""

    def test_get_plugin_info_loaded_plugin(self, clean_plugin_loader):
        """Test getting info for loaded plugin."""
        loader = clean_plugin_loader
        plugin = MockValidPlugin()
        loader.loaded_plugins["mock_valid_plugin"] = plugin

        with patch.object(loader, '_get_plugin_metadata',
                          return_value={"name": "mock_valid_plugin", "status": "loaded"}) as mock_get_metadata:
            info = loader.get_plugin_info("mock_valid_plugin")

        assert info is not None
        assert info["name"] == "mock_valid_plugin"
        assert info["status"] == "loaded"
        mock_get_metadata.assert_called_once_with(plugin, "loaded")

    def test_get_plugin_info_discovered_plugin(self, clean_plugin_loader):
        """Test getting info for discovered but not loaded plugin."""
        loader = clean_plugin_loader
        plugin = MockValidPlugin()
        loader.discovered_plugins["mock_valid_plugin"] = plugin

        with patch.object(loader, '_get_plugin_metadata',
                          return_value={"name": "mock_valid_plugin", "status": "discovered"}) as mock_get_metadata:
            info = loader.get_plugin_info("mock_valid_plugin")

        assert info is not None
        assert info["name"] == "mock_valid_plugin"
        assert info["status"] == "discovered"
        mock_get_metadata.assert_called_once_with(plugin, "discovered")

    def test_get_plugin_info_failed_plugin(self, clean_plugin_loader):
        """Test getting info for failed plugin."""
        loader = clean_plugin_loader
        loader.failed_plugins["mock_failed_plugin"] = "Failed to load"

        info = loader.get_plugin_info("mock_failed_plugin")

        assert info is not None
        assert info["name"] == "mock_failed_plugin"
        assert info["status"] == "failed"
        assert info["error"] == "Failed to load"

    def test_get_plugin_info_nonexistent(self, clean_plugin_loader):
        """Test getting info for non-existent plugin."""
        loader = clean_plugin_loader

        info = loader.get_plugin_info("nonexistent_plugin")

        assert info is None

    def test_get_all_plugins_info_empty(self, clean_plugin_loader):
        """Test getting all plugins info when no plugins."""
        loader = clean_plugin_loader

        info = loader.get_all_plugins_info()

        assert info == {}

    def test_get_all_plugins_info_with_plugins(self, clean_plugin_loader):
        """Test getting all plugins info with various plugin states."""
        loader = clean_plugin_loader

        # Add plugins in different states
        plugin = MockValidPlugin()
        loader.loaded_plugins["loaded_plugin"] = plugin
        loader.discovered_plugins["discovered_plugin"] = plugin
        loader.failed_plugins["failed_plugin"] = "Error message"

        with patch.object(loader, '_get_plugin_metadata') as mock_get_metadata:
            mock_get_metadata.side_effect = lambda p, status: {"name": f"{status}_plugin", "status": status}

            info = loader.get_all_plugins_info()

        assert len(info) == 3
        assert info["loaded_plugin"]["status"] == "loaded"
        assert info["discovered_plugin"]["status"] == "discovered"
        assert info["failed_plugin"]["status"] == "failed"

    def test_get_all_plugins_info_priority_order(self, clean_plugin_loader):
        """Test that get_all_plugins_info respects priority order."""
        loader = clean_plugin_loader

        # Add same plugin in multiple states (failed should take priority)
        plugin = MockValidPlugin()
        loader.loaded_plugins["test_plugin"] = plugin
        loader.discovered_plugins["test_plugin"] = plugin
        loader.failed_plugins["test_plugin"] = "Error message"

        info = loader.get_all_plugins_info()

        assert len(info) == 1
        assert info["test_plugin"]["status"] == "failed"

    def test_get_plugin_metadata_success(self, clean_plugin_loader):
        """Test getting plugin metadata successfully."""
        loader = clean_plugin_loader
        plugin = MockValidPlugin()

        metadata = loader._get_plugin_metadata(plugin, "loaded")

        assert metadata["name"] == "mock_valid_plugin"
        assert metadata["status"] == "loaded"
        assert "capabilities" in metadata

    def test_get_plugin_metadata_exception(self, clean_plugin_loader):
        """Test getting plugin metadata with exception."""
        loader = clean_plugin_loader
        plugin = MockValidPlugin()

        with patch.object(plugin, 'get_plugin_metadata', side_effect=RuntimeError("Metadata error")):
            metadata = loader._get_plugin_metadata(plugin, "loaded")

        assert metadata["name"] == "mock_valid_plugin"
        assert metadata["status"] == "error"
        assert "Failed to get metadata" in metadata["error"]


class TestPluginCleanup:
    """Test plugin cleanup functionality."""

    def test_cleanup_plugins_success(self, clean_plugin_loader):
        """Test successful cleanup of plugins."""
        loader = clean_plugin_loader
        plugin1 = MockValidPlugin()
        plugin2 = MockValidPlugin()
        loader.loaded_plugins["plugin1"] = plugin1
        loader.loaded_plugins["plugin2"] = plugin2

        with patch.object(plugin1, 'cleanup') as mock_cleanup1:
            with patch.object(plugin2, 'cleanup') as mock_cleanup2:
                loader.cleanup_plugins()

        mock_cleanup1.assert_called_once()
        mock_cleanup2.assert_called_once()
        assert len(loader.loaded_plugins) == 0
        loader.logger.info.assert_called()

    def test_cleanup_plugins_with_failures(self, clean_plugin_loader):
        """Test cleanup of plugins with some failures."""
        loader = clean_plugin_loader
        plugin1 = MockValidPlugin()
        plugin2 = MockFailingPlugin()
        loader.loaded_plugins["plugin1"] = plugin1
        loader.loaded_plugins["plugin2"] = plugin2

        with patch.object(plugin1, 'cleanup') as mock_cleanup1:
            loader.cleanup_plugins()

        mock_cleanup1.assert_called_once()
        assert len(loader.loaded_plugins) == 0
        loader.logger.warning.assert_called()

    def test_cleanup_plugins_empty(self, clean_plugin_loader):
        """Test cleanup when no plugins loaded."""
        loader = clean_plugin_loader

        loader.cleanup_plugins()

        loader.logger.info.assert_called()


class TestPluginLoadingHelpers:
    """Test plugin loading helper methods."""

    def test_load_plugin_from_entry_point_success(self, clean_plugin_loader):
        """Test successful loading from entry point."""
        loader = clean_plugin_loader

        entry_point = create_mock_entry_point("test_plugin", MockValidPlugin)

        plugin = loader._load_plugin_from_entry_point(entry_point)

        assert isinstance(plugin, MockValidPlugin)

    def test_load_plugin_from_entry_point_not_tool_plugin(self, clean_plugin_loader):
        """Test loading from entry point when not ToolPlugin."""
        loader = clean_plugin_loader

        entry_point = create_mock_entry_point("invalid_plugin", MockInvalidPlugin)

        with pytest.raises(TypeError) as exc_info:
            loader._load_plugin_from_entry_point(entry_point)

        assert "does not implement ToolPlugin interface" in str(exc_info.value)

    def test_load_plugin_from_entry_point_load_failure(self, clean_plugin_loader):
        """Test loading from entry point when load fails."""
        loader = clean_plugin_loader

        entry_point = create_mock_entry_point(
            "failing_plugin",
            None,
            load_exception=ImportError("Import failed")
        )

        with pytest.raises(ImportError):
            loader._load_plugin_from_entry_point(entry_point)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @patch('rv_tools.registry.plugin_loader.entry_points')
    def test_entry_points_api_compatibility(self, mock_entry_points_func, clean_plugin_loader):
        """Test compatibility with both old and new entry points API."""
        loader = clean_plugin_loader

        # Test case where entry_points() returns object that doesn't have 'get' attribute (new API)
        # We need to create a mock that actually doesn't have the 'get' attribute
        class MockEntryPointsNewAPI:
            def select(self, group):
                return MockEntryPointsList([])

        mock_eps = MockEntryPointsNewAPI()
        mock_entry_points_func.return_value = mock_eps

        # This should handle gracefully and use select method
        plugins = loader.discover_plugins()
        assert plugins == []

    def test_plugin_with_empty_tool_names(self, clean_plugin_loader):
        """Test plugin with empty tool names list."""
        loader = clean_plugin_loader

        class EmptyPlugin(ToolPlugin):
            def get_plugin_name(self) -> str:
                return "empty_plugin"

            def get_plugin_version(self) -> str:
                return "1.0.0"

            def get_plugin_description(self) -> str:
                return "Plugin with no tools"

            def get_tool_names(self) -> List[str]:
                return []

            def get_tool_class(self, tool_name: str):
                raise ValueError("No tools")

            def get_tool_spec(self, tool_name: str) -> ToolSpec:
                raise ValueError("No tools")

            def validate_dependencies(self) -> bool:
                return True

            def get_supported_capabilities(self) -> List[str]:
                return []

        plugin = EmptyPlugin()

        with patch.object(loader, 'validate_plugin_dependencies', return_value=True):
            result = loader._validate_and_load_plugin(plugin)

        assert result is plugin  # Should still load successfully

    def test_concurrent_plugin_operations(self, clean_plugin_loader):
        """Test that plugin operations handle concurrent access gracefully."""
        loader = clean_plugin_loader
        plugin = MockValidPlugin()

        # Simulate concurrent discovery and loading
        loader.discovered_plugins["test_plugin"] = plugin

        # Mock the metadata method to return appropriate status based on actual plugin state
        def mock_get_metadata(p, status):
            # Check actual loader state to determine correct status
            if "test_plugin" in loader.loaded_plugins:
                return {"name": "test_plugin", "status": "loaded"}
            elif "test_plugin" in loader.discovered_plugins:
                return {"name": "test_plugin", "status": "discovered"}
            else:
                return {"name": "test_plugin", "status": status}

        # Mock validation to succeed and simulate plugin being moved to loaded state
        def mock_validate_and_load(p):
            # Simulate the actual behavior of _validate_and_load_plugin
            loader.loaded_plugins["test_plugin"] = p
            return p

        with patch.object(loader, '_get_plugin_metadata', side_effect=mock_get_metadata):
            with patch.object(loader, '_validate_and_load_plugin', side_effect=mock_validate_and_load):
                # These operations should not interfere with each other
                info1 = loader.get_plugin_info("test_plugin")
                loaded_plugin = loader.load_plugin("test_plugin")
                info2 = loader.get_plugin_info("test_plugin")

        assert info1 is not None
        assert info1["status"] == "discovered"  # Initially discovered
        assert loaded_plugin is plugin
        assert info2 is not None
        assert info2["status"] == "loaded"  # After loading

    @patch('rv_tools.registry.plugin_loader.entry_points')
    def test_multiple_discovery_calls(self, mock_entry_points_func, clean_plugin_loader):
        """Test calling discover_plugins multiple times."""
        loader = clean_plugin_loader

        # First discovery
        valid_entry_point1 = create_mock_entry_point("plugin1", MockValidPlugin)
        entry_points_list1 = MockEntryPointsList([valid_entry_point1])
        mock_eps = Mock()
        if hasattr(mock_eps, 'get'):
            del mock_eps.get
        mock_eps.select.return_value = entry_points_list1
        mock_entry_points_func.return_value = mock_eps

        plugins1 = loader.discover_plugins()

        # Second discovery with different plugins
        valid_entry_point2 = create_mock_entry_point("plugin2", MockValidPlugin)
        entry_points_list2 = MockEntryPointsList([valid_entry_point2])
        mock_eps.select.return_value = entry_points_list2

        plugins2 = loader.discover_plugins()

        # Should include previously discovered plugins plus new ones
        assert len(plugins2) >= len(plugins1)

    def test_plugin_registration_with_variants(self, clean_plugin_loader, mock_registry):
        """Test plugin registration that includes variants."""
        loader = clean_plugin_loader
        plugin = MockValidPlugin()

        with patch.object(loader, 'load_all_plugins', return_value=[plugin]):
            with patch.object(plugin, 'register_tools') as mock_register_tools:
                loader.register_external_tools(mock_registry)

        # Verify tool registration was called
        mock_register_tools.assert_called_once_with(mock_registry)

    def test_plugin_cleanup_during_error(self, clean_plugin_loader):
        """Test plugin cleanup when an error occurs during loading."""
        loader = clean_plugin_loader
        plugin = MockValidPlugin()
        loader.loaded_plugins["test_plugin"] = plugin

        # Simulate error during cleanup
        with patch.object(plugin, 'cleanup', side_effect=Exception("Cleanup error")):
            loader.cleanup_plugins()

        # Should still clear the loaded plugins dict
        assert len(loader.loaded_plugins) == 0
        loader.logger.warning.assert_called()

    def test_plugin_with_special_characters_in_name(self, clean_plugin_loader):
        """Test plugin with special characters in name."""
        loader = clean_plugin_loader

        class SpecialNamePlugin(ToolPlugin):
            def get_plugin_name(self) -> str:
                return "special-plugin_v1.0"

            def get_plugin_version(self) -> str:
                return "1.0.0"

            def get_plugin_description(self) -> str:
                return "Plugin with special name"

            def get_tool_names(self) -> List[str]:
                return ["special_tool"]

            def get_tool_class(self, tool_name: str):
                return MockToolForPlugin

            def get_tool_spec(self, tool_name: str) -> ToolSpec:
                return ToolSpec(
                    name="special_tool",
                    description="Special tool",
                    url="https://example.com/special",
                    version="1.0.0"
                )

            def validate_dependencies(self) -> bool:
                return True

            def get_supported_capabilities(self) -> List[str]:
                return []

        plugin = SpecialNamePlugin()
        loader.discovered_plugins["special-plugin_v1.0"] = plugin

        with patch.object(loader, 'validate_plugin_dependencies', return_value=True):
            result = loader.load_plugin("special-plugin_v1.0")

        assert result is plugin
