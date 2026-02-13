# modules/rvdroid-tool/src/rvdroid_tool/config/tool_config.py

from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from rv_llm.config.llm_config import LLMConfig
from rv_llm.config.prompt_config import PromptConfig
from rv_android_core.util.error.exceptions import ConfigurationError

@dataclass
class RVDroidToolConfig:
    """
    Configuration class for the RVDroid tool.

    This class encapsulates all configurable parameters for the RVDroid tool,
    including LLM and prompt-specific settings, ensuring type safety and
    centralized management of tool configurations.
    """
    llm_config: LLMConfig = field(default_factory=LLMConfig)
    prompt_config: PromptConfig = field(default_factory=PromptConfig)
    # Add other RVDroid specific configurations here
    device_id: str = "emulator-5554"
    execution_timeout: int = 3600
    llm_enabled: bool = False
    preferred_strategy: Optional[str] = None
    output_dir: Optional[str] = None

    @classmethod
    def create_from_variant(cls, variant_config: Dict[str, Any], override_params: Optional[Dict[str, Any]] = None) -> 'RVDroidToolConfig':
        """
        Creates a RVDroidToolConfig instance from a variant dictionary,
        with optional overrides.

        Args:
            variant_config: A dictionary containing base configuration from a variant.
            override_params: Optional dictionary of parameters to override.

        Returns:
            An instance of RVDroidToolConfig.

        Raises:
            ConfigurationError: If required parameters are missing or invalid.
        """
        config_data = variant_config.copy()
        if override_params:
            config_data.update(override_params)

        try:
            llm_config = LLMConfig(
                llm_type=config_data.get("llm_type"),
                llm_model=config_data.get("llm_model"),
                temperature=config_data.get("temperature"),
                top_p=config_data.get("top_p"),
                max_tokens=config_data.get("max_tokens"),
                vision=config_data.get("vision", False)
            )
            prompt_config = PromptConfig(
                strategy_type=config_data.get("prompt_strategy")
            )

            return cls(
                llm_config=llm_config,
                prompt_config=prompt_config,
                device_id=config_data.get("device_id", "emulator-5554"),
                execution_timeout=config_data.get("execution_timeout", 3600),
                llm_enabled=config_data.get("llm_enabled", False),
                preferred_strategy=config_data.get("preferred_strategy"),
                output_dir=config_data.get("output_dir")
            )
        except Exception as e:
            raise ConfigurationError(f"Failed to create RVDroidToolConfig from variant: {e}")

    def validate(self) -> tuple[bool, str]:
        """
        Validates the current configuration.

        Returns:
            A tuple (is_valid, error_message).
        """
        if not self.llm_config.llm_type:
            return False, "LLM type is required in LLM configuration."
        if not self.llm_config.llm_model:
            return False, "LLM model is required in LLM configuration."
        if not self.prompt_config.strategy_type:
            return False, "Prompt strategy type is required in Prompt configuration."
        
        # Add more specific validation for RVDroid's own fields if necessary
        if self.execution_timeout <= 0:
            return False, "Execution timeout must be a positive integer."

        return True, ""
