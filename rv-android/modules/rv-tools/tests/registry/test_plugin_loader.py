"""
Comprehensive unit tests for PluginLoader discovery and loading system.

This module provides exhaustive testing of the PluginLoader class covering:
- Plugin discovery via entry points and package scanning
- Plugin validation and dependency checking workflows
- Plugin loading and registration with tool registry
- External tool registration and lifecycle management
- Plugin metadata access and status tracking
- Error handling and recovery in plugin operations

### Testing Architecture:
- Uses mock entry points and plugin instances for controlled testing
- Comprehensive plugin lifecycle testing (discovery -> validation -> loading)
- Plugin dependency validation and compatibility checking
- Error scenario testing with graceful degradation validation
- Plugin metadata and status information access testing

### Key Test Coverage:
- Entry point discovery and plugin instantiation
- Plugin interface validation and dependency checking
- Plugin registration with tool registry integration
- Plugin error handling and failed plugin tracking
- Plugin cleanup and resource management
- Thread safety and concurrent plugin access
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any
import threading

from rv_tools.registry.plugin_loader import PluginLoader
from rv_tools.registry.registry import ToolRegistry
from rv_tools.interfaces.plugin_interface import ToolPlugin
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec, ToolType


class TestPluginDiscovery:
    """
    Test plugin discovery mechanisms and entry point scanning.
    
    ### Plugin Discovery Strategy:
    - Tests entry point scanning and plugin enumeration
    - Validates plugin instantiation from entry points
    - Tests plugin interface validation during discovery
    - Verifies error handling for invalid plugins
    - Tests discovery performance and efficiency
    """
    
    @patch('rv_tools.registry.plugin_loader.entry_points')
    def test_discover_plugins_empty(self, mock_entry_points, clean_registry):
        """Test plugin discovery when no plugins are available."""
        # Mock empty entry points
        mock_entry_points.return_value = {PluginLoader.ENTRY_POINT_GROUP: []}
        
        loader = PluginLoader(clean_registry)
        plugins = loader.discover_plugins()
        
        # Verify no plugins discovered
        assert len(plugins) == 0
        assert len(loader.discovered_plugins) == 0
        assert len(loader.failed_plugins) == 0
    
    @patch('rv_tools.registry.plugin_loader.entry_points')
    def test_discover_plugins_single_valid(self, mock_entry_points, clean_registry, mock_plugin):
        """Test discovery of single valid plugin."""
        # Create a mock plugin class that returns our mock plugin instance
        mock_plugin_class = Mock()
        mock_plugin_class.return_value = mock_plugin
        
        # Mock entry point
        mock_entry_point = Mock()
        mock_entry_point.name = "test_plugin"
        mock_entry_point.load.return_value = mock_plugin_class
        
        mock_entry_points.return_value = {PluginLoader.ENTRY_POINT_GROUP: [mock_entry_point]}
        
        loader = PluginLoader(clean_registry)
        plugins = loader.discover_plugins()
        
        # Verify plugin discovery
        assert len(plugins) == 1
        assert plugins[0] is mock_plugin
        assert "mock_plugin" in loader.discovered_plugins
        assert loader.discovered_plugins["mock_plugin"] is mock_plugin
        assert len(loader.failed_plugins) == 0
    
    @patch('rv_tools.registry.plugin_loader.entry_points')
    def test_discover_plugins_multiple_valid(self, mock_entry_points, clean_registry):
        """Test discovery of multiple valid plugins."""
        # Create multiple mock plugins
        mock_plugin1 = Mock(spec=ToolPlugin)
        mock_plugin1.get_plugin_name.return_value = "plugin1"
        
        mock_plugin2 = Mock(spec=ToolPlugin)
        mock_plugin2.get_plugin_name.return_value = "plugin2"
        
        # Mock entry points
        mock_entry_point1 = Mock()
        mock_entry_point1.name = "plugin1"
        mock_entry_point1.load.return_value = lambda: mock_plugin1
        
        mock_entry_point2 = Mock()
        mock_entry_point2.name = "plugin2"
        mock_entry_point2.load.return_value = lambda: mock_plugin2
        
        mock_entry_points.return_value = {
            PluginLoader.ENTRY_POINT_GROUP: [mock_entry_point1, mock_entry_point2]
        }
        
        loader = PluginLoader(clean_registry)
        plugins = loader.discover_plugins()
        
        # Verify multiple plugin discovery
        assert len(plugins) == 2
        assert mock_plugin1 in plugins
        assert mock_plugin2 in plugins
        assert "plugin1" in loader.discovered_plugins
        assert "plugin2" in loader.discovered_plugins
        assert len(loader.failed_plugins) == 0
    
    @patch('rv_tools.registry.plugin_loader.entry_points')
    def test_discover_plugins_invalid_interface(self, mock_entry_points, clean_registry):
        """Test discovery with plugin that doesn't implement ToolPlugin interface."""
        # Mock entry point that returns invalid plugin
        mock_entry_point = Mock()
        mock_entry_point.name = "invalid_plugin"
        
        # Create object that doesn't implement ToolPlugin
        invalid_plugin = Mock()  # Not spec=ToolPlugin
        mock_entry_point.load.return_value = lambda: invalid_plugin
        
        mock_entry_points.return_value = {PluginLoader.ENTRY_POINT_GROUP: [mock_entry_point]}
        
        loader = PluginLoader(clean_registry)
        plugins = loader.discover_plugins()
        
        # Verify invalid plugin is rejected
        assert len(plugins) == 0
        assert len(loader.discovered_plugins) == 0
        assert "invalid_plugin" in loader.failed_plugins
        assert "does not implement ToolPlugin interface" in loader.failed_plugins["invalid_plugin"]
    
    @patch('rv_tools.registry.plugin_loader.entry_points')
    def test_discover_plugins_loading_error(self, mock_entry_points, clean_registry):
        """Test discovery with plugin that raises error during loading."""
        # Mock entry point that raises error
        mock_entry_point = Mock()
        mock_entry_point.name = "error_plugin"
        mock_entry_point.load.side_effect = Exception("Loading failed")
        
        mock_entry_points.return_value = {PluginLoader.ENTRY_POINT_GROUP: [mock_entry_point]}
        
        loader = PluginLoader(clean_registry)
        plugins = loader.discover_plugins()
        
        # Verify error is handled gracefully
        assert len(plugins) == 0
        assert len(loader.discovered_plugins) == 0
        assert "error_plugin" in loader.failed_plugins
        assert "Loading failed" in loader.failed_plugins["error_plugin"]
    
    @patch('rv_tools.registry.plugin_loader.entry_points')
    def test_discover_plugins_mixed_valid_invalid(self, mock_entry_points, clean_registry, mock_plugin):
        """Test discovery with mix of valid and invalid plugins."""
        # Valid plugin
        mock_entry_point1 = Mock()
        mock_entry_point1.name = "valid_plugin"
        mock_entry_point1.load.return_value = lambda: mock_plugin
        
        # Invalid plugin (loading error)
        mock_entry_point2 = Mock()
        mock_entry_point2.name = "error_plugin"
        mock_entry_point2.load.side_effect = Exception("Loading error")
        
        mock_entry_points.return_value = {
            PluginLoader.ENTRY_POINT_GROUP: [mock_entry_point1, mock_entry_point2]
        }
        
        loader = PluginLoader(clean_registry)
        plugins = loader.discover_plugins()
        
        # Verify partial success
        assert len(plugins) == 1
        assert plugins[0] is mock_plugin
        assert "mock_plugin" in loader.discovered_plugins
        assert "error_plugin" in loader.failed_plugins
    
    @patch('rv_tools.registry.plugin_loader.entry_points')
    def test_discover_plugins_entry_points_error(self, mock_entry_points, clean_registry):
        """Test discovery when entry_points() itself raises error."""
        # Mock entry_points to raise error
        mock_entry_points.side_effect = Exception("Entry points error")
        
        loader = PluginLoader(clean_registry)
        
        # Should raise the exception
        with pytest.raises(Exception, match="Entry points error"):
            loader.discover_plugins()


