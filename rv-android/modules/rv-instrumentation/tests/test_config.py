"""
Simple unit tests for RVInstrumentationConfig.

These basic tests verify configuration initialization and path resolution
without requiring external dependencies or full instrumentation setup.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from rv_instrumentation.config import RVInstrumentationConfig, ConfigurationError


class TestRVInstrumentationConfig(unittest.TestCase):
    """Basic tests for RVInstrumentationConfig functionality."""

    def test_config_initialization_with_defaults(self):
        """Test that configuration initializes with default values."""
        # Mock environment variables to avoid dependency on actual environment
        with patch.dict(os.environ, {}, clear=True):
            with patch('rv_instrumentation.config.os.getcwd') as mock_getcwd:
                mock_getcwd.return_value = '/mock/working/dir'
                
                # This will fail validation but we just want to test initialization
                with self.assertRaises(ConfigurationError):
                    RVInstrumentationConfig()

    def test_config_with_explicit_paths(self):
        """Test configuration with all explicit paths provided."""
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
            for tool in ['d2j-dex2jar.sh', 'd2j-asm-verify.sh', 'd2j-apk-sign.sh']:
                tool_path = dex2jar_home / tool
                tool_path.touch()
                tool_path.chmod(0o755)
            
            instrumented_dir = temp_path / "instrumented"
            working_dir = temp_path / "working"
            
            # Mock subprocess.run to avoid actual tool execution
            with patch('rv_instrumentation.config.subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(stdout="test output", stderr="", returncode=0)
                
                # Test configuration with explicit paths
                config = RVInstrumentationConfig(
                    monitor_output_dir=str(monitor_dir),
                    android_jar_path=str(android_jar),
                    android_platforms_dir=str(android_platforms),
                    keystore_file=str(keystore_file),
                    keystore_password="testpassword",
                    working_dir=str(working_dir),
                    instrumented_dir=str(instrumented_dir),
                    dex2jar_home=str(dex2jar_home)
                )
                
                # Verify configuration values
                self.assertEqual(config.monitor_output_dir, str(monitor_dir))
                self.assertEqual(config.android_jar_path, str(android_jar))
                self.assertEqual(config.keystore_file, str(keystore_file))
                self.assertEqual(config.keystore_password, "testpassword")
                self.assertEqual(config.dex2jar_home, str(dex2jar_home))

    # def test_bundled_keystore_path_resolution(self):
    #     """Test that bundled keystore path is resolved correctly."""
    #     # Create a minimal config just to test keystore path resolution
    #     config = RVInstrumentationConfig.__new__(RVInstrumentationConfig)
    #     config.keystore_file = None
    #     config.keystore_password = None
    #
    #     # Call the method that sets default paths
    #     config._apply_default_paths()
    #
    #     # Verify keystore path points to bundled keystore
    #     self.assertIsNotNone(config.keystore_file)
    #     self.assertTrue(config.keystore_file.endswith("keystore.jks"))
    #     self.assertEqual(config.keystore_password, "password")

    def test_dex2jar_tools_configuration(self):
        """Test dex2jar tools path configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dex2jar_home = Path(temp_dir) / "dex2jar"
            dex2jar_home.mkdir()
            
            config = RVInstrumentationConfig.__new__(RVInstrumentationConfig)
            config.dex2jar_home = str(dex2jar_home)
            
            tools = config.get_dex2jar_tools()
            
            expected_tools = ['dex2jar', 'asm_verify', 'apk_sign']
            self.assertEqual(set(tools.keys()), set(expected_tools))
            
            # Verify tool paths
            for tool_name, tool_path in tools.items():
                self.assertTrue(tool_path.startswith(str(dex2jar_home)))

    def test_configuration_summary(self):
        """Test configuration summary generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create minimal required structure
            monitor_dir = temp_path / "monitors"
            monitor_dir.mkdir()
            (monitor_dir / "test.aj").touch()
            (monitor_dir / "test.java").touch()
            
            config = RVInstrumentationConfig.__new__(RVInstrumentationConfig)
            config.monitor_output_dir = str(monitor_dir)
            config.android_jar_path = "/mock/android.jar"
            config.android_platforms_dir = "/mock/platforms"
            config.working_dir = str(temp_path)
            config.instrumented_dir = str(temp_path / "out")
            config.tmp_dir = str(temp_path / "tmp")
            config.lib_tmp_dir = str(temp_path / "lib_tmp")
            config.rvm_tmp_dir = str(temp_path / "rvm_tmp")
            config.dex2jar_home = str(temp_path / "dex2jar")
            config.keystore_file = str(temp_path / "test.jks")
            config.keystore_password = "test"
            
            summary = config.get_configuration_summary()
            
            # Verify summary structure
            self.assertIn('android_integration', summary)
            self.assertIn('instrumentation_paths', summary)
            self.assertIn('temporary_directories', summary)
            self.assertIn('tools', summary)
            self.assertIn('signing', summary)
            self.assertIn('monitor_artifacts', summary)
            self.assertEqual(summary['validation_status'], 'Validated')

    def test_apk_input_validation(self):
        """Test APK input validation functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a dummy APK file
            apk_file = temp_path / "test.apk"
            apk_file.touch()
            
            config = RVInstrumentationConfig.__new__(RVInstrumentationConfig)
            
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
