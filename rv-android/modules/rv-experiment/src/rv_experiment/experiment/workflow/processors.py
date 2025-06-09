# rvandroid/experiment/workflow/processors.py
"""
Workflow processors for specific workflow phases.

This module provides implementations of workflow components that process
specific phases of a workflow. Each processor is responsible for a specific
set of tasks within the workflow and can be registered with a workflow
to handle those tasks.
"""

import logging
from typing import List, Optional, Set

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_experiment.experiment.core.interfaces import (
    IExecutionContext,
    ExecutionPhase,
    IPhaseProcessor
)
from rv_android_core.event import EventBus, get_event_bus
from rv_experiment.experiment.workflow.components import (
    BaseWorkflowComponent,
    ComponentLifecycle
)


class BasePhaseProcessor(BaseWorkflowComponent, IPhaseProcessor):
    """
    Base implementation of a workflow phase processor.
    
    ### Architectural Decisions:
    - Implements both component and phase processor interfaces
    - Provides lifecycle management through component infrastructure
    - Supports phase-specific processing logic
    - Enables clear separation of concerns between phases
    
    ### Role in the System:
    - Serves as a foundation for phase processor implementations
    - Handles common processor functionality
    - Provides integration with workflow component registry
    - Enables consistent processor behavior across phases
    """

    def __init__(self, processor_id: Optional[str] = None,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 dependencies: Optional[Set[str]] = None,
                 event_bus: Optional[EventBus] = None,
                 supported_phases: Optional[List[ExecutionPhase]] = None):
        """
        Initialize the phase processor.
        
        Args:
            processor_id: Optional processor ID (defaults to class name)
            name: Optional display name (defaults to class name)
            description: Optional description (defaults to class docstring)
            dependencies: Optional set of component dependencies
            event_bus: Optional event bus for communication
            supported_phases: Optional list of supported phases
        """
        super().__init__(
            component_id=processor_id,
            name=name,
            description=description,
            dependencies=dependencies,
            event_bus=event_bus,
            supported_phases=supported_phases or []
        )
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def process(self, phase: ExecutionPhase, context: IExecutionContext) -> bool:
        """
        Process the specified phase with the given context.
        
        Args:
            phase: Phase to process
            context: Execution context
            
        Returns:
            True if processing was successful, False otherwise
        """
        if not self.can_process(phase):
            self.logger.warning(f"Processor {self.name} does not support phase {phase.name}")
            return False

        if self.lifecycle_state != ComponentLifecycle.ACTIVE:
            self.logger.warning(f"Processor {self.name} is not in the ACTIVE state: {self.lifecycle_state}")
            return False

        # Execute the processor for this phase
        return self.execute(phase, context)

    def can_process(self, phase: ExecutionPhase) -> bool:
        """
        Check if this processor can handle the specified phase.
        
        Args:
            phase: Phase to check
            
        Returns:
            True if this processor can handle the phase
        """
        return phase in self.supported_phases


class SetupProcessor(BasePhaseProcessor):
    """
    Processor for the SETUP phase of a workflow.
    
    ### Architectural Decisions:
    - Focuses on workflow initialization and environment setup
    - Separates setup concerns from other phases
    - Implements specific setup logic for experiment execution
    - Enables clear separation of setup procedures
    
    ### Role in the System:
    - Handles initial workflow setup
    - Creates necessary directories and files
    - Initializes experiment resources
    - Prepares the execution environment
    """

    def __init__(self, context: IExecutionContext, event_bus: Optional[EventBus] = None):
        """
        Initialize the setup processor.
        
        Args:
            context: Execution context
            event_bus: Optional event bus for communication
        """
        super().__init__(
            processor_id="SetupProcessor",
            name="Setup Processor",
            description="Processor for experiment setup phase",
            event_bus=event_bus or get_event_bus(),
            supported_phases=[ExecutionPhase.SETUP]
        )
        self.initialize(context)
        self.configure({})
        self.activate()

    def execute(self, phase: ExecutionPhase, context: IExecutionContext) -> bool:
        """
        Execute the setup phase.
        
        Args:
            phase: Phase to execute
            context: Execution context
            
        Returns:
            True if execution was successful, False otherwise
        """
        if phase != ExecutionPhase.SETUP:
            return False

        self.logger.info(f"Executing setup phase for experiment: {context.experiment_id}")

        # Implement setup logic
        try:
            # Create output directories
            import os
            os.makedirs(context.results_dir, exist_ok=True)
            os.makedirs(os.path.join(context.results_dir, "logs"), exist_ok=True)
            os.makedirs(os.path.join(context.results_dir, "reports"), exist_ok=True)
            os.makedirs(os.path.join(context.results_dir, "data"), exist_ok=True)

            # Initialize experiment state
            context.set("experiment.status", "initialized")
            context.set("experiment.start_time", import_module("datetime").datetime.now().isoformat())

            # Record experiment configuration
            if context.has("experiment.config"):
                config = context.get("experiment.config")
                with open(os.path.join(context.results_dir, "experiment_config.json"), "w") as f:
                    import_module("json").dump(config, f, indent=2)

            self.logger.info(f"Setup completed for experiment: {context.experiment_id}")
            return True

        except Exception as e:
            error_handler = ErrorHandler.get_instance()
            error_context = {
                "component": "SetupProcessor",
                "operation": "setup_phase",
                "experiment_id": context.experiment_id,
                "results_dir": context.results_dir
            }
            error_handler.handle_error(e, error_context)
            return False


