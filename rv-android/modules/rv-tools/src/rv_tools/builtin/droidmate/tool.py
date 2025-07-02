"""
DroidMate systematic test input generator implementation.

This module provides integration with the DroidMate Android testing framework,
enabling systematic test input generation for research and monitored operations testing.
"""

import os
from typing import Dict, Any, List

from rv_android_core.app import App
from rv_android_core.commands.command import Command
from rv_android_core.domain.task import Task
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT


class DroidMateTool(AbstractTool):
    """
    DroidMate systematic test input generator for monitored operations testing.

    ### Architectural Decisions:
    - Inherits directly from AbstractTool for simplified architecture
    - Implements systematic test input generation for research-oriented testing
    - Provides comprehensive exploration with configurable parameters
    - Uses JAR-based execution model for cross-platform compatibility
    - Supports multiple exploration strategies and configuration options
    - Integrates with rv-android-core infrastructure for error handling and logging

    ### Role in the System:
    - Serves as a systematic testing tool for comprehensive Android app exploration
    - Provides research-oriented test input generation with detailed logging
    - Enables systematic exploration with configurable strategies and parameters
    - Supports both JCA cryptography detection and generic monitored operations testing
    - Facilitates academic research through detailed execution traces and reports

    ### Key Features:
    - Systematic test input generation and exploration
    - Comprehensive logging and trace generation
    - Configurable exploration strategies and parameters
    - JAR-based execution for cross-platform compatibility
    - Integration with Android Debug Bridge (ADB) for device communication

    ### Tool Variants:
    DroidMate supports different exploration modes as variants:
    - systematic: Full systematic exploration
    - quick: Quick exploration with reduced parameters
    - research: Research mode with detailed logging
    """

    # Simplified tool specification
    TOOL_SPEC = ToolSpec.create_builtin_spec(
        name="droidmate",
        description="DroidMate systematic test input generator for comprehensive Android exploration",
        url="https://github.com/uds-se/droidmate",
        version="1.0.0",
        process_pattern="droidmate"
    )

    def __init__(self, name: str = None, description: str = None, process_pattern: str = None):
        """
        Initialize the DroidMate tool with rv-android-core infrastructure.
        """
        super().__init__(
            name=name or self.TOOL_SPEC.name,
            description=description or self.TOOL_SPEC.description,
            process_pattern=process_pattern or self.TOOL_SPEC.process_pattern
        )

        # Initialize rv-android-core infrastructure components
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_tools.builtin.droidmate",
            {CONTEXT_COMPONENT: "DroidMateTool"}
        )
        self.error_handler = ErrorHandler.get_instance()

        # Default DroidMate configuration
        self.config = {
            "exploration_timeout": 600,      # Exploration timeout in seconds
            "device_serial": None,           # Device serial number
            "droidmate_jar_path": None,      # Path to DroidMate jar file
            "output_dir": None,              # Output directory
            "exploration_strategy": "systematic", # Exploration strategy
            "reset_every_nth_exploration": 0, # Reset app every N explorations
            "time_limit_for_each_action": 3000, # Time limit per action in ms
            "api_logs_enabled": True,        # Enable API logging
            "debug_mode": False,             # Enable debug mode
            "inline_port_file": None,        # Inline port file path
            "uiautomator_daemon_tcp_port": 59800 # UIAutomator daemon port
        }

        self.logger.info("Initialized DroidMate tool for systematic exploration")

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure DroidMate-specific parameters.

        Supported configuration options:
        - exploration_timeout: Exploration timeout in seconds
        - device_serial: Device serial number
        - droidmate_jar_path: Path to DroidMate jar file
        - output_dir: Output directory
        - exploration_strategy: Exploration strategy
        - reset_every_nth_exploration: Reset app every N explorations
        - time_limit_for_each_action: Time limit per action in milliseconds
        - api_logs_enabled: Enable API logging
        - debug_mode: Enable debug mode
        - uiautomator_daemon_tcp_port: UIAutomator daemon port

        Args:
            config: Configuration dictionary with DroidMate parameters
        """
        if not config:
            return

        # Update exploration timeout
        if 'exploration_timeout' in config:
            try:
                timeout = int(config['exploration_timeout'])
                if timeout > 0:
                    self.config['exploration_timeout'] = timeout
                    self.logger.debug(f"Set DroidMate exploration timeout to: {timeout}s")
                else:
                    self.logger.warning("Exploration timeout must be positive")
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid exploration_timeout value: {config['exploration_timeout']}")

        # Update device serial
        if 'device_serial' in config:
            self.config['device_serial'] = config['device_serial']
            self.logger.debug(f"Set DroidMate device serial to: {config['device_serial']}")

        # Update DroidMate jar path
        if 'droidmate_jar_path' in config:
            self.config['droidmate_jar_path'] = config['droidmate_jar_path']
            self.logger.debug(f"Set DroidMate jar path to: {config['droidmate_jar_path']}")

        # Update output directory
        if 'output_dir' in config:
            self.config['output_dir'] = config['output_dir']
            self.logger.debug(f"Set DroidMate output directory to: {config['output_dir']}")

        # Update exploration strategy
        if 'exploration_strategy' in config:
            self.config['exploration_strategy'] = str(config['exploration_strategy'])
            self.logger.debug(f"Set DroidMate exploration strategy to: {config['exploration_strategy']}")

        # Update numeric parameters
        numeric_params = ['reset_every_nth_exploration', 'time_limit_for_each_action', 'uiautomator_daemon_tcp_port']
        for param in numeric_params:
            if param in config:
                try:
                    value = int(config[param])
                    if value >= 0:
                        self.config[param] = value
                        self.logger.debug(f"Set DroidMate {param} to: {value}")
                    else:
                        self.logger.warning(f"{param} must be non-negative")
                except (ValueError, TypeError):
                    self.logger.warning(f"Invalid {param} value: {config[param]}")

        # Update boolean flags
        boolean_flags = ['api_logs_enabled', 'debug_mode']
        for flag in boolean_flags:
            if flag in config:
                self.config[flag] = bool(config[flag])
                self.logger.debug(f"Set DroidMate {flag} to: {self.config[flag]}")

        # Update inline port file
        if 'inline_port_file' in config:
            self.config['inline_port_file'] = config['inline_port_file']
            self.logger.debug(f"Set DroidMate inline port file to: {config['inline_port_file']}")

    @ErrorHandler.handle_errors(
        component="DroidMateTool",
        phase="execute_tool_specific_logic"
    )
    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
        """
        Execute DroidMate testing with configured parameters.

        ### Execution Workflow:
        1. Resolve DroidMate jar file location
        2. Prepare output directory and configuration
        3. Execute DroidMate with specified parameters
        4. Capture execution output and traces
        5. Process results and generate reports

        Args:
            task: Task configuration containing timeout and other parameters
            app: Application under test with package name and metadata
        """
        self.logger.info(f"Executing DroidMate tool for {app.package_name}")
        self.logger.debug(f"Strategy: {self.config['exploration_strategy']}, Timeout: {self.config['exploration_timeout']}s")

        # Get timeout from task configuration
        timeout_in_seconds = getattr(task.config, 'timeout', self.config['exploration_timeout'])
        
        self.logger.info(f"DroidMate execution timeout: {timeout_in_seconds} seconds")

        # Create output directory for DroidMate results
        output_dir = os.path.join(os.path.dirname(task.result.trace_file), "droidmate_output")
        os.makedirs(output_dir, exist_ok=True)

        # Resolve DroidMate jar file
        droidmate_jar_path = self._resolve_droidmate_jar_path()

        # Build DroidMate command
        droidmate_cmd = self._build_droidmate_command(app, droidmate_jar_path, output_dir, timeout_in_seconds)
        
        # Build command string for logging
        cmd_str = f"{droidmate_cmd.command} {' '.join(droidmate_cmd.args)}"
        self.logger.debug(f"DroidMate command: {cmd_str}")

        # Execute DroidMate testing
        try:
            self.logger.info(f"Starting DroidMate execution for {app.package_name}")
            result = droidmate_cmd.invoke()
            
            # Write result to trace file
            with open(task.result.trace_file, 'w') as trace_file:
                trace_file.write(f"DroidMate execution completed\n")
                trace_file.write(f"Exploration strategy: {self.config['exploration_strategy']}\n")
                trace_file.write(f"Exploration timeout: {self.config['exploration_timeout']}s\n")
                trace_file.write(f"Output directory: {output_dir}\n")
                trace_file.write(f"Command: {cmd_str}\n")
                if result.stdout:
                    trace_file.write(f"STDOUT:\n{result.stdout}\n")
                if result.stderr:
                    trace_file.write(f"STDERR:\n{result.stderr}\n")
            
            self.logger.info("DroidMate execution completed successfully")
            
        except Exception as e:
            self.logger.error(f"DroidMate execution failed: {str(e)}")
            # Write error information to trace file
            with open(task.result.trace_file, 'w') as trace_file:
                trace_file.write(f"DroidMate execution error: {str(e)}\n")
                trace_file.write(f"Command: {cmd_str}\n")
            raise

    def _resolve_droidmate_jar_path(self) -> str:
        """
        Resolve the path to the DroidMate jar file.

        Returns:
            Path to DroidMate jar file

        Raises:
            FileNotFoundError: If DroidMate jar file is not found
        """
        # Check configured path first
        if self.config.get("droidmate_jar_path") and os.path.isfile(self.config["droidmate_jar_path"]):
            return self.config["droidmate_jar_path"]

        # Common search paths for DroidMate jar
        search_paths = [
            # Environment variable based path
            os.path.join(os.environ.get('TOOLS_DIR', ''), 'droidmate', 'droidmate-2-X.X.X-all.jar'),
            # Relative to current module
            os.path.join(os.path.dirname(__file__), 'droidmate-2-X.X.X-all.jar'),
            # Standard installation paths
            '/opt/rv-android/tools/droidmate/droidmate-2-X.X.X-all.jar',
            './tools/droidmate/droidmate-2-X.X.X-all.jar',
            '../tools/droidmate/droidmate-2-X.X.X-all.jar'
        ]

        # Also check for any DroidMate jar file in the expected locations
        for base_path in [os.path.dirname(__file__), '/opt/rv-android/tools/droidmate', './tools/droidmate']:
            if os.path.isdir(base_path):
                for file in os.listdir(base_path):
                    if file.startswith('droidmate') and file.endswith('.jar'):
                        jar_path = os.path.join(base_path, file)
                        self.logger.debug(f"Found DroidMate jar at: {jar_path}")
                        return jar_path

        for path in search_paths:
            if path and os.path.isfile(path):
                self.logger.debug(f"Found DroidMate jar at: {path}")
                return path

        raise FileNotFoundError("DroidMate jar file not found. Please ensure DroidMate is properly installed.")

    def _build_droidmate_command(self, app: App, droidmate_jar_path: str, output_dir: str, timeout_seconds: int) -> Command:
        """
        Build the DroidMate command with configured parameters.

        Args:
            app: Application under test
            droidmate_jar_path: Path to DroidMate jar file
            output_dir: Output directory for DroidMate results
            timeout_seconds: Command execution timeout

        Returns:
            Configured Command object for DroidMate execution
        """
        # Start building command arguments
        cmd_args = [
            "-jar", droidmate_jar_path,
            "-apk", app.apk_path,
            "-outputDir", output_dir,
            "-explorationTimeoutMs", str(self.config["exploration_timeout"] * 1000)
        ]

        # Add device serial if specified
        if self.config["device_serial"]:
            cmd_args.extend(["-deviceSerialNumber", self.config["device_serial"]])

        # Add exploration strategy
        cmd_args.extend(["-explorationStrategy", self.config["exploration_strategy"]])

        # Add reset frequency
        if self.config["reset_every_nth_exploration"] > 0:
            cmd_args.extend(["-resetEveryNthExploration", str(self.config["reset_every_nth_exploration"])])

        # Add action time limit
        cmd_args.extend(["-timeLimitForEachAction", str(self.config["time_limit_for_each_action"])])

        # Add UIAutomator daemon port
        cmd_args.extend(["-uiautomatorDaemonTcpPort", str(self.config["uiautomator_daemon_tcp_port"])])

        # Add API logs flag
        if self.config["api_logs_enabled"]:
            cmd_args.append("-apiLogsEnabled")

        # Add debug mode if enabled
        if self.config["debug_mode"]:
            cmd_args.append("-debug")

        # Add inline port file if specified
        if self.config["inline_port_file"]:
            cmd_args.extend(["-inlinePortFile", self.config["inline_port_file"]])

        return Command("java", cmd_args, timeout_seconds)

    def get_tool_info(self) -> dict:
        """
        Get comprehensive DroidMate tool information.

        Returns:
            Dictionary with tool information and current configuration
        """
        info = super().get_tool_info()
        info.update({
            "tool_spec": self.TOOL_SPEC.to_dict(),
            "exploration_strategy": self.config["exploration_strategy"],
            "current_timeout": self.config["exploration_timeout"],
            "api_logs_enabled": self.config["api_logs_enabled"],
            "debug_mode": self.config["debug_mode"],
            "version": self.TOOL_SPEC.version,
            "url": self.TOOL_SPEC.url
        })
        return info


# Function to register DroidMate variants
def register_droidmate_variants(registry):
    """
    Register DroidMate variants in the tool registry.
    
    Args:
        registry: ToolRegistry instance
    """
    # Register exploration mode variants
    variants = {
        "systematic": {"exploration_strategy": "systematic", "exploration_timeout": 900},
        "quick": {"exploration_strategy": "quick", "exploration_timeout": 300},
        "research": {"exploration_strategy": "systematic", "exploration_timeout": 1800, "debug_mode": True}
    }
    
    for variant_name, config in variants.items():
        registry.register_variant("droidmate", variant_name, config)