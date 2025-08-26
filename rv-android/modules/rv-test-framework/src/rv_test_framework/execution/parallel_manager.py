"""
Parallel execution manager with LLM model grouping strategy using existing TaskExecutor.

This component manages parallel execution of Task objects while optimizing GPU memory 
usage through intelligent grouping by LLM model. It uses existing rv-platform TaskExecutor
for individual task execution and coordinates model transitions.

### Architectural Decisions:
- **Model Grouping**: Groups Task objects by LLM model to minimize GPU memory operations
- **TaskExecutor Integration**: Uses existing rv-platform TaskExecutor for individual executions
- **Process Coordination**: Uses multiprocessing pool for parallel Task execution  
- **Transition Management**: Implements simple cleanup between model groups (ollama stop + sleep)
- **Failure Isolation**: Individual task failures don't affect other parallel executions

### Resource Management Strategy:
- **GPU Memory**: Only one LLM model loaded at a time across all workers
- **CPU Utilization**: User-configured worker count (3-10) without adaptive management
- **Emulator Management**: Delegates to existing rv-android-core EmulatorManager
- **Keep-Alive Strategy**: Uses 60-second keep-alive during model group execution

### Integration Patterns:
- TaskExecutor execution patterns with error handling
- EmulatorManager context management approach
- Task result processing and metrics collection
- Static analysis caching and integration patterns
"""

import os
import time
import subprocess
import signal
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import multiprocessing as mp
import threading

from rv_android_core.event import EventBus, EventType
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT, LOG_START, LOG_COMPLETE, LOG_ERROR
from rv_android_core.util.logging.manager import LoggingManager
from rv_platform.execution.executor import TaskExecutor

from rv_test_framework.core.models import ModelGroup, TaskResult
from rv_test_framework.util.port_manager import EmulatorPortManager


