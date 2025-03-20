# rvandroid/analysis/coverage_tracker.py
import logging
import os
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, Optional, List

from rvandroid.model.coverage import LogcatRepository
from rvandroid.model.log import RvCoverageLog, RvErrorLog
from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.log.logcat_parser import parse_logcat_line


class CoverageTracker:
    """
    A real-time coverage tracking system for monitoring method execution during testing.

    ### Architectural Decisions:
    - Implements thread-safe, event-driven coverage tracking
    - Uses efficient parsing and storage mechanisms
    - Supports real-time and post-execution coverage analysis
    - Provides standardized coverage metric calculation

    ### Role in the System:
    - Captures and processes runtime method execution data
    - Tracks code coverage during Android application testing
    - Generates comprehensive coverage metrics
    - Supports both live and retrospective coverage analysis
    """

    def __init__(self, logcat_file: str, static_data: Optional[StaticAnalysisData] = None):
        self.logger = logging.getLogger(__name__)
        self.logcat_file = logcat_file
        self.static_data = static_data

        # Repository for standardized coverage data - the single source of truth
        self.repository = LogcatRepository()

        # Running state
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Add a reader lock to prevent concurrent file access
        self._reader_lock = threading.RLock()

        # Metrics
        self.last_update_time = datetime.now()
        self.total_errors = 0
        self.total_method_calls = 0

        # Initialize repository from static_data if available
        if static_data and static_data.classes:
            self._initialize_from_static_data()

    def _initialize_from_static_data(self):
        """Initialize repository from static analysis data."""
        try:
            self.logger.info("Initializing coverage tracker from static analysis data")

            # Initialize classes and methods from static data
            classes = self.static_data.classes

            for class_name, class_info in classes.classes.items():
                # Create class data in repository
                from rvandroid.model.coverage import ClassCoverageData
                class_data = ClassCoverageData(
                    name=class_name,
                    is_activity=class_info.is_activity,
                    is_main_activity=getattr(class_info, "is_main_activity", False)
                )
                self.repository.add_class(class_data)

                # Add methods to class
                for method in class_info.methods:
                    from rvandroid.model.coverage import MethodCoverageData
                    method_data = MethodCoverageData(
                        class_name=class_name,
                        method_name=method.name,
                        signature=method.signature,
                        parameters=getattr(method, "params", []),
                        reachable=method.reachable,
                        reaches_mop=method.reaches_mop,
                        directly_reaches_mop=method.directly_reaches_mop
                    )
                    class_data.add_method(method_data)

            self.logger.info(f"Initialized repository with {len(self.repository.classes)} classes from static data")

        except Exception as e:
            self.logger.error(f"Error initializing from static data: {e}", exc_info=True)

    def start(self):
        """Start tracking coverage in a separate thread with improved resource management."""
        if self.is_running:
            self.logger.warning("Coverage tracker is already running")
            return

        # Make sure the logcat file exists
        try:
            parent_dir = os.path.dirname(self.logcat_file)
            if not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)

            # Create empty logcat file if it doesn't exist
            if not os.path.exists(self.logcat_file):
                with open(self.logcat_file, 'w'):
                    pass

            # Reset tracking state
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

    def stop(self):
        """Stop tracking coverage with proper resource cleanup."""
        if not self.is_running:
            return

        try:
            self._stop_event.set()

            if self.thread:
                # Give the thread a chance to terminate gracefully
                self.thread.join(timeout=5.0)

                # Check if thread is still alive
                if self.thread.is_alive():
                    self.logger.warning("Coverage tracker thread did not terminate gracefully")

            self.is_running = False
            self.logger.info("Coverage tracker stopped")

        except Exception as e:
            self.logger.error(f"Error stopping coverage tracker: {e}")
            self.is_running = False

    def _track_coverage(self):
        """Track coverage with improved file handling and error handling."""
        file_handle = None

        try:
            # Open the logcat file for reading
            with open(self.logcat_file, 'r') as f:
                file_handle = f

                # Process existing lines
                with self._reader_lock:
                    self.process_lines(f.readlines())

                # Move to the end of the file
                f.seek(0, os.SEEK_END)

                # Keep reading until stopped
                while not self._stop_event.is_set():
                    # Read any new lines with proper locking
                    with self._reader_lock:
                        new_lines = f.readlines()

                    # Process new lines
                    if new_lines:
                        self.process_lines(new_lines)

                    # Update coverage metrics periodically
                    if (datetime.now() - self.last_update_time).total_seconds() >= 5:
                        self._update_coverage_metrics()
                        self.last_update_time = datetime.now()

                    # Sleep briefly to avoid busy waiting
                    time.sleep(0.2)

        except Exception as e:
            self.logger.error(f"Error tracking coverage: {e}", exc_info=True)

        finally:
            self.is_running = False

            # Properly close the file handle if we opened it directly
            if file_handle and not file_handle.closed:
                try:
                    file_handle.close()
                except Exception:
                    pass

    @contextmanager
    def track_coverage(self):
        """
        Context manager for tracking coverage.
        Ensures the tracker is properly stopped even if an error occurs.

        Yields:
            Self for use within the context
        """
        self.start()
        try:
            yield self
        finally:
            self.stop()

    def process_lines(self, lines: List[str]):
        """
        Process lines from the logcat file.

        Args:
            lines: List of logcat lines
        """
        for line in lines:
            try:
                # Skip empty lines
                if not line.strip():
                    continue

                # Parse the line for RVSEC or RVSEC-COV entries
                error_log, coverage_log = parse_logcat_line(line)

                if error_log:
                    self._handle_error_log(error_log)
                elif coverage_log:
                    self._handle_coverage_log(coverage_log)

            except Exception as e:
                self.logger.error(f"Error processing line: {e}", exc_info=True)

    def _handle_coverage_log(self, coverage: RvCoverageLog):
        """
        Handle an RVSEC-COV log entry.

        Args:
            coverage: Parsed coverage log entry
        """
        try:
            # Add to the repository
            self.repository.register_method_call(coverage)
            self.total_method_calls += 1

            # Log that we tracked a method call
            self.logger.debug(
                f"Tracked method call: {coverage.clazz}.{coverage.method} (signature: {coverage.signature})"
            )

        except Exception as e:
            self.logger.error(f"Error handling RVSEC-COV log: {e}", exc_info=True)

    def _handle_error_log(self, error: RvErrorLog):
        """
        Handle an RVSEC log entry for a formal property violation.

        IMPORTANT: This method only processes runtime verification errors
        (formal property violations), not general system errors or exceptions.

        Args:
            error: Parsed runtime verification error log entry
        """
        try:
            # Update the repository
            self.repository.register_error(error)
            self.total_errors += 1

            # Log that we found a property violation
            self.logger.debug(
                f"Tracked formal property violation in {error.class_full_name}.{error.method}: "
                f"Specification '{error.spec}' was violated - {error.message}"
            )

        except Exception as e:
            self.logger.error(f"Error handling RVSEC log: {e}", exc_info=True)

    def _update_coverage_metrics(self):
        """Update coverage metrics based on current tracking data."""
        try:
            # Skip if repository is empty
            if not self.repository.classes:
                self.logger.warning("No coverage data available for metrics calculation")
                return

            # Calculate metrics using the repository
            metrics = self.repository.calculate_metrics()
            metrics_dict = metrics.to_dict()

            # Log coverage summary
            self.logger.info(
                f"Coverage update - Methods: {metrics_dict['method_coverage']:.2f}%, "
                f"Activities: {metrics_dict['activity_coverage']:.2f}%, "
                f"MOP Methods: {metrics_dict['mop_method_coverage']:.2f}%, "
                f"Called methods: {metrics.called_methods}, "
                f"Total methods: {metrics.total_methods}"
            )

        except Exception as e:
            self.logger.error(f"Error updating coverage metrics: {e}", exc_info=True)

    def get_coverage_metrics(self) -> Dict[str, float]:
        """
        Get the current coverage metrics.

        Returns:
            Dictionary of coverage metrics
        """
        # Get metrics from repository
        metrics_dict = self.repository.calculate_metrics().to_dict()

        return {
            "method_coverage": metrics_dict.get("method_coverage", 0),
            "activities_coverage": metrics_dict.get("activity_coverage", 0),
            "methods_jca_reachable_coverage": metrics_dict.get("mop_method_coverage", 0),
            "total_errors": metrics_dict.get("unique_errors", 0),
            "total_method_calls": metrics_dict.get("called_methods", 0)
        }
