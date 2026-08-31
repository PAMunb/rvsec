"""
Tests for PreProcessor downstream selection.

Validates that:
- _get_target_apks_for_analysis() filters by instrumentation success
- get_instrumented_apks() filters nothing: every instrumented APK executes, and
  the ones with no static analysis artefact are named in a warning instead of
  being dropped (INV-EXP-16 as modified)
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from rv_experiment.experiment.workflow.pre_processor import (
    PreProcessingConfigurationError,
)

# Module path used by all patch() targets below.
_MOD = "rv_experiment.experiment.workflow.pre_processor"


def _make_pre_processor(tmp_path):
    """Create a PreProcessor with mocked config pointing to tmp_path."""
    with (
        patch(
            "rv_experiment.experiment.workflow.pre_processor.LoggingManager"
        ) as mock_logging,
        patch(
            "rv_experiment.experiment.workflow.pre_processor.ErrorHandler"
        ) as mock_eh,
    ):
        mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
        mock_eh.get_instance.return_value = MagicMock()

        config = MagicMock()
        config.output_dir = str(tmp_path / "out")

        from rv_experiment.experiment.workflow.pre_processor import PreProcessor

        pp = PreProcessor(config)
        return pp, config


def _only_warning_naming(pp, fragment):
    """The single `logger.warning` message containing `fragment`.

    The workflow emits several warnings per call and a bare `assert_any_call`
    would need the exact text; matching on a fragment and asserting uniqueness
    keeps the assertion about the content that matters.
    """
    matches = [
        call.args[0]
        for call in pp.logger.warning.call_args_list
        if call.args and fragment in call.args[0]
    ]
    assert len(matches) == 1, f"expected one warning naming {fragment!r}, got {matches}"
    return matches[0]


def _app_stub(app_path, package_detector=False, strip_build_type_suffix=False):
    """Stand-in for `App` that accepts every policy kwarg `_build_app` passes.

    The arity is not incidental: `_build_app` forwards both run policies, so a
    stub that names fewer of them raises `TypeError` and turns a policy change
    into a test failure that reads like a workflow failure.
    """
    return MagicMock(name=os.path.basename(app_path), path=app_path)


def _policy_stub(app_path, package_detector=False, strip_build_type_suffix=False):
    """Same stand-in, exposing the policies it received for assertion."""
    return MagicMock(
        path=app_path,
        package_detector=package_detector,
        strip_build_type_suffix=strip_build_type_suffix,
    )


class TestGetTargetApksForAnalysis:
    """Tests for _get_target_apks_for_analysis filtering."""

    def test_returns_only_instrumented_apks(self, tmp_path):
        pp, config = _make_pre_processor(tmp_path)

        # Create instrumented_apks/ with only good.apk
        inst_dir = tmp_path / "out" / "instrumented_apks"
        inst_dir.mkdir(parents=True)
        (inst_dir / "good.apk").write_bytes(b"instrumented")

        # Config lists both good and bad APKs
        config.get_apk_list.return_value = [
            "/originals/good.apk",
            "/originals/bad.apk",
        ]

        result = pp._get_target_apks_for_analysis()

        assert result == ["/originals/good.apk"]

    def test_returns_empty_when_instrumented_dir_empty(self, tmp_path):
        pp, config = _make_pre_processor(tmp_path)

        inst_dir = tmp_path / "out" / "instrumented_apks"
        inst_dir.mkdir(parents=True)

        config.get_apk_list.return_value = ["/originals/app.apk"]

        result = pp._get_target_apks_for_analysis()

        assert result == []

    def test_returns_empty_when_instrumented_dir_missing(self, tmp_path):
        pp, config = _make_pre_processor(tmp_path)

        config.get_apk_list.return_value = ["/originals/app.apk"]

        result = pp._get_target_apks_for_analysis()

        assert result == []


class TestGetInstrumentedApks:
    """Tests for get_instrumented_apks: it reports, it does not exclude."""

    def test_apk_without_json_still_executes(self, tmp_path):
        """The APK with no artefact runs, and the warning names it.

        This is the inversion INV-EXP-16 asks for: the previous behaviour
        dropped `bad.apk` from the returned list while the executed set came
        from a directory glob that never saw the filter, so the APK ran anyway
        and the log claimed it had been excluded.
        """
        pp, config = _make_pre_processor(tmp_path)

        inst_dir = tmp_path / "out" / "instrumented_apks"
        inst_dir.mkdir(parents=True)

        # good.apk has .json, bad.apk does not
        (inst_dir / "good.apk").write_bytes(b"apk")
        (inst_dir / "good.apk.json").write_text("{}")
        (inst_dir / "bad.apk").write_bytes(b"apk")

        with patch("rv_experiment.experiment.workflow.pre_processor.App") as MockApp:
            MockApp.side_effect = _app_stub
            result = pp.get_instrumented_apks()

        assert sorted(app.path for app in result) == [
            str(inst_dir / "bad.apk"),
            str(inst_dir / "good.apk"),
        ]
        warning = _only_warning_naming(pp, "coverage denominator")
        assert "bad.apk" in warning
        assert "good.apk" not in warning

    def test_includes_apks_with_json(self, tmp_path):
        pp, config = _make_pre_processor(tmp_path)

        inst_dir = tmp_path / "out" / "instrumented_apks"
        inst_dir.mkdir(parents=True)
        (inst_dir / "a.apk").write_bytes(b"apk")
        (inst_dir / "a.apk.json").write_text("{}")
        (inst_dir / "b.apk").write_bytes(b"apk")
        (inst_dir / "b.apk.json").write_text("{}")

        with patch("rv_experiment.experiment.workflow.pre_processor.App") as MockApp:
            MockApp.side_effect = _app_stub
            result = pp.get_instrumented_apks()

        assert len(result) == 2

    def test_no_fallback_when_the_only_apk_has_no_json(self, tmp_path):
        """ "No artefact" is not "no instrumented APK", and only the second falls back.

        The fallback to originals answers the case where instrumentation
        produced nothing at all. Firing it here would replace a real
        instrumented APK with its un-instrumented original, which records no
        violations — the opposite of what a missing denominator warrants.
        """
        pp, config = _make_pre_processor(tmp_path)

        inst_dir = tmp_path / "out" / "instrumented_apks"
        inst_dir.mkdir(parents=True)
        (inst_dir / "nojson.apk").write_bytes(b"apk")

        config.get_apk_list.return_value = ["/originals/fallback.apk"]

        with patch("rv_experiment.experiment.workflow.pre_processor.App") as MockApp:
            MockApp.side_effect = _app_stub
            result = pp.get_instrumented_apks()

        assert [app.path for app in result] == [str(inst_dir / "nojson.apk")]
        assert "nojson.apk" in _only_warning_naming(pp, "coverage denominator")

    def test_returns_originals_when_instrumented_dir_missing(self, tmp_path):
        pp, config = _make_pre_processor(tmp_path)

        config.get_apk_list.return_value = ["/originals/app.apk"]

        with patch("rv_experiment.experiment.workflow.pre_processor.App") as MockApp:
            MockApp.side_effect = _app_stub
            result = pp.get_instrumented_apks()

        assert len(result) == 1
        assert result[0].path == "/originals/app.apk"


class TestPackageDetectorPropagation:
    """Every App the workflow builds carries the run's package policy (INV-EXP-34)."""

    def test_get_instrumented_apks_forwards_the_policy(self, tmp_path):
        pp, config = _make_pre_processor(tmp_path)
        config.package_detector = True
        config.get_apk_list.return_value = ["/originals/app.apk"]

        with patch("rv_experiment.experiment.workflow.pre_processor.App") as MockApp:
            MockApp.side_effect = _policy_stub
            result = pp.get_instrumented_apks()

        assert [app.package_detector for app in result] == [True]

    def test_default_policy_reaches_every_app(self, tmp_path):
        """Asserted on the call, not the result: `False` is also the stub's default,
        so only the kwarg proves the value was actually passed."""
        pp, config = _make_pre_processor(tmp_path)
        config.package_detector = False
        config.strip_build_type_suffix = False

        inst_dir = tmp_path / "out" / "instrumented_apks"
        inst_dir.mkdir(parents=True)
        (inst_dir / "a.apk").write_bytes(b"apk")
        (inst_dir / "a.apk.json").write_text("{}")

        with patch("rv_experiment.experiment.workflow.pre_processor.App") as MockApp:
            MockApp.side_effect = _policy_stub
            pp.get_instrumented_apks()

        MockApp.assert_called_once_with(
            app_path=str(inst_dir / "a.apk"),
            package_detector=False,
            strip_build_type_suffix=False,
        )


