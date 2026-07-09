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
(rv-agent) and is selected by experiment configuration.

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
    # mop_weight_activity: ape.mopWeightActivity was removed from Config.java on the
    # mop-fairtest branch (replaced by component triggering + mopWeightOpenMenu); the
    # key is inert (an unknown ape.property is ignored by Config.java) and kept only
    # for backward-compat with pre-mop-fairtest configs. calibração v4 does NOT search it.
    "mop_weight_activity": "ape.mopWeightActivity",
    "mop_weight_open_menu": "ape.mopWeightOpenMenu",
    "mop_weight_wtg": "ape.mopWeightWtg",
    # gh11/gh13: per-step component-trigger probability (default 0.0 = disabled).
    "component_percentage": "ape.componentPercentage",
    # mop-fairtest: cap on deterministic MOP short-circuit picks per (widget,type,activity).
    "mop_target_pick_cap": "ape.mopTargetPickCap",
    "coverage_boost_weight": "ape.coverageBoostWeight",
    # RV exploration flags — arm-defining (gh43 + rv-scoring-pipeline). Made explicit
    # per arm so no arm-defining behavior falls back to a jar Config default (INV-APV-13/14).
    "back_menu_pick_cap": "ape.backMenuPickCap",
    "foreign_activity_guard": "ape.foreignActivityGuard",
    "tree_package_guard": "ape.treePackageGuard",
    "dynamic_epsilon": "ape.dynamicEpsilon",
    "heuristic_input": "ape.heuristicInput",
    "fuzz_input_typed": "ape.fuzzInputTyped",
    "form_completion_enabled": "ape.formCompletionEnabled",
    "step_telemetry_enabled": "ape.stepTelemetryEnabled",
    "model_menu_enabled": "ape.modelMenuEnabled",
    "least_visited_priority_tiebreak": "ape.leastVisitedPriorityTiebreak",
    "tree_enhancements_enabled": "ape.treeEnhancementsEnabled",
    "activity_budget_enabled": "ape.activityBudgetEnabled",
    # Kill-switch — arm-defining (rv-scoring-pipeline apePureMode baseline).
    "ape_pure_mode": "ape.apePureMode",
    # MOP reach strategies — arm-defining (mop-reach-strategies: A′/B/E-min).
    "mop_activity_source_components": "ape.mopActivitySourceComponents",
    "mop_frontier_weight": "ape.mopFrontierWeight",
    "trigger_mop_first": "ape.triggerMopFirst",
    # Frontier boosting + component triggering — arm-defining (gh43).
    "frontier_boost_weight": "ape.frontierBoostWeight",
    "activity_trigger_enabled": "ape.activityTriggerEnabled",
    # Arm-neutral global tuning knob (idle-timeout-cap): mapped so an experiment can
    # lower the idle-drain ceiling globally, but NOT arm-defining (applies to every arm).
    "max_idle_timeout_ms": "ape.maxIdleTimeoutMs",
    # LLM parameters
    "llm_url": "ape.llmUrl",
    "llm_on_new_state": "ape.llmOnNewState",
    "llm_on_stagnation": "ape.llmOnStagnation",
    "llm_model": "ape.llmModel",
    "llm_temperature": "ape.llmTemperature",
    "llm_top_p": "ape.llmTopP",
    "llm_top_k": "ape.llmTopK",
    "llm_timeout_ms": "ape.llmTimeoutMs",
    "llm_percentage": "ape.llmPercentage",
    # mop-reach-strategies F′ seam — arm-defining (LLM boost when substrate is widgetless).
    "llm_percentage_no_substrate": "ape.llmPercentageNoSubstrate",
    "llm_prompt_variant": "ape.llmPromptVariant",
}


