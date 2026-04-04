"""
Android Monkey testing tool implementation.

Monkey generates pseudo-random streams of user events for stress testing
and monitored operations validation in Android applications.
"""

from typing import Any, Dict

from rv_android_core.commands.command import Command
from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


class MonkeyTool(AbstractTool):
    """
    Android Monkey tool for random event generation and monitored operations testing.

    ### Architectural Decisions:
    - Inherits directly from AbstractTool for simplified architecture
    - Provides clean interface to Android Monkey testing framework
    - Supports configuration through simple parameter dictionary
    - Implements random event generation for stress testing
    - Integrates with RV-Android monitored operations infrastructure

    ### Role in the System:
    - Generates pseudo-random user events for Android application testing
    - Provides stress testing capabilities for monitored operations validation
    - Enables exploration of unexpected application states and behaviors
    - Supports configurable event generation patterns and constraints
    - Facilitates discovery of crashes and performance issues

    ### Key Features:
    - Multiple event types (touch, gesture, navigation, system)
    - Configurable event generation parameters and constraints
    - Execution timeout and event count limits
    - Integration with monitored operations instrumentation
    - Device communication and command execution
    """

    # Simplified tool specification
    TOOL_SPEC = ToolSpec.create_builtin_spec(
        name="monkey",
        description="Android UI/Application exerciser generating pseudo-random user events",
        url="https://developer.android.com/studio/test/monkey",
        version="1.0.0",
        process_pattern="com.android.commands.monkey",
    )

    def __init__(
        self, name: str = None, description: str = None, process_pattern: str = None
    ):
        """
        Initialize Monkey tool with rv-android-core infrastructure.
        """
        super().__init__(
            name=name or self.TOOL_SPEC.name,
            description=description or self.TOOL_SPEC.description,
            process_pattern=process_pattern or self.TOOL_SPEC.process_pattern,
        )

        # Initialize rv-android-core infrastructure components
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_tools.builtin.monkey", {CONTEXT_COMPONENT: "MonkeyTool"}
        )

        # Default Monkey configuration
        self.config = {
            "event_count": 1_000_000_000,  # Number of events to generate
            "seed": None,  # Random seed for reproducibility
            "throttle": 0,  # Delay between events (ms)
            "device_id": "emulator-5554",  # Target device (fallback default)
            "verbosity": 2,  # Verbosity level (0-3)
            "ignore_crashes": False,  # Continue after crashes
            "ignore_timeouts": False,  # Continue after ANR timeouts
            "ignore_monitored_violations": True,  # Ignore monitored operations violations
            "kill_process_after_error": False,  # Kill process after error
            "monitor_native_crashes": True,  # Monitor for native crashes
            "event_percentages": {  # Event type percentages
                "touch": None,  # Touch events
                "motion": None,  # Motion events
                "trackball": None,  # Trackball events
                "syskeys": None,  # System key events
                "nav": None,  # Navigation events
                "majornav": None,  # Major navigation events
                "appswitch": None,  # App switch events
                "flip": None,  # Keyboard flip events
                "anyevent": None,  # Any event types
            },
        }

        self.logger.info("Initialized Monkey tool for random event generation")

    @classmethod
    def get_tool_spec(cls):
        """Get tool specification for registration."""
        return cls.TOOL_SPEC

    @classmethod
    def get_variants(cls) -> Dict[str, Dict[str, Any]]:
        """Get available Monkey variants with different configurations."""
        return {
            "default": {
                "event_count": 1000,
                "seed": None,
                "throttle": 0,
                "verbosity": 2,
                "ignore_crashes": False,
                "ignore_timeouts": False,
            },
            "fast": {
                "event_count": 500,
                "seed": 12345,
                "throttle": 0,
                "verbosity": 1,
                "ignore_crashes": True,
                "ignore_timeouts": True,
            },
            "stress": {
                "event_count": 10000,
                "seed": None,
                "throttle": 0,
                "verbosity": 3,
                "ignore_crashes": False,
                "ignore_timeouts": False,
            },
        }

    def configure(self, config: Dict[str, Any]) -> None:
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
        if not config:
            return

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
                self.logger.warning(
                    f"Invalid event_count value: {config['event_count']}"
                )

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
            "ignore_crashes",
            "ignore_timeouts",
            "ignore_monitored_violations",
            "kill_process_after_error",
            "monitor_native_crashes",
        ]

        for flag in boolean_flags:
            if flag in config:
                self.config[flag] = bool(config[flag])
                self.logger.debug(f"Set Monkey {flag} to: {self.config[flag]}")

        # Update event percentages
        if "event_percentages" in config and isinstance(
            config["event_percentages"], dict
        ):
            for event_type, percentage in config["event_percentages"].items():
                if event_type in self.config["event_percentages"]:
                    try:
                        if percentage is not None:
                            pct = float(percentage)
                            if 0 <= pct <= 100:
                                self.config["event_percentages"][event_type] = pct
                                self.logger.debug(
                                    f"Set {event_type} percentage to: {pct}%"
                                )
                            else:
                                self.logger.warning(
                                    f"Percentage for {event_type} must be 0-100"
                                )
                        else:
                            self.config["event_percentages"][event_type] = None
                    except (ValueError, TypeError):
                        self.logger.warning(
                            f"Invalid percentage for {event_type}: {percentage}"
                        )

    @ErrorHandler.handle_errors(
        component="MonkeyTool", phase="execute_tool_specific_logic", reraise=True
    )
    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
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
        timeout_in_seconds = getattr(task.config, "timeout", 300)  # Default 5 minutes

        self.logger.info(f"Monkey execution timeout: {timeout_in_seconds} seconds")

        # Build Monkey command
        monkey_cmd = self._build_monkey_command(app, timeout_in_seconds)

        # Build command string for logging
        cmd_str = f"{monkey_cmd.command} {' '.join(monkey_cmd.args)}"
        self.logger.debug(f"Monkey command: {cmd_str}")

        # Execute Monkey testing with centralized error handling
        self.logger.info(f"Starting Monkey execution for {app.package_name}")

        # Execute command with output redirection (binary mode for command output)
        with open(task.result.trace_file, "wb") as trace_file:
            # Use centralized command execution with error handling
            # Redirect both stdout and stderr to trace file to prevent console flooding
            self._execute_and_check_command(
                monkey_cmd, stdout=trace_file, stderr=trace_file
            )

        # Append success information to trace file (text mode for metadata)
        # with open(task.result.trace_file, 'a', encoding='utf-8') as trace_file:
        #     success_info = f"\n--- Monkey Execution Completed ---\n"
        #     success_info += f"Events: {event_count}\n"
        #     success_info += f"Command: {cmd_str}\n"
        #     trace_file.write(success_info)

        self.logger.info("Monkey execution completed successfully")

    def _build_monkey_command(self, app: App, timeout_seconds: int) -> Command:
        """
        Build the Monkey command with validated parameters from self.config.

        Constructs ADB shell command for Monkey tool execution with appropriate
        device targeting, verbosity level, security exception handling, and event count configuration.

        Args:
            app: Application under test containing package name and metadata
            timeout_seconds: Command execution timeout in seconds

        Returns:
            Configured Command object for Monkey execution
        """
        cmd_args = [
            "-s",
            self.config["device_id"],
            "shell",
            "monkey",
        ]

        # Verbosity flags (-v repeated N times)
        for _ in range(self.config.get("verbosity", 2)):
            cmd_args.append("-v")

        if self.config.get("ignore_crashes"):
            cmd_args.append("--ignore-crashes")

        if self.config.get("ignore_timeouts"):
            cmd_args.append("--ignore-timeouts")

        cmd_args.append("--ignore-security-exceptions")

        throttle = self.config.get("throttle", 0)
        if throttle > 0:
            cmd_args.extend(["--throttle", str(throttle)])

        seed = self.config.get("seed")
        if seed is not None:
            cmd_args.extend(["-s", str(seed)])

        cmd_args.extend(["-p", app.package_name])
        cmd_args.append(
            str(1_000_000_000)
        )  # Effectively infinite — timeout controls execution duration

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
            Dictionary with tool information and current configuration
        """
        info = super().get_tool_info()
        info.update(
            {
                "tool_spec": self.TOOL_SPEC.to_dict(),
                "supported_event_types": self.get_supported_event_types(),
                "current_event_count": self.config["event_count"],
                "current_seed": self.config["seed"],
                "version": self.TOOL_SPEC.version,
                "url": self.TOOL_SPEC.url,
            }
        )
        return info
