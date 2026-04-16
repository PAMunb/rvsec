"""
Tests for PreProcessor downstream filtering (gh49).

Validates that:
- _get_target_apks_for_analysis() filters by instrumentation success
- get_instrumented_apks() filters by static analysis data presence
"""

import os
from unittest.mock import MagicMock, patch


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