# The Python config keys whose value defines what an experiment arm *is* (INV-APV-15).
# Single source of truth for the guard tests: every member MUST be in
# APERV_PROPERTY_MAPPING (INV-APV-13) and set explicitly in every non-exempt variant
# (INV-APV-14). Excludes mop_data/strategy (Python-only orchestration) and the
# mop_weight_* keys (gated by mop_data — a null MopData disables scoring regardless of
# weight, so they cannot contaminate a non-MOP arm) and max_idle_timeout_ms (arm-neutral).
ARM_DEFINING_KEYS = frozenset(
    {
        "ape_pure_mode",
        "frontier_boost_weight",
        "activity_trigger_enabled",
        "back_menu_pick_cap",
        "foreign_activity_guard",
        "tree_package_guard",
        "dynamic_epsilon",
        "heuristic_input",
        "fuzz_input_typed",
        "form_completion_enabled",
        "step_telemetry_enabled",
        "model_menu_enabled",
        "least_visited_priority_tiebreak",
        "tree_enhancements_enabled",
        "activity_budget_enabled",
        "mop_activity_source_components",
        "mop_frontier_weight",
        "trigger_mop_first",
        "llm_percentage_no_substrate",
    }
)

# The six gh43 prompt-experiment variants are frozen for historical reproducibility and
# EXEMPT from the arm-defining explicitness policy (INV-APV-17). An explicit named set —
# NOT a `sata_mop_llm_` prefix match — so a future non-exempt sata_mop_llm_* arm cannot be
# silently absorbed into the exemption and escape the guard.
_ARM_DEFINING_EXEMPT = frozenset(
    {
        "sata_mop_llm_ape_current",
        "sata_mop_llm_ape_reasoning",
        "sata_mop_llm_compact_v1",
        "sata_mop_llm_v13",
        "sata_mop_llm_v17",
        "sata_mop_llm_visual_only",
    }
)

# RV exploration ON at the current mop-fairtest jar defaults, made explicit; MOP / reach /
# frontier / component-triggering OFF. Spread into every non-MOP baseline arm so no
# arm-defining flag falls back to a jar Config default (INV-APV-14). This dict enumerates
# exactly the 19 ARM_DEFINING_KEYS, so any variant spreading it satisfies the guard.
_BASELINE_ARM_FLAGS = {
    "back_menu_pick_cap": 3,
    "foreign_activity_guard": True,
    "tree_package_guard": True,
    "dynamic_epsilon": True,
    "heuristic_input": True,
    "fuzz_input_typed": True,
    "form_completion_enabled": True,
    "step_telemetry_enabled": True,
    "model_menu_enabled": True,
    "least_visited_priority_tiebreak": True,
    "tree_enhancements_enabled": True,
    "activity_budget_enabled": True,
    "llm_percentage_no_substrate": -1,
    "ape_pure_mode": False,
    "frontier_boost_weight": 0,
    "activity_trigger_enabled": False,
    "mop_activity_source_components": False,
    "mop_frontier_weight": 0,
    "trigger_mop_first": False,
}

# Every arm-defining flag at its off/zero value + the kill-switch ON. Used by ape_pure so
# the original-APE baseline is auditable from ape.properties without trusting the jar's
# apePureMode to force RV off (defense-in-depth, design D1). Also 19 keys → guard-clean.
_APE_PURE_ARM_FLAGS = {
    "back_menu_pick_cap": 0,
    "foreign_activity_guard": False,
    "tree_package_guard": False,
    "dynamic_epsilon": False,
    "heuristic_input": False,
    "fuzz_input_typed": False,
    "form_completion_enabled": False,
    "step_telemetry_enabled": False,
    "model_menu_enabled": False,
    "least_visited_priority_tiebreak": False,
    "tree_enhancements_enabled": False,
    "activity_budget_enabled": False,
    "llm_percentage_no_substrate": -1,
    "ape_pure_mode": True,
    "frontier_boost_weight": 0,
    "activity_trigger_enabled": False,
    "mop_activity_source_components": False,
    "mop_frontier_weight": 0,
    "trigger_mop_first": False,
}

# The MOP substrate: static-analysis data path + the four MOP scoring weights. Spread into
# every MOP arm. Weights are gated by mop_data (a null MopData disables scoring regardless),
# so they are NOT arm-defining, but are pinned here for auditability (INV-APV-15).
_MOP_SUBSTRATE = {
    "mop_data": "static_analysis",
    "mop_weight_direct": 500,
    "mop_weight_transitive": 300,
    "mop_weight_open_menu": 250,
    "mop_weight_wtg": 200,
}

