"""
Ares tool implementation for monitored operations testing.

This module provides integration with the ARES Android testing framework,
enabling systematic UI exploration and testing of monitored operations.
"""

import os
from typing import Dict, Any, Optional, List

from rv_android_core.app import App
from rv_android_core.commands.command import Command
from rv_android_core.tools.configurable_tool import ConfigurableTool
from rv_android_core.tools.tool_spec import ToolSpec, ToolType, ToolCategory
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT


class AresTool(ConfigurableTool):
    """
    ARES (Android Reverse Engineering Suite) tool for systematic UI exploration.

    ### Architectural Decisions:
    - Extends ConfigurableTool to leverage standardized configuration management
    - Implements Docker-based execution model for isolated and reproducible testing
    - Provides comprehensive timeout and resource management capabilities
    - Uses shell script execution pattern for external tool integration
    - Supports both instrumented and non-instrumented APK testing scenarios
    - Integrates with rv-android-core infrastructure for error handling and logging

    ### Role in the System:
    - Serves as a systematic UI exploration tool for monitored operations testing
    - Provides Docker-based isolated execution environment for consistent results
    - Enables automatic GUI testing with configurable exploration strategies
    - Supports both JCA cryptography detection and generic monitored operations
    - Facilitates comparative analysis with other testing tools in the framework
    - Generates structured trace files for comprehensive result analysis

    ### Key Considerations:
    - Requires Docker environment for proper execution isolation
    - Uses external shell scripts for tool invocation and parameter management
    - Supports configurable timeout mechanisms for long-running exploration sessions
    - Provides comprehensive logging for debugging and analysis purposes
    - Handles both successful execution and error scenarios gracefully
    - Integrates with experiment framework for batch execution and result collection

    ### Integration Strategy:
    - Compatible with experiment task execution system for automated workflows
    - Supports configuration inheritance from experiment and variant specifications
    - Enables result collection and analysis through standardized trace file format
    - Provides clear extension points for custom exploration strategies
    - Facilitates integration with coverage analysis and result processing systems
    - Supports plugin-based architecture for external tool ecosystem integration

    ### Performance and Scalability:
    - Optimized for efficient resource utilization through Docker containerization
    - Supports configurable timeout mechanisms to prevent resource exhaustion
    - Enables parallel execution across multiple device instances
    - Provides memory and CPU usage monitoring capabilities
    - Scales effectively for large-scale experiment execution scenarios
    - Adaptable to different APK complexity and exploration requirements
    """

    # Tool specification with comprehensive metadata
    TOOL_SPEC = ToolSpec.create_builtin_spec(
        name="ares",
        description="ARES Android testing framework for systematic UI exploration",
        category=ToolCategory.SYSTEMATIC,
        capabilities=[
            "ui_exploration",
            "systematic_testing", 
            "docker_execution",
            "trace_generation",
            "monitored_operations_testing"
        ]
    )

    def __init__(self):
        """
        Initialize the ARES tool with default configuration and rv-android-core infrastructure.
        
        ### Infrastructure Integration:
        - Sets up standardized logging with ARES-specific context
        - Initializes error handler for comprehensive error management
        - Configures ARES-specific parameters and Docker execution settings
        - Establishes integration with monitored operations framework
        """
        super().__init__(
            name="ares",
            description="ARES Android testing framework for systematic UI exploration",
            process_pattern="run_ares.sh"
        )

        # Initialize rv-android-core infrastructure components
        self._logging_manager = LoggingManager.get_instance()
        self.logger = self._logging_manager.get_logger(
            "rv_tools.builtin.ares",
            {CONTEXT_COMPONENT: "AresTool"}
        )
        self.error_handler = ErrorHandler.get_instance()

        # Default tool configuration
        self.default_config = {
            "timeout_minutes": 10,
            "device_id": "emulator-5554",
            "docker_image": "ares-testing",
            "exploration_strategy": "systematic",
            "max_depth": 10,
            "enable_screenshots": True,
            "output_format": "trace",
            "debug_mode": False,
            "resource_monitoring": True
        }

        self.logger.info("ARES tool initialized successfully")

    def configure_tool_specific(self, config: Dict[str, Any]) -> None:
        """
        Configure ARES-specific parameters and validate settings.

        Args:
            config: Configuration dictionary with tool-specific parameters

        Raises:
            ValueError: If configuration parameters are invalid
        """
        self.logger.debug("Configuring ARES-specific parameters")

        # Timeout configuration
        if 'timeout_minutes' in config:
            timeout = config['timeout_minutes']
            if not isinstance(timeout, int) or timeout < 1:
                raise ValueError("timeout_minutes must be a positive integer")
            self.tool_config['timeout_minutes'] = timeout

        # Device configuration
        if 'device_id' in config:
            self.tool_config['device_id'] = str(config['device_id'])

        # Docker configuration
        if 'docker_image' in config:
            self.tool_config['docker_image'] = str(config['docker_image'])

        # Exploration strategy
        if 'exploration_strategy' in config:
            strategy = config['exploration_strategy']
            valid_strategies = ['systematic', 'random', 'hybrid']
            if strategy not in valid_strategies:
                raise ValueError(f"exploration_strategy must be one of: {valid_strategies}")
            self.tool_config['exploration_strategy'] = strategy

        # Maximum exploration depth
        if 'max_depth' in config:
            depth = config['max_depth']
            if not isinstance(depth, int) or depth < 1:
                raise ValueError("max_depth must be a positive integer")
            self.tool_config['max_depth'] = depth

        # Boolean flags
        for flag in ['enable_screenshots', 'debug_mode', 'resource_monitoring']:
            if flag in config:
                self.tool_config[flag] = bool(config[flag])

        # Output format validation
        if 'output_format' in config:
            format_type = config['output_format']
            valid_formats = ['trace', 'json', 'xml']
            if format_type not in valid_formats:
                raise ValueError(f"output_format must be one of: {valid_formats}")
            self.tool_config['output_format'] = format_type

        self.logger.info("ARES tool configuration completed successfully")

    def build_command_args(self, app: App, output_file: str, task_config: Dict[str, Any]) -> List[str]:
        """
        Build command arguments for ARES execution.

        Args:
            app: Application instance containing APK information
            output_file: Path to output trace file
            task_config: Task-specific configuration parameters

        Returns:
            List of command arguments for tool execution
        """
        try:
            self.logger.debug(f"Building ARES command arguments for app: {app.name}")

            # Extract timeout from task configuration
            timeout_seconds = task_config.get('timeout', 600)  # Default 10 minutes
            timeout_minutes = max(1, int(timeout_seconds / 60))

            # Get tool directory for execution context
            tools_dir = os.environ.get('TOOLS_DIR', '/tools')
            ares_dir = os.path.join(tools_dir, 'ares')

            # Build comprehensive argument list
            args = [
                app.path,                                    # APK file path
                self.tool_config['device_id'],              # Target device
                str(timeout_minutes),                        # Execution timeout
                ares_dir,                                   # Tool directory
                self.tool_config['exploration_strategy'],    # Exploration strategy
                str(self.tool_config['max_depth']),         # Maximum depth
                self.tool_config['output_format']           # Output format
            ]

            # Add optional flags
            if self.tool_config['enable_screenshots']:
                args.append('--screenshots')

            if self.tool_config['debug_mode']:
                args.append('--debug')

            if self.tool_config['resource_monitoring']:
                args.append('--monitor-resources')

            self.logger.debug(f"ARES command arguments: {args}")
            return args

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "build_command_args",
                    "app_name": app.name,
                    "tool": "ares",
                    "component": "AresTool"
                }
            )
            raise

    def validate_execution_environment(self, app: App) -> bool:
        """
        Validate that the execution environment is properly configured for ARES.

        Args:
            app: Application instance to validate against

        Returns:
            True if environment is valid, False otherwise
        """
        try:
            self.logger.debug("Validating ARES execution environment")

            # Check if Docker is available
            try:
                docker_check = Command("docker", ["--version"], timeout=10)
                result = docker_check.invoke()
                if result.returncode != 0:
                    self.logger.error("Docker is not available or not responding")
                    return False
            except Exception as e:
                self.logger.error(f"Docker validation failed: {str(e)}")
                return False

            # Validate ARES directory structure
            tools_dir = os.environ.get('TOOLS_DIR', '/tools')
            ares_dir = os.path.join(tools_dir, 'ares')
            ares_script = os.path.join(ares_dir, 'run_ares.sh')

            if not os.path.exists(ares_dir):
                self.logger.error(f"ARES directory not found: {ares_dir}")
                return False

            if not os.path.exists(ares_script):
                self.logger.error(f"ARES execution script not found: {ares_script}")
                return False

            if not os.access(ares_script, os.X_OK):
                self.logger.error(f"ARES script is not executable: {ares_script}")
                return False

            # Validate APK file
            if not os.path.exists(app.path):
                self.logger.error(f"APK file not found: {app.path}")
                return False

            self.logger.info("ARES execution environment validation successful")
            return True

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "validate_execution_environment",
                    "app_name": app.name,
                    "tool": "ares",
                    "component": "AresTool"
                }
            )
            return False

    def get_execution_command(self, app: App, output_file: str, task_config: Dict[str, Any]) -> Command:
        """
        Create the execution command for ARES tool.

        Args:
            app: Application instance
            output_file: Path to output trace file
            task_config: Task-specific configuration

        Returns:
            Configured Command instance for execution
        """
        try:
            # Build command arguments
            args = self.build_command_args(app, output_file, task_config)
            
            # Calculate timeout with buffer
            timeout_seconds = task_config.get('timeout', 600)
            execution_timeout = timeout_seconds + 60  # Add 60 second buffer

            # Get ARES script path
            tools_dir = os.environ.get('TOOLS_DIR', '/tools')
            ares_script = os.path.join(tools_dir, 'ares', 'run_ares.sh')

            # Create command with comprehensive configuration
            command = Command(
                executable=ares_script,
                args=args,
                timeout=execution_timeout,
                working_directory=os.path.dirname(ares_script)
            )

            self.logger.info(f"ARES execution command created for app: {app.name}")
            return command

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "get_execution_command",
                    "app_name": app.name,
                    "tool": "ares",
                    "component": "AresTool"
                }
            )
            raise

    def process_execution_result(self, result, app: App, output_file: str) -> Dict[str, Any]:
        """
        Process the execution result and extract relevant metrics.

        Args:
            result: Command execution result
            app: Application instance
            output_file: Path to output trace file

        Returns:
            Dictionary containing execution metrics and status information
        """
        try:
            self.logger.debug(f"Processing ARES execution result for app: {app.name}")

            # Base result information
            execution_result = {
                "tool": "ares",
                "app_name": app.name,
                "execution_time": getattr(result, 'execution_time', 0),
                "return_code": result.returncode,
                "success": result.returncode == 0,
                "output_file": output_file,
                "trace_generated": os.path.exists(output_file) if output_file else False
            }

            # Add tool-specific metrics
            if result.returncode == 0:
                execution_result.update({
                    "exploration_completed": True,
                    "timeout_occurred": False,
                    "docker_execution": True,
                    "monitored_operations_detected": self._analyze_trace_for_monitored_operations(output_file)
                })
            else:
                execution_result.update({
                    "exploration_completed": False,
                    "timeout_occurred": result.returncode == 124,  # Standard timeout return code
                    "error_details": getattr(result, 'stderr', ''),
                    "monitored_operations_detected": 0
                })

            # Extract additional metrics from trace file
            if output_file and os.path.exists(output_file):
                execution_result.update(self._extract_trace_metrics(output_file))

            self.logger.info(f"ARES execution result processed for app: {app.name}")
            return execution_result

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "process_execution_result",
                    "app_name": app.name,
                    "tool": "ares",
                    "component": "AresTool"
                }
            )
            
            # Return basic error result
            return {
                "tool": "ares",
                "app_name": app.name,
                "success": False,
                "error": f"Result processing failed: {str(e)}"
            }

    def _analyze_trace_for_monitored_operations(self, trace_file: str) -> int:
        """
        Analyze trace file for monitored operations occurrences.

        Args:
            trace_file: Path to the trace file

        Returns:
            Number of monitored operations detected
        """
        try:
            if not os.path.exists(trace_file):
                return 0

            # Simple analysis - count lines that might indicate monitored operations
            # This is a basic implementation that should be enhanced based on actual trace format
            monitored_count = 0
            with open(trace_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    # Look for patterns that indicate monitored operations
                    if any(keyword in line.lower() for keyword in [
                        'cipher', 'encrypt', 'decrypt', 'hash', 'signature',
                        'monitored', 'violation', 'specification'
                    ]):
                        monitored_count += 1

            return monitored_count

        except Exception as e:
            self.logger.warning(f"Failed to analyze trace file for monitored operations: {str(e)}")
            return 0

    def _extract_trace_metrics(self, trace_file: str) -> Dict[str, Any]:
        """
        Extract additional metrics from the trace file.

        Args:
            trace_file: Path to the trace file

        Returns:
            Dictionary containing trace-based metrics
        """
        try:
            if not os.path.exists(trace_file):
                return {}

            # Get basic file information
            file_size = os.path.getsize(trace_file)
            
            # Count lines in trace file
            line_count = 0
            with open(trace_file, 'r', encoding='utf-8', errors='ignore') as f:
                line_count = sum(1 for _ in f)

            return {
                "trace_file_size": file_size,
                "trace_line_count": line_count,
                "trace_file_exists": True
            }

        except Exception as e:
            self.logger.warning(f"Failed to extract trace metrics: {str(e)}")
            return {"trace_file_exists": False}

    def get_tool_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about the ARES tool.

        Returns:
            Dictionary containing tool metadata and configuration
        """
        return {
            "name": self.name,
            "description": self.description,
            "type": "gui_testing",
            "category": "testing",
            "version": "1.0.0",
            "capabilities": self.TOOL_SPEC.capabilities,
            "supported_platforms": self.TOOL_SPEC.supported_platforms,
            "resource_requirements": self.TOOL_SPEC.resource_requirements,
            "configuration": dict(self.tool_config),
            "execution_pattern": self.process_pattern,
            "requires_docker": True,
            "monitored_operations_support": True
        }

    def __str__(self) -> str:
        """String representation of the ARES tool."""
        return f"AresTool(name='{self.name}', configured={bool(self.tool_config)})"

    def __repr__(self) -> str:
        """Detailed string representation of the ARES tool."""
        return (f"AresTool(name='{self.name}', description='{self.description}', "
                f"config_keys={list(self.tool_config.keys())})")