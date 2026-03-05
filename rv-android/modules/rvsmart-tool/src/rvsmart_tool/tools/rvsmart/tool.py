"""
RVSmart Tool for rv-platform integration.

Wraps the RVSmart Java exploration agent as an AbstractTool for execution
within the rv-platform task execution framework. RVSmart runs on the Android
device via app_process, performing algorithmic or hybrid LLM-guided UI
exploration to trigger monitored operations.
"""

import json
import os
from typing import Any, Dict

from rv_android_core.commands.command import Command
from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import (
    RVToolExecutionError,
    RVToolTimeoutError,
)
from rv_android_core.util.jar_resolver import JarResolver
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager

# Tool constants
RVSMART_TOOL_NAME = "rvsmart"
RVSMART_DESCRIPTION = "Java exploration agent running inside emulator via app_process"
RVSMART_JAR_NAME = "rvsmart.jar"
RVSMART_DEVICE_JAR_PATH = "/data/local/tmp/rvsmart.jar"
RVSMART_DEVICE_STATIC_DATA_PATH = "/data/local/tmp/static_analysis.json"
RVSMART_DEVICE_CONFIG_PATH = "/data/local/tmp/rvsmart.properties"
RVSMART_MAIN_CLASS = "br.unb.cic.rvsmart.Main"
RVSMART_METRICS_PREFIX = "RVSMART_METRICS:"
RVSMART_METRICS_FILENAME = "rvsmart_metrics.json"


