# rvandroid/util/spreadsheet_exporter.py

import csv
import logging
import os
from datetime import datetime

from rvandroid.experiment.task.task_model import Task
from rvandroid.domain.coverage import LogcatRepository


class ExportContext:
    """
    Contains metadata about the experiment for use in export operations.

    This class encapsulates contextual information needed when exporting
    data, such as APK details, repetition number, and tool information.
    """

    def __init__(self,
                 apk_name: str,
                 repetition: int,
                 timeout: int,
                 tool_name: str):
        """
        Initialize the export context.

        Args:
            apk_name: Name of the APK being tested
            repetition: Repetition number of the experiment
            timeout: Timeout value in seconds
            tool_name: Name of the testing tool used
        """
        self.apk_name = apk_name
        self.repetition = repetition
        self.timeout = timeout
        self.tool_name = tool_name
        self.timestamp = datetime.now()

    @classmethod
    def from_task(cls, task: Task) -> 'ExportContext':
        """
        Create an ExportContext from a Task instance.

        Args:
            task: The task containing experiment metadata

        Returns:
            An ExportContext initialized with task data
        """
        return cls(
            apk_name=task.config.apk_name,
            repetition=task.config.repetition,
            timeout=task.config.timeout,
            tool_name=task.config.tool_name
        )


