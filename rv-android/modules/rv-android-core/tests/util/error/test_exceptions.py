# tests/util/error/test_exceptions.py
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

from rv_android_core.util.error.exceptions import (
    ADBError,
    AnalysisError,
    CommandValidationError,
    ConfigurationError,
    EmulatorError,
    EventProcessingError,
    ExecutionError,
    InstrumentationError,
    JarNotFoundError,
    LogcatValidationError,
    NetworkError,
    RVAndroidError,
    RVCommandTimeoutError,
    RVExperimentError,
    RVExperimentExecutionError,
    RVParsingError,
    RVToolError,
    RVToolExecutionError,
    RVToolTimeoutError,
    RVValidationError,
    TaskExecutionError,
    ToolNotFoundError,
    ToolRegistrationError,
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
        assert (
            str(error)
            == "RVAndroidError: Test error message caused by ValueError: Original error"
        )


class TestDerivedExceptions:
    """Tests for all exceptions derived from RVAndroidError."""

    def test_configuration_error(self):
        """Test ConfigurationError initialization and inheritance."""
        error = ConfigurationError("Config error")
        assert isinstance(error, RVAndroidError)
        assert error.message == "Config error"
        assert str(error) == "ConfigurationError: Config error"

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
        assert isinstance(error, NetworkError)
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

    def test_execution_error(self):
        """Test ExecutionError initialization and inheritance."""
        error = ExecutionError("Test execution error")
        assert isinstance(error, RVAndroidError)
        assert error.message == "Test execution error"
        assert str(error) == "ExecutionError: Test execution error"

    def test_event_processing_error(self):
        """Test EventProcessingError initialization and inheritance."""
        error = EventProcessingError("Event error", "TEST_EVENT")
        assert isinstance(error, RVAndroidError)
        assert error.message == "Event error"
        assert error.event_type == "TEST_EVENT"
        assert str(error) == "EventProcessingError: Event error (Event: TEST_EVENT)"

    def test_event_processing_error_without_event_type(self):
        """Test EventProcessingError without event_type."""
        error = EventProcessingError("Event error")
        assert error.event_type is None
        assert str(error) == "EventProcessingError: Event error"


class TestValidationExceptions:
    """Tests for validation-related exceptions."""

    def test_rv_validation_error(self):
        """Test RVValidationError initialization and inheritance."""
        error = RVValidationError("Validation failed", "test_field")
        assert isinstance(error, ConfigurationError)
        assert isinstance(error, RVAndroidError)
        assert error.message == "Validation failed"
        assert error.field_name == "test_field"
        assert "(Field: test_field)" in str(error)

    def test_rv_validation_error_without_field(self):
        """Test RVValidationError without field_name."""
        error = RVValidationError("Validation failed")
        assert error.field_name is None
        assert str(error) == "RVValidationError: Validation failed"

    def test_command_validation_error(self):
        """Test CommandValidationError initialization and inheritance."""
        error = CommandValidationError("Invalid command", "cmd_field")
        assert isinstance(error, RVValidationError)
        assert isinstance(error, ConfigurationError)
        assert isinstance(error, RVAndroidError)
        assert error.message == "Invalid command"
        assert error.field_name == "cmd_field"

    def test_logcat_validation_error(self):
        """Test LogcatValidationError initialization and inheritance."""
        error = LogcatValidationError("Invalid logcat config", "tags_field")
        assert isinstance(error, RVValidationError)
        assert isinstance(error, ConfigurationError)
        assert isinstance(error, RVAndroidError)
        assert error.message == "Invalid logcat config"
        assert error.field_name == "tags_field"


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
        assert (
            str(error)
            == "TaskExecutionError: Task failed caused by ValueError: Original error (Task ID: 42)"
        )

    def test_rv_command_timeout_error(self):
        """Test RVCommandTimeoutError with timeout and command."""
        error = RVCommandTimeoutError(
            "Command timed out", timeout_seconds=30, command="adb shell"
        )
        assert isinstance(error, RVAndroidError)
        assert error.message == "Command timed out"
        assert error.timeout_seconds == 30
        assert error.command == "adb shell"
        assert "(Timeout: 30s)" in str(error)
        assert "(Command: adb shell)" in str(error)

    def test_rv_command_timeout_error_without_optional_fields(self):
        """Test RVCommandTimeoutError without optional fields."""
        error = RVCommandTimeoutError("Command timed out")
        assert error.timeout_seconds is None
        assert error.command is None
        assert str(error) == "RVCommandTimeoutError: Command timed out"

    def test_jar_not_found_error(self):
        """Test JarNotFoundError with jar_name and search_paths."""
        error = JarNotFoundError(
            "JAR not found", jar_name="test.jar", search_paths=["/path1", "/path2"]
        )
        assert isinstance(error, RVAndroidError)
        assert error.message == "JAR not found"
        assert error.jar_name == "test.jar"
        assert error.search_paths == ["/path1", "/path2"]
        assert "(JAR: test.jar)" in str(error)
        assert "(Searched: 2 paths)" in str(error)

    def test_jar_not_found_error_without_optional_fields(self):
        """Test JarNotFoundError without optional fields."""
        error = JarNotFoundError("JAR not found")
        assert error.jar_name is None
        assert error.search_paths == []
        assert str(error) == "JarNotFoundError: JAR not found"

    def test_rv_tool_error(self):
        """Test RVToolError with tool_name."""
        error = RVToolError("Tool failed", "DroidBot")
        assert isinstance(error, RVAndroidError)
        assert error.message == "Tool failed"
        assert error.tool_name == "DroidBot"
        assert str(error) == "RVToolError: Tool failed (Tool: DroidBot)"

    def test_rv_tool_error_without_tool_name(self):
        """Test RVToolError without tool_name."""
        error = RVToolError("Tool failed")
        assert error.tool_name is None
        assert str(error) == "RVToolError: Tool failed"

    def test_rv_tool_execution_error(self):
        """Test RVToolExecutionError inherits from RVToolError."""
        error = RVToolExecutionError("Execution failed", "monkey")
        assert isinstance(error, RVToolError)
        assert isinstance(error, RVAndroidError)
        assert error.message == "Execution failed"
        assert error.tool_name == "monkey"

    def test_rv_tool_timeout_error(self):
        """Test RVToolTimeoutError with tool_name and timeout_seconds."""
        error = RVToolTimeoutError("Timeout", "droidbot", timeout_seconds=60)
        assert isinstance(error, RVToolError)
        assert isinstance(error, RVAndroidError)
        assert error.message == "Timeout"
        assert error.tool_name == "droidbot"
        assert error.timeout_seconds == 60
        assert "(Tool: droidbot)" in str(error)
        assert "(Timeout: 60s)" in str(error)

    def test_rv_tool_timeout_error_without_optional_fields(self):
        """Test RVToolTimeoutError without optional fields."""
        error = RVToolTimeoutError("Timeout")
        assert error.tool_name is None
        assert error.timeout_seconds is None

    def test_tool_not_found_error(self):
        """Test ToolNotFoundError inherits from RVToolError."""
        error = ToolNotFoundError("Tool not found", "missing_tool")
        assert isinstance(error, RVToolError)
        assert isinstance(error, RVAndroidError)
        assert error.message == "Tool not found"
        assert error.tool_name == "missing_tool"

    def test_tool_registration_error(self):
        """Test ToolRegistrationError inherits from RVToolError."""
        error = ToolRegistrationError("Registration failed", "failing_tool")
        assert isinstance(error, RVToolError)
        assert isinstance(error, RVAndroidError)
        assert error.message == "Registration failed"
        assert error.tool_name == "failing_tool"

    def test_rv_experiment_error(self):
        """Test RVExperimentError with experiment_id."""
        error = RVExperimentError("Experiment failed", "exp_001")
        assert isinstance(error, RVAndroidError)
        assert error.message == "Experiment failed"
        assert error.experiment_id == "exp_001"
        assert "(Experiment: exp_001)" in str(error)

    def test_rv_experiment_error_without_experiment_id(self):
        """Test RVExperimentError without experiment_id."""
        error = RVExperimentError("Experiment failed")
        assert error.experiment_id is None
        assert str(error) == "RVExperimentError: Experiment failed"

    def test_rv_experiment_execution_error(self):
        """Test RVExperimentExecutionError inherits from RVExperimentError."""
        error = RVExperimentExecutionError("Execution failed", "exp_002")
        assert isinstance(error, RVExperimentError)
        assert isinstance(error, RVAndroidError)
        assert error.message == "Execution failed"
        assert error.experiment_id == "exp_002"

    def test_rv_parsing_error(self):
        """Test RVParsingError with parser_type."""
        error = RVParsingError("Parse failed", "xml_parser")
        assert isinstance(error, RVAndroidError)
        assert error.message == "Parse failed"
        assert error.parser_type == "xml_parser"
        assert "(Parser: xml_parser)" in str(error)

    def test_rv_parsing_error_without_parser_type(self):
        """Test RVParsingError without parser_type."""
        error = RVParsingError("Parse failed")
        assert error.parser_type is None
        assert str(error) == "RVParsingError: Parse failed"


class TestExceptionHierarchy:
    """Tests for validating the exception hierarchy."""

    def test_network_error_inheritance(self):
        """Test NetworkError inheritance structure."""
        assert issubclass(NetworkError, RVAndroidError)
        assert issubclass(ADBError, NetworkError)
        assert issubclass(ADBError, RVAndroidError)

    def test_execution_error_inheritance(self):
        """Test ExecutionError inheritance structure."""
        assert issubclass(ExecutionError, RVAndroidError)
        assert issubclass(TaskExecutionError, ExecutionError)
        assert issubclass(TaskExecutionError, RVAndroidError)

    def test_validation_error_inheritance(self):
        """Test RVValidationError inheritance structure."""
        assert issubclass(RVValidationError, ConfigurationError)
        assert issubclass(RVValidationError, RVAndroidError)
        assert issubclass(CommandValidationError, RVValidationError)
        assert issubclass(LogcatValidationError, RVValidationError)
        assert issubclass(CommandValidationError, ConfigurationError)
        assert issubclass(LogcatValidationError, ConfigurationError)

    def test_tool_error_inheritance(self):
        """Test RVToolError inheritance structure."""
        assert issubclass(RVToolError, RVAndroidError)
        assert issubclass(RVToolExecutionError, RVToolError)
        assert issubclass(RVToolTimeoutError, RVToolError)
        assert issubclass(ToolNotFoundError, RVToolError)
        assert issubclass(ToolRegistrationError, RVToolError)

    def test_experiment_error_inheritance(self):
        """Test RVExperimentError inheritance structure."""
        assert issubclass(RVExperimentError, RVAndroidError)
        assert issubclass(RVExperimentExecutionError, RVExperimentError)
        assert issubclass(RVExperimentExecutionError, RVAndroidError)


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

    def test_tool_error_chaining(self):
        """Test RVToolError chaining with cause."""
        cause = RuntimeError("Process crashed")
        RVToolExecutionError("Tool crashed", "monkey")
        error_with_cause = RVToolExecutionError(
            "Tool execution failed", "monkey", cause
        )
        assert error_with_cause.cause == cause
        assert "caused by RuntimeError" in str(error_with_cause)

    def test_experiment_error_chaining(self):
        """Test RVExperimentError chaining with cause."""
        cause = RVToolError("Tool failed", "droidbot")
        error = RVExperimentExecutionError("Experiment failed", "exp_001", cause)
        assert error.cause == cause
        assert "caused by RVToolError" in str(error)
