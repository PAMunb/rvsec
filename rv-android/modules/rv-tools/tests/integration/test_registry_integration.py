"""
Integration tests for registry workflows and tool management systems.

This module provides comprehensive integration testing of the complete
tool registry ecosystem, validating end-to-end workflows from tool
registration through execution and cleanup.

### Integration Test Coverage:
- Complete tool registration to execution workflows
- Registry-Factory integration for tool creation and configuration
- Multi-tool coordination and capability-based selection
- Configuration inheritance and variant merging
- Error propagation and recovery across registry components
- Performance and scalability under realistic load conditions

### Testing Architecture:
- Uses real registry and factory components (not mocks)
- Tests actual component interactions and data flow
- Validates realistic usage patterns and scenarios
- Tests system behavior under various load conditions
- Verifies error handling and recovery patterns

### Key Integration Scenarios:
- Tool registration, configuration, and creation workflows
- Complex specification parsing and tool instantiation
- Multi-variant configuration merging and inheritance
- Capability-based tool discovery and filtering
- Batch tool operations and performance validation
- Error scenarios and system resilience testing
"""

import pytest
import time
import threading
from typing import Dict, List, Any
from unittest.mock import Mock, patch

from rv_tools.registry.registry import ToolRegistry
from rv_tools.registry.factory import ToolFactory
from rv_android_core.tools.tool_spec import ToolSpec, ToolType, ToolCategory
from rv_android_core.app import App
from rv_android_core.util.exceptions import RVToolError

from ..fixtures.mock_tools import (
    MockBasicTool, MockConfigurableTool, MockComplexTool,
    create_mock_tool_collection, create_mock_tool_specs,
    create_mock_tool_configurations, create_mock_tool_variants
)


