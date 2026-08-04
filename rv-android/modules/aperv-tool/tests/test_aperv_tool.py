"""
Unit tests for ApeRVTool.

Tests cover: tool spec, variants, configure, JAR search paths, command building,
constants, and empty trace detection.
"""

import gzip
import hashlib
import json
import logging
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from rv_android_core.util.error.exceptions import (
    ConfigurationError,
    RVCommandTimeoutError,
    RVToolExecutionError,
    RVToolTimeoutError,
)

import aperv_tool.tools.aperv.tool as aperv_mod
from aperv_tool.tools.aperv.derive_mop_artifact import DEVICE_ARTIFACT_PATH
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

    def test_adb_timeout_uses_45s_grace(self):
        # gh90 task 5.5 / spec scenario "Timeout budget includes the widened grace
        # window": T + 45, not T + 15 — the old ceiling is where the lost coverage
        # dumps piled up (32 runs stacked against it, none beyond).
        cmd = self.tool._build_main_command(self._make_app(), "emulator-5554", 300)
        assert cmd.timeout == 345


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
        self.tool.configure(ApeRVTool.get_variants()["sata"])

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


# The 17 arm-defining Python keys → frozen ape.* names (spec INV-APV-13, verbatim).
# Pinned here so a typo'd java name in the mapping (which would make the property
# inert on the jar with no error — R1/D5) fails a unit test, not the experiment.
# trigger_mop_first was removed (task group 7): the APE-RV jar deleted Config.triggerMopFirst
# in mop-census-launcher, so the property is inert on the jar and is no longer arm-defining.
_EXPECTED_ARM_DEFINING_MAPPING = {
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

# The INV-APV-26 guard's scope. It began as "cal_*-prefixed variants", which was
# exactly the set that existed then. gh90's decisive-run LLM arm carries no cal_
# prefix, so leaving the scope as a prefix match would let the arm the whole run
# turns on escape the guard, and the guard-verification task would pass
# vacuously. Named explicitly rather than widened to "any arm with llm_url":
# sata_llm and sata_mop_llm predate INV-APV-26 and do not declare llm_percentage
# or llm_prompt_variant, so a blanket widening would fail on arms the invariant
# was never written for.
_LLM_GUARD_EXTRA_ARMS = {"mop_on_llm_70"}


def _llm_guarded_arms(variants):
    """The arms INV-APV-26 audits: the cal_* family plus the decisive-run LLM arm."""
    return {
        name: cfg
        for name, cfg in variants.items()
        if name.startswith("cal_") or name in _LLM_GUARD_EXTRA_ARMS
    }


# The three E3 decisive-run arms (gh90 A1), and the exact key set that separates
# the control from the reference. The list is pinned here so a silent edit to
# either dictionary fails a test rather than the experiment.
_DECISIVE_ARMS = ("mop_on_llm_off", "mop_off_llm_off", "mop_on_llm_70")
_MOP_CONTRAST_KEYS = {
    "mop_weight_direct",
    "mop_weight_transitive",
    "mop_weight_open_menu",
    "mop_weight_wtg",
    "mop_frontier_weight",
    "activity_trigger_enabled",
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

    def test_arm_defining_keys_count_is_17(self):
        # The APE-RV jar exposes 17 arm-defining properties: it has no triggerMopFirst and
        # no apePureMode. A key the jar does not read cannot define an arm.
        assert len(aperv_mod.ARM_DEFINING_KEYS) == 17

    def test_ape_pure_mode_is_not_an_arm_key(self):
        # ape.apePureMode is a retired key: the jar aborts at bootstrap when a properties
        # file carries it (issue #93), so no arm may declare or map it. Purity is
        # structural — the ape_pure arm is its 17 explicit off values, nothing more.
        assert "ape_pure_mode" not in aperv_mod.ARM_DEFINING_KEYS
        assert "ape_pure_mode" not in APERV_PROPERTY_MAPPING

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
        # INV-APV-13 verbatim: pin the 17 python→java names so a typo fails here.
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

    def test_ape_pure_sets_every_flag_off(self):
        # Spec scenario: every RV flag off explicitly, no kill-switch key, no mop_data.
        # These assertions are the whole definition of the arm — there is no jar-side
        # switch behind them.
        cfg = ApeRVTool.get_variants()["ape_pure"]
        assert "ape_pure_mode" not in cfg
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

    def test_llm_guarded_arms_declare_all_llm_keys(self):
        # INV-APV-26 guard: every arm in the guard's scope ⊇ LLM_ARM_KEYS. Failure
        # names the variant and the missing keys.
        arms = _llm_guarded_arms(ApeRVTool.get_variants())
        assert arms, "no arms found in the LLM guard scope"
        for name, cfg in arms.items():
            missing = LLM_ARM_KEYS - set(cfg)
            assert not missing, f"arm {name!r} missing LLM keys: {sorted(missing)}"

    def test_decisive_llm_arm_is_inside_the_llm_key_guard(self):
        # gh90 task 1.6 / spec scenario "The LLM arm is inside the LLM key guard":
        # mop_on_llm_70 carries no cal_ prefix, so the guard's original scoping
        # would have skipped it and task 1.7 would have passed vacuously.
        arms = _llm_guarded_arms(ApeRVTool.get_variants())

        assert "mop_on_llm_70" in arms
        assert not "mop_on_llm_70".startswith("cal_")
        # And the guard would actually bite: dropping one key fails it.
        crippled = dict(arms["mop_on_llm_70"])
        del crippled["llm_prompt_variant"]
        assert LLM_ARM_KEYS - set(crippled) == {"llm_prompt_variant"}

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


class TestDecisiveRunArms:
    """gh90 group 1: the E3 decisive run's arm set (INV-APV-29/30)."""

    def setup_method(self):
        self.variants = ApeRVTool.get_variants()

    def test_the_three_arms_exist_under_their_normative_names(self):
        # The variant string is the resume identity key and the consolidation
        # column key, so a rename silently splits a campaign's results.
        for name in _DECISIVE_ARMS:
            assert name in self.variants, f"missing decisive-run arm {name!r}"

    def test_control_arm_keeps_the_static_analysis_document(self):
        # INV-APV-29 / spec scenario "Control arm never omits the static analysis
        # document": omitting it would disable WtgPass and FrontierPass as
        # collateral, turning "MOP guidance off" into "navigation mostly off".
        control = self.variants["mop_off_llm_off"]

        assert (
            control.get("mop_data") == "static_analysis"
        ), "INV-APV-29: the control arm must keep a present, loadable mop_data"

    def test_control_arm_zeroes_all_five_mop_weights(self):
        control = self.variants["mop_off_llm_off"]

        for key in (
            "mop_weight_direct",
            "mop_weight_transitive",
            "mop_weight_open_menu",
            "mop_weight_wtg",
            "mop_frontier_weight",
        ):
            assert control[key] == 0, f"{key} must be 0 in the control arm"
        assert control["activity_trigger_enabled"] is False

    def test_control_arm_keeps_the_frontier_alive(self):
        # INV-APV-30: the control removes MOP guidance, not navigation. Zeroing
        # frontier_boost_weight too would confound the contrast.
        reference = self.variants["mop_on_llm_off"]
        control = self.variants["mop_off_llm_off"]

        assert control["frontier_boost_weight"] == reference["frontier_boost_weight"]
        assert control["frontier_boost_weight"] == 200

    def test_all_three_arms_carry_the_frontier_substrate(self):
        # INV-APV-30 — *sempre modo frontier*, including the control.
        for name in _DECISIVE_ARMS:
            cfg = self.variants[name]
            assert cfg["mop_data"] == "static_analysis", name
            assert cfg["frontier_boost_weight"] == 200, name
            assert cfg["strategy"] == "sata", name
            assert cfg["throttle_ms"] == 200, name

    def test_source_components_flag_is_explicit_in_all_three(self):
        # B2 / spec scenario: never inherited from the jar's false default
        # (Config.java:159), whose suppression of the MOP-activity signal is
        # measured at 20.0% → 85.0% of activities flagged on the subset40.
        for name in _DECISIVE_ARMS:
            cfg = self.variants[name]
            assert "mop_activity_source_components" in cfg, name
            assert cfg["mop_activity_source_components"] is True, name

    def test_reference_and_control_differ_exactly_in_the_mop_keys(self):
        # Spec scenario "Reference and control differ only in MOP keys". Asserted
        # by diffing the dictionaries rather than by trusting review — this is
        # what makes RQ-C1 a single-factor contrast.
        reference = self.variants["mop_on_llm_off"]
        control = self.variants["mop_off_llm_off"]

        differing = {
            key
            for key in set(reference) | set(control)
            if reference.get(key) != control.get(key)
        }

        assert differing == _MOP_CONTRAST_KEYS

    def test_reference_and_llm_arm_differ_only_in_llm_keys(self):
        # Spec scenario "Reference and LLM arm differ only in LLM keys": no MOP
        # weight, frontier or RV exploration flag may move with the LLM.
        #
        # The B3 jar-provenance declaration is the one exemption, and the second
        # assertion below is what licenses it: neither key is in
        # APERV_PROPERTY_MAPPING, so neither is written to ape.properties and
        # neither can reach the jar. Single-factor is a claim about the keys that
        # reach the jar, so exempting keys that provably do not reach it keeps
        # the contrast intact rather than punching a hole in it. The two
        # assertions must stay together — the exemption is only sound while the
        # keys remain unmapped.
        reference = self.variants["mop_on_llm_off"]
        llm_arm = self.variants["mop_on_llm_70"]

        differing = {
            key
            for key in set(reference) | set(llm_arm)
            if reference.get(key) != llm_arm.get(key)
        }

        assert differing, "the LLM arm must differ from the reference somewhere"
        assert _JAR_DECLARATION_KEYS <= differing, sorted(differing)
        for key in _JAR_DECLARATION_KEYS:
            assert key not in APERV_PROPERTY_MAPPING, key

        behavioural = differing - _JAR_DECLARATION_KEYS
        assert all(key.startswith("llm_") for key in behavioural), sorted(behavioural)
        assert not differing & _MOP_CONTRAST_KEYS

    def test_llm_arm_carries_the_cal_a1_dose_verbatim(self):
        # design D8: 0.7 is the only dose with a measured 300 s counterpart on
        # this substrate and subset, which is what makes the 1800 s result
        # readable as a dose × budget interaction.
        llm_arm = self.variants["mop_on_llm_70"]
        cal_a1 = self.variants["cal_a1"]

        for key in LLM_ARM_KEYS:
            assert llm_arm[key] == cal_a1[key], f"{key} diverged from the cal_a1 dose"
        assert llm_arm["llm_percentage"] == 0.7
        assert llm_arm["llm_prompt_variant"] == "v13"
        assert llm_arm["llm_temperature"] == 0

    def test_reference_arm_is_the_anc2_anchor(self):
        # Arm 1 is configurationally sata_mop_act_frontier: the reference is the
        # configuration that already won the multi-arm comparison, not a new one.
        reference = self.variants["mop_on_llm_off"]
        anc2 = self.variants["sata_mop_act_frontier"]

        assert reference == anc2

    def test_decisive_arms_satisfy_the_arm_defining_guard(self):
        # INV-APV-14 under its existing scope: none of the three is exempt, so
        # every arm-defining key must be explicit in all of them.
        for name in _DECISIVE_ARMS:
            assert name not in aperv_mod._ARM_DEFINING_EXEMPT
            missing = aperv_mod.ARM_DEFINING_KEYS - set(self.variants[name])
            assert not missing, f"{name} missing arm-defining keys: {sorted(missing)}"


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

    def test_ape_pure_writes_no_kill_switch(self, tmp_path):
        # Spec scenario: no kill-switch property is written for ape_pure — the arm's
        # purity is carried entirely by the explicit off values below.
        props = self._capture_properties(tmp_path, ApeRVTool.get_variants()["ape_pure"])
        assert "ape.apePureMode" not in props
        assert "ape.frontierBoostWeight=0" in props
        assert "ape.activityTriggerEnabled=false" in props

    def test_campaign_arm_writes_no_retired_kill_switch(self, tmp_path):
        # The stage-2 APE-RV jar aborts at bootstrap on a retired key, before step 1, so a
        # single ape.apePureMode line in a campaign arm's properties would zero the whole
        # arm (coverage 0, MOP violations 0). sata_mop_widget stands for the 23 arms that
        # inherit _BASELINE_ARM_FLAGS (issue #93).
        props = self._capture_properties(
            tmp_path, ApeRVTool.get_variants()["sata_mop_widget"], mop_json_pushed=True
        )
        assert "ape.apePureMode" not in props
        assert "ape.mopActivitySourceComponents=false" in props

    def test_act_frontier_writes_reach_package(self, tmp_path):
        # Spec scenario: reach-package flags appear for sata_mop_act_frontier.
        props = self._capture_properties(
            tmp_path,
            ApeRVTool.get_variants()["sata_mop_act_frontier"],
            mop_json_pushed=True,
        )
        assert "ape.mopActivitySourceComponents=true" in props
        assert "ape.mopFrontierWeight=200" in props
        assert f"ape.mopDataPath={DEVICE_ARTIFACT_PATH}" in props
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
        assert artifact["formatVersion"] == 1
        assert artifact["package"] == "br.unb.cic.cryptoapp"
        assert artifact["source"]["file"] == "app.apk.json"

    def test_cache_hit_skips_derivation(self, tmp_path, monkeypatch):
        # Spec scenario "cache hit skips derivation": a matching digest is the whole
        # freshness test, so the second call must not re-derive.
        _write_source(tmp_path, SOURCE_DOCUMENT)
        task = self._task(tmp_path)
        self.tool._derive_mop_artifact(task)
        first = self._artifact_path(tmp_path).read_bytes()

        def forbidden(*args, **kwargs):
            raise AssertionError("a fresh cache must not be re-derived")

        monkeypatch.setattr(aperv_mod, "derive", forbidden)

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
        raw = (tmp_path / "app.apk.json").read_bytes()
        assert artifact["source"]["digest"] == aperv_mod.digest_of(raw)

    def test_corrupt_cache_regenerates(self, tmp_path):
        # An unreadable cache is a miss, not a failure: regenerating costs
        # milliseconds and refusing would fail a run over a scratch file.
        _write_source(tmp_path, SOURCE_DOCUMENT)
        self._artifact_path(tmp_path).write_text("{ truncated")

        self.tool._derive_mop_artifact(self._task(tmp_path))

        assert (
            json.loads(self._artifact_path(tmp_path).read_text())["formatVersion"] == 1
        )

    def test_failed_derivation_leaves_no_file(self, tmp_path):
        # Spec scenario "failed derivation leaves no artifact behind": a truncated
        # analysis must not arm a run, and must leave no temp behind either.
        _write_source(tmp_path, {**SOURCE_DOCUMENT, "complete": False})
        before = set(os.listdir(tmp_path))

        with pytest.raises(RVToolExecutionError) as raised:
            self.tool._derive_mop_artifact(self._task(tmp_path))

        assert "complete" in str(raised.value)
        assert not self._artifact_path(tmp_path).exists()
        assert set(os.listdir(tmp_path)) == before

    def test_unparseable_source_raises(self, tmp_path):
        _write_source(tmp_path, raw="{not valid json")

        with pytest.raises(RVToolExecutionError):
            self.tool._derive_mop_artifact(self._task(tmp_path))

        assert not self._artifact_path(tmp_path).exists()

    def test_full_json_is_byte_identical_after_derivation(self, tmp_path):
        # INV-ANA-53: the full JSON stays the archived source every metric reads.
        source = _write_source(tmp_path, SOURCE_DOCUMENT)
        before = open(source, "rb").read()

        self.tool._derive_mop_artifact(self._task(tmp_path))

        assert open(source, "rb").read() == before


# --- gh90 B3: snap tolerance gated on the dead-pair ban -----------------------

# The raised radius, and the two keys an arm uses to declare which jar build it
# was raised for. The git sha names the source revision and is documentary; the
# sha256 names the built artifact and is the half the smoke actually verifies,
# against the jar_sha256 captured at run start. Both are Python-only — they must
# never reach ape.properties, because the jar has no property to receive them.
_SNAP_TOLERANCE_RAISED = 150
_JAR_SHA_KEY = "expected_jar_git_sha"
_JAR_DIGEST_KEY = "expected_jar_sha256"
_JAR_DECLARATION_KEYS = frozenset({_JAR_SHA_KEY, _JAR_DIGEST_KEY})


def _snap_tolerance_offenders(variants):
    """
    Arms that break the B3 pairing (INV-APV-34), with the reason.

    Widening the snap radius makes more LLM answers resolve to a widget. Without
    the dead-pair ban in the jar, the extra resolutions are repeated taps on
    pairs already known to produce no new state, so the widening amplifies the
    measured 25.6% dead-call waste instead of rescuing near-misses. The tolerance
    and the declaration of the jar it belongs to therefore travel together, in
    both directions: a dangling declaration left behind after a rollback is just
    as misleading as an ungated tolerance.

    All three travel together, not two: a digest with no git sha cannot be traced
    back to source, and a git sha with no digest is unverifiable, since ape-rv.jar
    carries no build stamp to compare a revision against.
    """
    offenders = {}
    for name, cfg in variants.items():
        sets_tolerance = "llm_snap_tolerance_px" in cfg
        declared = {key for key in _JAR_DECLARATION_KEYS if cfg.get(key)}
        if sets_tolerance and declared != _JAR_DECLARATION_KEYS:
            missing = sorted(_JAR_DECLARATION_KEYS - declared)
            offenders[name] = (
                f"raised tolerance without a declared jar sha ({', '.join(missing)})"
            )
        elif declared and cfg.get("llm_snap_tolerance_px") != _SNAP_TOLERANCE_RAISED:
            offenders[name] = "declared jar sha without the raised tolerance"
        elif declared and declared != _JAR_DECLARATION_KEYS:
            missing = sorted(_JAR_DECLARATION_KEYS - declared)
            offenders[name] = f"incomplete jar declaration ({', '.join(missing)})"
    return offenders


class TestSnapToleranceGate:
    """gh90 group 3: the B3 coupling, enforced by the suite (INV-APV-34)."""

    def test_shipped_arms_satisfy_the_pairing(self):
        assert _snap_tolerance_offenders(ApeRVTool.get_variants()) == {}

    def test_tolerance_without_declaration_fails(self):
        # Spec scenario "Tolerance and jar declaration travel together".
        offenders = _snap_tolerance_offenders(
            {"arm": {"llm_snap_tolerance_px": _SNAP_TOLERANCE_RAISED}}
        )

        assert "arm" in offenders
        assert "without a declared jar sha" in offenders["arm"]

    def test_dangling_jar_sha_declaration_fails(self):
        # Spec scenario "Declaration without the raised tolerance also fails":
        # the tolerance was rolled back to the jar default and the declaration
        # was left behind, which will silently mislead the next reader.
        offenders = _snap_tolerance_offenders(
            {
                "arm": {
                    _JAR_SHA_KEY: "abc1234",
                    _JAR_DIGEST_KEY: "def5678",
                    "llm_snap_tolerance_px": 50,
                }
            }
        )

        assert "arm" in offenders
        assert "without the raised tolerance" in offenders["arm"]

    def test_declaration_without_any_tolerance_key_also_fails(self):
        offenders = _snap_tolerance_offenders(
            {"arm": {_JAR_SHA_KEY: "abc1234", _JAR_DIGEST_KEY: "def5678"}}
        )

        assert "arm" in offenders

    def test_half_a_declaration_fails(self):
        # A digest with no git sha cannot be traced back to source, and a git sha
        # with no digest is unverifiable — ape-rv.jar carries no build stamp to
        # compare a revision against. Either half alone is a broken declaration.
        halves = ((_JAR_SHA_KEY, _JAR_DIGEST_KEY), (_JAR_DIGEST_KEY, _JAR_SHA_KEY))
        for present, missing in halves:
            offenders = _snap_tolerance_offenders(
                {
                    "arm": {
                        present: "abc1234",
                        "llm_snap_tolerance_px": _SNAP_TOLERANCE_RAISED,
                    }
                }
            )

            assert "arm" in offenders, present
            assert missing in offenders["arm"]

    def test_paired_declaration_passes(self):
        assert (
            _snap_tolerance_offenders(
                {
                    "arm": {
                        _JAR_SHA_KEY: "abc1234",
                        _JAR_DIGEST_KEY: "def5678",
                        "llm_snap_tolerance_px": _SNAP_TOLERANCE_RAISED,
                    }
                }
            )
            == {}
        )

    def test_declared_shas_never_reach_ape_properties(self):
        # The declaration is a guard-and-smoke artifact, not a jar property:
        # ape-rv.jar has no property to receive it, and its absence from the
        # mapping is also what keeps the two keys inert enough not to disturb
        # the arm 1 <-> arm 3 single-factor contrast.
        for key in _JAR_DECLARATION_KEYS:
            assert key not in APERV_PROPERTY_MAPPING, key


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
        self.tool.configure(ApeRVTool.get_variants()["cal_a1"])

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
            return _FakeResponse(json.dumps({"data": [{"id": "Qwen/Qwen3-VL-4B-Instruct"}]}))

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
        tool.configure(ApeRVTool.get_variants()["mop_on_llm_70"])

        tool._provenance_query_url(tool._tool_config["llm_url"])

        assert tool._tool_config["llm_url"] == "http://10.0.2.2:30000/v1"
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
        assert self.tool._tool_config["llm_model"] == "default"
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


class TestExecuteMopArtifactFlow:
    """Step 1c wiring: what reaches the device, and what fails the task."""

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

    def _artifact_pushes(self):
        return [p for p in self.pushed if p[1] == DEVICE_ARTIFACT_PATH]

    def _provenance_path(self, tmp_path):
        return tmp_path / "trace.provenance.json"

    def test_provenance_sidecar_written_for_an_llm_arm(self, tmp_path, monkeypatch):
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

        self._run(tmp_path, "cal_a1")

        recorded = json.loads(self._provenance_path(tmp_path).read_text())
        assert recorded["llm_model"] == "Qwen/Qwen3-VL-4B-Instruct"
        assert recorded["capture_status"] == "ok"
        assert recorded["jar_sha256"] == hashlib.sha256(b"jar").hexdigest()

    def test_no_query_for_a_non_llm_arm(self, tmp_path, monkeypatch):
        # Spec scenario "Non-LLM arms need no query": no request is issued, and
        # the absent record is not a failure.
        _write_source(tmp_path, SOURCE_DOCUMENT)

        def forbidden(*args, **kwargs):
            raise AssertionError("a non-LLM arm must not query /v1/models")

        monkeypatch.setattr(aperv_mod.urllib.request, "urlopen", forbidden)

        self._run(tmp_path, "sata_mop_act_frontier")

        assert not self._provenance_path(tmp_path).exists()

    def test_failed_query_does_not_abort_the_run(self, tmp_path, monkeypatch):
        # Spec scenario "Provenance query does not delay the run": the flow
        # proceeds to the exploration command and the failure is on record.
        _write_source(tmp_path, SOURCE_DOCUMENT)

        def unreachable(url, timeout=None):
            raise OSError("Connection refused")

        monkeypatch.setattr(aperv_mod.urllib.request, "urlopen", unreachable)

        self._run(tmp_path, "cal_a1")

        recorded = json.loads(self._provenance_path(tmp_path).read_text())
        assert recorded["capture_status"] == "query_failed"
        assert recorded["llm_model"] is None
        assert self._artifact_pushes(), "the run must still have pushed and executed"

    def test_full_json_never_pushed(self, tmp_path):
        # INV-APV-46: the device receives the derived projection and nothing else,
        # under any cache state.
        source = _write_source(tmp_path, SOURCE_DOCUMENT)

        self._run(tmp_path, "sata_mop_act_frontier")

        pushes = self._artifact_pushes()
        assert len(pushes) == 1
        local_path, _, content = pushes[0]
        assert local_path == str(tmp_path / "app.apk.mop.json")
        assert json.loads(content)["formatVersion"] == 1
        assert all(push[0] != source for push in self.pushed)
        assert not any(
            push[1] == "/data/local/tmp/static_analysis.json" for push in self.pushed
        )

    def test_properties_carry_new_mop_data_path(self, tmp_path):
        _write_source(tmp_path, SOURCE_DOCUMENT)

        self._run(tmp_path, "sata_mop_act_frontier")

        props = next(p for p in self.pushed if p[1] == APERV_DEVICE_PROPERTIES_PATH)[
            2
        ].decode()
        assert f"ape.mopDataPath={DEVICE_ARTIFACT_PATH}" in props
        assert "static_analysis.json" not in props

    def test_mop_arm_without_json_raises(self, tmp_path):
        # Spec scenario "sata_mop execution with static analysis JSON absent": a MOP
        # arm that cannot arm is a failed task. The warn-and-continue it replaces
        # produced runs labelled MOP that explored as pure SATA.
        with pytest.raises(RVToolExecutionError) as raised:
            self._run(tmp_path, "sata_mop_act_frontier")

        assert str(tmp_path / "app.apk.json") in str(raised.value)
        assert self._artifact_pushes() == []
        assert not any(push[1] == APERV_DEVICE_PROPERTIES_PATH for push in self.pushed)

    def test_mop_arm_derivation_error_raises(self, tmp_path):
        # Spec scenario "sata_mop execution when derivation fails": nothing is
        # pushed and the jar is never launched.
        _write_source(tmp_path, {**SOURCE_DOCUMENT, "complete": False})

        with pytest.raises(RVToolExecutionError):
            self._run(tmp_path, "sata_mop_act_frontier")

        assert self._artifact_pushes() == []

    def test_non_mop_arm_untouched(self, tmp_path, monkeypatch):
        # Spec scenario "Successful APE-RV execution with sata variant": no
        # derivation is attempted and nothing static reaches the device.
        _write_source(tmp_path, SOURCE_DOCUMENT)

        def forbidden(*args, **kwargs):
            raise AssertionError("a non-MOP arm must not derive")

        monkeypatch.setattr(aperv_mod, "derive", forbidden)

        self._run(tmp_path, "sata")

        assert self._artifact_pushes() == []
        assert not (tmp_path / "app.apk.mop.json").exists()
        props = next(p for p in self.pushed if p[1] == APERV_DEVICE_PROPERTIES_PATH)[
            2
        ].decode()
        assert "ape.mopDataPath" not in props


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
