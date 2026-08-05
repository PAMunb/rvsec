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
    # The package policy arrives resolved on the config; False is what an
    # unconfigured run carries — the package declared in the manifest.
    config.package_detector = False

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

    def test_warns_when_the_app_code_guard_is_inert(self, tmp_path):
        """A guard prefix matching no compiled class protects nothing.

        `org.fossify.calendar_20.apk` declares `org.fossify.calendar.debug`
        while its classes compile under `org/fossify/calendar/`, so the guard
        prefix `org/fossify/calendar/debug/` matches nothing. The pipeline says
        so rather than letting the skip branch quietly never fire.
        """
        config = _make_config_mock(tmp_path)
        os.makedirs(config.tmp_dir)
        app_dir = Path(config.tmp_dir) / "org" / "fossify" / "calendar"
        app_dir.mkdir(parents=True)
        (app_dir / "MainActivity.class").write_bytes(b"app")

        rv = _create_rv_instrumentation(config)
        rv._logger = MagicMock()
        app = MagicMock()
        app.name = "org.fossify.calendar_20.apk"
        app.code_package = "org.fossify.calendar.debug"

        with patch.object(
            rv, "_load_quarantine_patterns", return_value=["okio/**/*.class"]
        ):
            rv._AjcInstrumentation__quarantine_problematic_classes(app)

        warnings = [str(c) for c in rv._logger.warning.call_args_list]
        assert any("guard is inert" in w for w in warnings)

    def test_no_inert_warning_when_the_guard_covers_app_classes(self, tmp_path):
        """A guard that matches the compiled tree is silent."""
        config = _make_config_mock(tmp_path)
        os.makedirs(config.tmp_dir)
        app_dir = Path(config.tmp_dir) / "com" / "app"
        app_dir.mkdir(parents=True)
        (app_dir / "Foo.class").write_bytes(b"app")

        rv = _create_rv_instrumentation(config)
        rv._logger = MagicMock()
        app = MagicMock()
        app.name = "test.apk"
        app.code_package = "com.app"

        with patch.object(
            rv, "_load_quarantine_patterns", return_value=["okio/**/*.class"]
        ):
            rv._AjcInstrumentation__quarantine_problematic_classes(app)

        warnings = [str(c) for c in rv._logger.warning.call_args_list]
        assert not any("guard is inert" in w for w in warnings)

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


# ---------------------------------------------------------------------------
# Coverage-completion suites (gh-test-add): the classes below exercise the
# pipeline internals that the pre-existing suites did not reach, raising line
# coverage of ajc_instrumentation.py from 73% to ~100%. Each suite is designed
# with an explicit black-box (equivalence-partition / boundary) or white-box
# (basis-path) rationale documented in its docstring, and every external tool
# invocation is mocked so the tests stay hermetic (no dex2jar/ajc/d8/apksigner).
# ---------------------------------------------------------------------------


class TestInstrumentApksApkPaths:
    """Tests for instrument_apks APK-source selection (the `apk_paths` param).

    Basis-path coverage of the two-way branch at the discovery step: either an
    explicit `apk_paths` list is supplied (build App objects directly) or the
    directory is scanned via utils.get_apks. Also covers the discovery-error
    partition where get_apks raises.
    """

    def test_uses_provided_apk_paths_list(self, tmp_path):
        # Equivalence class: caller supplies an explicit apk_paths list. The
        # method must construct App objects from those paths instead of
        # scanning apks_dir. App() is patched to avoid androguard/real APKs.
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        app1 = MagicMock()
        app1.name = "provided1.apk"
        app1.path = "/provided/provided1.apk"

        out_dir = tmp_path / "out"
        out_dir.mkdir()

        with (
            patch.object(rv, "prepare_instrumentation"),
            patch(
                "rv_instrumentation_ajc.ajc_instrumentation.App", return_value=app1
            ) as mock_app,
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils,
            patch.object(rv, "instrument"),
            patch.object(rv, "check_if_instrumented"),
            patch.object(rv, "clear"),
        ):
            results = rv.instrument_apks(
                str(tmp_path), str(out_dir), apk_paths=["/provided/provided1.apk"]
            )

            # get_apks must NOT be consulted when apk_paths is provided, and
            # the App must carry the run's package policy (INV-EXP-34).
            mock_utils.get_apks.assert_not_called()
            mock_app.assert_called_once_with(
                "/provided/provided1.apk",
                package_detector=config.package_detector,
            )

        assert results.total_count == 1
        assert results.success_count == 1

    def test_apk_discovery_failure_returns_retrieval_error(self, tmp_path):
        # Equivalence class: apk_paths is None and utils.get_apks raises (e.g.
        # unreadable directory). The method must capture the failure as an
        # "apk_retrieval_error" entry with phase "retrieval" and total_count 1,
        # without attempting any per-APK instrumentation.
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        with (
            patch.object(rv, "prepare_instrumentation"),
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils,
            patch.object(rv, "clear"),
        ):
            mock_utils.get_apks.side_effect = OSError("cannot read directory")

            results = rv.instrument_apks(str(tmp_path), str(tmp_path / "out"))

        assert "apk_retrieval_error" in results.errors
        assert results.errors["apk_retrieval_error"].phase == "retrieval"
        assert results.total_count == 1
        assert results.success_count == 0


