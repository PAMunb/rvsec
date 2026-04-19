"""
Tests for DroidBotTool - DroidBot lightweight test input generator.

Tests cover:
- Tool specification and available policies
- configure() with policy validation
- _build_droidbot_command() with correct CLI flags
- get_available_policies() and get_tool_info()
"""

from unittest.mock import MagicMock, patch

import pytest
from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task
from rv_android_core.util.error.exceptions import ConfigurationError
from rv_tools.builtin.droidbot.tool import DroidBotTool


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def droidbot_tool():
    """Create DroidBotTool instance."""
    tool = DroidBotTool()
    tool.config = {}
    yield tool


@pytest.fixture
def mock_task():
    """Create a mock task with minimal configuration."""
    task = MagicMock()
    task.id = "test_task_001"
    task.config = MagicMock()
    task.config.timeout = 600
    task.result = MagicMock()
    task.result.trace_file = "/tmp/test_trace.txt"
    return task


@pytest.fixture
def mock_app():
    """Create a mock App instance."""
    app = MagicMock()
    app.path = "/path/to/test_app.apk"
    app.package_name = "com.test.app"
    return app


# ---------------------------------------------------------------------------
# Tests: Tool Specification
# ---------------------------------------------------------------------------


class TestToolSpecification:
    """Test DroidBotTool specification and policies."""

    def test_tool_spec_name(self):
        """Test tool spec name."""
        spec = DroidBotTool.get_tool_spec()
        assert spec.name == "droidbot"

    def test_tool_spec_version(self):
        """Test tool spec version."""
        spec = DroidBotTool.get_tool_spec()
        assert spec.version == "1.0.0"

    def test_get_variants_returns_all_policies(self):
        """Test that get_variants returns all policy variants."""
        variants = DroidBotTool.get_variants()
        assert "default" in variants
        assert "dfs_greedy" in variants
        assert "bfs_greedy" in variants
        assert "dfs_naive" in variants
        assert "bfs_naive" in variants
        assert "random" in variants

    def test_available_policies_list(self, droidbot_tool):
        """Test available policies list."""
        policies = droidbot_tool.get_available_policies()
        assert "dfs_naive" in policies
        assert "dfs_greedy" in policies
        assert "bfs_naive" in policies
        assert "bfs_greedy" in policies
        assert "random" in policies
        assert "monkey" in policies

    def test_default_variant_config(self):
        """Test default variant configuration."""
        variants = DroidBotTool.get_variants()
        assert variants["default"]["policy"] == "dfs_naive"
        assert variants["default"]["count"] == 1000


# ---------------------------------------------------------------------------
# Tests: configure()
# ---------------------------------------------------------------------------


class TestConfigure:
    """Test configure() with policy validation."""

    def test_configure_requires_policy(self, droidbot_tool):
        """Test that policy is required."""
        with pytest.raises(ConfigurationError, match="requires.*policy"):
            droidbot_tool.configure({})

    def test_configure_validates_policy(self, droidbot_tool):
        """Test that policy is validated."""
        with pytest.raises(ConfigurationError, match="Invalid.*policy"):
            droidbot_tool.configure({"policy": "invalid"})

    def test_configure_dfs_greedy_policy(self, droidbot_tool):
        """Test configure with dfs_greedy policy."""
        droidbot_tool.configure({"policy": "dfs_greedy"})
        assert droidbot_tool.config["policy"] == "dfs_greedy"

    def test_configure_bfs_greedy_policy(self, droidbot_tool):
        """Test configure with bfs_greedy policy."""
        droidbot_tool.configure({"policy": "bfs_greedy"})
        assert droidbot_tool.config["policy"] == "bfs_greedy"

    def test_configure_random_policy(self, droidbot_tool):
        """Test configure with random policy."""
        droidbot_tool.configure({"policy": "random"})
        assert droidbot_tool.config["policy"] == "random"

    def test_configure_custom_count(self, droidbot_tool):
        """Test configure with custom count."""
        droidbot_tool.configure({"policy": "dfs_naive", "count": 5000})
        assert droidbot_tool.config["count"] == 5000

    def test_configure_custom_interval(self, droidbot_tool):
        """Test configure with custom interval."""
        droidbot_tool.configure({"policy": "dfs_naive", "interval": 5})
        assert droidbot_tool.config["interval"] == 5

    def test_configure_custom_device_serial(self, droidbot_tool):
        """Test configure with custom device serial."""
        droidbot_tool.configure({"policy": "dfs_naive", "device_serial": "emulator-5556"})
        assert droidbot_tool.config["device_serial"] == "emulator-5556"

    def test_configure_default_values(self, droidbot_tool):
        """Test configure sets default values."""
        droidbot_tool.configure({"policy": "dfs_naive"})
        assert droidbot_tool.config["count"] == 1000
        assert droidbot_tool.config["interval"] == 3
        assert droidbot_tool.config["device_serial"] == "emulator-5554"
        assert droidbot_tool.config["ignore_ad"] is True


# ---------------------------------------------------------------------------
# Tests: _build_droidbot_command()
# ---------------------------------------------------------------------------