class TestRegistryFactoryIntegration:
    """
    Test integration between ToolRegistry and ToolFactory.
    
    ### Integration Testing Strategy:
    - Tests complete tool creation workflows using real components
    - Validates configuration merging across registry and factory
    - Tests tool specification parsing and instantiation
    - Verifies error handling and recovery patterns
    - Tests performance under realistic load conditions
    """
    
    def test_complete_tool_creation_workflow(self, clean_registry):
        """Test complete workflow from registration to tool creation."""
        registry = clean_registry
        
        # Register tools with specifications and configurations
        mock_tools = create_mock_tool_collection()
        mock_specs = create_mock_tool_specs()
        mock_configs = create_mock_tool_configurations()
        mock_variants = create_mock_tool_variants()
        
        # Register tools in registry
        for tool_name, tool in mock_tools.items():
            if tool_name in mock_specs:
                registry.register_tool(tool, mock_specs[tool_name])
        
        # Register configurations
        for tool_name, config in mock_configs.items():
            if tool_name in mock_tools:
                registry.register_configuration(tool_name, config)
        
        # Register variants
        for tool_name, variants in mock_variants.items():
            if tool_name in mock_tools:
                for variant_name, variant_config in variants.items():
                    registry.register_variant(tool_name, variant_name, variant_config)
        
        # Test tool creation through factory
        created_tool = ToolFactory.create_tool_from_spec("mock_configurable:performance@timeout=900", registry)
        
        # Verify tool creation and configuration
        assert created_tool is not None
        assert created_tool.name == "mock_configurable"
        assert created_tool is not mock_tools["mock_configurable"]  # Should be a copy
        
        # Verify configuration was applied (check if tool has been configured)
        if hasattr(created_tool, 'configuration_count'):
            # For mock tools, check configuration tracking
            assert created_tool.configuration_count > 0
        elif hasattr(created_tool, 'is_configured'):
            # For real tools, check if they were configured
            assert created_tool.is_configured is True
    
    def test_multi_tool_creation_and_coordination(self, clean_registry):
        """Test creation and coordination of multiple tools."""
        registry = clean_registry
        
        # Set up comprehensive tool environment
        mock_tools = create_mock_tool_collection()
        mock_specs = create_mock_tool_specs()
        mock_configs = create_mock_tool_configurations()
        
        # Register multiple tools
        for tool_name, tool in mock_tools.items():
            if tool_name in mock_specs:
                registry.register_tool(tool, mock_specs[tool_name])
                if tool_name in mock_configs:
                    registry.register_configuration(tool_name, mock_configs[tool_name])
        
        # Create multiple tools through factory
        tool_specs = [
            "mock_basic@timeout=300",
            "mock_configurable:performance",
            "mock_complex:ai@mode=research"
        ]
        
        created_tools = ToolFactory.batch_create_tools(tool_specs, registry)
        
        # Verify all tools created successfully
        assert len(created_tools) == 3
        assert all(tool is not None for tool in created_tools)
        
        # Verify tool names
        tool_names = [tool.name for tool in created_tools]
        assert "mock_basic" in tool_names
        assert "mock_configurable" in tool_names
        assert "mock_complex" in tool_names
        
        # Test capability-based tool selection
        ai_tools = registry.get_tools_by_capability("ai_guidance")
        analysis_tools = registry.get_tools_by_capability("data_analysis")
        
        # Verify capability filtering works with registered tools
        assert len(ai_tools) > 0
        assert len(analysis_tools) > 0
    
    def test_configuration_inheritance_and_merging(self, clean_registry):
        """Test complex configuration inheritance and merging scenarios."""
        registry = clean_registry
        
        # Register tool with complex configuration hierarchy
        mock_tool = MockConfigurableTool("inheritance_test_tool")
        tool_spec = ToolSpec(name="inheritance_test_tool",
            tool_type=ToolType.BUILTIN,
            description="Tool for testing configuration inheritance",
            version="1.0.0",
            category=ToolCategory.RANDOM_TESTING,
            capabilities=["test_execution", "configuration_testing"],
            dependencies=[]
        )
        
        registry.register_tool(mock_tool, tool_spec)
        
        # Register base configuration
        base_config = {
            "timeout": 300,
            "llm": {
                "model_name": "base-model",
                "temperature": 0.5,
                "max_tokens": 1024
            },
            "analysis": {
                "enabled": True,
                "depth": 3,
                "algorithms": ["basic"]
            }
        }
        registry.register_configuration("inheritance_test_tool", base_config)
        
        # Register multiple variants
        performance_variant = {
            "timeout": 600,
            "llm": {
                "model_name": "performance-model",
                "max_tokens": 2048
            },
            "analysis": {
                "depth": 5
            }
        }
        registry.register_variant("inheritance_test_tool", "performance", performance_variant)
        
        ai_variant = {
            "llm": {
                "model_name": "ai-model",
                "temperature": 0.8
            },
            "analysis": {
                "algorithms": ["advanced", "ml"]
            }
        }
        registry.register_variant("inheritance_test_tool", "ai", ai_variant)
        
        # Test configuration merging with multiple variants and parameters
        created_tool = ToolFactory.create_tool_from_spec(
            "inheritance_test_tool:performance:ai@timeout=900,verbose=true",
            registry
        )
        
        # Verify tool creation
        assert created_tool is not None
        assert created_tool.name == "inheritance_test_tool"
        
        # Verify configuration was applied and get merged config
        if hasattr(created_tool, 'configuration_count'):
            # For mock tools, check configuration tracking
            assert created_tool.configuration_count > 0
            merged_config = created_tool.last_configuration or {}
        else:
            # For real tools, check configuration was applied
            assert hasattr(created_tool, 'is_configured') and created_tool.is_configured
            merged_config = created_tool.config if hasattr(created_tool, 'config') else {}
        
        # Verify configuration merging hierarchy
        assert merged_config["timeout"] == 900  # From parameters (highest priority)
        assert merged_config["verbose"] is True  # From parameters
        assert merged_config["llm"]["model_name"] == "ai-model"  # From ai variant
        assert merged_config["llm"]["max_tokens"] == 2048  # From performance variant
        assert merged_config["llm"]["temperature"] == 0.8  # From ai variant
        assert merged_config["analysis"]["enabled"] is True  # From base
        assert merged_config["analysis"]["depth"] == 5  # From performance variant
        assert "advanced" in merged_config["analysis"]["algorithms"]  # From ai variant
    
    def test_capability_based_tool_discovery_integration(self, clean_registry):
        """Test comprehensive capability-based tool discovery."""
        registry = clean_registry
        
        # Register diverse tools with different capabilities
        tools_and_specs = [
            (MockBasicTool("basic_1"), ToolSpec(
                name="basic_1", tool_type=ToolType.BUILTIN, description="Basic tool 1",
                capabilities=["test_execution", "process_management"], version="1.0.0", category=ToolCategory.RANDOM_TESTING, dependencies=[])),
            (MockBasicTool("basic_2"), ToolSpec(name="basic_2", tool_type=ToolType.BUILTIN, description="Basic tool 2",
                capabilities=["test_execution", "data_collection"], version="1.0.0", category=ToolCategory.RANDOM_TESTING, dependencies=[])),
            (MockConfigurableTool("config_1"), ToolSpec(name="config_1", tool_type=ToolType.EXTERNAL, description="Configurable tool 1",
                capabilities=["test_execution", "ai_guidance", "configuration_management"], version="1.0.0", category=ToolCategory.RANDOM_TESTING, dependencies=[])),
            (MockComplexTool("complex_1"), ToolSpec(name="complex_1", tool_type=ToolType.PLUGIN, description="Complex tool 1",
                capabilities=["ai_guidance", "pattern_recognition", "data_analysis"], version="1.0.0", category=ToolCategory.RANDOM_TESTING, dependencies=[]))
        ]
        
        # Register all tools
        for tool, spec in tools_and_specs:
            registry.register_tool(tool, spec)
        
        # Test single capability filtering
        test_execution_tools = registry.get_tools_by_capability("test_execution")
        ai_guidance_tools = registry.get_tools_by_capability("ai_guidance")
        
        assert len(test_execution_tools) == 3  # basic_1, basic_2, config_1
        assert len(ai_guidance_tools) == 2    # config_1, complex_1
        
        # Test multiple capability filtering (require ALL)
        ai_and_test_tools = registry.get_tools_by_capabilities(
            ["test_execution", "ai_guidance"], require_all=True
        )
        assert len(ai_and_test_tools) == 1  # Only config_1
        assert ai_and_test_tools[0].name == "config_1"
        
        # Test multiple capability filtering (require ANY)
        ai_or_pattern_tools = registry.get_tools_by_capabilities(
            ["ai_guidance", "pattern_recognition"], require_all=False
        )
        assert len(ai_or_pattern_tools) == 2  # config_1, complex_1
        
        # Test capability enumeration
        all_capabilities = registry.get_available_capabilities()
        expected_capabilities = {
            "test_execution", "process_management", "data_collection",
            "ai_guidance", "configuration_management", "pattern_recognition", "data_analysis"
        }
        assert set(all_capabilities) == expected_capabilities
    
    def test_error_propagation_and_recovery(self, clean_registry):
        """Test error propagation and recovery across registry components."""
        registry = clean_registry
        
        # Register normal tool
        normal_tool = MockBasicTool("normal_tool")
        normal_spec = ToolSpec(name="normal_tool", tool_type=ToolType.BUILTIN, description="Normal tool",
            capabilities=["test_execution"], version="1.0.0", category=ToolCategory.RANDOM_TESTING, dependencies=[])
        registry.register_tool(normal_tool, normal_spec)
        
        # Test tool creation with non-existent tool
        with pytest.raises(RVToolError, match="Unknown tool"):
            ToolFactory.create_tool_from_spec("nonexistent_tool", registry)
        
        # Verify registry is still functional after error
        created_tool = ToolFactory.create_tool_from_spec("normal_tool", registry)
        assert created_tool is not None
        assert created_tool.name == "normal_tool"
        
        # Test invalid specification parsing
        with pytest.raises(RVToolError):
            ToolFactory.create_tool_from_spec("", registry)  # Empty spec
        
        # Verify registry remains functional
        registry_info = registry.get_registry_info()
        assert registry_info["total_tools"] == 1
        assert "normal_tool" in registry_info["registered_tools"]
        
        # Test batch operation with mixed valid/invalid specs
        mixed_specs = ["normal_tool", "nonexistent_tool", "normal_tool@timeout=300"]
        
        with pytest.raises(RVToolError):  # Should fail on first invalid spec
            ToolFactory.batch_create_tools(mixed_specs, registry)
        
        # Verify registry state is consistent
        assert registry.has_tool("normal_tool")
        assert not registry.has_tool("nonexistent_tool")