class TestProcess:
    """Tests for the process() orchestrator dispatch (flag combinations)."""

    def test_all_flags_true_calls_all_steps(self, tmp_path):
        """WHEN all flags True THEN each of the three steps runs once."""
        pp, _ = _make_pre_processor(tmp_path)
        pp._generate_monitors = MagicMock()
        pp._instrument_apks = MagicMock()
        pp._run_static_analysis = MagicMock()

        pp.process(generate_monitors=True, instrument=True, static_analysis=True)

        pp._generate_monitors.assert_called_once()
        pp._instrument_apks.assert_called_once()
        pp._run_static_analysis.assert_called_once()

    def test_all_flags_false_skips_all_steps(self, tmp_path):
        """WHEN all flags False THEN no step runs and the skip warnings fire."""
        pp, _ = _make_pre_processor(tmp_path)
        pp._generate_monitors = MagicMock()
        pp._instrument_apks = MagicMock()
        pp._run_static_analysis = MagicMock()

        pp.process(generate_monitors=False, instrument=False, static_analysis=False)

        pp._generate_monitors.assert_not_called()
        pp._instrument_apks.assert_not_called()
        pp._run_static_analysis.assert_not_called()
        pp.logger.warning.assert_any_call("Skipping monitor generation")
        pp.logger.warning.assert_any_call("Skipping APK instrumentation")
        pp.logger.warning.assert_any_call("Skipping static analysis")


