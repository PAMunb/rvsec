"""
Configure RVAgent exploration with SGLang backend and Qwen3-VL model.

Provide the central Pydantic configuration model for all RVAgent components,
including LLM inference parameters, exploration strategy weights, scorer
calibration, error detection thresholds, and device settings. All default
values originate from the rvsec-vision-llm validation benchmark.
"""

from typing import Any, Dict, Optional

from pydantic import Field
from rv_android_core.util.validation import BaseValidatedModel

from ..constants import RVAgentConstants


class RVAgentConfig(BaseValidatedModel):
    """Configure RVAgent exploration with SGLang backend.

    Centralize all tunable parameters for the RVAgent system into a single
    Pydantic model. Each field includes validation constraints (ge/le) and
    a description. Default values are calibrated from the rvsec-vision-llm
    benchmark (Qwen3-VL-4B-Instruct on SGLang).

    Supports three exploration modes:
    - pure_algorithm: Algorithmic exploration without LLM.
    - llm_only: LLM-driven exploration.
    - multimode: Hybrid LLM with algorithmic fallback (default 70/30 split).

    ### Role in the System:

    - Created by AgentFactory or CLI and injected into all agent components.
    - Consumed by RVAgent, LLMClient, RVAgentStrategy, ActionRanker, scorers,
      RoutingManager, MemoryCoordinator, and DeviceInterface.
    - Supports environment variable overrides for mode and log level.

    ### Key Features:

    - Pydantic validation with range constraints on all numeric parameters.
    - Section-organized fields: execution, LLM, output, tool, logging,
      coordinates, device, memory, strategy, fallback, static analysis,
      scorer weights, successor tracker, error detection, and exploration.
    - Convenience methods for LangChain integration and mode resolution.
    """

    # === EXECUTION CONFIGURATION ===
    device_id: str = Field(
        default=RVAgentConstants.DEFAULT_DEVICE_ID,
        description="Android device or emulator ID for testing",
    )
    agent_mode: str = Field(
        default="multimode",
        description="Agent exploration mode: 'pure_algorithm', 'llm_only', 'multimode'",
    )
    llm_probability: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="LLM probability for multimode (0.7 = 70% LLM, 30% algorithm)",
    )
    timeout: int = Field(
        default=RVAgentConstants.DEFAULT_TIMEOUT,
        ge=60,
        description="Test execution timeout in seconds",
    )
    repetition: int = Field(
        default=1,
        ge=1,
        description="Task repetition number (from platform, used in output filenames)",
    )
    results_dir: str = Field(
        default="./results", description="Directory for test results and artifacts"
    )
    package_name: str = Field(description="Target application package name (required)")

    # === SGLang LLM CONFIGURATION ===
    # Validated parameters from rvsec-vision-llm benchmark
    llm_model: str = Field(
        default="Qwen/Qwen3-VL-4B-Instruct", description="LLM model identifier"
    )
    llm_base_url: str = Field(
        default="http://192.168.0.36:30000/v1",
        description="SGLang server URL (OpenAI-compatible API)",
    )
    prompt_version: str = Field(
        default="v13",
        description="Prompt version (v13: dialog handling, v14: structured reasoning, v17: MOP navigation)",
    )

    # Inference parameters (validated from benchmark)
    llm_temperature: float = Field(
        default=0.01,
        ge=0.0,
        le=2.0,
        description="LLM temperature (0.01 optimal for tool calling)",
    )
    llm_top_p: float = Field(
        default=0.6, ge=0.0, le=1.0, description="LLM top-p parameter (0.6 optimal)"
    )
    llm_top_k: int = Field(default=50, ge=1, le=100, description="LLM top-k parameter")
    llm_max_tokens: int = Field(
        default=2048, ge=100, le=40000, description="Maximum tokens per LLM response"
    )
    llm_timeout: float = Field(
        default=30.0,
        ge=5.0,
        le=120.0,
        description="Timeout for single LLM call in seconds",
    )

    # === OUTPUT CONFIGURATION ===
    metrics_output_dir: Optional[str] = Field(
        default=None,
        description="Directory for saving agent metrics JSON. If None, metrics are not saved to file.",
    )

    # === TOOL CONFIGURATION ===
    debug_mode: bool = Field(
        default=False, description="Enable debug mode for detailed logging"
    )
    max_external_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum actions outside target app before restart",
    )

    # === LOGGING CONFIGURATION ===
    # debug_mode is a CLI shortcut (--debug flag); log_level is granular config (env: RVAGENT_LOG_LEVEL)
    log_level: str = Field(
        default="INFO", description="Log level: DEBUG, INFO, WARNING, ERROR"
    )

    # === COORDINATE CONFIGURATION ===
    coordinate_tolerance: int = Field(
        default=RVAgentConstants.COORDINATE_TOLERANCE,
        ge=10,
        le=100,
        description="Pixel tolerance for coordinate validation (50px validated)",
    )
    # === DEVICE AND SCREENSHOT CONFIGURATION ===
    device_dimensions: tuple[int, int] = Field(
        default=(1080, 1920), description="Device screen dimensions (width, height)"
    )
    optimized_dimensions: tuple[int, int] = Field(
        default=(704, 1248),
        description="Optimized screenshot dimensions for LLM (multiple of 32 for Qwen3-VL)",
    )
    screenshot_dir: str = Field(
        default="/tmp/rvagent_screenshots",
        description="Directory for storing captured screenshots",
    )
    screenshot_rotation_limit: int = Field(
        default=50,
        ge=10,
        le=200,
        description="Maximum number of screenshots to keep (rotation limit)",
    )

    # === MEMORY CONFIGURATION ===
    max_short_term_iterations: int = Field(
        default=RVAgentConstants.MAX_SHORT_TERM_ITERATIONS,
        ge=3,
        le=20,
        description="Maximum iterations in short-term memory",
    )
    max_long_term_states: int = Field(
        default=RVAgentConstants.MAX_LONG_TERM_STATES,
        ge=100,
        le=5000,
        description="Maximum states in long-term memory",
    )

    # === EXPLORATION STRATEGY CONFIGURATION ===
    strategy: str = Field(
        default="rvagent",
        description="Exploration strategy: 'rvagent', 'dfs', 'bfs', 'greedy'",
    )
    seed: Optional[int] = Field(
        default=None,
        description="Random seed for reproducible exploration. If None, non-deterministic.",
    )
    plateau_window: int = Field(
        default=10, ge=5, le=50, description="Plateau detection window size"
    )
    max_input_variations: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum test value variations per input field",
    )
    stochastic_probability: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Probability of using Gumbel-max stochastic action selection (0=deterministic, 1=always stochastic)",
    )
    stochastic_temperature: float = Field(
        default=1.0,
        ge=0.1,
        le=5.0,
        description="Temperature for Gumbel-max selection (higher = more random)",
    )

    # === FALLBACK CONFIGURATION ===
    llm_max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Max consecutive LLM failures before algorithm fallback",
    )
    auto_fallback_on_timeout: bool = Field(
        default=True, description="Automatically fallback to algorithm on LLM timeout"
    )
    auto_fallback_on_error: bool = Field(
        default=True, description="Automatically fallback to algorithm on LLM error"
    )

    # === STATIC ANALYSIS ===
    static_analysis_path: Optional[str] = Field(
        default=None,
        description="Path to static analysis data (GATOR output) for MOP guidance",
    )

    # === SCORER WEIGHTS (Calibration Parameters) ===
    # MopScorer - prioritizes actions reaching monitored operations
    mop_direct_score: float = Field(
        default=500.0,
        ge=0.0,
        le=1000.0,
        description="Score for actions directly reaching MOP methods",
    )
    mop_transitive_score: float = Field(
        default=300.0,
        ge=0.0,
        le=600.0,
        description="Score for actions transitively reaching MOP methods",
    )

    # WtgScorer - prioritizes WTG-guided navigation
    wtg_guided_score: float = Field(
        default=150.0,
        ge=0.0,
        le=500.0,
        description="Score for WTG-guided actions leading to unvisited screens",
    )

    # SaturationScorer - bonus for unsaturated states
    unsaturated_bonus: float = Field(
        default=100.0,
        ge=0.0,
        le=250.0,
        description="Bonus score for actions in unsaturated states",
    )

    # VisitationPenaltyScorer - penalizes over-visited states
    visitation_penalty_factor: float = Field(
        default=-15.0,
        le=0.0,
        ge=-50.0,
        description="Penalty factor for over-visited states (negative value)",
    )

    # StrengthScorer - historical success rate
    strength_weight: float = Field(
        default=50.0,
        ge=0.0,
        le=200.0,
        description="Weight for action strength (success rate) scoring",
    )

    # GradualDecayScorer - exponential decay by visits
    gradual_decay_base: float = Field(
        default=200.0,
        ge=50.0,
        le=500.0,
        description="Base score for GradualDecayScorer",
    )
    gradual_decay_rate: float = Field(
        default=0.7,
        ge=0.3,
        le=0.95,
        description="Decay rate per visit (0.7 = 70% retention)",
    )
    gradual_decay_min_visits: int = Field(
        default=5, ge=2, le=15, description="Visits after which score becomes zero"
    )

    # ComponentPriorityScorer - widget type priorities
    component_high_priority: float = Field(
        default=50.0,
        ge=20.0,
        le=100.0,
        description="Score for high-priority components (buttons, inputs)",
    )
    component_medium_priority: float = Field(
        default=40.0,
        ge=10.0,
        le=80.0,
        description="Score for medium-priority components (toggles, sliders)",
    )

    # === SUCCESSOR TRACKER PARAMETERS ===
    max_re_enables: int = Field(
        default=6,
        ge=1,
        le=20,
        description="Maximum times an action can be re-enabled for successor exploration",
    )
    ui_coverage_threshold: float = Field(
        default=0.9,
        ge=0.5,
        le=1.0,
        description="UI coverage threshold (executed_actions/total_actions per screen) for successor re-enablement",
    )

    # === ERROR DETECTION CONFIGURATION ===
    error_detection_enabled: bool = Field(
        default=True,
        description="Master switch for validation error detection on screen",
    )
    error_detection_confidence: float = Field(
        default=0.7,
        ge=0.3,
        le=0.95,
        description="Confidence threshold for error indicator detection [0.3, 0.95]",
    )
    error_max_indicator_size: int = Field(
        default=80,
        ge=30,
        le=200,
        description="Maximum pixel size for a valid error indicator [30, 200]",
    )
    error_max_indicator_count: int = Field(
        default=5,
        ge=2,
        le=20,
        description="Maximum indicators before assuming themed UI (not errors) [2, 20]",
    )

    # === SPATIAL ASSOCIATION (error-to-input mapping) ===
    spatial_edittext_boost: float = Field(
        default=1.2,
        ge=1.0,
        le=2.0,
        description="EditText priority tiebreaker for spatial error-to-input association [1.0, 2.0]",
    )
    spatial_spinner_boost: float = Field(
        default=1.1,
        ge=1.0,
        le=2.0,
        description="Spinner priority tiebreaker for spatial error-to-input association [1.0, 2.0]",
    )
    spatial_min_match_threshold: float = Field(
        default=0.1,
        ge=0.01,
        le=0.5,
        description="Minimum score to accept spatial match between error and input [0.01, 0.5]",
    )

    # === ADVANCED EXPLORATION STRATEGY PARAMETERS ===
    backtrack_saturation_threshold: float = Field(
        default=0.8,
        ge=0.5,
        le=1.0,
        description="Saturation threshold triggering backtrack (0.8 = backtrack when 80% of actions saturated)",
    )
    multi_value_saturation_threshold: int = Field(
        default=4,
        ge=2,
        le=12,
        description=(
            "Execution count threshold for multi-value widgets"
            " (EditText, Spinner, SeekBar) before saturation."
            " Default widgets use threshold=2."
        ),
    )
    mop_nav_weight: float = Field(
        default=2.0,
        ge=0.5,
        le=5.0,
        description="Weight multiplier for MOP-reaching targets in navigation scoring",
    )
    mop_max_input_variations: int = Field(
        default=11,
        ge=5,
        le=15,
        description="Maximum input value variations for MOP-reaching screens",
    )
    reward_gamma: float = Field(
        default=0.8,
        ge=0.5,
        le=0.99,
        description="Discount factor for N-step reward propagation (0.8 = 20% decay per step)",
    )
    reward_score_weight: float = Field(
        default=1.0,
        ge=0.1,
        le=5.0,
        description="Weight for cumulative_reward influence in StrengthScorer",
    )
    coverage_density_weight: float = Field(
        default=200.0,
        ge=50.0,
        le=600.0,
        description="CoverageDensityScorer weight for prioritizing screens with untested elements",
    )

    # === EXPLORATION PARAMETERS ===
    scroll_probability: float = Field(
        default=0.15,
        ge=0.0,
        le=0.5,
        description="Probability of scroll action for dynamic content discovery",
    )

    def get_langchain_config(self) -> Dict[str, Any]:
        """Build LangChain-compatible configuration for SGLang.

        Returns:
            Dictionary with ChatOpenAI initialization parameters:
            - "base_url" (str): SGLang server URL.
            - "model" (str): Model identifier.
            - "temperature" (float): Sampling temperature.
            - "max_tokens" (int): Maximum response tokens.
            - "top_p" (float): Nucleus sampling parameter.
            - "api_key" (str): Placeholder ("not-needed" for SGLang).
            - "extra_body" (dict, optional): Contains "top_k" when > 0.
        """
        config = {
            "base_url": self.llm_base_url,
            "model": self.llm_model,
            "temperature": self.llm_temperature,
            "max_tokens": self.llm_max_tokens,
            "top_p": self.llm_top_p,
            "api_key": "not-needed",  # SGLang doesn't require API key
        }
        # top_k is passed via extra_body because the OpenAI API schema does
        # not include it, but SGLang accepts it as an extended parameter.
        if self.llm_top_k > 0:
            config["extra_body"] = {"top_k": self.llm_top_k}
        return config

    def get_agent_mode(self) -> str:
        """Resolve agent exploration mode with environment override.

        Check RVAGENT_MODE environment variable first; fall back to the
        configured agent_mode if the variable is unset or invalid.

        Returns:
            Agent mode: 'pure_algorithm', 'llm_only', or 'multimode'.
        """
        import os

        env_mode = os.getenv("RVAGENT_MODE")
        valid_modes = ["pure_algorithm", "llm_only", "multimode"]
        if env_mode and env_mode in valid_modes:
            return env_mode
        return self.agent_mode

    def get_log_level(self) -> int:
        """Resolve logging level with environment override.

        Check RVAGENT_LOG_LEVEL environment variable first; fall back to the
        configured log_level if the variable is unset. Invalid level strings
        default to logging.INFO.

        Returns:
            Logging level as integer (e.g., logging.INFO = 20).
        """
        import logging
        import os

        level_str = os.getenv("RVAGENT_LOG_LEVEL", self.log_level).upper()
        return getattr(logging, level_str, logging.INFO)

    def validate(self) -> tuple[bool, Optional[str]]:
        """Validate configuration consistency beyond field-level constraints.

        Perform cross-field validation that Pydantic validators cannot express
        declaratively (e.g., mode membership).

        Returns:
            Tuple of (is_valid, error_message). error_message is None when valid.
        """
        valid_modes = ["pure_algorithm", "llm_only", "multimode"]
        if self.agent_mode not in valid_modes:
            return False, f"agent_mode must be one of {valid_modes}"

        return True, None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize all configuration fields to a dictionary."""
        return self.model_dump(exclude_unset=False)

    @classmethod
    def create_default(
        cls, package_name: str, device_id: str = None
    ) -> "RVAgentConfig":
        """Create configuration with default SGLang parameters.

        Convenience factory for the common case where only the target package
        (and optionally device ID) differ from defaults.

        Args:
            package_name: Target application package name.
            device_id: Android device ID. Defaults to emulator-5554 when omitted.

        Returns:
            RVAgentConfig instance with all other fields at their defaults.
        """
        config_data = {
            "package_name": package_name,
        }

        if device_id:
            config_data["device_id"] = device_id

        return cls(**config_data)
