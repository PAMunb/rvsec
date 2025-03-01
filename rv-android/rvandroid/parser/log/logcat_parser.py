"""
Module for parsing Android logcat output and extracting runtime verification
related logs including errors and coverage information.
"""

import re
from datetime import datetime
from typing import List, Set, Tuple, Dict, Any, Optional

from rvandroid.constants import METHODS
from rvandroid.model.log import RvErrorLog, RvCoverageLog, TAG_RVSEC, TAG_RVSEC_COV


def parse_logcat_file(log_file: str) -> Tuple[List[RvErrorLog], Dict, List[RvCoverageLog]]:
    """
    Parse a logcat file and extract runtime verification logs.
    
    Args:
        log_file (str): Path to the logcat file

    Returns:
        Tuple containing:
        - List of error logs
        - Dictionary of called methods organized by class
        - Chronologically ordered list of coverage logs
    """
    called_methods: Dict[str, Dict[str, Dict[str, RvCoverageLog]]] = {}
    methods: List[RvCoverageLog] = []
    rvsec_error_msgs: Set[str] = set()
    errors: List[RvErrorLog] = []

    for entry in _parse_logcat_entries(log_file):
        message = entry["message"]
        date = _convert_to_datetime(entry["date"], entry["time"])

        if entry["tag"] == TAG_RVSEC:
            error = _parse_error_message(message)
            error.time_occurred = date
            error.original_msg = entry["original"]

            if error.unique_msg not in rvsec_error_msgs:
                rvsec_error_msgs.add(error.unique_msg)
                errors.append(error)

        elif entry["tag"] == TAG_RVSEC_COV:
            coverage = _parse_coverage_message(message)
            if coverage.clazz not in called_methods:
                called_methods[coverage.clazz] = {METHODS: {}}

            if coverage.method not in called_methods[coverage.clazz][METHODS]:
                coverage.time_occurred = date
                coverage.original_msg = entry["original"]
                called_methods[coverage.clazz][METHODS][coverage.method] = coverage
                methods.append(coverage)

    return errors, called_methods, sorted(methods, key=lambda x: x.time_occurred)


def _parse_logcat_entries(log_file: str) -> Dict:
    """
    Parse individual logcat entries using regex pattern matching.
    
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
    match = re.match(r"<([^:]+):\s+([^:]+)\(([^)]*)\)>", signature)
    if not match:
        raise ValueError(f"Invalid signature format: {signature}")

    class_name, method_name, parameters = match.groups()
    return RvCoverageLog(class_name, method_name, parameters, signature)


def _parse_error_message(message: str) -> RvErrorLog:
    """
    Parse an error log message to extract error details.
    
    Args:
        message (str): Error message from the log

    Returns:
        RvErrorLog instance containing parsed error information
    """
    if message.endswith("went into an error state."):
        generic = _parse_generic_spec_error(message)
        return RvErrorLog(
            generic["spec"],
            generic["spec"],
            generic["class"],
            generic["method"],
            generic["file_name"],
            generic["message"]
        )
    else:
        # JCA specification error format
        parts = message.split(",")
        return RvErrorLog(
            parts[0],  # spec
            parts[5],  # error_type
            parts[1],  # class
            parts[3],  # method
            parts[4],  # source
            " ".join(parts[6:])  # message
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
            "line_number": int(line_number),
            "spec": spec,
            "message": f"{spec} went into an error state."
        }
    return None


def _convert_to_datetime(date: str, time: str) -> datetime:
    """
    Convert date and time strings from logcat format to datetime object.
    
    Args:
        date (str): Date string in MM-DD format
        time (str): Time string in HH:MM:SS.mmm format

    Returns:
        datetime object representing the parsed date and time
    """
    year = datetime.now().year
    # Handle edge case for year transition
    if year == 2025:
        year = 2024

    date_format = "%Y-%m-%d %H:%M:%S.%f"
    date_str = f"{year}-{date} {time}"
    return datetime.strptime(date_str, date_format)
