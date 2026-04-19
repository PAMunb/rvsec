"""
Tests for MonkeyTool - Android Monkey random event generation.

Tests cover:
- Tool specification and variants
- configure() with event count, seed, throttle, verbosity, boolean flags, percentages
- _build_monkey_command() with correct CLI flags
- get_supported_event_types() and get_tool_info()
"""

from unittest.mock import MagicMock, patch

import pytest
from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task
from rv_tools.builtin.monkey.tool import MonkeyTool


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def monkey_tool():
    """Create MonkeyTool instance."""
    tool = MonkeyTool()
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
    """Test MonkeyTool specification and variants."""

    def test_tool_spec_name(self):
        """Test tool spec name."""
        spec = MonkeyTool.get_tool_spec()
        assert spec.name == "monkey"

    def test_tool_spec_version(self):
        """Test tool spec version."""
        spec = MonkeyTool.get_tool_spec()
        assert spec.version == "1.0.0"

    def test_get_variants_returns_all(self):
        """Test that get_variants returns all variants."""
        variants = MonkeyTool.get_variants()
        assert "default" in variants
        assert "fast" in variants
        assert "stress" in variants

    def test_default_variant_config(self):
        """Test default variant configuration."""
        variants = MonkeyTool.get_variants()
        assert variants["default"]["event_count"] == 1000

    def test_fast_variant_config(self):
        """Test fast variant configuration."""
        variants = MonkeyTool.get_variants()
        assert variants["fast"]["event_count"] == 500
        assert variants["fast"]["seed"] == 12345

    def test_stress_variant_config(self):
        """Test stress variant configuration."""
        variants = MonkeyTool.get_variants()
        assert variants["stress"]["event_count"] == 10000
        assert variants["stress"]["verbosity"] == 3


# ---------------------------------------------------------------------------
# Tests: configure()
# ---------------------------------------------------------------------------


class TestConfigure:
    """Test configure() with various parameters."""

    def test_configure_empty_config(self, monkey_tool):
        """Test that empty config returns early."""
        initial_count = monkey_tool.config["event_count"]
        monkey_tool.configure({})
        assert monkey_tool.config["event_count"] == initial_count

    def test_configure_event_count(self, monkey_tool):
        """Test configure with custom event count."""
        monkey_tool.configure({"event_count": 5000})
        assert monkey_tool.config["event_count"] == 5000

    def test_configure_invalid_event_count(self, monkey_tool):
        """Test configure with invalid event count."""
        monkey_tool.configure({"event_count": -1})
        # Should remain unchanged
        assert monkey_tool.config["event_count"] == 1_000_000_000

    def test_configure_seed(self, monkey_tool):
        """Test configure with custom seed."""
        monkey_tool.configure({"seed": 12345})
        assert monkey_tool.config["seed"] == 12345

    def test_configure_throttle(self, monkey_tool):
        """Test configure with custom throttle."""
        monkey_tool.configure({"throttle": 100})
        assert monkey_tool.config["throttle"] == 100

    def test_configure_device_id(self, monkey_tool):
        """Test configure with custom device ID."""
        monkey_tool.configure({"device_id": "emulator-5556"})
        assert monkey_tool.config["device_id"] == "emulator-5556"

    def test_configure_verbosity(self, monkey_tool):
        """Test configure with custom verbosity."""
        monkey_tool.configure({"verbosity": 3})
        assert monkey_tool.config["verbosity"] == 3

    def test_configure_invalid_verbosity(self, monkey_tool):
        """Test configure with invalid verbosity."""
        monkey_tool.configure({"verbosity": 5})
        # Should remain at default
        assert monkey_tool.config["verbosity"] == 2

    def test_configure_boolean_flags(self, monkey_tool):
        """Test configure with boolean flags."""
        monkey_tool.configure({
            "ignore_crashes": True,
            "ignore_timeouts": True,
        })
        assert monkey_tool.config["ignore_crashes"] is True
        assert monkey_tool.config["ignore_timeouts"] is True

    def test_configure_event_percentages(self, monkey_tool):
        """Test configure with event percentages."""
        monkey_tool.configure({
            "event_percentages": {"touch": 50.0, "motion": 30.0}
        })
        assert monkey_tool.config["event_percentages"]["touch"] == 50.0
        assert monkey_tool.config["event_percentages"]["motion"] == 30.0


# ---------------------------------------------------------------------------
# Tests: _build_monkey_command()
# ---------------------------------------------------------------------------


