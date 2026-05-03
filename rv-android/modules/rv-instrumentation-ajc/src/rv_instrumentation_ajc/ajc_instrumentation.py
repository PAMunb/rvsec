import json
import os
import shutil
import time
from pathlib import Path
from typing import List, Optional

import yaml
from rv_android_core import constants
from rv_android_core.commands.command import Command
from rv_android_core.commands.command_exception import CommandException
from rv_android_core.domain.app import App
from rv_android_core.util import utils
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import InstrumentationError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_instrumentation_core import Instrumenter
from rv_instrumentation_core import InstrumentationError as InstrumentationErrorModel
from rv_instrumentation_core import InstrumentationResults

from rv_instrumentation_ajc.config import AjcInstrumentationConfig


class AjcInstrumentation(Instrumenter):
    """
    A specialized system for instrumenting and preparing Android APKs for runtime verification
    with monitored operations integration.

    The AjcInstrumentation serves as the core instrumentation engine that transforms standard
    Android APKs into runtime verification-enabled artifacts. It orchestrates a sophisticated
    pipeline that integrates decompilation, monitor weaving, recompilation, and signing to
    produce instrumented APKs ready for monitored operations analysis.

    ### Architectural Decisions:
    - Implements a comprehensive APK instrumentation pipeline with monitor integration
    - Uses advanced decompilation and recompilation techniques through dex2jar and d8
    - Integrates AspectJ weaving for runtime verification monitor injection
    - Provides robust error handling and recovery mechanisms throughout the pipeline
    - Separates configuration management from instrumentation logic for flexibility
    - Uses centralized logging and error handling for operational visibility

    ### Role in the System:
    - Acts as the bridge between rv-monitor-generator artifacts and executable APKs
    - Transforms standard APKs into monitored operations-enabled test artifacts
    - Enables runtime verification by injecting generated monitoring components
    - Supports automated experiment workflows for monitored operations analysis
    - Provides the foundation for APK-based runtime verification testing
    - Integrates with experiment orchestration systems for batch processing

    ### Instrumentation Pipeline Architecture:
    - **Decompilation Phase:** DEX → JAR conversion using dex2jar toolchain
    - **Monitor Integration:** Injection of generated AspectJ and Java monitor artifacts
    - **Weaving Phase:** AspectJ compilation to integrate monitoring pointcuts
    - **Dependency Integration:** Runtime verification library inclusion
    - **Recompilation Phase:** JAR → DEX conversion using Android d8 compiler
    - **Signing Phase:** APK signing for deployment readiness

    ### Key Considerations:
    - Handles complex APK transformation while preserving application functionality
    - Manages Android SDK integration for platform compatibility
    - Supports multiple monitored operations specification sets (JCA, generic)
    - Implements comprehensive validation for all pipeline dependencies
    - Ensures minimal runtime overhead from injected monitoring components
    - Provides detailed error reporting for debugging complex instrumentation failures

    ### Integration Points:
    - Consumes monitor artifacts from rv-monitor-generator module
    - Integrates with experiment orchestration for batch APK processing
    - Provides instrumented APKs for testing tools and analysis frameworks
    - Supports configuration-driven deployment across different environments
    - Enables seamless integration with CI/CD workflows for automated testing

    ### Performance and Scalability:
    - Designed for efficient batch processing of multiple APKs
    - Implements optimized temporary directory management
    - Provides configurable resource cleanup and error recovery
    - Supports parallel processing through stateless design
    - Minimizes memory footprint through streaming file operations
    """

    def __init__(self, config: Optional[AjcInstrumentationConfig] = None):
        """
        Initialize AjcInstrumentation with configuration and logging integration.

        Args:
            config: Configuration object. If None, will be created with default settings
                   from environment variables or explicit paths.
        """
        self.config = config or AjcInstrumentationConfig()

        # Initialize structured logging through LoggingManager
        logging_manager = LoggingManager.get_instance()
        self._logger = logging_manager.get_logger(
            "rv_instrumentation_ajc.AjcInstrumentation",
            {
                CONTEXT_COMPONENT: "AjcInstrumentation",
                "component_module": "rv-instrumentation",
            },
        )

        # Initialize centralized error handling
        self._error_handler = ErrorHandler.get_instance()

        self._logger.info(
            "AjcInstrumentation initialized",
            extra={
                "config_summary": self.config.get_configuration_summary().model_dump()
            },
        )

    @ErrorHandler.handle_errors(
        component="AjcInstrumentation", phase="batch_instrumentation"
    )
    def instrument_apks(
        self,
        apks_dir: str,
        results_dir: str,
        force_instrumentation: bool = False,
        apk_paths: Optional[List[str]] = None,
    ) -> InstrumentationResults:
        """
        Execute batch instrumentation of multiple APKs with comprehensive error tracking.

        This method orchestrates the complete instrumentation pipeline for multiple APKs,
        providing robust error handling, progress tracking, and detailed logging throughout
        the process. It prepares the instrumentation environment, processes each APK through
        the complete pipeline, and generates comprehensive error reports.

        ### Processing Pipeline:
        1. Environment preparation and dependency validation
        2. APK discovery and validation in source directory
        3. Iterative instrumentation of each APK with error isolation
        4. Temporary resource cleanup and error report generation
        5. Final validation and instrumentation summary

        Args:
            apks_dir: Directory containing source APKs to be instrumented.
                     Must contain valid Android APK files.
            results_dir: Directory where instrumented APKs and error logs will be saved.
                        Created automatically if it doesn't exist.
            force_instrumentation: If True, re-instruments APKs even if already processed.
                                  Useful for configuration changes or monitor updates.

        Returns:
            InstrumentationResults model containing comprehensive instrumentation outcomes

        Raises:
            InstrumentationError: If instrumentation environment validation fails
        """
        results = InstrumentationResults()

        self._logger.info(
            "Starting batch APK instrumentation",
            extra={
                "apks_dir": apks_dir,
                "results_dir": results_dir,
                "force_instrumentation": force_instrumentation,
                "pipeline_stage": "initialization",
            },
        )

        # Validate and prepare instrumentation environment
        try:
            self.prepare_instrumentation(results_dir)
        except Exception as e:
            self._logger.error(
                "Failed to prepare instrumentation environment",
                extra={"error": str(e), "pipeline_stage": "preparation"},
            )

            context = {
                "component": "AjcInstrumentation",
                "operation": "prepare_instrumentation",
                "results_dir": results_dir,
            }
            self._error_handler.handle_error(
                InstrumentationError(
                    "Failed to prepare instrumentation environment", e
                ),
                context,
            )

            setup_error = InstrumentationErrorModel(
                code=-1, message=str(e), phase="preparation", tool=None
            )
            results.errors["setup_error"] = setup_error
            results.total_count = 1
            return results

        # Discover and validate APKs for instrumentation
        try:
            if apk_paths is not None:
                apks = [App(p) for p in apk_paths]
                self._logger.info(f"Using {len(apks)} APKs from provided list")
            else:
                apks = utils.get_apks(apks_dir)
        except Exception as e:
            self._logger.error(
                "Failed to retrieve APKs from directory",
                extra={
                    "apks_dir": apks_dir,
                    "error": str(e),
                    "pipeline_stage": "apk_discovery",
                },
            )

            context = {
                "component": "AjcInstrumentation",
                "operation": "get_apks",
                "apks_dir": apks_dir,
            }
            self._error_handler.handle_error(
                InstrumentationError("Failed to retrieve APKs", e), context
            )

            retrieval_error = InstrumentationErrorModel(
                code=-1, message=str(e), phase="retrieval", tool=None
            )
            results.errors["apk_retrieval_error"] = retrieval_error
            results.total_count = 1
            return results

        total_apks = len(apks)
        results.total_count = total_apks

        self._logger.info(
            f"Discovered {total_apks} APKs for instrumentation",
            extra={"total_apks": total_apks, "pipeline_stage": "processing_start"},
        )

        self._logger.debug(self.config)

        # Process each APK through the instrumentation pipeline
        for index, app in enumerate(apks, 1):
            self._logger.info(
                f"Processing APK {index}/{total_apks}: {app.name}",
                extra={
                    "app_name": app.name,
                    "progress": f"{index}/{total_apks}",
                    "pipeline_stage": "individual_processing",
                },
            )

            try:
                # Execute instrumentation pipeline with comprehensive error handling
                with ErrorHandler.get_instance().error_context(
                    app_name=app.name, phase="instrumentation"
                ):
                    # Validate APK before processing
                    self.config.validate_apk_input(app.path)

                    # Execute instrumentation if needed
                    self.instrument(app, results_dir, force_instrumentation)

                    # Verify successful instrumentation
                    self.check_if_instrumented(app)

                self._logger.info(
                    f"Successfully instrumented APK: {app.name}",
                    extra={"app_name": app.name, "pipeline_stage": "completed"},
                )

                results.success_count += 1

            except CommandException as ex:
                self._logger.error(
                    f"Command execution failed for APK: {app.name}",
                    extra={
                        "app_name": app.name,
                        "tool": ex.tool,
                        "error_code": ex.code,
                        "error_message": ex.message,
                        "pipeline_stage": "command_execution",
                    },
                )

                error_model = InstrumentationErrorModel(
                    code=ex.code,
                    tool=ex.tool,
                    message=ex.message,
                    phase=getattr(ex, "_error_phase", "command_execution"),
                )
                results.errors[app.name] = error_model

                # Use centralized error handling
                context = {
                    "component": "AjcInstrumentation",
                    "operation": "instrument",
                    "app_name": app.name,
                    "tool": ex.tool,
                }
                self._error_handler.handle_error(
                    InstrumentationError(f"Command execution failed: {ex.message}", ex),
                    context,
                )

            except Exception as ex:
                self._logger.error(
                    f"General error while instrumenting APK: {app.name}",
                    extra={
                        "app_name": app.name,
                        "app_path": app.path,
                        "error": str(ex),
                        "pipeline_stage": "general_error",
                    },
                )

                error_model = InstrumentationErrorModel(
                    code=-1,
                    message=str(ex),
                    phase=getattr(ex, "_error_phase", "general_error"),
                    tool=None,
                )
                results.errors[app.name] = error_model

                # Use centralized error handling
                context = {
                    "component": "AjcInstrumentation",
                    "operation": "instrument",
                    "app_name": app.name,
                }
                self._error_handler.handle_error(
                    InstrumentationError(f"Failed to instrument APK: {app.name}", ex),
                    context,
                )

            finally:
                # Clean up temporary directories after each APK
                self.clear([self.config.tmp_dir, self.config.rvm_tmp_dir])

        # Final cleanup of shared temporary directories
        self.clear([self.config.lib_tmp_dir])

        # Generate comprehensive error report and summary
        if results.errors:
            self._logger.warning(
                f"Instrumentation completed with {len(results.errors)} errors",
                extra={
                    "total_errors": len(results.errors),
                    "total_apks": total_apks,
                    "success_rate": results.success_rate,
                    "pipeline_stage": "error_reporting",
                },
            )

            # Save detailed error report
            errors_file = os.path.join(results_dir, "instrument_errors.json")
            with open(errors_file, "w") as outfile:
                # Convert Pydantic models to serializable format
                serializable_errors = {
                    name: error.model_dump() for name, error in results.errors.items()
                }
                json.dump(serializable_errors, outfile, indent=2)

            self._logger.info(
                f"Error report saved to: {errors_file}",
                extra={"errors_file": errors_file},
            )

            # Log individual error summaries
            for app_name, error_details in results.errors.items():
                self._logger.warning(
                    f"APK instrumentation failed: {app_name}",
                    extra={
                        "app_name": app_name,
                        "tool": error_details.tool or "unknown",
                        "phase": error_details.phase,
                        "error_code": error_details.code,
                    },
                )
        else:
            self._logger.info(
                "All APKs instrumented successfully",
                extra={
                    "total_apks": total_apks,
                    "success_rate": results.success_rate,
                    "pipeline_stage": "completed_successfully",
                },
            )

        return results

    @ErrorHandler.handle_errors(component="AjcInstrumentation", phase="preparation")
    def prepare_instrumentation(self, results_dir: str) -> None:
        """
        Prepare the instrumentation environment by cleaning temporary directories,
        executing Maven dependency resolution, and creating required output directories.

        This method sets up the complete instrumentation environment required for
        APK processing, including dependency management, temporary directory preparation,
        and output directory structure creation.

        Args:
            results_dir: Directory where instrumented APKs will be stored

        Raises:
            InstrumentationError: If environment preparation fails
        """
        self._logger.info(
            "Preparing instrumentation environment",
            extra={
                "results_dir": results_dir,
                "pipeline_stage": "environment_preparation",
            },
        )

        # Clean temporary directories from previous runs
        temp_dirs = [
            self.config.lib_tmp_dir,
            self.config.tmp_dir,
            self.config.rvm_tmp_dir,
        ]
        self.clear(temp_dirs)

        # Resolve runtime dependencies (rv-monitor-rt, rvsec-core,
        # rvsec-logger-logcat, aspectjrt) via the ABC's Template Method —
        # shared with dexlib2's prepare_instrumentation. AJC consumes ALL
        # four jars: aspectjrt is required for AspectJ weaving at this
        # variant's compile step (the .aj aspect file pulled by ajc).
        rvsec_root = self.config.rvsec_root or os.environ.get("RVSEC_HOME")
        if not rvsec_root:
            raise InstrumentationError(
                "RVSEC_HOME environment variable is not set and "
                "config.rvsec_root is None; cannot resolve runtime libraries."
            )
        self._resolve_runtime_libs(Path(rvsec_root), Path(self.config.lib_tmp_dir))

        # Create output directory structure
        utils.create_folder_if_not_exists(results_dir)

        self._logger.debug("Instrumentation environment prepared successfully")

    @ErrorHandler.handle_errors(
        component="AjcInstrumentation",
        phase="single_apk_instrumentation",
        reraise=True,
    )
    def instrument(
        self, app: App, result_dir: str, force_instrumentation: bool = False
    ) -> None:
        """
        Execute the complete instrumentation pipeline for a single APK.

        This method orchestrates the entire APK instrumentation process, from initial
        validation through final signing. It implements comprehensive error handling
        and resource management to ensure reliable instrumentation across different
        APK types and complexity levels.

        ### Instrumentation Pipeline Phases:
        1. **Pre-validation:** Check for existing instrumented APK and handle force flag
        2. **Decompilation:** Convert DEX bytecode to Java classes using dex2jar
        3. **Monitor Integration:** Inject generated runtime verification monitors
        4. **AspectJ Weaving:** Integrate monitoring pointcuts with application code
        5. **Recompilation:** Convert instrumented classes back to DEX format
        6. **APK Assembly:** Create and sign the final instrumented APK
        7. **Post-validation:** Verify successful instrumentation completion

        Args:
            app: Android application object containing APK metadata and file paths.
                Must contain valid APK path and application metadata.
            result_dir: Directory where the instrumented APK will be stored.
                       Created automatically if it doesn't exist.
            force_instrumentation: If True, re-instruments APK even if already processed.
                                  Useful for monitor updates or configuration changes.

        Raises:
            InstrumentationError: If any phase of the instrumentation pipeline fails
            CommandException: If external tool execution fails
            ConfigurationError: If APK validation fails
        """
        # Check for existing instrumented APK and handle force instrumentation
        instrumented_apk = os.path.join(result_dir, app.name)
        if os.path.exists(instrumented_apk):
            if force_instrumentation:
                self._logger.info(
                    "Force re-instrumentation: removing existing APK",
                    extra={
                        "app_name": app.name,
                        "existing_apk": instrumented_apk,
                        "pipeline_stage": "force_cleanup",
                    },
                )
                os.remove(instrumented_apk)
            else:
                self._logger.info(
                    f"Skipping already instrumented APK: {app.name}",
                    extra={"app_name": app.name, "pipeline_stage": "skip_existing"},
                )
                return

        start = time.time()
        self._logger.info(
            f"Starting APK instrumentation: {app.name}",
            extra={
                "app_name": app.name,
                "app_path": app.path,
                "result_dir": result_dir,
                "pipeline_stage": "instrumentation_start",
            },
        )

        # Execute instrumentation pipeline with comprehensive error handling
        try:
            self.create_temp_directories()

            # Execute the instrumentation pipeline:
            # Phase 1: DEX -> JAR (dex2jar) -- decompile bytecode to Java classes
            self.__decompile_apk(app)
            # Phase 1b: Remove pre-desugared j$.* shims so d8 can later merge the
            # result with our non-java.* instrumentation classes without hitting
            # the "Merging DEX ... prefix 'j$.'" rejection.
            self.__strip_desugared_shims(app)
            # Phase 1c: Quarantine known-problematic library classes so ajc and
            # d8 do not see them during weaving / DEX compilation. Restored in
            # Phase 4b with their original bytecode preserved.
            self.__quarantine_problematic_classes(app)
            # Phase 2: Copy AspectJ/Java monitor files into the class directory
            self.__include_generated_monitors()
            # Phase 2b: Pre-ajc ASM COMPUTE_FRAMES so BCEL receives well-formed
            # StackMapTables and does not crash with "Index -1 out of bounds"
            # on modern bytecode patterns (try-with-resources, lambdas, ...).
            self.__pre_compute_stack_frames(app)
            # Phase 3: AspectJ weaving -- integrate monitoring pointcuts at bytecode level
            self.__weave_monitors(app)
            # Phase 4: Recompute stack map frames corrupted by ajc (ASM COMPUTE_FRAMES)
            self.__compute_stack_frames(app)
            # Phase 4b: Restore the quarantined classes back into tmp_dir so the
            # final APK ships them (with their ORIGINAL bytecode, not woven).
            self.__restore_quarantined_classes(app)
            # Phases 5-7: Merge support libs, recompile to DEX (d8), zipalign, sign APK
            signed_apk = self.__create_apk(app)

            # Validate successful APK creation
            if not os.path.exists(signed_apk):
                raise InstrumentationError(
                    f"Failed to create signed APK: {signed_apk}", None
                )

            # Calculate and log instrumentation metrics
            end = time.time()
            elapsed = end - start

            self._logger.info(
                "APK instrumentation completed successfully",
                extra={
                    "app_name": app.name,
                    "elapsed_time": utils.to_readable_time(elapsed),
                    "signed_apk": signed_apk,
                    "pipeline_stage": "instrumentation_completed",
                },
            )

        except Exception as e:
            self._logger.error(
                f"Instrumentation pipeline failed for APK: {app.name}",
                extra={
                    "app_name": app.name,
                    "error": str(e),
                    "pipeline_stage": "instrumentation_failed",
                },
            )
            raise

        finally:
            # Clean up temporary directories regardless of success/failure
            temp_cleanup = [self.config.tmp_dir, self.config.rvm_tmp_dir]
            self.clear(temp_cleanup)

    def create_temp_directories(self):
        """Create temporary directories required for instrumentation processing."""
        temp_directories = [self.config.tmp_dir, self.config.rvm_tmp_dir]
        for directory in temp_directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                self._logger.debug(f"Created temporary directory: {directory}")

    def __decompile_apk(self, app: App) -> None:
        """
        Decompile Android APK into Java classes for monitor integration.

        This method converts the APK's DEX bytecode to JAR format using dex2jar,
        performs structural verification, and extracts the classes into the temporary
        directory for subsequent monitor weaving operations.

        ### Decompilation Process:
        1. **Directory Preparation:** Clean and prepare temporary working directory
        2. **DEX to JAR Conversion:** Use dex2jar to convert DEX bytecode to Java classes
        3. **Structural Verification:** Validate JAR integrity using ASM verification
        4. **Class Extraction:** Unzip JAR contents for AspectJ weaving access
        5. **Cleanup:** Remove intermediate JAR file to conserve disk space

        Args:
            app: Android application object containing APK metadata and file paths

        Raises:
            CommandException: If dex2jar conversion or verification fails
            InstrumentationError: If decompilation pipeline fails
        """
        self._logger.info(
            f"Starting APK decompilation: {app.name}",
            extra={"app_name": app.name, "pipeline_stage": "decompilation"},
        )

        # Prepare clean temporary directory for decompilation
        utils.reset_folder(self.config.tmp_dir)

        # Generate intermediate JAR file for decompilation
        no_monitor_jar_name = f"no_monitor_{app.name}.jar"
        no_monitor_jar = os.path.join(self.config.tmp_dir, no_monitor_jar_name)

        # Execute dex2jar conversion
        self.__d2j_dex2jar(app, no_monitor_jar)

        # Validate successful JAR creation
        if not os.path.exists(no_monitor_jar):
            raise InstrumentationError(
                f"dex2jar failed to create JAR file: {no_monitor_jar}", None
            )

        # ASM verification is currently skipped (skip_verify=True) because some
        # APKs produce JARs with minor structural issues that do not affect weaving.
        # Enable for debugging when weaving fails on specific APKs.
        self.__d2j_asm_verify(no_monitor_jar, skip_verify=True)

        # Extract JAR into the tmp_dir as loose .class files so AspectJ's ajc
        # compiler can process them via -inpath. The JAR is deleted to save disk.
        utils.unzip(no_monitor_jar, self.config.tmp_dir)
        utils.delete_file(no_monitor_jar)

        self._logger.debug(
            "APK decompilation completed",
            extra={
                "app_name": app.name,
                "decompiled_classes_dir": self.config.tmp_dir,
                "pipeline_stage": "decompilation_completed",
            },
        )

    def __d2j_dex2jar(self, app: App, output_jar_file: str) -> None:
        """
        Execute dex2jar conversion from APK DEX bytecode to JAR format.

        Args:
            app: Android application object
            output_jar_file: Target path for generated JAR file

        Raises:
            CommandException: If dex2jar execution fails
        """
        tag = "dex2jar"
        exception_file_name = f"exception_{app.name}.zip"
        exception_file = os.path.join(self.config.tmp_dir, exception_file_name)

        dex2jar_tools = self.config.get_dex2jar_tools()
        dex2jar_cmd = Command(
            dex2jar_tools.dex2jar,
            ["-f", "-o", output_jar_file, "-e", exception_file, app.path],
        )

        # Skip stderr verification (3rd arg = True) because dex2jar writes
        # informational messages to stderr even on success -- treating stderr
        # as an error would cause false negatives on valid APKs.
        utils.execute_command(dex2jar_cmd, tag, True)

        # dex2jar writes an exception zip when it encounters conversion errors
        # (e.g., unsupported opcodes). Its presence indicates partial failure.
        if os.path.exists(exception_file):
            raise CommandException(
                tag,
                "-1",
                f"dex2jar conversion failed. See error details in {exception_file}",
            )

    def __d2j_asm_verify(self, jar_file: str, skip_verify: bool = False) -> None:
        """
        Verify JAR file structural integrity using dex2jar ASM verification.

        Args:
            jar_file: Path to JAR file for verification
            skip_verify: If True, skip verification process
        """
        if skip_verify:
            return

        dex2jar_tools = self.config.get_dex2jar_tools()
        asm_verify_cmd = Command(dex2jar_tools.asm_verify, [jar_file])
        utils.execute_command(asm_verify_cmd, "asm_verify")

    def __get_classpath(self, app: App) -> list:
        """
        Build comprehensive classpath for AspectJ weaving including Android SDK and dependencies.

        Args:
            app: Android application object (for future SDK version targeting)

        Returns:
            List of JAR file paths for AspectJ classpath
        """
        # Start with Android SDK JAR (TODO(#23): make dynamic based on app target SDK)
        classpath = [self.__get_android_jar(app)]

        # Add all runtime verification dependencies
        for lib in os.listdir(self.config.lib_tmp_dir):
            if lib.lower().endswith(constants.EXTENSION_JAR):
                classpath.append(os.path.join(self.config.lib_tmp_dir, lib))

        return classpath

    @ErrorHandler.handle_errors(
        component="AjcInstrumentation", phase="strip_desugared_shims", reraise=True
    )
    def __strip_desugared_shims(self, app: App) -> None:
        """
        Delete pre-desugared ``j$.*`` shim classes from ``tmp_dir``.

        APKs built with older AGP that applied Java 8+ desugaring ship
        ``j$.time.*``, ``j$.util.stream.*``, ``j$.util.function.*``, etc. —
        shim copies of ``java.*`` APIs for pre-API-24 runtimes. d8 refuses
        to merge ``j$.*`` classes with non-``java.*`` classes in the same
        DEX (error: ``Merging DEX file containing classes with prefix 'j$.'
        with other classes, except classes with prefix 'java.', is not
        allowed``). Our instrumentation necessarily adds non-``java.*``
        classes (``Coverage``, ``MultiSpec_*Aspect``, ``aspectjrt``,
        ``rv-monitor-rt``), so every APK that still ships ``j$.*`` classes
        hits this error.

        Since ``--min-api 26`` (Android 8.0+) provides all Java 8+ APIs
        natively, the shims are redundant; removing them unblocks d8
        without affecting runtime behaviour.

        Args:
            app: Android application object (used for structured logging).
        """
        tmp_dir = Path(self.config.tmp_dir)
        shim_root = tmp_dir / "j$"
        if not shim_root.exists():
            self._logger.debug(
                "No j$.* shims to strip",
                extra={"app_name": app.name, "pipeline_stage": "strip_desugared_shims"},
            )
            return

        removed = 0
        for class_file in shim_root.rglob("*.class"):
            class_file.unlink()
            removed += 1

        # Remove now-empty directories under j$/, then j$/ itself.
        shutil.rmtree(shim_root, ignore_errors=True)

        self._logger.info(
            f"Stripped {removed} desugared j$.* shim classes from {app.name}",
            extra={
                "app_name": app.name,
                "pipeline_stage": "strip_desugared_shims",
                "shims_removed": removed,
            },
        )

    def _load_quarantine_patterns(self) -> List[str]:
        """
        Load glob patterns from ``assets/weaving_excludes.yaml``.

        Each pattern is a relative glob under ``tmp_dir`` (e.g.
        ``"okio/**/*.class"``). Returns an empty list when the YAML is missing
        or unreadable, so the pipeline runs normally in that case
        (backward-compatible).
        """
        assets_dir = Path(__file__).parent.parent.parent / "assets"
        yaml_path = assets_dir / "weaving_excludes.yaml"
        if not yaml_path.exists():
            return []
        try:
            with open(yaml_path) as f:
                data = yaml.safe_load(f) or {}
            patterns = data.get("patterns", []) or []
            return [p for p in patterns if p]
        except Exception as e:
            self._logger.warning(
                f"Failed to load weaving_excludes.yaml: {e}",
                extra={"pipeline_stage": "quarantine"},
            )
            return []

    def _quarantine_root(self) -> Path:
        """
        Path of the quarantine directory — a SIBLING of ``tmp_dir``.

        Must NOT live inside ``tmp_dir``, because ajc's ``-inpath`` and
        ``rv-frame-computer.jar``'s ``Files.walkFileTree`` both recurse into
        hidden subdirectories (a ``tmp_dir/.quarantine/`` would still be
        visited and rewritten, defeating the point). A sibling path is
        outside the walker's scope and therefore safe.
        """
        tmp_dir = Path(self.config.tmp_dir)
        return tmp_dir.parent / (tmp_dir.name + "_quarantine")

    @ErrorHandler.handle_errors(
        component="AjcInstrumentation", phase="quarantine", reraise=True
    )
    def __quarantine_problematic_classes(self, app: App) -> None:
        """
        Move known-problematic library classes out of ``tmp_dir`` before weaving.

        Some third-party bytecode (``okio.*``, ``androidx.media3.datasource.*``,
        ``org.apache.tika.parser.*``, ``com.google.android.vending.licensing.AESObfuscator``,
        etc.) crashes ajc's BCEL (exit 255) and d8's R8 (exit 1) with
        ``ArrayIndexOutOfBoundsException: Index -1 out of bounds for length 0``.
        These are ABORT-level failures that ``-proceedOnError`` /
        ``skip_stderr=True`` / ASM ``COMPUTE_FRAMES`` cannot recover.

        To unblock the pipeline, the matching ``.class`` files are moved to a
        sibling ``<tmp_dir>_quarantine/`` directory (preserving the relative
        subtree). They are restored in ``__restore_quarantined_classes`` so
        the final APK keeps them with their original bytecode — the library
        runs normally at runtime, the only loss is MOP visibility into its
        internal JCA calls. Since MOP specs use ``call()`` semantics,
        ``app → library.crypto_call()`` is still captured at the caller site.

        A pattern that would match the APK's own ``code_package`` MUST NOT
        quarantine those files; a WARNING is logged and the match is
        skipped so developer code is never un-instrumented.

        Args:
            app: Android application object (``app.code_package`` used for
                the safety check).
        """
        if not self.config.enable_quarantine:
            self._logger.info(
                "Quarantine disabled by config; pipeline will weave/dex all classes",
                extra={
                    "app_name": app.name,
                    "pipeline_stage": "quarantine",
                    "enable_quarantine": False,
                },
            )
            return

        patterns = self._load_quarantine_patterns()
        if not patterns:
            self._logger.debug(
                "No quarantine patterns configured, skipping",
                extra={"pipeline_stage": "quarantine"},
            )
            return

        tmp_dir = Path(self.config.tmp_dir)
        quarantine_root = self._quarantine_root()

        code_pkg = getattr(app, "code_package", None) or ""
        code_pkg_path = code_pkg.replace(".", "/") if code_pkg else ""

        quarantined = 0
        skipped_app_code = 0
        for pattern in patterns:
            for match in tmp_dir.glob(pattern):
                if not match.is_file():
                    continue
                rel = match.relative_to(tmp_dir)
                rel_str = str(rel)
                # Safety: never quarantine app code.
                if code_pkg_path and rel_str.startswith(code_pkg_path + "/"):
                    skipped_app_code += 1
                    self._logger.warning(
                        f"Quarantine pattern '{pattern}' matched app code "
                        f"({rel_str}); leaving in place",
                        extra={
                            "app_name": app.name,
                            "pipeline_stage": "quarantine",
                            "pattern": pattern,
                            "relative_path": rel_str,
                        },
                    )
                    continue
                target = quarantine_root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(match), str(target))
                quarantined += 1

        self._logger.info(
            f"Quarantined {quarantined} library classes from {app.name}"
            + (
                f" (skipped {skipped_app_code} app-code matches)"
                if skipped_app_code
                else ""
            ),
            extra={
                "app_name": app.name,
                "pipeline_stage": "quarantine",
                "quarantined_count": quarantined,
                "app_code_skipped": skipped_app_code,
            },
        )

    @ErrorHandler.handle_errors(
        component="AjcInstrumentation", phase="restore_quarantine", reraise=True
    )
    def __restore_quarantined_classes(self, app: App) -> None:
        """
        Restore quarantined library classes back into ``tmp_dir``.

        Walks ``<tmp_dir>_quarantine/**`` (sibling of ``tmp_dir``, not a
        subdirectory — see ``_quarantine_root``) and moves every file back to
        its original relative location under ``tmp_dir``. OVERWRITES any file
        present at the target path, because the weaver may have produced a
        partial woven variant that we want to discard in favor of the
        original library bytecode. Finally removes the quarantine subtree.

        Args:
            app: Android application object (used for structured logging).
        """
        if not self.config.enable_quarantine:
            # Symmetric no-op: when quarantine is disabled, the matching
            # phase did not move anything, so there is nothing to restore.
            # A stale quarantine directory (left by a previous enabled run)
            # is intentionally NOT touched here — cleanup is the caller's
            # responsibility and treating it as state from this run would
            # be confusing.
            self._logger.debug(
                "Restore skipped: enable_quarantine=False",
                extra={
                    "app_name": app.name,
                    "pipeline_stage": "restore_quarantine",
                    "enable_quarantine": False,
                },
            )
            return

        quarantine_root = self._quarantine_root()
        if not quarantine_root.exists():
            self._logger.debug(
                "No quarantine directory to restore",
                extra={"app_name": app.name, "pipeline_stage": "restore_quarantine"},
            )
            return

        tmp_dir = Path(self.config.tmp_dir)
        restored = 0
        for src in quarantine_root.rglob("*.class"):
            rel = src.relative_to(quarantine_root)
            target = tmp_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                target.unlink()  # OVERWRITE: prefer original library bytecode
            shutil.move(str(src), str(target))
            restored += 1

        shutil.rmtree(quarantine_root, ignore_errors=True)

        self._logger.info(
            f"Restored {restored} quarantined classes for {app.name}",
            extra={
                "app_name": app.name,
                "pipeline_stage": "restore_quarantine",
                "restored_count": restored,
            },
        )

    @ErrorHandler.handle_errors(
        component="AjcInstrumentation", phase="monitor_integration", reraise=True
    )
    def __include_generated_monitors(self) -> None:
        """
        Include generated runtime verification monitor artifacts in the instrumentation pipeline.

        This method copies the monitor artifacts (AspectJ files and Java classes) generated
        by rv-monitor-generator into the temporary directory for integration with the
        decompiled application classes.

        Raises:
            InstrumentationError: If monitor artifacts are not available
        """
        self._logger.info(
            "Including generated runtime verification monitor artifacts",
            extra={
                "monitor_source": self.config.monitor_output_dir,
                "integration_target": self.config.tmp_dir,
                "pipeline_stage": "monitor_integration",
            },
        )

        # Verify monitor artifacts availability before copying
        if not os.path.exists(self.config.monitor_output_dir):
            raise InstrumentationError(
                f"Monitor output directory not found: {self.config.monitor_output_dir}",
                None,
            )

        # Copy all monitor artifacts to temporary directory
        utils.copy_files(self.config.monitor_output_dir, self.config.tmp_dir)

        self._logger.debug("Monitor artifacts integration completed successfully")

    @ErrorHandler.handle_errors(
        component="AjcInstrumentation", phase="aspect_weaving", reraise=True
    )
    def __weave_monitors(self, app: App) -> None:
        """
        Execute AspectJ weaving to integrate runtime verification monitors with application code.

        This method orchestrates the AspectJ compilation process that weaves generated
        monitor aspects into the application's decompiled classes. The weaving process
        integrates monitoring pointcuts at the bytecode level, enabling runtime verification
        of monitored operations during application execution.

        ### AspectJ Weaving Process:
        1. **Classpath Construction:** Build comprehensive classpath with Android SDK and dependencies
        2. **AspectJ Compilation:** Execute ajc compiler with weaving configuration
        3. **Monitor Integration:** Weave monitoring pointcuts into application bytecode
        4. **Source Cleanup:** Remove temporary AspectJ and Java source files

        ### Weaving Configuration:
        - Uses Java 1.8 source compatibility for broad Android support
        - Suppresses lint warnings for generated AspectJ code
        - Processes both inpath classes and source roots for comprehensive coverage

        Args:
            app: Android application object containing metadata for classpath construction

        Raises:
            CommandException: If AspectJ compilation fails
        """
        self._logger.info(
            f"Starting AspectJ monitor weaving for: {app.name}",
            extra={"app_name": app.name, "pipeline_stage": "aspectj_weaving"},
        )

        # Build comprehensive classpath for AspectJ weaving
        classpath = self.__get_classpath(app)
        classpath_str = ":".join(classpath)

        self._logger.debug(
            "AspectJ weaving classpath constructed",
            extra={"classpath_entries": len(classpath), "classpath": classpath_str},
        )

        # ajc processes two inputs simultaneously:
        #   -inpath: compiled .class files from the decompiled APK (bytecode weaving)
        #   -sourceroots: .aj and .java files from rv-monitor-generator (source compilation)
        # Both point to tmp_dir because monitor sources were copied there in Phase 2.
        # Output (-d) goes back to tmp_dir, overwriting the original classes with
        # woven versions. Java 1.8 source level ensures broad Android compatibility.
        # Note: ajc JVM tuning (-Xmx8g -Xss8m) is applied via the ajc launcher
        # script itself (see docker/base/Dockerfile installation of AspectJ).
        # The simple shell launcher does NOT forward -J- flags to the JVM, so
        # the tuning must live in the script. See gh50 tasks.md §20 and
        # design.md D-AJC-XSS.
        ajc_args = [
            "-cp",
            classpath_str,
            "-Xlint:ignore",
            "-proceedOnError",
            "-inpath",
            self.config.tmp_dir,
            "-d",
            self.config.tmp_dir,
            "-source",
            "1.8",
            "-sourceroots",
            self.config.tmp_dir,
        ]

        ajc_cmd = Command("ajc", ajc_args)

        # ajc with -proceedOnError deliberately continues past per-class failures
        # (e.g., "AspectJ Internal Error: unable to add stackmap attributes to
        # class 'X'. Index -1 out of bounds for length 0") and still exits 0 with
        # a valid partial output. It prints those errors to stderr — and without
        # skip_stderr=True, execute_command turns the stderr into an APK-wide
        # failure, wiping out all successfully woven classes. Same pattern as
        # d8 (INV-INS-19) and rv-frame-computer. Real ajc crashes (OOM, invalid
        # options, missing classpath) still surface through exit code != 0.
        utils.execute_command(ajc_cmd, "ajc", skip_stderr=True)

        # Remove .java and .aj source files after weaving -- only the compiled
        # .class files are needed for DEX conversion. Leaving them would bloat
        # the JAR and could confuse downstream d8 compilation.
        utils.delete_files_by_extension(constants.EXTENSION_JAVA, self.config.tmp_dir)
        utils.delete_files_by_extension(constants.EXTENSION_AJ, self.config.tmp_dir)

        self._logger.debug(
            "AspectJ monitor weaving completed successfully",
            extra={"app_name": app.name, "pipeline_stage": "aspectj_weaving_completed"},
        )

    def _run_frame_computer(self, app: App, phase_label: str) -> None:
        """
        Invoke rv-frame-computer.jar on tmp_dir with the given phase label.

        Shared helper for both pre-ajc and post-ajc stack map recomputation.
        The jar walks all .class files under tmp_dir, reads each with
        ClassReader, writes with ClassWriter(COMPUTE_FRAMES), and overwrites
        in place. Per-class failures are logged to stderr and skipped; the
        JVM exits 0 regardless, so skip_stderr=True is used to avoid
        treating single-class warnings as APK-wide failures.

        Args:
            app: Android application object for classpath construction.
            phase_label: Used for structured logging (values: "pre_frame_computation"
                or "frame_computation") so pre- and post-ajc invocations are
                distinguishable in log aggregation.
        """
        frame_computer_jar = self._get_frame_computer_jar()
        if not frame_computer_jar:
            self._logger.warning(
                "rv-frame-computer.jar not found, skipping frame recomputation",
                extra={"pipeline_stage": phase_label},
            )
            return

        classpath = self.__get_classpath(app)
        classpath_str = ":".join(classpath)

        self._logger.info(
            f"Recomputing stack map frames ({phase_label}) for: {app.name}",
            extra={"app_name": app.name, "pipeline_stage": phase_label},
        )

        frame_cmd = Command(
            "java",
            [
                "-jar",
                frame_computer_jar,
                self.config.tmp_dir,
                "--classpath",
                classpath_str,
            ],
        )
        # FrameComputer deliberately treats per-class failures as non-fatal:
        # it catches Throwable, prints "Warning: frame computation failed for
        # X.class: ..." to stderr, and continues to the next file. The JVM
        # still exits 0 after processing the batch. Without skip_stderr=True,
        # any single-class warning causes execute_command to raise, even
        # though the rest of the APK was recomputed successfully. Real Java
        # crashes (OOM, missing jar) are still detected via exit code != 0.
        utils.execute_command(frame_cmd, "frame_computer", skip_stderr=True)

        self._logger.debug(
            f"Stack map frame recomputation ({phase_label}) completed",
            extra={
                "app_name": app.name,
                "pipeline_stage": f"{phase_label}_completed",
            },
        )

    @ErrorHandler.handle_errors(
        component="AjcInstrumentation", phase="pre_frame_computation", reraise=True
    )
    def __pre_compute_stack_frames(self, app: App) -> None:
        """
        Recompute stack map frames BEFORE ajc weaving.

        ajc 1.9.25.1 uses BCEL, which crashes with
        ``AspectJ Internal Error: unable to add stackmap attributes to class
        '<X>'. Index -1 out of bounds for length 0`` on modern bytecode whose
        StackMapTable is missing or uses patterns BCEL cannot parse (nested
        try-with-resources, lambdas with captures, switch expressions).
        ``-proceedOnError`` classifies those as ABORT and does NOT skip — the
        whole APK fails.

        Running ASM ``COMPUTE_FRAMES`` before ajc feeds the weaver
        well-formed StackMapTables, so BCEL only needs to append advice
        rather than reconstruct frames from scratch. Empirically eliminates
        the majority of "Index -1" aborts (see gh50 Section 12).

        Args:
            app: Android application object for classpath construction.
        """
        self._run_frame_computer(app, "pre_frame_computation")

    @ErrorHandler.handle_errors(
        component="AjcInstrumentation", phase="frame_computation", reraise=True
    )
    def __compute_stack_frames(self, app: App) -> None:
        """
        Recompute stack map frames AFTER ajc weaving.

        Fixes stack map frame corruption left by ajc's BCEL-based weaver,
        which is the root cause of d8 AIOOBE (ArrayIndexOutOfBoundsException)
        failures downstream. Pair with ``__pre_compute_stack_frames`` to
        catch both sources of corruption.

        Args:
            app: Android application object for classpath construction.
        """
        self._run_frame_computer(app, "frame_computation")

    def _get_frame_computer_jar(self) -> Optional[str]:
        """Locate rv-frame-computer.jar in rv-android/lib/frame-computer/."""
        # Navigate from rvandroid.py → rv_instrumentation/ → src/ → rv-instrumentation/
        # → modules/ → rv-android/ → lib/frame-computer/
        rv_android_root = Path(__file__).resolve().parent.parent.parent.parent.parent
        jar_path = rv_android_root / "lib" / "frame-computer" / "rv-frame-computer.jar"
        if jar_path.exists():
            return str(jar_path)
        return None

    @ErrorHandler.handle_errors(
        component="AjcInstrumentation", phase="apk_creation", reraise=True
    )
    def __create_apk(self, app: App) -> str:
        """
        Create final instrumented APK from woven classes and runtime verification dependencies.

        This method orchestrates the final APK creation process, including runtime verification
        library integration, bytecode compilation, and APK signing. It produces a deployment-ready
        instrumented APK with all monitoring capabilities integrated.

        ### APK Creation Pipeline:
        1. **Dependency Integration:** Merge runtime verification support libraries
        2. **JAR Assembly:** Package all instrumented classes into intermediate JAR
        3. **DEX Compilation:** Convert JAR to Android DEX bytecode using d8
        4. **APK Assembly:** Create unsigned APK with instrumented DEX
        5. **APK Signing:** Sign APK for deployment readiness

        Args:
            app: Android application object containing metadata

        Returns:
            Path to the final signed instrumented APK

        Raises:
            InstrumentationError: If APK creation pipeline fails
        """
        self._logger.info(
            f"Creating instrumented APK for: {app.name}",
            extra={"app_name": app.name, "pipeline_stage": "apk_creation"},
        )

        # Integrate runtime verification support libraries
        self.__merge_support_classes()

        # Prepare temporary directory for JAR assembly
        utils.reset_folder(self.config.rvm_tmp_dir)
        monitored_jar_name = f"monitored_{app.name}.jar"
        monitored_jar = os.path.join(self.config.rvm_tmp_dir, monitored_jar_name)

        # Assemble all instrumented classes into JAR
        utils.zip_dir_content(monitored_jar, self.config.tmp_dir)
        shutil.move(monitored_jar, self.config.tmp_dir)
        shutil.rmtree(self.config.rvm_tmp_dir)
        monitored_jar = os.path.join(self.config.tmp_dir, monitored_jar_name)

        self._logger.debug(f"Instrumented classes assembled into JAR: {monitored_jar}")

        # Compile JAR to DEX format and create unsigned APK
        unsigned_apk = self.__d8(app, monitored_jar)

        if not os.path.exists(unsigned_apk):
            raise InstrumentationError(
                f"Failed to create unsigned APK: {unsigned_apk}", None
            )

        # Align native libraries to 16 KiB pages BEFORE signing. Modern APKs
        # (API 23+) default to android:extractNativeLibs="false" and store
        # .so files uncompressed; PackageManager aborts installation with
        # INSTALL_FAILED_INVALID_APK (res=-2) when those entries are not
        # page-aligned. apksigner's v2/v3 scheme preserves the zipalign-
        # produced alignment, so aligning before signing keeps it intact
        # in the final APK (Google's official guidance).
        self.__zipalign(unsigned_apk)

        # Sign APK with APK Signature Scheme v1+v2+v3 via apksigner.
        signed_apk = self.__sign_apk(app, unsigned_apk)

        self._logger.debug(f"Instrumented APK creation completed: {signed_apk}")
        return signed_apk

    @ErrorHandler.handle_errors(
        component="AjcInstrumentation", phase="library_integration", reraise=True
    )
    def __merge_support_classes(self) -> None:
        """
        Integrate runtime verification support libraries into the instrumented application.

        This method extracts and merges all required runtime verification libraries
        (rv-monitor-rt, aspectjrt, rvsec-core, etc.) with the instrumented application
        classes. The integration ensures that all runtime verification components are
        available during application execution.

        ### Library Integration Process:
        1. **Library Extraction:** Unzip all runtime verification JARs
        2. **Manifest Cleanup:** Remove conflicting META-INF manifests
        3. **Class Merging:** Integrate support classes with application classes
        4. **Cleanup:** Remove temporary extraction directories

        Raises:
            InstrumentationError: If support library integration fails
        """
        self._logger.info(
            "Integrating runtime verification support libraries",
            extra={"pipeline_stage": "support_library_integration"},
        )

        # Prepare temporary directory for library extraction
        utils.reset_folder(self.config.rvm_tmp_dir)

        # Define required runtime verification libraries
        required_jars = [
            "rv-monitor-rt.jar",  # RV-Monitor runtime library
            "rvsec-core.jar",  # RVSec core functionality
            "rvsec-logger-logcat.jar",  # Android logcat integration
            "aspectjrt.jar",  # AspectJ runtime library
        ]

        # Extract each required library
        for jar_name in required_jars:
            jar_path = os.path.join(self.config.lib_tmp_dir, jar_name)

            if not os.path.exists(jar_path):
                raise InstrumentationError(
                    f"Required runtime verification library not found: {jar_path}", None
                )

            self._logger.debug(f"Extracting support library: {jar_name}")
            utils.unzip(jar_path, self.config.rvm_tmp_dir)

        # Each JAR has its own META-INF with manifests and signatures. Merging
        # multiple META-INFs would produce conflicts (duplicate MANIFEST.MF entries),
        # and they are not needed for the final DEX output. Delete before merging.
        metainf_dir = os.path.join(self.config.rvm_tmp_dir, "META-INF")
        utils.delete_dir(metainf_dir)

        # Merge extracted support classes into the instrumented app's class tree.
        # dirs_exist_ok=True handles overlapping package directories gracefully.
        shutil.copytree(
            self.config.rvm_tmp_dir, self.config.tmp_dir, dirs_exist_ok=True
        )

        self._logger.debug(
            "Support libraries integrated successfully",
            extra={
                "integration_target": self.config.tmp_dir,
                "libraries_count": len(required_jars),
            },
        )

        # Clean up temporary extraction directory
        shutil.rmtree(self.config.rvm_tmp_dir)

    def __d8(self, app: App, monitored_jar: str) -> str:
        """
        Compile instrumented JAR to DEX format and create unsigned APK.

        This method converts the instrumented JAR containing woven monitoring code
        to Android DEX bytecode format, then integrates it into a copy of the original
        APK to create an unsigned instrumented APK ready for signing.

        ### DEX Compilation Process:
        1. **JAR to DEX Conversion:** Use Android d8 compiler for optimized DEX generation
        2. **APK Preparation:** Create working copy of original APK
        3. **DEX Integration:** Replace original classes.dex with instrumented version
        4. **Verification:** Perform basic structural validation

        Args:
            app: Android application object containing metadata
            monitored_jar: Path to JAR file containing instrumented and woven classes

        Returns:
            Path to unsigned APK with instrumented DEX bytecode

        Raises:
            CommandException: If d8 compilation or ZIP operations fail
        """
        self._logger.info(
            f"Compiling instrumented classes to DEX format: {app.name}",
            extra={
                "app_name": app.name,
                "monitored_jar": monitored_jar,
                "pipeline_stage": "dex_compilation",
            },
        )

        # d8 converts the instrumented JAR to DEX bytecode. --release enables
        # optimizations and --min-api 26 covers Android 8.0+. Desugaring is
        # left enabled so d8 can emit synthetic accessors for JDK 11+ nest-mate
        # field access used by rv-monitor-rt's inner classes.
        d8_cmd = Command(
            "d8",
            [
                monitored_jar,
                "--release",
                "--lib",
                self.__get_android_jar(app),
                "--min-api",
                "26",
            ],
        )

        # skip_stderr=True because d8 emits non-fatal "Expected stack map table"
        # warnings to stderr even on success (exit code 0). These warnings indicate
        # input classes with missing/imperfect frames but d8 still produces valid DEX.
        utils.execute_command(d8_cmd, "d8", True)

        # Create working copy of original APK
        unsigned_apk_name = f"unsigned_{app.name}"
        unsigned_apk = os.path.join(self.config.tmp_dir, unsigned_apk_name)

        self._logger.debug(
            "Creating unsigned APK copy",
            extra={"original_apk": app.path, "unsigned_apk": unsigned_apk},
        )

        # Copy the original APK and replace its classes.dex with the instrumented one.
        # This preserves resources, assets, AndroidManifest.xml, and native libraries
        # from the original APK -- only the Dalvik bytecode changes.
        shutil.copy2(app.path, unsigned_apk)

        if not os.path.exists(unsigned_apk):
            raise InstrumentationError(
                f"Failed to create unsigned APK copy: {unsigned_apk}", None
            )

        # zip -u updates the APK in-place, replacing classes.dex (and any
        # additional classesN.dex files) with the d8-compiled instrumented versions.
        # d8 outputs DEX files in the current working directory.
        self._logger.info(
            "Integrating instrumented DEX into APK",
            extra={
                "unsigned_apk": unsigned_apk_name,
                "pipeline_stage": "dex_integration",
            },
        )

        d8_zip_cmd = Command("zip", ["-u", unsigned_apk, f"*{constants.EXTENSION_DEX}"])
        utils.execute_command(d8_zip_cmd, "d8_zip")

        # Perform basic structural verification
        self.__d2j_asm_verify(unsigned_apk, skip_verify=True)

        self._logger.debug(f"DEX compilation and integration completed: {unsigned_apk}")
        return unsigned_apk

    @ErrorHandler.handle_errors(
        component="AjcInstrumentation", phase="zipalign", reraise=True
    )
    def __zipalign(self, apk_path: str) -> None:
        """
        Page-align uncompressed entries in the APK before apksigner signing.

        APKs that declare ``android:extractNativeLibs="false"`` (the default
        since API 23) store ``.so`` libraries uncompressed inside the APK.
        The Android PackageManager mmap()s those entries directly at install
        time and therefore requires them to start at a page-aligned offset.
        ``__d8`` rewrites the APK via the ``zip`` utility to inject the
        instrumented DEX, destroying any pre-existing alignment. Installing
        an unaligned APK fails with ``INSTALL_FAILED_INVALID_APK``
        (``res=-2`` — "Failed to extract native libraries").

        Running ``zipalign -P 16 4`` on the unsigned APK restores the
        alignment:
            * ``-P 16`` targets 16 KiB pages for uncompressed ``.so`` files
              (mandatory on API 35+, safe on older APIs because 16 KiB
              alignment also satisfies 4 KiB). ``-p`` (the legacy
              4 KiB-only flag) is mutually exclusive with ``-P`` and is
              therefore NOT passed.
            * the positional ``4`` aligns all other entries on 4-byte
              boundaries (standard ZIP alignment)
            * ``-f`` overwrites the destination file in place

        Must run BEFORE ``__sign_apk``. apksigner's APK Signing Block (v2/v3)
        lives between the ZIP central directory and the file entries; it
        does not modify entry offsets, so the alignment established here is
        preserved in the final signed APK. Google's official guidance
        explicitly requires this ordering when v2/v3 signing is used.

        Args:
            apk_path: Absolute path to the UNSIGNED APK. The file is
                rewritten in place with an aligned copy.
        """
        aligned_apk = apk_path + ".aligned"
        self._logger.info(
            f"Aligning native libraries (zipalign -P 16 4, pre-sign): {apk_path}"
        )
        zipalign_cmd = Command(
            "zipalign",
            ["-f", "-P", "16", "4", apk_path, aligned_apk],
            timeout=60,
        )
        utils.execute_command(zipalign_cmd, "zipalign")
        os.replace(aligned_apk, apk_path)

    @ErrorHandler.handle_errors(
        component="AjcInstrumentation", phase="apk_signing", reraise=True
    )
    def __sign_apk(self, app: App, unsigned_apk: str) -> str:
        """
        Sign the instrumented APK with APK Signature Schemes v1+v2+v3.

        Copies the unsigned APK to the instrumentation output directory, runs
        ``apksigner sign`` in place, then ``apksigner verify`` to confirm the
        result. The input unsigned APK is removed after a successful sign.

        apksigner (Android SDK ``build-tools/<ver>/apksigner``, version 0.9+)
        writes v1, v2, and v3 signatures in a single invocation and preserves
        zipalign-produced alignment, so ``__zipalign`` MUST run BEFORE this
        method. API 30+ emulators reject v1-only signatures with
        ``INSTALL_PARSE_FAILED_NO_CERTIFICATES``; including v2+v3 fixes it.

        Args:
            app: Android application object — ``app.name`` is the APK
                filename written under ``instrumented_dir``.
            unsigned_apk: Path to the aligned, unsigned APK.

        Returns:
            Path to the signed APK in ``instrumented_dir``.

        Raises:
            CommandException: If ``apksigner sign`` or ``apksigner verify``
                fail with non-zero exit code.
            InstrumentationError: If the signed APK does not exist after
                ``apksigner sign`` (sanity check for silent failures).
        """
        utils.create_folder_if_not_exists(self.config.instrumented_dir)
        signed_apk = os.path.join(self.config.instrumented_dir, app.name)

        self._logger.info(
            f"Starting APK signing process: {app.name}",
            extra={
                "app_name": app.name,
                "unsigned_apk": unsigned_apk,
                "signed_apk": signed_apk,
                "pipeline_stage": "apk_signing",
            },
        )

        shutil.copy2(unsigned_apk, signed_apk)

        sign_cmd = Command(
            "apksigner",
            [
                "sign",
                "--ks",
                self.config.keystore_file,
                "--ks-pass",
                f"pass:{self.config.keystore_password}",
                "--ks-key-alias",
                self.config.keystore_alias,
                signed_apk,
            ],
        )
        # apksigner runs under modern JVMs (JDK 21+) which emit native-access
        # restriction warnings ("WARNING: A restricted method in java.lang.System
        # has been called by org.conscrypt.NativeLibraryUtil ...") to stderr on
        # every invocation. Exit code is 0 on a successful sign; only the
        # code must gate failure. Same pattern as d8, rv-frame-computer, ajc,
        # and mvn — see INV-INS-19.
        utils.execute_command(sign_cmd, "apksigner", skip_stderr=True)

        if not os.path.exists(signed_apk):
            raise InstrumentationError(
                f"apksigner produced no output at {signed_apk}", None
            )

        verify_cmd = Command("apksigner", ["verify", signed_apk])
        utils.execute_command(verify_cmd, "apksigner_verify", skip_stderr=True)

        os.remove(unsigned_apk)

        self._logger.info(
            f"APK signing completed successfully: {signed_apk}",
            extra={
                "app_name": app.name,
                "signed_apk": signed_apk,
                "pipeline_stage": "apk_signing_completed",
            },
        )

        return signed_apk

    def clear(self, folders: list) -> None:
        """
        Clean up temporary directories and files from instrumentation process.

        Args:
            folders: List of directory paths to remove
        """
        for folder in folders:
            if os.path.exists(folder):
                self._logger.debug(f"Cleaning temporary directory: {folder}")
                shutil.rmtree(folder, ignore_errors=True)

        # d8 outputs classes.dex (and classesN.dex for multidex) in the working
        # directory. These stray files must be removed so the next APK does not
        # accidentally pick up DEX files from a previous run.
        utils.delete_files_by_extension(
            constants.EXTENSION_DEX, self.config.working_dir
        )

    def __get_android_jar(self, app: App) -> str:
        """
        Select android.jar matching the APK's targetSdkVersion.

        Tries the exact platform first, then falls back to the highest available.
        Minimum fallback is android-26 (matching --min-api 26).

        Args:
            app: Android application object with sdk_target from androguard

        Returns:
            Path to best-matching Android SDK JAR file
        """
        target = getattr(app, "sdk_target", None)
        platforms_dir = self.config.android_platforms_dir

        if target and platforms_dir:
            # Try exact match first
            exact_jar = os.path.join(platforms_dir, f"android-{target}", "android.jar")
            if os.path.exists(exact_jar):
                self._logger.debug(
                    f"Using android.jar for target SDK {target}",
                    extra={"android_jar": exact_jar},
                )
                return exact_jar

            # Fallback: highest available platform
            highest = self._find_highest_android_platform(platforms_dir)
            if highest:
                self._logger.info(
                    f"Platform android-{target} not available, using {highest}",
                    extra={"requested": target, "fallback": highest},
                )
                return os.path.join(platforms_dir, highest, "android.jar")

        return self.config.android_jar_path

    def _find_highest_android_platform(self, platforms_dir: str) -> Optional[str]:
        """Find the highest numbered android-XX platform directory."""
        if not os.path.isdir(platforms_dir):
            return None
        platforms = []
        for name in os.listdir(platforms_dir):
            if name.startswith("android-"):
                try:
                    level = int(name.split("-")[1])
                    if level >= 26:
                        platforms.append((level, name))
                except (ValueError, IndexError):
                    continue
        if not platforms:
            return None
        platforms.sort(reverse=True)
        return platforms[0][1]

    @ErrorHandler.handle_errors(
        component="AjcInstrumentation", phase="instrumentation_verification"
    )
    def check_if_instrumented(self, app: App) -> None:
        """
        Verify that APK was actually instrumented by comparing file hashes.

        This validation ensures that the instrumentation process actually modified
        the APK rather than simply copying the original file. Hash comparison provides
        a reliable method to detect instrumentation success.

        Args:
            app: Android application object containing original APK path

        Raises:
            CommandException: If APK was not actually instrumented
        """
        # Hash comparison catches a subtle failure mode: if all pipeline steps
        # succeed but weaving produces no bytecode changes (e.g., no matching
        # pointcuts), the output APK is byte-identical to the original. This
        # means no monitors were actually injected, so the experiment would
        # produce zero coverage data. Treating this as an error ensures we
        # catch misconfigured monitor specifications early.
        original_hash = utils.file_hash(app.path)
        instrumented_path = os.path.join(self.config.instrumented_dir, app.name)
        instrumented_hash = utils.file_hash(instrumented_path)

        if original_hash == instrumented_hash:
            self._logger.error(
                "Instrumentation verification failed: APK unchanged",
                extra={
                    "app_name": app.name,
                    "original_hash": original_hash,
                    "instrumented_hash": instrumented_hash,
                },
            )

            raise CommandException(
                "instrumentation_verification",
                "-1",
                f"APK {app.name} was not actually instrumented - hashes match original",
            )

        self._logger.debug(
            "Instrumentation verification successful: APK modified",
            extra={
                "app_name": app.name,
                "original_hash": original_hash,
                "instrumented_hash": instrumented_hash,
            },
        )
