import os
import shutil
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from rv_monitor_generator.config import RVGeneratorConfig
from rv_monitor_generator.runtime_verification_generator import RuntimeVerificationGenerator


class TestRuntimeVerificationGenerator:
    """
    Unit tests for RuntimeVerificationGenerator with proper architectural patterns.
    
    These tests follow the modern test architecture patterns and use proper
    configuration discovery mechanisms based on modular configuration classes.
    """

    @pytest.fixture
    def rvsec_root_dir(self):
        """
        Discover RVSEC root directory using configuration discovery logic.
        
        This follows the modular configuration approach where each module
        handles its own directory discovery independently.
        """
        # Get the current working directory (should be rv-android when tests run)
        working_dir = os.getcwd()

        # Navigate to RVSEC root (one level up from rv-android)
        rvsec_root = os.path.join(working_dir, os.path.abspath(".."))

        # Validate that this looks like a RVSEC installation
        expected_dirs = ['javamop', 'rv-monitor', 'rvsec']
        if all(os.path.exists(os.path.join(rvsec_root, d)) for d in expected_dirs):
            return rvsec_root
        else:
            pytest.skip("RVSEC installation not found - skipping integration tests")

    @pytest.fixture
    def temp_environment(self):
        """Create temporary directory structure for isolated testing."""
        temp_dir = tempfile.mkdtemp()

        # Create mock RVSEC structure
        rvsec_structure = {
            'javamop/bin': ['javamop'],
            'rv-monitor/bin': ['rv-monitor'],
            'rvsec/rvsec-mop/src/main/resources/jca': ['test1.mop', 'test2.mop'],
            'rvsec/rvsec-mop/src/main/resources/generic': ['generic1.mop'],
            'rvsec/rvsec-mop/src/main/resources/aspect': ['logging.aj']
        }

        for dir_path, files in rvsec_structure.items():
            full_dir = os.path.join(temp_dir, dir_path)
            os.makedirs(full_dir, exist_ok=True)

            for file_name in files:
                file_path = os.path.join(full_dir, file_name)
                with open(file_path, 'w') as f:
                    if file_name.endswith('.mop'):
                        f.write(f'// Test MOP specification: {file_name}')
                    elif file_name.endswith('.aj'):
                        f.write(f'// Test AspectJ file: {file_name}')
                    else:
                        f.write('#!/bin/bash\necho "Mock tool execution"')

                # Make binaries executable
                if dir_path.endswith('/bin'):
                    os.chmod(file_path, 0o755)

        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_config(self, temp_environment):
        """Create a properly configured RVGeneratorConfig for testing."""
        return RVGeneratorConfig(
            rvsec_root=temp_environment,
            mop_specs_dir=os.path.join(temp_environment, 'rvsec/rvsec-mop/src/main/resources/jca')
        )

    def test_initialization_with_config(self, mock_config):
        """Test RuntimeVerificationGenerator initialization with explicit config."""
        with patch('rv_monitor_generator.runtime_verification_generator.LoggingManager') as mock_logging_mgr, \
                patch('rv_monitor_generator.runtime_verification_generator.ErrorHandler') as mock_error_handler:
            # Setup mocks
            mock_logger = MagicMock()
            mock_logging_mgr.get_instance.return_value.get_logger.return_value = mock_logger
            mock_error_handler.get_instance.return_value = MagicMock()

            # Initialize generator
            generator = RuntimeVerificationGenerator(mock_config)

            # Verify initialization
            assert generator.config == mock_config
            assert generator._logger == mock_logger

            # Verify logging manager was called with proper context
            mock_logging_mgr.get_instance.assert_called_once()
            mock_logging_mgr.get_instance.return_value.get_logger.assert_called_once()

            # Verify logger was called with initialization message
            mock_logger.info.assert_called_once()

    def test_initialization_without_config(self):
        """Test RuntimeVerificationGenerator initialization with auto-config."""
        with patch('rv_monitor_generator.runtime_verification_generator.LoggingManager') as mock_logging_mgr, \
                patch('rv_monitor_generator.runtime_verification_generator.ErrorHandler') as mock_error_handler, \
                patch('rv_monitor_generator.config.os.getenv') as mock_getenv, \
                patch('rv_monitor_generator.config.os.path.exists') as mock_exists, \
                patch('rv_monitor_generator.config.os.path.isfile') as mock_isfile, \
                patch('rv_monitor_generator.config.os.path.isdir') as mock_isdir, \
                patch('rv_monitor_generator.config.os.access') as mock_access, \
                patch('rv_monitor_generator.config.subprocess.run') as mock_subprocess, \
                patch('rv_monitor_generator.config.glob.glob') as mock_glob:
            
            # Setup mocks for RVGeneratorConfig internal dependencies
            mock_getenv.return_value = '/fake/rvsec/path'
            mock_exists.return_value = True
            mock_isfile.return_value = True  # Binary files exist
            mock_isdir.return_value = True   # Directories exist
            mock_access.return_value = True  # Files are accessible
            mock_subprocess.return_value.stdout = "tool output"
            mock_subprocess.return_value.stderr = ""
            mock_glob.return_value = ['/fake/spec1.mop', '/fake/spec2.mop']
            
            # Setup logging mocks
            mock_logger = MagicMock()
            mock_logging_mgr.get_instance.return_value.get_logger.return_value = mock_logger

            # Initialize generator without explicit config
            generator = RuntimeVerificationGenerator()

            # Verify that config is a real RVGeneratorConfig instance, not a mock
            assert isinstance(generator.config, RVGeneratorConfig)
            # Verify that environment variable was used
            mock_getenv.assert_called()

    def test_generate_monitors_success(self, mock_config):
        """Test successful monitor generation pipeline."""
        output_dir = tempfile.mkdtemp()

        try:
            with patch('rv_monitor_generator.runtime_verification_generator.LoggingManager') as mock_logging_mgr, \
                    patch('rv_monitor_generator.runtime_verification_generator.ErrorHandler') as mock_error_handler, \
                    patch('rv_android_core.util.utils.reset_folder') as mock_reset, \
                    patch('rv_android_core.util.utils.execute_command') as mock_execute, \
                    patch('rv_android_core.util.utils.move_files_by_extension') as mock_move, \
                    patch('rv_android_core.util.utils.copy_files_by_extension') as mock_copy, \
                    patch('rv_android_core.util.utils.delete_files_by_extension') as mock_delete:

                # Setup mocks
                mock_logger = MagicMock()
                mock_logging_mgr.get_instance.return_value.get_logger.return_value = mock_logger
                mock_error_handler.get_instance.return_value = MagicMock()

                # Initialize and execute
                generator = RuntimeVerificationGenerator(mock_config)
                result = generator.generate_monitors(output_dir)

                # Verify success
                assert result is True

                # Verify pipeline execution
                mock_reset.assert_called_once_with(output_dir)
                assert mock_execute.call_count == 2  # JavaMOP + RV-Monitor
                mock_move.assert_called_once()  # Move RVM files
                mock_copy.assert_called_once()  # Copy AspectJ files
                mock_delete.assert_called_once()  # Delete intermediate RVM files

                # Verify logging
                assert mock_logger.info.call_count >= 3  # Init + Start + Complete

        finally:
            shutil.rmtree(output_dir)

    def test_generate_monitors_failure(self, mock_config):
        """Test monitor generation pipeline failure handling."""
        output_dir = tempfile.mkdtemp()

        try:
            with patch('rv_monitor_generator.runtime_verification_generator.LoggingManager') as mock_logging_mgr, \
                    patch('rv_monitor_generator.runtime_verification_generator.ErrorHandler') as mock_error_handler, \
                    patch('rv_android_core.util.utils.reset_folder') as mock_reset, \
                    patch('rv_android_core.util.utils.execute_command') as mock_execute:

                # Setup mocks
                mock_logger = MagicMock()
                mock_logging_mgr.get_instance.return_value.get_logger.return_value = mock_logger
                mock_error_handler_instance = MagicMock()
                mock_error_handler.get_instance.return_value = mock_error_handler_instance

                # Simulate failure
                mock_execute.side_effect = Exception("Tool execution failed")

                # Initialize and execute
                generator = RuntimeVerificationGenerator(mock_config)
                result = generator.generate_monitors(output_dir)

                # Verify failure handling
                assert result is False
                mock_error_handler_instance.handle_error.assert_called_once()

        finally:
            shutil.rmtree(output_dir)

    def test_get_generation_summary(self, mock_config):
        """Test generation summary functionality."""
        output_dir = tempfile.mkdtemp()

        try:
            # Create mock generated files
            test_files = [
                ('Monitor1.aj', '// AspectJ file'),
                ('Monitor2.aj', '// AspectJ file'),
                ('Monitor1.java', '// Java monitor class'),
                ('Monitor2.java', '// Java monitor class'),
                ('Monitor3.java', '// Java monitor class')
            ]

            for filename, content in test_files:
                with open(os.path.join(output_dir, filename), 'w') as f:
                    f.write(content)

            with patch('rv_monitor_generator.runtime_verification_generator.LoggingManager') as mock_logging_mgr, \
                    patch('rv_monitor_generator.runtime_verification_generator.ErrorHandler') as mock_error_handler:

                # Setup mocks
                mock_logger = MagicMock()
                mock_logging_mgr.get_instance.return_value.get_logger.return_value = mock_logger
                mock_error_handler.get_instance.return_value = MagicMock()

                # Initialize and get summary
                generator = RuntimeVerificationGenerator(mock_config)
                summary = generator.get_generation_summary(output_dir)

                # Verify summary content
                assert summary['output_directory'] == output_dir
                assert summary['aspectj_files']['count'] == 2
                assert summary['monitor_classes']['count'] == 3
                assert 'purpose' in summary['aspectj_files']
                assert 'purpose' in summary['monitor_classes']
                assert 'specs_processed' in summary

        finally:
            shutil.rmtree(output_dir)

    def test_mop_specs_discovery(self, mock_config):
        """Test MOP specification file discovery."""
        with patch('rv_monitor_generator.runtime_verification_generator.LoggingManager') as mock_logging_mgr, \
                patch('rv_monitor_generator.runtime_verification_generator.ErrorHandler') as mock_error_handler:
            # Setup mocks
            mock_logger = MagicMock()
            mock_logging_mgr.get_instance.return_value.get_logger.return_value = mock_logger
            mock_error_handler.get_instance.return_value = MagicMock()

            # Initialize generator
            generator = RuntimeVerificationGenerator(mock_config)

            # Test spec discovery
            specs = generator._get_mop_specs()

            # Verify specs found
            assert len(specs) == 2  # test1.mop and test2.mop from fixture
            assert all(spec.endswith('.mop') for spec in specs)


