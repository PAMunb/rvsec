# tests/experiment/test_experiment_controller.py
from unittest.mock import MagicMock, patch

import pytest

from rvandroid.experiment.event.bus import EventBus, EventType
from rvandroid.experiment.experiment_controller import ExperimentController
from rvandroid.experiment.task.task_storage import TaskStorage
from rvandroid.experiment.workflow.execution_controller import ExecutionController
from rvandroid.experiment.workflow.post_processor import PostProcessor
from rvandroid.experiment.workflow.pre_processor import PreProcessor
from rvandroid.experiment.workflow.result_manager import ResultManager
from rvandroid.experiment.workflow.workflow_factory import WorkflowFactory


class TestExperimentController:
    """Tests for the ExperimentController class."""

    @pytest.fixture
    def mock_event_bus(self):
        """Fixture for mocked EventBus."""
        mock_bus = MagicMock(spec=EventBus)
        return mock_bus

    @pytest.fixture
    def mock_workflow_factory(self):
        """Fixture for mocked WorkflowFactory."""
        mock_factory = MagicMock(spec=WorkflowFactory)
        mock_factory.create_pre_processor.return_value = MagicMock(spec=PreProcessor)
        mock_factory.create_execution_controller.return_value = MagicMock(spec=ExecutionController)
        mock_factory.create_post_processor.return_value = MagicMock(spec=PostProcessor)
        mock_factory.create_result_manager.return_value = MagicMock(spec=ResultManager)
        return mock_factory

    @pytest.fixture
    def mock_task_storage(self):
        """Fixture for mocked TaskStorage."""
        mock_storage = MagicMock(spec=TaskStorage)
        return mock_storage

    @pytest.fixture
    def mock_logging_manager(self):
        """Fixture for mocked LoggingManager."""
        mock_manager = MagicMock()
        mock_logger = MagicMock()
        mock_manager.get_logger.return_value = mock_logger
        return mock_manager

    @pytest.fixture
    def mock_tool(self):
        """Fixture for a mock tool."""
        mock_tool = MagicMock()
        mock_tool.name = "mock_tool"
        return mock_tool

    @patch('rvandroid.experiment.experiment_controller.EventBus')
    @patch('rvandroid.experiment.experiment_controller.LoggingManager')
    @patch('rvandroid.experiment.experiment_controller.WorkflowFactory')
    @patch('rvandroid.experiment.experiment_controller.TaskStorage')
    @patch('rvandroid.experiment.experiment_controller.os.makedirs')
    def test_initialization(self, mock_makedirs, mock_task_storage_cls,
                            mock_factory_cls, mock_logging_manager_cls,
                            mock_event_bus_cls):
        """Test the initialization of ExperimentController."""
        # Setup mocks
        mock_event_bus = MagicMock()
        mock_event_bus_cls.get_instance.return_value = mock_event_bus

        mock_logging_manager = MagicMock()
        mock_logger = MagicMock()
        mock_logging_manager.get_logger.return_value = mock_logger
        mock_logging_manager_cls.get_instance.return_value = mock_logging_manager

        mock_factory = MagicMock()
        mock_factory_cls.return_value = mock_factory
        mock_factory.create_pre_processor.return_value = MagicMock(spec=PreProcessor)
        mock_factory.create_execution_controller.return_value = MagicMock(spec=ExecutionController)
        mock_factory.create_post_processor.return_value = MagicMock(spec=PostProcessor)
        mock_factory.create_result_manager.return_value = MagicMock(spec=ResultManager)

        mock_task_storage = MagicMock()
        mock_task_storage_cls.return_value = mock_task_storage

        # Execute
        controller = ExperimentController()

        # Verify
        assert controller.event_bus == mock_event_bus
        assert mock_makedirs.called
        assert mock_logging_manager.setup_file_logging.called
        assert mock_task_storage_cls.called
        assert mock_factory_cls.called

        # Verify workflow components were created
        assert controller.pre_processor is not None
        assert controller.execution_controller is not None
        assert controller.post_processor is not None
        assert controller.result_manager is not None

        # Verify experiment_start was logged
        assert mock_logger.experiment_start.called

    @patch('rvandroid.experiment.experiment_controller.EventBus')
    @patch('rvandroid.experiment.experiment_controller.LoggingManager')
    @patch('rvandroid.experiment.experiment_controller.TaskStorage')
    @patch('rvandroid.experiment.experiment_controller.os.makedirs')
    def test_setup_event_handlers(self, mock_makedirs, mock_task_storage_cls,
                                  mock_logging_manager_cls, mock_event_bus_cls):
        """Test the event handler setup."""
        # Setup mocks
        mock_event_bus = MagicMock()
        mock_event_bus_cls.get_instance.return_value = mock_event_bus

        mock_logging_manager = MagicMock()
        mock_logging_manager_cls.get_instance.return_value = mock_logging_manager

        # Execute
        controller = ExperimentController()

        # Verify
        assert mock_event_bus.subscribe.call_count == 4

        # Check that handlers were registered for the expected event types
        event_types = [call_args[0][0] for call_args in mock_event_bus.subscribe.call_args_list]
        assert EventType.EXPERIMENT_STARTED in event_types
        assert EventType.EXPERIMENT_COMPLETED in event_types
        assert EventType.TASK_STARTED in event_types
        assert EventType.TASK_FAILED in event_types

    @patch('rvandroid.experiment.experiment_controller.EventBus')
    @patch('rvandroid.experiment.experiment_controller.LoggingManager')
    @patch('rvandroid.experiment.experiment_controller.os.makedirs')
    def test_execute_with_all_phases(self, mock_makedirs, mock_logging_manager_cls,
                                     mock_event_bus_cls, mock_tool):
        """Test execution with all phases enabled."""
        # Setup
        controller = ExperimentController()

        # Mock components
        controller.pre_processor = MagicMock()
        controller.pre_processor.get_instrumented_apks.return_value = [MagicMock()]

        controller.execution_controller = MagicMock()
        controller.post_processor = MagicMock()
        controller.result_manager = MagicMock()
        controller.event_bus = MagicMock()
        controller.logger = MagicMock()

        # Execute
        controller.execute(
            repetitions=2,
            timeouts=[30, 60],
            tools=[mock_tool],
            generate_monitors=True,
            instrument=True,
            static_analysis=True,
            skip_experiment=False,
            no_window=False
        )

        # Verify
        controller.pre_processor.process.assert_called_once_with(True, True, True)
        controller.pre_processor.get_instrumented_apks.assert_called_once()
        controller.execution_controller.setup.assert_called_once()
        controller.execution_controller.run.assert_called_once()
        controller.post_processor.process.assert_called_once()
        controller.result_manager.generate_reports.assert_called_once()

        # Verify events
        assert controller.event_bus.publish_experiment_event.call_count == 2

        # Called with EXPERIMENT_STARTED
        controller.event_bus.publish_experiment_event.assert_any_call(
            EventType.EXPERIMENT_STARTED,
            experiment_id=controller.experiment_id,
            message="Starting experiment execution",
            source="ExperimentController"
        )

        # Called with EXPERIMENT_COMPLETED
        controller.event_bus.publish_experiment_event.assert_any_call(
            EventType.EXPERIMENT_COMPLETED,
            experiment_id=controller.experiment_id,
            message="Experiment execution completed",
            source="ExperimentController"
        )

    @patch('rvandroid.experiment.experiment_controller.EventBus')
    @patch('rvandroid.experiment.experiment_controller.LoggingManager')
    @patch('rvandroid.experiment.experiment_controller.os.makedirs')
    def test_execute_skip_experiment(self, mock_makedirs, mock_logging_manager_cls,
                                     mock_event_bus_cls, mock_tool):
        """Test execution with skip_experiment=True."""
        # Setup
        controller = ExperimentController()

        # Mock components
        controller.pre_processor = MagicMock()
        controller.execution_controller = MagicMock()
        controller.post_processor = MagicMock()
        controller.result_manager = MagicMock()
        controller.event_bus = MagicMock()
        controller.logger = MagicMock()

        # Execute
        controller.execute(
            repetitions=2,
            timeouts=[30, 60],
            tools=[mock_tool],
            generate_monitors=True,
            instrument=True,
            static_analysis=True,
            skip_experiment=True,  # Skip the experiment execution
            no_window=False
        )

        # Verify
        controller.pre_processor.process.assert_called_once_with(True, True, True)

        # These should not be called when skip_experiment is True
        controller.execution_controller.setup.assert_not_called()
        controller.execution_controller.run.assert_not_called()
        controller.post_processor.process.assert_not_called()
        controller.result_manager.generate_reports.assert_not_called()

        # Only the STARTED and COMPLETED events should be published
        assert controller.event_bus.publish_experiment_event.call_count == 2

    # @patch('rvandroid.experiment.experiment_controller.EventBus')
    # @patch('rvandroid.experiment.experiment_controller.LoggingManager')
    # @patch('rvandroid.experiment.experiment_controller.os.makedirs')
    # @patch('rvandroid.experiment.experiment_controller.os.path.exists')
    # @patch('builtins.open', new_callable=MagicMock)
    # def test_resume_from_memory(self, mock_open, mock_path_exists,
    #                             mock_makedirs, mock_logging_manager_cls,
    #                             mock_event_bus_cls):
    #     """Test resuming experiment from a memory file."""
    #     # Setup
    #     controller = ExperimentController()
    #
    #     controller.logger = MagicMock()
    #     controller.task_storage = MagicMock()
    #     controller.execution_controller = MagicMock()
    #
    #     # Set up the exists check to return True
    #     mock_path_exists.return_value = True
    #
    #     # Set up task storage to load successfully
    #     controller.task_storage.load.return_value = True
    #     controller.task_storage.get_tasks.return_value = [MagicMock(), MagicMock()]
    #
    #     # Execute
    #     memory_file = "/path/to/memory_file.json"
    #     controller._resume_from_memory(memory_file)
    #
    #     # Verify
    #     assert controller.task_storage.load.called
    #     assert controller.execution_controller.update_storage.called
    #
    #     # Check that the success message was logged
    #     success_message = f"Successfully resumed experiment with {len(controller.task_storage.get_tasks())} tasks"
    #
    #     # Updated approach to check if the message was logged
    #     found_message = False
    #     for call in controller.logger.info.call_args_list:
    #         if call[0][0] == success_message:
    #             found_message = True
    #             break
    #     assert found_message, f"Expected log message not found: {success_message}"

    @patch('rvandroid.experiment.experiment_controller.EventBus')
    @patch('rvandroid.experiment.experiment_controller.LoggingManager')
    @patch('rvandroid.experiment.experiment_controller.os.makedirs')
    @patch('rvandroid.experiment.experiment_controller.os.path.exists')
    def test_resume_from_memory_file_not_found(self, mock_path_exists,
                                               mock_makedirs, mock_logging_manager_cls,
                                               mock_event_bus_cls):
        """Test resuming experiment when memory file doesn't exist."""
        # Setup
        controller = ExperimentController()

        controller.logger = MagicMock()

        # Set up the exists check to return False
        mock_path_exists.return_value = False

        # Execute
        memory_file = "/path/to/nonexistent_file.json"
        controller._resume_from_memory(memory_file)

        # Verify - check that error was logged with the appropriate message
        assert controller.logger.error.called

        # Look through all error calls to find one with the right message
        found_error = False
        for call in controller.logger.error.call_args_list:
            if "Memory file not found" in call[0][0]:
                found_error = True
                break
        assert found_error, "Expected error message not found"

    # @patch('rvandroid.experiment.experiment_controller.EventBus')
    # @patch('rvandroid.experiment.experiment_controller.LoggingManager')
    # @patch('rvandroid.experiment.experiment_controller.os.makedirs')
    # @patch('rvandroid.experiment.experiment_controller.os.path.exists')
    # def test_resume_from_memory_load_failure(self, mock_path_exists,
    #                                          mock_makedirs, mock_logging_manager_cls,
    #                                          mock_event_bus_cls):
    #     """Test resuming experiment when memory file loading fails."""
    #     # Setup
    #     controller = ExperimentController()
    #
    #     controller.logger = MagicMock()
    #     controller.task_storage = MagicMock()
    #
    #     # Set up the exists check to return True
    #     mock_path_exists.return_value = True
    #
    #     # Set up task storage to fail loading
    #     controller.task_storage.load.return_value = False
    #
    #     # Execute
    #     memory_file = "/path/to/broken_file.json"
    #     controller._resume_from_memory(memory_file)
    #
    #     # Verify
    #     assert controller.task_storage.load.called
    #     assert controller.logger.error.called
    #
    #     # Look through all error calls to find one with the right message
    #     found_error = False
    #     for call in controller.logger.error.call_args_list:
    #         if "Failed to load tasks" in call[0][0]:
    #             found_error = True
    #             break
    #     assert found_error, "Expected error message not found"
    #
    # @patch('rvandroid.experiment.experiment_controller.EventBus')
    # @patch('rvandroid.experiment.experiment_controller.LoggingManager')
    # @patch('rvandroid.experiment.experiment_controller.os.makedirs')
    # @patch('rvandroid.experiment.experiment_controller.os.path.exists')
    # def test_resume_from_memory_json_error(self, mock_path_exists,
    #                                        mock_makedirs, mock_logging_manager_cls,
    #                                        mock_event_bus_cls):
    #     """Test resuming experiment when memory file contains invalid JSON."""
    #     # Setup
    #     controller = ExperimentController()
    #
    #     controller.logger = MagicMock()
    #     controller.task_storage = MagicMock()
    #
    #     # Set up the exists check to return True
    #     mock_path_exists.return_value = True
    #
    #     # Set up task storage to raise a JSONDecodeError
    #     import json
    #     controller.task_storage.load.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
    #
    #     # Execute
    #     memory_file = "/path/to/invalid_json.json"
    #     controller._resume_from_memory(memory_file)
    #
    #     # Verify
    #     assert controller.task_storage.load.called
    #     assert controller.logger.error.called
    #
    #     # Look through all error calls to find one with the right message
    #     found_error = False
    #     for call in controller.logger.error.call_args_list:
    #         if "invalid json" in call[0][0].lower():
    #             found_error = True
    #             break
    #     assert found_error, "Expected error message not found"


