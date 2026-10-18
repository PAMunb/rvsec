"""
Unit tests for ApeRVTool.

Tests cover: tool spec, the cell variants, configure, ape.properties composition, the
device push flow (static-data artifact and broadcast catalog), JAR search paths, command
building, constants, and empty trace detection.
"""

import copy
import gzip
import hashlib
import json
import logging
import os
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from rv_android_core.util.error.exceptions import (
    ConfigurationError,
    RVCommandTimeoutError,
    RVToolExecutionError,
    RVToolTimeoutError,
)

import aperv_tool.tools.aperv.tool as aperv_mod
from aperv_tool.tools.aperv.derive_mop_artifact import (
    DEVICE_ARTIFACT_PATH,
    derive,
    serialize_canonical,
)
from aperv_tool.tools.aperv.tool import (
    APERV_DEVICE_BROADCAST_CATALOG_PATH,
    APERV_DEVICE_JAR_PATH,
    APERV_DEVICE_PROPERTIES_PATH,
    APERV_ORCHESTRATION_KEYS,
    APERV_PROPERTY_MAPPING,
    APERV_TEARDOWN_GRACE_S,
    LLM_URL_DEFAULT,
    ApeRVTool,
)

# The seven variant names: the six cells and default, bound to base.
CELLS = ("base", "mop", "as", "as_mop", "as_llm", "as_mop_llm")
STATIC_CELLS = ("as", "as_mop", "as_llm", "as_mop_llm")
LLM_CELLS = ("as_llm", "as_mop_llm")
# The ablation variant that shares containers with its cell, so it carries a name.
ABLATIONS = ("mop_k2",)


def _stub_clock(*readings):
    """A stand-in for the `time` module whose monotonic() returns the given readings.

    The readings are handed out in order and the last one is held, so a caller states only
    the pair the completion check reads: the moment the exploration started and the moment
    it returned. Replacing the module reference in tool.py's namespace, rather than
    time.monotonic itself, keeps the stub from reaching anything else in the session.
    """
    pending = list(readings)

    def monotonic():
        return pending.pop(0) if len(pending) > 1 else pending[0]

    return SimpleNamespace(monotonic=monotonic)


def _cell(name, **parameters):
    """The config ToolFactory hands configure() for `aperv:<name>@<parameters>`.

    A deep copy of the registered variant with the DSL parameters merged at the top level,
    as the factory merges them, so a test can neither mutate the variant table nor state a
    cell that get_variants() does not define.
    """
    return {**copy.deepcopy(ApeRVTool.get_variants()[name]), **parameters}


def _written_properties(tool, tmp_path, artifact_pushed=False):
    """The ape.properties content a configured tool would push, without a device.

    The push is intercepted rather than mocked away so the file really is written and read
    back — an assertion about a string the test itself built would prove nothing about the
    writer.
    """
    captured = {}

    def fake_push(local_path, device_path, device_serial, trace_file_path):
        with open(local_path) as handle:
            captured["properties"] = handle.read()

    tool._push_file_to_device = fake_push
    trace = str(tmp_path / "trace.bin")
    open(trace, "w").close()
    tool._push_properties("emulator-5554", trace, artifact_pushed)
    return captured["properties"]


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
    """Verify get_variants(): one variant per cell (INV-APV-05, -38, -40, -65, -66)."""

    DELETED_NAMES = (
        "sata",
        "sata_mop",
        "sata_llm",
        "sata_mop_llm",
        "mop_on_llm_off",
        "mop_off_llm_off",
        "mop_on_llm_70",
        "mopd_on_llm_off",
        "mopd_on_llm_90",
    )

    def test_the_variant_set_is_the_six_cells_and_default(self):
        variants = ApeRVTool.get_variants()
        assert set(variants) == {"default", *CELLS, *ABLATIONS}
        for name in self.DELETED_NAMES:
            assert name not in variants, f"{name} survives as an alias"

    def test_default_is_bound_to_the_same_object_as_base(self):
        # INV-TOOL-02: every registered tool carries default, and binding it to the same
        # object keeps it from drifting. A bare `aperv` runs the APE reference cell.
        variants = ApeRVTool.get_variants()
        assert variants["default"] is variants["base"]
        assert variants["default"]["variant"] == "base"

    @pytest.mark.parametrize("name", CELLS)
    def test_each_cell_names_its_own_preset_and_itself(self, name):
        cell = ApeRVTool.get_variants()[name]
        assert cell["preset"] == name
        assert cell["variant"] == name
        assert cell["strategy"] == "sata"

    def test_the_base_cell_carries_no_data_and_no_overrides(self):
        base = ApeRVTool.get_variants()["base"]
        assert base["preset"] == "base"
        assert base["overrides"] == {}
        assert "static_data" not in base
        assert "broadcast_catalog" not in base

    def test_only_the_llm_cells_carry_an_override(self):
        # INV-APV-38: the LLM preset needs a server, and a URL names a machine, not a cell.
        variants = ApeRVTool.get_variants()
        assert variants["as_mop_llm"]["overrides"] == {"llm_url": LLM_URL_DEFAULT}
        assert variants["as_llm"]["overrides"] == variants["as_mop_llm"]["overrides"]
        assert LLM_URL_DEFAULT == "http://10.0.2.2:30000/v1"
        for name in set(CELLS) - set(LLM_CELLS):
            assert variants[name]["overrides"] == {}, name

    def test_the_mop_ledger_ablation_is_the_mop_cell_with_one_key(self):
        # Spec scenario "The MOP ledger ablation is the mop cell with one key".
        variants = ApeRVTool.get_variants()
        k2 = variants["mop_k2"]
        assert k2["preset"] == "mop"
        assert k2["variant"] == "mop_k2"
        assert k2["strategy"] == "sata"
        assert k2["overrides"] == {"mop_coin_ledger_max_interactions": 2}
        same = set(k2) - {"variant", "overrides"}
        assert same == set(variants["mop"]) - {"variant", "overrides"}
        for key in same:
            assert k2[key] == variants["mop"][key], key

    def test_every_cell_but_base_carries_the_static_data(self):
        # INV-APV-66: the artifact reaches the device exactly when STATIC or MOP is mounted.
        variants = ApeRVTool.get_variants()
        for name in ("mop", *STATIC_CELLS, *ABLATIONS):
            assert variants[name]["static_data"] == "static_analysis", name
            assert "mop_data" not in variants[name], name

    def test_the_broadcast_catalog_follows_static(self):
        # INV-APV-10: component triggering is a STATIC member and the catalog's only
        # reader, so the four as* cells carry the flag and base and mop do not.
        variants = ApeRVTool.get_variants()
        for name in STATIC_CELLS:
            assert variants[name]["broadcast_catalog"] is True, name
        for name in ("base", "mop"):
            assert "broadcast_catalog" not in variants[name], name

    def test_no_variant_carries_a_property_expansion(self):
        # What a cell mounts lives in the jar. A dose or a throttle in a variant would be
        # the jar's vocabulary restated here; an ablation goes through the tool DSL, or,
        # when it shares containers with its cell, through a named variant.
        allowed = {
            "preset",
            "variant",
            "overrides",
            "strategy",
            "static_data",
            "broadcast_catalog",
        }
        for name, variant in ApeRVTool.get_variants().items():
            assert set(variant) <= allowed, (name, sorted(set(variant) - allowed))
            for key in ("throttle_ms", "llm_percentage", "mop_coin_percentage"):
                assert key not in variant["overrides"], (name, key)

    def test_every_variant_configures(self):
        # The variant table and configure() are two halves of one contract: a variant that
        # cannot be configured is a variant that cannot run, and nothing else in the suite
        # would notice.
        for name in ApeRVTool.get_variants():
            ApeRVTool().configure(_cell(name))


class TestConfigure:
    """Verify configure() validation (INV-APV-02)."""

    def setup_method(self):
        self.tool = ApeRVTool()

    def test_valid_cell_stores_config(self):
        # Spec scenario "Valid preset arm configured".
        self.tool.configure(
            {
                "strategy": "sata",
                "preset": "mop",
                "variant": "mop",
                "static_data": "static_analysis",
                "overrides": {},
            }
        )
        assert self.tool._tool_config["strategy"] == "sata"
        assert self.tool._tool_config["preset"] == "mop"
        assert self.tool._tool_config["variant"] == "mop"

    def test_invalid_strategy_raises(self):
        with pytest.raises(ConfigurationError, match="Valid strategies"):
            self.tool.configure(
                {"strategy": "unknown", "preset": "base", "variant": "base"}
            )

    def test_absent_strategy_raises(self):
        with pytest.raises(ConfigurationError):
            self.tool.configure({"preset": "base", "variant": "base"})

    def test_empty_config_raises(self):
        # INV-APV-02: absent strategy (empty dict) must raise, not store
        with pytest.raises(ConfigurationError):
            self.tool.configure({})

    @pytest.mark.parametrize("strategy", ["bfs", "dfs"])
    def test_retired_strategy_rejected_before_the_device(self, strategy):
        # Neither was ever an agent type: ApeAgent.createAgent knows sata, random and
        # replay only, so the jar aborts on either. Rejecting here is what keeps a run
        # from passing local validation and dying on an emulator.
        with pytest.raises(ConfigurationError):
            self.tool.configure(
                {"strategy": strategy, "preset": "base", "variant": "base"}
            )

    def test_missing_preset_raises(self):
        with pytest.raises(ConfigurationError, match="preset"):
            self.tool.configure({"strategy": "sata", "variant": "base"})

    def test_empty_preset_raises(self):
        with pytest.raises(ConfigurationError, match="preset"):
            self.tool.configure({"strategy": "sata", "preset": "", "variant": "base"})

    def test_missing_variant_raises_before_any_push(self):
        # Spec scenario "Missing variant raises ConfigurationError" (INV-APV-65).
        def fail_on_push(*args, **kwargs):
            raise AssertionError("a configuration without a variant reached the device")

        self.tool._push_file_to_device = fail_on_push
        with pytest.raises(ConfigurationError, match="variant"):
            self.tool.configure({"strategy": "sata", "preset": "base", "overrides": {}})

    def test_empty_variant_raises(self):
        with pytest.raises(ConfigurationError, match="variant"):
            self.tool.configure(
                {"strategy": "sata", "preset": "base", "variant": "", "overrides": {}}
            )

    def test_non_dict_overrides_raises(self):
        with pytest.raises(ConfigurationError, match="overrides"):
            self.tool.configure(
                {
                    "strategy": "sata",
                    "preset": "as",
                    "variant": "as",
                    "overrides": ["frontier_boost_weight"],
                }
            )

    def test_the_renamed_data_key_is_rejected_under_its_old_name(self):
        # Spec scenario "The renamed data key is rejected under its old name": mop_data
        # is no orchestration key, so an experiment YAML that still names it fails
        # loudly instead of running a cell without its data.
        assert "mop_data" not in APERV_ORCHESTRATION_KEYS
        with pytest.raises(ConfigurationError, match="mop_data"):
            self.tool.configure(
                {
                    "strategy": "sata",
                    "preset": "as",
                    "variant": "as",
                    "mop_data": "static_analysis",
                    "overrides": {},
                }
            )

    def test_configure_makes_copy(self):
        config = _cell("base")
        self.tool.configure(config)
        config["strategy"] = "mutated"
        assert self.tool._tool_config["strategy"] == "sata"

    def test_configure_copies_the_overrides_dict_too(self):
        # A shallow copy would leave the caller's overrides aliased, so a later DSL fold
        # would mutate the variant table itself — every subsequent run of the same cell
        # would inherit the smoke's override.
        config = _cell("as_llm")
        self.tool.configure(config)
        config["overrides"]["llm_url"] = "http://mutated/v1"
        assert self.tool._tool_config["overrides"]["llm_url"] == LLM_URL_DEFAULT

    def test_the_variant_table_is_not_mutated_by_a_fold(self):
        # get_variants() builds its dicts per call, but configure() must not rely on it:
        # folding a DSL key into a registered variant's own overrides dict would leak it.
        variant = ApeRVTool.get_variants()["as_llm"]
        self.tool.configure({**variant, "llm_url": "http://192.168.0.36:30000/v1"})
        assert variant["overrides"] == {"llm_url": LLM_URL_DEFAULT}

    def test_env_var_does_not_override_llm_url_at_l2(self, monkeypatch):
        """INV-TOOL-20: configure() at L2 must not consult os.environ.

        APERV_LLM_BASE_URL is read by the rv-experiment entry point and reaches the
        tool only as a top-level llm_url; L2 reads what the factory-merged config
        provides."""
        monkeypatch.setenv("APERV_LLM_BASE_URL", "http://custom:8080/v1")
        self.tool.configure(_cell("as_llm"))
        # The env var is ignored at L2; the cell's default carries through.
        assert self.tool._tool_config["overrides"]["llm_url"] == LLM_URL_DEFAULT

    def test_env_var_does_not_inject_llm_url_at_l2(self, monkeypatch):
        """INV-TOOL-20: env var with no llm_url in config still produces no llm_url
        at L2. Injection happens at the rv-experiment entry point."""
        monkeypatch.setenv("APERV_LLM_BASE_URL", "http://custom:8080/v1")
        self.tool.configure(_cell("base"))
        assert "llm_url" not in self.tool._tool_config["overrides"]


