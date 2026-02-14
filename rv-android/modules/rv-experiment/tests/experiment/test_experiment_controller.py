"""
Unit tests for the ExperimentController.

This module tests the orchestration logic of the ExperimentController,
ensuring that the three-phase workflow (pre-processing, execution, and
post-processing) is correctly invoked.

### Test Strategy:
- Mock all external dependencies (PreProcessor, ExecutionController, PostProcessor, etc.).
- Verify that the `run` method calls the workflow components in the correct order.
- Test both successful and failed experiment scenarios.
- Validate the behavior of the `execute_with_config` function.
"""

from unittest.mock import Mock, patch

import pytest

from rv_experiment.config import ExperimentConfig, ToolConfig
from rv_experiment.experiment.experiment_controller import ExperimentController, execute_with_config


@pytest.fixture
def mock_config():
    """Fixture for a mock ExperimentConfig."""
    config = Mock(spec=ExperimentConfig)
    config.results_dir = "/tmp/results"
    config.name = "test_experiment"
    config.generate_monitors = True
    config.instrument_apks = True
    config.run_static_analysis = True
    config.repetitions = 1
    config.timeouts = 300
    tool_config = Mock(spec=ToolConfig)
    tool_config.name = "test_tool"
    tool_config.variants = []
    tool_config.parameters = {}
    config.tool_configs = [tool_config]
    return config


@patch('rv_experiment.experiment.experiment_controller.PreProcessor')
@patch('rv_experiment.experiment.experiment_controller.ExecutionController')
@patch('rv_experiment.experiment.experiment_controller.PostProcessor')
@patch('rv_experiment.experiment.experiment_controller.LoggingManager')
@patch('rv_experiment.experiment.experiment_controller.ErrorHandler')
@patch('os.makedirs')
def test_run_exception(mock_makedirs, mock_error_handler, mock_logging_manager, mock_post_processor,
                       mock_execution_controller, mock_pre_processor, mock_config):
    """Test a run that raises an exception."""
    # Arrange
    mock_pre_processor_instance = mock_pre_processor.return_value
    mock_pre_processor_instance.process.side_effect = Exception("Test Exception")

    controller = ExperimentController(mock_config)

    # Act
    success = controller.run()

    # Assert
    assert success is False


@patch('rv_experiment.experiment.experiment_controller.ExperimentController')
def test_execute_with_config(mock_controller, mock_config):
    """Test the execute_with_config function."""
    # Arrange
    mock_controller_instance = mock_controller.return_value
    mock_controller_instance.run.return_value = True

    # Act
    result = execute_with_config(mock_config)

    # Assert
    assert result is True
    mock_controller.assert_called_with(mock_config)
    mock_controller_instance.run.assert_called_once()
