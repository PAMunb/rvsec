# rvandroid/parser/log/logcat_parser.py
"""
A comprehensive log parsing module for extracting runtime verification and coverage information from Android logcat output.

### Architectural Design:
- Implements robust parsing strategies for complex logcat log entries
- Provides flexible and extensible log parsing mechanisms
- Supports multiple parsing approaches for different log formats
- Enables detailed extraction of runtime verification events
"""

import re
from datetime import datetime
from typing import Dict, Any, Optional, Generator

from rvandroid.model.coverage import LogcatRepository
from rvandroid.model.log import RvErrorLog, RvCoverageLog, TAG_RVSEC, TAG_RVSEC_COV


def parse_logcat_file(log_file: str) -> LogcatRepository:
    """
    Parse a logcat file and extract runtime verification logs.
    Returns a standardized LogcatRepository.

    Args:
        log_file (str): Path to the logcat file

    Returns:
        LogcatRepository containing the parsed coverage data
    """
    # Initialize the repository
    repository = LogcatRepository()

    # Process log file line by line for memory efficiency
    for entry in _parse_logcat_entries(log_file):
        message = entry["message"]
        date = _convert_to_datetime(entry["date"], entry["time"])

        if entry["tag"] == TAG_RVSEC:
            error = _parse_error_message(message)
            error.time_occurred = date
            error.original_msg = entry["original"]

            # Add to repository
            repository.register_error(error)

        elif entry["tag"] == TAG_RVSEC_COV:
            coverage = _parse_coverage_message(message)
            coverage.time_occurred = date
            coverage.original_msg = entry["original"]

            # Add to repository
            repository.register_method_call(coverage)

    return repository


def stream_logcat_entries(log_file: str) -> Generator[Dict[str, Any], None, None]:
    """
    Stream logcat entries from a file as they are added.
    This allows for real-time processing of logs as they are generated.

    Args:
        log_file (str): Path to the logcat file

    Yields:
        Dictionary with parsed log entry fields
    """
    with open(log_file, 'r') as f:
        # Move to the end of the file to start processing from there
        f.seek(0, 2)  # Seek to EOF

        while True:
            line = f.readline()
            if not line:
                # No new data, yield control back temporarily
                yield None
                continue

            # Process line
            entry = _parse_logcat_line(line)
            if entry:
                yield entry