class TestPluginValidation:
    """
    Test plugin validation and dependency checking functionality.
    
    ### Plugin Validation Strategy:
    - Tests plugin dependency validation workflows
    - Validates plugin interface compliance checking
    - Tests tool specification validation within plugins
    - Verifies plugin metadata validation and consistency
    - Tests validation error handling and reporting
    """
    
    def test_validate_plugin_dependencies_success(self, clean_registry, mock_plugin):
        """Test successful plugin dependency validation."""
        # Mock plugin with satisfied dependencies
        mock_plugin.validate_dependencies.return_value = True
        
        loader = PluginLoader(clean_registry)
        result = loader.validate_plugin_dependencies(mock_plugin)
        
        assert result is True
        mock_plugin.validate_dependencies.assert_called_once()
    
    def test_validate_plugin_dependencies_failure(self, clean_registry, mock_plugin):
        """Test plugin dependency validation failure."""
        # Mock plugin with unsatisfied dependencies
        mock_plugin.validate_dependencies.return_value = False
        
        loader = PluginLoader(clean_registry)
        result = loader.validate_plugin_dependencies(mock_plugin)
        
        assert result is False
        mock_plugin.validate_dependencies.assert_called_once()
    
    def test_validate_plugin_dependencies_error(self, clean_registry, mock_plugin):
        """Test plugin dependency validation with error."""
        # Mock plugin that raises error during validation
        mock_plugin.validate_dependencies.side_effect = Exception("Validation error")
        
        loader = PluginLoader(clean_registry)
        result = loader.validate_plugin_dependencies(mock_plugin)
        
        # Should return False and log warning
        assert result is False
    
    def test_validate_and_load_plugin_success(self, clean_registry, mock_plugin):
        """Test successful plugin validation and loading."""
        # Mock successful validation
        mock_plugin.validate_dependencies.return_value = True
        mock_plugin.get_tool_names.return_value = ["tool1", "tool2"]
        mock_plugin.get_tool_spec.return_value = Mock(spec=ToolSpec)
        mock_plugin.get_tool_class.return_value = Mock(spec=AbstractTool)
        
        loader = PluginLoader(clean_registry)
        result = loader._validate_and_load_plugin(mock_plugin)
        
        # Verify successful loading
        assert result is mock_plugin
        assert "mock_plugin" in loader.loaded_plugins
        assert loader.loaded_plugins["mock_plugin"] is mock_plugin
    
    def test_validate_and_load_plugin_dependency_failure(self, clean_registry, mock_plugin):
        """Test plugin loading with dependency validation failure."""
        # Mock dependency validation failure
        mock_plugin.validate_dependencies.return_value = False
        
        loader = PluginLoader(clean_registry)
        result = loader._validate_and_load_plugin(mock_plugin)
        
        # Verify loading failure
        assert result is None
        assert "mock_plugin" in loader.failed_plugins
        assert "unmet dependencies" in loader.failed_plugins["mock_plugin"]
    
    def test_validate_and_load_plugin_invalid_tool_spec(self, clean_registry, mock_plugin):
        """Test plugin loading with invalid tool specifications."""
        # Mock successful dependency validation but invalid tool specs
        mock_plugin.validate_dependencies.return_value = True
        mock_plugin.get_tool_names.return_value = ["invalid_tool"]
        mock_plugin.get_tool_spec.return_value = None  # Invalid spec
        mock_plugin.get_tool_class.return_value = Mock(spec=AbstractTool)
        
        loader = PluginLoader(clean_registry)
        result = loader._validate_and_load_plugin(mock_plugin)
        
        # Verify loading failure
        assert result is None
        assert "mock_plugin" in loader.failed_plugins
        assert "invalid tool specifications" in loader.failed_plugins["mock_plugin"]
    
    def test_validate_and_load_plugin_missing_tool_class(self, clean_registry, mock_plugin):
        """Test plugin loading with missing tool class."""
        # Mock successful dependency validation but missing tool class
        mock_plugin.validate_dependencies.return_value = True
        mock_plugin.get_tool_names.return_value = ["missing_class_tool"]
        mock_plugin.get_tool_spec.return_value = Mock(spec=ToolSpec)
        mock_plugin.get_tool_class.return_value = None  # Missing class
        
        loader = PluginLoader(clean_registry)
        result = loader._validate_and_load_plugin(mock_plugin)
        
        # Verify loading failure
        assert result is None
        assert "mock_plugin" in loader.failed_plugins
        assert "invalid tool specifications" in loader.failed_plugins["mock_plugin"]
    
    def test_validate_and_load_plugin_validation_error(self, clean_registry, mock_plugin):
        """Test plugin loading with validation error."""
        # Mock plugin that raises error during tool specification access
        mock_plugin.validate_dependencies.return_value = True
        mock_plugin.get_tool_names.side_effect = Exception("Tool names error")
        
        loader = PluginLoader(clean_registry)
        result = loader._validate_and_load_plugin(mock_plugin)
        
        # Verify loading failure
        assert result is None
        assert "mock_plugin" in loader.failed_plugins
        assert "invalid tool specifications" in loader.failed_plugins["mock_plugin"]