class TestBuildDroidBotCommand:
    """Test _build_droidbot_command() with correct CLI flags."""

    def test_build_command_uses_droidbot(self, droidbot_tool, mock_app):
        """Test command uses droidbot as base."""
        droidbot_tool.configure({"policy": "dfs_naive"})
        cmd = droidbot_tool._build_droidbot_command(mock_app, 300)

        assert cmd.command == "droidbot"

    def test_build_command_includes_device_serial(self, droidbot_tool, mock_app):
        """Test command includes device serial."""
        droidbot_tool.configure({"policy": "dfs_naive", "device_serial": "emulator-5556"})
        cmd = droidbot_tool._build_droidbot_command(mock_app, 300)

        assert "-d" in cmd.args
        assert "emulator-5556" in cmd.args

    def test_build_command_includes_apk_path(self, droidbot_tool, mock_app):
        """Test command includes APK path."""
        droidbot_tool.configure({"policy": "dfs_naive"})
        cmd = droidbot_tool._build_droidbot_command(mock_app, 300)

        assert "-a" in cmd.args
        assert "/path/to/test_app.apk" in cmd.args

    def test_build_command_includes_policy(self, droidbot_tool, mock_app):
        """Test command includes policy."""
        droidbot_tool.configure({"policy": "dfs_greedy"})
        cmd = droidbot_tool._build_droidbot_command(mock_app, 300)

        assert "-policy" in cmd.args
        assert "dfs_greedy" in cmd.args

    def test_build_command_includes_count(self, droidbot_tool, mock_app):
        """Test command includes high event count."""
        droidbot_tool.configure({"policy": "dfs_naive"})
        cmd = droidbot_tool._build_droidbot_command(mock_app, 300)

        assert "-count" in cmd.args
        assert "10000000000" in cmd.args

    def test_build_command_includes_timeout(self, droidbot_tool, mock_app):
        """Test command includes timeout."""
        droidbot_tool.configure({"policy": "dfs_naive"})
        cmd = droidbot_tool._build_droidbot_command(mock_app, 600)

        assert "-timeout" in cmd.args
        assert "600" in cmd.args

    def test_build_command_includes_ignore_ad(self, droidbot_tool, mock_app):
        """Test command includes ignore_ad flag."""
        droidbot_tool.configure({"policy": "dfs_naive", "ignore_ad": True})
        cmd = droidbot_tool._build_droidbot_command(mock_app, 300)

        assert "-ignore_ad" in cmd.args

    def test_build_command_includes_is_emulator(self, droidbot_tool, mock_app):
        """Test command includes is_emulator flag."""
        droidbot_tool.configure({"policy": "dfs_naive"})
        cmd = droidbot_tool._build_droidbot_command(mock_app, 300)

        assert "-is_emulator" in cmd.args

    def test_build_command_default_serial(self, droidbot_tool, mock_app):
        """Test command uses default serial when not configured."""
        droidbot_tool.configure({"policy": "dfs_naive"})
        cmd = droidbot_tool._build_droidbot_command(mock_app, 300)

        idx = cmd.args.index("-d")
        assert cmd.args[idx + 1] == "emulator-5554"

    def test_build_command_timeout(self, droidbot_tool, mock_app):
        """Test command timeout is set correctly."""
        droidbot_tool.configure({"policy": "dfs_naive"})
        cmd = droidbot_tool._build_droidbot_command(mock_app, 900)

        assert cmd.timeout == 900


# ---------------------------------------------------------------------------
# Tests: get_tool_info()
# ---------------------------------------------------------------------------


class TestGetToolInfo:
    """Test get_tool_info() retrieval."""

    def test_get_tool_info_returns_base_info(self, droidbot_tool):
        """Test get_tool_info returns base tool information."""
        droidbot_tool.configure({"policy": "dfs_naive"})
        info = droidbot_tool.get_tool_info()

        assert "name" in info

    def test_get_tool_info_returns_tool_spec(self, droidbot_tool):
        """Test get_tool_info returns tool_spec."""
        droidbot_tool.configure({"policy": "dfs_naive"})
        info = droidbot_tool.get_tool_info()

        assert "tool_spec" in info

    def test_get_tool_info_returns_available_policies(self, droidbot_tool):
        """Test get_tool_info returns available_policies."""
        droidbot_tool.configure({"policy": "dfs_naive"})
        info = droidbot_tool.get_tool_info()

        assert "available_policies" in info
        assert "dfs_greedy" in info["available_policies"]

    def test_get_tool_info_returns_current_policy(self, droidbot_tool):
        """Test get_tool_info returns current_policy."""
        droidbot_tool.configure({"policy": "bfs_greedy"})
        info = droidbot_tool.get_tool_info()

        assert "current_policy" in info
        assert info["current_policy"] == "bfs_greedy"

    def test_get_tool_info_returns_count(self, droidbot_tool):
        """Test get_tool_info returns current_count."""
        droidbot_tool.configure({"policy": "dfs_naive", "count": 5000})
        info = droidbot_tool.get_tool_info()

        assert "current_count" in info
        assert info["current_count"] == 5000

    def test_get_tool_info_returns_timeout(self, droidbot_tool):
        """Test get_tool_info returns current_timeout."""
        droidbot_tool.configure({"policy": "dfs_naive", "timeout": 7200})
        info = droidbot_tool.get_tool_info()

        assert "current_timeout" in info
        assert info["current_timeout"] == 7200