class StaticAnalysisProcessor(BasePhaseProcessor):
    """
    Processor for the STATIC_ANALYSIS phase of a workflow.
    
    ### Architectural Decisions:
    - Handles all static analysis tasks in a dedicated processor
    - Separates static analysis from dynamic execution
    - Enables flexible static analysis tool integration
    - Facilitates consistent static analysis results storage
    
    ### Role in the System:
    - Executes static analysis of applications
    - Manages static analysis tools and their output
    - Processes static analysis results
    - Provides static analysis data to other phases
    """

    def __init__(self, context: IExecutionContext, event_bus: Optional[EventBus] = None):
        """
        Initialize the static analysis processor.
        
        Args:
            context: Execution context
            event_bus: Optional event bus for communication
        """
        super().__init__(
            processor_id="StaticAnalysisProcessor",
            name="Static Analysis Processor",
            description="Processor for static analysis phase",
            event_bus=event_bus or get_event_bus(),
            supported_phases=[ExecutionPhase.STATIC_ANALYSIS]
        )
        self.initialize(context)
        self.configure({})
        self.activate()

    def execute(self, phase: ExecutionPhase, context: IExecutionContext) -> bool:
        """
        Execute the static analysis phase.
        
        Args:
            phase: Phase to execute
            context: Execution context
            
        Returns:
            True if execution was successful, False otherwise
        """
        if phase != ExecutionPhase.STATIC_ANALYSIS:
            return False

        self.logger.info(f"Executing static analysis phase for experiment: {context.experiment_id}")

        # Implement static analysis logic
        try:
            # Get application data
            app = context.get("experiment.app")
            if not app:
                self.logger.error("No application specified for static analysis")
                return False

            # Execute static analysis
            from rv_android_core.analysis.static import static_analysis

            analyzer = static_analysis.StaticAnalyzer(app)
            results = analyzer.analyze()

            # Store results in context
            context.set("static_analysis.results", results)

            # Generate report
            report_path = os.path.join(context.results_dir, "reports", "static_analysis_report.json")
            with open(report_path, "w") as f:
                import_module("json").dump(results.to_dict(), f, indent=2)

            self.logger.info(f"Static analysis completed for experiment: {context.experiment_id}")
            return True

        except Exception as e:
            error_handler = ErrorHandler.get_instance()
            error_context = {
                "component": "StaticAnalysisProcessor",
                "operation": "static_analysis_phase",
                "experiment_id": context.experiment_id,
                "app": str(context.get("experiment.app", "unknown"))
            }
            error_handler.handle_error(e, error_context)
            return False


