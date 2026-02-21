"""
RVAgentConfig tests for SGLang configuration.

Validates configuration loading and SGLang-specific settings.
"""

import pytest

pytestmark = pytest.mark.smoke


class TestConfigSGLang:
    """Test RVAgentConfig for SGLang."""

    def test_import_config(self):
        """RVAgentConfig imports without error."""
        from rv_agent.config.agent_config import RVAgentConfig

        assert RVAgentConfig is not None

    def test_create_default_config(self):
        """Default config creates with package name."""
        from rv_agent.config.agent_config import RVAgentConfig

        config = RVAgentConfig.create_default(
            package_name="com.example.app", device_id="emulator-5554"
        )

        assert config.package_name == "com.example.app"
        assert config.device_id == "emulator-5554"

    def test_sglang_defaults(self):
        """Config has correct SGLang defaults."""
        from rv_agent.config.agent_config import RVAgentConfig

        config = RVAgentConfig.create_default(package_name="test")

        # SGLang server URL
        assert "192.168.0.36:30000" in config.llm_base_url
        assert "/v1" in config.llm_base_url

        # Qwen model
        assert "Qwen" in config.llm_model or "qwen" in config.llm_model.lower()

    def test_inference_parameters(self):
        """Config has validated inference parameters."""
        from rv_agent.config.agent_config import RVAgentConfig

        config = RVAgentConfig.create_default(package_name="test")

        # Temperature should be low for tool calling
        assert config.llm_temperature <= 0.1

        # Top-p should be moderate
        assert 0.5 <= config.llm_top_p <= 0.8

        # Max tokens should be reasonable
        assert config.llm_max_tokens >= 1000

    def test_langchain_config(self):
        """get_langchain_config returns correct structure."""
        from rv_agent.config.agent_config import RVAgentConfig

        config = RVAgentConfig.create_default(package_name="test")
        lc_config = config.get_langchain_config()

        assert "base_url" in lc_config
        assert "model" in lc_config
        assert "temperature" in lc_config
        assert "max_tokens" in lc_config
        assert "api_key" in lc_config

        # API key should be placeholder for SGLang
        assert lc_config["api_key"] == "not-needed"

    def test_agent_modes(self):
        """All agent modes are recognized."""
        from rv_agent.config.agent_config import RVAgentConfig

        for mode in ["pure_algorithm", "llm_only", "multimode"]:
            config = RVAgentConfig(package_name="test", agent_mode=mode)
            assert config.agent_mode == mode

    def test_multimode_probability(self):
        """Multimode LLM probability is configurable."""
        from rv_agent.config.agent_config import RVAgentConfig

        config = RVAgentConfig(
            package_name="test", agent_mode="multimode", llm_probability=0.7
        )

        assert config.llm_probability == 0.7

    def test_default_multimode_probability(self):
        """Default multimode probability is 0.7 (70%)."""
        from rv_agent.config.agent_config import RVAgentConfig

        config = RVAgentConfig.create_default(package_name="test")

        assert config.llm_probability == 0.7

    def test_coordinate_config(self):
        """Coordinate configuration is present."""
        from rv_agent.config.agent_config import RVAgentConfig

        config = RVAgentConfig.create_default(package_name="test")

        # Device dimensions
        assert config.device_dimensions == (1080, 1920)

        # Optimized dimensions for Qwen3-VL
        assert config.optimized_dimensions == (704, 1248)

    def test_config_validation(self):
        """Config validates correctly."""
        from rv_agent.config.agent_config import RVAgentConfig

        config = RVAgentConfig.create_default(package_name="test")
        is_valid, error = config.validate()

        assert is_valid, f"Config validation failed: {error}"

    def test_invalid_mode_rejected(self):
        """Invalid agent mode fails validation."""
        from rv_agent.config.agent_config import RVAgentConfig

        config = RVAgentConfig(package_name="test", agent_mode="invalid_mode")

        # Mode validation happens in validate() method
        is_valid, error = config.validate()
        assert not is_valid
        assert "agent_mode" in error.lower()

    def test_to_dict(self):
        """Config converts to dictionary."""
        from rv_agent.config.agent_config import RVAgentConfig

        config = RVAgentConfig.create_default(package_name="test")
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert "package_name" in config_dict
        assert "llm_model" in config_dict
        assert "agent_mode" in config_dict