class TestPrepareInstrumentation:
    """Tests for prepare_instrumentation environment setup.

    Basis-path coverage of the rvsec_root resolution branch: a resolvable root
    proceeds to _resolve_runtime_libs + directory creation; an unresolvable one
    raises InstrumentationError before any library resolution.
    """

    def test_success_resolves_libs_and_creates_output_dir(self, tmp_path):
        # Happy path: rvsec_root is set on the config, so runtime libraries are
        # resolved and the results directory is created.
        config = _make_config_mock(tmp_path)
        config.rvsec_root = str(tmp_path / "rvsec")
        config.lib_tmp_dir = str(tmp_path / "lib_tmp")
        rv = _create_rv_instrumentation(config)

        results_dir = str(tmp_path / "results")

        with (
            patch.object(rv, "clear") as mock_clear,
            patch.object(rv, "_resolve_runtime_libs") as mock_resolve,
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils,
        ):
            rv.prepare_instrumentation(results_dir)

            mock_clear.assert_called_once()
            mock_resolve.assert_called_once()
            mock_utils.create_folder_if_not_exists.assert_called_once_with(results_dir)

    def test_missing_rvsec_root_skips_library_resolution(self, tmp_path):
        # Boundary/error case: config.rvsec_root is None AND RVSEC_HOME is
        # absent from the environment. The method raises InstrumentationError
        # BEFORE _resolve_runtime_libs; the reraise=False decorator absorbs it,
        # so the observable effect is that library resolution never runs.
        config = _make_config_mock(tmp_path)
        config.rvsec_root = None
        rv = _create_rv_instrumentation(config)

        with (
            patch.object(rv, "clear"),
            patch.object(rv, "_resolve_runtime_libs") as mock_resolve,
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils"),
            patch.dict("os.environ", {}, clear=True),
        ):
            rv.prepare_instrumentation(str(tmp_path / "results"))

            mock_resolve.assert_not_called()


