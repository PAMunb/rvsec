"""
Tests for RVSmartTool.

Verifies tool spec, variants, configuration, metrics extraction,
JAR search paths, and command building.
"""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

from rvsmart_tool.tools.rvsmart.tool import (
    RVSmartTool,
    RVSMART_METRICS_PREFIX,
    RVSMART_DEVICE_JAR_PATH,
    RVSMART_DEVICE_STATIC_DATA_PATH,
    RVSMART_DEVICE_CONFIG_PATH,
    RVSMART_MAIN_CLASS,
)


class TestToolSpec:
    """Tests for RVSmartTool.TOOL_SPEC."""

    def test_tool_spec_name(self):
        spec = RVSmartTool.get_tool_spec()
        assert spec.name == "rvsmart"

    def test_tool_spec_version(self):
        spec = RVSmartTool.get_tool_spec()
        assert spec.version == "1.0.0"

    def test_tool_spec_process_pattern(self):
        spec = RVSmartTool.get_tool_spec()
        assert spec.process_pattern == "br.unb.cic.rvsmart"

    def test_tool_spec_url(self):
        spec = RVSmartTool.get_tool_spec()
        assert "PAMunb/rvsec" in spec.url


class TestVariants:
    """Tests for RVSmartTool variant definitions."""

    def test_variants_has_default(self):
        variants = RVSmartTool.get_variants()
        assert "default" in variants

    def test_variants_has_mvp(self):
        variants = RVSmartTool.get_variants()
        assert "mvp" in variants

    def test_variants_has_fast(self):
        variants = RVSmartTool.get_variants()
        assert "fast" in variants

    def test_variants_has_hybrid(self):
        variants = RVSmartTool.get_variants()
        assert "hybrid" in variants

    def test_variants_all_have_mode(self):
        variants = RVSmartTool.get_variants()
        for name, config in variants.items():
            assert (
                "mode" in config or "llm_base_url" in config
            ), f"Variant '{name}' should have 'mode' or 'llm_base_url'"

    def test_default_variant_mode(self):
        variants = RVSmartTool.get_variants()
        assert variants["default"]["mode"] == "pure_algorithm"

    def test_hybrid_variant_mode(self):
        variants = RVSmartTool.get_variants()
        assert variants["hybrid"]["mode"] == "multimode"

    def test_hybrid_variant_has_llm_url(self):
        variants = RVSmartTool.get_variants()
        assert "llm_base_url" in variants["hybrid"]
        assert "10.0.2.2" in variants["hybrid"]["llm_base_url"]

    def test_fast_variant_throttle(self):
        variants = RVSmartTool.get_variants()
        assert variants["fast"]["throttle_ms"] == 30


class TestConfigure:
    """Tests for RVSmartTool.configure()."""

    @patch("rvsmart_tool.tools.rvsmart.tool.LoggingManager")
    def test_configure_stores_config(self, mock_logging):
        mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
        tool = RVSmartTool()
        config = {"mode": "pure_algorithm", "throttle_ms": 50}
        tool.configure(config)
        assert tool._tool_config == config

    @patch("rvsmart_tool.tools.rvsmart.tool.LoggingManager")
    def test_configure_requires_no_mandatory_params(self, mock_logging):
        """Defaults should work -- configure with empty dict should not raise."""
        mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
        tool = RVSmartTool()
        tool.configure({})
        assert tool._tool_config == {}

    @patch("rvsmart_tool.tools.rvsmart.tool.LoggingManager")
    def test_configure_copies_config(self, mock_logging):
        """configure() should copy the config, not store a reference."""
        mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
        tool = RVSmartTool()
        original = {"mode": "pure_algorithm"}
        tool.configure(original)
        original["mode"] = "multimode"
        assert tool._tool_config["mode"] == "pure_algorithm"


class TestMetricsExtraction:
    """Tests for metrics extraction from trace files."""

    @patch("rvsmart_tool.tools.rvsmart.tool.LoggingManager")
    def test_extract_metrics_valid_line(self, mock_logging):
        mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
        tool = RVSmartTool()

        metrics = {"iterations": 42, "unique_states": 10, "coverage": 0.75}
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_path = os.path.join(tmpdir, "trace.log")
            with open(trace_path, "w") as f:
                f.write("some output line\n")
                f.write(f"{RVSMART_METRICS_PREFIX} {json.dumps(metrics)}\n")
                f.write("another output line\n")

            # Create mock task
            task = MagicMock()
            task.result.trace_file = trace_path

            tool._extract_metrics(task)

            # Verify metrics file was written
            metrics_path = os.path.join(tmpdir, "rvsmart_metrics.json")
            assert os.path.exists(metrics_path)
            with open(metrics_path) as f:
                written = json.load(f)
            assert written["iterations"] == 42
            assert written["unique_states"] == 10

    @patch("rvsmart_tool.tools.rvsmart.tool.LoggingManager")
    def test_extract_metrics_missing_prefix(self, mock_logging):
        mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
        tool = RVSmartTool()

        with tempfile.TemporaryDirectory() as tmpdir:
            trace_path = os.path.join(tmpdir, "trace.log")
            with open(trace_path, "w") as f:
                f.write("no metrics here\n")

            task = MagicMock()
            task.result.trace_file = trace_path

            tool._extract_metrics(task)

            metrics_path = os.path.join(tmpdir, "rvsmart_metrics.json")
            assert os.path.exists(metrics_path)
            with open(metrics_path) as f:
                written = json.load(f)
            assert written["status"] == "metrics_unavailable"


