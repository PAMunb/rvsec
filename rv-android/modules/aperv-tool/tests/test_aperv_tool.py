"""
Unit tests for ApeRVTool.

Tests cover: tool spec, variants, configure, JAR search paths, command building,
constants, and empty trace detection.
"""

import logging
import os
from unittest.mock import MagicMock, patch

import pytest

from aperv_tool.tools.aperv.tool import (
    APERV_DEVICE_JAR_PATH,
    APERV_DEVICE_PROPERTIES_PATH,
    APERV_AVAILABLE_STRATEGIES,
    ApeRVTool,
)
from rv_android_core.util.error.exceptions import ConfigurationError


class TestToolSpec:
    """Verify TOOL_SPEC metadata."""

    def test_tool_name(self):
        spec = ApeRVTool.get_tool_spec()
        assert spec.name == "aperv"

    def test_process_pattern(self):
        spec = ApeRVTool.get_tool_spec()
        assert spec.process_pattern == "com.android.commands.monkey"

    def test_version(self):
        spec = ApeRVTool.get_tool_spec()
        assert spec.version == "1.0.0"


class TestVariants:
    """Verify get_variants() structure (INV-APV-05)."""

    def test_exactly_five_variants(self):
        variants = ApeRVTool.get_variants()
        assert set(variants.keys()) == {"default", "sata", "sata_mop", "bfs", "random"}

    def test_default_uses_sata_strategy(self):
        variants = ApeRVTool.get_variants()
        assert variants["default"]["strategy"] == "sata"

    def test_sata_mop_has_mop_data_static_analysis(self):
        variants = ApeRVTool.get_variants()
        assert "mop_data" in variants["sata_mop"]
        assert variants["sata_mop"]["mop_data"] == "static_analysis"

    def test_non_sata_mop_variants_lack_mop_data(self):
        variants = ApeRVTool.get_variants()
        for name in ["default", "sata", "bfs", "random"]:
            assert "mop_data" not in variants[name], f"{name} should not have mop_data"

    def test_all_variants_have_throttle_ms(self):
        variants = ApeRVTool.get_variants()
        for name, config in variants.items():
            assert "throttle_ms" in config, f"{name} missing throttle_ms"
            assert config["throttle_ms"] == 200


class TestConfigure:
    """Verify configure() validation (INV-APV-02)."""

    def setup_method(self):
        self.tool = ApeRVTool()

    def test_valid_strategy_stores_config(self):
        self.tool.configure({"strategy": "sata", "throttle_ms": 200})
        assert self.tool._tool_config["strategy"] == "sata"

    def test_invalid_strategy_raises(self):
        with pytest.raises(ConfigurationError):
            self.tool.configure({"strategy": "invalid_strategy"})

    def test_absent_strategy_raises(self):
        with pytest.raises(ConfigurationError):
            self.tool.configure({"throttle_ms": 200})

    def test_empty_config_raises(self):
        # INV-APV-02: absent strategy (empty dict) must raise, not store
        with pytest.raises(ConfigurationError):
            self.tool.configure({})

    def test_dfs_is_accepted(self):
        # dfs is in APERV_AVAILABLE_STRATEGIES even without a named variant (D6)
        self.tool.configure({"strategy": "dfs"})
        assert self.tool._tool_config["strategy"] == "dfs"

    def test_configure_makes_copy(self):
        config = {"strategy": "sata", "throttle_ms": 200}
        self.tool.configure(config)
        config["strategy"] = "mutated"
        assert self.tool._tool_config["strategy"] == "sata"


