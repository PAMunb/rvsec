"""
Simple mock tool implementations for rv-tools simplified architecture testing.

This module provides minimal mock tool implementations that follow
the simplified AbstractTool interface for testing the core functionalities
of the rv-tools system.
"""

from typing import Dict, Any
from rv_android_core.domain.app import App
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec
from rv_android_core.domain.task import Task


class MockBasicTool(AbstractTool):
    """
    Simple mock implementation of AbstractTool for basic testing scenarios.
    """
    
    # Class-level tool specification
    TOOL_SPEC = ToolSpec(
        name="mock_basic_tool",
        description="Mock basic tool for testing",
        url="https://example.com/mock_basic_tool",
        version="1.0.0"
    )
    
    def __init__(self, name: str = "mock_basic_tool"):
        """Initialize mock basic tool."""
        super().__init__(
            name=name,
            description="Mock basic tool for testing",
            process_pattern=f"{name}.*"
        )
        
        # Track execution calls for testing
        self.execution_count = 0
        self.last_task = None
        self.last_app = None
    
    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
        """Execute mock tool logic with tracking."""
        # Track execution for testing
        self.execution_count += 1
        self.last_task = task
        self.last_app = app
        
        # Log execution for testing verification
        self.logger.info(f"Mock basic tool executed for app: {app.name if app else 'unknown'}")
    
    def reset_execution_tracking(self) -> None:
        """Reset execution tracking for clean testing."""
        self.execution_count = 0
        self.last_task = None
        self.last_app = None


class MockConfigurableTool(AbstractTool):
    """
    Mock implementation of configurable tool for configuration testing.
    """
    
    # Class-level tool specification
    TOOL_SPEC = ToolSpec(
        name="mock_configurable_tool",
        description="Mock configurable tool for testing",
        url="https://example.com/mock_configurable_tool",
        version="2.0.0"
    )
    
    def __init__(self, name: str = "mock_configurable_tool"):
        """Initialize mock configurable tool."""
        super().__init__(
            name=name,
            description="Mock configurable tool for testing",
            process_pattern=f"{name}.*"
        )
        
        # Track configuration and execution for testing
        self.configuration_count = 0
        self.configuration_history = []
        self.last_configuration = None
        self.execution_count = 0
        self.last_task = None
        self.last_app = None
        self.config = {}
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Handle tool configuration with tracking."""
        # Track configuration for testing
        self.configuration_count += 1
        self.configuration_history.append(config.copy())
        self.last_configuration = config.copy()
        self.config.update(config)
    
    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
        """Execute mock tool logic with configuration awareness."""
        # Track execution for testing
        self.execution_count += 1
        self.last_task = task
        self.last_app = app
        
        # Use configuration in execution
        timeout = self.config.get("timeout", 300)
        verbose = self.config.get("verbose", False)
        
        # Log execution with configuration context
        self.logger.info(f"Mock configurable tool executed for app: {app.name if app else 'unknown'}")
        self.logger.debug(f"Execution with timeout: {timeout}, verbose: {verbose}")
    
    def reset_tracking(self) -> None:
        """Reset all tracking for clean testing."""
        self.configuration_count = 0
        self.configuration_history = []
        self.last_configuration = None
        self.execution_count = 0
        self.last_task = None
        self.last_app = None
        self.config = {}


def create_mock_tool_collection():
    """
    Create a collection of mock tools for testing.
    
    Returns:
        Dictionary mapping tool names to mock tool instances
    """
    return {
        "mock_basic": MockBasicTool("mock_basic"),
        "mock_configurable": MockConfigurableTool("mock_configurable"),
        "mock_basic_alt": MockBasicTool("mock_basic_alt"),
    }


def create_mock_tool_specs():
    """
    Create tool specifications for mock tools.
    
    Returns:
        Dictionary mapping tool names to tool specifications
    """
    return {
        "mock_basic": MockBasicTool.TOOL_SPEC,
        "mock_configurable": MockConfigurableTool.TOOL_SPEC,
    }


def create_mock_tool_configurations():
    """
    Create sample configurations for mock tools.
    
    Returns:
        Dictionary mapping tool names to configuration dictionaries
    """
    return {
        "mock_basic": {
            "timeout": 300,
            "verbose": True,
        },
        "mock_configurable": {
            "timeout": 600,
            "verbose": False,
            "llm": {
                "model_name": "test-model",
                "temperature": 0.5,
            },
            "analysis": {
                "enabled": True,
                "depth": 3
            }
        },
    }


def create_mock_tool_variants():
    """
    Create sample variants for mock tools.
    
    Returns:
        Dictionary mapping tool names to variant configurations
    """
    return {
        "mock_configurable": {
            "performance": {
                "timeout": 1200,
                "analysis": {"depth": 7}
            },
            "debug": {
                "verbose": True,
                "analysis": {"enabled": False}
            }
        },
    }