class TestDslOverrideFold:
    """The tool DSL delivers overrides at the top level; configure() folds them (INV-APV-39).

    ToolFactory merges `{**variant_config, **tool_config.parameters}`, so
    `aperv:as_mop@mop_coin_percentage=0.5` arrives beside `preset` rather than inside
    `overrides` — and `_push_properties()` reads only `overrides`. Without the fold the
    override would produce no property line and no error, and the run would execute a
    configuration nobody asked for. These tests are the reason that cannot happen.
    """

    def setup_method(self):
        self.tool = ApeRVTool()

    def test_dsl_override_is_folded_into_overrides(self):
        self.tool.configure(_cell("as_mop", mop_coin_percentage=0.5))
        assert self.tool._tool_config["overrides"]["mop_coin_percentage"] == 0.5
        assert "mop_coin_percentage" not in self.tool._tool_config

    def test_dsl_override_reaches_the_properties_file(self, tmp_path):
        # Spec scenario "DSL override reaches the properties file".
        self.tool.configure(_cell("as_mop", mop_coin_percentage=0.5))
        assert (
            "ape.mopCoinPercentage=0.5"
            in _written_properties(
                self.tool, tmp_path, artifact_pushed=True
            ).splitlines()
        )

    def test_dsl_value_wins_over_the_cells_own_entry(self, tmp_path):
        # Spec scenario "DSL override wins over the arm's own value": the DSL is the
        # operator's last word.
        self.tool.configure(_cell("as_mop_llm", llm_url="http://192.168.0.36:30000/v1"))
        assert (
            self.tool._tool_config["overrides"]["llm_url"]
            == "http://192.168.0.36:30000/v1"
        )
        lines = _written_properties(self.tool, tmp_path).splitlines()
        llm_url_lines = [ln for ln in lines if ln.startswith("ape.llmUrl=")]
        assert llm_url_lines == ["ape.llmUrl=http://192.168.0.36:30000/v1"]

    def test_llm_url_from_the_environment_variable_replaces_the_default(
        self, tmp_path, monkeypatch
    ):
        # Spec scenario "LLM URL override via environment variable". rv-experiment reads
        # APERV_LLM_BASE_URL and places it in the LLM cell's parameters as llm_url; the
        # factory merges it at the top level beside the cell's own default, and the fold
        # moves it into overrides, where it wins and writes exactly one ape.llmUrl line.
        monkeypatch.setenv("APERV_LLM_BASE_URL", "http://192.168.1.100:30000/v1")
        self.tool.configure(
            {
                "strategy": "sata",
                "preset": "as_llm",
                "variant": "as_llm",
                "static_data": "static_analysis",
                "broadcast_catalog": True,
                "overrides": {"llm_url": "http://10.0.2.2:30000/v1"},
                "llm_url": "http://192.168.1.100:30000/v1",
            }
        )
        assert (
            self.tool._tool_config["overrides"]["llm_url"]
            == "http://192.168.1.100:30000/v1"
        )
        assert "llm_url" not in self.tool._tool_config
        lines = _written_properties(self.tool, tmp_path).splitlines()
        assert [ln for ln in lines if ln.startswith("ape.llmUrl=")] == [
            "ape.llmUrl=http://192.168.1.100:30000/v1"
        ]

    def test_typo_raises_instead_of_vanishing(self):
        # Spec scenario "Unhonourable top-level key fails loudly": `mop_coin_percentag`
        # has no mapping entry. Silently dropping it would run the cell unchanged while
        # the operator believed it had been overridden.
        with pytest.raises(ConfigurationError, match="mop_coin_percentag"):
            self.tool.configure(_cell("as_mop", mop_coin_percentag=0.5))

    def test_orchestration_keys_survive_the_fold(self):
        self.tool.configure(_cell("as_mop_llm", seed=42))
        for key in ("static_data", "broadcast_catalog", "variant", "seed"):
            assert key in self.tool._tool_config
            assert key not in self.tool._tool_config["overrides"]


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
        self.tool.configure(_cell("base"))

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

    def test_adb_timeout_uses_45s_grace(self):
        # gh90 task 5.5 / spec scenario "Timeout budget includes the widened grace
        # window": T + 45, not T + 15 — the old ceiling is where the lost coverage
        # dumps piled up (32 runs stacked against it, none beyond).
        cmd = self.tool._build_main_command(self._make_app(), "emulator-5554", 300)
        assert cmd.timeout == 345

    def test_adb_timeout_is_derived_from_the_shared_grace(self):
        # The command timeout and INV-APV-60's completion floor are the same grace
        # read from opposite sides, so it is stated once. A literal here would let
        # the two drift apart silently.
        cmd = self.tool._build_main_command(self._make_app(), "emulator-5554", 300)
        assert cmd.timeout == 300 + APERV_TEARDOWN_GRACE_S


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


class TestGzipAtCollection:
    """Step 5: compress the raw capture beside the trace (INV-APV-52).

    The step is write-only and non-fatal by design: it may cost a compressed
    copy, never a run's data, and it must leave the artifact of record exactly
    as the jar wrote it.
    """

    def setup_method(self):
        self.tool = ApeRVTool()

    NDJSON = (
        b'{"type":"RUN_START","run_id":"r","t0":1750000000000,"params":{}}\n'
        b'{"type":"ACT","id":1,"name":"com.foo/.Main","mop":1}\n'
        b'{"s":1,"t":10,"act":1,"st":1,"dec":{"a":"CLICK","src":"SATA","ch":"x"}}\n'
    )

    def test_gzip_at_collection_leaves_trace_byte_identical(self, tmp_path):
        """The `.gz` decompresses to the trace, and the trace does not move."""
        trace = tmp_path / "run.trace"
        trace.write_bytes(self.NDJSON)
        before = hashlib.sha256(trace.read_bytes()).hexdigest()

        self.tool._gzip_trace(str(trace))

        assert hashlib.sha256(trace.read_bytes()).hexdigest() == before
        archive = tmp_path / "run.trace.ndjson.gz"
        assert archive.is_file()
        with gzip.open(archive, "rb") as handle:
            assert handle.read() == self.NDJSON

    def test_gzip_keeps_the_trace_stem(self, tmp_path):
        """The suffix is appended, not substituted (design D-3).

        `clock_logcat_join` and `coverage_dump` find a run's sibling files by
        the `.trace` stem, so substituting the suffix would break run identity
        for a cosmetic gain.
        """
        trace = tmp_path / "app.apk__1__1800__aperv.trace"
        trace.write_bytes(self.NDJSON)

        self.tool._gzip_trace(str(trace))

        assert (tmp_path / "app.apk__1__1800__aperv.trace.ndjson.gz").is_file()
        assert not (tmp_path / "app.apk__1__1800__aperv.ndjson.gz").exists()

    def test_gzip_failure_is_non_fatal(self, tmp_path, caplog, monkeypatch):
        """A compression failure warns, names the trace, and changes nothing."""
        trace = tmp_path / "run.trace"
        trace.write_bytes(self.NDJSON)

        def boom(*args, **kwargs):
            raise OSError("No space left on device")

        monkeypatch.setattr(aperv_mod.gzip, "open", boom)

        with caplog.at_level(logging.WARNING):
            self.tool._gzip_trace(str(trace))

        assert "Failed to compress trace" in caplog.text
        assert str(trace) in caplog.text
        assert trace.read_bytes() == self.NDJSON

    def test_gzip_of_missing_trace_does_not_raise(self):
        """Nothing about a missing trace is this step's problem to escalate."""
        self.tool._gzip_trace("/nonexistent/path/run.trace")

    def test_truncated_trace_is_compressed_as_it_stands(self, tmp_path):
        """No validation: a trace cut mid-write is compressed, not inspected.

        Step 5 makes no `RUN_START`/`RUN_END` presence check and interprets no
        exit code (INV-APV-53) — truncated-run identification stays post-hoc.
        """
        truncated = self.NDJSON + b'{"s":2,"t":20,"act":1,"st":'
        trace = tmp_path / "run.trace"
        trace.write_bytes(truncated)

        self.tool._gzip_trace(str(trace))

        with gzip.open(tmp_path / "run.trace.ndjson.gz", "rb") as handle:
            assert handle.read() == truncated


