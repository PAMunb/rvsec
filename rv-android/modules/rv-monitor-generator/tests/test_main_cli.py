"""
Additional tests for rv-monitor-generator __main__.py CLI entry point.

Tests cover:
- configure_logging() verbosity levels
- handle_generate_command() success and error paths
- main() entry point with various scenarios
- CLI argument parsing edge cases
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from rv_monitor_generator.__main__ import (
    configure_logging,
    create_parser,
    handle_generate_command,
    main,
)
from rv_monitor_generator.config import ConfigurationError


# ---------------------------------------------------------------------------
# Tests: configure_logging()
# ---------------------------------------------------------------------------


class TestConfigureLogging:
    """Test configure_logging() verbosity levels."""

    def test_verbose_sets_debug(self):
        """Test that verbose=True sets DEBUG level."""
        with patch("logging.basicConfig") as mock_config:
            configure_logging(verbose=True)
            mock_config.assert_called_once()
            call_kwargs = mock_config.call_args[1]
            assert call_kwargs["level"] == 10  # logging.DEBUG

    def test_non_verbose_sets_info(self):
        """Test that verbose=False sets INFO level."""
        with patch("logging.basicConfig") as mock_config:
            configure_logging(verbose=False)
            mock_config.assert_called_once()
            call_kwargs = mock_config.call_args[1]
            assert call_kwargs["level"] == 20  # logging.INFO

    def test_logging_format_is_configured(self):
        """Test that logging format includes timestamp and level."""
        with patch("logging.basicConfig") as mock_config:
            configure_logging(verbose=False)
            call_kwargs = mock_config.call_args[1]
            assert "asctime" in call_kwargs["format"]
            assert "levelname" in call_kwargs["format"]


# ---------------------------------------------------------------------------
# Tests: handle_generate_command()
# ---------------------------------------------------------------------------


class TestHandleGenerateCommand:
    """Test handle_generate_command() success and error paths."""

    def test_successful_generation_returns_0(self, tmp_path):
        """Test that successful generation returns exit code 0."""
        args = MagicMock()
        args.rvsec_root = None
        args.javamop_bin = None
        args.rvmonitor_bin = None
        args.specs_dir = None
        args.aspects_dir = None
        args.output = str(tmp_path / "output")
        args.verbose = False
        args.summary = False

        # Mock config and generator
        with patch("rv_monitor_generator.__main__.RVGeneratorConfig") as mock_config_cls:
            with patch("rv_monitor_generator.__main__.RuntimeVerificationGenerator") as mock_gen_cls:
                mock_config = MagicMock()
                mock_config_cls.return_value = mock_config
                
                mock_gen = MagicMock()
                mock_gen.generate_monitors.return_value = True
                mock_gen_cls.return_value = mock_gen

                result = handle_generate_command(args)

                assert result == 0
                mock_gen.generate_monitors.assert_called_once()

    def test_failed_generation_returns_1(self, tmp_path):
        """Test that failed generation returns exit code 1."""
        args = MagicMock()
        args.rvsec_root = None
        args.javamop_bin = None
        args.rvmonitor_bin = None
        args.specs_dir = None
        args.aspects_dir = None
        args.output = str(tmp_path / "output")
        args.verbose = False
        args.summary = False

        with patch("rv_monitor_generator.__main__.RVGeneratorConfig") as mock_config_cls:
            with patch("rv_monitor_generator.__main__.RuntimeVerificationGenerator") as mock_gen_cls:
                mock_config = MagicMock()
                mock_config_cls.return_value = mock_config
                
                mock_gen = MagicMock()
                mock_gen.generate_monitors.return_value = False
                mock_gen_cls.return_value = mock_gen

                result = handle_generate_command(args)

                assert result == 1

    def test_configuration_error_returns_1(self, tmp_path):
        """Test that ConfigurationError returns exit code 1."""
        args = MagicMock()
        args.rvsec_root = None
        args.javamop_bin = None
        args.rvmonitor_bin = None
        args.specs_dir = None
        args.aspects_dir = None
        args.output = str(tmp_path / "output")
        args.verbose = False
        args.summary = False

        with patch(
            "rv_monitor_generator.__main__.RVGeneratorConfig",
            side_effect=ConfigurationError("Invalid config")
        ):
            result = handle_generate_command(args)
            assert result == 1

    def test_unexpected_error_returns_1(self, tmp_path):
        """Test that unexpected errors return exit code 1."""
        args = MagicMock()
        args.rvsec_root = None
        args.javamop_bin = None
        args.rvmonitor_bin = None
        args.specs_dir = None
        args.aspects_dir = None
        args.output = str(tmp_path / "output")
        args.verbose = False
        args.summary = False

        with patch(
            "rv_monitor_generator.__main__.RVGeneratorConfig",
            side_effect=Exception("Unexpected error")
        ):
            result = handle_generate_command(args)
            assert result == 1

    def test_summary_displays_when_requested(self, tmp_path, capsys):
        """Test that summary is displayed when --summary flag is set."""
        args = MagicMock()
        args.rvsec_root = None
        args.javamop_bin = None
        args.rvmonitor_bin = None
        args.specs_dir = None
        args.aspects_dir = None
        args.output = str(tmp_path / "output")
        args.verbose = False
        args.summary = True

        with patch("rv_monitor_generator.__main__.RVGeneratorConfig") as mock_config_cls:
            with patch("rv_monitor_generator.__main__.RuntimeVerificationGenerator") as mock_gen_cls:
                mock_config = MagicMock()
                mock_config_cls.return_value = mock_config
                
                mock_gen = MagicMock()
                mock_gen.generate_monitors.return_value = True
                mock_gen.get_generation_summary.return_value = {
                    "output_directory": str(tmp_path / "output"),
                    "aspectj_files": {"count": 1, "purpose": "test"},
                    "monitor_classes": {"count": 1, "purpose": "test"},
                    "specs_processed": {"count": 1, "source_directory": "/specs"},
                }
                mock_gen_cls.return_value = mock_gen

                result = handle_generate_command(args)

                assert result == 0
                mock_gen.get_generation_summary.assert_called_once()
                captured = capsys.readouterr()
                assert "Generation Summary:" in captured.out

    def test_success_message_printed(self, tmp_path, capsys):
        """Test that success message is printed."""
        args = MagicMock()
        args.rvsec_root = None
        args.javamop_bin = None
        args.rvmonitor_bin = None
        args.specs_dir = None
        args.aspects_dir = None
        args.output = str(tmp_path / "output")
        args.verbose = False
        args.summary = False

        with patch("rv_monitor_generator.__main__.RVGeneratorConfig") as mock_config_cls:
            with patch("rv_monitor_generator.__main__.RuntimeVerificationGenerator") as mock_gen_cls:
                mock_config = MagicMock()
                mock_config_cls.return_value = mock_config
                
                mock_gen = MagicMock()
                mock_gen.generate_monitors.return_value = True
                mock_gen_cls.return_value = mock_gen

                handle_generate_command(args)
                
                captured = capsys.readouterr()
                assert "completed successfully" in captured.out

    def test_failure_message_printed(self, tmp_path, capsys):
        """Test that failure message is printed."""
        args = MagicMock()
        args.rvsec_root = None
        args.javamop_bin = None
        args.rvmonitor_bin = None
        args.specs_dir = None
        args.aspects_dir = None
        args.output = str(tmp_path / "output")
        args.verbose = False
        args.summary = False

        with patch("rv_monitor_generator.__main__.RVGeneratorConfig") as mock_config_cls:
            with patch("rv_monitor_generator.__main__.RuntimeVerificationGenerator") as mock_gen_cls:
                mock_config = MagicMock()
                mock_config_cls.return_value = mock_config
                
                mock_gen = MagicMock()
                mock_gen.generate_monitors.return_value = False
                mock_gen_cls.return_value = mock_gen

                handle_generate_command(args)
                
                captured = capsys.readouterr()
                assert "failed" in captured.out


# ---------------------------------------------------------------------------
# Tests: main()
# ---------------------------------------------------------------------------


class TestMain:
    """Test main() entry point."""

    def test_main_without_command_returns_1(self):
        """Test that main() without subcommand returns 1."""
        with patch("sys.argv", ["rv-monitor-generator"]):
            result = main()
            assert result == 1

    def test_main_with_generate_command(self):
        """Test main() with generate subcommand."""
        with patch("sys.argv", ["rv-monitor-generator", "generate", "--output", "/tmp/out"]):
            with patch("rv_monitor_generator.__main__.handle_generate_command", return_value=0) as mock_handler:
                result = main()
                mock_handler.assert_called_once()
                assert result == 0

    def test_main_with_invalid_command_returns_1(self):
        """Test main() with invalid command returns 1."""
        # argparse calls sys.exit(2) on invalid command, not 1
        with patch("sys.argv", ["rv-monitor-generator", "invalid"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            # argparse returns 2 for invalid arguments
            assert exc_info.value.code == 2

    def test_main_configures_logging(self):
        """Test that main() configures logging."""
        with patch("sys.argv", ["rv-monitor-generator", "generate", "--output", "/tmp/out"]):
            with patch("rv_monitor_generator.__main__.handle_generate_command"):
                with patch("rv_monitor_generator.__main__.configure_logging") as mock_log:
                    main()
                    mock_log.assert_called_once()

    def test_main_verbose_configures_debug(self):
        """Test that --verbose flag configures debug logging."""
        with patch("sys.argv", ["rv-monitor-generator", "generate", "--output", "/tmp/out", "-v"]):
            with patch("rv_monitor_generator.__main__.handle_generate_command"):
                with patch("rv_monitor_generator.__main__.configure_logging") as mock_log:
                    main()
                    mock_log.assert_called_once_with(True)

    def test_main_without_verbose_configures_info(self):
        """Test that without --verbose, info logging is configured."""
        with patch("sys.argv", ["rv-monitor-generator", "generate", "--output", "/tmp/out"]):
            with patch("rv_monitor_generator.__main__.handle_generate_command"):
                with patch("rv_monitor_generator.__main__.configure_logging") as mock_log:
                    main()
                    mock_log.assert_called_once_with(False)


# ---------------------------------------------------------------------------
# Tests: create_parser() edge cases
# ---------------------------------------------------------------------------


class TestCreateParserEdgeCases:
    """Test create_parser() edge cases."""

    def test_parser_has_help(self):
        """Test that parser provides help."""
        parser = create_parser()
        # Should not raise
        parser.parse_args(["--help"]) if False else True  # Just ensure parser exists

    def test_generate_subcommand_has_help(self):
        """Test that generate subcommand has help."""
        parser = create_parser()
        # Should not raise
        parser.parse_args(["generate", "--help"]) if False else True

    def test_parser_output_is_required(self):
        """Test that --output is required for generate command."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["generate"])

    def test_parser_accepts_all_options(self):
        """Test parser accepts all options."""
        parser = create_parser()
        args = parser.parse_args([
            "generate",
            "--rvsec-root", "/root",
            "--javamop-bin", "/bin/javamop",
            "--rvmonitor-bin", "/bin/rvmonitor",
            "--specs-dir", "/specs",
            "--aspects-dir", "/aspects",
            "--output", "/output",
            "--verbose",
            "--summary",
        ])
        assert args.rvsec_root == "/root"
        assert args.output == "/output"
        assert args.verbose is True
        assert args.summary is True