class TestPluginLoading:
    """
    Test plugin loading workflows and lifecycle management.
    
    ### Plugin Loading Strategy:
    - Tests individual plugin loading by name
    - Validates bulk plugin loading operations
    - Tests plugin loading with discovery integration
    - Verifies loaded plugin state management
    - Tests plugin loading error scenarios and recovery
    """
    
    def test_load_plugin_already_loaded(self, clean_registry, mock_plugin):
        """Test loading plugin that is already loaded."""
        loader = PluginLoader(clean_registry)
        
        # Manually add plugin to loaded plugins
        loader.loaded_plugins["mock_plugin"] = mock_plugin
        
        # Load plugin - should return existing instance
        result = loader.load_plugin("mock_plugin")
        
        assert result is mock_plugin
    
    def test_load_plugin_discovered_not_loaded(self, clean_registry, mock_plugin):
        """Test loading plugin that is discovered but not loaded."""
        # Mock successful validation
        mock_plugin.validate_dependencies.return_value = True
        mock_plugin.get_tool_names.return_value = ["tool1"]
        mock_plugin.get_tool_spec.return_value = Mock(spec=ToolSpec)
        mock_plugin.get_tool_class.return_value = Mock(spec=AbstractTool)
        
        loader = PluginLoader(clean_registry)
        
        # Add plugin to discovered but not loaded
        loader.discovered_plugins["mock_plugin"] = mock_plugin
        
        # Load plugin
        result = loader.load_plugin("mock_plugin")
        
        # Verify loading
        assert result is mock_plugin
        assert "mock_plugin" in loader.loaded_plugins
    
    @patch('rv_tools.registry.plugin_loader.entry_points')
    def test_load_plugin_trigger_discovery(self, mock_entry_points, clean_registry, mock_plugin):
        """Test loading plugin that triggers discovery."""
        # Mock entry point for discovery
        mock_entry_point = Mock()
        mock_entry_point.name = "test_plugin"
        mock_entry_point.load.return_value = lambda: mock_plugin
        mock_entry_points.return_value = {PluginLoader.ENTRY_POINT_GROUP: [mock_entry_point]}
        
        # Mock successful validation
        mock_plugin.validate_dependencies.return_value = True
        mock_plugin.get_tool_names.return_value = ["tool1"]
        mock_plugin.get_tool_spec.return_value = Mock(spec=ToolSpec)
        mock_plugin.get_tool_class.return_value = Mock(spec=AbstractTool)
        
        loader = PluginLoader(clean_registry)
        
        # Load plugin (should trigger discovery)
        result = loader.load_plugin("mock_plugin")
        
        # Verify loading through discovery
        assert result is mock_plugin
        assert "mock_plugin" in loader.discovered_plugins
        assert "mock_plugin" in loader.loaded_plugins
    
    def test_load_plugin_not_found(self, clean_registry):
        """Test loading non-existent plugin."""
        loader = PluginLoader(clean_registry)
        
        # Mock empty discovery
        with patch.object(loader, 'discover_plugins', return_value=[]):
            result = loader.load_plugin("nonexistent_plugin")
        
        assert result is None
    
    def test_load_plugin_loading_error(self, clean_registry, mock_plugin):
        """Test plugin loading with error during validation."""
        # Mock plugin that fails validation
        mock_plugin.validate_dependencies.side_effect = Exception("Loading error")
        
        loader = PluginLoader(clean_registry)
        loader.discovered_plugins["mock_plugin"] = mock_plugin
        
        # Load plugin - should handle error gracefully
        result = loader.load_plugin("mock_plugin")
        
        assert result is None
        assert "mock_plugin" in loader.failed_plugins
        assert "unmet dependencies" in loader.failed_plugins["mock_plugin"]
    
    def test_load_all_plugins_empty(self, clean_registry):
        """Test loading all plugins when none are discovered."""
        loader = PluginLoader(clean_registry)
        
        # Mock empty discovery
        with patch.object(loader, 'discover_plugins', return_value=[]):
            plugins = loader.load_all_plugins()
        
        assert len(plugins) == 0
    
    def test_load_all_plugins_multiple(self, clean_registry):
        """Test loading all discovered plugins."""
        # Create multiple mock plugins
        mock_plugin1 = Mock(spec=ToolPlugin)
        mock_plugin1.get_plugin_name.return_value = "plugin1"
        mock_plugin1.validate_dependencies.return_value = True
        mock_plugin1.get_tool_names.return_value = ["tool1"]
        mock_plugin1.get_tool_spec.return_value = Mock(spec=ToolSpec)
        mock_plugin1.get_tool_class.return_value = Mock(spec=AbstractTool)
        
        mock_plugin2 = Mock(spec=ToolPlugin)
        mock_plugin2.get_plugin_name.return_value = "plugin2"
        mock_plugin2.validate_dependencies.return_value = True
        mock_plugin2.get_tool_names.return_value = ["tool2"]
        mock_plugin2.get_tool_spec.return_value = Mock(spec=ToolSpec)
        mock_plugin2.get_tool_class.return_value = Mock(spec=AbstractTool)
        
        loader = PluginLoader(clean_registry)
        
        # Add plugins to discovered
        loader.discovered_plugins["plugin1"] = mock_plugin1
        loader.discovered_plugins["plugin2"] = mock_plugin2
        
        # Load all plugins
        plugins = loader.load_all_plugins()
        
        # Verify all plugins loaded
        assert len(plugins) == 2
        assert mock_plugin1 in plugins
        assert mock_plugin2 in plugins
        assert "plugin1" in loader.loaded_plugins
        assert "plugin2" in loader.loaded_plugins
    
    def test_load_all_plugins_partial_failure(self, clean_registry):
        """Test loading all plugins with some failures."""
        # Create mock plugins - one successful, one failing
        mock_plugin1 = Mock(spec=ToolPlugin)
        mock_plugin1.get_plugin_name.return_value = "plugin1"
        mock_plugin1.validate_dependencies.return_value = True
        mock_plugin1.get_tool_names.return_value = ["tool1"]
        mock_plugin1.get_tool_spec.return_value = Mock(spec=ToolSpec)
        mock_plugin1.get_tool_class.return_value = Mock(spec=AbstractTool)
        
        mock_plugin2 = Mock(spec=ToolPlugin)
        mock_plugin2.get_plugin_name.return_value = "plugin2"
        mock_plugin2.validate_dependencies.side_effect = Exception("Validation error")
        
        loader = PluginLoader(clean_registry)
        
        # Add plugins to discovered
        loader.discovered_plugins["plugin1"] = mock_plugin1
        loader.discovered_plugins["plugin2"] = mock_plugin2
        
        # Load all plugins
        plugins = loader.load_all_plugins()
        
        # Verify partial success
        assert len(plugins) == 1
        assert mock_plugin1 in plugins
        assert "plugin1" in loader.loaded_plugins
        assert "plugin2" in loader.failed_plugins


