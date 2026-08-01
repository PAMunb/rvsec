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

import hashlib
import json
import os
import tempfile
import urllib.request
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
    # MOP reach strategies — arm-defining (mop-reach-strategies: A′/B). E-min is the
    # activity-trigger launcher (activity_trigger_enabled below); trigger_mop_first was
    # removed after the APE-RV jar deleted Config.triggerMopFirst (mop-census-launcher),
    # making ape.triggerMopFirst inert — see task group 7.
    "mop_activity_source_components": "ape.mopActivitySourceComponents",
    "mop_frontier_weight": "ape.mopFrontierWeight",
    # Frontier boosting + component triggering — arm-defining (gh43).
    "frontier_boost_weight": "ape.frontierBoostWeight",
    "activity_trigger_enabled": "ape.activityTriggerEnabled",
    # Arm-neutral global tuning knob (idle-timeout-cap): mapped so an experiment can
    # lower the idle-drain ceiling globally, but NOT arm-defining (applies to every arm).
    "max_idle_timeout_ms": "ape.maxIdleTimeoutMs",
    # Arm-neutral launcher-dose sub-params (activity-trigger-dose): the launcher cadence
    # (stagnation step at which it fires) and the per-run launch cap. Mapped so an
    # experiment can dose the launcher, but NOT arm-defining — a paired comparison sets
    # the same dose on both arms, so these values are identical across arms and cannot
    # define an arm (same rationale as max_idle_timeout_ms). They tune the arm-defining
    # activity_trigger_enabled without themselves selecting a behavior.
    "activity_trigger_stagnation_step": "ape.activityTriggerStagnationStep",
    "activity_trigger_max_per_run": "ape.activityTriggerMaxPerRun",
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
    # Phase-B LLM knobs (INV-APV-27) — mapped so a Phase-B arm can set them the moment the
    # Phase-B jar exposes the properties, with no further aperv-tool change. Inert for
    # Phase-A: no cal_a* arm sets either key (the Phase-A jar hardcodes max_tokens=1024 and
    # the snap tolerance), and INV-APV-08 writes only keys present in both _tool_config and
    # the mapping, so ape.properties for a cal_a* arm never emits these. The Java property
    # names follow plan §7 and are corrected in a Phase-B iteration if the ape-side J1
    # change decides differently. NOT members of LLM_ARM_KEYS (a dead knob would fake
    # explicitness — see INV-APV-26).
    "llm_max_tokens": "ape.llmMaxTokens",
    "llm_snap_tolerance_px": "ape.llmSnapTolerancePx",
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

# The LLM configuration keys every calibration arm (cal_*) MUST declare explicitly
# (INV-APV-26). A second guard, scoped to cal_*-prefixed variants only, that closes the
# INV-APV-14 gap: ARM_DEFINING_KEYS enforces explicitness over the arm-defining flags but
# _LLM_FLAGS omits llm_percentage and llm_prompt_variant, so two LLM arms could differ
# only through a key no guard covers. Calibration arms differ *precisely* in LLM keys, so
# for them every LLM key the Phase-A jar consumes is part of the audited surface.
#
# llm_max_tokens and llm_snap_tolerance_px are deliberately NOT here: the Phase-A jar
# hardcodes max_tokens=1024 and the snap tolerance, so requiring them would fake
# explicitness over a knob the deployed binary ignores. They join the guard only when the
# Phase-B jar exposes the corresponding Java properties (INV-APV-27).
LLM_ARM_KEYS = frozenset(
    {
        "llm_url",
        "llm_on_new_state",
        "llm_on_stagnation",
        "llm_model",
        "llm_temperature",
        "llm_top_p",
        "llm_top_k",
        "llm_timeout_ms",
        "llm_percentage",
        "llm_percentage_no_substrate",
        "llm_prompt_variant",
    }
)

# RV exploration ON at the current mop-fairtest jar defaults, made explicit; MOP / reach /
# frontier / component-triggering OFF. Spread into every non-MOP baseline arm so no
# arm-defining flag falls back to a jar Config default (INV-APV-14). This dict enumerates
# exactly the 18 ARM_DEFINING_KEYS, so any variant spreading it satisfies the guard.
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
}

# Every arm-defining flag at its off/zero value + the kill-switch ON. Used by ape_pure so
# the original-APE baseline is auditable from ape.properties without trusting the jar's
# apePureMode to force RV off (defense-in-depth, design D1). Also 18 keys → guard-clean.
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