class TestGenerateMonitors:
    """Tests for _generate_monitors() (success/failure/ImportError/Exception)."""

    _GEN = "rv_monitor_generator.runtime_verification_generator.RuntimeVerificationGenerator"

    def test_success_logs_complete(self, tmp_path):
        """`os.makedirs` is real here: the provenance marker of INV-EXP-38 is a
        genuine file write, so mocking the directory away turns a success into a
        `FileNotFoundError` handled as a monitor-generation failure."""
        pp, config = _make_pre_processor(tmp_path)
        config.specification_set = "jca"
        with patch(self._GEN) as mock_gen:
            mock_gen.return_value.generate_monitors.return_value = True
            pp._generate_monitors()

        pp.logger.warning.assert_not_called()
        pp.error_handler.handle_error.assert_not_called()
        marker = tmp_path / "out" / "monitors" / "specification_set.txt"
        assert marker.read_text().strip() == "jca"

    def test_failure_logs_warning(self, tmp_path):
        pp, _ = _make_pre_processor(tmp_path)
        with (
            patch(f"{_MOD}.os.makedirs"),
            patch(self._GEN) as mock_gen,
        ):
            mock_gen.return_value.generate_monitors.return_value = False
            pp._generate_monitors()

        pp.logger.warning.assert_any_call("Monitor generation failed")

    def test_import_error_logs_warning(self, tmp_path):
        pp, _ = _make_pre_processor(tmp_path)
        # Forcing the inner import to fail: sys.modules entry set to None makes
        # `from rv_monitor_generator.runtime_verification_generator import ...`
        # raise ImportError.
        with (
            patch(f"{_MOD}.os.makedirs"),
            patch.dict(
                sys.modules,
                {"rv_monitor_generator.runtime_verification_generator": None},
            ),
        ):
            pp._generate_monitors()

        pp.logger.warning.assert_any_call(
            "Monitor generator module not available - skipping monitor generation"
        )

    def test_generic_exception_handled(self, tmp_path):
        pp, _ = _make_pre_processor(tmp_path)
        with (
            patch(f"{_MOD}.os.makedirs"),
            patch(self._GEN) as mock_gen,
        ):
            mock_gen.return_value.generate_monitors.side_effect = RuntimeError("boom")
            pp._generate_monitors()

        pp.error_handler.handle_error.assert_called_once()


