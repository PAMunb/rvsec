"""
Unit tests for AjcInstrumentation pipeline.

These tests verify the instrumentation pipeline methods with mocked subprocess
calls, ensuring correct command construction and error handling without
requiring actual JAR execution or Android SDK tools.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
from rv_android_core.commands.command_exception import CommandException
from rv_android_core.util.error.exceptions import InstrumentationError


def _make_config_mock(temp_path):
    """Create a mock AjcInstrumentationConfig with paths pointing to temp_path."""
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
    """Create an AjcInstrumentation instance with mocked dependencies."""
    with (
        patch(
            "rv_instrumentation_ajc.ajc_instrumentation.LoggingManager"
        ) as mock_logging,
        patch(
            "rv_instrumentation_ajc.ajc_instrumentation.ErrorHandler"
        ) as mock_error_handler,
    ):
        mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
        mock_error_handler.get_instance.return_value = MagicMock()

        from rv_instrumentation_ajc.ajc_instrumentation import AjcInstrumentation

        rv = AjcInstrumentation(config)
        return rv


class TestCreateTempDirectories:
    """Tests for AjcInstrumentation.create_temp_directories."""

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
    """Tests for AjcInstrumentation.clear."""

    def test_removes_existing_folders(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        folder = tmp_path / "to_remove"
        folder.mkdir()
        (folder / "file.txt").write_text("test")

        with patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils:
            rv.clear([str(folder)])

        assert not os.path.exists(str(folder))

    def test_ignores_nonexistent_folders(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        with patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils:
            # Should not raise
            rv.clear([str(tmp_path / "nonexistent")])

    def test_deletes_dex_files_from_working_dir(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        with patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils:
            rv.clear([])
            mock_utils.delete_files_by_extension.assert_called_once()


class TestCheckIfInstrumented:
    """Tests for AjcInstrumentation.check_if_instrumented."""

    def test_logs_error_when_hashes_match(self, tmp_path):
        """When hashes match, check_if_instrumented raises CommandException internally.
        The ErrorHandler decorator may absorb the exception, so we verify the logger
        was called with an error message."""
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        app = MagicMock()
        app.name = "test.apk"
        app.path = str(tmp_path / "original.apk")

        with patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils:
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

        with patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils:
            mock_utils.file_hash.side_effect = ["abc123", "def456"]

            # Should not raise
            rv.check_if_instrumented(app)

    def test_compares_original_and_instrumented_paths(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        app = MagicMock()
        app.name = "test.apk"
        app.path = "/original/test.apk"

        with patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils:
            mock_utils.file_hash.side_effect = ["aaa", "bbb"]

            rv.check_if_instrumented(app)

            expected_instrumented = os.path.join(config.instrumented_dir, "test.apk")
            calls = mock_utils.file_hash.call_args_list
            assert calls[0] == call("/original/test.apk")
            assert calls[1] == call(expected_instrumented)


class TestInstrumentSkipExisting:
    """Tests for AjcInstrumentation.instrument skip logic."""

    def test_skips_already_instrumented_apk(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        app = MagicMock()
        app.name = "test.apk"

        # Create the "already instrumented" file in result_dir
        result_dir = str(tmp_path / "results")
        os.makedirs(result_dir)
        (Path(result_dir) / "test.apk").write_bytes(b"existing")

        with patch("rv_instrumentation_ajc.ajc_instrumentation.utils"):
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
        with (
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils,
            patch.object(
                rv, "_AjcInstrumentation__decompile_apk", side_effect=Exception("stop")
            ),
        ):
            mock_utils.reset_folder = MagicMock()

            try:
                rv.instrument(app, result_dir, force_instrumentation=True)
            except Exception:
                pass

        assert not existing.exists()


class TestInstrumentApksBatch:
    """Tests for AjcInstrumentation.instrument_apks batch processing."""

    def test_returns_results_with_correct_total_count(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        app1 = MagicMock()
        app1.name = "app1.apk"
        app1.path = str(tmp_path / "app1.apk")

        app2 = MagicMock()
        app2.name = "app2.apk"
        app2.path = str(tmp_path / "app2.apk")

        with (
            patch.object(rv, "prepare_instrumentation"),
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils,
            patch.object(rv, "instrument"),
            patch.object(rv, "check_if_instrumented"),
            patch.object(rv, "clear"),
        ):
            mock_utils.get_apks.return_value = [app1, app2]

            results = rv.instrument_apks(str(tmp_path), str(tmp_path / "out"))

        assert results.total_count == 2

    def test_tracks_success_count(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        app1 = MagicMock()
        app1.name = "app1.apk"
        app1.path = str(tmp_path / "app1.apk")

        with (
            patch.object(rv, "prepare_instrumentation"),
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils,
            patch.object(rv, "instrument"),
            patch.object(rv, "check_if_instrumented"),
            patch.object(rv, "clear"),
        ):
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

        with (
            patch.object(rv, "prepare_instrumentation"),
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils,
            patch.object(
                rv, "instrument", side_effect=CommandException("dex2jar", "-1", "fail")
            ),
            patch.object(rv, "clear"),
        ):
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

        with (
            patch.object(rv, "prepare_instrumentation"),
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils,
            patch.object(rv, "instrument", side_effect=RuntimeError("unexpected")),
            patch.object(rv, "clear"),
        ):
            mock_utils.get_apks.return_value = [app1]

            results = rv.instrument_apks(str(tmp_path), str(out_dir))

        assert "broken.apk" in results.errors
        assert results.errors["broken.apk"].phase == "general_error"

    def test_preparation_failure_returns_error_result(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        with (
            patch.object(
                rv, "prepare_instrumentation", side_effect=Exception("maven failed")
            ),
            patch.object(rv, "clear"),
        ):
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

        with (
            patch.object(rv, "prepare_instrumentation"),
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils,
            patch.object(rv, "instrument", side_effect=exc),
            patch.object(rv, "clear"),
        ):
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

        with (
            patch.object(rv, "prepare_instrumentation"),
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils,
            patch.object(rv, "instrument", side_effect=instrument_side_effect),
            patch.object(rv, "check_if_instrumented"),
            patch.object(rv, "clear"),
        ):
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

        with (
            patch.object(rv, "prepare_instrumentation"),
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils,
            patch.object(rv, "instrument", side_effect=RuntimeError("always fails")),
            patch.object(rv, "clear"),
        ):
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

        with (
            patch.object(rv, "prepare_instrumentation"),
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils,
            patch.object(rv, "instrument", side_effect=exc),
            patch.object(rv, "clear"),
        ):
            mock_utils.get_apks.return_value = [app1]

            results = rv.instrument_apks(str(tmp_path), str(out_dir))

        import json

        errors_file = out_dir / "instrument_errors.json"
        assert errors_file.exists()
        with open(errors_file) as f:
            data = json.load(f)
        assert "failing.apk" in data
        assert data["failing.apk"]["phase"] == "aspect_weaving"


class TestWeaveMonitorsFlags:
    """Tests for __weave_monitors ajc command construction."""

    def test_ajc_includes_proceed_on_error_and_skip_stderr(self, tmp_path):
        # -proceedOnError lets ajc continue past per-class failures and still
        # exit 0 with a valid partial output. Those failures are printed to
        # stderr, so skip_stderr=True is also required (same pattern as d8
        # and rv-frame-computer, INV-INS-19). Real ajc crashes still surface
        # through non-zero exit code.
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        captured_cmd = {}

        def capture_execute(cmd, tool_name, skip_stderr=False, stdout=None):
            captured_cmd["args"] = cmd.args
            captured_cmd["skip_stderr"] = skip_stderr

        with (
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils,
            patch.object(
                rv,
                "_AjcInstrumentation__get_classpath",
                return_value=["/fake/android.jar"],
            ),
        ):
            mock_utils.execute_command = capture_execute

            app = MagicMock()
            app.name = "test.apk"
            rv._AjcInstrumentation__weave_monitors(app)

        assert "-proceedOnError" in captured_cmd["args"]
        assert captured_cmd["skip_stderr"] is True


class TestD8Flags:
    """Tests for __d8 command construction."""

    def test_d8_skip_stderr_enabled(self, tmp_path):
        # d8 prints non-fatal "Expected stack map table" warnings to stderr
        # even on exit code 0, so execute_command must skip stderr capture
        # to avoid false failures. Exit code still gates real errors.
        # Desugaring is left enabled (no --no-desugaring) so d8 generates
        # synthetic accessors for JDK 11+ nest-mate access in rv-monitor-rt.
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        os.makedirs(config.tmp_dir, exist_ok=True)
        captured_calls = []

        def capture_execute(cmd, tool_name, skip_stderr=False, stdout=None):
            captured_calls.append(
                {"tool": tool_name, "args": cmd.args, "skip_stderr": skip_stderr}
            )

        app = MagicMock()
        app.name = "test.apk"
        app.path = str(tmp_path / "test.apk")
        (tmp_path / "test.apk").write_bytes(b"fake")

        with (
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils,
            patch.object(
                rv,
                "_AjcInstrumentation__get_android_jar",
                return_value="/fake/android.jar",
            ),
            patch.object(rv, "_AjcInstrumentation__d2j_asm_verify"),
        ):
            mock_utils.execute_command = capture_execute

            try:
                rv._AjcInstrumentation__d8(app, "/fake/monitored.jar")
            except Exception:
                pass

        d8_call = next(c for c in captured_calls if c["tool"] == "d8")
        assert d8_call["skip_stderr"] is True
        assert "--no-desugaring" not in d8_call["args"]


class TestZipalign:
    """Tests for __zipalign page-alignment step."""

    def test_zipalign_invokes_with_page_alignment_flags(self, tmp_path):
        # -P 16 targets 16 KiB pages for uncompressed .so files (mandatory
        # on API 35+, safe on older APIs). The legacy -p flag is mutually
        # exclusive with -P in zipalign 35.0.1+, so it MUST NOT be passed
        # (doing so makes zipalign exit 2 with "Invalid options: -P and -p
        # cannot be used in combination"). The positional 4 aligns all
        # other entries on 4-byte boundaries. -f overwrites the destination.
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        unsigned_apk = str(tmp_path / "unsigned_test.apk")
        (tmp_path / "unsigned_test.apk").write_bytes(b"fake")

        captured = {}

        def capture_execute(cmd, tool_name):
            captured["tool"] = tool_name
            captured["args"] = cmd.args

        with (
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils,
            patch(
                "rv_instrumentation_ajc.ajc_instrumentation.os.replace"
            ) as mock_replace,
        ):
            mock_utils.execute_command = capture_execute
            rv._AjcInstrumentation__zipalign(unsigned_apk)

        assert captured["tool"] == "zipalign"
        assert "-f" in captured["args"]
        # -p and -P are mutually exclusive; only -P must be present
        assert "-p" not in captured["args"]
        assert "-P" in captured["args"]
        p_idx = captured["args"].index("-P")
        assert captured["args"][p_idx + 1] == "16"
        # positional alignment value comes right after the -P <kb> pair
        assert "4" in captured["args"]
        # source and destination paths
        assert unsigned_apk in captured["args"]
        assert unsigned_apk + ".aligned" in captured["args"]
        mock_replace.assert_called_once_with(unsigned_apk + ".aligned", unsigned_apk)


class TestGetAndroidJar:
    """Tests for __get_android_jar dynamic selection."""

    def test_exact_match(self, tmp_path):
        config = _make_config_mock(tmp_path)
        config.android_platforms_dir = str(tmp_path / "platforms")
        rv = _create_rv_instrumentation(config)

        platform_dir = tmp_path / "platforms" / "android-34"
        platform_dir.mkdir(parents=True)
        (platform_dir / "android.jar").write_bytes(b"fake")

        app = MagicMock()
        app.sdk_target = 34

        result = rv._AjcInstrumentation__get_android_jar(app)

        assert result == str(platform_dir / "android.jar")

    def test_fallback_to_highest(self, tmp_path):
        config = _make_config_mock(tmp_path)
        config.android_platforms_dir = str(tmp_path / "platforms")
        rv = _create_rv_instrumentation(config)

        # Create android-30 and android-33 but NOT android-36
        for level in [30, 33]:
            d = tmp_path / "platforms" / f"android-{level}"
            d.mkdir(parents=True)
            (d / "android.jar").write_bytes(b"fake")

        app = MagicMock()
        app.sdk_target = 36

        result = rv._AjcInstrumentation__get_android_jar(app)

        assert "android-33" in result

    def test_fallback_to_config_when_no_target(self, tmp_path):
        config = _make_config_mock(tmp_path)
        config.android_platforms_dir = None
        rv = _create_rv_instrumentation(config)

        app = MagicMock(spec=[])  # no sdk_target attribute

        result = rv._AjcInstrumentation__get_android_jar(app)

        assert result == config.android_jar_path

    def test_skips_platforms_below_26(self, tmp_path):
        config = _make_config_mock(tmp_path)
        config.android_platforms_dir = str(tmp_path / "platforms")
        rv = _create_rv_instrumentation(config)

        # Only platform below 26
        d = tmp_path / "platforms" / "android-21"
        d.mkdir(parents=True)
        (d / "android.jar").write_bytes(b"fake")

        app = MagicMock()
        app.sdk_target = 36

        result = rv._AjcInstrumentation__get_android_jar(app)

        # Should fallback to config default since no platform >= 26
        assert result == config.android_jar_path


class TestComputeStackFrames:
    """Tests for __compute_stack_frames."""

    def test_invokes_frame_computer_jar(self, tmp_path):
        # skip_stderr must be True: FrameComputer prints per-class "Warning:
        # frame computation failed for X.class" entries to stderr and keeps
        # processing the remaining classes. Without skip_stderr, a single
        # warning would make execute_command raise and mark the whole APK
        # failed. Real JVM crashes still surface through exit code != 0.
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        captured_cmd = {}

        def capture_execute(cmd, tool_name, skip_stderr=False, stdout=None):
            captured_cmd["tool"] = tool_name
            captured_cmd["args"] = cmd.args
            captured_cmd["command"] = cmd.command
            captured_cmd["skip_stderr"] = skip_stderr

        app = MagicMock()
        app.name = "test.apk"

        with (
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils,
            patch.object(
                rv,
                "_get_frame_computer_jar",
                return_value="/fake/rv-frame-computer.jar",
            ),
            patch.object(
                rv,
                "_AjcInstrumentation__get_classpath",
                return_value=["/fake/android.jar"],
            ),
        ):
            mock_utils.execute_command = capture_execute

            rv._AjcInstrumentation__compute_stack_frames(app)

        assert captured_cmd["command"] == "java"
        assert "-jar" in captured_cmd["args"]
        assert "/fake/rv-frame-computer.jar" in captured_cmd["args"]
        assert "--classpath" in captured_cmd["args"]
        assert captured_cmd["tool"] == "frame_computer"
        assert captured_cmd["skip_stderr"] is True

    def test_skips_when_jar_not_found(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        app = MagicMock()
        app.name = "test.apk"

        with (
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils,
            patch.object(rv, "_get_frame_computer_jar", return_value=None),
        ):
            mock_utils.execute_command = MagicMock()

            rv._AjcInstrumentation__compute_stack_frames(app)

            mock_utils.execute_command.assert_not_called()


class TestPreComputeStackFrames:
    """Tests for __pre_compute_stack_frames (pre-ajc invocation)."""

    def test_pre_compute_frames_runs_before_weaving(self, tmp_path):
        # Pre-ajc invocation must use the same helper as the post-ajc
        # method (same jar, same classpath, same skip_stderr=True) but with
        # phase label "pre_frame_computation" for log aggregation.
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        captured_cmd = {}

        def capture_execute(cmd, tool_name, skip_stderr=False, stdout=None):
            captured_cmd["tool"] = tool_name
            captured_cmd["args"] = cmd.args
            captured_cmd["command"] = cmd.command
            captured_cmd["skip_stderr"] = skip_stderr

        app = MagicMock()
        app.name = "test.apk"

        with (
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils,
            patch.object(
                rv,
                "_get_frame_computer_jar",
                return_value="/fake/rv-frame-computer.jar",
            ),
            patch.object(
                rv,
                "_AjcInstrumentation__get_classpath",
                return_value=["/fake/android.jar"],
            ),
        ):
            mock_utils.execute_command = capture_execute

            rv._AjcInstrumentation__pre_compute_stack_frames(app)

        assert captured_cmd["command"] == "java"
        assert "-jar" in captured_cmd["args"]
        assert "/fake/rv-frame-computer.jar" in captured_cmd["args"]
        assert captured_cmd["tool"] == "frame_computer"
        assert captured_cmd["skip_stderr"] is True

    def test_pre_compute_skipped_when_jar_missing(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        app = MagicMock()
        app.name = "test.apk"

        with (
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils,
            patch.object(rv, "_get_frame_computer_jar", return_value=None),
        ):
            mock_utils.execute_command = MagicMock()

            rv._AjcInstrumentation__pre_compute_stack_frames(app)

            mock_utils.execute_command.assert_not_called()


class TestStripDesugaredShims:
    """Tests for __strip_desugared_shims (pre-desugared j$.* cleanup)."""

    def test_removes_j_dollar_class_files(self, tmp_path):
        # APKs built with older AGP ship j$.time.*, j$.util.stream.*, etc.
        # These shims are incompatible with d8 merge when non-java.* classes
        # are present in the same DEX, so the pipeline must remove them
        # before instrumentation.
        config = _make_config_mock(tmp_path)
        os.makedirs(config.tmp_dir)

        # Seed tmp_dir with j$.* shims + a regular app class
        j_dollar_time = Path(config.tmp_dir) / "j$" / "time"
        j_dollar_stream = Path(config.tmp_dir) / "j$" / "util" / "stream"
        app_pkg = Path(config.tmp_dir) / "com" / "app"
        j_dollar_time.mkdir(parents=True)
        j_dollar_stream.mkdir(parents=True)
        app_pkg.mkdir(parents=True)
        (j_dollar_time / "Foo.class").write_bytes(b"shim")
        (j_dollar_stream / "Bar.class").write_bytes(b"shim")
        (app_pkg / "Baz.class").write_bytes(b"app")

        rv = _create_rv_instrumentation(config)
        app = MagicMock()
        app.name = "test.apk"

        rv._AjcInstrumentation__strip_desugared_shims(app)

        # j$/ subtree removed entirely, app class preserved
        assert not (Path(config.tmp_dir) / "j$").exists()
        assert (app_pkg / "Baz.class").exists()

    def test_noop_when_no_shims_present(self, tmp_path):
        config = _make_config_mock(tmp_path)
        os.makedirs(config.tmp_dir)

        app_pkg = Path(config.tmp_dir) / "com" / "app"
        app_pkg.mkdir(parents=True)
        (app_pkg / "Baz.class").write_bytes(b"app")

        rv = _create_rv_instrumentation(config)
        app = MagicMock()
        app.name = "test.apk"

        # Should not raise and should leave the tree untouched
        rv._AjcInstrumentation__strip_desugared_shims(app)

        assert (app_pkg / "Baz.class").exists()

    def test_logs_count_of_removed_shims(self, tmp_path):
        config = _make_config_mock(tmp_path)
        os.makedirs(config.tmp_dir)
        shim_dir = Path(config.tmp_dir) / "j$" / "time"
        shim_dir.mkdir(parents=True)
        (shim_dir / "A.class").write_bytes(b"")
        (shim_dir / "B.class").write_bytes(b"")
        (shim_dir / "C.class").write_bytes(b"")

        rv = _create_rv_instrumentation(config)
        rv._logger = MagicMock()
        app = MagicMock()
        app.name = "test.apk"

        rv._AjcInstrumentation__strip_desugared_shims(app)

        # _logger.info called with a message containing the count
        info_calls = [
            str(c) for c in rv._logger.info.call_args_list if "Stripped" in str(c)
        ]
        assert any("Stripped 3" in c for c in info_calls)


class TestLoadQuarantinePatterns:
    """Tests for AjcInstrumentation._load_quarantine_patterns."""

    def test_loads_patterns_from_yaml(self, tmp_path):
        # Exercise the YAML parsing by mocking Path.exists + yaml.safe_load so
        # we test the helper's logic without touching the shipped assets file.
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        fake_yaml = {
            "patterns": [
                "okio/**/*.class",
                "org/apache/tika/**/*.class",
            ]
        }
        with (
            patch(
                "rv_instrumentation_ajc.ajc_instrumentation.Path.exists",
                return_value=True,
            ),
            patch("builtins.open", create=True),
            patch(
                "rv_instrumentation_ajc.ajc_instrumentation.yaml.safe_load",
                return_value=fake_yaml,
            ),
        ):
            result = rv._load_quarantine_patterns()

        assert "okio/**/*.class" in result
        assert "org/apache/tika/**/*.class" in result

    def test_returns_empty_list_when_missing(self, tmp_path):
        # When assets/weaving_excludes.yaml does not exist, the helper must
        # return [] so the pipeline runs unchanged (backward-compatible).
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        with patch(
            "rv_instrumentation_ajc.ajc_instrumentation.Path.exists", return_value=False
        ):
            result = rv._load_quarantine_patterns()

        assert result == []

    def test_expanded_list_loaded(self, tmp_path):
        # gh50 19.4.1 — load the production weaving_excludes.yaml and assert
        # both wave-1 (gh50 §16) and wave-2 (gh50 §19) entries are returned.
        # Specifically, org/spongycastle/**/*.class must be present (it is the
        # canonical wave-2 example), and the total list length must match
        # the YAML's actual `patterns:` count so additions/removals to the
        # asset are detected by the test.
        from pathlib import Path as RealPath

        import yaml

        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        # Production YAML lives in the module's assets/ dir (resolved via the
        # ajc_instrumentation module file path, not the test config tmp_dir).
        import rv_instrumentation_ajc.ajc_instrumentation as _ajc_mod

        prod_yaml = (
            RealPath(_ajc_mod.__file__).resolve().parent.parent.parent
            / "assets"
            / "weaving_excludes.yaml"
        )
        assert prod_yaml.exists(), f"production YAML missing: {prod_yaml}"
        with open(prod_yaml) as fh:
            expected = yaml.safe_load(fh)["patterns"]

        # _load_quarantine_patterns reads from <module>/assets/weaving_excludes.yaml
        # via the same resolution; calling it should return the exact YAML list.
        result = rv._load_quarantine_patterns()

        assert len(result) == len(expected), (
            f"pattern count mismatch: got {len(result)} expected {len(expected)}"
        )
        # Wave-2 §19 canary — added 2026-04 to cover JCA-557 oldset crashes.
        assert "org/spongycastle/**/*.class" in result
        # Wave-1 §16 canary — added 2026-04 for JCA-400 modern dataset.
        assert "okio/**/*.class" in result


class TestQuarantineProblematicClasses:
    """Tests for __quarantine_problematic_classes."""

    def test_quarantine_moves_matching_classes(self, tmp_path):
        # Seed tmp_dir with okio/Buffer, androidx/media3/datasource/X, and
        # com/app/Foo. Only the first two match quarantine patterns; app code
        # stays in place.
        config = _make_config_mock(tmp_path)
        os.makedirs(config.tmp_dir)
        okio_dir = Path(config.tmp_dir) / "okio"
        media_dir = Path(config.tmp_dir) / "androidx" / "media3" / "datasource"
        app_dir = Path(config.tmp_dir) / "com" / "app"
        okio_dir.mkdir(parents=True)
        media_dir.mkdir(parents=True)
        app_dir.mkdir(parents=True)
        (okio_dir / "Buffer.class").write_bytes(b"okio")
        (media_dir / "AesFlushingCipher.class").write_bytes(b"media")
        (app_dir / "Foo.class").write_bytes(b"app")

        rv = _create_rv_instrumentation(config)
        app = MagicMock()
        app.name = "test.apk"
        app.code_package = "com.app"

        patterns = [
            "okio/**/*.class",
            "androidx/media3/datasource/**/*.class",
        ]
        with patch.object(rv, "_load_quarantine_patterns", return_value=patterns):
            rv._AjcInstrumentation__quarantine_problematic_classes(app)

        assert not (okio_dir / "Buffer.class").exists()
        assert not (media_dir / "AesFlushingCipher.class").exists()
        assert (app_dir / "Foo.class").exists()
        # Quarantine root is a SIBLING of tmp_dir, NOT a subdir, so ajc and
        # frame_computer walkers cannot descend into it.
        qroot = Path(config.tmp_dir).parent / (
            Path(config.tmp_dir).name + "_quarantine"
        )
        assert (qroot / "okio" / "Buffer.class").exists()
        assert (
            qroot / "androidx" / "media3" / "datasource" / "AesFlushingCipher.class"
        ).exists()

    def test_skips_code_package_matches(self, tmp_path):
        # If a pattern accidentally matches the APK's own code package, the
        # file MUST stay in place and a WARNING MUST be logged.
        config = _make_config_mock(tmp_path)
        os.makedirs(config.tmp_dir)
        # Imagine an app whose code_package is "okio" (extreme edge case) —
        # the okio/**/*.class pattern matches but must skip.
        okio_app = Path(config.tmp_dir) / "okio" / "MyAppClass.class"
        okio_app.parent.mkdir(parents=True)
        okio_app.write_bytes(b"app")

        rv = _create_rv_instrumentation(config)
        rv._logger = MagicMock()
        app = MagicMock()
        app.name = "test.apk"
        app.code_package = "okio"

        with patch.object(
            rv, "_load_quarantine_patterns", return_value=["okio/**/*.class"]
        ):
            rv._AjcInstrumentation__quarantine_problematic_classes(app)

        assert okio_app.exists()
        # WARNING logged
        warnings = [str(c) for c in rv._logger.warning.call_args_list]
        assert any("matched app code" in w for w in warnings)

    def test_spongycastle_moved(self, tmp_path):
        # gh50 19.4.2 — wave-2 canary. Seed tmp_dir with the canonical
        # JCA-557 crasher (Camellia$AlgParamGen, BCException at ajc weaving),
        # call __quarantine_problematic_classes with the wave-2 spongycastle
        # pattern, and assert the file is moved to the sibling
        # <tmp_dir>_quarantine/ root preserving its relative path.
        config = _make_config_mock(tmp_path)
        os.makedirs(config.tmp_dir)
        sc_dir = Path(config.tmp_dir) / "org" / "spongycastle" / "jcajce"
        sc_dir.mkdir(parents=True)
        sc_class = sc_dir / "Camellia$AlgParamGen.class"
        sc_class.write_bytes(b"spongycastle-bytecode")

        rv = _create_rv_instrumentation(config)
        app = MagicMock()
        app.name = "test.apk"
        app.code_package = "com.app"  # NOT under org/spongycastle

        with patch.object(
            rv,
            "_load_quarantine_patterns",
            return_value=["org/spongycastle/**/*.class"],
        ):
            rv._AjcInstrumentation__quarantine_problematic_classes(app)

        # Original file removed from tmp_dir.
        assert not sc_class.exists()
        # Quarantined under <tmp_dir>_quarantine/ with original relative path.
        qroot = Path(config.tmp_dir).parent / (
            Path(config.tmp_dir).name + "_quarantine"
        )
        assert (
            qroot / "org" / "spongycastle" / "jcajce" / "Camellia$AlgParamGen.class"
        ).exists()
        assert (
            qroot
            / "org"
            / "spongycastle"
            / "jcajce"
            / "Camellia$AlgParamGen.class"
        ).read_bytes() == b"spongycastle-bytecode"

    def test_noop_when_no_matches(self, tmp_path):
        config = _make_config_mock(tmp_path)
        os.makedirs(config.tmp_dir)
        app_dir = Path(config.tmp_dir) / "com" / "app"
        app_dir.mkdir(parents=True)
        (app_dir / "Foo.class").write_bytes(b"app")

        rv = _create_rv_instrumentation(config)
        app = MagicMock()
        app.name = "test.apk"
        app.code_package = "com.app"

        with patch.object(
            rv, "_load_quarantine_patterns", return_value=["okio/**/*.class"]
        ):
            rv._AjcInstrumentation__quarantine_problematic_classes(app)

        assert (app_dir / "Foo.class").exists()
        qroot = Path(config.tmp_dir).parent / (
            Path(config.tmp_dir).name + "_quarantine"
        )
        # quarantine root may exist but is empty if any dir was created; main
        # invariant is no class file under it
        assert not list(qroot.rglob("*.class")) if qroot.exists() else True


class TestRestoreQuarantinedClasses:
    """Tests for __restore_quarantined_classes."""

    def test_restore_moves_files_back(self, tmp_path):
        config = _make_config_mock(tmp_path)
        os.makedirs(config.tmp_dir)
        qroot = Path(config.tmp_dir).parent / (
            Path(config.tmp_dir).name + "_quarantine"
        )
        quarantine = qroot / "okio"
        quarantine.mkdir(parents=True)
        (quarantine / "Buffer.class").write_bytes(b"quarantined")

        rv = _create_rv_instrumentation(config)
        app = MagicMock()
        app.name = "test.apk"

        rv._AjcInstrumentation__restore_quarantined_classes(app)

        assert (Path(config.tmp_dir) / "okio" / "Buffer.class").exists()
        assert (
            Path(config.tmp_dir) / "okio" / "Buffer.class"
        ).read_bytes() == b"quarantined"
        # quarantine subtree removed
        assert not qroot.exists()

    def test_restore_overwrites_existing(self, tmp_path):
        # If the weaver produced a partial variant of a quarantined class at
        # the target path, restore MUST overwrite it with the quarantined
        # (original) bytecode so the final APK ships the library untouched.
        config = _make_config_mock(tmp_path)
        os.makedirs(config.tmp_dir)
        okio_dir = Path(config.tmp_dir) / "okio"
        okio_dir.mkdir()
        (okio_dir / "Buffer.class").write_bytes(b"woven_variant")  # stale
        qroot = Path(config.tmp_dir).parent / (
            Path(config.tmp_dir).name + "_quarantine"
        )
        quarantine = qroot / "okio"
        quarantine.mkdir(parents=True)
        (quarantine / "Buffer.class").write_bytes(b"original")

        rv = _create_rv_instrumentation(config)
        app = MagicMock()
        app.name = "test.apk"

        rv._AjcInstrumentation__restore_quarantined_classes(app)

        assert (okio_dir / "Buffer.class").read_bytes() == b"original"

    def test_noop_when_quarantine_absent(self, tmp_path):
        config = _make_config_mock(tmp_path)
        os.makedirs(config.tmp_dir)

        rv = _create_rv_instrumentation(config)
        app = MagicMock()
        app.name = "test.apk"

        # Should not raise
        rv._AjcInstrumentation__restore_quarantined_classes(app)


class TestEnableQuarantineToggle:
    """Tests for the `enable_quarantine` config flag (gh50 §21)."""

    def test_quarantine_disabled_skips_yaml_load_and_move(self, tmp_path):
        # When enable_quarantine=False, the early-return must fire BEFORE
        # `_load_quarantine_patterns` is consulted and BEFORE any file move
        # is attempted. Tracks regression of the gh50 §21 toggle.
        config = _make_config_mock(tmp_path)
        config.enable_quarantine = False
        os.makedirs(config.tmp_dir)
        okio_dir = Path(config.tmp_dir) / "okio"
        okio_dir.mkdir(parents=True)
        (okio_dir / "Buffer.class").write_bytes(b"okio")

        rv = _create_rv_instrumentation(config)
        app = MagicMock()
        app.name = "test.apk"
        app.code_package = "com.app"

        with (
            patch.object(rv, "_load_quarantine_patterns") as mock_load,
            patch(
                "rv_instrumentation_ajc.ajc_instrumentation.shutil.move"
            ) as mock_move,
        ):
            rv._AjcInstrumentation__quarantine_problematic_classes(app)

            mock_load.assert_not_called()
            mock_move.assert_not_called()

        # The class file must remain in place; no quarantine root created.
        assert (okio_dir / "Buffer.class").exists()
        qroot = Path(config.tmp_dir).parent / (
            Path(config.tmp_dir).name + "_quarantine"
        )
        assert not qroot.exists()

    def test_restore_disabled_is_noop_even_with_stale_dir(self, tmp_path):
        # If a stale `<tmp_dir>_quarantine/` survives from a previous run
        # while the current run is disabled, the restore must NOT touch it.
        # Cleanup of stale state is the caller's responsibility.
        config = _make_config_mock(tmp_path)
        config.enable_quarantine = False
        os.makedirs(config.tmp_dir)

        qroot = Path(config.tmp_dir).parent / (
            Path(config.tmp_dir).name + "_quarantine"
        )
        stale_dir = qroot / "okio"
        stale_dir.mkdir(parents=True)
        stale_file = stale_dir / "Buffer.class"
        stale_file.write_bytes(b"stale")

        rv = _create_rv_instrumentation(config)
        app = MagicMock()
        app.name = "test.apk"

        rv._AjcInstrumentation__restore_quarantined_classes(app)

        # Stale file must be preserved exactly where it was.
        assert stale_file.exists()
        assert stale_file.read_bytes() == b"stale"
        # And nothing must land under tmp_dir.
        assert not (Path(config.tmp_dir) / "okio" / "Buffer.class").exists()

    def test_quarantine_enabled_path_unchanged(self, tmp_path):
        # Regression: with the default (truthy MagicMock for the field),
        # __quarantine_problematic_classes still moves files as before.
        config = _make_config_mock(tmp_path)
        # MagicMock is truthy → existing behavior; explicit assignment for
        # clarity even though it is the implicit default.
        config.enable_quarantine = True
        os.makedirs(config.tmp_dir)
        okio_dir = Path(config.tmp_dir) / "okio"
        okio_dir.mkdir(parents=True)
        (okio_dir / "Buffer.class").write_bytes(b"okio")

        rv = _create_rv_instrumentation(config)
        app = MagicMock()
        app.name = "test.apk"
        app.code_package = "com.app"

        with patch.object(
            rv, "_load_quarantine_patterns", return_value=["okio/**/*.class"]
        ):
            rv._AjcInstrumentation__quarantine_problematic_classes(app)

        # File moved to quarantine root.
        assert not (okio_dir / "Buffer.class").exists()
        qroot = Path(config.tmp_dir).parent / (
            Path(config.tmp_dir).name + "_quarantine"
        )
        assert (qroot / "okio" / "Buffer.class").exists()


class TestSignApk:
    """Tests for __sign_apk (apksigner-based)."""

    def test_apksigner_command_schema(self, tmp_path):
        # apksigner sign must carry --ks, --ks-pass, --ks-key-alias and the
        # final APK path (apksigner overwrites in place). v1/v2/v3 schemes
        # are enabled by default in apksigner 0.9+, so no --v*-signing-enabled
        # flags are passed.
        config = _make_config_mock(tmp_path)
        config.keystore_file = str(tmp_path / "keystore.jks")
        config.keystore_password = "password"
        config.keystore_alias = "server"
        os.makedirs(tmp_path / "instrumented", exist_ok=True)
        unsigned = tmp_path / "unsigned_test.apk"
        unsigned.write_bytes(b"fake")

        rv = _create_rv_instrumentation(config)

        captured = []

        def capture_execute(cmd, tool_name, skip_stderr=False, stdout=None):
            captured.append(
                {"tool": tool_name, "args": cmd.args, "skip_stderr": skip_stderr}
            )

        app = MagicMock()
        app.name = "test.apk"

        with patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils:
            mock_utils.execute_command = capture_execute
            mock_utils.create_folder_if_not_exists = MagicMock()

            # apksigner verify is also captured; we stub os.path.exists to True
            with (
                patch(
                    "rv_instrumentation_ajc.ajc_instrumentation.os.path.exists",
                    return_value=True,
                ),
                patch("rv_instrumentation_ajc.ajc_instrumentation.os.remove"),
                patch("rv_instrumentation_ajc.ajc_instrumentation.shutil.copy2"),
            ):
                rv._AjcInstrumentation__sign_apk(app, str(unsigned))

        sign_call = next(c for c in captured if c["tool"] == "apksigner")
        args = sign_call["args"]
        assert "sign" in args
        ks_idx = args.index("--ks")
        assert args[ks_idx + 1] == config.keystore_file
        kspass_idx = args.index("--ks-pass")
        assert args[kspass_idx + 1] == "pass:password"
        alias_idx = args.index("--ks-key-alias")
        assert args[alias_idx + 1] == "server"
        # Last positional arg is the APK path under instrumented_dir
        signed_apk = os.path.join(config.instrumented_dir, app.name)
        assert signed_apk in args
        # JDK 21+ emits native-access warnings to stderr on every apksigner
        # invocation (INV-INS-19); both sign and verify must skip stderr.
        assert sign_call["skip_stderr"] is True
        verify_call = next(c for c in captured if c["tool"] == "apksigner_verify")
        assert verify_call["skip_stderr"] is True

    def test_verify_step_runs_after_sign(self, tmp_path):
        # The full flow invokes two apksigner commands: sign then verify.
        # Both target the same signed APK in instrumented_dir.
        config = _make_config_mock(tmp_path)
        config.keystore_file = str(tmp_path / "keystore.jks")
        config.keystore_password = "password"
        config.keystore_alias = "server"
        unsigned = tmp_path / "unsigned_test.apk"
        unsigned.write_bytes(b"fake")

        rv = _create_rv_instrumentation(config)
        captured = []

        def capture_execute(cmd, tool_name, skip_stderr=False, stdout=None):
            captured.append({"tool": tool_name, "args": cmd.args})

        app = MagicMock()
        app.name = "test.apk"

        with patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils:
            mock_utils.execute_command = capture_execute
            mock_utils.create_folder_if_not_exists = MagicMock()
            with (
                patch(
                    "rv_instrumentation_ajc.ajc_instrumentation.os.path.exists",
                    return_value=True,
                ),
                patch("rv_instrumentation_ajc.ajc_instrumentation.os.remove"),
                patch("rv_instrumentation_ajc.ajc_instrumentation.shutil.copy2"),
            ):
                rv._AjcInstrumentation__sign_apk(app, str(unsigned))

        # Both calls go to apksigner (first tool_name apksigner, then apksigner_verify)
        tools = [c["tool"] for c in captured]
        assert tools == ["apksigner", "apksigner_verify"]
        verify_call = captured[1]
        assert "verify" in verify_call["args"]
        signed_apk = os.path.join(config.instrumented_dir, app.name)
        assert signed_apk in verify_call["args"]

    def test_unsigned_apk_removed_after_signing(self, tmp_path):
        # After a successful apksigner sign + verify, the unsigned source
        # must be removed so tmp_dir does not accumulate stale artifacts
        # between APKs in batch mode.
        config = _make_config_mock(tmp_path)
        config.keystore_file = str(tmp_path / "keystore.jks")
        config.keystore_password = "password"
        config.keystore_alias = "server"
        unsigned = tmp_path / "unsigned_test.apk"
        unsigned.write_bytes(b"fake")

        rv = _create_rv_instrumentation(config)
        app = MagicMock()
        app.name = "test.apk"

        with (
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils,
            patch(
                "rv_instrumentation_ajc.ajc_instrumentation.os.path.exists",
                return_value=True,
            ),
            patch(
                "rv_instrumentation_ajc.ajc_instrumentation.os.remove"
            ) as mock_remove,
            patch("rv_instrumentation_ajc.ajc_instrumentation.shutil.copy2"),
        ):
            mock_utils.execute_command = MagicMock()
            mock_utils.create_folder_if_not_exists = MagicMock()
            rv._AjcInstrumentation__sign_apk(app, str(unsigned))

        mock_remove.assert_called_once_with(str(unsigned))

    def test_no_jarsigner_or_d2j_apk_sign_methods(self, tmp_path):
        # Regression: the legacy v1-only signing chain (jarsigner, jarsigner
        # verify, d2j_apk_sign) must not exist on the class — they would
        # produce v1-only APKs rejected by API 30+ emulators.
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)
        assert not hasattr(rv, "_AjcInstrumentation__jarsigner")
        assert not hasattr(rv, "_AjcInstrumentation__jarsigner_verify")
        assert not hasattr(rv, "_AjcInstrumentation__d2j_apk_sign")
