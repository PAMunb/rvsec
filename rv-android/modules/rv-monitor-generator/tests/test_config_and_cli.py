"""
Tests for RVGeneratorConfig validation, path resolution, and CLI argument parsing.
"""

import os
import shutil
import subprocess
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from rv_monitor_generator.__main__ import create_parser, handle_generate_command, main
from rv_monitor_generator.config import ConfigurationError, RVGeneratorConfig


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_rvsec_root():
    """Create a minimal mock RVSEC directory structure with tool binaries and specs."""
    temp_dir = tempfile.mkdtemp()

    dirs_and_files = {
        "javamop/bin": ["javamop"],
        "rv-monitor/bin": ["rv-monitor"],
        "rvsec/rvsec-mop/src/main/resources/jca": ["Cipher.mop", "Hash.mop"],
        "rvsec/rvsec-mop/src/main/resources/aspect": ["logging.aj"],
    }

    for dir_path, files in dirs_and_files.items():
        full_dir = os.path.join(temp_dir, dir_path)
        os.makedirs(full_dir, exist_ok=True)
        for fname in files:
            fpath = os.path.join(full_dir, fname)
            with open(fpath, "w") as f:
                if fname.endswith(".mop"):
                    f.write(f"// MOP spec: {fname}")
                elif fname.endswith(".aj"):
                    f.write(f"// AspectJ: {fname}")
                else:
                    f.write('#!/bin/bash\necho "ok"')
            if dir_path.endswith("/bin"):
                os.chmod(fpath, 0o755)

    yield temp_dir
    shutil.rmtree(temp_dir)


