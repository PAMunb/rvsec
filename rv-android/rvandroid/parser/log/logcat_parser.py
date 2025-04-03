# rvandroid/parser/log/logcat_parser.py
"""
A comprehensive log parsing module for extracting runtime verification and coverage information from Android logcat output.

### Architectural Design:
- Implements robust parsing strategies for complex logcat log entries
- Provides flexible and extensible log parsing mechanisms
- Supports multiple parsing approaches for different log formats
- Enables detailed extraction of runtime verification events
"""

import logging
import re
from datetime import datetime
from typing import Dict, Any, Optional, Generator
from typing import Tuple

from rvandroid.domain.coverage import LogcatRepository
from rvandroid.domain.log import RvErrorLog, RvCoverageLog, TAG_RVSEC, TAG_RVSEC_COV


def parse_logcat_file(log_file: str, static_data=None) -> LogcatRepository:
    """
    Parse a logcat file and extract runtime verification logs.
    Returns a standardized LogcatRepository.

    Args:
        log_file (str): Path to the logcat file
        static_data: Optional static analysis data to initialize the repository

    Returns:
        LogcatRepository containing the parsed coverage data
    """
    # Initialize the repository
    repository = LogcatRepository()
    logger = logging.getLogger(__name__)

    # Initialize repository with static data if provided
    if static_data and hasattr(static_data, 'classes'):
        logger.debug("Initializing repository with static analysis data")
        _initialize_repository_from_static_data(repository, static_data)

    # Process log file line by line for memory efficiency
    try:
        with open(log_file, 'r') as f:
            for line in f:
                error_log, coverage_log = parse_logcat_line(line)

                if error_log:
                    repository.register_rv_error(error_log)
                elif coverage_log:
                    repository.register_method_call(coverage_log)
    except Exception as e:
        logger.error(f"Error parsing logcat file {log_file}: {e}", exc_info=True)

    return repository


def _initialize_repository_from_static_data(repository: LogcatRepository, static_data) -> None:
    """
    Initialize repository with data from static analysis.
    
    Args:
        repository: LogcatRepository instance to initialize
        static_data: Static analysis data
    """
    try:
        # Process classes from static data
        classes = static_data.classes
        for class_name, class_info in classes.classes.items():
            # Create class in repository
            from rvandroid.domain.coverage import ClassCoverageData
            class_data = ClassCoverageData(
                name=class_name,
                is_activity=class_info.is_activity,
                is_main_activity=getattr(class_info, "is_main_activity", False)
            )

            # Add to repository
            repository.add_class(class_data)

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

    except Exception as e:
        logging.getLogger(__name__).error(f"Error initializing from static data: {e}", exc_info=True)


def stream_logcat_entries(log_file: str) -> Generator[Dict[str, Any], None, None]:
    """
    Stream logcat entries from a file as they are added.
    This allows for real-time processing of logs as they are generated.

    Args:
        log_file (str): Path to the logcat file

    Yields:
        Dictionary with parsed log entry fields or None if no new entries
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


def parse_logcat_line(line: str) -> Tuple[Optional[RvErrorLog], Optional[RvCoverageLog]]:
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
        if error:
            error.original_msg = entry["original"]
            error.time_occurred = _convert_to_datetime(entry["date"], entry["time"])
            return error, None
    elif tag == TAG_RVSEC_COV:
        coverage = _parse_coverage_message(message)
        if coverage:
            coverage.original_msg = entry["original"]
            coverage.time_occurred = _convert_to_datetime(entry["date"], entry["time"])
            return None, coverage

    return None, None


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


def _parse_error_message(message: str) -> Optional[RvErrorLog]:
    """
    Parse an error log message to extract error details.
    Enhanced version with better handling of different error formats.

    Args:
        message: Error message from the log

    Returns:
        RvErrorLog instance containing parsed error information or None if parsing fails
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

    # Alternative format with ::: separator (FSM format)
    if ":::" in message:
        split = message.split(":::")
        if len(split) >= 2:
            tmp = split[0]
            tmp = tmp[:tmp.find("(") if "(" in tmp else len(tmp)]
            dot_idx = tmp.rfind(".")
            if dot_idx != -1:
                clazz = tmp[:dot_idx]
                method = tmp[dot_idx + 1:]
                message_text = split[1].strip()
                spec = message_text.split(" ")[0]
                return RvErrorLog(spec, spec, clazz, method, "Unknown Source:1", message_text)

    # Fallback for malformed messages - log warning instead of creating malformed data
    logging.getLogger(__name__).warning(f"Failed to parse error message: {message}")
    return None


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


def _parse_coverage_message(message: str) -> Optional[RvCoverageLog]:
    """
    Parse a coverage log message to extract class, method and parameter information.

    Args:
        message (str): Method signature from the log

    Returns:
        RvCoverageLog instance containing parsed information or None if parsing fails
    """
    # First try the modern format with angle brackets
    match = re.match(r"<([^:]+):\s+([^ ]+)\s+([^:(]+)\(([^)]*)\)>", message)
    if match:
        class_name, return_type, method_name, parameters = match.groups()
        return RvCoverageLog(class_name, method_name, parameters, message)

    # Try the legacy format with ::: separators
    parts = message.split(":::")
    if len(parts) >= 2:
        class_name = parts[0].strip()
        method_name = parts[1].strip()
        params = parts[2].strip() if len(parts) > 2 else ""
        return RvCoverageLog(class_name, method_name, params, message)

    # Fallback for malformed messages - log warning instead of creating malformed data
    logging.getLogger(__name__).warning(f"Failed to parse coverage message: {message}")
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
