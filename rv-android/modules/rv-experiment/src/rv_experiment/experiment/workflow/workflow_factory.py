# rv_experiment/experiment/workflow/workflow_factory.py
"""
Factory centralizing construction of the Requirement "Three-Phase Workflow
(FR15, NFR08)" components: PreProcessor (Phase 1), ExecutionController (Phase 2),
and PostProcessor + ResultManager (Phase 3).

Current state: ExperimentController is the sole orchestrator of the three-phase
workflow, and it instantiates PreProcessor / ExecutionController / PostProcessor
directly in its own __init__ rather than through this factory.

TODO(dead-code): this factory is not on the live orchestration path — it is only
re-exported from this package's __init__.py and exercised by its own unit test.
No production caller constructs a WorkflowFactory. It is a candidate for removal
(P1/P3) pending a separate cleanup change.
"""

from rv_experiment.experiment.workflow.execution_controller import ExecutionController
from rv_experiment.experiment.workflow.post_processor import PostProcessor
from rv_experiment.experiment.workflow.pre_processor import PreProcessor
from rv_experiment.experiment.workflow.result_manager import ResultManager
from rv_platform.storage.task_storage import TaskStorage

if False:  # TYPE_CHECKING
    from rv_experiment.config import ExperimentConfig


class WorkflowFactory:
    """
    Factory for creating and configuring the workflow components of the
    Requirement "Three-Phase Workflow (FR15, NFR08)".

    ### Architectural Decisions:
    - Implements the factory pattern for consistent component creation
    - Centralizes component configuration and dependency injection
    - Provides a clean interface for component creation

    ### Role in the System:
    - Builds the components of each workflow phase: PreProcessor (Phase 1),
      ExecutionController (Phase 2), PostProcessor + ResultManager (Phase 3).

    Current state: ExperimentController is the sole orchestrator of the
    three-phase workflow and constructs these components directly in its own
    __init__; it does not route their creation through this factory.
    """

    def __init__(self, storage: TaskStorage, config: "ExperimentConfig"):
        """
        Initialize the workflow factory.

        Args:
            storage: Task storage for the experiment
            config: Experiment configuration for component coordination
        """
        self.storage = storage
        self.config = config

    def create_pre_processor(self, results_dir: str) -> PreProcessor:
        """
        Create the Phase 1 (pre-processing) component of the Three-Phase Workflow.

        Args:
            results_dir: Directory for experiment results (ignored, using config)

        Returns:
            Configured PreProcessor instance
        """
        # Create PreProcessor with direct implementation
        return PreProcessor(self.config)

    def create_execution_controller(self) -> ExecutionController:
        """
        Create the Phase 2 (execution) component of the Three-Phase Workflow.

        Returns:
            Configured ExecutionController instance
        """
        return ExecutionController(self.config)

    def create_post_processor(self, results_dir: str) -> PostProcessor:
        """
        Create the Phase 3 (post-processing) component of the Three-Phase Workflow.

        Builds the PostProcessor with config.output_dir (the "out" directory).

        TODO(INV-EXP-11/INV-EXP-14): this passes config.output_dir ("out"), but
        the Phase 3 outputs (instrument_errors.json, experiment_completion.json)
        MUST live in the results directory per INV-EXP-11 and INV-EXP-14 (flat
        results dir). The live ExperimentController constructs PostProcessor with
        self.results_dir, so there is no runtime impact today; this factory would
        misroute the files if it were ever put on the live path.

        Args:
            results_dir: Directory for experiment results (ignored, using config)

        Returns:
            Configured PostProcessor instance
        """
        return PostProcessor(self.config.output_dir)

    def create_result_manager(self, results_dir: str) -> ResultManager:
        """
        Create the Phase 3 (post-processing) result-manager component of the
        Three-Phase Workflow.

        Builds the ResultManager with config.output_dir (the "out" directory).

        TODO(INV-EXP-11/INV-EXP-14): same misroute as create_post_processor —
        ResultManager writes instrument_errors.json, which INV-EXP-11 requires in
        the results directory (INV-EXP-14 flat results dir), but this passes
        config.output_dir ("out"). No runtime impact today because the live
        ExperimentController wires ResultManager (via PostProcessor) to
        self.results_dir; this factory would misroute it if put on the live path.

        Args:
            results_dir: Directory for experiment results (ignored, using config)

        Returns:
            Configured ResultManager instance
        """
        return ResultManager(self.config.output_dir, self.storage)
