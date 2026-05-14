"""
Orchestrate static analysis of Android applications via the GATOR-based client.

Run the unified GATOR analysis client on Android APKs to produce a single JSON
file containing reachability data, window definitions, and window transitions.
The client writes sections in priority order with flush between each, so a
timeout still preserves the most critical data (reachability first, then
windows, then transitions).

### Architectural Decisions:

- Single-client invocation: one GATOR process produces all three analysis
  sections (reachability, windows, transitions) in a single JSON file, avoiding
  the coordination overhead of three separate tools (GESDA, GATOR, REACH)
- Priority-ordered output: the client flushes reachability before windows and
  windows before transitions, so timeout yields gracefully degraded data
- File-level caching: if the output JSON already exists, the analysis is
  skipped entirely (no content validation — existence implies completion or
  partial timeout output that the parser can recover)

### Role in the System:

- Called by StaticAnalysisComponent in rv-platform during pre-processing
  (Phase 1 of TaskExecutor, outside emulator session)
- Produces StaticAnalysisData consumed by rv-agent (navigation guidance,
  MOP prioritization) and rv-coverage (method universe for coverage %)

### Integration Points:

- Input: App instance (APK path, package name) from rv-android-core
- Output: StaticAnalysisResult with JSON file path and execution metrics
- Parser: StaticAnalysisParser converts the JSON into StaticAnalysisData
- Dependencies: rv-android-core (Command, ErrorHandler, App, BaseAnalyzer)
"""

import os.path
import sys
import time
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator
from rv_android_core.analysis.base_analyzer import BaseAnalyzer
from rv_android_core.commands.command import Command
from rv_android_core.commands.command_result import CommandResult
from rv_android_core.constants import EXTENSION_STATIC_ANALYSIS
from rv_android_core.domain.app import App
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import RVAndroidError, RVCommandTimeoutError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.context_adapter import ContextAdapter
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.validation import BaseValidatedModel, validated_model
from rv_static_analysis.config import RVStaticAnalysisConfig
from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser


class StaticAnalysisException(RVAndroidError):
    """Exception raised for errors in static analysis execution."""


class StaticAnalysisResult(BaseValidatedModel):
    """Result from static analysis execution."""

    analysis_file: str = Field(
        default="", description="Path to unified analysis JSON output"
    )
    success: bool = Field(default=True, description="Overall success status")
    timed_out: bool = Field(
        default=False, description="Whether analysis was interrupted by timeout"
    )
    errors: List[str] = Field(
        default_factory=list, description="Error messages encountered during analysis"
    )
    execution_times: Dict[str, float] = Field(
        default_factory=dict, description="Execution times per phase in seconds"
    )


