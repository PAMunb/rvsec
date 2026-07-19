"""
Tests for PreProcessor downstream filtering (gh49).

Validates that:
- _get_target_apks_for_analysis() filters by instrumentation success
- get_instrumented_apks() filters by static analysis data presence
"""

import os
import sys
from unittest.mock import MagicMock, patch

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
    """Tests for get_instrumented_apks SA filtering."""

    def test_excludes_apks_without_json(self, tmp_path):
        pp, config = _make_pre_processor(tmp_path)

        inst_dir = tmp_path / "out" / "instrumented_apks"
        inst_dir.mkdir(parents=True)

        # good.apk has .json, bad.apk does not
        (inst_dir / "good.apk").write_bytes(b"apk")
        (inst_dir / "good.apk.json").write_text("{}")
        (inst_dir / "bad.apk").write_bytes(b"apk")

        with patch("rv_experiment.experiment.workflow.pre_processor.App") as MockApp:
            MockApp.side_effect = lambda app_path: MagicMock(
                name=os.path.basename(app_path), path=app_path
            )
            result = pp.get_instrumented_apks()

        assert len(result) == 1
        assert result[0].path == str(inst_dir / "good.apk")

    def test_includes_apks_with_json(self, tmp_path):
        pp, config = _make_pre_processor(tmp_path)

        inst_dir = tmp_path / "out" / "instrumented_apks"
        inst_dir.mkdir(parents=True)
        (inst_dir / "a.apk").write_bytes(b"apk")
        (inst_dir / "a.apk.json").write_text("{}")
        (inst_dir / "b.apk").write_bytes(b"apk")
        (inst_dir / "b.apk.json").write_text("{}")

        with patch("rv_experiment.experiment.workflow.pre_processor.App") as MockApp:
            MockApp.side_effect = lambda app_path: MagicMock(
                name=os.path.basename(app_path), path=app_path
            )
            result = pp.get_instrumented_apks()

        assert len(result) == 2

    def test_falls_back_to_originals_when_no_apk_has_json(self, tmp_path):
        pp, config = _make_pre_processor(tmp_path)

        inst_dir = tmp_path / "out" / "instrumented_apks"
        inst_dir.mkdir(parents=True)
        (inst_dir / "nojson.apk").write_bytes(b"apk")

        config.get_apk_list.return_value = ["/originals/fallback.apk"]

        with patch("rv_experiment.experiment.workflow.pre_processor.App") as MockApp:
            MockApp.side_effect = lambda app_path: MagicMock(
                name=os.path.basename(app_path), path=app_path
            )
            result = pp.get_instrumented_apks()

        # Should fall back to originals
        assert len(result) == 1
        assert result[0].path == "/originals/fallback.apk"

    def test_returns_originals_when_instrumented_dir_missing(self, tmp_path):
        pp, config = _make_pre_processor(tmp_path)

        config.get_apk_list.return_value = ["/originals/app.apk"]

        with patch("rv_experiment.experiment.workflow.pre_processor.App") as MockApp:
            MockApp.side_effect = lambda app_path: MagicMock(
                name=os.path.basename(app_path), path=app_path
            )
            result = pp.get_instrumented_apks()

        assert len(result) == 1
        assert result[0].path == "/originals/app.apk"


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
        pp, _ = _make_pre_processor(tmp_path)
        with (
            patch(f"{_MOD}.os.makedirs"),
            patch(self._GEN) as mock_gen,
        ):
            mock_gen.return_value.generate_monitors.return_value = True
            pp._generate_monitors()

        pp.logger.warning.assert_not_called()
        pp.error_handler.handle_error.assert_not_called()

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

        pp.logger.warning.assert_any_call(
            "Static analysis failed for x.apk: ['err']"
        )

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
