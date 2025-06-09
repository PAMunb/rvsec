"""
DroidMate tool implementation for monitored operations testing.

This module provides integration with the DroidMate Android testing framework,
enabling systematic test input generation and API coverage analysis.
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


class DroidMateTool(ConfigurableTool):
    """
    DroidMate systematic test input generator for monitored operations testing.

    ### Architectural Decisions:
    - Extends ConfigurableTool to leverage standardized configuration management
    - Implements JAR-based execution model for comprehensive testing capabilities
    - Provides sophisticated action and time limit management for controlled exploration
    - Uses Java Virtual Machine execution for cross-platform compatibility
    - Supports comprehensive logging and debugging capabilities for analysis
    - Integrates with rv-android-core infrastructure for error handling and logging

    ### Role in the System:
    - Serves as a comprehensive test input generator for monitored operations testing
    - Provides systematic exploration with configurable action and time limits
    - Enables API coverage analysis and detailed execution trace generation
    - Supports both JCA cryptography detection and generic monitored operations testing
    - Facilitates research-oriented testing with extensive customization options
    - Generates structured output for comprehensive result analysis and debugging

    ### Key Considerations:
    - Uses Java-based execution requiring proper JVM configuration
    - Supports extensive parameter customization for research and development
    - Provides comprehensive logging capabilities for debugging and analysis
    - Handles both instrumented and non-instrumented APK testing scenarios
    - Integrates with output directory management for organized result collection
    - Supports configurable exploration strategies and selector mechanisms

    ### Integration Strategy:
    - Compatible with experiment task execution system for automated workflows
    - Supports configuration inheritance from experiment and variant specifications
    - Enables result collection and analysis through standardized output formats
    - Provides clear extension points for custom exploration and selection strategies
    - Facilitates integration with coverage analysis and API monitoring systems
    - Supports plugin-based architecture for external tool ecosystem integration

    ### Performance and Scalability:
    - Optimized for efficient resource utilization through JVM-based execution
    - Supports configurable timeout and action limit mechanisms
    - Enables parallel execution across multiple APK instances and devices
    - Provides comprehensive memory and performance monitoring capabilities
    - Scales effectively for large-scale research and experiment execution scenarios
    - Adaptable to different APK complexity and exploration requirements
    """

    # Tool specification with comprehensive metadata
    TOOL_SPEC = ToolSpec.create_builtin_spec(
        name="droidmate",
        description="DroidMate-2 systematic test input generator for Android applications",
        category=ToolCategory.SYSTEMATIC,
        capabilities=[
            "systematic_testing",
            "api_coverage_analysis",
            "action_based_exploration",
            "trace_generation",
            "research_oriented_testing",
            "monitored_operations_testing"
        ]
    )

    def __init__(self):
        """
        Initialize the DroidMate tool with default configuration and rv-android-core infrastructure.
        
        ### Infrastructure Integration:
        - Sets up standardized logging with DroidMate-specific context
        - Initializes error handler for comprehensive error management
        - Configures DroidMate-specific parameters and execution settings
        - Establishes integration with monitored operations framework
        """
        super().__init__(
            name="droidmate",
            description="DroidMate-2 systematic test input generator for Android applications",
            process_pattern="java -jar droidmate"
        )

        # Initialize rv-android-core infrastructure components
        self._logging_manager = LoggingManager.get_instance()
        self.logger = self._logging_manager.get_logger(
            "tools.droidmate", 
            {CONTEXT_COMPONENT: "DroidMateTool"}
        )
        self.error_handler = ErrorHandler.get_instance()

        # Default tool configuration
        self.default_config = {
            "action_limit": 100000000,  # Effectively unlimited actions
            "time_limit_millis": 600000,  # 10 minutes
            "device_id": "emulator-5554",
            "output_dir": None,
            "apks_dir": None,
            "log_level": "debug",
            "enable_coverage": True,
            "exploration_strategy": "default",
            "reset_app_after_each_action": False,
            "check_app_is_running_retry_attempts": 3,
            "check_app_is_running_retry_delay": 1000,
            "wait_for_can_reboot_delay": 60000
        }

        self.logger.info("DroidMate tool initialized successfully")

    def configure_tool_specific(self, config: Dict[str, Any]) -> None:
        """
        Configure DroidMate-specific parameters and validate settings.

        Args:
            config: Configuration dictionary with tool-specific parameters

        Raises:
            ValueError: If configuration parameters are invalid
        """
        self.logger.debug("Configuring DroidMate-specific parameters")

        # Action limit configuration
        if 'action_limit' in config:
            action_limit = config['action_limit']
            if not isinstance(action_limit, int) or action_limit < 1:
                raise ValueError("action_limit must be a positive integer")
            self.tool_config['action_limit'] = action_limit

        # Time limit configuration
        if 'time_limit_millis' in config:
            time_limit = config['time_limit_millis']
            if not isinstance(time_limit, int) or time_limit < 1000:
                raise ValueError("time_limit_millis must be at least 1000 (1 second)")
            self.tool_config['time_limit_millis'] = time_limit

        # Device configuration
        if 'device_id' in config:
            self.tool_config['device_id'] = str(config['device_id'])

        # Directory configurations
        if 'output_dir' in config:
            output_dir = config['output_dir']
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            self.tool_config['output_dir'] = output_dir

        if 'apks_dir' in config:
            apks_dir = config['apks_dir']
            if apks_dir and not os.path.exists(apks_dir):
                raise ValueError(f"apks_dir does not exist: {apks_dir}")
            self.tool_config['apks_dir'] = apks_dir

        # Log level configuration
        if 'log_level' in config:
            log_level = config['log_level']
            valid_levels = ['error', 'warn', 'info', 'debug', 'trace']
            if log_level not in valid_levels:
                raise ValueError(f"log_level must be one of: {valid_levels}")
            self.tool_config['log_level'] = log_level

        # Exploration strategy configuration
        if 'exploration_strategy' in config:
            self.tool_config['exploration_strategy'] = str(config['exploration_strategy'])

        # Retry configuration
        if 'check_app_is_running_retry_attempts' in config:
            attempts = config['check_app_is_running_retry_attempts']
            if not isinstance(attempts, int) or attempts < 0:
                raise ValueError("check_app_is_running_retry_attempts must be a non-negative integer")
            self.tool_config['check_app_is_running_retry_attempts'] = attempts

        if 'check_app_is_running_retry_delay' in config:
            delay = config['check_app_is_running_retry_delay']
            if not isinstance(delay, int) or delay < 0:
                raise ValueError("check_app_is_running_retry_delay must be a non-negative integer")
            self.tool_config['check_app_is_running_retry_delay'] = delay

        if 'wait_for_can_reboot_delay' in config:
            delay = config['wait_for_can_reboot_delay']
            if not isinstance(delay, int) or delay < 0:
                raise ValueError("wait_for_can_reboot_delay must be a non-negative integer")
            self.tool_config['wait_for_can_reboot_delay'] = delay

        # Boolean flags
        boolean_flags = ['enable_coverage', 'reset_app_after_each_action']
        for flag in boolean_flags:
            if flag in config:
                self.tool_config[flag] = bool(config[flag])

        self.logger.info("DroidMate tool configuration completed successfully")

    def build_command_args(self, app: App, output_file: str, task_config: Dict[str, Any]) -> List[str]:
        """
        Build command arguments for DroidMate execution.

        Args:
            app: Application instance containing APK information
            output_file: Path to output trace file
            task_config: Task-specific configuration parameters

        Returns:
            List of command arguments for tool execution
        """
        try:
            self.logger.debug(f"Building DroidMate command arguments for app: {app.name}")

            # Get DroidMate JAR path
            tools_dir = os.environ.get('TOOLS_DIR', '/tools')
            droidmate_jar = os.path.join(tools_dir, 'droidmate', 'droidmate-2-X.X.X-all.jar')

            # Get directories
            output_dir = self.tool_config.get('output_dir') or os.path.join(tools_dir, 'droidmate', 'temp')
            apks_dir = self.tool_config.get('apks_dir') or os.path.dirname(app.path)

            # Calculate timeout
            timeout_seconds = task_config.get('timeout', 600)
            timeout_millis = self.tool_config.get('time_limit_millis', timeout_seconds * 1000)

            # Build comprehensive argument list
            args = [
                "-jar",
                droidmate_jar,
                f"--Exploration-apkNames={app.name}",
                f"--Exploration-apksDir={apks_dir}",
                f"--Output-outputDir={output_dir}",
                f"--Selectors-timeLimit={timeout_millis}",
                f"--Selectors-actionLimit={self.tool_config['action_limit']}",
                f"--Core-logLevel={self.tool_config['log_level']}"
            ]

            # Add device configuration
            if self.tool_config.get('device_id'):
                args.append(f"--Selectors-deviceSerialNumber={self.tool_config['device_id']}")

            # Add retry configuration
            if self.tool_config.get('check_app_is_running_retry_attempts') != 3:
                args.append(f"--Selectors-checkAppIsRunningRetryAttempts={self.tool_config['check_app_is_running_retry_attempts']}")

            if self.tool_config.get('check_app_is_running_retry_delay') != 1000:
                args.append(f"--Selectors-checkAppIsRunningRetryDelay={self.tool_config['check_app_is_running_retry_delay']}")

            if self.tool_config.get('wait_for_can_reboot_delay') != 60000:
                args.append(f"--Selectors-waitForCanRebootDelay={self.tool_config['wait_for_can_reboot_delay']}")

            # Add boolean flags
            if self.tool_config.get('reset_app_after_each_action'):
                args.append("--Selectors-resetEveryNthExplorationForward=1")

            self.logger.debug(f"DroidMate command arguments: {args}")
            return args

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "build_command_args",
                    "app_name": app.name,
                    "tool": "droidmate",
                    "component": "DroidMateTool"
                }
            )
            raise

    def validate_execution_environment(self, app: App) -> bool:
        """
        Validate that the execution environment is properly configured for DroidMate.

        Args:
            app: Application instance to validate against

        Returns:
            True if environment is valid, False otherwise
        """
        try:
            self.logger.debug("Validating DroidMate execution environment")

            # Check if Java is available
            try:
                java_check = Command("java", ["-version"], timeout=10)
                result = java_check.invoke()
                if result.returncode != 0:
                    self.logger.error("Java is not available or not responding")
                    return False
            except Exception as e:
                self.logger.error(f"Java validation failed: {str(e)}")
                return False

            # Validate DroidMate JAR file
            tools_dir = os.environ.get('TOOLS_DIR', '/tools')
            droidmate_jar = os.path.join(tools_dir, 'droidmate', 'droidmate-2-X.X.X-all.jar')

            if not os.path.exists(droidmate_jar):
                self.logger.error(f"DroidMate JAR not found: {droidmate_jar}")
                return False

            # Validate APK file
            if not os.path.exists(app.path):
                self.logger.error(f"APK file not found: {app.path}")
                return False

            # Validate output directory
            output_dir = self.tool_config.get('output_dir') or os.path.join(tools_dir, 'droidmate', 'temp')
            os.makedirs(output_dir, exist_ok=True)

            self.logger.info("DroidMate execution environment validation successful")
            return True

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "validate_execution_environment",
                    "app_name": app.name,
                    "tool": "droidmate",
                    "component": "DroidMateTool"
                }
            )
            return False

    def get_execution_command(self, app: App, output_file: str, task_config: Dict[str, Any]) -> Command:
        """
        Create the execution command for DroidMate tool.

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

            # Create command with comprehensive configuration
            command = Command(
                executable="java",
                args=args,
                timeout=execution_timeout
            )

            self.logger.info(f"DroidMate execution command created for app: {app.name}")
            return command

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "get_execution_command",
                    "app_name": app.name,
                    "tool": "droidmate",
                    "component": "DroidMateTool"
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
            self.logger.debug(f"Processing DroidMate execution result for app: {app.name}")

            # Base result information
            execution_result = {
                "tool": "droidmate",
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
                    "java_execution": True,
                    "monitored_operations_detected": self._analyze_trace_for_monitored_operations(output_file)
                })
            else:
                execution_result.update({
                    "exploration_completed": False,
                    "timeout_occurred": result.returncode == 124,
                    "error_details": getattr(result, 'stderr', ''),
                    "monitored_operations_detected": 0
                })

            # Extract additional metrics from trace file
            if output_file and os.path.exists(output_file):
                execution_result.update(self._extract_trace_metrics(output_file))

            self.logger.info(f"DroidMate execution result processed for app: {app.name}")
            return execution_result

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "process_execution_result",
                    "app_name": app.name,
                    "tool": "droidmate",
                    "component": "DroidMateTool"
                }
            )
            
            return {
                "tool": "droidmate",
                "app_name": app.name,
                "success": False,
                "error": f"Result processing failed: {str(e)}"
            }

    def _analyze_trace_for_monitored_operations(self, trace_file: str) -> int:
        """Analyze trace file for monitored operations occurrences."""
        try:
            if not os.path.exists(trace_file):
                return 0
            monitored_count = 0
            with open(trace_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if any(keyword in line.lower() for keyword in [
                        'cipher', 'encrypt', 'decrypt', 'hash', 'signature',
                        'monitored', 'violation', 'specification'
                    ]):
                        monitored_count += 1
            return monitored_count
        except Exception as e:
            self.logger.warning(f"Failed to analyze trace file: {str(e)}")
            return 0

    def _extract_trace_metrics(self, trace_file: str) -> Dict[str, Any]:
        """Extract additional metrics from the trace file."""
        try:
            if not os.path.exists(trace_file):
                return {}
            file_size = os.path.getsize(trace_file)
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
        """Get comprehensive information about the DroidMate tool."""
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
            "requires_java": True,
            "monitored_operations_support": True
        }

    def __str__(self) -> str:
        """String representation of the DroidMate tool."""
        return f"DroidMateTool(name='{self.name}', configured={bool(self.tool_config)})"

    def __repr__(self) -> str:
        """Detailed string representation of the DroidMate tool."""
        return (f"DroidMateTool(name='{self.name}', description='{self.description}', "
                f"config_keys={list(self.tool_config.keys())})")