class TestInstrumentApks:
    """Tests for _instrument_apks() (empty/success/failure/ImportError/Exception)."""

    @staticmethod
    def _setup_config(config):
        config.instrumentation_variant = "ajc"
        config.get_rv_instrumentation_config.return_value = MagicMock()
        config.apks_dir = "/apks"

    def test_empty_apk_list_warns_and_returns(self, tmp_path):
        pp, config = _make_pre_processor(tmp_path)
        self._setup_config(config)
        config.get_apk_list.return_value = []
        with (
            patch(f"{_MOD}.os.makedirs"),
            patch(f"{_MOD}.get_instrumenter"),
        ):
            pp._instrument_apks()

        pp.logger.warning.assert_any_call("No APKs configured for instrumentation")

    def test_success_logs_complete(self, tmp_path):
        pp, config = _make_pre_processor(tmp_path)
        self._setup_config(config)
        config.get_apk_list.return_value = ["/apks/a.apk"]
        with (
            patch(f"{_MOD}.os.makedirs"),
            patch(f"{_MOD}.get_instrumenter") as mock_gi,
        ):
            mock_gi.return_value.instrument_apks.return_value = True
            pp._instrument_apks()

        pp.logger.error.assert_not_called()

    def test_failure_logs_error(self, tmp_path):
        pp, config = _make_pre_processor(tmp_path)
        self._setup_config(config)
        config.get_apk_list.return_value = ["/apks/a.apk"]
        with (
            patch(f"{_MOD}.os.makedirs"),
            patch(f"{_MOD}.get_instrumenter") as mock_gi,
        ):
            mock_gi.return_value.instrument_apks.return_value = False
            pp._instrument_apks()

        pp.logger.error.assert_any_call("APK instrumentation failed")

    def test_import_error_copies_originals(self, tmp_path):
        pp, config = _make_pre_processor(tmp_path)
        self._setup_config(config)
        pp._copy_original_apks = MagicMock()
        with (
            patch(f"{_MOD}.os.makedirs"),
            patch(f"{_MOD}.get_instrumenter", side_effect=ImportError),
        ):
            pp._instrument_apks()

        pp._copy_original_apks.assert_called_once()

    def test_generic_exception_handled_and_copies(self, tmp_path):
        pp, config = _make_pre_processor(tmp_path)
        self._setup_config(config)
        pp._copy_original_apks = MagicMock()
        with (
            patch(f"{_MOD}.os.makedirs"),
            patch(f"{_MOD}.get_instrumenter", side_effect=RuntimeError("boom")),
        ):
            pp._instrument_apks()

        pp.error_handler.handle_error.assert_called_once()
        pp._copy_original_apks.assert_called_once()


class TestCopyOriginalApks:
    """Tests for _copy_original_apks() dest-existence branch."""

    def test_copies_when_dest_missing(self, tmp_path):
        pp, config = _make_pre_processor(tmp_path)
        config.get_apk_list.return_value = ["/orig/a.apk"]
        # Real makedirs creates the tmp instrumented dir; copy2 is mocked so no
        # real file movement occurs. Dest does not exist -> copy2 is invoked.
        with patch("shutil.copy2") as mock_copy:
            pp._copy_original_apks()

        mock_copy.assert_called_once()

    def test_skips_when_dest_exists(self, tmp_path):
        pp, config = _make_pre_processor(tmp_path)
        inst_dir = tmp_path / "out" / "instrumented_apks"
        inst_dir.mkdir(parents=True)
        (inst_dir / "a.apk").write_bytes(b"exists")
        config.get_apk_list.return_value = ["/orig/a.apk"]
        with patch("shutil.copy2") as mock_copy:
            pp._copy_original_apks()

        mock_copy.assert_not_called()


