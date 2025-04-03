# rvandroid/analysis/coverage/tracker.py
import os
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, List, Dict

from rvandroid.analysis.coverage.repository import CoverageRepository
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.experiment.event.bus import EventBus, EventType
from rvandroid.parser.log.logcat_parser import parse_logcat_line
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class CoverageTracker:
    """
    Tracks code coverage during test execution.
    Processes logcat output to extract coverage information.

    ### Architectural Decisions:
    - Separates coverage tracking from data storage
    - Uses event-driven architecture for real-time updates
    - Leverages standardized repository pattern for data management
    - Integrates with the unified analysis component structure

    ### Role in the System:
    - Monitors method execution in real-time
    - Extracts coverage data from logcat output
    - Updates repository with coverage information
    - Publishes coverage events for monitoring
    - Provides metrics for the unified result system
    """

    def __init__(self, logcat_file: str, static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the coverage tracker.

        Args:
            logcat_file: Path to the logcat file to monitor
            static_data: Optional static analysis data
        """
        self.logcat_file = logcat_file
        self.static_data = static_data

        # Set up logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            'analysis.coverage.tracker',
            {CONTEXT_COMPONENT: 'CoverageTracker'}
        )

        # Initialize repository
        self.repository = CoverageRepository()

        # Get the core repository for direct operations
        self.core_repository = self.repository.get_underlying_repository()

        # Event bus for publishing events
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

        # Track previous metrics for change detection
        self._previous_metrics = {
            "method_coverage": 0.0,
            "activity_coverage": 0.0,
            "mop_method_coverage": 0.0,
            "called_methods": 0,
            "total_activities": 0,
            "unique_errors": 0
        }

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
                from rvandroid.domain.coverage import ClassCoverageData
                class_data = ClassCoverageData(
                    name=class_name,
                    is_activity=class_info.is_activity,
                    is_main_activity=getattr(class_info, "is_main_activity", False)
                )

                # Add to repository
                self.core_repository.add_class(class_data)

                # Add methods to class
                for method in class_info.methods:
                    from rvandroid.domain.coverage import MethodCoverageData
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
                f"Initialized repository with {len(self.core_repository.classes)} classes "
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

                    # Process new lines
                    if new_lines:
                        self.process_lines(new_lines)

                    # Update metrics periodically
                    if (datetime.now() - self.last_update_time).total_seconds() >= 5:
                        self._update_coverage_metrics()
                        self.last_update_time = datetime.now()

                    # Sleep to avoid busy waiting
                    time.sleep(0.2)

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
                self.repository.register_error(error_log)
                self.total_errors += 1
                self.logger.info(
                    f"Tracked formal property violation in {error_log.class_full_name}.{error_log.method}: {error_log.message}"
                )

            elif coverage_log:
                self.repository.register_method_call(coverage_log)
                self.total_method_calls += 1
                self.logger.debug(
                    f"Processed method call: {coverage_log.clazz}.{coverage_log.method}"
                )

        except Exception as e:
            self.logger.error(f"Error processing logcat line: {e}", exc_info=True)

    def _update_coverage_metrics(self) -> None:
        """Update coverage metrics and publish events only when metrics change."""
        try:
            # Get repository for metrics calculation
            metrics = self.repository.calculate_metrics()

            # Extract metrics from the metrics object
            current_metrics = {
                "method_coverage": metrics.to_dict().get("method_coverage", 0.0),
                "activity_coverage": metrics.to_dict().get("activity_coverage", 0.0),
                "mop_method_coverage": metrics.to_dict().get("mop_method_coverage", 0.0),
                "called_methods": metrics.called_methods,
                "total_activities": metrics.total_activities,
                "unique_errors": metrics.unique_errors
            }

            # Check if any metrics have changed
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

        except Exception as e:
            self.logger.error(f"Error updating coverage metrics: {e}", exc_info=True)

    def get_coverage_metrics(self) -> Dict[str, float]:
        """
        Get the current coverage metrics.

        Returns:
            Dictionary with coverage metrics
        """
        return self.repository.get_metrics()