class TestTimeoutPathCollects:
    """Step 8: the timeout path runs collection before re-raising.

    Timeout is how a normal exploration run ends — APE-RV explores until it is
    killed — so this is the majority path. Collecting only on the clean path
    would exempt most runs from collection while looking correct in a test that
    never times out.
    """

    def setup_method(self):
        self.tool = ApeRVTool()

    def test_timeout_path_runs_collection_before_reraise(self, tmp_path):
        self.tool.configure(_cell("base"))

        task = MagicMock()
        task.results_dir = str(tmp_path)
        task.config.apk_name = "app.apk"
        task.config.device_id = "emulator-5554"
        task.config.timeout = 60
        trace = tmp_path / "run.trace"
        trace.write_bytes(b'{"s":1,"t":10,"act":1,"st":1}\n')
        task.result.trace_file = str(trace)

        app = MagicMock()
        app.package_name = "br.unb.cic.cryptoapp"

        (tmp_path / "ape-rv.jar").write_bytes(b"jar")
        self.tool._resolve_jar_path = lambda: str(tmp_path / "ape-rv.jar")
        self.tool._push_file_to_device = lambda *a, **kw: None

        main_cmd = MagicMock()
        main_cmd.invoke.side_effect = RVCommandTimeoutError("killed after 105 s")
        self.tool._build_main_command = lambda *a, **kw: main_cmd

        order = []
        real_gzip = self.tool._gzip_trace
        self.tool._gzip_trace = lambda path: (
            order.append("gzip"),
            real_gzip(path),
        )

        with pytest.raises(RVToolTimeoutError):
            self.tool.execute_tool_specific_logic(task, app)

        # Collection ran, and it ran before the re-raise reached the caller.
        assert order == ["gzip"]
        assert (tmp_path / "run.trace.ndjson.gz").is_file()
        with gzip.open(tmp_path / "run.trace.ndjson.gz", "rb") as handle:
            assert handle.read() == trace.read_bytes()


class TestCompletionIsEstablished:
    """INV-APV-60: a run is not successful merely because the process returned.

    Two runs of the gh97 leg B campaign ended early — one at 1284 s of an 1800 s
    budget when the emulator died (adb exit 255), one at 1012 s when APE-RV stopped
    on its own (exit 1) — and both were stored COMPLETED with error_message null,
    so no resume could reach them. The exit code cannot separate those two from a
    normal run, because APE-RV exits non-zero when it detects an application crash
    during exploration. Elapsed time can: the exploration is budget-bound by
    construction.
    """

    def setup_method(self):
        self.tool = ApeRVTool()
        self.tool.configure(_cell("base"))

    def _clock(self, monkeypatch, *readings):
        monkeypatch.setattr(aperv_mod, "time", _stub_clock(*readings))

    def _run(self, tmp_path, timeout, invoke_result):
        task = MagicMock()
        task.results_dir = str(tmp_path)
        task.config.apk_name = "app.apk"
        task.config.device_id = "emulator-5554"
        task.config.timeout = timeout
        trace = tmp_path / "run.trace"
        trace.write_bytes(b'{"s":1,"t":10,"act":1,"st":1}\n')
        task.result.trace_file = str(trace)

        app = MagicMock()
        app.package_name = "br.unb.cic.cryptoapp"

        (tmp_path / "ape-rv.jar").write_bytes(b"jar")
        self.tool._resolve_jar_path = lambda: str(tmp_path / "ape-rv.jar")
        self.tool._push_file_to_device = lambda *a, **kw: None

        main_cmd = MagicMock()
        if isinstance(invoke_result, Exception):
            main_cmd.invoke.side_effect = invoke_result
        else:
            main_cmd.invoke.return_value = invoke_result
        self.tool._build_main_command = lambda *a, **kw: main_cmd

        self.tool.execute_tool_specific_logic(task, app)

    def test_truncated_run_raises_naming_elapsed_and_budget(
        self, tmp_path, monkeypatch
    ):
        # net.pfiers.osmfocus rep 1 as it actually happened: back at 1012 s of 1800,
        # exit 1, emulator alive. Before this check it was stored COMPLETED.
        self._clock(monkeypatch, 1000.0, 1000.0 + 1012)

        with pytest.raises(RVToolExecutionError) as excinfo:
            self._run(tmp_path, 1800, MagicMock(code=1))

        message = str(excinfo.value)
        assert "1012" in message
        assert "1800" in message

    def test_truncated_run_still_compresses_the_trace(self, tmp_path, monkeypatch):
        # The artifacts of a truncated run are the evidence of what truncated it,
        # so the new exit path compresses before it raises, like the other two.
        self._clock(monkeypatch, 1000.0, 1000.0 + 1284)

        with pytest.raises(RVToolExecutionError):
            self._run(tmp_path, 1800, MagicMock(code=255))

        assert (tmp_path / "run.trace.ndjson.gz").is_file()

    def test_full_budget_with_nonzero_exit_does_not_raise(self, tmp_path, monkeypatch):
        # The campaign's 357 intact runs spanned 1860-1909 s against an 1800 s budget,
        # many of them exiting non-zero because the application under test crashed —
        # which is data the run exists to collect, not a failure.
        self._clock(monkeypatch, 1000.0, 1000.0 + 1860)

        self._run(tmp_path, 1800, MagicMock(code=211))

        assert (tmp_path / "run.trace.ndjson.gz").is_file()

    def test_return_inside_the_teardown_grace_does_not_raise(
        self, tmp_path, monkeypatch
    ):
        # The floor is budget minus the grace the command already carries, so a run
        # that ended a few seconds early is a normal ending, not a truncation.
        self._clock(monkeypatch, 1000.0, 1000.0 + (1800 - APERV_TEARDOWN_GRACE_S))

        self._run(tmp_path, 1800, MagicMock(code=0))

    def test_timeout_path_is_untouched(self, tmp_path, monkeypatch):
        # A timeout is the expected, successful ending: it must still raise
        # RVToolTimeoutError — which rv-platform records as a completed run — and
        # must not be re-judged by the completion check, whatever the clock says.
        self._clock(monkeypatch, 1000.0, 1000.0 + 10)

        with pytest.raises(RVToolTimeoutError):
            self._run(tmp_path, 1800, RVCommandTimeoutError("killed after 1845 s"))

        assert (tmp_path / "run.trace.ndjson.gz").is_file()


class TestFrozenCorpusCarveOut:
    """INV-APV-55: the frozen legacy-corpus readers are not migrated.

    These scripts read the archived corpus behind the 2026-07-24 calibration
    report and the decisive run — a dataset that will not be regenerated. They
    are not compatibility shims keeping a superseded implementation alive for
    new data, so P3 does not reach them: it governs superseded *implementation*,
    not analysis code over frozen data. The operational test is simple —
    `clock_logcat_join.py` migrated because it must read *new* traces; these
    never will.
    """

    # Repo root: modules/aperv-tool/tests/ -> modules/aperv-tool -> modules -> root
    REPO_ROOT = Path(__file__).resolve().parents[3]

    FROZEN_FILES = ("scripts/cmpm_stratify.py", "scripts/analyze_cmpv2_llm.py")
    FROZEN_DIRS = (
        "experimento-cal/scripts",
        "experimento-20260721/scripts",
        "calibracao",
    )

    def _frozen_sources(self):
        paths = [self.REPO_ROOT / name for name in self.FROZEN_FILES]
        for directory in self.FROZEN_DIRS:
            paths.extend(sorted((self.REPO_ROOT / directory).rglob("*.py")))
        return [path for path in paths if path.is_file()]

    def test_frozen_corpus_scripts_untouched(self):
        """None of them was adapted to the new reader.

        The assertion is about content rather than a `git diff`, deliberately.
        Several of these files carry unrelated working-tree edits that predate
        this change, so a diff-based check would report noise from elsewhere as
        a violation of this carve-out and would say nothing about the property
        the invariant protects. What it protects is that the migration did not
        reach them: they still parse the legacy `[APE-*]` `key=value` family and
        none of them imports the NDJSON reader.
        """
        sources = self._frozen_sources()
        assert len(sources) >= len(self.FROZEN_FILES), "frozen script paths not found"

        migrated = [
            str(path.relative_to(self.REPO_ROOT))
            for path in sources
            if "trace_ndjson" in path.read_text(encoding="utf-8", errors="replace")
        ]
        assert migrated == [], f"frozen-corpus scripts were migrated: {migrated}"

    def test_frozen_corpus_scripts_still_parse_the_legacy_family(self):
        """At least one reader per carve-out region still reads `[APE-*]`.

        This is the non-vacuity half: if the legacy parsers had been quietly
        removed, the assertion above would pass over files that no longer read
        anything, and the carve-out would be protecting nothing.
        """
        legacy_readers = [
            path
            for path in self._frozen_sources()
            if "[APE-" in path.read_text(encoding="utf-8", errors="replace")
        ]
        assert legacy_readers, "no frozen script parses the legacy line family"


class TestNoExitContract:
    """INV-APV-53: nothing on the collection path reads `RUN_END`."""

    def test_no_collection_path_reads_run_end(self):
        """The sentinel is write-only, so no source file here may mention it.

        Owner decision D5: no presence check, no exit-code interpretation, no
        task-status change and no retry logic keyed on it. A source-level
        assertion is the right shape because the rule is about what the code is
        allowed to know, not about a behavior a fixture could exercise.
        """
        collection_root = Path(aperv_mod.__file__).parent
        offenders = [
            path.name
            for path in sorted(collection_root.rglob("*.py"))
            if "RUN_END" in path.read_text(encoding="utf-8")
        ]
        assert offenders == []


class TestPushPropertiesLlm:
    """Verify _push_properties() writes the LLM server URL and nothing the preset owns."""

    def setup_method(self):
        self.tool = ApeRVTool()

    @pytest.mark.parametrize("name", LLM_CELLS)
    def test_llm_cell_writes_the_url_and_nothing_else(self, tmp_path, name):
        # The sampling block belongs to the LLM group's preset block; only the server URL
        # is deployment-specific, so only it crosses as an override (INV-APV-38).
        self.tool.configure(_cell(name))
        props = _written_properties(self.tool, tmp_path, artifact_pushed=True)
        assert f"ape.llmUrl={LLM_URL_DEFAULT}" in props.splitlines()
        for preset_owned in (
            "ape.llm=",
            "ape.llmOnNewState",
            "ape.llmOnStagnation",
            "ape.llmModel",
            "ape.llmTemperature",
            "ape.llmTopP",
            "ape.llmTopK",
            "ape.llmTimeoutMs",
            "ape.llmPercentage",
        ):
            assert preset_owned not in props

    def test_llm_properties_absent_for_a_non_llm_cell(self, tmp_path):
        self.tool.configure(_cell("base"))
        assert "ape.llm" not in _written_properties(self.tool, tmp_path)