class TestRunStaticAnalysis:
    """Tests for _run_static_analysis() branches."""

    _SA = "rv_static_analysis.analysis.static.static_analysis.StaticAnalyzer"

    def test_no_targets_warns_and_returns(self, tmp_path):
        pp, _ = _make_pre_processor(tmp_path)
        pp._get_target_apks_for_analysis = MagicMock(return_value=[])
        with (
            patch(f"{_MOD}.os.makedirs"),
            patch(f"{_MOD}.App"),
            patch(self._SA),
        ):
            pp._run_static_analysis()

        pp.logger.warning.assert_any_call("No APKs available for static analysis")

    def test_success_logs_complete(self, tmp_path):
        pp, _ = _make_pre_processor(tmp_path)
        pp._get_target_apks_for_analysis = MagicMock(return_value=["/orig/x.apk"])
        with (
            patch(f"{_MOD}.os.makedirs"),
            patch(f"{_MOD}.App"),
            patch(self._SA) as mock_sa,
        ):
            mock_sa.return_value.analyze.return_value.success = True
            pp._run_static_analysis()

        pp.error_handler.handle_error.assert_not_called()

    def test_analyze_failure_warns(self, tmp_path):
        pp, _ = _make_pre_processor(tmp_path)
        pp._get_target_apks_for_analysis = MagicMock(return_value=["/orig/x.apk"])
        with (
            patch(f"{_MOD}.os.makedirs"),
            patch(f"{_MOD}.App"),
            patch(self._SA) as mock_sa,
        ):
            result = mock_sa.return_value.analyze.return_value
            result.success = False
            result.errors = ["err"]
            pp._run_static_analysis()

        pp.logger.warning.assert_any_call("Static analysis failed for x.apk: ['err']")

    def test_per_apk_exception_handled(self, tmp_path):
        pp, _ = _make_pre_processor(tmp_path)
        pp._get_target_apks_for_analysis = MagicMock(return_value=["/orig/x.apk"])
        with (
            patch(f"{_MOD}.os.makedirs"),
            patch(f"{_MOD}.App"),
            patch(self._SA) as mock_sa,
        ):
            mock_sa.return_value.analyze.side_effect = RuntimeError("boom")
            pp._run_static_analysis()

        pp.error_handler.handle_error.assert_called_once()

    def test_import_error_warns(self, tmp_path):
        pp, _ = _make_pre_processor(tmp_path)
        with (
            patch(f"{_MOD}.os.makedirs"),
            patch.dict(
                sys.modules,
                {"rv_static_analysis.analysis.static.static_analysis": None},
            ),
        ):
            pp._run_static_analysis()

        pp.logger.warning.assert_any_call(
            "Static analysis module not available - skipping static analysis"
        )

    def test_setup_exception_handled(self, tmp_path):
        pp, config = _make_pre_processor(tmp_path)
        config.get_static_analysis_config.side_effect = RuntimeError("boom")
        with (
            patch(f"{_MOD}.os.makedirs"),
            patch(f"{_MOD}.App"),
            patch(self._SA),
        ):
            pp._run_static_analysis()

        pp.error_handler.handle_error.assert_called_once()


class TestGetInstrumentedApksExceptionBranch:
    """Covers the App() constructor exception path in get_instrumented_apks()."""

    def test_app_constructor_exception_handled(self, tmp_path):
        pp, config = _make_pre_processor(tmp_path)
        inst_dir = tmp_path / "out" / "instrumented_apks"
        inst_dir.mkdir(parents=True)
        (inst_dir / "x.apk").write_bytes(b"apk")
        (inst_dir / "x.apk.json").write_text("{}")
        # Empty original list so the fallback loop makes no further App() calls.
        config.get_apk_list.return_value = []

        with patch(f"{_MOD}.App", side_effect=RuntimeError("boom")):
            result = pp.get_instrumented_apks()

        pp.error_handler.handle_error.assert_called_once()
        assert result == []


class TestSkipInstrumentWithStaticAnalysis:
    """`--skip-instrument --static-analysis` aborts instead of analysing nothing
    (INV-EXP-37)."""

    def test_aborts_naming_the_flag_and_the_directory(self, tmp_path):
        pp, _ = _make_pre_processor(tmp_path)

        with pytest.raises(PreProcessingConfigurationError) as excinfo:
            pp._assert_instrumentation_available_for_static(instrument=False)

        message = str(excinfo.value)
        assert "--skip-instrument" in message
        assert "--static-analysis" in message
        assert str(tmp_path / "out" / "instrumented_apks") in message

    def test_previous_runs_instrumented_apks_are_a_legitimate_input(self, tmp_path):
        """The test is the directory, not the flag: pointing `--apks-dir` at an
        earlier run's `instrumented_apks/` is the documented way to reuse it."""
        pp, _ = _make_pre_processor(tmp_path)
        inst_dir = tmp_path / "out" / "instrumented_apks"
        inst_dir.mkdir(parents=True)
        (inst_dir / "a.apk").write_bytes(b"apk")

        pp._assert_instrumentation_available_for_static(instrument=False)

        assert any(
            "reusing" in call.args[0].lower()
            for call in pp.logger.info.call_args_list
            if call.args
        )

    def test_instrumentation_requested_never_aborts(self, tmp_path):
        pp, _ = _make_pre_processor(tmp_path)

        pp._assert_instrumentation_available_for_static(instrument=True)


