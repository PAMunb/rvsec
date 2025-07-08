"""
Pytest configuration and shared fixtures for RV-Tools tests.

This module provides comprehensive test fixtures and configuration for
monitored operations testing tool registry and plugin system tests.

### Key Fixtures:
- **clean_registry**: Isolated ToolRegistry instance for each test
- **mock_logging_manager**: Controlled logging for test isolation
- **mock_error_handler**: Error handling mock for testing error scenarios
- **sample_tools**: Collection of mock tools for comprehensive testing

### Architectural Decisions:
- Provides complete test isolation through registry reset mechanisms
- Mocks rv-android-core components for unit test independence
- Supports both unit testing (mocked dependencies) and integration testing
- Enables comprehensive error scenario testing through controlled mocks
- Maintains consistent "monitored operations" terminology across tests
"""

import pytest
from unittest.mock import Mock
from typing import Dict
import threading

from rv_tools.registry.registry import ToolRegistry
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec


@pytest.fixture(autouse=True)
def reset_registry():
    """
    Automatically reset the ToolRegistry singleton before each test.
    
    ### Architectural Role:
    - Ensures complete test isolation by resetting registry state
    - Prevents test interference through shared singleton state
    - Enables predictable test execution regardless of test order
    - Maintains clean state for comprehensive registry testing
    """
    # Reset the singleton instance before each test
    ToolRegistry.reset_instance()
    yield
    # Reset again after test completion for cleanup
    ToolRegistry.reset_instance()


@pytest.fixture
def clean_registry():
    """
    Provide a clean ToolRegistry instance for testing.
    
    ### Implementation Strategy:
    - Creates fresh registry instance with no pre-registered tools
    - Provides isolated environment for registry operation testing
    - Enables comprehensive validation of registration workflows
    - Supports both positive and negative test scenarios
    
    Returns:
        ToolRegistry: Fresh registry instance
    """
    return ToolRegistry.get_instance()


@pytest.fixture
def mock_logging_manager():
    """
    Provide a mock LoggingManager for test isolation.
    
    ### Test Architecture:
    - Isolates tests from actual logging infrastructure
    - Enables verification of logging calls and messages
    - Provides controlled logging behavior for error scenarios
    - Maintains test performance through mock logging operations
    
    Returns:
        Mock: Configured LoggingManager mock
    """
    mock_manager = Mock()
    mock_logger = Mock()
    mock_manager.get_instance.return_value = mock_manager
    mock_manager.get_logger.return_value = mock_logger
    
    # Configure logger methods to be no-ops but trackable
    mock_logger.debug = Mock()
    mock_logger.info = Mock()
    mock_logger.warning = Mock()
    mock_logger.error = Mock()
    
    return mock_manager


@pytest.fixture
def mock_error_handler():
    """
    Provide a mock ErrorHandler for controlled error testing.
    
    ### Error Testing Strategy:
    - Enables verification of error handling workflows
    - Provides controlled error behavior for negative test scenarios
    - Isolates tests from actual error handling infrastructure
    - Supports comprehensive error scenario validation
    
    Returns:
        Mock: Configured ErrorHandler mock
    """
    mock_handler = Mock()
    mock_handler.get_instance.return_value = mock_handler
    mock_handler.handle_error = Mock()
    
    return mock_handler


@pytest.fixture
def sample_tool_specs():
    """
    Provide sample tool specifications for testing.
    
    ### Test Data Strategy:
    - Provides diverse tool specifications covering different scenarios
    - Enables comprehensive testing of tool specification parsing
    - Supports validation of tool capability and metadata handling
    - Covers both simple and complex tool configuration patterns
    
    Returns:
        Dict[str, ToolSpec]: Collection of tool specifications
    """
    return {
        "basic_tool": ToolSpec(
            name="basic_tool",
            description="Basic monitored operations testing tool",
            url="https://example.com/basic",
            version="1.0.0"
        ),
        "advanced_tool": ToolSpec(
            name="advanced_tool",
            description="Advanced AI-driven monitored operations tool",
            url="https://example.com/advanced",
            version="2.1.0"
        ),
        "plugin_tool": ToolSpec(
            name="plugin_tool",
            description="External plugin monitored operations tool",
            url="https://example.com/plugin",
            version="0.5.0"
        )
    }