class TestBuildMonkeyCommand:
    """Test _build_monkey_command() with correct CLI flags."""

    def test_build_command_uses_adb(self, monkey_tool, mock_app):
        """Test command uses adb as base."""
        cmd = monkey_tool._build_monkey_command(mock_app, 300)

        assert cmd.command == "adb"

    def test_build_command_includes_device_id(self, monkey_tool, mock_app):
        """Test command includes device ID."""
        monkey_tool.configure({"device_id": "emulator-5556"})
        cmd = monkey_tool._build_monkey_command(mock_app, 300)

        assert "-s" in cmd.args
        assert "emulator-5556" in cmd.args

    def test_build_command_includes_shell_monkey(self, monkey_tool, mock_app):
        """Test command includes shell monkey."""
        cmd = monkey_tool._build_monkey_command(mock_app, 300)

        assert "shell" in cmd.args
        assert "monkey" in cmd.args

    def test_build_command_includes_package_name(self, monkey_tool, mock_app):
        """Test command includes package name."""
        cmd = monkey_tool._build_monkey_command(mock_app, 300)

        assert "-p" in cmd.args
        assert "com.test.app" in cmd.args

    def test_build_command_includes_verbosity(self, monkey_tool, mock_app):
        """Test command includes verbosity flags."""
        monkey_tool.configure({"verbosity": 3})
        cmd = monkey_tool._build_monkey_command(mock_app, 300)

        # Should have 3 -v flags
        assert cmd.args.count("-v") == 3

    def test_build_command_includes_ignore_crashes(self, monkey_tool, mock_app):
        """Test command includes ignore-crashes flag."""
        monkey_tool.configure({"ignore_crashes": True})
        cmd = monkey_tool._build_monkey_command(mock_app, 300)

        assert "--ignore-crashes" in cmd.args

    def test_build_command_includes_ignore_timeouts(self, monkey_tool, mock_app):
        """Test command includes ignore-timeouts flag."""
        monkey_tool.configure({"ignore_timeouts": True})
        cmd = monkey_tool._build_monkey_command(mock_app, 300)

        assert "--ignore-timeouts" in cmd.args

    def test_build_command_always_includes_ignore_security(self, monkey_tool, mock_app):
        """Test command always includes ignore-security-exceptions."""
        cmd = monkey_tool._build_monkey_command(mock_app, 300)

        assert "--ignore-security-exceptions" in cmd.args

    def test_build_command_includes_throttle(self, monkey_tool, mock_app):
        """Test command includes throttle when set."""
        monkey_tool.configure({"throttle": 100})
        cmd = monkey_tool._build_monkey_command(mock_app, 300)

        assert "--throttle" in cmd.args
        assert "100" in cmd.args

    def test_build_command_includes_seed(self, monkey_tool, mock_app):
        """Test command includes seed when set."""
        monkey_tool.configure({"seed": 12345})
        cmd = monkey_tool._build_monkey_command(mock_app, 300)

        assert "-s" in cmd.args
        assert "12345" in cmd.args

    def test_build_command_includes_event_count(self, monkey_tool, mock_app):
        """Test command includes event count."""
        cmd = monkey_tool._build_monkey_command(mock_app, 300)

        assert "1000000000" in cmd.args

    def test_build_command_timeout(self, monkey_tool, mock_app):
        """Test command timeout is set correctly."""
        cmd = monkey_tool._build_monkey_command(mock_app, 600)

        assert cmd.timeout == 600


# ---------------------------------------------------------------------------
# Tests: get_supported_event_types() and get_tool_info()
# ---------------------------------------------------------------------------


class TestGetEventTypesAndToolInfo:
    """Test get_supported_event_types() and get_tool_info()."""

    def test_get_supported_event_types(self, monkey_tool):
        """Test get_supported_event_types returns all types."""
        types = monkey_tool.get_supported_event_types()
        assert "touch" in types
        assert "motion" in types
        assert "trackball" in types
        assert "syskeys" in types
        assert "nav" in types

    def test_get_tool_info_returns_base_info(self, monkey_tool):
        """Test get_tool_info returns base tool information."""
        info = monkey_tool.get_tool_info()
        assert "name" in info

    def test_get_tool_info_returns_tool_spec(self, monkey_tool):
        """Test get_tool_info returns tool_spec."""
        info = monkey_tool.get_tool_info()
        assert "tool_spec" in info

    def test_get_tool_info_returns_event_types(self, monkey_tool):
        """Test get_tool_info returns supported_event_types."""
        info = monkey_tool.get_tool_info()
        assert "supported_event_types" in info

    def test_get_tool_info_returns_event_count(self, monkey_tool):
        """Test get_tool_info returns current_event_count."""
        info = monkey_tool.get_tool_info()
        assert "current_event_count" in info
        assert info["current_event_count"] == 1_000_000_000
