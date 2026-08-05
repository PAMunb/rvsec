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
import re
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
    APERV_ORCHESTRATION_KEYS,
    APERV_PROPERTY_MAPPING,
    ApeRVTool,
)


def _written_properties(tool, tmp_path, mop_json_pushed=False):
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
    tool._push_properties("emulator-5554", trace, mop_json_pushed)
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
    """Verify get_variants() structure (INV-APV-05)."""

    PRESET_IDENTITY_ARMS = {
        "sata": "aperv",
        "sata_mop": "mop",
        "sata_llm": "llm",
        "sata_mop_llm": "llm_mop",
    }

    def test_preset_identity_arms_are_one_to_one_with_the_jar_presets(self):
        variants = ApeRVTool.get_variants()
        for name, preset in self.PRESET_IDENTITY_ARMS.items():
            assert variants[name]["preset"] == preset

    def test_default_is_bound_to_the_same_object_as_sata(self):
        # INV-TOOL-02: an alias by shared object, so the two cannot drift apart.
        variants = ApeRVTool.get_variants()
        assert variants["default"] is variants["sata"]
        assert variants["default"]["strategy"] == "sata"

    def test_preset_identity_arms_carry_nothing_but_the_server_url(self):
        # The preset states the arm; only the URL is deployment-specific. Anything else in
        # these overrides would be the jar's vocabulary restated on the Python side, which
        # is the duplication this change deletes.
        variants = ApeRVTool.get_variants()
        assert variants["sata"]["overrides"] == {}
        assert variants["sata_mop"]["overrides"] == {}
        assert set(variants["sata_llm"]["overrides"]) == {"llm_url"}
        assert set(variants["sata_mop_llm"]["overrides"]) == {"llm_url"}

    def test_every_llm_preset_arm_declares_the_url(self):
        # INV-APV-38: the preset states the LLM routing gates ON while deliberately omitting
        # the server URL, so an arm that inherits it without supplying one activates routing
        # over an absent mechanism and aborts at resolution. A fail-fast, not a fallback.
        for name, arm in ApeRVTool.get_variants().items():
            if arm.get("preset") in ("llm", "llm_mop"):
                assert "llm_url" in arm["overrides"], f"{name} has no llm_url"

    def test_mop_arms_carry_the_static_analysis_document(self):
        variants = ApeRVTool.get_variants()
        assert variants["sata_mop"]["mop_data"] == "static_analysis"
        assert variants["sata_mop_llm"]["mop_data"] == "static_analysis"

    def test_non_mop_variants_lack_mop_data(self):
        variants = ApeRVTool.get_variants()
        for name in ["default", "sata", "sata_llm"]:
            assert "mop_data" not in variants[name], f"{name} should not have mop_data"

    def test_llm_variants_use_sata_strategy(self):
        variants = ApeRVTool.get_variants()
        assert variants["sata_llm"]["strategy"] == "sata"
        assert variants["sata_mop_llm"]["strategy"] == "sata"

    def test_no_migrated_arm_carries_throttle_ms(self):
        # The aperv preset already states ape.defaultGUIThrottle=200, which every arm used;
        # restating it per arm would be a delta that is not a delta.
        for name, arm in ApeRVTool.get_variants().items():
            if "preset" in arm:
                assert (
                    "throttle_ms" not in arm
                ), f"{name} restates the preset's throttle"

    def test_every_variant_configures(self):
        # The arm table and configure() are two halves of one contract: a variant that
        # cannot be configured is a variant that cannot run, and nothing else in the suite
        # would notice.
        for name, arm in ApeRVTool.get_variants().items():
            if "preset" not in arm:
                continue
            ApeRVTool().configure(dict(arm))