def _parse_logcat_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Parse a single logcat line.

    Args:
        line: Raw logcat line

    Returns:
        Dictionary with parsed fields or None if line cannot be parsed
    """
    pattern = r"(\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}\.\d{3})\s+(\d+)\s+(\d+)\s+(\w)\s+(\S+)\s*:\s*(.*)"
    match = re.match(pattern, line)
    if not match:
        return None

    date, time, pid, tid, level, tag, message = match.groups()
    return {
        "date": date,
        "time": time,
        "pid": pid,
        "tid": tid,
        "level": level,
        "tag": tag,
        "message": message,
        "original": line.strip()
    }


def parse_logcat_line(line: str) -> tuple[Optional[RvErrorLog], Optional[RvCoverageLog]]:
    """
    Parse a single logcat line for RVSEC or RVSEC-COV entries.

    Args:
        line: Logcat line to parse

    Returns:
        Tuple of (error_log, coverage_log) - only one will be non-None
    """
    entry = _parse_logcat_line(line)
    if not entry:
        return None, None

    tag = entry["tag"]
    message = entry["message"]

    # Parse based on the tag
    if tag == TAG_RVSEC:
        error = _parse_error_message(message)
        error.original_msg = entry["original"]
        error.time_occurred = _convert_to_datetime(entry["date"], entry["time"])
        return error, None
    elif tag == TAG_RVSEC_COV:
        coverage = _parse_coverage_message(message)
        coverage.original_msg = entry["original"]
        coverage.time_occurred = _convert_to_datetime(entry["date"], entry["time"])
        return None, coverage

    return None, None


def _parse_logcat_entries(log_file: str) -> Generator[Dict[str, Any], None, None]:
    """
    Parse individual logcat entries using regex pattern matching.
    Uses generator to process large files efficiently.

    Args:
        log_file (str): Path to the logcat file

    Yields:
        Dictionary containing parsed log entry fields
    """
    pattern = r"(\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}\.\d{3})\s+(\d+)\s+(\d+)\s+(\w)\s+(\S+)\s*:\s*(.*)"

    with open(log_file, 'r') as f:
        for line in f:
            match = re.match(pattern, line)
            if match:
                date, time, pid, tid, level, tag, message = match.groups()
                yield {
                    "date": date,
                    "time": time,
                    "pid": pid,
                    "tid": tid,
                    "level": level,
                    "tag": tag,
                    "message": message,
                    "original": line.strip()
                }


def _parse_coverage_message(signature: str) -> RvCoverageLog:
    """
    Parse a coverage log message to extract class, method and parameter information.

    Args:
        signature (str): Method signature from the log

    Returns:
        RvCoverageLog instance containing parsed information

    Raises:
        ValueError: If signature format is invalid
    """
    match = re.match(r"<([^:]+):\s+([^ ]+)\s+([^:(]+)\(([^)]*)\)>", signature)
    if not match:
        raise ValueError(f"Invalid signature format: {signature}")

    class_name, _, method_name, parameters = match.groups()
    return RvCoverageLog(class_name, method_name, parameters, signature)


def _parse_error_message(message: str) -> RvErrorLog:
    """
    Parse an error log message to extract error details.
    Enhanced version with better handling of different error formats.

    Args:
        message: Error message from the log

    Returns:
        RvErrorLog instance containing parsed error information
    """
    # First check if this is a generic "went into an error state" message
    if message.endswith("went into an error state."):
        generic = _parse_generic_spec_error(message)
        if generic:
            return RvErrorLog(
                generic["spec"],
                generic["spec"],
                generic["class"],
                generic["method"],
                generic["file_name"],
                generic["message"]
            )

    # Try to parse JCA specification error format
    parts = message.split(",")

    # Check if we have enough parts for the expected format
    if len(parts) >= 6:
        return RvErrorLog(
            parts[0],  # spec
            parts[5],  # error_type
            parts[1],  # class
            parts[3],  # method
            parts[4],  # source
            ",".join(parts[6:]) if len(parts) > 6 else "No additional message"  # message
        )

    # Fallback for malformed messages
    return RvErrorLog(
        "unknown",  # spec
        "unknown",  # error_type
        "unknown",  # class
        "unknown",  # method
        "unknown",  # source
        message  # use the whole message
    )


def _parse_generic_spec_error(log_line: str) -> Optional[Dict[str, Any]]:
    """
    Parse a generic specification error message.

    Args:
        log_line (str): Log line containing the error message

    Returns:
        Dictionary containing parsed error information or None if parsing fails
    """
    pattern = r"(.*)\.(.*)\((.*):(.*)\) ::: (.*) went into an error state."
    match = re.match(pattern, log_line)

    if match:
        class_name, method_name, file_name, line_number, spec = match.groups()
        return {
            "class": class_name,
            "method": method_name,
            "file_name": file_name,
            "line_number": int(line_number) if line_number.isdigit() else 0,
            "spec": spec,
            "message": f"{spec} went into an error state."
        }
    return None


def _convert_to_datetime(date: str, time: str) -> datetime:
    """
    Convert date and time strings from logcat format to datetime object.
    Handles year transitions intelligently.

    Args:
        date (str): Date string in MM-DD format
        time (str): Time string in HH:MM:SS.mmm format

    Returns:
        datetime object representing the parsed date and time
    """
    current_year = datetime.now().year

    # Handle edge case for year transition
    current_month = datetime.now().month
    log_month = int(date.split('-')[0])

    # If current month is January (1) and log month is December (12),
    # it means the log is from the previous year
    year = current_year - 1 if current_month == 1 and log_month == 12 else current_year

    date_format = "%Y-%m-%d %H:%M:%S.%f"
    date_str = f"{year}-{date} {time}"
    return datetime.strptime(date_str, date_format)