# The frontier reach substrate: the arm-defining configuration of sata_mop_act_frontier
# (MOP on + reach package A′+B+E-min) that won the cmpma multi-arm comparison
# (cov_mop 37.75% vs ≤35%, Friedman+Holm). Spread into every cal_* calibration arm so that
# whenever the LLM router does not delegate a step — and on every no_match fallback — the
# arm explores in frontier mode. `sata_mop_act_frontier` without the LLM block is exactly
# the ANC2 anchor, so `cal_* − ANC2` isolates the LLM contribution on the same algorithmic
# base (design decision 3). Enumerates every ARM_DEFINING_KEY (via _BASELINE_ARM_FLAGS with
# the four frontier overrides) + the MOP substrate, so any cal_* arm spreading it satisfies
# the INV-APV-14 guard.
_FRONTIER_SUBSTRATE = {
    **_BASELINE_ARM_FLAGS,
    **_MOP_SUBSTRATE,
    "mop_activity_source_components": True,
    "frontier_boost_weight": 200,
    "mop_frontier_weight": 200,
    "activity_trigger_enabled": True,
}

# What "MOP guidance off" means, as a delta over the frontier substrate. Spread
# into the decisive run's control arm so the arm reads as "the reference arm plus
# this", making the single-factor property visible at the definition site rather
# than only in a test.
#
# The shape is forced, not chosen (INV-APV-29). Three things could plausibly mean
# MOP-off, and two of them silently destroy the experiment:
#
#   1. Point ape.mopDataPath at a missing file → requireMopArm raises
#      StopTestingException and the whole run ABORTS (StatefulAgent.java:216-223).
#   2. Omit mop_data so the path is never set → loads as null without aborting,
#      but WtgPass:29 and FrontierPass:35 both require mopData != null, so the
#      generic WTG and frontier navigation die as collateral. The contrast would
#      then be "full substrate versus almost no substrate", not "MOP guidance on
#      versus off".
#   3. Keep the document, zero the weights, turn the trigger off → the MOP
#      short-circuits become no-ops (pickBestMopTarget requires mopBoost > 0)
#      while the frontier and WTG passes keep running on generic signal.
#
# Only the third isolates MOP guidance, so mop_data stays present here and
# frontier_boost_weight is deliberately NOT zeroed: the control removes MOP
# guidance, not navigation (INV-APV-30).
_MOP_OFF_OVERRIDES = {
    "mop_weight_direct": 0,
    "mop_weight_transitive": 0,
    "mop_weight_open_menu": 0,
    "mop_weight_wtg": 0,
    "mop_frontier_weight": 0,
    "activity_trigger_enabled": False,
}

