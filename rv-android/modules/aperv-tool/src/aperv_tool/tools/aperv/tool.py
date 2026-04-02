"""
ApeRV Tool for rv-platform integration.

Wraps the enhanced APE-RV binary (ape-rv.jar) as an AbstractTool for execution
within the rv-platform task execution framework. APE-RV runs on the Android
device via app_process, performing model-based UI exploration using SATA, BFS,
random, or DFS strategies to trigger monitored operations.

### Role in the System:

ApeRVTool is the rv-platform plugin for APE-RV, an enhanced fork of the AOSP
Monkey tool that implements model-based testing via the Widget Table Graph (WTG)
model. Within rv-platform, it sits alongside other AbstractTool implementations
(rvsmart-tool, rv-agent) and is selected by experiment configuration.

### Key Features:

- JAR deployment: resolves ape-rv.jar via priority search and pushes to the device
- Strategy selection: SATA (adaptive random), BFS, DFS, and random exploration
- Properties injection: generates ape.properties with throttle configuration
- Timeout-aware execution: treats timeout as expected exit for exploration tools

### Architectural Decisions:

- process_pattern is shared with the builtin ape tool; ape and aperv must not
  run concurrently on the same device (INV-APV-07, D8)
- Working directory is /system/bin rather than /data/local/tmp/ because the
  enhanced binary requires system-level resource resolution (INV-APV-04, D7)
- Coverage collection is delegated to the rv-android logcat infrastructure
  rather than parsing APE-RV output directly

### Integration Points:

- Input: Task (device serial, timeout, trace file path), App (package name)
- Output: trace file with APE-RV stdout, ape.properties pushed to device
- Upstream: JarResolver finds ape-rv.jar; rv-platform supplies Task and App
- Downstream: rv-android logcat reads Coverage.aj output during execution
"""

import os
import tempfile
from typing import Any, Dict

from rv_android_core.commands.command import Command
from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import (
    ConfigurationError,
    RVCommandTimeoutError,
    RVToolExecutionError,
    RVToolTimeoutError,
)
from rv_android_core.util.jar_resolver import JarResolver
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager

# Tool constants
APERV_TOOL_NAME = "aperv"
APERV_JAR_NAME = "ape-rv.jar"
APERV_DEVICE_JAR_PATH = "/data/local/tmp/ape-rv.jar"
APERV_DEVICE_PROPERTIES_PATH = "/data/local/tmp/ape.properties"
APERV_MAIN_CLASS = "com.android.commands.monkey.Monkey"

# Strategies accepted by configure(). "dfs" is accepted but has no named variant
# (accessible via parameter override, e.g. aperv:default@strategy=dfs). See D6.
APERV_AVAILABLE_STRATEGIES = ["sata", "random", "bfs", "dfs"]

# Maps Python config key -> Java ape.properties key.
# Keys in _tool_config that appear here are written to ape.properties.
# Keys NOT here (strategy, mop_data) are Python-only and not written.
APERV_PROPERTY_MAPPING = {
    # Exploration parameters
    "default_epsilon": "ape.defaultEpsilon",
    "graph_stable_restart_threshold": "ape.graphStableRestartThreshold",
    "state_stable_restart_threshold": "ape.stateStableRestartThreshold",
    "fuzzing_rate": "ape.fuzzingRate",
    "do_fuzzing": "ape.doFuzzing",
    "throttle_for_activity_transition": "ape.throttleForActivityTransition",
    "throttle_ms": "ape.defaultGUIThrottle",
    "max_extra_priority_aliased_actions": "ape.maxExtraPriorityAliasedActions",
    "max_states_per_activity": "ape.maxStatesPerActivity",
    "trivial_activity_rank_threshold": "ape.trivialActivityRankThreshold",
    "do_back_to_trivial_activity": "ape.doBackToTrivialActivity",
    # MOP weight parameters
    "mop_weight_direct": "ape.mopWeightDirect",
    "mop_weight_transitive": "ape.mopWeightTransitive",
    "mop_weight_activity": "ape.mopWeightActivity",
    # LLM parameters
    "llm_url": "ape.llmUrl",
    "llm_on_new_state": "ape.llmOnNewState",
    "llm_on_stagnation": "ape.llmOnStagnation",
    "llm_model": "ape.llmModel",
    "llm_temperature": "ape.llmTemperature",
    "llm_top_p": "ape.llmTopP",
    "llm_top_k": "ape.llmTopK",
    "llm_timeout_ms": "ape.llmTimeoutMs",
    "llm_max_calls": "ape.llmMaxCalls",
    "llm_percentage": "ape.llmPercentage",
    "llm_prompt_variant": "ape.llmPromptVariant",
}


