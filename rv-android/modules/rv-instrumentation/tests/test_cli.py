"""
Unit tests for rv-instrumentation CLI argument parsing.

These tests verify the CLI argument parser configuration and argument mapping
without executing actual instrumentation commands.
"""

import pytest
from rv_instrumentation.__main__ import create_parser


class TestCliParser:
    """Tests for CLI argument parser."""

    def test_instrument_command_requires_apk(self):
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["instrument", "--output", "/out"])

    def test_instrument_command_requires_output(self):
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["instrument", "--apk", "/app.apk"])

    def test_instrument_command_parses_apk_and_output(self):
        parser = create_parser()
        args = parser.parse_args(["instrument", "--apk", "/app.apk", "--output", "/out"])

        assert args.command == "instrument"
        assert args.apk == "/app.apk"
        assert args.output == "/out"

    def test_batch_command_requires_apks_dir(self):
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["batch", "--output", "/out"])

    def test_batch_command_parses_apks_dir_and_output(self):
        parser = create_parser()
        args = parser.parse_args(["batch", "--apks-dir", "/apks", "--output", "/out"])

        assert args.command == "batch"
        assert args.apks_dir == "/apks"
        assert args.output == "/out"

    def test_force_flag_defaults_to_false(self):
        parser = create_parser()
        args = parser.parse_args(["instrument", "--apk", "/app.apk", "--output", "/out"])

        assert args.force is False

    def test_force_flag_set_to_true(self):
        parser = create_parser()
        args = parser.parse_args(["instrument", "--apk", "/app.apk", "--output", "/out", "--force"])

        assert args.force is True

    def test_verbose_flag_defaults_to_false(self):
        parser = create_parser()
        args = parser.parse_args(["instrument", "--apk", "/app.apk", "--output", "/out"])

        assert args.verbose is False

    def test_verbose_short_flag(self):
        parser = create_parser()
        args = parser.parse_args(["instrument", "--apk", "/app.apk", "--output", "/out", "-v"])

        assert args.verbose is True

    def test_dry_run_flag(self):
        parser = create_parser()
        args = parser.parse_args(["instrument", "--apk", "/app.apk", "--output", "/out", "--dry-run"])

        assert args.dry_run is True

    def test_no_command_sets_none(self):
        parser = create_parser()
        args = parser.parse_args([])

        assert args.command is None

    def test_rvsec_root_option(self):
        parser = create_parser()
        args = parser.parse_args([
            "instrument", "--apk", "/app.apk", "--output", "/out",
            "--rvsec-root", "/rvsec"
        ])

        assert args.rvsec_root == "/rvsec"

    def test_monitor_dir_option(self):
        parser = create_parser()
        args = parser.parse_args([
            "instrument", "--apk", "/app.apk", "--output", "/out",
            "--monitor-dir", "/monitors"
        ])

        assert args.monitor_dir == "/monitors"

    def test_keystore_options(self):
        parser = create_parser()
        args = parser.parse_args([
            "instrument", "--apk", "/app.apk", "--output", "/out",
            "--keystore", "/ks.jks", "--keystore-password", "secret"
        ])

        assert args.keystore == "/ks.jks"
        assert args.keystore_password == "secret"