def _make_config(temp_rvsec_root, **overrides):
    """Helper to build a valid RVGeneratorConfig with subprocess mocked."""
    kwargs = {"rvsec_root": temp_rvsec_root}
    kwargs.update(overrides)
    with patch("rv_monitor_generator.config.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="help output", stderr="")
        return RVGeneratorConfig(**kwargs)


# ===========================================================================
# RVGeneratorConfig tests
# ===========================================================================


class TestRVGeneratorConfigDefaults:
    """Test default values and automatic path resolution."""

    def test_default_javamop_bin_from_rvsec_root(self, temp_rvsec_root):
        config = _make_config(temp_rvsec_root)
        assert config.javamop_bin == os.path.join(
            temp_rvsec_root, "javamop", "bin", "javamop"
        )

    def test_default_rvmonitor_bin_from_rvsec_root(self, temp_rvsec_root):
        config = _make_config(temp_rvsec_root)
        assert config.rvmonitor_bin == os.path.join(
            temp_rvsec_root, "rv-monitor", "bin", "rv-monitor"
        )

    def test_default_mop_specs_dir_is_jca(self, temp_rvsec_root):
        config = _make_config(temp_rvsec_root)
        assert config.mop_specs_dir.endswith("jca")

    def test_default_aspects_dir_from_rvsec_root(self, temp_rvsec_root):
        config = _make_config(temp_rvsec_root)
        assert config.aspects_dir.endswith("aspect")


class TestRVGeneratorConfigExplicitPaths:
    """Test configuration with all individual paths provided."""

    def test_explicit_paths_skip_rvsec_root_resolution(self, temp_rvsec_root):
        javamop = os.path.join(temp_rvsec_root, "javamop", "bin", "javamop")
        rvmonitor = os.path.join(temp_rvsec_root, "rv-monitor", "bin", "rv-monitor")
        specs = os.path.join(
            temp_rvsec_root, "rvsec/rvsec-mop/src/main/resources/jca"
        )
        aspects = os.path.join(
            temp_rvsec_root, "rvsec/rvsec-mop/src/main/resources/aspect"
        )

        with patch("rv_monitor_generator.config.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="help", stderr="")
            config = RVGeneratorConfig(
                javamop_bin=javamop,
                rvmonitor_bin=rvmonitor,
                mop_specs_dir=specs,
                aspects_dir=aspects,
            )

        assert config.javamop_bin == javamop
        assert config.rvmonitor_bin == rvmonitor

    def test_aspects_dir_defaults_relative_to_specs_when_explicit_tools(
        self, temp_rvsec_root
    ):
        """When tool paths and mop_specs_dir are explicit but aspects_dir is not,
        aspects_dir defaults to a sibling 'aspect' directory."""
        javamop = os.path.join(temp_rvsec_root, "javamop", "bin", "javamop")
        rvmonitor = os.path.join(temp_rvsec_root, "rv-monitor", "bin", "rv-monitor")
        specs = os.path.join(
            temp_rvsec_root, "rvsec/rvsec-mop/src/main/resources/jca"
        )
        expected_aspects = os.path.join(
            temp_rvsec_root, "rvsec/rvsec-mop/src/main/resources/aspect"
        )

        with patch("rv_monitor_generator.config.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="help", stderr="")
            config = RVGeneratorConfig(
                javamop_bin=javamop,
                rvmonitor_bin=rvmonitor,
                mop_specs_dir=specs,
            )

        assert config.aspects_dir == expected_aspects


class TestRVGeneratorConfigEnvVariable:
    """Test resolution via RVSEC_HOME environment variable."""

    def test_resolves_from_env_when_no_rvsec_root(self, temp_rvsec_root):
        with patch.dict(os.environ, {"RVSEC_HOME": temp_rvsec_root}), patch(
            "rv_monitor_generator.config.subprocess.run"
        ) as mock_run:
            mock_run.return_value = MagicMock(stdout="help", stderr="")
            config = RVGeneratorConfig()

        assert config.javamop_bin.startswith(temp_rvsec_root)

    def test_raises_when_no_source_available(self):
        with patch.dict(os.environ, {}, clear=True), patch(
            "rv_monitor_generator.config.os.getenv", return_value=None
        ):
            with pytest.raises(ConfigurationError, match="Configuration resolution failed"):
                RVGeneratorConfig()


class TestRVGeneratorConfigValidation:
    """Test validation checks in _validate_configuration."""

    def test_missing_javamop_binary_raises(self, temp_rvsec_root):
        # Remove the javamop binary
        javamop_path = os.path.join(temp_rvsec_root, "javamop", "bin", "javamop")
        os.remove(javamop_path)

        with pytest.raises(ConfigurationError, match="JavaMOP binary not found"):
            _make_config(temp_rvsec_root)

    def test_non_executable_binary_raises(self, temp_rvsec_root):
        javamop_path = os.path.join(temp_rvsec_root, "javamop", "bin", "javamop")
        os.chmod(javamop_path, 0o644)  # Remove execute permission

        with pytest.raises(ConfigurationError, match="not executable"):
            _make_config(temp_rvsec_root)

    def test_missing_specs_directory_raises(self, temp_rvsec_root):
        specs_dir = os.path.join(
            temp_rvsec_root, "rvsec/rvsec-mop/src/main/resources/jca"
        )
        shutil.rmtree(specs_dir)
        os.makedirs(specs_dir)  # Recreate empty dir (no .mop files)

        with pytest.raises(ConfigurationError, match="No MOP specification files"):
            _make_config(temp_rvsec_root)

    def test_tool_functionality_timeout_raises(self, temp_rvsec_root):
        with patch("rv_monitor_generator.config.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="javamop", timeout=10)
            with pytest.raises(ConfigurationError, match="functionality test failed"):
                RVGeneratorConfig(rvsec_root=temp_rvsec_root)

    def test_tool_produces_no_output_raises(self, temp_rvsec_root):
        with patch("rv_monitor_generator.config.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", stderr="")
            with pytest.raises(ConfigurationError, match="produced no output"):
                RVGeneratorConfig(rvsec_root=temp_rvsec_root)


class TestRVGeneratorConfigSummary:
    """Test get_configuration_summary output."""

    def test_summary_contains_required_keys(self, temp_rvsec_root):
        config = _make_config(temp_rvsec_root)
        summary = config.get_configuration_summary()

        assert "tools" in summary
        assert "directories" in summary
        assert "specifications" in summary
        assert "validation_status" in summary

    def test_summary_specs_count_matches_filesystem(self, temp_rvsec_root):
        config = _make_config(temp_rvsec_root)
        summary = config.get_configuration_summary()

        assert summary["specifications"]["count"] == 2  # Cipher.mop + Hash.mop

    def test_summary_specs_lists_filenames(self, temp_rvsec_root):
        config = _make_config(temp_rvsec_root)
        summary = config.get_configuration_summary()

        filenames = summary["specifications"]["files"]
        assert "Cipher.mop" in filenames
        assert "Hash.mop" in filenames


class TestRVGeneratorConfigStr:
    """Test __str__ representation."""

    def test_str_contains_tool_paths(self, temp_rvsec_root):
        config = _make_config(temp_rvsec_root)
        text = str(config)

        assert "JavaMOP" in text
        assert "RV-Monitor" in text
        assert "Specifications" in text
        assert "Aspects" in text


class TestRVGeneratorConfigValidateOutputDir:
    """Test validate_output_directory method."""

    def test_creates_output_directory(self, temp_rvsec_root):
        config = _make_config(temp_rvsec_root)
        output_dir = os.path.join(tempfile.mkdtemp(), "nested", "output")

        try:
            config.validate_output_directory(output_dir)
            assert os.path.isdir(output_dir)
        finally:
            shutil.rmtree(os.path.dirname(os.path.dirname(output_dir)))

    def test_raises_on_unwritable_path(self, temp_rvsec_root):
        config = _make_config(temp_rvsec_root)

        with pytest.raises(ConfigurationError, match="Cannot write to output directory"):
            config.validate_output_directory("/proc/nonexistent/dir")


# ===========================================================================
# CLI tests
# ===========================================================================


class TestCLIParser:
    """Test CLI argument parsing via create_parser."""

    def test_generate_command_requires_output(self):
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["generate"])

    def test_generate_command_parses_output(self):
        parser = create_parser()
        args = parser.parse_args(["generate", "--output", "/tmp/out"])
        assert args.output == "/tmp/out"
        assert args.command == "generate"

    def test_generate_command_parses_all_options(self):
        parser = create_parser()
        args = parser.parse_args(
            [
                "generate",
                "--rvsec-root", "/root",
                "--javamop-bin", "/bin/javamop",
                "--rvmonitor-bin", "/bin/rv-monitor",
                "--specs-dir", "/specs",
                "--aspects-dir", "/aspects",
                "--output", "/out",
                "--verbose",
                "--summary",
            ]
        )
        assert args.rvsec_root == "/root"
        assert args.javamop_bin == "/bin/javamop"
        assert args.rvmonitor_bin == "/bin/rv-monitor"
        assert args.specs_dir == "/specs"
        assert args.aspects_dir == "/aspects"
        assert args.output == "/out"
        assert args.verbose is True
        assert args.summary is True

    def test_no_command_returns_exit_code_1(self):
        """main() without a subcommand prints help and returns 1."""
        with patch("sys.argv", ["rv-monitor-generator"]):
            result = main()
        assert result == 1


class TestCLIHandleGenerate:
    """Test handle_generate_command function."""

    def test_configuration_error_returns_1(self):
        """A ConfigurationError during config creation returns exit code 1."""
        args = MagicMock()
        args.rvsec_root = None
        args.javamop_bin = None
        args.rvmonitor_bin = None
        args.specs_dir = None
        args.aspects_dir = None
        args.output = "/tmp/out"
        args.verbose = False
        args.summary = False

        with patch.dict(os.environ, {}, clear=True), patch(
            "rv_monitor_generator.config.os.getenv", return_value=None
        ):
            result = handle_generate_command(args)

        assert result == 1