class TestConfigure:
    """Verify configure() validation (INV-APV-02)."""

    def setup_method(self):
        self.tool = ApeRVTool()

    def test_valid_preset_arm_stores_config(self):
        self.tool.configure({"strategy": "sata", "preset": "mop", "overrides": {}})
        assert self.tool._tool_config["strategy"] == "sata"
        assert self.tool._tool_config["preset"] == "mop"

    def test_invalid_strategy_raises(self):
        with pytest.raises(ConfigurationError):
            self.tool.configure({"strategy": "invalid_strategy", "preset": "aperv"})

    def test_absent_strategy_raises(self):
        with pytest.raises(ConfigurationError):
            self.tool.configure({"preset": "aperv"})

    def test_empty_config_raises(self):
        # INV-APV-02: absent strategy (empty dict) must raise, not store
        with pytest.raises(ConfigurationError):
            self.tool.configure({})

    @pytest.mark.parametrize("strategy", ["bfs", "dfs"])
    def test_retired_strategy_rejected_before_the_device(self, strategy):
        # Neither was ever an agent type: ApeAgent.createAgent knows sata, random and
        # replay only, so before stage 2 they ran SataAgent silently and after it they
        # abort on the device. Rejecting here is what keeps a run from passing local
        # validation and dying on an emulator.
        with pytest.raises(ConfigurationError):
            self.tool.configure({"strategy": strategy, "preset": "aperv"})

    def test_missing_preset_raises(self):
        with pytest.raises(ConfigurationError, match="preset"):
            self.tool.configure({"strategy": "sata"})

    def test_empty_preset_raises(self):
        with pytest.raises(ConfigurationError, match="preset"):
            self.tool.configure({"strategy": "sata", "preset": ""})

    def test_non_dict_overrides_raises(self):
        with pytest.raises(ConfigurationError, match="overrides"):
            self.tool.configure(
                {
                    "strategy": "sata",
                    "preset": "mop",
                    "overrides": ["frontier_boost_weight"],
                }
            )

    def test_configure_makes_copy(self):
        config = {"strategy": "sata", "preset": "aperv", "overrides": {}}
        self.tool.configure(config)
        config["strategy"] = "mutated"
        assert self.tool._tool_config["strategy"] == "sata"

    def test_configure_copies_the_overrides_dict_too(self):
        # A shallow copy would leave the caller's overrides aliased, so a later DSL fold
        # would mutate the variant table itself — every subsequent arm of the same run
        # would inherit the smoke's override.
        overrides = {"llm_url": "http://10.0.2.2:30000/v1"}
        self.tool.configure(
            {"strategy": "sata", "preset": "llm", "overrides": overrides}
        )
        overrides["llm_url"] = "http://mutated/v1"
        assert (
            self.tool._tool_config["overrides"]["llm_url"] == "http://10.0.2.2:30000/v1"
        )

    def test_env_var_does_not_override_llm_url_at_l2(self, monkeypatch):
        """gh55 INV-TOOL-20: configure() at L2 must not consult os.environ.
        APERV_LLM_BASE_URL override is now handled at L5; L2 only reads what
        the factory-merged config dict provides."""
        monkeypatch.setenv("APERV_LLM_BASE_URL", "http://custom:8080/v1")
        self.tool.configure(
            {
                "strategy": "sata",
                "preset": "llm",
                "overrides": {"llm_url": "http://10.0.2.2:30000/v1"},
            }
        )
        # The env var is ignored at L2; the config value carries through.
        assert (
            self.tool._tool_config["overrides"]["llm_url"] == "http://10.0.2.2:30000/v1"
        )

    def test_env_var_does_not_inject_llm_url_at_l2(self, monkeypatch):
        """gh55 INV-TOOL-20: env var with no llm_url in config still produces
        no llm_url at L2. Injection happens at L5 via parameters."""
        monkeypatch.setenv("APERV_LLM_BASE_URL", "http://custom:8080/v1")
        self.tool.configure({"strategy": "sata", "preset": "aperv", "overrides": {}})
        assert "llm_url" not in self.tool._tool_config["overrides"]