class ExecutionProcessor(BasePhaseProcessor):
    """
    Processor for the EXECUTION phase of a workflow.
    
    ### Architectural Decisions:
    - Focuses on dynamic execution of application testing
    - Separates execution concerns from analysis
    - Enables flexible test tool integration
    - Facilitates consistent execution results collection
    
    ### Role in the System:
    - Executes application testing tools
    - Manages dynamic analysis and runtime verification
    - Handles error recovery during execution
    - Collects execution data for later analysis
    """

    def __init__(self, context: IExecutionContext, event_bus: Optional[EventBus] = None):
        """
        Initialize the execution processor.
        
        Args:
            context: Execution context
            event_bus: Optional event bus for communication
        """
        super().__init__(
            processor_id="ExecutionProcessor",
            name="Execution Processor",
            description="Processor for experiment execution phase",
            event_bus=event_bus or get_event_bus(),
            supported_phases=[ExecutionPhase.EXECUTION]
        )
        self.initialize(context)
        self.configure({})
        self.activate()

    def execute(self, phase: ExecutionPhase, context: IExecutionContext) -> bool:
        """
        Execute the execution phase.
        
        Args:
            phase: Phase to execute
            context: Execution context
            
        Returns:
            True if execution was successful, False otherwise
        """
        if phase != ExecutionPhase.EXECUTION:
            return False

        self.logger.info(f"Executing execution phase for experiment: {context.experiment_id}")

        # Implement execution logic
        try:
            # Get task data
            task = context.get("experiment.task")
            if not task:
                self.logger.error("No task specified for execution")
                return False

            # Get tool information
            tool_name = task.config.tool_name
            self.logger.info(f"Executing task with tool: {tool_name}")

            # Create task executor
            from rv_experiment.experiment.core.factory import WorkflowFactory

            factory = context.get("experiment.factory")
            if not factory:
                # Create a factory
                base_dir = context.results_dir
                factory = WorkflowFactory(base_dir, self.event_bus)

            executor = factory.create_task_executor(task)

            # Execute the task
            result = executor.execute()

            # Store results in context
            context.set("execution.result", result)
            context.set("execution.completed", True)

            self.logger.info(f"Execution completed for experiment: {context.experiment_id}")

            # Return success based on task result
            return result.success

        except Exception as e:
            error_handler = ErrorHandler.get_instance()
            error_context = {
                "component": "ExecutionProcessor",
                "operation": "execution_phase",
                "experiment_id": context.experiment_id,
                "task": str(context.get("experiment.task", "unknown"))
            }
            error_handler.handle_error(e, error_context)
            return False


class AnalysisProcessor(BasePhaseProcessor):
    """
    Processor for the ANALYSIS phase of a workflow.
    
    ### Architectural Decisions:
    - Handles post-execution analysis in a dedicated phase
    - Separates analysis from execution and reporting
    - Enables modular analysis plugin architecture
    - Facilitates consistent analysis results production
    
    ### Role in the System:
    - Analyzes execution results
    - Processes coverage and performance data
    - Evaluates experiment success metrics
    - Prepares data for reporting
    """

    def __init__(self, context: IExecutionContext, event_bus: Optional[EventBus] = None):
        """
        Initialize the analysis processor.
        
        Args:
            context: Execution context
            event_bus: Optional event bus for communication
        """
        super().__init__(
            processor_id="AnalysisProcessor",
            name="Analysis Processor",
            description="Processor for results analysis phase",
            event_bus=event_bus or get_event_bus(),
            supported_phases=[ExecutionPhase.ANALYSIS]
        )
        self.initialize(context)
        self.configure({})
        self.activate()

    def execute(self, phase: ExecutionPhase, context: IExecutionContext) -> bool:
        """
        Execute the analysis phase.
        
        Args:
            phase: Phase to execute
            context: Execution context
            
        Returns:
            True if execution was successful, False otherwise
        """
        if phase != ExecutionPhase.ANALYSIS:
            return False

        self.logger.info(f"Executing analysis phase for experiment: {context.experiment_id}")

        # Implement analysis logic
        try:
            # Check if execution completed
            if not context.get("execution.completed", False):
                self.logger.warning("Analysis skipped: Execution phase did not complete successfully")
                return False

            # Get execution result
            result = context.get("execution.result")
            if not result:
                self.logger.error("No execution result found for analysis")
                return False

            # Process coverage data
            from rv_coverage.analysis.coverage import analyzer as coverage_analyzer

            coverage_data = coverage_analyzer.analyze_coverage(result)
            context.set("analysis.coverage", coverage_data)

            # Analyze execution logs
            from rv_android_core.analysis.results import processor as results_processor

            execution_metrics = results_processor.process_execution_logs(result)
            context.set("analysis.metrics", execution_metrics)

            # Store analysis results
            analysis_result = {
                "coverage": coverage_data.to_dict() if hasattr(coverage_data, "to_dict") else coverage_data,
                "metrics": execution_metrics
            }
            context.set("analysis.results", analysis_result)

            # Save analysis results to file
            import os
            import json

            results_file = os.path.join(context.results_dir, "analysis_results.json")
            with open(results_file, "w") as f:
                json.dump(analysis_result, f, indent=2)

            self.logger.info(f"Analysis completed for experiment: {context.experiment_id}")
            return True

        except Exception as e:
            error_handler = ErrorHandler.get_instance()
            error_context = {
                "component": "AnalysisProcessor",
                "operation": "analysis_phase",
                "experiment_id": context.experiment_id,
                "execution_completed": context.get("execution.completed", False)
            }
            error_handler.handle_error(e, error_context)
            return False


