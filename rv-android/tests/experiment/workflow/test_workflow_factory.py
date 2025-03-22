# tests/experiment/workflow/test_workflow_factory.py
"""
Unit tests for the WorkflowFactory component in the experiment workflow.
"""
import pytest
from unittest.mock import MagicMock, patch

from rvandroid.experiment.event_system import EventBus
from rvandroid.experiment.task_storage import TaskStorage
from rvandroid.experiment.workflow.workflow_factory import WorkflowFactory
from rvandroid.experiment.workflow.pre_processor import PreProcessor
from rvandroid.experiment.workflow.execution_controller import ExecutionController
from rvandroid.experiment.workflow.post_processor import PostProcessor
from rvandroid.experiment.workflow.result_manager import ResultManager


@pytest.fixture
def setup_environment():
    """Set up common test environment."""
    # Mock storage with storage_file attribute
    storage = MagicMock(spec=TaskStorage)
    storage.storage_file = "/tmp/test_storage.json"

    # Mock event bus
    event_bus = MagicMock(spec=EventBus)

    # Create workflow factory
    factory = WorkflowFactory(storage, event_bus)

    # Return all needed objects
    return {
        'factory': factory,
        'storage': storage,
        'event_bus': event_bus
    }


def test_create_pre_processor(setup_environment):
    """Test creation of pre processor component."""
    env = setup_environment
    factory = env['factory']
    event_bus = env['event_bus']

    # Test with actual results directory
    results_dir = "/tmp/test_results"

    # Create pre processor
    pre_processor = factory.create_pre_processor(results_dir)

    # Verify it's the correct type
    assert isinstance(pre_processor, PreProcessor)

    # Verify it was initialized with correct parameters
    assert pre_processor.results_dir == results_dir
    assert pre_processor.event_bus == event_bus


def test_create_execution_controller(setup_environment):
    """Test creation of execution controller component."""
    env = setup_environment
    factory = env['factory']
    storage = env['storage']
    event_bus = env['event_bus']

    # Create execution controller with patched ExecutionManager
    with patch('rvandroid.experiment.workflow.execution_controller.ExecutionManager') as mock_manager_class:
        # Configure the mock
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        # Create execution controller
        execution_controller = factory.create_execution_controller()

        # Verify it's the correct type
        assert isinstance(execution_controller, ExecutionController)

        # Verify it was initialized with correct parameters
        assert execution_controller.task_storage == storage
        assert execution_controller.event_bus == event_bus

        # Verify ExecutionManager was created with correct parameters
        mock_manager_class.assert_called_once_with(storage, event_bus)


def test_create_post_processor(setup_environment):
    """Test creation of post processor component."""
    env = setup_environment
    factory = env['factory']
    event_bus = env['event_bus']

    # Test with actual results directory
    results_dir = "/tmp/test_results"

    # Mock the execution controller creation
    mock_execution_controller = MagicMock()
    with patch.object(factory, 'create_execution_controller',
                      return_value=mock_execution_controller):
        # Create post processor
        post_processor = factory.create_post_processor(results_dir)

        # Verify it's the correct type
        assert isinstance(post_processor, PostProcessor)

        # Verify it was initialized with correct parameters
        assert post_processor.results_dir == results_dir
        assert post_processor.event_bus == event_bus
        assert post_processor.execution_controller == mock_execution_controller


def test_create_result_manager(setup_environment):
    """Test creation of result manager component."""
    env = setup_environment
    factory = env['factory']
    event_bus = env['event_bus']

    # Test with actual results directory
    results_dir = "/tmp/test_results"

    # Create result manager
    result_manager = factory.create_result_manager(results_dir)

    # Verify it's the correct type
    assert isinstance(result_manager, ResultManager)

    # Verify it was initialized with correct parameters
    assert result_manager.results_dir == results_dir
    assert result_manager.event_bus == event_bus


def test_factory_component_relationships(setup_environment):
    """Test relationships between components created by the factory."""
    env = setup_environment
    factory = env['factory']

    # Test with actual results directory
    results_dir = "/tmp/test_results"

    # Create components - patch deeper dependencies to avoid actual instantiation
    with patch('rvandroid.experiment.workflow.execution_controller.ExecutionManager'):
        pre_processor = factory.create_pre_processor(results_dir)
        execution_controller = factory.create_execution_controller()

        # For post_processor, we need to use the actual execution_controller
        # so we don't need to patch create_execution_controller
        post_processor = factory.create_post_processor(results_dir)
        result_manager = factory.create_result_manager(results_dir)

        # Verify each component has the same event bus
        assert pre_processor.event_bus == execution_controller.event_bus
        assert execution_controller.event_bus == post_processor.event_bus
        assert post_processor.event_bus == result_manager.event_bus