@pytest.fixture
def mock_basic_tool(sample_tool_specs):
    """
    Provide a mock basic tool implementation for testing.
    
    ### Mock Tool Architecture:
    - Implements AbstractTool interface for realistic testing
    - Provides predictable behavior for tool operation validation
    - Supports configuration testing through mock methods
    - Enables comprehensive tool lifecycle testing
    
    Returns:
        Mock: Configured tool mock with realistic behavior
    """
    mock_tool = Mock(spec=AbstractTool)
    mock_tool.name = "basic_tool"
    mock_tool.description = "Mock basic monitored operations tool"
    mock_tool.process_pattern = "basic_tool.*"
    mock_tool.TOOL_SPEC = sample_tool_specs["basic_tool"]
    
    # Configure methods to be trackable
    mock_tool.execute_tool_specific_logic = Mock()
    mock_tool.execute = Mock()
    mock_tool.kill_related_processes = Mock()
    mock_tool.get_tool_info.return_value = {
        "name": "basic_tool",
        "description": "Mock basic monitored operations tool",
        "process_pattern": "basic_tool.*"
    }
    
    return mock_tool


@pytest.fixture
def mock_configurable_tool(sample_tool_specs):
    """
    Provide a mock configurable tool for configuration testing.
    
    ### Configuration Testing Strategy:
    - Implements AbstractTool interface with configuration capabilities
    - Provides realistic configuration handling behavior
    - Enables testing of configuration merging and parameter processing
    - Supports variant configuration testing scenarios
    
    Returns:
        Mock: Configured tool mock with configuration capabilities
    """
    mock_tool = Mock(spec=AbstractTool)
    mock_tool.name = "configurable_tool"
    mock_tool.description = "Mock configurable monitored operations tool"
    mock_tool.process_pattern = "configurable_tool.*"
    mock_tool.TOOL_SPEC = sample_tool_specs["advanced_tool"]
    mock_tool.config = {}
    
    # Configure configuration methods
    mock_tool.configure = Mock()
    
    # Configure inherited methods
    mock_tool.execute_tool_specific_logic = Mock()
    mock_tool.execute = Mock()
    mock_tool.kill_related_processes = Mock()
    mock_tool.get_tool_info.return_value = {
        "name": "configurable_tool",
        "description": "Mock configurable monitored operations tool",
        "process_pattern": "configurable_tool.*",
        "configuration": {},
        "configurable": True
    }
    
    return mock_tool


@pytest.fixture
def sample_configurations():
    """
    Provide sample tool configurations for testing.
    
    ### Configuration Test Data:
    - Covers various configuration complexity levels
    - Includes nested configuration structures
    - Provides variant configuration examples
    - Supports parameter override testing scenarios
    
    Returns:
        Dict[str, Dict]: Collection of tool configurations
    """
    return {
        "basic_config": {
            "timeout": 300,
            "verbose": True,
            "device_id": "emulator-5554"
        },
        "advanced_config": {
            "timeout": 600,
            "llm": {
                "model_name": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 2048
            },
            "strategy": {
                "type": "adaptive",
                "exploration_depth": 5
            },
            "parser": {
                "type": "uiautomator",
                "visitor": "enhanced"
            }
        },
        "variant_config": {
            "strategy": {
                "type": "bfs",
                "max_depth": 10
            },
            "running_minutes": 15
        }
    }


@pytest.fixture
def sample_tool_specifications():
    """
    Provide sample tool specification strings for factory testing.
    
    ### Specification Testing Strategy:
    - Covers simple tool names and complex specifications
    - Includes variant specifications and parameter overrides
    - Provides both valid and invalid specification examples
    - Supports comprehensive specification parsing validation
    
    Returns:
        Dict[str, str]: Collection of tool specification strings
    """
    return {
        "simple": "basic_tool",
        "with_variant": "basic_tool:performance",
        "with_multiple_variants": "basic_tool:performance:debug",
        "with_parameters": "basic_tool@timeout=300,verbose=true",
        "complex": "advanced_tool:ai:adaptive@model=gpt-4,temp=0.7,max_tokens=2048",
        "invalid_tool": "nonexistent_tool",
        "invalid_format": "basic_tool@invalid_param_format",
        "empty_spec": "",
        "whitespace_spec": "  basic_tool  :  performance  @  timeout=300  "
    }


