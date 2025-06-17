"""
Standardized logging models for runtime verification.

This module provides validated data models for tracking coverage and formal
property violations during runtime verification execution.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import Field, field_validator, computed_field

from rv_android_core.util import utils
from rv_android_core.util.validation import BaseValidatedModel
from rv_android_core.util.validation.decorators import validated_model

# Constants for log tags
TAG_RVSEC = "RVSEC"
TAG_RVSEC_COV = "RVSEC-COV"


@validated_model(['spec', 'error_type', 'class_full_name', 'method', 'source', 'message'])
class RvErrorLog(BaseValidatedModel):
    """
    Validated data model for runtime verification property violations.
    
    This model provides structured representation of formal property violations
    detected during runtime verification execution. It enforces data consistency
    and enables reliable error reporting and analysis workflows.

    ### Critical Usage Guidelines:
    This class should ONLY be used for runtime verification errors, meaning
    violations of properties defined in formal specifications. Do NOT use this
    class for general system errors, exceptions, or other non-property-related
    failures. For those cases, use regular exceptions or the error handling
    mechanisms provided in util.exceptions.

    ### Appropriate Usage Examples:
    - Security property violations detected by monitors
    - Temporal logic constraint violations  
    - Protocol state machine error state transitions
    - Monitor specification breach detection

    ### Inappropriate Usage Examples:
    - File not found errors
    - Network connection failures
    - Configuration errors
    - General system exceptions

    ### Architectural Role:
    - Provides standardized structure for property violation reporting
    - Enables consistent error analysis and aggregation workflows
    - Supports temporal correlation of violations with application execution
    - Facilitates automated security analysis and reporting
    """

    spec: str = Field(
        description="Monitor specification identifier that detected the violation"
    )
    error_type: str = Field(
        description="Classification of the property violation type"
    )
    class_full_name: str = Field(
        description="Fully qualified class name where the violation occurred"
    )
    method: str = Field(
        description="Method name where the violation was detected"
    )
    source: str = Field(
        description="Source file or monitor location that detected the violation"
    )
    message: str = Field(
        description="Detailed violation description and context information"
    )
    original_msg: str = Field(
        default="",
        description="Original raw message from the monitoring system"
    )
    time_occurred: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the violation was detected"
    )
    time_since_task_start: int = Field(
        default=0,
        description="Seconds elapsed since task execution started when violation occurred"
    )

    @computed_field
    @property
    def unique_msg(self) -> str:
        """Generate unique identifier for this property violation."""
        return f"{self.class_full_name}:::{self.method}:::{self.spec}:::{self.error_type}:::{self.message}"

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
        Create a RvErrorLog from a dictionary representation.

        Args:
            data: Dictionary containing error violation data

        Returns:
            New RvErrorLog instance with validated data
        """
        # Handle timestamp conversion if provided
        time_occurred = None
        if 'time_occurred' in data:
            time_ms = data['time_occurred']
            if isinstance(time_ms, (int, float)):
                time_occurred = datetime.fromtimestamp(time_ms / 1000.0)

        return cls(
            spec=data.get('spec', ''),
            error_type=data.get('error_type', ''),
            class_full_name=data.get('class_full_name', ''),
            method=data.get('method', ''),
            source=data.get('source', ''),
            message=data.get('message', ''),
            original_msg=data.get('original_msg', ''),
            time_occurred=time_occurred or datetime.now(),
            time_since_task_start=data.get('time_since_task_start', 0)
        )

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


@validated_model(['clazz', 'method', 'params', 'signature'])
class RvCoverageLog(BaseValidatedModel):
    """
    Validated data model for method execution coverage tracking.
    
    This model provides structured representation of method execution events
    detected during runtime verification, enabling comprehensive coverage
    analysis and temporal correlation with application behavior.

    ### Architectural Role:
    - Captures precise method execution events for coverage calculation
    - Provides temporal correlation between static and dynamic analysis
    - Enables coverage percentage computation and progress tracking
    - Supports comprehensive execution flow analysis and reporting

    ### Integration Points:
    - Generated by instrumentation monitoring during application execution
    - Consumed by coverage analyzers for static-dynamic correlation
    - Used by experiment systems for execution progress tracking
    - Integrated with result analysis and reporting pipelines
    """

    clazz: str = Field(
        description="Fully qualified class name where method execution occurred"
    )
    method: str = Field(
        description="Method name that was executed"
    )
    params: str = Field(
        description="Method parameter types (semicolon-separated format)"
    )
    signature: str = Field(
        description="Complete method signature including class, method, and parameters"
    )
    original_msg: str = Field(
        default="",
        description="Original raw message from the monitoring instrumentation"
    )
    time_occurred: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the method execution was detected"
    )
    time_since_task_start: int = Field(
        default=0,
        description="Seconds elapsed since task execution started when method was called"
    )

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
        Create a RvCoverageLog from a dictionary representation.

        Args:
            data: Dictionary containing coverage execution data

        Returns:
            New RvCoverageLog instance with validated data
        """
        # Handle timestamp conversion if provided
        time_occurred = None
        if 'time_occurred' in data:
            time_ms = data['time_occurred']
            if isinstance(time_ms, (int, float)):
                time_occurred = datetime.fromtimestamp(time_ms / 1000.0)

        return cls(
            clazz=data.get('class', ''),
            method=data.get('method', ''),
            params=data.get('params', ''),
            signature=data.get('signature', ''),
            original_msg=data.get('original_msg', ''),
            time_occurred=time_occurred or datetime.now(),
            time_since_task_start=data.get('time_since_task_start', 0)
        )

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
