"""
Configuration mapping for RVAgentTool.

Maps platform Task/ToolConfig to RVAgentConfig for rv-agent execution.
"""

from typing import Any, Dict, Optional

from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task

# Local, explicit copy of the agent-side kill-switch registry (RV_STEERING_FLAGS
# in rv_agent `strategies/rvagent_strategy/ranking/pipeline.py`): every
# arm-defining key mapped to its off/0 value. Kept as a literal here so tool
# registration stays free of the heavy rv_agent import (the tool imports rv_agent
# lazily inside execute). The guard pytest asserts this dict equals
# RV_STEERING_FLAGS, so any drift between the two fails CI (INV-RVA-01/02).
RV_STEERING_OFF: Dict[str, Any] = {
    # MOP/WTG scorer weights — gate whether MOP/WTG steering is active at all.
    "mop_direct_score": 0.0,
    "mop_transitive_score": 0.0,
    "wtg_guided_score": 0.0,
    # Ported steering scorers / launch / trigger flags.
    "mop_frontier_weight": 0.0,
    "mop_activity_source_components": False,
    "trigger_mop_first": False,
    "component_trigger_enabled": False,
    "state_mop_density_enabled": False,
    "form_completion_enabled": False,
    # Exploration guards and caps.
    "foreign_activity_guard": False,
    "back_menu_pick_cap": 0,
    "mop_target_pick_cap": 0,
    "idle_timeout_cap": 0,
    "dynamic_epsilon": False,
    "activity_budget_enabled": False,
}

# Mapped-but-not-arm-defining knobs. These flow through for calibration and
# `@param=value` overrides but are NOT required in every variant: each is
# subordinate to a gate flag (launch cadence/cap gated by trigger_mop_first,
# component cadence gated by component_trigger_enabled) or is the deterministic
# seed. `pure_mode` is the kill-switch *driver* (not itself arm-defining) and
# must still reach RVAgentConfig. Mirrors the aperv precedent of mapping
# max_idle_timeout_ms / activity-trigger-dose sub-params without marking them
# arm-defining.
RV_TUNING_PARAMS = (
    "pure_mode",
    "seed",
    "launch_cadence",
    "launch_cap",
    "component_percentage",
)


