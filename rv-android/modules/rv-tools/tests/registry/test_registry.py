"""
Comprehensive unit tests for ToolRegistry singleton and tool management.

This module provides exhaustive testing of the ToolRegistry class covering:
- Singleton pattern implementation and thread safety
- Tool registration workflows (instances and classes)
- Configuration and variant management systems
- Tool discovery and capability-based filtering
- Registry information and metadata access
- Error handling and logging integration

### Testing Architecture:
- Uses isolated registry instances for test independence
- Mocks rv-android-core components for unit test isolation
- Comprehensive error scenario and edge case coverage
- Thread safety validation through concurrent access testing
- Performance validation for registry operations at scale

### Key Test Coverage:
- Registry singleton behavior and thread safety guarantees
- Tool registration validation and conflict handling
- Configuration merging and variant inheritance patterns
- Capability indexing and filtering efficiency
- Tool specification parsing and validation logic
- Registry state management and cleanup operations
"""

import pytest
import threading
import time
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from typing import Dict, List, Any

from rv_tools.registry.registry import ToolRegistry
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.configurable_tool import ConfigurableTool
from rv_android_core.tools.tool_spec import ToolSpec, ToolType


class TestToolRegistrySingleton:
    """
    Test ToolRegistry singleton pattern implementation and thread safety.
    
    ### Architectural Testing Focus:
    - Validates singleton pattern implementation correctness
    - Ensures thread safety through concurrent access testing
    - Verifies instance consistency across multiple access patterns
    - Tests singleton reset functionality for testing scenarios
    - Validates proper initialization and state management
    """
    
    def test_singleton_instance_consistency(self, clean_registry):
        """Test that get_instance() returns the same instance consistently."""
        # Get multiple instances
        instance1 = ToolRegistry.get_instance()
        instance2 = ToolRegistry.get_instance()
        instance3 = ToolRegistry.get_instance()
        
        # Verify all instances are the same object
        assert instance1 is instance2
        assert instance2 is instance3
        assert id(instance1) == id(instance2) == id(instance3)
    
    def test_singleton_thread_safety(self, threading_test_helper):
        """Test singleton thread safety under concurrent access."""
        # Reset registry before test
        ToolRegistry.reset_instance()
        
        # Run concurrent access test
        results, exceptions = threading_test_helper["run_concurrent"](
            threading_test_helper["simulate_registry_access"],
            num_threads=20,
            iterations=50
        )
        
        # Verify no exceptions occurred
        assert len(exceptions) == 0, f"Exceptions during concurrent access: {exceptions}"
        
        # Verify all instances have the same ID (same object)
        unique_ids = set(results)
        assert len(unique_ids) == 1, f"Multiple singleton instances created: {unique_ids}"
    
    def test_singleton_reset_functionality(self):
        """Test registry reset functionality for testing scenarios."""
        # Get initial instance
        instance1 = ToolRegistry.get_instance()
        initial_id = id(instance1)
        
        # Register a tool to modify state
        mock_tool = Mock(spec=AbstractTool)
        mock_tool.name = "test_tool"
        instance1.register_tool(mock_tool)
        
        # Verify tool is registered
        assert instance1.has_tool("test_tool")
        
        # Reset the instance
        ToolRegistry.reset_instance()
        
        # Get new instance after reset
        instance2 = ToolRegistry.get_instance()
        new_id = id(instance2)
        
        # Verify new instance is different and clean
        assert initial_id != new_id
        assert not instance2.has_tool("test_tool")
        assert len(instance2.get_tool_names()) == 0
    
    @patch('rv_tools.registry.registry.LoggingManager')
    @patch('rv_tools.registry.registry.ErrorHandler')
    def test_singleton_initialization(self, mock_error_handler, mock_logging_manager):
        """Test proper initialization of singleton instance."""
        # Reset to ensure clean initialization
        ToolRegistry.reset_instance()
        
        # Mock the infrastructure components
        mock_logging_manager.get_instance.return_value = mock_logging_manager
        mock_logger = Mock()
        mock_logging_manager.get_logger.return_value = mock_logger
        mock_error_handler.get_instance.return_value = mock_error_handler
        
        # Get instance to trigger initialization
        registry = ToolRegistry.get_instance()
        
        # Verify initialization calls
        mock_logging_manager.get_instance.assert_called_once()
        mock_logging_manager.get_logger.assert_called_once()
        mock_error_handler.get_instance.assert_called_once()
        mock_logger.info.assert_called_with("Tool registry initialized")
        
        # Verify instance state
        assert isinstance(registry.tools, dict)
        assert isinstance(registry.tool_classes, dict)
        assert isinstance(registry.tool_specs, dict)
        assert isinstance(registry.configurations, dict)
        assert isinstance(registry.variants, dict)
        assert isinstance(registry.capability_index, dict)


