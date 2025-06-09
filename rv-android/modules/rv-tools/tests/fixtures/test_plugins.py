"""
Mock plugin implementations for comprehensive plugin system testing.

This module provides realistic mock plugin implementations that follow
the ToolPlugin interface for thorough testing of the plugin loader
and registry integration without external dependencies.

### Mock Plugin Types:
- **MockBasicPlugin**: Simple plugin with one tool for basic testing
- **MockComplexPlugin**: Advanced plugin with multiple tools and dependencies
- **MockFailingPlugin**: Plugin that simulates various failure scenarios
- **MockExternalPlugin**: Plugin simulating external package integration

### Mock Implementation Strategy:
- Follows ToolPlugin interface contracts for realistic testing
- Provides configurable behavior for different testing scenarios
- Supports dependency validation and error simulation
- Maintains plugin lifecycle state for comprehensive testing
"""

from typing import Dict, List, Any, Optional, Type
from unittest.mock import Mock

from rv_tools.interfaces.plugin_interface import ToolPlugin
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.configurable_tool import ConfigurableTool
from rv_android_core.tools.tool_spec import ToolSpec, ToolType, ToolCategory
from rv_tools.registry.registry import ToolRegistry
from .mock_tools import MockBasicTool, MockConfigurableTool


class MockBasicPlugin(ToolPlugin):
    """
    Mock implementation of basic plugin for simple testing scenarios.
    
    ### Mock Basic Plugin Architecture:
    - Implements minimal ToolPlugin interface for testing
    - Provides single tool for basic plugin functionality testing
    - Supports basic plugin lifecycle and registration testing
    - Enables plugin discovery and loading workflow validation
    
    ### Testing Applications:
    - Basic plugin discovery and loading testing
    - Plugin registration with tool registry testing
    - Plugin metadata and information access testing
    - Plugin cleanup and lifecycle management testing
    """
    
    def __init__(self):
        """Initialize mock basic plugin."""
        self._plugin_name = "mock_basic_plugin"
        self._plugin_version = "1.0.0"
        self._dependencies_satisfied = True
        
        # Plugin tools
        self._tools = {
            "plugin_basic_tool": {
                "class": MockBasicTool,
                "spec": ToolSpec(
                    name="plugin_basic_tool",
                    description="Basic tool from mock plugin",
                    version="1.0.0",
                    tool_type=ToolType.PLUGIN,
                    category=ToolCategory.RANDOM_TESTING,
                    capabilities=["test_execution", "plugin_testing"],
                    dependencies=["python>=3.12"]
                )
            }
        }
        
        # Track registration calls for testing
        self.registration_count = 0
        self.cleanup_count = 0
    
    def get_plugin_name(self) -> str:
        """Get plugin name."""
        return self._plugin_name
    
    def get_plugin_version(self) -> str:
        """Get plugin version."""
        return self._plugin_version
    
    def get_plugin_description(self) -> str:
        """Get plugin description."""
        return "Mock basic plugin for testing"
    
    def get_dependencies(self) -> List[str]:
        """Get plugin dependencies."""
        return ["python>=3.12"]
    
    def get_plugin_metadata(self) -> Dict[str, Any]:
        """Get plugin metadata."""
        return {
            "name": self._plugin_name,
            "version": self._plugin_version,
            "description": "Mock basic plugin for testing",
            "author": "Test Suite",
            "tools": list(self._tools.keys()),
            "dependencies": self.get_dependencies(),
            "registration_count": self.registration_count,
            "cleanup_count": self.cleanup_count
        }
    
    def get_tool_names(self) -> List[str]:
        """Get list of tool names provided by this plugin."""
        return list(self._tools.keys())
    
    def get_tool_spec(self, tool_name: str) -> Optional[ToolSpec]:
        """Get tool specification for given tool name."""
        if tool_name in self._tools:
            return self._tools[tool_name]["spec"]
        return None
    
    def get_tool_class(self, tool_name: str) -> Optional[Type[AbstractTool]]:
        """Get tool class for given tool name."""
        if tool_name in self._tools:
            return self._tools[tool_name]["class"]
        return None
    
    def get_supported_capabilities(self) -> List[str]:
        """Get list of capabilities supported by this plugin."""
        capabilities = set()
        for tool_info in self._tools.values():
            capabilities.update(tool_info["spec"].capabilities)
        return list(capabilities)
    
    def validate_dependencies(self) -> bool:
        """Validate plugin dependencies."""
        return self._dependencies_satisfied
    
    def register_tools(self, registry: ToolRegistry) -> None:
        """Register plugin tools with the registry."""
        self.registration_count += 1
        
        for tool_name, tool_info in self._tools.items():
            # Register tool class and specification
            registry.register_tool_class(tool_name, tool_info["class"], tool_info["spec"])
    
    def cleanup(self) -> None:
        """Cleanup plugin resources."""
        self.cleanup_count += 1
    
    def set_dependencies_satisfied(self, satisfied: bool) -> None:
        """Set dependency satisfaction status for testing."""
        self._dependencies_satisfied = satisfied


