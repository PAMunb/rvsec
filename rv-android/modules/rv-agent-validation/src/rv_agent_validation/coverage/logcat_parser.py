"""
Parser for logcat files with RVSEC coverage and error entries.

Supports threadtime format with RVSEC-COV and RVSEC tags.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set, Tuple

from rv_agent_validation.coverage.signature_normalizer import SignatureNormalizer


@dataclass
class CoverageEntry:
    """A single coverage log entry."""
    class_name: str
    method: str
    signature: str  # Normalized: class.method(params)
    timestamp: Optional[float] = None


@dataclass
class ErrorEntry:
    """A single error log entry."""
    spec: str
    class_name: str
    method: str
    message: str
    unique_key: str  # For deduplication
    timestamp: Optional[float] = None


class LogcatCoverageParser:
    """
    Parser for logcat files with RVSEC coverage data.

    Parses both RVSEC-COV (coverage) and RVSEC (errors) entries.
    """

    TAG_COV = "RVSEC-COV"
    TAG_ERR = "RVSEC"

    # Threadtime format pattern
    LOGCAT_PATTERN = re.compile(
        r"(\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}\.\d{3})\s+(\d+)\s+(\d+)\s+(\w)\s+(\S+)\s*:\s*(.*)"
    )

    # Coverage message pattern: <class: returnType method(params)>
    COVERAGE_PATTERN = re.compile(
        r"<([^:]+):\s+([^ ]+)\s+([^:(]+)\(([^)]*)\)>"
    )

    # Generic spec error pattern: class.method(file:line) ::: SpecName message
    GENERIC_ERROR_PATTERN = re.compile(
        r"(.+)\.([^.]+)\(([^:]+):([^)]+)\) ::: (\S+) (.+)"
    )

    def __init__(self):
        self.normalizer = SignatureNormalizer()
        self._first_timestamp: Optional[float] = None
        self._first_date: Optional[str] = None

    def parse_file(self, file_path: Path) -> Tuple[List[CoverageEntry], List[ErrorEntry]]:
        """
        Parse logcat file and extract coverage and error entries.

        Args:
            file_path: Path to logcat file

        Returns:
            Tuple of (coverage_entries, error_entries)
        """
        coverage: List[CoverageEntry] = []
        errors: List[ErrorEntry] = []
        seen_errors: Set[str] = set()

        # Reset timestamp tracking
        self._first_timestamp = None
        self._first_date = None

        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                entry = self._parse_logcat_line(line)
                if not entry:
                    continue

                tag = entry['tag']
                message = entry['message']
                timestamp = self._calculate_relative_time(entry['date'], entry['time'])

                if tag == self.TAG_COV:
                    cov = self._parse_coverage_message(message)
                    if cov:
                        cov.timestamp = timestamp
                        coverage.append(cov)

                elif tag == self.TAG_ERR:
                    err = self._parse_error_message(message)
                    if err and err.unique_key not in seen_errors:
                        err.timestamp = timestamp
                        seen_errors.add(err.unique_key)
                        errors.append(err)

        return coverage, errors

    def _parse_logcat_line(self, line: str) -> Optional[dict]:
        """Parse a single logcat line in threadtime format."""
        match = self.LOGCAT_PATTERN.match(line)
        if not match:
            return None

        date, time, pid, tid, level, tag, message = match.groups()
        return {
            'date': date,
            'time': time,
            'tag': tag,
            'message': message,
        }

    def _parse_coverage_message(self, message: str) -> Optional[CoverageEntry]:
        """Parse RVSEC-COV message to extract coverage data."""
        # Try modern format: <class: returnType method(params)>
        match = self.COVERAGE_PATTERN.match(message)
        if match:
            class_name, return_type, method_name, parameters = match.groups()

            # Build signature: class.method(params)
            if parameters:
                params_clean = parameters.replace(" ", "")
                signature = f"{class_name}.{method_name}({params_clean})"
            else:
                signature = f"{class_name}.{method_name}()"

            # Normalize for inner classes
            normalized_sig = self.normalizer.normalize_signature(signature)
            normalized_class = self.normalizer.normalize_class_name(class_name)

            return CoverageEntry(
                class_name=normalized_class,
                method=method_name,
                signature=normalized_sig,
            )

        # Try legacy format: class:::method:::params
        parts = message.split(":::")
        if len(parts) >= 2:
            class_name = parts[0].strip()
            method_name = parts[1].strip()
            params = parts[2].strip() if len(parts) > 2 else ""

            if params.startswith('(') and params.endswith(')'):
                signature = f"{class_name}.{method_name}{params}"
            else:
                signature = f"{class_name}.{method_name}({params})"

            signature = signature.replace(" ", "")
            normalized_sig = self.normalizer.normalize_signature(signature)
            normalized_class = self.normalizer.normalize_class_name(class_name)

            return CoverageEntry(
                class_name=normalized_class,
                method=method_name,
                signature=normalized_sig,
            )

        return None

    def _parse_error_message(self, message: str) -> Optional[ErrorEntry]:
        """Parse RVSEC error message."""
        # Try generic spec format: class.method(file:line) ::: SpecName message
        if " ::: " in message:
            match = self.GENERIC_ERROR_PATTERN.match(message)
            if match:
                class_name, method_name, file_name, line_number, spec, error_msg = match.groups()
                normalized_class = self.normalizer.normalize_class_name(class_name)
                unique_key = f"{normalized_class}:::{method_name}:::{spec}"

                return ErrorEntry(
                    spec=spec,
                    class_name=normalized_class,
                    method=method_name,
                    message=error_msg,
                    unique_key=unique_key,
                )

        # Try JCA format: spec,class,...
        parts = message.split(",")
        if len(parts) >= 6:
            spec = parts[0]
            class_name = parts[1]
            method = parts[3]
            msg = ",".join(parts[6:]) if len(parts) > 6 else ""

            normalized_class = self.normalizer.normalize_class_name(class_name)
            unique_key = f"{normalized_class}:::{method}:::{spec}"

            return ErrorEntry(
                spec=spec,
                class_name=normalized_class,
                method=method,
                message=msg,
                unique_key=unique_key,
            )

        return None

    def _calculate_relative_time(self, date: str, time: str) -> float:
        """Calculate seconds since first event."""
        time_parts = time.split(':')
        hours = int(time_parts[0])
        minutes = int(time_parts[1])
        seconds_part = time_parts[2].split('.')
        seconds = int(seconds_part[0])
        milliseconds = int(seconds_part[1]) if len(seconds_part) > 1 else 0

        absolute_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0

        if self._first_timestamp is None:
            self._first_timestamp = absolute_seconds
            self._first_date = date

        # Handle day rollover
        day_offset = 0
        if date != self._first_date:
            first_month, first_day = map(int, self._first_date.split('-'))
            current_month, current_day = map(int, date.split('-'))

            if current_month == first_month:
                day_offset = current_day - first_day
            else:
                day_offset = 1  # Simplified

            absolute_seconds += day_offset * 86400

        return absolute_seconds - self._first_timestamp
