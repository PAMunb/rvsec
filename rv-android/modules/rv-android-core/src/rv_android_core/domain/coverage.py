"""
Unified model for method coverage tracking and analysis.

This module provides validated data structures for tracking method coverage
and coverage metrics during runtime verification execution.
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from pydantic import Field
from rv_android_core.domain.log import RvCoverageLog, RvDiagnosticEvent, RvErrorLog
from rv_android_core.util.validation import BaseValidatedModel
from rv_android_core.util.validation.decorators import validated_model


@validated_model(["class_name", "method_name", "signature", "parameters"])
class MethodCoverageData(BaseValidatedModel):
    """
    Validated data model for method coverage information and execution tracking.

    This model provides comprehensive tracking of method execution status including
    static analysis reachability information and dynamic execution data with
    precise timing correlation for experiment analysis.

    ### Architectural Role:
    - Represents individual method coverage state in the runtime verification system
    - Bridges static analysis data with dynamic execution monitoring results
    - Provides temporal correlation between method calls and experiment timeline
    - Enables precise coverage calculation and progress tracking

    ### Critical Timing Data Flow:
    The time_since_task_start field preserves timing information from RvCoverageLog
    objects throughout the complete data flow to maintain accurate timing data
    for CSV report generation and temporal analysis.

    ### Integration Points:
    - Created from static analysis results during experiment initialization
    - Updated by coverage monitoring during application execution
    - Consumed by result analysis for coverage percentage calculation
    - Used by reporting systems for detailed coverage analysis
    """

    class_name: str = Field(
        description="Fully qualified class name containing this method"
    )
    method_name: str = Field(description="Method name within the containing class")
    signature: str = Field(description="Complete method signature including parameters")
    parameters: List[str] = Field(
        description="List of parameter types for method signature"
    )
    # === STATIC ANALYSIS FLAGS ===
    # These three flags form a reachability hierarchy from GATOR static analysis:
    # reachable -> reaches_target -> directly_reaches_target (each level is a subset).
    # "MOP" refers to any monitored operation (JCA or generic), not specifically security.
    reachable: bool = Field(
        default=False,
        description="Whether method is reachable according to static analysis",
    )
    reaches_target: bool = Field(
        default=False,
        description="Whether method can reach monitor-oriented programming operations",
    )
    directly_reaches_target: bool = Field(
        default=False,
        description="Whether method directly invokes monitored operations",
    )
    called: bool = Field(
        default=False,
        description="Whether method has been executed during runtime verification",
    )
    call_count: int = Field(
        default=0, description="Number of times method has been called during execution"
    )
    first_called_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when method was first called during execution",
    )
    last_called_at: Optional[datetime] = Field(
        default=None, description="Timestamp when method was most recently called"
    )
    from_static_analysis: bool = Field(
        default=False,
        description="Whether method data originates from static analysis results",
    )
    # time_since_task_start uses tool_execution_start (not task start_time) as epoch,
    # so coverage timestamps reflect actual tool execution duration. This value
    # flows unchanged from RvCoverageLog -> MethodCoverageData -> CSV export.
    time_since_task_start: int = Field(
        default=0,
        description="Seconds elapsed since task start when method was first called (preserved from RvCoverageLog)",
    )

    def register_call(
        self,
        timestamp: Optional[datetime] = None,
        time_since_task_start: Optional[int] = None,
    ) -> None:
        """
        Register a call to this method.

        ### Critical Architecture Decision:
        This method preserves timing data from RvCoverageLog objects to maintain
        accurate timing information throughout the data flow. The time_since_task_start
        is essential for generating correct CSV reports with actual execution times.

        Args:
            timestamp: When the call occurred (defaults to now)
            time_since_task_start: Seconds since task execution started (from RvCoverageLog)
        """
        current_time = timestamp or datetime.now()
        self.called = True
        self.call_count += 1

        if not self.first_called_at:
            self.first_called_at = current_time
            # Store the time_since_task_start from the FIRST call for CSV export
            if time_since_task_start is not None:
                self.time_since_task_start = time_since_task_start

        self.last_called_at = current_time

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to a dictionary representation.

        Returns:
            Dictionary with method coverage details
        """
        result = {
            "class_name": self.class_name,
            "method_name": self.method_name,
            "signature": self.signature,
            "parameters": self.parameters,
            "reachable": self.reachable,
            "reaches_target": self.reaches_target,
            "directly_reaches_target": self.directly_reaches_target,
            "called": self.called,
            "call_count": self.call_count,
            "from_static_analysis": self.from_static_analysis,
        }

        # Convert datetime objects to ISO format strings if present
        if self.first_called_at:
            result["first_called_at"] = self.first_called_at.isoformat()
        else:
            result["first_called_at"] = None

        if self.last_called_at:
            result["last_called_at"] = self.last_called_at.isoformat()
        else:
            result["last_called_at"] = None

        return result

    @classmethod
    def from_coverage_log(cls, log: RvCoverageLog) -> "MethodCoverageData":
        """
        Create a method coverage data instance from a coverage log entry.

        Args:
            log: Coverage log entry

        Returns:
            New MethodCoverageData instance initialized from the log
        """
        parameters = log.get_parameters_list()

        instance = cls(
            class_name=log.clazz,
            method_name=log.method,
            signature=log.signature,
            parameters=parameters,
            # Default values for other fields
            reachable=False,
            reaches_target=False,
            directly_reaches_target=False,
        )

        # Register the call with the timestamp from the log
        instance.register_call(log.time_occurred)

        # Store the time since task start from the original log
        instance.time_since_task_start = log.time_since_task_start

        return instance


