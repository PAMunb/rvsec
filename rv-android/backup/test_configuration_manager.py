import argparse
from unittest.mock import patch, MagicMock

import pytest

from rv_llm.config.configuration import Configuration
from rv_llm.config.configuration_manager import ConfigurationManager


class TestConfigurationManager:
    """Tests for the ConfigurationManager class"""

    @pytest.fixture
    def mock_config(self):
        """Create a mock Configuration instance"""
        mock = MagicMock(spec=Configuration)
        return mock

    @pytest.fixture
    def config_manager(self, mock_config):
        """Create a ConfigurationManager with mocked dependencies"""
        with patch('rv_llm.config.configuration_manager.Configuration') as mock_config_cls:
            mock_config_cls.get_instance.return_value = mock_config
            manager = ConfigurationManager()
            assert manager.config == mock_config
            return manager

    def test_configuration_manager_initialization(self, config_manager, mock_config):
        """Test ConfigurationManager constructor"""
        assert config_manager.config == mock_config
        assert hasattr(config_manager, 'logger')

    def test_load_from_args(self, config_manager, mock_config):
        """Test load_from_args method"""
        # Create mock args
        args = argparse.Namespace(
            debug=True,
            r=5,
            t=[30, 60, 90],
            tools=["monkey", "droidbot"],
            c="memory.json",
            no_window=True,
            skip_monitors=True,
            skip_instrument=False,
            skip_static_analysis=True,
            skip_experiment=True
        )

        # Call method
        config_manager.load_from_args(args)

        # Verify config was updated with correct values and inversions for skip flags
        mock_config.set.assert_any_call("debug", True)
        mock_config.set.assert_any_call("repetitions", 5)
        mock_config.set.assert_any_call("timeouts", [30, 60, 90])
        mock_config.set.assert_any_call("tools", ["monkey", "droidbot"])
        mock_config.set.assert_any_call("memory_file", "memory.json")
        mock_config.set.assert_any_call("no_window", True)
        mock_config.set.assert_any_call("generate_monitors", False)  # Inverted
        mock_config.set.assert_any_call("instrument", True)  # Inverted
        mock_config.set.assert_any_call("static_analysis", False)  # Inverted
        mock_config.set.assert_any_call("skip_experiment", True)  # Not inverted

    def test_get_experiment_config(self, config_manager, mock_config):
        """Test get_experiment_config method"""
        # Setup mock returns
        mock_config.get_int.return_value = 5
        mock_config.get_list.return_value = [30, 60]
        mock_config.get_bool.side_effect = [True, False, True, False, True]
        mock_config.get_str.return_value = "memory.json"

        # Call method
        config = config_manager.get_experiment_config()

        # Verify config values
        assert config["repetitions"] == 5
        assert config["timeouts"] == [30, 60]
        assert config["generate_monitors"] is True
        assert config["instrument"] is False
        assert config["static_analysis"] is True
        assert config["skip_experiment"] is False
        assert config["no_window"] is True
        assert config["memory_file"] == "memory.json"

        # Verify config methods were called with correct parameters
        mock_config.get_int.assert_any_call("repetitions", 1)
        mock_config.get_list.assert_called_once_with("timeouts")
        mock_config.get_bool.assert_any_call("generate_monitors", True)
        mock_config.get_bool.assert_any_call("instrument", True)
        mock_config.get_bool.assert_any_call("static_analysis", True)
        mock_config.get_bool.assert_any_call("skip_experiment", False)
        mock_config.get_bool.assert_any_call("no_window", True)
        mock_config.get_str.assert_called_once_with("memory_file", "")

    def test_get_tool_config(self, config_manager, mock_config):
        """Test get_tool_config method"""
        # Setup mock returns
        mock_config.get_int.return_value = 60
        mock_config.get_bool.return_value = True
        mock_config.get_str.side_effect = ["127.0.0.1:50405", "http://127.0.0.1:5000"]

        # Test default tool config
        config = config_manager.get_tool_config("monkey")
        assert config["timeout"] == 60
        assert config["no_window"] is True

        # Test humanoid config
        config = config_manager.get_tool_config("humanoid")
        assert config["timeout"] == 60
        assert config["no_window"] is True
        assert config["humanoid_url"] == "127.0.0.1:50405"

        # Test rvandroid config
        config = config_manager.get_tool_config("rvandroid")
        assert config["timeout"] == 60
        assert config["no_window"] is True
        assert config["rvandroid_url"] == "http://127.0.0.1:5000"

        # Verify config methods were called with correct parameters
        mock_config.get_int.assert_any_call("timeout", 60)
        mock_config.get_bool.assert_any_call("no_window", True)
        mock_config.get_str.assert_any_call("humanoid_url", "127.0.0.1:50405")
        mock_config.get_str.assert_any_call("rvandroid_url", "http://127.0.0.1:5000")

    def test_get_android_config(self, config_manager, mock_config):
        """Test get_android_config method"""
        # Setup mock returns
        mock_config.get_bool.return_value = True

        # Call method
        config = config_manager.get_android_config()

        # Verify config values
        assert config["avd_name"] == "RVSec"
        assert config["no_window"] is True
        assert config["clean_logcat"] is True

        # Verify config methods were called with correct parameters
        mock_config.get_bool.assert_called_once_with("no_window", True)

    def test_save_configuration(self, config_manager, mock_config):
        """Test save_configuration method"""
        # Setup mock returns
        mock_config.save_to_file.return_value = True

        # Call method
        result = config_manager.save_configuration("config.json")

        # Verify result and method call
        assert result is True
        mock_config.save_to_file.assert_called_once_with("config.json")

    def test_load_configuration(self, config_manager, mock_config):
        """Test load_configuration method"""
        # Setup mock returns
        mock_config.load_from_file.return_value = True

        # Call method
        result = config_manager.load_configuration("config.json")

        # Verify result and method call
        assert result is True
        mock_config.load_from_file.assert_called_once_with("config.json")

    def test_get_configuration_summary(self, config_manager, mock_config):
        """Test get_configuration_summary method"""
        # Setup mock returns
        mock_config.get_schema_info.return_value = {
            "repetitions": {
                "current_value": 5,
                "default": 1,
                "env_var": "RV_REPETITIONS",
                "modified": True
            },
            "timeouts": {
                "current_value": [30, 60],
                "default": [60],
                "env_var": "RV_TIMEOUTS",
                "modified": True
            }
        }

        # Call method
        summary = config_manager.get_configuration_summary()

        # Verify the summary is a string and contains expected text
        assert isinstance(summary, str)
        assert "Current Configuration:" in summary
        assert "repetitions" in summary
        assert "timeouts" in summary

        # Verify config methods were called
        mock_config.get_schema_info.assert_called_once()
