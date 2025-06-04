"""
Factory for creating integrated components that combine new and legacy systems.

This module provides factory methods for creating integrated components that connect
the new orchestration and analysis systems with the existing experiment workflow.
"""
from typing import Optional, List

from rvandroid.analysis.results.integration import AnalysisAdapter
from rvandroid.experiment.event import EventBus, get_event_bus
from rvandroid.experiment.execution_manager import ExecutionManager
from rvandroid.experiment.orchestration.integration import OrchestratorAdapter
from rvandroid.experiment.orchestration.interfaces import OrchestrationMode
from rvandroid.experiment.task.task_storage import TaskStorage
from rvandroid.experiment.workflow.execution_controller import ExecutionController
from rvandroid.experiment.workflow.result_manager import ResultManager
from rvandroid.experiment.workflow.workflow_factory import WorkflowFactory
from rvandroid.util.logging.manager import LoggingManager

# TODO deprecated
class IntegrationFactory:
    """
    Factory for creating integrated components that combine new and legacy systems.
    
    This class provides methods for creating integrated components that connect
    the new orchestration and analysis systems with the existing experiment workflow.
    """
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        """
        Initialize the integration factory.
        
        Args:
            event_bus: Optional event bus for event handling. If not provided,
                      the default event bus will be used.
        """
        # Set up event bus (using dependency injection)
        self.event_bus = event_bus or get_event_bus()
        
        # Configure logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            'experiment_workflow.integration_factory',
            {'component': 'IntegrationFactory'}
        )
        
        self.logger.info("IntegrationFactory initialized")
    
    def create_orchestrator_adapter(self, 
                                    results_dir: str, 
                                    task_storage: TaskStorage,
                                    execution_mode: OrchestrationMode = OrchestrationMode.SEQUENTIAL) -> OrchestratorAdapter:
        """
        Create an orchestrator adapter that connects the new orchestration system with the existing experiment workflow.
        
        Args:
            results_dir: Directory for experiment results
            task_storage: Storage for task information
            execution_mode: Mode for task execution (sequential, parallel, etc.)
        
        Returns:
            An orchestrator adapter instance
        """
        self.logger.info(f"Creating orchestrator adapter with mode: {execution_mode.name}")
        
        return OrchestratorAdapter(
            results_dir=results_dir,
            event_bus=self.event_bus,
            task_storage=task_storage,
            execution_mode=execution_mode
        )
    
    def create_execution_controller_with_new_orchestration(self, 
                                                          results_dir: str,
                                                          task_storage: TaskStorage) -> ExecutionController:
        """
        Create an execution controller that uses the new orchestration system.
        
        This method creates an execution controller that uses the new orchestration system
        while maintaining the interface expected by the experiment controller.
        
        Args:
            results_dir: Directory for experiment results
            task_storage: Storage for task information
        
        Returns:
            An execution controller instance that uses the new orchestration system
        """
        self.logger.info(f"Creating execution controller with new orchestration system")
        
        # Create orchestrator adapter
        orchestrator = self.create_orchestrator_adapter(
            results_dir=results_dir,
            task_storage=task_storage
        )
        
        # Create execution controller that delegates to orchestrator adapter
        controller = ExecutionController(
            execution_manager=None,  # Not needed since we're using the orchestrator
            task_storage=task_storage,
            event_bus=self.event_bus,
            results_dir=results_dir
        )
        
        # Replace the standard run logic with orchestrator delegation
        original_run = controller.run
        
        def new_run():
            """Run the experiment using the orchestrator adapter."""
            self.logger.info("Delegating experiment execution to orchestrator adapter")
            return orchestrator.run()
        
        # Replace the method with our new implementation
        controller.run = new_run
        
        # Replace the setup method to delegate to orchestrator
        original_setup = controller.setup
        
        def new_setup(apks, repetitions, timeouts, tools, **kwargs):
            """Set up the experiment using the orchestrator adapter."""
            self.logger.info("Delegating experiment setup to orchestrator adapter")
            return orchestrator.setup(apks, repetitions, timeouts, tools, **kwargs)
        
        # Replace the method with our new implementation
        controller.setup = new_setup
        
        self.logger.info("Created execution controller with new orchestration system")
        return controller
    
    def create_analysis_adapter(self, 
                               results_dir: str,
                               task_storage: Optional[TaskStorage] = None) -> AnalysisAdapter:
        """
        Create an analysis adapter that connects the new analysis system with the existing result processing.
        
        Args:
            results_dir: Directory containing experiment results
            task_storage: Optional task storage for accessing task information
        
        Returns:
            An analysis adapter instance
        """
        self.logger.info(f"Creating analysis adapter for results directory: {results_dir}")
        
        return AnalysisAdapter(
            results_dir=results_dir,
            task_storage=task_storage
        )
    
    def create_result_manager_with_new_analysis(self, 
                                               results_dir: str,
                                               task_storage: Optional[TaskStorage] = None) -> ResultManager:
        """
        Create a result manager that uses the new analysis system.
        
        This method creates a result manager that uses the new analysis system
        while maintaining the interface expected by the experiment controller.
        
        Args:
            results_dir: Directory containing experiment results
            task_storage: Optional task storage for accessing task information
        
        Returns:
            A result manager instance that uses the new analysis system
        """
        self.logger.info(f"Creating result manager with new analysis system")
        
        # Create analysis adapter
        analysis_adapter = self.create_analysis_adapter(
            results_dir=results_dir,
            task_storage=task_storage
        )
        
        # Create standard result manager
        result_manager = ResultManager(
            results_dir=results_dir,
            event_bus=self.event_bus
        )
        
        # Replace the standard generate_reports method with enhanced version
        original_generate = result_manager.generate_reports
        
        def new_generate_reports():
            """Generate reports using the new analysis system."""
            self.logger.info("Generating reports with new analysis system")
            
            # Process results using new analysis system
            analysis_results = analysis_adapter.process_results()
            
            # Also call original method for backward compatibility
            original_results = original_generate()
            
            # Enhance results with advanced analysis
            enhanced_results = {
                **original_results,
                'advanced_analysis': analysis_results
            }
            
            self.logger.info("Report generation completed with enhanced analysis")
            return enhanced_results
        
        # Replace the method with our new implementation
        result_manager.generate_reports = new_generate_reports
        
        self.logger.info("Created result manager with new analysis system")
        return result_manager
    
    def create_integrated_workflow_factory(self) -> WorkflowFactory:
        """
        Create a workflow factory that integrates the new systems with the existing workflow.
        
        This method creates a workflow factory that uses the new orchestration and analysis systems
        while maintaining compatibility with the existing experiment controller.
        
        Returns:
            A workflow factory that creates integrated components
        """
        self.logger.info("Creating integrated workflow factory")
        
        # Start with standard workflow factory
        factory = WorkflowFactory(None, self.event_bus)
        
        # Store original methods to replace
        original_create_execution_controller = factory.create_execution_controller
        original_create_result_manager = factory.create_result_manager
        
        # Replace with methods that create integrated components
        def new_create_execution_controller():
            """Create an execution controller that uses the new orchestration system."""
            # Get task storage from factory
            task_storage = factory.task_storage
            
            # Get results directory from factory context
            results_dir = factory.results_dir
            
            return self.create_execution_controller_with_new_orchestration(
                results_dir=results_dir,
                task_storage=task_storage
            )
        
        def new_create_result_manager(results_dir):
            """Create a result manager that uses the new analysis system."""
            # Get task storage from factory
            task_storage = factory.task_storage
            
            return self.create_result_manager_with_new_analysis(
                results_dir=results_dir,
                task_storage=task_storage
            )
        
        # Replace methods with our new implementations
        factory.create_execution_controller = new_create_execution_controller
        factory.create_result_manager = new_create_result_manager
        
        self.logger.info("Created integrated workflow factory")
        return factory