@validated_model(["name"])
class ClassCoverageData(BaseValidatedModel):
    """
    Validated data model for class-level coverage information and metrics.

    This model aggregates method coverage data at the class level and provides
    comprehensive metrics for understanding application component coverage
    during runtime verification execution.

    ### Architectural Role:
    - Aggregates method-level coverage data for comprehensive class analysis
    - Provides class-level metrics for coverage calculation and reporting
    - Enables efficient lookup and management of method coverage within classes
    - Supports Activity-specific tracking for Android component analysis

    ### Integration Points:
    - Contains MethodCoverageData instances for all methods within the class
    - Used by LogcatRepository for coverage data organization and retrieval
    - Consumed by metrics calculation for class-level coverage percentages
    - Integrated with reporting systems for detailed class analysis
    """

    name: str = Field(description="Fully qualified class name")
    component_type: Optional[str] = Field(
        default=None,
        description="Android component type: 'activity', 'service', 'receiver', 'provider', or None",
    )
    is_main: bool = Field(
        default=False, description="Whether this class is the main (launcher) component"
    )
    methods: Dict[str, MethodCoverageData] = Field(
        default_factory=dict,
        description="Dictionary of method signatures to coverage data for all methods in class",
    )

    @property
    def called(self) -> bool:
        """Check if any method in this class has been called."""
        return any(method.called for method in self.methods.values())

    @property
    def method_count(self) -> int:
        """Get the total number of methods in this class."""
        return len(self.methods)

    @property
    def called_method_count(self) -> int:
        """Get the number of methods that have been called."""
        return sum(1 for method in self.methods.values() if method.called)

    @property
    def reachable_method_count(self) -> int:
        """Get the number of reachable methods."""
        return sum(1 for method in self.methods.values() if method.reachable)

    @property
    def called_reachable_method_count(self) -> int:
        """Get the number of reachable methods that have been called."""
        return sum(
            1 for method in self.methods.values() if method.reachable and method.called
        )

    @property
    def mop_reaching_method_count(self) -> int:
        """Get the number of methods that can reach MOP operations."""
        return sum(1 for method in self.methods.values() if method.reaches_target)

    @property
    def called_mop_reaching_method_count(self) -> int:
        """Get the number of MOP-reaching methods that have been called."""
        return sum(
            1
            for method in self.methods.values()
            if method.reaches_target and method.called
        )

    def add_method(self, method: MethodCoverageData) -> None:
        """
        Add a method to this class.

        Args:
            method: Method data to add
        """
        self.methods[method.signature] = method

    def register_method_call(
        self,
        signature: str,
        timestamp: Optional[datetime] = None,
        time_since_task_start: Optional[int] = None,
    ) -> bool:
        """
        Register a call to a method in this class.

        ### Critical Architecture Decision:
        This method propagates timing data from RvCoverageLog through the coverage
        data structure to ensure accurate timing information in reports.

        Args:
            signature: Method signature
            timestamp: When the call occurred (optional)
            time_since_task_start: Seconds since task execution started (from RvCoverageLog)

        Returns:
            True if the method was found and updated, False otherwise
        """
        if signature in self.methods:
            self.methods[signature].register_call(timestamp, time_since_task_start)
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to a dictionary representation.

        Returns:
            Dictionary with class coverage details
        """
        return {
            "name": self.name,
            "component_type": self.component_type,
            "is_main": self.is_main,
            "method_count": self.method_count,
            "called_method_count": self.called_method_count,
            "reachable_method_count": self.reachable_method_count,
            "called_reachable_method_count": self.called_reachable_method_count,
            "mop_reaching_method_count": self.mop_reaching_method_count,
            "called_mop_reaching_method_count": self.called_mop_reaching_method_count,
            "methods": [method.to_dict() for method in self.methods.values()],
        }


class CoverageMetrics(BaseValidatedModel):
    """
    Validated data model for comprehensive coverage metrics and analysis.

    This model provides standardized structure for storing and reporting coverage
    metrics calculated from static analysis and dynamic execution data during
    runtime verification experiments.

    ### Architectural Role:
    - Provides standardized metrics container for coverage calculation results
    - Enables consistent coverage reporting across different experiment types
    - Supports both raw counts and calculated percentages for analysis
    - Facilitates comparison and aggregation of coverage data

    ### Integration Points:
    - Generated by LogcatRepository.calculate_metrics() from coverage data
    - Consumed by result analysis and reporting systems
    - Used by experiment orchestration for progress tracking
    - Integrated with CSV and JSON output generation for analysis
    """

    # Basic counts from static analysis
    total_classes: int = Field(
        default=0, description="Total number of classes identified in static analysis"
    )
    total_activities: int = Field(
        default=0, description="Total number of Android Activity classes in application"
    )
    total_methods: int = Field(
        default=0, description="Total number of methods identified in static analysis"
    )
    total_reachable_methods: int = Field(
        default=0,
        description="Total number of methods marked as reachable by static analysis",
    )
    total_target_methods: int = Field(
        default=0,
        description="Total number of methods that can reach monitored operations",
    )
    total_direct_target_methods: int = Field(
        default=0,
        description="Total number of methods that directly invoke monitored operations",
    )

    # Called counts from dynamic execution
    called_classes: int = Field(
        default=0,
        description="Number of classes with at least one method called during execution",
    )
    called_activities: int = Field(
        default=0,
        description="Number of Activity classes with methods called during execution",
    )
    called_methods: int = Field(
        default=0, description="Number of methods actually called during execution"
    )
    called_reachable_methods: int = Field(
        default=0,
        description="Number of reachable methods that were called during execution",
    )
    called_target_methods: int = Field(
        default=0,
        description="Number of MOP-reaching methods that were called during execution",
    )
    called_direct_target_methods: int = Field(
        default=0,
        description="Number of directly MOP-invoking methods that were called during execution",
    )

    # Error counts from runtime verification
    total_errors: int = Field(
        default=0,
        description="Total number of property violations detected during execution",
    )
    unique_errors: int = Field(
        default=0, description="Number of unique property violation types detected"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to a dictionary with raw counts and calculated percentages.

        Returns:
            Dictionary containing all raw count fields plus calculated percentage
            fields: "class_coverage", "activity_coverage", "method_coverage",
            "reachable_method_coverage", "mop_method_coverage",
            "direct_mop_method_coverage".
        """
        return {
            # Raw counts
            "total_classes": self.total_classes,
            "total_activities": self.total_activities,
            "total_methods": self.total_methods,
            "total_reachable_methods": self.total_reachable_methods,
            "total_target_methods": self.total_target_methods,
            "total_direct_target_methods": self.total_direct_target_methods,
            "called_classes": self.called_classes,
            "called_activities": self.called_activities,
            "called_methods": self.called_methods,
            "called_reachable_methods": self.called_reachable_methods,
            "called_target_methods": self.called_target_methods,
            "called_direct_target_methods": self.called_direct_target_methods,
            "total_errors": self.total_errors,
            "unique_errors": self.unique_errors,
            # Percentages
            "class_coverage": self._percentage(self.called_classes, self.total_classes),
            "activity_coverage": self._percentage(
                self.called_activities, self.total_activities
            ),
            "method_coverage": self._percentage(
                self.called_methods, self.total_methods
            ),
            "reachable_method_coverage": self._percentage(
                self.called_reachable_methods, self.total_reachable_methods
            ),
            "mop_method_coverage": self._percentage(
                self.called_target_methods, self.total_target_methods
            ),
            "direct_mop_method_coverage": self._percentage(
                self.called_direct_target_methods, self.total_direct_target_methods
            ),
        }

    @staticmethod
    def _percentage(part: int, total: int) -> float:
        """Calculate percentage safely."""
        return (part / total * 100) if total > 0 else 0.0