class TestPushProperties:
    """Verify "ape.properties Composition": preset, variant, data path, then deltas."""

    def setup_method(self):
        self.tool = ApeRVTool()

    def _capture_properties(self, tmp_path, config, artifact_pushed=False):
        """Helper: configure tool, call _push_properties, return its lines."""
        self.tool.configure(config)
        props = _written_properties(self.tool, tmp_path, artifact_pushed)
        return [line for line in props.split("\n") if line]

    def test_preset_and_variant_lines_come_first(self, tmp_path):
        # Spec scenario "Preset and variant lines come first".
        lines = self._capture_properties(
            tmp_path, _cell("as_mop_llm"), artifact_pushed=True
        )
        assert lines == [
            "ape.preset=as_mop_llm",
            "ape.variant=as_mop_llm",
            f"ape.staticDataPath={DEVICE_ARTIFACT_PATH}",
            "ape.llmUrl=http://10.0.2.2:30000/v1",
        ]

    def test_the_mop_ledger_ablation_writes_its_key(self, tmp_path):
        # Spec scenario "The MOP ledger ablation is the mop cell with one key".
        lines = self._capture_properties(
            tmp_path, _cell("mop_k2"), artifact_pushed=True
        )
        assert lines == [
            "ape.preset=mop",
            "ape.variant=mop_k2",
            f"ape.staticDataPath={DEVICE_ARTIFACT_PATH}",
            "ape.mopCoinLedgerMaxInteractions=2",
        ]

    def test_a_cell_with_data_writes_exactly_three_lines(self, tmp_path):
        # Spec scenario "Properties file carries preset plus deltas only".
        lines = self._capture_properties(
            tmp_path, _cell("as_mop"), artifact_pushed=True
        )
        assert lines == [
            "ape.preset=as_mop",
            "ape.variant=as_mop",
            "ape.staticDataPath=/data/local/tmp/mop-artifact.json",
        ]
        assert not [ln for ln in lines if ln.startswith("ape.mopDataPath")]

    def test_base_cell_writes_two_lines(self, tmp_path):
        # Spec scenario "Base cell writes two lines".
        lines = self._capture_properties(tmp_path, _cell("base"))
        assert lines == ["ape.preset=base", "ape.variant=base"]

    def test_the_default_variant_runs_as_base(self, tmp_path):
        # Spec scenario "The default variant runs as base".
        lines = self._capture_properties(tmp_path, _cell("default"))
        assert lines == ["ape.preset=base", "ape.variant=base"]

    def test_the_data_line_needs_the_push(self, tmp_path):
        # ape.staticDataPath names a file on the device, so it is written only when the
        # artifact was pushed, whatever the variant declares.
        lines = self._capture_properties(tmp_path, _cell("as_mop"))
        assert lines == ["ape.preset=as_mop", "ape.variant=as_mop"]

    def test_a_dose_ablation_writes_the_dose(self, tmp_path):
        # Spec scenario "A dose ablation writes the dose".
        lines = self._capture_properties(
            tmp_path, _cell("as_mop_llm", llm_percentage=0.7), artifact_pushed=True
        )
        assert "ape.llmPercentage=0.7" in lines
        assert not [ln for ln in lines if ln.startswith("ape.mopCoinPercentage")]

    def test_deltas_are_written_in_mapping_order(self, tmp_path):
        # Order follows APERV_PROPERTY_MAPPING rather than the variant dict, so two runs of
        # the same variant produce byte-identical files however the dict was authored.
        lines = self._capture_properties(
            tmp_path,
            _cell(
                "as_mop",
                overrides={"mop_coin_percentage": 0.5, "default_epsilon": 0.08},
            ),
        )
        assert lines[:2] == ["ape.preset=as_mop", "ape.variant=as_mop"]
        assert lines.index("ape.defaultEpsilon=0.08") < lines.index(
            "ape.mopCoinPercentage=0.5"
        )

    def test_bools_are_serialized_lowercase(self, tmp_path):
        # Spec scenario "Bools are serialized lowercase".
        lines = self._capture_properties(
            tmp_path, _cell("as", heuristic_input=False, mop=True)
        )
        assert "ape.heuristicInput=false" in lines
        assert "ape.mop=true" in lines
        assert not [ln for ln in lines if "True" in ln or "False" in ln]

    def test_python_only_keys_not_written(self, tmp_path):
        # Spec scenario "Python-only keys are still excluded".
        props = "\n".join(
            self._capture_properties(
                tmp_path,
                _cell("as_mop", seed=42, llm_snap_tolerance_px=120),
                artifact_pushed=True,
            )
        )
        for python_only in ("strategy", "static_data", "broadcast_catalog", "seed"):
            assert python_only not in props
        # ...while an ordinary override on the same cell travels the normal path.
        assert "ape.llmSnapTolerancePx=120" in props

    def test_platform_device_addressing_keys_are_accepted(self, tmp_path):
        # Spec scenario "The platform's device addressing is accepted and never written".
        # rv-experiment's ExecutionController injects device_port/device_serial/device_id
        # into every tool's parameters whenever --device-port is set. They address a
        # device; they do not configure the jar, so they are accepted and never reach
        # ape.properties.
        lines = self._capture_properties(
            tmp_path,
            _cell(
                "as_mop",
                device_port=5554,
                device_serial="emulator-5554",
                device_id="emulator-5554",
            ),
            artifact_pushed=True,
        )
        props = "\n".join(lines)
        for injected in ("device_port", "device_serial", "device_id", "5554"):
            assert injected not in props
        assert lines == [
            "ape.preset=as_mop",
            "ape.variant=as_mop",
            f"ape.staticDataPath={DEVICE_ARTIFACT_PATH}",
        ]

    def test_unmapped_override_key_aborts_in_configure(self):
        # Spec scenario "Unmapped override key aborts before push": configure() is where
        # it has to be caught, because the jar, the broadcast catalog and the derived
        # artifact are all pushed before ape.properties is generated (INV-APV-02).
        def fail_on_push(*args, **kwargs):
            raise AssertionError("an unmapped override reached the device")

        self.tool._push_file_to_device = fail_on_push
        with pytest.raises(ConfigurationError, match="mop_coin_percentag"):
            self.tool.configure(_cell("as_mop", overrides={"mop_coin_percentag": 0.5}))

    def test_no_semantic_validation_of_override_values(self, tmp_path):
        # Spec scenario "No semantic validation is performed on override values": llm_url
        # on a cell without LLM is written unchanged, and the jar rejects it.
        lines = self._capture_properties(
            tmp_path, _cell("as_mop", llm_url=LLM_URL_DEFAULT), artifact_pushed=True
        )
        assert f"ape.llmUrl={LLM_URL_DEFAULT}" in lines


class TestRetiredGuards:
    """The guard machinery is gone, and a revert would be caught rather than merged.

    `ARM_DEFINING_KEYS`, `_ARM_DEFINING_EXEMPT` and `LLM_ARM_KEYS` were explicitness
    obligations over the per-arm dictionaries. With an arm expressed as a preset plus its
    deltas there is no expansion left to keep complete, and a missing or misspelled key
    aborts the run in the jar instead of passing silently — a stronger check than the one
    being retired, because it is applied to the binary that actually runs.

    Their substitute is recorded rather than assumed: the jar's fail-fast resolution, the
    one-time regeneration diff in tests/migration/, and the write-only RUN_START echo that
    makes "which arm ran this task" answerable from the trace alone. Deliberately no runtime
    replacement (owner decision D1).
    """

    @pytest.mark.parametrize(
        "name", ["ARM_DEFINING_KEYS", "_ARM_DEFINING_EXEMPT", "LLM_ARM_KEYS"]
    )
    def test_the_guard_constants_are_gone(self, name):
        assert not hasattr(aperv_mod, name), (
            f"{name} is back. It validated Python constants against other Python "
            "constants about arms that no longer carry expansions; the jar's fail-fast "
            "resolution replaced it."
        )

    @pytest.mark.parametrize(
        "name",
        [
            "_BASELINE_ARM_FLAGS",
            "_APE_PURE_ARM_FLAGS",
            "_MOP_SUBSTRATE",
            "_LLM_FLAGS",
            "_FRONTIER_SUBSTRATE",
            "_MOP_OFF_OVERRIDES",
            "_CAL_LLM_COMMON",
        ],
    )
    def test_the_substrate_dicts_are_gone(self, name):
        # When a producer is deleted its outputs go too: a substrate dict with no arm
        # spreading it is the dead shim P3 forbids.
        assert not hasattr(aperv_mod, name), f"{name} is back"

    def test_no_run_start_parsing(self):
        # INV-APV-43 (owner decision D1): the tool writes the trace and never reads it
        # back. Drift auditing is post-hoc analysis, not a runtime check — adding one here
        # would recreate the guard family under a new name.
        source = Path(aperv_mod.__file__).read_text()

        assert "RUN_START" not in source
        assert "RUN_END" not in source


