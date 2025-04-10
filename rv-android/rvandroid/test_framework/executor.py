"""
Test framework executor module.

This module provides the executor components for the test framework,
handling the execution of test cases and management of the testing process.
"""

import logging
import os
import time
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Tuple, ContextManager

from rvandroid.app import App
from rvandroid.android import Android
from rvandroid.analysis.results.integrated_metrics import IntegratedMetricsCalculator
from rvandroid.analysis.static_analysis import StaticAnalyzer
from rvandroid.commands.command import Command
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.experiment.task.task_model import Task, TaskResult, TaskConfig, TaskStatus
from rvandroid.parser.log.logcat_parser import parse_logcat_file
from rvandroid.parser.static.static_analysis_parser import StaticAnalysisParser
from rvandroid.test_framework.config import TestCase, TestSuite, ToolConfiguration
from rvandroid.tools.tool_factory import ToolFactory
from rvandroid.tools.tool_spec import AbstractTool
from rvandroid.util.emulator_manager import EmulatorManager
from rvandroid.util.exceptions import EmulatorError
from rvandroid.util.logging.constants import CONTEXT_COMPONENT, CONTEXT_PHASE
from rvandroid.util.logging.manager import LoggingManager
from rvandroid.util.logcat_manager import LogcatManager


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
    batch_metrics: Dict[str, Any] = field(default_factory=dict)
    
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
        
        # Emulator manager for handling emulator operations
        self.emulator_manager = EmulatorManager()
        
        # Logcat manager for handling logcat capture
        self.logcat_manager = LogcatManager()
        
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
            
            # Start emulator, run test, and clean up - similar to rv-android
            logger.info(f"Starting emulator session for test case: {test_case.get_id()}")
            
            # Use the emulator manager to start an emulator for this test
            try:
                # Start a new emulator for this test (using context manager for cleanup)
                with self.emulator_manager.start_emulator("RVSec", test_case.tool_config.no_window) as android:
                    logger.info(f"Emulator started successfully")
                    
                    # Clear logcat buffer for clean logs
                    logger.info(f"Clearing logcat buffer")
                    self.emulator_manager.clear_logcat()
                    
                    # Start logcat capture to file
                    logger.info(f"Starting logcat capture to {logcat_file}")
                    if not self.logcat_manager.start_capture(logcat_file):
                        logger.warning(f"Failed to start logcat capture, results may be incomplete")
                    
                    # Install the app
                    logger.info(f"Installing app: {app.name}")
                    if not self.emulator_manager.install_app(app):
                        raise Exception(f"Failed to install app: {app.name}")
                    
                    try:
                        # Execute the testing tool
                        logger.info(f"Executing tool: {test_case.tool_config.tool_name}")
                        tool.execute(task, app)
                        
                        logger.info(f"Tool execution completed")
                    finally:
                        # Stop logcat capture
                        logger.info(f"Stopping logcat capture")
                        self.logcat_manager.stop_capture()
                    
                    # Process results
                    self._process_results(result, task, app)
                
                # Emulator will be automatically stopped by the context manager
                logger.info(f"Emulator session completed for test case: {test_case.get_id()}")
                
                # Mark test as completed
                result.mark_completed()
                logger.info(f"Test case completed: {test_case.get_id()}")
                
            except Exception as emulator_error:
                logger.error(f"Error in emulator session: {str(emulator_error)}")
                # Mark as error but continue to next test
                result.mark_error(str(emulator_error))
            
        except Exception as e:
            logger.error(f"Error executing test case: {str(e)}", exc_info=True)
            result.mark_error(str(e))
            logger.info(f"Test case failed: {test_case.get_id()}")
        
        return result
    
    def _get_static_analysis_data(self, app: App, level: str, output_dir: str) -> Optional[StaticAnalysisData]:
        """
        Get static analysis data for an app from pre-generated files.
        
        Looks for existing static analysis files and parses them. 
        The files should follow the naming pattern: apk_name.extension
        
        Args:
            app: App to analyze
            level: Analysis level (basic, standard, detailed) - used to determine which files to load
            output_dir: Output directory for analysis files
            
        Returns:
            StaticAnalysisData if analysis is successful, None otherwise
        """
        # Check cache first
        cache_key = f"{app.path}:{level}"
        if cache_key in self.static_analysis_cache:
            return self.static_analysis_cache[cache_key]
        
        # Get the base name of the APK file
        apk_basename = os.path.basename(app.path)
        app_dir = os.path.dirname(app.path)
        
        # Define potential locations to search for static analysis files
        search_dirs = [
            app_dir,  # Same directory as APK
            os.path.join(os.path.dirname(os.path.dirname(app.path)), "out"),  # out directory at project root
            "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/out",  # Hardcoded path to out
            os.path.join(os.environ.get("HOME", ""), "out")  # out in user's home
        ]
        
        # Define the file paths for static analysis results
        # For each directory, try both naming formats (with and without .apk)
        gesda_file = None
        gator_file = None
        reach_file = None
        
        # Look for files in each directory
        for search_dir in search_dirs:
            if not os.path.exists(search_dir):
                continue
                
            # Try with and without .apk suffix
            for file_basename in [apk_basename, f"{apk_basename}.apk"]:
                potential_gesda = os.path.join(search_dir, f"{file_basename}.gesda")
                potential_gator = os.path.join(search_dir, f"{file_basename}.wtg")
                potential_reach = os.path.join(search_dir, f"{file_basename}.reach")
                
                # Set the file path if found
                if os.path.exists(potential_gesda) and not gesda_file:
                    gesda_file = potential_gesda
                    self.logger.info(f"Found GESDA file: {gesda_file}")
                    
                if os.path.exists(potential_gator) and not gator_file:
                    gator_file = potential_gator
                    self.logger.info(f"Found GATOR file: {gator_file}")
                    
                if os.path.exists(potential_reach) and not reach_file:
                    reach_file = potential_reach
                    self.logger.info(f"Found REACH file: {reach_file}")
        
        # Check if files exist
        missing_files = []
        
        # GESDA is always required
        if not gesda_file:
            missing_files.append("GESDA file not found in any search directory")
            self.logger.warning("GESDA file not found in any search directory")
        
        # For standard level, we also need GATOR
        if level in ["standard", "detailed"]:
            if not gator_file:
                self.logger.warning("GATOR file not found in any search directory")
                if level == "standard":
                    missing_files.append("GATOR file not found in any search directory")
        
        # For detailed level, we need REACH
        if level == "detailed":
            if not reach_file:
                self.logger.warning("REACH file not found in any search directory")
                missing_files.append("REACH file not found in any search directory")
        
        # For basic level, only GESDA is required
        # For standard level, GESDA and GATOR are required
        # For detailed level, all files are required
        
        # If any required files are missing (according to level), log an error and return None
        if missing_files:
            self.logger.error(f"Missing required static analysis files for {apk_basename}: {', '.join(missing_files)}")
            if level != "basic":
                self.logger.info(f"Consider using a lower analysis level (current: {level})")
            return None
        
        try:
            # Parse the static analysis files based on the analysis level
            parser = StaticAnalysisParser()
            
            # Parse the files
            self.logger.info(f"Loading static analysis data for {apk_basename} (level: {level})")
            
            # Print debug info about found files
            self.logger.info(f"Static analysis files for {apk_basename}:")
            self.logger.info(f"  GESDA file: {gesda_file} (found: {bool(gesda_file)})")
            self.logger.info(f"  GATOR file: {gator_file} (found: {bool(gator_file)})")
            self.logger.info(f"  REACH file: {reach_file} (found: {bool(reach_file)})")
            
            # Set up paths, using empty string as fallback for missing files
            gesda_file_path = gesda_file if gesda_file else ""
            gator_file_path = gator_file if gator_file else ""
            reach_file_path = reach_file if reach_file else ""
            
            self.logger.info(f"Using files for parsing:")
            self.logger.info(f"  GESDA: {gesda_file_path}")
            self.logger.info(f"  GATOR: {gator_file_path}")
            self.logger.info(f"  REACH: {reach_file_path}")
            
            # Parse with the available files
            try:
                # Try parsing with the reach file
                static_data = parser.parse(
                    reach_file=reach_file_path,
                    gator_file=gator_file_path,
                    gesda_file=gesda_file_path,
                    package=app.package_name
                )
            except Exception as e:
                self.logger.error(f"Error parsing with reach file: {str(e)}")
                self.logger.info("Trying to parse without reach file")
                
                # Fallback: try parsing without reach file (using empty string)
                try:
                    static_data = parser.parse(
                        reach_file="",
                        gator_file=gator_file_path,
                        gesda_file=gesda_file_path,
                        package=app.package_name
                    )
                except Exception as fallback_error:
                    self.logger.error(f"Fallback error: {str(fallback_error)}")
                    # Last resort: try to create a minimal static data object
                    from rvandroid.domain.classes import Classes
                    from rvandroid.domain.window import Windows
                    from rvandroid.domain.wtg import WindowTransitionGraph
                    static_data = StaticAnalysisData(Classes(), Windows(), WindowTransitionGraph())
            
            # Cache results
            if static_data:
                self.static_analysis_cache[cache_key] = static_data
                # Add detailed logs about the loaded data
                classes_count = len(static_data.classes.classes) if static_data.classes else 0
                windows_count = len(static_data.windows.windows) if static_data.windows else 0
                wtg_count = len(static_data.wtg.transitions) if (static_data.wtg and hasattr(static_data.wtg, 'transitions')) else 0
                
                self.logger.info(f"Successfully loaded static analysis data for {apk_basename}: "
                               f"classes={classes_count}, windows={windows_count}, transitions={wtg_count}")
            else:
                self.logger.warning(f"Failed to create static analysis data for {apk_basename}")
            
            return static_data
            
        except Exception as e:
            self.logger.error(f"Error parsing static analysis files: {str(e)}", exc_info=True)
            return None
    
    def _configure_tool(self, tool_config: ToolConfiguration, static_data: Optional[StaticAnalysisData]) -> AbstractTool:
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
        # Import ToolRegistry
        from rvandroid.tools.registry import ToolRegistry
        
        # Get tool registry instance
        registry = ToolRegistry.get_instance()
        
        # Get tool from registry
        tool = registry.get_tool(tool_config.tool_name)
        
        if not tool:
            raise ValueError(f"Unknown tool: {tool_config.tool_name}")
        
        # Create a deep copy of the tool (to avoid modifying the original)
        import copy
        tool = copy.deepcopy(tool)
        
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
                    tool: AbstractTool,
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
        from rvandroid.experiment.task.task_model import TaskConfiguration
        
        # Create task configuration with additional parameters
        task_config = TaskConfiguration(
            apk_name=app.package_name,
            repetition=1,
            timeout=tool_config.timeout,
            tool_name=tool.name,
            device_id="emulator-5554",
            no_window=tool_config.no_window
        )
        
        # Create task
        task = Task(task_config)
        
        # Set result file paths
        task.result.trace_file = trace_file
        task.result.logcat_file = logcat_file
        
        # Set results directory
        task.results_dir = result_dir
        
        # Set app instance
        task.set_app(app)
        
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
                # Parse logcat file WITH static data - this ensures the static data is
                # properly initialized in the repository for coverage calculation
                # This is critical - without passing static_data here, coverage will be 0%
                logcat_data = parse_logcat_file(task.result.logcat_file, task.static_data)
                
                # Create integrated metrics calculator
                calculator = IntegratedMetricsCalculator(app.package_name)
                
                # Set logcat data
                calculator.set_logcat_data(logcat_data)
                
                # Set static data if available (although it's already used in logcat parsing)
                if task.static_data:
                    self.logger.info(f"Setting static data to calculator (has classes: {bool(task.static_data.classes)})")
                    calculator.set_static_data(task.static_data)
                else:
                    self.logger.warning("No static data available on task for metrics calculation")
                
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
    
    Manages the execution of test suites sequentially
    and aggregates results.
    
    ### Key Responsibilities:
    - Executes test suites
    - Collects and aggregates test results
    - Provides progress monitoring and reporting
    """
    
    def __init__(self, output_dir: str = "test_results"):
        """
        Initialize the test runner.
        
        Args:
            output_dir: Directory for test results
        """
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
        Run a complete test suite sequentially.
        
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
        
        # Export results to CSV
        self.export_results_to_csv(self.output_dir)
        
        # Generate results summary
        summary = self.get_results_summary()
        self.logger.info(f"Test suite summary: {summary}")
        
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
        
    def export_results_to_csv(self, output_dir: str = None) -> bool:
        """
        Export test results to CSV files.
        
        Exports comprehensive test data to CSV files, including:
        - coverage_data.csv: Coverage metrics for all tests
        - error_data.csv: System error information
        - mop_error_data.csv: Detailed MOP error metrics
        - monitored_operations.csv: Monitored operations metrics
        
        Args:
            output_dir: Directory to save CSV files (defaults to self.output_dir)
            
        Returns:
            True if export was successful, False otherwise
        """
        if not self.results:
            self.logger.warning("No results to export")
            return False
            
        if not output_dir:
            output_dir = self.output_dir
            
        try:
            # Create CSV files
            coverage_file = os.path.join(output_dir, "coverage_data.csv")
            error_file = os.path.join(output_dir, "error_data.csv")
            mop_error_file = os.path.join(output_dir, "mop_error_data.csv")
            monitored_ops_file = os.path.join(output_dir, "monitored_operations.csv")
            
            import csv
            import json
            
            # Create coverage CSV file
            with open(coverage_file, 'w', newline='') as f:
                writer = csv.writer(f)
                # Write header
                writer.writerow([
                    "test_id", "tool", "app", "llm_model", "strategy", 
                    "method_coverage", "activity_coverage", "mop_method_coverage",
                    "execution_time", "status", "timestamp"
                ])
                
                # Write data
                for result in self.results:
                    test_id = result.test_case.get_id()
                    tool = result.test_case.tool_config.tool_name
                    app = os.path.basename(result.test_case.app_path)
                    llm_model = result.test_case.tool_config.llm_model
                    strategy = result.test_case.tool_config.strategy_type
                    
                    # Get coverage data
                    method_coverage = result.coverage_data.get("method_coverage", 0) if hasattr(result, "coverage_data") and result.coverage_data else 0
                    activity_coverage = result.coverage_data.get("activity_coverage", 0) if hasattr(result, "coverage_data") and result.coverage_data else 0
                    mop_method_coverage = result.coverage_data.get("mop_method_coverage", 0) if hasattr(result, "coverage_data") and result.coverage_data else 0
                    
                    # Write row
                    writer.writerow([
                        test_id, tool, app, llm_model, strategy,
                        method_coverage, activity_coverage, mop_method_coverage,
                        result.execution_time, result.status, 
                        result.end_time.isoformat() if result.end_time else ""
                    ])
            
            # Create error CSV file
            with open(error_file, 'w', newline='') as f:
                writer = csv.writer(f)
                # Write header
                writer.writerow([
                    "test_id", "tool", "app", "error_message", 
                    "execution_time", "status", "timestamp", 
                    "total_errors", "unique_errors"
                ])
                
                # Write data for error results
                for result in self.results:
                    test_id = result.test_case.get_id()
                    tool = result.test_case.tool_config.tool_name
                    app = os.path.basename(result.test_case.app_path)
                    
                    # Get error counts
                    total_errors = 0
                    unique_errors = 0
                    
                    if hasattr(result, "error_data") and result.error_data:
                        total_errors = result.error_data.get("total_errors", 0)
                        unique_errors = result.error_data.get("unique_errors", 0)
                    
                    # Only write system errors here if status is error
                    if result.status == "error":
                        # Write row
                        writer.writerow([
                            test_id, tool, app, result.error_message,
                            result.execution_time, result.status,
                            result.end_time.isoformat() if result.end_time else "",
                            total_errors, unique_errors
                        ])
            
            # Create MOP error CSV file for detailed MOP error data
            with open(mop_error_file, 'w', newline='') as f:
                writer = csv.writer(f)
                # Write header
                writer.writerow([
                    "test_id", "tool", "app", "llm_model", "strategy",
                    "mop_error_count", "mop_unique_errors", "mop_error_categories",
                    "mop_error_rate", "monitored_operations_ratio", "status", "timestamp"
                ])
                
                # Write data for all results with MOP errors
                for result in self.results:
                    test_id = result.test_case.get_id()
                    tool = result.test_case.tool_config.tool_name
                    app = os.path.basename(result.test_case.app_path)
                    llm_model = result.test_case.tool_config.llm_model
                    strategy = result.test_case.tool_config.strategy_type
                    
                    # Get MOP error data
                    mop_error_count = 0
                    mop_unique_errors = 0
                    mop_error_categories = "{}"
                    mop_error_rate = 0.0
                    monitored_operations_ratio = 0.0
                    
                    if hasattr(result, "error_data") and result.error_data:
                        mop_error_count = result.error_data.get("mop_error_count", 0)
                        mop_unique_errors = result.error_data.get("mop_unique_errors", 0)
                        
                        # Convert dictionary to JSON string for storage in CSV
                        if "mop_error_categories" in result.error_data:
                            categories = result.error_data.get("mop_error_categories", {})
                            if categories:
                                mop_error_categories = json.dumps(categories)
                        
                        mop_error_rate = result.error_data.get("mop_error_rate", 0.0)
                        monitored_operations_ratio = result.error_data.get("monitored_operations_ratio", 0.0)
                    
                    # Write row
                    writer.writerow([
                        test_id, tool, app, llm_model, strategy,
                        mop_error_count, mop_unique_errors, mop_error_categories,
                        mop_error_rate, monitored_operations_ratio,
                        result.status, result.end_time.isoformat() if result.end_time else ""
                    ])
            
            # Create monitored operations CSV file
            with open(monitored_ops_file, 'w', newline='') as f:
                writer = csv.writer(f)
                # Write header
                writer.writerow([
                    "test_id", "tool", "app", "llm_model", "strategy",
                    "mop_specifications", "mop_triggers", "triggered_specifications", 
                    "monitored_operations_count", "monitored_operations_triggered",
                    "status", "timestamp"
                ])
                
                # Write data for all results
                for result in self.results:
                    test_id = result.test_case.get_id()
                    tool = result.test_case.tool_config.tool_name
                    app = os.path.basename(result.test_case.app_path)
                    llm_model = result.test_case.tool_config.llm_model
                    strategy = result.test_case.tool_config.strategy_type
                    
                    # Get monitored operations data
                    mop_specifications = 0
                    mop_triggers = 0
                    triggered_specifications = "[]"
                    monitored_operations_count = 0
                    monitored_operations_triggered = 0
                    
                    # Extract from error_data (populated by IntegratedMetricsCalculator)
                    if hasattr(result, "error_data") and result.error_data:
                        monitored_operations_count = result.error_data.get("monitored_operations_count", 0)
                        monitored_operations_triggered = result.error_data.get("monitored_operations_triggered", 0)
                        
                        if "mop_specs_triggered" in result.error_data:
                            specs = result.error_data.get("mop_specs_triggered", [])
                            if specs:
                                triggered_specifications = json.dumps(specs)
                    
                    # Write row
                    writer.writerow([
                        test_id, tool, app, llm_model, strategy,
                        mop_specifications, mop_triggers, triggered_specifications,
                        monitored_operations_count, monitored_operations_triggered,
                        result.status, result.end_time.isoformat() if result.end_time else ""
                    ])
                    
            self.logger.info(f"Results exported to {output_dir} (coverage, errors, MOP errors, monitored operations)")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting results to CSV: {e}")
            return False