@pytest.mark.skip("Requires ToolRegistry which may not be imported in experiment_controller")
class TestExecuteFunction:
    """Tests for the 'execute' function."""

    @patch('rvandroid.experiment.experiment_controller.Configuration')
    @patch('rvandroid.experiment.experiment_controller.ExperimentController')
    @patch('rvandroid.experiment.experiment_controller.LoggingManager')
    def test_execute_function_with_provided_tools(self, mock_logging_manager_cls,
                                                  mock_exp_controller_cls,
                                                  mock_configuration_cls):
        """Test execute function with provided tools."""
        from rvandroid.experiment.experiment_controller import execute

        # Setup mocks
        mock_logging_manager = MagicMock()
        mock_logger = MagicMock()
        mock_logging_manager.get_logger.return_value = mock_logger
        mock_logging_manager_cls.get_instance.return_value = mock_logging_manager

        mock_config = MagicMock()
        mock_config.get_int.return_value = 1
        mock_config.get_list.side_effect = lambda key, default: [60] if key == "timeouts" else []
        mock_config.get_str.return_value = ""
        mock_config.get_bool.return_value = True
        mock_configuration_cls.get_instance.return_value = mock_config

        mock_exp_controller = MagicMock()
        mock_exp_controller_cls.return_value = mock_exp_controller

        # Setup tools
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"

        # Execute with explicitly provided tools
        execute(tools=[mock_tool])

        # Verify
        mock_exp_controller.execute.assert_called_once()

        # Check that we're using the provided tools
        call_args = mock_exp_controller.execute.call_args[1]
        assert call_args["tools"] == [mock_tool]
