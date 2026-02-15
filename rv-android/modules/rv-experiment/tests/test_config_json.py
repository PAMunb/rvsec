"""
Tests for ExperimentConfig JSON serialization and ToolConfig integration.

Validates that ExperimentConfig correctly serializes/deserializes with the
unified ToolConfig from rv-android-core, including round-trip fidelity,
current-format deserialization, type preservation, and variant expansion.
"""

import json
from unittest.mock import patch

import pytest

from rv_android_core.domain.task import ToolConfig
from rv_experiment.config import ExperimentConfig


@pytest.fixture
def sample_tool_configs():
    """Create sample ToolConfig instances for testing."""
    return [
        ToolConfig(name="monkey", variant="default", parameters={}),
        ToolConfig(name="droidbot", variant="dfs_greedy", parameters={"count": 2000}),
    ]


@pytest.fixture
def sample_experiment_config(sample_tool_configs, tmp_path):
    """Create a minimal ExperimentConfig for testing."""
    apks_dir = tmp_path / "apks"
    apks_dir.mkdir()
    (apks_dir / "test.apk").touch()

    return ExperimentConfig(
        name="test_experiment",
        description="Test experiment for JSON round-trip",
        tool_configs=sample_tool_configs,
        apks_dir=str(apks_dir),
        repetitions=2,
        timeouts=[300, 600],
        specification_set="jca",
    )


class TestJsonRoundTrip:
    """Test JSON serialization round-trip."""

    def test_json_round_trip(self, sample_experiment_config):
        """Create ExperimentConfig, save to JSON via to_json(), load via from_dict(), verify tool_configs match."""
        # Serialize to JSON
        json_str = sample_experiment_config.to_json()

        # Deserialize from JSON
        data = json.loads(json_str)
        restored = ExperimentConfig.from_dict(data)

        # Verify tool configs match
        assert len(restored.tool_configs) == len(sample_experiment_config.tool_configs)

        for original, restored_tc in zip(
            sample_experiment_config.tool_configs, restored.tool_configs
        ):
            assert restored_tc.name == original.name
            assert restored_tc.variant == original.variant
            assert restored_tc.parameters == original.parameters

        # Verify other fields
        assert restored.name == sample_experiment_config.name
        assert restored.repetitions == sample_experiment_config.repetitions
        assert restored.timeouts == sample_experiment_config.timeouts


class TestFromDictCurrentFormat:
    """Test from_dict() with current field names."""

    def test_from_dict_current_format(self, tmp_path):
        """Verify from_dict() works with current ToolConfig field names (name, variant, parameters)."""
        apks_dir = tmp_path / "apks"
        apks_dir.mkdir()
        (apks_dir / "test.apk").touch()

        data = {
            "name": "test_exp",
            "tool_configs": [
                {"name": "droidbot", "variant": "dfs_greedy", "parameters": {}},
                {"name": "monkey", "variant": "default", "parameters": {"seed": 42}},
            ],
            "apks_dir": str(apks_dir),
        }

        config = ExperimentConfig.from_dict(data)

        assert len(config.tool_configs) == 2
        assert config.tool_configs[0].name == "droidbot"
        assert config.tool_configs[0].variant == "dfs_greedy"
        assert config.tool_configs[0].parameters == {}
        assert config.tool_configs[1].name == "monkey"
        assert config.tool_configs[1].variant == "default"
        assert config.tool_configs[1].parameters == {"seed": 42}


