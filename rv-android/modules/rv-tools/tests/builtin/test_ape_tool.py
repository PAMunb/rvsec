"""
Tests for APETool - CEGAR-based model abstraction testing tool.

Tests cover:
- Tool specification and available strategies
- configure() with strategy validation
- _resolve_ape_jar_path() resolution
- _build_ape_shell_command() with correct CLI flags
- execute_tool_specific_logic(): teardown grace, elapsed-time completion rule,
  ape.properties push (INV-TOOL-27, INV-TOOL-28, INV-TOOL-29)
- get_available_strategies() and get_tool_info()
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from rv_android_core.commands.command import Command
from rv_android_core.constants import TOOL_TEARDOWN_GRACE_S
from rv_android_core.util.error.exceptions import (
    ConfigurationError,
    RVCommandTimeoutError,
    RVToolExecutionError,
    RVToolTimeoutError,
)

from rv_tools.builtin.ape import tool as ape_module
from rv_tools.builtin.ape.tool import APE_PROPERTIES_CONTENT, APETool

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
        """The command timeout is the budget plus the shared teardown grace."""
        ape_tool.configure({"strategy": "sata"})
        cmd = ape_tool._build_ape_shell_command(mock_app, 10, 600)

        assert cmd.timeout == 600 + TOOL_TEARDOWN_GRACE_S


# ---------------------------------------------------------------------------
# Tests: execute_tool_specific_logic()
# ---------------------------------------------------------------------------


class _FakeResult:
    """The part of CommandResult the tool reads."""

    def __init__(self, code: int):
        self.code = code

    def is_failure(self) -> bool:
        return self.code != 0

    def has_error_output(self) -> bool:
        return False


class _Device:
    """Records each Command.invoke and answers per command kind.

    A push is recognised by its ``push`` argument; anything else is the APE run.
    The pushed properties file is read at invoke time, since the tool removes it
    after the push.
    """

    def __init__(self, ape_code=0, ape_raises=None, properties_push_code=0):
        self.ape_code = ape_code
        self.ape_raises = ape_raises
        self.properties_push_code = properties_push_code
        self.calls = []
        self.pushed_properties = None

    def invoke(self, command, stdout=None, stderr=None, stdin=None):
        self.calls.append(command)
        if "push" in command.args:
            if command.args[-1] == "/data/local/tmp/ape.properties":
                with open(command.args[-2]) as f:
                    self.pushed_properties = f.read()
                return _FakeResult(self.properties_push_code)
            return _FakeResult(0)
        if self.ape_raises is not None:
            raise self.ape_raises
        return _FakeResult(self.ape_code)

    def ape_calls(self):
        return [c for c in self.calls if "push" not in c.args]


@pytest.fixture
def run_ape(ape_tool, mock_app, tmp_path, monkeypatch):
    """Run execute_tool_specific_logic against a fake device and clock.

    Returns a function taking the fake device and the elapsed seconds of the APE
    command; it returns the device so the test can inspect what ran.
    """
    ape_tool.configure({"strategy": "sata", "device_serial": "emulator-5554"})
    ape_tool.jar_resolver.resolve_jar_path = MagicMock(return_value="/x/ape.jar")

    task = MagicMock()
    task.config.timeout = 300
    task.result.trace_file = str(tmp_path / "trace.txt")

    def run(device, elapsed=310.0):
        clock = iter([1000.0, 1000.0 + elapsed])
        monkeypatch.setattr(ape_module.time, "monotonic", lambda: next(clock))
        monkeypatch.setattr(
            Command,
            "invoke",
            lambda self, stdout=None, stderr=None, stdin=None: device.invoke(
                self, stdout, stderr, stdin
            ),
        )
        ape_tool.execute_tool_specific_logic(task, mock_app)
        return device

    run.task = task
    return run


class TestExecuteToolSpecificLogic:
    """Grace, completion rule and capture properties of the ape built-in."""

    def test_command_timeout_carries_the_grace(self, run_ape):
        """A 300 s budget runs --running-minutes 5 under a 345 s timeout."""
        device = run_ape(_Device())

        [ape_cmd] = device.ape_calls()
        assert ape_cmd.timeout == 345
        index = ape_cmd.args.index("--running-minutes")
        assert ape_cmd.args[index + 1] == "5"

    def test_non_zero_exit_after_full_budget_completes(self, run_ape):
        """Exit 1 after 310 s of a 300 s budget is a completed run."""
        run_ape(_Device(ape_code=1), elapsed=310.0)

    def test_early_return_raises_whatever_the_exit_code(self, run_ape):
        """Exit 0 after 120 s of a 300 s budget is a truncated run."""
        with pytest.raises(RVToolExecutionError) as excinfo:
            run_ape(_Device(ape_code=0), elapsed=120.0)

        assert "120" in str(excinfo.value)
        assert "300" in str(excinfo.value)

    def test_return_just_above_the_floor_completes(self, run_ape):
        """256 s of a 300 s budget is above the 255 s floor."""
        run_ape(_Device(ape_code=0), elapsed=256.0)

    def test_host_timeout_is_a_normal_end(self, ape_tool, run_ape, mock_app):
        """The command timeout reaches execute() and becomes RVToolTimeoutError."""
        timeout = RVCommandTimeoutError("timed out", timeout_seconds=345)

        with pytest.raises(RVCommandTimeoutError):
            run_ape(_Device(ape_raises=timeout))

        with pytest.raises(RVToolTimeoutError):
            ape_tool.execute(run_ape.task, mock_app)

    def test_properties_pushed_before_ape_with_exact_content(self, run_ape):
        """ape.properties goes to the device before the APE command runs."""
        device = run_ape(_Device())

        properties_index = next(
            i
            for i, c in enumerate(device.calls)
            if c.args[-1:] == ["/data/local/tmp/ape.properties"]
        )
        ape_index = device.calls.index(device.ape_calls()[0])
        assert properties_index < ape_index

        push = device.calls[properties_index]
        assert push.command == "adb"
        assert push.args[:3] == ["-s", "emulator-5554", "push"]
        assert push.timeout == 60
        assert device.pushed_properties == (
            "ape.takeScreenshotForEveryStep=false\n"
            "ape.saveGUITreeToXmlEveryStep=false\n"
            "ape.takeScreenshotForNewState=true\n"
        )
        assert device.pushed_properties == APE_PROPERTIES_CONTENT
        assert not os.path.exists(push.args[-2])

    def test_failed_properties_push_raises_and_ape_never_starts(self, run_ape):
        """A failed push stops the run before APE."""
        device = _Device(properties_push_code=1)

        with pytest.raises(RVToolExecutionError, match="APE properties"):
            run_ape(device)

        assert device.ape_calls() == []


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
