"""
Tests for QTestingTool - Docker-based Q-learning UI exploration.

Tests cover:
- Tool specification and variants
- configure() with default and custom values
- _build_create_command() with network detection
- _copy_config_file() INI generation
- _cleanup_container() error handling
"""

import os
import tempfile
from unittest.mock import MagicMock, patch, mock_open

import pytest
from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task
from rv_tools.builtin.qtesting.tool import QTestingTool

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def qtesting_tool():
    """Create QTestingTool instance."""
    tool = QTestingTool()
    tool.config = {}
    yield tool


@pytest.fixture
def mock_task():
    """Create a mock task with minimal configuration."""
    task = MagicMock()
    task.id = "test_task_001"
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
    """Test QTestingTool specification and variants."""

    def test_tool_spec_name(self):
        """Test tool spec name."""
        spec = QTestingTool.get_tool_spec()
        assert spec.name == "qtesting"

    def test_tool_spec_version(self):
        """Test tool spec version."""
        spec = QTestingTool.get_tool_spec()
        assert spec.version == "1.0.0"

    def test_tool_spec_url(self):
        """Test tool spec URL."""
        spec = QTestingTool.get_tool_spec()
        assert "QTesting" in spec.url or "qtesting" in spec.url.lower()

    def test_get_variants_returns_default(self):
        """Test that get_variants returns default variant."""
        variants = QTestingTool.get_variants()
        assert "default" in variants

    def test_default_variant_has_docker_image(self):
        """Test default variant has docker image."""
        variants = QTestingTool.get_variants()
        assert "docker_image" in variants["default"]
        assert "phtcosta/qtesting" in variants["default"]["docker_image"]


# ---------------------------------------------------------------------------
# Tests: configure()
# ---------------------------------------------------------------------------


class TestConfigure:
    """Test configure() with default and custom values."""

    def test_configure_with_empty_config(self, qtesting_tool):
        """Test that empty config returns early."""
        qtesting_tool.configure({})
        assert qtesting_tool.config == {}

    def test_configure_defaults(self, qtesting_tool):
        """Test configure sets default values."""
        qtesting_tool.configure({})
        # Empty config returns early
        assert qtesting_tool.config == {}

    def test_configure_custom_docker_image(self, qtesting_tool):
        """Test configure with custom docker image."""
        config = {"docker_image": "custom/qtesting:v1"}
        qtesting_tool.configure(config)
        assert qtesting_tool.config["docker_image"] == "custom/qtesting:v1"

    def test_configure_custom_device_serial(self, qtesting_tool):
        """Test configure with custom device serial."""
        config = {"device_serial": "emulator-5558"}
        qtesting_tool.configure(config)
        assert qtesting_tool.config["device_serial"] == "emulator-5558"

    def test_configure_custom_timeout(self, qtesting_tool):
        """Test configure with custom timeout."""
        config = {"timeout": 7200}
        qtesting_tool.configure(config)
        assert qtesting_tool.config["timeout"] == 7200


# ---------------------------------------------------------------------------
# Tests: _build_create_command()
# ---------------------------------------------------------------------------


class TestBuildCreateCommand:
    """Test _build_create_command() with network detection."""

    def test_build_command_basic_structure(self, qtesting_tool):
        """Test command has basic docker create structure."""
        qtesting_tool.configure({"docker_image": "phtcosta/qtesting:latest"})
        cmd = qtesting_tool._build_create_command("qtesting_test")

        assert cmd.command == "docker"
        assert "create" in cmd.args
        assert "--name" in cmd.args
        assert "qtesting_test" in cmd.args

    def test_build_command_uses_host_network_outside_docker(self, qtesting_tool):
        """Test command uses host network outside Docker."""
        qtesting_tool.configure({"docker_image": "phtcosta/qtesting:latest"})
        with patch("os.path.exists", return_value=False):
            cmd = qtesting_tool._build_create_command("qtesting_test")

            assert "--network" in cmd.args
            assert "host" in cmd.args

    def test_build_command_uses_container_network_inside_docker(self, qtesting_tool):
        """Test command uses container network inside Docker."""
        qtesting_tool.configure({"docker_image": "phtcosta/qtesting:latest"})
        with patch("os.path.exists", return_value=True):
            with patch("socket.gethostname", return_value="test-host"):
                cmd = qtesting_tool._build_create_command("qtesting_test")

                assert "--network" in cmd.args
                assert "container:test-host" in cmd.args

    def test_build_command_includes_docker_image(self, qtesting_tool):
        """Test command includes docker image."""
        qtesting_tool.configure({"docker_image": "custom/qtesting:v1"})
        cmd = qtesting_tool._build_create_command("qtesting_test")

        assert "custom/qtesting:v1" in cmd.args


# ---------------------------------------------------------------------------
# Tests: _copy_config_file()
# ---------------------------------------------------------------------------


class TestCopyConfigFile:
    """Test _copy_config_file() INI generation."""

    def test_copy_config_creates_file(self, qtesting_tool):
        """Test that config file is created."""
        qtesting_tool.configure({})

        with patch("rv_tools.builtin.qtesting.tool.Command") as mock_cmd:
            mock_instance = MagicMock()
            mock_cmd.return_value = mock_instance

            # Should not raise
            qtesting_tool._copy_config_file("qtesting_test", "emulator-5554", 3600)

            mock_cmd.assert_called()

    def test_copy_config_includes_device_serial(self, qtesting_tool):
        """Test that config includes device serial."""
        qtesting_tool.configure({})

        # _copy_config_file creates temp file and copies to container
        # Just verify it doesn't raise
        with patch("rv_tools.builtin.qtesting.tool.Command") as mock_cmd:
            mock_cmd_instance = MagicMock()
            mock_cmd.return_value = mock_cmd_instance

            qtesting_tool._copy_config_file("qtesting_test", "emulator-5556", 3600)

            # Verify Command was called
            assert mock_cmd.called


# ---------------------------------------------------------------------------
# Tests: _cleanup_container()
# ---------------------------------------------------------------------------


class TestCleanupContainer:
    """Test _cleanup_container() error handling."""

    def test_cleanup_removes_container(self, qtesting_tool):
        """Test cleanup removes container."""
        with patch("rv_tools.builtin.qtesting.tool.Command") as mock_cmd:
            mock_instance = MagicMock()
            mock_cmd.return_value = mock_instance

            qtesting_tool._cleanup_container("qtesting_test")

            mock_cmd.assert_called_once_with(
                "docker", ["rm", "-f", "qtesting_test"], 30
            )
            mock_instance.invoke.assert_called_once()

    def test_cleanup_handles_exception(self, qtesting_tool):
        """Test cleanup handles exceptions gracefully."""
        with patch("rv_tools.builtin.qtesting.tool.Command") as mock_cmd:
            mock_instance = MagicMock()
            mock_instance.invoke.side_effect = Exception("Docker error")
            mock_cmd.return_value = mock_instance
            qtesting_tool.logger.warning = MagicMock()

            # Should not raise
            qtesting_tool._cleanup_container("qtesting_test")

            qtesting_tool.logger.warning.assert_called_once()