class TestDslOverrideFold:
    """The tool DSL delivers overrides at the top level; configure() folds them (INV-APV-39).

    ToolFactory merges `{**variant_config, **tool_config.parameters}`, so
    `aperv:sata_mop@frontier_boost_weight=200` arrives beside `preset` rather than inside
    `overrides` — and `_push_properties()` reads only `overrides`. Without the fold the
    override would produce no property line and no error, and the run would execute a
    configuration nobody asked for. These tests are the reason that cannot happen.
    """

    def setup_method(self):
        self.tool = ApeRVTool()

    def test_dsl_override_is_folded_into_overrides(self):
        self.tool.configure(
            {"strategy": "sata", "preset": "mop", "frontier_boost_weight": 200}
        )
        assert self.tool._tool_config["overrides"]["frontier_boost_weight"] == 200
        assert "frontier_boost_weight" not in self.tool._tool_config

    def test_dsl_override_reaches_the_properties_file(self, tmp_path):
        self.tool.configure(
            {"strategy": "sata", "preset": "mop", "frontier_boost_weight": 200}
        )
        assert "ape.frontierBoostWeight=200" in _written_properties(self.tool, tmp_path)

    def test_dsl_value_wins_over_the_arms_own_entry(self, tmp_path):
        # The DSL is the operator's last word — that is what makes it usable for smokes
        # and ablations without declaring a variant.
        self.tool.configure(
            {
                "strategy": "sata",
                "preset": "mop",
                "overrides": {"mop_frontier_weight": 200},
                "mop_frontier_weight": 400,
            }
        )
        assert self.tool._tool_config["overrides"]["mop_frontier_weight"] == 400
        lines = _written_properties(self.tool, tmp_path).splitlines()
        assert lines.count("ape.mopFrontierWeight=400") == 1
        assert not [ln for ln in lines if ln == "ape.mopFrontierWeight=200"]

    def test_typo_raises_instead_of_vanishing(self):
        # `frontier_bost_weight` has no mapping entry. Silently dropping it would run the
        # arm unchanged while the operator believed it had been overridden.
        with pytest.raises(ConfigurationError, match="frontier_bost_weight"):
            self.tool.configure(
                {"strategy": "sata", "preset": "mop", "frontier_bost_weight": 200}
            )

    def test_orchestration_keys_survive_the_fold(self):
        self.tool.configure(
            {
                "strategy": "sata",
                "preset": "llm_mop",
                "mop_data": "static_analysis",
                "seed": 42,
                "overrides": {},
            }
        )
        for key in ("mop_data", "seed"):
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
        self.tool.configure({"strategy": "sata", "preset": "aperv", "overrides": {}})

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
        self.tool.configure({"strategy": "sata", "preset": "aperv", "overrides": {}})

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

    def test_llm_arm_writes_the_url_and_nothing_else(self, tmp_path):
        # The sampling block belongs to the `llm` preset; only the server URL is
        # deployment-specific, so only it crosses as an override (INV-APV-38).
        self.tool.configure(
            {
                "strategy": "sata",
                "preset": "llm",
                "overrides": {"llm_url": "http://10.0.2.2:30000/v1"},
            }
        )
        props = _written_properties(self.tool, tmp_path)
        assert "ape.llmUrl=http://10.0.2.2:30000/v1" in props
        for preset_owned in (
            "ape.llmOnNewState",
            "ape.llmOnStagnation",
            "ape.llmModel",
            "ape.llmTemperature",
            "ape.llmTopP",
            "ape.llmTopK",
            "ape.llmTimeoutMs",
        ):
            assert preset_owned not in props

    def test_llm_properties_absent_for_a_non_llm_arm(self, tmp_path):
        self.tool.configure({"strategy": "sata", "preset": "aperv", "overrides": {}})
        assert "ape.llm" not in _written_properties(self.tool, tmp_path)