class TestToolRegistration:
    """
    Test tool registration workflows and validation.
    
    ### Registration Testing Strategy:
    - Validates tool instance and class registration patterns
    - Tests tool specification integration and metadata handling
    - Verifies configuration and variant initialization
    - Tests registration conflict handling and overwriting behavior
    - Validates capability indexing during registration
    """
    
    def test_register_tool_instance_basic(self, clean_registry, mock_basic_tool):
        """Test basic tool instance registration."""
        registry = clean_registry
        
        # Register the tool
        registry.register_tool(mock_basic_tool, mock_basic_tool.TOOL_SPEC)
        
        # Verify registration
        assert registry.has_tool("basic_tool")
        retrieved_tool = registry.get_tool("basic_tool")
        assert retrieved_tool is mock_basic_tool
        
        # Verify tool names
        tool_names = registry.get_tool_names()
        assert "basic_tool" in tool_names
        
        # Verify tool specification
        tool_spec = registry.get_tool_spec("basic_tool")
        assert tool_spec is mock_basic_tool.TOOL_SPEC
    
    def test_register_tool_without_spec(self, clean_registry, mock_basic_tool):
        """Test tool registration without specification."""
        registry = clean_registry
        
        # Register tool without specification
        registry.register_tool(mock_basic_tool)
        
        # Verify tool is registered
        assert registry.has_tool("basic_tool")
        retrieved_tool = registry.get_tool("basic_tool")
        assert retrieved_tool is mock_basic_tool
        
        # Verify no specification is stored
        tool_spec = registry.get_tool_spec("basic_tool")
        assert tool_spec is None
    
    def test_register_tool_class(self, clean_registry, sample_tool_specs):
        """Test tool class registration."""
        registry = clean_registry
        tool_spec = sample_tool_specs["basic_tool"]
        
        # Create mock tool class
        MockToolClass = Mock()
        MockToolClass.__name__ = "MockBasicTool"
        
        # Register tool class
        registry.register_tool_class("basic_tool", MockToolClass, tool_spec)
        
        # Verify class registration
        retrieved_class = registry.get_tool_class("basic_tool")
        assert retrieved_class is MockToolClass
        
        # Verify tool specification
        retrieved_spec = registry.get_tool_spec("basic_tool")
        assert retrieved_spec is tool_spec
        
        # Verify tool is not in instance registry
        assert not registry.has_tool("basic_tool")
        assert registry.get_tool("basic_tool") is None
    
    def test_register_tool_overwrite_warning(self, clean_registry, mock_basic_tool):
        """Test tool registration overwrite behavior and warning."""
        registry = clean_registry
        
        # Register tool first time
        registry.register_tool(mock_basic_tool, mock_basic_tool.TOOL_SPEC)
        
        # Create different tool with same name
        mock_tool_2 = Mock(spec=AbstractTool)
        mock_tool_2.name = "basic_tool"
        
        # Register tool with same name (should overwrite)
        with patch.object(registry, 'logger') as mock_logger:
            registry.register_tool(mock_tool_2)
            
            # Verify warning was logged
            mock_logger.warning.assert_called_with(
                "Tool 'basic_tool' already registered, replacing existing instance"
            )
        
        # Verify tool was overwritten
        retrieved_tool = registry.get_tool("basic_tool")
        assert retrieved_tool is mock_tool_2
        assert retrieved_tool is not mock_basic_tool
    
    def test_register_tool_configuration_initialization(self, clean_registry, mock_basic_tool):
        """Test configuration and variant initialization during registration."""
        registry = clean_registry
        
        # Register tool
        registry.register_tool(mock_basic_tool, mock_basic_tool.TOOL_SPEC)
        
        # Verify configuration initialization
        assert "basic_tool" in registry.configurations
        assert isinstance(registry.configurations["basic_tool"], dict)
        
        # Verify variant initialization (empty, no default variant auto-created)
        assert "basic_tool" in registry.variants
        assert isinstance(registry.variants["basic_tool"], dict)
        assert len(registry.variants["basic_tool"]) == 0  # No variants by default
    
    def test_register_tool_capability_indexing(self, clean_registry, sample_tool_specs):
        """Test capability indexing during tool registration."""
        registry = clean_registry
        tool_spec = sample_tool_specs["advanced_tool"]
        
        mock_tool = Mock(spec=AbstractTool)
        mock_tool.name = "advanced_tool"
        
        # Register tool with capabilities
        registry.register_tool(mock_tool, tool_spec)
        
        # Verify capability indexing
        capabilities = tool_spec.capabilities
        for capability in capabilities:
            assert capability in registry.capability_index
            assert "advanced_tool" in registry.capability_index[capability]
        
        # Test capability-based tool retrieval
        ai_tools = registry.get_tools_by_capability("ai_guidance")
        assert len(ai_tools) == 1
        assert ai_tools[0] is mock_tool
    
    def test_register_tool_error_handling(self, clean_registry):
        """Test error handling during tool registration.""" 
        registry = clean_registry
        
        # Create a tool that raises exception when name is accessed
        class BadTool:
            @property
            def name(self):
                raise Exception("Test error")
        
        mock_tool = BadTool()
        
        # Mock the error handler that's already in the registry
        mock_error_handler = Mock()
        registry.error_handler = mock_error_handler
        
        # Attempt registration - should call error handler AND raise exception
        with pytest.raises(Exception, match="Test error"):
            registry.register_tool(mock_tool)
        
        # Verify error handler was called
        mock_error_handler.handle_error.assert_called_once()
        
        # Verify the exception was captured in error handler arguments
        call_args = mock_error_handler.handle_error.call_args
        assert call_args is not None
        error_arg = call_args[0][0]  # First positional argument should be the exception
        assert isinstance(error_arg, Exception)
        assert "Test error" in str(error_arg)


