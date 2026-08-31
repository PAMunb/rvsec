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
- File-level caching under the artefact's own key: an existing output JSON is
  reused when it records the scope key this run would use, or no key at all
  (INV-ANA-70). Nothing else about the content is validated — a partial file
  from a timeout is still a hit, because the parser recovers it

### Role in the System:

- Called by rv-experiment's PreProcessor during pre-processing, before any
  task runs. rv-platform does not run analyses — its components only read
  artefacts already on disk, via the parser.
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
from rv_static_analysis.analysis.static.denominator_gate import (
    REFUSED_ARTIFACT_SUFFIX,
    DenominatorImplausibleError,
    check_denominator,
)
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
    # The key this run filtered on, and where the key came from. Recorded here
    # because the artefact cannot carry it: GATOR writes the manifest package
    # into the JSON's `package` member irrespective of the `codePackage` client
    # parameter it ran under, so two analyses of one APK under two keys are
    # indistinguishable from the files alone (INV-ANA-58). The run states what
    # it did; nothing reads back.
    code_package: str = Field(
        default="", description="Package key used to scope app-owned classes"
    )
    code_package_source: str = Field(
        default="",
        description="Origin of the key: 'manifest', 'manifest-neutralized' or "
        "'detector'. 'manifest-neutralized' means the build-type suffix policy "
        "removed a segment; the policy being on with nothing to remove still "
        "reports 'manifest', because the value names what produced the key",
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

    - Instantiated by rv-experiment's PreProcessor, once per APK
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
        # Record the key and its origin at the moment the analysis runs, on the
        # result and in the log. Both the GATOR argv and the parser receive this
        # same value below; nothing recovers it from a stored artefact
        # afterwards (INV-ANA-58).
        self.result.code_package = self.app.code_package
        self.result.code_package_source = self.app.code_package_source

        self.logger.info(
            "Starting static analysis",
            extra={
                "app_name": self.app.name,
                "app_package": self.app.package_name,
                "code_package": self.result.code_package,
                "code_package_source": self.result.code_package_source,
            },
        )

        try:
            self._run_analysis()
            self.result.execution_times = self.execution_times
            self._check_denominator()

            self.logger.info(
                "Static analysis completed",
                extra={
                    "execution_times": self.execution_times,
                    "total_time": sum(self.execution_times.values()),
                },
            )
            return self.result

        except DenominatorImplausibleError as e:
            # A refused denominator fails this APK's analysis and no more. It is
            # reported through the same channel as an execution failure — a
            # failed result carrying the message — rather than propagating,
            # because the decorator above would swallow a raise and return
            # `None`, which is the silence the gate exists to end. Stopping a
            # 200-APK campaign is not warranted either: the refusal names the
            # parsed count, the compiled count and the key, so the operator
            # re-runs that APK once the jar or the key is corrected.
            self.logger.error(
                "Static analysis refused: implausible denominator",
                extra={
                    "error_message": str(e),
                    "code_package": self.result.code_package,
                },
            )
            self.result.success = False
            self.result.errors.append(str(e))
            self._quarantine_refused_artifact()
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

    def _quarantine_refused_artifact(self) -> None:
        """Move a refused artefact out of the path every consumer reads.

        Without this the gate is a log line. Everything downstream keys on the
        artefact's **presence**, not on the result object the analysis returned:
        `pre_processor._report_missing_static_analysis` builds its list with
        `os.path.exists(<apk>.apk.json)`, and `result_processor._resolve_static_data`
        calls `read_static_analysis_files(results_dir, apk)`, which finds the file
        by name. So a refused artefact left on disk is parsed and its collapsed
        class list is published as a coverage percentage with `measured=true` —
        the outcome INV-ANA-69's scenario forbids in as many words ("the pipeline
        MUST NOT publish a coverage percentage for that APK").

        The file is **renamed, not deleted**. The refusal is a tripwire on a
        stale `lib/gator/` jar or on a key the deny-list could not resolve, and
        both are diagnosed from the artefact itself — the recorded key, its
        origin and `class_defs_under_key` are what name the cause. With the
        suffix gone the consumers see it as absent, so the row takes the honest
        path that already exists: empty coverage cells, `measured=false`
        (INV-PLT-35), violation columns written as usual.
        """
        if not os.path.isfile(self.analysis_file):
            return
        quarantined = self.analysis_file + REFUSED_ARTIFACT_SUFFIX
        os.replace(self.analysis_file, quarantined)
        self.logger.warning(
            f"Refused artefact moved to {quarantined}: the APK will run without a "
            "coverage denominator (empty cells, measured=false) rather than "
            "publish a percentage over a denominator the gate rejected"
        )

    def _check_denominator(self) -> None:
        """Judge the denominator the run just produced (INV-ANA-69).

        `analyze()` is the only place that holds both the APK and the key, which
        is why the gate is wired here and the parser stays keyless (INV-ANA-61).
        It costs a parse: `analyze()` does not read the artefact today — that
        happens in `get_static_data()` — so this is a read that did not exist.

        **The gate raises.** It landed warn-only only while the run had no way
        to supply a key that resolves: under the literal manifest key 75 of the
        162 corpus APKs have no compiled class at all, and aborting 46% of a
        campaign for a reason the run itself could not fix would have been a
        tripwire on the operator rather than on the pipeline. The build-type
        suffix policy is that way, so the tolerance goes: a warning is what the
        code already emitted at several of these points, and it is why these
        defects survived three changes.

        A legacy artefact that records no `class_defs_under_key` is still not
        judged: the gate has no universe to divide by, and inventing one would
        be the silent measurement this whole change removes.

        Raises:
            DenominatorImplausibleError: the artefact's class list cannot be the
                app's class universe under the key that produced it.
        """
        try:
            data = StaticAnalysisParser().parse_file(self.analysis_file)
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.warning(f"Denominator not checked: artefact unreadable ({exc})")
            return

        if data.class_defs_under_key is None:
            self.logger.debug(
                "Denominator not checked: the artefact records no "
                "class_defs_under_key (pre-INV-ANA-66 producer)"
            )
            return

        key = data.code_package or self.result.code_package or ""
        check_denominator(data.classes, data.class_defs_under_key, key)

    def _run_analysis(self) -> None:
        """Build and execute the GATOR analysis command."""
        cmd_args = self.config.get_tool_command(
            "analysis",
            self.app.path,
            self.analysis_file,
            code_package=self.app.code_package,
            code_package_source=self.app.code_package_source,
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

    def _disagreeing_recorded_key(self, result_file: str) -> Optional[str]:
        """The scope key a stored artefact records, when it is not this run's.

        `None` means the artefact may be reused, and it covers two different
        situations deliberately. An artefact that records **no** key — every one
        produced before INV-ANA-66, which is all 162 of the article corpus — is
        reused: the `package` member is the manifest package whatever key
        filtered the file, so resolving a key from it would be exactly the
        invented measurement this change removes (INV-ANA-58). And an artefact
        recording this run's own key is reused because it is the same artefact
        this run would produce.

        An unreadable artefact is also reused rather than regenerated: the
        parser recovers truncated JSON on purpose (INV-ANA-06), so a parse
        failure here says something about this method, not about the file.

        The key is read through the parser and not with a bare `json.load`, and
        the cost is real — 2258 ms against 318 ms on the corpus's largest
        artefact (`org.quantumbadger.redreader_117`, 48 MB), because the parser
        builds four domain aggregates to answer one string. It is paid on
        purpose: a timed-out GATOR run leaves a **truncated** artefact, which
        `json.load` rejects outright and the parser recovers by bracket closing.
        Reading it the fast way would turn exactly those artefacts — the ones a
        key change is most likely to have stranded — into unverifiable reuses,
        which is the check's own failure mode. This runs once per APK during
        pre-processing, never on resume; `result_processor` is what re-reads
        artefacts there, and it does not call this.
        """
        try:
            recorded = StaticAnalysisParser().parse_file(result_file).code_package
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.warning(
                f"Scope key of {result_file} not verified: artefact unreadable "
                f"({exc}); reusing it"
            )
            return None

        if not recorded or recorded == self.app.code_package:
            return None
        return recorded

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
            # File-level caching: an existing output JSON answers for this run, but
            # only under its own scope key (INV-ANA-70). Existence alone used to
            # imply completion, which silently reused an artefact produced under a
            # different key the moment a run's key policy changed — and the
            # denominator gate would then have judged the old artefact by the new
            # key. What survives unchanged is the reuse itself, which is what makes
            # experiment resume cheap.
            if os.path.isfile(result_file):
                stale_key = self._disagreeing_recorded_key(result_file)
                if stale_key is None:
                    self.logger.info(
                        "Analysis result already exists, skipping",
                        extra={
                            "tool_name": name,
                            "result_file": result_file,
                        },
                    )
                    return CommandResult(0, b"", b"")

                self.logger.warning(
                    f"Regenerating {result_file}: it was produced under scope key "
                    f"'{stale_key}' and this run scopes by "
                    f"'{self.app.code_package}'. Reusing it would publish a "
                    "denominator built from one key against coverage measured "
                    "under another."
                )
                os.remove(result_file)

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
            static_data = parser.parse_file(self.analysis_file)
            # The key is logged because this run *performed* the analysis and
            # chose the scope (INV-ANA-58); it is not passed to the parse, which
            # reads the artefact at the scope already baked into it.
            self.logger.info(
                "Static analysis data parsed",
                extra={
                    "package": self.app.code_package,
                    "code_package_source": self.app.code_package_source,
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