class TestPushProperties:
    """Verify the D4 output contract: preset first, artifact path, then deltas only."""

    def setup_method(self):
        self.tool = ApeRVTool()

    def _capture_properties(self, tmp_path, config, mop_json_pushed=False):
        """Helper: configure tool, call _push_properties, return content."""
        self.tool.configure(config)
        return _written_properties(self.tool, tmp_path, mop_json_pushed)

    def test_preset_line_comes_first(self, tmp_path):
        props = self._capture_properties(
            tmp_path,
            {
                "strategy": "sata",
                "preset": "llm_mop",
                "mop_data": "static_analysis",
                "overrides": {"llm_url": "http://10.0.2.2:30000/v1"},
            },
            mop_json_pushed=True,
        )
        lines = [line for line in props.strip().split("\n") if line]
        assert lines[0] == "ape.preset=llm_mop"
        assert lines[1] == f"ape.mopDataPath={DEVICE_ARTIFACT_PATH}"
        assert lines[2] == "ape.llmUrl=http://10.0.2.2:30000/v1"
        assert len(lines) == 3

    def test_empty_override_arm_writes_two_lines(self, tmp_path):
        # The four MOP weights come from the `mop` preset, so the arm restates nothing.
        props = self._capture_properties(
            tmp_path,
            {
                "strategy": "sata",
                "preset": "mop",
                "mop_data": "static_analysis",
                "overrides": {},
            },
            mop_json_pushed=True,
        )
        lines = [line for line in props.strip().split("\n") if line]
        assert lines == ["ape.preset=mop", f"ape.mopDataPath={DEVICE_ARTIFACT_PATH}"]
        assert "ape.mopWeight" not in props

    def test_baseline_arm_writes_one_line(self, tmp_path):
        props = self._capture_properties(
            tmp_path, {"strategy": "sata", "preset": "aperv", "overrides": {}}
        )
        assert [line for line in props.strip().split("\n") if line] == [
            "ape.preset=aperv"
        ]
        for absent in (
            "ape.mopDataPath",
            "ape.frontierBoostWeight",
            "ape.dynamicEpsilon",
        ):
            assert absent not in props

    def test_deltas_are_written_in_mapping_order(self, tmp_path):
        # Order follows APERV_PROPERTY_MAPPING rather than the arm dict, so two runs of the
        # same arm produce byte-identical files regardless of how the dict was authored.
        props = self._capture_properties(
            tmp_path,
            {
                "strategy": "sata",
                "preset": "mop",
                "overrides": {
                    "activity_trigger_enabled": True,
                    "default_epsilon": 0.08,
                },
            },
        )
        lines = [line for line in props.strip().split("\n") if line]
        assert lines.index("ape.defaultEpsilon=0.08") < lines.index(
            "ape.activityTriggerEnabled=true"
        )

    def test_bools_are_serialized_lowercase(self, tmp_path):
        props = self._capture_properties(
            tmp_path,
            {
                "strategy": "sata",
                "preset": "mop",
                "overrides": {
                    "activity_trigger_enabled": True,
                    "mop_activity_source_components": True,
                    "do_fuzzing": False,
                },
            },
        )
        assert "ape.activityTriggerEnabled=true" in props
        assert "ape.mopActivitySourceComponents=true" in props
        assert "ape.doFuzzing=false" in props
        assert "True" not in props and "False" not in props

    def test_python_only_keys_not_written(self, tmp_path):
        props = self._capture_properties(
            tmp_path,
            {
                "strategy": "sata",
                "preset": "llm_mop",
                "mop_data": "static_analysis",
                "seed": 42,
                "overrides": {"llm_snap_tolerance_px": 150},
            },
        )
        for python_only in (
            "strategy",
            "mop_data",
            "seed",
        ):
            assert python_only not in props
        # ...while an ordinary override on the same arm travels the normal path.
        assert "ape.llmSnapTolerancePx=150" in props

    def test_platform_device_addressing_keys_are_accepted(self, tmp_path):
        # rv-experiment's ExecutionController injects device_port/device_serial/device_id
        # into every tool's parameters whenever --device-port is set, and every Docker
        # compose file sets it. ToolFactory merges them at the top level, so rejecting them
        # would abort every containerized and parallel run — including the A/B gate — inside
        # Platform._load_tool, before a device is touched. They address a device; they do
        # not configure the jar, so they are accepted and never reach ape.properties.
        arm = dict(self.tool.get_variants()["sata_mop"])
        arm.update(
            {
                "device_port": 5554,
                "device_serial": "emulator-5554",
                "device_id": "emulator-5554",
            }
        )
        props = self._capture_properties(tmp_path, arm, mop_json_pushed=True)
        for injected in ("device_port", "device_serial", "device_id", "5554"):
            assert injected not in props

    def test_unmapped_override_key_aborts_in_configure(self):
        # Under the jar's fail-fast resolution this typo would abort the run on the device.
        # configure() is where it has to be caught: the jar, the broadcast catalog and the
        # derived MOP artifact are all pushed before ape.properties is generated, so a check
        # at push time would already have cost three pushes and a derivation (INV-APV-02).
        with pytest.raises(ConfigurationError, match="frontier_bost_weight"):
            self.tool.configure(
                {
                    "strategy": "sata",
                    "preset": "mop",
                    "overrides": {"frontier_bost_weight": 200},
                }
            )


