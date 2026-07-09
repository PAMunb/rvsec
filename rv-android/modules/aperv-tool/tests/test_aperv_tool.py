"""
Unit tests for ApeRVTool.

Tests cover: tool spec, variants, configure, JAR search paths, command building,
constants, and empty trace detection.
"""

import logging
import os
from unittest.mock import MagicMock

import pytest
from rv_android_core.util.error.exceptions import ConfigurationError

import aperv_tool.tools.aperv.tool as aperv_mod
from aperv_tool.tools.aperv.tool import (
    APERV_DEVICE_JAR_PATH,
    APERV_DEVICE_PROPERTIES_PATH,
    APERV_PROPERTY_MAPPING,
    ApeRVTool,
)


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

    def test_base_variants_present(self):
        variants = ApeRVTool.get_variants()
        base_variants = {
            "default",
            "sata",
            "sata_mop",
            "bfs",
            "random",
            "sata_llm",
            "sata_mop_llm",
        }
        assert base_variants.issubset(
            set(variants.keys())
        ), f"Missing base variants: {base_variants - set(variants.keys())}"

    def test_default_uses_sata_strategy(self):
        variants = ApeRVTool.get_variants()
        assert variants["default"]["strategy"] == "sata"

    def test_sata_mop_has_mop_data_static_analysis(self):
        variants = ApeRVTool.get_variants()
        assert "mop_data" in variants["sata_mop"]
        assert variants["sata_mop"]["mop_data"] == "static_analysis"

    def test_non_mop_variants_lack_mop_data(self):
        variants = ApeRVTool.get_variants()
        for name in ["default", "sata", "bfs", "random", "sata_llm"]:
            assert "mop_data" not in variants[name], f"{name} should not have mop_data"

    def test_sata_llm_has_llm_url_no_mop_data(self):
        variants = ApeRVTool.get_variants()
        assert "llm_url" in variants["sata_llm"]
        assert "mop_data" not in variants["sata_llm"]

    def test_sata_mop_llm_has_both_llm_url_and_mop_data(self):
        variants = ApeRVTool.get_variants()
        assert "llm_url" in variants["sata_mop_llm"]
        assert variants["sata_mop_llm"]["mop_data"] == "static_analysis"

    def test_llm_variants_have_all_llm_keys(self):
        """LLM variants must include all 8 LLM config keys explicitly."""
        variants = ApeRVTool.get_variants()
        llm_keys = {
            "llm_url",
            "llm_on_new_state",
            "llm_on_stagnation",
            "llm_model",
            "llm_temperature",
            "llm_top_p",
            "llm_top_k",
            "llm_timeout_ms",
        }
        for name in ["sata_llm", "sata_mop_llm"]:
            for key in llm_keys:
                assert key in variants[name], f"{name} missing {key}"

    def test_llm_variants_use_sata_strategy(self):
        variants = ApeRVTool.get_variants()
        assert variants["sata_llm"]["strategy"] == "sata"
        assert variants["sata_mop_llm"]["strategy"] == "sata"

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

    def test_env_var_does_not_override_llm_url_at_l2(self, monkeypatch):
        """gh55 INV-TOOL-20: configure() at L2 must not consult os.environ.
        APERV_LLM_BASE_URL override is now handled at L5; L2 only reads what
        the factory-merged config dict provides."""
        monkeypatch.setenv("APERV_LLM_BASE_URL", "http://custom:8080/v1")
        self.tool.configure(
            {
                "strategy": "sata",
                "throttle_ms": 200,
                "llm_url": "http://10.0.2.2:30000/v1",
            }
        )
        # The env var is ignored at L2; the config value carries through.
        assert self.tool._tool_config["llm_url"] == "http://10.0.2.2:30000/v1"

    def test_env_var_does_not_inject_llm_url_at_l2(self, monkeypatch):
        """gh55 INV-TOOL-20: env var with no llm_url in config still produces
        no llm_url at L2. Injection happens at L5 via parameters."""
        monkeypatch.setenv("APERV_LLM_BASE_URL", "http://custom:8080/v1")
        self.tool.configure({"strategy": "sata", "throttle_ms": 200})
        assert "llm_url" not in self.tool._tool_config


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
        assert (
            os.path.dirname(
                self.tool._resolve_jar_path.__func__.__code__.co_filename
                if False
                else __file__
            )
            or True
        )  # just verify length
        import aperv_tool.tools.aperv.tool as tool_module

        assert captured["paths"][0] == os.path.dirname(tool_module.__file__)

    def test_l2_supplies_only_module_dir(self, monkeypatch):
        """gh55 D10: L2 _resolve_jar_path passes ONLY the module directory to
        the resolver. RVSEC_HOME / TOOLS_DIR-derived paths are added by
        JarResolver._build_search_paths at L1, not by L2."""
        monkeypatch.setenv("RVSEC_HOME", "/fake/rvsec")
        monkeypatch.setenv("TOOLS_DIR", "/fake/tools")

        captured = {}

        def fake_resolve(jar_name, search_paths):
            captured["paths"] = search_paths
            raise FileNotFoundError("not found")

        self.tool.jar_resolver.resolve_jar_path = fake_resolve

        with pytest.raises(Exception):
            self.tool._resolve_jar_path()

        # L2 only supplies the module dir; the resolver internally extends
        # the search list with TOOLS_DIR / RVSEC_HOME at L1.
        assert len(captured["paths"]) == 1
        import aperv_tool.tools.aperv.tool as tool_module

        assert captured["paths"][0] == os.path.dirname(tool_module.__file__)


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


