"""
APE (Android Programmatic Events) testing tool implementation.

This module provides integration with the APE Android testing framework,
enabling CEGAR-based model abstraction refinement for systematic exploration.
"""

import os
from typing import Dict, Any, List

from rv_android_core.domain.app import App
from rv_android_core.commands.command import Command
from rv_android_core.domain.task import Task
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import RVToolTimeoutError, RVToolExecutionError
from rv_android_core.util.jar_resolver import JarResolver


class APETool(AbstractTool):
    """
    APE (Android Programmatic Events) testing tool for systematic exploration.

    ### Architectural Decisions:
    - Inherits directly from AbstractTool for simplified architecture
    - Implements CEGAR-based model abstraction refinement for systematic testing
    - Provides clean interface to APE testing framework with configurable parameters
    - Uses ADB shell execution model matching original implementation
    - Supports multiple exploration strategies with systematic state space coverage
    - Integrates with rv-android-core infrastructure for error handling and logging

    ### Role in the System:
    - Serves as a model-based testing tool for systematic Android app exploration
    - Provides CEGAR-based abstraction refinement for efficient state space coverage
    - Enables systematic exploration with configurable strategies and parameters
    - Supports both JCA cryptography detection and generic monitored operations testing
    - Facilitates systematic analysis of application state spaces and transitions

    ### Key Features:
    - Multiple exploration strategies: sata, bfs, dfs, random
    - CEGAR-based model abstraction and refinement capabilities
    - Configurable execution timeouts and exploration parameters
    - JAR-based deployment and execution on Android devices via ADB shell
    - Integration with Android Debug Bridge (ADB) for device communication

    ### Tool Variants:
    APE supports different exploration strategies as variants:
    - sata: SATA (Static Analysis Targeted Abstraction) strategy
    - bfs: Breadth-first search exploration
    - dfs: Depth-first search exploration
    - random: Random exploration strategy
    """

    # Simplified tool specification
    TOOL_SPEC = ToolSpec.create_builtin_spec(
        name="ape",
        description="APE CEGAR-based model abstraction testing tool for systematic Android exploration",
        url="https://github.com/tjusenchen/ape",
        version="1.0.0",
        process_pattern="com.android.commands.monkey"
    )

    # Available exploration strategies that can be used as variants
    AVAILABLE_STRATEGIES = [
        'sata', 'bfs', 'dfs', 'random'
    ]

    def __init__(self):
        """
        Initialize the APE tool with rv-android-core infrastructure.
        """
        # Initialize base class with tool spec parameters
        tool_spec = self.get_tool_spec()
        super().__init__(
            name=tool_spec.name,
            description=tool_spec.description,
            process_pattern=tool_spec.process_pattern
        )
        
        # Initialize rv-android-core infrastructure components
        self.jar_resolver = JarResolver()

        # Configuration will be set through configure() method
        self.config = {}

        self.logger.info("Initialized APE tool for systematic exploration")

    @classmethod
    def get_tool_spec(cls):
        """
        Get tool specification for registration.
        
        Returns:
            ToolSpec instance with tool metadata
        """
        return cls.TOOL_SPEC

    @classmethod
    def get_variants(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get available APE variants with exploration strategy configurations.
        
        Returns:
            Dictionary mapping variant names to APE configuration parameters
        """
        return {
            "default": {
                "strategy": "sata",
                "running_minutes": 5,
                "debug_mode": True
            },
            "sata": {
                "strategy": "sata",
                "running_minutes": 10,
                "debug_mode": False
            },
            "bfs": {
                "strategy": "bfs",
                "running_minutes": 5,
                "debug_mode": False
            },
            "dfs": {
                "strategy": "dfs", 
                "running_minutes": 5,
                "debug_mode": False
            },
            "random": {
                "strategy": "random",
                "running_minutes": 5,
                "debug_mode": False
            }
        }
        
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure APE tool with resolved variant parameters.
        
        Args:
            config: Configuration dictionary with APE-specific parameters
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        from rv_android_core.util.error.exceptions import ConfigurationError
        
        # Validate required strategy
        if "strategy" not in config:
            raise ConfigurationError("APE tool requires 'strategy' parameter")
        
        if config["strategy"] not in self.AVAILABLE_STRATEGIES:
            raise ConfigurationError(
                f"Invalid APE strategy '{config['strategy']}'. "
                f"Available strategies: {self.AVAILABLE_STRATEGIES}"
            )
        
        # Set configuration with defaults
        self.config = {
            "strategy": config["strategy"],
            "running_minutes": config.get("running_minutes", 5),
            "device_serial": config.get("device_serial", "emulator-5554"),
            "debug_mode": config.get("debug_mode", True),
            "output_dir": config.get("output_dir", None),
            "ape_jar_path": config.get("ape_jar_path", None),
            **config  # Include any additional parameters
        }
        
        self.logger.info(
            f"Configured APE tool - Strategy: {self.config['strategy']}, "
            f"Duration: {self.config['running_minutes']}min"
        )

    @ErrorHandler.handle_errors(
        component="APETool",
        phase="execute_tool_specific_logic",
        reraise=True
    )
    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
        """
        Execute APE testing with configured parameters using original ADB shell approach.

        ### Execution Workflow:
        1. Resolve APE jar file location
        2. Calculate execution timeout from task configuration
        3. Push APE jar to Android device
        4. Execute APE using original ADB shell command format
        5. Check command execution result and handle failures

        Args:
            task: Task configuration containing timeout and other parameters
            app: Application under test with package name and metadata
            
        Raises:
            RVToolExecutionError: If APE execution fails or command returns non-zero exit code
        """
        self.logger.info(f"Executing APE tool for {app.package_name}")

        # Get timeout from task configuration
        timeout_in_seconds = getattr(task.config, 'timeout', self.config['running_minutes'] * 60)
        timeout_in_minutes = int(timeout_in_seconds / 60)
        if timeout_in_minutes == 0:
            timeout_in_minutes = 1
        
        self.logger.debug(f"Strategy: {self.config['strategy']}, Running minutes: {timeout_in_minutes}")
        self.logger.info(f"APE execution timeout: {timeout_in_seconds} seconds ({timeout_in_minutes} minutes)")

        # Create output directory for APE results
        output_dir = os.path.join(os.path.dirname(task.result.trace_file), "ape_output")
        os.makedirs(output_dir, exist_ok=True)

        # Resolve APE jar file
        ape_jar_path = self._resolve_ape_jar_path()

        # Step 1: Push APE jar to device
        self._push_ape_jar_to_device(ape_jar_path, task.result.trace_file)

        # Step 2: Execute APE using original ADB shell command format
        ape_cmd = self._build_ape_shell_command(app, timeout_in_minutes, timeout_in_seconds)
        
        # Build command string for logging
        cmd_str = f"{ape_cmd.command} {' '.join(ape_cmd.args)}"
        self.logger.debug(f"APE command: {cmd_str}")

        # Execute APE testing with centralized error handling
        self.logger.info(f"Starting APE execution for {app.package_name}")
        
        # Execute command with output redirection (binary mode for command output)
        try:
            with open(task.result.trace_file, 'wb') as trace_file:
                # Use centralized command execution with error handling
                # Redirect both stdout and stderr to trace file to prevent console flooding
                self._execute_and_check_command(ape_cmd, stdout=trace_file, stderr=trace_file)
            
            # # Append success information to trace file (text mode for metadata)
            # with open(task.result.trace_file, 'a', encoding='utf-8') as trace_file:
            #     success_info = f"\n--- APE Execution Completed ---\n"
            #     success_info += f"Strategy: {self.config['strategy']}\n"
            #     success_info += f"Running minutes: {timeout_in_minutes}\n"
            #     success_info += f"Command: {cmd_str}\n"
            #     trace_file.write(success_info)
                
        except RVToolTimeoutError:
            # APE timeout is expected behavior - log as completion
            self.logger.info(f"APE execution timed out after {timeout_in_seconds} seconds (expected behavior)")
            
            # Append timeout information to trace file (text mode for metadata)
            # with open(task.result.trace_file, 'a', encoding='utf-8') as trace_file:
            #     timeout_info = f"\n--- APE Execution Completed (Timeout) ---\n"
            #     timeout_info += f"Timeout duration: {timeout_in_seconds} seconds\n"
            #     timeout_info += f"Strategy: {self.config['strategy']}\n"
            #     timeout_info += f"Command: {cmd_str}\n"
            #     trace_file.write(timeout_info)
            
            # Re-raise the timeout exception (will be handled gracefully by error handler)
            raise
        
        self.logger.info("APE execution completed successfully")

    def _resolve_ape_jar_path(self) -> str:
        """
        Resolve the path to the APE jar file using centralized JarResolver.

        Returns:
            Path to APE jar file

        Raises:
            RVToolExecutionError: If APE jar file is not found
        """
        # Use JarResolver for centralized JAR resolution
        search_paths = [
            # Environment variable based path
            os.path.join(os.environ.get('TOOLS_DIR', ''), 'ape'),
            # Relative to current module
            os.path.dirname(__file__),
            # Standard installation paths
            '/opt/rv-android/tools/ape',
            './tools/ape',
            '../tools/ape'
        ]

        try:
            # Check configured path first
            if self.config.get("ape_jar_path"):
                return self.jar_resolver.resolve_jar_path("ape.jar", [os.path.dirname(self.config["ape_jar_path"])])
            
            # Use JarResolver with search paths
            return self.jar_resolver.resolve_jar_path("ape.jar", search_paths)
        except FileNotFoundError as e:
            error_msg = "APE jar file not found. Please ensure APE is properly installed."
            self.logger.error(error_msg)
            raise RVToolExecutionError(
                error_msg,
                tool_name=self.name,
                cause=e
            )

    def _push_ape_jar_to_device(self, jar_path: str, trace_file_path: str) -> None:
        """
        Push APE jar to Android device (matching original implementation).

        Args:
            jar_path: Local path to APE jar file
            trace_file_path: Path to trace file for logging output
            
        Raises:
            RVToolExecutionError: If jar push fails
        """
        device_jar_path = "/data/local/tmp/ape.jar"
        
        self.logger.info(f"Pushing APE jar from {jar_path} to {device_jar_path}")
        
        push_cmd = Command('adb', [
            '-s', self.config['device_serial'],
            'push', '-a', '-p', jar_path, device_jar_path
        ], timeout=60)  # 60 seconds timeout for push
        
        with open(trace_file_path, 'ab') as trace_file:
            trace_file.write("\n--- APE Jar Push ---\n".encode('utf-8'))
            result = push_cmd.invoke(stdout=trace_file)
            
            if result.is_failure():
                error_msg = f"Failed to push APE jar to device with exit code {result.code}"
                if result.has_error_output():
                    error_msg += f". Error: {result.get_stderr_text()}"
                
                self.logger.error(error_msg)
                raise RVToolExecutionError(
                    error_msg,
                    tool_name=self.name,
                    cause=None
                )
        
        self.logger.debug("APE jar pushed to device successfully")

    def _build_ape_shell_command(self, app: App, timeout_minutes: int, timeout_seconds: int) -> Command:
        """
        Build the APE command using original ADB shell format.

        Args:
            app: Application under test
            timeout_minutes: Execution timeout in minutes
            timeout_seconds: Command execution timeout in seconds

        Returns:
            Configured Command object for APE execution
        """
        # Build original ADB shell command format
        cmd_args = [
            '-s', self.config['device_serial'],
            'shell',
            'CLASSPATH=/data/local/tmp/ape.jar',
            '/system/bin/app_process',
            '/data/local/tmp/',
            'com.android.commands.monkey.Monkey',
            '-p', app.package_name,
            '--running-minutes', str(timeout_minutes),
            '--ape', self.config['strategy']
        ]

        return Command("adb", cmd_args, timeout_seconds)

    def get_available_strategies(self) -> List[str]:
        """
        Get list of available exploration strategies.

        Returns:
            List of available strategy names
        """
        return self.AVAILABLE_STRATEGIES.copy()

    def get_tool_info(self) -> dict:
        """
        Get comprehensive APE tool information.

        Returns:
            Dictionary with tool information and current configuration
        """
        info = super().get_tool_info()
        info.update({
            "tool_spec": self.TOOL_SPEC.to_dict(),
            "available_strategies": self.get_available_strategies(),
            "current_strategy": self.config["strategy"],
            "current_running_minutes": self.config["running_minutes"],
            "version": self.TOOL_SPEC.version,
            "url": self.TOOL_SPEC.url
        })
        return info