class TestLoggedSetEqualsExecutedSet:
    """INV-EXP-16 as modified: what the log names and what runs are one set."""

    def test_mixed_case_logs_no_exclusion(self, tmp_path):
        """Three instrumented APKs, one without an artefact: all three execute
        and the only thing the log claims about the third is that it will run
        without a denominator.

        That the third still contributes violations is pinned one layer down,
        at the report writer — `test_missing_json_counts_and_errors_survive` in
        rv-platform's `test_result_processor.py` — because violations are
        reconstructed from logcat and never consult the static artefact.
        """
        pp, config = _make_pre_processor(tmp_path)
        inst_dir = tmp_path / "out" / "instrumented_apks"
        inst_dir.mkdir(parents=True)
        for name in ("a.apk", "b.apk", "c.apk"):
            (inst_dir / name).write_bytes(b"apk")
        (inst_dir / "a.apk.json").write_text("{}")
        (inst_dir / "b.apk.json").write_text("{}")

        with patch(f"{_MOD}.App") as MockApp:
            MockApp.side_effect = _app_stub
            result = pp.get_instrumented_apks()

        assert sorted(os.path.basename(app.path) for app in result) == [
            "a.apk",
            "b.apk",
            "c.apk",
        ]
        warning = _only_warning_naming(pp, "coverage denominator")
        assert "1 of 3" in warning
        assert "c.apk" in warning
        assert not any(
            "exclud" in call.args[0].lower()
            for call in pp.logger.warning.call_args_list
            if call.args
        )


class TestConsolidatedStaticAnalysisReport:
    """One statement of what will run without a denominator (INV-EXP-39)."""

    @staticmethod
    def _populate(tmp_path, total, with_artefact):
        inst_dir = tmp_path / "out" / "instrumented_apks"
        inst_dir.mkdir(parents=True)
        for index in range(total):
            (inst_dir / f"app{index:03d}.apk").write_bytes(b"apk")
            if index < with_artefact:
                (inst_dir / f"app{index:03d}.apk.json").write_text("{}")
        return inst_dir

    def test_report_names_two_of_fifty(self, tmp_path):
        pp, _ = _make_pre_processor(tmp_path)
        self._populate(tmp_path, total=50, with_artefact=48)

        pp._report_missing_static_analysis(static_analysis=True)

        warning = _only_warning_naming(pp, "2 of 50")
        assert "app048.apk" in warning
        assert "app049.apk" in warning

    def test_skip_static_report_names_the_flag_and_the_count(self, tmp_path):
        """ "No artefact" and "no artefact because you asked for none" are
        different facts, and only the second is the reader's own decision
        (INV-EXP-39 as amended)."""
        pp, _ = _make_pre_processor(tmp_path)
        self._populate(tmp_path, total=4, with_artefact=0)

        pp._report_missing_static_analysis(static_analysis=False)

        warning = _only_warning_naming(pp, "--skip-static")
        assert "4 of 4" in warning

    def test_all_present_reports_no_warning(self, tmp_path):
        pp, _ = _make_pre_processor(tmp_path)
        self._populate(tmp_path, total=3, with_artefact=3)

        pp._report_missing_static_analysis(static_analysis=True)

        pp.logger.warning.assert_not_called()
        pp.logger.info.assert_any_call(
            "Static analysis artefact present for all 3 APKs"
        )


class TestMonitorsProvenance:
    """`--skip-monitors` must not silently instrument with another set's monitors
    (INV-EXP-38)."""

    @staticmethod
    def _write_marker(tmp_path, recorded):
        monitors_dir = tmp_path / "out" / "monitors"
        monitors_dir.mkdir(parents=True)
        (monitors_dir / "specification_set.txt").write_text(f"{recorded}\n")

    def test_wrong_set_aborts_naming_both(self, tmp_path):
        pp, config = _make_pre_processor(tmp_path)
        config.specification_set = "jca_android"
        self._write_marker(tmp_path, "generic")

        with pytest.raises(PreProcessingConfigurationError) as excinfo:
            pp._check_monitors_provenance()

        message = str(excinfo.value)
        assert "generic" in message
        assert "jca_android" in message

    def test_absent_marker_warns(self, tmp_path):
        """Absence is warn, not abort: both resume paths force
        `generate_monitors=False`, and no `out/monitors/` produced before the
        marker existed carries one — aborting would make every earlier
        experiment unresumable."""
        pp, config = _make_pre_processor(tmp_path)
        config.specification_set = "jca"

        pp._check_monitors_provenance()

        assert "jca" in _only_warning_naming(pp, "no provenance marker")

    def test_same_set_proceeds_with_a_log_line(self, tmp_path):
        pp, config = _make_pre_processor(tmp_path)
        config.specification_set = "jca"
        self._write_marker(tmp_path, "jca")

        pp._check_monitors_provenance()

        pp.logger.warning.assert_not_called()
        pp.logger.info.assert_any_call(
            "Reusing monitors generated from specification set 'jca'"
        )
