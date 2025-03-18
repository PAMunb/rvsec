# rvandroid/analysis/coverage_tracker.py
"""
Real-time coverage tracking for task execution.
Monitors logcat file for RVSEC and RVSEC-COV entries and updates coverage metrics.
"""
import logging
import os
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, List, Optional, Set

from rvandroid.analysis.coverage import process_coverage
from rvandroid.model.coverage import CoverageRepository
from rvandroid.model.log import RvCoverageLog, RvErrorLog
from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.log.logcat_parser import (
    parse_logcat_line
)


class CoverageTracker:
    """
    Tracks code coverage in real-time by monitoring the logcat file.

    This class monitors the logcat file for RVSEC and RVSEC-COV entries during
    task execution and updates coverage metrics accordingly.
    """

    def __init__(self, logcat_file: str, static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the coverage tracker.

        Args:
            logcat_file: Path to the logcat file
            static_data: Static analysis data for the app
        """
        self.logger = logging.getLogger(__name__)
        self.logcat_file = logcat_file
        self.static_data = static_data

        # Repository for standardized coverage data
        self.repository = CoverageRepository()

        # Legacy data structures for backward compatibility
        self.all_methods: Dict = {}
        self.called_methods: Dict[str, Dict[str, Dict[str, RvCoverageLog]]] = {}
        self.class_methods: Dict[str, List[RvCoverageLog]] = {}
        self.formatted_methods: Dict[str, Dict[str, Dict[str, RvCoverageLog]]] = {}
        self.coverage: Dict = {}
        self.errors: List[RvErrorLog] = []

        # Running state
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Add a reader lock to prevent concurrent file access
        self._reader_lock = threading.RLock()
        self._stop_event = threading.Event()

        # Tracking sets for unique entries
        self.seen_errors: Set[str] = set()
        self.seen_method_calls: Dict[str, Set[str]] = {}

        # Metrics
        self.last_update_time = datetime.now()
        self.total_errors = 0
        self.total_method_calls = 0

        # Initialize all_methods from static_data if available
        print(f"static_data={static_data}")
        print(f"static_data.classes={static_data.classes}")
        if static_data and static_data.classes:
            self._initialize_from_static_data()

    def _initialize_from_static_data(self):
        """Initialize tracking data from static analysis data."""
        try:
            self.logger.info("Initializing coverage tracker from static analysis data")

            # Initialize classes and methods from static data
            classes = self.static_data.classes
            print(f"******* classes={classes}")
            for clazz in classes.classes:
                print(f"CLASS={clazz}")

            self.all_methods = {}
            for class_name, class_info in classes.classes.items():
                print(f"CLASS={class_name}")
                self.all_methods[class_name] = {
                    "is_activity": class_info.is_activity,
                    "methods": {}
                }

                # Initialize method tracking for this class
                self.seen_method_calls[class_name] = set()

                # Add methods from class
                for method in class_info.methods:
                    print(f"  --- {method.signature}")
                    self.all_methods[class_name]["methods"][method.signature] = {
                        "reachable": method.reachable,
                        "reaches_mop": method.reaches_mop,
                        "directly_reaches_mop": method.directly_reaches_mop,
                        "called": False
                    }

                    # Also add to the repository
                    class_data = self.repository.get_class(class_name)
                    if not class_data:
                        from rvandroid.model.coverage import ClassCoverageData
                        class_data = ClassCoverageData(
                            name=class_name,
                            is_activity=class_info.is_activity,
                            is_main_activity=class_info.is_main_activity
                        )
                        self.repository.add_class(class_data)

                    from rvandroid.model.coverage import MethodCoverageData
                    method_data = MethodCoverageData(
                        class_name=class_name,
                        method_name=method.name,
                        signature=method.signature,
                        parameters=method.params,
                        reachable=method.reachable,
                        reaches_mop=method.reaches_mop,
                        directly_reaches_mop=method.directly_reaches_mop
                    )
                    class_data.add_method(method_data)

            self.logger.info(f"Initialized tracking for {len(self.all_methods)} classes from static data")

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

                # print(f"line: {line}")

                # Parse the line for RVSEC or RVSEC-COV entries
                error_log, coverage_log = parse_logcat_line(line)
                # print(f"error_log={error_log}")
                # print(f"coverage_log={coverage_log}")

                if error_log:
                    self._handle_error_log(error_log)
                elif coverage_log:
                    self._handle_coverage_log(coverage_log)

            except Exception as e:
                self.logger.error(f"Error processing line: {e}", exc_info=True)

    def _handle_error_log(self, error: RvErrorLog):
        """
        Handle an RVSEC log entry.

        Args:
            error: Parsed error log entry
        """
        try:
            # Skip if we've already seen this error
            if error.unique_msg in self.seen_errors:
                return

            # Add to seen errors and tracked errors
            self.seen_errors.add(error.unique_msg)
            self.errors.append(error)
            self.total_errors += 1

            # Add to the repository
            self.repository.register_error(error)

            # Log that we found an error
            self.logger.debug(f"Tracked error in {error.class_full_name}.{error.method}: {error.message}")

        except Exception as e:
            self.logger.error(f"Error handling RVSEC log: {e}", exc_info=True)

    def _handle_coverage_log(self, coverage: RvCoverageLog):
        """
        Handle an RVSEC-COV log entry.

        Args:
            coverage: Parsed coverage log entry
        """
        try:
            # print(f"self.class_methods={self.class_methods}")
            # print(f"coverage.clazz={coverage.clazz}")
            # Initialize tracking structures if needed
            if coverage.clazz not in self.class_methods:
                self.class_methods[coverage.clazz] = []
                self.seen_method_calls[coverage.clazz] = set()

            # Skip if we've already seen this method signature
            if coverage.signature in self.seen_method_calls[coverage.clazz]:
                return

            # Add to seen method signatures
            self.seen_method_calls[coverage.clazz].add(coverage.signature)

            # Add to the class's method list
            self.class_methods[coverage.clazz].append(coverage)
            self.total_method_calls += 1

            # Add to the repository
            self.repository.register_method_call(coverage)

            # Update static data called status
            if (self.all_methods and coverage.clazz in self.all_methods and
                    coverage.signature in self.all_methods[coverage.clazz]["methods"]):
                self.all_methods[coverage.clazz]["methods"][coverage.signature]["called"] = True

            # Log that we tracked a method call
            self.logger.debug(
                f"Tracked method call: {coverage.clazz}.{coverage.method} (signature: {coverage.signature})"
            )

        except Exception as e:
            self.logger.error(f"Error handling RVSEC-COV log: {e}", exc_info=True)

    def _update_coverage_metrics(self):
        """Update coverage metrics based on current tracking data."""
        try:
            print(f"self.all_methods={self.all_methods}")
            # Skip if we don't have static data or all_methods
            if not self.all_methods:
                self.logger.warning("No static data available for coverage calculation")
                return

            # Update metrics using the repository
            metrics = self.repository.calculate_metrics()

            # Log the number of tracked methods for debugging
            method_count = sum(len(methods) for methods in self.class_methods.values())
            self.logger.debug(f"Updating coverage metrics with {method_count} tracked methods")

            # Convert class_methods to the format expected by process_coverage
            self.formatted_methods = {}
            for class_name, method_logs in self.class_methods.items():
                if not method_logs:
                    continue

                # Initialize class structure
                if class_name not in self.formatted_methods:
                    self.formatted_methods[class_name] = {"methods": {}}

                # Add each method with signature as key
                for log in method_logs:
                    self.formatted_methods[class_name]["methods"][log.signature] = log

                # Log the number of methods for this class
                self.logger.debug(f"Class {class_name}: {len(self.formatted_methods[class_name]['methods'])} methods")

            # Process coverage using the existing function for backward compatibility
            self.coverage = process_coverage(self.formatted_methods, self.all_methods)

            # Log coverage summary
            self.logger.info(
                f"Coverage update - Methods: {metrics.to_dict()['method_coverage']:.2f}%, "
                f"Activities: {metrics.to_dict()['activity_coverage']:.2f}%, "
                f"MOP Methods: {metrics.to_dict()['mop_method_coverage']:.2f}%, "
                f"Called methods: {self.total_method_calls}, "
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
        metrics_dict = self.repository.calculate_metrics().to_dict()

        # For backward compatibility
        summary = self.coverage.get("SUMMARY", {})

        return {
            "method_coverage": metrics_dict["method_coverage"],
            "activities_coverage": metrics_dict["activity_coverage"],
            "activities_coverage_total": summary.get("activities_coverage_total", 0),
            "methods_jca_reachable_coverage": metrics_dict["mop_method_coverage"],
            "methods_jca_reachable_coverage_total": summary.get("methods_jca_reachable_coverage_total", 0),
            "total_errors": self.total_errors,
            "total_method_calls": self.total_method_calls
        }
