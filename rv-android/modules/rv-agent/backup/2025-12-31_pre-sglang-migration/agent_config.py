"""
RVAgent Configuration.

Configuration for RVAgent with multi-mode support (pure_dfs, llm_only, hybrid).
"""
from typing import Optional, Dict, Any
from pydantic import Field
from rv_android_core.util.validation import BaseValidatedModel
from ..constants import RVAgentConstants


class RVAgentConfig(BaseValidatedModel):
    """
    Configuration for RVAgent exploration with multi-mode support.

    Supports three exploration modes:
    - pure_dfs: Depth-first search without LLM
    - llm_only: LLM-driven exploration without algorithmic constraints
    - hybrid: LLM with algorithmic validation and fallback

    Design Principles:
    - Direct LangChain integration
    - Pydantic validation with clear field definitions
    - Support for both local and cloud LLMs
    - Configurable fallback strategies
    """

    # === EXECUTION CONFIGURATION ===
    device_id: str = Field(
        default=RVAgentConstants.DEFAULT_DEVICE_ID,
        description="Android device or emulator ID for testing"
    )
    agent_mode: str = Field(
        default="multimode",
        description="Agent exploration mode: 'pure_dfs', 'llm_only', 'hybrid', 'multimode'"
    )
    llm_probability: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="LLM probability for multimode (0.7 = 70% LLM, 30% DFS)"
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
    package_name: Optional[str] = Field( # TODO nao pode ser opcional
        default=None,
        description="Target application package name"
    )

    # === LLM CONFIGURATION (PHASE 0 VALIDATED) ===
    llm_provider: str = Field(
        default="ollama",
        description="LLM provider: 'ollama', 'anthropic', 'openai', 'vllm'"
    )
    llm_model: str = Field(
        default=RVAgentConstants.DEFAULT_MODEL,
        description="LLM model identifier (Current: qwen3-vl:4b with 704x1248 resolution)"
    )
    llm_base_url: Optional[str] = Field(
        default=None,
        description="Optional custom base URL for LLM API (e.g., 'http://localhost:8000/v1' for vLLM)"
    )
    prompt_version: str = Field(
        default="v12",
        description="Prompt version to use (e.g., 'v10')"
    )
    llm_temperature: float = Field(
        default=RVAgentConstants.DEFAULT_TEMPERATURE,
        ge=0.0,
        le=1.0,
        description="LLM temperature parameter (VALIDATED: 0.25 optimal)"
    )
    llm_top_p: float = Field(
        default=RVAgentConstants.DEFAULT_TOP_P,
        ge=0.1,
        le=1.0,
        description="LLM top-p parameter (VALIDATED: 0.8 optimal)"
    )
    llm_top_k: int = Field(
        default=RVAgentConstants.DEFAULT_TOP_K,
        ge=1,
        le=100,
        description="LLM top-k parameter (VALIDATED: 50 optimal)"
    )
    llm_max_tokens: int = Field(
        default=512,  # Reduced from DEFAULT (likely 2048+) for focused responses
        ge=100,
        le=40000,
        description="Maximum tokens per LLM response"
    )

    # === OPTIONAL INTEGRATION ===
    server_url: Optional[str] = Field(
        default=None,
        description="RV-Platform server URL for integration mode"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API key for cloud LLM providers (Anthropic, OpenAI)"
    )

    # === TOOL CONFIGURATION ===
    debug_mode: bool = Field(
        default=False,
        description="Enable debug mode for detailed logging"
    )
    # TODO REMOVER!!!
    max_iterations: int = Field(
        default=RVAgentConstants.DEFAULT_MAX_ITERATIONS,
        ge=5,
        le=200,
        description="Maximum test iterations before stopping"
    )
    max_external_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum actions outside target app before restart"
    )

    # === COORDINATE ENHANCEMENT SETTINGS ===
    coordinate_tolerance: int = Field(
        default=RVAgentConstants.COORDINATE_TOLERANCE,
        ge=10,
        le=100,
        description="Pixel tolerance for coordinate validation (VALIDATED: 50px)"
    )
    enable_coordinate_enhancement: bool = Field(
        default=True,
        description="Enable coordinate enhancement (100% vs 30% success rate)"
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

    # === RVAGENT EXPLORATION CONFIGURATION ===
    strategy: str = Field(
        default="rvagent",
        description="Exploration strategy: 'rvagent' (default), 'dfs', 'bfs', 'greedy', 'simulated_annealing', 'genetic_algorithm'"
    )
    plateau_window: int = Field(
        default=10,
        ge=5,
        le=50,
        description="Plateau detection window size for RVAgent strategy (iterations without progress)"
    )
    max_input_variations: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum test value variations per input field for RVAgent strategy"
    )

    # === MULTI-MODE CONFIGURATION ===
    llm_timeout: float = Field(
        default=15.0,  # Reduced from 30s to trigger fallback faster
        ge=5.0,
        le=120.0,
        description="Timeout for single LLM call in seconds"
    )
    llm_max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Max consecutive LLM failures before DFS fallback"
    )
    auto_fallback_on_timeout: bool = Field(
        default=True,
        description="Automatically fallback to DFS on LLM timeout"
    )
    auto_fallback_on_error: bool = Field(
        default=True,
        description="Automatically fallback to DFS on LLM error"
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
    # TODO rever: deve pegar os 3 arquivos de analise estatica
    static_analysis_path: Optional[str] = Field(
        default=None,
        description="Path to static analysis data (GATOR output) for MOP guidance"
    )

    def get_langchain_config(self) -> Dict[str, Any]:
        """
        Get LangChain-compatible configuration parameters.

        Returns Phase 0 validated parameters for optimal performance.

        Returns:
            Dictionary with LangChain initialization parameters
        """
        config = {
            "model": self.llm_model,
            "temperature": self.llm_temperature,
            "top_p": self.llm_top_p,
            "top_k": self.llm_top_k,
            "max_tokens": self.llm_max_tokens,
        }

        # Use custom base_url if provided, otherwise use provider defaults
        if self.llm_base_url:
            config["base_url"] = self.llm_base_url
        elif self.llm_provider == "ollama":
            config["base_url"] = "http://localhost:11434"

        if self.api_key:
            config["api_key"] = self.api_key

        return config

    def get_validated_params_summary(self) -> Dict[str, Any]:
        """
        Get summary of Phase 0 validated parameters.

        Returns:
            Dictionary with validation source and results
        """
        return {
            "validation_source": "Phase 0 - Overnight execution (9,855 tests)",
            "optimal_config": "T0.25_P0.8_K50",
            "success_rate": "81.6% (validated)",
            "coordinate_enhancement": "100% vs 30% success rate",
            "model_performance": {
                "qwen3-vl:4b": "Current model (704x1248 resolution, multiples of 32)",
                "claude-3-5-haiku": "100% success rate (premium)"
            },
            "breakthrough_testing": {
                "claude_sonnet": "100% success, 5.1s response",
                "claude_haiku": "100% success, 1.5s response, 80% cheaper"
            }
        }

    def get_agent_mode(self) -> str:
        """
        Get agent exploration mode.

        Environment variable RVAGENT_MODE overrides config setting.

        Returns:
            Agent mode: 'pure_dfs', 'llm_only', or 'hybrid'
        """
        import os
        env_mode = os.getenv("RVAGENT_MODE")
        if env_mode and env_mode in ["pure_dfs", "llm_only", "hybrid"]:
            return env_mode
        return self.agent_mode

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

        if self.llm_provider in ["anthropic", "openai"] and not self.api_key:
            return False, f"api_key is required for {self.llm_provider} provider"

        if not self.enable_coordinate_enhancement:
            return False, "Coordinate enhancement is mandatory for RVAgent success"

        valid_modes = ["pure_dfs", "llm_only", "hybrid"]
        if self.agent_mode not in valid_modes:
            return False, f"agent_mode must be one of {valid_modes}"

        mode = self.get_agent_mode()
        if mode in ["llm_only", "hybrid"] and not self.llm_model:
            return False, f"{mode} mode requires llm_model configuration"

        return True, None

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary format."""
        return self.model_dump(exclude_unset=False)

    @classmethod
    def create_optimal_config(cls, package_name: str, device_id: str = None) -> "RVAgentConfig":
        """
        Create configuration with Phase 0 optimal parameters.

        Args:
            package_name: Target application package name
            device_id: Android device ID (optional)

        Returns:
            RVAgentConfig with optimal validated parameters
        """
        config_data = {
            "package_name": package_name,
            "llm_model": RVAgentConstants.DEFAULT_MODEL,
            "llm_temperature": RVAgentConstants.DEFAULT_TEMPERATURE,
            "llm_top_p": RVAgentConstants.DEFAULT_TOP_P,
            "llm_top_k": RVAgentConstants.DEFAULT_TOP_K,
            "enable_coordinate_enhancement": True,
            "coordinate_tolerance": RVAgentConstants.COORDINATE_TOLERANCE,
        }

        if device_id:
            config_data["device_id"] = device_id

        return cls(**config_data)

    @classmethod
    def create_premium_config(cls, package_name: str, api_key: str, device_id: str = None) -> "RVAgentConfig":
        """
        Create configuration with premium Claude Haiku for maximum performance.

        Args:
            package_name: Target application package name
            api_key: Anthropic API key
            device_id: Android device ID (optional)

        Returns:
            RVAgentConfig with premium Claude settings
        """
        config_data = {
            "package_name": package_name,
            "llm_provider": "anthropic",
            "llm_model": RVAgentConstants.PREMIUM_MODEL,
            "llm_temperature": 0.05,  # Lower temperature for premium accuracy
            "llm_max_tokens": 200,    # Concise responses for speed
            "api_key": api_key,
            "enable_coordinate_enhancement": True,
            "coordinate_tolerance": RVAgentConstants.COORDINATE_TOLERANCE,
        }

        if device_id:
            config_data["device_id"] = device_id

        return cls(**config_data)