# tests/util/test_exceptions.py
"""
Unit tests for the exceptions module.

This module tests the custom exception hierarchy defined in the rv-android system,
ensuring proper initialization, inheritance relationships, and string representation.

### Architectural Decisions:
- Tests each exception class's initialization and inheritance
- Verifies proper string formatting for exception messages
- Ensures proper cause propagation for chained exceptions
- Validates specialized exception attributes and behavior

### Role in the System:
- Confirms consistent exception behavior across the codebase
- Ensures exception hierarchy matches architectural requirements
- Validates error reporting format for debugging and logging
- Tests specialized exception metadata for troubleshooting
"""

from rvandroid.util.exceptions import (
    RVAndroidError,
    ConfigurationError,
    ResourceError,
    NetworkError,
    EmulatorError,
    ADBError,
    InstrumentationError,
    AnalysisError,
    ExecutionError,
    MonitorError,
    RvTimeoutError,
    TaskExecutionError,
    ToolError,
    LogcatError,
    CoverageError
)


class TestRVAndroidError:
    """Tests for the base RVAndroidError exception class."""

    def test_init_with_message_only(self):
        """Test initialization with message only."""
        error = RVAndroidError("Test error message")
        assert error.message == "Test error message"
        assert error.cause is None
        assert str(error) == "RVAndroidError: Test error message"

    def test_init_with_cause(self):
        """Test initialization with a cause."""
        cause = ValueError("Original error")
        error = RVAndroidError("Test error message", cause)
        assert error.message == "Test error message"
        assert error.cause == cause
        assert str(error) == "RVAndroidError: Test error message caused by ValueError: Original error"

    # def test_nested_causes(self):
    #     """Test nested exception causes."""
    #     inner_cause = ValueError("Inner error")
    #     middle_error = RVAndroidError("Middle layer", inner_cause)
    #     outer_error = RVAndroidError("Outer layer", middle_error)
    #
    #     assert outer_error.message == "Outer layer"
    #     assert outer_error.cause == middle_error
    #     # The string representation needs to match exactly what RVAndroidError.__str__ produces
    #     # Let's be more explicit about what we expect and avoid string concatenation
    #     expected_str = f"RVAndroidError: Outer layer caused by RVAndroidError: Middle layer caused by ValueError: Inner error"
    #     assert str(outer_error) == expected_str


class TestDerivedExceptions:
    """Tests for all exceptions derived from RVAndroidError."""

    def test_configuration_error(self):
        """Test ConfigurationError initialization and inheritance."""
        error = ConfigurationError("Config error")
        assert isinstance(error, RVAndroidError)
        assert error.message == "Config error"
        assert str(error) == "ConfigurationError: Config error"

    def test_resource_error(self):
        """Test ResourceError initialization and inheritance."""
        error = ResourceError("Resource error")
        assert isinstance(error, RVAndroidError)
        assert error.message == "Resource error"
        assert str(error) == "ResourceError: Resource error"

    def test_network_error(self):
        """Test NetworkError initialization and inheritance."""
        error = NetworkError("Network error")
        assert isinstance(error, RVAndroidError)
        assert error.message == "Network error"
        assert str(error) == "NetworkError: Network error"

    def test_emulator_error(self):
        """Test EmulatorError initialization and inheritance."""
        error = EmulatorError("Emulator error")
        assert isinstance(error, RVAndroidError)
        assert error.message == "Emulator error"
        assert str(error) == "EmulatorError: Emulator error"

    def test_adb_error(self):
        """Test ADBError initialization and inheritance."""
        error = ADBError("ADB error")
        assert isinstance(error, NetworkError)  # ADBError extends NetworkError
        assert isinstance(error, RVAndroidError)
        assert error.message == "ADB error"
        assert str(error) == "ADBError: ADB error"

    def test_instrumentation_error(self):
        """Test InstrumentationError initialization and inheritance."""
        error = InstrumentationError("Instrumentation error")
        assert isinstance(error, RVAndroidError)
        assert error.message == "Instrumentation error"
        assert str(error) == "InstrumentationError: Instrumentation error"

    def test_analysis_error(self):
        """Test AnalysisError initialization and inheritance."""
        error = AnalysisError("Analysis error")
        assert isinstance(error, RVAndroidError)
        assert error.message == "Analysis error"
        assert str(error) == "AnalysisError: Analysis error"

    def test_test_execution_error(self):
        """Test ExecutionError initialization and inheritance."""
        error = ExecutionError("Test execution error")
        assert isinstance(error, RVAndroidError)
        assert error.message == "Test execution error"
        assert str(error) == "ExecutionError: Test execution error"

    def test_monitor_error(self):
        """Test MonitorError initialization and inheritance."""
        error = MonitorError("Monitor error")
        assert isinstance(error, RVAndroidError)
        assert error.message == "Monitor error"
        assert str(error) == "MonitorError: Monitor error"

    def test_rv_timeout_error(self):
        """Test RvTimeoutError initialization and inheritance."""
        error = RvTimeoutError("Timeout error")
        assert isinstance(error, RVAndroidError)
        assert error.message == "Timeout error"
        assert str(error) == "RvTimeoutError: Timeout error"