class TestJarSearchPaths:
    """Tests for JAR search path resolution."""

    def test_jar_search_paths_first_is_module_dir(self):
        """First search path is the tool module directory (APE/FastBot pattern)."""
        import rvsmart_tool.tools.rvsmart.tool as tool_module

        paths = RVSmartTool._get_jar_search_paths()
        assert paths[0] == os.path.dirname(tool_module.__file__)

    @patch.dict(os.environ, {"RVSEC_HOME": "/fake/rvsec"})
    def test_jar_search_paths_includes_rvsec_home(self):
        paths = RVSmartTool._get_jar_search_paths()
        expected = os.path.join("/fake/rvsec", "rvsec-android", "rvsmart", "target")
        assert expected in paths

    @patch.dict(os.environ, {"TOOLS_DIR": "/fake/tools"})
    def test_jar_search_paths_includes_tools_dir(self):
        paths = RVSmartTool._get_jar_search_paths()
        expected = os.path.join("/fake/tools", "rvsmart")
        assert expected in paths

    @patch.dict(os.environ, {}, clear=True)
    def test_jar_search_paths_without_env_vars(self):
        """Without env vars, only module dir path should be present."""
        env = os.environ.copy()
        env.pop("RVSEC_HOME", None)
        env.pop("TOOLS_DIR", None)
        with patch.dict(os.environ, env, clear=True):
            paths = RVSmartTool._get_jar_search_paths()
            assert len(paths) == 1  # Only module dir


class TestBuildCommand:
    """Tests for command construction."""

    @patch("rvsmart_tool.tools.rvsmart.tool.LoggingManager")
    def test_build_command_args(self, mock_logging):
        mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
        tool = RVSmartTool()
        tool.configure({"mode": "pure_algorithm", "throttle_ms": 50})

        app = MagicMock()
        app.package_name = "br.unb.cic.cryptoapp"

        cmd = tool._build_main_command(
            app=app,
            device_serial="emulator-5554",
            timeout_seconds=300,
            has_static_data=False,
        )

        args = cmd.args
        assert "--package" in args
        assert "br.unb.cic.cryptoapp" in args
        assert "--timeout" in args
        assert "300" in args
        assert RVSMART_MAIN_CLASS in args
        assert f"CLASSPATH={RVSMART_DEVICE_JAR_PATH}" in args

    @patch("rvsmart_tool.tools.rvsmart.tool.LoggingManager")
    def test_build_command_with_static_data(self, mock_logging):
        mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
        tool = RVSmartTool()
        tool.configure({"mode": "pure_algorithm"})

        app = MagicMock()
        app.package_name = "com.example.app"

        cmd = tool._build_main_command(
            app=app,
            device_serial="emulator-5554",
            timeout_seconds=120,
            has_static_data=True,
        )

        args = cmd.args
        assert "--static-data" in args
        assert RVSMART_DEVICE_STATIC_DATA_PATH in args

    @patch("rvsmart_tool.tools.rvsmart.tool.LoggingManager")
    def test_build_command_with_mode(self, mock_logging):
        mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
        tool = RVSmartTool()
        tool.configure({"mode": "multimode"})

        app = MagicMock()
        app.package_name = "com.example.app"

        cmd = tool._build_main_command(
            app=app,
            device_serial="emulator-5554",
            timeout_seconds=60,
            has_static_data=False,
        )

        args = cmd.args
        assert "--mode" in args
        assert "multimode" in args

    @patch("rvsmart_tool.tools.rvsmart.tool.LoggingManager")
    def test_build_command_includes_config_path(self, mock_logging):
        mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
        tool = RVSmartTool()
        tool.configure({"mode": "pure_algorithm", "throttle_ms": 50})

        app = MagicMock()
        app.package_name = "com.example.app"

        cmd = tool._build_main_command(
            app=app,
            device_serial="emulator-5554",
            timeout_seconds=60,
            has_static_data=False,
        )

        args = cmd.args
        assert "--config" in args
        assert RVSMART_DEVICE_CONFIG_PATH in args