@dataclass
class ParserDiagnostics:
    """Why every logcat line that did not become a record did not become one.

    Whatever the logcat parser drops is invisible in every count downstream of it,
    and whatever it substitutes for a value the producer did not supply reads as a
    measurement everywhere. This object makes both countable: no line leaves the
    parser without incrementing exactly one of the seven discard counters or
    becoming a record, and every sentinel the parser writes into a record is
    counted under its own name. The gate is arithmetic — records registered plus
    counted lines equals lines read (INV-ANA-62).

    It lives here, beside `LogcatRepository`, rather than in `rv-coverage` where the
    parsing happens, because the repository is what carries it to its readers and
    `rv-android-core` cannot import `rv-coverage` — the dependency runs the other
    way. `rv-coverage` constructs nothing: it increments the object the repository
    already owns, so the live `CoverageTracker` path and the offline
    `parse_logcat_file` path count onto the same totals.

    The seven discard counters:
        lines_not_threadtime: the line is not in Android's threadtime format at all
            (a `--------- beginning of crash` banner, a truncated tail).
        lines_other_tag: a well-formed threadtime line under a tag that is neither
            `RVSEC`, `RVSEC-COV` nor one of the diagnostic tags.
        format1_regex_failed: the message ends in `went into an error state.` — so it
            is Format 1 — but its regex does not match. It is dropped rather than
            retried as Format 2, because a class or method name bearing five commas
            would otherwise be scrambled into a JCA record.
        format2_short: between one and four commas, no `:::`, no Format-1 suffix —
            the shape logcat leaves when it cuts a payload before its sixth comma.
        format3_unresolved: a `:::` message whose left part has no dot, so no class
            and method can be recovered (the `[helper] ::: ` lines of `generic_new`).
        unrecognised: the message matched none of the three formats.
        continuation_lines: an unrecognised message that immediately follows, from
            the same `(pid, tid)`, a record flagged truncated — the second half of a
            payload logcat split on a newline.

    The sentinel and grammar counters:
        truncated_envelopes: a record whose envelope's last quoted value is unclosed.
        sentinel_error_type, sentinel_source, sentinel_code, sentinel_event: one per
            value the producer did not supply and the parser named `UNSPECIFIED`
            rather than invented.
        envelope_forbidden_chars: a value containing `:::`, which the producer
            contract forbids because it is the separator of `unique_msg`. The record
            is kept verbatim; the parser counts, it does not repair.

    The three crossing counters (INV-ANA-68):
        These count something else, and the difference is load-bearing. A discard
        counter above counts a line that became NO record. These count a record that
        was made and then found no home in the static analysis — the crossing at
        `LogcatRepository.register_method_call`, where a class or a signature that
        the artefact does not carry is dropped with nothing but a `logger.debug` to
        show for it. Splitting them by scope is what separates "the denominator is
        wrong" from "the run touched library code":

        unmatched_out_of_scope: the executed class sits outside the effective scope
            key. Expected — the app called a library.
        unmatched_in_scope: the executed class sits INSIDE the key and the artefact
            still does not have it. This is the one that indicts the denominator.
        unmatched_unclassified: no effective key was available to classify against —
            the state of every artefact written before the key reached disk. Counted
            under its own name rather than silently attributed to either side.

        They stay OUT of `discarded_lines`: those lines did become records, which is
        the same reason the sentinel and grammar counters are excluded, and it is
        what keeps INV-ANA-62's identity true unchanged (task 2.9).
    """

    lines_not_threadtime: int = 0
    lines_other_tag: int = 0
    format1_regex_failed: int = 0
    format2_short: int = 0
    format3_unresolved: int = 0
    unrecognised: int = 0
    continuation_lines: int = 0
    truncated_envelopes: int = 0
    sentinel_error_type: int = 0
    sentinel_source: int = 0
    sentinel_code: int = 0
    sentinel_event: int = 0
    envelope_forbidden_chars: int = 0
    unmatched_out_of_scope: int = 0
    unmatched_in_scope: int = 0
    unmatched_unclassified: int = 0

    # Not a counter: the parser's one piece of carry-over state. A payload logcat
    # split on a newline arrives as two lines, and the second has no structure of
    # its own; the only thing that identifies it is that the previous record from
    # the same `(pid, tid)` came out truncated. The state lives here because it
    # needs exactly the lifetime and the sharing the counters have — one object per
    # repository, seen by both the live and the offline path — and it is one-shot:
    # the parser clears it on the next line from that thread, so a truncation can
    # account for at most one following line. `to_dict` does not expose it.
    last_truncated_key: Optional[Any] = None

    def to_dict(self) -> Dict[str, int]:
        """The counters by name, for a report or a test's arithmetic."""
        return {
            "lines_not_threadtime": self.lines_not_threadtime,
            "lines_other_tag": self.lines_other_tag,
            "format1_regex_failed": self.format1_regex_failed,
            "format2_short": self.format2_short,
            "format3_unresolved": self.format3_unresolved,
            "unrecognised": self.unrecognised,
            "continuation_lines": self.continuation_lines,
            "truncated_envelopes": self.truncated_envelopes,
            "sentinel_error_type": self.sentinel_error_type,
            "sentinel_source": self.sentinel_source,
            "sentinel_code": self.sentinel_code,
            "sentinel_event": self.sentinel_event,
            "envelope_forbidden_chars": self.envelope_forbidden_chars,
            "unmatched_out_of_scope": self.unmatched_out_of_scope,
            "unmatched_in_scope": self.unmatched_in_scope,
            "unmatched_unclassified": self.unmatched_unclassified,
        }

    @property
    def discarded_lines(self) -> int:
        """Lines read that became no record at all — the seven discard counters.

        The sentinel and grammar counters are deliberately excluded: those lines did
        become records, so adding them would double-count against lines read.
        """
        return (
            self.lines_not_threadtime
            + self.lines_other_tag
            + self.format1_regex_failed
            + self.format2_short
            + self.format3_unresolved
            + self.unrecognised
            + self.continuation_lines
        )