class SpreadsheetExporter:
    """
    Exports data from the repository to spreadsheet files.

    This class is responsible for exporting coverage and error data
    from a LogcatRepository to CSV files for further analysis.
    """

    def __init__(self):
        """Initialize the spreadsheet exporter."""
        self.logger = logging.getLogger(__name__)

    def export_coverage_data(self,
                             repository: LogcatRepository,
                             context: ExportContext,
                             output_file: str) -> bool:
        """
        Export coverage data to a new CSV file.

        Args:
            repository: The repository containing the data to export
            context: The context providing experiment metadata
            output_file: Path to the output CSV file

        Returns:
            True if export was successful, False otherwise
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            # Get metrics for coverage percentages
            metrics = repository.calculate_metrics().to_dict()

            # Prepare data rows
            rows = []

            # Process each class and its methods
            for class_name, class_data in repository.classes.items():
                for method_signature, method_data in class_data.methods.items():
                    # Skip methods that weren't called
                    if not method_data.called:
                        continue

                    # Add row for each called method
                    row = {
                        'apk': context.apk_name,
                        'rep': context.repetition,
                        'timeout': context.timeout,
                        'tool': context.tool_name,
                        'time': self._format_timestamp(method_data.last_called_at or context.timestamp),
                        'class': class_name,
                        'method': method_data.method_name,
                        'signature': method_signature,
                        'cov_class': metrics.get('class_coverage', 0),
                        'cov_act': metrics.get('activity_coverage', 0),
                        'cov_method': metrics.get('method_coverage', 0),
                        'cov_rv_method': metrics.get('mop_method_coverage', 0)
                    }
                    rows.append(row)

            # Write to CSV file
            with open(output_file, 'w', newline='') as f:
                if not rows:
                    self.logger.warning(f"No coverage data to export to {output_file}")
                    # Write header only
                    writer = csv.DictWriter(f, fieldnames=[
                        'apk', 'rep', 'timeout', 'tool', 'time', 'class', 'method',
                        'signature', 'cov_class', 'cov_act', 'cov_method', 'cov_rv_method'
                    ])
                    writer.writeheader()
                else:
                    # Write data
                    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                    writer.writeheader()
                    writer.writerows(rows)

            self.logger.info(f"Exported {len(rows)} coverage entries to {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Error exporting coverage data: {e}", exc_info=True)
            return False

    def export_error_data(self,
                          repository: LogcatRepository,
                          context: ExportContext,
                          output_file: str) -> bool:
        """
        Export runtime verification error data to a new CSV file.

        Args:
            repository: The repository containing the data to export
            context: The context providing experiment metadata
            output_file: Path to the output CSV file

        Returns:
            True if export was successful, False otherwise
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            # Prepare data rows
            rows = []

            # Process each error
            for error in repository.errors:
                row = {
                    'apk': context.apk_name,
                    'rep': context.repetition,
                    'timeout': context.timeout,
                    'tool': context.tool_name,
                    'time': self._format_timestamp(error.time_occurred),
                    'spec': error.spec,
                    'class': error.class_full_name,
                    'method': error.method,
                    'message': error.message,
                    'unique_msg': error.unique_msg,
                    'signature': f"{error.class_full_name}.{error.method}"
                }
                rows.append(row)

            # Write to CSV file
            with open(output_file, 'w', newline='') as f:
                if not rows:
                    self.logger.warning(f"No error data to export to {output_file}")
                    # Write header only
                    writer = csv.DictWriter(f, fieldnames=[
                        'apk', 'rep', 'timeout', 'tool', 'time', 'spec', 'class',
                        'method', 'message', 'unique_msg', 'signature'
                    ])
                    writer.writeheader()
                else:
                    # Write data
                    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                    writer.writeheader()
                    writer.writerows(rows)

            self.logger.info(f"Exported {len(rows)} error entries to {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Error exporting error data: {e}", exc_info=True)
            return False

    def append_to_coverage_sheet(self,
                                 repository: LogcatRepository,
                                 context: ExportContext,
                                 output_file: str) -> bool:
        """
        Append coverage data to an existing CSV file.

        Args:
            repository: The repository containing the data to export
            context: The context providing experiment metadata
            output_file: Path to the output CSV file

        Returns:
            True if append was successful, False otherwise
        """
        try:
            # Create file if it doesn't exist
            file_exists = os.path.exists(output_file)
            if not file_exists:
                return self.export_coverage_data(repository, context, output_file)

            # Get metrics for coverage percentages
            metrics = repository.calculate_metrics().to_dict()

            # Prepare data rows
            rows = []

            # Process each class and its methods
            for class_name, class_data in repository.classes.items():
                for method_signature, method_data in class_data.methods.items():
                    # Skip methods that weren't called
                    if not method_data.called:
                        continue

                    # Add row for each called method
                    row = {
                        'apk': context.apk_name,
                        'rep': context.repetition,
                        'timeout': context.timeout,
                        'tool': context.tool_name,
                        'time': self._format_timestamp(method_data.last_called_at or context.timestamp),
                        'class': class_name,
                        'method': method_data.method_name,
                        'signature': method_signature,
                        'cov_class': metrics.get('class_coverage', 0),
                        'cov_act': metrics.get('activity_coverage', 0),
                        'cov_method': metrics.get('method_coverage', 0),
                        'cov_rv_method': metrics.get('mop_method_coverage', 0)
                    }
                    rows.append(row)

            # Get fieldnames from existing file
            with open(output_file, 'r', newline='') as f:
                reader = csv.reader(f)
                fieldnames = next(reader)  # Read header row

            # Append to CSV file
            with open(output_file, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writerows(rows)

            self.logger.info(f"Appended {len(rows)} coverage entries to {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Error appending to coverage sheet: {e}", exc_info=True)
            return False

    def append_to_error_sheet(self,
                              repository: LogcatRepository,
                              context: ExportContext,
                              output_file: str) -> bool:
        """
        Append runtime verification error data to an existing CSV file.

        Args:
            repository: The repository containing the data to export
            context: The context providing experiment metadata
            output_file: Path to the output CSV file

        Returns:
            True if append was successful, False otherwise
        """
        try:
            # Create file if it doesn't exist
            file_exists = os.path.exists(output_file)
            if not file_exists:
                return self.export_error_data(repository, context, output_file)

            # Prepare data rows
            rows = []

            # Process each error
            for error in repository.errors:
                row = {
                    'apk': context.apk_name,
                    'rep': context.repetition,
                    'timeout': context.timeout,
                    'tool': context.tool_name,
                    'time': self._format_timestamp(error.time_occurred),
                    'spec': error.spec,
                    'class': error.class_full_name,
                    'method': error.method,
                    'message': error.message,
                    'unique_msg': error.unique_msg,
                    'signature': f"{error.class_full_name}.{error.method}"
                }
                rows.append(row)

            # Get fieldnames from existing file
            with open(output_file, 'r', newline='') as f:
                reader = csv.reader(f)
                fieldnames = next(reader)  # Read header row

            # Append to CSV file
            with open(output_file, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writerows(rows)

            self.logger.info(f"Appended {len(rows)} error entries to {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Error appending to error sheet: {e}", exc_info=True)
            return False

    def _format_timestamp(self, timestamp: datetime) -> str:
        """
        Format a timestamp for inclusion in the CSV.

        Args:
            timestamp: Datetime object to format

        Returns:
            Formatted timestamp string
        """
        return timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