class RVSmartTool(AbstractTool):
    """
    RVSmart Java exploration agent for rv-platform integration.

    RVSmart is a Java-based tool that runs inside the Android emulator via
    app_process. It performs UI exploration using algorithmic strategies
    (DFS, random) or hybrid mode with LLM guidance to trigger monitored
    operations for runtime verification.

    ### Architectural Role:
    - Implements AbstractTool interface for platform integration
    - Manages JAR deployment and execution on the Android device
    - Pushes static analysis data and configuration to the device
    - Extracts metrics from the tool's stdout output

    ### Integration Points:
    - Registered via rv-platform on import (external tool)
    - Uses JarResolver for JAR file discovery
    - Receives static_data from platform StaticAnalysisComponent
    - Outputs metrics to rvsmart_metrics.json in results directory

    ### Tool Execution Flow:
    1. configure() stores variant configuration
    2. execute_tool_specific_logic() resolves JAR and pushes to device
    3. Optionally pushes static_analysis.json and rvsmart.properties
    4. Runs health check (--health-check)
    5. Executes main command via adb shell app_process
    6. Captures stdout to trace file and extracts metrics
    """

    TOOL_SPEC = ToolSpec.create_builtin_spec(
        name=RVSMART_TOOL_NAME,
        description=RVSMART_DESCRIPTION,
        url="https://github.com/PAMunb/rvsec",
        version="1.0.0",
        process_pattern="br.unb.cic.rvsmart",
    )

    # JAR search paths in priority order:
    # 1. os.path.dirname(__file__) — same directory as this module (JAR copied by mvn install)
    # 2. $RVSEC_HOME/rvsec/rvsec-android/rvsmart/target/rvsmart.jar
    # 3. $TOOLS_DIR/rvsmart/rvsmart.jar
    JAR_SEARCH_PATHS = [
        os.path.dirname(__file__),
        os.path.join(
            os.environ.get("RVSEC_HOME", ""), "rvsec", "rvsec-android", "rvsmart", "target"
        ),
        os.path.join(os.environ.get("TOOLS_DIR", ""), "rvsmart"),
    ]

    def __init__(self):
        """
        Initialize RVSmart tool.

        Sets up logging, JAR resolver, and prepares for configuration.
        """
        tool_spec = self.get_tool_spec()
        super().__init__(
            name=tool_spec.name,
            description=tool_spec.description,
            process_pattern=tool_spec.process_pattern,
        )

        # Initialize component logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvsmart_tool.tools.rvsmart", {CONTEXT_COMPONENT: "RVSmartTool"}
        )

        # JAR resolver for locating rvsmart.jar
        self.jar_resolver = JarResolver()

        # Configuration stored from configure() method
        self._tool_config: Dict[str, Any] = {}

        self.logger.info("RVSmart tool initialized")

    @classmethod
    def get_tool_spec(cls) -> ToolSpec:
        """
        Get tool specification for registration.

        Returns:
            ToolSpec instance with tool metadata
        """
        return cls.TOOL_SPEC

    @classmethod
    def get_variants(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get available RVSmart variants.

        Variants configure the exploration mode and throttle for different
        testing scenarios. The 'hybrid' variant enables LLM guidance via
        an API endpoint accessible from the emulator at 10.0.2.2.

        NOTE: timeout is ALWAYS controlled by Task.config, not by variants.
        The platform manages execution timeout uniformly across all tools.

        Returns:
            Dictionary mapping variant names to configuration parameters
        """
        return {
            "default": {
                "mode": "pure_algorithm",
                "throttle_ms": 50,
            },
            "mvp": {
                "mode": "pure_algorithm",
                "throttle_ms": 50,
            },
            "fast": {
                "mode": "pure_algorithm",
                "throttle_ms": 30,
            },
            "hybrid": {
                "mode": "multimode",
                "llm_base_url": "http://10.0.2.2:30000/v1",
            },
        }

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure tool with resolved variant parameters.

        Called by ToolFactory after resolving variant configuration.
        Stores configuration for use in execute_tool_specific_logic.

        Args:
            config: Configuration dictionary with tool-specific parameters
        """
        self._tool_config = config.copy() if config else {}
        self.logger.info(
            f"RVSmart tool configured: mode={self._tool_config.get('mode', 'default')}"
        )

    @ErrorHandler.handle_errors(
        component="RVSmartTool", phase="execute_tool_specific_logic", reraise=True
    )
    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
        """
        Execute RVSmart exploration on the device.

        Pushes the JAR, static data, and config to the device, runs a
        health check, then executes the main exploration command. Output
        is captured to the trace file and metrics are extracted.

        Args:
            task: Task configuration with device, timeout, static data
            app: Application under test
        """
        self.logger.info(f"Executing RVSmart for {app.package_name}")

        # Get device serial from task configuration
        device_serial = "emulator-5554"
        task_config = task.config if hasattr(task, "config") else None
        if task_config and hasattr(task_config, "device_id") and task_config.device_id:
            device_serial = task_config.device_id

        # Get timeout from task configuration
        timeout_seconds = 300
        if task_config and hasattr(task_config, "timeout") and task_config.timeout:
            timeout_seconds = task_config.timeout

        # Step 1: Resolve and push JAR to device
        jar_path = self._resolve_jar_path()
        self._push_file_to_device(
            jar_path, RVSMART_DEVICE_JAR_PATH, device_serial, task.result.trace_file
        )

        # Step 2: Optionally push static analysis JSON file to device
        static_json_path = self._find_static_analysis_file(task)
        if static_json_path:
            self._push_file_to_device(
                static_json_path,
                RVSMART_DEVICE_STATIC_DATA_PATH,
                device_serial,
                task.result.trace_file,
            )
            self.logger.info("Pushed static analysis data to device")

        # Step 3: Optionally generate and push config properties
        if self._tool_config:
            self._push_config_properties(device_serial, task.result.trace_file)

        # Step 4: Run health check
        self._run_health_check(device_serial, task.result.trace_file)

        # Step 5: Build and execute main command
        main_cmd = self._build_main_command(
            app, device_serial, timeout_seconds, static_json_path is not None
        )

        self.logger.info(f"Starting RVSmart exploration (timeout={timeout_seconds}s)")

        try:
            with open(task.result.trace_file, "wb") as trace_file:
                self._execute_and_check_command(
                    main_cmd, stdout=trace_file, stderr=trace_file
                )
        except RVToolTimeoutError:
            # Timeout is expected behavior for exploration tools
            self.logger.info(
                f"RVSmart execution timed out after {timeout_seconds} seconds (expected behavior)"
            )
            raise

        # Step 6: Extract metrics from trace file
        self._extract_metrics(task)

        self.logger.info("RVSmart execution completed successfully")

    def _resolve_jar_path(self) -> str:
        """
        Resolve the path to rvsmart.jar using priority search.

        Priority:
        1. os.path.dirname(__file__) — tool module directory (APE/FastBot pattern)
        2. $RVSEC_HOME/rvsec-android/rvsmart/target/rvsmart.jar
        3. $TOOLS_DIR/rvsmart/rvsmart.jar

        Returns:
            Absolute path to rvsmart.jar

        Raises:
            RVToolExecutionError: If rvsmart.jar is not found
        """
        search_paths = self._get_jar_search_paths()

        try:
            return self.jar_resolver.resolve_jar_path(RVSMART_JAR_NAME, search_paths)
        except Exception as e:
            error_msg = (
                "rvsmart.jar not found. Ensure RVSmart is built and available at one of: "
                f"{search_paths}"
            )
            self.logger.error(error_msg)
            raise RVToolExecutionError(error_msg, tool_name=self.name, cause=e)

    @classmethod
    def _get_jar_search_paths(cls):
        """
        Build JAR search paths from current environment.

        Evaluates environment variables at call time (not class load time)
        to support dynamic configuration.

        Returns:
            List of directories to search for rvsmart.jar
        """
        paths = [
            # Same directory as this file (JAR copied by mvn install)
            os.path.dirname(__file__),
        ]
        rvsec_home = os.environ.get("RVSEC_HOME", "")
        if rvsec_home:
            paths.append(os.path.join(rvsec_home, "rvsec", "rvsec-android", "rvsmart", "target"))
        tools_dir = os.environ.get("TOOLS_DIR", "")
        if tools_dir:
            paths.append(os.path.join(tools_dir, "rvsmart"))
        return paths

    def _push_file_to_device(
        self,
        local_path: str,
        device_path: str,
        device_serial: str,
        trace_file_path: str,
    ) -> None:
        """
        Push a file to the Android device via adb push.

        Args:
            local_path: Local file path
            device_path: Target path on device
            device_serial: Device serial number
            trace_file_path: Trace file for logging push output

        Raises:
            RVToolExecutionError: If push fails
        """
        self.logger.info(f"Pushing {local_path} to {device_path}")

        push_cmd = Command(
            "adb",
            ["-s", device_serial, "push", "-a", "-p", local_path, device_path],
            timeout=60,
        )

        with open(trace_file_path, "ab") as trace_file:
            result = push_cmd.invoke(stdout=trace_file)
            if result.is_failure():
                error_msg = (
                    f"Failed to push {local_path} to device (exit code {result.code})"
                )
                if result.has_error_output():
                    error_msg += f". Error: {result.get_stderr_text()}"
                self.logger.error(error_msg)
                raise RVToolExecutionError(error_msg, tool_name=self.name, cause=None)

        self.logger.debug(f"Pushed {local_path} to {device_path}")

    def _find_static_analysis_file(self, task: Task):
        """
        Find the static analysis JSON file on disk for this task.

        The StaticAnalysisComponent copies the JSON to task.results_dir as
        <apk_name>.json. We push this file directly instead of re-serializing
        the Pydantic model.

        Args:
            task: Platform task

        Returns:
            Path to the JSON file if it exists, None otherwise
        """
        if not hasattr(task, "results_dir") or not task.results_dir:
            return None
        if not hasattr(task, "config") or not task.config:
            return None

        json_path = os.path.join(
            task.results_dir, f"{task.config.apk_name}.json"
        )
        if os.path.isfile(json_path):
            self.logger.info(f"Found static analysis file: {json_path}")
            return json_path
        return None

    def _push_config_properties(self, device_serial: str, trace_file_path: str) -> None:
        """
        Generate rvsmart.properties from tool config and push to device.

        Args:
            device_serial: Device serial number
            trace_file_path: Trace file for logging
        """
        import tempfile

        # Build properties content from tool config
        lines = []
        for key, value in self._tool_config.items():
            lines.append(f"{key}={value}")
        properties_content = "\n".join(lines) + "\n"

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".properties", delete=False
        ) as tmp:
            tmp.write(properties_content)
            tmp_path = tmp.name

        try:
            self._push_file_to_device(
                tmp_path, RVSMART_DEVICE_CONFIG_PATH, device_serial, trace_file_path
            )
            self.logger.debug("Pushed rvsmart.properties to device")
        finally:
            os.unlink(tmp_path)

    def _run_health_check(self, device_serial: str, trace_file_path: str) -> None:
        """
        Run rvsmart health check on the device to verify JAR is functional.

        Args:
            device_serial: Device serial number
            trace_file_path: Trace file for logging

        Raises:
            RVToolExecutionError: If health check fails
        """
        self.logger.info("Running RVSmart health check")

        health_cmd = Command(
            "adb",
            [
                "-s",
                device_serial,
                "shell",
                f"CLASSPATH={RVSMART_DEVICE_JAR_PATH}",
                "/system/bin/app_process",
                "/data/local/tmp/",
                RVSMART_MAIN_CLASS,
                "--health-check",
            ],
            timeout=30,
        )

        with open(trace_file_path, "ab") as trace_file:
            result = health_cmd.invoke(stdout=trace_file, stderr=trace_file)
            if result.is_failure():
                self.logger.warning(
                    f"RVSmart health check failed (exit code {result.code}), "
                    "proceeding with execution anyway"
                )
            else:
                self.logger.info("RVSmart health check passed")

    def _build_main_command(
        self, app: App, device_serial: str, timeout_seconds: int, has_static_data: bool
    ) -> Command:
        """
        Build the main rvsmart execution command.

        Command format:
        adb shell CLASSPATH=/data/local/tmp/rvsmart.jar /system/bin/app_process
            /data/local/tmp/ br.unb.cic.rvsmart.Main
            --package <pkg> --timeout <s>
            [--static-data /data/local/tmp/static_analysis.json]
            [--config /data/local/tmp/rvsmart.properties]
            [--mode <mode>]

        Args:
            app: Application under test
            device_serial: Device serial number
            timeout_seconds: Execution timeout in seconds
            has_static_data: Whether static analysis data was pushed

        Returns:
            Configured Command for rvsmart execution
        """
        cmd_args = [
            "-s",
            device_serial,
            "shell",
            f"CLASSPATH={RVSMART_DEVICE_JAR_PATH}",
            "/system/bin/app_process",
            "/data/local/tmp/",
            RVSMART_MAIN_CLASS,
            "--package",
            app.package_name,
            "--timeout",
            str(timeout_seconds),
        ]

        # Add static data path if available
        if has_static_data:
            cmd_args.extend(["--static-data", RVSMART_DEVICE_STATIC_DATA_PATH])

        # Add config path if config was pushed
        if self._tool_config:
            cmd_args.extend(["--config", RVSMART_DEVICE_CONFIG_PATH])

        # Add mode if specified
        mode = self._tool_config.get("mode")
        if mode:
            cmd_args.extend(["--mode", mode])

        return Command("adb", cmd_args, timeout_seconds)

    def _extract_metrics(self, task: Task) -> None:
        """
        Extract metrics from the trace file.

        Reads the trace file looking for a line starting with RVSMART_METRICS:
        prefix, parses the JSON after the prefix, and writes it to
        rvsmart_metrics.json in the results directory.

        If no metrics line is found, writes a default metrics file with
        status "metrics_unavailable".

        Args:
            task: Task with result containing trace_file path
        """
        trace_path = task.result.trace_file
        metrics_data = None

        try:
            with open(trace_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(RVSMART_METRICS_PREFIX):
                        json_str = line[len(RVSMART_METRICS_PREFIX) :].strip()
                        metrics_data = json.loads(json_str)
                        break
        except Exception as e:
            self.logger.warning(f"Error reading trace file for metrics: {e}")

        if metrics_data is None:
            self.logger.warning("No RVSMART_METRICS line found in trace file")
            metrics_data = {"status": "metrics_unavailable"}

        # Write metrics to file in results directory
        results_dir = os.path.dirname(trace_path)
        metrics_path = os.path.join(results_dir, RVSMART_METRICS_FILENAME)

        try:
            with open(metrics_path, "w", encoding="utf-8") as f:
                json.dump(metrics_data, f, indent=2)
            self.logger.info(f"Metrics written to {metrics_path}")
        except Exception as e:
            self.logger.warning(f"Failed to write metrics file: {e}")

    def get_tool_info(self) -> dict:
        """
        Get comprehensive tool information.

        Returns:
            Dictionary with tool information and current configuration
        """
        info = super().get_tool_info()
        info.update(
            {
                "tool_spec": self.TOOL_SPEC.to_dict(),
                "current_config": self._tool_config,
                "version": self.TOOL_SPEC.version,
                "url": self.TOOL_SPEC.url,
            }
        )
        return info
