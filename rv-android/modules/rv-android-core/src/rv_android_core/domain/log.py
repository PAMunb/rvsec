"""
Standardized logging models for runtime verification.

This module provides validated data models for tracking coverage and formal
property violations during runtime verification execution.
"""

from datetime import datetime
from typing import Any, Dict, List

from pydantic import Field, computed_field
from rv_android_core.util import utils
from rv_android_core.util.logging.constants import (
    TAG_RVSEC,  # noqa: F401
    TAG_RVSEC_COV,
)
from rv_android_core.util.validation import BaseValidatedModel
from rv_android_core.util.validation.decorators import validated_model


@validated_model(
    ["spec", "error_type", "class_full_name", "method", "source", "message"]
)
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
    error_type: str = Field(description="Classification of the property violation type")
    class_full_name: str = Field(
        description="Fully qualified class name where the violation occurred"
    )
    method: str = Field(description="Method name where the violation was detected")
    source: str = Field(
        description="Source file or monitor location that detected the violation"
    )
    message: str = Field(
        description="Detailed violation description and context information"
    )
    original_msg: str = Field(
        default="", description="Original raw message from the monitoring system"
    )
    time_occurred: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the violation was detected",
    )
    time_since_task_start: int = Field(
        default=0,
        description="Seconds elapsed since task execution started when violation occurred",
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
            "spec": self.spec,
            "error_type": self.error_type,
            "class_full_name": self.class_full_name,
            "method": self.method,
            "message": self.message,
            "time_occurred": utils.datetime_to_milliseconds(self.time_occurred),
            "time_since_task_start": self.time_since_task_start,
            "unique_msg": self.unique_msg,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RvErrorLog":
        """
        Create a RvErrorLog from a dictionary representation.

        Args:
            data: Dictionary containing error violation data

        Returns:
            New RvErrorLog instance with validated data
        """
        # Handle timestamp conversion if provided
        time_occurred = None
        if "time_occurred" in data:
            time_ms = data["time_occurred"]
            if isinstance(time_ms, (int, float)):
                time_occurred = datetime.fromtimestamp(time_ms / 1000.0)

        return cls(
            spec=data.get("spec", ""),
            error_type=data.get("error_type", ""),
            class_full_name=data.get("class_full_name", ""),
            method=data.get("method", ""),
            source=data.get("source", ""),
            message=data.get("message", ""),
            original_msg=data.get("original_msg", ""),
            time_occurred=time_occurred or datetime.now(),
            time_since_task_start=data.get("time_since_task_start", 0),
        )

    def __str__(self):
        return (
            f"RvErrorLog(spec={self.spec}, type={self.error_type}, "
            f"classFullName={self.class_full_name}, method={self.method}, "
            f"message={self.message}, time_occurred={self.time_occurred}, "
            f"time_since_task_start={self.time_since_task_start})"
        )

    def __repr__(self):
        return f"{self.unique_msg}:{self.time_occurred}"

    def __hash__(self):
        return hash(self.unique_msg)

    def __eq__(self, other):
        if not isinstance(other, RvErrorLog):
            return False
        return self.unique_msg == other.unique_msg


@validated_model(["category", "class_full_name", "method", "message"])
class RvDiagnosticEvent(BaseValidatedModel):
    """
    Validated data model for an execution-level diagnostic event.

    A diagnostic event records something that happened to the application *under
    test* during exploration — a crash (unhandled exception), a class-load
    `VerifyError`, or an ANR — captured from logcat tags other than RVSEC/RVSEC-COV
    when diagnostics are enabled (`RV_LOGCAT_DIAGNOSTICS`). It is distinct from
    `RvErrorLog`, which represents a formal property violation detected by a monitor.

    ### Why a separate model with a category discriminator:
    The three diagnostic kinds share the same shape (a class/method, a message, an
    app attribution, and an optional stack trace). A single model with a `category`
    enum keeps adding a kind to a one-value change instead of a new class. Diagnostic
    events live in their own `LogcatRepository.diagnostic_events` collection and never
    enter coverage/MOP metrics or the `total_errors`/`unique_errors` counts.

    ### Trace handling:
    `stack_head` (the first frame) is the per-event CSV summary; `original_msg` holds
    the full multi-line block in memory and on resume reconstruction. The complete
    trace is never written to a CSV — the `.logcat` remains the source of truth.
    """

    category: str = Field(
        description="Event kind discriminator: 'crash' | 'verify_error' | 'anr'"
    )
    class_full_name: str = Field(
        description=(
            "Exception class (crash), rejected class (verify_error), or affected "
            "package (anr)"
        )
    )
    method: str = Field(
        description="First application stack frame when available, else empty"
    )
    message: str = Field(
        description="First human-readable line (FATAL EXCEPTION / Rejecting class / ANR in)"
    )
    source: str = Field(
        default="",
        description="File:line of the first application frame when extractable",
    )
    process: str = Field(
        default="",
        description="Package of the affected app, from 'Process:'/'ANR in' (attribution)",
    )
    pid: str = Field(
        default="", description="Process id reported in the diagnostic block"
    )
    tid: str = Field(
        default="", description="Thread id reported in the diagnostic block"
    )
    fatal: bool = Field(
        default=False, description="True for a FATAL crash that terminated the process"
    )
    stack_head: str = Field(
        default="", description="First stack frame, summary for the app_events.csv row"
    )
    n_frames: int = Field(
        default=0, description="Number of stack frames in the captured trace"
    )
    original_msg: str = Field(
        default="", description="Full multi-line diagnostic block preserved verbatim"
    )
    time_occurred: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the diagnostic event was detected",
    )
    time_since_task_start: int = Field(
        default=0,
        description="Seconds elapsed since task execution started when the event occurred",
    )

    @computed_field
    @property
    def unique_msg(self) -> str:
        """Generate a unique identifier; includes category so events that share
        class/method but differ in kind (crash vs verify_error) stay distinct."""
        return (
            f"{self.category}:::{self.class_full_name}:::{self.method}:::{self.message}"
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to a dictionary representation.

        Returns:
            Dictionary with diagnostic event details (full trace stays in `.logcat`;
            `original_msg` carries it in memory for reconstruction)
        """
        return {
            "category": self.category,
            "class_full_name": self.class_full_name,
            "method": self.method,
            "source": self.source,
            "message": self.message,
            "process": self.process,
            "pid": self.pid,
            "tid": self.tid,
            "fatal": self.fatal,
            "stack_head": self.stack_head,
            "n_frames": self.n_frames,
            "original_msg": self.original_msg,
            "time_occurred": utils.datetime_to_milliseconds(self.time_occurred),
            "time_since_task_start": self.time_since_task_start,
            "unique_msg": self.unique_msg,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RvDiagnosticEvent":
        """
        Create an RvDiagnosticEvent from a dictionary representation.

        Args:
            data: Dictionary containing diagnostic event data

        Returns:
            New RvDiagnosticEvent instance with validated data
        """
        time_occurred = None
        if "time_occurred" in data:
            time_ms = data["time_occurred"]
            if isinstance(time_ms, (int, float)):
                time_occurred = datetime.fromtimestamp(time_ms / 1000.0)

        return cls(
            category=data.get("category", ""),
            class_full_name=data.get("class_full_name", ""),
            method=data.get("method", ""),
            source=data.get("source", ""),
            message=data.get("message", ""),
            process=data.get("process", ""),
            pid=data.get("pid", ""),
            tid=data.get("tid", ""),
            fatal=data.get("fatal", False),
            stack_head=data.get("stack_head", ""),
            n_frames=data.get("n_frames", 0),
            original_msg=data.get("original_msg", ""),
            time_occurred=time_occurred or datetime.now(),
            time_since_task_start=data.get("time_since_task_start", 0),
        )

    def __str__(self):
        return (
            f"RvDiagnosticEvent(category={self.category}, "
            f"class_full_name={self.class_full_name}, method={self.method}, "
            f"process={self.process}, fatal={self.fatal}, "
            f"time_since_task_start={self.time_since_task_start})"
        )

    def __repr__(self):
        return f"{self.unique_msg}:{self.time_occurred}"

    def __hash__(self):
        return hash(self.unique_msg)

    def __eq__(self, other):
        if not isinstance(other, RvDiagnosticEvent):
            return False
        return self.unique_msg == other.unique_msg


@validated_model(["clazz", "method", "params", "signature"])
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
    method: str = Field(description="Method name that was executed")
    params: str = Field(
        description="Method parameter types (semicolon-separated format)"
    )
    signature: str = Field(
        description="Complete method signature including class, method, and parameters"
    )
    original_msg: str = Field(
        default="",
        description="Original raw message from the monitoring instrumentation",
    )
    time_occurred: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the method execution was detected",
    )
    time_since_task_start: int = Field(
        default=0,
        description="Seconds elapsed since task execution started when method was called",
    )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to a dictionary representation.

        Returns:
            Dictionary with coverage details
        """
        return {
            "class": self.clazz,
            "method": self.method,
            "params": self.params,
            "signature": self.signature,
            "time_occurred": utils.datetime_to_milliseconds(self.time_occurred),
            "time_since_task_start": self.time_since_task_start,
            "original_msg": self.original_msg,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RvCoverageLog":
        """
        Create a RvCoverageLog from a dictionary representation.

        Args:
            data: Dictionary containing coverage execution data

        Returns:
            New RvCoverageLog instance with validated data
        """
        # Handle timestamp conversion if provided
        time_occurred = None
        if "time_occurred" in data:
            time_ms = data["time_occurred"]
            if isinstance(time_ms, (int, float)):
                time_occurred = datetime.fromtimestamp(time_ms / 1000.0)

        return cls(
            clazz=data.get("class", ""),
            method=data.get("method", ""),
            params=data.get("params", ""),
            signature=data.get("signature", ""),
            original_msg=data.get("original_msg", ""),
            time_occurred=time_occurred or datetime.now(),
            time_since_task_start=data.get("time_since_task_start", 0),
        )

    def get_parameters_list(self) -> List[str]:
        """
        Get the method parameters as a list.

        Returns:
            List of parameter types
        """
        return self.params.split(";") if self.params else []

    def __str__(self):
        return (
            f"RvCoverageLog(clazz={self.clazz}, method={self.method}, "
            f"params={self.params}, time_occurred={self.time_occurred}, "
            f"time_since_task_start={self.time_since_task_start})"
        )

    def __repr__(self):
        return f"{self.signature}:{self.time_occurred}"

    def __hash__(self):
        return hash(self.signature)

    def __eq__(self, other):
        if not isinstance(other, RvCoverageLog):
            return False
        return self.signature == other.signature