# LLM keys shared verbatim by all nine calibration arms. The varying keys — prompt variant,
# percentage, sampling (temperature/top_p/top_k), and routing (on_new_state/on_stagnation) —
# are written explicitly per arm (design decision 3: the diff-vs-cal_a1 is exactly what the
# experiment varies). llm_percentage_no_substrate=-1 comes from the frontier substrate.
# 10.0.2.2 is the emulator host-loopback alias; APERV_LLM_BASE_URL overrides at configure().
_CAL_LLM_COMMON = {
    "llm_url": "http://10.0.2.2:30000/v1",
    "llm_model": "default",
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
      + nine cal_a1…cal_a9 calibration arms (frontier substrate + explicit LLM keys)
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

        Eleven base non-exempt arms + nine cal_* calibration arms + three E3
        decisive-run arms + six exempt gh43 prompt-experiment arms, 29 in total.
        Every non-exempt arm sets every key in ARM_DEFINING_KEYS
        explicitly (INV-APV-14), spreading the shared _BASELINE_ARM_FLAGS (RV exploration ON,
        MOP/reach off) and — for MOP arms — _MOP_SUBSTRATE, so an arm's identity is its
        variant dict and never a jar Config default. "default" aliases sata (INV-TOOL-02);
        "sata_mop" aliases sata_mop_widget by shared object (INV-APV-16). The six gh43 arms
        are frozen and EXEMPT (INV-APV-17). The nine cal_a1…cal_a9 arms sit on the
        _FRONTIER_SUBSTRATE and additionally declare every LLM_ARM_KEYS key explicitly
        (INV-APV-26); they implement the Phase-A calibration arm table (plan §6, rev. 3.2).
        The three gh90 arms — mop_on_llm_off, mop_off_llm_off, mop_on_llm_70 — are the
        E3 decisive run's arm set: a shared reference plus one single-factor contrast
        each for MOP guidance (RQ-C1) and for the LLM (RQ-C3).

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
            # E-min is the activity-trigger launcher (activity_trigger_enabled); trigger_mop_first
            # was removed after the jar deleted Config.triggerMopFirst (mop-census-launcher).
            "sata_mop_act_frontier": {
                **sata_mop_widget,
                "mop_activity_source_components": True,
                "frontier_boost_weight": 200,
                "mop_frontier_weight": 200,
                "activity_trigger_enabled": True,
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
            # --- Calibration arm variants (cal_*) — Phase-A arm table (plan §6, rev. 3.2) ---
            # All nine arms sit on the _FRONTIER_SUBSTRATE (sata_mop_act_frontier: MOP on,
            # reach package A′+B+E-min) so every non-LLM step and every no_match fallback
            # explores in frontier mode. Each declares every LLM_ARM_KEYS key explicitly
            # (INV-APV-26) plus the full ARM_DEFINING_KEYS set (via the substrate). Written
            # as explicit dict literals — the diff-vs-cal_a1 is exactly what the experiment
            # varies (design decision 3). llm_on_new_state/llm_on_stagnation are Python bools
            # (serialized to true/false by _push_properties); llm_temperature 0 disables
            # sampling stochasticity.
            #
            # cal_a1 = control: the cmp_llm_20260721 LLM-key config (v13, 70%, temperature 0)
            # carried onto the frontier substrate. cmp_llm itself ran on the widget substrate,
            # so cal_a1 is NOT the identical cmp_llm arm — the cross-substrate anchors are
            # re-measured in-experiment by the Phase-A design (ANC1/ANC2/cal_a1).
            "cal_a1": {
                **_FRONTIER_SUBSTRATE,
                **_CAL_LLM_COMMON,
                "strategy": "sata",
                "throttle_ms": 200,
                "llm_prompt_variant": "v13",
                "llm_percentage": 0.7,
                "llm_temperature": 0,
                "llm_top_p": 0.6,
                "llm_top_k": 50,
                "llm_on_new_state": True,
                "llm_on_stagnation": True,
            },
            # cal_a2 (H1): lower the LLM budget to 30% at the same routing/sampling as cal_a1.
            "cal_a2": {
                **_FRONTIER_SUBSTRATE,
                **_CAL_LLM_COMMON,
                "strategy": "sata",
                "throttle_ms": 200,
                "llm_prompt_variant": "v13",
                "llm_percentage": 0.3,
                "llm_temperature": 0,
                "llm_top_p": 0.6,
                "llm_top_k": 50,
                "llm_on_new_state": True,
                "llm_on_stagnation": True,
            },
            # cal_a3 (H1, stagnation-only): route to the LLM only when stagnating
            # (llm_on_new_state off), percentage 0 — the LLM fires purely on the stagnation
            # trigger, never on new-state entry.
            "cal_a3": {
                **_FRONTIER_SUBSTRATE,
                **_CAL_LLM_COMMON,
                "strategy": "sata",
                "throttle_ms": 200,
                "llm_prompt_variant": "v13",
                "llm_percentage": 0,
                "llm_temperature": 0,
                "llm_top_p": 0.6,
                "llm_top_k": 50,
                "llm_on_new_state": False,
                "llm_on_stagnation": True,
            },
            # cal_a4 (H1, new-state+stagnation): both triggers on, percentage 0 — routing is
            # trigger-driven rather than budget-driven.
            "cal_a4": {
                **_FRONTIER_SUBSTRATE,
                **_CAL_LLM_COMMON,
                "strategy": "sata",
                "throttle_ms": 200,
                "llm_prompt_variant": "v13",
                "llm_percentage": 0,
                "llm_temperature": 0,
                "llm_top_p": 0.6,
                "llm_top_k": 50,
                "llm_on_new_state": True,
                "llm_on_stagnation": True,
            },
            # cal_a5 (H3, vendor bundle): the vendor-recommended sampling bundle
            # (temperature 0.7, top_p 0.8, top_k 20) at 30% budget.
            "cal_a5": {
                **_FRONTIER_SUBSTRATE,
                **_CAL_LLM_COMMON,
                "strategy": "sata",
                "throttle_ms": 200,
                "llm_prompt_variant": "v13",
                "llm_percentage": 0.3,
                "llm_temperature": 0.7,
                "llm_top_p": 0.8,
                "llm_top_k": 20,
                "llm_on_new_state": True,
                "llm_on_stagnation": True,
            },
            # cal_a6 (H3, temperature isolated): same as cal_a5 but top_p/top_k held at the
            # cal_a1 values (0.6 / 50) — isolates temperature from the nucleus/top-k bundle
            # (cal_a6 vs cal_a5 differ only in llm_top_p and llm_top_k).
            "cal_a6": {
                **_FRONTIER_SUBSTRATE,
                **_CAL_LLM_COMMON,
                "strategy": "sata",
                "throttle_ms": 200,
                "llm_prompt_variant": "v13",
                "llm_percentage": 0.3,
                "llm_temperature": 0.7,
                "llm_top_p": 0.6,
                "llm_top_k": 50,
                "llm_on_new_state": True,
                "llm_on_stagnation": True,
            },
            # cal_a7 (H3, AutoDroid point): the AutoDroid temperature setting (0.25).
            "cal_a7": {
                **_FRONTIER_SUBSTRATE,
                **_CAL_LLM_COMMON,
                "strategy": "sata",
                "throttle_ms": 200,
                "llm_prompt_variant": "v13",
                "llm_percentage": 0.3,
                "llm_temperature": 0.25,
                "llm_top_p": 0.6,
                "llm_top_k": 50,
                "llm_on_new_state": True,
                "llm_on_stagnation": True,
            },
            # cal_a8 (H2, short extreme): the shortest prompt (visual_only) at 30% budget.
            "cal_a8": {
                **_FRONTIER_SUBSTRATE,
                **_CAL_LLM_COMMON,
                "strategy": "sata",
                "throttle_ms": 200,
                "llm_prompt_variant": "visual_only",
                "llm_percentage": 0.3,
                "llm_temperature": 0,
                "llm_top_p": 0.6,
                "llm_top_k": 50,
                "llm_on_new_state": True,
                "llm_on_stagnation": True,
            },
            # cal_a9 (H2, long extreme): the longest prompt (v17) at 30% budget.
            "cal_a9": {
                **_FRONTIER_SUBSTRATE,
                **_CAL_LLM_COMMON,
                "strategy": "sata",
                "throttle_ms": 200,
                "llm_prompt_variant": "v17",
                "llm_percentage": 0.3,
                "llm_temperature": 0,
                "llm_top_p": 0.6,
                "llm_top_k": 50,
                "llm_on_new_state": True,
                "llm_on_stagnation": True,
            },
            # --- E3 decisive-run arms (gh90) -------------------------------------
            # The three arms of the run that decides whether the LLM stays in the
            # design. All three sit on the frontier substrate (INV-APV-30) — the
            # standing rule is *sempre modo frontier* — and each contrast is
            # single-factor: arm 2 differs from arm 1 only in the MOP keys, arm 3
            # only in the LLM keys, which the guard tests assert by diffing the
            # dictionaries rather than by trusting review.
            #
            # The names are normative, not cosmetic: the variant string is the
            # resume identity key (platform.py:308-318) and the consolidation
            # column key ({arm}__{metric}), so a rename silently splits a
            # campaign's results. They spell out both factors so each contrast is
            # legible straight off the results CSV header.
            #
            # Arm 1 is configurationally sata_mop_act_frontier, the ANC2 anchor
            # that won the previous multi-arm comparison — the reference is not a
            # newly invented baseline.
            "mop_on_llm_off": {
                **_FRONTIER_SUBSTRATE,
                "strategy": "sata",
                "throttle_ms": 200,
            },
            # Arm 2 — the experiment's first control arm. Every APE-RV run ever
            # executed had MOP guidance on, so no measured difference has ever
            # been attributable to MOP guidance rather than to APE's baseline
            # exploration. arm 1 vs arm 2 is RQ-C1.
            "mop_off_llm_off": {
                **_FRONTIER_SUBSTRATE,
                **_MOP_OFF_OVERRIDES,
                "strategy": "sata",
                "throttle_ms": 200,
            },
            # Arm 3 — the LLM at the cal_a1 dose, carried over verbatim. 0.7 is
            # the only dose with a measured 300 s counterpart on this substrate
            # and subset, which is what lets the 1800 s result be read as a
            # dose × budget interaction (design D8). arm 1 vs arm 3 is RQ-C3.
            "mop_on_llm_70": {
                **_FRONTIER_SUBSTRATE,
                **_CAL_LLM_COMMON,
                "strategy": "sata",
                "throttle_ms": 200,
                "llm_prompt_variant": "v13",
                "llm_percentage": 0.7,
                "llm_temperature": 0,
                "llm_top_p": 0.6,
                "llm_top_k": 50,
                "llm_on_new_state": True,
                "llm_on_stagnation": True,
                # B3: the raised snap radius, and the jar it is raised for.
                #
                # Widening the radius makes more LLM answers resolve to a
                # widget. Without the dead-pair ban the extra resolutions are
                # repeated taps on pairs already known to produce no new state,
                # so the widening amplifies the measured 25.6% dead-call waste
                # instead of rescuing near-misses. The tolerance is therefore
                # only ever set alongside a declaration of which jar build it
                # belongs to, and _snap_tolerance_offenders fails the suite on
                # any of the three alone (INV-APV-34).
                #
                # The two declarations answer different questions. The sha256 is
                # the gate: it is compared at smoke time against the jar_sha256
                # captured at run start, and it is what actually proves which
                # binary ran. The git sha is documentary — it is the only way
                # back from a digest to the source revision, since ape-rv.jar
                # carries no build stamp of its own. Both are Python-only and
                # stay out of APERV_PROPERTY_MAPPING: the jar has no property to
                # receive them, and that absence is what keeps them inert enough
                # not to disturb the arm 1 <-> arm 3 single-factor contrast.
                #
                # The ape build is not bit-reproducible, so a rebuild of the
                # same revision changes the digest and this pair has to be
                # re-recorded. That is the accepted cost of verifying the
                # artifact rather than a claim it makes about itself.
                "llm_snap_tolerance_px": 150,
                "expected_jar_git_sha": "5dcf225976b26ce78d8b31dd88d7f858dad29d43",
                "expected_jar_sha256": (
                    "386ce08d1846a4088755a8d755e5b70391af3b42add091d231dbcc52aed24e69"
                ),
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

    def _compact_static_analysis_json(self, source_path: str) -> str | None:
        """
        Compact the static analysis JSON into a temporary file for device push.

        Compaction is three operations: deduplicating exact-duplicate entries in
        `transitions` (preserving first-occurrence order), enriching every
        `listeners[]` object with the two handler-reach booleans, and serializing
        without pretty-print whitespace. The first and third are lossless; the
        second is purely additive (INV-APV-21, INV-APV-31). No field is projected
        away.

        This exists because the Java side applies a pre-read footprint guard
        (MopData.java:202) that rejects any file above roughly maxMemory()/6 —
        about 32 MB at the emulator's ~192 MB heap. An oversized JSON makes the
        MOP arms abort with 0 steps while the non-MOP baselines explore normally,
        which is a per-app fairness gap rather than a crash. Duplicate edges carry
        no information: no consumer of the edge list in the sibling `ape` repo
        reads multiplicity (all are set-membership or first-match-fixed-weight),
        so removing them is safe. Order is preserved because rekeyDialogsToHost
        (MopData.java:884) resolves the first inbound edge and breaks (INV-APV-22).

        Runs unconditionally rather than above a size threshold (INV-APV-23): a
        threshold would leave this path exercised on ~1 app in 181 and would
        duplicate the Java-side PARSE_FOOTPRINT_FACTOR as a second constant to
        keep in sync across repositories.

        Args:
            source_path: Path to the source JSON, from _find_static_analysis_file()

        Returns:
            Path to the compacted temp file, or None if compaction failed —
            the caller treats None as "push the source unchanged" (INV-APV-24).
        """
        tmp_path: str | None = None
        try:
            with open(source_path, "r") as source_file:
                document = json.load(source_file)

            # Dedup by canonical serialization of the whole entry rather than an
            # explicit (sourceId, targetId, events) key tuple: identical for the
            # current schema, but stays correct if the producer adds a field later,
            # where a fixed tuple would silently collapse distinct entries (D4).
            transitions = document.get("transitions")
            if isinstance(transitions, list):
                seen: set[str] = set()
                unique = []
                for entry in transitions:
                    fingerprint = json.dumps(entry, sort_keys=True)
                    if fingerprint not in seen:
                        seen.add(fingerprint)
                        unique.append(entry)
                document["transitions"] = unique

            # N6: populate the two handler-reach booleans from the document's own
            # reachability section. Wrapped because INV-APV-31 requires *any*
            # enrichment failure to degrade to an un-enriched push rather than
            # propagate: the method is defensive and does not raise, but an
            # unforeseen producer schema change must not become a task failure in
            # the MOP arms only — the same between-arm asymmetry INV-APV-24 exists
            # to remove. Degrading here keeps the dedup+minify result (INV-APV-31),
            # which is NOT the same as the outer fallback's source-file push.
            try:
                self._enrich_listener_reach(document, source_path)
            except Exception as e:  # noqa: BLE001 - see INV-APV-31 above
                self.logger.warning(
                    f"Listener reach enrichment failed for {source_path}: {e}. "
                    f"Pushing the document deduplicated and minified but un-enriched."
                )

            # delete=False so the file survives until the caller unlinks it after
            # the push, mirroring the _push_properties() temp-file idiom.
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as tmp:
                tmp_path = tmp.name
                json.dump(document, tmp, separators=(",", ":"))

            return tmp_path
        except (json.JSONDecodeError, OSError, MemoryError) as e:
            # Never raise: a compaction problem must not become a task failure in
            # one arm only, which would manufacture the very between-arm asymmetry
            # this function exists to remove (INV-APV-24, D3).
            self.logger.warning(
                f"Failed to compact static analysis JSON {source_path}: {e}. "
                f"Falling back to pushing the source file unchanged."
            )
            if tmp_path:
                # Remove the partial temp file so no temp survives the fallback
                # path (INV-APV-25). The source is untouched either way.
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
            return None

    def _index_reaches_target(self, reachability: list) -> tuple[dict[str, bool], bool]:
        """
        Index the document's `reachability` section by method signature.

        Every access is defensive because the section is producer output with no
        schema guarantee, and a single odd entry must not cost the whole
        enrichment.

        Args:
            reachability: The document's `reachability` list.

        Returns:
            `(reaches_by_signature, saw_methods)`. The flag distinguishes a
            genuinely empty section — an app that reaches nothing, for which
            false on every listener is correct — from a malformed one, for which
            no answer may be fabricated.
        """
        reaches_by_signature: dict[str, bool] = {}
        saw_methods = False
        for entry in reachability:
            if not isinstance(entry, dict):
                continue
            methods = entry.get("methods")
            if not isinstance(methods, list):
                continue
            saw_methods = True
            for method in methods:
                if not isinstance(method, dict):
                    continue
                signature = method.get("signature")
                if isinstance(signature, str):
                    reaches_by_signature[signature] = bool(method.get("reachesTarget"))
        return reaches_by_signature, saw_methods

    def _enrich_listener_reach(self, document: dict, source_path: str) -> int:
        """
        Populate the two handler-reach booleans on every listener, in place.

        The scoring pipeline has a direct/transitive axis it has never been able
        to use: the producer's method-level `directlyReachesTarget` means 0-hop —
        true only when the method's own body invokes a JCA target — and UI
        handlers delegate, so it is false for every handler in the corpus. That
        is why `[DM]` is 0 across all 181 apps and `mop_weight_direct=500` has
        never fired. The redefined semantics (INV-APV-32) is *the handler of THIS
        widget reaches a JCA target at any call depth*, which is the property the
        weight was always meant to reward, and it is computed from the same
        `reachesTarget` bit — never copied from the producer's 0-hop field.

        Both booleans therefore carry the same value by construction. They stay
        two fields because the consumer reads them as two: it takes this widget's
        own handler as the direct axis and derives the transitive axis from its
        own containment logic (`MopData.java:516-517,531-533`), with precedence
        over its local join. So the enrichment reaches the scoring pipeline with
        no jar change.

        Lookup is exact string match on the Soot signature: both sides come from
        the same document, and the producer emits `listeners[].handler` in the
        same form it uses for `methods[].signature`. A miss yields false on both
        fields and no warning — misses are expected in apps whose handler set and
        reachability set were computed over different class subsets.

        Expect sparsity, not saturation: over the 40-APK subset this flags 160 of
        45,200 listeners (0.4%), with only 7 apps carrying any flaggable listener.

        Args:
            document: Parsed static analysis JSON, modified in place. No
                structural guarantee is assumed — every section access is
                defensive.
            source_path: Source file path, named in the warning when the
                reachability section is unusable.

        Returns:
            Number of listeners enriched. Zero when the `reachability` section is
            missing or malformed, in which case no field is written at all and
            the caller pushes the document deduplicated and minified but
            un-enriched (INV-APV-31).
        """
        # A missing or non-list reachability section cannot be defaulted: writing
        # false everywhere would fabricate an answer indistinguishable from a
        # measured one. Return 0 instead, leaving the document un-enriched.
        reachability = document.get("reachability")
        if not isinstance(reachability, list):
            self.logger.warning(
                f"Static analysis document {source_path} has no usable "
                f"reachability section; pushing it un-enriched."
            )
            return 0

        reaches_by_signature, saw_methods = self._index_reaches_target(reachability)

        # A non-empty reachability section that yielded no methods[] anywhere is
        # the malformed shape, distinct from a genuinely empty one: an app with
        # `reachability: []` reaches nothing, and false on every listener is the
        # correct answer for it.
        if reachability and not saw_methods:
            self.logger.warning(
                f"Static analysis document {source_path} has a malformed "
                f"reachability section (no methods[] entries); pushing it un-enriched."
            )
            return 0

        enriched = 0
        windows = document.get("windows")
        for window in windows if isinstance(windows, list) else []:
            if not isinstance(window, dict):
                continue
            widgets = window.get("widgets")
            for widget in widgets if isinstance(widgets, list) else []:
                if not isinstance(widget, dict):
                    continue
                listeners = widget.get("listeners")
                for listener in listeners if isinstance(listeners, list) else []:
                    if not isinstance(listener, dict):
                        continue
                    handler = listener.get("handler")
                    reaches = isinstance(handler, str) and reaches_by_signature.get(
                        handler, False
                    )
                    listener["handlerReachesTarget"] = reaches
                    listener["handlerDirectlyReachesTarget"] = reaches
                    enriched += 1

        return enriched

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
                value = self._tool_config[python_key]
                # Serialize Python bools as lowercase true/false so the line matches what
                # the jar's Config loader expects (arm flags are Python bools in the variant
                # dicts; LLM keys are already lowercase strings). bool is an int subclass,
                # so this branch must precede any numeric handling.
                if isinstance(value, bool):
                    value = "true" if value else "false"
                lines.append(f"{java_key}={value}")
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

    def _models_endpoint(self, llm_url: str) -> str:
        """
        Build the `/v1/models` URL from the configured base URL.

        `llm_url` is an OpenAI-compatible base that already carries the `/v1`
        segment in every arm that sets it, so appending `/v1/models` blindly
        would produce `/v1/v1/models`.
        """
        base = llm_url.rstrip("/")
        return f"{base}/models" if base.endswith("/v1") else f"{base}/v1/models"

    def _capture_llm_provenance(self, llm_url: str, jar_path: str) -> Dict[str, Any]:
        """
        Record which backend actually served this run, by asking it.

        Reading the configured model name would record the intent, not the fact,
        and intent-versus-fact divergence is precisely the failure this exists to
        catch: an SGLang server restarted with a different checkpoint,
        quantization or sampling default serves a different experiment under an
        unchanged configuration, and nothing downstream could tell. So the model
        comes from a live `GET {llm_url}/v1/models` (INV-APV-33).

        When the query fails the run proceeds — aborting would trade a small
        evidential gap for a lost run — but the fields record the failure instead
        of being back-filled from configuration, so downstream analysis can
        distinguish "we know it was model X" from "we do not know". For the same
        reason `llm_sampling` is only populated on success: the sampling in
        effect is what the server honoured, and an unreachable server cannot
        attest to it.

        Note the address this queries is the one the *device* uses. In an
        emulator setup `llm_url` is the `10.0.2.2` host-loopback alias, which the
        harness itself cannot resolve, and the capture then records
        `unreachable` — an honest "unknown" rather than a fabricated value. A
        campaign that wants the record sets `APERV_LLM_BASE_URL` to a
        host-reachable address, which is what the Docker setup already does.

        Args:
            llm_url: OpenAI-compatible base URL configured for this arm.
            jar_path: Local path to the `ape-rv.jar` being pushed.

        Returns:
            `llm_backend`, `llm_model`, `llm_sampling`, `jar_sha256` and
            `capture_status`. `jar_sha256` identifies the binary for post-hoc
            correlation and is NOT the B3 gate — that gate's runtime half is the
            `git_sha` of the `[APE-BUILD]` banner, because the build stamp is a
            dexed Java constant and not a readable jar entry (INV-BUILD-09).
        """
        provenance: Dict[str, Any] = {
            "llm_backend": llm_url,
            "llm_model": None,
            "llm_sampling": None,
            "jar_sha256": None,
            "capture_status": "ok",
        }

        try:
            digest = hashlib.sha256()
            with open(jar_path, "rb") as jar_file:
                for chunk in iter(lambda: jar_file.read(1024 * 1024), b""):
                    digest.update(chunk)
            provenance["jar_sha256"] = digest.hexdigest()
        except OSError as e:
            provenance["capture_status"] = "jar_digest_failed"
            self.logger.warning(f"Could not digest {jar_path} for provenance: {e}")

        endpoint = self._models_endpoint(llm_url)
        # llm_url comes from configuration, and urlopen honours file: and other
        # local schemes — a mistyped value would make the tool read a local path
        # and record it as a served model. Only the two schemes an
        # OpenAI-compatible backend speaks are accepted.
        if not endpoint.startswith(("http://", "https://")):
            provenance["capture_status"] = "unsupported_llm_url_scheme"
            self.logger.warning(
                f"LLM provenance skipped: {llm_url!r} is not an http(s) URL."
            )
            return provenance

        try:
            with urllib.request.urlopen(endpoint, timeout=5) as response:  # noqa: S310
                served = json.load(response)
            models = [
                entry["id"]
                for entry in served.get("data", [])
                if isinstance(entry, dict) and "id" in entry
            ]
            if not models:
                provenance["capture_status"] = "no_models_served"
                return provenance
            # Comma-joined when the server offers several, so the record names
            # everything that could have answered rather than picking one.
            provenance["llm_model"] = ",".join(models)
            provenance["llm_sampling"] = {
                key: self._tool_config[key]
                for key in (
                    "llm_temperature",
                    "llm_top_p",
                    "llm_top_k",
                    "llm_percentage",
                    "llm_prompt_variant",
                )
                if key in self._tool_config
            }
        except (OSError, ValueError, KeyError, TypeError) as e:
            # OSError covers URLError and socket timeouts; ValueError covers a
            # response body that is not JSON. The run is never aborted for this.
            provenance["capture_status"] = "query_failed"
            self.logger.warning(
                f"LLM provenance query to {llm_url} failed: {e}. "
                f"Recording the failure rather than inferring from configuration."
            )

        return provenance

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
            Command with timeout = timeout_seconds + 45
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

        # Seed propagation (INV-APV-18): a configured seed reaches Monkey as `-s <seed>`
        # (parsed at Monkey.java:881-882, seeding RandomHelper) so paired-by-app runs are
        # reproducible. This Monkey `-s` is distinct from the adb `-s <serial>` at arg[0].
        # `seed` has no APERV_PROPERTY_MAPPING entry, so it never lands in ape.properties.
        seed = self._tool_config.get("seed")
        if seed is not None:
            cmd_args += ["-s", str(seed)]

        # +45s grace period gives APE-RV time to flush its WTG model, emit the
        # coverage dump and exit cleanly after --running-minutes expires. Without
        # this buffer, the Command timeout kills the process before it can write
        # final output.
        #
        # The 45 is a HYPOTHESIS about censored teardown durations, not a
        # measurement, and the distinction matters: among iter0 runs whose teardown
        # completed, the overrun beyond the exploration budget reaches 12,991 ms
        # with 32 runs stacked against the old 15 s ceiling and none beyond it —
        # the signature of a hard wall rather than a natural distribution. The
        # teardown duration of the runs that were cut is unobservable, which is
        # what censoring means, so no recovery rate can be claimed in advance; the
        # smoke reports what the wider window actually cost (design D9).
        return Command("adb", cmd_args, timeout_seconds + 45)

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
        # The JSON is compacted into a temp file first so it clears the Java-side
        # footprint guard (MopData.java:202); the source stays byte-identical as an
        # archived artifact that offline consolidation and resume re-parse
        # (INV-APV-20). The flag tracks whether the push succeeded so
        # _push_properties() knows whether to include ape.mopDataPath — it is set
        # identically on the compacted and the fallback path, so a compaction
        # failure is invisible to ape.properties.
        mop_json_pushed = False
        if self._tool_config.get("mop_data") == "static_analysis":
            static_json = self._find_static_analysis_file(task)
            if static_json:
                compacted = self._compact_static_analysis_json(static_json)
                push_path = compacted or static_json
                try:
                    self._push_file_to_device(
                        push_path,
                        "/data/local/tmp/static_analysis.json",
                        device_serial,
                        task.result.trace_file,
                    )
                    mop_json_pushed = True
                finally:
                    # Unlink in a finally so no temp survives even when the push
                    # raises RVToolExecutionError (INV-APV-25).
                    if compacted:
                        os.unlink(compacted)
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

        # Step 2b: Capture which backend actually serves this run (N4). Only for
        # arms that declare LLM keys — a non-LLM arm has nothing to attest, and
        # the absence of the record is not a failure there.
        #
        # The record goes to a sidecar next to the trace rather than into
        # TaskResult: TaskResult has no free-form field for it, and this change
        # deliberately adds no interface to rv-platform or rv-android-core. The
        # sidecar sits in the results directory alongside the .trace and .logcat
        # of the same run, which is where offline consolidation already looks.
        # It cannot be written into the trace itself: step 3 opens that file in
        # "wb" and would truncate anything written here.
        #
        # The discriminator is `llm_url`, not membership in LLM_ARM_KEYS: that
        # set contains `llm_percentage_no_substrate`, which every arm carries
        # through _BASELINE_ARM_FLAGS, so testing the set would query the server
        # for arms that never call it. `llm_url` is present only in arms that do.
        llm_url = self._tool_config.get("llm_url")
        if llm_url:
            provenance = self._capture_llm_provenance(llm_url, jar_path)
            provenance_path = (
                os.path.splitext(task.result.trace_file)[0] + ".provenance.json"
            )
            try:
                with open(provenance_path, "w") as provenance_file:
                    json.dump(provenance, provenance_file, indent=2)
            except OSError as e:
                # Losing the record must not cost the run — the same reasoning
                # that keeps a failed query non-fatal (INV-APV-33).
                self.logger.warning(
                    f"Could not write LLM provenance to {provenance_path}: {e}"
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
