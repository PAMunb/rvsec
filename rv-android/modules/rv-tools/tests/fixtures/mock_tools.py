"""
Mock tool implementations for comprehensive registry testing.

This module provides realistic mock tool implementations that follow
the actual interface contracts for thorough testing of the tool registry
and factory systems without external dependencies.

### Mock Tool Types:
- **MockBasicTool**: Simple AbstractTool implementation for basic testing
- **MockConfigurableTool**: ConfigurableTool with realistic configuration behavior
- **MockComplexTool**: Advanced tool with multiple capabilities and variants
- **MockFailingTool**: Tool that simulates various failure scenarios

### Mock Implementation Strategy:
- Follows actual interface contracts for realistic testing
- Provides configurable behavior for different testing scenarios
- Supports error simulation for comprehensive negative testing
- Maintains state consistency for tool lifecycle testing
"""

from typing import Dict, Any, List, Optional
from unittest.mock import Mock

from rv_android_core.app import App
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.configurable_tool import ConfigurableTool
from rv_android_core.tools.tool_spec import ToolSpec, ToolType, ToolCategory


class MockBasicTool(AbstractTool):
    """
    Mock implementation of AbstractTool for basic testing scenarios.
    
    ### Mock Tool Architecture:
    - Implements minimal AbstractTool interface for testing
    - Provides predictable behavior for tool operation validation
    - Supports basic execution workflow testing
    - Enables tool registration and lifecycle testing
    
    ### Testing Applications:
    - Registry tool registration and retrieval testing
    - Basic tool execution workflow validation
    - Tool specification and metadata testing
    - Process cleanup and error handling testing
    """
    
    # Class-level tool specification
    TOOL_SPEC = ToolSpec(
        name="mock_basic_tool",
        description="Mock basic tool for monitored operations testing",
        version="1.0.0",
        tool_type=ToolType.BUILTIN,
        category=ToolCategory.RANDOM_TESTING,
        capabilities=["test_execution", "process_management"],
        dependencies=["android>=7.0"]
    )
    
    def __init__(self, name: str = "mock_basic_tool"):
        """
        Initialize mock basic tool.
        
        Args:
            name: Tool name (defaults to mock_basic_tool)
        """
        super().__init__(
            name=name,
            description="Mock basic tool for monitored operations testing",
            process_pattern="mock_basic.*"
        )
        
        # Track execution calls for testing
        self.execution_count = 0
        self.last_task = None
        self.last_app = None
        self.execution_error = None  # Set to exception to simulate error
        
    def execute_tool_specific_logic(self, task: Any, app: App) -> None:
        """
        Execute mock tool logic with tracking.
        
        Args:
            task: Task configuration and context
            app: Application under test
            
        Raises:
            Exception: If execution_error is set
        """
        # Track execution for testing
        self.execution_count += 1
        self.last_task = task
        self.last_app = app
        
        # Simulate error if configured
        if self.execution_error:
            raise self.execution_error
        
        # Log execution for testing verification
        self.logger.info(f"Mock basic tool executed for app: {app.name if app else 'unknown'}")
    
    def set_execution_error(self, error: Exception) -> None:
        """Set error to simulate during execution."""
        self.execution_error = error
    
    def clear_execution_error(self) -> None:
        """Clear execution error simulation."""
        self.execution_error = None
    
    def reset_execution_tracking(self) -> None:
        """Reset execution tracking for clean testing."""
        self.execution_count = 0
        self.last_task = None
        self.last_app = None