class TestToolRetrieval:
    """
    Test tool discovery and retrieval functionality.
    
    ### Retrieval Testing Strategy:
    - Tests individual tool retrieval by name
    - Validates bulk tool retrieval operations
    - Tests capability-based filtering and discovery
    - Verifies tool specification and metadata access
    - Tests tool existence checking and validation
    """
    
    def test_get_tool_existing(self, clean_registry, mock_basic_tool):
        """Test retrieval of existing tool."""
        registry = clean_registry
        registry.register_tool(mock_basic_tool)
        
        # Retrieve tool
        retrieved_tool = registry.get_tool("basic_tool")
        assert retrieved_tool is mock_basic_tool
    
    def test_get_tool_nonexistent(self, clean_registry):
        """Test retrieval of non-existent tool."""
        registry = clean_registry
        
        # Attempt to retrieve non-existent tool
        retrieved_tool = registry.get_tool("nonexistent_tool")
        assert retrieved_tool is None
    
    def test_get_tools_multiple(self, clean_registry, mock_basic_tool, mock_configurable_tool):
        """Test retrieval of multiple tools by name."""
        registry = clean_registry
        
        # Register multiple tools
        registry.register_tool(mock_basic_tool)
        registry.register_tool(mock_configurable_tool)
        
        # Retrieve multiple tools
        tool_names = ["basic_tool", "configurable_tool", "nonexistent_tool"]
        retrieved_tools = registry.get_tools(tool_names)
        
        # Verify results (should skip nonexistent tool)
        assert len(retrieved_tools) == 2
        assert mock_basic_tool in retrieved_tools
        assert mock_configurable_tool in retrieved_tools
    
    def test_get_all_tools(self, clean_registry, mock_basic_tool, mock_configurable_tool):
        """Test retrieval of all registered tools."""
        registry = clean_registry
        
        # Initially no tools
        all_tools = registry.get_all_tools()
        assert len(all_tools) == 0
        
        # Register tools
        registry.register_tool(mock_basic_tool)
        registry.register_tool(mock_configurable_tool)
        
        # Retrieve all tools
        all_tools = registry.get_all_tools()
        assert len(all_tools) == 2
        assert mock_basic_tool in all_tools
        assert mock_configurable_tool in all_tools
    
    def test_get_tool_names(self, clean_registry, mock_basic_tool, mock_configurable_tool):
        """Test retrieval of tool names."""
        registry = clean_registry
        
        # Initially no tool names
        tool_names = registry.get_tool_names()
        assert len(tool_names) == 0
        
        # Register tools
        registry.register_tool(mock_basic_tool)
        registry.register_tool(mock_configurable_tool)
        
        # Retrieve tool names
        tool_names = registry.get_tool_names()
        assert len(tool_names) == 2
        assert "basic_tool" in tool_names
        assert "configurable_tool" in tool_names
    
    def test_list_registered_tools_alias(self, clean_registry, mock_basic_tool):
        """Test list_registered_tools() alias for get_tool_names()."""
        registry = clean_registry
        registry.register_tool(mock_basic_tool)
        
        # Verify alias works the same
        tool_names_1 = registry.get_tool_names()
        tool_names_2 = registry.list_registered_tools()
        
        assert tool_names_1 == tool_names_2
        assert "basic_tool" in tool_names_2
    
    def test_has_tool(self, clean_registry, mock_basic_tool):
        """Test tool existence checking."""
        registry = clean_registry
        
        # Initially tool doesn't exist
        assert not registry.has_tool("basic_tool")
        assert not registry.has_tool("nonexistent_tool")
        
        # Register tool
        registry.register_tool(mock_basic_tool)
        
        # Now tool exists
        assert registry.has_tool("basic_tool")
        assert not registry.has_tool("nonexistent_tool")