class MockComplexPlugin(ToolPlugin):
    """
    Mock implementation of complex plugin with multiple tools and dependencies.
    
    ### Mock Complex Plugin Architecture:
    - Implements comprehensive ToolPlugin interface for advanced testing
    - Provides multiple tools with different capabilities
    - Supports dependency validation and configuration management
    - Enables complex plugin integration and workflow testing
    
    ### Testing Applications:
    - Multi-tool plugin registration and management testing
    - Plugin dependency validation and error handling testing
    - Complex plugin metadata and capability testing
    - Advanced plugin lifecycle and cleanup testing
    """
    
    def __init__(self):
        """Initialize mock complex plugin."""
        self._plugin_name = "mock_complex_plugin"
        self._plugin_version = "2.1.0"
        self._dependencies_satisfied = True
        self._dependency_errors = []
        
        # Plugin tools with different types and capabilities
        self._tools = {
            "plugin_advanced_tool": {
                "class": MockConfigurableTool,
                "spec": ToolSpec(
                    name="plugin_advanced_tool",
                    description="Advanced configurable tool from complex plugin",
                    version="2.1.0",
                    tool_type=ToolType.PLUGIN,
                    category=ToolCategory.AI_GUIDED,
                    capabilities=["test_execution", "configuration_management", "ai_guidance"],
                    dependencies=["python>=3.12", "memory>=2GB"]
                )
            },
            "plugin_analysis_tool": {
                "class": MockBasicTool,
                "spec": ToolSpec(
                    name="plugin_analysis_tool",
                    description="Analysis tool from complex plugin",
                    version="2.1.0",
                    tool_type=ToolType.PLUGIN,
                    category=ToolCategory.SYSTEMATIC,
                    capabilities=["data_analysis", "pattern_recognition", "report_generation"],
                    dependencies=["python>=3.12", "numpy>=1.20", "pandas>=1.3"]
                )
            },
            "plugin_ai_tool": {
                "class": MockConfigurableTool,
                "spec": ToolSpec(
                    name="plugin_ai_tool",
                    description="AI-enhanced tool from complex plugin",
                    version="2.1.0",
                    tool_type=ToolType.PLUGIN,
                    category=ToolCategory.AI_GUIDED,
                    capabilities=["ai_guidance", "machine_learning", "pattern_recognition"],
                    dependencies=["python>=3.12", "tensorflow>=2.8", "torch>=1.12"]
                )
            }
        }
        
        # Plugin dependencies
        self._dependencies = [
            {"name": "python", "version": ">=3.12", "required": True},
            {"name": "numpy", "version": ">=1.20", "required": True},
            {"name": "pandas", "version": ">=1.3", "required": True},
            {"name": "tensorflow", "version": ">=2.8", "required": False},
            {"name": "torch", "version": ">=1.12", "required": False}
        ]
        
        # Track operations for testing
        self.registration_count = 0
        self.cleanup_count = 0
        self.validation_count = 0
        self.last_registry = None
    
    def get_plugin_name(self) -> str:
        """Get plugin name."""
        return self._plugin_name
    
    def get_plugin_version(self) -> str:
        """Get plugin version."""
        return self._plugin_version
    
    def get_plugin_description(self) -> str:
        """Get plugin description."""
        return "Mock complex plugin with multiple tools and dependencies"
    
    def get_dependencies(self) -> List[str]:
        """Get plugin dependencies as string list."""
        return [dep["name"] + dep.get("version", "") for dep in self._dependencies if dep.get("required", True)]
    
    def get_plugin_metadata(self) -> Dict[str, Any]:
        """Get comprehensive plugin metadata."""
        return {
            "name": self._plugin_name,
            "version": self._plugin_version,
            "description": "Mock complex plugin with multiple tools and dependencies",
            "author": "Test Suite",
            "tools": list(self._tools.keys()),
            "dependencies": self._dependencies,
            "capabilities": self.get_supported_capabilities(),
            "registration_count": self.registration_count,
            "cleanup_count": self.cleanup_count,
            "validation_count": self.validation_count,
            "complexity": "high",
            "category": "ai_enhanced"
        }
    
    def get_tool_names(self) -> List[str]:
        """Get list of tool names provided by this plugin."""
        return list(self._tools.keys())
    
    def get_tool_spec(self, tool_name: str) -> Optional[ToolSpec]:
        """Get tool specification for given tool name."""
        if tool_name in self._tools:
            return self._tools[tool_name]["spec"]
        return None
    
    def get_tool_class(self, tool_name: str) -> Optional[Type[AbstractTool]]:
        """Get tool class for given tool name."""
        if tool_name in self._tools:
            return self._tools[tool_name]["class"]
        return None
    
    def get_supported_capabilities(self) -> List[str]:
        """Get comprehensive list of capabilities supported by this plugin."""
        capabilities = set()
        for tool_info in self._tools.values():
            capabilities.update(tool_info["spec"].capabilities)
        return sorted(list(capabilities))
    
    def validate_dependencies(self) -> bool:
        """Validate plugin dependencies with detailed checking."""
        self.validation_count += 1
        
        if not self._dependencies_satisfied:
            return False
        
        # Simulate dependency validation logic
        for dep in self._dependencies:
            if dep["required"] and dep["name"] in self._dependency_errors:
                return False
        
        return True
    
    def register_tools(self, registry: ToolRegistry) -> None:
        """Register all plugin tools with the registry."""
        self.registration_count += 1
        self.last_registry = registry
        
        for tool_name, tool_info in self._tools.items():
            # Register tool class and specification
            registry.register_tool_class(tool_name, tool_info["class"], tool_info["spec"])
            
            # Register default configurations for configurable tools
            if issubclass(tool_info["class"], ConfigurableTool):
                default_config = self._get_default_config(tool_name)
                if default_config:
                    registry.register_configuration(tool_name, default_config)
    
    def cleanup(self) -> None:
        """Cleanup plugin resources."""
        self.cleanup_count += 1
        # Simulate resource cleanup
        self.last_registry = None
    
    def set_dependencies_satisfied(self, satisfied: bool) -> None:
        """Set dependency satisfaction status for testing."""
        self._dependencies_satisfied = satisfied
    
    def add_dependency_error(self, dependency_name: str) -> None:
        """Add dependency error for testing."""
        if dependency_name not in self._dependency_errors:
            self._dependency_errors.append(dependency_name)
    
    def clear_dependency_errors(self) -> None:
        """Clear all dependency errors."""
        self._dependency_errors = []
    
    def _get_default_config(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get default configuration for a tool."""
        default_configs = {
            "plugin_advanced_tool": {
                "timeout": 900,
                "llm": {
                    "model_name": "plugin-model",
                    "temperature": 0.7,
                    "max_tokens": 2048
                },
                "analysis": {
                    "enabled": True,
                    "depth": 5
                }
            },
            "plugin_ai_tool": {
                "timeout": 1200,
                "ai": {
                    "model_type": "transformer",
                    "batch_size": 32,
                    "learning_rate": 0.001
                },
                "ml": {
                    "algorithm": "neural_network",
                    "epochs": 100
                }
            }
        }
        return default_configs.get(tool_name)


class MockFailingPlugin(ToolPlugin):
    """
    Mock plugin that simulates various failure scenarios for error testing.
    
    ### Mock Failing Plugin Architecture:
    - Implements ToolPlugin interface with configurable failure modes
    - Provides controlled error simulation for comprehensive error testing
    - Supports different failure types and error scenarios
    - Enables plugin error handling and recovery testing validation
    
    ### Testing Applications:
    - Plugin error handling and recovery testing
    - Plugin loader error scenario validation
    - Plugin registration failure testing
    - Plugin lifecycle error testing
    """
    
    def __init__(self):
        """Initialize mock failing plugin."""
        self._plugin_name = "mock_failing_plugin"
        self._plugin_version = "0.1.0"
        
        # Failure configuration
        self.failure_mode = None
        self.failure_message = "Simulated plugin failure"
        self.should_fail_validation = False
        self.should_fail_registration = False
        self.should_fail_metadata = False
        self.should_fail_cleanup = False
        
        # Track operations for testing
        self.operation_count = 0
        self.operations_attempted = []
    
    def get_plugin_name(self) -> str:
        """Get plugin name with optional failure."""
        self.operations_attempted.append("get_plugin_name")
        if self.failure_mode == "name":
            raise Exception(self.failure_message)
        return self._plugin_name
    
    def get_plugin_version(self) -> str:
        """Get plugin version with optional failure."""
        self.operations_attempted.append("get_plugin_version")
        if self.failure_mode == "version":
            raise Exception(self.failure_message)
        return self._plugin_version
    
    def get_plugin_description(self) -> str:
        """Get plugin description with optional failure."""
        self.operations_attempted.append("get_plugin_description")
        if self.failure_mode == "description":
            raise Exception(self.failure_message)
        return "Mock failing plugin for error testing"
    
    def get_dependencies(self) -> List[str]:
        """Get plugin dependencies with optional failure."""
        self.operations_attempted.append("get_dependencies")
        if self.failure_mode == "dependencies":
            raise Exception(self.failure_message)
        return ["python>=3.12"]
    
    def get_plugin_metadata(self) -> Dict[str, Any]:
        """Get plugin metadata with optional failure."""
        self.operations_attempted.append("get_plugin_metadata")
        if self.should_fail_metadata or self.failure_mode == "metadata":
            raise Exception(self.failure_message)
        
        return {
            "name": self._plugin_name,
            "version": self._plugin_version,
            "description": "Mock failing plugin for error testing",
            "author": "Test Suite",
            "tools": ["failing_tool"],
            "failure_mode": self.failure_mode,
            "operations_attempted": self.operations_attempted.copy()
        }
    
    def get_tool_names(self) -> List[str]:
        """Get tool names with optional failure."""
        self.operations_attempted.append("get_tool_names")
        if self.failure_mode == "tool_names":
            raise Exception(self.failure_message)
        return ["failing_tool"]
    
    def get_tool_spec(self, tool_name: str) -> Optional[ToolSpec]:
        """Get tool spec with optional failure."""
        self.operations_attempted.append(f"get_tool_spec_{tool_name}")
        if self.failure_mode == "tool_spec":
            raise Exception(self.failure_message)
        
        if tool_name == "failing_tool":
            return ToolSpec(
                name="failing_tool",
                description="Tool that simulates failures",
                version="0.1.0",
                tool_type=ToolType.PLUGIN,
                category=ToolCategory.RANDOM_TESTING,
                capabilities=["error_simulation"],
                dependencies=["python>=3.12"]
            )
        return None
    
    def get_tool_class(self, tool_name: str) -> Optional[Type[AbstractTool]]:
        """Get tool class with optional failure."""
        self.operations_attempted.append(f"get_tool_class_{tool_name}")
        if self.failure_mode == "tool_class":
            raise Exception(self.failure_message)
        
        if tool_name == "failing_tool":
            return MockBasicTool
        return None
    
    def get_supported_capabilities(self) -> List[str]:
        """Get capabilities with optional failure."""
        self.operations_attempted.append("get_supported_capabilities")
        if self.failure_mode == "capabilities":
            raise Exception(self.failure_message)
        return ["error_simulation"]
    
    def validate_dependencies(self) -> bool:
        """Validate dependencies with optional failure."""
        self.operations_attempted.append("validate_dependencies")
        if self.should_fail_validation or self.failure_mode == "validation":
            if self.failure_mode == "validation":
                raise Exception(self.failure_message)
            return False
        return True
    
    def register_tools(self, registry: ToolRegistry) -> None:
        """Register tools with optional failure."""
        self.operations_attempted.append("register_tools")
        if self.should_fail_registration or self.failure_mode == "registration":
            raise Exception(self.failure_message)
        
        # Simulate successful registration
        self.operation_count += 1
    
    def cleanup(self) -> None:
        """Cleanup with optional failure."""
        self.operations_attempted.append("cleanup")
        if self.should_fail_cleanup or self.failure_mode == "cleanup":
            raise Exception(self.failure_message)
        
        self.operation_count += 1
    
    def set_failure_mode(self, mode: str, message: str = None) -> None:
        """Set failure mode for testing."""
        self.failure_mode = mode
        if message:
            self.failure_message = message
    
    def set_validation_failure(self, should_fail: bool) -> None:
        """Set validation failure for testing."""
        self.should_fail_validation = should_fail
    
    def set_registration_failure(self, should_fail: bool) -> None:
        """Set registration failure for testing."""
        self.should_fail_registration = should_fail
    
    def set_metadata_failure(self, should_fail: bool) -> None:
        """Set metadata failure for testing."""
        self.should_fail_metadata = should_fail
    
    def set_cleanup_failure(self, should_fail: bool) -> None:
        """Set cleanup failure for testing."""
        self.should_fail_cleanup = should_fail
    
    def clear_failures(self) -> None:
        """Clear all failure modes."""
        self.failure_mode = None
        self.should_fail_validation = False
        self.should_fail_registration = False
        self.should_fail_metadata = False
        self.should_fail_cleanup = False
    
    def reset_tracking(self) -> None:
        """Reset operation tracking."""
        self.operation_count = 0
        self.operations_attempted = []


class MockExternalPlugin(ToolPlugin):
    """
    Mock plugin simulating external package integration for realistic testing.
    
    ### Mock External Plugin Architecture:
    - Simulates real external package plugin behavior
    - Provides realistic dependency management and validation
    - Supports external tool integration patterns
    - Enables comprehensive external plugin testing scenarios
    
    ### Testing Applications:
    - External plugin integration and compatibility testing
    - Real-world plugin dependency and validation testing
    - Plugin ecosystem and package management testing
    - External tool registration and lifecycle testing
    """
    
    def __init__(self, package_name: str = "external_test_package"):
        """
        Initialize mock external plugin.
        
        Args:
            package_name: Name of simulated external package
        """
        self._plugin_name = f"external_{package_name}_plugin"
        self._plugin_version = "1.5.0"
        self._package_name = package_name
        
        # Simulate external package tools
        self._tools = {
            f"external_{package_name}_tool": {
                "class": MockConfigurableTool,
                "spec": ToolSpec(
                    name=f"external_{package_name}_tool",
                    description=f"External tool from {package_name} package",
                    version="1.5.0",
                    tool_type=ToolType.PLUGIN,
                    category=ToolCategory.HYBRID,
                    capabilities=["external_integration", "package_tool", "test_execution"],
                    dependencies=[f"python>=3.12", f"{package_name}>=1.5.0"]
                )
            }
        }
        
        # Simulate realistic external dependencies
        self._dependencies = [
            {"name": "python", "version": ">=3.12", "satisfied": True},
            {"name": package_name, "version": ">=1.5.0", "satisfied": True},
            {"name": "requests", "version": ">=2.25", "satisfied": True},
            {"name": "optional_dep", "version": ">=1.0", "satisfied": False, "required": False}
        ]
        
        # Track operations for testing
        self.registration_count = 0
        self.cleanup_count = 0
        self.validation_count = 0
    
    def get_plugin_name(self) -> str:
        """Get plugin name."""
        return self._plugin_name
    
    def get_plugin_version(self) -> str:
        """Get plugin version."""
        return self._plugin_version
    
    def get_plugin_description(self) -> str:
        """Get plugin description."""
        return f"External plugin from {self._package_name} package"
    
    def get_dependencies(self) -> List[str]:
        """Get plugin dependencies as string list."""
        return [dep["name"] + dep.get("version", "") for dep in self._dependencies if dep.get("required", True)]
    
    def get_plugin_metadata(self) -> Dict[str, Any]:
        """Get comprehensive external plugin metadata."""
        return {
            "name": self._plugin_name,
            "version": self._plugin_version,
            "description": f"External plugin from {self._package_name} package",
            "author": "External Package Team",
            "package": self._package_name,
            "tools": list(self._tools.keys()),
            "dependencies": self._dependencies,
            "capabilities": self.get_supported_capabilities(),
            "external": True,
            "registration_count": self.registration_count,
            "cleanup_count": self.cleanup_count,
            "validation_count": self.validation_count
        }
    
    def get_tool_names(self) -> List[str]:
        """Get list of external tool names."""
        return list(self._tools.keys())
    
    def get_tool_spec(self, tool_name: str) -> Optional[ToolSpec]:
        """Get external tool specification."""
        if tool_name in self._tools:
            return self._tools[tool_name]["spec"]
        return None
    
    def get_tool_class(self, tool_name: str) -> Optional[Type[AbstractTool]]:
        """Get external tool class."""
        if tool_name in self._tools:
            return self._tools[tool_name]["class"]
        return None
    
    def get_supported_capabilities(self) -> List[str]:
        """Get capabilities supported by external tools."""
        capabilities = set()
        for tool_info in self._tools.values():
            capabilities.update(tool_info["spec"].capabilities)
        return list(capabilities)
    
    def validate_dependencies(self) -> bool:
        """Validate external package dependencies."""
        self.validation_count += 1
        
        # Check required dependencies
        for dep in self._dependencies:
            if dep.get("required", True) and not dep.get("satisfied", False):
                return False
        
        return True
    
    def register_tools(self, registry: ToolRegistry) -> None:
        """Register external tools with the registry."""
        self.registration_count += 1
        
        for tool_name, tool_info in self._tools.items():
            # Register external tool
            registry.register_tool_class(tool_name, tool_info["class"], tool_info["spec"])
            
            # Register external tool configuration
            external_config = {
                "external": True,
                "package": self._package_name,
                "timeout": 1200,
                "connection": {
                    "host": "external-service.example.com",
                    "port": 8080,
                    "timeout": 30
                }
            }
            registry.register_configuration(tool_name, external_config)
    
    def cleanup(self) -> None:
        """Cleanup external plugin resources."""
        self.cleanup_count += 1
        # Simulate external resource cleanup
    
    def simulate_dependency_issue(self, dependency_name: str) -> None:
        """Simulate dependency satisfaction issue for testing."""
        for dep in self._dependencies:
            if dep["name"] == dependency_name:
                dep["satisfied"] = False
                break
    
    def resolve_dependency_issue(self, dependency_name: str) -> None:
        """Resolve dependency satisfaction issue."""
        for dep in self._dependencies:
            if dep["name"] == dependency_name:
                dep["satisfied"] = True
                break


def create_mock_plugin_collection() -> Dict[str, ToolPlugin]:
    """
    Create a collection of mock plugins for comprehensive testing.
    
    Returns:
        Dictionary mapping plugin names to mock plugin instances
    """
    return {
        "basic": MockBasicPlugin(),
        "complex": MockComplexPlugin(),
        "failing": MockFailingPlugin(),
        "external": MockExternalPlugin(),
        "external_alt": MockExternalPlugin("alternative_package")
    }


def create_mock_plugin_entry_points() -> List[Dict[str, Any]]:
    """
    Create mock entry point data for plugin discovery testing.
    
    Returns:
        List of entry point dictionaries for mocking
    """
    plugins = create_mock_plugin_collection()
    
    entry_points = []
    for name, plugin in plugins.items():
        entry_points.append({
            "name": name,
            "plugin_class": type(plugin),
            "plugin_instance": plugin
        })
    
    return entry_points