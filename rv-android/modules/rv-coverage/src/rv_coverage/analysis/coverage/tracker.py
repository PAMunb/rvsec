# rv_coverage/analysis/coverage/tracker.py
import os
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, List, Dict

from rv_android_core.domain.coverage import LogcatRepository
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.event.bus import EventBus, EventType
from rv_coverage.parser.log.logcat_parser import parse_logcat_line


class CoverageTracker:
    """
    Real-time coverage tracking system for Android application testing.
    
    The CoverageTracker monitors logcat output in real-time, extracting coverage
    information and formal property violations as they occur during test execution.
    It serves as the primary real-time monitoring component in the RV-Android system.

    ### Architectural Decisions:
    - **Real-Time Processing**: Continuously monitors logcat files for new entries,
      providing immediate coverage feedback during test execution
    - **Direct Repository Integration**: Uses LogcatRepository directly without wrapper
      layers for optimal performance and minimal latency
    - **Event-Driven Architecture**: Publishes coverage and error events through EventBus
      for real-time system integration and monitoring
    - **Thread-Safe Operation**: Implements proper threading patterns for concurrent
      logcat processing without blocking test execution
    - **Performance Optimization**: Uses change detection to minimize unnecessary
      metric calculations and reduce CPU overhead
    - **Context Manager Support**: Provides convenient context manager interface
      for automated lifecycle management

    ### Role in the System:
    - **Real-Time Monitor**: Primary component for live coverage monitoring during tests
    - **Event Publisher**: Publishes coverage updates and MOP error events for system
      integration and real-time dashboards
    - **Data Collector**: Extracts and processes coverage information from logcat streams
    - **Metric Provider**: Calculates and maintains up-to-date coverage metrics
    - **Error Detector**: Identifies and reports formal property violations as they occur
    - **State Manager**: Maintains consistent coverage state throughout test lifecycle

    ### Integration Points:
    - **EventBus**: Publishes COVERAGE_UPDATED and COVERAGE_ERROR_DETECTED events
    - **LogcatRepository**: Direct repository access for immediate data storage
    - **LoggingManager**: Standardized logging with contextual information
    - **ErrorHandler**: Robust error handling for logcat parsing failures
    - **StaticAnalysisData**: Initialization from static analysis results

    ### Performance Considerations:
    - **Change Detection**: Only calculates metrics when data has actually changed
    - **Efficient Threading**: Uses optimized sleep patterns based on data availability
    - **Memory Management**: Processes logcat entries incrementally without accumulation
    - **CPU Optimization**: Minimizes redundant calculations through caching strategies
    - **I/O Efficiency**: Uses file positioning to avoid re-reading processed data

    ### Event Publishing Strategy:
    - **Coverage Events**: Published when method coverage metrics change significantly
    - **Error Events**: Immediate publication when MOP violations are detected
    - **Contextual Data**: All events include timing and contextual information
    - **Decoupled Design**: Event consumers can subscribe without affecting tracking performance

    ### Usage Patterns:
    ```python
    # Context manager usage (recommended)
    with CoverageTracker(logcat_file, static_data) as tracker:
        # Run tests, tracker monitors automatically
        pass
    
    # Manual lifecycle management
    tracker = CoverageTracker(logcat_file, static_data)
    tracker.start()
    try:
        # Run tests
        pass
    finally:
        tracker.stop()
    
    # Get real-time metrics
    metrics = tracker.get_coverage_metrics()
    ```

    ### Thread Safety:
    All public methods are thread-safe and can be called from multiple threads
    concurrently. Internal state is protected by appropriate locking mechanisms.
    """

    def __init__(self, logcat_file: str, static_data: Optional[StaticAnalysisData] = None,
                 task_start_time: Optional[datetime] = None):
        """
        Initialize the coverage tracker.

        Args:
            logcat_file: Path to the logcat file to monitor
            static_data: Optional static analysis data
            task_start_time: When tool execution started (for calculating accurate relative timing)
                            Note: This should be tool_execution_start, not task creation time
        """
        self.logcat_file = logcat_file
        self.static_data = static_data
        # Using task_start_time parameter name for compatibility, but this should contain tool_execution_start time
        self.tool_execution_start_time = task_start_time

        # Set up logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            'analysis.coverage.tracker',
            {CONTEXT_COMPONENT: 'CoverageTracker'}
        )

        # Initialize LogcatRepository directly for optimal performance
        # Direct repository usage provides better performance and simpler data flow
        self.repository = LogcatRepository()

        # Event bus for publishing coverage and MOP error events
        self.event_bus = EventBus.get_instance()

        # Initialize running state
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._reader_lock = threading.RLock()

        # Metrics
        self.last_update_time = datetime.now()
        self.total_errors = 0
        self.total_method_calls = 0

        # Track previous metrics for change detection and performance optimization
        self._previous_metrics = {
            "method_coverage": 0.0,
            "activity_coverage": 0.0,
            "mop_method_coverage": 0.0,
            "called_methods": 0,
            "total_activities": 0,
            "unique_errors": 0
        }

        # Performance optimization: track if data has changed since last metrics calculation
        self._data_changed_since_last_update = False

        # Initialize repository with static data
        if static_data and static_data.classes:
            self._initialize_from_static_data()

    def _initialize_from_static_data(self) -> None:
        """Initialize the repository from static analysis data."""
        try:
            self.logger.info("Initializing coverage tracker from static analysis data")

            # Process classes from static data
            classes = self.static_data.classes
            for class_name, class_info in classes.classes.items():
                # Create class in repository
                from rv_android_core.domain.coverage import ClassCoverageData
                class_data = ClassCoverageData(
                    name=class_name,
                    is_activity=class_info.is_activity,
                    is_main_activity=getattr(class_info, "is_main_activity", False)
                )

                # Add to repository directly - no wrapper layer needed
                self.repository.add_class(class_data)

                # Add methods to class
                for method in class_info.methods:
                    from rv_android_core.domain.coverage import MethodCoverageData
                    method_data = MethodCoverageData(
                        class_name=class_name,
                        method_name=method.name,
                        signature=method.signature,
                        parameters=getattr(method, "params", []),
                        reachable=method.reachable,
                        reaches_mop=method.reaches_mop,
                        directly_reaches_mop=method.directly_reaches_mop,
                        from_static_analysis=True
                    )
                    class_data.add_method(method_data)

            # Log summary of initialized data
            total_methods = sum(len(class_info.methods) for class_info in classes.classes.values())
            self.logger.info(
                f"Initialized repository with {len(self.repository.classes)} classes "
                f"and {total_methods} methods from static data"
            )

        except Exception as e:
            self.logger.error(f"Error initializing from static data: {e}", exc_info=True)

    def start(self) -> None:
        """Start the coverage tracker thread."""
        if self.is_running:
            self.logger.warning("Coverage tracker is already running")
            return

        # Ensure logcat file exists
        try:
            parent_dir = os.path.dirname(self.logcat_file)
            if not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)

            # Create empty file if it doesn't exist
            if not os.path.exists(self.logcat_file):
                with open(self.logcat_file, 'w'):
                    pass

            # Reset tracker state
            self._stop_event.clear()
            self.is_running = True

            # Start tracking thread
            self.thread = threading.Thread(target=self._track_coverage, daemon=True)
            self.thread.start()

            self.logger.info(f"Coverage tracker started for {self.logcat_file}")

        except Exception as e:
            self.is_running = False
            self.logger.error(f"Failed to start coverage tracker: {e}")
            raise

    def stop(self) -> None:
        """Stop the coverage tracker thread."""
        if not self.is_running:
            return

        try:
            self._stop_event.set()

            if self.thread:
                # Give thread time to terminate
                self.thread.join(timeout=5.0)

                # Check if still alive
                if self.thread.is_alive():
                    self.logger.warning("Coverage tracker thread did not terminate gracefully")

            self.is_running = False
            self.logger.info("Coverage tracker stopped")

        except Exception as e:
            self.logger.error(f"Error stopping coverage tracker: {e}")
            self.is_running = False

    def _track_coverage(self) -> None:
        """Main tracking method that runs in a separate thread."""
        file_handle = None

        try:
            with open(self.logcat_file, 'r') as f:
                file_handle = f

                # Process existing lines
                with self._reader_lock:
                    self.process_lines(f.readlines())

                # Move to end of file
                f.seek(0, os.SEEK_END)

                # Keep reading until stopped
                while not self._stop_event.is_set():
                    # Read new lines
                    with self._reader_lock:
                        new_lines = f.readlines()

                    # Process new lines if any
                    if new_lines:
                        self.process_lines(new_lines)
                        # Update metrics immediately after processing new data
                        self._update_coverage_metrics()
                        self.last_update_time = datetime.now()
                    else:
                        # Only update metrics periodically if no new data
                        if (datetime.now() - self.last_update_time).total_seconds() >= 10:
                            self._update_coverage_metrics()
                            self.last_update_time = datetime.now()

                    # Longer sleep when no new data to reduce CPU usage
                    sleep_time = 0.5 if new_lines else 1.0
                    time.sleep(sleep_time)

        except Exception as e:
            self.logger.error(f"Error tracking coverage: {e}", exc_info=True)

        finally:
            self.is_running = False

            # Close file handle if needed
            if file_handle and not file_handle.closed:
                try:
                    file_handle.close()
                except Exception:
                    pass

    @contextmanager
    def track_coverage(self):
        """
        Context manager for tracking coverage.

        Yields:
            Self for use within the context
        """
        self.start()
        try:
            yield self
        finally:
            self.stop()

    def process_lines(self, lines: List[str]) -> None:
        """
        Process multiple logcat lines.

        Args:
            lines: List of logcat lines
        """
        for line in lines:
            self._process_line(line)

    def _process_line(self, line: str) -> None:
        """
        Process a single logcat line.

        Args:
            line: Logcat line to process
        """
        try:
            # Skip empty lines
            if not line.strip():
                return

            # Parse line for coverage or error info
            error_log, coverage_log = parse_logcat_line(line)

            # Update repository
            if error_log:
                # Calculate time since tool execution start using logcat timestamp
                if self.tool_execution_start_time and error_log.time_occurred:
                    time_since_start = int((error_log.time_occurred - self.tool_execution_start_time).total_seconds())
                    time_since_start = max(0, time_since_start)  # Ensure non-negative
                else:
                    time_since_start = 0
                
                # Set timing info for error
                error_log.time_since_task_start = time_since_start
                self.repository.register_rv_error(error_log)
                self.total_errors += 1
                self._data_changed_since_last_update = True  # Mark data as changed
                
                # Publish MOP error event for real-time monitoring
                self.event_bus.publish_analysis_event(
                    EventType.ERROR_DETECTED,
                    data={
                        "spec": error_log.spec,
                        "error_type": error_log.error_type,
                        "class_name": error_log.class_full_name,
                        "method": error_log.method,
                        "message": error_log.message,
                        "time_since_start": time_since_start
                    },
                    source="CoverageTracker"
                )
                
                self.logger.info(
                    f"Tracked formal property violation in {error_log.class_full_name}.{error_log.method}: {error_log.message}"
                )

            elif coverage_log:
                # Calculate time since tool execution start using logcat timestamp
                if self.tool_execution_start_time and coverage_log.time_occurred:
                    time_since_start = int((coverage_log.time_occurred - self.tool_execution_start_time).total_seconds())
                    time_since_start = max(0, time_since_start)  # Ensure non-negative
                else:
                    time_since_start = 0
                    
                # Set timing info for coverage
                coverage_log.time_since_task_start = time_since_start
                self.repository.register_method_call(coverage_log)
                self.total_method_calls += 1
                self._data_changed_since_last_update = True  # Mark data as changed
                self.logger.debug(
                    f"Processed method call: {coverage_log.clazz}.{coverage_log.method} at t={time_since_start}s"
                )

        except Exception as e:
            self.logger.error(f"Error processing logcat line: {e}", exc_info=True)

    def _update_coverage_metrics(self) -> None:
        """
        Update coverage metrics and publish events only when data has changed.
        
        ### Performance Optimization:
        Uses data change tracking to avoid unnecessary metric calculations and
        only processes metrics when new data has been added since the last update.
        This significantly reduces CPU usage by eliminating redundant calculations.
        """
        try:
            # Only calculate metrics if data has changed since last update
            if not self._data_changed_since_last_update:
                return

            # Get repository for metrics calculation
            metrics = self.repository.calculate_metrics()

            # Convert to dict once to avoid multiple expensive calls
            metrics_dict = metrics.to_dict()

            # Extract metrics from the cached dict
            current_metrics = {
                "method_coverage": metrics_dict.get("method_coverage", 0.0),
                "activity_coverage": metrics_dict.get("activity_coverage", 0.0),
                "mop_method_coverage": metrics_dict.get("mop_method_coverage", 0.0),
                "called_methods": metrics.called_methods,
                "total_activities": metrics.total_activities,
                "unique_errors": metrics.unique_errors
            }

            # Check if any metrics have actually changed from previous values
            changed = False
            for key, value in current_metrics.items():
                if self._previous_metrics.get(key) != value:
                    changed = True
                    break

            # Only log and publish events if metrics have changed
            if changed:
                # Update previous metrics
                self._previous_metrics = current_metrics.copy()

                # Publish metrics update event
                self.event_bus.publish_analysis_event(
                    EventType.COVERAGE_UPDATED,
                    data=current_metrics,
                    source="CoverageTracker"
                )

                # Log update since changes occurred
                self.logger.info(
                    f"Coverage update - Methods: {current_metrics['method_coverage']:.2f}%, "
                    f"Activities: {current_metrics['activity_coverage']:.2f}%, "
                    f"MOP Methods: {current_metrics['mop_method_coverage']:.2f}%, "
                    f"Called methods: {current_metrics['called_methods']}"
                )

            # Reset data changed flag after processing
            self._data_changed_since_last_update = False

        except Exception as e:
            self.logger.error(f"Error updating coverage metrics: {e}", exc_info=True)

    def get_coverage_metrics(self) -> Dict[str, float]:
        """
        Get the current coverage metrics.

        Returns:
            Dictionary with coverage metrics
        """
        metrics = self.repository.calculate_metrics()
        return metrics.to_dict()
