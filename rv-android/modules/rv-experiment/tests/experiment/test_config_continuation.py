# tests/experiment/test_config_continuation.py
import json
import os
import tempfile
from unittest.mock import patch
from datetime import datetime

import pytest

from rv_android_core.util.exceptions import ConfigurationError
from rv_experiment.config import ExperimentConfig
from rv_platform.config.platform_config import ToolConfig


class TestExperimentConfigContinuation:
    """Tests for experiment continuation functionality in ExperimentConfig"""

    @pytest.fixture
    def sample_config(self):
        """Fixture providing a basic experiment configuration"""
        return ExperimentConfig(
            name="test_experiment",
            tool_configs=[ToolConfig(name="monkey")],
            specification_set="jca"
        )

    @pytest.fixture 
    def sample_status_file(self, tmp_path):
        """Fixture providing a temporary status file"""
        status_data = {
            "experiment": {
                "experiment_id": "exp_20250101_120000_abcd1234",
                "start_time": "2025-01-01T12:00:00",
                "config_checksum": "abcd1234567890",
                "current_status": "running"
            },
            "statistics": {
                "total_tasks": 10,
                "completed_tasks": 5,
                "failed_tasks": 1,
                "pending_tasks": 4
            },
            "tasks": []
        }
        
        status_file = tmp_path / "tasks.json"
        with open(status_file, 'w') as f:
            json.dump(status_data, f)
        
        return str(status_file)

    def test_get_effective_rvsec_root_config_override(self, sample_config):
        """Test RVSEC_HOME resolution with config override (highest priority)"""
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            sample_config.rvsec_root = temp_dir
            
            # Should use config override even if environment variable exists
            with patch.dict(os.environ, {"RVSEC_HOME": "/some/other/path"}):
                result = sample_config.get_effective_rvsec_root()
                assert result == temp_dir

    def test_get_effective_rvsec_root_environment_fallback(self, sample_config):
        """Test RVSEC_HOME resolution with environment variable fallback"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # No config override, should use environment variable
            sample_config.rvsec_root = None
            
            with patch.dict(os.environ, {"RVSEC_HOME": temp_dir}):
                result = sample_config.get_effective_rvsec_root()
                assert result == temp_dir

    def test_get_effective_rvsec_root_error_when_missing(self, sample_config):
        """Test RVSEC_HOME resolution error when neither config nor environment are set"""
        sample_config.rvsec_root = None
        
        # Clear environment variable
        with patch.dict(os.environ, {}, clear=True):
            # ErrorHandler catches and logs the exception, so no exception is raised
            result = sample_config.get_effective_rvsec_root()
            # When ErrorHandler catches an error, it returns None
            assert result is None

    def test_get_effective_rvsec_root_error_nonexistent_path(self, sample_config):
        """Test RVSEC_HOME resolution error when path doesn't exist"""
        sample_config.rvsec_root = "/nonexistent/path/that/should/not/exist"
        
        # ErrorHandler catches and logs the exception, so no exception is raised
        result = sample_config.get_effective_rvsec_root()
        # When ErrorHandler catches an error, it returns None
        assert result is None

    def test_load_from_status_success(self, sample_status_file):
        """Test successful loading of experiment configuration from status file"""
        config = ExperimentConfig.load_from_status(sample_status_file)
        
        assert config.resume_mode is True
        assert config.status_file == sample_status_file
        assert config.name == "exp_20250101_120000_abcd1234"
        assert "resumed_from" in config.metadata
        assert "original_start_time" in config.metadata
        assert "continuation_time" in config.metadata
        assert "config_checksum" in config.metadata

    def test_load_from_status_file_not_found(self):
        """Test loading from non-existent status file"""
        # ErrorHandler catches and logs the exception, so no exception is raised
        result = ExperimentConfig.load_from_status("/nonexistent/file.json")
        # When ErrorHandler catches an error, it returns None
        assert result is None

    def test_load_from_status_invalid_json(self, tmp_path):
        """Test loading from invalid JSON status file"""
        invalid_file = tmp_path / "invalid.json"
        with open(invalid_file, 'w') as f:
            f.write("invalid json content")
        
        # ErrorHandler catches and logs the exception, so no exception is raised
        result = ExperimentConfig.load_from_status(str(invalid_file))
        # When ErrorHandler catches an error, it returns None
        assert result is None

    def test_load_from_status_missing_experiment_data(self, tmp_path):
        """Test loading from status file missing experiment metadata"""
        incomplete_file = tmp_path / "incomplete.json"
        with open(incomplete_file, 'w') as f:
            json.dump({"statistics": {}, "tasks": []}, f)
        
        # ErrorHandler catches and logs the exception, so no exception is raised
        result = ExperimentConfig.load_from_status(str(incomplete_file))
        # When ErrorHandler catches an error, it returns None
        assert result is None

    def test_enable_continuation_mode(self, sample_config, sample_status_file):
        """Test enabling continuation mode on existing config"""
        assert sample_config.resume_mode is False
        assert sample_config.status_file is None
        
        sample_config.enable_continuation_mode(sample_status_file)
        
        assert sample_config.resume_mode is True
        assert sample_config.status_file == sample_status_file
        assert "continuation_enabled" in sample_config.metadata
        assert "status_file" in sample_config.metadata
        assert "continuation_time" in sample_config.metadata

    def test_get_enhanced_storage_config(self, sample_config):
        """Test enhanced storage configuration generation"""
        storage_config = sample_config.get_enhanced_storage_config()
        
        # Verify storage configuration is properly initialized
        assert storage_config.enable_metadata is True
        assert storage_config.enable_statistics is True
        assert storage_config.auto_save is True

    def test_continuation_fields_defaults(self, sample_config):
        """Test that continuation fields have proper defaults"""
        assert sample_config.resume_mode is False
        assert sample_config.rvsec_root is None
        assert sample_config.status_file is None

    def test_continuation_fields_can_be_set(self):
        """Test that continuation fields can be set during initialization"""
        config = ExperimentConfig(
            name="test_continuation",
            tool_configs=[ToolConfig(name="monkey")],
            specification_set="jca",
            resume_mode=True,
            rvsec_root="/custom/rvsec/path",
            status_file="/path/to/status.json"
        )
        
        assert config.resume_mode is True
        assert config.rvsec_root == "/custom/rvsec/path"
        assert config.status_file == "/path/to/status.json"