class TestPropertyMapping:
    """The pass-through table: what it translates, and what it must not carry."""

    # The thirteen entries the group-isolation jar's vocabulary adds to the table.
    ADDED = {
        "addons": "ape.addons",
        "static": "ape.static",
        "mop": "ape.mop",
        "llm": "ape.llm",
        "mop_coin_percentage": "ape.mopCoinPercentage",
        "mop_coin_ledger_max_interactions": "ape.mopCoinLedgerMaxInteractions",
        "llm_gate_min_actions": "ape.llmGateMinActions",
        "llm_breaker_failures": "ape.llmBreakerFailures",
        "llm_breaker_open_ms": "ape.llmBreakerOpenMs",
        "activity_stable_restart_threshold": "ape.activityStableRestartThreshold",
        "take_screenshot_for_every_step": "ape.takeScreenshotForEveryStep",
        "save_gui_tree_to_xml_every_step": "ape.saveGUITreeToXmlEveryStep",
        "llm_boundary_top_pct": "ape.llmBoundaryTopPct",
    }

    def test_the_mapping_holds_the_group_isolation_vocabulary(self):
        # Spec scenario "The mapping holds the group-isolation vocabulary".
        assert len(APERV_PROPERTY_MAPPING) == 67
        assert {key: APERV_PROPERTY_MAPPING[key] for key in self.ADDED} == self.ADDED
        for absent in (
            "mop_target_pick_cap",
            "least_visited_priority_tiebreak",
            "mop_weight_activity",
            "step_telemetry_enabled",
            "variant",
            "preset",
        ):
            assert absent not in APERV_PROPERTY_MAPPING, absent

    def test_no_entry_writes_a_fixed_or_retired_line(self):
        # Spec scenario "Dead key removed": the data path and the preset/variant lines
        # come from the variant and the push, never from an override, and the jar aborts
        # on its retired keys.
        for written in (
            "ape.preset",
            "ape.variant",
            "ape.staticDataPath",
            "ape.mopDataPath",
            "ape.mopTargetPickCap",
            "ape.leastVisitedPriorityTiebreak",
        ):
            assert written not in APERV_PROPERTY_MAPPING.values(), written

    def test_no_orchestration_key_is_mapped(self):
        # A key in both sets would be folded into overrides and written as a property,
        # while the code that reads it at the top level would never see it.
        assert not set(APERV_PROPERTY_MAPPING) & APERV_ORCHESTRATION_KEYS

    def test_the_orchestration_keys(self):
        assert APERV_ORCHESTRATION_KEYS == {
            "preset",
            "variant",
            "overrides",
            "strategy",
            "static_data",
            "broadcast_catalog",
            "seed",
            "device_port",
            "device_serial",
            "device_id",
        }

    def test_the_distance_keys_are_mapped(self):
        assert {
            python_key: APERV_PROPERTY_MAPPING[python_key]
            for python_key in (
                "mop_scoring",
                "mop_weight_d1",
                "mop_weight_d2",
                "mop_weight_d3",
                "mop_retire_after",
                "mop_launcher_dmax",
            )
        } == {
            "mop_scoring": "ape.mopScoring",
            "mop_weight_d1": "ape.mopWeightD1",
            "mop_weight_d2": "ape.mopWeightD2",
            "mop_weight_d3": "ape.mopWeightD3",
            "mop_retire_after": "ape.mopRetireAfter",
            "mop_launcher_dmax": "ape.mopLauncherDmax",
        }

    def test_the_live_llm_sub_parameters_stay_mapped(self):
        # Spec scenario "Live ungoverned key travels the normal path".
        assert APERV_PROPERTY_MAPPING["llm_max_tokens"] == "ape.llmMaxTokens"
        assert (
            APERV_PROPERTY_MAPPING["llm_snap_tolerance_px"] == "ape.llmSnapTolerancePx"
        )


class TestCorpusBasis:
    """The run states which application list it was drawn from (INV-APV-56).

    The value is provenance the caller supplies, not a digest this module computes:
    `aperv-tool` does not own the corpus list, does not know where it lives, and
    must not grow a filesystem dependency on a campaign's layout in order to hash
    it. What it owns is the contract — the shape of the value, its validation
    before anything reaches a device, and the guarantee that an unstated corpus
    produces an absent key rather than a defaulted one.
    """

    BASIS = "subset40:b60903adf4c8fca07e014e3655db158a220184d112f2f995a181fd98dd3d48d4"

    def setup_method(self):
        self.tool = ApeRVTool()

    def test_the_key_is_mapped_to_the_jars_own_name(self):
        # `ape.corpusBasis` is what KeyOwnership declares; a mistyped Java name would be
        # rejected by the jar's resolver and abort the run before step 1.
        assert APERV_PROPERTY_MAPPING["corpus_basis"] == "ape.corpusBasis"

    def test_the_configured_basis_is_written_byte_identical(self, tmp_path):
        # Byte-identical is the point: the pre-flight compares this line's value against
        # a digest recomputed from the list file, so any normalization here — a case
        # change, a strip, a re-derivation — would turn a match into a false mismatch.
        self.tool.configure(_cell("as_mop", overrides={"corpus_basis": self.BASIS}))
        props = _written_properties(self.tool, tmp_path, artifact_pushed=True)
        assert f"ape.corpusBasis={self.BASIS}" in props.splitlines()

    def test_the_dsl_seam_carries_it_from_the_top_level(self, tmp_path):
        # This is the seam the campaign uses: `aperv:<cell>@corpus_basis=subset40:<sha>`
        # arrives merged at the TOP level of the config, and configure()'s fold is what
        # moves it into `overrides` where _push_properties() reads. Without the mapping
        # entry the key would be rejected as unrecognised instead of silently dropped —
        # which is the behaviour this asserts is not needed.
        self.tool.configure(_cell("as_mop", corpus_basis=self.BASIS))
        assert self.tool._tool_config["overrides"]["corpus_basis"] == self.BASIS
        assert f"ape.corpusBasis={self.BASIS}" in _written_properties(
            self.tool, tmp_path
        )

    def test_an_absent_basis_emits_no_key(self, tmp_path):
        # INV-APV-56. Absence is a legitimate state — every campaign before this one ran
        # without it, and every standalone invocation still does — so there is no
        # placeholder, no empty value and no warning.
        self.tool.configure(_cell("base"))
        assert "ape.corpusBasis" not in _written_properties(self.tool, tmp_path)

    @pytest.mark.parametrize(
        "rejected",
        [
            "subset40",  # an identifier with no digest
            "subset40:" + "b" * 63,  # one hex digit short
            "subset40:" + "B" * 64,  # uppercase: a different byte string
            "subset40:" + "z" * 64,  # right length, not hexadecimal
            ":" + "b" * 64,  # no identifier to read in a report
            "sub set40:" + "b" * 64,  # a space would break the properties line
            40,  # not a string at all
        ],
    )
    def test_a_malformed_basis_is_rejected_before_the_device(self, rejected):
        """The raise comes from `configure()`, so no emulator time is spent on it.

        The push sentinel below is what makes that concrete rather than assumed: if
        validation ever moved into `_push_properties()`, the jar, the broadcast
        catalog and the MOP artifact would already have been pushed by the time the
        error surfaced.
        """

        def fail_on_push(*args, **kwargs):
            raise AssertionError("a malformed basis reached the device")

        self.tool._push_file_to_device = fail_on_push

        with pytest.raises(ConfigurationError) as excinfo:
            self.tool.configure(_cell("as_mop", overrides={"corpus_basis": rejected}))
        message = str(excinfo.value)
        assert "corpus_basis" in message
        assert repr(rejected) in message

    def test_a_well_formed_basis_is_accepted_whatever_it_names(self):
        # Shape is all this side validates: whether the digest corresponds to any list
        # is checked where the list lives, by recomputing it. A tool that verified the
        # digest would need to know the campaign's directory layout to find the file.
        self.tool.configure(
            _cell(
                "as_mop",
                overrides={"corpus_basis": "a_corpus.v2-1:" + "0123456789abcdef" * 4},
            )
        )


class TestRunStartIsWriteOnly:
    """INV-APV-57: no execution-path module reads `RUN_START`, corpus basis included.

    The property is pushed and never read back, mirroring `run-spec` INV-RUN-03 —
    which declares `RUN_START` write-only at level 0 — and `gh95` decision D1. A
    runtime echo-vs-intent validator here would contradict a level-0 invariant of
    the other repository and would rebuild the retired guard family under a new name.

    The sweep carves out `analysis/`, and the carve-out is the invariant rather than
    an exception to it: `RUN_START` is *supposed* to be consumed there, by post-hoc
    readers over recorded traces. That is where the campaign's pre-flight verifies
    the echoed basis.
    """

    SRC_ROOT = Path(aperv_mod.__file__).parents[2]
    POST_HOC_PACKAGE = "analysis"

    def _execution_path_sources(self):
        return [
            path
            for path in sorted(self.SRC_ROOT.rglob("*.py"))
            if self.POST_HOC_PACKAGE not in path.relative_to(self.SRC_ROOT).parts
        ]

    def test_no_execution_path_module_reads_run_start(self):
        offenders = [
            str(path.relative_to(self.SRC_ROOT))
            for path in self._execution_path_sources()
            if "RUN_START" in path.read_text(encoding="utf-8")
        ]
        assert offenders == [], f"execution-path modules mention RUN_START: {offenders}"

    def test_the_sweep_covers_the_module_that_pushes_the_property(self):
        # Non-vacuity, first half: a sweep whose file list silently emptied — a moved
        # package, a renamed directory — would pass while checking nothing.
        swept = {path.name for path in self._execution_path_sources()}
        assert "tool.py" in swept
        assert "derive_mop_artifact.py" in swept

    def test_the_same_search_finds_the_post_hoc_readers(self):
        # Non-vacuity, second half: the search really does match this token where the
        # token exists. Without this, a typo in the pattern would make the assertion
        # above green by construction.
        readers = [
            path.name
            for path in sorted((self.SRC_ROOT / self.POST_HOC_PACKAGE).rglob("*.py"))
            if "RUN_START" in path.read_text(encoding="utf-8")
        ]
        assert "trace_ndjson.py" in readers


class TestNoExternalArtifactIdentityInSource:
    """INV-APV-59: source never names the revision or digest of an external build.

    A variant declaring `expected_jar_git_sha` or `expected_jar_sha256` would pin the
    revision and digest of one `ape-rv.jar` build as literals. `ape-rv.jar` is built in
    a sibling repository whose build is not bit-reproducible, so the same revision
    yields a different digest every time it is built: a gate on the pin fails on
    correct redeployments and passes on stale ones, and a routine rebuild becomes an
    edit of a Python constant here.

    Identity is recorded by measurement rather than declaration:
    `_capture_llm_provenance()` digests the jar it is about to push into
    `jar_sha256`. This class exists so the pin cannot return under another name.
    """

    SRC_ROOT = Path(aperv_mod.__file__).parents[2]

    # A git sha is 40 hex characters and a sha256 is 64. Word boundaries keep the
    # pattern off longer alphanumeric runs (base64 blobs, device serials).
    ARTIFACT_DIGEST = re.compile(r"\b[0-9a-fA-F]{40}\b|\b[0-9a-fA-F]{64}\b")

    def test_no_source_file_carries_a_digest_or_revision_literal(self):
        offenders = {
            str(path.relative_to(self.SRC_ROOT)): self.ARTIFACT_DIGEST.findall(
                path.read_text(encoding="utf-8")
            )
            for path in sorted(self.SRC_ROOT.rglob("*.py"))
            if self.ARTIFACT_DIGEST.search(path.read_text(encoding="utf-8"))
        }
        assert offenders == {}, (
            f"external artifact identity declared in source: {offenders}"
        )

    def test_no_arm_declares_an_expected_artifact(self):
        # The keys are also absent from APERV_ORCHESTRATION_KEYS, so an experiment YAML
        # or a tool-DSL override reintroducing either one is rejected by configure()
        # rather than silently carried — the declaration cannot come back through data.
        for name, variant in ApeRVTool.get_variants().items():
            declared = [key for key in variant if key.startswith("expected_")]
            assert declared == [], f"{name} declares {declared}"

        assert "expected_jar_git_sha" not in APERV_ORCHESTRATION_KEYS
        assert "expected_jar_sha256" not in APERV_ORCHESTRATION_KEYS

    def test_the_pattern_matches_the_shapes_it_is_meant_to_catch(self):
        # Non-vacuity: without this, a broken pattern would make the sweep above green by
        # matching nothing. The samples are synthetic hex of the two lengths — a git sha
        # and a sha256 — rather than the real literals this change deleted, because a test
        # that pinned a real digest to prove digests are banned would be the thing it bans.
        assert self.ARTIFACT_DIGEST.search(f'"{"a" * 40}"')
        assert self.ARTIFACT_DIGEST.search(f'"{"b" * 64}"')
        assert not self.ARTIFACT_DIGEST.search(f'"{"c" * 39}"')


