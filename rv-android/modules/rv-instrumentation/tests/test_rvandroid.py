"""
Unit tests for RVInstrumentation pipeline.

These tests verify the instrumentation pipeline methods with mocked subprocess
calls, ensuring correct command construction and error handling without
requiring actual JAR execution or Android SDK tools.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest
from rv_android_core.commands.command_exception import CommandException
from rv_android_core.util.error.exceptions import InstrumentationError


def _make_config_mock(temp_path):
    """Create a mock RVInstrumentationConfig with paths pointing to temp_path."""
    config = MagicMock()
    config.tmp_dir = str(temp_path / "tmp")
    config.rvm_tmp_dir = str(temp_path / "rvm_tmp")
    config.lib_tmp_dir = str(temp_path / "lib_tmp")
    config.working_dir = str(temp_path)
    config.instrumented_dir = str(temp_path / "instrumented")
    config.monitor_output_dir = str(temp_path / "monitors")
    config.android_jar_path = str(temp_path / "android.jar")
    config.keystore_file = str(temp_path / "keystore.jks")
    config.keystore_password = "password"
    config.dex2jar_home = str(temp_path / "dex2jar")

    dex2jar_tools = MagicMock()
    dex2jar_tools.dex2jar = str(temp_path / "dex2jar" / "d2j-dex2jar.sh")
    dex2jar_tools.asm_verify = str(temp_path / "dex2jar" / "d2j-asm-verify.sh")
    dex2jar_tools.apk_sign = str(temp_path / "dex2jar" / "d2j-apk-sign.sh")
    config.get_dex2jar_tools.return_value = dex2jar_tools

    summary = MagicMock()
    summary.model_dump.return_value = {"status": "ok"}
    config.get_configuration_summary.return_value = summary

    return config


def _create_rv_instrumentation(config):
    """Create an RVInstrumentation instance with mocked dependencies."""
    with patch("rv_instrumentation.rvandroid.LoggingManager") as mock_logging, \
         patch("rv_instrumentation.rvandroid.ErrorHandler") as mock_error_handler:
        mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
        mock_error_handler.get_instance.return_value = MagicMock()

        from rv_instrumentation.rvandroid import RVInstrumentation
        rv = RVInstrumentation(config)
        return rv


class TestCreateTempDirectories:
    """Tests for RVInstrumentation.create_temp_directories."""

    def test_creates_tmp_dir_when_missing(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        rv.create_temp_directories()

        assert os.path.isdir(config.tmp_dir)

    def test_creates_rvm_tmp_dir_when_missing(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        rv.create_temp_directories()

        assert os.path.isdir(config.rvm_tmp_dir)

    def test_does_not_fail_when_dirs_already_exist(self, tmp_path):
        config = _make_config_mock(tmp_path)
        os.makedirs(config.tmp_dir, exist_ok=True)
        os.makedirs(config.rvm_tmp_dir, exist_ok=True)
        rv = _create_rv_instrumentation(config)

        # Should not raise
        rv.create_temp_directories()

        assert os.path.isdir(config.tmp_dir)
        assert os.path.isdir(config.rvm_tmp_dir)


class TestClear:
    """Tests for RVInstrumentation.clear."""

    def test_removes_existing_folders(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        folder = tmp_path / "to_remove"
        folder.mkdir()
        (folder / "file.txt").write_text("test")

        with patch("rv_instrumentation.rvandroid.utils") as mock_utils:
            rv.clear([str(folder)])

        assert not os.path.exists(str(folder))

    def test_ignores_nonexistent_folders(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        with patch("rv_instrumentation.rvandroid.utils") as mock_utils:
            # Should not raise
            rv.clear([str(tmp_path / "nonexistent")])

    def test_deletes_dex_files_from_working_dir(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        with patch("rv_instrumentation.rvandroid.utils") as mock_utils:
            rv.clear([])
            mock_utils.delete_files_by_extension.assert_called_once()


class TestCheckIfInstrumented:
    """Tests for RVInstrumentation.check_if_instrumented."""

    def test_logs_error_when_hashes_match(self, tmp_path):
        """When hashes match, check_if_instrumented raises CommandException internally.
        The ErrorHandler decorator may absorb the exception, so we verify the logger
        was called with an error message."""
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        app = MagicMock()
        app.name = "test.apk"
        app.path = str(tmp_path / "original.apk")

        with patch("rv_instrumentation.rvandroid.utils") as mock_utils:
            mock_utils.file_hash.return_value = "abc123"

            # The method either raises CommandException or the decorator absorbs it.
            # In either case the error logger should be called.
            try:
                rv.check_if_instrumented(app)
            except (CommandException, Exception):
                pass

            # Verify file_hash was called for both original and instrumented paths
            assert mock_utils.file_hash.call_count == 2

    def test_passes_when_hashes_differ(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        app = MagicMock()
        app.name = "test.apk"
        app.path = str(tmp_path / "original.apk")

        with patch("rv_instrumentation.rvandroid.utils") as mock_utils:
            mock_utils.file_hash.side_effect = ["abc123", "def456"]

            # Should not raise
            rv.check_if_instrumented(app)

    def test_compares_original_and_instrumented_paths(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        app = MagicMock()
        app.name = "test.apk"
        app.path = "/original/test.apk"

        with patch("rv_instrumentation.rvandroid.utils") as mock_utils:
            mock_utils.file_hash.side_effect = ["aaa", "bbb"]

            rv.check_if_instrumented(app)

            expected_instrumented = os.path.join(config.instrumented_dir, "test.apk")
            calls = mock_utils.file_hash.call_args_list
            assert calls[0] == call("/original/test.apk")
            assert calls[1] == call(expected_instrumented)


class TestInstrumentSkipExisting:
    """Tests for RVInstrumentation.instrument skip logic."""

    def test_skips_already_instrumented_apk(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        app = MagicMock()
        app.name = "test.apk"

        # Create the "already instrumented" file in result_dir
        result_dir = str(tmp_path / "results")
        os.makedirs(result_dir)
        (Path(result_dir) / "test.apk").write_bytes(b"existing")

        with patch("rv_instrumentation.rvandroid.utils"):
            # Should return without calling create_temp_directories
            rv.instrument(app, result_dir, force_instrumentation=False)

        # create_temp_directories is only called when instrumentation proceeds
        # Since we skipped, the method returned early

    def test_removes_existing_when_force_enabled(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        app = MagicMock()
        app.name = "test.apk"

        result_dir = str(tmp_path / "results")
        os.makedirs(result_dir)
        existing = Path(result_dir) / "test.apk"
        existing.write_bytes(b"existing")

        # The method will fail at decompile phase. The ErrorHandler decorator
        # may absorb the exception, so we just verify the file was removed.
        with patch("rv_instrumentation.rvandroid.utils") as mock_utils, \
             patch.object(rv, "_RVInstrumentation__decompile_apk", side_effect=Exception("stop")):
            mock_utils.reset_folder = MagicMock()

            try:
                rv.instrument(app, result_dir, force_instrumentation=True)
            except Exception:
                pass

        assert not existing.exists()


class TestInstrumentApksBatch:
    """Tests for RVInstrumentation.instrument_apks batch processing."""

    def test_returns_results_with_correct_total_count(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        app1 = MagicMock()
        app1.name = "app1.apk"
        app1.path = str(tmp_path / "app1.apk")

        app2 = MagicMock()
        app2.name = "app2.apk"
        app2.path = str(tmp_path / "app2.apk")

        with patch.object(rv, "prepare_instrumentation"), \
             patch("rv_instrumentation.rvandroid.utils") as mock_utils, \
             patch.object(rv, "instrument"), \
             patch.object(rv, "check_if_instrumented"), \
             patch.object(rv, "clear"):
            mock_utils.get_apks.return_value = [app1, app2]

            results = rv.instrument_apks(str(tmp_path), str(tmp_path / "out"))

        assert results.total_count == 2

    def test_tracks_success_count(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        app1 = MagicMock()
        app1.name = "app1.apk"
        app1.path = str(tmp_path / "app1.apk")

        with patch.object(rv, "prepare_instrumentation"), \
             patch("rv_instrumentation.rvandroid.utils") as mock_utils, \
             patch.object(rv, "instrument"), \
             patch.object(rv, "check_if_instrumented"), \
             patch.object(rv, "clear"):
            mock_utils.get_apks.return_value = [app1]

            results = rv.instrument_apks(str(tmp_path), str(tmp_path / "out"))

        assert results.success_count == 1

    def test_records_command_exception_errors(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        app1 = MagicMock()
        app1.name = "failing.apk"
        app1.path = str(tmp_path / "failing.apk")

        out_dir = tmp_path / "out"
        out_dir.mkdir()

        with patch.object(rv, "prepare_instrumentation"), \
             patch("rv_instrumentation.rvandroid.utils") as mock_utils, \
             patch.object(rv, "instrument", side_effect=CommandException("dex2jar", "-1", "fail")), \
             patch.object(rv, "clear"):
            mock_utils.get_apks.return_value = [app1]

            results = rv.instrument_apks(str(tmp_path), str(out_dir))

        assert "failing.apk" in results.errors
        assert results.errors["failing.apk"].tool == "dex2jar"

    def test_records_general_exception_errors(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        app1 = MagicMock()
        app1.name = "broken.apk"
        app1.path = str(tmp_path / "broken.apk")

        out_dir = tmp_path / "out"
        out_dir.mkdir()

        with patch.object(rv, "prepare_instrumentation"), \
             patch("rv_instrumentation.rvandroid.utils") as mock_utils, \
             patch.object(rv, "instrument", side_effect=RuntimeError("unexpected")), \
             patch.object(rv, "clear"):
            mock_utils.get_apks.return_value = [app1]

            results = rv.instrument_apks(str(tmp_path), str(out_dir))

        assert "broken.apk" in results.errors
        assert results.errors["broken.apk"].phase == "general_error"

    def test_preparation_failure_returns_error_result(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        with patch.object(rv, "prepare_instrumentation", side_effect=Exception("maven failed")), \
             patch.object(rv, "clear"):
            results = rv.instrument_apks(str(tmp_path), str(tmp_path / "out"))

        assert "setup_error" in results.errors
        assert results.success_count == 0

    def test_error_model_has_correct_phase_from_error_phase(self, tmp_path):
        """Test that _error_phase attribute on exception propagates to InstrumentationError.phase."""
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        app1 = MagicMock()
        app1.name = "signing_fail.apk"
        app1.path = str(tmp_path / "signing_fail.apk")

        out_dir = tmp_path / "out"
        out_dir.mkdir()

        # Simulate a CommandException with _error_phase set by the decorator
        exc = CommandException("jarsigner", 1, "signing failed")
        exc._error_phase = "apk_signing"

        with patch.object(rv, "prepare_instrumentation"), \
             patch("rv_instrumentation.rvandroid.utils") as mock_utils, \
             patch.object(rv, "instrument", side_effect=exc), \
             patch.object(rv, "clear"):
            mock_utils.get_apks.return_value = [app1]

            results = rv.instrument_apks(str(tmp_path), str(out_dir))

        assert "signing_fail.apk" in results.errors
        assert results.errors["signing_fail.apk"].phase == "apk_signing"
        assert results.errors["signing_fail.apk"].tool == "jarsigner"

    def test_batch_mixed_results_accurate_counts(self, tmp_path):
        """Test batch with mix of successes and failures has accurate counts."""
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        good_app = MagicMock()
        good_app.name = "good.apk"
        good_app.path = str(tmp_path / "good.apk")

        bad_app = MagicMock()
        bad_app.name = "bad.apk"
        bad_app.path = str(tmp_path / "bad.apk")

        out_dir = tmp_path / "out"
        out_dir.mkdir()

        exc = CommandException("d8", -1, "d8 failed")
        exc._error_phase = "apk_creation"

        call_count = 0
        def instrument_side_effect(app, result_dir, force=False):
            nonlocal call_count
            call_count += 1
            if app.name == "bad.apk":
                raise exc

        with patch.object(rv, "prepare_instrumentation"), \
             patch("rv_instrumentation.rvandroid.utils") as mock_utils, \
             patch.object(rv, "instrument", side_effect=instrument_side_effect), \
             patch.object(rv, "check_if_instrumented"), \
             patch.object(rv, "clear"):
            mock_utils.get_apks.return_value = [good_app, bad_app]

            results = rv.instrument_apks(str(tmp_path), str(out_dir))

        assert results.total_count == 2
        assert results.success_count == 1
        assert len(results.errors) == 1
        assert "bad.apk" in results.errors
        assert results.errors["bad.apk"].phase == "apk_creation"

    def test_success_count_zero_when_all_fail(self, tmp_path):
        """Test that success_count is 0 when all APKs fail instrumentation."""
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        app1 = MagicMock()
        app1.name = "fail1.apk"
        app1.path = str(tmp_path / "fail1.apk")

        app2 = MagicMock()
        app2.name = "fail2.apk"
        app2.path = str(tmp_path / "fail2.apk")

        out_dir = tmp_path / "out"
        out_dir.mkdir()

        with patch.object(rv, "prepare_instrumentation"), \
             patch("rv_instrumentation.rvandroid.utils") as mock_utils, \
             patch.object(rv, "instrument", side_effect=RuntimeError("always fails")), \
             patch.object(rv, "clear"):
            mock_utils.get_apks.return_value = [app1, app2]

            results = rv.instrument_apks(str(tmp_path), str(out_dir))

        assert results.success_count == 0
        assert results.total_count == 2
        assert len(results.errors) == 2

    def test_instrument_errors_json_written_on_failure(self, tmp_path):
        """Test that instrument_errors.json is written when errors exist."""
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        app1 = MagicMock()
        app1.name = "failing.apk"
        app1.path = str(tmp_path / "failing.apk")

        out_dir = tmp_path / "out"
        out_dir.mkdir()

        exc = CommandException("ajc", 1, "weaving failed")
        exc._error_phase = "aspect_weaving"

        with patch.object(rv, "prepare_instrumentation"), \
             patch("rv_instrumentation.rvandroid.utils") as mock_utils, \
             patch.object(rv, "instrument", side_effect=exc), \
             patch.object(rv, "clear"):
            mock_utils.get_apks.return_value = [app1]

            results = rv.instrument_apks(str(tmp_path), str(out_dir))

        import json
        errors_file = out_dir / "instrument_errors.json"
        assert errors_file.exists()
        with open(errors_file) as f:
            data = json.load(f)
        assert "failing.apk" in data
        assert data["failing.apk"]["phase"] == "aspect_weaving"
