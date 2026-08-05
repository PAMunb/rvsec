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

import gzip
import hashlib
import json
import os
import re
import shutil
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

from aperv_tool.tools.aperv.derive_mop_artifact import (
    ARTIFACT_SUFFIX,
    DEVICE_ARTIFACT_PATH,
    DerivationError,
    derive,
    digest_of,
    serialize_canonical,
)

# Tool constants
APERV_TOOL_NAME = "aperv"
APERV_JAR_NAME = "ape-rv.jar"
APERV_DEVICE_JAR_PATH = "/data/local/tmp/ape-rv.jar"
APERV_DEVICE_PROPERTIES_PATH = "/data/local/tmp/ape.properties"
APERV_MAIN_CLASS = "com.android.commands.monkey.Monkey"

# Suffix of the in-progress artifact write. The temporary file shares the results
# directory with its destination so the rename that publishes it is atomic.
ARTIFACT_TEMP_SUFFIX = ".mop.json.tmp"

# Strategies accepted by configure(), matching what the jar's ApeAgent.createAgent builds.
# "bfs" and "dfs" are absent deliberately: they were never agent types, and a run configured
# with either used to fall through to SataAgent silently. The jar now aborts on an unknown
# --ape value, so accepting them here would only let a run pass local validation and die on
# the device — the silent-degradation class this whole re-architecture removes. "replay" is
# legal in the jar but stays out too: it needs --ape-replay <log>, which this tool never
# passes. "random" remains reachable as aperv:sata@strategy=random even though the named
# random arm is retired.
APERV_AVAILABLE_STRATEGIES = ["sata", "random"]

# The top-level config keys that are Python orchestration rather than jar configuration.
# Everything else at the top level must be a mapped override key, or configure() raises:
# these are the only names that legitimately never reach ape.properties.
#
# device_port/device_serial/device_id are device addressing, not configuration: rv-experiment's
# ExecutionController injects all three into every tool's parameters whenever --device-port is
# set, which every Docker compose file does. The tool reads the serial from task.config.device_id
# at execution time and never from _tool_config, so they are accepted and ignored here — rejecting
# them would abort every containerized and parallel run before a device is touched.
APERV_ORCHESTRATION_KEYS = frozenset(
    {
        "preset",
        "overrides",
        "strategy",
        "mop_data",
        "seed",
        "device_port",
        "device_serial",
        "device_id",
    }
)

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
    "mop_weight_open_menu": "ape.mopWeightOpenMenu",
    "mop_weight_wtg": "ape.mopWeightWtg",
    # gh11/gh13: per-step component-trigger probability (default 0.0 = disabled).
    "component_percentage": "ape.componentPercentage",
    # mop-fairtest: cap on deterministic MOP short-circuit picks per (widget,type,activity).
    "mop_target_pick_cap": "ape.mopTargetPickCap",
    "coverage_boost_weight": "ape.coverageBoostWeight",
    # RV exploration flags. Every preset states all of them, so an arm overrides one only
    # to deviate from its preset — which no surviving arm does.
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
    # MOP reach strategies (mop-reach-strategies: A′/B). E-min is the activity-trigger
    # launcher (activity_trigger_enabled below).
    "mop_activity_source_components": "ape.mopActivitySourceComponents",
    "mop_frontier_weight": "ape.mopFrontierWeight",
    # Frontier boosting + component triggering (gh43).
    "frontier_boost_weight": "ape.frontierBoostWeight",
    "activity_trigger_enabled": "ape.activityTriggerEnabled",
    # Global tuning knob (idle-timeout-cap): mapped so an experiment can lower the
    # idle-drain ceiling. Applies to every arm, so it never distinguishes one.
    "max_idle_timeout_ms": "ape.maxIdleTimeoutMs",
    # Launcher-dose sub-params (activity-trigger-dose): the cadence at which the launcher
    # fires and the per-run launch cap. A paired comparison sets the same dose on both
    # arms, so they tune activity_trigger_enabled without themselves selecting a behavior.
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
    # mop-reach-strategies F′ seam: the LLM boost applied when the substrate is widgetless.
    "llm_percentage_no_substrate": "ape.llmPercentageNoSubstrate",
    "llm_prompt_variant": "ape.llmPromptVariant",
    # Live Feature.LLM sub-parameters in the jar's ownership table. The snap tolerance is
    # set by mop_on_llm_70 alone; max_tokens is mapped and set by no arm, so it takes the
    # jar's default.
    "llm_max_tokens": "ape.llmMaxTokens",
    "llm_snap_tolerance_px": "ape.llmSnapTolerancePx",
    # Deployment provenance, not configuration: the application list this run was
    # drawn from. The jar recognises the key, echoes it into the trace's opening
    # record and reads it nowhere, so it changes no behaviour — it makes a recorded
    # run answer "which corpus?" from its own artifacts, which today is
    # reconstructed after the fact from a compose file or an operator's memory.
    "corpus_basis": "ape.corpusBasis",
}