class TestCapabilitySystem:
    """
    Test capability indexing and filtering functionality.
    
    ### Capability Testing Strategy:
    - Tests capability indexing during tool registration
    - Validates capability-based tool filtering
    - Tests complex capability requirement matching
    - Verifies capability index maintenance and updates
    - Tests capability discovery and enumeration
    """
    
    def test_capability_indexing(self, clean_registry, sample_tool_specs):
        """Test capability indexing during tool registration."""
        registry = clean_registry
        
        # Create tools with different capabilities
        tool1 = Mock(spec=AbstractTool)
        tool1.name = "tool1"
        spec1 = sample_tool_specs["basic_tool"]
        
        tool2 = Mock(spec=AbstractTool) 
        tool2.name = "tool2"
        spec2 = sample_tool_specs["advanced_tool"]
        
        # Register tools
        registry.register_tool(tool1, spec1)
        registry.register_tool(tool2, spec2)
        
        # Verify capability indexing
        assert "test_execution" in registry.capability_index
        assert "ai_guidance" in registry.capability_index
        assert "pattern_recognition" in registry.capability_index
        
        # Verify tool associations
        assert "tool1" in registry.capability_index["test_execution"]
        assert "tool2" in registry.capability_index["test_execution"]
        assert "tool2" in registry.capability_index["ai_guidance"]
        assert "tool1" not in registry.capability_index["ai_guidance"]
    
    def test_get_tools_by_capability_single(self, clean_registry, sample_tool_specs):
        """Test tool retrieval by single capability."""
        registry = clean_registry
        
        # Register tools with different capabilities
        tool1 = Mock(spec=AbstractTool)
        tool1.name = "tool1"
        registry.register_tool(tool1, sample_tool_specs["basic_tool"])
        
        tool2 = Mock(spec=AbstractTool)
        tool2.name = "tool2"
        registry.register_tool(tool2, sample_tool_specs["advanced_tool"])
        
        # Test capability-based retrieval
        test_execution_tools = registry.get_tools_by_capability("test_execution")
        assert len(test_execution_tools) == 2
        assert tool1 in test_execution_tools
        assert tool2 in test_execution_tools
        
        ai_guidance_tools = registry.get_tools_by_capability("ai_guidance")
        assert len(ai_guidance_tools) == 1
        assert tool2 in ai_guidance_tools
        assert tool1 not in ai_guidance_tools
        
        nonexistent_tools = registry.get_tools_by_capability("nonexistent_capability")
        assert len(nonexistent_tools) == 0
    
    def test_get_tools_by_capabilities_require_all(self, clean_registry, sample_tool_specs):
        """Test tool retrieval requiring ALL specified capabilities."""
        registry = clean_registry
        
        # Register tools
        tool1 = Mock(spec=AbstractTool)
        tool1.name = "tool1"
        registry.register_tool(tool1, sample_tool_specs["basic_tool"])
        
        tool2 = Mock(spec=AbstractTool)
        tool2.name = "tool2"  
        registry.register_tool(tool2, sample_tool_specs["advanced_tool"])
        
        # Test requiring all capabilities
        common_caps = ["test_execution", "process_management"]
        tools_with_common = registry.get_tools_by_capabilities(common_caps, require_all=True)
        assert len(tools_with_common) == 1
        assert tool1 in tools_with_common
        
        advanced_caps = ["test_execution", "ai_guidance", "pattern_recognition"]
        tools_with_advanced = registry.get_tools_by_capabilities(advanced_caps, require_all=True)
        assert len(tools_with_advanced) == 1
        assert tool2 in tools_with_advanced
        
        impossible_caps = ["test_execution", "nonexistent_capability"]
        tools_with_impossible = registry.get_tools_by_capabilities(impossible_caps, require_all=True)
        assert len(tools_with_impossible) == 0
    
    def test_get_tools_by_capabilities_require_any(self, clean_registry, sample_tool_specs):
        """Test tool retrieval requiring ANY of specified capabilities."""
        registry = clean_registry
        
        # Register tools
        tool1 = Mock(spec=AbstractTool)
        tool1.name = "tool1"
        registry.register_tool(tool1, sample_tool_specs["basic_tool"])
        
        tool2 = Mock(spec=AbstractTool)
        tool2.name = "tool2"
        registry.register_tool(tool2, sample_tool_specs["advanced_tool"])
        
        # Test requiring any capability
        mixed_caps = ["ai_guidance", "process_management"]
        tools_with_any = registry.get_tools_by_capabilities(mixed_caps, require_all=False)
        assert len(tools_with_any) == 2
        assert tool1 in tools_with_any  # has process_management
        assert tool2 in tools_with_any  # has ai_guidance
        
        exclusive_caps = ["pattern_recognition", "nonexistent_capability"]
        tools_with_exclusive = registry.get_tools_by_capabilities(exclusive_caps, require_all=False)
        assert len(tools_with_exclusive) == 1
        assert tool2 in tools_with_exclusive
    
    def test_get_tools_by_capabilities_empty_list(self, clean_registry, mock_basic_tool, mock_configurable_tool):
        """Test tool retrieval with empty capability list."""
        registry = clean_registry
        
        # Register tools
        registry.register_tool(mock_basic_tool)
        registry.register_tool(mock_configurable_tool)
        
        # Empty capabilities should return all tools
        all_tools_via_caps = registry.get_tools_by_capabilities([])
        all_tools_direct = registry.get_all_tools()
        
        assert len(all_tools_via_caps) == len(all_tools_direct)
        assert set(all_tools_via_caps) == set(all_tools_direct)
    
    def test_get_available_capabilities(self, clean_registry, sample_tool_specs):
        """Test enumeration of available capabilities."""
        registry = clean_registry
        
        # Initially no capabilities
        capabilities = registry.get_available_capabilities()
        assert len(capabilities) == 0
        
        # Register tools with capabilities
        tool1 = Mock(spec=AbstractTool)
        tool1.name = "tool1"
        registry.register_tool(tool1, sample_tool_specs["basic_tool"])
        
        tool2 = Mock(spec=AbstractTool)
        tool2.name = "tool2"
        registry.register_tool(tool2, sample_tool_specs["advanced_tool"])
        
        # Get available capabilities
        capabilities = registry.get_available_capabilities()
        
        # Verify all capabilities are present
        expected_caps = set()
        expected_caps.update(sample_tool_specs["basic_tool"].capabilities)
        expected_caps.update(sample_tool_specs["advanced_tool"].capabilities)
        
        assert set(capabilities) == expected_caps


