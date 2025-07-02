"""
DroidBot tool implementation for monitored operations testing.

This module provides integration with the DroidBot Android testing framework,
enabling lightweight test input generation and UI transition graph construction.
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


class DroidBotTool(ConfigurableTool):
    """
    DroidBot lightweight test input generator for monitored operations testing.

    ### Architectural Decisions:
    - Extends ConfigurableTool to leverage standardized configuration management
    - Implements policy-based exploration strategies for systematic testing coverage
    - Provides comprehensive event generation and UI transition graph construction
    - Uses direct binary execution model for efficient resource utilization
    - Supports both guided and random exploration policies with configurable parameters
    - Integrates with rv-android-core infrastructure for error handling and logging

    ### Role in the System:
    - Serves as a lightweight and efficient UI exploration tool for monitored operations
    - Provides policy-based exploration strategies for comprehensive coverage analysis
    - Enables rapid test input generation with configurable event counts and timeouts
    - Supports both JCA cryptography detection and generic monitored operations testing
    - Facilitates UI transition graph construction for structural analysis of applications
    - Generates detailed trace files for comprehensive result analysis and debugging

    ### Key Considerations:
    - Uses direct binary execution for minimal overhead and maximum performance
    - Supports multiple exploration policies including DFS, BFS, and greedy strategies
    - Provides configurable event generation with count limits and timeout mechanisms
    - Handles both emulator and real device execution environments
    - Integrates with Android Debug Bridge (ADB) for device communication
    - Supports UI element filtering and ad-blocking for focused testing

    ### Integration Strategy:
    - Compatible with experiment task execution system for automated workflows
    - Supports configuration inheritance from experiment and variant specifications
    - Enables result collection and analysis through standardized trace file format
    - Provides clear extension points for custom exploration policies
    - Facilitates integration with coverage analysis and UI pattern recognition systems
    - Supports plugin-based architecture for external tool ecosystem integration

    ### Performance and Scalability:
    - Optimized for efficient resource utilization with minimal memory footprint
    - Supports configurable timeout mechanisms to prevent resource exhaustion
    - Enables parallel execution across multiple device instances and applications
    - Provides event generation rate control for performance tuning
    - Scales effectively for large-scale experiment execution scenarios
    - Adaptable to different APK complexity and exploration requirements
    """

    # Tool specification with comprehensive metadata
    TOOL_SPEC = ToolSpec.create_builtin_spec(
        name="droidbot",
        description="DroidBot lightweight test input generator for Android applications",
        category=ToolCategory.MODEL_BASED,
        capabilities=[
            "ui_exploration",
            "event_generation",
            "transition_graph_construction",
            "policy_based_testing",
            "trace_generation",
            "monitored_operations_testing"
        ]
    )

    def __init__(self):
        """
        Initialize the DroidBot tool with default configuration and rv-android-core infrastructure.
        
        ### Infrastructure Integration:
        - Sets up standardized logging with DroidBot-specific context
        - Initializes error handler for comprehensive error management
        - Configures DroidBot-specific parameters and exploration settings
        - Establishes integration with monitored operations framework
        """
        super().__init__(
            name="droidbot",
            description="DroidBot lightweight test input generator for Android applications",
            process_pattern="droidbot"
        )

        # Initialize rv-android-core infrastructure components
        self._logging_manager = LoggingManager.get_instance()
        self.logger = self._logging_manager.get_logger(
            "rv_tools.builtin.droidbot",
            {CONTEXT_COMPONENT: "DroidBotTool"}
        )
        self.error_handler = ErrorHandler.get_instance()

        # Default tool configuration
        self.default_config = {
            "policy": "dfs_naive",
            "count": 10000000000,  # Effectively unlimited
            "timeout": 600,  # 10 minutes
            "device_id": "emulator-5554",
            "ignore_ad": True,
            "is_emulator": True,
            "enable_accessibility_hard": False,
            "master": None,
            "humanoid": None,
            "use_method_profiling": "none",
            "grant_perm": True,
            "enable_monkey": False,
            "output_dir": None,
            "cv_mode": False,
            "debug_mode": False,
            "random_input": False,
            "script_path": None,
            "event_interval": 1,
            "event_count": None
        }

        self.logger.info("DroidBot tool initialized successfully")

    def configure_tool_specific(self, config: Dict[str, Any]) -> None:
        """
        Configure DroidBot-specific parameters and validate settings.

        Args:
            config: Configuration dictionary with tool-specific parameters

        Raises:
            ValueError: If configuration parameters are invalid
        """
        self.logger.debug("Configuring DroidBot-specific parameters")

        # Policy configuration
        if 'policy' in config:
            policy = config['policy']
            valid_policies = [
                'dfs_naive', 'dfs_greedy', 'bfs_naive', 'bfs_greedy',
                'random', 'monkey', 'none', 'manual'
            ]
            if policy not in valid_policies:
                raise ValueError(f"policy must be one of: {valid_policies}")
            self.tool_config['policy'] = policy

        # Event count configuration
        if 'count' in config:
            count = config['count']
            if isinstance(count, str) and count.isdigit():
                count = int(count)
            if not isinstance(count, int) or count < 1:
                raise ValueError("count must be a positive integer")
            self.tool_config['count'] = count

        # Event count alternative parameter
        if 'event_count' in config:
            event_count = config['event_count']
            if event_count is not None:
                if isinstance(event_count, str) and event_count.isdigit():
                    event_count = int(event_count)
                if not isinstance(event_count, int) or event_count < 1:
                    raise ValueError("event_count must be a positive integer")
                self.tool_config['event_count'] = event_count

        # Timeout configuration
        if 'timeout' in config:
            timeout = config['timeout']
            if not isinstance(timeout, int) or timeout < 1:
                raise ValueError("timeout must be a positive integer")
            self.tool_config['timeout'] = timeout

        # Device configuration
        if 'device_id' in config:
            self.tool_config['device_id'] = str(config['device_id'])

        # Event interval configuration
        if 'event_interval' in config:
            interval = config['event_interval']
            if not isinstance(interval, (int, float)) or interval < 0:
                raise ValueError("event_interval must be a non-negative number")
            self.tool_config['event_interval'] = interval

        # Script path configuration
        if 'script_path' in config:
            script_path = config['script_path']
            if script_path and not os.path.exists(script_path):
                raise ValueError(f"script_path does not exist: {script_path}")
            self.tool_config['script_path'] = script_path

        # Output directory configuration
        if 'output_dir' in config:
            self.tool_config['output_dir'] = str(config['output_dir'])

        # Master configuration
        if 'master' in config:
            self.tool_config['master'] = str(config['master'])

        # Humanoid configuration
        if 'humanoid' in config:
            self.tool_config['humanoid'] = str(config['humanoid'])

        # Method profiling configuration
        if 'use_method_profiling' in config:
            profiling = config['use_method_profiling']
            valid_profiling = ['none', 'full', 'sampling']
            if profiling not in valid_profiling:
                raise ValueError(f"use_method_profiling must be one of: {valid_profiling}")
            self.tool_config['use_method_profiling'] = profiling

        # Boolean flags
        boolean_flags = [
            'ignore_ad', 'is_emulator', 'enable_accessibility_hard',
            'grant_perm', 'enable_monkey', 'cv_mode', 'debug_mode', 'random_input'
        ]
        
        for flag in boolean_flags:
            if flag in config:
                self.tool_config[flag] = bool(config[flag])

        self.logger.info("DroidBot tool configuration completed successfully")

    def build_command_args(self, app: App, output_file: str, task_config: Dict[str, Any]) -> List[str]:
        """
        Build command arguments for DroidBot execution.

        Args:
            app: Application instance containing APK information
            output_file: Path to output trace file
            task_config: Task-specific configuration parameters

        Returns:
            List of command arguments for tool execution
        """
        try:
            self.logger.debug(f"Building DroidBot command arguments for app: {app.name}")

            # Base arguments
            args = [
                "-d", self.tool_config['device_id'],
                "-a", app.path,
                "-policy", self.tool_config['policy']
            ]

            # Timeout configuration
            timeout_seconds = task_config.get('timeout', self.tool_config['timeout'])
            args.extend(["-timeout", str(timeout_seconds)])

            # Event count configuration
            if self.tool_config.get('event_count') is not None:
                args.extend(["-count", str(self.tool_config['event_count'])])
            elif self.tool_config.get('count') != 10000000000:  # If not default unlimited
                args.extend(["-count", str(self.tool_config['count'])])

            # Event interval configuration
            if self.tool_config['event_interval'] != 1:
                args.extend(["-interval", str(self.tool_config['event_interval'])])

            # Output directory configuration
            if self.tool_config.get('output_dir'):
                args.extend(["-o", self.tool_config['output_dir']])

            # Script path configuration
            if self.tool_config.get('script_path'):
                args.extend(["-script", self.tool_config['script_path']])

            # Master configuration
            if self.tool_config.get('master'):
                args.extend(["-master", self.tool_config['master']])

            # Humanoid configuration
            if self.tool_config.get('humanoid'):
                args.extend(["-humanoid", self.tool_config['humanoid']])

            # Method profiling configuration
            if self.tool_config['use_method_profiling'] != 'none':
                args.extend(["-use_method_profiling", self.tool_config['use_method_profiling']])

            # Boolean flags
            if self.tool_config['ignore_ad']:
                args.append("-ignore_ad")

            if self.tool_config['is_emulator']:
                args.append("-is_emulator")

            if self.tool_config['enable_accessibility_hard']:
                args.append("-enable_accessibility_hard")

            if self.tool_config['grant_perm']:
                args.append("-grant_perm")

            if self.tool_config['enable_monkey']:
                args.append("-enable_monkey")

            if self.tool_config['cv_mode']:
                args.append("-cv_mode")

            if self.tool_config['debug_mode']:
                args.append("-debug")

            if self.tool_config['random_input']:
                args.append("-random_input")

            self.logger.debug(f"DroidBot command arguments: {args}")
            return args

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "build_command_args",
                    "app_name": app.name,
                    "tool": "droidbot",
                    "component": "DroidBotTool"
                }
            )
            raise

    def validate_execution_environment(self, app: App) -> bool:
        """
        Validate that the execution environment is properly configured for DroidBot.

        Args:
            app: Application instance to validate against

        Returns:
            True if environment is valid, False otherwise
        """
        try:
            self.logger.debug("Validating DroidBot execution environment")

            # Check if DroidBot is available
            try:
                droidbot_check = Command("droidbot", ["--help"], timeout=10)
                result = droidbot_check.invoke()
                if result.returncode != 0:
                    self.logger.error("DroidBot is not available or not responding")
                    return False
            except Exception as e:
                self.logger.error(f"DroidBot validation failed: {str(e)}")
                return False

            # Check if ADB is available
            try:
                adb_check = Command("adb", ["devices"], timeout=10)
                result = adb_check.invoke()
                if result.returncode != 0:
                    self.logger.error("ADB is not available or not responding")
                    return False
            except Exception as e:
                self.logger.error(f"ADB validation failed: {str(e)}")
                return False

            # Validate APK file
            if not os.path.exists(app.path):
                self.logger.error(f"APK file not found: {app.path}")
                return False

            # Check device connectivity
            device_id = self.tool_config['device_id']
            try:
                device_check = Command("adb", ["-s", device_id, "shell", "echo", "test"], timeout=10)
                result = device_check.invoke()
                if result.returncode != 0:
                    self.logger.error(f"Device not accessible: {device_id}")
                    return False
            except Exception as e:
                self.logger.error(f"Device connectivity check failed: {str(e)}")
                return False

            self.logger.info("DroidBot execution environment validation successful")
            return True

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "validate_execution_environment",
                    "app_name": app.name,
                    "tool": "droidbot",
                    "component": "DroidBotTool"
                }
            )
            return False

    def get_execution_command(self, app: App, output_file: str, task_config: Dict[str, Any]) -> Command:
        """
        Create the execution command for DroidBot tool.

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
            timeout_seconds = task_config.get('timeout', self.tool_config['timeout'])
            execution_timeout = timeout_seconds + 30  # Add 30 second buffer

            # Create command with comprehensive configuration
            command = Command(
                executable="droidbot",
                args=args,
                timeout=execution_timeout
            )

            self.logger.info(f"DroidBot execution command created for app: {app.name}")
            return command

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "get_execution_command",
                    "app_name": app.name,
                    "tool": "droidbot",
                    "component": "DroidBotTool"
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
            self.logger.debug(f"Processing DroidBot execution result for app: {app.name}")

            # Base result information
            execution_result = {
                "tool": "droidbot",
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
                    "policy_used": self.tool_config['policy'],
                    "monitored_operations_detected": self._analyze_trace_for_monitored_operations(output_file)
                })
            else:
                execution_result.update({
                    "exploration_completed": False,
                    "timeout_occurred": result.returncode == 124,  # Standard timeout return code
                    "error_details": getattr(result, 'stderr', ''),
                    "policy_used": self.tool_config['policy'],
                    "monitored_operations_detected": 0
                })

            # Extract additional metrics from trace file
            if output_file and os.path.exists(output_file):
                execution_result.update(self._extract_trace_metrics(output_file))

            self.logger.info(f"DroidBot execution result processed for app: {app.name}")
            return execution_result

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "process_execution_result",
                    "app_name": app.name,
                    "tool": "droidbot",
                    "component": "DroidBotTool"
                }
            )
            
            # Return basic error result
            return {
                "tool": "droidbot",
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
        Get comprehensive information about the DroidBot tool.

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
            "requires_adb": True,
            "monitored_operations_support": True
        }

    def __str__(self) -> str:
        """String representation of the DroidBot tool."""
        return f"DroidBotTool(name='{self.name}', configured={bool(self.tool_config)})"

    def __repr__(self) -> str:
        """Detailed string representation of the DroidBot tool."""
        return (f"DroidBotTool(name='{self.name}', description='{self.description}', "
                f"config_keys={list(self.tool_config.keys())})")