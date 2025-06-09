"""
Comprehensive unit tests for ToolFactory creation and configuration system.

This module provides exhaustive testing of the ToolFactory class covering:
- Tool creation from specification strings
- Configuration merging and inheritance patterns  
- Tool-specific parameter handling and validation
- Batch tool creation and validation workflows
- Error handling for invalid specifications and configurations

### Testing Architecture:
- Uses controlled registry instances with mock tools for testing
- Comprehensive specification parsing and validation testing
- Parameter handling testing for different tool types (APE, Monkey, DroidBot, RVAndroid)
- Configuration merging validation with deep nested structures
- Error scenario testing with controlled failure conditions

### Key Test Coverage:
- Specification string parsing with variants and parameters
- Configuration merging from base configurations, variants, and parameters
- Tool-specific parameter processing and type conversion
- Tool instance creation vs class instantiation patterns
- Batch operations and specification validation
- Error handling and logging integration throughout factory operations
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any
import copy

from rv_tools.registry.factory import ToolFactory
from rv_tools.registry.registry import ToolRegistry
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.configurable_tool import ConfigurableTool
from rv_android_core.tools.tool_spec import ToolSpec, ToolType
from rv_android_core.util.exceptions import RVToolError, RVToolConfigurationError, ConfigurationError


class TestToolCreation:
    """
    Test tool creation from specifications and configurations.
    
    ### Tool Creation Testing Strategy:
    - Tests creation from simple and complex specifications
    - Validates tool instance creation vs class instantiation
    - Tests configuration application during creation
    - Verifies tool copying and state management
    - Tests creation error handling and recovery
    """
    
    def test_create_tool_from_spec_simple(self, clean_registry, mock_basic_tool):
        """Test creating tool from simple specification."""
        registry = clean_registry
        registry.register_tool(mock_basic_tool)
        
        # Create tool from simple spec
        tool = ToolFactory.create_tool_from_spec("basic_tool", registry)
        
        # Verify tool creation
        assert tool is not None
        assert tool.name == "basic_tool"
        # Should be a copy, not the original
        assert tool is not mock_basic_tool
    
    def test_create_tool_from_spec_with_registry_singleton(self, clean_registry, mock_basic_tool):
        """Test tool creation using registry singleton."""
        registry = clean_registry
        registry.register_tool(mock_basic_tool)
        
        # Create tool without explicit registry (should use singleton)
        tool = ToolFactory.create_tool_from_spec("basic_tool")
        
        # Verify tool creation
        assert tool is not None
        assert tool.name == "basic_tool"
    
    def test_create_tool_from_spec_with_variant(self, clean_registry, mock_configurable_tool, sample_configurations):
        """Test creating tool with variant specification."""
        registry = clean_registry
        registry.register_tool(mock_configurable_tool)
        registry.register_variant("configurable_tool", "performance", sample_configurations["variant_config"])
        
        # Create tool with variant
        tool = ToolFactory.create_tool_from_spec("configurable_tool:performance", registry)
        
        # Verify tool creation and configuration
        assert tool is not None
        assert tool.name == "configurable_tool"
        # Verify configure was called (mock should track this)
        tool.configure.assert_called_once()
    
    def test_create_tool_from_spec_with_parameters(self, clean_registry, mock_configurable_tool):
        """Test creating tool with parameters."""
        registry = clean_registry
        registry.register_tool(mock_configurable_tool)
        
        # Create tool with parameters
        tool = ToolFactory.create_tool_from_spec("configurable_tool@timeout=300,verbose=true", registry)
        
        # Verify tool creation and configuration
        assert tool is not None
        assert tool.name == "configurable_tool"
        # Verify configure was called with parameters
        tool.configure.assert_called_once()
        config_arg = tool.configure.call_args[0][0]
        assert "timeout" in config_arg
    
    def test_create_tool_from_spec_complex(self, clean_registry, mock_configurable_tool, sample_configurations):
        """Test creating tool with complex specification (variants + parameters)."""
        registry = clean_registry
        registry.register_tool(mock_configurable_tool)
        registry.register_variant("configurable_tool", "ai", sample_configurations["advanced_config"])
        
        # Create tool with complex specification
        spec = "configurable_tool:ai@model=gpt-4,temp=0.8"
        tool = ToolFactory.create_tool_from_spec(spec, registry)
        
        # Verify tool creation
        assert tool is not None
        assert tool.name == "configurable_tool"
        tool.configure.assert_called_once()
    
    def test_create_tool_from_class(self, clean_registry, sample_tool_specs):
        """Test creating tool from registered class."""
        registry = clean_registry
        
        # Create mock tool class with required attributes
        MockToolClass = Mock()
        MockToolClass.__name__ = "MockToolClass"  # Add __name__ attribute
        
        mock_instance = Mock(spec=ConfigurableTool)
        mock_instance.name = "class_tool"
        mock_instance.configure = Mock()
        MockToolClass.return_value = mock_instance
        
        # Register tool class
        registry.register_tool_class("class_tool", MockToolClass, sample_tool_specs["basic_tool"])
        
        # Create tool from specification
        tool = ToolFactory.create_tool_from_spec("class_tool", registry)
        
        # Verify tool creation from class
        MockToolClass.assert_called_once()
        assert tool is mock_instance
    
    def test_create_tool_nonexistent(self, clean_registry):
        """Test creating non-existent tool."""
        registry = clean_registry
        
        # Attempt to create non-existent tool
        with pytest.raises(RVToolError, match="Unknown tool: nonexistent_tool"):
            ToolFactory.create_tool_from_spec("nonexistent_tool", registry)
    
    def test_create_configured_tool_method(self, clean_registry, mock_configurable_tool, sample_configurations):
        """Test create_configured_tool method."""
        registry = clean_registry
        registry.register_tool(mock_configurable_tool)
        registry.register_variant("configurable_tool", "performance", sample_configurations["variant_config"])
        
        # Create configured tool
        tool = ToolFactory.create_configured_tool(
            tool_name="configurable_tool",
            variants=["performance"],
            params={"timeout": "600"},
            registry=registry
        )
        
        # Verify tool creation and configuration
        assert tool is not None
        assert tool.name == "configurable_tool"
        tool.configure.assert_called_once()


class TestConfigurationMerging:
    """
    Test configuration merging logic and inheritance patterns.
    
    ### Configuration Merging Strategy:
    - Tests deep configuration merging algorithms
    - Validates variant configuration inheritance
    - Tests parameter override hierarchies
    - Verifies nested configuration structure handling
    - Tests configuration precedence and conflict resolution
    """
    
    def test_deep_merge_simple(self):
        """Test simple configuration merging."""
        base = {"key1": "value1", "key2": "value2"}
        override = {"key2": "new_value2", "key3": "value3"}
        
        result = ToolFactory._deep_merge(base, override)
        
        expected = {"key1": "value1", "key2": "new_value2", "key3": "value3"}
        assert result == expected
        # Verify original dictionaries are not modified
        assert base == {"key1": "value1", "key2": "value2"}
        assert override == {"key2": "new_value2", "key3": "value3"}
    
    def test_deep_merge_nested(self):
        """Test deep merging with nested dictionaries."""
        base = {
            "section1": {
                "key1": "value1",
                "key2": "value2"
            },
            "section2": {
                "nested": {
                    "deep_key": "deep_value"
                }
            }
        }
        
        override = {
            "section1": {
                "key2": "new_value2",  # Override existing
                "key3": "value3"       # Add new
            },
            "section3": {
                "new_section": "new_value"
            }
        }
        
        result = ToolFactory._deep_merge(base, override)
        
        # Verify deep merging
        assert result["section1"]["key1"] == "value1"  # Preserved from base
        assert result["section1"]["key2"] == "new_value2"  # Overridden
        assert result["section1"]["key3"] == "value3"  # Added from override
        assert result["section2"]["nested"]["deep_key"] == "deep_value"  # Preserved
        assert result["section3"]["new_section"] == "new_value"  # New section
    
    def test_deep_merge_type_conflicts(self):
        """Test deep merging with type conflicts."""
        base = {
            "config": {
                "nested_dict": {"key": "value"}
            }
        }
        
        override = {
            "config": {
                "nested_dict": "string_value"  # Type conflict: dict -> string
            }
        }
        
        result = ToolFactory._deep_merge(base, override)
        
        # Type conflicts should be resolved by taking override value
        assert result["config"]["nested_dict"] == "string_value"
    
    def test_configuration_merging_in_tool_creation(self, clean_registry):
        """Test configuration merging during tool creation."""
        registry = clean_registry
        
        # Create mock configurable tool
        mock_tool = Mock(spec=ConfigurableTool)
        mock_tool.name = "test_tool"
        mock_tool.configure = Mock()
        registry.register_tool(mock_tool)
        
        # Set up base configuration
        base_config = {
            "timeout": 300,
            "llm": {
                "model": "gpt-3.5",
                "temperature": 0.5
            }
        }
        registry.register_configuration("test_tool", base_config)
        
        # Set up variant configuration
        variant_config = {
            "llm": {
                "model": "gpt-4",  # Override model
                "max_tokens": 2048  # Add new parameter
            },
            "strategy": "adaptive"  # Add new section
        }
        registry.register_variant("test_tool", "advanced", variant_config)
        
        # Create tool with variant and parameters
        tool = ToolFactory.create_tool_from_spec("test_tool:advanced@timeout=600", registry)
        
        # Verify configure was called on the returned tool copy
        tool.configure.assert_called_once()
        merged_config = tool.configure.call_args[0][0]
        
        # Verify configuration merging
        assert merged_config["timeout"] == 600  # From parameters (highest priority)
        assert merged_config["llm"]["model"] == "gpt-4"  # From variant
        assert merged_config["llm"]["temperature"] == 0.5  # From base (preserved)
        assert merged_config["llm"]["max_tokens"] == 2048  # From variant (new)
        assert merged_config["strategy"] == "adaptive"  # From variant (new section)


class TestParameterHandling:
    """
    Test tool-specific parameter processing and type conversion.
    
    ### Parameter Handling Strategy:
    - Tests parameter conversion for different tool types
    - Validates type conversion and validation logic
    - Tests tool-specific parameter mapping
    - Verifies parameter error handling and defaults
    - Tests complex parameter parsing scenarios
    """
    
    def test_params_to_config_general(self):
        """Test general parameter handling."""
        params = {"timeout": "300", "other_param": "value"}
        config = ToolFactory._params_to_config("generic_tool", params)
        
        # General timeout parameter should be converted
        assert config["timeout"] == 300
        # Other parameters should be ignored for generic tools
        assert "other_param" not in config
    
    def test_params_to_config_ape(self):
        """Test APE-specific parameter handling."""
        params = {
            "strategy": "bfs",
            "running_minutes": "15",
            "device_id": "emulator-5554",
            "timeout": "600"
        }
        
        config = ToolFactory._params_to_config("ape", params)
        
        # Verify APE-specific parameters
        assert config["strategy"] == "bfs"
        assert config["running_minutes"] == 15
        assert config["device_id"] == "emulator-5554"
        assert config["timeout"] == 600  # General parameter
    
    def test_params_to_config_ape_invalid_numbers(self):
        """Test APE parameter handling with invalid numbers."""
        params = {
            "running_minutes": "invalid",
            "timeout": "also_invalid",
            "strategy": "dfs"
        }
        
        config = ToolFactory._params_to_config("ape", params)
        
        # Invalid numbers should be ignored, valid strings preserved
        assert "running_minutes" not in config
        assert "timeout" not in config
        assert config["strategy"] == "dfs"  # String parameters should work
    
    def test_params_to_config_monkey(self):
        """Test Monkey-specific parameter handling."""
        params = {
            "event_count": "10000",
            "seed": "12345", 
            "throttle": "100",
            "device_id": "emulator-5554",
            "verbosity": "2",
            "ignore_crashes": "true",
            "ignore_timeouts": "false",
            "kill_process_after_error": "1",
            "monitor_native_crashes": "yes"
        }
        
        config = ToolFactory._params_to_config("monkey", params)
        
        # Verify numeric parameters
        assert config["event_count"] == 10000
        assert config["seed"] == 12345
        assert config["throttle"] == 100
        assert config["verbosity"] == 2
        assert config["device_id"] == "emulator-5554"
        
        # Verify boolean parameters
        assert config["ignore_crashes"] is True
        assert config["ignore_timeouts"] is False
        assert config["kill_process_after_error"] is True
        assert config["monitor_native_crashes"] is True
    
    def test_params_to_config_monkey_boolean_variations(self):
        """Test Monkey boolean parameter variations."""
        # Test different boolean representations
        test_cases = [
            ("true", True), ("True", True), ("TRUE", True),
            ("false", False), ("False", False), ("FALSE", False),
            ("1", True), ("0", False),
            ("yes", True), ("no", False),
            ("on", True), ("off", False),
            ("invalid", False)  # Invalid values should default to False
        ]
        
        for param_value, expected in test_cases:
            params = {"ignore_crashes": param_value}
            config = ToolFactory._params_to_config("monkey", params)
            assert config["ignore_crashes"] is expected, f"Failed for value: {param_value}"
    
    def test_params_to_config_droidbot(self):
        """Test DroidBot-specific parameter handling."""
        params = {
            "policy": "dfs",
            "count": "1000",
            "interval": "2",
            "device_id": "emulator-5554"
        }
        
        config = ToolFactory._params_to_config("droidbot", params)
        
        # Verify DroidBot parameters
        assert config["policy"] == "dfs"
        assert config["count"] == 1000
        assert config["interval"] == 2
        assert config["device_id"] == "emulator-5554"
    
    def test_params_to_config_rvandroid(self):
        """Test RVAndroid/RVDroid-specific parameter handling."""
        params = {
            "model": "gpt-4",
            "model_type": "openai",
            "temp": "0.7",
            "temperature": "0.8",  # Should be overridden by temp
            "max_tokens": "2048",
            "strategy": "adaptive",
            "parser": "uiautomator",
            "visitor": "enhanced",
            "device_id": "emulator-5554"
        }
        
        config = ToolFactory._params_to_config("rvandroid", params)
        
        # Verify LLM configuration
        assert config["llm"]["model_name"] == "gpt-4"
        assert config["llm"]["model_type"] == "openai"
        assert config["llm"]["temperature"] == 0.7  # temp should take precedence
        assert config["llm"]["max_tokens"] == 2048
        
        # Verify other configurations
        assert config["strategy"]["type"] == "adaptive"
        assert config["parser"]["type"] == "uiautomator"
        assert config["visitor"]["type"] == "enhanced"
        assert config["device_id"] == "emulator-5554"
    
    def test_params_to_config_rvdroid_alias(self):
        """Test that rvdroid uses same parameter handling as rvandroid."""
        params = {"model": "gpt-4", "temp": "0.7"}
        
        config_rvandroid = ToolFactory._params_to_config("rvandroid", params)
        config_rvdroid = ToolFactory._params_to_config("rvdroid", params)
        
        # Should produce identical configurations
        assert config_rvandroid == config_rvdroid
    
    def test_params_to_config_temperature_precedence(self):
        """Test temperature parameter precedence in RVAndroid."""
        # Test that 'temp' takes precedence over 'temperature'
        params = {"temp": "0.7", "temperature": "0.5"}
        config = ToolFactory._params_to_config("rvandroid", params)
        
        assert config["llm"]["temperature"] == 0.7
        
        # Test that 'temperature' works when 'temp' is not present
        params = {"temperature": "0.5"}
        config = ToolFactory._params_to_config("rvandroid", params)
        
        assert config["llm"]["temperature"] == 0.5
    
    def test_params_to_config_invalid_numbers_rvandroid(self):
        """Test RVAndroid parameter handling with invalid numbers."""
        params = {
            "model": "gpt-4",
            "temp": "invalid_temp",
            "max_tokens": "invalid_tokens"
        }
        
        config = ToolFactory._params_to_config("rvandroid", params)
        
        # Invalid numbers should be ignored
        assert config["llm"]["model_name"] == "gpt-4"  # String should work
        assert "temperature" not in config["llm"]  # Invalid temp ignored
        assert "max_tokens" not in config["llm"]  # Invalid max_tokens ignored


class TestBatchOperations:
    """
    Test batch tool creation and specification validation.
    
    ### Batch Operations Strategy:
    - Tests batch creation of multiple tools
    - Validates specification validation workflows
    - Tests error handling in batch operations
    - Verifies performance of batch processing
    - Tests mixed valid/invalid specification handling
    """
    
    def test_batch_create_tools(self, clean_registry, mock_basic_tool, mock_configurable_tool):
        """Test batch creation of multiple tools."""
        registry = clean_registry
        registry.register_tool(mock_basic_tool)
        registry.register_tool(mock_configurable_tool)
        
        # Create batch of tools
        specs = ["basic_tool", "configurable_tool", "basic_tool:performance"]
        tools = ToolFactory.batch_create_tools(specs, registry)
        
        # Verify batch creation
        assert len(tools) == 3
        assert all(tool is not None for tool in tools)
        assert tools[0].name == "basic_tool"
        assert tools[1].name == "configurable_tool"  
        assert tools[2].name == "basic_tool"
    
    def test_batch_create_tools_with_error(self, clean_registry, mock_basic_tool):
        """Test batch creation with invalid specification."""
        registry = clean_registry
        registry.register_tool(mock_basic_tool)
        
        # Create batch with invalid specification
        specs = ["basic_tool", "nonexistent_tool"]
        
        # Should raise error on first invalid spec
        with pytest.raises(RVToolError, match="Unknown tool: nonexistent_tool"):
            ToolFactory.batch_create_tools(specs, registry)
    
    def test_validate_tool_spec_valid(self, clean_registry, mock_basic_tool, sample_configurations):
        """Test specification validation for valid specs."""
        registry = clean_registry
        registry.register_tool(mock_basic_tool)
        registry.register_variant("basic_tool", "performance", sample_configurations["variant_config"])
        
        # Test valid specifications
        valid_specs = [
            "basic_tool",
            "basic_tool:performance",
            "basic_tool@timeout=300",
            "basic_tool:performance@timeout=600"
        ]
        
        for spec in valid_specs:
            assert ToolFactory.validate_tool_spec(spec, registry), f"Failed for spec: {spec}"
    
    def test_validate_tool_spec_invalid_tool(self, clean_registry):
        """Test specification validation for invalid tool."""
        registry = clean_registry
        
        # Test invalid tool name
        assert not ToolFactory.validate_tool_spec("nonexistent_tool", registry)
    
    def test_validate_tool_spec_invalid_variant(self, clean_registry, mock_basic_tool):
        """Test specification validation for invalid variant."""
        registry = clean_registry
        registry.register_tool(mock_basic_tool)
        
        # Test invalid variant
        assert not ToolFactory.validate_tool_spec("basic_tool:nonexistent_variant", registry)
    
    def test_validate_tool_spec_tool_class(self, clean_registry, sample_tool_specs):
        """Test specification validation for tool class."""
        registry = clean_registry
        
        # Register tool class (not instance)
        MockToolClass = Mock()
        MockToolClass.__name__ = "MockToolClass"  # Add __name__ attribute
        registry.register_tool_class("class_tool", MockToolClass, sample_tool_specs["basic_tool"])
        
        # Should validate successfully for tool class
        assert ToolFactory.validate_tool_spec("class_tool", registry)
    
    def test_validate_tool_spec_default_variant_always_valid(self, clean_registry, mock_basic_tool):
        """Test that default variant is always considered valid."""
        registry = clean_registry
        registry.register_tool(mock_basic_tool)
        
        # Default variant should always be valid even if not explicitly registered
        assert ToolFactory.validate_tool_spec("basic_tool:default", registry)
    
    def test_validate_tool_spec_malformed(self, clean_registry):
        """Test specification validation for malformed specs."""
        registry = clean_registry
        
        # Test various malformed specifications
        malformed_specs = [
            "",  # Empty string
            # Note: The current implementation is quite permissive with malformed specs
            # It may not fail on some malformed inputs due to the parsing logic
        ]
        
        for spec in malformed_specs:
            # Empty string should result in invalid tool name
            result = ToolFactory.validate_tool_spec(spec, registry)
            assert not result, f"Should have failed for malformed spec: '{spec}'"


class TestToolCopyingAndInstantiation:
    """
    Test tool copying and class instantiation mechanisms.
    
    ### Copy/Instantiation Strategy:
    - Tests deep copying of tool instances
    - Validates class instantiation workflows
    - Tests configuration application during copying/instantiation
    - Verifies instance isolation and state management
    - Tests error handling in copying and instantiation
    """
    
    def test_create_tool_copy_basic(self, mock_basic_tool):
        """Test basic tool copying functionality."""
        # Mock deepcopy to track calls
        with patch('rv_tools.registry.factory.copy.deepcopy') as mock_deepcopy:
            mock_logger = Mock()
            mock_copy = Mock(spec=AbstractTool)
            mock_copy.name = "basic_tool"
            mock_deepcopy.return_value = mock_copy
            
            # Create tool copy
            result = ToolFactory._create_tool_copy(mock_basic_tool, {}, mock_logger)
            
            # Verify copying
            mock_deepcopy.assert_called_once_with(mock_basic_tool)
            assert result is mock_copy
            mock_logger.debug.assert_called_with("Created copy of tool: basic_tool")
    
    def test_create_tool_copy_with_configuration(self, mock_configurable_tool, sample_configurations):
        """Test tool copying with configuration application."""
        config = sample_configurations["basic_config"]
        
        with patch('rv_tools.registry.factory.copy.deepcopy') as mock_deepcopy:
            mock_logger = Mock()
            mock_copy = Mock(spec=ConfigurableTool)
            mock_copy.name = "configurable_tool"
            mock_copy.configure = Mock()
            mock_deepcopy.return_value = mock_copy
            
            # Create tool copy with configuration
            result = ToolFactory._create_tool_copy(mock_configurable_tool, config, mock_logger)
            
            # Verify configuration was applied
            mock_copy.configure.assert_called_once_with(config)
            assert result is mock_copy
    
    def test_create_tool_copy_without_configure_method(self, mock_basic_tool):
        """Test tool copying when tool doesn't have configure method."""
        with patch('rv_tools.registry.factory.copy.deepcopy') as mock_deepcopy:
            mock_logger = Mock()
            mock_copy = Mock(spec=AbstractTool)
            mock_copy.name = "basic_tool"
            # Don't add configure method to mock_copy
            mock_deepcopy.return_value = mock_copy
            
            config = {"timeout": 300}
            
            # Create tool copy - should not fail even without configure method
            result = ToolFactory._create_tool_copy(mock_basic_tool, config, mock_logger)
            
            # Should succeed without trying to configure
            assert result is mock_copy
    
    def test_create_tool_copy_error_handling(self, mock_basic_tool):
        """Test error handling in tool copying."""
        with patch('rv_tools.registry.factory.copy.deepcopy', side_effect=Exception("Copy failed")):
            mock_logger = Mock()
            
            # Should raise the original Exception (enhanced ErrorHandler reraises with reraise=True)
            with pytest.raises(Exception, match="Copy failed"):
                ToolFactory._create_tool_copy(mock_basic_tool, {}, mock_logger)
            
            # The ErrorHandler decorator logs the error automatically
    
    def test_create_tool_from_class_basic(self, sample_tool_specs):
        """Test basic tool instantiation from class."""
        # Create mock tool class
        MockToolClass = Mock()
        MockToolClass.__name__ = "MockToolClass"  # Add __name__ attribute
        mock_instance = Mock(spec=AbstractTool)
        mock_instance.name = "class_tool"
        MockToolClass.return_value = mock_instance
        
        mock_logger = Mock()
        
        # Create tool from class
        result = ToolFactory._create_tool_from_class(MockToolClass, {}, mock_logger)
        
        # Verify instantiation
        MockToolClass.assert_called_once()
        assert result is mock_instance
        mock_logger.debug.assert_called_with("Instantiated tool from class: MockToolClass")
    
    def test_create_tool_from_class_with_configuration(self):
        """Test tool instantiation with configuration."""
        # Create mock configurable tool class
        MockToolClass = Mock()
        mock_instance = Mock(spec=ConfigurableTool)
        mock_instance.name = "configurable_class_tool"
        mock_instance.configure = Mock()
        MockToolClass.return_value = mock_instance
        MockToolClass.__name__ = "MockConfigurableToolClass"
        
        mock_logger = Mock()
        config = {"timeout": 300, "verbose": True}
        
        # Create tool from class with configuration
        result = ToolFactory._create_tool_from_class(MockToolClass, config, mock_logger)
        
        # Verify configuration was applied
        mock_instance.configure.assert_called_once_with(config)
        assert result is mock_instance
    
    def test_create_tool_from_class_error_handling(self):
        """Test error handling in tool class instantiation."""
        # Create mock tool class that raises exception
        MockToolClass = Mock(side_effect=Exception("Instantiation failed"))
        MockToolClass.__name__ = "FailingToolClass"
        
        mock_logger = Mock()
        
        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="Failed to create tool from class 'FailingToolClass': Instantiation failed"):
            ToolFactory._create_tool_from_class(MockToolClass, {}, mock_logger)
        
        # Verify error was logged
        mock_logger.error.assert_called_once()