class TestPushPropertiesLlm:
    """Verify _push_properties() generates LLM keys when llm_url is present."""

    def setup_method(self):
        self.tool = ApeRVTool()

    def test_llm_properties_present_when_llm_url_set(self, tmp_path):
        """All 9 ape.llm* keys must appear when using full LLM variant config."""
        self.tool.configure(ApeRVTool.get_variants()["sata_llm"])

        captured_content = {}

        def fake_push(local_path, device_path, device_serial, trace_file_path):
            with open(local_path) as f:
                captured_content["properties"] = f.read()

        self.tool._push_file_to_device = fake_push
        trace = str(tmp_path / "trace.bin")
        open(trace, "w").close()

        self.tool._push_properties("emulator-5554", trace)

        props = captured_content["properties"]
        assert "ape.llmUrl=http://10.0.2.2:30000/v1" in props
        assert "ape.llmOnNewState=true" in props
        assert "ape.llmOnStagnation=true" in props
        assert "ape.llmModel=default" in props
        assert "ape.llmTemperature=0.3" in props
        assert "ape.llmTopP=0.6" in props
        assert "ape.llmTopK=50" in props
        assert "ape.llmTimeoutMs=15000" in props

    def test_llm_properties_absent_when_no_llm_url(self, tmp_path):
        """No ape.llm* keys for non-LLM variants."""
        self.tool.configure(
            {
                "strategy": "sata",
                "throttle_ms": 200,
            }
        )

        captured_content = {}

        def fake_push(local_path, device_path, device_serial, trace_file_path):
            with open(local_path) as f:
                captured_content["properties"] = f.read()

        self.tool._push_file_to_device = fake_push
        trace = str(tmp_path / "trace.bin")
        open(trace, "w").close()

        self.tool._push_properties("emulator-5554", trace)

        props = captured_content["properties"]
        assert "ape.llm" not in props


class TestPushPropertiesCalibration:
    """Verify _push_properties() writes calibration parameters via APERV_PROPERTY_MAPPING."""

    def setup_method(self):
        self.tool = ApeRVTool()

    def _capture_properties(self, tmp_path, config, mop_json_pushed=False):
        """Helper: configure tool, call _push_properties, return content."""
        self.tool.configure(config)
        captured = {}

        def fake_push(local_path, device_path, device_serial, trace_file_path):
            with open(local_path) as f:
                captured["properties"] = f.read()

        self.tool._push_file_to_device = fake_push
        trace = str(tmp_path / "trace.bin")
        open(trace, "w").close()
        self.tool._push_properties("emulator-5554", trace, mop_json_pushed)
        return captured["properties"]

    def test_exploration_params_written(self, tmp_path):
        props = self._capture_properties(
            tmp_path,
            {
                "strategy": "sata",
                "throttle_ms": 200,
                "default_epsilon": 0.08,
                "graph_stable_restart_threshold": 150,
            },
        )
        assert "ape.defaultEpsilon=0.08" in props
        assert "ape.graphStableRestartThreshold=150" in props

    def test_mop_weight_params_written(self, tmp_path):
        props = self._capture_properties(
            tmp_path,
            {
                "strategy": "sata",
                "throttle_ms": 200,
                "mop_weight_direct": 400,
                "mop_weight_transitive": 250,
                "mop_weight_activity": 80,
            },
        )
        assert "ape.mopWeightDirect=400" in props
        assert "ape.mopWeightTransitive=250" in props
        assert "ape.mopWeightActivity=80" in props

    def test_minimal_config_only_throttle(self, tmp_path):
        props = self._capture_properties(
            tmp_path,
            {
                "strategy": "sata",
                "throttle_ms": 200,
            },
        )
        assert "ape.defaultGUIThrottle=200" in props
        # Only throttle_ms is in the mapping; strategy is not
        lines = [l for l in props.strip().split("\n") if l]
        assert len(lines) == 1

    def test_python_only_keys_not_written(self, tmp_path):
        props = self._capture_properties(
            tmp_path,
            {
                "strategy": "sata",
                "throttle_ms": 200,
                "mop_data": "static_analysis",
            },
        )
        assert "strategy" not in props
        assert "mop_data" not in props

    def test_mixed_params_all_written(self, tmp_path):
        props = self._capture_properties(
            tmp_path,
            {
                "strategy": "sata",
                "throttle_ms": 300,
                "default_epsilon": 0.1,
                "mop_weight_direct": 500,
                "llm_url": "http://10.0.2.2:30000/v1",
                "llm_temperature": 0.5,
            },
        )
        assert "ape.defaultGUIThrottle=300" in props
        assert "ape.defaultEpsilon=0.1" in props
        assert "ape.mopWeightDirect=500" in props
        assert "ape.llmUrl=http://10.0.2.2:30000/v1" in props
        assert "ape.llmTemperature=0.5" in props
        # Python-only keys absent
        assert "strategy" not in props
        assert "mop_data" not in props


