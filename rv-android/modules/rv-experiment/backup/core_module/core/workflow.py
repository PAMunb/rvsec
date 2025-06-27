# rvandroid/experiment/core/workflow.py
"""
Base workflow implementation for the unified execution framework.

This module provides the BaseWorkflow class, which serves as a foundation for
all workflow implementations. It implements the core workflow lifecycle and
provides hooks for customization by subclasses.
"""

import threading
from collections import defaultdict
from typing import Dict, List, Optional, Callable, Set

from rv_android_core.util.logging.constants import LOG_START, LOG_COMPLETE, LOG_ERROR
from rv_android_core.util.logging.manager import LoggingManager
from rv_experiment.experiment.core.interfaces import (
    IWorkflow,
    IExecutionContext,
    IPhaseProcessor,
    ExecutionPhase
)
from rv_android_core.event import (
    EventBus,
    EventType
)


class BaseWorkflow(IWorkflow):
    """
    Base implementation of the workflow interface.
    
    ### Architectural Decisions:
    - Implements a phase-based workflow execution model
    - Provides comprehensive lifecycle management and error handling
    - Supports flexible processor registration and discovery
    - Enables complex workflow composition and extension
    
    ### Role in the System:
    - Serves as the foundation for all workflow implementations
    - Manages the workflow lifecycle and phase execution
    - Coordinates phase processors and their execution
    - Provides comprehensive error handling and recovery
    """

    def __init__(self, workflow_name: str, context: IExecutionContext):
        """
        Initialize the workflow.
        
        Args:
            workflow_name: Name of the workflow
            context: Execution context
        """
        self._name = workflow_name
        self._context = context
        self._processors: Dict[str, IPhaseProcessor] = {}
        self._phase_hooks: Dict[ExecutionPhase, List[Callable[[IExecutionContext], None]]] = defaultdict(list)
        self._lock = threading.RLock()
        self._executed_phases: Set[ExecutionPhase] = set()

        # Initialize logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            'experiment.core.workflow',
            {
                'experiment_id': context.experiment_id,
                'workflow': workflow_name
            }
        )

    @property
    def name(self) -> str:
        """
        Get the workflow name.
        
        Returns:
            Workflow name
        """
        return self._name

    @property
    def context(self) -> IExecutionContext:
        """
        Get the workflow execution context.
        
        Returns:
            Execution context
        """
        return self._context

    def register_processor(self, processor: IPhaseProcessor) -> None:
        """
        Register a phase processor with the workflow.
        
        Args:
            processor: Processor to register
        """
        with self._lock:
            self._processors[processor.name] = processor
            self.logger.debug(
                f"Registered processor: {processor.name} for phases: {[p.name for p in processor.supported_phases]}")

    def get_processors(self) -> List[IPhaseProcessor]:
        """
        Get all registered processors.
        
        Returns:
            List of registered processors
        """
        with self._lock:
            return list(self._processors.values())

    def get_processors_for_phase(self, phase: ExecutionPhase) -> List[IPhaseProcessor]:
        """
        Get processors that can handle the specified phase.
        
        Args:
            phase: Phase to find processors for
            
        Returns:
            List of processors that can handle the phase
        """
        with self._lock:
            return [p for p in self._processors.values() if p.can_process(phase)]

    def execute(self, phases: Optional[List[ExecutionPhase]] = None) -> bool:
        """
        Execute the workflow with the specified phases.
        
        Args:
            phases: Phases to execute (defaults to all phases in order)
            
        Returns:
            True if execution was successful, False otherwise
        """
        # If no phases are specified, use all phases in order
        if phases is None:
            phases = list(ExecutionPhase)

        # Publish workflow started event
        self._context.event_bus.publish_workflow_event(
            event_type=EventType.WORKFLOW_STARTED,
            workflow_id=self._name,
            experiment_id=self._context.experiment_id,
            source="BaseWorkflow",
            channel=EventBus.LIFECYCLE_CHANNEL
        )

        with self.logger.with_context(workflow=self._name):
            self.logger.info(LOG_START.format(phase=f"Workflow {self._name}"))

            success = True

            # Execute each phase in sequence
            for phase in phases:
                phase_success = self.execute_phase(phase)

                if not phase_success:
                    success = False
                    # Workflow can decide to continue or break based on failure
                    if not self._should_continue_after_failure(phase):
                        self.logger.warning(f"Stopping workflow execution after failure in phase: {phase.name}")
                        break

            # Publish workflow completion event
            if success:
                self._context.event_bus.publish_workflow_event(
                    event_type=EventType.WORKFLOW_COMPLETED,
                    workflow_id=self._name,
                    experiment_id=self._context.experiment_id,
                    source="BaseWorkflow",
                    channel=EventBus.LIFECYCLE_CHANNEL
                )
                self.logger.info(LOG_COMPLETE.format(phase=f"Workflow {self._name}"))
            else:
                self._context.event_bus.publish_workflow_event(
                    event_type=EventType.WORKFLOW_FAILED,
                    workflow_id=self._name,
                    experiment_id=self._context.experiment_id,
                    details={"executed_phases": [p.name for p in self._executed_phases]},
                    source="BaseWorkflow",
                    channel=EventBus.LIFECYCLE_CHANNEL
                )
                self.logger.error(LOG_ERROR.format(
                    phase=f"Workflow {self._name}",
                    error="One or more phases failed"
                ))

            return success

    def execute_phase(self, phase: ExecutionPhase) -> bool:
        """
        Execute a specific phase of the workflow.
        
        Args:
            phase: Phase to execute
            
        Returns:
            True if execution was successful, False otherwise
        """
        with self._lock:
            processors = self.get_processors_for_phase(phase)

            if not processors:
                self.logger.warning(f"No processors found for phase: {phase.name}")
                return True  # Not having processors for a phase is not considered a failure

            # Publish phase started event
            self._context.event_bus.publish_workflow_event(
                event_type=EventType.PHASE_STARTED,
                workflow_id=self._name,
                experiment_id=self._context.experiment_id,
                details={"phase": phase.name},
                source="BaseWorkflow",
                channel=EventBus.LIFECYCLE_CHANNEL
            )

            with self.logger.with_context(workflow=self._name, phase=phase.name):
                self.logger.info(LOG_START.format(phase=f"Phase {phase.name}"))

                # Execute pre-phase hooks
                self._execute_hooks(phase)

                success = True

                # Execute each processor
                for processor in processors:
                    try:
                        processor_success = processor.process(phase, self._context)

                        if not processor_success:
                            self.logger.error(LOG_ERROR.format(
                                phase=f"Processor {processor.name}",
                                error="Processing failed"
                            ))
                            success = False

                    except Exception as e:
                        self.logger.error(LOG_ERROR.format(
                            phase=f"Processor {processor.name}",
                            error=str(e)
                        ))
                        success = False

                # Track executed phases
                self._executed_phases.add(phase)

                # Publish phase completion event
                if success:
                    self._context.event_bus.publish_workflow_event(
                        event_type=EventType.PHASE_COMPLETED,
                        workflow_id=self._name,
                        experiment_id=self._context.experiment_id,
                        details={"phase": phase.name},
                        source="BaseWorkflow",
                        channel=EventBus.LIFECYCLE_CHANNEL
                    )
                    self.logger.info(LOG_COMPLETE.format(phase=f"Phase {phase.name}"))
                else:
                    self._context.event_bus.publish_workflow_event(
                        event_type=EventType.PHASE_FAILED,
                        workflow_id=self._name,
                        experiment_id=self._context.experiment_id,
                        details={"phase": phase.name},
                        source="BaseWorkflow",
                        channel=EventBus.LIFECYCLE_CHANNEL
                    )
                    self.logger.error(LOG_ERROR.format(
                        phase=f"Phase {phase.name}",
                        error="Phase execution failed"
                    ))

                return success

    def add_execution_hook(self, phase: ExecutionPhase, hook: Callable[[IExecutionContext], None]) -> None:
        """
        Add a hook to be executed before a specific phase.
        
        Args:
            phase: Phase to hook
            hook: Function to execute
        """
        with self._lock:
            self._phase_hooks[phase].append(hook)

    def _execute_hooks(self, phase: ExecutionPhase) -> None:
        """
        Execute hooks for the specified phase.
        
        Args:
            phase: Phase to execute hooks for
        """
        hooks = self._phase_hooks.get(phase, [])

        for hook in hooks:
            try:
                hook(self._context)
            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    phase=f"Executing hook for phase {phase.name}",
                    error=str(e)
                ))

    def _should_continue_after_failure(self, phase: ExecutionPhase) -> bool:
        """
        Determine if workflow should continue after a phase failure.
        
        This method can be overridden by subclasses to customize behavior.
        
        Args:
            phase: Failed phase
            
        Returns:
            True if workflow should continue, False otherwise
        """
        # Default implementation continues execution
        # except for PREPARATION and STATIC_ANALYSIS phases
        critical_phases = [ExecutionPhase.PREPARATION, ExecutionPhase.STATIC_ANALYSIS]
        return phase not in critical_phases