class TestConfiguration:
    """
    Test configuration and variant management functionality.
    
    ### Configuration Testing Strategy:
    - Tests configuration registration and retrieval
    - Validates variant configuration handling
    - Tests configuration merging and inheritance
    - Verifies deep configuration merging logic
    - Tests configuration validation and error handling
    """
    
    def test_register_configuration(self, clean_registry, sample_configurations):
        """Test configuration registration."""
        registry = clean_registry
        config = sample_configurations["basic_config"]
        
        # Register configuration
        registry.register_configuration("test_tool", config)
        
        # Verify configuration storage
        assert "test_tool" in registry.configurations
        stored_config = registry.configurations["test_tool"]
        assert stored_config == config
        assert stored_config is not config  # Should be a copy
    
    def test_register_variant(self, clean_registry, sample_configurations):
        """Test variant configuration registration."""
        registry = clean_registry
        base_config = sample_configurations["basic_config"]
        variant_config = sample_configurations["variant_config"]
        
        # Register base configuration and variant
        registry.register_configuration("test_tool", base_config)
        registry.register_variant("test_tool", "performance", variant_config)
        
        # Verify variant storage
        assert "test_tool" in registry.variants
        assert "performance" in registry.variants["test_tool"]
        stored_variant = registry.variants["test_tool"]["performance"]
        assert stored_variant == variant_config
        assert stored_variant is not variant_config  # Should be a copy
    
    def test_get_tool_configuration_default(self, clean_registry, sample_configurations):
        """Test getting default tool configuration."""
        registry = clean_registry
        config = sample_configurations["basic_config"]
        
        # Register configuration
        registry.register_configuration("test_tool", config)
        
        # Get default configuration
        retrieved_config = registry.get_tool_configuration("test_tool")
        assert retrieved_config == config
        
        # Verify it's a copy, not the original
        assert retrieved_config is not config
        retrieved_config["new_key"] = "new_value"
        assert "new_key" not in registry.configurations["test_tool"]
    
    def test_get_tool_configuration_with_variant(self, clean_registry, sample_configurations):
        """Test getting tool configuration with variant."""
        registry = clean_registry
        base_config = sample_configurations["basic_config"]
        variant_config = sample_configurations["variant_config"]
        
        # Register base and variant configurations
        registry.register_configuration("test_tool", base_config)
        registry.register_variant("test_tool", "performance", variant_config)
        
        # Get configuration with variant
        merged_config = registry.get_tool_configuration("test_tool", "performance")
        
        # Verify merging (variant should override base)
        assert merged_config["timeout"] == base_config["timeout"]  # From base
        assert merged_config["verbose"] == base_config["verbose"]  # From base  
        assert merged_config["device_id"] == base_config["device_id"]  # From base
        assert merged_config["strategy"] == variant_config["strategy"]  # From variant
        assert merged_config["running_minutes"] == variant_config["running_minutes"]  # From variant
    
    def test_get_tool_configuration_deep_merge(self, clean_registry):
        """Test deep configuration merging."""
        registry = clean_registry
        
        # Create configurations with nested structures
        base_config = {
            "timeout": 300,
            "llm": {
                "model_name": "gpt-3.5",
                "temperature": 0.5,
                "max_tokens": 1024
            },
            "strategy": {
                "type": "random",
                "depth": 3
            }
        }
        
        variant_config = {
            "llm": {
                "model_name": "gpt-4",  # Override model
                "temperature": 0.7     # Override temperature, keep max_tokens
            },
            "strategy": {
                "type": "adaptive",    # Override type, keep depth
                "exploration": True    # Add new property
            },
            "new_section": {
                "enabled": True
            }
        }
        
        # Register configurations
        registry.register_configuration("test_tool", base_config)
        registry.register_variant("test_tool", "advanced", variant_config)
        
        # Get merged configuration
        merged_config = registry.get_tool_configuration("test_tool", "advanced")
        
        # Verify deep merging
        assert merged_config["timeout"] == 300  # From base
        assert merged_config["llm"]["model_name"] == "gpt-4"  # From variant
        assert merged_config["llm"]["temperature"] == 0.7  # From variant
        assert merged_config["llm"]["max_tokens"] == 1024  # From base (preserved)
        assert merged_config["strategy"]["type"] == "adaptive"  # From variant
        assert merged_config["strategy"]["depth"] == 3  # From base (preserved)
        assert merged_config["strategy"]["exploration"] is True  # From variant (new)
        assert merged_config["new_section"]["enabled"] is True  # From variant (new section)
    
    def test_get_tool_configuration_nonexistent(self, clean_registry):
        """Test getting configuration for non-existent tool."""
        registry = clean_registry
        
        # Get configuration for non-existent tool
        config = registry.get_tool_configuration("nonexistent_tool")
        assert config == {}
        
        # Get configuration with non-existent variant
        config = registry.get_tool_configuration("nonexistent_tool", "nonexistent_variant")
        assert config == {}
    
    def test_get_tool_configuration_nonexistent_variant(self, clean_registry, sample_configurations):
        """Test getting configuration with non-existent variant."""
        registry = clean_registry
        base_config = sample_configurations["basic_config"]
        
        # Register base configuration only
        registry.register_configuration("test_tool", base_config)
        
        # Get configuration with non-existent variant (should return base only)
        config = registry.get_tool_configuration("test_tool", "nonexistent_variant")
        assert config == base_config
    
    @patch('rv_tools.registry.registry.ErrorHandler')
    def test_configuration_error_handling(self, mock_error_handler, clean_registry):
        """Test error handling in configuration operations."""
        registry = clean_registry
        
        # Mock error handler
        error_handler_instance = Mock()
        mock_error_handler.get_instance.return_value = error_handler_instance
        registry.error_handler = error_handler_instance
        
        # Test with invalid configuration (simulate error during copy operation)
        mock_config = Mock()
        mock_config.copy.side_effect = Exception("Copy error")
        
        with pytest.raises(Exception, match="Copy error"):
            registry.register_configuration("test_tool", mock_config)
        
        # Verify error handler was called
        error_handler_instance.handle_error.assert_called_once()