class TestSeedPropagation:
    """Group 3: seed reaches the jar as -s <seed>, never ape.properties (INV-APV-18)."""

    def setup_method(self):
        self.tool = ApeRVTool()
        self.tool.configure(_cell("base"))

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
    # The producer's shape: a list of classes, each carrying its methods[] with the
    # reachable / reachesTarget / directlyReachesTarget bits (gh90 N6 reads it).
    "reachability": [
        {
            "className": "br.unb.cic.cryptoapp.MainActivity",
            "componentType": "ACTIVITY",
            "isMain": True,
            "methods": [
                {
                    "name": "onCreate",
                    "signature": (
                        "<br.unb.cic.cryptoapp.MainActivity: "
                        "void onCreate(android.os.Bundle)>"
                    ),
                    "reachable": True,
                    "reachesTarget": True,
                    "directlyReachesTarget": False,
                }
            ],
        }
    ],
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


CRYPTOAPP_FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "cryptoapp.apk.json"
)


def _write_source(tmp_path, document=None, raw=None):
    """Write a source JSON (pretty-printed, as the producer emits it)."""
    path = tmp_path / "app.apk.json"
    if raw is not None:
        path.write_text(raw)
    else:
        path.write_text(json.dumps(document, indent=2))
    return str(path)


# --- gh96: host-side MOP artifact derivation ---------------------------------


class TestDeriveMopArtifact:
    """`_derive_mop_artifact()`: the digest cache and the atomic write."""

    def setup_method(self):
        self.tool = ApeRVTool()

    def _task(self, tmp_path):
        task = MagicMock()
        task.results_dir = str(tmp_path)
        task.config.apk_name = "app.apk"
        return task

    def _artifact_path(self, tmp_path):
        return tmp_path / "app.apk.mop.json"

    def test_derives_and_writes_the_artifact(self, tmp_path):
        _write_source(tmp_path, SOURCE_DOCUMENT)

        path = self.tool._derive_mop_artifact(self._task(tmp_path))

        assert path == str(self._artifact_path(tmp_path))
        artifact = json.loads(self._artifact_path(tmp_path).read_text())
        assert artifact["formatVersion"] == 2
        assert artifact["package"] == "br.unb.cic.cryptoapp"
        assert artifact["source"]["file"] == "app.apk.json"

    def test_cache_hit_skips_derivation(self, tmp_path, monkeypatch):
        # Spec scenario "cache hit skips derivation": a matching digest is the whole
        # freshness test, so the second call must not re-derive, and must not parse
        # the source either: on a large document the parse is the expensive part.
        source = _write_source(tmp_path, SOURCE_DOCUMENT)
        task = self._task(tmp_path)
        self.tool._derive_mop_artifact(task)
        first = self._artifact_path(tmp_path).read_bytes()

        def forbidden(*args, **kwargs):
            raise AssertionError("a fresh cache must not be re-derived")

        # The cache reader parses the small cached artifact, and `json.load` parses
        # through `json.loads`; only a parse of the source is off limits.
        real_load, real_loads = json.load, json.loads
        source_text = Path(source).read_text()

        def load_but_not_the_source(fp, *args, **kwargs):
            if getattr(fp, "name", None) == source:
                raise AssertionError("a cache hit must not parse the source")
            return real_load(fp, *args, **kwargs)

        def loads_but_not_the_source(text, *args, **kwargs):
            if text in (source_text, source_text.encode()):
                raise AssertionError("a cache hit must not parse the source")
            return real_loads(text, *args, **kwargs)

        monkeypatch.setattr(aperv_mod, "derive", forbidden)
        monkeypatch.setattr(aperv_mod, "read_analysis_document", forbidden)
        monkeypatch.setattr(aperv_mod.json, "load", load_but_not_the_source)
        monkeypatch.setattr(aperv_mod.json, "loads", loads_but_not_the_source)

        assert self.tool._derive_mop_artifact(task) == str(
            self._artifact_path(tmp_path)
        )
        assert self._artifact_path(tmp_path).read_bytes() == first

    def test_stale_cache_regenerates(self, tmp_path):
        # Spec scenario "stale cache regenerates": the artifact must describe the
        # JSON that is there now, not the one that was there when it was written.
        _write_source(tmp_path, SOURCE_DOCUMENT)
        task = self._task(tmp_path)
        self.tool._derive_mop_artifact(task)

        changed = {**SOURCE_DOCUMENT, "package": "com.example.other"}
        _write_source(tmp_path, changed)
        self.tool._derive_mop_artifact(task)

        artifact = json.loads(self._artifact_path(tmp_path).read_text())
        assert artifact["package"] == "com.example.other"
        assert artifact["source"]["digest"] == aperv_mod.digest_of_file(
            str(tmp_path / "app.apk.json")
        )

    def test_corrupt_cache_regenerates(self, tmp_path):
        # An unreadable cache is a miss, not a failure: regenerating costs
        # milliseconds and refusing would fail a run over a scratch file.
        _write_source(tmp_path, SOURCE_DOCUMENT)
        self._artifact_path(tmp_path).write_text("{ truncated")

        self.tool._derive_mop_artifact(self._task(tmp_path))

        assert (
            json.loads(self._artifact_path(tmp_path).read_text())["formatVersion"] == 2
        )

    def test_cached_artifact_of_an_older_format_regenerates(
        self, tmp_path, monkeypatch
    ):
        # Spec scenario "cached artifact of an older format regenerates": the digest
        # names the input, not the derivation, so a format-1 artifact derived before
        # the bump matches its source and would reach a jar that rejects it.
        source = _write_source(tmp_path, SOURCE_DOCUMENT)
        self._artifact_path(tmp_path).write_text(
            json.dumps(
                {
                    "formatVersion": 1,
                    "source": {
                        "digest": aperv_mod.digest_of_file(source),
                        "file": "app.apk.json",
                        "generator": "aperv-derive/1",
                    },
                }
            )
        )
        calls = []
        real_derive = aperv_mod.derive

        def counting_derive(*args, **kwargs):
            calls.append(args)
            return real_derive(*args, **kwargs)

        monkeypatch.setattr(aperv_mod, "derive", counting_derive)

        self.tool._derive_mop_artifact(self._task(tmp_path))

        assert len(calls) == 1
        artifact = json.loads(self._artifact_path(tmp_path).read_text())
        assert artifact["formatVersion"] == 2
        assert artifact["source"]["generator"] == "aperv-derive/2"

    def test_failed_derivation_leaves_no_file(self, tmp_path):
        # Spec scenario "failed derivation leaves no artifact behind": a section of
        # the wrong type is a producer bug that must not arm a run, and must leave
        # no temp behind either.
        _write_source(tmp_path, {**SOURCE_DOCUMENT, "windows": "none"})
        before = set(os.listdir(tmp_path))

        with pytest.raises(RVToolExecutionError) as raised:
            self.tool._derive_mop_artifact(self._task(tmp_path))

        assert "windows" in str(raised.value)
        assert not self._artifact_path(tmp_path).exists()
        assert set(os.listdir(tmp_path)) == before

    def test_unparseable_source_raises(self, tmp_path):
        _write_source(tmp_path, raw="{not valid json")

        with pytest.raises(RVToolExecutionError):
            self.tool._derive_mop_artifact(self._task(tmp_path))

        assert not self._artifact_path(tmp_path).exists()

    def test_cache_miss_streams_the_source(self, tmp_path, monkeypatch):
        # INV-APV-64: a miss reads the source in streaming. A whole-document parse
        # of a gh120 document peaks at about 3.1 times its size, which is three
        # campaign containers for the largest one.
        source = _write_source(tmp_path, SOURCE_DOCUMENT)
        source_text = Path(source).read_text()
        real_load, real_loads = json.load, json.loads

        def load_but_not_the_source(fp, *args, **kwargs):
            if getattr(fp, "name", None) == source:
                raise AssertionError("the source must not be parsed whole")
            return real_load(fp, *args, **kwargs)

        def loads_but_not_the_source(text, *args, **kwargs):
            if text in (source_text, source_text.encode()):
                raise AssertionError("the source must not be parsed whole")
            return real_loads(text, *args, **kwargs)

        monkeypatch.setattr(aperv_mod.json, "load", load_but_not_the_source)
        monkeypatch.setattr(aperv_mod.json, "loads", loads_but_not_the_source)

        self.tool._derive_mop_artifact(self._task(tmp_path))

        assert self._artifact_path(tmp_path).exists()

    def test_streaming_byte_identical_on_cryptoapp(self, tmp_path):
        # Spec scenario "the streaming derivation is byte-identical to the
        # whole-document one", through the method the run calls.
        source = tmp_path / "app.apk.json"
        source.write_bytes(Path(CRYPTOAPP_FIXTURE).read_bytes())
        with open(source, encoding="utf-8") as handle:
            expected = serialize_canonical(
                derive(
                    json.load(handle),
                    source_file="app.apk.json",
                    source_digest=aperv_mod.digest_of_file(str(source)),
                )
            )

        self.tool._derive_mop_artifact(self._task(tmp_path))

        assert self._artifact_path(tmp_path).read_bytes() == expected

    @pytest.mark.parametrize(
        "marker",
        ['"directlyReachesTarget"', '"transitions"'],
        ids=["inside-reachability", "after-windows-closed"],
    )
    def test_truncated_source_raises_and_leaves_nothing(self, tmp_path, marker):
        # A producer killed mid-write leaves a document whose root never closes.
        # Cut after `windows` closed, every section the derivation needs but
        # `transitions` is complete, and it is still no document to arm a run on.
        text = json.dumps(SOURCE_DOCUMENT, indent=2)
        _write_source(tmp_path, raw=text[: text.index(marker)])
        before = set(os.listdir(tmp_path))

        with pytest.raises(RVToolExecutionError) as raised:
            self.tool._derive_mop_artifact(self._task(tmp_path))

        assert "the document is truncated" in str(raised.value)
        assert str(tmp_path / "app.apk.json") in str(raised.value)
        assert not self._artifact_path(tmp_path).exists()
        assert set(os.listdir(tmp_path)) == before

    def test_non_utf8_source_raises_and_leaves_nothing(self, tmp_path):
        # Bytes that are not UTF-8 stop the document being JSON midway, so the
        # streaming read reports it as truncated.
        text = json.dumps(SOURCE_DOCUMENT, indent=2)
        cut = text.index('"windows"')
        source = tmp_path / "app.apk.json"
        source.write_bytes(
            text[:cut].encode() + b'"bad\xff": 1, ' + text[cut:].encode()
        )
        before = set(os.listdir(tmp_path))

        with pytest.raises(RVToolExecutionError):
            self.tool._derive_mop_artifact(self._task(tmp_path))

        assert not self._artifact_path(tmp_path).exists()
        assert set(os.listdir(tmp_path)) == before

    def test_full_json_is_byte_identical_after_derivation(self, tmp_path):
        # INV-ANA-53: the full JSON stays the archived source every metric reads.
        source = _write_source(tmp_path, SOURCE_DOCUMENT)
        before = open(source, "rb").read()

        self.tool._derive_mop_artifact(self._task(tmp_path))

        assert open(source, "rb").read() == before