class TestJarSearchPaths:
    """Verify _resolve_jar_path() search path construction (INV-APV-01)."""

    def setup_method(self):
        self.tool = ApeRVTool()

    def test_no_env_only_module_dir(self, monkeypatch):
        monkeypatch.delenv("RVSEC_HOME", raising=False)
        monkeypatch.delenv("TOOLS_DIR", raising=False)

        # Patch jar_resolver so it raises (jar not found) — we inspect the paths
        captured = {}

        def fake_resolve(jar_name, search_paths):
            captured["paths"] = search_paths
            raise FileNotFoundError("not found")

        self.tool.jar_resolver.resolve_jar_path = fake_resolve

        with pytest.raises(Exception):
            self.tool._resolve_jar_path()

        assert len(captured["paths"]) == 1
        assert os.path.dirname(
            self.tool._resolve_jar_path.__func__.__code__.co_filename
            if False
            else __file__
        ) or True  # just verify length
        import aperv_tool.tools.aperv.tool as tool_module
        assert captured["paths"][0] == os.path.dirname(tool_module.__file__)

    def test_rvsec_home_set_appends_path(self, monkeypatch):
        monkeypatch.setenv("RVSEC_HOME", "/fake/rvsec")
        monkeypatch.delenv("TOOLS_DIR", raising=False)

        captured = {}

        def fake_resolve(jar_name, search_paths):
            captured["paths"] = search_paths
            raise FileNotFoundError("not found")

        self.tool.jar_resolver.resolve_jar_path = fake_resolve

        with pytest.raises(Exception):
            self.tool._resolve_jar_path()

        assert any("/fake/rvsec/ape/target" in p for p in captured["paths"])

    def test_empty_rvsec_home_not_appended(self, monkeypatch):
        monkeypatch.setenv("RVSEC_HOME", "")
        monkeypatch.delenv("TOOLS_DIR", raising=False)

        captured = {}

        def fake_resolve(jar_name, search_paths):
            captured["paths"] = search_paths
            raise FileNotFoundError("not found")

        self.tool.jar_resolver.resolve_jar_path = fake_resolve

        with pytest.raises(Exception):
            self.tool._resolve_jar_path()

        assert len(captured["paths"]) == 1

    def test_tools_dir_set_appends_path(self, monkeypatch):
        monkeypatch.delenv("RVSEC_HOME", raising=False)
        monkeypatch.setenv("TOOLS_DIR", "/fake/tools")

        captured = {}

        def fake_resolve(jar_name, search_paths):
            captured["paths"] = search_paths
            raise FileNotFoundError("not found")

        self.tool.jar_resolver.resolve_jar_path = fake_resolve

        with pytest.raises(Exception):
            self.tool._resolve_jar_path()

        assert any("/fake/tools/aperv" in p for p in captured["paths"])


class TestBuildCommand:
    """Verify _build_main_command() output (INV-APV-04)."""

    def setup_method(self):
        self.tool = ApeRVTool()
        self.tool.configure({"strategy": "sata", "throttle_ms": 200})

    def _make_app(self, package="br.unb.cic.cryptoapp"):
        app = MagicMock()
        app.package_name = package
        return app

    def test_ape_flag_uses_strategy(self):
        cmd = self.tool._build_main_command(self._make_app(), "emulator-5554", 300)
        args = cmd.args
        idx = args.index("--ape")
        assert args[idx + 1] == "sata"

    def test_running_minutes_minimum_one_for_60s(self):
        cmd = self.tool._build_main_command(self._make_app(), "emulator-5554", 60)
        args = cmd.args
        idx = args.index("--running-minutes")
        assert args[idx + 1] == "1"

    def test_running_minutes_for_300s(self):
        cmd = self.tool._build_main_command(self._make_app(), "emulator-5554", 300)
        args = cmd.args
        idx = args.index("--running-minutes")
        assert args[idx + 1] == "5"

    def test_classpath_uses_device_jar_path(self):
        cmd = self.tool._build_main_command(self._make_app(), "emulator-5554", 60)
        assert f"CLASSPATH={APERV_DEVICE_JAR_PATH}" in cmd.args

    def test_uses_app_process(self):
        cmd = self.tool._build_main_command(self._make_app(), "emulator-5554", 60)
        assert "/system/bin/app_process" in cmd.args

    def test_working_dir_is_system_bin(self):
        # INV-APV-04: working dir must be /system/bin
        cmd = self.tool._build_main_command(self._make_app(), "emulator-5554", 60)
        app_process_idx = cmd.args.index("/system/bin/app_process")
        assert cmd.args[app_process_idx + 1] == "/system/bin"

    def test_command_timeout_is_timeout_plus_15(self):
        cmd = self.tool._build_main_command(self._make_app(), "emulator-5554", 300)
        assert cmd.timeout == 315


class TestConstants:
    """Verify constant values (INV-APV-03)."""

    def test_device_jar_path(self):
        assert APERV_DEVICE_JAR_PATH == "/data/local/tmp/ape-rv.jar"

    def test_device_properties_path(self):
        assert APERV_DEVICE_PROPERTIES_PATH == "/data/local/tmp/ape.properties"


class TestCheckEmptyTrace:
    """Verify _check_empty_trace() warning behavior."""

    def setup_method(self):
        self.tool = ApeRVTool()

    def test_empty_file_logs_warning(self, tmp_path, caplog):
        empty = tmp_path / "trace.bin"
        empty.write_bytes(b"")
        with caplog.at_level(logging.WARNING):
            self.tool._check_empty_trace(str(empty))
        assert "aperv produced empty trace file" in caplog.text

    def test_non_empty_file_no_warning(self, tmp_path, caplog):
        nonempty = tmp_path / "trace.bin"
        nonempty.write_bytes(b"some data")
        with caplog.at_level(logging.WARNING):
            self.tool._check_empty_trace(str(nonempty))
        assert "aperv produced empty trace file" not in caplog.text

    def test_nonexistent_file_no_exception(self):
        # Must not raise even if file doesn't exist
        self.tool._check_empty_trace("/nonexistent/path/trace.bin")
