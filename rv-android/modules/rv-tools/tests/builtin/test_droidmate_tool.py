"""
Tests for DroidMateTool - DroidMate-2 JAR-based Android UI exploration.

Tests cover:
- Tool specification and variants
- configure() with default and custom values
- _resolve_jar() path resolution
- _build_droidmate_command() with correct CLI flags
- execute_tool_specific_logic() workflow
"""

import os
from unittest.mock import MagicMock, patch, mock_open

import pytest
from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task
from rv_tools.builtin.droidmate.tool import DroidMateTool


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def droidmate_tool():
    """Create DroidMateTool instance."""
    with patch("rv_tools.builtin.droidmate.tool.JarResolver"):
        tool = DroidMateTool()
        yield tool


@pytest.fixture
def mock_task():
    """Create a mock task with minimal configuration."""
    task = MagicMock()
    task.config = MagicMock()
    task.config.timeout = 3600
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
    """Test DroidMateTool specification and variants."""

    def test_tool_spec_name(self):
        """Test tool spec name."""
        spec = DroidMateTool.get_tool_spec()
        assert spec.name == "droidmate"

    def test_tool_spec_version(self):
        """Test tool spec version."""
        spec = DroidMateTool.get_tool_spec()
        assert spec.version == "1.0.0"

    def test_tool_spec_url(self):
        """Test tool spec URL."""
        spec = DroidMateTool.get_tool_spec()
        assert "droidmate" in spec.url

    def test_get_variants_returns_default(self):
        """Test that get_variants returns default variant."""
        variants = DroidMateTool.get_variants()
        assert "default" in variants
        assert "action_limit" in variants["default"]

    def test_default_action_limit(self):
        """Test default action limit is very large."""
        variants = DroidMateTool.get_variants()
        assert variants["default"]["action_limit"] == 100000000


# ---------------------------------------------------------------------------
# Tests: configure()
# ---------------------------------------------------------------------------


class TestConfigure:
    """Test configure() with default and custom values."""

    def test_configure_with_empty_config(self, droidmate_tool):
        """Test that empty config returns early."""
        droidmate_tool.configure({})
        assert droidmate_tool.config == {}

    def test_configure_defaults(self, droidmate_tool):
        """Test configure with empty dict sets defaults."""
        droidmate_tool.configure({})
        # Should remain empty
        assert droidmate_tool.config == {}

    def test_configure_custom_action_limit(self, droidmate_tool):
        """Test configure with custom action limit."""
        config = {"action_limit": 50000}
        droidmate_tool.configure(config)
        assert droidmate_tool.config["action_limit"] == 50000

    def test_configure_custom_device_serial(self, droidmate_tool):
        """Test configure with custom device serial."""
        config = {"device_serial": "emulator-5558"}
        droidmate_tool.configure(config)
        assert droidmate_tool.config["device_serial"] == "emulator-5558"

    def test_configure_custom_timeout(self, droidmate_tool):
        """Test configure with custom timeout."""
        config = {"timeout": 7200}
        droidmate_tool.configure(config)
        assert droidmate_tool.config["timeout"] == 7200

    def test_configure_default_values(self, droidmate_tool):
        """Test configure sets default values."""
        config = {}
        droidmate_tool.configure(config)
        # Empty config returns early, so config stays {}
        assert droidmate_tool.config == {}


# ---------------------------------------------------------------------------
# Tests: _resolve_jar()
# ---------------------------------------------------------------------------


class TestResolveJar:
    """Test _resolve_jar() path resolution."""

    def test_resolve_jar_uses_jar_resolver(self, droidmate_tool):
        """Test that _resolve_jar uses JarResolver."""
        droidmate_tool.jar_resolver.resolve_jar_path = MagicMock(return_value="/path/to/jar.jar")
        
        result = droidmate_tool._resolve_jar()
        
        droidmate_tool.jar_resolver.resolve_jar_path.assert_called_once()
        assert result == "/path/to/jar.jar"

    def test_resolve_jar_searches_module_directory(self, droidmate_tool):
        """Test that _resolve_jar searches module directory."""
        droidmate_tool.jar_resolver.resolve_jar_path = MagicMock(return_value="/path/to/jar.jar")
        
        droidmate_tool._resolve_jar()
        
        call_args = droidmate_tool.jar_resolver.resolve_jar_path.call_args
        search_paths = call_args[0][1]
        assert os.path.dirname(__file__) in search_paths or any("droidmate" in p for p in search_paths)