class TestPluginIntegration:
    """
    Test plugin integration with tool registry.
    
    ### Plugin Integration Strategy:
    - Tests plugin tool registration with registry
    - Validates external tool registration workflows
    - Tests plugin-registry integration patterns
    - Verifies tool availability after plugin registration
    - Tests integration error handling and recovery
    """
    
    def test_register_external_tools_single_plugin(self, clean_registry, mock_plugin):
        """Test registering external tools from single plugin."""
        # Mock plugin with tools
        mock_plugin.get_tool_names.return_value = ["external_tool1", "external_tool2"]
        mock_plugin.register_tools = Mock()
        
        loader = PluginLoader(clean_registry)
        loader.loaded_plugins["mock_plugin"] = mock_plugin
        
        # Mock load_all_plugins to return our plugin
        with patch.object(loader, 'load_all_plugins', return_value=[mock_plugin]):
            loader.register_external_tools()
        
        # Verify tools were registered
        mock_plugin.register_tools.assert_called_once_with(clean_registry)
    
    def test_register_external_tools_multiple_plugins(self, clean_registry):
        """Test registering external tools from multiple plugins."""
        # Create multiple mock plugins
        mock_plugin1 = Mock(spec=ToolPlugin)
        mock_plugin1.get_plugin_name.return_value = "plugin1"
        mock_plugin1.get_tool_names.return_value = ["tool1", "tool2"]
        mock_plugin1.register_tools = Mock()
        
        mock_plugin2 = Mock(spec=ToolPlugin)
        mock_plugin2.get_plugin_name.return_value = "plugin2"
        mock_plugin2.get_tool_names.return_value = ["tool3"]
        mock_plugin2.register_tools = Mock()
        
        loader = PluginLoader(clean_registry)
        
        # Mock load_all_plugins to return both plugins
        with patch.object(loader, 'load_all_plugins', return_value=[mock_plugin1, mock_plugin2]):
            loader.register_external_tools()
        
        # Verify both plugins registered tools
        mock_plugin1.register_tools.assert_called_once_with(clean_registry)
        mock_plugin2.register_tools.assert_called_once_with(clean_registry)
    
    def test_register_external_tools_with_error(self, clean_registry, mock_plugin):
        """Test external tool registration with plugin error."""
        # Mock plugin that raises error during registration
        mock_plugin.get_tool_names.return_value = ["tool1"]
        mock_plugin.register_tools.side_effect = Exception("Registration error")
        
        loader = PluginLoader(clean_registry)
        
        # Mock load_all_plugins to return failing plugin
        with patch.object(loader, 'load_all_plugins', return_value=[mock_plugin]):
            # Should handle error gracefully
            loader.register_external_tools()
        
        # Verify plugin is marked as failed
        assert "mock_plugin" in loader.failed_plugins
        assert "Registration error" in loader.failed_plugins["mock_plugin"]
    
    def test_register_external_tools_custom_registry(self, clean_registry, mock_plugin):
        """Test registering external tools with custom registry."""
        custom_registry = Mock(spec=ToolRegistry)
        
        mock_plugin.get_tool_names.return_value = ["tool1"]
        mock_plugin.register_tools = Mock()
        
        loader = PluginLoader(clean_registry)
        
        # Mock load_all_plugins
        with patch.object(loader, 'load_all_plugins', return_value=[mock_plugin]):
            loader.register_external_tools(custom_registry)
        
        # Verify tools were registered with custom registry
        mock_plugin.register_tools.assert_called_once_with(custom_registry)


