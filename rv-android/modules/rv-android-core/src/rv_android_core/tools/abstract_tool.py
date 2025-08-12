"""
Abstract base class for all testing tools in the RV-Android framework.

This module defines the core contract and template method pattern for 
monitored operations testing tools.
"""

import os
from abc import ABC, abstractmethod
from typing import Dict, Any

from rv_android_core.domain.app import App
from rv_android_core.commands.circuit_breaker import CommandCircuitBreaker
from rv_android_core.commands.command import Command
from rv_android_core.commands.command_result import CommandResult
from rv_android_core.domain.task import Task
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import (
    RVCommandTimeoutError, RVToolTimeoutError, RVToolExecutionError,
    CircuitBreakerOpenError
)
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT, CONTEXT_TOOL_NAME
from rv_android_core.util.logging.manager import LoggingManager


class AbstractTool(ABC):
    """
    Abstract base class defining the core contract for monitored operations testing tools.

    ### Architectural Decisions:
    - Implements a standardized interface for test automation tool integration
    - Defines a template method pattern for tool execution workflow
    - Provides consistent mechanism for tool-specific logic implementation
    - Supports flexible extension and customization of testing strategies
    - Integrates with rv-android-core infrastructure for error handling and logging

    ### Role in the System:
    - Serves as the foundational abstraction for all testing tools
    - Defines uniform execution workflow for different testing approaches
    - Enables seamless integration of diverse monitored operations testing strategies
    - Provides standardized mechanism for process management and cleanup
    - Acts as critical component in experiment tool orchestration

    ### Key Considerations:
    - Enforces consistent execution contract for all tool implementations
    - Manages tool-specific process termination and resource cleanup
    - Supports flexible tool initialization and configuration patterns
    - Provides template for implementing tool-specific execution logic
    - Ensures proper integration with error handling and logging infrastructure

    ### Integration Strategy:
    - Compatible with multiple testing tool implementations
    - Supports dynamic tool registration and execution via plugin system
    - Enables dependency injection and tool composition patterns
    - Provides clear extension point for new monitored operations testing tools
    - Facilitates tool-agnostic experiment design and execution

    ### Performance and Scalability:
    - Designed for lightweight tool abstraction with minimal overhead
    - Minimizes performance impact in tool execution and management
    - Supports diverse testing tool implementations and complexity levels
    - Enables efficient process termination and resource cleanup
    - Adaptable to different monitored operations testing scale requirements
    """

    def __init__(self, name: str, description: str, process_pattern: str):
        """
        Initialize the abstract tool with basic properties.

        Args:
            name: Unique tool identifier
            description: Human-readable tool description
            process_pattern: Pattern for identifying related processes to cleanup
        """
        self.name = name
        self.description = description
        self.process_pattern = process_pattern

        # Set up standardized logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            f"rv_tools.builtin.{name}",
            {
                CONTEXT_COMPONENT: f"{name.title()}Tool",
                CONTEXT_TOOL_NAME: name
            }
        )

        # Initialize error handler
        self.error_handler = ErrorHandler.get_instance()

        # Initialize circuit breaker for command resilience
        self.circuit_breaker = CommandCircuitBreaker()

        super().__init__()

    @classmethod
    @abstractmethod
    def get_variants(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get available variants for this tool.
        
        Every tool must provide at least a 'default' variant configuration.
        Variants define tool-specific parameter sets that can be referenced
        by name in experiment configurations.
        
        ### Architectural Overview:
        This method enables the variant system by providing predefined configurations
        that can be referenced by name in experiment specifications. Each variant
        represents a complete configuration for the tool with specific parameters.
        
        ### Implementation Requirements:
        - Must include at least a 'default' variant
        - Variant names should be descriptive and meaningful
        - Parameters should be complete for tool execution
        - Avoid complex nested structures for simplicity
        
        Returns:
            Dictionary mapping variant names to configuration parameters
            
        Example:
            {
                "default": {"policy": "dfs_naive", "timeout": 300},
                "greedy": {"policy": "dfs_greedy", "count": 5000, "timeout": 600}
            }
        """
        pass
    
    @classmethod
    def register_variants(cls, registry) -> None:
        """
        Register all variants for this tool with the registry.
        
        This method is called automatically during tool registration
        to populate the registry with available variants. Tools should
        not override this method unless custom registration logic is required.
        
        ### Automatic Registration Process:
        1. Gets tool specification from get_tool_spec()
        2. Retrieves variants from get_variants()
        3. Registers each variant with the registry
        4. Provides error handling for registration failures
        
        Args:
            registry: ToolRegistry instance to register variants with
            
        Raises:
            ConfigurationError: If variant registration fails
        """
        tool_spec = cls.get_tool_spec()
        tool_name = tool_spec.name
        
        try:
            for variant_name, config in cls.get_variants().items():
                registry.register_variant(tool_name, variant_name, config)
        except Exception as e:
            from rv_android_core.util.error.exceptions import ConfigurationError
            raise ConfigurationError(f"Failed to register variants for {tool_name}: {e}")
    
    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure tool with resolved variant parameters.
        
        This method receives configuration resolved from variant registration
        and experiment parameters. Implementation must prepare the tool for
        execution with the provided configuration.
        
        ### Configuration Resolution Flow:
        1. ToolFactory resolves variant configuration from registry
        2. Applies parameter overrides from experiment configuration
        3. Calls this method with final configuration dictionary
        4. Tool prepares internal state for execution
        
        ### Implementation Guidelines:
        - Store configuration in instance variables for execution
        - Validate required parameters and provide clear error messages
        - Prepare any tool-specific setup required for execution
        - Do not perform heavy operations - defer to execution phase
        
        Args:
            config: Configuration dictionary with tool-specific parameters
            
        Raises:
            ConfigurationError: If configuration is invalid or incomplete
        """
        pass

    @classmethod
    @abstractmethod
    def get_tool_spec(cls):
        """
        Get tool specification for registration.
        
        This method must be implemented by all tools to provide
        specification information for registry registration.
        
        Returns:
            ToolSpec instance with tool metadata
        """
        pass
    
    @abstractmethod
    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
        """
        Execute tool-specific testing logic.
        
        This is the main extension point that every tool implementation must provide.
        It should contain the core testing logic specific to each tool.
        
        Args:
            task: Task configuration and context (can be Task or task_model.Task)
            app: Application under test
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        pass

    def execute(self, task: Task, app: App) -> None:
        """
        Execute the tool using template method pattern with unified error handling.
        
        This method implements the standard execution workflow that delegates
        to the abstract method for tool-specific logic, then performs cleanup.
        Provides centralized timeout and error handling for all tools.
        
        ### Execution Workflow:
        1. Log tool execution start
        2. Delegate to tool-specific logic implementation
        3. Handle command timeouts and convert to tool timeouts
        4. Perform process cleanup and resource management
        5. Handle any errors that occur during execution
        6. Log success only if no exceptions occurred
        
        Args:
            task: Task configuration and context
            app: Application under test
        """
        execution_successful = False
        
        try:
            self.logger.info(f"Executing monitored operations tool: {self.name}")
            self.logger.debug(f"Tool description: {self.description}")

            # Execute tool-specific logic
            self.execute_tool_specific_logic(task, app)

            # Cleanup related processes
            self.kill_related_processes(self.process_pattern)

            # Mark execution as successful only if we reach this point
            execution_successful = True
            self.logger.info(f"Tool {self.name} execution completed successfully")

        except RVCommandTimeoutError as e:
            # Convert command timeout to tool timeout - this is expected behavior
            timeout_msg = f"{self.name} execution timed out after {e.timeout_seconds} seconds"
            self.logger.info(f"Tool timeout detected: {timeout_msg}")
            
            # Raise tool timeout exception (handled gracefully by error handler)
            raise RVToolTimeoutError(
                timeout_msg,
                tool_name=self.name,
                timeout_seconds=e.timeout_seconds,
                cause=e
            )

        except Exception as e:
            self.logger.error(f"Error executing tool {self.name}: {str(e)}", exc_info=True)

            # Handle error using centralized error handler
            self.error_handler.handle_error(
                e,
                context={
                    "tool_name": self.name,
                    "app_name": app.name if app else "unknown",
                    "task_id": getattr(task, 'id', 'unknown')
                }
            )
            raise

    def _execute_and_check_command(self, command: Command, stdout=None, stderr=None, stdin=None) -> CommandResult:
        """
        Execute command with circuit breaker protection and unified error handling.
        
        This method centralizes all command execution logic providing consistent
        behavior across all tools. It integrates circuit breaker pattern for
        resilience against consistently failing commands while maintaining
        existing timeout and error handling behavior.
        
        ### Command Execution Strategy:
        1. Check circuit breaker state for command execution permission
        2. Execute command using Command infrastructure with timeout handling
        3. Handle command timeouts (do not count as circuit breaker failures)
        4. Check result.is_failure() and record circuit breaker failures
        5. Record circuit breaker success for successful executions
        6. Provide detailed error context for debugging and trace file logging
        
        Args:
            command: Command instance to execute
            stdout: Where to redirect standard output (default: PIPE)
            stderr: Where to redirect standard error (default: PIPE)
            stdin: Input to pass to the command (default: None)
            
        Returns:
            CommandResult on successful execution
            
        Raises:
            CircuitBreakerOpenError: When circuit breaker blocks command execution
            RVToolTimeoutError: When command times out (converted from RVCommandTimeoutError)
            RVToolExecutionError: When command fails with non-zero exit code
        """
        try:
            # Check circuit breaker before execution
            self.circuit_breaker.is_execution_allowed(command)
            
            # Execute command - may raise RVCommandTimeoutError
            result = command.invoke(stdout=stdout, stderr=stderr, stdin=stdin)
            
            # Check for command failure
            if result.is_failure():
                # Record failure in circuit breaker
                self.circuit_breaker.record_failure(command)
                
                error_msg = f"{self.name} command failed with exit code {result.code}"
                if result.has_error_output():
                    error_msg += f". Error output: {result.get_stderr_text()}"
                
                # Log error details for debugging
                self.logger.error(f"Command execution failed: {error_msg}")
                
                raise RVToolExecutionError(
                    error_msg,
                    tool_name=self.name,
                    cause=None
                )
            
            # Record success in circuit breaker
            self.circuit_breaker.record_success(command)
            
            return result
            
        except RVCommandTimeoutError as e:
            # Timeout is expected behavior - do not record as circuit breaker failure
            timeout_msg = f"{self.name} execution timed out after {e.timeout_seconds} seconds"
            self.logger.info(f"Tool timeout detected during command execution: {timeout_msg}")
            
            raise RVToolTimeoutError(
                timeout_msg,
                tool_name=self.name,
                timeout_seconds=e.timeout_seconds,
                cause=e
            )
        
        except CircuitBreakerOpenError:
            # Circuit breaker blocked execution - re-raise as-is
            raise

    def kill_related_processes(self, process_pattern: str) -> None:
        """
        Terminate processes related to this tool for cleanup.
        
        This method identifies and kills processes that match the given pattern
        to ensure clean tool termination and prevent resource leaks.
        
        Args:
            process_pattern: Pattern to match processes for termination
        """
        if not process_pattern:
            self.logger.debug("No process pattern specified, skipping process cleanup")
            return

        try:
            self.logger.debug(f"Cleaning up processes matching pattern: {process_pattern}")

            # Get list of processes matching the pattern
            get_processes_cmd = Command('adb', [
                'shell',
                'ps',
                '|',
                'grep',
                process_pattern
            ])

            get_processes_result = get_processes_cmd.invoke()

            if not get_processes_result.stdout:
                self.logger.debug("No matching processes found for cleanup")
                return

            # Kill each matching process
            killed_count = 0
            for line in get_processes_result.stdout.decode('ascii').split(os.linesep):
                line = line.strip()
                if line:
                    tokens = line.split()
                    if len(tokens) >= 2:
                        process_id = tokens[1]
                        try:
                            kill_process_cmd = Command('adb', [
                                'shell',
                                'kill',
                                process_id
                            ])
                            kill_process_cmd.invoke()
                            killed_count += 1
                            self.logger.debug(f"Killed process {process_id}")
                        except Exception as e:
                            self.logger.warning(f"Failed to kill process {process_id}: {str(e)}")

            if killed_count > 0:
                self.logger.info(f"Cleaned up {killed_count} related processes")

        except Exception as e:
            self.logger.warning(f"Error during process cleanup: {str(e)}")
            # Don't raise here as cleanup errors shouldn't fail the main execution

    def get_tool_info(self) -> dict:
        """
        Get tool information and metadata.
        
        Returns:
            Dictionary containing tool name, description, and process pattern
        """
        return {
            "name": self.name,
            "description": self.description,
            "process_pattern": self.process_pattern
        }

    def __str__(self) -> str:
        """String representation of the tool."""
        return f"{self.__class__.__name__}(name='{self.name}', description='{self.description}')"

    def __repr__(self) -> str:
        """Detailed string representation of the tool."""
        return (f"{self.__class__.__name__}(name='{self.name}', "
                f"description='{self.description}', process_pattern='{self.process_pattern}')")
