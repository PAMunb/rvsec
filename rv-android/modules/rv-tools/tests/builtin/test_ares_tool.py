"""
Tests for AresTool - Docker-based ARES reinforcement learning exploration.

Tests cover:
- Tool specification and variants
- configure() with default and custom values
- _build_create_command() with network detection
- _cleanup_container() error handling
- Tool info retrieval
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task
from rv_tools.builtin.ares.tool import AresTool


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ares_tool():
    """Create AresTool instance."""
    tool = AresTool()
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
    """Test AresTool specification and variants."""

    def test_tool_spec_name(self):
        """Test tool spec name."""
        spec = AresTool.get_tool_spec()
        assert spec.name == "ares"

    def test_tool_spec_version(self):
        """Test tool spec version."""
        spec = AresTool.get_tool_spec()
        assert spec.version == "1.0.0"

    def test_tool_spec_url(self):
        """Test tool spec URL."""
        spec = AresTool.get_tool_spec()
        assert "ARES" in spec.url or "ares" in spec.url

    def test_get_variants_returns_default(self):
        """Test that get_variants returns default variant."""
        variants = AresTool.get_variants()
        assert "default" in variants

    def test_default_variant_has_docker_image(self):
        """Test default variant has docker image."""
        variants = AresTool.get_variants()
        assert "docker_image" in variants["default"]
        assert "phtcosta/ares" in variants["default"]["docker_image"]


# ---------------------------------------------------------------------------
# Tests: configure()
# ---------------------------------------------------------------------------


class TestConfigure:
    """Test configure() with default and custom values."""

    def test_configure_defaults(self, ares_tool):
        """Test configure with empty dict sets defaults."""
        ares_tool.configure({})
        assert ares_tool.config["docker_image"] == "phtcosta/ares:latest"
        assert ares_tool.config["device_serial"] == "emulator-5554"
        assert ares_tool.config["timeout"] == 600

    def test_configure_custom_docker_image(self, ares_tool):
        """Test configure with custom docker image."""
        config = {"docker_image": "custom/ares:v1"}
        ares_tool.configure(config)
        assert ares_tool.config["docker_image"] == "custom/ares:v1"

    def test_configure_custom_device_serial(self, ares_tool):
        """Test configure with custom device serial."""
        config = {"device_serial": "emulator-5558"}
        ares_tool.configure(config)
        assert ares_tool.config["device_serial"] == "emulator-5558"

    def test_configure_custom_timeout(self, ares_tool):
        """Test configure with custom timeout."""
        config = {"timeout": 1200}
        ares_tool.configure(config)
        assert ares_tool.config["timeout"] == 1200


# ---------------------------------------------------------------------------
# Tests: _build_create_command()
# ---------------------------------------------------------------------------


class TestBuildCreateCommand:
    """Test _build_create_command() with network detection."""

    def test_build_command_basic_structure(self, ares_tool):
        """Test command has basic docker create structure."""
        ares_tool.configure({})
        cmd = ares_tool._build_create_command("ares_test", 10)

        assert cmd.command == "docker"
        assert "create" in cmd.args
        assert "--name" in cmd.args
        assert "ares_test" in cmd.args

    def test_build_command_includes_env_vars(self, ares_tool):
        """Test command includes environment variables."""
        ares_tool.configure({"device_serial": "emulator-5556"})
        cmd = ares_tool._build_create_command("ares_test", 15)

        assert "-e" in cmd.args
        assert "EMUNAME=emulator-5556" in cmd.args
        assert "TIMEOUT_IN_MINUTES=15" in cmd.args

    def test_build_command_uses_host_network_outside_docker(self, ares_tool):
        """Test command uses host network outside Docker."""
        ares_tool.configure({})
        with patch("os.path.exists", return_value=False):
            cmd = ares_tool._build_create_command("ares_test", 10)

            assert "--network" in cmd.args
            assert "host" in cmd.args

    def test_build_command_uses_container_network_inside_docker(self, ares_tool):
        """Test command uses container network inside Docker."""
        ares_tool.configure({})
        with patch("os.path.exists", return_value=True):
            with patch("socket.gethostname", return_value="test-host"):
                cmd = ares_tool._build_create_command("ares_test", 10)

                assert "--network" in cmd.args
                assert "container:test-host" in cmd.args

    def test_build_command_includes_docker_image(self, ares_tool):
        """Test command includes docker image."""
        ares_tool.configure({"docker_image": "custom/ares:v1"})
        cmd = ares_tool._build_create_command("ares_test", 10)

        assert "custom/ares:v1" in cmd.args

    def test_build_command_default_serial(self, ares_tool):
        """Test command uses default serial when not configured."""
        ares_tool.configure({})
        cmd = ares_tool._build_create_command("ares_test", 10)

        assert "EMUNAME=emulator-5554" in cmd.args


# ---------------------------------------------------------------------------
# Tests: _cleanup_container()
# ---------------------------------------------------------------------------


class TestCleanupContainer:
    """Test _cleanup_container() error handling."""

    def test_cleanup_removes_container(self, ares_tool):
        """Test cleanup removes container."""
        with patch("rv_tools.builtin.ares.tool.Command") as mock_cmd:
            mock_instance = MagicMock()
            mock_cmd.return_value = mock_instance

            ares_tool._cleanup_container("ares_test")

            mock_cmd.assert_called_once_with(
                "docker", ["rm", "-f", "ares_test"], 30
            )
            mock_instance.invoke.assert_called_once()

    def test_cleanup_handles_exception(self, ares_tool):
        """Test cleanup handles exceptions gracefully."""
        with patch("rv_tools.builtin.ares.tool.Command") as mock_cmd:
            mock_instance = MagicMock()
            mock_instance.invoke.side_effect = Exception("Docker error")
            mock_cmd.return_value = mock_instance

            # Should not raise
            ares_tool._cleanup_container("ares_test")


# ---------------------------------------------------------------------------
# Tests: get_tool_info()
# ---------------------------------------------------------------------------


class TestGetToolInfo:
    """Test get_tool_info() retrieval."""

    def test_get_tool_info_returns_base_info(self, ares_tool):
        """Test get_tool_info returns base tool information."""
        ares_tool.configure({})
        info = ares_tool.get_tool_info()

        assert "name" in info

    def test_get_tool_info_returns_tool_spec(self, ares_tool):
        """Test get_tool_info returns tool_spec."""
        ares_tool.configure({})
        info = ares_tool.get_tool_info()

        assert "tool_spec" in info

    def test_get_tool_info_returns_docker_image(self, ares_tool):
        """Test get_tool_info returns docker_image."""
        ares_tool.configure({"docker_image": "custom/ares:v1"})
        info = ares_tool.get_tool_info()

        assert "docker_image" in info
        assert info["docker_image"] == "custom/ares:v1"