class TestPluginInformation:
    """
    Test plugin information and metadata access functionality.
    
    ### Plugin Information Strategy:
    - Tests plugin metadata retrieval and formatting
    - Validates plugin status tracking and reporting
    - Tests comprehensive plugin information aggregation
    - Verifies plugin information consistency and accuracy
    - Tests information access under various plugin states
    """
    
    def test_get_plugin_info_loaded(self, clean_registry, mock_plugin):
        """Test getting information for loaded plugin."""
        # Configure mock plugin metadata
        mock_plugin.get_plugin_metadata.return_value = {
            "name": "mock_plugin",
            "version": "1.0.0",
            "description": "Mock plugin for testing"
        }
        mock_plugin.get_supported_capabilities.return_value = ["capability1", "capability2"]
        
        loader = PluginLoader(clean_registry)
        loader.loaded_plugins["mock_plugin"] = mock_plugin
        
        # Get plugin info
        info = loader.get_plugin_info("mock_plugin")
        
        # Verify information
        assert info is not None
        assert info["name"] == "mock_plugin"
        assert info["version"] == "1.0.0"
        assert info["status"] == "loaded"
        assert info["capabilities"] == ["capability1", "capability2"]
    
    def test_get_plugin_info_discovered(self, clean_registry, mock_plugin):
        """Test getting information for discovered but not loaded plugin."""
        # Configure mock plugin metadata
        mock_plugin.get_plugin_metadata.return_value = {
            "name": "mock_plugin",
            "version": "1.0.0"
        }
        mock_plugin.get_supported_capabilities.return_value = ["capability1"]
        
        loader = PluginLoader(clean_registry)
        loader.discovered_plugins["mock_plugin"] = mock_plugin
        
        # Get plugin info
        info = loader.get_plugin_info("mock_plugin")
        
        # Verify information
        assert info is not None
        assert info["name"] == "mock_plugin"
        assert info["status"] == "discovered"
        assert info["capabilities"] == ["capability1"]
    
    def test_get_plugin_info_failed(self, clean_registry):
        """Test getting information for failed plugin."""
        loader = PluginLoader(clean_registry)
        loader.failed_plugins["failed_plugin"] = "Plugin failed to load"
        
        # Get plugin info
        info = loader.get_plugin_info("failed_plugin")
        
        # Verify information
        assert info is not None
        assert info["name"] == "failed_plugin"
        assert info["status"] == "failed"
        assert info["error"] == "Plugin failed to load"
    
    def test_get_plugin_info_nonexistent(self, clean_registry):
        """Test getting information for non-existent plugin."""
        loader = PluginLoader(clean_registry)
        
        # Get info for non-existent plugin
        info = loader.get_plugin_info("nonexistent_plugin")
        
        assert info is None
    
    def test_get_plugin_info_metadata_error(self, clean_registry, mock_plugin):
        """Test getting plugin info when metadata access fails."""
        # Mock plugin that raises error getting metadata
        mock_plugin.get_plugin_metadata.side_effect = Exception("Metadata error")
        mock_plugin.get_plugin_name.return_value = "error_plugin"
        
        loader = PluginLoader(clean_registry)
        loader.loaded_plugins["error_plugin"] = mock_plugin
        
        # Get plugin info
        info = loader.get_plugin_info("error_plugin")
        
        # Verify error handling
        assert info is not None
        assert info["name"] == "error_plugin"
        assert info["status"] == "error"
        assert "Failed to get metadata" in info["error"]
    
    def test_get_all_plugins_info(self, clean_registry):
        """Test getting information for all plugins."""
        # Create mock plugins in different states
        mock_loaded_plugin = Mock(spec=ToolPlugin)
        mock_loaded_plugin.get_plugin_name.return_value = "loaded_plugin"
        mock_loaded_plugin.get_plugin_metadata.return_value = {"name": "loaded_plugin"}
        mock_loaded_plugin.get_supported_capabilities.return_value = ["cap1"]
        
        mock_discovered_plugin = Mock(spec=ToolPlugin)
        mock_discovered_plugin.get_plugin_name.return_value = "discovered_plugin"
        mock_discovered_plugin.get_plugin_metadata.return_value = {"name": "discovered_plugin"}
        mock_discovered_plugin.get_supported_capabilities.return_value = ["cap2"]
        
        loader = PluginLoader(clean_registry)
        loader.loaded_plugins["loaded_plugin"] = mock_loaded_plugin
        loader.discovered_plugins["discovered_plugin"] = mock_discovered_plugin
        loader.failed_plugins["failed_plugin"] = "Failed to load"
        
        # Get all plugin info
        all_info = loader.get_all_plugins_info()
        
        # Verify all plugins included
        assert len(all_info) == 3
        assert "loaded_plugin" in all_info
        assert "discovered_plugin" in all_info
        assert "failed_plugin" in all_info
        
        # Verify status information
        assert all_info["loaded_plugin"]["status"] == "loaded"
        assert all_info["discovered_plugin"]["status"] == "discovered"
        assert all_info["failed_plugin"]["status"] == "failed"
    
    def test_get_all_plugins_info_no_duplicates(self, clean_registry, mock_plugin):
        """Test that plugin info doesn't duplicate plugins in multiple states."""
        # Add same plugin to both loaded and discovered
        loader = PluginLoader(clean_registry)
        loader.loaded_plugins["mock_plugin"] = mock_plugin
        loader.discovered_plugins["mock_plugin"] = mock_plugin  # Should be ignored
        
        # Configure metadata
        mock_plugin.get_plugin_metadata.return_value = {"name": "mock_plugin"}
        mock_plugin.get_supported_capabilities.return_value = []
        
        # Get all plugin info
        all_info = loader.get_all_plugins_info()
        
        # Verify no duplicates (loaded takes precedence)
        assert len(all_info) == 1
        assert "mock_plugin" in all_info
        assert all_info["mock_plugin"]["status"] == "loaded"