def build_agent_config_dict(
    task: Task, app: App, tool_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Build RVAgentConfig dictionary from platform task context.

    Maps task configuration, app metadata, and tool variant configuration
    to RVAgentConfig parameters.

    Args:
        task: Platform task with configuration and static data
        app: Application under test
        tool_config: Tool variant configuration (from configure())

    Returns:
        Dictionary suitable for RVAgentConfig construction
    """
    # Start with required field
    config_dict = {
        "package_name": app.package_name,
    }

    # Map device_id, timeout, and repetition from task configuration
    task_config = task.config if hasattr(task, "config") else None
    if task_config:
        if hasattr(task_config, "device_id") and task_config.device_id:
            config_dict["device_id"] = task_config.device_id
        if hasattr(task_config, "timeout") and task_config.timeout:
            config_dict["timeout"] = task_config.timeout
        if hasattr(task_config, "repetition") and task_config.repetition:
            config_dict["repetition"] = task_config.repetition

    # Map agent_mode from tool variant config
    if "agent_mode" in tool_config:
        config_dict["agent_mode"] = tool_config["agent_mode"]

    # Map llm_probability from tool variant config
    if "llm_probability" in tool_config:
        config_dict["llm_probability"] = tool_config["llm_probability"]

    # Map strategy from tool variant config
    if "strategy" in tool_config:
        config_dict["strategy"] = tool_config["strategy"]

    # NOTE: timeout is ALWAYS from task.config, never from tool_config
    # The platform controls execution timeout, not the tool variant

    # Map debug_mode from tool variant config
    if "debug_mode" in tool_config:
        config_dict["debug_mode"] = tool_config["debug_mode"]

    # Map LLM configuration from tool variant config
    llm_params = [
        "llm_model",
        "llm_base_url",
        "llm_temperature",
        "llm_top_p",
        "llm_top_k",
        "llm_max_tokens",
        "llm_timeout",
        "prompt_version",
    ]
    for param in llm_params:
        if param in tool_config:
            config_dict[param] = tool_config[param]

    # Map exploration strategy parameters
    strategy_params = [
        "plateau_window",
        "max_input_variations",
        "stochastic_probability",
        "stochastic_temperature",
        # Advanced exploration (gh26)
        "backtrack_saturation_threshold",
        "multi_value_saturation_threshold",
        "mop_nav_weight",
        "mop_max_input_variations",
    ]
    for param in strategy_params:
        if param in tool_config:
            config_dict[param] = tool_config[param]

    # Map scorer weight parameters (for calibration)
    scorer_params = [
        # MopScorer
        "mop_direct_score",
        "mop_transitive_score",
        # WtgScorer
        "wtg_guided_score",
        # SaturationScorer
        "unsaturated_bonus",
        # VisitationPenaltyScorer
        "visitation_penalty_factor",
        # StrengthScorer
        "strength_weight",
        # GradualDecayScorer
        "gradual_decay_base",
        "gradual_decay_rate",
        "gradual_decay_min_visits",
        # ComponentPriorityScorer
        "component_high_priority",
        "component_medium_priority",
        # SuccessorTracker
        "max_re_enables",
        "ui_coverage_threshold",
        # CoverageDensityScorer (gh26)
        "coverage_density_weight",
        # RewardPropagator (gh26)
        "reward_gamma",
        "reward_score_weight",
        # Exploration
        "scroll_probability",
    ]
    for param in scorer_params:
        if param in tool_config:
            config_dict[param] = tool_config[param]

    # Map error detection parameters (gh18)
    error_detection_params = [
        "error_detection_confidence",
        "error_max_indicator_size",
        "error_max_indicator_count",
        # Spatial association
        "spatial_edittext_boost",
        "spatial_spinner_boost",
        "spatial_min_match_threshold",
    ]
    for param in error_detection_params:
        if param in tool_config:
            config_dict[param] = tool_config[param]

    # Map fallback/memory parameters
    fallback_params = [
        "max_short_term_iterations",
        "llm_max_retries",
    ]
    for param in fallback_params:
        if param in tool_config:
            config_dict[param] = tool_config[param]

    # Map gh77 RV steering flags (arm-defining) + kill-switch driver + tuning
    # knobs. The arm-defining keys are the single source of truth in
    # RV_STEERING_OFF (a pinned copy of the agent kill-switch registry); mapping
    # every one of them here is what INV-RVA-02 requires — no arm-defining key may
    # be silently dropped on the way to RVAgentConfig. RV_TUNING_PARAMS carries
    # pure_mode (the kill-switch driver), seed, and the gate-subordinate cadence/
    # cap knobs. (mop_direct_score/mop_transitive_score/wtg_guided_score also
    # appear in scorer_params above; re-listing them here is a harmless idempotent
    # pass-through and keeps the arm-defining mapping visible in one place.)
    rv_arm_params = list(RV_STEERING_OFF) + list(RV_TUNING_PARAMS)
    for param in rv_arm_params:
        if param in tool_config:
            config_dict[param] = tool_config[param]

    # Map metrics output directory from task results_dir if available
    if hasattr(task, "results_dir") and task.results_dir:
        config_dict["metrics_output_dir"] = task.results_dir

    return config_dict


def get_static_data(task: Task) -> Optional[Any]:
    """
    Extract static analysis data from task context.

    The platform's StaticAnalysisComponent loads static data into
    task.static_data before tool execution.

    Args:
        task: Platform task with potential static data

    Returns:
        StaticAnalysisData if available, None otherwise
    """
    if hasattr(task, "static_data") and task.static_data is not None:
        return task.static_data
    return None
