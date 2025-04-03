"""
Test framework executor module.

This module provides the executor components for the test framework,
handling the execution of test cases and management of the testing process.
"""

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Tuple

from rvandroid.app import App
from rvandroid.analysis.results.integrated_metrics import IntegratedMetricsCalculator
from rvandroid.analysis.static_analysis import StaticAnalyzer
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.experiment.task.task_model import Task, TaskResult, TaskConfig, TaskStatus
from rvandroid.parser.log.logcat_parser import parse_logcat_file
from rvandroid.test_framework.config import TestCase, TestSuite, ToolConfiguration
from rvandroid.tools.tool_factory import ToolFactory
from rvandroid.tools.tool_spec import ToolSpec
from rvandroid.util.logging.constants import CONTEXT_COMPONENT, CONTEXT_PHASE
from rvandroid.util.logging.manager import LoggingManager


@dataclass
class TestResult:
    """
    Result of executing a test case.
    
    Captures the outcome and metrics from executing a test case,
    including execution timing, coverage data, and errors.
    """
    test_case: TestCase
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    status: str = "pending"  # pending, running, completed, error
    
    # Paths to result files
    logcat_file: str = ""
    trace_file: str = ""
    
    # Analysis results
    coverage_data: Dict[str, Any] = field(default_factory=dict)
    error_data: Dict[str, Any] = field(default_factory=dict)
    
    # Performance metrics
    execution_time: float = 0.0
    
    # Error information
    error_message: str = ""
    
    def mark_started(self) -> None:
        """Mark the test as started."""
        self.start_time = datetime.now()
        self.status = "running"
    
    def mark_completed(self) -> None:
        """Mark the test as completed."""
        self.end_time = datetime.now()
        self.status = "completed"
        self.execution_time = (self.end_time - self.start_time).total_seconds()
    
    def mark_error(self, error_message: str) -> None:
        """Mark the test as failed with an error message."""
        self.end_time = datetime.now()
        self.status = "error"
        self.error_message = error_message
        self.execution_time = (self.end_time - self.start_time).total_seconds()


