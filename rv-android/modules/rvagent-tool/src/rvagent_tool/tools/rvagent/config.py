"""
Configuration mapping for RVAgentTool.

Maps platform Task/ToolConfig to RVAgentConfig for rv-agent execution.
"""

from typing import Dict, Any, Optional
from rv_android_core.domain.task import Task
from rv_android_core.domain.app import App


def build_agent_config_dict(
    task: Task,
    app: App,
    tool_config: Dict[str, Any]
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

    # Map device_id from task configuration
    task_config = task.config if hasattr(task, 'config') else None
    if task_config:
        if hasattr(task_config, 'device_id') and task_config.device_id:
            config_dict["device_id"] = task_config.device_id
        if hasattr(task_config, 'timeout') and task_config.timeout:
            config_dict["timeout"] = task_config.timeout

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
        "llm_model", "llm_base_url", "llm_temperature",
        "llm_top_p", "llm_top_k", "llm_max_tokens", "llm_timeout",
        "prompt_version"
    ]
    for param in llm_params:
        if param in tool_config:
            config_dict[param] = tool_config[param]

    # Map exploration strategy parameters
    strategy_params = [
        "plateau_window", "max_input_variations",
        "stochastic_probability", "stochastic_temperature"
    ]
    for param in strategy_params:
        if param in tool_config:
            config_dict[param] = tool_config[param]

    # Map scorer weight parameters (for calibration)
    scorer_params = [
        # MopScorer
        "mop_direct_score", "mop_transitive_score",
        # WtgScorer
        "wtg_guided_score",
        # SaturationScorer
        "unsaturated_bonus",
        # VisitationPenaltyScorer
        "visitation_penalty_factor",
        # StrengthScorer
        "strength_weight",
        # GradualDecayScorer
        "gradual_decay_base", "gradual_decay_rate", "gradual_decay_min_visits",
        # ComponentPriorityScorer
        "component_high_priority", "component_medium_priority",
        # SuccessorTracker
        "max_re_enables", "ui_coverage_threshold",
        # Exploration
        "scroll_probability",
    ]
    for param in scorer_params:
        if param in tool_config:
            config_dict[param] = tool_config[param]

    # Map metrics output directory from task results_dir if available
    if hasattr(task, 'results_dir') and task.results_dir:
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
    if hasattr(task, 'static_data') and task.static_data is not None:
        return task.static_data
    return None
