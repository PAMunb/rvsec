import pytest
import os
import json
import tempfile
from unittest.mock import patch, MagicMock

from rv_llm.config.configuration import Configuration, ConfigValue
from rv_android_core.constants import ENV_REPETITIONS, ENV_TIMEOUTS, ENV_TOOLS


class TestConfigValue:
    """Tests for the ConfigValue class"""

    def test_config_value_initialization(self):
        """Test ConfigValue constructor with various types"""
        # String config
        str_config = ConfigValue("app_name", "RVApp", str, "Application name")
        assert str_config.key == "app_name"
        assert str_config.default == "RVApp"
        assert str_config.value_type == str
        assert str_config.description == "Application name"
        assert str_config.env_var is None
        assert str_config.choices is None
        assert str_config.value == "RVApp"  # Default is used as initial value

        # Int config with environment variable
        int_config = ConfigValue("repetitions", 1, int, "Number of repetitions", ENV_REPETITIONS)
        assert int_config.key == "repetitions"
        assert int_config.default == 1
        assert int_config.value_type == int
        assert int_config.env_var == ENV_REPETITIONS

        # Bool config with choices
        bool_config = ConfigValue("debug", True, bool, "Debug mode", choices=[True, False])
        assert bool_config.key == "debug"
        assert bool_config.default is True
        assert bool_config.value_type == bool
        assert bool_config.choices == [True, False]

        # List config with validator
        validator = lambda x: len(x) > 0
        list_config = ConfigValue("tools", ["monkey"], list, "Testing tools", validator=validator)
        assert list_config.key == "tools"
        assert list_config.default == ["monkey"]
        assert list_config.value_type == list
        assert list_config.validator == validator

    def test_config_value_setter(self):
        """Test value setter with valid values"""
        # String config
        str_config = ConfigValue("app_name", "RVApp", str)
        str_config.value = "NewApp"
        assert str_config.value == "NewApp"

        # Int config with conversion
        int_config = ConfigValue("repetitions", 1, int)
        int_config.value = "5"  # String that should be converted to int
        assert int_config.value == 5
        assert isinstance(int_config.value, int)

        # Boolean config with conversion
        bool_config = ConfigValue("debug", False, bool)
        bool_config.value = "true"  # String that should be converted to bool
        assert bool_config.value is True

        # List config with conversion
        list_config = ConfigValue("tools", ["monkey"], list)
        list_config.value = "monkey droidbot"  # String that should be converted to list
        assert list_config.value == ["monkey", "droidbot"]

    def test_config_value_setter_invalid_type(self):
        """Test value setter with invalid types"""
        # Int config with non-convertible value
        int_config = ConfigValue("repetitions", 1, int)
        with pytest.raises(TypeError):
            int_config.value = "not_an_int"

    def test_config_value_setter_invalid_choice(self):
        """Test value setter with invalid choices"""
        # Config with limited choices
        config = ConfigValue("log_level", "info", str, choices=["debug", "info", "warning", "error"])

        # Valid choice
        config.value = "debug"
        assert config.value == "debug"

        # Invalid choice
        with pytest.raises(ValueError):
            config.value = "trace"  # Not in choices

    def test_config_value_setter_invalid_validator(self):
        """Test value setter with failing validator"""
        # Config with validator
        validator = lambda x: x > 0
        config = ConfigValue("timeout", 60, int, validator=validator)

        # Valid value
        config.value = 30
        assert config.value == 30

        # Invalid value
        with pytest.raises(ValueError):
            config.value = 0  # Validator requires > 0

    def test_bool_conversion(self):
        """Test special boolean conversion cases"""
        bool_config = ConfigValue("feature_flag", False, bool)

        # Test various truthy strings
        bool_config.value = "true"
        assert bool_config.value is True

        bool_config.value = "yes"
        assert bool_config.value is True

        bool_config.value = "1"
        assert bool_config.value is True

        bool_config.value = "y"
        assert bool_config.value is True

        # Test various falsy strings
        bool_config.value = "false"
        assert bool_config.value is False

        bool_config.value = "no"
        assert bool_config.value is False

        bool_config.value = "0"
        assert bool_config.value is False

        bool_config.value = "n"
        assert bool_config.value is False

    def test_list_conversion(self):
        """Test special list conversion cases"""
        list_config = ConfigValue("tools", ["monkey"], list)

        # Test string to list conversion
        list_config.value = "monkey droidbot humanoid"
        assert list_config.value == ["monkey", "droidbot", "humanoid"]

        # Test non-list iterable to list
        list_config.value = ("monkey", "droidbot")
        assert list_config.value == ["monkey", "droidbot"]
        assert isinstance(list_config.value, list)


