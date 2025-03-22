# rvandroid/experiment_workflow/workflow_factory.py
"""
Factory for creating experiment workflow components.
Enables centralized component creation and configuration.
"""
from rvandroid.experiment.event_system import EventBus
from rvandroid.experiment.task_storage import TaskStorage
from rvandroid.experiment.workflow.execution_controller import ExecutionController
from rvandroid.experiment.workflow.post_processor import PostProcessor
from rvandroid.experiment.workflow.pre_processor import PreProcessor
from rvandroid.experiment.workflow.result_manager import ResultManager


class WorkflowFactory:
    """
    A factory for creating and configuring experiment workflow components.

    ### Architectural Decisions:
    - Implements the factory pattern for consistent component creation
    - Centralizes component configuration and dependency injection
    - Ensures proper component initialization and integration
    - Provides a clean interface for component creation

    ### Role in the System:
    - Creates properly configured workflow components
    - Manages component dependencies and relationships
    - Ensures consistent component initialization
    - Facilitates component testing and reuse
    """

    def __init__(self, storage: TaskStorage, event_bus: EventBus):
        """
        Initialize the workflow factory.

        Args:
            storage: Task storage for the experiment
            event_bus: Event bus for component communication
        """
        self.storage = storage
        self.event_bus = event_bus

    def create_pre_processor(self, results_dir: str) -> PreProcessor:
        """
        Create a pre-processor component.

        Args:
            results_dir: Directory for experiment results

        Returns:
            Configured PreProcessor instance
        """
        return PreProcessor(results_dir, self.event_bus)

    def create_execution_controller(self) -> ExecutionController:
        """
        Create an execution controller component.

        Returns:
            Configured ExecutionController instance
        """
        return ExecutionController(self.storage, self.event_bus)

    def create_post_processor(self, results_dir: str) -> PostProcessor:
        """
        Create a post-processor component.

        Args:
            results_dir: Directory for experiment results

        Returns:
            Configured PostProcessor instance
        """
        execution_controller = self.create_execution_controller()
        return PostProcessor(results_dir, self.event_bus, execution_controller)

    def create_result_manager(self, results_dir: str) -> ResultManager:
        """
        Create a result manager component.

        Args:
            results_dir: Directory for experiment results

        Returns:
            Configured ResultManager instance
        """
        return ResultManager(results_dir, self.event_bus)
