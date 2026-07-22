"""
Tests for APETool - CEGAR-based model abstraction testing tool.

Tests cover:
- Tool specification and available strategies
- configure() with strategy validation
- _resolve_ape_jar_path() resolution
- _build_ape_shell_command() with correct CLI flags
- get_available_strategies() and get_tool_info()
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task
from rv_android_core.util.error.exceptions import (
    ConfigurationError,
    RVToolExecutionError,
)
from rv_tools.builtin.ape.tool import APETool

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ape_tool():
    """Create APETool instance."""
    with patch("rv_tools.builtin.ape.tool.JarResolver"):
        tool = APETool()
        tool.config = {}
        yield tool


@pytest.fixture
def mock_task():
    """Create a mock task with minimal configuration."""
    task = MagicMock()
    task.id = "test_task_001"
    task.config = MagicMock()
    task.config.timeout = 300
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
    """Test APETool specification and strategies."""

    def test_tool_spec_name(self):
        """Test tool spec name."""
        spec = APETool.get_tool_spec()
        assert spec.name == "ape"

    def test_tool_spec_version(self):
        """Test tool spec version."""
        spec = APETool.get_tool_spec()
        assert spec.version == "1.0.0"

    def test_tool_spec_url(self):
        """Test tool spec URL."""
        spec = APETool.get_tool_spec()
        assert "ape" in spec.url.lower()

    def test_get_variants_returns_all_strategies(self):
        """Test that get_variants returns all strategies."""
        variants = APETool.get_variants()
        assert "default" in variants
        assert "sata" in variants
        assert "bfs" in variants
        assert "dfs" in variants
        assert "random" in variants

    def test_available_strategies_list(self, ape_tool):
        """Test available strategies list."""
        strategies = ape_tool.get_available_strategies()
        assert strategies == ["sata", "bfs", "dfs", "random"]

    def test_default_variant_config(self):
        """Test default variant configuration."""
        variants = APETool.get_variants()
        assert variants["default"]["strategy"] == "sata"
        assert variants["default"]["running_minutes"] == 5


# ---------------------------------------------------------------------------
# Tests: configure()
# ---------------------------------------------------------------------------


class TestConfigure:
    """Test configure() with strategy validation."""

    def test_configure_requires_strategy(self, ape_tool):
        """Test that strategy is required."""
        with pytest.raises(ConfigurationError, match="requires.*strategy"):
            ape_tool.configure({})

    def test_configure_validates_strategy(self, ape_tool):
        """Test that strategy is validated."""
        with pytest.raises(ConfigurationError, match="Invalid.*strategy"):
            ape_tool.configure({"strategy": "invalid"})

    def test_configure_sata_strategy(self, ape_tool):
        """Test configure with sata strategy."""
        ape_tool.configure({"strategy": "sata"})
        assert ape_tool.config["strategy"] == "sata"

    def test_configure_bfs_strategy(self, ape_tool):
        """Test configure with bfs strategy."""
        ape_tool.configure({"strategy": "bfs"})
        assert ape_tool.config["strategy"] == "bfs"

    def test_configure_dfs_strategy(self, ape_tool):
        """Test configure with dfs strategy."""
        ape_tool.configure({"strategy": "dfs"})
        assert ape_tool.config["strategy"] == "dfs"

    def test_configure_random_strategy(self, ape_tool):
        """Test configure with random strategy."""
        ape_tool.configure({"strategy": "random"})
        assert ape_tool.config["strategy"] == "random"

    def test_configure_custom_running_minutes(self, ape_tool):
        """Test configure with custom running minutes."""
        ape_tool.configure({"strategy": "sata", "running_minutes": 15})
        assert ape_tool.config["running_minutes"] == 15

    def test_configure_custom_device_serial(self, ape_tool):
        """Test configure with custom device serial."""
        ape_tool.configure({"strategy": "sata", "device_serial": "emulator-5556"})
        assert ape_tool.config["device_serial"] == "emulator-5556"

    def test_configure_default_values(self, ape_tool):
        """Test configure sets default values."""
        ape_tool.configure({"strategy": "sata"})
        assert ape_tool.config["running_minutes"] == 5
        assert ape_tool.config["device_serial"] == "emulator-5554"
        assert ape_tool.config["debug_mode"] is True


# ---------------------------------------------------------------------------
# Tests: _resolve_ape_jar_path()
# ---------------------------------------------------------------------------


class TestResolveApeJarPath:
    """Test _resolve_ape_jar_path() resolution."""

    def test_resolve_jar_uses_jar_resolver(self, ape_tool):
        """Test that _resolve_ape_jar_path uses JarResolver."""
        ape_tool.configure({"strategy": "sata"})
        ape_tool.jar_resolver.resolve_jar_path = MagicMock(
            return_value="/path/to/ape.jar"
        )

        result = ape_tool._resolve_ape_jar_path()

        ape_tool.jar_resolver.resolve_jar_path.assert_called_once()
        assert result == "/path/to/ape.jar"

    def test_resolve_jar_raises_when_not_found(self, ape_tool):
        """Test that _resolve_ape_jar_path raises when jar not found."""
        ape_tool.configure({"strategy": "sata"})
        ape_tool.jar_resolver.resolve_jar_path = MagicMock(
            side_effect=FileNotFoundError()
        )

        with pytest.raises(RVToolExecutionError, match="APE jar.*not found"):
            ape_tool._resolve_ape_jar_path()

    def test_resolve_jar_uses_configured_path(self, ape_tool):
        """Test that configured path is used if provided."""
        ape_tool.configure({"strategy": "sata", "ape_jar_path": "/custom/ape.jar"})
        ape_tool.jar_resolver.resolve_jar_path = MagicMock(
            return_value="/custom/ape.jar"
        )

        result = ape_tool._resolve_ape_jar_path()

        assert result == "/custom/ape.jar"


# ---------------------------------------------------------------------------
# Tests: _build_ape_shell_command()
# ---------------------------------------------------------------------------


class TestBuildApeShellCommand:
    """Test _build_ape_shell_command() with correct CLI flags."""

    def test_build_command_uses_adb(self, ape_tool, mock_app):
        """Test command uses adb as base."""
        ape_tool.configure({"strategy": "sata"})
        cmd = ape_tool._build_ape_shell_command(mock_app, 5, 300)

        assert cmd.command == "adb"

    def test_build_command_includes_device_serial(self, ape_tool, mock_app):
        """Test command includes device serial."""
        ape_tool.configure({"strategy": "sata", "device_serial": "emulator-5556"})
        cmd = ape_tool._build_ape_shell_command(mock_app, 5, 300)

        assert "-s" in cmd.args
        assert "emulator-5556" in cmd.args

    def test_build_command_includes_package_name(self, ape_tool, mock_app):
        """Test command includes package name."""
        ape_tool.configure({"strategy": "sata"})
        cmd = ape_tool._build_ape_shell_command(mock_app, 5, 300)

        assert "-p" in cmd.args
        assert "com.test.app" in cmd.args

    def test_build_command_includes_running_minutes(self, ape_tool, mock_app):
        """Test command includes running minutes."""
        ape_tool.configure({"strategy": "sata"})
        cmd = ape_tool._build_ape_shell_command(mock_app, 10, 600)

        assert "--running-minutes" in cmd.args
        assert "10" in cmd.args

    def test_build_command_includes_strategy(self, ape_tool, mock_app):
        """Test command includes strategy flag."""
        ape_tool.configure({"strategy": "bfs"})
        cmd = ape_tool._build_ape_shell_command(mock_app, 5, 300)

        assert "bfs" in cmd.args

    def test_build_command_includes_ape_flag(self, ape_tool, mock_app):
        """Test command includes --ape flag."""
        ape_tool.configure({"strategy": "dfs"})
        cmd = ape_tool._build_ape_shell_command(mock_app, 5, 300)

        assert "--ape" in cmd.args

    def test_build_command_includes_classpath(self, ape_tool, mock_app):
        """Test command includes CLASSPATH env var."""
        ape_tool.configure({"strategy": "sata"})
        cmd = ape_tool._build_ape_shell_command(mock_app, 5, 300)

        assert "CLASSPATH=/data/local/tmp/ape.jar" in cmd.args

    def test_build_command_includes_app_process(self, ape_tool, mock_app):
        """Test command includes app_process."""
        ape_tool.configure({"strategy": "sata"})
        cmd = ape_tool._build_ape_shell_command(mock_app, 5, 300)

        assert "/system/bin/app_process" in cmd.args

    def test_build_command_timeout(self, ape_tool, mock_app):
        """Test command timeout is set correctly."""
        ape_tool.configure({"strategy": "sata"})
        cmd = ape_tool._build_ape_shell_command(mock_app, 5, 600)

        assert cmd.timeout == 600


# ---------------------------------------------------------------------------
# Tests: get_tool_info()
# ---------------------------------------------------------------------------


class TestGetToolInfo:
    """Test get_tool_info() retrieval."""

    def test_get_tool_info_returns_base_info(self, ape_tool):
        """Test get_tool_info returns base tool information."""
        ape_tool.configure({"strategy": "sata"})
        info = ape_tool.get_tool_info()

        assert "name" in info

    def test_get_tool_info_returns_tool_spec(self, ape_tool):
        """Test get_tool_info returns tool_spec."""
        ape_tool.configure({"strategy": "sata"})
        info = ape_tool.get_tool_info()

        assert "tool_spec" in info

    def test_get_tool_info_returns_available_strategies(self, ape_tool):
        """Test get_tool_info returns available_strategies."""
        ape_tool.configure({"strategy": "sata"})
        info = ape_tool.get_tool_info()

        assert "available_strategies" in info
        assert "sata" in info["available_strategies"]

    def test_get_tool_info_returns_current_strategy(self, ape_tool):
        """Test get_tool_info returns current_strategy."""
        ape_tool.configure({"strategy": "bfs"})
        info = ape_tool.get_tool_info()

        assert "current_strategy" in info
        assert info["current_strategy"] == "bfs"

    def test_get_tool_info_returns_running_minutes(self, ape_tool):
        """Test get_tool_info returns current_running_minutes."""
        ape_tool.configure({"strategy": "sata", "running_minutes": 15})
        info = ape_tool.get_tool_info()

        assert "current_running_minutes" in info
        assert info["current_running_minutes"] == 15