class TestConfiguration:
    """Tests for the Configuration class"""

    @pytest.fixture
    def config(self):
        """Create a clean Configuration instance for each test"""
        # Reset the singleton instance to ensure clean state
        old_instance = Configuration._instance
        Configuration._instance = None

        # Create a fresh instance
        instance = Configuration.get_instance()

        # Yield the instance for the test
        yield instance

        # Restore the old instance after the test
        Configuration._instance = old_instance

    def test_singleton_pattern(self):
        """Test that Configuration uses singleton pattern"""
        Configuration._instance = None  # Reset singleton

        config1 = Configuration.get_instance()
        config2 = Configuration.get_instance()

        assert config1 is config2  # Same instance

    def test_initialization(self, config):
        """Test Configuration constructor and default values"""
        assert hasattr(config, 'schema')
        assert hasattr(config, 'logger')

        # Check some key configuration parameters
        assert "repetitions" in config.schema
        assert config.schema["repetitions"].default == 1
        assert config.schema["repetitions"].value_type == int

        assert "timeouts" in config.schema
        assert config.schema["timeouts"].default == [60]

        assert "tools" in config.schema
        assert "monkey" in config.schema["tools"].default

    @patch.dict(os.environ, {ENV_REPETITIONS: "5"})
    def test_load_from_environment(self):
        """Test loading values from environment variables"""
        # Reset the singleton to force environment loading
        Configuration._instance = None
        config = Configuration.get_instance()

        # Check values loaded from environment
        assert config.get("repetitions") == 5

    @patch.dict(os.environ, {"RV_SKIP_MONITORS": "true", "RV_SKIP_INSTRUMENT": "1"})
    def test_load_from_environment_skip_flags(self):
        """Test loading inverted skip flags from environment"""
        # Reset the singleton to force environment loading
        Configuration._instance = None
        config = Configuration.get_instance()

        # Check inverted values
        assert config.get("generate_monitors") is False  # RV_SKIP_MONITORS=true inverts to False
        assert config.get("instrument") is False  # RV_SKIP_INSTRUMENT=1 inverts to False

    def test_load_from_file(self, config):
        """Test loading configuration from a file"""
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            json.dump({
                "repetitions": 3,
                "timeouts": [45, 90],
                "debug": True
            }, f)
            config_file = f.name

        try:
            # Load the config
            result = config.load_from_file(config_file)

            # Check result and values
            assert result is True
            assert config.get("repetitions") == 3
            assert config.get("timeouts") == [45, 90]
            assert config.get("debug") is True
        finally:
            # Clean up
            os.unlink(config_file)

    def test_load_from_file_nonexistent(self, config):
        """Test loading from a nonexistent file"""
        result = config.load_from_file("/nonexistent/file.json")
        assert result is False

    def test_load_from_file_invalid_json(self, config):
        """Test loading from an invalid JSON file"""
        # Create a temporary file with invalid JSON
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("not valid json")
            config_file = f.name

        try:
            # Try to load the config
            result = config.load_from_file(config_file)

            # Should fail gracefully
            assert result is False
        finally:
            # Clean up
            os.unlink(config_file)

    def test_save_to_file(self, config):
        """Test saving configuration to a file"""
        # Set some values
        config.set("repetitions", 3)
        config.set("timeouts", [45, 90])

        # Save to a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            config_file = f.name

        try:
            # Save the config
            result = config.save_to_file(config_file)

            # Check result
            assert result is True

            # Read the file and verify contents
            with open(config_file, 'r') as f:
                data = json.load(f)
                assert data["repetitions"] == 3
                assert data["timeouts"] == [45, 90]
        finally:
            # Clean up
            os.unlink(config_file)

    def test_save_to_file_error(self, config):
        """Test saving to a file with error handling"""
        # Try to save to an invalid directory
        result = config.save_to_file("/nonexistent/directory/config.json")

        # Should fail gracefully
        assert result is False

    def test_get_set_methods(self, config):
        """Test get and set methods"""
        # Test get with default
        assert config.get("nonexistent", "default") == "default"

        # Test set and get for existing keys in schema
        config.set("repetitions", 5)
        assert config.get("repetitions") == 5

        # Test set with invalid key - should raise ValueError
        with pytest.raises(ValueError):
            config.set("nonexistent_key", "value")

    def test_type_specific_getters(self, config):
        """Test type-specific getter methods"""
        # Setup values for keys that exist in the schema
        config.set("repetitions", 5)
        config.set("tools", ["monkey", "droidbot"])
        config.set("debug", True)

        # Test getters
        assert config.get_int("repetitions") == 5
        assert config.get_list("tools") == ["monkey", "droidbot"]
        assert config.get_bool("debug") is True
        assert config.get_str("repetitions") == "5"  # Conversion to string

        # Test getters with defaults for non-existent keys
        assert config.get_int("nonexistent", 10) == 10
        assert config.get_bool("nonexistent", False) is False
        assert config.get_str("nonexistent", "Default") == "Default"
        assert config.get_list("nonexistent", ["default"]) == ["default"]

    def test_get_with_missing_key_and_no_default(self, config):
        """Test get method with missing key and no default"""
        with pytest.raises(ValueError):
            config.get_int("nonexistent")

        with pytest.raises(ValueError):
            config.get_bool("nonexistent")

        with pytest.raises(ValueError):
            config.get_str("nonexistent")

        with pytest.raises(ValueError):
            config.get_list("nonexistent")

    def test_update_method(self, config):
        """Test update method for batch updates"""
        update_dict = {
            "repetitions": 3,
            "debug": True,
            "nonexistent": "should be ignored"  # Invalid key
        }

        # Should log a warning but not raise an exception
        with patch.object(config.logger, 'warning') as mock_warning:
            config.update(update_dict)

            # Check that a warning was logged for the invalid key
            mock_warning.assert_called()

        # Check valid updates were applied
        assert config.get("repetitions") == 3
        assert config.get("debug") is True

    def test_to_dict(self, config):
        """Test to_dict method"""
        # Setup some values
        config.set("repetitions", 3)
        config.set("debug", True)

        # Get dictionary
        config_dict = config.to_dict()

        # Verify
        assert "repetitions" in config_dict
        assert config_dict["repetitions"] == 3
        assert "debug" in config_dict
        assert config_dict["debug"] is True

    def test_get_schema_info(self, config):
        """Test get_schema_info method"""
        schema_info = config.get_schema_info()

        # Check schema structure
        assert "repetitions" in schema_info
        assert "type" in schema_info["repetitions"]
        assert "default" in schema_info["repetitions"]
        assert "description" in schema_info["repetitions"]
        assert "current_value" in schema_info["repetitions"]

    def test_validate_all(self, config):
        """Test validate_all method"""
        # All defaults should be valid
        assert config.validate_all() == []

        # Add a value that should fail validation
        # Need to access protected member directly to avoid the validation during set
        repetitions_config = config.schema["repetitions"]
        original_value = repetitions_config.value

        # Create a validator function that fails
        original_validator = repetitions_config.validator

        def always_fail(x): return False

        repetitions_config.validator = always_fail

        # Validation should now fail
        errors = config.validate_all()
        assert len(errors) > 0
        assert "repetitions" in errors[0]

        # Restore original validator
        repetitions_config.validator = original_validator

    def test_reset_to_defaults(self, config):
        """Test reset_to_defaults method"""
        # Change some values
        config.set("repetitions", 10)
        config.set("debug", True)

        # Reset to defaults
        config.reset_to_defaults()

        # Check values are back to defaults
        assert config.get("repetitions") == 1
        assert config.get("debug") is False

    def test_get_experiment_summary(self, config):
        """Test get_experiment_summary method"""
        # Setup some values
        config.set("repetitions", 3)
        config.set("timeouts", [30, 60])
        config.set("tools", ["monkey", "droidbot"])

        # Get summary
        summary = config.get_experiment_summary()

        # Check summary content
        assert isinstance(summary, str)
        assert "repetitions=3" in summary
        assert "timeouts=[30, 60]" in summary
        assert "tools=['monkey', 'droidbot']" in summary

    def test_print_experiment_summary(self, config):
        """Test print_experiment_summary method"""
        with patch.object(config.logger, 'info') as mock_info:
            config.print_experiment_summary()
            mock_info.assert_called_once()