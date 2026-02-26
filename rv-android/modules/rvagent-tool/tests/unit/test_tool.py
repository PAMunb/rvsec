"""
Unit tests for RVAgentTool.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestRVAgentToolSpec:
    """Test tool specification."""

    def test_get_tool_spec(self):
        """Test get_tool_spec returns valid ToolSpec."""
        from rvagent_tool.tools.rvagent.tool import RVAgentTool

        spec = RVAgentTool.get_tool_spec()

        assert spec.name == "rvagent"
        assert "LLM" in spec.description
        assert spec.version == "1.0.0"
        assert spec.url == "https://github.com/PAMunb/rvsec"
        # rv-agent doesn't spawn persistent processes on device
        assert spec.process_pattern == ""

    def test_tool_initialization(self):
        """Test tool initializes correctly."""
        from rvagent_tool.tools.rvagent.tool import RVAgentTool

        tool = RVAgentTool()

        assert tool.name == "rvagent"
        assert tool._tool_config == {}


class TestRVAgentToolVariants:
    """Test tool variants."""

    def test_get_variants_returns_dict(self):
        """Test get_variants returns dictionary."""
        from rvagent_tool.tools.rvagent.tool import RVAgentTool

        variants = RVAgentTool.get_variants()

        assert isinstance(variants, dict)
        assert len(variants) > 0

    def test_default_variant_exists(self):
        """Test default variant is defined."""
        from rvagent_tool.tools.rvagent.tool import RVAgentTool

        variants = RVAgentTool.get_variants()

        assert "default" in variants
        assert "agent_mode" in variants["default"]

    def test_multimode_variant(self):
        """Test multimode variant configuration."""
        from rvagent_tool.tools.rvagent.tool import RVAgentTool

        variants = RVAgentTool.get_variants()

        assert "multimode" in variants
        assert variants["multimode"]["agent_mode"] == "multimode"
        assert variants["multimode"]["llm_probability"] == 0.7
        # timeout should NOT be in variants - it comes from Task.config
        assert "timeout" not in variants["multimode"]

    def test_pure_algorithm_variant(self):
        """Test pure_algorithm variant configuration."""
        from rvagent_tool.tools.rvagent.tool import RVAgentTool

        variants = RVAgentTool.get_variants()

        assert "pure_algorithm" in variants
        assert variants["pure_algorithm"]["agent_mode"] == "pure_algorithm"

    def test_llm_only_variant(self):
        """Test llm_only variant configuration."""
        from rvagent_tool.tools.rvagent.tool import RVAgentTool

        variants = RVAgentTool.get_variants()

        assert "llm_only" in variants
        assert variants["llm_only"]["agent_mode"] == "llm_only"


class TestRVAgentToolConfigure:
    """Test tool configuration."""

    def test_configure_stores_config(self):
        """Test configure stores configuration."""
        from rvagent_tool.tools.rvagent.tool import RVAgentTool

        tool = RVAgentTool()
        config = {"agent_mode": "multimode", "timeout": 300}

        tool.configure(config)

        assert tool._tool_config == config

    def test_configure_with_none(self):
        """Test configure handles None config."""
        from rvagent_tool.tools.rvagent.tool import RVAgentTool

        tool = RVAgentTool()

        tool.configure(None)

        assert tool._tool_config == {}

    def test_configure_copies_config(self):
        """Test configure copies config (doesn't store reference)."""
        from rvagent_tool.tools.rvagent.tool import RVAgentTool

        tool = RVAgentTool()
        config = {"agent_mode": "multimode"}

        tool.configure(config)
        config["agent_mode"] = "llm_only"  # Modify original

        assert tool._tool_config["agent_mode"] == "multimode"


class TestConfigMapping:
    """Test configuration mapping functions."""

    def test_build_agent_config_dict_minimal(self):
        """Test build_agent_config_dict with minimal input."""
        from rvagent_tool.tools.rvagent.config import build_agent_config_dict

        # Create mock task and app
        task = MagicMock()
        task.config = None

        app = MagicMock()
        app.package_name = "com.example.app"

        tool_config = {"agent_mode": "multimode"}

        config_dict = build_agent_config_dict(task, app, tool_config)

        assert config_dict["package_name"] == "com.example.app"
        assert config_dict["agent_mode"] == "multimode"

    def test_build_agent_config_dict_with_task_config(self):
        """Test build_agent_config_dict maps task config."""
        from rvagent_tool.tools.rvagent.config import build_agent_config_dict

        # Create mock task with config
        task = MagicMock()
        task.config = MagicMock()
        task.config.device_id = "emulator-5556"
        task.config.timeout = 600

        app = MagicMock()
        app.package_name = "com.example.app"

        tool_config = {}

        config_dict = build_agent_config_dict(task, app, tool_config)

        assert config_dict["device_id"] == "emulator-5556"
        assert config_dict["timeout"] == 600

    def test_build_agent_config_dict_maps_repetition(self):
        """Test build_agent_config_dict maps task.config.repetition."""
        from rvagent_tool.tools.rvagent.config import build_agent_config_dict

        task = MagicMock()
        task.config = MagicMock()
        task.config.device_id = "emulator-5554"
        task.config.timeout = 600
        task.config.repetition = 3

        app = MagicMock()
        app.package_name = "com.example.app"

        tool_config = {"agent_mode": "pure_algorithm"}

        config_dict = build_agent_config_dict(task, app, tool_config)

        assert config_dict["repetition"] == 3
        assert config_dict["timeout"] == 600
        assert config_dict["agent_mode"] == "pure_algorithm"

    def test_build_agent_config_dict_repetition_default_when_missing(self):
        """Test repetition is not set when task.config has no repetition."""
        from rvagent_tool.tools.rvagent.config import build_agent_config_dict

        task = MagicMock()
        task.config = MagicMock()
        task.config.device_id = "emulator-5554"
        task.config.timeout = 600
        task.config.repetition = None  # Not set

        app = MagicMock()
        app.package_name = "com.example.app"

        tool_config = {}

        config_dict = build_agent_config_dict(task, app, tool_config)

        # repetition should NOT be in config_dict when None
        assert "repetition" not in config_dict

    def test_build_agent_config_dict_timeout_from_task_only(self):
        """Test timeout always comes from task config, never tool_config."""
        from rvagent_tool.tools.rvagent.config import build_agent_config_dict

        task = MagicMock()
        task.config = MagicMock()
        task.config.device_id = "emulator-5554"
        task.config.timeout = 300

        app = MagicMock()
        app.package_name = "com.example.app"

        # Even if tool_config has timeout, it should be ignored
        tool_config = {"timeout": 900, "agent_mode": "multimode"}

        config_dict = build_agent_config_dict(task, app, tool_config)

        # Timeout must come from task.config, not tool_config
        assert config_dict["timeout"] == 300
        assert config_dict["agent_mode"] == "multimode"

    def test_get_static_data_with_data(self):
        """Test get_static_data returns static data when present."""
        from rvagent_tool.tools.rvagent.config import get_static_data

        task = MagicMock()
        task.static_data = {"wtg": {}, "mop": {}}

        result = get_static_data(task)

        assert result == {"wtg": {}, "mop": {}}

    def test_get_static_data_without_data(self):
        """Test get_static_data returns None when no data."""
        from rvagent_tool.tools.rvagent.config import get_static_data

        task = MagicMock()
        task.static_data = None

        result = get_static_data(task)

        assert result is None

    def test_get_static_data_no_attribute(self):
        """Test get_static_data handles missing attribute."""
        from rvagent_tool.tools.rvagent.config import get_static_data

        task = MagicMock(spec=[])  # No static_data attribute

        result = get_static_data(task)

        assert result is None


class TestRVAgentToolInfo:
    """Test tool info retrieval."""

    def test_get_tool_info(self):
        """Test get_tool_info returns comprehensive info."""
        from rvagent_tool.tools.rvagent.tool import RVAgentTool

        tool = RVAgentTool()
        tool.configure({"agent_mode": "multimode"})

        info = tool.get_tool_info()

        assert info["name"] == "rvagent"
        assert "version" in info
        assert "url" in info
        assert "current_config" in info
        assert info["current_config"]["agent_mode"] == "multimode"