class TestToolSpecification:
    """
    Test tool specification parsing and validation functionality.
    
    ### Specification Testing Strategy:
    - Tests tool specification string parsing
    - Validates variant and parameter extraction
    - Tests specification validation and error handling
    - Verifies complex specification parsing scenarios
    - Tests edge cases and malformed specifications
    """
    
    def test_resolve_tool_spec_simple(self, clean_registry):
        """Test parsing simple tool specification."""
        registry = clean_registry
        
        # Parse simple specification
        tool_name, variants, params = registry.resolve_tool_spec("basic_tool")
        
        assert tool_name == "basic_tool"
        assert variants == ["default"]
        assert params == {}
    
    def test_resolve_tool_spec_with_variant(self, clean_registry):
        """Test parsing specification with variant."""
        registry = clean_registry
        
        # Parse specification with single variant
        tool_name, variants, params = registry.resolve_tool_spec("basic_tool:performance")
        
        assert tool_name == "basic_tool"
        assert variants == ["performance"]
        assert params == {}
    
    def test_resolve_tool_spec_with_multiple_variants(self, clean_registry):
        """Test parsing specification with multiple variants."""
        registry = clean_registry
        
        # Parse specification with multiple variants
        tool_name, variants, params = registry.resolve_tool_spec("basic_tool:performance:debug")
        
        assert tool_name == "basic_tool"
        assert variants == ["performance", "debug"]
        assert params == {}
    
    def test_resolve_tool_spec_with_parameters(self, clean_registry):
        """Test parsing specification with parameters."""
        registry = clean_registry
        
        # Parse specification with parameters
        tool_name, variants, params = registry.resolve_tool_spec("basic_tool@timeout=300,verbose=true")
        
        assert tool_name == "basic_tool"
        assert variants == ["default"]
        assert params == {"timeout": "300", "verbose": "true"}
    
    def test_resolve_tool_spec_complex(self, clean_registry):
        """Test parsing complex specification with variants and parameters."""
        registry = clean_registry
        
        # Parse complex specification
        tool_name, variants, params = registry.resolve_tool_spec(
            "advanced_tool:ai:adaptive@model=gpt-4,temp=0.7,max_tokens=2048"
        )
        
        assert tool_name == "advanced_tool"
        assert variants == ["ai", "adaptive"]
        assert params == {
            "model": "gpt-4",
            "temp": "0.7", 
            "max_tokens": "2048"
        }
    
    def test_resolve_tool_spec_with_whitespace(self, clean_registry):
        """Test parsing specification with whitespace."""
        registry = clean_registry
        
        # Parse specification with extra whitespace
        tool_name, variants, params = registry.resolve_tool_spec(
            "  basic_tool  :  performance  @  timeout=300  ,  verbose=true  "
        )
        
        assert tool_name == "basic_tool"
        assert variants == ["performance"]
        assert params == {"timeout": "300", "verbose": "true"}
    
    def test_resolve_tool_spec_empty_parameters(self, clean_registry):
        """Test parsing specification with empty parameters."""
        registry = clean_registry
        
        # Parse specification with @ but no parameters
        tool_name, variants, params = registry.resolve_tool_spec("basic_tool@")
        
        assert tool_name == "basic_tool"
        assert variants == ["default"]
        assert params == {}
    
    def test_resolve_tool_spec_malformed_parameters(self, clean_registry):
        """Test parsing specification with malformed parameters."""
        registry = clean_registry
        
        # Parse specification with malformed parameters (no = sign)
        tool_name, variants, params = registry.resolve_tool_spec("basic_tool@invalid_param,valid=value")
        
        assert tool_name == "basic_tool"
        assert variants == ["default"]
        # Should skip invalid parameter, keep valid one
        assert params == {"valid": "value"}
    
    def test_resolve_tool_spec_empty_string(self, clean_registry):
        """Test parsing empty specification string."""
        registry = clean_registry
        
        # Parse empty specification
        tool_name, variants, params = registry.resolve_tool_spec("")
        
        assert tool_name == ""
        assert variants == ["default"]
        assert params == {}
    
    @patch('rv_tools.registry.registry.ErrorHandler')
    def test_resolve_tool_spec_error_handling(self, mock_error_handler, clean_registry):
        """Test error handling in specification parsing."""
        registry = clean_registry
        
        # Mock error handler
        error_handler_instance = Mock()
        mock_error_handler.get_instance.return_value = error_handler_instance
        registry.error_handler = error_handler_instance
        
        # Create a spec that would cause an error by mocking the spec parameter directly
        mock_spec = Mock()
        mock_spec.split.side_effect = Exception("Parse error")
        
        with pytest.raises(ValueError, match="Invalid tool specification"):
            # This should trigger an error during parsing
            registry.resolve_tool_spec(mock_spec)
        
        # Verify error handler was called
        error_handler_instance.handle_error.assert_called_once()


