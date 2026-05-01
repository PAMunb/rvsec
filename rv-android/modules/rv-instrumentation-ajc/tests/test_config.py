"""
Unit tests for AjcInstrumentationConfig Pydantic models.

These tests verify configuration initialization, path resolution, and Pydantic model validation
without requiring external dependencies or full instrumentation setup.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from rv_android_core.util.error.exceptions import ConfigurationError
from rv_instrumentation_ajc.config import ConfigurationSummary, Dex2jarTools
from rv_instrumentation_ajc.config import (
    InstrumentationError as InstrumentationErrorModel,
)
from rv_instrumentation_ajc.config import (
    InstrumentationResults,
    AjcInstrumentationConfig,
)


class TestAjcInstrumentationConfig(unittest.TestCase):
    """Tests for AjcInstrumentationConfig Pydantic model functionality."""

    def test_config_initialization_with_defaults(self):
        """Test that configuration initializes with default values and validates properly."""
        # Mock environment variables to avoid dependency on actual environment
        with patch.dict(os.environ, {}, clear=True):
            with patch("rv_instrumentation_ajc.config.os.getcwd") as mock_getcwd:
                mock_getcwd.return_value = "/mock/working/dir"

                # This will fail validation but we just want to test initialization
                with self.assertRaises(ConfigurationError):
                    AjcInstrumentationConfig()

    def test_config_with_explicit_paths(self):
        """Test configuration with all explicit paths provided using Pydantic validation."""
        # Create temporary directories for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create required directories and files
            monitor_dir = temp_path / "monitors"
            monitor_dir.mkdir()

            # Create dummy monitor files
            (monitor_dir / "test.aj").touch()
            (monitor_dir / "test.java").touch()

            android_platforms = temp_path / "android" / "platforms"
            android_platforms.mkdir(parents=True)

            android_jar = android_platforms / "android-29" / "android.jar"
            android_jar.parent.mkdir()
            android_jar.touch()

            keystore_file = temp_path / "test.jks"
            keystore_file.touch()

            dex2jar_home = temp_path / "dex2jar"
            dex2jar_home.mkdir()

            # Create dex2jar tools
            for tool in ["d2j-dex2jar.sh", "d2j-asm-verify.sh", "d2j-apk-sign.sh"]:
                tool_path = dex2jar_home / tool
                tool_path.touch()
                tool_path.chmod(0o755)

            instrumented_dir = temp_path / "instrumented"
            working_dir = temp_path / "working"

            # Mock LoggingManager and ErrorHandler to avoid dependency issues
            with patch("rv_instrumentation_ajc.config.LoggingManager") as mock_logging:
                mock_logging.get_instance.return_value.get_logger.return_value = (
                    MagicMock()
                )

                # Test configuration with explicit paths (both positional and named work)
                config = AjcInstrumentationConfig(
                    monitor_output_dir=str(monitor_dir),
                    android_jar_path=str(android_jar),
                    android_platforms_dir=str(android_platforms),
                    keystore_file=str(keystore_file),
                    keystore_password="testpassword",
                    working_dir=str(working_dir),
                    instrumented_dir=str(instrumented_dir),
                    dex2jar_home=str(dex2jar_home),
                )

                # Verify configuration values using Pydantic attributes
                self.assertEqual(config.monitor_output_dir, str(monitor_dir))
                self.assertEqual(config.android_jar_path, str(android_jar))
                self.assertEqual(config.keystore_file, str(keystore_file))
                self.assertEqual(config.keystore_password, "testpassword")
                self.assertEqual(config.dex2jar_home, str(dex2jar_home))

                # Test that model is a proper Pydantic instance
                self.assertTrue(hasattr(config, "model_dump"))
                self.assertTrue(hasattr(AjcInstrumentationConfig, "model_fields"))

    def test_positional_constructor_compatibility(self):
        """Test that @validated_model decorator enables positional arguments."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create minimal required structure
            monitor_dir = temp_path / "monitors"
            monitor_dir.mkdir()
            (monitor_dir / "test.aj").touch()
            (monitor_dir / "test.java").touch()

            android_platforms = temp_path / "android" / "platforms"
            android_platforms.mkdir(parents=True)
            android_jar = android_platforms / "android-29" / "android.jar"
            android_jar.parent.mkdir()
            android_jar.touch()

            keystore_file = temp_path / "test.jks"
            keystore_file.touch()

            dex2jar_home = temp_path / "dex2jar"
            dex2jar_home.mkdir()
            for tool in ["d2j-dex2jar.sh", "d2j-asm-verify.sh", "d2j-apk-sign.sh"]:
                tool_path = dex2jar_home / tool
                tool_path.touch()
                tool_path.chmod(0o755)

            with patch("rv_instrumentation_ajc.config.LoggingManager") as mock_logging:
                mock_logging.get_instance.return_value.get_logger.return_value = (
                    MagicMock()
                )

                # Test positional constructor (legacy compatibility)
                config = AjcInstrumentationConfig(
                    None,  # rvsec_root
                    str(monitor_dir),  # monitor_output_dir
                    str(android_jar),  # android_jar_path
                    str(android_platforms),  # android_platforms_dir
                    str(keystore_file),  # keystore_file
                    "password",  # keystore_password
                    str(temp_path),  # working_dir
                    str(temp_path / "out"),  # instrumented_dir
                    str(temp_path / "tmp"),  # tmp_dir
                    str(temp_path / "lib_tmp"),  # lib_tmp_dir
                    str(temp_path / "rvm_tmp"),  # rvm_tmp_dir
                    str(dex2jar_home),  # dex2jar_home
                )

                # Verify positional arguments were mapped correctly
                self.assertEqual(config.monitor_output_dir, str(monitor_dir))
                self.assertEqual(config.android_jar_path, str(android_jar))
                self.assertEqual(config.keystore_file, str(keystore_file))
                self.assertEqual(config.dex2jar_home, str(dex2jar_home))

    def test_dex2jar_tools_pydantic_model(self):
        """Test Dex2jarTools Pydantic model validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dex2jar_home = Path(temp_dir) / "dex2jar"
            dex2jar_home.mkdir()

            # Create tool files (apk_sign removed; signing now uses apksigner)
            for filename in ("d2j-dex2jar.sh", "d2j-asm-verify.sh"):
                tool_path = dex2jar_home / filename
                tool_path.touch()
                tool_path.chmod(0o755)

            # Test Dex2jarTools model directly
            tools = Dex2jarTools(
                dex2jar=str(dex2jar_home / "d2j-dex2jar.sh"),
                asm_verify=str(dex2jar_home / "d2j-asm-verify.sh"),
            )

            # Verify Pydantic model behavior
            self.assertIsInstance(tools.model_dump(), dict)
            self.assertEqual(tools.dex2jar, str(dex2jar_home / "d2j-dex2jar.sh"))
            self.assertEqual(tools.asm_verify, str(dex2jar_home / "d2j-asm-verify.sh"))

    def test_dex2jar_tools_validation_failure(self):
        """Test that Dex2jarTools model validates tool existence."""
        # Test with non-existent tool paths
        with self.assertRaises(ValueError) as context:
            Dex2jarTools(
                dex2jar="/nonexistent/path",
                asm_verify="/another/nonexistent/path",
            )

        self.assertIn("dex2jar tool not found", str(context.exception))

    def test_configuration_summary_pydantic_model(self):
        """Test ConfigurationSummary Pydantic model structure."""
        summary = ConfigurationSummary(
            android_integration={"android_jar_path": "/path/to/android.jar"},
            instrumentation_paths={"working_dir": "/path/to/work"},
            temporary_directories={"tmp_dir": "/path/to/tmp"},
            tools={"dex2jar_home": "/path/to/dex2jar"},
            signing={"keystore_file": "/path/to/keystore"},
            monitor_artifacts={"aspectj_count": 2, "java_count": 3},
            validation_status="Validated",
        )

        # Verify Pydantic model behavior
        self.assertIsInstance(summary.model_dump(), dict)
        self.assertEqual(summary.validation_status, "Validated")
        self.assertEqual(summary.monitor_artifacts["aspectj_count"], 2)

    def test_instrumentation_error_model(self):
        """Test InstrumentationError Pydantic model."""
        error = InstrumentationErrorModel(
            code=-1,
            tool="dex2jar",
            message="Tool execution failed",
            phase="decompilation",
        )

        # Verify Pydantic model behavior
        self.assertEqual(error.code, -1)
        self.assertEqual(error.tool, "dex2jar")
        self.assertEqual(error.message, "Tool execution failed")
        self.assertEqual(error.phase, "decompilation")
        self.assertIsInstance(error.model_dump(), dict)

    def test_instrumentation_results_model(self):
        """Test InstrumentationResults Pydantic model with computed field."""
        results = InstrumentationResults(total_count=10, success_count=8)

        # Test computed field
        self.assertEqual(results.success_rate, 80.0)

        # Test with errors
        error = InstrumentationErrorModel(
            code=-1, message="Failed to process", phase="test", tool=None
        )
        results.errors["app1"] = error

        # Verify model dump includes errors
        dumped = results.model_dump()
        self.assertIn("errors", dumped)
        self.assertIn("success_rate", dumped)
        self.assertEqual(dumped["success_rate"], 80.0)

    def test_get_dex2jar_tools_returns_pydantic_model(self):
        """Test that get_dex2jar_tools returns validated Pydantic model."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create minimal required structure
            monitor_dir = temp_path / "monitors"
            monitor_dir.mkdir()
            (monitor_dir / "test.aj").touch()
            (monitor_dir / "test.java").touch()

            android_platforms = temp_path / "android" / "platforms"
            android_platforms.mkdir(parents=True)
            android_jar = android_platforms / "android-29" / "android.jar"
            android_jar.parent.mkdir()
            android_jar.touch()

            keystore_file = temp_path / "test.jks"
            keystore_file.touch()

            dex2jar_home = temp_path / "dex2jar"
            dex2jar_home.mkdir()

            # Create dex2jar tools
            for tool in ["d2j-dex2jar.sh", "d2j-asm-verify.sh", "d2j-apk-sign.sh"]:
                tool_path = dex2jar_home / tool
                tool_path.touch()
                tool_path.chmod(0o755)

            with patch("rv_instrumentation_ajc.config.LoggingManager") as mock_logging:
                mock_logging.get_instance.return_value.get_logger.return_value = (
                    MagicMock()
                )

                config = AjcInstrumentationConfig(
                    monitor_output_dir=str(monitor_dir),
                    android_jar_path=str(android_jar),
                    android_platforms_dir=str(android_platforms),
                    keystore_file=str(keystore_file),
                    keystore_password="testpassword",
                    working_dir=str(temp_path),
                    instrumented_dir=str(temp_path / "out"),
                    dex2jar_home=str(dex2jar_home),
                )

                # Test that method returns Pydantic model
                tools = config.get_dex2jar_tools()
                self.assertIsInstance(tools, Dex2jarTools)
                self.assertTrue(hasattr(tools, "model_dump"))

    def test_get_configuration_summary_returns_pydantic_model(self):
        """Test that get_configuration_summary returns validated Pydantic model."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create minimal required structure
            monitor_dir = temp_path / "monitors"
            monitor_dir.mkdir()
            (monitor_dir / "test.aj").touch()
            (monitor_dir / "test.java").touch()

            android_platforms = temp_path / "android" / "platforms"
            android_platforms.mkdir(parents=True)
            android_jar = android_platforms / "android-29" / "android.jar"
            android_jar.parent.mkdir()
            android_jar.touch()

            keystore_file = temp_path / "test.jks"
            keystore_file.touch()

            dex2jar_home = temp_path / "dex2jar"
            dex2jar_home.mkdir()

            # Create dex2jar tools
            for tool in ["d2j-dex2jar.sh", "d2j-asm-verify.sh", "d2j-apk-sign.sh"]:
                tool_path = dex2jar_home / tool
                tool_path.touch()
                tool_path.chmod(0o755)

            with patch("rv_instrumentation_ajc.config.LoggingManager") as mock_logging:
                mock_logging.get_instance.return_value.get_logger.return_value = (
                    MagicMock()
                )

                config = AjcInstrumentationConfig(
                    monitor_output_dir=str(monitor_dir),
                    android_jar_path=str(android_jar),
                    android_platforms_dir=str(android_platforms),
                    keystore_file=str(keystore_file),
                    keystore_password="testpassword",
                    working_dir=str(temp_path),
                    instrumented_dir=str(temp_path / "out"),
                    dex2jar_home=str(dex2jar_home),
                )

                # Test that method returns Pydantic model
                summary = config.get_configuration_summary()
                self.assertIsInstance(summary, ConfigurationSummary)
                self.assertTrue(hasattr(summary, "model_dump"))

                # Verify structure using Pydantic attributes
                self.assertEqual(summary.validation_status, "Validated")
                self.assertIn("aspectj_count", summary.monitor_artifacts)
                self.assertIn("java_count", summary.monitor_artifacts)

    def test_apk_input_validation(self):
        """Test APK input validation functionality with Pydantic integration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a dummy APK file
            apk_file = temp_path / "test.apk"
            apk_file.touch()

            # Create minimal config for testing validation method
            monitor_dir = temp_path / "monitors"
            monitor_dir.mkdir()
            (monitor_dir / "test.aj").touch()
            (monitor_dir / "test.java").touch()

            android_platforms = temp_path / "android" / "platforms"
            android_platforms.mkdir(parents=True)
            android_jar = android_platforms / "android-29" / "android.jar"
            android_jar.parent.mkdir()
            android_jar.touch()

            keystore_file = temp_path / "test.jks"
            keystore_file.touch()

            dex2jar_home = temp_path / "dex2jar"
            dex2jar_home.mkdir()
            for tool in ["d2j-dex2jar.sh", "d2j-asm-verify.sh", "d2j-apk-sign.sh"]:
                tool_path = dex2jar_home / tool
                tool_path.touch()
                tool_path.chmod(0o755)

            with patch("rv_instrumentation_ajc.config.LoggingManager") as mock_logging:
                mock_logging.get_instance.return_value.get_logger.return_value = (
                    MagicMock()
                )

                config = AjcInstrumentationConfig(
                    monitor_output_dir=str(monitor_dir),
                    android_jar_path=str(android_jar),
                    android_platforms_dir=str(android_platforms),
                    keystore_file=str(keystore_file),
                    keystore_password="testpassword",
                    working_dir=str(temp_path),
                    instrumented_dir=str(temp_path / "out"),
                    dex2jar_home=str(dex2jar_home),
                )

                # Valid APK should not raise exception
                try:
                    config.validate_apk_input(str(apk_file))
                except ConfigurationError:
                    self.fail(
                        "validate_apk_input raised ConfigurationError for valid APK"
                    )

                # Non-existent file should raise exception
                with self.assertRaises(ConfigurationError):
                    config.validate_apk_input(str(temp_path / "nonexistent.apk"))

                # Non-APK file should raise exception
                non_apk = temp_path / "test.txt"
                non_apk.touch()
                with self.assertRaises(ConfigurationError):
                    config.validate_apk_input(str(non_apk))

    def test_pydantic_serialization_methods(self):
        """Test Pydantic model serialization capabilities."""
        error = InstrumentationErrorModel(
            code=-1, tool="test_tool", message="Test error message", phase="test_phase"
        )

        # Test model_dump
        dumped = error.model_dump()
        self.assertIsInstance(dumped, dict)
        self.assertEqual(dumped["code"], -1)
        self.assertEqual(dumped["tool"], "test_tool")

        # Test model_dump_json
        json_str = error.model_dump_json()
        self.assertIsInstance(json_str, str)
        self.assertIn('"code":-1', json_str)

        # Test from_dict class method
        recreated = InstrumentationErrorModel.from_dict(dumped)
        self.assertEqual(recreated.code, error.code)
        self.assertEqual(recreated.tool, error.tool)
        self.assertEqual(recreated.message, error.message)
        self.assertEqual(recreated.phase, error.phase)