class ApeRVTool(AbstractTool):
    """
    APE-RV exploration tool for rv-platform integration.

    Wraps the enhanced APE-RV binary (ape-rv.jar) as an AbstractTool. APE-RV
    runs inside the Android emulator via app_process, performing model-based UI
    exploration using the Widget Table Graph model with adaptive random testing.

    ### Role in the System:
    Implements the AbstractTool interface so rv-platform can dispatch APE-RV
    as a first-class exploration tool alongside rvsmart and rv-agent. Manages
    the full device interaction lifecycle: JAR push, properties push, execution,
    and empty-trace detection.

    ### Architectural Decisions:
    - process_pattern shared with builtin ape tool (INV-APV-07, D8): ape and
      aperv must not run concurrently on the same device — the shared pattern
      lets rv-platform detect and terminate stray ape processes before launch
    - Working directory is /system/bin (not /data/local/tmp/) because the
      enhanced binary requires system-level resource resolution (INV-APV-04, D7)
    - Coverage collection is delegated to the rv-android logcat infrastructure;
      APE-RV output is captured only for diagnostics

    ### Key Features:
    - Seven named variants: default, sata, sata_mop, bfs, random, sata_llm, sata_mop_llm
    - Eager strategy validation in configure() catches typos before device access
    - ape.properties injection configures GUI throttle without modifying the JAR
    - Timeout is treated as expected exit (exploration tools run until time limit)

    ### Integration Points:
    - Input: Task (device_id, timeout, trace_file), App (package_name)
    - Output: binary trace file with APE-RV stdout/stderr
    - Upstream: JarResolver locates ape-rv.jar; rv-platform supplies context
    - Downstream: logcat manager captures coverage events during execution
    """

    TOOL_SPEC = ToolSpec.create_builtin_spec(
        name=APERV_TOOL_NAME,
        description="Enhanced APE-RV model-based Android UI exploration tool",
        url="https://github.com/PAMunb/ape-rv",
        version="1.0.0",
        # Shared with builtin ape tool — ape and aperv must never run concurrently.
        # See INV-APV-07 and design.md D8.
        process_pattern="com.android.commands.monkey",
    )

    def __init__(self):
        """
        Initialize ApeRV tool.

        Sets up logging, JAR resolver, and prepares for configuration.

        State:
            self.logger: Context-aware logger tagged with component "ApeRVTool".
            self.jar_resolver: Resolves ape-rv.jar via priority search paths.
            self._tool_config: Stores validated config from configure(). Empty
                until configure() is called; checked in execute_tool_specific_logic()
                to decide whether to push ape.properties.
        """
        tool_spec = self.get_tool_spec()
        super().__init__(
            name=tool_spec.name,
            description=tool_spec.description,
            process_pattern=tool_spec.process_pattern,
        )

        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "aperv_tool.tools.aperv", {CONTEXT_COMPONENT: "ApeRVTool"}
        )

        self.jar_resolver = JarResolver()
        self._tool_config: Dict[str, Any] = {}

    @classmethod
    def get_tool_spec(cls) -> ToolSpec:
        """Get tool specification for registration."""
        return cls.TOOL_SPEC

    @classmethod
    def get_variants(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get available APE-RV variants.

        Returns 7 variants. The "default" variant maps to sata (INV-TOOL-02).
        The "sata_mop" variant enables MOP-guided scoring via static analysis
        data. The "sata_llm" and "sata_mop_llm" variants add LLM guidance
        via an OpenAI-compatible endpoint (gh6 APE-RV LLM integration).

        Returns:
            Dictionary mapping variant names to configuration parameters
        """
        return {
            "default": {
                "strategy": "sata",
                "throttle_ms": 200,
            },
            "sata": {
                "strategy": "sata",
                "throttle_ms": 200,
            },
            "sata_mop": {
                "strategy": "sata",
                "throttle_ms": 200,
                "mop_data": "static_analysis",
            },
            "bfs": {
                "strategy": "bfs",
                "throttle_ms": 200,
            },
            "random": {
                "strategy": "random",
                "throttle_ms": 200,
            },
            "sata_llm": {
                "strategy": "sata",
                "throttle_ms": 200,
                "llm_url": "http://10.0.2.2:30000/v1",
                "llm_on_new_state": "true",
                "llm_on_stagnation": "true",
                "llm_model": "default",
                "llm_temperature": 0.3,
                "llm_top_p": 0.6,
                "llm_top_k": 50,
                "llm_timeout_ms": 15000,
                "llm_max_calls": 200,
            },
            "sata_mop_llm": {
                "strategy": "sata",
                "throttle_ms": 200,
                "mop_data": "static_analysis",
                "llm_url": "http://10.0.2.2:30000/v1",
                "llm_on_new_state": "true",
                "llm_on_stagnation": "true",
                "llm_model": "default",
                "llm_temperature": 0.3,
                "llm_top_p": 0.6,
                "llm_top_k": 50,
                "llm_timeout_ms": 15000,
                "llm_max_calls": 200,
            },
            # --- Prompt variant experiment variants (gh43) ---
            # All use sata + mop + llm at 70% rate with high call budget.
            # Differ only in llm_prompt_variant.
            **{
                f"sata_mop_llm_{v}": {
                    "strategy": "sata",
                    "throttle_ms": 200,
                    "mop_data": "static_analysis",
                    "llm_url": "http://10.0.2.2:30000/v1",
                    "llm_on_new_state": "true",
                    "llm_on_stagnation": "true",
                    "llm_model": "default",
                    "llm_temperature": 0.3,
                    "llm_top_p": 0.6,
                    "llm_top_k": 50,
                    "llm_timeout_ms": 15000,
                    "llm_max_calls": 999,
                    "llm_percentage": 0.7,
                    "llm_prompt_variant": v,
                }
                for v in [
                    "ape_current", "ape_reasoning", "compact_v1",
                    "rvsmart_v13", "rvsmart_v17", "visual_only",
                ]
            },
        }

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure tool with resolved variant parameters.

        Validates that the strategy key is present and is one of the accepted
        strategies. Raises ConfigurationError immediately so typos in experiment
        YAML are caught before any device interaction (INV-APV-02).

        Args:
            config: Configuration dictionary with tool-specific parameters

        Raises:
            ConfigurationError: If strategy key is absent or not in
                APERV_AVAILABLE_STRATEGIES
        """
        strategy = config.get("strategy")
        if strategy is None:
            raise ConfigurationError(
                "aperv: 'strategy' key is required in tool configuration. "
                f"Valid strategies: {APERV_AVAILABLE_STRATEGIES}"
            )
        if strategy not in APERV_AVAILABLE_STRATEGIES:
            raise ConfigurationError(
                f"aperv: invalid strategy '{strategy}'. "
                f"Valid strategies: {APERV_AVAILABLE_STRATEGIES}"
            )
        self._tool_config = config.copy()

        # Allow env var override for LLM URL (host execution uses different URL than Docker)
        llm_url_override = os.environ.get("APERV_LLM_BASE_URL")
        if llm_url_override and "llm_url" in self._tool_config:
            self._tool_config["llm_url"] = llm_url_override

    def _resolve_jar_path(self) -> str:
        """
        Resolve the path to ape-rv.jar using priority search.

        Search priority (INV-APV-01):
        1. os.path.dirname(__file__) — module directory (populated by mvn install)
        2. $RVSEC_HOME/ape/target/ — development Maven build
        3. $TOOLS_DIR/aperv/ — manual placement

        Returns:
            Absolute path to ape-rv.jar

        Raises:
            RVToolExecutionError: If ape-rv.jar is not found in any search path
        """
        search_paths = [os.path.dirname(__file__)]
        rvsec_home = os.environ.get("RVSEC_HOME", "")
        if rvsec_home:
            search_paths.append(os.path.join(rvsec_home, "ape", "target"))
        tools_dir = os.environ.get("TOOLS_DIR", "")
        if tools_dir:
            search_paths.append(os.path.join(tools_dir, "aperv"))

        try:
            return self.jar_resolver.resolve_jar_path(APERV_JAR_NAME, search_paths)
        except Exception as e:
            error_msg = (
                f"ape-rv.jar not found. Ensure APE-RV is built and "
                f"available at one of: {search_paths}"
            )
            self.logger.error(error_msg)
            raise RVToolExecutionError(error_msg, tool_name=self.name, cause=e)

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
            trace_file_path: Trace file for logging push output (append binary mode)

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

    def _find_static_analysis_file(self, task: Task) -> str | None:
        """
        Locate the static analysis JSON file for the current task's APK.

        Looks for <task.results_dir>/<apk_name>.json, matching the file produced
        by rv-android static analysis for the instrumented APK.

        Args:
            task: Task with results_dir and config.apk_name

        Returns:
            Absolute path string if found, None otherwise
        """
        if not hasattr(task, "results_dir") or not task.results_dir:
            return None
        if not hasattr(task, "config") or not task.config:
            return None
        json_path = os.path.join(task.results_dir, f"{task.config.apk_name}.json")
        if os.path.isfile(json_path):
            self.logger.info(f"Found static analysis file: {json_path}")
            return json_path
        return None

    def _push_properties(
        self, device_serial: str, trace_file_path: str, mop_json_pushed: bool = False
    ) -> None:
        """
        Generate ape.properties from tool config and push to device.

        Writes ape.defaultGUIThrottle=<throttle_ms> to a temporary file. When
        mop_json_pushed is True, also appends ape.mopDataPath pointing to the
        previously pushed static analysis JSON.

        Args:
            device_serial: Device serial number
            trace_file_path: Trace file for logging
            mop_json_pushed: If True, include ape.mopDataPath in properties
        """
        lines = []
        if mop_json_pushed:
            lines.append("ape.mopDataPath=/data/local/tmp/static_analysis.json")
        for python_key, java_key in APERV_PROPERTY_MAPPING.items():
            if python_key in self._tool_config:
                lines.append(f"{java_key}={self._tool_config[python_key]}")
        properties_content = "\n".join(lines) + "\n"

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".properties", delete=False
        ) as tmp:
            tmp.write(properties_content)
            tmp_path = tmp.name

        try:
            self._push_file_to_device(
                tmp_path, APERV_DEVICE_PROPERTIES_PATH, device_serial, trace_file_path
            )
            self.logger.debug("Pushed ape.properties to device")
        finally:
            os.unlink(tmp_path)

    def _build_main_command(
        self, app: App, device_serial: str, timeout_seconds: int
    ) -> Command:
        """
        Build the APE-RV execution command.

        Command format (INV-APV-04: working dir must be /system/bin):
        adb -s <serial> shell CLASSPATH=/data/local/tmp/ape-rv.jar
            /system/bin/app_process /system/bin
            com.android.commands.monkey.Monkey
            -p <package>
            --running-minutes <max(1, timeout // 60)>
            --ape <strategy>

        Args:
            app: Application under test
            device_serial: Device serial number
            timeout_seconds: Execution timeout in seconds

        Returns:
            Command with timeout = timeout_seconds + 15
        """
        strategy = self._tool_config.get("strategy", "sata")
        running_minutes = max(1, timeout_seconds // 60)

        cmd_args = [
            "-s",
            device_serial,
            "shell",
            f"CLASSPATH={APERV_DEVICE_JAR_PATH}",
            "/system/bin/app_process",
            "/system/bin",  # INV-APV-04: working dir /system/bin, not /data/local/tmp/
            APERV_MAIN_CLASS,
            "-p",
            app.package_name,
            "--running-minutes",
            str(running_minutes),
            "--ape",
            strategy,
        ]

        return Command("adb", cmd_args, timeout_seconds + 15)

    def _check_empty_trace(self, trace_file_path: str) -> None:
        """
        Check if the trace file is empty (0 bytes).

        An empty trace indicates APE-RV produced no output — possible silent
        hang or startup crash. Logs a warning but does not fail.

        Args:
            trace_file_path: Path to the trace file written by
                execute_tool_specific_logic.
        """
        try:
            if (
                os.path.isfile(trace_file_path)
                and os.path.getsize(trace_file_path) == 0
            ):
                self.logger.warning(
                    "aperv produced empty trace file — "
                    "possible silent hang or startup crash"
                )
        except OSError:
            pass

    @ErrorHandler.handle_errors(
        component="ApeRVTool", phase="execute_tool_specific_logic", reraise=True
    )
    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
        """
        Execute APE-RV exploration on the device.

        Orchestrates JAR resolution, device push, properties push, command
        execution, and empty trace check. Timeout is expected normal exit for
        exploration tools.

        Args:
            task: Task configuration with device, timeout, trace file
            app: Application under test
        """
        self.logger.info(f"Executing APE-RV for {app.package_name}")

        # Extract device serial from task configuration
        device_serial = "emulator-5554"
        task_config = task.config if hasattr(task, "config") else None
        if task_config and hasattr(task_config, "device_id") and task_config.device_id:
            device_serial = task_config.device_id

        # Extract timeout from task configuration
        timeout_seconds = 300
        if task_config and hasattr(task_config, "timeout") and task_config.timeout:
            timeout_seconds = task_config.timeout

        # Step 1: Resolve ape-rv.jar and push to device
        jar_path = self._resolve_jar_path()
        self._push_file_to_device(
            jar_path, APERV_DEVICE_JAR_PATH, device_serial, task.result.trace_file
        )

        # Step 1a: Push system-broadcast.json for component triggering (gh11)
        broadcast_catalog = os.path.join(os.path.dirname(__file__), "system-broadcast.json")
        if os.path.exists(broadcast_catalog):
            self._push_file_to_device(
                broadcast_catalog,
                "/data/local/tmp/system-broadcast.json",
                device_serial,
                task.result.trace_file,
            )

        # Step 1b: Optionally push static analysis JSON for sata_mop variant
        mop_json_pushed = False
        if self._tool_config.get("mop_data") == "static_analysis":
            static_json = self._find_static_analysis_file(task)
            if static_json:
                self._push_file_to_device(
                    static_json,
                    "/data/local/tmp/static_analysis.json",
                    device_serial,
                    task.result.trace_file,
                )
                mop_json_pushed = True
            else:
                self.logger.warning(
                    "sata_mop: static analysis file not found in results_dir, "
                    "running without MOP data"
                )

        # Step 2: Optionally push ape.properties (when tool is configured)
        if self._tool_config:
            self._push_properties(device_serial, task.result.trace_file, mop_json_pushed)

        # Step 3: Build and execute main command
        main_cmd = self._build_main_command(app, device_serial, timeout_seconds)

        self.logger.info(f"Starting APE-RV exploration (timeout={timeout_seconds}s)")

        try:
            with open(task.result.trace_file, "wb") as trace_file:
                # Use invoke() directly: APE-RV exits with non-zero when it detects
                # app crashes during exploration (e.g. exit code 211) — this is normal
                # behavior, not a tool failure. Coverage is collected via logcat
                # regardless. Only RVCommandTimeoutError (timeout) is re-raised.
                result = main_cmd.invoke(stdout=trace_file, stderr=trace_file)
                if result.code != 0:
                    self.logger.debug(
                        f"APE-RV exited with code {result.code} "
                        "(non-zero is normal when app crashes are detected)"
                    )
        except RVCommandTimeoutError:
            # Timeout is expected behavior for exploration tools
            self.logger.info(
                f"APE-RV execution timed out after {timeout_seconds} seconds "
                "(expected behavior)"
            )
            raise RVToolTimeoutError(
                f"APE-RV timed out after {timeout_seconds} seconds",
                tool_name=self.name,
            )

        # Step 4: Check for empty trace
        self._check_empty_trace(task.result.trace_file)

        self.logger.info("APE-RV execution completed successfully")