class TestPerformanceAndScalability:
    """
    Test performance and scalability of registry operations.
    
    ### Performance Testing Strategy:
    - Tests registry operations under realistic load conditions
    - Validates performance with large numbers of tools and configurations
    - Tests concurrent access and thread safety
    - Measures operation latency and throughput
    - Validates memory usage and resource management
    """
    
    def test_large_scale_tool_registration(self, clean_registry):
        """Test registry performance with large numbers of tools."""
        registry = clean_registry
        
        # Create large number of tools
        num_tools = 100
        tools = []
        specs = []
        
        start_time = time.time()
        
        for i in range(num_tools):
            tool_name = f"perf_tool_{i}"
            tool = MockBasicTool(tool_name)
            spec = ToolSpec(name=tool_name,
                tool_type=ToolType.BUILTIN,
                description=f"Performance test tool {i}",
                capabilities=[f"capability_{i % 10}", "test_execution"], version="1.0.0", category=ToolCategory.RANDOM_TESTING, dependencies=[])
            tools.append(tool)
            specs.append(spec)
            
            # Register tool
            registry.register_tool(tool, spec)
        
        registration_time = time.time() - start_time
        
        # Verify all tools registered
        assert len(registry.get_tool_names()) == num_tools
        
        # Test retrieval performance
        start_time = time.time()
        for i in range(num_tools):
            tool_name = f"perf_tool_{i}"
            retrieved_tool = registry.get_tool(tool_name)
            assert retrieved_tool is not None
            assert retrieved_tool.name == tool_name
        
        retrieval_time = time.time() - start_time
        
        # Test capability-based filtering performance
        start_time = time.time()
        for i in range(10):
            capability_name = f"capability_{i}"
            filtered_tools = registry.get_tools_by_capability(capability_name)
            assert len(filtered_tools) == num_tools // 10  # Each capability should have 10 tools
        
        filtering_time = time.time() - start_time
        
        # Performance assertions (adjust thresholds based on requirements)
        assert registration_time < 5.0, f"Registration took too long: {registration_time}s"
        assert retrieval_time < 2.0, f"Retrieval took too long: {retrieval_time}s"
        assert filtering_time < 1.0, f"Filtering took too long: {filtering_time}s"
    
    def test_concurrent_registry_access(self, clean_registry, threading_test_helper):
        """Test registry thread safety under concurrent access."""
        registry = clean_registry
        
        # Pre-populate registry with some tools
        for i in range(10):
            tool_name = f"concurrent_tool_{i}"
            tool = MockBasicTool(tool_name)
            registry.register_tool(tool, tool.TOOL_SPEC)
        
        # Test concurrent tool retrieval
        def retrieve_tools():
            results = []
            for i in range(10):
                tool_name = f"concurrent_tool_{i}"
                tool = registry.get_tool(tool_name)
                if tool:
                    results.append(tool.name)
            return len(results)
        
        # Run concurrent retrieval
        results, exceptions = threading_test_helper["run_concurrent"](
            retrieve_tools,
            num_threads=20,
            iterations=50
        )
        
        # Verify no exceptions and consistent results
        assert len(exceptions) == 0, f"Exceptions during concurrent access: {exceptions}"
        assert all(result == 10 for result in results), "Inconsistent retrieval results"
        
        # Test concurrent capability filtering
        def filter_by_capability():
            tools = registry.get_tools_by_capability("test_execution")
            return len(tools)
        
        results, exceptions = threading_test_helper["run_concurrent"](
            filter_by_capability,
            num_threads=15,
            iterations=30
        )
        
        # Verify thread safety of capability filtering
        assert len(exceptions) == 0
        assert all(result == 10 for result in results)  # All tools have test_execution capability
    
    def test_complex_configuration_performance(self, clean_registry):
        """Test performance of complex configuration operations."""
        registry = clean_registry
        
        # Register tool with complex configuration structure
        tool = MockConfigurableTool("complex_config_tool")
        spec = ToolSpec(name="complex_config_tool", tool_type=ToolType.EXTERNAL, description="Complex config tool",
            capabilities=["test_execution", "configuration_management"], version="1.0.0", category=ToolCategory.RANDOM_TESTING, dependencies=[])
        registry.register_tool(tool, spec)
        
        # Create complex base configuration
        base_config = {
            "timeout": 300,
            "llm": {
                "model_name": "base-model",
                "temperature": 0.5,
                "max_tokens": 1024,
                "advanced": {
                    "batch_size": 32,
                    "learning_rate": 0.001,
                    "epochs": 100
                }
            },
            "analysis": {
                "enabled": True,
                "depth": 5,
                "algorithms": ["pattern_matching", "ml_inference"],
                "preprocessing": {
                    "normalize": True,
                    "feature_extraction": {
                        "method": "auto",
                        "parameters": {"threshold": 0.8}
                    }
                }
            }
        }
        registry.register_configuration("complex_config_tool", base_config)
        
        # Create multiple complex variants
        num_variants = 20
        for i in range(num_variants):
            variant_config = {
                "llm": {
                    "model_name": f"variant-model-{i}",
                    "temperature": 0.5 + (i * 0.01),
                    "advanced": {
                        "batch_size": 32 + i,
                        "learning_rate": 0.001 + (i * 0.0001)
                    }
                },
                "analysis": {
                    "depth": 5 + i,
                    "preprocessing": {
                        "feature_extraction": {
                            "parameters": {"threshold": 0.8 - (i * 0.01)}
                        }
                    }
                }
            }
            registry.register_variant("complex_config_tool", f"variant_{i}", variant_config)
        
        # Test configuration merging performance
        start_time = time.time()
        
        for i in range(num_variants):
            merged_config = registry.get_tool_configuration("complex_config_tool", f"variant_{i}")
            
            # Verify configuration structure is correct
            assert merged_config["llm"]["model_name"] == f"variant-model-{i}"
            assert merged_config["llm"]["temperature"] == 0.5 + (i * 0.01)
            assert merged_config["analysis"]["depth"] == 5 + i
            assert "pattern_matching" in merged_config["analysis"]["algorithms"]  # From base
        
        merging_time = time.time() - start_time
        
        # Test tool creation with complex configurations
        start_time = time.time()
        
        for i in range(0, num_variants, 5):  # Test every 5th variant
            spec = f"complex_config_tool:variant_{i}@timeout={600 + i * 10}"
            created_tool = ToolFactory.create_tool_from_spec(spec, registry)
            assert created_tool is not None
            assert created_tool.name == "complex_config_tool"
        
        creation_time = time.time() - start_time
        
        # Performance assertions
        assert merging_time < 2.0, f"Configuration merging took too long: {merging_time}s"
        assert creation_time < 3.0, f"Tool creation took too long: {creation_time}s"


