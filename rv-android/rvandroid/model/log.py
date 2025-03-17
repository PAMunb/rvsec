# rvandroid/model/log.py
"""
Standardized logging models for runtime verification.
This module defines consistent data structures for tracking coverage and errors.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional

from rvandroid.util import utils

# Constants for log tags
TAG_RVSEC = "RVSEC"
TAG_RVSEC_COV = "RVSEC-COV"


class RvErrorLog:
    """
    Represents an error detected during runtime verification.
    Provides a standardized structure for error data.
    """

    def __init__(self, spec: str, error_type: str, class_full_name: str, method: str, source: str, message: str):
        """
        Initialize a new RvErrorLog.

        Args:
            spec: Specification identifier
            error_type: Type of error
            class_full_name: Full class name
            method: Method name
            source: Source file or location
            message: Error message
        """
        self.spec = spec
        self.error_type = error_type
        self.class_full_name = class_full_name
        self.method = method
        self.source = source
        self.message = message
        # Create a unique identifier for this error
        self.unique_msg: str = f"{class_full_name}:::{method}:::{spec}:::{error_type}:::{message}"
        self.original_msg: str = ""
        self.time_occurred: datetime = datetime.now()
        self.time_since_task_start: int = 0  # in seconds

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to a dictionary representation.

        Returns:
            Dictionary with error details
        """
        return {
            'spec': self.spec,
            'error_type': self.error_type,
            'class_full_name': self.class_full_name,
            'method': self.method,
            'message': self.message,
            "time_occurred": utils.datetime_to_milliseconds(self.time_occurred),
            "time_since_task_start": self.time_since_task_start,
            "unique_msg": self.unique_msg
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RvErrorLog':
        """
        Create a RvErrorLog from a dictionary.

        Args:
            data: Dictionary with error data

        Returns:
            New RvErrorLog instance
        """
        instance = cls(
            spec=data.get('spec', ''),
            error_type=data.get('error_type', ''),
            class_full_name=data.get('class_full_name', ''),
            method=data.get('method', ''),
            source=data.get('source', ''),
            message=data.get('message', '')
        )

        # Set timestamp if provided
        if 'time_occurred' in data:
            time_ms = data['time_occurred']
            if isinstance(time_ms, (int, float)):
                instance.time_occurred = datetime.fromtimestamp(time_ms / 1000.0)

        if 'time_since_task_start' in data:
            instance.time_since_task_start = data['time_since_task_start']

        return instance

    def __str__(self):
        return (f"RvErrorLog(spec={self.spec}, type={self.error_type}, "
                f"classFullName={self.class_full_name}, method={self.method}, "
                f"message={self.message}, time_occurred={self.time_occurred}, "
                f"time_since_task_start={self.time_since_task_start})")

    def __repr__(self):
        return f"{self.unique_msg}:{self.time_occurred}"

    def __hash__(self):
        return hash(self.unique_msg)

    def __eq__(self, other):
        if not isinstance(other, RvErrorLog):
            return False
        return self.unique_msg == other.unique_msg


class RvCoverageLog:
    """
    Represents a method execution coverage log entry.
    Provides a standardized structure for method call data.
    """

    def __init__(self, clazz: str, method: str, params: str, signature: str):
        """
        Initialize a new RvCoverageLog.

        Args:
            clazz: Class name
            method: Method name
            params: Parameter string (semicolon-separated)
            signature: Full method signature
        """
        self.clazz = clazz
        self.method = method
        self.params = params
        self.signature = signature
        self.original_msg: str = ""
        self.time_occurred: datetime = datetime.now()
        self.time_since_task_start: int = 0  # in seconds

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to a dictionary representation.

        Returns:
            Dictionary with coverage details
        """
        return {
            'class': self.clazz,
            'method': self.method,
            'params': self.params,
            'signature': self.signature,
            'time_occurred': utils.datetime_to_milliseconds(self.time_occurred),
            'time_since_task_start': self.time_since_task_start,
            'original_msg': self.original_msg
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RvCoverageLog':
        """
        Create a RvCoverageLog from a dictionary.

        Args:
            data: Dictionary with coverage data

        Returns:
            New RvCoverageLog instance
        """
        instance = cls(
            clazz=data.get('class', ''),
            method=data.get('method', ''),
            params=data.get('params', ''),
            signature=data.get('signature', '')
        )

        # Set timestamp if provided
        if 'time_occurred' in data:
            time_ms = data['time_occurred']
            if isinstance(time_ms, (int, float)):
                instance.time_occurred = datetime.fromtimestamp(time_ms / 1000.0)

        if 'time_since_task_start' in data:
            instance.time_since_task_start = data['time_since_task_start']

        if 'original_msg' in data:
            instance.original_msg = data['original_msg']

        return instance

    def get_parameters_list(self) -> List[str]:
        """
        Get the method parameters as a list.

        Returns:
            List of parameter types
        """
        return self.params.split(";") if self.params else []

    def __str__(self):
        return (f"RvCoverageLog(clazz={self.clazz}, method={self.method}, "
                f"params={self.params}, time_occurred={self.time_occurred}, "
                f"time_since_task_start={self.time_since_task_start})")

    def __repr__(self):
        return f"{self.signature}:{self.time_occurred}"

    def __hash__(self):
        return hash(self.signature)

    def __eq__(self, other):
        if not isinstance(other, RvCoverageLog):
            return False
        return self.signature == other.signature
