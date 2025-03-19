# rvandroid/experiment/experiment_03.py
"""
Main experiment implementation for rv-android.
Coordinates the entire experiment lifecycle using the new architecture.
"""
import json
import os
from typing import List

from rvandroid.app import App
from rvandroid.constants import EXTENSION_APK, EXTENSION_REACH, EXTENSION_GATOR, EXTENSION_GESDA
from rvandroid.experiment.event_system import EventBus, EventType
from rvandroid.experiment.execution_manager import ExecutionManager
from rvandroid.experiment.task_storage import TaskStorage
from rvandroid.rvandroid import RvAndroid
from rvandroid.rvsec import RVSec
from rvandroid.tools.tool_spec import AbstractTool
from settings import TIMESTAMP, RESULTS_DIR, INSTRUMENTED_DIR


class Experiment03:
    """
    A sophisticated experiment orchestration system for comprehensive Android application testing and runtime verification.

    ### Architectural Decisions:
    - Implements a modular, event-driven approach to experiment execution
    - Supports configurable pre-processing, execution, and post-processing stages
    - Enables flexible tool integration and multi-stage experiment workflow
    - Provides robust error handling and logging mechanisms

    ### Role in the System:
    - Acts as the primary experiment coordinator for automated Android testing
    - Manages the entire lifecycle of a testing experiment
    - Coordinates interactions between tools, emulators, and analysis modules
    - Enables reproducible and configurable testing scenarios

    ### Key Considerations:
    - Supports dynamic configuration of experiment parameters
    - Handles complex pre-processing tasks like monitor generation and APK instrumentation
    - Manages task scheduling, execution, and result collection
    - Provides comprehensive logging and performance tracking
    - Supports resuming experiments from previous execution states

    ### Integration Strategy:
    - Compatible with multiple testing tools and runtime verification approaches
    - Integrates with Android emulation, instrumentation, and analysis systems
    - Uses dependency injection for tool and configuration management
    - Supports event-based communication between experiment components

    ### Performance and Scalability:
    - Designed for efficient execution across diverse experiment configurations
    - Minimizes overhead through modular and event-driven architecture
    - Supports parallel and sequential task execution
    - Adaptable to different app complexities and testing requirements
    - Enables comprehensive performance and coverage reporting
    """

    def __init__(self):
        """Initialize the experiment with event bus and logging setup"""
        # Get the event bus instance
        self.event_bus = EventBus.get_instance()

        # Configure logging
        from rvandroid.util.logging_manager import LoggingManager
        logging_manager = LoggingManager.get_instance()

        # Set up experiment identifier
        self.experiment_id = f"experiment_{TIMESTAMP}"

        # Initialize logger with experiment context
        self.logger = logging_manager.get_logger('experiment.experiment_03', {
            'experiment_id': self.experiment_id,
            'component': 'Experiment03'
        })

        # Create experiment directory
        self.results_dir = os.path.join(RESULTS_DIR, self.experiment_id)
        os.makedirs(self.results_dir, exist_ok=True)

        # Set up file logging for this experiment
        logging_manager.setup_file_logging(
            log_dir=os.path.join(self.results_dir, "logs"),
            experiment_id=self.experiment_id
        )

        # Create task storage
        storage_file = os.path.join(self.results_dir, "tasks.json")
        self.task_storage = TaskStorage(storage_file)

        # Create execution manager
        self.execution_manager = ExecutionManager(self.task_storage, self.event_bus)

        # Register event handlers
        self._setup_event_handlers()

        # Log experiment initialization
        self.logger.experiment_start(f"Experiment {self.experiment_id} initialized")

    def _setup_event_handlers(self):
        """
        Set up event handlers for the experiment.

        Registers callback functions for various event types that may occur during
        experiment execution, ensuring proper logging and coordination.
        """

        def on_experiment_started(event):
            """Handle experiment start events"""
            self.logger.info(f"Experiment started: {event.experiment_id}")

        def on_experiment_completed(event):
            """Handle experiment completion events"""
            self.logger.info(f"Experiment completed: {event.experiment_id}")

        def on_task_started(event):
            """Handle task start events"""
            self.logger.info(f"Task {event.task_id} started: "
                             f"{event.task_config.get('apk_name')}, "
                             f"{event.task_config.get('tool_name')}")

        def on_task_failed(event):
            """Handle task failure events"""
            self.logger.error(f"Task {event.task_id} failed: {event.details.get('error', 'Unknown error')}")

        # Register handlers directly instead of using decorators
        self.event_bus.subscribe(EventType.EXPERIMENT_STARTED, on_experiment_started)
        self.event_bus.subscribe(EventType.EXPERIMENT_COMPLETED, on_experiment_completed)
        self.event_bus.subscribe(EventType.TASK_STARTED, on_task_started)
        self.event_bus.subscribe(EventType.TASK_FAILED, on_task_failed)

    def execute(self, repetitions: int, timeouts: List[int], tools: List[AbstractTool],
                memory_file: str = "", generate_monitors: bool = True, instrument: bool = True,
                static_analysis: bool = True, skip_experiment: bool = False, no_window: bool = False):
        """
        Execute the entire experiment workflow with configurable pre-processing, execution, and post-processing steps.

        Manages the full experiment lifecycle including optional monitor generation, APK instrumentation,
        static analysis, and experiment execution. Supports resuming from a previous state via memory file
        and provides flexible configuration for experiment parameters.

        Args:
            repetitions: Number of times each task should be repeated
            timeouts: List of timeout durations to apply during experiment
            tools: Collection of testing tools to be used in the experiment
            memory_file: Path to a previous execution state file for resuming an experiment
            generate_monitors: Flag to enable automatic monitor generation
            instrument: Flag to enable APK instrumentation
            static_analysis: Flag to enable static code analysis
            skip_experiment: Flag to bypass experiment execution
            no_window: Flag to run emulator in headless mode without visual display

        Note:
            - If a memory file is provided, the experiment will attempt to resume from that state
            - Pre-processing steps are conditionally executed based on input flags
            - Experiment can be fully or partially skipped using configuration parameters
        """
        self.logger.info("Executing Experiment...")

        # Publish experiment started event
        self.event_bus.publish_experiment_event(
            EventType.EXPERIMENT_STARTED,
            experiment_id=self.experiment_id,
            message="Starting experiment execution",
            source="Experiment03"
        )

        # If memory file is provided, load it
        if memory_file:
            if not os.path.exists(memory_file):
                self.logger.error(f"Memory file not found: {memory_file}")
                return

            # Copy task storage to our results directory
            self.task_storage = TaskStorage(memory_file)
            self.task_storage.load()

            # Update execution manager
            self.execution_manager = ExecutionManager(self.task_storage, self.event_bus)
        else:
            # Pre-process APKs if not resuming from memory file
            if generate_monitors or instrument or static_analysis:
                self._pre_process_apks(generate_monitors, instrument, static_analysis)

        # Run experiment if not skipped
        if not skip_experiment:
            self._run_experiment(repetitions, timeouts, tools, no_window)

            # Post-processing
            self._post_process()

        # Publish experiment completed event
        self.event_bus.publish_experiment_event(
            EventType.EXPERIMENT_COMPLETED,
            experiment_id=self.experiment_id,
            message="Experiment execution completed",
            source="Experiment03"
        )

        self.logger.info("Experiment completed successfully!")

    def _pre_process_apks(self, generate_monitors: bool, instrument: bool, static_analysis: bool):
        """
        Pre-process APKs before experiment execution.

        Prepares the system for experiments by generating monitors, instrumenting APKs,
        and performing static analysis as requested.

        Args:
            generate_monitors: Whether to generate monitors
            instrument: Whether to instrument APKs
            static_analysis: Whether to perform static analysis
        """
        self.logger.info("Pre-processing APKs...")

        # Generate monitors if requested
        if generate_monitors:
            self.logger.info("Generating monitors...")
            rvsec = RVSec()
            rvsec.generate_monitors()

        # Instrument APKs if requested
        if instrument:
            self.logger.info("Instrumenting APKs...")
            rvandroid = RvAndroid()
            rvandroid.instrument_apks(results_dir=INSTRUMENTED_DIR)

        # Perform static analysis if requested
        if static_analysis:
            self.logger.info("Performing static analysis...")
            self._run_static_analysis()

        self.logger.info("Pre-processing completed")

    def _run_static_analysis(self):
        """
        Run static analysis on all instrumented APKs.

        Analyzes each APK to generate static analysis files that will be used for
        coverage tracking and other analyses during experiments.
        """
        import rvandroid.analysis.static_analysis as static

        for file in os.listdir(INSTRUMENTED_DIR):
            if file.casefold().endswith(EXTENSION_APK):
                app = App(os.path.join(INSTRUMENTED_DIR, file))
                base_name_template = app.name + "{}"
                gesda_file = os.path.join(INSTRUMENTED_DIR, base_name_template.format(EXTENSION_GESDA))
                gator_file = os.path.join(INSTRUMENTED_DIR, base_name_template.format(EXTENSION_GATOR))
                reach_file = os.path.join(INSTRUMENTED_DIR, base_name_template.format(EXTENSION_REACH))

                try:
                    static.run_static_analysis(app, gesda_file, gator_file, reach_file)
                    self.event_bus.publish_analysis_event(
                        EventType.STATIC_ANALYSIS_COMPLETED,
                        data={"app_name": app.name},
                        source="Experiment03"
                    )
                except Exception as e:
                    self.logger.error(f"Error in static analysis for {app.name}: {e}")

    def _run_experiment(self, repetitions: int, timeouts: List[int], tools: List[AbstractTool], no_window: bool):
        """
        Run the experiment with all tasks.

        Executes all experiment tasks for each combination of apps, tools, timeouts, and repetitions.
        Manages the creation, scheduling, and execution of tasks through the ExecutionManager.

        Args:
            repetitions: Number of repetitions for each task
            timeouts: List of timeouts to test
            tools: List of testing tools to use
            no_window: Whether to run emulator without window
        """
        self.logger.info("Running experiment...")

        # Get instrumented APKs
        apks = self._get_instrumented_apks()
        if not apks:
            self.logger.error("No instrumented APKs found")
            return
        self.logger.info(f"Found {len(apks)} instrumented APKs")

        # Register apps and tools
        for app in apks:
            self.execution_manager.register_app(app)

        for tool in tools:
            self.execution_manager.register_tool(tool)

        # Set up tasks if we don't already have them from a memory file
        if len(self.task_storage.get_tasks()) == 0:
            self.execution_manager.setup_execution(
                apks=apks,
                repetitions=repetitions,
                timeouts=timeouts,
                tools=tools,
                no_window=no_window
            )

        # Run all tasks
        self.execution_manager.run_all_tasks()

        # Log statistics
        stats = self.execution_manager.get_statistics()
        self.logger.info(f"Experiment execution statistics: {stats}")

    def _get_instrumented_apks(self) -> List[App]:
        """
        Get all instrumented APKs.

        Scans the instrumented directory for APK files and creates App objects for each one.

        Returns:
            List of App objects representing the instrumented APKs
        """
        apks = []
        for file in os.listdir(INSTRUMENTED_DIR):
            if file.casefold().endswith(EXTENSION_APK):
                try:
                    app = App(os.path.join(INSTRUMENTED_DIR, file))
                    apks.append(app)
                except Exception as e:
                    self.logger.error(f"Error processing APK {file}: {e}")

        return apks

    def _post_process(self):
        """
        Process results after experiment execution and generate diagnostics.
        Uses standardized models for result processing.
        """
        self.logger.info("Processing results...")

        # Generate coverage report using standardized models
        coverage_report = self.execution_manager.get_coverage_report()
        report_path = os.path.join(self.results_dir, "coverage_report.json")

        # Save coverage report
        with open(report_path, 'w') as f:
            json.dump(coverage_report, f, indent=2)

        self.logger.info(f"Coverage report saved to {report_path}")

        # Process analysis results using standardized models
        from rvandroid.analysis.results_analysis import process_results
        results = process_results(self.results_dir)

        # Generate performance metrics dashboard
        try:
            from rvandroid.util.performance_visualizer import PerformanceVisualizer
            visualizer = PerformanceVisualizer()

            # Generate coverage comparison chart
            visualizer.generate_coverage_comparison_chart(
                coverage_report=coverage_report,
                output_dir=os.path.join(self.results_dir, "charts")
            )

            # Generate complete dashboard
            dashboard_dir = visualizer.generate_performance_dashboard(self.results_dir)
            self.logger.info(f"Performance dashboard generated at {dashboard_dir}")

            # Log dashboard URL for easy access
            dashboard_index = os.path.join(dashboard_dir, "index.html")
            if os.path.exists(dashboard_index):
                self.logger.info(f"Dashboard available at: file://{os.path.abspath(dashboard_index)}")
        except Exception as e:
            self.logger.error(f"Error generating performance dashboard: {e}", exc_info=True)

        # Generate diagnostic report
        try:
            from rvandroid.util.diagnostics import DiagnosticTool
            diagnostic_tool = DiagnosticTool()
            report = diagnostic_tool.generate_report()
            report_path = os.path.join(self.results_dir, "diagnostic_report.json")
            report.save_to_file(report_path)
            self.logger.info(f"Diagnostic report saved to {report_path}")
        except Exception as e:
            self.logger.error(f"Error generating diagnostic report: {e}", exc_info=True)

        self.logger.info("Results processing completed")