class MockConfigurableTool(ConfigurableTool):
    """
    Mock implementation of ConfigurableTool for configuration testing.
    
    ### Mock Configurable Tool Architecture:
    - Implements full ConfigurableTool interface for configuration testing
    - Provides realistic configuration handling and validation
    - Supports configuration merging and parameter processing testing
    - Enables configuration inheritance and override testing
    
    ### Testing Applications:
    - Configuration system testing and validation
    - Tool factory configuration merging testing
    - Variant configuration and parameter override testing
    - Configuration error handling and validation testing
    """
    
    # Class-level tool specification
    TOOL_SPEC = ToolSpec(
        name="mock_configurable_tool",
        description="Mock configurable tool for monitored operations testing",
        version="2.0.0",
        tool_type=ToolType.EXTERNAL,
        category=ToolCategory.AI_GUIDED,
        capabilities=["test_execution", "configuration_management", "advanced_features"],
        dependencies=["android>=8.0", "memory>=2GB"]
    )
    
    def __init__(self, name: str = "mock_configurable_tool"):
        """
        Initialize mock configurable tool.
        
        Args:
            name: Tool name (defaults to mock_configurable_tool)
        """
        super().__init__(
            name=name,
            description="Mock configurable tool for monitored operations testing",
            process_pattern="mock_configurable.*"
        )
        
        # Track configuration calls for testing
        self.configuration_count = 0
        self.configuration_history = []
        self.last_configuration = None
        
        # Track execution for testing
        self.execution_count = 0
        self.last_task = None
        self.last_app = None
        
        # Error simulation
        self.configuration_error = None
        self.execution_error = None
    
    def configure_tool_specific(self, config: Dict[str, Any]) -> None:
        """
        Handle tool-specific configuration with tracking.
        
        Args:
            config: Configuration dictionary
            
        Raises:
            Exception: If configuration_error is set
        """
        # Track configuration for testing
        self.configuration_count += 1
        self.configuration_history.append(config.copy())
        self.last_configuration = config.copy()
        
        # Simulate configuration error if configured
        if self.configuration_error:
            raise self.configuration_error
        
        # Log configuration for testing verification
        self.logger.debug(f"Mock configurable tool configured with: {config}")
        
        # Simulate tool-specific configuration processing
        if "timeout" in config:
            self.set_config_value("processed_timeout", config["timeout"] + 10)
        
        if "llm" in config and isinstance(config["llm"], dict):
            # Process LLM configuration
            if "model_name" in config["llm"]:
                self.set_config_value("llm.processed_model", config["llm"]["model_name"].upper())
    
    def execute_tool_specific_logic(self, task: Any, app: App) -> None:
        """
        Execute mock tool logic with configuration awareness.
        
        Args:
            task: Task configuration and context
            app: Application under test
            
        Raises:
            Exception: If execution_error is set
        """
        # Track execution for testing
        self.execution_count += 1
        self.last_task = task
        self.last_app = app
        
        # Simulate error if configured
        if self.execution_error:
            raise self.execution_error
        
        # Use configuration in execution
        timeout = self.get_config_value("timeout", 300)
        verbose = self.get_config_value("verbose", False)
        
        # Log execution with configuration context
        self.logger.info(f"Mock configurable tool executed for app: {app.name if app else 'unknown'}")
        self.logger.debug(f"Execution with timeout: {timeout}, verbose: {verbose}")
    
    def set_configuration_error(self, error: Exception) -> None:
        """Set error to simulate during configuration."""
        self.configuration_error = error
    
    def set_execution_error(self, error: Exception) -> None:
        """Set error to simulate during execution."""
        self.execution_error = error
    
    def clear_errors(self) -> None:
        """Clear all error simulations."""
        self.configuration_error = None
        self.execution_error = None
    
    def reset_tracking(self) -> None:
        """Reset all tracking for clean testing."""
        self.configuration_count = 0
        self.configuration_history = []
        self.last_configuration = None
        self.execution_count = 0
        self.last_task = None
        self.last_app = None
        self.clear_config()