# The LLM sampling block shared by the LLM arms (sata_llm / sata_mop_llm). 10.0.2.2 is the
# Android emulator alias for host loopback; APERV_LLM_BASE_URL overrides at configure().
_LLM_FLAGS = {
    "llm_url": "http://10.0.2.2:30000/v1",
    "llm_on_new_state": "true",
    "llm_on_stagnation": "true",
    "llm_model": "default",
    "llm_temperature": 0.3,
    "llm_top_p": 0.6,
    "llm_top_k": 50,
    "llm_timeout_ms": 15000,
}


class ApeRVTool(AbstractTool):
    """
    APE-RV exploration tool for rv-platform integration.

    Wraps the enhanced APE-RV binary (ape-rv.jar) as an AbstractTool. APE-RV
    runs inside the Android emulator via app_process, performing model-based UI
    exploration using the Widget Table Graph model with adaptive random testing.

    ### Role in the System:
    Implements the AbstractTool interface so rv-platform can dispatch APE-RV
    as a first-class exploration tool alongside rv-agent. Manages
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
    - Named variants: eleven arm-defining-explicit arms (default, sata, bfs, random,
      ape_pure, sata_mop_widget, sata_mop [alias], sata_mop_activity,
      sata_mop_act_frontier, sata_llm, sata_mop_llm) + six frozen gh43 prompt arms
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
        # Retrieve spec once and delegate to AbstractTool. The spec is a class-level
        # constant, but we go through get_tool_spec() so subclasses can override it.
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
        # Empty dict signals "not yet configured" — execute_tool_specific_logic()
        # checks truthiness to decide whether ape.properties should be pushed.
        # After configure(), this holds the full merged variant config.
        self._tool_config: Dict[str, Any] = {}

    @classmethod
    def get_tool_spec(cls) -> ToolSpec:
        """Get tool specification for registration."""
        return cls.TOOL_SPEC

    @classmethod
    def get_variants(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get available APE-RV variants.

        Eleven non-exempt arms + six exempt gh43 prompt-experiment arms. Every non-exempt
        arm sets every key in ARM_DEFINING_KEYS explicitly (INV-APV-14), spreading the shared
        _BASELINE_ARM_FLAGS (RV exploration ON, MOP/reach off) and — for MOP arms —
        _MOP_SUBSTRATE, so an arm's identity is its variant dict and never a jar Config
        default. "default" aliases sata (INV-TOOL-02); "sata_mop" aliases sata_mop_widget by
        shared object (INV-APV-16). The six gh43 arms are frozen and EXEMPT (INV-APV-17).

        Returns:
            Dictionary mapping variant names to configuration parameters
        """
        # "mop_data" and "strategy" are Python-only keys consumed during execution; they are
        # NOT written to ape.properties (no APERV_PROPERTY_MAPPING entry). Build sata_mop_widget
        # once and bind sata_mop to the same object so the alias holds by construction (D4).
        sata_mop_widget = {
            **_BASELINE_ARM_FLAGS,
            **_MOP_SUBSTRATE,
            "strategy": "sata",
            "throttle_ms": 200,
        }
        return {
            # Baseline arms — RV exploration ON (defaults explicit), MOP/reach OFF.
            "default": {**_BASELINE_ARM_FLAGS, "strategy": "sata", "throttle_ms": 200},
            "sata": {**_BASELINE_ARM_FLAGS, "strategy": "sata", "throttle_ms": 200},
            "bfs": {**_BASELINE_ARM_FLAGS, "strategy": "bfs", "throttle_ms": 200},
            "random": {**_BASELINE_ARM_FLAGS, "strategy": "random", "throttle_ms": 200},
            # ape_pure — original APE via the apePureMode kill-switch; every RV flag off.
            "ape_pure": {**_APE_PURE_ARM_FLAGS, "strategy": "sata", "throttle_ms": 200},
            # MOP arms — decompose the reach mechanism (widget → +A′ → +B+E-min).
            "sata_mop_widget": sata_mop_widget,
            # sata_mop is the back-compat alias of sata_mop_widget (same object, INV-APV-16).
            "sata_mop": sata_mop_widget,
            "sata_mop_activity": {
                **sata_mop_widget,
                "mop_activity_source_components": True,
            },
            "sata_mop_act_frontier": {
                **sata_mop_widget,
                "mop_activity_source_components": True,
                "frontier_boost_weight": 200,
                "mop_frontier_weight": 200,
                "activity_trigger_enabled": True,
                "trigger_mop_first": True,
            },
            # LLM arms — full arm-defining baseline + LLM sampling block.
            "sata_llm": {
                **_BASELINE_ARM_FLAGS,
                **_LLM_FLAGS,
                "strategy": "sata",
                "throttle_ms": 200,
            },
            "sata_mop_llm": {
                **_BASELINE_ARM_FLAGS,
                **_MOP_SUBSTRATE,
                **_LLM_FLAGS,
                "strategy": "sata",
                "throttle_ms": 200,
            },
            # --- Prompt variant experiment variants (gh43) — FROZEN / EXEMPT (INV-APV-17) ---
            # Six controlled prompt-ablation arms, sata + mop + llm at 70% rate, differing
            # only in llm_prompt_variant. Frozen exactly as authored for reproducibility;
            # deliberately NOT carrying the arm-defining baseline (exempt from INV-APV-14).
            **{
                f"sata_mop_llm_{v}": {
                    "strategy": "sata",
                    "throttle_ms": 200,
                    "mop_data": "static_analysis",
                    **_LLM_FLAGS,
                    "llm_percentage": 0.7,
                    "llm_prompt_variant": v,
                }
                for v in [
                    "ape_current",
                    "ape_reasoning",
                    "compact_v1",
                    "v13",
                    "v17",
                    "visual_only",
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
        # Validate eagerly so experiment YAML typos are caught before any device
        # interaction — a failed push mid-experiment wastes minutes of emulator time.
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
        # Defensive copy preserves the caller's dict.
        self._tool_config = config.copy()

        # gh55 D8: LLM URL override flows through `parameters["llm_url"]` (set by
        # L5 from env / CLI). The factory merge `{**variant_defaults, **parameters}`
        # ensures the value is present at configure() time. No `os.environ` read
        # at L2 — operators set `APERV_LLM_BASE_URL` (or the variant default)
        # and L5 propagates it via `ToolConfig.parameters`.

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
        # gh55 D10: RVSEC_HOME and TOOLS_DIR are L1 cross-layer infra — read once
        # inside JarResolver, never at L2. The aperv-specific subdir (`ape/target`
        # for RVSEC_HOME and `aperv` for TOOLS_DIR) is communicated to the
        # resolver via the standard `<tool_subdir>/<jar_name>` convention.
        # The module-local JAR (shipped with the package) takes precedence; the
        # resolver auto-extends with RVSEC_HOME-based and TOOLS_DIR-based paths
        # via _build_search_paths.
        search_paths = [os.path.dirname(__file__)]

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
            # -a preserves file timestamps; -p shows transfer progress in the trace.
            ["-s", device_serial, "push", "-a", "-p", local_path, device_path],
            timeout=60,
        )

        # Append mode ("ab") so multiple pushes (JAR, properties, broadcast catalog)
        # accumulate in the same trace file without overwriting earlier output.
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
        # Guard against tasks that lack results_dir or config — this happens when
        # running aperv standalone (outside rv-experiment) where pre-processing
        # (static analysis) was not executed.
        if not hasattr(task, "results_dir") or not task.results_dir:
            return None
        if not hasattr(task, "config") or not task.config:
            return None
        # The static analysis module writes <apk_name>.json to the task's results_dir.
        # The file maps activities to monitored operations for MOP-guided exploration.
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
        # Build the properties file content by translating Python config keys to
        # Java property names. Only keys present in _tool_config AND in
        # APERV_PROPERTY_MAPPING are written — Python-only keys (strategy, mop_data)
        # are excluded automatically because they have no mapping entry.
        lines = []
        if mop_json_pushed:
            # Hardcoded device path — must match the push destination in execute_tool_specific_logic()
            lines.append("ape.mopDataPath=/data/local/tmp/static_analysis.json")
        for python_key, java_key in APERV_PROPERTY_MAPPING.items():
            if python_key in self._tool_config:
                lines.append(f"{java_key}={self._tool_config[python_key]}")
        properties_content = "\n".join(lines) + "\n"

        # Write to a temp file first because adb push requires a local file path.
        # delete=False so the file survives until we explicitly unlink it after push.
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
        # APE-RV accepts minutes, not seconds. Floor division with min 1 ensures
        # short timeouts (< 60s) still get at least one minute of exploration.
        running_minutes = max(1, timeout_seconds // 60)

        # The command runs APE-RV inside the emulator via app_process, which loads
        # the JAR into an Android runtime process (not a standard JVM). This is the
        # same mechanism the AOSP Monkey tool uses.
        cmd_args = [
            "-s",
            device_serial,
            "shell",
            # CLASSPATH is set as an inline env var for the shell command, not via
            # adb shell's env mechanism, because app_process reads it from the
            # process environment at startup.
            f"CLASSPATH={APERV_DEVICE_JAR_PATH}",
            "/system/bin/app_process",
            # Working directory is /system/bin (not /data/local/tmp/) because APE-RV
            # requires system-level resource resolution for internal Android APIs.
            # Using /data/local/tmp/ causes ClassNotFoundException on some API levels.
            "/system/bin",
            APERV_MAIN_CLASS,
            "-p",
            app.package_name,
            "--running-minutes",
            str(running_minutes),
            "--ape",
            strategy,
        ]

        # +15s grace period gives APE-RV time to flush its WTG model and exit
        # cleanly after --running-minutes expires. Without this buffer, the
        # Command timeout kills the process before it can write final output.
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

        # --- Step 0: Extract execution parameters from task ---
        # Defaults (emulator-5554, 300s) handle standalone execution where task.config
        # may be absent. In normal rv-platform flow, these are always populated.
        device_serial = "emulator-5554"
        task_config = task.config if hasattr(task, "config") else None
        if task_config and hasattr(task_config, "device_id") and task_config.device_id:
            device_serial = task_config.device_id

        timeout_seconds = 300
        if task_config and hasattr(task_config, "timeout") and task_config.timeout:
            timeout_seconds = task_config.timeout

        # Step 1: Resolve ape-rv.jar and push to device
        jar_path = self._resolve_jar_path()
        self._push_file_to_device(
            jar_path, APERV_DEVICE_JAR_PATH, device_serial, task.result.trace_file
        )

        # Step 1b: Push system-broadcast.json for component triggering (gh11).
        # This catalog tells APE-RV which broadcast intents to fire at receivers
        # discovered in the manifest. Optional — APE-RV degrades gracefully without it.
        broadcast_catalog = os.path.join(
            os.path.dirname(__file__), "system-broadcast.json"
        )
        if os.path.exists(broadcast_catalog):
            self._push_file_to_device(
                broadcast_catalog,
                "/data/local/tmp/system-broadcast.json",
                device_serial,
                task.result.trace_file,
            )

        # Step 1c: Optionally push static analysis JSON for MOP-guided variants.
        # The flag tracks whether the push succeeded so _push_properties() knows
        # whether to include ape.mopDataPath in the generated properties file.
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

        # Step 2: Push ape.properties with exploration parameters.
        # Skipped only when _tool_config is empty (tool used without configure()),
        # which means APE-RV falls back to its built-in defaults.
        if self._tool_config:
            self._push_properties(
                device_serial, task.result.trace_file, mop_json_pushed
            )

        # Step 3: Build and execute main command
        main_cmd = self._build_main_command(app, device_serial, timeout_seconds)

        self.logger.info(f"Starting APE-RV exploration (timeout={timeout_seconds}s)")

        try:
            # "wb" (not "ab") because the main execution output should replace the
            # push diagnostic output written earlier. The push output is low-value;
            # the exploration trace is the primary artifact for post-processing.
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
            # Timeout is the normal exit path for exploration tools — APE-RV is
            # designed to explore indefinitely until killed. We re-raise as
            # RVToolTimeoutError so rv-platform records this as a completed run
            # (not a failure) and proceeds to collect coverage from logcat.
            self.logger.info(
                f"APE-RV execution timed out after {timeout_seconds} seconds "
                "(expected behavior)"
            )
            raise RVToolTimeoutError(
                f"APE-RV timed out after {timeout_seconds} seconds",
                tool_name=self.name,
            )

        # Step 4: Detect silent failures. An empty trace suggests APE-RV crashed
        # at startup (e.g., missing CLASSPATH, incompatible API level) without
        # producing any output. This is a warning, not an error, because coverage
        # may still have been captured via logcat independently.
        self._check_empty_trace(task.result.trace_file)

        self.logger.info("APE-RV execution completed successfully")
