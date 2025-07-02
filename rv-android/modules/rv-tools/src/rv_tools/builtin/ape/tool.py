"""
APE (Android Programmatic Events) testing tool implementation.

This module provides integration with the APE Android testing framework,
enabling CEGAR-based model abstraction refinement for systematic exploration.
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


class APETool(AbstractTool):
    """
    APE (Android Programmatic Events) testing tool for systematic exploration.

    ### Architectural Decisions:
    - Inherits directly from AbstractTool for simplified architecture
    - Implements CEGAR-based model abstraction refinement for systematic testing
    - Provides clean interface to APE testing framework with configurable parameters
    - Uses direct binary execution model for efficient resource utilization
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
    - JAR-based deployment and execution on Android devices
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

    def __init__(self, name: str = None, description: str = None, process_pattern: str = None):
        """
        Initialize the APE tool with rv-android-core infrastructure.
        """
        super().__init__(
            name=name or self.TOOL_SPEC.name,
            description=description or self.TOOL_SPEC.description,
            process_pattern=process_pattern or self.TOOL_SPEC.process_pattern
        )

        # Initialize rv-android-core infrastructure components
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_tools.builtin.ape",
            {CONTEXT_COMPONENT: "APETool"}
        )
        self.error_handler = ErrorHandler.get_instance()

        # Default APE configuration
        self.config = {
            "strategy": "sata",              # Exploration strategy
            "running_minutes": 5,            # Execution time in minutes
            "device_serial": None,           # Device serial number
            "ape_jar_path": None,            # Path to APE jar file
            "push_jar": True,                # Whether to push jar to device
            "debug_mode": False,             # Enable debug mode
            "output_dir": None               # Output directory for results
        }

        self.logger.info("Initialized APE tool for systematic exploration")

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure APE-specific parameters.

        Supported configuration options:
        - strategy: Exploration strategy (sata, bfs, dfs, random)
        - running_minutes: Execution time limit in minutes
        - device_serial: Device serial number
        - ape_jar_path: Path to APE jar file
        - push_jar: Whether to push jar to device
        - debug_mode: Enable debug mode
        - output_dir: Output directory for results

        Args:
            config: Configuration dictionary with APE parameters
        """
        if not config:
            return

        # Update exploration strategy
        if 'strategy' in config:
            strategy = config['strategy']
            if strategy not in self.AVAILABLE_STRATEGIES:
                self.logger.warning(f"Invalid strategy '{strategy}'. Using default 'sata'")
                self.logger.warning(f"Available strategies: {self.AVAILABLE_STRATEGIES}")
            else:
                self.config['strategy'] = strategy
                self.logger.debug(f"Set APE strategy to: {strategy}")

        # Update running minutes
        if 'running_minutes' in config:
            try:
                minutes = int(config['running_minutes'])
                if minutes > 0:
                    self.config['running_minutes'] = minutes
                    self.logger.debug(f"Set APE running minutes to: {minutes}")
                else:
                    self.logger.warning("Running minutes must be positive")
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid running_minutes value: {config['running_minutes']}")

        # Update device serial
        if 'device_serial' in config:
            self.config['device_serial'] = config['device_serial']
            self.logger.debug(f"Set APE device serial to: {config['device_serial']}")

        # Update APE jar path
        if 'ape_jar_path' in config:
            self.config['ape_jar_path'] = config['ape_jar_path']
            self.logger.debug(f"Set APE jar path to: {config['ape_jar_path']}")

        # Update boolean flags
        boolean_flags = ['push_jar', 'debug_mode']
        for flag in boolean_flags:
            if flag in config:
                self.config[flag] = bool(config[flag])
                self.logger.debug(f"Set APE {flag} to: {self.config[flag]}")

        # Update output directory
        if 'output_dir' in config:
            self.config['output_dir'] = config['output_dir']
            self.logger.debug(f"Set APE output directory to: {config['output_dir']}")

    @ErrorHandler.handle_errors(
        component="APETool",
        phase="execute_tool_specific_logic"
    )
    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
        """
        Execute APE testing with configured parameters.

        ### Execution Workflow:
        1. Resolve APE jar file location
        2. Calculate execution timeout from task configuration
        3. Push APE jar to Android device (if enabled)
        4. Execute APE with specified strategy and parameters
        5. Capture execution output for analysis

        Args:
            task: Task configuration containing timeout and other parameters
            app: Application under test with package name and metadata
        """
        self.logger.info(f"Executing APE tool for {app.package_name}")
        self.logger.debug(f"Strategy: {self.config['strategy']}, Running minutes: {self.config['running_minutes']}")

        # Get timeout from task configuration
        timeout_in_seconds = getattr(task.config, 'timeout', self.config['running_minutes'] * 60)
        
        self.logger.info(f"APE execution timeout: {timeout_in_seconds} seconds")

        # Create output directory for APE results
        output_dir = os.path.join(os.path.dirname(task.result.trace_file), "ape_output")
        os.makedirs(output_dir, exist_ok=True)

        # Resolve APE jar file
        ape_jar_path = self._resolve_ape_jar_path()

        # Build APE command
        ape_cmd = self._build_ape_command(app, ape_jar_path, output_dir, timeout_in_seconds)
        
        # Build command string for logging
        cmd_str = f"{ape_cmd.command} {' '.join(ape_cmd.args)}"
        self.logger.debug(f"APE command: {cmd_str}")

        # Execute APE testing
        try:
            self.logger.info(f"Starting APE execution for {app.package_name}")
            result = ape_cmd.invoke()
            
            # Write result to trace file
            with open(task.result.trace_file, 'w') as trace_file:
                trace_file.write(f"APE execution completed\n")
                trace_file.write(f"Strategy: {self.config['strategy']}\n")
                trace_file.write(f"Running minutes: {self.config['running_minutes']}\n")
                trace_file.write(f"Output directory: {output_dir}\n")
                trace_file.write(f"Command: {cmd_str}\n")
                if result.stdout:
                    trace_file.write(f"STDOUT:\n{result.stdout}\n")
                if result.stderr:
                    trace_file.write(f"STDERR:\n{result.stderr}\n")
            
            self.logger.info("APE execution completed successfully")
            
        except Exception as e:
            self.logger.error(f"APE execution failed: {str(e)}")
            # Write error information to trace file
            with open(task.result.trace_file, 'w') as trace_file:
                trace_file.write(f"APE execution error: {str(e)}\n")
                trace_file.write(f"Command: {cmd_str}\n")
            raise

    def _resolve_ape_jar_path(self) -> str:
        """
        Resolve the path to the APE jar file.

        Returns:
            Path to APE jar file

        Raises:
            FileNotFoundError: If APE jar file is not found
        """
        # Check configured path first
        if self.config.get("ape_jar_path") and os.path.isfile(self.config["ape_jar_path"]):
            return self.config["ape_jar_path"]

        # Common search paths for APE jar
        search_paths = [
            # Environment variable based path
            os.path.join(os.environ.get('TOOLS_DIR', ''), 'ape', 'ape.jar'),
            # Relative to current module
            os.path.join(os.path.dirname(__file__), 'ape.jar'),
            # Standard installation paths
            '/opt/rv-android/tools/ape/ape.jar',
            './tools/ape/ape.jar',
            '../tools/ape/ape.jar'
        ]

        for path in search_paths:
            if path and os.path.isfile(path):
                self.logger.debug(f"Found APE jar at: {path}")
                return path

        raise FileNotFoundError("APE jar file not found. Please ensure APE is properly installed.")

    def _build_ape_command(self, app: App, ape_jar_path: str, output_dir: str, timeout_seconds: int) -> Command:
        """
        Build the APE command with configured parameters.

        Args:
            app: Application under test
            ape_jar_path: Path to APE jar file
            output_dir: Output directory for APE results
            timeout_seconds: Command execution timeout

        Returns:
            Configured Command object for APE execution
        """
        # Start building command arguments
        cmd_args = [
            "-jar", ape_jar_path,
            "-p", app.package_name,
            "-running-minutes", str(self.config["running_minutes"]),
            "-ape", self.config["strategy"]
        ]

        # Add device serial if specified
        if self.config["device_serial"]:
            cmd_args.extend(["-s", self.config["device_serial"]])

        # Add debug mode if enabled
        if self.config["debug_mode"]:
            cmd_args.append("-debug")

        # Add output directory
        cmd_args.extend(["-o", output_dir])

        return Command("java", cmd_args, timeout_seconds)

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


# Function to register APE variants
def register_ape_variants(registry):
    """
    Register APE variants in the tool registry.
    
    Args:
        registry: ToolRegistry instance
    """
    # Register exploration strategy variants
    variants = {
        "sata": {"strategy": "sata"},
        "bfs": {"strategy": "bfs"},
        "dfs": {"strategy": "dfs"},
        "random": {"strategy": "random"}
    }
    
    for variant_name, config in variants.items():
        registry.register_variant("ape", variant_name, config)