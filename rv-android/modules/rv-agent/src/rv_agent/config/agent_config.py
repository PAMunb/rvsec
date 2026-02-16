"""
RVAgent Configuration.

Configuration for RVAgent with SGLang backend and Qwen3-VL model.
Based on validation from rvsec-vision-llm benchmark (2,847 tests).
"""

from typing import Optional, Dict, Any
from pydantic import Field
from rv_android_core.util.validation import BaseValidatedModel
from ..constants import RVAgentConstants


class RVAgentConfig(BaseValidatedModel):
    """
    Configuration for RVAgent exploration with SGLang backend.

    Supports three exploration modes:
    - pure_algorithm: Algorithmic exploration without LLM
    - llm_only: LLM-driven exploration
    - multimode: Hybrid LLM with algorithmic fallback (70% LLM / 30% algorithm)

    Based on validation from rvsec-vision-llm benchmark:
    - Model: Qwen3-VL-4B-Instruct
    - Server: SGLang (recommended over vLLM for tool calling)
    - Hit rate: 57.7% with visual grounding
    - Tool call rate: 90.3%
    """

    # === EXECUTION CONFIGURATION ===
    device_id: str = Field(
        default=RVAgentConstants.DEFAULT_DEVICE_ID,
        description="Android device or emulator ID for testing"
    )
    agent_mode: str = Field(
        default="multimode",
        description="Agent exploration mode: 'pure_algorithm', 'llm_only', 'multimode'"
    )
    llm_probability: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="LLM probability for multimode (0.7 = 70% LLM, 30% algorithm)"
    )
    timeout: int = Field(
        default=RVAgentConstants.DEFAULT_TIMEOUT,
        ge=60,
        description="Test execution timeout in seconds"
    )
    results_dir: str = Field(
        default="./results",
        description="Directory for test results and artifacts"
    )
    package_name: str = Field(
        description="Target application package name (required)"
    )

    # === SGLang LLM CONFIGURATION ===
    # Validated parameters from rvsec-vision-llm benchmark
    llm_model: str = Field(
        default="Qwen/Qwen3-VL-4B-Instruct",
        description="LLM model identifier"
    )
    llm_base_url: str = Field(
        default="http://192.168.0.36:30000/v1",
        description="SGLang server URL (OpenAI-compatible API)"
    )
    prompt_version: str = Field( 
        default="v13",
        description="Prompt version (v13: dialog handling, v14: structured reasoning)"
    )

    # Inference parameters (validated from benchmark)
    llm_temperature: float = Field(
        default=0.01,
        ge=0.0,
        le=2.0,
        description="LLM temperature (0.01 optimal for tool calling)"
    )
    llm_top_p: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="LLM top-p parameter (0.6 optimal)"
    )
    llm_top_k: int = Field(
        default=50,
        ge=1,
        le=100,
        description="LLM top-k parameter"
    )
    llm_max_tokens: int = Field(
        default=2048,
        ge=100,
        le=40000,
        description="Maximum tokens per LLM response"
    )
    llm_timeout: float = Field(
        default=30.0,
        ge=5.0,
        le=120.0,
        description="Timeout for single LLM call in seconds"
    )

    # === OUTPUT CONFIGURATION ===
    metrics_output_dir: Optional[str] = Field(
        default=None,
        description="Directory for saving agent metrics JSON. If None, metrics are not saved to file."
    )

    # === TOOL CONFIGURATION ===
    debug_mode: bool = Field(
        default=False,
        description="Enable debug mode for detailed logging"
    )
    max_external_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum actions outside target app before restart"
    )

    # === LOGGING CONFIGURATION ===
    # debug_mode is a CLI shortcut (--debug flag); log_level is granular config (env: RVAGENT_LOG_LEVEL)
    log_level: str = Field(
        default="INFO",
        description="Log level: DEBUG, INFO, WARNING, ERROR"
    )

    # === COORDINATE CONFIGURATION ===
    coordinate_tolerance: int = Field(
        default=RVAgentConstants.COORDINATE_TOLERANCE,
        ge=10,
        le=100,
        description="Pixel tolerance for coordinate validation (50px validated)"
    )
    # === DEVICE AND SCREENSHOT CONFIGURATION ===
    device_dimensions: tuple[int, int] = Field(
        default=(1080, 1920),
        description="Device screen dimensions (width, height)"
    )
    optimized_dimensions: tuple[int, int] = Field(
        default=(704, 1248),
        description="Optimized screenshot dimensions for LLM (multiple of 32 for Qwen3-VL)"
    )
    screenshot_dir: str = Field(
        default="/tmp/rvagent_screenshots",
        description="Directory for storing captured screenshots"
    )
    screenshot_rotation_limit: int = Field(
        default=50,
        ge=10,
        le=200,
        description="Maximum number of screenshots to keep (rotation limit)"
    )

    # === MEMORY CONFIGURATION ===
    max_short_term_iterations: int = Field(
        default=RVAgentConstants.MAX_SHORT_TERM_ITERATIONS,
        ge=3,
        le=20,
        description="Maximum iterations in short-term memory"
    )
    max_long_term_states: int = Field(
        default=RVAgentConstants.MAX_LONG_TERM_STATES,
        ge=100,
        le=5000,
        description="Maximum states in long-term memory"
    )

    # === EXPLORATION STRATEGY CONFIGURATION ===
    strategy: str = Field(
        default="rvagent",
        description="Exploration strategy: 'rvagent', 'dfs', 'bfs', 'greedy'"
    )
    seed: Optional[int] = Field(
        default=None,
        description="Random seed for reproducible exploration. If None, non-deterministic."
    )
    plateau_window: int = Field(
        default=10,
        ge=5,
        le=50,
        description="Plateau detection window size"
    )
    max_input_variations: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum test value variations per input field"
    )
    stochastic_probability: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Probability of using Gumbel-max stochastic action selection (0=deterministic, 1=always stochastic)"
    )
    stochastic_temperature: float = Field(
        default=1.0,
        ge=0.1,
        le=5.0,
        description="Temperature for Gumbel-max selection (higher = more random)"
    )

    # === FALLBACK CONFIGURATION ===
    llm_max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Max consecutive LLM failures before algorithm fallback"
    )
    auto_fallback_on_timeout: bool = Field(
        default=True,
        description="Automatically fallback to algorithm on LLM timeout"
    )
    auto_fallback_on_error: bool = Field(
        default=True,
        description="Automatically fallback to algorithm on LLM error"
    )

    # === STATIC ANALYSIS ===
    static_analysis_path: Optional[str] = Field(
        default=None,
        description="Path to static analysis data (GATOR output) for MOP guidance"
    )

    # === SCORER WEIGHTS (Calibration Parameters) ===
    # MopScorer - prioritizes actions reaching monitored operations
    mop_direct_score: float = Field(
        default=300.0,
        ge=0.0,
        le=1000.0,
        description="Score for actions directly reaching MOP methods"
    )
    mop_transitive_score: float = Field(
        default=150.0,
        ge=0.0,
        le=500.0,
        description="Score for actions transitively reaching MOP methods"
    )

    # WtgScorer - prioritizes WTG-guided navigation
    wtg_guided_score: float = Field(
        default=250.0,
        ge=0.0,
        le=500.0,
        description="Score for WTG-guided actions leading to unvisited screens"
    )

    # SaturationScorer - bonus for unsaturated states
    unsaturated_bonus: float = Field(
        default=80.0,
        ge=0.0,
        le=200.0,
        description="Bonus score for actions in unsaturated states"
    )

    # VisitationPenaltyScorer - penalizes over-visited states
    visitation_penalty_factor: float = Field(
        default=-10.0,
        le=0.0,
        ge=-50.0,
        description="Penalty factor for over-visited states (negative value)"
    )

    # StrengthScorer - historical success rate
    strength_weight: float = Field(
        default=50.0,
        ge=0.0,
        le=200.0,
        description="Weight for action strength (success rate) scoring"
    )

    # GradualDecayScorer - exponential decay by visits
    gradual_decay_base: float = Field(
        default=200.0,
        ge=50.0,
        le=500.0,
        description="Base score for GradualDecayScorer"
    )
    gradual_decay_rate: float = Field(
        default=0.7,
        ge=0.3,
        le=0.95,
        description="Decay rate per visit (0.7 = 70% retention)"
    )
    gradual_decay_min_visits: int = Field(
        default=5,
        ge=2,
        le=15,
        description="Visits after which score becomes zero"
    )

    # ComponentPriorityScorer - widget type priorities
    component_high_priority: float = Field(
        default=50.0,
        ge=20.0,
        le=100.0,
        description="Score for high-priority components (buttons, inputs)"
    )
    component_medium_priority: float = Field(
        default=40.0,
        ge=10.0,
        le=80.0,
        description="Score for medium-priority components (toggles, sliders)"
    )

    # === SUCCESSOR TRACKER PARAMETERS ===
    max_re_enables: int = Field(
        default=6,
        ge=1,
        le=20,
        description="Maximum times an action can be re-enabled for successor exploration"
    )
    ui_coverage_threshold: float = Field(
        default=0.9,
        ge=0.5,
        le=1.0,
        description="UI coverage threshold (executed_actions/total_actions per screen) for successor re-enablement"
    )

    # === EXPLORATION PARAMETERS ===
    scroll_probability: float = Field(
        default=0.15,
        ge=0.0,
        le=0.5,
        description="Probability of scroll action for dynamic content discovery"
    )

    def get_langchain_config(self) -> Dict[str, Any]:
        """
        Get LangChain-compatible configuration for SGLang.

        Returns:
            Dictionary with ChatOpenAI initialization parameters
        """
        config = {
            "base_url": self.llm_base_url,
            "model": self.llm_model,
            "temperature": self.llm_temperature,
            "max_tokens": self.llm_max_tokens,
            "top_p": self.llm_top_p,
            "api_key": "not-needed",  # SGLang doesn't require API key
        }
        # top_k via extra_body (SGLang supports, OpenAI doesn't)
        if self.llm_top_k > 0:
            config["extra_body"] = {"top_k": self.llm_top_k}
        return config

    def get_agent_mode(self) -> str:
        """
        Get agent exploration mode.

        Environment variable RVAGENT_MODE overrides config setting.

        Returns:
            Agent mode: 'pure_algorithm', 'llm_only', or 'multimode'
        """
        import os
        env_mode = os.getenv("RVAGENT_MODE")
        valid_modes = ["pure_algorithm", "llm_only", "multimode"]
        if env_mode and env_mode in valid_modes:
            return env_mode
        return self.agent_mode

    def get_log_level(self) -> int:
        """
        Get logging level with environment variable override.

        Environment variable RVAGENT_LOG_LEVEL overrides config setting.

        Returns:
            Logging level as integer (e.g., logging.INFO)
        """
        import os
        import logging
        level_str = os.getenv("RVAGENT_LOG_LEVEL", self.log_level).upper()
        return getattr(logging, level_str, logging.INFO)

    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate configuration consistency.

        Returns:
            Tuple of (is_valid, error_message)
        """
        valid_modes = ["pure_algorithm", "llm_only", "multimode"]
        if self.agent_mode not in valid_modes:
            return False, f"agent_mode must be one of {valid_modes}"

        return True, None

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary format."""
        return self.model_dump(exclude_unset=False)

    @classmethod
    def create_default(cls, package_name: str, device_id: str = None) -> "RVAgentConfig":
        """
        Create configuration with default SGLang parameters.

        Args:
            package_name: Target application package name
            device_id: Android device ID (optional)

        Returns:
            RVAgentConfig with default parameters
        """
        config_data = {
            "package_name": package_name,
        }

        if device_id:
            config_data["device_id"] = device_id

        return cls(**config_data)