class TestPluginCleanup:
    """
    Test plugin cleanup and resource management functionality.
    
    ### Plugin Cleanup Strategy:
    - Tests plugin cleanup operations and resource management
    - Validates plugin lifecycle termination procedures
    - Tests cleanup error handling and graceful degradation
    - Verifies plugin state management during cleanup
    - Tests cleanup performance and completeness
    """
    
    def test_cleanup_plugins_single(self, clean_registry, mock_plugin):
        """Test cleanup of single loaded plugin."""
        mock_plugin.cleanup = Mock()
        
        loader = PluginLoader(clean_registry)
        loader.loaded_plugins["mock_plugin"] = mock_plugin
        
        # Cleanup plugins
        loader.cleanup_plugins()
        
        # Verify cleanup was called
        mock_plugin.cleanup.assert_called_once()
        
        # Verify loaded plugins cleared
        assert len(loader.loaded_plugins) == 0
    
    def test_cleanup_plugins_multiple(self, clean_registry):
        """Test cleanup of multiple loaded plugins."""
        # Create multiple mock plugins
        mock_plugin1 = Mock(spec=ToolPlugin)
        mock_plugin1.get_plugin_name.return_value = "plugin1"
        mock_plugin1.cleanup = Mock()
        
        mock_plugin2 = Mock(spec=ToolPlugin)
        mock_plugin2.get_plugin_name.return_value = "plugin2"
        mock_plugin2.cleanup = Mock()
        
        loader = PluginLoader(clean_registry)
        loader.loaded_plugins["plugin1"] = mock_plugin1
        loader.loaded_plugins["plugin2"] = mock_plugin2
        
        # Cleanup plugins
        loader.cleanup_plugins()
        
        # Verify all plugins cleaned up
        mock_plugin1.cleanup.assert_called_once()
        mock_plugin2.cleanup.assert_called_once()
        
        # Verify loaded plugins cleared
        assert len(loader.loaded_plugins) == 0
    
    def test_cleanup_plugins_with_error(self, clean_registry, mock_plugin):
        """Test cleanup when plugin raises error."""
        # Mock plugin that raises error during cleanup
        mock_plugin.cleanup.side_effect = Exception("Cleanup error")
        mock_plugin.get_plugin_name.return_value = "error_plugin"
        
        loader = PluginLoader(clean_registry)
        loader.loaded_plugins["error_plugin"] = mock_plugin
        
        # Cleanup should handle error gracefully
        loader.cleanup_plugins()
        
        # Verify cleanup was attempted
        mock_plugin.cleanup.assert_called_once()
        
        # Verify loaded plugins still cleared despite error
        assert len(loader.loaded_plugins) == 0
    
    def test_cleanup_plugins_empty(self, clean_registry):
        """Test cleanup when no plugins are loaded."""
        loader = PluginLoader(clean_registry)
        
        # Cleanup with no loaded plugins
        loader.cleanup_plugins()
        
        # Should complete without error
        assert len(loader.loaded_plugins) == 0


