"""
Unit tests for ApeRVTool.

Tests cover: tool spec, variants, configure, JAR search paths, command building,
constants, and empty trace detection.
"""

import json
import logging
import os
import tempfile
from unittest.mock import MagicMock

import pytest
from rv_android_core.util.error.exceptions import ConfigurationError

import aperv_tool.tools.aperv.tool as aperv_mod
from aperv_tool.tools.aperv.tool import (
    APERV_DEVICE_JAR_PATH,
    APERV_DEVICE_PROPERTIES_PATH,
    APERV_PROPERTY_MAPPING,
    LLM_ARM_KEYS,
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


# The 18 arm-defining Python keys → frozen ape.* names (spec INV-APV-13, verbatim).
# Pinned here so a typo'd java name in the mapping (which would make the property
# inert on the jar with no error — R1/D5) fails a unit test, not the experiment.
# trigger_mop_first was removed (task group 7): the APE-RV jar deleted Config.triggerMopFirst
# in mop-census-launcher, so the property is inert on the jar and is no longer arm-defining.
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

# The Phase-A calibration arm table verbatim from the delta spec (specs/aperv/spec.md,
# plan §6 rev. 3.2) — the seven per-arm varying LLM keys. Pins every cal_* value so a typo
# in the variant dict fails here. (prompt, percentage, temperature, top_p, top_k,
# on_new_state, on_stagnation.)
_EXPECTED_CAL_ARM_TABLE = {
    "cal_a1": ("v13", 0.7, 0, 0.6, 50, True, True),
    "cal_a2": ("v13", 0.3, 0, 0.6, 50, True, True),
    "cal_a3": ("v13", 0, 0, 0.6, 50, False, True),
    "cal_a4": ("v13", 0, 0, 0.6, 50, True, True),
    "cal_a5": ("v13", 0.3, 0.7, 0.8, 20, True, True),
    "cal_a6": ("v13", 0.3, 0.7, 0.6, 50, True, True),
    "cal_a7": ("v13", 0.3, 0.25, 0.6, 50, True, True),
    "cal_a8": ("visual_only", 0.3, 0, 0.6, 50, True, True),
    "cal_a9": ("v17", 0.3, 0, 0.6, 50, True, True),
}

# The sata_mop_act_frontier arm-defining substrate every cal_* arm must carry.
_EXPECTED_FRONTIER_SUBSTRATE = {
    "mop_data": "static_analysis",
    "mop_activity_source_components": True,
    "frontier_boost_weight": 200,
    "mop_frontier_weight": 200,
    "activity_trigger_enabled": True,
}


class TestArmDefiningConstants:
    """Group 1 guard: ARM_DEFINING_KEYS + _ARM_DEFINING_EXEMPT + mapping (INV-APV-13/15/17)."""

    def test_all_arm_defining_keys_are_mapped(self):
        # INV-APV-13 (task 4.1): every arm-defining key reaches ape.properties.
        missing = aperv_mod.ARM_DEFINING_KEYS - set(APERV_PROPERTY_MAPPING)
        assert not missing, f"arm-defining keys absent from mapping: {sorted(missing)}"

    def test_arm_defining_keys_count_is_18(self):
        # 18 after trigger_mop_first was dropped (task group 7 — jar deleted the property).
        assert len(aperv_mod.ARM_DEFINING_KEYS) == 18

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
        # INV-APV-13 verbatim: pin the 18 python→java names so a typo fails here.
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

    def test_activity_trigger_dose_mapped_but_not_arm_defining(self):
        # activity-trigger-dose: the launcher cadence/cap are arm-neutral tuning knobs —
        # mapped to ape.properties, shared identically by both arms of a paired run, so
        # NOT arm-defining (same rationale as max_idle_timeout_ms).
        assert (
            APERV_PROPERTY_MAPPING["activity_trigger_stagnation_step"]
            == "ape.activityTriggerStagnationStep"
        )
        assert (
            APERV_PROPERTY_MAPPING["activity_trigger_max_per_run"]
            == "ape.activityTriggerMaxPerRun"
        )
        assert "activity_trigger_stagnation_step" not in aperv_mod.ARM_DEFINING_KEYS
        assert "activity_trigger_max_per_run" not in aperv_mod.ARM_DEFINING_KEYS


class TestArmVariants:
    """Group 2: frozen arm variants (INV-APV-14/16, Variants requirement)."""

    def test_non_exempt_variants_set_all_arm_defining_keys(self):
        # INV-APV-14 (task 4.2): the executable explicitness guard.
        variants = ApeRVTool.get_variants()
        for name, cfg in variants.items():
            if name in aperv_mod._ARM_DEFINING_EXEMPT:
                continue
            missing = aperv_mod.ARM_DEFINING_KEYS - set(cfg)
            assert (
                not missing
            ), f"variant {name!r} missing arm-defining keys: {sorted(missing)}"

    def test_sata_mop_is_alias_of_widget(self):
        # INV-APV-16 (task 4.4): same object, equal dict.
        variants = ApeRVTool.get_variants()
        assert variants["sata_mop"] == variants["sata_mop_widget"]

    def test_new_arm_variants_present(self):
        variants = ApeRVTool.get_variants()
        for name in [
            "ape_pure",
            "sata_mop_widget",
            "sata_mop_activity",
            "sata_mop_act_frontier",
        ]:
            assert name in variants, f"missing new arm variant {name!r}"

    def test_ape_pure_kill_switch_and_offs(self):
        # Task 2.3 / spec scenario: kill-switch true, every RV flag off, no mop_data.
        cfg = ApeRVTool.get_variants()["ape_pure"]
        assert cfg["ape_pure_mode"] is True
        assert cfg["dynamic_epsilon"] is False
        assert cfg["form_completion_enabled"] is False
        assert cfg["model_menu_enabled"] is False
        assert cfg["tree_enhancements_enabled"] is False
        assert cfg["frontier_boost_weight"] == 0
        assert cfg["activity_trigger_enabled"] is False
        assert "mop_data" not in cfg

    def test_sata_baseline_disables_reach_explicitly(self):
        # Spec scenario: baseline sata arm disables RV steering explicitly.
        cfg = ApeRVTool.get_variants()["sata"]
        assert cfg["frontier_boost_weight"] == 0
        assert cfg["activity_trigger_enabled"] is False
        assert cfg["dynamic_epsilon"] is True
        assert cfg["ape_pure_mode"] is False
        assert "mop_data" not in cfg

    def test_sata_mop_widget_values(self):
        # Spec scenario: sata_mop_widget is the MOP control arm.
        cfg = ApeRVTool.get_variants()["sata_mop_widget"]
        assert cfg["mop_data"] == "static_analysis"
        assert cfg["mop_weight_direct"] == 500
        assert cfg["mop_weight_transitive"] == 300
        assert cfg["mop_weight_open_menu"] == 250
        assert cfg["mop_weight_wtg"] == 200
        assert cfg["mop_activity_source_components"] is False
        assert cfg["frontier_boost_weight"] == 0
        assert cfg["mop_frontier_weight"] == 0
        assert cfg["activity_trigger_enabled"] is False

    def test_sata_mop_activity_differs_only_by_a_prime(self):
        # Spec scenario: sata_mop_activity isolates strategy A′.
        variants = ApeRVTool.get_variants()
        widget = variants["sata_mop_widget"]
        activity = variants["sata_mop_activity"]
        assert activity["mop_activity_source_components"] is True
        # Every other arm-defining key equals the widget arm.
        for key in aperv_mod.ARM_DEFINING_KEYS:
            if key == "mop_activity_source_components":
                continue
            assert activity[key] == widget[key], f"{key} diverged from widget arm"

    def test_sata_mop_act_frontier_reach_package(self):
        # Spec scenario: sata_mop_act_frontier enables the reach package A′+B+E-min.
        cfg = ApeRVTool.get_variants()["sata_mop_act_frontier"]
        assert cfg["mop_activity_source_components"] is True
        assert cfg["frontier_boost_weight"] == 200
        assert cfg["mop_frontier_weight"] == 200
        assert cfg["activity_trigger_enabled"] is True
        assert cfg["mop_data"] == "static_analysis"
        # trigger_mop_first no longer exists (task group 7 — jar deleted the property).
        assert "trigger_mop_first" not in cfg

    def test_cal_variants_declare_all_llm_keys(self):
        # INV-APV-26 guard (task 1.4): every cal_* arm ⊇ LLM_ARM_KEYS. Failure names the
        # variant and the missing keys.
        variants = ApeRVTool.get_variants()
        cal_arms = {n: c for n, c in variants.items() if n.startswith("cal_")}
        assert cal_arms, "no cal_* arms found in get_variants()"
        for name, cfg in cal_arms.items():
            missing = LLM_ARM_KEYS - set(cfg)
            assert not missing, f"cal arm {name!r} missing LLM keys: {sorted(missing)}"

    def test_cal_arms_match_plan_table(self):
        # Task 1.5: concrete value assertions for all nine arms — the seven varying LLM
        # keys per the plan §6 table, the frontier substrate in every arm, plus the
        # constant LLM keys shared by all arms.
        variants = ApeRVTool.get_variants()
        assert set(_EXPECTED_CAL_ARM_TABLE) == {
            n for n in variants if n.startswith("cal_")
        }, "cal_* arm set diverged from the expected Phase-A table"
        for name, (
            prompt,
            pct,
            temp,
            top_p,
            top_k,
            on_new,
            on_stag,
        ) in _EXPECTED_CAL_ARM_TABLE.items():
            cfg = variants[name]
            assert cfg["llm_prompt_variant"] == prompt, name
            assert cfg["llm_percentage"] == pct, name
            assert cfg["llm_temperature"] == temp, name
            assert cfg["llm_top_p"] == top_p, name
            assert cfg["llm_top_k"] == top_k, name
            # Routing flags are Python bools (serialized to true/false by _push_properties).
            assert cfg["llm_on_new_state"] is on_new, name
            assert cfg["llm_on_stagnation"] is on_stag, name
            # Constant LLM keys shared by all nine arms.
            assert cfg["llm_url"] == "http://10.0.2.2:30000/v1", name
            assert cfg["llm_model"] == "default", name
            assert cfg["llm_timeout_ms"] == 15000, name
            assert cfg["llm_percentage_no_substrate"] == -1, name
            assert cfg["strategy"] == "sata", name
            assert cfg["throttle_ms"] == 200, name
            # Frontier substrate present in every cal_* arm (no widget-substrate arm).
            for key, expected in _EXPECTED_FRONTIER_SUBSTRATE.items():
                assert cfg[key] == expected, f"{name}: {key} not frontier substrate"

    def test_cal_arms_carry_frontier_not_widget_substrate(self):
        # Spec scenario "Every cal_* arm falls back to frontier mode": the substrate MUST
        # equal sata_mop_act_frontier (ANC2) and never the widget substrate. Compared
        # against the live ANC2 arm so the two cannot drift apart.
        variants = ApeRVTool.get_variants()
        anc2 = variants["sata_mop_act_frontier"]
        substrate_keys = [
            "mop_activity_source_components",
            "frontier_boost_weight",
            "mop_frontier_weight",
            "activity_trigger_enabled",
            "mop_data",
        ]
        for name, cfg in variants.items():
            if not name.startswith("cal_"):
                continue
            assert (
                cfg["frontier_boost_weight"] == 200
            ), f"{name} not on frontier substrate"
            for key in substrate_keys:
                assert cfg[key] == anc2[key], f"{name}: {key} diverged from ANC2"

    def test_cal_a3_is_stagnation_only(self):
        # Spec scenario: cal_a3 routes only on stagnation; all other LLM keys == cal_a1.
        variants = ApeRVTool.get_variants()
        a1, a3 = variants["cal_a1"], variants["cal_a3"]
        assert a3["llm_on_new_state"] is False
        assert a3["llm_on_stagnation"] is True
        assert a3["llm_percentage"] == 0
        for key in LLM_ARM_KEYS:
            if key in ("llm_on_new_state", "llm_percentage"):
                continue
            assert a3[key] == a1[key], f"cal_a3 {key} diverged from cal_a1"

    def test_cal_a6_vs_cal_a5_isolates_top_p_top_k(self):
        # Spec scenario: cal_a6 vs cal_a5 differ only in top_p (0.6 vs 0.8) and top_k
        # (50 vs 20); both have temperature 0.7 and percentage 0.3.
        variants = ApeRVTool.get_variants()
        a5, a6 = variants["cal_a5"], variants["cal_a6"]
        assert a5["llm_top_p"] == 0.8 and a6["llm_top_p"] == 0.6
        assert a5["llm_top_k"] == 20 and a6["llm_top_k"] == 50
        assert a5["llm_temperature"] == 0.7 and a6["llm_temperature"] == 0.7
        assert a5["llm_percentage"] == 0.3 and a6["llm_percentage"] == 0.3
        differing = {k for k in LLM_ARM_KEYS if a5[k] != a6[k]}
        assert differing == {"llm_top_p", "llm_top_k"}, differing

    def test_property_mapping_covers_llm_max_tokens_and_snap(self):
        # Task 1.5 / INV-APV-27: the two Phase-B mappings are present, and no cal_a* arm
        # sets either key (the Phase-A jar hardcodes them — a set value would fake config).
        assert APERV_PROPERTY_MAPPING["llm_max_tokens"] == "ape.llmMaxTokens"
        assert (
            APERV_PROPERTY_MAPPING["llm_snap_tolerance_px"] == "ape.llmSnapTolerancePx"
        )
        assert "llm_max_tokens" not in LLM_ARM_KEYS
        assert "llm_snap_tolerance_px" not in LLM_ARM_KEYS
        for name, cfg in ApeRVTool.get_variants().items():
            if not name.startswith("cal_"):
                continue
            assert "llm_max_tokens" not in cfg, name
            assert "llm_snap_tolerance_px" not in cfg, name


class TestSeedPropagation:
    """Group 3: seed reaches the jar as -s <seed>, never ape.properties (INV-APV-18)."""

    def setup_method(self):
        self.tool = ApeRVTool()
        self.tool.configure({"strategy": "sata", "throttle_ms": 200})

    def _make_app(self, package="br.unb.cic.cryptoapp"):
        app = MagicMock()
        app.package_name = package
        return app

    def test_seed_passed_as_dash_s(self):
        # INV-APV-18: -s <seed> appears after --ape <strategy>. (arg[0] -s is the adb
        # serial flag — assert on the tail after --ape so the two do not collide.)
        self.tool._tool_config["seed"] = 42
        cmd = self.tool._build_main_command(self._make_app(), "emulator-5554", 60)
        tail = cmd.args[cmd.args.index("--ape") :]
        assert "-s" in tail
        assert tail[tail.index("-s") + 1] == "42"

    def test_no_seed_omits_dash_s(self):
        # INV-APV-18: no seed configured → no -s in the Monkey args (after --ape).
        cmd = self.tool._build_main_command(self._make_app(), "emulator-5554", 60)
        tail = cmd.args[cmd.args.index("--ape") :]
        assert "-s" not in tail


class TestArmProperties:
    """Group 4: arm-defining flags reach ape.properties (lowercased bools); seed excluded."""

    def setup_method(self):
        self.tool = ApeRVTool()

    def _capture_properties(self, tmp_path, config, mop_json_pushed=False):
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

    def test_sata_arm_writes_reach_offs_lowercase(self, tmp_path):
        # Spec scenario: arm-defining flags appear in properties for a baseline arm.
        props = self._capture_properties(tmp_path, ApeRVTool.get_variants()["sata"])
        assert "ape.frontierBoostWeight=0" in props
        assert "ape.activityTriggerEnabled=false" in props
        assert "ape.dynamicEpsilon=true" in props
        assert "ape.mopDataPath" not in props

    def test_ape_pure_writes_kill_switch_lowercase(self, tmp_path):
        # Spec scenario: kill-switch flag appears in properties for ape_pure.
        props = self._capture_properties(tmp_path, ApeRVTool.get_variants()["ape_pure"])
        assert "ape.apePureMode=true" in props
        assert "ape.frontierBoostWeight=0" in props
        assert "ape.activityTriggerEnabled=false" in props

    def test_act_frontier_writes_reach_package(self, tmp_path):
        # Spec scenario: reach-package flags appear for sata_mop_act_frontier.
        props = self._capture_properties(
            tmp_path,
            ApeRVTool.get_variants()["sata_mop_act_frontier"],
            mop_json_pushed=True,
        )
        assert "ape.mopActivitySourceComponents=true" in props
        assert "ape.mopFrontierWeight=200" in props
        assert "ape.mopDataPath=/data/local/tmp/static_analysis.json" in props
        # trigger_mop_first dropped (task group 7): never written to properties anymore.
        assert "ape.triggerMopFirst" not in props

    def test_seed_not_written_to_properties(self, tmp_path):
        # Spec scenario: seed is a CLI-only, Python-only key — never in ape.properties.
        cfg = {**ApeRVTool.get_variants()["sata"], "seed": 42}
        props = self._capture_properties(tmp_path, cfg)
        assert "seed" not in props


# --- gh80: static analysis JSON compaction -----------------------------------

# A source document carrying all seven top-level keys the producer emits, with
# duplicate transitions in the [A, B, A, C, B] shape the spec scenario names.
TRANSITION_A = {"sourceId": "w1", "targetId": "w2", "events": ["click"]}
TRANSITION_B = {"sourceId": "w2", "targetId": "w3", "events": ["swipe"]}
TRANSITION_C = {"sourceId": "w3", "targetId": "w1", "events": ["back"]}

SOURCE_DOCUMENT = {
    "package": "br.unb.cic.cryptoapp",
    "mainActivity": "br.unb.cic.cryptoapp.MainActivity",
    "components": {"activities": ["MainActivity", "SecondActivity"]},
    "reachability": {"br.unb.cic.cryptoapp.MainActivity": ["onCreate", "doCrypto"]},
    "windows": [{"id": "w1", "title": "main"}],
    "transitions": [
        TRANSITION_A,
        TRANSITION_B,
        TRANSITION_A,
        TRANSITION_C,
        TRANSITION_B,
    ],
    "complete": True,
}


def _write_source(tmp_path, document=None, raw=None):
    """Write a source JSON (pretty-printed, as the producer emits it)."""
    path = tmp_path / "app.apk.json"
    if raw is not None:
        path.write_text(raw)
    else:
        path.write_text(json.dumps(document, indent=2))
    return str(path)


class TestCompactStaticAnalysisJson:
    """Group 1: _compact_static_analysis_json() semantics (INV-APV-20..25)."""

    def setup_method(self):
        self.tool = ApeRVTool()

    def test_dedup_preserves_first_occurrence_order(self, tmp_path):
        # INV-APV-22: [A, B, A, C, B] -> exactly [A, B, C]. Order is load-bearing
        # because rekeyDialogsToHost takes the first inbound edge and breaks.
        source = _write_source(tmp_path, SOURCE_DOCUMENT)

        compacted = self.tool._compact_static_analysis_json(source)

        assert compacted is not None
        with open(compacted) as f:
            result = json.load(f)
        assert result["transitions"] == [TRANSITION_A, TRANSITION_B, TRANSITION_C]
        os.unlink(compacted)

    def test_all_top_level_keys_survive_unchanged(self, tmp_path):
        # INV-APV-21: no field is projected away; only transitions is touched.
        source = _write_source(tmp_path, SOURCE_DOCUMENT)

        compacted = self.tool._compact_static_analysis_json(source)

        with open(compacted) as f:
            result = json.load(f)
        assert set(result.keys()) == set(SOURCE_DOCUMENT.keys())
        for key in SOURCE_DOCUMENT:
            if key != "transitions":
                assert result[key] == SOURCE_DOCUMENT[key]
        os.unlink(compacted)

    def test_output_has_no_pretty_print_whitespace(self, tmp_path):
        # INV-APV-21(b): minified serialization, and it re-parses to the same
        # document modulo the transitions dedup.
        source = _write_source(tmp_path, SOURCE_DOCUMENT)

        compacted = self.tool._compact_static_analysis_json(source)

        raw = open(compacted).read()
        assert "\n" not in raw
        assert ", " not in raw
        assert ": " not in raw
        expected = {
            **SOURCE_DOCUMENT,
            "transitions": [TRANSITION_A, TRANSITION_B, TRANSITION_C],
        }
        assert json.loads(raw) == expected
        os.unlink(compacted)

    def test_source_file_is_byte_identical_after_call(self, tmp_path):
        # INV-APV-20: the source is an archived artifact — never written.
        source = _write_source(tmp_path, SOURCE_DOCUMENT)
        before = open(source, "rb").read()

        compacted = self.tool._compact_static_analysis_json(source)

        assert open(source, "rb").read() == before
        assert compacted != source
        os.unlink(compacted)

    def test_document_without_transitions_key(self, tmp_path):
        # Spec scenario: the key is not added when the source lacks it.
        document = {"package": "com.example", "complete": True}
        source = _write_source(tmp_path, document)

        compacted = self.tool._compact_static_analysis_json(source)

        with open(compacted) as f:
            result = json.load(f)
        assert "transitions" not in result
        assert result == document
        os.unlink(compacted)

    def test_document_with_empty_transitions(self, tmp_path):
        # Spec scenario: sdmse/email ship transitions: [] — it stays [].
        document = {**SOURCE_DOCUMENT, "transitions": []}
        source = _write_source(tmp_path, document)

        compacted = self.tool._compact_static_analysis_json(source)

        with open(compacted) as f:
            result = json.load(f)
        assert result["transitions"] == []
        os.unlink(compacted)

    def test_malformed_json_returns_none_and_warns(self, tmp_path, caplog):
        # INV-APV-24 + INV-APV-25: fall back, warn, raise nothing, leak no temp.
        source = _write_source(tmp_path, raw="{not valid json")
        before_temps = set(os.listdir(tempfile.gettempdir()))

        with caplog.at_level(logging.WARNING):
            compacted = self.tool._compact_static_analysis_json(source)

        assert compacted is None
        assert source in caplog.text
        assert set(os.listdir(tempfile.gettempdir())) == before_temps

    def test_oserror_on_temp_write_returns_none(self, tmp_path, caplog, monkeypatch):
        # INV-APV-24, OSError leg: temp file cannot be created (e.g. disk full).
        source = _write_source(tmp_path, SOURCE_DOCUMENT)
        before_temps = set(os.listdir(tempfile.gettempdir()))

        def raise_oserror(*args, **kwargs):
            raise OSError("No space left on device")

        monkeypatch.setattr(aperv_mod.tempfile, "NamedTemporaryFile", raise_oserror)

        with caplog.at_level(logging.WARNING):
            compacted = self.tool._compact_static_analysis_json(source)

        assert compacted is None
        assert source in caplog.text
        assert set(os.listdir(tempfile.gettempdir())) == before_temps

    def test_memoryerror_on_load_returns_none(self, tmp_path, caplog, monkeypatch):
        # INV-APV-24, MemoryError leg: host cannot hold the document. Degrades to
        # the source push; the Java guard then decides (D3).
        source = _write_source(tmp_path, SOURCE_DOCUMENT)
        before_temps = set(os.listdir(tempfile.gettempdir()))

        def raise_memoryerror(*args, **kwargs):
            raise MemoryError("document too large")

        monkeypatch.setattr(aperv_mod.json, "load", raise_memoryerror)

        with caplog.at_level(logging.WARNING):
            compacted = self.tool._compact_static_analysis_json(source)

        assert compacted is None
        assert source in caplog.text
        assert set(os.listdir(tempfile.gettempdir())) == before_temps


class TestExecuteCompactionFlow:
    """Group 2: Step 1c wiring — which path is pushed, and temp lifetime."""

    def setup_method(self):
        self.tool = ApeRVTool()
        self.pushed = []

    def _make_task(self, tmp_path, source_path=None):
        task = MagicMock()
        task.results_dir = str(tmp_path)
        task.config.apk_name = "app.apk"
        task.config.device_id = "emulator-5554"
        task.config.timeout = 60
        trace = tmp_path / "trace.bin"
        trace.write_bytes(b"")
        task.result.trace_file = str(trace)
        return task

    def _run(self, tmp_path, variant):
        """Execute the flow with the device and the jar stubbed out."""
        self.tool.configure(ApeRVTool.get_variants()[variant])
        task = self._make_task(tmp_path)
        app = MagicMock()
        app.package_name = "br.unb.cic.cryptoapp"

        def fake_push(local_path, device_path, device_serial, trace_file_path):
            # Snapshot content at push time: the temp is unlinked right after.
            content = (
                open(local_path, "rb").read() if os.path.isfile(local_path) else None
            )
            self.pushed.append((local_path, device_path, content))

        self.tool._resolve_jar_path = lambda: str(tmp_path / "ape-rv.jar")
        (tmp_path / "ape-rv.jar").write_bytes(b"jar")
        self.tool._push_file_to_device = fake_push

        result = MagicMock()
        result.code = 0
        main_cmd = MagicMock()
        main_cmd.invoke.return_value = result
        self.tool._build_main_command = lambda *a, **kw: main_cmd

        self.tool.execute_tool_specific_logic(task, app)
        return task

    def _static_pushes(self):
        return [
            p for p in self.pushed if p[1] == "/data/local/tmp/static_analysis.json"
        ]

    def test_pushes_compacted_temp_not_source(self, tmp_path):
        # Spec scenario: the compacted temp reaches the device, not the source.
        source = _write_source(tmp_path, SOURCE_DOCUMENT)

        self._run(tmp_path, "sata_mop_act_frontier")

        pushes = self._static_pushes()
        assert len(pushes) == 1
        local_path, _, content = pushes[0]
        assert local_path != source
        assert json.loads(content)["transitions"] == [
            TRANSITION_A,
            TRANSITION_B,
            TRANSITION_C,
        ]

    def test_falls_back_to_source_when_compaction_fails(self, tmp_path):
        # Spec scenario: malformed source -> the source itself is pushed, and
        # ape.mopDataPath is emitted exactly as on the success path.
        source = _write_source(tmp_path, raw="{not valid json")
        captured = {}
        original_push_properties = self.tool._push_properties

        def spy_push_properties(device_serial, trace_file_path, mop_json_pushed=False):
            captured["mop_json_pushed"] = mop_json_pushed
            return original_push_properties(
                device_serial, trace_file_path, mop_json_pushed
            )

        self.tool._push_properties = spy_push_properties

        self._run(tmp_path, "sata_mop_act_frontier")

        pushes = self._static_pushes()
        assert len(pushes) == 1
        assert pushes[0][0] == source
        # INV-APV-24: the fallback is invisible to ape.properties.
        assert captured["mop_json_pushed"] is True
        props = next(p for p in self.pushed if p[1] == APERV_DEVICE_PROPERTIES_PATH)[
            2
        ].decode()
        assert "ape.mopDataPath=/data/local/tmp/static_analysis.json" in props

    def test_no_compaction_when_mop_data_unset(self, tmp_path):
        # Spec scenario: sata/ape_pure push no static analysis JSON at all.
        _write_source(tmp_path, SOURCE_DOCUMENT)
        calls = []
        self.tool._compact_static_analysis_json = lambda p: calls.append(p)

        self._run(tmp_path, "sata")

        assert self._static_pushes() == []
        assert calls == []

    def test_no_temp_leak_on_success_and_fallback(self, tmp_path):
        # INV-APV-25: no temp survives execute_tool_specific_logic() on either path.
        _write_source(tmp_path, SOURCE_DOCUMENT)
        before = set(os.listdir(tempfile.gettempdir()))
        self._run(tmp_path, "sata_mop_act_frontier")
        assert set(os.listdir(tempfile.gettempdir())) == before

        self.tool = ApeRVTool()
        self.pushed = []
        _write_source(tmp_path, raw="{not valid json")
        before = set(os.listdir(tempfile.gettempdir()))
        self._run(tmp_path, "sata_mop_act_frontier")
        assert set(os.listdir(tempfile.gettempdir())) == before

    def test_small_json_is_compacted_anyway(self, tmp_path):
        # INV-APV-23: no size gate — a ~100 KB source is compacted like any other.
        document = {
            **SOURCE_DOCUMENT,
            "windows": [{"id": f"w{i}", "title": "x" * 100} for i in range(800)],
        }
        source = _write_source(tmp_path, document)
        assert os.path.getsize(source) > 100_000

        self._run(tmp_path, "sata_mop_act_frontier")

        local_path, _, content = self._static_pushes()[0]
        assert local_path != source
        assert b"\n" not in content

    def test_no_compaction_when_json_not_found(self, tmp_path, caplog):
        # Spec scenario (retained): mop_data set but no JSON in results_dir —
        # the not-found branch must not attempt compaction. Distinct from the
        # mop_data-unset case, which never reaches this branch at all.
        calls = []
        self.tool._compact_static_analysis_json = lambda p: calls.append(p)

        with caplog.at_level(logging.WARNING):
            self._run(tmp_path, "sata_mop_act_frontier")

        assert calls == []
        assert self._static_pushes() == []
        assert "static analysis file not found in results_dir" in caplog.text