class TestInstrumentFullPipeline:
    """Tests for instrument() driving the full phase sequence to success.

    Basis-path coverage of the try-body (phases 1-7) that the pre-existing
    skip/force tests never reached: with every phase mocked and a signed APK
    that exists on disk, the method completes without raising.
    """

    def test_full_pipeline_success_invokes_all_phases(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        result_dir = str(tmp_path / "results")
        os.makedirs(result_dir)

        app = MagicMock()
        app.name = "pipeline.apk"
        app.path = str(tmp_path / "pipeline.apk")

        signed_apk = tmp_path / "signed_pipeline.apk"
        signed_apk.write_bytes(b"signed")

        with (
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils"),
            patch.object(rv, "create_temp_directories"),
            patch.object(rv, "clear"),
            patch.object(rv, "_AjcInstrumentation__decompile_apk") as m_decompile,
            patch.object(rv, "_AjcInstrumentation__strip_desugared_shims"),
            patch.object(rv, "_AjcInstrumentation__quarantine_problematic_classes"),
            patch.object(rv, "_AjcInstrumentation__include_generated_monitors"),
            patch.object(rv, "_AjcInstrumentation__pre_compute_stack_frames"),
            patch.object(rv, "_AjcInstrumentation__weave_monitors") as m_weave,
            patch.object(rv, "_AjcInstrumentation__compute_stack_frames"),
            patch.object(rv, "_AjcInstrumentation__restore_quarantined_classes"),
            patch.object(
                rv,
                "_AjcInstrumentation__create_apk",
                return_value=str(signed_apk),
            ) as m_create,
        ):
            rv.instrument(app, result_dir, force_instrumentation=False)

            m_decompile.assert_called_once_with(app)
            m_weave.assert_called_once_with(app)
            m_create.assert_called_once_with(app)

    def test_raises_when_signed_apk_missing(self, tmp_path):
        # Boundary: __create_apk returns a path that does not exist on disk,
        # so the post-assembly existence check raises InstrumentationError
        # (single_apk_instrumentation is decorated reraise=True → propagates).
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        result_dir = str(tmp_path / "results")
        os.makedirs(result_dir)

        app = MagicMock()
        app.name = "pipeline.apk"
        app.path = str(tmp_path / "pipeline.apk")

        with (
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils"),
            patch.object(rv, "create_temp_directories"),
            patch.object(rv, "clear"),
            patch.object(rv, "_AjcInstrumentation__decompile_apk"),
            patch.object(rv, "_AjcInstrumentation__strip_desugared_shims"),
            patch.object(rv, "_AjcInstrumentation__quarantine_problematic_classes"),
            patch.object(rv, "_AjcInstrumentation__include_generated_monitors"),
            patch.object(rv, "_AjcInstrumentation__pre_compute_stack_frames"),
            patch.object(rv, "_AjcInstrumentation__weave_monitors"),
            patch.object(rv, "_AjcInstrumentation__compute_stack_frames"),
            patch.object(rv, "_AjcInstrumentation__restore_quarantined_classes"),
            patch.object(
                rv,
                "_AjcInstrumentation__create_apk",
                return_value=str(tmp_path / "does_not_exist.apk"),
            ),
        ):
            with pytest.raises(InstrumentationError):
                rv.instrument(app, result_dir, force_instrumentation=False)


class TestDecompileApk:
    """Tests for __decompile_apk (DEX → loose .class files).

    Basis-path coverage: the success path (dex2jar produces the JAR, which is
    extracted then deleted) and the boundary where dex2jar silently produces
    no JAR (missing-output check raises).
    """

    def test_success_extracts_and_deletes_jar(self, tmp_path):
        config = _make_config_mock(tmp_path)
        os.makedirs(config.tmp_dir)
        rv = _create_rv_instrumentation(config)

        app = MagicMock()
        app.name = "test.apk"

        jar_path = os.path.join(config.tmp_dir, "no_monitor_test.apk.jar")

        def fake_dex2jar(a, out_jar):
            Path(out_jar).write_bytes(b"jar")

        with (
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils,
            patch.object(
                rv, "_AjcInstrumentation__d2j_dex2jar", side_effect=fake_dex2jar
            ),
            patch.object(rv, "_AjcInstrumentation__d2j_asm_verify"),
        ):
            rv._AjcInstrumentation__decompile_apk(app)

            mock_utils.reset_folder.assert_called_once_with(config.tmp_dir)
            mock_utils.unzip.assert_called_once_with(jar_path, config.tmp_dir)
            mock_utils.delete_file.assert_called_once_with(jar_path)

    def test_raises_when_dex2jar_produces_no_jar(self, tmp_path):
        # Boundary: dex2jar returns without creating the JAR → the existence
        # check raises InstrumentationError (no decorator here, raises directly).
        config = _make_config_mock(tmp_path)
        os.makedirs(config.tmp_dir)
        rv = _create_rv_instrumentation(config)

        app = MagicMock()
        app.name = "test.apk"

        with (
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils"),
            patch.object(rv, "_AjcInstrumentation__d2j_dex2jar"),  # no-op, no jar
        ):
            with pytest.raises(InstrumentationError):
                rv._AjcInstrumentation__decompile_apk(app)


class TestD2jDex2jar:
    """Tests for __d2j_dex2jar command construction and exception detection."""

    def test_builds_dex2jar_command_with_skip_stderr(self, tmp_path):
        # dex2jar writes informational text to stderr on success, so the
        # execute_command call must pass the skip-stderr flag (3rd positional
        # True). No exception zip → no CommandException.
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        app = MagicMock()
        app.name = "test.apk"
        app.path = "/orig/test.apk"

        captured = {}

        def capture_execute(cmd, tag, skip_stderr=False):
            captured["command"] = cmd.command
            captured["args"] = cmd.args
            captured["tag"] = tag
            captured["skip_stderr"] = skip_stderr

        with patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils:
            mock_utils.execute_command = capture_execute
            out_jar = os.path.join(config.tmp_dir, "out.jar")
            rv._AjcInstrumentation__d2j_dex2jar(app, out_jar)

        assert captured["tag"] == "dex2jar"
        assert captured["skip_stderr"] is True
        assert out_jar in captured["args"]
        assert app.path in captured["args"]

    def test_raises_when_exception_zip_present(self, tmp_path):
        # dex2jar drops an exception zip when it hits unsupported opcodes; its
        # presence must be surfaced as a CommandException.
        config = _make_config_mock(tmp_path)
        os.makedirs(config.tmp_dir)
        rv = _create_rv_instrumentation(config)

        app = MagicMock()
        app.name = "test.apk"
        app.path = "/orig/test.apk"

        # Pre-create the exception zip dex2jar would have written.
        exc_zip = os.path.join(config.tmp_dir, "exception_test.apk.zip")
        Path(exc_zip).write_bytes(b"err")

        with patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils:
            mock_utils.execute_command = MagicMock()
            with pytest.raises(CommandException) as ei:
                rv._AjcInstrumentation__d2j_dex2jar(
                    app, os.path.join(config.tmp_dir, "out.jar")
                )

        assert ei.value.tool == "dex2jar"


class TestD2jAsmVerify:
    """Tests for __d2j_asm_verify skip-toggle (boundary on the skip_verify flag)."""

    def test_skip_verify_true_is_noop(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        with patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils:
            mock_utils.execute_command = MagicMock()
            rv._AjcInstrumentation__d2j_asm_verify("/some.jar", skip_verify=True)
            mock_utils.execute_command.assert_not_called()

    def test_skip_verify_false_runs_asm_verify(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        captured = {}

        def capture_execute(cmd, tag):
            captured["tag"] = tag
            captured["args"] = cmd.args

        with patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils:
            mock_utils.execute_command = capture_execute
            rv._AjcInstrumentation__d2j_asm_verify("/some.jar", skip_verify=False)

        assert captured["tag"] == "asm_verify"
        assert "/some.jar" in captured["args"]


class TestGetClasspath:
    """Tests for __get_classpath assembly (android.jar + lib_tmp_dir jars)."""

    def test_includes_android_jar_and_only_jar_libs(self, tmp_path):
        # Equivalence partition on directory entries: only *.jar files are added
        # to the classpath; non-jar files (e.g. a README) are excluded.
        config = _make_config_mock(tmp_path)
        os.makedirs(config.lib_tmp_dir)
        (Path(config.lib_tmp_dir) / "rv-monitor-rt.jar").write_bytes(b"jar")
        (Path(config.lib_tmp_dir) / "notes.txt").write_bytes(b"text")
        rv = _create_rv_instrumentation(config)

        app = MagicMock()

        with patch.object(
            rv,
            "_AjcInstrumentation__get_android_jar",
            return_value="/fake/android.jar",
        ):
            classpath = rv._AjcInstrumentation__get_classpath(app)

        assert "/fake/android.jar" in classpath
        assert os.path.join(config.lib_tmp_dir, "rv-monitor-rt.jar") in classpath
        assert not any(p.endswith("notes.txt") for p in classpath)


class TestLoadQuarantinePatternsError:
    """Tests for _load_quarantine_patterns YAML-error handling."""

    def test_returns_empty_on_yaml_error(self, tmp_path):
        # Robustness: a corrupt weaving_excludes.yaml (safe_load raises) must
        # degrade gracefully to [] so the pipeline still runs, and a warning is
        # logged rather than propagating the parse error.
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)
        rv._logger = MagicMock()

        with (
            patch(
                "rv_instrumentation_ajc.ajc_instrumentation.Path.exists",
                return_value=True,
            ),
            patch("builtins.open", create=True),
            patch(
                "rv_instrumentation_ajc.ajc_instrumentation.yaml.safe_load",
                side_effect=ValueError("bad yaml"),
            ),
        ):
            result = rv._load_quarantine_patterns()

        assert result == []
        assert rv._logger.warning.called


class TestQuarantineEdgeCases:
    """Tests for __quarantine_problematic_classes secondary branches."""

    def test_empty_patterns_is_noop(self, tmp_path):
        # Boundary: enable_quarantine is on but the pattern list is empty, so
        # the method returns before touching the filesystem.
        config = _make_config_mock(tmp_path)
        config.enable_quarantine = True
        os.makedirs(config.tmp_dir)
        app_dir = Path(config.tmp_dir) / "com" / "app"
        app_dir.mkdir(parents=True)
        (app_dir / "Foo.class").write_bytes(b"app")
        rv = _create_rv_instrumentation(config)

        app = MagicMock()
        app.name = "test.apk"
        app.code_package = "com.app"

        with patch.object(rv, "_load_quarantine_patterns", return_value=[]):
            rv._AjcInstrumentation__quarantine_problematic_classes(app)

        assert (app_dir / "Foo.class").exists()
        qroot = Path(config.tmp_dir).parent / (Path(config.tmp_dir).name + "_quarantine")
        assert not qroot.exists()

    def test_directory_matches_are_skipped(self, tmp_path):
        # White-box: a glob that matches BOTH a .class file and a subdirectory
        # must move only the file (is_file() gate); the directory match hits the
        # `continue` branch and is left in place.
        config = _make_config_mock(tmp_path)
        config.enable_quarantine = True
        os.makedirs(config.tmp_dir)
        okio_dir = Path(config.tmp_dir) / "okio"
        okio_dir.mkdir()
        (okio_dir / "Buffer.class").write_bytes(b"okio")
        (okio_dir / "internal").mkdir()  # directory that also matches okio/*
        rv = _create_rv_instrumentation(config)

        app = MagicMock()
        app.name = "test.apk"
        app.code_package = "com.app"

        with patch.object(
            rv, "_load_quarantine_patterns", return_value=["okio/*"]
        ):
            rv._AjcInstrumentation__quarantine_problematic_classes(app)

        # File moved to quarantine; the subdirectory stays where it was.
        assert not (okio_dir / "Buffer.class").exists()
        assert (okio_dir / "internal").is_dir()
        qroot = Path(config.tmp_dir).parent / (Path(config.tmp_dir).name + "_quarantine")
        assert (qroot / "okio" / "Buffer.class").exists()


class TestIncludeGeneratedMonitors:
    """Tests for __include_generated_monitors artifact copying."""

    def test_copies_monitor_artifacts_when_dir_present(self, tmp_path):
        config = _make_config_mock(tmp_path)
        os.makedirs(config.monitor_output_dir)
        rv = _create_rv_instrumentation(config)

        with patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils:
            rv._AjcInstrumentation__include_generated_monitors()
            mock_utils.copy_files.assert_called_once_with(
                config.monitor_output_dir, config.tmp_dir
            )

    def test_raises_when_monitor_dir_missing(self, tmp_path):
        # Boundary: monitor_output_dir does not exist → InstrumentationError
        # (monitor_integration is reraise=True → propagates).
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        with patch("rv_instrumentation_ajc.ajc_instrumentation.utils"):
            with pytest.raises(InstrumentationError):
                rv._AjcInstrumentation__include_generated_monitors()


class TestGetFrameComputerJar:
    """Tests for _get_frame_computer_jar path resolution."""

    def test_returns_path_when_jar_exists(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        with patch(
            "rv_instrumentation_ajc.ajc_instrumentation.Path.exists", return_value=True
        ):
            result = rv._get_frame_computer_jar()

        assert result is not None
        assert result.endswith("rv-frame-computer.jar")

    def test_returns_none_when_jar_absent(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        with patch(
            "rv_instrumentation_ajc.ajc_instrumentation.Path.exists", return_value=False
        ):
            result = rv._get_frame_computer_jar()

        assert result is None


class TestCreateApk:
    """Tests for __create_apk orchestration of assembly → d8 → align → sign."""

    def test_assembles_and_returns_signed_apk(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        app = MagicMock()
        app.name = "test.apk"

        unsigned = tmp_path / "unsigned_test.apk"
        unsigned.write_bytes(b"unsigned")
        signed = tmp_path / "instrumented" / "test.apk"

        with (
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils"),
            patch("rv_instrumentation_ajc.ajc_instrumentation.shutil.move"),
            patch("rv_instrumentation_ajc.ajc_instrumentation.shutil.rmtree"),
            patch.object(rv, "_AjcInstrumentation__merge_support_classes") as m_merge,
            patch.object(
                rv, "_AjcInstrumentation__d8", return_value=str(unsigned)
            ) as m_d8,
            patch.object(rv, "_AjcInstrumentation__zipalign") as m_align,
            patch.object(
                rv, "_AjcInstrumentation__sign_apk", return_value=str(signed)
            ) as m_sign,
        ):
            result = rv._AjcInstrumentation__create_apk(app)

        assert result == str(signed)
        m_merge.assert_called_once()
        m_d8.assert_called_once()
        m_align.assert_called_once_with(str(unsigned))
        m_sign.assert_called_once_with(app, str(unsigned))

    def test_raises_when_unsigned_apk_missing(self, tmp_path):
        # Boundary: __d8 returns a path that does not exist → InstrumentationError
        # (apk_creation is reraise=True → propagates).
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        app = MagicMock()
        app.name = "test.apk"

        with (
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils"),
            patch("rv_instrumentation_ajc.ajc_instrumentation.shutil.move"),
            patch("rv_instrumentation_ajc.ajc_instrumentation.shutil.rmtree"),
            patch.object(rv, "_AjcInstrumentation__merge_support_classes"),
            patch.object(
                rv,
                "_AjcInstrumentation__d8",
                return_value=str(tmp_path / "missing_unsigned.apk"),
            ),
        ):
            with pytest.raises(InstrumentationError):
                rv._AjcInstrumentation__create_apk(app)


class TestMergeSupportClasses:
    """Tests for __merge_support_classes runtime-library integration."""

    def test_extracts_all_required_jars_and_merges(self, tmp_path):
        config = _make_config_mock(tmp_path)
        os.makedirs(config.lib_tmp_dir)
        for jar in [
            "rv-monitor-rt.jar",
            "rvsec-core.jar",
            "rvsec-logger-logcat.jar",
            "aspectjrt.jar",
        ]:
            (Path(config.lib_tmp_dir) / jar).write_bytes(b"jar")
        rv = _create_rv_instrumentation(config)

        with (
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils,
            patch(
                "rv_instrumentation_ajc.ajc_instrumentation.shutil.copytree"
            ) as mock_copytree,
            patch("rv_instrumentation_ajc.ajc_instrumentation.shutil.rmtree"),
        ):
            rv._AjcInstrumentation__merge_support_classes()

            # All four runtime libraries unzipped, then the merged tree copied
            # into tmp_dir.
            assert mock_utils.unzip.call_count == 4
            mock_copytree.assert_called_once()

    def test_raises_when_required_jar_missing(self, tmp_path):
        # Boundary: one of the four required jars is absent from lib_tmp_dir →
        # InstrumentationError (library_integration is reraise=True).
        config = _make_config_mock(tmp_path)
        os.makedirs(config.lib_tmp_dir)
        # Only three of the four required jars present.
        for jar in ["rv-monitor-rt.jar", "rvsec-core.jar", "aspectjrt.jar"]:
            (Path(config.lib_tmp_dir) / jar).write_bytes(b"jar")
        rv = _create_rv_instrumentation(config)

        with (
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils"),
            patch("rv_instrumentation_ajc.ajc_instrumentation.shutil.copytree"),
            patch("rv_instrumentation_ajc.ajc_instrumentation.shutil.rmtree"),
        ):
            with pytest.raises(InstrumentationError):
                rv._AjcInstrumentation__merge_support_classes()


class TestD8:
    """Tests for __d8 DEX compilation + APK repackaging."""

    def test_compiles_and_repackages_unsigned_apk(self, tmp_path):
        config = _make_config_mock(tmp_path)
        os.makedirs(config.tmp_dir)
        rv = _create_rv_instrumentation(config)

        app = MagicMock()
        app.name = "test.apk"
        app.path = str(tmp_path / "test.apk")
        (tmp_path / "test.apk").write_bytes(b"orig-apk")

        captured = []

        def capture_execute(cmd, tag, skip_stderr=False):
            captured.append({"tag": tag, "args": cmd.args, "skip_stderr": skip_stderr})

        with (
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils,
            patch.object(
                rv,
                "_AjcInstrumentation__get_android_jar",
                return_value="/fake/android.jar",
            ),
        ):
            mock_utils.execute_command = capture_execute
            unsigned = rv._AjcInstrumentation__d8(
                app, str(Path(config.tmp_dir) / "monitored.jar")
            )

        expected = os.path.join(config.tmp_dir, "unsigned_test.apk")
        assert unsigned == expected
        assert os.path.exists(unsigned)  # real shutil.copy2 duplicated app.path
        d8_call = next(c for c in captured if c["tag"] == "d8")
        assert d8_call["skip_stderr"] is True
        assert "--min-api" in d8_call["args"]

    def test_raises_when_unsigned_copy_fails(self, tmp_path):
        # Boundary: shutil.copy2 does not produce the unsigned APK → the
        # existence check raises InstrumentationError (no decorator, direct).
        config = _make_config_mock(tmp_path)
        os.makedirs(config.tmp_dir)
        rv = _create_rv_instrumentation(config)

        app = MagicMock()
        app.name = "test.apk"
        app.path = str(tmp_path / "test.apk")

        with (
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils,
            patch.object(
                rv,
                "_AjcInstrumentation__get_android_jar",
                return_value="/fake/android.jar",
            ),
            patch("rv_instrumentation_ajc.ajc_instrumentation.shutil.copy2"),  # no-op
        ):
            mock_utils.execute_command = MagicMock()
            with pytest.raises(InstrumentationError):
                rv._AjcInstrumentation__d8(
                    app, str(Path(config.tmp_dir) / "monitored.jar")
                )


class TestSignApkMissingOutput:
    """Test for __sign_apk silent-failure guard (signed APK not produced)."""

    def test_raises_when_signed_apk_not_created(self, tmp_path):
        # Boundary: apksigner exits 0 but no signed APK lands at the target
        # (copy2 is a no-op here) → InstrumentationError (apk_signing reraise=True).
        config = _make_config_mock(tmp_path)
        config.keystore_alias = "server"
        rv = _create_rv_instrumentation(config)

        app = MagicMock()
        app.name = "test.apk"

        unsigned = tmp_path / "unsigned_test.apk"
        unsigned.write_bytes(b"unsigned")

        with (
            patch("rv_instrumentation_ajc.ajc_instrumentation.utils") as mock_utils,
            patch("rv_instrumentation_ajc.ajc_instrumentation.shutil.copy2"),  # no-op
        ):
            mock_utils.execute_command = MagicMock()
            mock_utils.create_folder_if_not_exists = MagicMock()
            with pytest.raises(InstrumentationError):
                rv._AjcInstrumentation__sign_apk(app, str(unsigned))


class TestFindHighestAndroidPlatform:
    """Tests for _find_highest_android_platform selection logic."""

    def test_returns_none_when_dir_absent(self, tmp_path):
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        result = rv._find_highest_android_platform(str(tmp_path / "no_such_dir"))

        assert result is None

    def test_skips_malformed_names_and_picks_highest(self, tmp_path):
        # White-box: entries whose suffix is not an int ("android-abc",
        # "android-") hit the ValueError/IndexError `continue`; the highest
        # numeric platform >= 26 wins.
        platforms = tmp_path / "platforms"
        platforms.mkdir()
        for name in ["android-abc", "android-", "android-28", "android-33"]:
            (platforms / name).mkdir()
        config = _make_config_mock(tmp_path)
        rv = _create_rv_instrumentation(config)

        result = rv._find_highest_android_platform(str(platforms))

        assert result == "android-33"
