"""
Simple unit tests for RVStaticAnalysisConfig.

These basic tests verify configuration initialization and path resolution
without requiring external dependencies or full static analysis setup.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from rv_static_analysis.config import RVStaticAnalysisConfig, ConfigurationError


class TestRVStaticAnalysisConfig(unittest.TestCase):
    """Basic tests for RVStaticAnalysisConfig functionality."""

    def test_config_initialization_with_defaults(self):
        """Test that configuration initializes with default values."""
        # Mock environment variables to avoid dependency on actual environment
        with patch.dict(os.environ, {}, clear=True):
            with patch('rv_static_analysis.config.os.getcwd') as mock_getcwd:
                mock_getcwd.return_value = '/mock/working/dir'
                
                # This will fail validation but we just want to test initialization
                with self.assertRaises(ConfigurationError):
                    RVStaticAnalysisConfig()

    def test_config_with_explicit_paths(self):
        """Test configuration with all explicit paths provided."""
        # Create temporary directories for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create required directories and files
            lib_dir = temp_path / "lib"
            lib_dir.mkdir()
            
            # Create static analysis tools
            gesda_dir = lib_dir / "gesda"
            gesda_dir.mkdir()
            gesda_jar = gesda_dir / "rvsec-gesda.jar"
            gesda_jar.touch()
            
            gator_dir = lib_dir / "gator"
            gator_dir.mkdir()
            gator_python = gator_dir / "gator"
            gator_python.touch()
            gator_python.chmod(0o755)
            gator_client_jar = gator_dir / "rvsec-gator-client.jar"
            gator_client_jar.touch()
            
            reach_dir = lib_dir / "reach"
            reach_dir.mkdir()
            reach_jar = reach_dir / "rvsec-reach.jar"
            reach_jar.touch()
            
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
            
            # Test configuration with explicit paths
            config = RVStaticAnalysisConfig(
                lib_dir=str(lib_dir),
                android_platforms_dir=str(android_platforms),
                rt_jar=str(android_jar),
                mop_dir=str(mop_dir),
                output_dir=str(output_dir),
                working_dir=str(working_dir),
                gesda_jar=str(gesda_jar),
                gator_dir=str(gator_dir),
                reach_jar=str(reach_jar)
            )
            
            # Verify configuration values
            self.assertEqual(config.lib_dir, str(lib_dir))
            self.assertEqual(config.android_platforms_dir, str(android_platforms))
            self.assertEqual(config.rt_jar, str(android_jar))
            self.assertEqual(config.mop_dir, str(mop_dir))
            self.assertEqual(config.gesda_jar, str(gesda_jar))
            self.assertEqual(config.gator_dir, str(gator_dir))
            self.assertEqual(config.reach_jar, str(reach_jar))

    def test_static_analysis_tools_configuration(self):
        """Test static analysis tools path configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            lib_dir = Path(temp_dir) / "lib"
            lib_dir.mkdir()
            
            # Use Pydantic constructor with validation disabled
            config = RVStaticAnalysisConfig(
                lib_dir=str(lib_dir),
                gesda_jar=str(lib_dir / "gesda" / "rvsec-gesda.jar"),
                gator_dir=str(lib_dir / "gator"),
                reach_jar=str(lib_dir / "reach" / "rvsec-reach.jar"),
                validate_on_init=False
            )
            
            tools = config.get_tool_components()
            
            expected_tools = ['gesda_jar', 'gator_python', 'gator_client_jar', 'reach_jar']
            self.assertEqual(set(tools.keys()), set(expected_tools))
            
            # Verify tool paths
            for tool_name, tool_path in tools.items():
                if tool_name in ['gator_python', 'gator_client_jar']:
                    self.assertTrue(tool_path.startswith(str(lib_dir / "gator")))
                else:
                    self.assertTrue(tool_path.startswith(str(lib_dir)))

    def test_tool_command_generation(self):
        """Test tool command generation functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create minimal required structure
            lib_dir = temp_path / "lib"
            lib_dir.mkdir()
            
            # Use Pydantic constructor with validation disabled
            config = RVStaticAnalysisConfig(
                lib_dir=str(lib_dir),
                gesda_jar=str(lib_dir / "gesda" / "rvsec-gesda.jar"),
                gator_dir=str(lib_dir / "gator"),
                reach_jar=str(lib_dir / "reach" / "rvsec-reach.jar"),
                android_platforms_dir=str(temp_path / "platforms"),
                rt_jar=str(temp_path / "android.jar"),
                mop_dir=str(temp_path / "mop"),
                validate_on_init=False
            )
            
            # Test GESDA command
            gesda_cmd = config.get_tool_command('gesda', '/test/app.apk', '/test/output.gesda')
            self.assertEqual(gesda_cmd[0], 'java')
            self.assertIn('-jar', gesda_cmd)
            self.assertIn('/test/app.apk', gesda_cmd)
            
            # Test GATOR command
            gator_cmd = config.get_tool_command('gator', '/test/app.apk', '/test/output.wtg')
            self.assertEqual(gator_cmd[0], 'python')
            self.assertIn('/test/app.apk', gator_cmd)
            
            # Test REACH command
            reach_cmd = config.get_tool_command(
                'reach', '/test/app.apk', '/test/output.reach',
                gesda_file='/test/input.gesda'
            )
            self.assertEqual(reach_cmd[0], 'java')
            self.assertIn('-jar', reach_cmd)
            self.assertIn('/test/input.gesda', reach_cmd)

    def test_configuration_summary(self):
        """Test configuration summary generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Use Pydantic constructor with validation disabled
            config = RVStaticAnalysisConfig(
                rvsec_root=str(temp_path),
                lib_dir=str(temp_path / "lib"),
                android_platforms_dir=str(temp_path / "platforms"),
                rt_jar=str(temp_path / "rt.jar"),
                mop_dir=str(temp_path / "mop"),
                output_dir=str(temp_path / "output"),
                working_dir=str(temp_path / "working"),
                gesda_jar=str(temp_path / "lib" / "gesda" / "rvsec-gesda.jar"),
                gator_dir=str(temp_path / "lib" / "gator"),
                reach_jar=str(temp_path / "lib" / "reach" / "rvsec-reach.jar"),
                validate_on_init=False
            )
            
            summary = config.get_configuration_summary()
            
            # Verify summary structure
            self.assertIn('rvsec_integration', summary)
            self.assertIn('java_android_integration', summary)
            self.assertIn('static_analysis_tools', summary)
            self.assertIn('tool_availability', summary)
            self.assertEqual(summary['validation_status'], 'Validated')

    def test_apk_input_validation(self):
        """Test APK input validation functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a dummy APK file
            apk_file = temp_path / "test.apk"
            apk_file.touch()
            
            # Use Pydantic constructor with validation disabled
            config = RVStaticAnalysisConfig(
                validate_on_init=False,
                rvsec_root=str(temp_path)
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

    def test_unsupported_tool_command_error(self):
        """Test error handling for unsupported tools."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = RVStaticAnalysisConfig(
                validate_on_init=False,
                rvsec_root=temp_dir
            )
            
            with self.assertRaises(ConfigurationError) as context:
                config.get_tool_command('unsupported_tool', '/test/app.apk', '/test/output')
            
            self.assertIn("Unsupported static analysis tool", str(context.exception))

    def test_reach_command_without_gesda_file(self):
        """Test REACH command generation fails without GESDA file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = RVStaticAnalysisConfig(
                validate_on_init=False,
                rvsec_root=temp_dir,
                reach_jar="/mock/reach.jar",
                android_platforms_dir="/mock/platforms",
                mop_dir="/mock/mop"
            )
            
            with self.assertRaises(ConfigurationError) as context:
                config.get_tool_command('reach', '/test/app.apk', '/test/output.reach')
            
            self.assertIn("REACH tool requires GESDA output file", str(context.exception))
