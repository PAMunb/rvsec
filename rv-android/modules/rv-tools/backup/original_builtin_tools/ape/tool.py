"""
APE (Android Programmatic Events) testing tool implementation.

APE applies a CEGAR (Counter-Example Guided Abstraction Refinement) style 
technique to refine and coarsen model abstraction for Android app testing.
"""

import os
from typing import Any

from rv_android_core.app import App
from rv_android_core.commands.command import Command
from rv_android_core.tools.configurable_tool import ConfigurableTool
from rv_android_core.tools.tool_spec import ToolSpec, ToolType, ToolCategory
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT


class APETool(ConfigurableTool):
    """
    APE (Android Programmatic Events) testing tool for monitored operations.

    ### Architectural Decisions:
    - Extends ConfigurableTool for standardized configuration handling
    - Provides clean interface to APE testing framework
    - Supports customization of APE parameters through configuration
    - Implements CEGAR-based model abstraction refinement
    - Integrates with RV-Android monitored operations infrastructure

    ### Role in the System:
    - Integrates APE Android testing tool into monitored operations framework
    - Enables APE-based testing with configurable parameters and strategies
    - Provides unified interface for APE execution in experiments
    - Supports systematic exploration of Android app state spaces
    - Facilitates model-based testing with abstraction refinement

    ### Key Considerations:
    - Supports multiple exploration strategies (sata, bfs, dfs, random)
    - Manages APE jar deployment and execution on Android devices
    - Provides timeout management and execution control
    - Integrates with monitored operations instrumentation
    - Handles device communication and file transfer operations

    ### Integration Strategy:
    - Compatible with experiment framework and task management
    - Supports configuration through ToolRegistry and ToolFactory
    - Enables dynamic parameter customization per experiment
    - Provides standardized logging and error handling
    - Facilitates result collection and analysis integration

    ### Performance and Scalability:
    - Optimized for systematic state space exploration
    - Supports configurable timeout and execution limits
    - Enables efficient model abstraction and refinement
    - Adaptable to different app complexity levels
    - Minimizes overhead through targeted exploration strategies
    """

    # APE tool specification
    TOOL_SPEC = ToolSpec.create_builtin_spec(
        name="ape",
        description="Android Programmatic Events testing with CEGAR-based model abstraction",
        category=ToolCategory.MODEL_BASED,
        version="1.0.0",
        process_pattern="com.android.commands.ape",
        capabilities=[
            "model_based_testing",
            "state_space_exploration", 
            "abstraction_refinement",
            "systematic_exploration",
            "cegar_technique"
        ]
    )

    def __init__(self):
        """
        Initialize APE tool with default configuration and rv-android-core infrastructure.
        
        ### Infrastructure Integration:
        - Sets up standardized logging with APE-specific context
        - Initializes error handler for comprehensive error management
        - Configures APE-specific parameters and execution settings
        - Establishes integration with monitored operations framework
        """
        super().__init__(
            name=self.TOOL_SPEC.name,
            description=self.TOOL_SPEC.description,
            process_pattern=self.TOOL_SPEC.process_pattern
        )

        # Initialize rv-android-core infrastructure components
        self._logging_manager = LoggingManager.get_instance()
        self.logger = self._logging_manager.get_logger(
            "rv_tools.builtin.ape",
            {CONTEXT_COMPONENT: "APETool"}
        )
        self.error_handler = ErrorHandler.get_instance()

        # Default APE configuration
        self.config = {
            "strategy": "sata",           # Exploration strategy (sata, bfs, dfs, random)
            "running_minutes": None,      # Will be calculated from task timeout
            "ape_jar_path": None,         # Will be resolved at runtime
            "device_id": "emulator-5554", # Default device
            "push_jar": True              # Whether to push jar to device
        }

        self.logger.info(f"Initialized APE tool with capabilities: {self.TOOL_SPEC.capabilities}")

    def configure_tool_specific(self, config: dict) -> None:
        """
        Configure APE-specific parameters.
        
        Supported configuration options:
        - strategy: Exploration strategy (sata, bfs, dfs, random)
        - running_minutes: Execution time limit in minutes
        - device_id: Target Android device identifier
        - push_jar: Whether to push APE jar to device (default: True)
        
        Args:
            config: Configuration dictionary with APE parameters
        """
        # Update strategy if specified
        if "strategy" in config:
            strategy = config["strategy"]
            valid_strategies = ["sata", "bfs", "dfs", "random"]
            if strategy in valid_strategies:
                self.config["strategy"] = strategy
                self.logger.debug(f"Set APE strategy to: {strategy}")
            else:
                self.logger.warning(f"Invalid APE strategy '{strategy}', using default 'sata'")

        # Update running minutes if specified
        if "running_minutes" in config:
            try:
                minutes = int(config["running_minutes"])
                if minutes > 0:
                    self.config["running_minutes"] = minutes
                    self.logger.debug(f"Set APE running minutes to: {minutes}")
                else:
                    self.logger.warning("APE running minutes must be positive")
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid running_minutes value: {config['running_minutes']}")

        # Update device ID if specified
        if "device_id" in config:
            self.config["device_id"] = str(config["device_id"])
            self.logger.debug(f"Set APE device ID to: {self.config['device_id']}")

        # Update jar push setting if specified
        if "push_jar" in config:
            self.config["push_jar"] = bool(config["push_jar"])
            self.logger.debug(f"Set APE push_jar to: {self.config['push_jar']}")

    def execute_tool_specific_logic(self, task: Any, app: App) -> None:
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
        strategy = self.config["strategy"]
        device_id = self.config["device_id"]
        
        self.logger.info(f"Executing APE tool with strategy: {strategy}")
        self.logger.debug(f"Target device: {device_id}, App: {app.package_name}")

        # Resolve APE jar file path
        ape_jar_path = self._resolve_ape_jar_path()
        if not ape_jar_path:
            raise FileNotFoundError("APE jar file not found. Please ensure APE is properly installed.")

        # Calculate timeout from task configuration
        timeout_in_seconds = getattr(task.config, 'timeout', 300)  # Default 5 minutes
        
        # Use configured running_minutes or calculate from timeout
        if self.config["running_minutes"] is not None:
            timeout_in_minutes = self.config["running_minutes"]
            timeout_in_seconds = timeout_in_minutes * 60  # Update seconds for command timeout
        else:
            timeout_in_minutes = max(1, int(timeout_in_seconds / 60))  # At least 1 minute

        self.logger.info(f"APE execution timeout: {timeout_in_minutes} minutes ({timeout_in_seconds} seconds)")

        # Execute APE testing workflow
        with open(task.result.trace_file, 'wb') as trace_file:
            try:
                # Push APE jar to device if enabled
                if self.config["push_jar"]:
                    self._push_ape_jar(ape_jar_path, device_id, trace_file)

                # Execute APE with configured parameters
                self._execute_ape_command(
                    app=app,
                    device_id=device_id,
                    strategy=strategy,
                    timeout_minutes=timeout_in_minutes,
                    timeout_seconds=timeout_in_seconds,
                    trace_file=trace_file
                )

                self.logger.info("APE execution completed successfully")

            except Exception as e:
                self.error_handler.handle_error(
                    e,
                    context={
                        "operation": "ape_execution",
                        "app_package": app.package_name,
                        "strategy": strategy,
                        "device_id": device_id,
                        "component": "APETool"
                    }
                )
                # Write error information to trace file
                error_msg = f"APE execution error: {str(e)}\n"
                trace_file.write(error_msg.encode('utf-8'))
                raise

    def _resolve_ape_jar_path(self) -> str:
        """
        Resolve the path to the APE jar file.
        
        This method looks for the APE jar in several possible locations:
        1. Configured path in self.config["ape_jar_path"]
        2. TOOLS_DIR environment variable + ape/ape.jar
        3. Current directory + lib/ape/ape.jar
        4. Default system locations
        
        Returns:
            Path to APE jar file or None if not found
        """
        # Check configured path first
        if self.config.get("ape_jar_path") and os.path.isfile(self.config["ape_jar_path"]):
            return self.config["ape_jar_path"]

        # Common search paths for APE jar
        search_paths = [
            # Environment variable based path
            os.path.join(os.environ.get('TOOLS_DIR', ''), 'ape', 'ape.jar'),
            # Relative to current module
            os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'lib', 'ape', 'ape.jar'),
            # Standard installation paths
            '/opt/rv-android/lib/ape/ape.jar',
            './lib/ape/ape.jar',
            '../lib/ape/ape.jar'
        ]

        for path in search_paths:
            if path and os.path.isfile(path):
                self.logger.debug(f"Found APE jar at: {path}")
                return path

        self.logger.error("APE jar file not found in any of the expected locations")
        return None

    def _push_ape_jar(self, ape_jar_path: str, device_id: str, trace_file) -> None:
        """
        Push APE jar file to the Android device.
        
        Args:
            ape_jar_path: Local path to APE jar file
            device_id: Target device identifier
            trace_file: Output stream for command output
        """
        device_jar_path = "/data/local/tmp/ape.jar"
        
        self.logger.info(f"Pushing APE jar to device {device_id}: {ape_jar_path} -> {device_jar_path}")
        
        push_cmd = Command('adb', [
            '-s', device_id,
            'push', '-a', '-p',
            ape_jar_path,
            device_jar_path
        ])
        
        try:
            push_cmd.invoke(stdout=trace_file)
            self.logger.debug("APE jar successfully pushed to device")
        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "push_ape_jar",
                    "device_id": device_id,
                    "jar_path": ape_jar_path,
                    "component": "APETool"
                }
            )
            raise

    def _execute_ape_command(self, app: App, device_id: str, strategy: str, 
                           timeout_minutes: int, timeout_seconds: int, trace_file) -> None:
        """
        Execute the APE testing command on the device.
        
        Args:
            app: Application under test
            device_id: Target device identifier
            strategy: APE exploration strategy
            timeout_minutes: Execution timeout in minutes
            timeout_seconds: Command timeout in seconds
            trace_file: Output stream for command output
        """
        self.logger.info(f"Starting APE execution for {app.package_name} with {strategy} strategy")
        
        # Construct APE command
        ape_cmd = Command('adb', [
            '-s', device_id,
            'shell',
            'CLASSPATH=/data/local/tmp/ape.jar',
            '/system/bin/app_process',
            '/data/local/tmp/',
            'com.android.commands.monkey.Monkey',
            '-p', app.package_name,
            '--running-minutes', str(timeout_minutes),
            '--ape', strategy
        ], timeout_seconds)

        # Build command string for logging
        cmd_str = f"{ape_cmd.command} {' '.join(ape_cmd.args)}"
        self.logger.debug(f"APE command: {cmd_str}")
        
        try:
            # Execute APE command
            ape_cmd.invoke(stdout=trace_file)
            self.logger.info(f"APE command completed for {app.package_name}")
            
        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "execute_ape_command",
                    "app_package": app.package_name,
                    "device_id": device_id,
                    "strategy": strategy,
                    "timeout_minutes": timeout_minutes,
                    "component": "APETool"
                }
            )
            raise

    def get_supported_strategies(self) -> list:
        """
        Get list of supported APE exploration strategies.
        
        Returns:
            List of supported strategy names
        """
        return ["sata", "bfs", "dfs", "random"]

    def get_tool_info(self) -> dict:
        """
        Get comprehensive APE tool information.
        
        Returns:
            Dictionary with tool information, capabilities, and current configuration
        """
        info = super().get_tool_info()
        info.update({
            "tool_spec": self.TOOL_SPEC.to_dict(),
            "supported_strategies": self.get_supported_strategies(),
            "current_strategy": self.config["strategy"],
            "version": self.TOOL_SPEC.version,
            "category": self.TOOL_SPEC.category.value
        })
        return info