# The three arms of the E3 decisive run. Reference ↔ control answers RQ-C1 and
# reference ↔ LLM arm answers RQ-C3, so what may differ between them is asserted
# rather than left to reading the table.
_DECISIVE_ARMS = ("mop_on_llm_off", "mop_off_llm_off", "mop_on_llm_70")

# What "MOP guidance off" is allowed to move, in Python override keys. The effective-plan
# version of this contrast lives in the migration tier, where the jar's presets are
# available; here it only keeps the LLM contrast honest.
_MOP_CONTRAST_KEYS = {
    "mop_weight_direct",
    "mop_weight_transitive",
    "mop_weight_open_menu",
    "mop_weight_wtg",
    "mop_frontier_weight",
    "activity_trigger_enabled",
}


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

    def test_the_two_llm_sub_parameters_stay_mapped(self):
        # gh88's archive left a requirement framing these as "mapped but outside
        # LLM_ARM_KEYS and set by no cal_a* arm". The guard and the cal arms are both gone,
        # so the framing goes with them; the entries stay, because the jar declares both as
        # live Feature.LLM sub-parameters and mop_on_llm_70 sets the snap tolerance.
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
        self.tool.configure(
            {
                "strategy": "sata",
                "preset": "mop",
                "overrides": {"corpus_basis": self.BASIS},
            }
        )
        props = _written_properties(self.tool, tmp_path)
        assert f"ape.corpusBasis={self.BASIS}" in props.splitlines()

    def test_the_dsl_seam_carries_it_from_the_top_level(self, tmp_path):
        # This is the seam the campaign uses: `aperv:<arm>@corpus_basis=subset40:<sha>`
        # arrives merged at the TOP level of the config, and configure()'s fold is what
        # moves it into `overrides` where _push_properties() reads. Without the mapping
        # entry the key would be rejected as unrecognised instead of silently dropped —
        # which is the behaviour this asserts is not needed.
        self.tool.configure(
            {
                "strategy": "sata",
                "preset": "mop",
                "overrides": {},
                "corpus_basis": self.BASIS,
            }
        )
        assert self.tool._tool_config["overrides"]["corpus_basis"] == self.BASIS
        assert f"ape.corpusBasis={self.BASIS}" in _written_properties(
            self.tool, tmp_path
        )

    def test_an_absent_basis_emits_no_key(self, tmp_path):
        # INV-APV-56. Absence is a legitimate state — every campaign before this one ran
        # without it, and every standalone invocation still does — so there is no
        # placeholder, no empty value and no warning.
        self.tool.configure({"strategy": "sata", "preset": "aperv", "overrides": {}})
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
            self.tool.configure(
                {
                    "strategy": "sata",
                    "preset": "mop",
                    "overrides": {"corpus_basis": rejected},
                }
            )
        message = str(excinfo.value)
        assert "corpus_basis" in message
        assert repr(rejected) in message

    def test_a_well_formed_basis_is_accepted_whatever_it_names(self):
        # Shape is all this side validates: whether the digest corresponds to any list
        # is checked where the list lives, by recomputing it. A tool that verified the
        # digest would need to know the campaign's directory layout to find the file.
        self.tool.configure(
            {
                "strategy": "sata",
                "preset": "mop",
                "overrides": {
                    "corpus_basis": "a_corpus.v2-1:" + "0123456789abcdef" * 4
                },
            }
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

    `mop_on_llm_70` used to declare `expected_jar_git_sha` and `expected_jar_sha256`
    — the revision and digest of one `ape-rv.jar` build, as literals — with a guard
    enforcing the pairing and a smoke gate comparing the digest against the jar
    actually pushed. `ape-rv.jar` is built in a sibling repository whose build is not
    bit-reproducible, so the same revision yields a different digest every time it is
    built: the gate failed on correct redeployments and passed on stale ones, and a
    routine rebuild became an edit of a Python constant here.

    Identity is still recorded, by measurement rather than declaration:
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
        assert (
            offenders == {}
        ), f"external artifact identity declared in source: {offenders}"

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

    def test_control_arm_zeroes_every_mop_weight_it_must(self):
        # The four scoring weights are zeroed explicitly; mop_frontier_weight and
        # activity_trigger_enabled are absent because the `mop` preset already states them
        # at 0 and false. Restating a preset value as an override would be a delta that is
        # not a delta — and the effective plan, which is what the run sees, is identical
        # either way (proved by the migration tier's effective-configuration contrast).
        overrides = self.variants["mop_off_llm_off"]["overrides"]

        for key in (
            "mop_weight_direct",
            "mop_weight_transitive",
            "mop_weight_open_menu",
            "mop_weight_wtg",
        ):
            assert overrides[key] == 0, f"{key} must be 0 in the control arm"
        assert "mop_frontier_weight" not in overrides
        assert "activity_trigger_enabled" not in overrides

    def test_control_arm_keeps_the_frontier_alive(self):
        # INV-APV-30: the control removes MOP guidance, not navigation. Zeroing
        # frontier_boost_weight too would confound the contrast.
        reference = self.variants["mop_on_llm_off"]["overrides"]
        control = self.variants["mop_off_llm_off"]["overrides"]

        assert control["frontier_boost_weight"] == reference["frontier_boost_weight"]
        assert control["frontier_boost_weight"] == 200

    def test_all_three_arms_carry_the_reach_package_substrate(self):
        # INV-APV-30 — *sempre modo frontier*, including the control.
        for name in _DECISIVE_ARMS:
            cfg = self.variants[name]
            assert cfg["mop_data"] == "static_analysis", name
            assert cfg["overrides"]["frontier_boost_weight"] == 200, name
            assert cfg["strategy"] == "sata", name

    def test_source_components_flag_is_explicit_in_all_three(self):
        # B2 / spec scenario: never inherited from the `mop` preset's false, whose
        # suppression of the MOP-activity signal is measured at 20.0% -> 85.0% of
        # activities flagged on the subset40.
        for name in _DECISIVE_ARMS:
            overrides = self.variants[name]["overrides"]
            assert overrides.get("mop_activity_source_components") is True, name

    def test_the_llm_arm_differs_from_the_reference_only_in_llm_keys(self):
        # Spec scenario "Reference and LLM arm differ only in LLM keys". Both arms carry
        # the same four reach-package overrides, so what is left is the LLM dose — no MOP
        # weight, frontier or exploration key may move with the LLM.
        #
        # The presets differ (mop vs llm_mop), and that difference is itself LLM-only: the
        # llm_mop vector is the mop vector plus the LLM sampling block, which the migration
        # tier's effective-configuration contrast checks against the jar's own tables.
        reference = self.variants["mop_on_llm_off"]["overrides"]
        llm_arm = self.variants["mop_on_llm_70"]["overrides"]

        differing = {
            key
            for key in set(reference) | set(llm_arm)
            if reference.get(key) != llm_arm.get(key)
        }

        assert differing, "the LLM arm must differ from the reference somewhere"
        assert all(key.startswith("llm_") for key in differing), sorted(differing)
        assert not differing & _MOP_CONTRAST_KEYS

    def test_the_two_arms_carry_the_same_top_level_keys(self):
        # The contrast has no exemption left. The LLM arm used to carry two extra top-level
        # keys declaring the jar build its snap tolerance was raised for, which had to be
        # argued harmless every time the diff was read; they are gone (INV-APV-59), so the
        # arms differ in their overrides and in nothing else.
        reference = self.variants["mop_on_llm_off"]
        llm_arm = self.variants["mop_on_llm_70"]

        assert set(reference) == set(llm_arm)

    def test_the_llm_arm_carries_the_calibrated_dose(self):
        # design D8: 0.7 is the only dose with a measured 300 s counterpart on this
        # substrate and subset, which is what makes the 1800 s result readable as a
        # dose x budget interaction. The cal_a1 arm it was carried over from is retired;
        # the dose is now stated here, which is the only place it still has to be right.
        overrides = self.variants["mop_on_llm_70"]["overrides"]

        assert overrides["llm_percentage"] == 0.7
        assert overrides["llm_prompt_variant"] == "v13"
        assert overrides["llm_temperature"] == 0


class TestSeedPropagation:
    """Group 3: seed reaches the jar as -s <seed>, never ape.properties (INV-APV-18)."""

    def setup_method(self):
        self.tool = ApeRVTool()
        self.tool.configure({"strategy": "sata", "preset": "aperv", "overrides": {}})

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
        # An LLM arm carrying an explicit dose: what provenance records is the arm's own
        # declared sampling, so the fixture has to declare some.
        self.tool.configure(
            {
                "strategy": "sata",
                "preset": "llm_mop",
                "mop_data": "static_analysis",
                "overrides": {
                    "llm_url": "http://10.0.2.2:30000/v1",
                    "llm_prompt_variant": "v13",
                    "llm_percentage": 0.7,
                    "llm_temperature": 0,
                },
            }
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
        tool.configure(
            {
                "strategy": "sata",
                "preset": "llm_mop",
                "overrides": {"llm_url": "http://10.0.2.2:30000/v1"},
            }
        )

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

    # Representative arm shapes. The flow under test cares about three things only —
    # whether a MOP artifact is derived, whether an LLM server is queried, and neither —
    # so the fixtures state exactly that rather than standing in for a named arm.
    MOP_ARM = {
        "strategy": "sata",
        "preset": "mop",
        "mop_data": "static_analysis",
        "overrides": {},
    }
    MOP_LLM_ARM = {
        "strategy": "sata",
        "preset": "llm_mop",
        "mop_data": "static_analysis",
        "overrides": {"llm_url": "http://10.0.2.2:30000/v1"},
    }
    BASELINE_ARM = {"strategy": "sata", "preset": "aperv", "overrides": {}}

    def _run(self, tmp_path, arm):
        """Execute the flow with the device and the jar stubbed out."""
        self.tool.configure(dict(arm))
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

        self._run(tmp_path, self.MOP_LLM_ARM)

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

        self._run(tmp_path, self.MOP_ARM)

        assert not self._provenance_path(tmp_path).exists()

    def test_failed_query_does_not_abort_the_run(self, tmp_path, monkeypatch):
        # Spec scenario "Provenance query does not delay the run": the flow
        # proceeds to the exploration command and the failure is on record.
        _write_source(tmp_path, SOURCE_DOCUMENT)

        def unreachable(url, timeout=None):
            raise OSError("Connection refused")

        monkeypatch.setattr(aperv_mod.urllib.request, "urlopen", unreachable)

        self._run(tmp_path, self.MOP_LLM_ARM)

        recorded = json.loads(self._provenance_path(tmp_path).read_text())
        assert recorded["capture_status"] == "query_failed"
        assert recorded["llm_model"] is None
        assert self._artifact_pushes(), "the run must still have pushed and executed"

    def test_full_json_never_pushed(self, tmp_path):
        # INV-APV-46: the device receives the derived projection and nothing else,
        # under any cache state.
        source = _write_source(tmp_path, SOURCE_DOCUMENT)

        self._run(tmp_path, self.MOP_ARM)

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

        self._run(tmp_path, self.MOP_ARM)

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
            self._run(tmp_path, self.MOP_ARM)

        assert str(tmp_path / "app.apk.json") in str(raised.value)
        assert self._artifact_pushes() == []
        assert not any(push[1] == APERV_DEVICE_PROPERTIES_PATH for push in self.pushed)

    def test_mop_arm_derivation_error_raises(self, tmp_path):
        # Spec scenario "sata_mop execution when derivation fails": nothing is
        # pushed and the jar is never launched.
        _write_source(tmp_path, {**SOURCE_DOCUMENT, "complete": False})

        with pytest.raises(RVToolExecutionError):
            self._run(tmp_path, self.MOP_ARM)

        assert self._artifact_pushes() == []

    def test_non_mop_arm_untouched(self, tmp_path, monkeypatch):
        # Spec scenario "Successful APE-RV execution with sata variant": no
        # derivation is attempted and nothing static reaches the device.
        _write_source(tmp_path, SOURCE_DOCUMENT)

        def forbidden(*args, **kwargs):
            raise AssertionError("a non-MOP arm must not derive")

        monkeypatch.setattr(aperv_mod, "derive", forbidden)

        self._run(tmp_path, self.BASELINE_ARM)

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
