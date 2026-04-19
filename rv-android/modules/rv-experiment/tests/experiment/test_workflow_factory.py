"""
Tests for WorkflowFactory - experiment workflow component factory.

Tests cover:
- Factory initialization with storage and config
- create_pre_processor() component creation
- create_execution_controller() component creation
- create_post_processor() component creation
- create_result_manager() component creation
"""

from unittest.mock import MagicMock, patch

import pytest
from rv_experiment.experiment.workflow.workflow_factory import WorkflowFactory


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_storage():
    """Create mock TaskStorage."""
    storage = MagicMock()
    storage.get_tasks.return_value = []
    return storage


@pytest.fixture
def mock_config():
    """Create mock ExperimentConfig."""
    config = MagicMock()
    config.output_dir = "/tmp/test_results"
    return config


@pytest.fixture
def workflow_factory(mock_storage, mock_config):
    """Create WorkflowFactory instance."""
    return WorkflowFactory(storage=mock_storage, config=mock_config)


# ---------------------------------------------------------------------------
# Tests: Initialization
# ---------------------------------------------------------------------------


class TestWorkflowFactoryInitialization:
    """Test WorkflowFactory initialization."""

    def test_init_stores_storage(self, workflow_factory, mock_storage):
        """Test that storage is stored correctly."""
        assert workflow_factory.storage is mock_storage

    def test_init_stores_config(self, workflow_factory, mock_config):
        """Test that config is stored correctly."""
        assert workflow_factory.config is mock_config


# ---------------------------------------------------------------------------
# Tests: create_pre_processor()
# ---------------------------------------------------------------------------


class TestCreatePreProcessor:
    """Test create_pre_processor() component creation."""

    def test_create_pre_processor_returns_instance(self, workflow_factory):
        """Test that create_pre_processor returns PreProcessor instance."""
        with patch("rv_experiment.experiment.workflow.workflow_factory.PreProcessor") as mock_pp:
            workflow_factory.create_pre_processor("/tmp/results")
            mock_pp.assert_called_once()

    def test_create_pre_processor_uses_config(self, workflow_factory, mock_config):
        """Test that pre-processor uses config from factory."""
        with patch("rv_experiment.experiment.workflow.workflow_factory.PreProcessor") as mock_pp:
            workflow_factory.create_pre_processor("/tmp/results")
            # Should use config, not results_dir parameter
            call_args = mock_pp.call_args[0][0]
            assert call_args is mock_config

    def test_create_pre_processor_ignores_results_dir_param(self, workflow_factory):
        """Test that results_dir parameter is ignored (uses config)."""
        with patch("rv_experiment.experiment.workflow.workflow_factory.PreProcessor") as mock_pp:
            workflow_factory.create_pre_processor("/ignored/path")
            # Should use config.output_dir
            assert mock_pp.called


# ---------------------------------------------------------------------------
# Tests: create_execution_controller()
# ---------------------------------------------------------------------------


class TestCreateExecutionController:
    """Test create_execution_controller() component creation."""

    def test_create_execution_controller_returns_instance(self, workflow_factory):
        """Test that create_execution_controller returns ExecutionController instance."""
        with patch("rv_experiment.experiment.workflow.workflow_factory.ExecutionController") as mock_ec:
            workflow_factory.create_execution_controller()
            mock_ec.assert_called_once()

    def test_create_execution_controller_uses_config(self, workflow_factory, mock_config):
        """Test that execution controller uses config from factory."""
        with patch("rv_experiment.experiment.workflow.workflow_factory.ExecutionController") as mock_ec:
            workflow_factory.create_execution_controller()
            call_args = mock_ec.call_args[0][0]
            assert call_args is mock_config

    def test_create_execution_controller_no_params(self, workflow_factory, mock_config):
        """Test that execution controller requires no additional params."""
        with patch("rv_experiment.experiment.workflow.workflow_factory.ExecutionController") as mock_ec:
            workflow_factory.create_execution_controller()
            # Controller is called with config from factory
            assert mock_ec.called
            assert mock_ec.call_args[0][0] is mock_config


# ---------------------------------------------------------------------------
# Tests: create_post_processor()
# ---------------------------------------------------------------------------


class TestCreatePostProcessor:
    """Test create_post_processor() component creation."""

    def test_create_post_processor_returns_instance(self, workflow_factory):
        """Test that create_post_processor returns PostProcessor instance."""
        with patch("rv_experiment.experiment.workflow.workflow_factory.PostProcessor") as mock_pp:
            workflow_factory.create_post_processor("/tmp/results")
            mock_pp.assert_called_once()

    def test_create_post_processor_uses_config_output_dir(self, workflow_factory, mock_config):
        """Test that post-processor uses config.output_dir."""
        with patch("rv_experiment.experiment.workflow.workflow_factory.PostProcessor") as mock_pp:
            workflow_factory.create_post_processor("/tmp/results")
            # Should use config.output_dir, not parameter
            call_args = mock_pp.call_args[0][0]
            assert call_args == mock_config.output_dir

    def test_create_post_processor_ignores_param(self, workflow_factory):
        """Test that results_dir parameter is ignored."""
        with patch("rv_experiment.experiment.workflow.workflow_factory.PostProcessor") as mock_pp:
            workflow_factory.create_post_processor("/ignored/path")
            # Should use config.output_dir
            call_args = mock_pp.call_args[0][0]
            assert call_args == "/tmp/test_results"


# ---------------------------------------------------------------------------
# Tests: create_result_manager()
# ---------------------------------------------------------------------------


class TestCreateResultManager:
    """Test create_result_manager() component creation."""

    def test_create_result_manager_returns_instance(self, workflow_factory):
        """Test that create_result_manager returns ResultManager instance."""
        with patch("rv_experiment.experiment.workflow.workflow_factory.ResultManager") as mock_rm:
            workflow_factory.create_result_manager("/tmp/results")
            mock_rm.assert_called_once()

    def test_create_result_manager_uses_config_output_dir(self, workflow_factory, mock_config):
        """Test that result manager uses config.output_dir."""
        with patch("rv_experiment.experiment.workflow.workflow_factory.ResultManager") as mock_rm:
            workflow_factory.create_result_manager("/tmp/results")
            call_args = mock_rm.call_args[0]
            assert call_args[0] == mock_config.output_dir

    def test_create_result_manager_uses_storage(self, workflow_factory, mock_storage):
        """Test that result manager uses storage from factory."""
        with patch("rv_experiment.experiment.workflow.workflow_factory.ResultManager") as mock_rm:
            workflow_factory.create_result_manager("/tmp/results")
            call_args = mock_rm.call_args[0]
            assert call_args[1] is mock_storage

    def test_create_result_manager_ignores_param(self, workflow_factory):
        """Test that results_dir parameter is ignored."""
        with patch("rv_experiment.experiment.workflow.workflow_factory.ResultManager") as mock_rm:
            workflow_factory.create_result_manager("/ignored/path")
            # Should use config.output_dir
            call_args = mock_rm.call_args[0]
            assert call_args[0] == "/tmp/test_results"
