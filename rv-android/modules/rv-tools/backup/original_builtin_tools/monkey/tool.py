"""
Android Monkey testing tool implementation.

Monkey generates pseudo-random streams of user events for stress testing
and monitored operations validation in Android applications.
"""

from typing import Any

from rv_android_core.app import App
from rv_android_core.commands.command import Command
from rv_android_core.tools.configurable_tool import ConfigurableTool
from rv_android_core.tools.tool_spec import ToolSpec, ToolType, ToolCategory
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT


class MonkeyTool(ConfigurableTool):
    """
    Android Monkey tool for random event generation and monitored operations testing.

    ### Architectural Decisions:
    - Extends ConfigurableTool for standardized configuration handling
    - Provides clean interface to Android Monkey testing framework
    - Supports extensive customization of Monkey parameters
    - Implements random event generation for stress testing
    - Integrates with RV-Android monitored operations infrastructure

    ### Role in the System:
    - Generates pseudo-random user events for Android application testing
    - Provides stress testing capabilities for monitored operations validation
    - Enables exploration of unexpected application states and behaviors
    - Supports configurable event generation patterns and constraints
    - Facilitates discovery of crashes and performance issues

    ### Key Considerations:
    - Supports multiple event types (touch, gesture, navigation, system)
    - Provides configurable event generation parameters and constraints
    - Manages execution timeout and event count limits
    - Integrates with monitored operations instrumentation for coverage
    - Handles device communication and command execution

    ### Integration Strategy:
    - Compatible with experiment framework and task management
    - Supports configuration through ToolRegistry and ToolFactory
    - Enables dynamic parameter customization per experiment
    - Provides standardized logging and error handling
    - Facilitates result collection and analysis integration

    ### Performance and Scalability:
    - Optimized for high-volume event generation
    - Supports configurable event generation rates and patterns
    - Enables efficient exploration of application state spaces
    - Adaptable to different application complexity and performance levels
    - Minimizes overhead through targeted event generation strategies
    """

    # Monkey tool specification
    TOOL_SPEC = ToolSpec.create_builtin_spec(
        name="monkey",
        description="Android UI/Application exerciser generating pseudo-random user events",
        category=ToolCategory.RANDOM_TESTING,
        version="1.0.0",
        process_pattern="com.android.commands.monkey",
        capabilities=[
            "random_testing",
            "stress_testing",
            "event_generation",
            "crash_detection",
            "performance_testing",
            "state_exploration"
        ]
    )

    def __init__(self):
        """
        Initialize Monkey tool with default configuration and rv-android-core infrastructure.
        
        ### Infrastructure Integration:
        - Sets up standardized logging with Monkey-specific context
        - Initializes error handler for comprehensive error management
        - Configures Monkey-specific parameters and event generation settings
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
            "rv_tools.builtin.monkey",
            {CONTEXT_COMPONENT: "MonkeyTool"}
        )
        self.error_handler = ErrorHandler.get_instance()

        # Default Monkey configuration
        self.config = {
            "event_count": 1_000_000_000,    # Number of events to generate
            "seed": None,                     # Random seed for reproducibility
            "throttle": 0,                    # Delay between events (ms)
            "device_id": "emulator-5554",     # Target device
            "verbosity": 2,                   # Verbosity level (0-3)
            "ignore_crashes": False,          # Continue after crashes
            "ignore_timeouts": False,         # Continue after ANR timeouts
            "ignore_monitored_violations": True, # Ignore monitored operations violations
            "kill_process_after_error": False, # Kill process after error
            "monitor_native_crashes": True,   # Monitor for native crashes
            "event_percentages": {            # Event type percentages
                "touch": None,                # Touch events
                "motion": None,               # Motion events  
                "trackball": None,            # Trackball events
                "syskeys": None,              # System key events
                "nav": None,                  # Navigation events
                "majornav": None,             # Major navigation events
                "appswitch": None,            # App switch events
                "flip": None,                 # Keyboard flip events
                "anyevent": None              # Any event types
            }
        }

        self.logger.info(f"Initialized Monkey tool with capabilities: {self.TOOL_SPEC.capabilities}")

    def configure_tool_specific(self, config: dict) -> None:
        """
        Configure Monkey-specific parameters.
        
        Supported configuration options:
        - event_count: Number of events to generate
        - seed: Random seed for reproducible testing
        - throttle: Delay between events in milliseconds
        - device_id: Target Android device identifier
        - verbosity: Output verbosity level (0-3)
        - ignore_crashes: Whether to continue after application crashes
        - ignore_timeouts: Whether to continue after ANR timeouts
        - ignore_monitored_violations: Whether to ignore monitored operations violations
        - event_percentages: Dictionary with event type percentages
        
        Args:
            config: Configuration dictionary with Monkey parameters
        """
        # Update event count
        if "event_count" in config:
            try:
                count = int(config["event_count"])
                if count > 0:
                    self.config["event_count"] = count
                    self.logger.debug(f"Set Monkey event count to: {count}")
                else:
                    self.logger.warning("Event count must be positive")
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid event_count value: {config['event_count']}")

        # Update random seed
        if "seed" in config:
            try:
                seed = int(config["seed"]) if config["seed"] is not None else None
                self.config["seed"] = seed
                self.logger.debug(f"Set Monkey seed to: {seed}")
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid seed value: {config['seed']}")

        # Update throttle delay
        if "throttle" in config:
            try:
                throttle = int(config["throttle"])
                if throttle >= 0:
                    self.config["throttle"] = throttle
                    self.logger.debug(f"Set Monkey throttle to: {throttle}ms")
                else:
                    self.logger.warning("Throttle must be non-negative")
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid throttle value: {config['throttle']}")

        # Update device ID
        if "device_id" in config:
            self.config["device_id"] = str(config["device_id"])
            self.logger.debug(f"Set Monkey device ID to: {self.config['device_id']}")

        # Update verbosity level
        if "verbosity" in config:
            try:
                verbosity = int(config["verbosity"])
                if 0 <= verbosity <= 3:
                    self.config["verbosity"] = verbosity
                    self.logger.debug(f"Set Monkey verbosity to: {verbosity}")
                else:
                    self.logger.warning("Verbosity must be between 0 and 3")
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid verbosity value: {config['verbosity']}")

        # Update boolean flags
        boolean_flags = [
            "ignore_crashes", "ignore_timeouts", "ignore_monitored_violations",
            "kill_process_after_error", "monitor_native_crashes"
        ]
        
        for flag in boolean_flags:
            if flag in config:
                self.config[flag] = bool(config[flag])
                self.logger.debug(f"Set Monkey {flag} to: {self.config[flag]}")

        # Update event percentages
        if "event_percentages" in config and isinstance(config["event_percentages"], dict):
            for event_type, percentage in config["event_percentages"].items():
                if event_type in self.config["event_percentages"]:
                    try:
                        if percentage is not None:
                            pct = float(percentage)
                            if 0 <= pct <= 100:
                                self.config["event_percentages"][event_type] = pct
                                self.logger.debug(f"Set {event_type} percentage to: {pct}%")
                            else:
                                self.logger.warning(f"Percentage for {event_type} must be 0-100")
                        else:
                            self.config["event_percentages"][event_type] = None
                    except (ValueError, TypeError):
                        self.logger.warning(f"Invalid percentage for {event_type}: {percentage}")

    def execute_tool_specific_logic(self, task: Any, app: App) -> None:
        """
        Execute Monkey testing with configured parameters.
        
        ### Execution Workflow:
        1. Build Monkey command with configured parameters
        2. Add event type percentages if specified
        3. Execute Monkey command on target device
        4. Capture execution output for analysis
        
        Args:
            task: Task configuration containing timeout and other parameters
            app: Application under test with package name and metadata
        """
        device_id = self.config["device_id"]
        event_count = self.config["event_count"]
        
        self.logger.info(f"Executing Monkey tool for {app.package_name}")
        self.logger.debug(f"Device: {device_id}, Events: {event_count}")

        # Get timeout from task configuration
        timeout_in_seconds = getattr(task.config, 'timeout', 300)  # Default 5 minutes
        
        self.logger.info(f"Monkey execution timeout: {timeout_in_seconds} seconds")

        # Build Monkey command
        monkey_cmd = self._build_monkey_command(app, timeout_in_seconds)
        
        # Build command string for logging
        cmd_str = f"{monkey_cmd.command} {' '.join(monkey_cmd.args)}"
        self.logger.debug(f"Monkey command: {cmd_str}")

        # Execute Monkey testing
        with open(task.result.trace_file, 'wb') as trace_file:
            try:
                self.logger.info(f"Starting Monkey execution for {app.package_name}")
                monkey_cmd.invoke(stdout=trace_file)
                self.logger.info("Monkey execution completed successfully")
                
            except Exception as e:
                self.logger.error(f"Monkey execution failed: {str(e)}")
                # Write error information to trace file
                error_msg = f"Monkey execution error: {str(e)}\n"
                trace_file.write(error_msg.encode('utf-8'))
                raise

    def _build_monkey_command(self, app: App, timeout_seconds: int) -> Command:
        """
        Build the Monkey command with configured parameters.
        
        Args:
            app: Application under test
            timeout_seconds: Command execution timeout
            
        Returns:
            Configured Command object for Monkey execution
        """
        # Start building command arguments
        cmd_args = [
            "-s", self.config["device_id"],
            "shell", "monkey"
        ]

        # Add verbosity flags
        verbosity = self.config["verbosity"]
        for _ in range(verbosity):
            cmd_args.append("-v")

        # Add random seed if specified
        if self.config["seed"] is not None:
            cmd_args.extend(["--seed", str(self.config["seed"])])

        # Add throttle delay if specified
        if self.config["throttle"] > 0:
            cmd_args.extend(["--throttle", str(self.config["throttle"])])

        # Add boolean flags
        if self.config["ignore_crashes"]:
            cmd_args.append("--ignore-crashes")
            
        if self.config["ignore_timeouts"]:
            cmd_args.append("--ignore-timeouts")
            
        if self.config["ignore_monitored_violations"]:
            cmd_args.append("--ignore-security-exceptions")
            
        if self.config["kill_process_after_error"]:
            cmd_args.append("--kill-process-after-error")
            
        if self.config["monitor_native_crashes"]:
            cmd_args.append("--monitor-native-crashes")

        # Add event type percentages
        event_percentages = self.config["event_percentages"]
        for event_type, percentage in event_percentages.items():
            if percentage is not None:
                cmd_args.extend([f"--pct-{event_type}", str(int(percentage))])

        # Add package constraint
        cmd_args.extend(["-p", app.package_name])

        # Add event count
        cmd_args.append(str(self.config["event_count"]))

        return Command("adb", cmd_args, timeout_seconds)

    def get_supported_event_types(self) -> list:
        """
        Get list of supported Monkey event types.
        
        Returns:
            List of supported event type names
        """
        return list(self.config["event_percentages"].keys())

    def get_tool_info(self) -> dict:
        """
        Get comprehensive Monkey tool information.
        
        Returns:
            Dictionary with tool information, capabilities, and current configuration
        """
        info = super().get_tool_info()
        info.update({
            "tool_spec": self.TOOL_SPEC.to_dict(),
            "supported_event_types": self.get_supported_event_types(),
            "current_event_count": self.config["event_count"],
            "current_seed": self.config["seed"],
            "version": self.TOOL_SPEC.version,
            "category": self.TOOL_SPEC.category.value
        })
        return info