@pytest.fixture
def mock_plugin():
    """
    Provide a mock plugin for plugin system testing.
    
    ### Plugin Testing Architecture:
    - Implements ToolPlugin interface for realistic plugin testing
    - Provides controlled plugin behavior for validation scenarios
    - Supports plugin lifecycle testing (discovery, loading, cleanup)
    - Enables comprehensive plugin system integration testing
    
    Returns:
        Mock: Configured plugin mock with realistic plugin behavior
    """
    from rv_tools.interfaces.plugin_interface import ToolPlugin
    
    mock_plugin = Mock(spec=ToolPlugin)
    mock_plugin.get_plugin_name.return_value = "mock_plugin"
    mock_plugin.get_plugin_version.return_value = "1.0.0"
    mock_plugin.get_tool_names.return_value = ["plugin_tool_1", "plugin_tool_2"]
    mock_plugin.get_supported_capabilities.return_value = ["custom_analysis", "data_export"]
    mock_plugin.validate_dependencies.return_value = True
    mock_plugin.register_tools = Mock()
    mock_plugin.cleanup = Mock()
    
    # Configure tool specifications
    mock_plugin.get_tool_spec.return_value = ToolSpec(
        name="plugin_tool_1",
        description="Mock plugin tool for testing",
        url="https://example.com/plugin1",
        version="1.0.0"
    )
    
    mock_plugin.get_tool_class.return_value = Mock(spec=AbstractTool)
    
    mock_plugin.get_plugin_metadata.return_value = {
        "name": "mock_plugin",
        "version": "1.0.0",
        "description": "Mock plugin for testing",
        "author": "Test Suite",
        "tools": ["plugin_tool_1", "plugin_tool_2"]
    }
    
    return mock_plugin


@pytest.fixture
def sample_app():
    """
    Provide a sample App instance for tool execution testing.
    
    ### App Testing Strategy:
    - Provides realistic App instance for tool execution validation
    - Supports comprehensive tool execution workflow testing
    - Enables validation of tool-app interaction patterns
    - Maintains consistency with rv-android-core App interface
    
    Returns:
        Mock: Configured App mock for tool testing
    """
    from rv_android_core.domain.app import App
    
    mock_app = Mock(spec=App)
    mock_app.name = "test_app"
    mock_app.package_name = "com.example.testapp"
    mock_app.apk_path = "/path/to/test_app.apk"
    mock_app.main_activity = "com.example.testapp.MainActivity"
    
    return mock_app


@pytest.fixture
def threading_test_helper():
    """
    Provide utilities for testing thread safety.
    
    ### Thread Safety Testing:
    - Enables comprehensive thread safety validation
    - Provides utilities for concurrent access testing
    - Supports registry singleton thread safety verification
    - Enables race condition and deadlock detection
    
    Returns:
        Dict: Thread testing utilities and helpers
    """
    def run_concurrent_operations(operation, num_threads=10, iterations=100):
        """Run an operation concurrently from multiple threads."""
        results = []
        exceptions = []
        
        def worker():
            try:
                for _ in range(iterations):
                    result = operation()
                    results.append(result)
            except Exception as e:
                exceptions.append(e)
        
        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        return results, exceptions
    
    def simulate_registry_access():
        """Simulate concurrent registry access."""
        registry = ToolRegistry.get_instance()
        return id(registry)  # Return instance ID to verify singleton
    
    return {
        "run_concurrent": run_concurrent_operations,
        "simulate_registry_access": simulate_registry_access
    }


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test" 
    )
    config.addinivalue_line(
        "markers", "thread_safety: mark test as thread safety test"
    )
    config.addinivalue_line(
        "markers", "error_scenario: mark test as error scenario test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location."""
    for item in items:
        # Add markers based on test file location
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "test_" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        
        # Add markers based on test name patterns
        if "thread" in item.name.lower() or "concurrent" in item.name.lower():
            item.add_marker(pytest.mark.thread_safety)
        
        if "error" in item.name.lower() or "fail" in item.name.lower():
            item.add_marker(pytest.mark.error_scenario)