@validated_model(["app", "config", "output_dir"])
class StaticAnalyzer(BaseValidatedModel, BaseAnalyzer[StaticAnalysisResult]):
    """
    Run the unified GATOR-based analysis client on a single APK.

    Orchestrate command execution, caching, timeout handling, and result
    parsing for the GATOR analysis client. The client produces a single JSON
    file with reachability, windows, and transitions sections written in
    priority order. On timeout, partial JSON is preserved and the parser
    recovers truncated sections via bracket recovery (INV-ANA-06).

    ### Architectural Decisions:

    - Pydantic + BaseAnalyzer dual inheritance: Pydantic provides validated
      construction and serialization; BaseAnalyzer provides the analyze/
      get_metrics interface expected by rv-platform components
    - File-level caching: if the output file exists, execution is skipped.
      This enables experiment resume without re-running expensive analysis
    - Timeout tolerance: RVCommandTimeoutError is caught and treated as a
      partial success — the parser handles truncated JSON gracefully

    ### Role in the System:

    - Instantiated by StaticAnalysisComponent in rv-platform for each task
    - analyze() returns StaticAnalysisResult; get_static_data() parses the
      JSON into StaticAnalysisData for downstream consumers
    - get_metrics() provides execution timing for performance reporting

    ### Integration Points:

    - Input: App (APK path, package), RVStaticAnalysisConfig (tool paths)
    - Output: StaticAnalysisResult (file path, timing, status)
    - Parser: StaticAnalysisParser converts JSON to StaticAnalysisData
    - Error handling: @ErrorHandler on analyze(), error_context in commands
    """

    app: App = Field(..., description="Android application to analyze")
    config: RVStaticAnalysisConfig = Field(
        default_factory=RVStaticAnalysisConfig,
        description="Configuration for static analysis",
    )
    output_dir: Optional[str] = Field(
        default=None, description="Directory for analysis output"
    )

    # BaseAnalyzer inherited fields
    analyzer_name: str = Field(default="static", exclude=True)
    static_data: Optional[StaticAnalysisData] = Field(default=None, exclude=True)

    # Internal state
    execution_times: Dict[str, float] = Field(default_factory=dict, exclude=True)
    result: StaticAnalysisResult = Field(
        default_factory=StaticAnalysisResult, exclude=True
    )
    logger: Optional[ContextAdapter] = Field(default=None, exclude=True)
    error_handler: Optional[ErrorHandler] = Field(default=None, exclude=True)
    analysis_file: str = Field(default="", exclude=True)

    @field_validator("app")
    @classmethod
    def validate_app(cls, v):
        """Validate that app is a valid App instance."""
        if (
            not hasattr(v, "name")
            or not hasattr(v, "package_name")
            or not hasattr(v, "path")
        ):
            raise ValueError(
                "app must be a valid App instance with name, package_name, and path"
            )
        return v

    def model_post_init(self, __context) -> None:
        """Initialize analyzer state after Pydantic construction.

        Resolve the output directory, create it on disk, build the analysis
        file path, and set up logging and error handling.

        State:
            self.output_dir: Resolved output directory. Defaults to
                config.output_dir / app.package_name if not provided.
            self.execution_times: Empty dict, populated during analyze().
            self.result: Fresh StaticAnalysisResult, updated during analyze().
            self.logger: ContextAdapter scoped to this analyzer instance.
            self.error_handler: Shared ErrorHandler singleton.
            self.analysis_file: Full path to the output JSON file.
        """
        if self.output_dir is None:
            self.output_dir = os.path.join(
                self.config.output_dir, self.app.package_name
            )

        self.execution_times = {}
        self.result = StaticAnalysisResult()

        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_static_analysis.analysis.static.static_analysis.StaticAnalyzer",
            {CONTEXT_COMPONENT: "StaticAnalyzer", "app_package": self.app.package_name},
        )
        self.error_handler = ErrorHandler.get_instance()

        os.makedirs(self.output_dir, exist_ok=True)

        # Single output file: {app_name}.json
        self.analysis_file = os.path.join(
            self.output_dir, f"{self.app.name}{EXTENSION_STATIC_ANALYSIS}"
        )
        self.result.analysis_file = self.analysis_file

        self.logger.info(
            "StaticAnalyzer initialized",
            extra={
                "output_dir": self.output_dir,
                "app_name": self.app.name,
                "analysis_file": self.analysis_file,
            },
        )

    def _initialize_from_static_data(self) -> None:
        """Satisfy BaseAnalyzer interface — no initialization needed."""

    @ErrorHandler.handle_errors(component="StaticAnalyzer", phase="static_analysis")
    def analyze(self, data: Any = None) -> StaticAnalysisResult:
        """Run the unified analysis client on the APK.

        Execute the GATOR analysis command and collect execution metrics.
        On StaticAnalysisException (non-zero exit code), the result is
        marked as failed but still returned with error details.

        Args:
            data: Unused. Present to satisfy the BaseAnalyzer interface.

        Returns:
            StaticAnalysisResult with analysis file path, success status,
            timeout flag, error messages, and per-phase execution times.
        """
        self.logger.info(
            "Starting static analysis",
            extra={
                "app_name": self.app.name,
                "app_package": self.app.package_name,
            },
        )

        try:
            self._run_analysis()
            self.result.execution_times = self.execution_times

            self.logger.info(
                "Static analysis completed",
                extra={
                    "execution_times": self.execution_times,
                    "total_time": sum(self.execution_times.values()),
                },
            )
            return self.result

        except StaticAnalysisException as e:
            self.logger.error(
                "Static analysis failed",
                extra={
                    "error_message": str(e),
                },
            )
            self.result.success = False
            self.result.errors.append(str(e))
            return self.result

    def _run_analysis(self) -> None:
        """Build and execute the GATOR analysis command."""
        cmd_args = self.config.get_tool_command(
            "analysis",
            self.app.path,
            self.analysis_file,
            code_package=self.app.code_package,
        )
        cmd = Command(cmd_args[0], cmd_args[1:], timeout=self.config.analysis_timeout)
        self._execute_command("ANALYSIS", self.analysis_file, cmd)

        # Defensive post-condition: GATOR writes JSON incrementally (reachability
        # → windows → transitions). Even a timed-out run produces a partial file.
        # If nothing exists, the invocation failed (typically CommandNotFoundError
        # swallowed upstream) — escalate so the caller sees a hard error instead
        # of zeroed coverage metrics downstream.
        if not os.path.isfile(self.analysis_file):
            raise StaticAnalysisException(
                f"GATOR did not produce output JSON at {self.analysis_file}; "
                "check that the python interpreter and gator launcher are reachable."
            )

    def _execute_command(
        self, name: str, result_file: str, command: Command
    ) -> CommandResult:
        """Execute analysis command with caching, timeout handling, and logging.

        If the output file already exists, execution is skipped (cache hit).
        On timeout, the partial JSON is preserved -- the parser handles
        truncated files via bracket recovery (INV-ANA-06).

        Args:
            name: Human-readable label for the analysis phase (used in logs
                and execution_times keys).
            result_file: Expected output file path. If this file exists,
                execution is skipped.
            command: Command instance to invoke.

        Returns:
            CommandResult from the executed command, or a synthetic
            success result (exit code 0) on cache hit or timeout.

        Raises:
            StaticAnalysisException: When the command exits with a non-zero
                code (not caused by timeout).
        """
        with self.error_handler.error_context(
            component="StaticAnalyzer",
            phase="command_execution",
            tool_name=name,
            app_name=self.app.name,
        ):
            # File-level caching: if the output JSON exists, skip execution entirely.
            # We do not validate content -- existence implies a previous run completed
            # (or timed out with partial output the parser can recover). This enables
            # experiment resume without re-running the expensive GATOR analysis.
            if os.path.isfile(result_file):
                self.logger.info(
                    "Analysis result already exists, skipping",
                    extra={
                        "tool_name": name,
                        "result_file": result_file,
                    },
                )
                return CommandResult(0, b"", b"")

            self.logger.info(
                f"Executing analysis: {name}",
                extra={
                    "tool_name": name,
                    "app_name": self.app.name,
                },
            )

            start_time = time.time()
            # Timeout is treated as partial success (not failure) because the GATOR
            # client writes sections in priority order -- reachability first, then
            # windows, then transitions -- and flushes between each. Even if killed
            # mid-write, the parser recovers truncated JSON via bracket completion
            # (INV-ANA-06), so a timed-out run still yields usable reachability data
            # (the most critical section for coverage calculation and MOP tracking).
            try:
                cmd_result = command.invoke(stdout=sys.stdout)
            except RVCommandTimeoutError:
                execution_time = time.time() - start_time
                self.execution_times[name] = execution_time
                self.result.timed_out = True
                self.logger.warning(
                    "Analysis timed out, partial JSON preserved",
                    extra={
                        "tool_name": name,
                        "execution_time": execution_time,
                    },
                )
                # Partial JSON is usable — parser recovers truncated files
                return CommandResult(0, b"", b"")

            execution_time = time.time() - start_time
            self.execution_times[name] = execution_time

            if cmd_result.code != 0:
                error_msg = f"Analysis {name} failed with exit code {cmd_result.code}"
                if cmd_result.stderr:
                    error_msg += f". Error: {cmd_result.get_stderr_text()}"
                self.logger.error(
                    "Analysis execution failed",
                    extra={
                        "tool_name": name,
                        "exit_code": cmd_result.code,
                        "execution_time": execution_time,
                    },
                )
                raise StaticAnalysisException(error_msg)

            self.logger.info(
                f"Analysis '{name}' completed",
                extra={
                    "tool_name": name,
                    "execution_time": execution_time,
                },
            )
            return cmd_result

    def get_metrics(self) -> Dict[str, Any]:
        """Collect execution metrics for monitoring and debugging.

        Returns:
            Dictionary with keys:
            - "execution_times" (Dict[str, float]): Per-phase times in seconds.
            - "total_execution_time" (float): Sum of all phase times.
            - "success" (bool): Whether analysis completed without errors.
            - "timed_out" (bool): Whether analysis was interrupted by timeout.
            - "error_count" (int): Number of errors encountered.
            - "errors" (List[str]): Error messages.
            - "analysis_file" (str): Path to the output JSON file.
        """
        total_time = sum(self.execution_times.values())
        return {
            "execution_times": self.execution_times,
            "total_execution_time": total_time,
            "success": self.result.success,
            "timed_out": self.result.timed_out,
            "error_count": len(self.result.errors),
            "errors": self.result.errors,
            "analysis_file": self.analysis_file,
        }

    def get_static_data(self) -> Optional[StaticAnalysisData]:
        """Parse the analysis JSON into StaticAnalysisData.

        Use StaticAnalysisParser.parse_file() which handles truncated JSON
        from timeout gracefully -- partial sections return empty domain objects.

        Returns:
            StaticAnalysisData with classes, windows, and WTG parsed from
            the analysis JSON, or None if analysis failed (not timed out)
            or parsing raised an exception.
        """
        if not self.result.success and not self.result.timed_out:
            self.logger.warning(
                "Cannot load static data: analysis failed",
                extra={
                    "errors": self.result.errors,
                },
            )
            return None

        try:
            parser = StaticAnalysisParser()
            static_data = parser.parse_file(self.analysis_file, self.app.code_package)
            self.logger.info(
                "Static analysis data parsed",
                extra={
                    "package": self.app.code_package,
                },
            )
            return static_data

        except Exception as e:
            self.logger.error(
                "Error parsing static analysis data",
                extra={
                    "error_message": str(e),
                    "analysis_file": self.analysis_file,
                },
            )
            return None