def execute(tools=None):
    """
    Execute experiment with configuration from the Configuration singleton

    Args:
        tools: Optional list of tool objects to use (if None, gets tools from configuration)
    """
    from rvandroid.config.configuration import Configuration
    from rvandroid.tools.registry import ToolRegistry

    # Get configuration instance
    config = Configuration.get_instance()

    # Get experiment configuration
    repetitions = config.get_int("repetitions", 1)
    timeouts = config.get_list("timeouts", [60])
    memory_file = config.get_str("memory_file", "")
    generate_monitors = config.get_bool("generate_monitors", True)
    instrument = config.get_bool("instrument", True)
    static_analysis = config.get_bool("static_analysis", True)
    skip_experiment = config.get_bool("skip_experiment", False)
    no_window = config.get_bool("no_window", True)

    # If tools not provided, get tool names from config and look them up
    if tools is None:
        tool_names = config.get_list("tools", ["monkey"])
        # Get the tool registry
        registry = ToolRegistry.get_instance()
        # Get tools by name
        tools = registry.get_tools(tool_names)

    # Create experiment instance and execute
    experiment = Experiment03()
    experiment.execute(
        repetitions=repetitions,
        timeouts=timeouts,
        tools=tools,
        memory_file=memory_file,
        generate_monitors=generate_monitors,
        instrument=instrument,
        static_analysis=static_analysis,
        skip_experiment=skip_experiment,
        no_window=no_window
    )


def _execute(repetitions: int, timeouts: List[int], tools: List[AbstractTool], memory_file="",
             generate_monitors=True, instrument=True, static_analysis=True, skip_experiment=False,
             no_window=False):
    """
    Execute experiment with explicit parameters.

    Args:
        repetitions: Number of repetitions for each task
        timeouts: List of timeouts to test
        tools: List of testing tools to use
        memory_file: Optional file path to load previous execution state
        generate_monitors: Whether to generate monitors
        instrument: Whether to instrument APKs
        static_analysis: Whether to perform static analysis
        skip_experiment: Whether to skip the experiment execution
        no_window: Whether to run emulator without window
    """
    experiment = Experiment03()
    experiment.execute(
        repetitions=repetitions,
        timeouts=timeouts,
        tools=tools,
        memory_file=memory_file,
        generate_monitors=generate_monitors,
        instrument=instrument,
        static_analysis=static_analysis,
        skip_experiment=skip_experiment,
        no_window=no_window
    )