class ReportingProcessor(BasePhaseProcessor):
    """
    Processor for the REPORTING phase of a workflow.
    
    ### Architectural Decisions:
    - Handles report generation in a dedicated phase
    - Separates reporting from analysis
    - Enables multiple report format generation
    - Facilitates consistent reporting standards
    
    ### Role in the System:
    - Generates reports from analysis results
    - Creates visualizations of experiment data
    - Formats results for human consumption
    - Exports data in various formats
    """

    def __init__(self, context: IExecutionContext, event_bus: Optional[EventBus] = None):
        """
        Initialize the reporting processor.
        
        Args:
            context: Execution context
            event_bus: Optional event bus for communication
        """
        super().__init__(
            processor_id="ReportingProcessor",
            name="Reporting Processor",
            description="Processor for reporting phase",
            event_bus=event_bus or get_event_bus(),
            supported_phases=[ExecutionPhase.REPORTING]
        )
        self.initialize(context)
        self.configure({})
        self.activate()

    def execute(self, phase: ExecutionPhase, context: IExecutionContext) -> bool:
        """
        Execute the reporting phase.
        
        Args:
            phase: Phase to execute
            context: Execution context
            
        Returns:
            True if execution was successful, False otherwise
        """
        if phase != ExecutionPhase.REPORTING:
            return False

        self.logger.info(f"Executing reporting phase for experiment: {context.experiment_id}")

        # Implement reporting logic
        try:
            # Check if analysis completed
            if not context.has("analysis.results"):
                self.logger.warning("Reporting skipped: Analysis results not available")
                return False

            # Get analysis results
            analysis_results = context.get("analysis.results")

            # Generate reports
            from rv_android_core.analysis.results import report_generator

            report_generator.generate_reports(
                analysis_results,
                context.results_dir,
                experiment_id=context.experiment_id
            )

            # Record report generation
            context.set("experiment.status", "completed")
            context.set("experiment.end_time", import_module("datetime").datetime.now().isoformat())

            self.logger.info(f"Reporting completed for experiment: {context.experiment_id}")
            return True

        except Exception as e:
            error_handler = ErrorHandler.get_instance()
            error_context = {
                "component": "ReportingProcessor",
                "operation": "reporting_phase",
                "experiment_id": context.experiment_id,
                "has_analysis_results": context.has("analysis.results")
            }
            error_handler.handle_error(e, error_context)
            return False


class CleanupProcessor(BasePhaseProcessor):
    """
    Processor for the CLEANUP phase of a workflow.
    
    ### Architectural Decisions:
    - Handles resource cleanup in a dedicated phase
    - Ensures proper experiment termination
    - Enables selective resource preservation
    - Facilitates consistent cleanup procedures
    
    ### Role in the System:
    - Cleans up temporary resources
    - Ensures proper experiment completion
    - Preserves important artifacts
    - Finalizes experiment status
    """

    def __init__(self, context: IExecutionContext, event_bus: Optional[EventBus] = None):
        """
        Initialize the cleanup processor.
        
        Args:
            context: Execution context
            event_bus: Optional event bus for communication
        """
        super().__init__(
            processor_id="CleanupProcessor",
            name="Cleanup Processor",
            description="Processor for cleanup phase",
            event_bus=event_bus or get_event_bus(),
            supported_phases=[ExecutionPhase.CLEANUP]
        )
        self.initialize(context)
        self.configure({})
        self.activate()

    def execute(self, phase: ExecutionPhase, context: IExecutionContext) -> bool:
        """
        Execute the cleanup phase.
        
        Args:
            phase: Phase to execute
            context: Execution context
            
        Returns:
            True if execution was successful, False otherwise
        """
        if phase != ExecutionPhase.CLEANUP:
            return False

        self.logger.info(f"Executing cleanup phase for experiment: {context.experiment_id}")

        # Implement cleanup logic
        try:
            # Clean up temporary files
            import os
            import shutil

            temp_dir = os.path.join(context.results_dir, "temp")
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

            # Record cleanup completion
            context.set("experiment.cleaned", True)

            # Create a summary file
            summary = {
                "experiment_id": context.experiment_id,
                "status": context.get("experiment.status", "unknown"),
                "start_time": context.get("experiment.start_time"),
                "end_time": context.get("experiment.end_time"),
                "cleaned": True
            }

            summary_file = os.path.join(context.results_dir, "experiment_summary.json")
            with open(summary_file, "w") as f:
                import_module("json").dump(summary, f, indent=2)

            self.logger.info(f"Cleanup completed for experiment: {context.experiment_id}")
            return True

        except Exception as e:
            error_handler = ErrorHandler.get_instance()
            error_context = {
                "component": "CleanupProcessor",
                "operation": "cleanup_phase",
                "experiment_id": context.experiment_id,
                "results_dir": context.results_dir
            }
            error_handler.handle_error(e, error_context)
            return False


def import_module(name):
    """Helper function to import modules dynamically."""
    import importlib
    return importlib.import_module(name)