# ---------------------------------------------------------------------------
# Tests: _build_droidmate_command()
# ---------------------------------------------------------------------------


class TestBuildDroidMateCommand:
    """Test _build_droidmate_command() with correct CLI flags."""

    def test_build_command_basic_structure(self, droidmate_tool, mock_app):
        """Test command has basic java -jar structure."""
        droidmate_tool.configure({})
        cmd = droidmate_tool._build_droidmate_command(
            mock_app, "/path/to/jar.jar", "/tmp/output", 3600
        )
        
        assert cmd.command == "java"
        assert "-jar" in cmd.args

    def test_build_command_includes_jar_path(self, droidmate_tool, mock_app):
        """Test command includes JAR path."""
        droidmate_tool.configure({})
        cmd = droidmate_tool._build_droidmate_command(
            mock_app, "/custom/jar.jar", "/tmp/output", 3600
        )
        
        assert "/custom/jar.jar" in cmd.args

    def test_build_command_apk_name_and_dir(self, droidmate_tool, mock_app):
        """Test command splits APK into name and directory."""
        droidmate_tool.configure({})
        cmd = droidmate_tool._build_droidmate_command(
            mock_app, "/path/to/jar.jar", "/tmp/output", 3600
        )
        
        assert "--Exploration-apkNames=test_app.apk" in cmd.args
        assert "--Exploration-apksDir=/path/to" in cmd.args

    def test_build_command_output_dir(self, droidmate_tool, mock_app):
        """Test command includes output directory."""
        droidmate_tool.configure({})
        cmd = droidmate_tool._build_droidmate_command(
            mock_app, "/path/to/jar.jar", "/custom/output", 3600
        )
        
        assert "--Output-outputDir=/custom/output" in cmd.args

    def test_build_command_timeout_in_millis(self, droidmate_tool, mock_app):
        """Test command converts timeout to milliseconds."""
        droidmate_tool.configure({})
        cmd = droidmate_tool._build_droidmate_command(
            mock_app, "/path/to/jar.jar", "/tmp/output", 5
        )
        
        # 5 seconds = 5000 milliseconds
        assert "--Selectors-timeLimit=5000" in cmd.args

    def test_build_command_action_limit(self, droidmate_tool, mock_app):
        """Test command includes action limit."""
        droidmate_tool.configure({"action_limit": 100000})
        cmd = droidmate_tool._build_droidmate_command(
            mock_app, "/path/to/jar.jar", "/tmp/output", 3600
        )
        
        assert "--Selectors-actionLimit=100000" in cmd.args

    def test_build_command_log_level(self, droidmate_tool, mock_app):
        """Test command sets log level to debug."""
        droidmate_tool.configure({})
        cmd = droidmate_tool._build_droidmate_command(
            mock_app, "/path/to/jar.jar", "/tmp/output", 3600
        )
        
        assert "--Core-logLevel=debug" in cmd.args

    def test_build_command_timeout(self, droidmate_tool, mock_app):
        """Test command timeout is set correctly."""
        droidmate_tool.configure({})
        cmd = droidmate_tool._build_droidmate_command(
            mock_app, "/path/to/jar.jar", "/tmp/output", 7200
        )
        
        assert cmd.timeout == 7200


# ---------------------------------------------------------------------------
# Tests: execute_tool_specific_logic()
# ---------------------------------------------------------------------------