def simplified_task_worker(task_serialized: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simplified worker function for ProcessPoolExecutor compatibility.
    Minimal implementation focusing on core task execution without complex dependencies.
    """
    import os
    import time
    import subprocess
    from datetime import datetime
    
    task_id = task_serialized.get('id', 'unknown')
    
    start_time = datetime.now()
    
    try:
        # Simulate task execution with actual tool call
        # This mimics the essential task execution without complex component interactions
        apk_path = task_serialized.get('apk_path', './out/instrumented_apks/cryptoapp.apk')
        timeout = task_serialized.get('timeout', 60)
        
        
        # Simple subprocess execution with device specification - key insight from working implementation
        device_serial = f'emulator-{5554 + (os.getpid() % 10)}'  # Simple device allocation
        
        cmd = [
            'poetry', 'run', 'droidbot',
            '-a', apk_path,
            '-policy', 'rvandroid', 
            '-o', f'./debug_test_results/worker_{os.getpid()}_output',
            '-timeout', str(timeout),
            '--rvandroid_url', 'http://localhost:5000/api/get_actions',
            '--rvandroid_screenshots', 'false',
            '-d', device_serial,  # Use specific device
            '--is_emulator'       # Indicate emulator usage
        ]
        
        
        # Execute with proper timeout handling
        result = subprocess.run(cmd, timeout=timeout + 30, capture_output=True, text=True)
        success = result.returncode == 0
        error_message = result.stderr if not success else ""
        
        
        
    except subprocess.TimeoutExpired:
        success = False
        error_message = f"Task execution timed out after {timeout + 30}s"
        
    except Exception as e:
        success = False
        error_message = str(e)
    
    end_time = datetime.now()
    execution_time = (end_time - start_time).total_seconds()
    
    
    # Return minimal serializable result
    return {
        'task_id': task_id,
        'config_name': task_serialized.get('config_name', 'unknown'),
        'apk_name': task_serialized.get('apk_name', 'unknown.apk'),
        'repetition': task_serialized.get('repetition', 1),
        'success': success,
        'error_message': error_message,
        'execution_time': execution_time,
        'logcat_file': '',
        'trace_file': '',
        'metrics': {}
    }


def execute_task_in_isolated_process(process_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a task in an isolated process with minimal dependencies.
    Based on the working ProcessPoolExecutor implementation.
    """
    import os
    import sys
    from pathlib import Path
    from datetime import datetime
    
    
    # Setup paths like run_test_framework.py does
    current_directory = os.getcwd()
    parent_directory = os.path.dirname(current_directory)
    
    project_root = Path(__file__).parent.parent.parent.parent.parent
    sys.path.insert(0, str(project_root / "modules" / "rv-android-core" / "src"))
    sys.path.insert(0, str(project_root / "modules" / "rv-platform" / "src"))
    sys.path.insert(0, str(project_root / "modules" / "rv-experiment" / "src"))
    sys.path.insert(0, str(project_root / "modules" / "rv-tools" / "src"))
    sys.path.insert(0, str(project_root / "modules" / "rv-coverage" / "src"))
    sys.path.insert(0, str(project_root / "modules" / "rv-static-analysis" / "src"))
    sys.path.insert(0, str(project_root / "modules" / "rv-llm" / "src"))
    sys.path.insert(0, str(project_root / "modules" / "rvandroid-tool" / "src"))
    sys.path.insert(0, str(project_root / "modules" / "rv-screen-parser" / "src"))
    sys.path.insert(0, str(project_root / "modules" / "rv-test-framework" / "src"))
    
    # Import constants and set RVSEC_HOME
    from rv_android_core import constants
    os.environ[constants.ENV_RVSEC_HOME] = parent_directory
    
    task_dict = process_data['task_dict'] 
    results_dir = process_data['results_dir']
    process_config = process_data['process_config']
    
    emulator_port = process_config['emulator_port']
    server_port = process_config['server_port']
    process_id = process_config['process_id']
    
    # Set port-specific environment variables for this process
    os.environ['RV_EMULATOR_PORT'] = str(emulator_port)
    os.environ['RV_SERVER_PORT'] = str(server_port)
    os.environ['RV_PROCESS_ID'] = process_id
    
    
    try:
        # Recreate minimal task object from dict - use simpler approach
        from rv_android_core.domain.task import Task, TaskConfiguration
        from rv_android_core.domain.app import App
        
        # Create simple tool config class locally to avoid import issues
        class SimpleToolConfig:
            def __init__(self, tool_name, variant, additional_params):
                self.tool_name = tool_name
                self.variant = variant  
                self.additional_params = additional_params
        
        # Reconstruct App
        app_path = task_dict['app']['app_path']
        if os.path.exists(app_path):
            app = App(app_path)
        else:
            app = None
        
        # Reconstruct ToolConfig
        tool_config_data = task_dict['config']['tool_config']
        tool_config = SimpleToolConfig(
            tool_name=tool_config_data['tool_name'],
            variant=tool_config_data['variant'],
            additional_params=tool_config_data['additional_params']
        )
        
        # Reconstruct TaskConfiguration using tool_config as dict to avoid Pydantic validation issues
        task_config = TaskConfiguration(
            apk_name=task_dict['config']['apk_name'],
            timeout=task_dict['config']['timeout'],
            repetition=task_dict['config']['repetition'],
            tool_config=tool_config_data  # Pass dict directly instead of object
        )
        
        # Reconstruct Task using factory method (if available) or direct construction
        try:
            # Try using from_dict if available
            task = Task.from_dict(task_dict)
            if app:
                task.set_app(app)
        except AttributeError:
            # Fallback: create Task manually (check constructor signature)
            task = Task(config=task_config, app=app)
            task.id = task_dict['id']
        
        
        # Execute using existing TaskExecutor pattern
        start_time = datetime.now()
        
        # Import required components
        from rv_platform.execution.executor import TaskExecutor
        from rv_platform.components.static_analysis import StaticAnalysisComponent
        from rv_platform.components.emulator import EmulatorComponent
        from rv_platform.components.logcat import LogcatComponent
        from rv_platform.components.coverage import CoverageComponent
        from rv_platform.components.tool_execution import ToolExecutionComponent
        from rv_tools.registry.factory import ToolFactory
        
        # Initialize tool registry in the isolated process
        # ProcessPoolExecutor creates completely separate processes that don't share
        # singleton instances, so we must rebuild the tool registry from scratch
        # This includes both builtin tools (ape, monkey, droidbot) and external tools (rvandroid)
        try:
            # Create fresh registry instance for this isolated process
            from rv_tools.registry import ToolRegistry
            
            # Create registry and register all builtin tools with variants
            tool_registry = ToolRegistry.get_instance()
            
            # Register builtin tools (ape, monkey, droidbot, etc.) with their variants
            # This automatically populates the registry with all available tools
            from rv_tools import _register_builtin_tools
            _register_builtin_tools()
            
            # Register external tools (rvandroid, rvdroid) if available
            # These are registered through rv-experiment's ExperimentToolRegistry
            try:
                from rv_experiment.tools.experiment_tools import ExperimentToolRegistry
                experiment_registry = ExperimentToolRegistry.get_instance()
                experiment_registry.register_external_tools()
                # Use the registry that includes external tools
                tool_registry = experiment_registry.registry
            except ImportError:
                # Fall back to builtin tools only if external registration fails
                pass
            
            # Get the specific tool instance (e.g., "rvandroid" with "vision" variant)
            tool = tool_registry.get_tool(
                tool_config_data['tool_name'],
                tool_config_data['variant']
            )
            
        except Exception as tool_error:
            # Fallback: create tool using ToolFactory
            from rv_tools.registry.factory import ToolFactory
            tool_factory = ToolFactory()
            tool = tool_factory.create_tool(tool_config)
        
        # Initialize process-specific instances like the working implementation
        from rv_android_core.util.logging.manager import LoggingManager
        from rv_android_core.util.error.error_handler import ErrorHandler
        from rv_android_core.event.bus import EventBus
        
        
        # Create process-specific instances to avoid singleton sharing issues
        # ProcessPoolExecutor isolates processes, so singleton instances from the parent
        # process are not accessible. We must create new instances in each worker process.
        # This prevents "singleton not initialized" errors during parallel execution.
        try:
            # Create fresh singleton instances for this isolated process
            logging_manager = LoggingManager.get_instance()
            error_handler = ErrorHandler.get_instance() 
            event_bus = EventBus.get_instance()
        except Exception as instance_error:
            # Fall back to None if singleton initialization fails
            # TaskExecutor can handle None values for optional dependencies
            logging_manager = None
            error_handler = None
            event_bus = None
        
        # Create TaskExecutor with process-specific instances
        task_executor = TaskExecutor(
            task=task,
            tool=tool,
            event_bus=event_bus,
            error_handler=error_handler
        )
        
        
        # Import and register all essential components in execution order (like working implementation)
        apks_dir = "./out/instrumented_apks"
        
        
        # Configure task to use specific emulator port for parallel execution
        # This ensures each parallel task uses a different emulator instance (5554, 5556, 5558...)
        # EmulatorComponent.start_emulator() extracts device_port from task.config.tool_config.additional_params
        # and passes it to the emulator command line: emulator -avd RVSec -port {device_port}
        if not hasattr(task.config.tool_config, 'additional_params'):
            task.config.tool_config.additional_params = {}
        if task.config.tool_config.additional_params is None:
            task.config.tool_config.additional_params = {}
            
        # Set the emulator port and device serial for this specific parallel task
        # This prevents "emulator port already in use" conflicts during concurrent execution
        task.config.tool_config.additional_params['device_port'] = emulator_port
        task.config.tool_config.additional_params['device_serial'] = f'emulator-{emulator_port}'
        
        
        # Create EmulatorComponent with port-configured task
        emulator_component = EmulatorComponent(task, event_bus) if event_bus else EmulatorComponent(task)
        
        # Pass event_bus to components to avoid ProcessIsolationError
        components = [
            StaticAnalysisComponent(task, apks_dir, event_bus) if event_bus else StaticAnalysisComponent(task, apks_dir),
            emulator_component,
            LogcatComponent(task, event_bus) if event_bus else LogcatComponent(task),
            CoverageComponent(task, event_bus) if event_bus else CoverageComponent(task),
            ToolExecutionComponent(task, tool, event_bus) if event_bus else ToolExecutionComponent(task, tool)
        ]
        
        for component in components:
            task_executor.register_component(component)
            
        
        
        # Execute the task
        execution_success = task_executor.execute()
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        
        # Create result
        result_dict = {
            'task_id': task.id,
            'config_name': tool_config.additional_params.get('config_name', 'unknown'),
            'apk_name': task_config.apk_name,
            'repetition': task_config.repetition,
            'success': execution_success,
            'error_message': '',
            'execution_time': execution_time,
            'logcat_file': '',
            'trace_file': '',
            'metrics': {}
        }
        
        return result_dict
        
    except Exception as e:
        import traceback
        error_msg = f"Process execution failed: {str(e)}\nTraceback: {traceback.format_exc()}"
        
        return {
            'task_id': task_dict['id'],
            'config_name': 'unknown',
            'apk_name': task_dict['config']['apk_name'],
            'repetition': task_dict['config']['repetition'],
            'success': False,
            'error_message': error_msg,
            'execution_time': 0.0,
            'logcat_file': '',
            'trace_file': '',
            'metrics': {}
        }


def execute_single_task(
    task_data: Dict[str, Any]  # Task data with dynamic resource allocation
) -> Dict[str, Any]:  # Return serialized TaskResult dict
    """
    Execute single Task object with true parallelism using dynamic resource allocation.
    
    This function is executed in worker threads and implements resource isolation
    for parallel execution without emulator/server contamination.
    
    ### True Parallelism Implementation:
    1. Generate unique worker_id for resource isolation
    2. Allocate dynamic server_port and device_serial per worker
    3. Inject resource parameters via additional_params
    4. TaskExecutor uses isolated resources (emulator + server)
    5. EmulatorComponent starts dedicated emulator instance
    6. RVAndroid tool uses dedicated server port and device
    
    Args:
        task_data: Dictionary containing task configuration
        
    Returns:
        TaskResult with execution outcome and metrics
    """
    import threading
    from datetime import datetime
    
    # Extract task from task_data first
    task = task_data['task']
    results_dir = task_data['results_dir']
    
    # Generate unique worker ID for resource isolation
    worker_id = threading.current_thread().ident % 100  # Limit to reasonable range
    
    # Dynamic resource allocation with socket validation to prevent duplicated emulators
    process_id = f"worker_{worker_id}_{task.id}"
    
    try:
        # Allocate validated emulator port using socket binding confirmation
        device_port = EmulatorPortManager.allocate_port(process_id)
        device_serial = f"emulator-{device_port}"
        
        # Allocate server port (simple offset-based, validated later if needed)
        server_port = 5000 + worker_id
        server_url = f"http://localhost:{server_port}/api/get_actions"
        
    except RuntimeError as e:
        # Port allocation failed - log error and fail gracefully
        import logging
        logging.error(f"EmulatorPortManager allocation failed for {process_id}: {e}")
        raise RuntimeError(f"Failed to allocate resources for parallel execution: {e}")
    
    # Inject dynamic resource parameters via additional_params (hybrid approach)
    if hasattr(task.config.tool_config, 'additional_params'):
        if task.config.tool_config.additional_params is None:
            task.config.tool_config.additional_params = {}
    else:
        task.config.tool_config.additional_params = {}
    
    # Set resource isolation parameters
    task.config.tool_config.additional_params.update({
        'worker_id': worker_id,
        'server_port': server_port,
        'device_port': device_port,
        'device_serial': device_serial,
        'server_url': server_url
    })
    
    # Override task.config.device_id with dynamic device_serial for parallel execution
    task.config.device_id = device_serial
    
    # Create task result object
    result = TaskResult(
        task_id=task.id,
        config_name=task.config.tool_config.additional_params.get("config_name", "unknown"),
        apk_name=task.config.apk_name,
        repetition=task.config.repetition
    )
    
    start_time = datetime.now()
    
    try:
        # Import ToolFactory for tool creation
        from rv_tools import ToolFactory
        
        # Create tool factory instance and tool (following rv-platform pattern)
        tool_factory = ToolFactory()
        tool = tool_factory.create_tool(tool_config=task.config.tool_config)
        
        # Configure tool with dynamic parameters (device_serial, device_id for parallel execution)
        tool_dynamic_config = {
            'device_serial': device_serial,
            'device_id': device_serial  # For tools that use device_id instead of device_serial
        }
        
        # Add any existing tool parameters from additional_params
        if hasattr(task.config.tool_config, 'additional_params') and task.config.tool_config.additional_params:
            tool_dynamic_config.update(task.config.tool_config.additional_params)
            
        # Configure tool with dynamic parameters
        if hasattr(tool, 'configure'):
            tool.configure(tool_dynamic_config)
        
        # Create TaskExecutor with task and tool (following rv-platform pattern)
        from rv_android_core.event import EventBus
        from rv_platform.components.coverage import CoverageComponent
        from rv_platform.components.emulator import EmulatorComponent
        from rv_platform.components.logcat import LogcatComponent
        from rv_platform.components.result_processor import ResultProcessorComponent
        from rv_platform.components.static_analysis import StaticAnalysisComponent
        from rv_platform.components.tool_execution import ToolExecutionComponent
        
        event_bus = EventBus.get_instance()
        
        # Use standard TaskExecutor - rely on EmulatorPortManager socket validation to prevent duplication
        task_executor = TaskExecutor(
            task=task,
            tool=tool,
            event_bus=event_bus,
            task_storage=None,
            error_handler=None
        )
        
        # Register all essential components in execution order (following rv-platform pattern)
        # Extract apks_dir from task data (APKs directory where static analysis files are located)
        apks_dir = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/out/instrumented_apks"
        
        components = [
            StaticAnalysisComponent(task, apks_dir, event_bus),
            EmulatorComponent(task, event_bus),
            LogcatComponent(task, event_bus),
            CoverageComponent(task, event_bus),
            ToolExecutionComponent(task, tool, event_bus)
        ]
        
        for component in components:
            task_executor.register_component(component)
        
        # Execute task using existing TaskExecutor infrastructure with all components
        execution_success = task_executor.execute()
        
        end_time = datetime.now()
        result.execution_time = (end_time - start_time).total_seconds()
        result.success = execution_success
        
        # Set result file paths (following existing patterns)
        result.logcat_file = task.result.logcat_file if hasattr(task.result, 'logcat_file') else ""
        result.trace_file = task.result.trace_file if hasattr(task.result, 'trace_file') else ""
        
        # Extract metrics from task execution (following test framework patterns)
        if hasattr(task, 'metrics') and task.metrics:
            result.metrics = task.metrics
        
    except Exception as e:
        end_time = datetime.now()
        result.execution_time = (end_time - start_time).total_seconds()
        result.success = False
        result.error_message = str(e)
    
    finally:
        # Aggressive cleanup for test framework: ensure emulator processes are terminated
        try:
            from rv_test_framework.util.process_cleaner import ProcessCleaner
            process_cleaner = ProcessCleaner()
            
            # Clean up emulator on specific device port used by this task
            if 'device_port' in locals():
                cleaned = process_cleaner.cleanup_specific_ports([device_port])
                if cleaned > 0:
                    import logging
                    logging.info(f"ProcessCleaner cleaned up {cleaned} emulator process(es) on port {device_port}")
        except Exception as cleanup_error:
            # Log cleanup error but don't fail the task
            import logging
            logging.warning(f"ProcessCleaner failed for port {device_port}: {cleanup_error}")
        
        # Cleanup allocated resources - release emulator port
        try:
            EmulatorPortManager.release_process_ports(process_id)
        except Exception as cleanup_error:
            # Log cleanup error but don't fail the task
            import logging
            logging.warning(f"Failed to cleanup resources for {process_id}: {cleanup_error}")
    
    # Return serialized result for ProcessPoolExecutor compatibility
    return {
        'task_id': result.task_id,
        'config_name': result.config_name,
        'apk_name': result.apk_name,
        'repetition': result.repetition,
        'success': result.success,
        'error_message': result.error_message,
        'execution_time': result.execution_time,
        'logcat_file': result.logcat_file,
        'trace_file': result.trace_file,
        'metrics': result.metrics
    }


class ParallelManager:
    """
    Manages parallel Task execution with model-based grouping using existing infrastructure.
    
    This class coordinates parallel execution using TaskExecutor with model-grouped execution.
    
    ### Execution Flow:
    1. Groups Task objects by LLM model type and name
    2. Executes each group with configured parallelism using TaskExecutor
    3. Manages simple model transitions (ollama stop + sleep)
    4. Aggregates results through existing PerformanceMonitor
    5. No complex resource management - user responsibility
    
    ### Integration Components:
    - TestRunner.run_test_suite() coordination patterns
    - TestExecutor.execute_test_case() execution logic  
    - EmulatorManager context management approach
    - Result processing and CSV export patterns
    """
    
    @ErrorHandler.handle_errors(
        component="ParallelManager",
        phase="initialization"
    )
    def __init__(
        self, 
        max_workers: int = 5,
        results_dir: str = "./results",
        event_bus: Optional[EventBus] = None
    ):
        """
        Initialize parallel manager with simple configuration.
        
        ### Initialization Strategy:
        Sets up process pool for parallel execution, prepares for Task object execution
        using existing TaskExecutor infrastructure, following old TestRunner patterns.
        
        Args:
            max_workers: Maximum parallel task executions (user-defined)
            results_dir: Directory for execution results  
            event_bus: Optional event bus for coordination
        """
        self.max_workers = max_workers
        self.results_dir = results_dir
        self.event_bus = event_bus or EventBus.get_instance()
        
        # Setup logging using existing infrastructure
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            'rv_test_framework.execution.parallel_manager',
            {CONTEXT_COMPONENT: 'ParallelManager'}
        )
        
        # Error handler integration
        self.error_handler = ErrorHandler.get_instance()
        
        # Execution state
        self.current_model: Optional[str] = None
        self.total_tasks_executed = 0
        self.total_tasks_successful = 0
        
        self.logger.info(f"ParallelManager initialized: {max_workers} workers")
    
    @ErrorHandler.handle_errors(
        component="ParallelManager",
        phase="model_group_execution"
    )
    def execute_model_groups(
        self, 
        model_groups: List[ModelGroup],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[TaskResult]:
        """
        Execute all model groups with model transitions.
        
        This method follows the test framework's TestRunner.run_test_suite() patterns,
        adapting them for model-grouped execution with simple transitions.
        
        ### Execution Strategy:
        - Execute each model group sequentially to avoid GPU memory conflicts
        - Use parallel execution within each model group  
        - Implement simple model transitions (ollama stop + sleep)
        - Aggregate results from all model groups
        
        Args:
            model_groups: List of model groups to execute
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of all task execution results
        """
        with self.logger.with_context(
            total_groups=len(model_groups),
            phase="model_groups_execution"
        ):
            self.logger.info(LOG_START.format(phase=f"execution of {len(model_groups)} model groups"))
            
            all_results: List[TaskResult] = []
            
            self.logger.info(f"🔄 MODEL_GROUPS: Starting loop over {len(model_groups)} model groups")
            
            for group_index, model_group in enumerate(model_groups):
                self.logger.info(f"🔄 MODEL_GROUPS: Processing group {group_index}: {model_group.model_name}")
                try:
                    # Report progress
                    if progress_callback:
                        progress_callback(
                            group_index, 
                            len(model_groups), 
                            f"Executing model group: {model_group.model_name}"
                        )
                    
                    # Execute model group
                    self.logger.info(f"🔄 MODEL_GROUPS: Calling _execute_model_group for {model_group.model_name}...")
                    group_results = self._execute_model_group(model_group, group_index)
                    self.logger.info(f"✅ MODEL_GROUPS: _execute_model_group returned {len(group_results)} results")
                    all_results.extend(group_results)
                    self.logger.info(f"✅ MODEL_GROUPS: Extended all_results, total now: {len(all_results)}")
                    
                    # Model transition (except for last group)
                    if group_index < len(model_groups) - 1:
                        self._transition_model(
                            current_model=model_group.model_name,
                            next_group=model_groups[group_index + 1]
                        )
                
                except Exception as e:
                    self.logger.error(f"Error executing model group {model_group.model_name}: {e}")
                    
                    # Create failure results for all tasks in this group
                    for task in model_group.tasks:
                        failure_result = TaskResult(
                            task_id=task.id,
                            config_name=task.config.tool_config.additional_params.get("config_name", "unknown"),
                            apk_name=task.config.apk_name,
                            repetition=task.config.repetition,
                            success=False,
                            error_message=f"Model group execution failed: {str(e)}"
                        )
                        all_results.append(failure_result)
            
            # Final progress update
            if progress_callback:
                progress_callback(len(model_groups), len(model_groups), "All model groups completed")
            
            self.logger.info(f"✅ MODEL_GROUPS: All model groups completed. Returning {len(all_results)} results")
            self.logger.info(LOG_COMPLETE.format(phase=f"execution of {len(model_groups)} model groups"))
            self.logger.info(f"Total tasks executed: {len(all_results)}")
            
            # Final aggressive cleanup to ensure no emulator processes are left running
            try:
                from rv_test_framework.util.process_cleaner import ProcessCleaner
                process_cleaner = ProcessCleaner()
                remaining_processes = process_cleaner.cleanup_all_emulators()
                if remaining_processes > 0:
                    self.logger.info(f"Final cleanup: removed {remaining_processes} remaining emulator process(es)")
                else:
                    self.logger.debug("Final cleanup: no emulator processes found")
            except Exception as e:
                self.logger.warning(f"Final cleanup failed: {e}")
            
            return all_results
    
    def _execute_model_group(self, model_group: ModelGroup, group_index: int) -> List[TaskResult]:
        """
        Execute single model group using parallel execution.
        
        This method uses the execution patterns from the test framework's
        TestExecutor, adapting them for parallel task execution.
        
        Args:
            model_group: Model group to execute
            group_index: Index of current group for logging
            
        Returns:
            List of task results for this model group
        """
        with self.logger.with_context(
            model_name=model_group.model_name,
            model_type=model_group.model_type,
            task_count=len(model_group.tasks),
            group_index=group_index
        ):
            self.logger.info(LOG_START.format(
                phase=f"model group {model_group.model_name} ({len(model_group.tasks)} tasks)"
            ))
            
            results: List[TaskResult] = []
            
            # Use ProcessPoolExecutor instead of ThreadPoolExecutor to avoid singleton deadlocks
            # ThreadPoolExecutor shares singleton instances (EventBus, LoggingManager) between threads,
            # causing deadlocks when multiple threads try to access the same singleton concurrently.
            # ProcessPoolExecutor creates isolated processes that don't share memory/singletons.
            from concurrent.futures import ProcessPoolExecutor
            import multiprocessing
            
            # Set spawn method to ensure Poetry virtual environment is properly inherited by child processes
            # Without this, child processes would use system Python instead of Poetry's virtual environment
            multiprocessing.set_start_method('spawn', force=True)
            
            # Get current Python executable (should be Poetry's virtual env)
            import sys
            python_executable = sys.executable
            
            executor = ProcessPoolExecutor(max_workers=self.max_workers)
            try:
                # Submit all tasks for this model group
                future_to_task = {}
                
                for task_index, task in enumerate(model_group.tasks):
                    # Create simplified task data for ProcessPoolExecutor compatibility
                    task_serialized = {
                        'id': task.id,
                        'apk_path': f'./out/instrumented_apks/{task.config.apk_name}',
                        'timeout': task.config.timeout,
                        'config_name': task.config.tool_config.additional_params.get("config_name", "unknown"),
                        'apk_name': task.config.apk_name,
                        'repetition': task.config.repetition
                    }
                    
                    # Generate unique process configuration like the working implementation
                    import time
                    process_id = f"tf_process_{task_index}_{int(time.time())}"
                    
                    # Allocate unique ports for true parallel execution without conflicts
                    # Each concurrent task needs different ports:
                    # - Emulator ports: 5554, 5556, 5558... (Android emulator uses even numbers)
                    # - Server ports: 5000, 5001, 5002... (for rvandroid tool HTTP server)
                    base_emulator_port = 5554  # Android emulator default starting port
                    base_server_port = 5000    # Default HTTP server port
                    emulator_port = base_emulator_port + (task_index * 2)  # Even numbers: 5554, 5556, 5558...
                    server_port = base_server_port + task_index           # Sequential: 5000, 5001, 5002...
                    
                    
                    # Serialize task completely for ProcessPoolExecutor compatibility  
                    task_dict = {
                        'id': task.id,
                        'config': {
                            'apk_name': task.config.apk_name,
                            'timeout': task.config.timeout,
                            'repetition': task.config.repetition,
                            'tool_config': {
                                'tool_name': task.config.tool_config.tool_name,
                                'variant': task.config.tool_config.variant,
                                'additional_params': task.config.tool_config.additional_params
                            }
                        },
                        'app': {
                            'app_path': str(task.app.app_path) if task.app else f'./out/instrumented_apks/{task.config.apk_name}'
                        }
                    }
                    
                    process_data = {
                        'task_dict': task_dict,
                        'results_dir': self.results_dir,
                        'process_config': {
                            'process_id': process_id,
                            'emulator_port': emulator_port,
                            'server_port': server_port
                        }
                    }
                    
                    future = executor.submit(execute_task_in_isolated_process, process_data)
                    future_to_task[future] = task
                
                # Use as_completed() like the working ProcessPoolExecutor implementation
                self.logger.info(f"🔄 PARALLEL: Collecting results from {len(future_to_task)} futures using as_completed...")
                
                from concurrent.futures import as_completed, TimeoutError
                timeout = 180  # 3 minutes timeout
                
                try:
                    for future in as_completed(future_to_task, timeout=timeout):
                        task = future_to_task[future]
                        try:
                            # Get result from future - should work with ProcessPoolExecutor
                            result_dict = future.result()
                            # Deserialize result dict back to TaskResult
                            result = TaskResult(
                                task_id=result_dict['task_id'],
                                config_name=result_dict['config_name'],
                                apk_name=result_dict['apk_name'],
                                repetition=result_dict['repetition'],
                                success=result_dict['success'],
                                error_message=result_dict.get('error_message', ''),
                                execution_time=result_dict.get('execution_time', 0.0),
                                logcat_file=result_dict.get('logcat_file', ''),
                                trace_file=result_dict.get('trace_file', ''),
                                metrics=result_dict.get('metrics', {})
                            )
                            results.append(result)
                            
                            # Update statistics
                            self.total_tasks_executed += 1
                            if result.success:
                                self.total_tasks_successful += 1
                            
                            # Log task completion
                            status = "SUCCESS" if result.success else f"FAILED: {result.error_message}"
                            self.logger.info(f"✅ PARALLEL: Task {result.task_id} completed: {status}")
                            
                        except Exception as e:
                            self.logger.error(f"❌ PARALLEL: Task execution failed: {task.id}: {e}")
                            
                            # Create failure result
                            failure_result = TaskResult(
                                task_id=task.id,
                                config_name=task.config.tool_config.additional_params.get("config_name", "unknown"),
                                apk_name=task.config.apk_name,
                                repetition=task.config.repetition,
                                success=False,
                                error_message=str(e)
                            )
                            results.append(failure_result)
                            self.total_tasks_executed += 1
                
                except TimeoutError:
                    self.logger.error(f"❌ PARALLEL: Timeout after {timeout}s waiting for futures")
                    
                    # Create failure results for incomplete futures
                    for future, task in future_to_task.items():
                        if not any(r.task_id == task.id for r in results):
                            self.logger.warning(f"⚠️  PARALLEL: Creating timeout result for unfinished task {task.id}")
                            failure_result = TaskResult(
                                task_id=task.id,
                                config_name=task.config.tool_config.additional_params.get("config_name", "unknown"),
                                apk_name=task.config.apk_name,
                                repetition=task.config.repetition,
                                success=False,
                                error_message=f"Task did not complete within {timeout}s timeout"
                            )
                            results.append(failure_result)
                            self.total_tasks_executed += 1
                
                self.logger.info(f"✅ PARALLEL: Collected {len(results)} results using as_completed")
            finally:
                # Cancel any remaining futures to prevent deadlock
                self.logger.info("🔄 PARALLEL: Checking for remaining futures...")
                remaining_futures = [f for f in future_to_task if not f.done()]
                if remaining_futures:
                    self.logger.warning(f"⚠️  PARALLEL: Cancelling {len(remaining_futures)} unfinished futures")
                    for future in remaining_futures:
                        future.cancel()
                        
                # Explicitly shutdown executor and wait for all processes to complete
                self.logger.info("🔄 PARALLEL: Shutting down ProcessPoolExecutor...")
                executor.shutdown(wait=True)
                self.logger.info("✅ PARALLEL: ProcessPoolExecutor shutdown complete")
            
            successful_count = sum(1 for r in results if r.success)
            failed_count = len(results) - successful_count
            
            self.logger.info(LOG_COMPLETE.format(
                phase=f"model group {model_group.model_name}: {successful_count} successful, {failed_count} failed"
            ))
            
            return results
    
    def _transition_model(self, current_model: str, next_group: ModelGroup) -> None:
        """
        Perform simple model transition between groups.
        
        ### Transition Strategy:
        - Stop current model using ollama stop command  
        - Sleep for GPU memory cleanup
        - Log transition for monitoring
        
        Args:
            current_model: Current model name to stop
            next_group: Next model group to prepare for
        """
        with self.logger.with_context(
            current_model=current_model,
            next_model=next_group.model_name
        ):
            self.logger.info(LOG_START.format(phase=f"model transition: {current_model} -> {next_group.model_name}"))
            
            try:
                # Stop current model to free GPU memory
                if next_group.model_type == "ollama":
                    stop_cmd = ["ollama", "stop", current_model]
                    self.logger.info(f"Stopping model: {' '.join(stop_cmd)}")
                    
                    result = subprocess.run(
                        stop_cmd,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.returncode != 0:
                        self.logger.warning(f"Model stop command failed: {result.stderr}")
                    else:
                        self.logger.info(f"Model {current_model} stopped successfully")
                
                # Sleep for GPU memory cleanup (simple approach)
                cleanup_time = 60  # seconds
                self.logger.info(f"Waiting {cleanup_time}s for GPU memory cleanup")
                time.sleep(cleanup_time)
                
                self.logger.info(LOG_COMPLETE.format(phase="model transition"))
                
            except subprocess.TimeoutExpired:
                self.logger.warning(f"Model stop command timed out for {current_model}")
            except Exception as e:
                self.logger.warning(f"Model transition failed: {e}")
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """
        Get execution statistics for monitoring and reporting.
        
        Returns:
            Dictionary with execution statistics
        """
        return {
            "total_tasks_executed": self.total_tasks_executed,
            "total_tasks_successful": self.total_tasks_successful,
            "total_tasks_failed": self.total_tasks_executed - self.total_tasks_successful,
            "success_rate": (
                self.total_tasks_successful / self.total_tasks_executed * 100
                if self.total_tasks_executed > 0 else 0
            ),
            "max_workers": self.max_workers,
            "results_directory": self.results_dir
        }


def _execute_rvandroid_direct(task, tool, event_bus) -> bool:
    """
    Execute RVAndroid directly without invoke_as_daemon to prevent emulator duplication.
    
    This function manually orchestrates the components (emulator, static analysis, etc.)
    and then executes the droidbot command directly using subprocess instead of the
    tool's execute() method which uses invoke_as_daemon causing process duplication.
    
    Args:
        task: Task to execute
        tool: RVAndroid tool instance
        event_bus: Event bus for coordination
        
    Returns:
        Success status
    """
    from rv_platform.components.static_analysis import StaticAnalysisComponent
    from rv_platform.components.emulator import EmulatorComponent
    from rv_platform.components.logcat import LogcatComponent
    from rv_platform.components.coverage import CoverageComponent
    from rv_android_core.util.error.exceptions import RVToolTimeoutError
    from rv_platform.task import Task
    from rv_android_core.event import EventBus
    import logging
    
    logger = logging.getLogger(f"direct_rvandroid.{task.id}")
    
    try:
        logger.info(f"Starting direct RVAndroid execution for task {task.id}")
        
        # Initialize components in execution order
        apks_dir = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/out/instrumented_apks"
        
        static_component = StaticAnalysisComponent(task, apks_dir, event_bus)
        emulator_component = EmulatorComponent(task, event_bus)
        logcat_component = LogcatComponent(task, event_bus)
        coverage_component = CoverageComponent(task, event_bus)
        
        # Execute components in order
        context = {}
        
        # 1. Static Analysis
        logger.info("Starting static analysis")
        if not static_component.initialize(context) or not static_component.execute(context):
            logger.error("Static analysis failed")
            return False
        
        # 2. Emulator
        logger.info("Starting emulator")
        if not emulator_component.initialize(context) or not emulator_component.execute(context):
            logger.error("Emulator startup failed")
            return False
        
        # 3. Logcat
        logger.info("Starting logcat")
        if not logcat_component.initialize(context) or not logcat_component.execute(context):
            logger.error("Logcat setup failed")
            return False
        
        # 4. Coverage
        logger.info("Starting coverage")
        if not coverage_component.initialize(context) or not coverage_component.execute(context):
            logger.error("Coverage setup failed")
            return False
        
        # 5. Execute RVAndroid DIRECTLY (no invoke_as_daemon)
        logger.info("Starting direct RVAndroid tool execution")
        success = _execute_droidbot_command_direct(task, logger)
        
        # Cleanup components
        logger.info("Cleaning up components")
        coverage_component.cleanup(context)
        logcat_component.cleanup(context)
        emulator_component.cleanup(context)
        static_component.cleanup(context)
        
        logger.info(f"Direct RVAndroid execution completed for task {task.id}: {'success' if success else 'failed'}")
        return success
        
    except Exception as e:
        logger.error(f"Direct RVAndroid execution failed for task {task.id}: {e}")
        return False


def _execute_droidbot_command_direct(task, logger) -> bool:
    """
    Execute DroidBot command directly using subprocess to prevent emulator duplication.
    
    Args:
        task: Task with configuration
        logger: Logger instance
        
    Returns:
        Success status
    """
    try:
        # Build DroidBot command exactly like the original tool
        cmd_parts = ["poetry", "run", "droidbot"]
        
        # Add APK path
        if hasattr(task, 'app') and hasattr(task.app, 'path'):
            cmd_parts.extend(["-a", str(task.app.path)])
        elif hasattr(task, 'apk_path') and task.apk_path:
            cmd_parts.extend(["-a", str(task.apk_path)])
        
        # Add policy
        cmd_parts.extend(["-policy", "rvandroid"])
        
        # Add output directory
        if hasattr(task, 'results_dir'):
            output_dir = os.path.join(task.results_dir, "rvandroid_output")
        else:
            output_dir = f"/tmp/rvandroid_output_{task.id}"
        os.makedirs(output_dir, exist_ok=True)
        cmd_parts.extend(["-o", output_dir])
        
        # Add timeout
        timeout = 60
        if hasattr(task, 'config') and hasattr(task.config, 'timeout'):
            timeout = task.config.timeout
        elif hasattr(task, 'timeout'):
            timeout = task.timeout
        cmd_parts.extend(["-timeout", str(timeout)])
        
        # Add RVAndroid server URL from additional_params
        if hasattr(task, 'additional_params') and task.additional_params and 'server_port' in task.additional_params:
            server_port = task.additional_params['server_port']
            url = f"http://localhost:{server_port}/api/get_actions"
            cmd_parts.extend(["--rvandroid_url", url])
        
        # Add screenshot configuration
        cmd_parts.extend(["--rvandroid_screenshots", "false"])
        
        # Add device serial
        if hasattr(task, 'additional_params') and task.additional_params and 'device_serial' in task.additional_params:
            device_serial = task.additional_params['device_serial']
            cmd_parts.extend(["-d", device_serial])
            logger.info(f"Using device serial: {device_serial}")
        
        logger.info(f"Executing command: {' '.join(cmd_parts)}")
        
        # Execute directly with subprocess (no daemon fork)
        process = subprocess.Popen(
            cmd_parts,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid  # Create new process group
        )
        
        try:
            # Wait for completion with timeout
            stdout, stderr = process.communicate(timeout=timeout)
            
            if stdout:
                logger.debug(f"DroidBot stdout: {stdout}")
            if stderr:
                logger.debug(f"DroidBot stderr: {stderr}")
            
            return_code = process.returncode
            success = return_code == 0
            
            if not success:
                logger.warning(f"DroidBot exited with code: {return_code}")
            
            return success
            
        except subprocess.TimeoutExpired:
            logger.info(f"DroidBot timed out after {timeout}s (expected)")
            
            # Terminate process group
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                time.sleep(2)
                if process.poll() is None:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
            
            return True  # Timeout is expected for testing tools
            
    except Exception as e:
        logger.error(f"Direct DroidBot execution failed: {e}")
        return False