class MockComplexTool(ConfigurableTool):
    """
    Mock implementation of complex tool with multiple capabilities and variants.
    
    ### Mock Complex Tool Architecture:
    - Implements advanced tool features for comprehensive testing
    - Provides multiple capabilities and variant configurations
    - Supports complex configuration structures and dependencies
    - Enables advanced registry and factory testing scenarios
    
    ### Testing Applications:
    - Advanced capability-based tool filtering testing
    - Complex configuration merging and inheritance testing
    - Multi-variant tool specification testing
    - Advanced tool factory creation and parameter processing
    """
    
    # Class-level tool specification with multiple capabilities
    TOOL_SPEC = ToolSpec(
        name="mock_complex_tool",
        description="Mock complex tool with multiple capabilities for monitored operations testing",
        version="3.0.0",
        tool_type=ToolType.PLUGIN,
        category=ToolCategory.AI_GUIDED,
        capabilities=[
            "test_execution", "ai_guidance", "pattern_recognition", 
            "data_analysis", "custom_analysis", "report_generation"
        ],
        dependencies=[
            "android>=9.0", "memory>=4GB", "python>=3.12", "numpy", "pandas", "sklearn"
        ]
    )
    
    def __init__(self, name: str = "mock_complex_tool"):
        """
        Initialize mock complex tool.
        
        Args:
            name: Tool name (defaults to mock_complex_tool)
        """
        super().__init__(
            name=name,
            description="Mock complex tool with multiple capabilities for monitored operations testing",
            process_pattern="mock_complex.*"
        )
        
        # Initialize tracking attributes first
        self.operations_performed = []
        self.analysis_results = {}
        self.current_mode = "standard"
        
        # Initialize complex default configuration
        self.configure({
            "mode": "standard",
            "timeout": 600,
            "llm": {
                "model_name": "mock-model",
                "temperature": 0.7,
                "max_tokens": 2048
            },
            "analysis": {
                "enabled": True,
                "depth": 5,
                "algorithms": ["pattern_matching", "ml_inference"]
            },
            "reporting": {
                "format": "json",
                "include_metadata": True,
                "verbosity": "detailed"
            }
        })
        
        # Variant-specific behavior simulation
        self.variant_behaviors = {
            "basic": {"analysis_depth": 3, "ai_enabled": False},
            "advanced": {"analysis_depth": 7, "ai_enabled": False},
            "ai": {"analysis_depth": 5, "ai_enabled": True},
            "research": {"analysis_depth": 10, "ai_enabled": True, "experimental_features": True}
        }
    
    def configure_tool_specific(self, config: Dict[str, Any]) -> None:
        """
        Handle complex tool-specific configuration.
        
        Args:
            config: Configuration dictionary
        """
        # Process mode configuration
        if "mode" in config:
            self.current_mode = config["mode"]
            self.operations_performed.append(f"mode_changed_to_{self.current_mode}")
        
        # Process variant configuration if specified
        if "variant" in config and config["variant"] in self.variant_behaviors:
            variant_config = self.variant_behaviors[config["variant"]]
            for key, value in variant_config.items():
                self.set_config_value(f"variant.{key}", value)
            self.operations_performed.append(f"variant_applied_{config['variant']}")
        
        # Process LLM configuration
        if "llm" in config:
            llm_config = config["llm"]
            if "model_name" in llm_config:
                self.operations_performed.append(f"llm_model_set_{llm_config['model_name']}")
        
        # Process analysis configuration
        if "analysis" in config:
            analysis_config = config["analysis"]
            if "depth" in analysis_config:
                self.operations_performed.append(f"analysis_depth_set_{analysis_config['depth']}")
        
        self.logger.debug(f"Complex tool configured in {self.current_mode} mode")
    
    def execute_tool_specific_logic(self, task: Any, app: App) -> None:
        """
        Execute complex tool logic with multi-capability behavior.
        
        Args:
            task: Task configuration and context
            app: Application under test
        """
        app_name = app.name if app else "unknown"
        self.logger.info(f"Mock complex tool executing for app: {app_name}")
        
        # Simulate different execution phases based on capabilities
        self._execute_test_execution_phase(task, app)
        
        if self.get_config_value("variant.ai_enabled", False):
            self._execute_ai_guidance_phase(task, app)
        
        if self.get_config_value("analysis.enabled", True):
            self._execute_analysis_phase(task, app)
        
        if self.get_config_value("reporting.format"):
            self._execute_reporting_phase(task, app)
        
        self.operations_performed.append(f"full_execution_completed_{app_name}")
    
    def _execute_test_execution_phase(self, task: Any, app: App) -> None:
        """Execute test execution capability."""
        timeout = self.get_config_value("timeout", 600)
        self.operations_performed.append(f"test_execution_phase_timeout_{timeout}")
        self.analysis_results["test_execution"] = {"duration": timeout * 0.8, "status": "completed"}
    
    def _execute_ai_guidance_phase(self, task: Any, app: App) -> None:
        """Execute AI guidance capability."""
        model = self.get_config_value("llm.model_name", "mock-model")
        temperature = self.get_config_value("llm.temperature", 0.7)
        self.operations_performed.append(f"ai_guidance_phase_model_{model}_temp_{temperature}")
        self.analysis_results["ai_guidance"] = {"model": model, "recommendations": 5}
    
    def _execute_analysis_phase(self, task: Any, app: App) -> None:
        """Execute analysis capability."""
        depth = self.get_config_value("analysis.depth", 5)
        algorithms = self.get_config_value("analysis.algorithms", [])
        self.operations_performed.append(f"analysis_phase_depth_{depth}_algos_{len(algorithms)}")
        self.analysis_results["analysis"] = {"depth": depth, "patterns_found": depth * 2}
    
    def _execute_reporting_phase(self, task: Any, app: App) -> None:
        """Execute reporting capability."""
        report_format = self.get_config_value("reporting.format", "json")
        verbosity = self.get_config_value("reporting.verbosity", "standard")
        self.operations_performed.append(f"reporting_phase_format_{report_format}_verbosity_{verbosity}")
        self.analysis_results["reporting"] = {"format": report_format, "size": "large" if verbosity == "detailed" else "medium"}
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of tool execution for testing verification."""
        return {
            "operations_performed": self.operations_performed.copy(),
            "analysis_results": self.analysis_results.copy(),
            "current_mode": self.current_mode,
            "configuration": self.get_config_dict()
        }
    
    def reset_execution_state(self) -> None:
        """Reset execution state for clean testing."""
        self.operations_performed = []
        self.analysis_results = {}
        self.current_mode = "standard"


class MockFailingTool(AbstractTool):
    """
    Mock tool that simulates various failure scenarios for error testing.
    
    ### Mock Failing Tool Architecture:
    - Implements AbstractTool with configurable failure modes
    - Provides controlled error simulation for comprehensive error testing
    - Supports different failure types and error scenarios
    - Enables error handling and recovery testing validation
    
    ### Testing Applications:
    - Error handling and recovery testing
    - Registry error scenario validation
    - Tool execution failure testing
    - Error propagation and logging testing
    """
    
    # Class-level tool specification
    TOOL_SPEC = ToolSpec(
        name="mock_failing_tool",
        description="Mock tool that simulates failures for error testing",
        version="1.0.0",
        tool_type=ToolType.BUILTIN,
        category=ToolCategory.RANDOM_TESTING,
        capabilities=["test_execution", "error_simulation"],
        dependencies=["android>=7.0"]
    )
    
    def __init__(self, name: str = "mock_failing_tool"):
        """
        Initialize mock failing tool.
        
        Args:
            name: Tool name (defaults to mock_failing_tool)
        """
        super().__init__(
            name=name,
            description="Mock tool that simulates failures for error testing",
            process_pattern="mock_failing.*"
        )
        
        # Failure configuration
        self.failure_mode = None
        self.failure_message = "Simulated failure"
        self.failure_count = 0
        self.max_failures = 1  # Fail first N executions, then succeed
    
    def set_failure_mode(self, mode: str, message: str = None, max_failures: int = 1) -> None:
        """
        Configure failure behavior.
        
        Args:
            mode: Failure mode ('execution', 'initialization', 'cleanup', etc.)
            message: Custom failure message
            max_failures: Number of times to fail before succeeding
        """
        self.failure_mode = mode
        if message:
            self.failure_message = message
        self.max_failures = max_failures
        self.failure_count = 0
    
    def clear_failure_mode(self) -> None:
        """Clear failure mode for normal operation."""
        self.failure_mode = None
        self.failure_count = 0
    
    def execute_tool_specific_logic(self, task: Any, app: App) -> None:
        """
        Execute with optional failure simulation.
        
        Args:
            task: Task configuration and context
            app: Application under test
            
        Raises:
            Exception: Based on configured failure mode
        """
        # Check if we should fail
        if self.failure_mode == "execution" and self.failure_count < self.max_failures:
            self.failure_count += 1
            self.logger.error(f"Simulating execution failure: {self.failure_message}")
            raise Exception(self.failure_message)
        
        # Normal execution
        app_name = app.name if app else "unknown"
        self.logger.info(f"Mock failing tool executed successfully for app: {app_name}")
    
    def kill_related_processes(self, process_pattern: str) -> None:
        """
        Override process cleanup with optional failure simulation.
        
        Args:
            process_pattern: Pattern for process cleanup
            
        Raises:
            Exception: If cleanup failure mode is set
        """
        if self.failure_mode == "cleanup" and self.failure_count < self.max_failures:
            self.failure_count += 1
            self.logger.error(f"Simulating cleanup failure: {self.failure_message}")
            raise Exception(self.failure_message)
        
        # Normal cleanup (or simulate normal cleanup)
        self.logger.debug(f"Mock cleanup completed for pattern: {process_pattern}")
    
    def get_tool_info(self) -> dict:
        """
        Get tool info with optional failure simulation.
        
        Returns:
            Tool information dictionary
            
        Raises:
            Exception: If info failure mode is set
        """
        if self.failure_mode == "info" and self.failure_count < self.max_failures:
            self.failure_count += 1
            raise Exception(self.failure_message)
        
        info = super().get_tool_info()
        info["failure_mode"] = self.failure_mode
        info["failure_count"] = self.failure_count
        return info


def create_mock_tool_collection() -> Dict[str, AbstractTool]:
    """
    Create a collection of mock tools for comprehensive testing.
    
    Returns:
        Dictionary mapping tool names to mock tool instances
    """
    return {
        "mock_basic": MockBasicTool("mock_basic"),
        "mock_configurable": MockConfigurableTool("mock_configurable"),
        "mock_complex": MockComplexTool("mock_complex"),
        "mock_failing": MockFailingTool("mock_failing"),
        "mock_basic_alt": MockBasicTool("mock_basic_alt"),
        "mock_configurable_alt": MockConfigurableTool("mock_configurable_alt")
    }


def create_mock_tool_specs() -> Dict[str, ToolSpec]:
    """
    Create tool specifications for mock tools.
    
    Returns:
        Dictionary mapping tool names to tool specifications
    """
    return {
        "mock_basic": MockBasicTool.TOOL_SPEC,
        "mock_configurable": MockConfigurableTool.TOOL_SPEC,
        "mock_complex": MockComplexTool.TOOL_SPEC,
        "mock_failing": MockFailingTool.TOOL_SPEC
    }


def create_mock_tool_configurations() -> Dict[str, Dict[str, Any]]:
    """
    Create sample configurations for mock tools.
    
    Returns:
        Dictionary mapping tool names to configuration dictionaries
    """
    return {
        "mock_basic": {
            "timeout": 300,
            "verbose": True,
            "device_id": "emulator-5554"
        },
        "mock_configurable": {
            "timeout": 600,
            "verbose": False,
            "llm": {
                "model_name": "test-model",
                "temperature": 0.5,
                "max_tokens": 1024
            },
            "analysis": {
                "enabled": True,
                "depth": 3
            }
        },
        "mock_complex": {
            "mode": "research",
            "timeout": 900,
            "variant": "ai",
            "llm": {
                "model_name": "advanced-model",
                "temperature": 0.8,
                "max_tokens": 4096
            },
            "analysis": {
                "enabled": True,
                "depth": 10,
                "algorithms": ["pattern_matching", "ml_inference", "statistical_analysis"]
            },
            "reporting": {
                "format": "json",
                "include_metadata": True,
                "verbosity": "detailed"
            }
        }
    }


def create_mock_tool_variants() -> Dict[str, Dict[str, Dict[str, Any]]]:
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
        "mock_complex": {
            "basic": {
                "variant": "basic",
                "analysis": {"depth": 3}
            },
            "advanced": {
                "variant": "advanced", 
                "analysis": {"depth": 7}
            },
            "ai": {
                "variant": "ai",
                "llm": {"temperature": 0.9}
            },
            "research": {
                "variant": "research",
                "analysis": {"depth": 10},
                "reporting": {"verbosity": "detailed"}
            }
        }
    }