# `<corpus-id>:<sha256>`, e.g. `subset40:b60903ad…d48d4`. Both halves earn their
# place: the identifier is what a human reads in a report, and the digest is what
# makes two runs provably drawn from the same list rather than from two lists that
# happen to share a name.
CORPUS_BASIS_PATTERN = re.compile(r"^[A-Za-z0-9._-]+:[0-9a-f]{64}$")


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
    - Named variants: eight names carrying seven configurations, each a jar preset
      plus a dict of override deltas (default [alias of sata], sata, sata_mop,
      sata_llm, sata_mop_llm, and the three E3 decisive-run arms mop_on_llm_off,
      mop_off_llm_off, mop_on_llm_70)
    - Eager validation in configure() catches typos before device access, including
      tool-DSL overrides that no arm could honour
    - ape.properties injection states the preset and its deltas without modifying the JAR
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

        Eight names carrying seven configurations. An arm is a `preset` name plus an
        `overrides` dict of deltas over it, and nothing else: the jar owns what a preset
        means, this module owns the experimental matrix — which arms exist, what their
        names are, and how each differs from its preset.

        Four are one-to-one with the jar's presets and carry nothing but the
        deployment-specific server URL where an LLM is involved — `sata` (aperv),
        `sata_mop` (mop), `sata_llm` (llm), `sata_mop_llm` (llm_mop) — with `default`
        bound to the same object as `sata` (INV-TOOL-02). The other three are the E3
        decisive run's arms: a reference on the reach package, its MOP-off control, and
        its LLM arm.

        Python-only orchestration keys stay at the top level and never reach
        ape.properties: `strategy` (the --ape flag), `mop_data` (whether the derived MOP
        artifact is pushed), `seed`, and the two jar-provenance declarations.

        Returns:
            Dictionary mapping variant names to configuration parameters
        """
        # "mop_data" and "strategy" are Python-only keys consumed during execution; they are
        # NOT written to ape.properties. Build sata once and bind default to the same object
        # so the alias holds by construction (INV-TOOL-02).
        sata = {"preset": "aperv", "strategy": "sata", "overrides": {}}
        return {
            # The four preset-identity arms. Each is one-to-one with a jar preset and carries
            # nothing but the deployment-specific server URL where an LLM is involved — the
            # preset names an arm, the URL names a machine. throttle_ms is absent from all of
            # them because the aperv preset already states ape.defaultGUIThrottle=200.
            "default": sata,
            "sata": sata,
            # sata_mop is the frozen corpus's identity: 4,096 aperv:sata_mop.trace artifacts
            # and 1,066 files under results/ carry that exact token, so renaming it would
            # orphan every one of those runs from resume and every row from consolidation.
            # A data-identity constraint, not backward compatibility (INV-APV-42).
            "sata_mop": {
                "preset": "mop",
                "strategy": "sata",
                "mop_data": "static_analysis",
                "overrides": {},
            },
            # 10.0.2.2 is the Android emulator alias for host loopback; APERV_LLM_BASE_URL
            # redirects it at L5 without touching the variant table.
            "sata_llm": {
                "preset": "llm",
                "strategy": "sata",
                "overrides": {"llm_url": "http://10.0.2.2:30000/v1"},
            },
            "sata_mop_llm": {
                "preset": "llm_mop",
                "strategy": "sata",
                "mop_data": "static_analysis",
                "overrides": {"llm_url": "http://10.0.2.2:30000/v1"},
            },
            # --- E3 decisive-run arms (gh90) -------------------------------------
            # The three arms of the run that decides whether the LLM stays in the
            # design. All three sit on the reach package (INV-APV-30) — the
            # standing rule is *sempre modo frontier* — and each contrast is
            # single-factor: arm 2 differs from arm 1 only in the MOP keys, arm 3
            # only in the LLM keys, which the override dicts now make readable
            # directly rather than only through a test.
            #
            # The names are normative, not cosmetic: the variant string is the
            # resume identity key (platform.py:308-318) and the consolidation
            # column key ({arm}__{metric}), so a rename silently splits a
            # campaign's results.
            #
            # Arm 1 absorbs the retired sata_mop_act_frontier: the two carried
            # byte-identical effective configurations — the ANC2 anchor under two
            # names — so the reference is not a newly invented baseline but the
            # configuration that won the cmpma multi-arm comparison (cov_mop
            # 37.75% vs <=35%, Friedman+Holm), under the name the decisive run
            # recorded. E-min is the activity-trigger launcher.
            "mop_on_llm_off": {
                "preset": "mop",
                "strategy": "sata",
                "mop_data": "static_analysis",
                "overrides": {
                    "mop_activity_source_components": True,
                    "frontier_boost_weight": 200,
                    "mop_frontier_weight": 200,
                    "activity_trigger_enabled": True,
                },
            },
            # Arm 2 — the experiment's first control arm. Every APE-RV run ever
            # executed had MOP guidance on, so no measured difference has ever
            # been attributable to MOP guidance rather than to APE's baseline
            # exploration. arm 1 vs arm 2 is RQ-C1.
            #
            # The shape is forced, not chosen (INV-APV-29). Three things could
            # plausibly mean MOP-off, and two of them silently destroy the
            # experiment:
            #
            #   1. Point ape.mopDataPath at a missing file -> requireMopArm raises
            #      StopTestingException and the whole run ABORTS.
            #   2. Omit mop_data so the path is never set -> loads as null without
            #      aborting, but WtgPass and FrontierPass both require
            #      mopData != null, so the generic WTG and frontier navigation die
            #      as collateral. The contrast would then be "full substrate versus
            #      almost no substrate", not "MOP guidance on versus off".
            #   3. Keep the document, zero the weights, turn the trigger off -> the
            #      MOP short-circuits become no-ops (pickBestMopTarget requires
            #      mopBoost > 0) while the frontier and WTG passes keep running on
            #      generic signal.
            #
            # Only the third isolates MOP guidance, so mop_data stays present and
            # frontier_boost_weight is deliberately NOT zeroed: the control removes
            # MOP guidance, not navigation (INV-APV-30). mop_frontier_weight and
            # activity_trigger_enabled are absent because the mop preset already
            # states them at 0 and false — an override restating a preset value
            # would be a delta that is not a delta.
            "mop_off_llm_off": {
                "preset": "mop",
                "strategy": "sata",
                "mop_data": "static_analysis",
                "overrides": {
                    "mop_activity_source_components": True,
                    "frontier_boost_weight": 200,
                    "mop_weight_direct": 0,
                    "mop_weight_transitive": 0,
                    "mop_weight_open_menu": 0,
                    "mop_weight_wtg": 0,
                },
            },
            # Arm 3 — the LLM dose the Phase-A calibration settled on (v13 at 70%,
            # temperature 0), stated here because this is now its only home. 0.7 is
            # the only dose with a measured 300 s counterpart on this substrate
            # and subset, which is what lets the 1800 s result be read as a
            # dose x budget interaction (design D8). arm 1 vs arm 3 is RQ-C3.
            "mop_on_llm_70": {
                "preset": "llm_mop",
                "strategy": "sata",
                "mop_data": "static_analysis",
                "overrides": {
                    "mop_activity_source_components": True,
                    "frontier_boost_weight": 200,
                    "mop_frontier_weight": 200,
                    "activity_trigger_enabled": True,
                    "llm_url": "http://10.0.2.2:30000/v1",
                    "llm_prompt_variant": "v13",
                    "llm_percentage": 0.7,
                    "llm_temperature": 0,
                    # The raised snap radius. Widening it makes more LLM answers
                    # resolve to a widget, which pays off only against a jar that
                    # bans dead pairs: without the ban the extra resolutions are
                    # repeated taps on pairs already known to produce no new
                    # state, and the widening amplifies the measured 25.6%
                    # dead-call waste instead of rescuing near-misses. Which jar
                    # is installed is a deployment fact, recorded per run by the
                    # jar_sha256 of the run's provenance (INV-APV-59); this file
                    # states the arm, not the binary.
                    "llm_snap_tolerance_px": 150,
                },
            },
        }

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure tool with resolved variant parameters.

        An arm is a preset name plus a dict of override deltas, so configure()
        validates all three parts of that shape — strategy, preset, overrides — and
        folds any tool-DSL override into place. Everything is raised before any
        device interaction, so a typo in experiment YAML costs nothing (INV-APV-02).

        Args:
            config: Configuration dictionary with tool-specific parameters

        Raises:
            ConfigurationError: If strategy is absent or outside
                APERV_AVAILABLE_STRATEGIES, if preset is absent or empty, if
                overrides is not a dict, if a top-level key is neither a mapped
                override nor a recognised orchestration key (INV-APV-39), or if
                `corpus_basis` is present and does not match CORPUS_BASIS_PATTERN
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

        # The preset is what the jar resolves the arm from, so an arm without one has no
        # configuration at all — the jar would fall back to its own defaults while the
        # results directory still carried the arm's name.
        preset = config.get("preset")
        if not preset:
            raise ConfigurationError(
                "aperv: 'preset' key is required and must be non-empty. "
                "An arm is a preset name plus its override deltas."
            )

        overrides = config.get("overrides", {})
        if not isinstance(overrides, dict):
            raise ConfigurationError(
                f"aperv: 'overrides' must be a dict, got {type(overrides).__name__}."
            )

        # Defensive copy preserves the caller's dict.
        self._tool_config = config.copy()
        self._tool_config["overrides"] = dict(overrides)

        # Fold the tool DSL's overrides into `overrides` (INV-APV-39).
        #
        # ToolFactory merges DSL parameters at the TOP LEVEL of the config
        # (`{**variant_config, **tool_config.parameters}`), while _push_properties()
        # reads only `overrides`. Without this fold, `aperv:sata_mop@mop_frontier_weight=400`
        # would land somewhere nothing reads: no property line, no error, and a run whose
        # configuration silently differs from what the operator asked for. That is the exact
        # failure class this change exists to remove, so it may not be introduced by it.
        #
        # The DSL value wins over an arm's own entry for the same key — the DSL is the
        # operator's last word, which is what makes it usable for smokes and ablations
        # without declaring a variant.
        for key in list(self._tool_config):
            if key in APERV_PROPERTY_MAPPING:
                self._tool_config["overrides"][key] = self._tool_config.pop(key)

        # Anything still at the top level that is neither orchestration nor a mapped
        # override cannot be honoured. Failing loudly is the whole point: a silently
        # dropped key runs the arm unchanged while the operator believes it was overridden.
        unrecognised = set(self._tool_config) - APERV_ORCHESTRATION_KEYS
        if unrecognised:
            raise ConfigurationError(
                f"aperv: unrecognised configuration key(s) {sorted(unrecognised)}. "
                "A key must be either an APERV_PROPERTY_MAPPING override or one of "
                f"{sorted(APERV_ORCHESTRATION_KEYS)}."
            )

        # An override the mapping cannot translate has no ape.* name to be written under,
        # so the jar would abort on the properties file. Checking it here rather than at
        # push time is what makes INV-APV-02 true as stated: the jar, the broadcast catalog
        # and the MOP artifact are all pushed before ape.properties is generated, so a check
        # living in _push_properties() would already have cost three pushes and the
        # derivation. One rule covers both sources of the key — an arm's own overrides dict
        # and the DSL keys just folded into it.
        unmapped = set(self._tool_config["overrides"]) - set(APERV_PROPERTY_MAPPING)
        if unmapped:
            raise ConfigurationError(
                f"aperv: override key(s) {sorted(unmapped)} have no ape.* property "
                "mapping, so the jar would reject the properties file."
            )

        # A malformed corpus basis is a broken assertion rather than a broken run, and
        # that is why it is caught here. The jar accepts any string and echoes it, so a
        # value that is not `<corpus-id>:<sha256>` produces a run whose provenance line
        # looks populated while nothing can be checked against it — the campaign's
        # pre-flight would be comparing a recomputed digest against something that never
        # was one. Shape is the whole of what this side owns: whether the digest matches
        # the list is verified where the list lives, by recomputing it from the file.
        # Reading it after the DSL fold covers both sources of the key at once, an arm's
        # own `overrides` dict and an `@corpus_basis=…` parameter.
        basis = self._tool_config["overrides"].get("corpus_basis")
        if basis is not None and (
            not isinstance(basis, str) or not CORPUS_BASIS_PATTERN.match(basis)
        ):
            raise ConfigurationError(
                f"aperv: 'corpus_basis' value {basis!r} is not of the form "
                "<corpus-id>:<sha256>, so the provenance it would record cannot be "
                "verified against any list. Expected /^[A-Za-z0-9._-]+:[0-9a-f]{64}$/."
            )

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

    def _derive_mop_artifact(self, task: Task) -> str:
        """
        Return the host path of the derived MOP artifact, generating it when needed.

        The artifact is a pure function of the full static-analysis JSON, so
        freshness is a digest comparison rather than a timestamp one: mtime does not
        survive a copy, a resume or a container boundary, and a stale artifact would
        arm a run against a substrate that no longer describes the app. The recorded
        digest lives inside the artifact, so there is no sidecar to keep consistent.

        Writes go through a temporary file in the same directory followed by an
        atomic rename, so a crash mid-write cannot leave a truncated artifact that a
        later run would read and trust.

        The cache sits next to its source in the results directory: inspectable,
        diffable and archived with the run.

        Args:
            task: Task whose `results_dir` and `config.apk_name` locate the full JSON.

        Returns:
            Path of the `<apk_name>.mop.json` whose `source.digest` matches the
            current full JSON.

        Raises:
            RVToolExecutionError: The full JSON is unreadable, unparseable or too
                large to hold in memory, the derivation refused it, or the artifact
                could not be written. `MemoryError` is caught with the rest because
                the document is parsed whole before deriving, and a bare one would
                lose the path and tool context the caller needs to act. No partial
                file survives any of those paths.
        """
        source_path = os.path.join(task.results_dir, f"{task.config.apk_name}.json")
        artifact_path = os.path.join(
            task.results_dir, f"{task.config.apk_name}{ARTIFACT_SUFFIX}"
        )

        tmp_path = None
        try:
            with open(source_path, "rb") as source_file:
                raw = source_file.read()
            digest = digest_of(raw)

            if self._cached_artifact_digest(artifact_path) == digest:
                self.logger.debug(f"Reusing cached MOP artifact {artifact_path}")
                return artifact_path

            artifact = derive(
                json.loads(raw),
                source_file=os.path.basename(source_path),
                source_digest=digest,
            )
            payload = serialize_canonical(artifact)

            handle, tmp_path = tempfile.mkstemp(
                dir=task.results_dir, suffix=ARTIFACT_TEMP_SUFFIX
            )
            with os.fdopen(handle, "wb") as tmp_file:
                tmp_file.write(payload)
            os.replace(tmp_path, artifact_path)
            tmp_path = None

            stats = artifact["stats"]
            self.logger.info(
                f"Derived MOP artifact {artifact_path} "
                f"({len(raw)} -> {len(payload)} bytes, "
                f"flagged={stats['flagged']}/{stats['widgetsTotal']} widgets, "
                f"mopActivities={len(artifact['mopActivities'])}, "
                f"recovered={stats['recovered']})"
            )
            return artifact_path
        except (DerivationError, OSError, json.JSONDecodeError, MemoryError) as e:
            raise RVToolExecutionError(
                f"Could not derive the MOP artifact from {source_path}: {e}",
                tool_name=self.name,
                cause=e,
            )
        finally:
            # Reached on the error paths and on an os.replace that never ran; a
            # successful rename has already consumed the temporary file.
            if tmp_path is not None:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def _cached_artifact_digest(self, artifact_path: str) -> str | None:
        """
        Read the source digest a cached artifact records, or None when there is no
        usable cache.

        A missing, unreadable or corrupt artifact is not an error: it is a cache
        miss, and regenerating costs milliseconds. Only the digest is read, because
        it is the only field freshness depends on.
        """
        try:
            with open(artifact_path, "r") as artifact_file:
                cached = json.load(artifact_file)
        except (OSError, json.JSONDecodeError):
            return None
        source = cached.get("source") if isinstance(cached, dict) else None
        return source.get("digest") if isinstance(source, dict) else None

    def _push_properties(
        self, device_serial: str, trace_file_path: str, mop_json_pushed: bool = False
    ) -> None:
        """
        Generate ape.properties from tool config and push to device.

        The file states the arm as the jar reads it: a preset name, the MOP artifact
        path when one was pushed, and one line per override delta. What the preset
        contains is the jar's business — this side never restates it.

            ape.preset=<preset>                                # always first
            ape.mopDataPath=/data/local/tmp/mop-artifact.json  # only when pushed
            ape.<mapped-override-key>=<value>                  # deltas, mapping order

        The order is fixed so two runs of the same arm produce byte-identical output.

        Args:
            device_serial: Device serial number
            trace_file_path: Trace file for logging
            mop_json_pushed: If True, include ape.mopDataPath in properties
        """
        # Every key here is mappable: configure() rejected the unmappable ones before the
        # run reached a device (INV-APV-02).
        overrides = self._tool_config.get("overrides", {})

        lines = [f"ape.preset={self._tool_config['preset']}"]
        if mop_json_pushed:
            # Same constant the push destination uses, so the property and the file
            # cannot drift apart.
            lines.append(f"ape.mopDataPath={DEVICE_ARTIFACT_PATH}")
        # Walk the mapping rather than the overrides so line order follows the table and
        # is stable across runs regardless of how the arm dict was written.
        for python_key, java_key in APERV_PROPERTY_MAPPING.items():
            if python_key in overrides:
                value = overrides[python_key]
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

    def _provenance_query_url(self, llm_url: str) -> str:
        """
        Resolve the arm's `llm_url` to an address this process can actually reach.

        `llm_url` has two consumers in different address spaces. The jar reads it
        from `ape.properties` and runs *inside* the emulator, where `10.0.2.2` is
        QEMU's user-mode alias for the host loopback. This query runs outside the
        emulator, where that alias resolves to nothing at all — configured
        verbatim it simply times out while the LLM itself works, which is how the
        field arrived empty from a server the jar was reaching normally.

        `127.0.0.1` is the right address in both deployments: on a host-driven
        run it is SGLang's published port, and in the containerized run it is the
        socat bridge the entrypoint binds there
        (`docker/rvandroid/docker-entrypoint.sh`). Only the query is resolved —
        the value written into `ape.properties` is untouched, so the jar keeps
        the alias it needs.
        """
        return llm_url.replace("//10.0.2.2:", "//127.0.0.1:").replace(
            "//10.0.2.2/", "//127.0.0.1/"
        )

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

        The address queried is deliberately not the configured one:
        `_provenance_query_url` resolves the emulator-only `10.0.2.2` alias,
        because this runs outside the emulator while `llm_url` is written for the
        jar that runs inside it. `llm_backend` records the address actually
        contacted — a record naming an address that was never reached would be
        worse than none.

        Args:
            llm_url: OpenAI-compatible base URL configured for this arm.
            jar_path: Local path to the `ape-rv.jar` being pushed.

        Returns:
            `llm_backend`, `llm_model`, `llm_sampling`, `jar_sha256` and
            `capture_status`. `jar_sha256` is the digest of the binary about to
            be pushed, and it is the only statement this repository makes about
            which jar ran: `ape-rv.jar` carries no build stamp to read, so the
            identity is measured from the file at push time rather than declared
            anywhere in source (INV-APV-59).
        """
        query_url = self._provenance_query_url(llm_url)
        provenance: Dict[str, Any] = {
            "llm_backend": query_url,
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

        endpoint = self._models_endpoint(query_url)
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
            # Read from the arm's overrides: a sampling key the arm does not override is
            # the preset's, and recording the preset's value here would misreport a
            # deployment-wide default as this arm's declared setting. What the run
            # actually resolved is echoed by the jar into the trace.
            overrides = self._tool_config.get("overrides", {})
            provenance["llm_sampling"] = {
                key: overrides[key]
                for key in (
                    "llm_temperature",
                    "llm_top_p",
                    "llm_top_k",
                    "llm_percentage",
                    "llm_prompt_variant",
                )
                if key in overrides
            }
        except (OSError, ValueError, KeyError, TypeError) as e:
            # OSError covers URLError and socket timeouts; ValueError covers a
            # response body that is not JSON. The run is never aborted for this.
            provenance["capture_status"] = "query_failed"
            self.logger.warning(
                f"LLM provenance query to {query_url} failed: {e}. "
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

    def _gzip_trace(self, trace_file_path: str) -> None:
        """Write a compressed copy of the raw capture beside the trace.

        From stage 4 the trace is NDJSON and grows to roughly 3.5 GB per 880
        tasks, so compression at rest is worth a step; it is the Python side's
        job because the jar writes to stdout and never touches the file.

        Three properties are deliberate. The step is **write-only**: it reads the
        trace and writes only the `.gz`, so `task.result.trace_file` stays the
        raw capture byte for byte — no reformatting, no truncation, and no
        conversion back to the retired line family anywhere in this tool
        (INV-APV-52). It **inspects nothing**: the trace's content is never
        parsed, no record is looked for, no sentinel is checked, no exit code is
        interpreted and no task status changes (INV-APV-53) — identifying a
        truncated run stays post-hoc analysis over trace and logcat timestamps.
        And it is **non-fatal**: a failure here
        (a full results volume, a permission problem) costs a compressed copy,
        never a run's data, so it logs a WARNING naming the trace and returns.

        The name is the full trace path with the suffix appended, which yields
        `<run>.trace.ndjson.gz`. Substituting the suffix instead would break the
        `.trace` stem that `clock_logcat_join` and `coverage_dump` key on to find
        a run's sibling files, for a cosmetic gain (design D-3).

        Args:
            trace_file_path: Path to the trace file written by
                execute_tool_specific_logic.
        """
        gzip_path = str(trace_file_path) + ".ndjson.gz"
        try:
            # copyfileobj streams in chunks, so a multi-gigabyte trace is never
            # held in memory.
            with open(trace_file_path, "rb") as source:
                with gzip.open(gzip_path, "wb") as target:
                    shutil.copyfileobj(source, target)
            self.logger.debug(f"Compressed trace to {gzip_path}")
        except Exception as e:
            self.logger.warning(
                f"Failed to compress trace {trace_file_path}: {e} — "
                "the uncompressed trace is untouched and the run is unaffected"
            )

    @ErrorHandler.handle_errors(
        component="ApeRVTool", phase="execute_tool_specific_logic", reraise=True
    )
    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
        """
        Execute APE-RV exploration on the device.

        Orchestrates JAR resolution, device push, properties push, command
        execution, the empty-trace check and trace compression. Timeout is the
        expected normal exit for exploration tools, and collection runs on that
        path too — it is where most runs end.

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

        # Step 1c: Derive and push the MOP artifact for MOP-guided variants.
        # Only the derived projection travels: the full JSON stays where it is as the
        # archived source that offline consolidation and resume re-parse.
        #
        # A MOP arm without its static-analysis input is a failed task, not a
        # degraded run. The warn-and-continue this replaces produced runs labelled as
        # MOP arms that explored as pure SATA, indistinguishable in the results
        # directory from a real one — the worst evidence-to-signal ratio in the
        # pipeline. Failing here makes the supervisor retry it and shows it in the
        # run summary.
        mop_json_pushed = False
        if self._tool_config.get("mop_data") == "static_analysis":
            static_json = self._find_static_analysis_file(task)
            if not static_json:
                results_dir = getattr(task, "results_dir", None) or "<results_dir>"
                apk_name = getattr(task_config, "apk_name", None) or "<apk_name>"
                expected_path = os.path.join(results_dir, f"{apk_name}.json")
                raise RVToolExecutionError(
                    f"MOP arm cannot arm: no static analysis JSON at {expected_path}",
                    tool_name=self.name,
                    cause=None,
                )
            artifact_path = self._derive_mop_artifact(task)
            self._push_file_to_device(
                artifact_path,
                DEVICE_ARTIFACT_PATH,
                device_serial,
                task.result.trace_file,
            )
            mop_json_pushed = True

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
        # The discriminator is `llm_url` in the arm's overrides, not the preset name.
        # Both say the same thing today — the llm and llm_mop presets state the routing
        # gates ON, and INV-APV-38 requires every such arm to supply the URL — but the URL
        # is what this step actually needs, so testing for it cannot go looking for a
        # server that was never configured.
        llm_url = self._tool_config.get("overrides", {}).get("llm_url")
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
            # Collection runs on this path too, before the re-raise. Timeout is
            # how a normal exploration run ends — it is the majority path, not
            # the exception — so skipping compression here would exempt most
            # runs from it. The trace captured up to the kill is compressed as
            # it stands, truncated final line included.
            self._gzip_trace(task.result.trace_file)
            raise RVToolTimeoutError(
                f"APE-RV timed out after {timeout_seconds} seconds",
                tool_name=self.name,
            )

        # Step 4: Detect silent failures. An empty trace suggests APE-RV crashed
        # at startup (e.g., missing CLASSPATH, incompatible API level) without
        # producing any output. This is a warning, not an error, because coverage
        # may still have been captured via logcat independently.
        self._check_empty_trace(task.result.trace_file)

        # Step 5: Compress the raw capture beside the trace. Write-only and
        # non-fatal; the trace itself is left byte-identical (INV-APV-52).
        self._gzip_trace(task.result.trace_file)

        self.logger.info("APE-RV execution completed successfully")
