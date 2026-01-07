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
    platform_integration: str = Field(
        default="standalone",
        description="Platform integration: 'standalone' or 'platform'"
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
        default="http://192.168.0.21:30000/v1",
        description="SGLang server URL (OpenAI-compatible API)"
    )
    prompt_version: str = Field(
        default="v12",
        description="Prompt version to use"
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

    # === OPTIONAL INTEGRATION ===
    server_url: Optional[str] = Field(
        default=None,
        description="RV-Platform server URL for integration mode"
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
    log_level: str = Field(
        default="INFO",
        description="Log level: DEBUG, INFO, WARNING, ERROR"
    )
    verbose_counters: bool = Field(
        default=False,
        description="Enable detailed counter tracking logs ([COUNTER] messages)"
    )

    # === COORDINATE CONFIGURATION ===
    coordinate_tolerance: int = Field(
        default=RVAgentConstants.COORDINATE_TOLERANCE,
        ge=10,
        le=100,
        description="Pixel tolerance for coordinate validation (50px validated)"
    )
    enable_coordinate_enhancement: bool = Field(
        default=True,
        description="Enable coordinate enhancement in prompts"
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

    # === LOOP DETECTION CONFIGURATION ===
    max_consecutive_type_text: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Max consecutive SET_TEXT actions before loop detection"
    )
    max_consecutive_click: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Max consecutive CLICK actions before loop detection"
    )
    max_consecutive_scroll: int = Field(
        default=5,
        ge=2,
        le=20,
        description="Max consecutive SCROLL actions before loop detection"
    )

    # === STATIC ANALYSIS ===
    static_analysis_path: Optional[str] = Field(
        default=None,
        description="Path to static analysis data (GATOR output) for MOP guidance"
    )

    def get_langchain_config(self) -> Dict[str, Any]:
        """
        Get LangChain-compatible configuration for SGLang.

        Returns:
            Dictionary with ChatOpenAI initialization parameters
        """
        return {
            "base_url": self.llm_base_url,
            "model": self.llm_model,
            "temperature": self.llm_temperature,
            "max_tokens": self.llm_max_tokens,
            "api_key": "not-needed",  # SGLang doesn't require API key
            "model_kwargs": {
                "top_p": self.llm_top_p,
            },
        }

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

    def get_verbose_counters(self) -> bool:
        """
        Get verbose_counters setting with environment variable override.

        Environment variable RVAGENT_VERBOSE_COUNTERS overrides config setting.

        Returns:
            True if verbose counter logging is enabled
        """
        import os
        env_val = os.getenv("RVAGENT_VERBOSE_COUNTERS", "")
        if env_val:
            return env_val.lower() in ("1", "true", "yes")
        return self.verbose_counters

    def get_loop_threshold(self, action_type: str) -> int:
        """
        Get loop detection threshold for action type.

        Args:
            action_type: Action type (SET_TEXT, CLICK, SCROLL, etc.)

        Returns:
            Maximum consecutive repetitions before loop detection
        """
        thresholds = {
            "SET_TEXT": self.max_consecutive_type_text,
            "CLICK": self.max_consecutive_click,
            "SCROLL": self.max_consecutive_scroll,
            "SWIPE": self.max_consecutive_scroll,
            "BACK": 2,
        }
        return thresholds.get(action_type, 3)

    def is_platform_mode(self) -> bool:
        """Check if running in platform integration mode."""
        return self.platform_integration == "platform" and self.server_url is not None

    def is_standalone_mode(self) -> bool:
        """Check if running in standalone mode."""
        return self.platform_integration == "standalone"

    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate configuration consistency.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if self.platform_integration == "platform" and not self.server_url:
            return False, "server_url is required for platform mode"

        if not self.enable_coordinate_enhancement:
            return False, "Coordinate enhancement is mandatory for RVAgent success"

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