class TestSpecializedExceptions:
    """Tests for exceptions with additional attributes or special behavior."""

    def test_task_execution_error(self):
        """Test TaskExecutionError with task_id."""
        error = TaskExecutionError("Task failed", 42)
        assert isinstance(error, ExecutionError)
        assert error.message == "Task failed"
        assert error.task_id == 42
        assert str(error) == "TaskExecutionError: Task failed (Task ID: 42)"

    def test_task_execution_error_with_cause(self):
        """Test TaskExecutionError with task_id and cause."""
        cause = ValueError("Original error")
        error = TaskExecutionError("Task failed", 42, cause)
        assert error.message == "Task failed"
        assert error.task_id == 42
        assert error.cause == cause
        assert str(error) == "TaskExecutionError: Task failed caused by ValueError: Original error (Task ID: 42)"

    def test_tool_error(self):
        """Test ToolError with tool_name."""
        error = ToolError("Tool failed", "DroidBot")
        assert isinstance(error, ExecutionError)
        assert error.message == "Tool failed"
        assert error.tool_name == "DroidBot"
        assert str(error) == "ToolError: Tool failed (Tool: DroidBot)"

    def test_tool_error_with_cause(self):
        """Test ToolError with tool_name and cause."""
        cause = ValueError("Original error")
        error = ToolError("Tool failed", "DroidBot", cause)
        assert error.message == "Tool failed"
        assert error.tool_name == "DroidBot"
        assert error.cause == cause
        assert str(error) == "ToolError: Tool failed caused by ValueError: Original error (Tool: DroidBot)"

    def test_logcat_error(self):
        """Test LogcatError initialization and inheritance."""
        error = LogcatError("Logcat error")
        assert isinstance(error, AnalysisError)
        assert isinstance(error, RVAndroidError)
        assert error.message == "Logcat error"
        assert str(error) == "LogcatError: Logcat error"

    def test_coverage_error(self):
        """Test CoverageError initialization and inheritance."""
        error = CoverageError("Coverage error")
        assert isinstance(error, AnalysisError)
        assert isinstance(error, RVAndroidError)
        assert error.message == "Coverage error"
        assert str(error) == "CoverageError: Coverage error"


class TestExceptionHierarchy:
    """Tests for validating the exception hierarchy."""

    def test_networkError_inheritance(self):
        """Test NetworkError inheritance structure."""
        assert issubclass(NetworkError, RVAndroidError)
        assert issubclass(ADBError, NetworkError)
        assert issubclass(ADBError, RVAndroidError)

    def test_analysisError_inheritance(self):
        """Test AnalysisError inheritance structure."""
        assert issubclass(AnalysisError, RVAndroidError)
        assert issubclass(LogcatError, AnalysisError)
        assert issubclass(CoverageError, AnalysisError)
        assert issubclass(LogcatError, RVAndroidError)
        assert issubclass(CoverageError, RVAndroidError)

    def test_execution_error_inheritance(self):
        """Test ExecutionError inheritance structure."""
        assert issubclass(ExecutionError, RVAndroidError)
        assert issubclass(TaskExecutionError, ExecutionError)
        assert issubclass(ToolError, ExecutionError)
        assert issubclass(TaskExecutionError, RVAndroidError)
        assert issubclass(ToolError, RVAndroidError)


class TestExceptionUsage:
    """Tests for common exception usage patterns."""

    def test_try_except_with_cause(self):
        """Test try/except pattern with cause propagation."""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise AnalysisError("Analysis failed", e)
        except AnalysisError as ae:
            assert ae.message == "Analysis failed"
            assert isinstance(ae.cause, ValueError)
            assert str(ae.cause) == "Original error"

    def test_exception_chaining(self):
        """Test exception chaining across multiple layers."""
        try:
            try:
                try:
                    raise ValueError("Low-level error")
                except ValueError as e:
                    raise ADBError("ADB command failed", e)
            except ADBError as e:
                raise EmulatorError("Emulator operation failed", e)
        except EmulatorError as ee:
            assert ee.message == "Emulator operation failed"
            assert isinstance(ee.cause, ADBError)
            assert isinstance(ee.cause.cause, ValueError)