# The 19 arm-defining Python keys → frozen ape.* names (spec INV-APV-13, verbatim).
# Pinned here so a typo'd java name in the mapping (which would make the property
# inert on the jar with no error — R1/D5) fails a unit test, not the experiment.
_EXPECTED_ARM_DEFINING_MAPPING = {
    "ape_pure_mode": "ape.apePureMode",
    "frontier_boost_weight": "ape.frontierBoostWeight",
    "activity_trigger_enabled": "ape.activityTriggerEnabled",
    "back_menu_pick_cap": "ape.backMenuPickCap",
    "foreign_activity_guard": "ape.foreignActivityGuard",
    "tree_package_guard": "ape.treePackageGuard",
    "dynamic_epsilon": "ape.dynamicEpsilon",
    "heuristic_input": "ape.heuristicInput",
    "fuzz_input_typed": "ape.fuzzInputTyped",
    "form_completion_enabled": "ape.formCompletionEnabled",
    "step_telemetry_enabled": "ape.stepTelemetryEnabled",
    "model_menu_enabled": "ape.modelMenuEnabled",
    "least_visited_priority_tiebreak": "ape.leastVisitedPriorityTiebreak",
    "tree_enhancements_enabled": "ape.treeEnhancementsEnabled",
    "activity_budget_enabled": "ape.activityBudgetEnabled",
    "mop_activity_source_components": "ape.mopActivitySourceComponents",
    "mop_frontier_weight": "ape.mopFrontierWeight",
    "trigger_mop_first": "ape.triggerMopFirst",
    "llm_percentage_no_substrate": "ape.llmPercentageNoSubstrate",
}

_EXPECTED_EXEMPT_VARIANTS = {
    "sata_mop_llm_ape_current",
    "sata_mop_llm_ape_reasoning",
    "sata_mop_llm_compact_v1",
    "sata_mop_llm_v13",
    "sata_mop_llm_v17",
    "sata_mop_llm_visual_only",
}


class TestArmDefiningConstants:
    """Group 1 guard: ARM_DEFINING_KEYS + _ARM_DEFINING_EXEMPT + mapping (INV-APV-13/15/17)."""

    def test_all_arm_defining_keys_are_mapped(self):
        # INV-APV-13 (task 4.1): every arm-defining key reaches ape.properties.
        missing = aperv_mod.ARM_DEFINING_KEYS - set(APERV_PROPERTY_MAPPING)
        assert not missing, f"arm-defining keys absent from mapping: {sorted(missing)}"

    def test_arm_defining_keys_count_is_19(self):
        assert len(aperv_mod.ARM_DEFINING_KEYS) == 19

    def test_arm_defining_keys_excludes_orchestration_and_weights(self):
        # INV-APV-15: mop_data/strategy are Python-only; mop_weight_* are gated by
        # mop_data (null MopData disables scoring) so they are NOT arm-defining.
        forbidden = {
            "mop_data",
            "strategy",
            "mop_weight_direct",
            "mop_weight_transitive",
            "mop_weight_activity",
            "mop_weight_open_menu",
            "mop_weight_wtg",
            "max_idle_timeout_ms",
        }
        assert forbidden.isdisjoint(aperv_mod.ARM_DEFINING_KEYS)

    def test_arm_defining_maps_to_frozen_java_names(self):
        # INV-APV-13 verbatim: pin the 19 python→java names so a typo fails here.
        assert set(aperv_mod.ARM_DEFINING_KEYS) == set(_EXPECTED_ARM_DEFINING_MAPPING)
        for py_key, java_key in _EXPECTED_ARM_DEFINING_MAPPING.items():
            assert APERV_PROPERTY_MAPPING[py_key] == java_key

    def test_exempt_set_is_exactly_the_six_gh43_variants(self):
        # INV-APV-17: explicit named set, not a prefix match.
        assert aperv_mod._ARM_DEFINING_EXEMPT == _EXPECTED_EXEMPT_VARIANTS

    def test_max_idle_timeout_mapped_but_not_arm_defining(self):
        # Task 1.4 / INV-APV-15: arm-neutral tuning knob — mapped, not arm-defining.
        assert APERV_PROPERTY_MAPPING["max_idle_timeout_ms"] == "ape.maxIdleTimeoutMs"
        assert "max_idle_timeout_ms" not in aperv_mod.ARM_DEFINING_KEYS
