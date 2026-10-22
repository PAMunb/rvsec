"""
APE (Android Programmatic Events) testing tool implementation.

This module provides integration with the APE Android testing framework,
enabling CEGAR-based model abstraction refinement for systematic exploration.
"""

import os
import tempfile
import time
from typing import Any, Dict, List

from rv_android_core.commands.command import Command
from rv_android_core.constants import TOOL_TEARDOWN_GRACE_S
from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import RVToolExecutionError
from rv_android_core.util.jar_resolver import JarResolver

APE_DEVICE_PROPERTIES_PATH = "/data/local/tmp/ape.properties"

# Upstream APE writes a screenshot and a GUI-tree XML on every step by default. These
# lines make it capture once per new abstract state instead, the capture policy the
# APE-RV jar applies by default, so the two arms of a comparison capture the same
# things. This is the only setting of the `ape` tool that departs from the author's
# defaults. APE reads /data/local/tmp/ape.properties first, then /sdcard/ape.properties.
APE_PROPERTIES_CONTENT = (
    "ape.takeScreenshotForEveryStep=false\n"
    "ape.saveGUITreeToXmlEveryStep=false\n"
    "ape.takeScreenshotForNewState=true\n"
)


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
    - Same host timing as APE-RV: the command timeout is the budget plus
      TOOL_TEARDOWN_GRACE_S, and a run is judged by elapsed time, not exit code
    - Pushes an ape.properties that captures on each new abstract state rather
      than on every step

    ### Tool Variants:
    APE supports different exploration strategies as variants:
    - sata: SATA (Static Analysis Targeted Abstraction) strategy
    - bfs: Breadth-first search exploration
    - dfs: Depth-first search exploration
    - random: Random exploration strategy
    """

    # APE reuses the Monkey entry point (com.android.commands.monkey.Monkey)
    # as its Java main class, so process_pattern must match the same pattern
    # used by Monkey. The platform distinguishes them by which tool was started.
    TOOL_SPEC = ToolSpec.create_builtin_spec(
        name="ape",
        description="APE CEGAR-based model abstraction testing tool for systematic Android exploration",
        url="https://github.com/tjusenchen/ape",
        version="1.0.0",
        process_pattern="com.android.commands.monkey",
    )

    # Available exploration strategies that can be used as variants
    AVAILABLE_STRATEGIES = ["sata", "bfs", "dfs", "random"]

    def __init__(self):
        """
        Initialize the APE tool with rv-android-core infrastructure.

        State:
            jar_resolver: JarResolver for locating APE jar files on disk.
            config: Dictionary holding strategy, running_minutes, device_serial,
                and other APE-specific parameters. Populated by configure().
        """
        # Initialize base class with tool spec parameters
        tool_spec = self.get_tool_spec()
        super().__init__(
            name=tool_spec.name,
            description=tool_spec.description,
            process_pattern=tool_spec.process_pattern,
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
            "default": {"strategy": "sata", "running_minutes": 5, "debug_mode": True},
            "sata": {"strategy": "sata", "running_minutes": 10, "debug_mode": False},
            "bfs": {"strategy": "bfs", "running_minutes": 5, "debug_mode": False},
            "dfs": {"strategy": "dfs", "running_minutes": 5, "debug_mode": False},
            "random": {"strategy": "random", "running_minutes": 5, "debug_mode": False},
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

        # Build config with explicit defaults, then spread incoming config.
        # Same merge pattern as DroidBot — see DroidBotTool.configure().
        self.config = {
            "strategy": config["strategy"],
            "running_minutes": config.get("running_minutes", 5),
            "device_serial": config.get("device_serial", "emulator-5554"),
            "debug_mode": config.get("debug_mode", True),
            "output_dir": config.get("output_dir", None),
            "ape_jar_path": config.get("ape_jar_path", None),
            **config,  # Spread ensures any extra/future parameters are preserved
        }

        self.logger.info(
            f"Configured APE tool - Strategy: {self.config['strategy']}, "
            f"Duration: {self.config['running_minutes']}min"
        )

    @ErrorHandler.handle_errors(
        component="APETool", phase="execute_tool_specific_logic", reraise=True
    )
    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
        """
        Run APE on the device for the task's budget and check that it ran for it.

        ### Execution Workflow:
        1. Resolve the budget from the task configuration
        2. Resolve the APE jar and push it to the device
        3. Push ape.properties with the capture settings
        4. Run APE with a command timeout of the budget plus TOOL_TEARDOWN_GRACE_S
        5. Compare the elapsed time with the budget minus TOOL_TEARDOWN_GRACE_S

        Args:
            task: Task configuration containing timeout and other parameters
            app: Application under test with package name and metadata

        Raises:
            RVCommandTimeoutError: APE was still running at the command timeout.
                AbstractTool.execute() converts it to RVToolTimeoutError, the
                normal end of a run.
            RVToolExecutionError: The jar or properties push failed, or APE
                returned more than TOOL_TEARDOWN_GRACE_S short of its budget.
        """
        # --- Step 1: Resolve execution parameters ---
        self.logger.info(f"Executing APE tool for {app.package_name}")

        # APE's --running-minutes flag requires minutes, but the platform uses
        # seconds. Convert here, clamping to a minimum of 1 minute so APE
        # always has a meaningful exploration window.
        timeout_in_seconds = getattr(
            task.config, "timeout", self.config["running_minutes"] * 60
        )
        timeout_in_minutes = int(timeout_in_seconds / 60)
        if timeout_in_minutes == 0:
            timeout_in_minutes = 1

        self.logger.debug(
            f"Strategy: {self.config['strategy']}, Running minutes: {timeout_in_minutes}"
        )
        self.logger.info(
            f"APE execution timeout: {timeout_in_seconds} seconds ({timeout_in_minutes} minutes)"
        )

        output_dir = os.path.join(os.path.dirname(task.result.trace_file), "ape_output")
        os.makedirs(output_dir, exist_ok=True)

        # --- Step 2: Resolve and deploy the APE jar and its properties ---
        # APE runs inside the Android runtime via app_process, so the jar must
        # be pushed to /data/local/tmp/ before each execution. A failed push of
        # either file raises before APE starts.
        ape_jar_path = self._resolve_ape_jar_path()
        self._push_ape_jar_to_device(ape_jar_path, task.result.trace_file)
        self._push_ape_properties(task.result.trace_file)

        # --- Step 3: Build and execute APE shell command ---
        ape_cmd = self._build_ape_shell_command(
            app, timeout_in_minutes, timeout_in_seconds
        )

        cmd_str = f"{ape_cmd.command} {' '.join(ape_cmd.args)}"
        self.logger.debug(f"APE command: {cmd_str}")
        self.logger.info(f"Starting APE execution for {app.package_name}")

        started = time.monotonic()

        # invoke() rather than _execute_and_check_command(): the exit code is not
        # consulted. APE exits non-zero when the app under test crashes, which is
        # data the run exists to collect, and a device that went away also exits
        # non-zero, so the code cannot tell a lost run from a good one. A command
        # timeout raises RVCommandTimeoutError, which propagates to
        # AbstractTool.execute() and ends the run normally. Both streams go to the
        # trace file to keep APE's output off the console.
        with open(task.result.trace_file, "wb") as trace_file:
            result = ape_cmd.invoke(stdout=trace_file, stderr=trace_file)
        if result.code != 0:
            self.logger.debug(
                f"APE exited with code {result.code} "
                "(non-zero is normal when app crashes are detected)"
            )

        # --- Step 4: Check that APE ran for its budget ---
        # APE ends on its own --running-minutes timer, so a run that returned more
        # than the grace short of the budget did not explore it, whatever ended it.
        # Raising makes rv-platform store the task as ERROR, which its resume
        # re-executes. This is the completion rule of APE-RV.
        elapsed_seconds = time.monotonic() - started
        completion_floor = timeout_in_seconds - TOOL_TEARDOWN_GRACE_S
        if elapsed_seconds < completion_floor:
            raise RVToolExecutionError(
                f"APE returned after {elapsed_seconds:.0f}s of a "
                f"{timeout_in_seconds}s exploration budget "
                f"(floor {completion_floor}s): the exploration was truncated, "
                "so this run did not happen as declared",
                tool_name=self.name,
                cause=None,
            )

        self.logger.info("APE execution completed successfully")

    def _resolve_ape_jar_path(self) -> str:
        """
        Resolve the path to the APE jar file using centralized JarResolver.

        Returns:
            Path to APE jar file

        Raises:
            RVToolExecutionError: If APE jar file is not found
        """
        # Use JarResolver for centralized JAR resolution (gh55 D10: TOOLS_DIR is
        # an L1 cross-layer infra read; the resolver consults it internally so
        # this method must NOT call os.environ at L2). Search paths ordered by
        # specificity: configured path first (handled below), co-located with
        # this module file (Docker images bundle jars alongside the tool code),
        # then standard installs. The resolver also adds RVSEC_HOME-derived and
        # TOOLS_DIR-derived paths automatically inside _build_search_paths.
        search_paths = [
            os.path.dirname(__file__),
            "/opt/rv-android/tools/ape",
            "./tools/ape",
            "../tools/ape",
        ]

        try:
            # Check configured path first
            if self.config.get("ape_jar_path"):
                return self.jar_resolver.resolve_jar_path(
                    "ape.jar", [os.path.dirname(self.config["ape_jar_path"])]
                )

            # Use JarResolver with search paths
            return self.jar_resolver.resolve_jar_path("ape.jar", search_paths)
        except FileNotFoundError as e:
            error_msg = (
                "APE jar file not found. Please ensure APE is properly installed."
            )
            self.logger.error(error_msg)
            raise RVToolExecutionError(error_msg, tool_name=self.name, cause=e)

    def _push_ape_jar_to_device(self, jar_path: str, trace_file_path: str) -> None:
        """
        Push APE jar to Android device (matching original implementation).

        Args:
            jar_path: Local path to APE jar file
            trace_file_path: Path to trace file for logging output

        Raises:
            RVToolExecutionError: If jar push fails
        """
        # /data/local/tmp/ is writable without root and survives across ADB
        # sessions, making it the standard staging location for tool jars.
        device_jar_path = "/data/local/tmp/ape.jar"

        self.logger.info(f"Pushing APE jar from {jar_path} to {device_jar_path}")

        push_cmd = Command(
            "adb",
            [
                "-s",
                self.config["device_serial"],
                "push",
                "-a",
                "-p",
                jar_path,
                device_jar_path,
            ],
            timeout=60,
        )  # 60 seconds timeout for push

        with open(trace_file_path, "ab") as trace_file:
            trace_file.write("\n--- APE Jar Push ---\n".encode("utf-8"))
            result = push_cmd.invoke(stdout=trace_file)

            if result.is_failure():
                error_msg = (
                    f"Failed to push APE jar to device with exit code {result.code}"
                )
                if result.has_error_output():
                    error_msg += f". Error: {result.get_stderr_text()}"

                self.logger.error(error_msg)
                raise RVToolExecutionError(error_msg, tool_name=self.name, cause=None)

        self.logger.debug("APE jar pushed to device successfully")

    def _push_ape_properties(self, trace_file_path: str) -> None:
        """
        Push APE_PROPERTIES_CONTENT to /data/local/tmp/ape.properties.

        The file is not removed after the run: each task boots its own emulator
        with -read-only and -no-snapshot-save, so it does not outlive the task.

        Args:
            trace_file_path: Path to trace file for logging output

        Raises:
            RVToolExecutionError: If the push fails
        """
        self.logger.info(f"Pushing APE properties to {APE_DEVICE_PROPERTIES_PATH}")

        # adb push needs a local file. delete=False so the file survives the
        # with-block until the push has read it; it is removed in the finally.
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".properties", delete=False
        ) as tmp:
            tmp.write(APE_PROPERTIES_CONTENT)
            tmp_path = tmp.name

        try:
            push_cmd = Command(
                "adb",
                [
                    "-s",
                    self.config["device_serial"],
                    "push",
                    tmp_path,
                    APE_DEVICE_PROPERTIES_PATH,
                ],
                timeout=60,
            )

            with open(trace_file_path, "ab") as trace_file:
                trace_file.write("\n--- APE Properties Push ---\n".encode("utf-8"))
                result = push_cmd.invoke(stdout=trace_file)

                if result.is_failure():
                    error_msg = (
                        "Failed to push APE properties to device with exit code "
                        f"{result.code}"
                    )
                    if result.has_error_output():
                        error_msg += f". Error: {result.get_stderr_text()}"

                    self.logger.error(error_msg)
                    raise RVToolExecutionError(
                        error_msg, tool_name=self.name, cause=None
                    )
        finally:
            os.unlink(tmp_path)

        self.logger.debug("APE properties pushed to device successfully")

    def _build_ape_shell_command(
        self, app: App, timeout_minutes: int, timeout_seconds: int
    ) -> Command:
        """
        Build the APE command using original ADB shell format.

        Args:
            app: Application under test
            timeout_minutes: Execution timeout in minutes
            timeout_seconds: Exploration budget in seconds

        Returns:
            Command with timeout = timeout_seconds + TOOL_TEARDOWN_GRACE_S
        """
        # APE piggybacks on the Monkey entry point class but with its own
        # CEGAR-based exploration engine loaded via the --ape flag. The
        # CLASSPATH env var and app_process invocation are the standard way
        # to run custom Java code inside Android's Dalvik/ART runtime without
        # packaging it as an APK.
        cmd_args = [
            "-s",
            self.config["device_serial"],
            "shell",
            "CLASSPATH=/data/local/tmp/ape.jar",
            "/system/bin/app_process",
            "/data/local/tmp/",
            "com.android.commands.monkey.Monkey",
            "-p",
            app.package_name,
            "--running-minutes",
            str(timeout_minutes),
            "--ape",
            self.config["strategy"],
        ]

        # The grace lets APE end on its own --running-minutes timer and finish its
        # teardown before the host kills it. APE-RV reads the same constant, so both
        # arms of a comparison get the same host time.
        return Command("adb", cmd_args, timeout_seconds + TOOL_TEARDOWN_GRACE_S)

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
        info.update(
            {
                "tool_spec": self.TOOL_SPEC.to_dict(),
                "available_strategies": self.get_available_strategies(),
                "current_strategy": self.config["strategy"],
                "current_running_minutes": self.config["running_minutes"],
                "version": self.TOOL_SPEC.version,
                "url": self.TOOL_SPEC.url,
            }
        )
        return info