# --- gh90 N4: per-run LLM backend provenance ---------------------------------


class _FakeResponse:
    """Minimal stand-in for the object urlopen returns as a context manager."""

    def __init__(self, body):
        self._body = body.encode()

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


class TestLlmProvenance:
    """gh90 group 3: what actually served the run (INV-APV-33)."""

    def setup_method(self):
        self.tool = ApeRVTool()
        # An LLM cell carrying an explicit dose: what provenance records is the variant's
        # own declared sampling, so the fixture has to declare some.
        self.tool.configure(
            _cell(
                "as_mop_llm",
                llm_prompt_variant="v13",
                llm_percentage=0.7,
                llm_temperature=0,
            )
        )

    def _jar(self, tmp_path):
        jar = tmp_path / "ape-rv.jar"
        jar.write_bytes(b"jar bytes")
        return str(jar)

    def _serve(self, monkeypatch, body):
        monkeypatch.setattr(
            aperv_mod.urllib.request,
            "urlopen",
            lambda url, timeout=None: _FakeResponse(body),
        )

    def test_provenance_from_live_query(self, tmp_path, monkeypatch):
        # Spec scenario "Backend recorded from a live query".
        self._serve(
            monkeypatch,
            json.dumps({"data": [{"id": "Qwen/Qwen3-VL-4B-Instruct"}]}),
        )

        provenance = self.tool._capture_llm_provenance(
            "http://192.168.0.36:30000/v1", self._jar(tmp_path)
        )

        assert provenance["capture_status"] == "ok"
        assert provenance["llm_model"] == "Qwen/Qwen3-VL-4B-Instruct"
        assert provenance["llm_backend"] == "http://192.168.0.36:30000/v1"
        assert provenance["llm_sampling"]["llm_temperature"] == 0
        assert provenance["llm_sampling"]["llm_prompt_variant"] == "v13"
        assert provenance["jar_sha256"] == hashlib.sha256(b"jar bytes").hexdigest()

    def test_emulator_alias_is_resolved_for_the_query(self, tmp_path, monkeypatch):
        # gh90 task 6.7. The arm's llm_url is written for the jar, which runs
        # inside the emulator where 10.0.2.2 is QEMU's host-loopback alias. This
        # query runs outside it, so querying the configured value verbatim times
        # out against a server the jar reaches normally — the gate 6.6 failure.
        seen = {}

        def capture(url, timeout=None):
            seen["url"] = url
            return _FakeResponse(
                json.dumps({"data": [{"id": "Qwen/Qwen3-VL-4B-Instruct"}]})
            )

        monkeypatch.setattr(aperv_mod.urllib.request, "urlopen", capture)

        provenance = self.tool._capture_llm_provenance(
            "http://10.0.2.2:30000/v1", self._jar(tmp_path)
        )

        assert seen["url"] == "http://127.0.0.1:30000/v1/models"
        assert provenance["capture_status"] == "ok"
        assert provenance["llm_model"] == "Qwen/Qwen3-VL-4B-Instruct"
        # The record names the address actually contacted, not the configured
        # one: naming an address that was never reached would be worse than none.
        assert provenance["llm_backend"] == "http://127.0.0.1:30000/v1"

    def test_resolution_leaves_other_hosts_alone(self):
        # Only the emulator alias is special. A campaign pointing at a real host
        # or a compose service name must reach that host, not the loopback.
        for url in (
            "http://192.168.0.36:30000/v1",
            "http://sglang:30000/v1",
            "http://110.0.2.24:30000/v1",
        ):
            assert self.tool._provenance_query_url(url) == url

    def test_resolution_never_reaches_ape_properties(self):
        # The jar needs the alias it was configured with, and _push_properties
        # builds the file by reading _tool_config through APERV_PROPERTY_MAPPING.
        # Asserting both halves is what pins the separation: the config is not
        # mutated, and llm_url is a mapped key, so the unmutated alias is exactly
        # what the jar receives.
        tool = ApeRVTool()
        tool.configure(_cell("as_mop_llm"))

        tool._provenance_query_url(tool._tool_config["overrides"]["llm_url"])

        assert tool._tool_config["overrides"]["llm_url"] == "http://10.0.2.2:30000/v1"
        assert APERV_PROPERTY_MAPPING["llm_url"] == "ape.llmUrl"

    def test_provenance_records_failure_not_config(self, tmp_path, monkeypatch, caplog):
        # Spec scenario "Query failure is recorded, not inferred": the arm
        # configures llm_model="default", and that value must NOT appear.
        def unreachable(url, timeout=None):
            raise OSError("Connection refused")

        monkeypatch.setattr(aperv_mod.urllib.request, "urlopen", unreachable)

        with caplog.at_level(logging.WARNING):
            provenance = self.tool._capture_llm_provenance(
                "http://10.0.2.2:30000/v1", self._jar(tmp_path)
            )

        assert provenance["capture_status"] == "query_failed"
        assert provenance["llm_model"] is None
        assert provenance["llm_sampling"] is None
        # A failed query records the failure; it does not edit the arm it failed for.
        assert self.tool._tool_config["overrides"]["llm_prompt_variant"] == "v13"
        # The jar digest is independent of the server and still recorded.
        assert provenance["jar_sha256"] is not None

    def test_malformed_response_is_a_failure_not_a_value(self, tmp_path, monkeypatch):
        self._serve(monkeypatch, "<html>gateway error</html>")

        provenance = self.tool._capture_llm_provenance(
            "http://host:30000/v1", self._jar(tmp_path)
        )

        assert provenance["capture_status"] == "query_failed"
        assert provenance["llm_model"] is None

    def test_empty_model_list_is_recorded_as_such(self, tmp_path, monkeypatch):
        self._serve(monkeypatch, json.dumps({"data": []}))

        provenance = self.tool._capture_llm_provenance(
            "http://host:30000/v1", self._jar(tmp_path)
        )

        assert provenance["capture_status"] == "no_models_served"
        assert provenance["llm_model"] is None

    def test_missing_jar_is_recorded_not_raised(self, tmp_path, monkeypatch):
        self._serve(monkeypatch, json.dumps({"data": [{"id": "m"}]}))

        provenance = self.tool._capture_llm_provenance(
            "http://host:30000/v1", str(tmp_path / "absent.jar")
        )

        assert provenance["jar_sha256"] is None
        assert provenance["capture_status"] == "jar_digest_failed"

    def test_non_http_url_is_refused_before_opening_anything(self, tmp_path):
        # urlopen honours file: and other local schemes, so a mistyped llm_url
        # could make the tool read a local path and record it as a served model.
        provenance = self.tool._capture_llm_provenance(
            f"file://{tmp_path}", self._jar(tmp_path)
        )

        assert provenance["capture_status"] == "unsupported_llm_url_scheme"
        assert provenance["llm_model"] is None

    def test_endpoint_does_not_double_the_v1_segment(self):
        # Every arm's llm_url already carries /v1; appending /v1/models blindly
        # would query /v1/v1/models and always fail.
        assert (
            self.tool._models_endpoint("http://host:30000/v1")
            == "http://host:30000/v1/models"
        )
        assert (
            self.tool._models_endpoint("http://host:30000/v1/")
            == "http://host:30000/v1/models"
        )
        assert (
            self.tool._models_endpoint("http://host:30000")
            == "http://host:30000/v1/models"
        )


class _ExecutionHarness:
    """Runs execute_tool_specific_logic() for a cell with the device and jar stubbed."""

    def setup_method(self):
        self.tool = ApeRVTool()
        self.pushed = []
        self._real_time = aperv_mod.time

    def teardown_method(self):
        aperv_mod.time = self._real_time

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

    def _run(self, tmp_path, name):
        """Execute the flow for cell `name` with the device and the jar stubbed out."""
        self.tool.configure(_cell(name))
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

        # The mocked command returns instantly, which INV-APV-60 would read as a run
        # truncated to 0 s. These tests are about what reaches the device, not about the
        # completion contract — TestCompletionIsEstablished owns that — so the clock
        # reports an exploration that consumed its budget.
        aperv_mod.time = _stub_clock(1000.0, 1000.0 + task.config.timeout)

        self.tool.execute_tool_specific_logic(task, app)
        return task

    def _artifact_pushes(self):
        return [p for p in self.pushed if p[1] == DEVICE_ARTIFACT_PATH]

    def _provenance_path(self, tmp_path):
        return tmp_path / "trace.provenance.json"

    def _properties(self):
        return next(p for p in self.pushed if p[1] == APERV_DEVICE_PROPERTIES_PATH)[
            2
        ].decode()