class TestTypePreservation:
    """Test that types are preserved through JSON round-trip."""

    def test_type_preservation(self, tmp_path):
        """Verify int/float types are preserved through JSON round-trip (not converted to strings)."""
        apks_dir = tmp_path / "apks"
        apks_dir.mkdir()
        (apks_dir / "test.apk").touch()

        config = ExperimentConfig(
            name="type_test",
            tool_configs=[
                ToolConfig(
                    name="monkey",
                    parameters={"seed": 42, "throttle": 100, "ratio": 0.5},
                ),
            ],
            apks_dir=str(apks_dir),
        )

        # Round-trip through JSON
        json_str = config.to_json()
        data = json.loads(json_str)
        restored = ExperimentConfig.from_dict(data)

        params = restored.tool_configs[0].parameters
        assert isinstance(
            params["seed"], int
        ), f"seed should be int, got {type(params['seed'])}"
        assert isinstance(
            params["throttle"], int
        ), f"throttle should be int, got {type(params['throttle'])}"
        assert isinstance(
            params["ratio"], float
        ), f"ratio should be float, got {type(params['ratio'])}"
        assert params["seed"] == 42
        assert params["throttle"] == 100
        assert params["ratio"] == 0.5


class TestVariantExpansionAtParseTime:
    """Test that parse_tool_specification expands multi-variant specs."""

    @patch("rv_tools.ToolRegistry.get_instance")
    def test_variant_expansion_at_parse_time(self, mock_registry):
        """Test that parse_tool_specification('droidbot:a:b', {}) returns 2 ToolConfig instances."""
        from rv_experiment.__main__ import CLIContext

        # Mock the tool registry to avoid actual tool loading
        mock_registry_instance = mock_registry.return_value
        mock_registry_instance.get_all_tools.return_value = []

        ctx = CLIContext.__new__(CLIContext)
        ctx.tool_registry = mock_registry_instance

        # Set up a minimal logger
        from unittest.mock import MagicMock

        ctx.logger = MagicMock()

        result = ctx.parse_tool_specification("droidbot:a:b")

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0].name == "droidbot"
        assert result[0].variant == "a"
        assert result[1].name == "droidbot"
        assert result[1].variant == "b"

    @patch("rv_tools.ToolRegistry.get_instance")
    def test_single_variant_produces_one_config(self, mock_registry):
        """Test that a single variant produces exactly one ToolConfig."""
        from rv_experiment.__main__ import CLIContext
        from unittest.mock import MagicMock

        mock_registry_instance = mock_registry.return_value
        mock_registry_instance.get_all_tools.return_value = []

        ctx = CLIContext.__new__(CLIContext)
        ctx.tool_registry = mock_registry_instance
        ctx.logger = MagicMock()

        result = ctx.parse_tool_specification("droidbot:dfs_greedy")

        assert len(result) == 1
        assert result[0].name == "droidbot"
        assert result[0].variant == "dfs_greedy"

    @patch("rv_tools.ToolRegistry.get_instance")
    def test_no_variant_produces_default(self, mock_registry):
        """Test that no variant produces a single ToolConfig with 'default' variant."""
        from rv_experiment.__main__ import CLIContext
        from unittest.mock import MagicMock

        mock_registry_instance = mock_registry.return_value
        mock_registry_instance.get_all_tools.return_value = []

        ctx = CLIContext.__new__(CLIContext)
        ctx.tool_registry = mock_registry_instance
        ctx.logger = MagicMock()

        result = ctx.parse_tool_specification("monkey")

        assert len(result) == 1
        assert result[0].name == "monkey"
        assert result[0].variant == "default"
        assert result[0].parameters == {}

    @patch("rv_tools.ToolRegistry.get_instance")
    def test_variant_expansion_with_parameters(self, mock_registry):
        """Test that parameters are preserved across expanded variants."""
        from rv_experiment.__main__ import CLIContext
        from unittest.mock import MagicMock

        mock_registry_instance = mock_registry.return_value
        mock_registry_instance.get_all_tools.return_value = []

        ctx = CLIContext.__new__(CLIContext)
        ctx.tool_registry = mock_registry_instance
        ctx.logger = MagicMock()

        result = ctx.parse_tool_specification("droidbot:a:b@count=500")

        assert len(result) == 2
        assert result[0].parameters == {"count": "500"}
        assert result[1].parameters == {"count": "500"}
        # Verify parameters are independent copies
        result[0].parameters["extra"] = "test"
        assert "extra" not in result[1].parameters