class TestErrorHandlingAndResilience:
    """
    Test error handling and system resilience under various failure conditions.
    
    ### Resilience Testing Strategy:
    - Tests system behavior under various error conditions
    - Validates error recovery and graceful degradation
    - Tests error propagation and isolation
    - Verifies system state consistency after errors
    - Tests resource cleanup and memory management
    """
    
    def test_registry_resilience_under_errors(self, clean_registry):
        """Test registry resilience when components fail."""
        registry = clean_registry
        
        # Register normal tools
        normal_tools = []
        for i in range(5):
            tool_name = f"normal_tool_{i}"
            tool = MockBasicTool(tool_name)
            spec = ToolSpec(name=tool_name, tool_type=ToolType.BUILTIN, description=f"Normal tool {i}",
                capabilities=["test_execution"], version="1.0.0", category=ToolCategory.RANDOM_TESTING, dependencies=[])
            registry.register_tool(tool, spec)
            normal_tools.append(tool)
        
        # Simulate tool with problematic configuration
        problematic_tool = MockConfigurableTool("problematic_tool")
        problematic_tool.set_configuration_error(Exception("Configuration error"))
        
        problematic_spec = ToolSpec(name="problematic_tool", tool_type=ToolType.EXTERNAL, description="Problematic tool",
            capabilities=["test_execution"], version="1.0.0", category=ToolCategory.RANDOM_TESTING, dependencies=[])
        registry.register_tool(problematic_tool, problematic_spec)
        
        # Verify registry still functions normally
        assert len(registry.get_tool_names()) == 6
        
        # Test that other tools still work despite problematic tool
        for i in range(5):
            tool_name = f"normal_tool_{i}"
            retrieved_tool = registry.get_tool(tool_name)
            assert retrieved_tool is not None
            assert retrieved_tool.name == tool_name
        
        # Test capability filtering still works
        test_tools = registry.get_tools_by_capability("test_execution")
        assert len(test_tools) == 6  # All tools including problematic one
        
        # Test registry information is consistent
        registry_info = registry.get_registry_info()
        assert registry_info["total_tools"] == 6
        assert len(registry_info["registered_tools"]) == 6
    
    def test_factory_error_isolation(self, clean_registry):
        """Test that factory errors don't affect registry state."""
        registry = clean_registry
        
        # Register good tools
        good_tool = MockBasicTool("good_tool")
        good_spec = ToolSpec(name="good_tool", tool_type=ToolType.BUILTIN, description="Good tool",
            capabilities=["test_execution"], version="1.0.0", category=ToolCategory.RANDOM_TESTING, dependencies=[])
        registry.register_tool(good_tool, good_spec)
        registry.register_configuration("good_tool", {"timeout": 300})
        
        # Test successful tool creation
        created_tool = ToolFactory.create_tool_from_spec("good_tool", registry)
        assert created_tool is not None
        
        # Test factory error with invalid specification
        with pytest.raises(RVToolError):
            ToolFactory.create_tool_from_spec("nonexistent_tool", registry)
        
        # Verify registry state is unchanged after factory error
        assert registry.has_tool("good_tool")
        assert len(registry.get_tool_names()) == 1
        
        # Verify factory can still create good tools after error
        another_tool = ToolFactory.create_tool_from_spec("good_tool@timeout=600", registry)
        assert another_tool is not None
        assert another_tool.name == "good_tool"
    
    def test_memory_and_resource_management(self, clean_registry):
        """Test memory usage and resource cleanup."""
        registry = clean_registry
        
        # Create and register many tools to test memory usage
        initial_tool_count = len(registry.get_tool_names())
        
        # Register many tools
        num_tools = 50
        for i in range(num_tools):
            tool_name = f"memory_test_tool_{i}"
            tool = MockBasicTool(tool_name)
            spec = ToolSpec(name=tool_name, tool_type=ToolType.BUILTIN, description=f"Memory test tool {i}",
                capabilities=["test_execution"], version="1.0.0", category=ToolCategory.RANDOM_TESTING, dependencies=[])
            registry.register_tool(tool, spec)
            
            # Register configuration for each tool
            config = {
                "timeout": 300 + i,
                "data": [f"item_{j}" for j in range(10)],  # Some data to use memory
                "metadata": {"created": i, "type": "memory_test"}
            }
            registry.register_configuration(tool_name, config)
        
        # Verify all tools are registered
        assert len(registry.get_tool_names()) == initial_tool_count + num_tools
        
        # Test registry operations work correctly with many tools
        registry_info = registry.get_registry_info()
        assert registry_info["total_tools"] == initial_tool_count + num_tools
        assert registry_info["total_configurations"] == num_tools
        
        # Test capability filtering with many tools
        test_execution_tools = registry.get_tools_by_capability("test_execution")
        assert len(test_execution_tools) == initial_tool_count + num_tools
        
        # Clear registry to test cleanup
        registry.clear()
        
        # Verify cleanup worked
        assert len(registry.get_tool_names()) == 0
        assert len(registry.configurations) == 0
        assert len(registry.variants) == 0
        assert len(registry.capability_index) == 0
        
        # Verify registry can be used normally after cleanup
        new_tool = MockBasicTool("post_cleanup_tool")
        new_spec = ToolSpec(name="post_cleanup_tool", tool_type=ToolType.BUILTIN, description="Post cleanup tool",
            capabilities=["test_execution"], version="1.0.0", category=ToolCategory.RANDOM_TESTING, dependencies=[])
        registry.register_tool(new_tool, new_spec)
        
        assert registry.has_tool("post_cleanup_tool")
        assert len(registry.get_tool_names()) == 1