class TestExecutor:
    """
    Executor for test cases in the test framework.
    
    Responsible for executing individual test cases, managing resources,
    and collecting results.
    
    ### Key Responsibilities:
    - Prepares the test environment
    - Configures tools based on test specifications
    - Executes test cases
    - Collects and processes test results
    - Manages resources throughout the test lifecycle
    """
    
    def __init__(self, output_dir: str = "test_results"):
        """
        Initialize the test executor.
        
        Args:
            output_dir: Directory for test results
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Set up logging
        self.logger = LoggingManager.get_instance().get_logger(
            'test_framework.executor',
            {
                CONTEXT_COMPONENT: 'TestExecutor',
                CONTEXT_PHASE: 'initialization'
            }
        )
        
        # Tool factory for creating tool instances
        self.tool_factory = ToolFactory()
        
        # Cache for static analysis data
        self.static_analysis_cache: Dict[str, StaticAnalysisData] = {}
        
    def execute_test_case(self, test_case: TestCase) -> TestResult:
        """
        Execute a single test case.
        
        Args:
            test_case: The test case to execute
            
        Returns:
            TestResult containing the test outcome
        """
        # Initialize result
        result = TestResult(test_case=test_case)
        
        # Create result directory
        result_dir = test_case.get_result_dir()
        os.makedirs(result_dir, exist_ok=True)
        
        # Set up logger with test context
        logger = LoggingManager.get_instance().get_logger(
            'test_framework.executor',
            {
                CONTEXT_COMPONENT: 'TestExecutor',
                CONTEXT_PHASE: 'execution',
                'test_id': test_case.get_id()
            }
        )
        
        # Set up trace and logcat file paths
        trace_file = os.path.join(result_dir, "trace.txt")
        logcat_file = os.path.join(result_dir, "logcat.txt")
        result.trace_file = trace_file
        result.logcat_file = logcat_file
        
        try:
            # Mark as started
            result.mark_started()
            logger.info(f"Starting test case: {test_case.get_id()}")
            
            # Create App instance
            app = App(test_case.app_path)
            
            # Get static analysis data if needed
            static_data = None
            if test_case.tool_config.use_static_analysis:
                static_data = self._get_static_analysis_data(
                    app,
                    test_case.tool_config.static_analysis_level,
                    result_dir
                )
            
            # Configure and create tool
            tool = self._configure_tool(test_case.tool_config, static_data)
            
            # Create task for execution
            task = self._create_task(app, tool, result_dir, trace_file, logcat_file, test_case.tool_config)
            
            # Set static data on task
            task.static_data = static_data
            
            # Execute the task
            logger.info(f"Executing tool: {test_case.tool_config.tool_name}")
            tool.execute(task, app)
            
            # Process results
            self._process_results(result, task, app)
            
            # Mark as completed
            result.mark_completed()
            logger.info(f"Test case completed: {test_case.get_id()}")
            
        except Exception as e:
            logger.error(f"Error executing test case: {str(e)}", exc_info=True)
            result.mark_error(str(e))
        
        return result
    
    def _get_static_analysis_data(self, app: App, level: str, output_dir: str) -> Optional[StaticAnalysisData]:
        """
        Get static analysis data for an app.
        
        Uses a cache to avoid duplicate static analysis runs.
        
        Args:
            app: App to analyze
            level: Analysis level (basic, standard, detailed)
            output_dir: Output directory for analysis files
            
        Returns:
            StaticAnalysisData if analysis is successful, None otherwise
        """
        # Check cache first
        cache_key = f"{app.path}:{level}"
        if cache_key in self.static_analysis_cache:
            return self.static_analysis_cache[cache_key]
        
        # Set up analysis files
        gesda_file = os.path.join(output_dir, f"{app.package_name}.gesda")
        gator_file = os.path.join(output_dir, f"{app.package_name}.wtg")
        reach_file = os.path.join(output_dir, f"{app.package_name}.reach")
        
        # Create analyzer
        analyzer = StaticAnalyzer(app, output_dir)
        analyzer.gesda_file = gesda_file
        analyzer.gator_file = gator_file
        analyzer.reach_file = reach_file
        
        try:
            # For basic level, only run GESDA
            if level == "basic":
                analyzer._run_gesda()
            # For standard level, run GESDA and GATOR
            elif level == "standard":
                analyzer._run_gesda()
                analyzer._run_gator()
            # For detailed level, run all analyzers
            else:
                analyzer.analyze()
            
            # Get static data
            static_data = analyzer.get_static_data()
            
            # Cache results
            if static_data:
                self.static_analysis_cache[cache_key] = static_data
            
            return static_data
            
        except Exception as e:
            self.logger.error(f"Error in static analysis: {str(e)}", exc_info=True)
            return None
    
    def _configure_tool(self, tool_config: ToolConfiguration, static_data: Optional[StaticAnalysisData]) -> ToolSpec:
        """
        Configure a tool based on test configuration.
        
        Args:
            tool_config: Tool configuration
            static_data: Static analysis data (optional)
            
        Returns:
            Configured tool instance
            
        Raises:
            ValueError: If tool configuration is invalid
        """
        # Get tool from factory
        tool = self.tool_factory.get_tool(tool_config.tool_name)
        
        if not tool:
            raise ValueError(f"Unknown tool: {tool_config.tool_name}")
        
        # Create component configurator
        configurator = ComponentConfigurator(static_data)
        
        # Configure LLM
        configurator.set_llm(
            tool_config.llm_type,
            tool_config.llm_model,
            temperature=tool_config.temperature,
            max_tokens=tool_config.max_tokens
        )
        
        # Configure strategy
        configurator.set_strategy(tool_config.strategy_type, **tool_config.strategy_params)
        
        # Configure parser
        configurator.set_parser(tool_config.parser_type, **tool_config.parser_params)
        
        # Configure visitor
        configurator.set_visitor(tool_config.visitor_type, **tool_config.visitor_params)
        
        # Set component configurator on tool
        tool.component_config = configurator
        
        # Configure additional tool-specific settings
        tool_specific_config = {}
        
        # Add screenshot analysis configuration if enabled
        if tool_config.use_screenshot_analysis:
            tool_specific_config["use_screenshot_analysis"] = True
            tool_specific_config["screenshot_analysis_level"] = tool_config.screenshot_analysis_level
        
        # Add any extra parameters
        tool_specific_config.update(tool_config.extra_params)
        
        # Configure tool with specific settings
        if tool_specific_config:
            tool.configure(tool_specific_config)
        
        return tool
    
    def _create_task(self, 
                    app: App, 
                    tool: ToolSpec,
                    result_dir: str,
                    trace_file: str,
                    logcat_file: str,
                    tool_config: ToolConfiguration) -> Task:
        """
        Create a task for executing a tool on an app.
        
        Args:
            app: App to test
            tool: Tool to execute
            result_dir: Directory for results
            trace_file: Path for trace output
            logcat_file: Path for logcat output
            tool_config: Tool configuration
            
        Returns:
            Task configured for execution
        """
        # Create task configuration
        task_config = TaskConfig(
            timeout=tool_config.timeout,
            device_id="emulator-5554"  # Default device ID
        )
        
        # Create task result
        task_result = TaskResult(
            output_dir=result_dir,
            trace_file=trace_file,
            logcat_file=logcat_file
        )
        
        # Create unique task ID
        task_id = f"{app.package_name}_{tool.name}_{int(time.time())}"
        
        # Create task
        task = Task(
            id=task_id,
            app_name=app.package_name,
            app_path=app.path,
            tool_name=tool.name,
            config=task_config,
            result=task_result,
            status=TaskStatus.CREATED
        )
        
        return task
    
    def _process_results(self, test_result: TestResult, task: Task, app: App) -> None:
        """
        Process test results after execution.
        
        Args:
            test_result: Test result to update
            task: Executed task
            app: Tested app
        """
        try:
            # Check if logcat file exists
            if os.path.exists(task.result.logcat_file):
                # Parse logcat file
                logcat_data = parse_logcat_file(task.result.logcat_file)
                
                # Create integrated metrics calculator
                calculator = IntegratedMetricsCalculator(app.package_name)
                calculator.set_logcat_data(logcat_data)
                
                # Set static data if available
                if task.static_data:
                    calculator.set_static_data(task.static_data)
                
                # Calculate metrics
                analysis_result = calculator.calculate_metrics()
                
                # Update test result with coverage data
                if analysis_result and hasattr(analysis_result, 'coverage'):
                    test_result.coverage_data = analysis_result.coverage.to_dict()
                
                # Update test result with error data
                if analysis_result and hasattr(analysis_result, 'errors'):
                    test_result.error_data = analysis_result.errors.to_dict()
        
        except Exception as e:
            self.logger.error(f"Error processing results: {str(e)}", exc_info=True)


class TestRunner:
    """
    Runner for executing test suites.
    
    Manages the execution of test suites, including parallel execution
    of test cases and result aggregation.
    
    ### Key Responsibilities:
    - Executes test suites
    - Manages parallel test execution
    - Collects and aggregates test results
    - Provides progress monitoring and reporting
    """
    
    def __init__(self, max_workers: int = 1, output_dir: str = "test_results"):
        """
        Initialize the test runner.
        
        Args:
            max_workers: Maximum number of parallel test executions
            output_dir: Directory for test results
        """
        self.max_workers = max_workers
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Set up logging
        self.logger = LoggingManager.get_instance().get_logger(
            'test_framework.runner',
            {CONTEXT_COMPONENT: 'TestRunner'}
        )
        
        # Create executor
        self.executor = TestExecutor(output_dir)
        
        # Results storage
        self.results: List[TestResult] = []
        
    def run_test_suite(self, test_suite: TestSuite, 
                      progress_callback: Optional[Callable[[int, int, str], None]] = None) -> List[TestResult]:
        """
        Run a complete test suite.
        
        Args:
            test_suite: Test suite to run
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of test results
        """
        # Update output directory from test suite
        if test_suite.output_dir:
            self.output_dir = test_suite.output_dir
            self.executor.output_dir = test_suite.output_dir
            os.makedirs(self.output_dir, exist_ok=True)
        
        # Get all test cases
        test_cases = test_suite.get_test_cases()
        total_tests = len(test_cases)
        
        if total_tests == 0:
            self.logger.warning("No test cases found in test suite")
            return []
        
        self.logger.info(f"Starting test suite: {test_suite.name} with {total_tests} test cases")
        
        # Results container
        results = []
        
        # Report initial progress
        if progress_callback:
            progress_callback(0, total_tests, "Starting")
        
        # Create timestamp for this run
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suite_dir = os.path.join(self.output_dir, f"{test_suite.name}_{timestamp}")
        os.makedirs(suite_dir, exist_ok=True)
        
        # Execute tests in parallel if multiple workers
        if self.max_workers > 1:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all test cases
                future_to_test = {
                    executor.submit(self.executor.execute_test_case, test_case): test_case
                    for test_case in test_cases
                }
                
                # Process results as they complete
                completed = 0
                for future in as_completed(future_to_test):
                    test_case = future_to_test[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        self.logger.error(f"Test case failed: {test_case.get_id()}: {str(e)}")
                        # Create failure result
                        result = TestResult(test_case=test_case)
                        result.mark_error(str(e))
                        results.append(result)
                    
                    # Update progress
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, total_tests, f"Completed: {test_case.get_id()}")
        else:
            # Execute tests sequentially
            for i, test_case in enumerate(test_cases):
                try:
                    result = self.executor.execute_test_case(test_case)
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Test case failed: {test_case.get_id()}: {str(e)}")
                    # Create failure result
                    result = TestResult(test_case=test_case)
                    result.mark_error(str(e))
                    results.append(result)
                
                # Update progress
                if progress_callback:
                    progress_callback(i + 1, total_tests, f"Completed: {test_case.get_id()}")
        
        # Save results
        self.results = results
        
        # Final progress update
        if progress_callback:
            progress_callback(total_tests, total_tests, "Completed")
        
        self.logger.info(f"Test suite completed: {test_suite.name}")
        
        return results
    
    def get_results_summary(self) -> Dict[str, Any]:
        """
        Get a summary of test results.
        
        Returns:
            Dictionary with test result summary
        """
        if not self.results:
            return {"status": "No tests executed"}
        
        # Count statuses
        total = len(self.results)
        completed = sum(1 for r in self.results if r.status == "completed")
        errors = sum(1 for r in self.results if r.status == "error")
        
        # Calculate average execution time for successful tests
        execution_times = [r.execution_time for r in self.results if r.status == "completed"]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        # Group results by tool
        tool_results = {}
        for result in self.results:
            tool_name = result.test_case.tool_config.tool_name
            if tool_name not in tool_results:
                tool_results[tool_name] = {
                    "total": 0,
                    "completed": 0,
                    "errors": 0
                }
            
            tool_results[tool_name]["total"] += 1
            if result.status == "completed":
                tool_results[tool_name]["completed"] += 1
            elif result.status == "error":
                tool_results[tool_name]["errors"] += 1
        
        return {
            "total": total,
            "completed": completed,
            "errors": errors,
            "completion_rate": (completed / total) * 100 if total > 0 else 0,
            "avg_execution_time": avg_execution_time,
            "tools": tool_results
        }