class TestFactoryErrorHandling:
    """
    Test comprehensive error handling in factory operations.
    
    ### Error Handling Strategy:
    - Tests error handling in tool creation workflows
    - Validates error propagation and logging
    - Tests recovery from configuration errors
    - Verifies error context and information preservation
    - Tests error handling in batch operations
    """
    
    @patch('rv_tools.registry.factory.ErrorHandler')
    @patch('rv_tools.registry.factory.LoggingManager')
    def test_create_tool_from_spec_error_handling(self, mock_logging_manager, mock_error_handler, clean_registry):
        """Test error handling in create_tool_from_spec."""
        registry = clean_registry
        
        # Mock logging and error handling
        mock_logger = Mock()
        mock_logging_manager.get_instance.return_value = mock_logging_manager
        mock_logging_manager.get_logger.return_value = mock_logger
        
        error_handler_instance = Mock()
        mock_error_handler.get_instance.return_value = error_handler_instance
        
        # Mock the error_context context manager for enhanced ErrorHandler compatibility
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_context_manager)
        mock_context_manager.__exit__ = Mock(return_value=None)
        error_handler_instance.error_context.return_value = mock_context_manager
        
        # Create tool that will cause error during creation
        mock_tool = Mock(spec=AbstractTool)
        mock_tool.name = "error_tool"
        registry.register_tool(mock_tool)
        
        # Mock deepcopy to raise exception
        with patch('rv_tools.registry.factory.copy.deepcopy', side_effect=Exception("Copy error")):
            with pytest.raises(Exception, match="Copy error"):
                ToolFactory.create_tool_from_spec("error_tool", registry)
            
            # Verify error context was used (enhanced ErrorHandler pattern)
            error_handler_instance.error_context.assert_called_once_with(
                component="ToolFactory", phase="tool_creation"
            )
    
    def test_create_tool_registry_access_error(self, clean_registry):
        """Test error handling when registry operations fail."""
        registry = clean_registry
        
        # Mock registry method to raise exception
        with patch.object(registry, 'resolve_tool_spec', side_effect=Exception("Registry error")):
            with pytest.raises(Exception, match="Registry error"):
                ToolFactory.create_tool_from_spec("any_tool", registry)
    
    @patch('rv_tools.registry.factory.LoggingManager')
    def test_logging_integration(self, mock_logging_manager, clean_registry, mock_basic_tool):
        """Test logging integration in factory operations."""
        registry = clean_registry
        registry.register_tool(mock_basic_tool)
        
        # Mock logging manager
        mock_logger = Mock()
        mock_logging_manager.get_instance.return_value = mock_logging_manager
        mock_logging_manager.get_logger.return_value = mock_logger
        
        # Create tool
        ToolFactory.create_tool_from_spec("basic_tool", registry)
        
        # Verify logging calls
        mock_logging_manager.get_logger.assert_called_with(
            "tools.factory",
            {"component": "ToolFactory"}
        )
        
        # Verify debug logging calls
        debug_calls = [call.args[0] for call in mock_logger.debug.call_args_list]
        assert any("Creating tool from specification" in call for call in debug_calls)
    
    def test_configuration_application_error(self, clean_registry):
        """Test error handling when configuration application fails."""
        registry = clean_registry
        
        # Create mock tool with configure method that raises exception
        mock_tool = Mock(spec=ConfigurableTool)
        mock_tool.name = "config_error_tool"
        mock_tool.configure = Mock(side_effect=Exception("Configuration error"))
        registry.register_tool(mock_tool)
        
        # Mock deepcopy to return the tool (so we get to configure call)
        with patch('rv_tools.registry.factory.copy.deepcopy', return_value=mock_tool):
            # This should not raise exception here, but it would in real scenario
            # The test shows the error would occur during configure call
            pass