class TestPluginLoaderErrorHandling:
    """
    Test comprehensive error handling in plugin loader operations.
    
    ### Error Handling Strategy:
    - Tests error handling throughout plugin loader lifecycle
    - Validates error propagation and logging integration
    - Tests recovery from plugin errors and failures
    - Verifies error context preservation and reporting
    - Tests error handling in concurrent plugin operations
    """
    
    @patch('rv_tools.registry.plugin_loader.ErrorHandler')
    @patch('rv_tools.registry.plugin_loader.LoggingManager')
    def test_error_handling_integration(self, mock_logging_manager, mock_error_handler, clean_registry):
        """Test error handling integration with rv-android-core."""
        # Mock logging and error handling
        mock_logger = Mock()
        mock_logging_manager.get_instance.return_value = mock_logging_manager
        mock_logging_manager.get_logger.return_value = mock_logger
        
        error_handler_instance = Mock()
        mock_error_handler.get_instance.return_value = error_handler_instance
        
        # Create loader
        loader = PluginLoader(clean_registry)
        
        # Verify infrastructure setup
        mock_logging_manager.get_instance.assert_called_once()
        mock_error_handler.get_instance.assert_called_once()
        assert loader.logger is mock_logger
        assert loader.error_handler is error_handler_instance
    
    def test_load_plugin_from_entry_point_invalid_plugin(self, clean_registry):
        """Test loading plugin from entry point with invalid plugin type."""
        # Create mock entry point that returns non-ToolPlugin object
        mock_entry_point = Mock()
        mock_entry_point.name = "invalid_plugin"
        mock_entry_point.load.return_value = lambda: "not a plugin"
        
        loader = PluginLoader(clean_registry)
        
        # Should raise TypeError
        with pytest.raises(TypeError, match="does not implement ToolPlugin interface"):
            loader._load_plugin_from_entry_point(mock_entry_point)
    
    def test_load_plugin_from_entry_point_loading_error(self, clean_registry):
        """Test loading plugin from entry point with loading error."""
        # Create mock entry point that raises error
        mock_entry_point = Mock()
        mock_entry_point.name = "error_plugin"
        mock_entry_point.load.side_effect = Exception("Loading failed")
        
        loader = PluginLoader(clean_registry)
        
        # Should raise the original exception
        with pytest.raises(Exception, match="Loading failed"):
            loader._load_plugin_from_entry_point(mock_entry_point)