class TestExecuteMopArtifactFlow(_ExecutionHarness):
    """Step 1c wiring, keyed on `static_data`: what reaches the device, and what fails
    the task (INV-APV-06, INV-APV-45)."""

    def test_provenance_sidecar_written_for_an_llm_cell(self, tmp_path, monkeypatch):
        # Spec step 6: one query per run, recorded next to the run's artifacts.
        # The sidecar cannot live inside the trace — step 7 opens that file in
        # "wb" and would truncate anything written before it.
        _write_source(tmp_path, SOURCE_DOCUMENT)
        monkeypatch.setattr(
            aperv_mod.urllib.request,
            "urlopen",
            lambda url, timeout=None: _FakeResponse(
                json.dumps({"data": [{"id": "Qwen/Qwen3-VL-4B-Instruct"}]})
            ),
        )

        self._run(tmp_path, "as_mop_llm")

        recorded = json.loads(self._provenance_path(tmp_path).read_text())
        assert recorded["llm_model"] == "Qwen/Qwen3-VL-4B-Instruct"
        assert recorded["capture_status"] == "ok"
        assert recorded["jar_sha256"] == hashlib.sha256(b"jar").hexdigest()

    def test_no_query_for_a_non_llm_cell(self, tmp_path, monkeypatch):
        # Spec scenario "Non-LLM arms need no query": no request is issued, and
        # the absent record is not a failure.
        _write_source(tmp_path, SOURCE_DOCUMENT)

        def forbidden(*args, **kwargs):
            raise AssertionError("a non-LLM arm must not query /v1/models")

        monkeypatch.setattr(aperv_mod.urllib.request, "urlopen", forbidden)

        self._run(tmp_path, "as_mop")

        assert not self._provenance_path(tmp_path).exists()

    def test_failed_query_does_not_abort_the_run(self, tmp_path, monkeypatch):
        # Spec scenario "Provenance query does not delay the run": the flow
        # proceeds to the exploration command and the failure is on record.
        _write_source(tmp_path, SOURCE_DOCUMENT)

        def unreachable(url, timeout=None):
            raise OSError("Connection refused")

        monkeypatch.setattr(aperv_mod.urllib.request, "urlopen", unreachable)

        self._run(tmp_path, "as_mop_llm")

        recorded = json.loads(self._provenance_path(tmp_path).read_text())
        assert recorded["capture_status"] == "query_failed"
        assert recorded["llm_model"] is None
        assert self._artifact_pushes(), "the run must still have pushed and executed"

    def test_full_json_never_pushed(self, tmp_path):
        # INV-APV-46: the device receives the derived projection and nothing else,
        # under any cache state.
        source = _write_source(tmp_path, SOURCE_DOCUMENT)

        self._run(tmp_path, "as_mop")

        pushes = self._artifact_pushes()
        assert len(pushes) == 1
        local_path, _, content = pushes[0]
        assert local_path == str(tmp_path / "app.apk.mop.json")
        assert json.loads(content)["formatVersion"] == 2
        assert all(push[0] != source for push in self.pushed)
        assert not any(
            push[1] == "/data/local/tmp/static_analysis.json" for push in self.pushed
        )

    def test_older_format_cache_is_never_pushed(self, tmp_path):
        # INV-APV-47: a format-1 artifact whose digest matches is a cache miss, so
        # the device receives the format the jar reads, not the stale cache.
        source = _write_source(tmp_path, SOURCE_DOCUMENT)
        (tmp_path / "app.apk.mop.json").write_text(
            json.dumps(
                {
                    "formatVersion": 1,
                    "source": {"digest": aperv_mod.digest_of_file(source)},
                }
            )
        )

        self._run(tmp_path, "as_mop")

        (push,) = self._artifact_pushes()
        assert json.loads(push[2])["formatVersion"] == 2

    @pytest.mark.parametrize("name", ("mop", *STATIC_CELLS))
    def test_every_cell_with_static_data_pushes_the_artifact(self, tmp_path, name):
        # INV-APV-45: a cell with static_data either pushes the artifact and writes
        # ape.staticDataPath, or fails before the jar is launched.
        _write_source(tmp_path, SOURCE_DOCUMENT)

        self._run(tmp_path, name)

        assert len(self._artifact_pushes()) == 1
        lines = self._properties().splitlines()
        assert lines[:3] == [
            f"ape.preset={name}",
            f"ape.variant={name}",
            f"ape.staticDataPath={DEVICE_ARTIFACT_PATH}",
        ]
        assert not [ln for ln in lines if ln.startswith("ape.mopDataPath")]
        assert "static_analysis.json" not in self._properties()

    def test_cell_without_json_raises(self, tmp_path):
        # A cell that cannot load its static data is a failed task, not a run of a
        # different configuration under the cell's name (INV-APV-45).
        with pytest.raises(RVToolExecutionError) as raised:
            self._run(tmp_path, "as_mop")

        assert str(tmp_path / "app.apk.json") in str(raised.value)
        assert self._artifact_pushes() == []
        assert not any(push[1] == APERV_DEVICE_PROPERTIES_PATH for push in self.pushed)

    def test_cell_derivation_error_raises(self, tmp_path):
        # Derivation failure: a section of the
        # wrong type refuses derivation, nothing is pushed and the jar is never
        # launched.
        _write_source(tmp_path, {**SOURCE_DOCUMENT, "windows": "none"})

        with pytest.raises(RVToolExecutionError):
            self._run(tmp_path, "as_mop")

        assert self._artifact_pushes() == []

    @pytest.mark.parametrize("name", ["as", "as_mop"])
    def test_cell_arms_on_wtgless_document(self, tmp_path, name):
        # Spec scenario "WTG-less document arms both aperv arms": the producer's
        # first-pass document carries substrate but no WTG, and the task does not fail
        # for the as cell or for the as_mop cell.
        wtgless = {**SOURCE_DOCUMENT, "transitions": []}
        del wtgless["complete"]
        _write_source(tmp_path, wtgless)

        self._run(tmp_path, name)

        pushes = self._artifact_pushes()
        assert len(pushes) == 1
        artifact = json.loads(pushes[0][2])
        assert artifact["wtg"] == {}
        assert artifact["stats"]["wtgEdges"] == 0
        assert (tmp_path / "app.apk.mop.json").exists()

    def test_base_cell_untouched(self, tmp_path, monkeypatch):
        # Spec scenario "Successful APE-RV execution with sata variant": aperv:base
        # derives nothing, and neither an artifact nor a broadcast catalog reaches the
        # device.
        _write_source(tmp_path, SOURCE_DOCUMENT)

        def forbidden(*args, **kwargs):
            raise AssertionError("the base cell must not derive")

        monkeypatch.setattr(aperv_mod, "derive", forbidden)

        self._run(tmp_path, "base")

        assert self._artifact_pushes() == []
        assert not (tmp_path / "app.apk.mop.json").exists()
        assert [device for _, device, _ in self.pushed] == [
            APERV_DEVICE_JAR_PATH,
            APERV_DEVICE_PROPERTIES_PATH,
        ]
        assert self._properties().splitlines() == [
            "ape.preset=base",
            "ape.variant=base",
        ]


class TestBroadcastCatalogPush(_ExecutionHarness):
    """Step 1b: system-broadcast.json follows STATIC (INV-APV-10).

    Component triggering is a STATIC member and the catalog's only reader, so the catalog
    is pushed on the four as* cells, which carry `broadcast_catalog`, and never on base or
    mop. The module directory ships the catalog, so the present case uses the real file.
    """

    def _catalog_pushes(self):
        return [p for p in self.pushed if p[1] == APERV_DEVICE_BROADCAST_CATALOG_PATH]

    def test_the_module_directory_ships_the_catalog(self):
        # Non-vacuity: the pushed-when-present scenarios below rely on the real file.
        module_dir = os.path.dirname(aperv_mod.__file__)
        assert os.path.isfile(
            os.path.join(module_dir, aperv_mod.APERV_BROADCAST_CATALOG_NAME)
        )

    @pytest.mark.parametrize("name", STATIC_CELLS)
    def test_pushed_on_the_cells_that_mount_static(self, tmp_path, name):
        # Spec scenario "Broadcast catalog pushed when present".
        _write_source(tmp_path, SOURCE_DOCUMENT)

        self._run(tmp_path, name)

        (push,) = self._catalog_pushes()
        assert os.path.basename(push[0]) == "system-broadcast.json"
        assert push[1] == "/data/local/tmp/system-broadcast.json"
        # The dose comes from the preset, not from the tool.
        assert "ape.componentPercentage" not in self._properties()

    @pytest.mark.parametrize("name", ["base", "mop"])
    def test_not_pushed_on_the_cells_without_static(self, tmp_path, name):
        # Spec scenario "The cells without STATIC push no catalog".
        _write_source(tmp_path, SOURCE_DOCUMENT)

        self._run(tmp_path, name)

        assert self._catalog_pushes() == []

    def test_not_pushed_when_the_file_is_missing(self, tmp_path, monkeypatch):
        # Spec scenario "Broadcast catalog absent": component triggering degrades
        # gracefully, so the run continues without the catalog.
        _write_source(tmp_path, SOURCE_DOCUMENT)
        monkeypatch.setattr(
            aperv_mod, "APERV_BROADCAST_CATALOG_NAME", "absent-system-broadcast.json"
        )

        self._run(tmp_path, "as")

        assert self._catalog_pushes() == []
        assert len(self._artifact_pushes()) == 1
        assert any(p[1] == APERV_DEVICE_PROPERTIES_PATH for p in self.pushed)


# --- gh96: the artifact is device input, never an analysis input -------------

ARTIFACT_SUFFIX_PATTERN = ".mop" + ".json"


def _modules_root():
    """The workspace `modules/` directory, from this test file's location."""
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
    )


class TestMopArtifactAudit:
    """INV-ANA-53: the derived artifact must not leak into an analysis path."""

    def test_no_module_outside_aperv_tool_reads_mop_json(self):
        """
        The artifact is a lossy projection built for an explorer: no call graph, no
        method signatures, `reachesTarget` renamed, dialog widgets merged into their
        hosts. A metric computed over it would answer a different question under the
        same name, so the full JSON stays the sole analysis input and this is checked
        rather than left to convention.

        The suffix is assembled from two pieces so the assertion's own source line is
        not itself a match — the audit must not be the thing it reports.

        Scope is `modules/` — the workspace's importable code, which is what a metric
        or analysis path is written in. `scripts/` is deliberately outside it: the
        one-shot corpus driver of gh96 writes `.mop.json` files by design and is
        deleted once the equivalence gate is green.
        """
        offenders = []
        for module_dir in sorted(os.listdir(_modules_root())):
            if module_dir == "aperv-tool":
                continue
            module_path = os.path.join(_modules_root(), module_dir)
            if not os.path.isdir(module_path):
                continue
            for root, dirs, files in os.walk(module_path):
                dirs[:] = [d for d in dirs if d not in {"__pycache__", ".venv"}]
                for file_name in files:
                    if not file_name.endswith(".py"):
                        continue
                    path = os.path.join(root, file_name)
                    with open(path, "r", errors="replace") as handle:
                        for number, line in enumerate(handle, start=1):
                            if ARTIFACT_SUFFIX_PATTERN in line:
                                offenders.append(f"{path}:{number}: {line.strip()}")

        assert offenders == [], (
            "the derived MOP artifact is device input only; these references are "
            "outside aperv-tool:\n" + "\n".join(offenders)
        )