class TestRegistryInformation:
    """
    Test registry information and metadata access functionality.
    
    ### Information Testing Strategy:
    - Tests registry statistics and metadata retrieval
    - Validates registry state information
    - Tests registry clearing and reset operations
    - Verifies information accuracy and consistency
    - Tests information access under various registry states
    """
    
    def test_get_registry_info_empty(self, clean_registry):
        """Test registry information when empty."""
        registry = clean_registry
        
        info = registry.get_registry_info()
        
        assert info["total_tools"] == 0
        assert info["total_tool_classes"] == 0
        assert info["total_configurations"] == 0
        assert info["total_variants"] == 0
        assert info["available_capabilities"] == []
        assert info["registered_tools"] == []
    
    def test_get_registry_info_with_tools(self, clean_registry, mock_basic_tool, mock_configurable_tool, sample_tool_specs):
        """Test registry information with registered tools."""
        registry = clean_registry
        
        # Register tools and configurations
        registry.register_tool(mock_basic_tool, sample_tool_specs["basic_tool"])
        registry.register_tool(mock_configurable_tool, sample_tool_specs["advanced_tool"])
        registry.register_configuration("basic_tool", {"timeout": 300})
        registry.register_variant("basic_tool", "performance", {"timeout": 600})
        registry.register_variant("configurable_tool", "ai", {"model": "gpt-4"})
        
        # Get registry information
        info = registry.get_registry_info()
        
        # Verify information accuracy
        assert info["total_tools"] == 2
        assert info["total_tool_classes"] == 0  # No classes registered
        assert info["total_configurations"] == 2  # Both tools get empty configs on registration
        assert info["total_variants"] == 2  # 2 custom variants (no default variants automatically created)
        
        # Verify capabilities
        expected_capabilities = set()
        expected_capabilities.update(sample_tool_specs["basic_tool"].capabilities)
        expected_capabilities.update(sample_tool_specs["advanced_tool"].capabilities)
        assert set(info["available_capabilities"]) == expected_capabilities
        
        # Verify registered tools
        assert set(info["registered_tools"]) == {"basic_tool", "configurable_tool"}
    
    def test_clear_registry(self, clean_registry, mock_basic_tool, sample_configurations):
        """Test registry clearing functionality."""
        registry = clean_registry
        
        # Populate registry
        registry.register_tool(mock_basic_tool)
        registry.register_configuration("basic_tool", sample_configurations["basic_config"])
        registry.register_variant("basic_tool", "performance", {"timeout": 600})
        
        # Verify registry has content
        assert len(registry.get_tool_names()) > 0
        assert len(registry.configurations) > 0
        assert len(registry.variants) > 0
        
        # Clear registry
        registry.clear()
        
        # Verify registry is empty
        assert len(registry.get_tool_names()) == 0
        assert len(registry.configurations) == 0
        assert len(registry.variants) == 0
        assert len(registry.capability_index) == 0
        assert len(registry.tool_specs) == 0
        assert len(registry.tool_classes) == 0
    
    def test_registry_thread_safety_information_access(self, clean_registry, threading_test_helper):
        """Test thread safety of information access operations."""
        registry = clean_registry
        
        # Add some tools for information access
        for i in range(5):
            mock_tool = Mock(spec=AbstractTool)
            mock_tool.name = f"tool_{i}"
            registry.register_tool(mock_tool)
        
        def access_registry_info():
            """Access various registry information."""
            info = registry.get_registry_info()
            names = registry.get_tool_names()
            all_tools = registry.get_all_tools()
            capabilities = registry.get_available_capabilities()
            return len(info["registered_tools"]) + len(names) + len(all_tools) + len(capabilities)
        
        # Run concurrent access
        results, exceptions = threading_test_helper["run_concurrent"](
            access_registry_info,
            num_threads=10,
            iterations=20
        )
        
        # Verify no exceptions and consistent results
        assert len(exceptions) == 0
        assert all(result == results[0] for result in results)  # All results should be the same