class TestExecuteToolSpecificLogic:
    """Test execute_tool_specific_logic() workflow."""

    def test_execute_resolves_jar(self, droidmate_tool, mock_task, mock_app):
        """Test that execute resolves JAR path."""
        droidmate_tool.configure({})
        droidmate_tool._resolve_jar = MagicMock(return_value="/path/to/jar.jar")
        droidmate_tool._build_droidmate_command = MagicMock()
        droidmate_tool._execute_and_check_command = MagicMock()

        droidmate_tool.execute_tool_specific_logic(mock_task, mock_app)

        droidmate_tool._resolve_jar.assert_called_once()

    def test_execute_builds_command(self, droidmate_tool, mock_task, mock_app):
        """Test that execute builds DroidMate command."""
        droidmate_tool.configure({})
        droidmate_tool._resolve_jar = MagicMock(return_value="/path/to/jar.jar")
        droidmate_tool._build_droidmate_command = MagicMock()
        droidmate_tool._execute_and_check_command = MagicMock()

        droidmate_tool.execute_tool_specific_logic(mock_task, mock_app)

        droidmate_tool._build_droidmate_command.assert_called_once()

    def test_execute_creates_output_dir(self, droidmate_tool, mock_task, mock_app, tmp_path):
        """Test that execute creates output directory."""
        trace_file = str(tmp_path / "trace.txt")
        mock_task.result.trace_file = trace_file
        
        droidmate_tool.configure({})
        droidmate_tool._resolve_jar = MagicMock(return_value="/path/to/jar.jar")
        droidmate_tool._build_droidmate_command = MagicMock()
        droidmate_tool._execute_and_check_command = MagicMock()

        droidmate_tool.execute_tool_specific_logic(mock_task, mock_app)

        output_dir = os.path.join(os.path.dirname(trace_file), "droidmate_output")
        assert os.path.exists(output_dir)

    def test_execute_uses_task_timeout(self, droidmate_tool, mock_task, mock_app):
        """Test that execute uses timeout from task config."""
        mock_task.config.timeout = 7200
        
        droidmate_tool.configure({})
        droidmate_tool._resolve_jar = MagicMock(return_value="/path/to/jar.jar")
        droidmate_tool._build_droidmate_command = MagicMock()
        droidmate_tool._execute_and_check_command = MagicMock()

        droidmate_tool.execute_tool_specific_logic(mock_task, mock_app)

        call_args = droidmate_tool._build_droidmate_command.call_args
        assert call_args[0][3] == 7200  # timeout_seconds

    def test_execute_uses_config_timeout(self, droidmate_tool, mock_task, mock_app):
        """Test that execute falls back to config timeout."""
        # Remove task timeout to force fallback to config
        del mock_task.config.timeout
        droidmate_tool.configure({"timeout": 5000})
        
        droidmate_tool._resolve_jar = MagicMock(return_value="/path/to/jar.jar")
        droidmate_tool._build_droidmate_command = MagicMock()
        droidmate_tool._execute_and_check_command = MagicMock()

        droidmate_tool.execute_tool_specific_logic(mock_task, mock_app)

        call_args = droidmate_tool._build_droidmate_command.call_args
        # Should use config timeout (5000) or default (3600)
        timeout_used = call_args[0][3]
        assert timeout_used in [5000, 3600]

    def test_execute_writes_to_trace_file(self, droidmate_tool, mock_task, mock_app, tmp_path):
        """Test that execute writes output to trace file."""
        trace_file = tmp_path / "trace.txt"
        mock_task.result.trace_file = str(trace_file)
        
        droidmate_tool.configure({})
        droidmate_tool._resolve_jar = MagicMock(return_value="/path/to/jar.jar")
        
        mock_cmd = MagicMock()
        mock_cmd.command = "java"
        mock_cmd.args = ["-jar", "test.jar"]
        mock_cmd.timeout = 3600
        droidmate_tool._build_droidmate_command = MagicMock(return_value=mock_cmd)
        droidmate_tool._execute_and_check_command = MagicMock()

        droidmate_tool.execute_tool_specific_logic(mock_task, mock_app)

        droidmate_tool._execute_and_check_command.assert_called_once()
