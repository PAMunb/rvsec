"""
Parse Android logcat output for runtime verification and coverage data.

Extract RVSEC (property violation) and RVSEC-COV (method coverage) entries
from standard Android logcat format, producing typed domain objects
(RvErrorLog, RvCoverageLog) stored in a LogcatRepository.

### Role in the System:
Entry point for all logcat data in rv-coverage. Both CoverageTracker
(real-time) and CoverageAnalyzer (batch) delegate line-level parsing here.

### Key Features:
- Three error formats: JCA comma-separated, FSM ``:::``, generic spec error
- Two coverage formats: modern angle-bracket signatures, legacy ``:::``
- Year-aware timestamp conversion handling December/January transitions
- Memory-efficient line-by-line file processing

### Integration Points:
- RvErrorLog / RvCoverageLog (rv-android-core): domain model output
- LogcatRepository (rv-android-core): repository populated by parse_logcat_file
- CoverageTracker: calls parse_logcat_line per line in real-time
- CoverageAnalyzer: calls parse_logcat_file for batch processing
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from rv_android_core.domain.coverage import LogcatRepository
from rv_android_core.domain.log import (
    TAG_RVSEC,
    TAG_RVSEC_COV,
    RvCoverageLog,
    RvErrorLog,
)
from rv_android_core.util.android.repository_initializer import (
    initialize_repository_from_static_data,
)


def parse_logcat_file(log_file: str, static_data=None) -> LogcatRepository:
    """
    Parse a logcat file and return a populated LogcatRepository.

    Read the file line-by-line for memory efficiency, extracting all RVSEC
    error entries and RVSEC-COV coverage entries. Optionally initialize the
    repository with static analysis data to enable reachability-based metrics.

    Args:
        log_file: Absolute path to the logcat file.
        static_data: Optional StaticAnalysisData to pre-populate the repository
            with reachable classes and methods.

    Returns:
        LogcatRepository containing all parsed errors and method calls.
    """
    # Initialize the repository
    repository = LogcatRepository()
    logger = logging.getLogger(__name__)

    # Initialize repository with static data if provided
    if static_data and hasattr(static_data, "classes"):
        logger.debug("Initializing repository with static analysis data")
        initialize_repository_from_static_data(repository, static_data, "LogcatParser")

    # Process log file line by line for memory efficiency
    try:
        with open(log_file, "r") as f:
            for line in f:
                error_log, coverage_log = parse_logcat_line(line)

                if error_log:
                    repository.register_rv_error(error_log)
                elif coverage_log:
                    repository.register_method_call(coverage_log)
    except Exception as e:
        logger.error(f"Error parsing logcat file {log_file}: {e}", exc_info=True)

    return repository


def parse_logcat_line(
    line: str,
) -> Tuple[Optional[RvErrorLog], Optional[RvCoverageLog]]:
    """
    Parse a single logcat line for RVSEC or RVSEC-COV entries.

    Args:
        line: Raw logcat line in standard Android format.

    Returns:
        Tuple of ``(error_log, coverage_log)``. At most one element is
        non-None. Both are None for non-RVSEC lines or unparseable input.
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
    """Parse a raw logcat line into its component fields.

    Returns:
        Dict with date, time, pid, tid, level, tag, message, original;
        or None if the line does not match standard logcat format.
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
        "original": line.strip(),
    }


def _parse_error_message(message: str) -> Optional[RvErrorLog]:
    """
    Parse an RVSEC error message into an RvErrorLog.

    Try three formats in order: generic spec error (``went into an error
    state.``), JCA comma-separated (6+ fields), and FSM ``:::`` separator.
    Log a warning and return None if no format matches.

    Args:
        message: The message portion of an RVSEC-tagged logcat line.

    Returns:
        Parsed RvErrorLog, or None if the message format is unrecognized.
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
                generic["message"],
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
            (
                ",".join(parts[6:]) if len(parts) > 6 else "No additional message"
            ),  # message
        )

    # Alternative format with ::: separator (FSM format)
    if ":::" in message:
        split = message.split(":::")
        if len(split) >= 2:
            tmp = split[0]
            tmp = tmp[: tmp.find("(") if "(" in tmp else len(tmp)]
            dot_idx = tmp.rfind(".")
            if dot_idx != -1:
                clazz = tmp[:dot_idx]
                method = tmp[dot_idx + 1 :]
                message_text = split[1].strip()
                spec = message_text.split(" ")[0]
                return RvErrorLog(
                    spec, spec, clazz, method, "Unknown Source:1", message_text
                )

    # Fallback for malformed messages - log warning instead of creating malformed data
    logging.getLogger(__name__).warning(f"Failed to parse error message: {message}")
    return None


def _parse_generic_spec_error(log_line: str) -> Optional[Dict[str, Any]]:
    """Parse ``class.method(file:line) ::: Spec went into an error state.`` format.

    Returns:
        Dict with class, method, file_name, line_number, spec, message;
        or None if the pattern does not match.
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
            "message": f"{spec} went into an error state.",
        }
    return None


def _parse_coverage_message(message: str) -> Optional[RvCoverageLog]:
    """
    Parse an RVSEC-COV message into an RvCoverageLog.

    Try the modern angle-bracket format first (``<class: retType method(params)>``),
    then the legacy ``:::`` format. Log a warning and return None if neither matches.

    Args:
        message: The message portion of an RVSEC-COV-tagged logcat line.

    Returns:
        Parsed RvCoverageLog, or None if the message format is unrecognized.
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
    Convert logcat date and time strings to a datetime object.

    Logcat timestamps lack a year. Infer the year from the current date,
    attributing December entries to the previous year when the current
    month is January (year-transition handling).

    Args:
        date: Date string in ``MM-DD`` format.
        time: Time string in ``HH:MM:SS.mmm`` format.

    Returns:
        Datetime with the inferred year.
    """
    current_year = datetime.now().year

    # Handle edge case for year transition
    current_month = datetime.now().month
    log_month = int(date.split("-")[0])

    # If current month is January (1) and log month is December (12),
    # it means the log is from the previous year
    year = current_year - 1 if current_month == 1 and log_month == 12 else current_year

    date_format = "%Y-%m-%d %H:%M:%S.%f"
    date_str = f"{year}-{date} {time}"
    return datetime.strptime(date_str, date_format)
