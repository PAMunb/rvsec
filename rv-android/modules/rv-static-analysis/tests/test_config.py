"""
Unit tests for RVStaticAnalysisConfig.

Tests verify configuration initialization, path resolution, command generation,
and validation for the unified GATOR-based analysis pipeline.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rv_static_analysis.config import ConfigurationError, RVStaticAnalysisConfig


class TestRVStaticAnalysisConfig(unittest.TestCase):
    """Tests for RVStaticAnalysisConfig functionality."""

    def test_config_initialization_with_defaults(self):
        """Test that configuration initializes with default values."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("rv_static_analysis.config.os.getcwd") as mock_getcwd:
                mock_getcwd.return_value = "/mock/working/dir"

                # Validation fails without real paths
                with self.assertRaises(ConfigurationError):
                    RVStaticAnalysisConfig()

    def test_config_with_explicit_paths(self):
        """Test configuration with all explicit paths provided."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create required directories and files
            lib_dir = temp_path / "lib"
            lib_dir.mkdir()

            # Create GATOR directory with launcher and client JAR
            gator_dir = lib_dir / "gator"
            gator_dir.mkdir()
            gator_python = gator_dir / "gator"
            gator_python.touch()
            gator_python.chmod(0o755)
            analysis_client_jar = gator_dir / "rvsec-analysis-client.jar"
            analysis_client_jar.touch()

            # Create Android SDK structure
            android_platforms = temp_path / "android" / "platforms"
            android_platforms.mkdir(parents=True)

            android_jar = android_platforms / "android-29" / "android.jar"
            android_jar.parent.mkdir()
            android_jar.touch()

            # Create MOP directory
            mop_dir = temp_path / "specs" / "jca"
            mop_dir.mkdir(parents=True)
            (mop_dir / "test.mop").touch()

            output_dir = temp_path / "output"
            working_dir = temp_path / "working"

            config = RVStaticAnalysisConfig(
                lib_dir=str(lib_dir),
                android_platforms_dir=str(android_platforms),
                android_jar=str(android_jar),
                mop_dir=str(mop_dir),
                output_dir=str(output_dir),
                working_dir=str(working_dir),
                gator_dir=str(gator_dir),
                analysis_client_jar=str(analysis_client_jar),
            )

            # Verify configuration values
            self.assertEqual(config.lib_dir, str(lib_dir.resolve()))
            self.assertEqual(config.gator_dir, str(gator_dir.resolve()))
            self.assertEqual(
                config.analysis_client_jar, str(analysis_client_jar.resolve())
            )
            self.assertEqual(config.android_jar, str(android_jar.resolve()))

    def test_tool_command_generation(self):
        """Test unified analysis command generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            lib_dir = temp_path / "lib"
            lib_dir.mkdir()

            config = RVStaticAnalysisConfig(
                lib_dir=str(lib_dir),
                gator_dir=str(lib_dir / "gator"),
                analysis_client_jar=str(
                    lib_dir / "gator" / "rvsec-analysis-client.jar"
                ),
                android_platforms_dir=str(temp_path / "platforms"),
                android_jar=str(temp_path / "android.jar"),
                mop_dir=str(temp_path / "mop"),
                validate_on_init=False,
            )

            cmd = config.get_tool_command(
                "analysis", "/test/app.apk", "/test/output.json"
            )
            self.assertEqual(cmd[0], "python")
            self.assertIn("-p", cmd)
            self.assertIn("/test/app.apk", cmd)
            self.assertIn("--client-jar", cmd)
            self.assertIn("-client", cmd)
            self.assertIn("RvsecAnalysisClient", cmd)
            # gh51: Soot 4.7.1 replaced -withCHA with explicit `-cgAlgorithm cha`
            self.assertIn("-cgAlgorithm", cmd)
            self.assertIn("cha", cmd)

    def test_unsupported_tool_command_error(self):
        """Test error handling for unsupported tool names."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = RVStaticAnalysisConfig(
                validate_on_init=False,
                rvsec_root=temp_dir,
            )

            with self.assertRaises(ConfigurationError) as context:
                config.get_tool_command("invalid_tool", "/test/app.apk", "/test/output")

            self.assertIn("Unsupported tool", str(context.exception))

    def test_configuration_summary(self):
        """Test configuration summary generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            config = RVStaticAnalysisConfig(
                rvsec_root=str(temp_path),
                lib_dir=str(temp_path / "lib"),
                android_platforms_dir=str(temp_path / "platforms"),
                android_jar=str(temp_path / "android.jar"),
                mop_dir=str(temp_path / "mop"),
                output_dir=str(temp_path / "output"),
                working_dir=str(temp_path / "working"),
                gator_dir=str(temp_path / "lib" / "gator"),
                analysis_client_jar=str(
                    temp_path / "lib" / "gator" / "rvsec-analysis-client.jar"
                ),
                validate_on_init=False,
            )

            summary = config.get_configuration_summary()

            self.assertIn("rvsec_integration", summary)
            self.assertIn("android_integration", summary)
            self.assertIn("analysis_tool", summary)
            self.assertIn("gator_dir", summary["analysis_tool"])
            self.assertIn("analysis_client_jar", summary["analysis_tool"])

    def test_apk_input_validation(self):
        """Test APK input validation functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            apk_file = temp_path / "test.apk"
            apk_file.touch()

            config = RVStaticAnalysisConfig(
                validate_on_init=False,
                rvsec_root=str(temp_path),
            )

            # Valid APK should not raise exception
            try:
                config.validate_apk_input(str(apk_file))
            except ConfigurationError:
                self.fail("validate_apk_input raised ConfigurationError for valid APK")

            # Non-existent file should raise exception
            with self.assertRaises(ConfigurationError):
                config.validate_apk_input(str(temp_path / "nonexistent.apk"))

            # Non-APK file should raise exception
            non_apk = temp_path / "test.txt"
            non_apk.touch()
            with self.assertRaises(ConfigurationError):
                config.validate_apk_input(str(non_apk))

    def test_jvm_memory_and_timeout_defaults(self):
        """Test default JVM memory and timeout values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = RVStaticAnalysisConfig(
                validate_on_init=False,
                rvsec_root=temp_dir,
            )

            self.assertEqual(config.jvm_memory, "12g")
            self.assertEqual(config.analysis_timeout, 600)

    def test_tool_command_with_custom_timeout(self):
        """Test command generation with custom timeout."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = RVStaticAnalysisConfig(
                validate_on_init=False,
                rvsec_root=temp_dir,
                gator_dir=str(Path(temp_dir) / "gator"),
                analysis_client_jar=str(Path(temp_dir) / "gator" / "client.jar"),
                mop_dir=str(Path(temp_dir) / "mop"),
            )

            cmd = config.get_tool_command(
                "analysis", "/test/app.apk", "/test/output.json", timeout=1200
            )
            self.assertIn("1200", cmd)

    def test_tool_command_with_code_package(self):
        """Test that code_package kwarg adds codePackage clientParam to GATOR command."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = RVStaticAnalysisConfig(
                validate_on_init=False,
                rvsec_root=temp_dir,
                gator_dir=str(Path(temp_dir) / "gator"),
                analysis_client_jar=str(Path(temp_dir) / "gator" / "client.jar"),
                mop_dir=str(Path(temp_dir) / "mop"),
            )

            cmd = config.get_tool_command(
                "analysis",
                "/test/app.apk",
                "/test/output.json",
                code_package="com.gh4a",
            )

            # Must have TWO -clientParam flags: mopDir and codePackage
            client_param_indices = [i for i, v in enumerate(cmd) if v == "-clientParam"]
            self.assertEqual(len(client_param_indices), 2)

            # First -clientParam is mopDir
            self.assertTrue(cmd[client_param_indices[0] + 1].startswith("mopDir="))

            # Second -clientParam is codePackage
            self.assertEqual(cmd[client_param_indices[1] + 1], "codePackage=com.gh4a")

    def test_tool_command_without_code_package(self):
        """Test that omitting code_package does not add codePackage clientParam."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = RVStaticAnalysisConfig(
                validate_on_init=False,
                rvsec_root=temp_dir,
                gator_dir=str(Path(temp_dir) / "gator"),
                analysis_client_jar=str(Path(temp_dir) / "gator" / "client.jar"),
                mop_dir=str(Path(temp_dir) / "mop"),
            )

            cmd = config.get_tool_command(
                "analysis",
                "/test/app.apk",
                "/test/output.json",
            )

            # Only ONE -clientParam (mopDir)
            client_param_indices = [i for i, v in enumerate(cmd) if v == "-clientParam"]
            self.assertEqual(len(client_param_indices), 1)

            # No codePackage anywhere in the command
            self.assertFalse(any("codePackage" in v for v in cmd))

    def test_tool_command_includes_jvm_memory(self):
        """Test that get_tool_command passes --jvm-memory from config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = RVStaticAnalysisConfig(
                validate_on_init=False,
                rvsec_root=temp_dir,
                gator_dir=str(Path(temp_dir) / "gator"),
                analysis_client_jar=str(Path(temp_dir) / "gator" / "client.jar"),
                mop_dir=str(Path(temp_dir) / "mop"),
                jvm_memory="20g",
            )

            cmd = config.get_tool_command(
                "analysis",
                "/test/app.apk",
                "/test/output.json",
            )

            idx = cmd.index("--jvm-memory")
            self.assertEqual(cmd[idx + 1], "20G")