class TestRuntimeVerificationGeneratorIntegration:
    """
    Integration tests using real RVSEC installation when available.
    
    These tests will be skipped if RVSEC is not properly installed.
    """

    @pytest.fixture
    def rvsec_root_dir(self):
        """Discover RVSEC root directory dynamically."""
        working_dir = os.getcwd()
        rvsec_root = os.path.join(working_dir, os.path.abspath(".."))

        # Validate RVSEC installation
        required_components = [
            'javamop/bin/javamop',
            'rv-monitor/bin/rv-monitor',
            'rvsec/rvsec-mop/src/main/resources/jca',
            'rvsec/rvsec-mop/src/main/resources/aspect'
        ]

        if all(os.path.exists(os.path.join(rvsec_root, comp)) for comp in required_components):
            return rvsec_root
        else:
            pytest.skip("RVSEC installation not found - skipping integration tests")

    def test_real_config_validation(self, rvsec_root_dir):
        """Test configuration validation with real RVSEC installation."""
        # Test JCA configuration
        jca_config = RVGeneratorConfig(
            rvsec_root=rvsec_root_dir,
            mop_specs_dir=os.path.join(rvsec_root_dir, 'rvsec/rvsec-mop/src/main/resources/jca')
        )

        # Verify configuration is valid
        assert os.path.exists(jca_config.javamop_bin)
        assert os.path.exists(jca_config.rvmonitor_bin)
        assert os.path.exists(jca_config.mop_specs_dir)
        assert os.path.exists(jca_config.aspects_dir)

        # Test generic configuration if available
        generic_specs_dir = os.path.join(rvsec_root_dir, 'rvsec/rvsec-mop/src/main/resources/generic')
        if os.path.exists(generic_specs_dir):
            generic_config = RVGeneratorConfig(
                rvsec_root=rvsec_root_dir,
                mop_specs_dir=generic_specs_dir
            )
            assert os.path.exists(generic_config.mop_specs_dir)

    def test_environment_variable_config(self, rvsec_root_dir):
        """Test configuration using RVSEC_HOME environment variable."""
        with patch.dict(os.environ, {'RVSEC_HOME': rvsec_root_dir}):
            # Create config without explicit rvsec_root
            config = RVGeneratorConfig(
                mop_specs_dir=os.path.join(rvsec_root_dir, 'rvsec/rvsec-mop/src/main/resources/jca')
            )

            # Verify environment-based configuration
            assert config.javamop_bin.startswith(rvsec_root_dir)
            assert config.rvmonitor_bin.startswith(rvsec_root_dir)

    @pytest.mark.slow
    def test_tool_functionality_validation(self, rvsec_root_dir):
        """Test that JavaMOP and RV-Monitor tools are actually functional."""
        config = RVGeneratorConfig(
            rvsec_root=rvsec_root_dir,
            mop_specs_dir=os.path.join(rvsec_root_dir, 'rvsec/rvsec-mop/src/main/resources/jca')
        )

        # This test validates that the tools can actually be executed
        # The _validate_tool_functionality method is called during config initialization
        # If we get here without an exception, the tools are functional

        assert config.javamop_bin.endswith('javamop')
        assert config.rvmonitor_bin.endswith('rv-monitor')
