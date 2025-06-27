# rvandroid/experiment_workflow/workflow_factory.py
"""
Factory for creating experiment workflow components.
Enables centralized component creation and configuration.
"""
from rv_android_core.event import EventBus
from rv_experiment.experiment.task.storage import TaskStorage
from rv_experiment.experiment.workflow.execution_controller import ExecutionController
from rv_experiment.experiment.workflow.post_processor import PostProcessor
from rv_experiment.experiment.workflow.pre_processor import PreProcessor
from rv_experiment.experiment.workflow.result_manager import ResultManager

if False:  # TYPE_CHECKING
    from rv_experiment.config import ExperimentConfig


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

    def __init__(self, storage: TaskStorage, event_bus: EventBus, config: 'ExperimentConfig'):
        """
        Initialize the workflow factory.

        Args:
            storage: Task storage for the experiment
            event_bus: Event bus for component communication
            config: Experiment configuration for component coordination
        """
        self.storage = storage
        self.event_bus = event_bus
        self.config = config

    def create_pre_processor(self, results_dir: str) -> PreProcessor:
        """
        Create a pre-processor component.

        Args:
            results_dir: Directory for experiment results (ignored, using config)

        Returns:
            Configured PreProcessor instance
        """
        # Create PreProcessor with direct implementation
        return PreProcessor(self.config, self.event_bus)

    def create_execution_controller(self) -> ExecutionController:
        """
        Create an execution controller component.

        Returns:
            Configured ExecutionController instance
        """
        return ExecutionController(self.storage, self.config, self.event_bus)

    def create_post_processor(self, results_dir: str) -> PostProcessor:
        """
        Create a post-processor component.

        Args:
            results_dir: Directory for experiment results (ignored, using config)

        Returns:
            Configured PostProcessor instance
        """
        execution_controller = self.create_execution_controller()
        result_manager = self.create_result_manager(results_dir)
        return PostProcessor(self.config.output_dir, self.event_bus, execution_controller, result_manager)

    def create_result_manager(self, results_dir: str) -> ResultManager:
        """
        Create a result manager component.

        Args:
            results_dir: Directory for experiment results (ignored, using config)

        Returns:
            Configured ResultManager instance
        """
        return ResultManager(self.config.output_dir, self.storage, self.event_bus)