class LogcatRepository:
    """
    Repository for logcat-based coverage data with centralized metrics calculation.

    Provides unified coverage metrics calculation to eliminate duplication
    between CoverageAnalyzer and CoverageTracker components.

    ### Architectural Role:
    - Centralizes coverage metrics calculation logic
    - Maintains class and method coverage state
    - Provides consistent metrics format across components
    - Supports caching for performance optimization

    ### Integration Points:
    - Used by CoverageAnalyzer for analysis operations
    - Used by CoverageTracker for real-time tracking
    - Populated by repository_initializer function
    - Supports ResultManager for report generation
    """

    def __init__(self, scope_key: Optional[str] = None):
        """Initialize an empty coverage repository.

        Args:
            scope_key: The effective scope key the static analysis artefact records
                (INV-ANA-66). It classifies discards at the crossing and filters
                nothing. It is never re-derived here (INV-ANA-58, INV-CORE-60): the
                artefact's own record is the only admissible source, and `None` —
                the state of every artefact written before the key reached disk — is
                carried as `unmatched_unclassified` rather than guessed. A missing
                key costs the row its two `unmatched_*` cells and nothing else;
                coverage is still computed from the artefact's own denominator.

        State:
            self.classes: Map of fully-qualified class name to ClassCoverageData.
                Populated by repository_initializer from static analysis data.
            self.errors: Ordered list of all RV property violations detected.
            self.unique_errors: Set of unique error message signatures for deduplication.
            self.diagnostic_events: Ordered list of execution-level diagnostic events
                (crashes, VerifyError, ANR). Isolated from coverage/MOP metrics and the
                error counts — metric calculation reads only self.classes/self.errors,
                so this collection never perturbs any existing metric (INV-CORE-39).
            self.parser_diagnostics: Counters for every logcat line the parser did not
                turn into a record, and for every sentinel it wrote into one. The
                parser increments this object rather than owning one, so the live and
                the offline paths count onto the same totals (INV-ANA-62).
            self._static_totals: Cached static analysis totals, invalidated when
                classes are added. Lazily computed by _calculate_static_totals().
        """
        self.logger = logging.getLogger(__name__)
        self.scope_key: Optional[str] = scope_key
        self.classes: Dict[str, ClassCoverageData] = {}
        self.errors: List[RvErrorLog] = []
        self.unique_errors: Set[str] = set()
        self.diagnostic_events: List[RvDiagnosticEvent] = []
        self.parser_diagnostics: ParserDiagnostics = ParserDiagnostics()

        # Cache for static analysis totals - calculated once
        self._static_totals: Optional[Dict[str, int]] = None

    def add_class(self, class_data: ClassCoverageData) -> None:
        """
        Add a class to the repository.

        Args:
            class_data: Class coverage data
        """
        # Guard against duplicate additions: static analysis data is loaded once
        # during experiment initialization. Re-adding would overwrite runtime
        # call tracking (called=True, call_count, timestamps) with fresh defaults.
        if class_data.name not in self.classes:
            self.classes[class_data.name] = class_data

            # Mark methods from static analysis
            for signature, method in class_data.methods.items():
                method.from_static_analysis = True

            # Invalidate cached totals so calculate_metrics() recomputes them
            self._static_totals = None

    def get_class(self, class_name: str) -> Optional[ClassCoverageData]:
        """
        Get a class by name.

        Args:
            class_name: Class name

        Returns:
            Class coverage data or None if not found
        """
        return self.classes.get(class_name)

    def register_method_call(self, coverage_log: RvCoverageLog) -> None:
        """
        Register a method call from a coverage log entry.
        Only registers calls to methods that exist in static analysis data.

        ### Critical Architecture Decision:
        This method is the primary entry point for preserving timing data from
        RvCoverageLog objects into the coverage data structure. It ensures that
        the time_since_task_start calculated by CoverageTracker is preserved
        throughout the data flow to generate accurate CSV reports.

        Args:
            coverage_log: Coverage log entry with timing information
        """
        class_name = coverage_log.clazz
        signature = coverage_log.signature

        # Get the class if it exists
        class_data = self.get_class(class_name)
        if not class_data:
            self.logger.debug(f"Ignoring method call for unknown class: {class_name}")
            self._count_unmatched(class_name)
            return

        # Only register calls to methods that exist in static analysis data
        # CRITICAL: Pass both timestamp AND time_since_task_start from RvCoverageLog
        if signature in class_data.methods:
            class_data.register_method_call(
                signature,
                coverage_log.time_occurred,
                coverage_log.time_since_task_start,
            )
        else:
            self.logger.debug(
                f"Ignoring method call not found in static analysis: {signature}"
            )
            self._count_unmatched(class_name)

    def _count_unmatched(self, class_name: str) -> None:
        """Classify one crossing discard by scope (INV-ANA-68, INV-CORE-60).

        A class outside the key is a library call and is expected; one inside it is
        a hole in the denominator. Without the key neither claim can be made, so the
        event is counted unclassified — never silently as in-scope, which would read
        as evidence for the denominator it is supposed to be testing.
        """
        if self.scope_key is None:
            self.parser_diagnostics.unmatched_unclassified += 1
        elif class_name.startswith(self.scope_key):
            self.parser_diagnostics.unmatched_in_scope += 1
        else:
            self.parser_diagnostics.unmatched_out_of_scope += 1

    def register_rv_error(self, error_log: RvErrorLog) -> None:
        """
        Register a formal property violation detected during runtime verification.

        IMPORTANT: This method is ONLY for registering formal property violations
        detected by runtime verification monitors, not for general system errors
        or exceptions.

        Args:
            error_log: Runtime verification error log entry
        """
        self.errors.append(error_log)
        self.unique_errors.add(error_log.unique_msg)

    def register_diagnostic_event(self, event: RvDiagnosticEvent) -> None:
        """
        Register an execution-level diagnostic event (crash, VerifyError, ANR).

        Kept strictly separate from coverage (`self.classes`) and property-violation
        (`self.errors`) data: this collection is never read by `calculate_metrics()`,
        `total_errors`, or `unique_errors`, so diagnostic events cannot affect any
        coverage/MOP metric or error count (INV-CORE-39).

        Args:
            event: Parsed diagnostic event produced by the analysis-domain parser
        """
        self.diagnostic_events.append(event)

    def get_diagnostic_events(self) -> List[Dict[str, Any]]:
        """
        Get all diagnostic events as a list of dictionaries for export/reporting.

        Returns:
            List of diagnostic event dictionaries sorted by time_since_task_start
        """
        event_dicts = [event.to_dict() for event in self.diagnostic_events]
        return sorted(event_dicts, key=lambda x: x.get("time_since_task_start", 0))

    def get_static_method_count(self) -> int:
        """Get the count of methods from static analysis."""
        if self._static_totals is None:
            self._calculate_static_totals()
        return self._static_totals.get("total_methods", 0) if self._static_totals else 0

    def calculate_metrics(self, restrict_to_static: bool = True) -> CoverageMetrics:
        """
        Calculate coverage metrics from the repository data.
        Returns 0% for all metrics if no static analysis data is available.

        Args:
            restrict_to_static: If True, only include methods found in static analysis

        Returns:
            Coverage metrics
        """
        metrics = CoverageMetrics()

        # RV property violations are counted from the errors/unique_errors
        # collections, which are independent of static-analysis class data.
        # Counting them before the empty-classes early return keeps the error
        # aggregates accurate in the degraded case (logcat present, static
        # analysis absent — e.g. --skip-static or a resumed task whose JSON
        # could not be resolved), conforming to INV-ANA-25.
        metrics.total_errors = len(self.errors)
        metrics.unique_errors = len(self.unique_errors)

        # Without static analysis data, coverage is undefined (0/0).
        # This happens when --skip-static is used without pre-existing data.
        if not self.classes:
            self.logger.warning(
                "No static analysis data available, returning 0% for all metrics"
            )
            return metrics

        # Step 1: Compute static totals (cached after first call, invalidated by add_class)
        if self._static_totals is None:
            self._calculate_static_totals()

        # Use static totals for total counts
        if self._static_totals:
            metrics.total_classes = self._static_totals.get("total_classes", 0)
            metrics.total_activities = self._static_totals.get("total_activities", 0)
            metrics.total_methods = self._static_totals.get("total_methods", 0)
            metrics.total_reachable_methods = self._static_totals.get(
                "total_reachable_methods", 0
            )
            metrics.total_target_methods = self._static_totals.get(
                "total_target_methods", 0
            )
            metrics.total_direct_target_methods = self._static_totals.get(
                "total_direct_target_methods", 0
            )
        else:
            self.logger.warning(
                "Static totals not available, metrics may be inaccurate"
            )

        # Step 2: Aggregate dynamic execution counts across all classes/methods
        for class_data in self.classes.values():
            if class_data.called:
                metrics.called_classes += 1
                if class_data.component_type == "activity":
                    metrics.called_activities += 1

            # Count called methods
            for method in class_data.methods.values():
                # Only count methods from static analysis, which is now enforced
                if method.called:
                    metrics.called_methods += 1
                    if method.reachable:
                        metrics.called_reachable_methods += 1
                    if method.reaches_target:
                        metrics.called_target_methods += 1
                    if method.directly_reaches_target:
                        metrics.called_direct_target_methods += 1

        return metrics

    def calculate_coverage_metrics(
        self, cache_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive coverage metrics.

        Provides centralized implementation for coverage metrics calculation,
        eliminating duplication across CoverageAnalyzer and CoverageTracker.
        Calculates class and method coverage percentages with caching support.

        Args:
            cache_key: Optional cache key for performance optimization

        Returns:
            Dictionary containing all coverage metrics with standardized format
        """
        # Use existing calculate_metrics() for core logic
        metrics_obj = self.calculate_metrics()
        metrics_dict = metrics_obj.to_dict()

        # Calculate coverage percentages
        total_classes = metrics_dict.get("total_classes", 0)
        covered_classes = metrics_dict.get("called_classes", 0)
        total_methods = metrics_dict.get("total_methods", 0)
        covered_methods = metrics_dict.get("called_methods", 0)

        class_coverage = (
            (covered_classes / total_classes * 100) if total_classes > 0 else 0
        )
        method_coverage = (
            (covered_methods / total_methods * 100) if total_methods > 0 else 0
        )

        return {
            "total_classes": total_classes,
            "covered_classes": covered_classes,
            "class_coverage_percentage": class_coverage,
            "total_methods": total_methods,
            "covered_methods": covered_methods,
            "method_coverage_percentage": method_coverage,
            "total_activities": metrics_dict.get("total_activities", 0),
            "called_activities": metrics_dict.get("called_activities", 0),
            "activity_coverage_percentage": metrics_dict.get("activity_coverage", 0.0),
            "total_target_methods": metrics_dict.get("total_target_methods", 0),
            "called_target_methods": metrics_dict.get("called_target_methods", 0),
            "mop_method_coverage_percentage": metrics_dict.get(
                "mop_method_coverage", 0.0
            ),
            "total_direct_target_methods": metrics_dict.get(
                "total_direct_target_methods", 0
            ),
            "called_direct_target_methods": metrics_dict.get(
                "called_direct_target_methods", 0
            ),
            "direct_mop_method_coverage_percentage": metrics_dict.get(
                "direct_mop_method_coverage", 0.0
            ),
            "total_errors": metrics_dict.get("total_errors", 0),
            "unique_errors": metrics_dict.get("unique_errors", 0),
            "timestamp": time.time(),
        }

    def _calculate_static_totals(self) -> None:
        """Calculate and cache totals from static analysis data.

        Iterate all classes and methods to compute aggregate counts for
        classes, activities, methods, reachable methods, and MOP methods.
        Store result in self._static_totals for reuse by calculate_metrics().
        """
        totals = {
            "total_classes": 0,
            "total_activities": 0,
            "total_methods": 0,
            "total_reachable_methods": 0,
            "total_target_methods": 0,
            "total_direct_target_methods": 0,
        }

        # Count all classes and methods from static analysis
        for class_name, class_data in self.classes.items():
            totals["total_classes"] += 1

            if class_data.component_type == "activity":
                totals["total_activities"] += 1

            # Count methods
            for signature, method in class_data.methods.items():
                totals["total_methods"] += 1

                if method.reachable:
                    totals["total_reachable_methods"] += 1

                if method.reaches_target:
                    totals["total_target_methods"] += 1

                if method.directly_reaches_target:
                    totals["total_direct_target_methods"] += 1

        # Cache the results
        self._static_totals = totals
        self.logger.debug(f"Calculated static analysis totals: {totals}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert repository to dictionary format for serialization.

        Returns:
            Dictionary representation of the repository
        """
        metrics = self.calculate_metrics()

        return {
            "metrics": metrics.to_dict(),
            "classes": {
                name: class_data.to_dict() for name, class_data in self.classes.items()
            },
            "errors": {
                "count": len(self.errors),
                "unique_count": len(self.unique_errors),
                "items": [error.to_dict() for error in self.errors],
            },
        }

    def get_method_calls(self) -> List[Dict[str, Any]]:
        """
        Get all method calls as a list of dictionaries for export/reporting.

        ### Critical Architecture Decision:
        This method provides the final data structure used by ResultManager to generate
        CSV reports. It returns ONE entry per method (based on first call time) to avoid
        duplicates in coverage.csv. The time_since_task_start from RvCoverageLog objects
        is correctly propagated to maintain accurate timing data throughout the complete
        data flow: RvCoverageLog -> MethodCoverageData -> CSV.

        Returns:
            List of unique method call dictionaries sorted by first call time
        """
        method_calls = []

        for class_name, class_data in self.classes.items():
            for signature, method_data in class_data.methods.items():
                if method_data.called:
                    # CRITICAL: Use time_since_task_start preserved from RvCoverageLog
                    # Each method appears only ONCE based on its first call time
                    call_data = {
                        "time": method_data.time_since_task_start,  # Time of FIRST call from RvCoverageLog
                        "class_name": class_name,
                        "method_name": method_data.method_name,
                        "signature": signature,
                        "is_mop_method": method_data.reaches_target,
                        "activity": (
                            class_name
                            if class_data.component_type == "activity"
                            else None
                        ),
                        "call_count": method_data.call_count,
                        "first_called_at": (
                            method_data.first_called_at.isoformat()
                            if method_data.first_called_at
                            else None
                        ),
                        "last_called_at": (
                            method_data.last_called_at.isoformat()
                            if method_data.last_called_at
                            else None
                        ),
                    }
                    method_calls.append(call_data)

        # Sort method calls by time_since_task_start to maintain chronological order
        # This ensures progressive coverage calculation works correctly in CSV
        return sorted(method_calls, key=lambda x: x["time"])

    def get_errors(self) -> List[Dict[str, Any]]:
        """
        Get all monitored operations errors as a list of dictionaries for export/reporting.

        ### Critical Architecture Decision:
        This method returns errors sorted by time_since_task_start to maintain chronological
        order in the errors.csv output, enabling proper temporal analysis of security violations.

        Returns:
            List of error dictionaries sorted by occurrence time
        """
        error_dicts = [error.to_dict() for error in self.errors]
        # Sort by time_since_task_start to maintain chronological order in errors.csv
        return sorted(error_dicts, key=lambda x: x.get("time_since_task_start", 0))

    def get_static_methods(self) -> List[str]:
        """
        Get all method signatures from static analysis.

        Returns:
            List of method signatures
        """
        signatures = []
        for class_data in self.classes.values():
            signatures.extend(class_data.methods.keys())
        return signatures

    def get_static_activities(self) -> List[str]:
        """
        Get all activity class names from static analysis.

        Returns:
            List of activity class names
        """
        return [
            name
            for name, class_data in self.classes.items()
            if class_data.component_type == "activity"
        ]

    def get_target_methods(self) -> List[str]:
        """
        Get all MOP-reachable method signatures from static analysis.

        Returns:
            List of MOP-reachable method signatures
        """
        mop_signatures = []
        for class_data in self.classes.values():
            for signature, method_data in class_data.methods.items():
                if method_data.reaches_target:
                    mop_signatures.append(signature)
        return mop_signatures
