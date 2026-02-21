"""
Unit tests for the RVAgentConfig model.
"""

import pytest
from unittest.mock import patch
from rv_agent.config.agent_config import RVAgentConfig


@pytest.fixture
def default_config():
    """A default RVAgentConfig instance for testing."""
    return RVAgentConfig(package_name="com.example.app")


class TestAgentConfig:
    """Test suite for RVAgentConfig."""

    def test_get_langchain_config(self, default_config):
        """Test that the LangChain config is generated correctly."""
        lc_config = default_config.get_langchain_config()
        assert lc_config["base_url"] == default_config.llm_base_url
        assert lc_config["model"] == default_config.llm_model
        assert "api_key" in lc_config
        assert "temperature" in lc_config
        # top_k is passed via extra_body for SGLang
        if default_config.llm_top_k > 0:
            assert "extra_body" in lc_config
            assert lc_config["extra_body"]["top_k"] == default_config.llm_top_k

    @patch("os.getenv")
    def test_get_agent_mode_from_env(self, mock_getenv, default_config):
        """Test that get_agent_mode prioritizes the environment variable."""
        # Default mode is 'multimode'
        assert default_config.get_agent_mode() == "multimode"

        # Set env var
        mock_getenv.return_value = "llm_only"
        assert default_config.get_agent_mode() == "llm_only"
        mock_getenv.assert_called_with("RVAGENT_MODE")

        # Invalid env var should be ignored
        mock_getenv.return_value = "invalid_mode"
        assert default_config.get_agent_mode() == "multimode"

    def test_validate_failure_cases(self):
        """Test the failure paths of the validate method."""
        # Custom validation: invalid agent_mode
        config = RVAgentConfig(
            package_name="com.example.app", agent_mode="invalid_mode"
        )
        is_valid, msg = config.validate()
        assert not is_valid
        assert "agent_mode must be one of" in msg

    def test_validate_success(self, default_config):
        """Test the success path of the validate method."""
        is_valid, msg = default_config.validate()
        assert is_valid is True
        assert msg is None

    def test_to_dict(self, default_config):
        """Test conversion to dictionary."""
        d = default_config.to_dict()
        assert isinstance(d, dict)
        assert d["package_name"] == "com.example.app"

    def test_create_default(self):
        """Test the create_default class method."""
        config = RVAgentConfig.create_default(package_name="com.test.app")
        assert config.package_name == "com.test.app"
        assert config.device_id == RVAgentConfig.model_fields["device_id"].default

    def test_create_default_with_device_id(self):
        """Test create_default with a specific device_id."""
        config = RVAgentConfig.create_default(
            package_name="com.test.app", device_id="emulator-5556"
        )
        assert config.package_name == "com.test.app"
        assert config.device_id == "emulator-5556"
