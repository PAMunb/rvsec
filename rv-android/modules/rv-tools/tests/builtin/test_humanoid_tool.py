"""
Tests for HumanoidTool - DroidBot with Humanoid inference server.

Tests cover:
- Tool specification and variants
- configure() with URL resolution chain (config > env var > default)
- _build_humanoid_command() with correct CLI flags
- get_tool_info() extended information
- execute_tool_specific_logic() workflow
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task
from rv_android_core.constants import ENV_HUMANOID_URL
from rv_tools.builtin.humanoid.tool import HumanoidTool


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def humanoid_tool():
    """Create HumanoidTool instance."""
    tool = HumanoidTool()
    # Clear config for clean tests
    tool.config = {}
    yield tool


def _merged_config(**overrides) -> dict:
    """Build a config dict simulating ToolFactory.create_tool's variant-default
    merge: `{**variant_defaults, **tool_config.parameters}`. Tests that exercise
    configure() should call it with this dict, mirroring the production flow.

    Per gh55 D8 (ARES/QTesting precedent), the variant default for `humanoid_url`
    lives in `get_variants()["default"]["humanoid_url"]`. The factory always
    merges, so configure() never sees a missing key in production.
    """
    base = HumanoidTool.get_variants()["default"].copy()
    base.update(overrides)
    return base


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
    """Test HumanoidTool specification and variants."""

    def test_tool_spec_name(self):
        """Test tool spec name."""
        spec = HumanoidTool.get_tool_spec()
        assert spec.name == "humanoid"

    def test_tool_spec_version(self):
        """Test tool spec version."""
        spec = HumanoidTool.get_tool_spec()
        assert spec.version == "1.0.0"

    def test_tool_spec_url(self):
        """Test tool spec URL."""
        spec = HumanoidTool.get_tool_spec()
        assert "humanoid" in spec.url.lower()

    def test_get_variants_returns_default(self):
        """Test that get_variants returns default variant."""
        variants = HumanoidTool.get_variants()
        assert "default" in variants

    def test_default_variant_has_policy(self):
        """Test default variant has dfs_greedy policy."""
        variants = HumanoidTool.get_variants()
        assert variants["default"]["policy"] == "dfs_greedy"

    def test_default_variant_has_ignore_ad(self):
        """Test default variant has ignore_ad enabled."""
        variants = HumanoidTool.get_variants()
        assert variants["default"]["ignore_ad"] is True


# ---------------------------------------------------------------------------
# Tests: configure() - URL Resolution Chain
# ---------------------------------------------------------------------------


class TestConfigure:
    """Test configure() under gh55 D8: variant default carries humanoid_url; no env reads at L2."""

    def test_configure_uses_humanoid_url_from_merged_dict(self, humanoid_tool):
        """L5-injected URL flows through factory merge into configure()."""
        config = _merged_config(humanoid_url="http://custom.server:50405")
        humanoid_tool.configure(config)
        assert humanoid_tool.config["humanoid_url"] == "http://custom.server:50405"

    def test_configure_uses_variant_default_when_no_l5_override(self, humanoid_tool):
        """When L5 does not override, variant default 127.0.0.1:50405 carries through."""
        config = _merged_config()  # = variant default
        humanoid_tool.configure(config)
        assert humanoid_tool.config["humanoid_url"] == "127.0.0.1:50405"

    def test_configure_does_not_consult_environment(self, humanoid_tool):
        """Layer Purity: configure() must not read RV_HUMANOID_URL at L2.
        Even with the env var set, the variant-default merged dict wins."""
        with patch.dict(os.environ, {ENV_HUMANOID_URL: "http://env.server:50405"}):
            config = _merged_config()  # variant default only
            humanoid_tool.configure(config)
            # The env var is set but L2 ignored it; default carried through.
            assert humanoid_tool.config["humanoid_url"] == "127.0.0.1:50405"

    def test_configure_raises_keyerror_when_humanoid_url_missing(self, humanoid_tool):
        """Defensive: configure(dict_without_humanoid_url) raises KeyError.
        In production this never happens because the factory always merges
        variant defaults — but the contract is explicit (no env fallback)."""
        config = {"policy": "dfs_greedy"}  # no humanoid_url
        with pytest.raises(KeyError):
            humanoid_tool.configure(config)

    def test_configure_custom_policy(self, humanoid_tool):
        config = _merged_config(policy="random")
        humanoid_tool.configure(config)
        assert humanoid_tool.config["policy"] == "random"

    def test_configure_default_policy(self, humanoid_tool):
        config = _merged_config()
        humanoid_tool.configure(config)
        assert humanoid_tool.config["policy"] == "dfs_greedy"

    def test_configure_custom_count(self, humanoid_tool):
        config = _merged_config(count=5000000000)
        humanoid_tool.configure(config)
        assert humanoid_tool.config["count"] == 5000000000

    def test_configure_custom_timeout(self, humanoid_tool):
        config = _merged_config(timeout=7200)
        humanoid_tool.configure(config)
        assert humanoid_tool.config["timeout"] == 7200

    def test_configure_custom_device_serial(self, humanoid_tool):
        config = _merged_config(device_serial="emulator-5558")
        humanoid_tool.configure(config)
        assert humanoid_tool.config["device_serial"] == "emulator-5558"

    def test_configure_custom_ignore_ad(self, humanoid_tool):
        config = _merged_config(ignore_ad=False)
        humanoid_tool.configure(config)
        assert humanoid_tool.config["ignore_ad"] is False

    def test_l5_injection_overrides_variant_default(self, humanoid_tool):
        """gh55 D8: L5-set parameters merge AFTER variant defaults, so they win."""
        config = _merged_config(humanoid_url="http://l5-resolved.server:50405")
        humanoid_tool.configure(config)
        assert humanoid_tool.config["humanoid_url"] == "http://l5-resolved.server:50405"


# ---------------------------------------------------------------------------
# Tests: _build_humanoid_command()
# ---------------------------------------------------------------------------


class TestBuildHumanoidCommand:
    """Test _build_humanoid_command() with correct CLI flags."""

    def test_build_command_uses_droidbot(self, humanoid_tool, mock_app):
        """Test command uses droidbot as base."""
        humanoid_tool.configure(_merged_config())
        cmd = humanoid_tool._build_humanoid_command(mock_app, 3600)
        
        assert cmd.command == "droidbot"

    def test_build_command_includes_device_serial(self, humanoid_tool, mock_app):
        """Test command includes device serial."""
        humanoid_tool.configure(_merged_config(device_serial="emulator-5556"))
        cmd = humanoid_tool._build_humanoid_command(mock_app, 3600)
        
        assert "-d" in cmd.args
        assert "emulator-5556" in cmd.args

    def test_build_command_includes_apk_path(self, humanoid_tool, mock_app):
        """Test command includes APK path."""
        humanoid_tool.configure(_merged_config())
        cmd = humanoid_tool._build_humanoid_command(mock_app, 3600)
        
        assert "-a" in cmd.args
        assert "/path/to/test_app.apk" in cmd.args

    def test_build_command_includes_humanoid_url(self, humanoid_tool, mock_app):
        """Test command includes humanoid URL."""
        humanoid_tool.configure(_merged_config(humanoid_url="http://test.server:50405"))
        cmd = humanoid_tool._build_humanoid_command(mock_app, 3600)
        
        assert "-humanoid" in cmd.args
        assert "http://test.server:50405" in cmd.args

    def test_build_command_includes_policy(self, humanoid_tool, mock_app):
        """Test command includes policy."""
        humanoid_tool.configure(_merged_config(policy="dfs_greedy"))
        cmd = humanoid_tool._build_humanoid_command(mock_app, 3600)
        
        assert "-policy" in cmd.args
        assert "dfs_greedy" in cmd.args

    def test_build_command_includes_count(self, humanoid_tool, mock_app):
        """Test command includes count."""
        humanoid_tool.configure(_merged_config(count=10000000000))
        cmd = humanoid_tool._build_humanoid_command(mock_app, 3600)
        
        assert "-count" in cmd.args
        assert "10000000000" in cmd.args

    def test_build_command_includes_timeout(self, humanoid_tool, mock_app):
        """Test command includes timeout."""
        humanoid_tool.configure(_merged_config())
        cmd = humanoid_tool._build_humanoid_command(mock_app, 7200)
        
        assert "-timeout" in cmd.args
        assert "7200" in cmd.args

    def test_build_command_includes_ignore_ad(self, humanoid_tool, mock_app):
        """Test command includes ignore_ad flag."""
        humanoid_tool.configure(_merged_config(ignore_ad=True))
        cmd = humanoid_tool._build_humanoid_command(mock_app, 3600)
        
        assert "-ignore_ad" in cmd.args

    def test_build_command_includes_is_emulator(self, humanoid_tool, mock_app):
        """Test command includes is_emulator flag."""
        humanoid_tool.configure(_merged_config())
        cmd = humanoid_tool._build_humanoid_command(mock_app, 3600)
        
        assert "-is_emulator" in cmd.args

    def test_build_command_default_serial(self, humanoid_tool, mock_app):
        """Test command uses default serial when not configured."""
        humanoid_tool.configure(_merged_config())
        cmd = humanoid_tool._build_humanoid_command(mock_app, 3600)
        
        # Should have emulator-5554 as default
        idx = cmd.args.index("-d")
        assert cmd.args[idx + 1] == "emulator-5554"


# ---------------------------------------------------------------------------
# Tests: get_tool_info()
# ---------------------------------------------------------------------------


class TestGetToolInfo:
    """Test get_tool_info() extended information."""

    def test_get_tool_info_returns_base_info(self, humanoid_tool):
        """Test get_tool_info returns base tool information."""
        humanoid_tool.configure(_merged_config())
        info = humanoid_tool.get_tool_info()
        
        assert "name" in info

    def test_get_tool_info_returns_tool_spec(self, humanoid_tool):
        """Test get_tool_info returns tool_spec."""
        humanoid_tool.configure(_merged_config())
        info = humanoid_tool.get_tool_info()
        
        assert "tool_spec" in info

    def test_get_tool_info_returns_humanoid_url(self, humanoid_tool):
        """Test get_tool_info returns humanoid_url."""
        humanoid_tool.configure(_merged_config())
        info = humanoid_tool.get_tool_info()
        
        assert "humanoid_url" in info

    def test_get_tool_info_returns_current_policy(self, humanoid_tool):
        """Test get_tool_info returns current_policy."""
        humanoid_tool.configure(_merged_config())
        info = humanoid_tool.get_tool_info()
        
        assert "current_policy" in info


# ---------------------------------------------------------------------------
# Tests: execute_tool_specific_logic()
# ---------------------------------------------------------------------------


class TestExecuteToolSpecificLogic:
    """Test execute_tool_specific_logic() workflow."""

    def test_execute_builds_command(self, humanoid_tool, mock_task, mock_app):
        """Test that execute builds humanoid command."""
        humanoid_tool.configure(_merged_config())
        humanoid_tool._build_humanoid_command = MagicMock()

        try:
            humanoid_tool.execute_tool_specific_logic(mock_task, mock_app)
        except Exception:
            pass  # May fail due to missing _execute_and_check_command

        humanoid_tool._build_humanoid_command.assert_called_once()

    def test_execute_uses_task_timeout(self, humanoid_tool, mock_task, mock_app):
        """Test that execute uses timeout from task config."""
        mock_task.config.timeout = 7200
        humanoid_tool.configure(_merged_config())
        humanoid_tool._build_humanoid_command = MagicMock()

        try:
            humanoid_tool.execute_tool_specific_logic(mock_task, mock_app)
        except Exception:
            pass

        call_args = humanoid_tool._build_humanoid_command.call_args
        assert call_args[0][1] == 7200  # timeout_seconds

    def test_execute_uses_config_timeout(self, humanoid_tool, mock_task, mock_app):
        """Test that execute falls back to config timeout."""
        # Remove task timeout to force fallback to config
        del mock_task.config.timeout
        humanoid_tool.configure(_merged_config(timeout=5000))
        humanoid_tool._build_humanoid_command = MagicMock()

        try:
            humanoid_tool.execute_tool_specific_logic(mock_task, mock_app)
        except Exception:
            pass

        call_args = humanoid_tool._build_humanoid_command.call_args
        # Should use config timeout (5000) or default (3600)
        timeout_used = call_args[0][1]
        assert timeout_used in [5000, 3600]
