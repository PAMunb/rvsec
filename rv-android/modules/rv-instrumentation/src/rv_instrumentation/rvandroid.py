import json
import os
import shutil
import time
from typing import List, Optional

from rv_android_core import constants
from rv_android_core.commands.command import Command
from rv_android_core.commands.command_exception import CommandException
from rv_android_core.domain.app import App
from rv_android_core.util import utils
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import InstrumentationError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_instrumentation.config import InstrumentationError as InstrumentationErrorModel
from rv_instrumentation.config import InstrumentationResults, RVInstrumentationConfig


class RVInstrumentation:
    """
    A specialized system for instrumenting and preparing Android APKs for runtime verification
    with monitored operations integration.

    The RVInstrumentation serves as the core instrumentation engine that transforms standard
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

    def __init__(self, config: Optional[RVInstrumentationConfig] = None):
        """
        Initialize RVInstrumentation with configuration and logging integration.

        Args:
            config: Configuration object. If None, will be created with default settings
                   from environment variables or explicit paths.
        """
        self.config = config or RVInstrumentationConfig()

        # Initialize structured logging through LoggingManager
        logging_manager = LoggingManager.get_instance()
        self._logger = logging_manager.get_logger(
            "rv_instrumentation.RVInstrumentation",
            {
                CONTEXT_COMPONENT: "RVInstrumentation",
                "component_module": "rv-instrumentation",
            },
        )

        # Initialize centralized error handling
        self._error_handler = ErrorHandler.get_instance()

        self._logger.info(
            "RVInstrumentation initialized",
            extra={
                "config_summary": self.config.get_configuration_summary().model_dump()
            },
        )

    @ErrorHandler.handle_errors(
        component="RVInstrumentation", phase="batch_instrumentation"
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
                "component": "RVInstrumentation",
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
                "component": "RVInstrumentation",
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
                    phase="command_execution",
                )
                results.errors[app.name] = error_model

                # Use centralized error handling
                context = {
                    "component": "RVInstrumentation",
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
                    code=-1, message=str(ex), phase="general_error", tool=None
                )
                results.errors[app.name] = error_model

                # Use centralized error handling
                context = {
                    "component": "RVInstrumentation",
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

    @ErrorHandler.handle_errors(component="RVInstrumentation", phase="preparation")
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

        # Execute Maven for dependency resolution
        self.__execute_maven()

        # Create output directory structure
        utils.create_folder_if_not_exists(results_dir)

        self._logger.debug("Instrumentation environment prepared successfully")

    @ErrorHandler.handle_errors(
        component="RVInstrumentation", phase="single_apk_instrumentation"
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

            # Execute instrumentation pipeline phases
            self.__decompile_apk(app)
            self.__include_generated_monitors()
            self.__weave_monitors(app)
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
        # Ensure temporary directories exist for processing
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

        # Perform structural verification (optional but recommended)
        self.__d2j_asm_verify(no_monitor_jar, skip_verify=True)

        # Extract JAR contents for AspectJ weaving
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

        # Execute dex2jar (skip stderr verification as dex2jar outputs to stderr normally)
        utils.execute_command(dex2jar_cmd, tag, True)

        # Check for exception file indicating conversion errors
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

    def __d2j_apk_sign(self, signed_apk: str, unsigned_apk: str) -> None:
        """
        Sign APK using dex2jar APK signing tool.

        Args:
            signed_apk: Target path for signed APK
            unsigned_apk: Source path for unsigned APK
        """
        dex2jar_tools = self.config.get_dex2jar_tools()
        apk_sign_cmd = Command(
            dex2jar_tools.apk_sign, ["-f", "-o", signed_apk, unsigned_apk]
        )
        utils.execute_command(apk_sign_cmd, "apk_sign")

    @ErrorHandler.handle_errors(component="RVInstrumentation", phase="maven_execution")
    def __execute_maven(self) -> None:
        """
        Execute Maven build to resolve and copy runtime verification dependencies.

        This method runs Maven to download and prepare all required runtime verification
        libraries (rv-monitor-rt, aspectjrt, etc.) into the temporary library directory
        for subsequent integration during the instrumentation process.

        Raises:
            CommandException: If Maven execution fails
        """
        self._logger.info(
            "Executing Maven dependency resolution",
            extra={
                "lib_tmp_dir": self.config.lib_tmp_dir,
                "pipeline_stage": "maven_dependencies",
            },
        )

        maven_cmd = Command("mvn", ["clean", "compile"])
        utils.execute_command(maven_cmd, "maven")

        self._logger.debug("Maven dependency resolution completed successfully")

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
        component="RVInstrumentation", phase="monitor_integration"
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

    @ErrorHandler.handle_errors(component="RVInstrumentation", phase="aspect_weaving")
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

        # Execute AspectJ compiler with monitor weaving configuration
        ajc_cmd = Command(
            "ajc",
            [
                "-cp",
                classpath_str,
                "-Xlint:ignore",  # Suppress AspectJ lint warnings for generated code
                "-inpath",
                self.config.tmp_dir,  # Process compiled classes
                "-d",
                self.config.tmp_dir,  # Output directory for woven classes
                "-source",
                "1.8",  # Java source compatibility
                "-sourceroots",
                self.config.tmp_dir,  # Source directory for AspectJ files
            ],
        )

        utils.execute_command(ajc_cmd, "ajc")

        # Clean up temporary source files after successful weaving
        utils.delete_files_by_extension(constants.EXTENSION_JAVA, self.config.tmp_dir)
        utils.delete_files_by_extension(constants.EXTENSION_AJ, self.config.tmp_dir)

        self._logger.debug(
            "AspectJ monitor weaving completed successfully",
            extra={"app_name": app.name, "pipeline_stage": "aspectj_weaving_completed"},
        )

    @ErrorHandler.handle_errors(component="RVInstrumentation", phase="apk_creation")
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

        # TODO(#23): Implement zipalign optimization for better performance

        # Sign APK for deployment readiness
        signed_apk = self.__sign_apk(app, unsigned_apk)

        self._logger.debug(f"Instrumented APK creation completed: {signed_apk}")
        return signed_apk

    @ErrorHandler.handle_errors(
        component="RVInstrumentation", phase="library_integration"
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

        # Remove conflicting manifest files
        metainf_dir = os.path.join(self.config.rvm_tmp_dir, "META-INF")
        utils.delete_dir(metainf_dir)

        # Merge support classes with instrumented application classes
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

        # Execute d8 compiler to convert JAR to DEX
        # TODO(#23): Make min-api dynamic based on app.min_api when available
        d8_cmd = Command(
            "d8",
            [
                monitored_jar,
                "--release",
                "--lib",
                self.__get_android_jar(app),
                "--min-api",
                "26",  # Conservative minimum API level
            ],
        )

        utils.execute_command(d8_cmd, "d8")

        # Create working copy of original APK
        unsigned_apk_name = f"unsigned_{app.name}"
        unsigned_apk = os.path.join(self.config.tmp_dir, unsigned_apk_name)

        self._logger.debug(
            "Creating unsigned APK copy",
            extra={"original_apk": app.path, "unsigned_apk": unsigned_apk},
        )

        shutil.copy2(app.path, unsigned_apk)

        if not os.path.exists(unsigned_apk):
            raise InstrumentationError(
                f"Failed to create unsigned APK copy: {unsigned_apk}", None
            )

        # Replace original classes.dex with instrumented version
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

    @ErrorHandler.handle_errors(component="RVInstrumentation", phase="apk_signing")
    def __sign_apk(self, app: App, unsigned_apk: str) -> str:
        """
        Sign instrumented APK for deployment readiness.

        This method executes the complete APK signing process using both dex2jar
        signing tools and Java jarsigner for comprehensive signature validation.
        The signing process ensures the instrumented APK can be deployed on Android
        devices for runtime verification testing.

        ### APK Signing Process:
        1. **Output Directory Preparation:** Ensure target directory exists
        2. **Initial Signing:** Use dex2jar APK signing for basic signature
        3. **Manifest Cleanup:** Remove conflicting META-INF entries
        4. **Keystore Signing:** Apply final signature using configured keystore
        5. **Signature Verification:** Validate successful signing completion

        Args:
            app: Android application object containing metadata
            unsigned_apk: Path to unsigned APK requiring signature

        Returns:
            Path to final signed instrumented APK ready for deployment

        Raises:
            CommandException: If any signing step fails
            InstrumentationError: If signed APK validation fails
        """
        # Ensure output directory exists
        utils.create_folder_if_not_exists(self.config.instrumented_dir)

        self._logger.info(
            f"Starting APK signing process: {app.name}",
            extra={
                "app_name": app.name,
                "unsigned_apk": unsigned_apk,
                "pipeline_stage": "apk_signing",
            },
        )

        # Define target path for signed APK
        signed_apk = os.path.join(self.config.instrumented_dir, app.name)

        # Execute initial dex2jar APK signing
        self.__d2j_apk_sign(signed_apk, unsigned_apk)

        # Remove unsigned APK after successful initial signing
        os.remove(unsigned_apk)

        # Validate initial signing success
        if not os.path.exists(signed_apk):
            raise InstrumentationError(
                f"dex2jar APK signing failed: {signed_apk}", None
            )

        # Clean up conflicting META-INF entries
        zip_cmd = Command("zip", ["-q", "-d", signed_apk, "META-INF*"])
        utils.execute_command(zip_cmd, "zip_sign_apk")

        # Apply final keystore signature
        self.__jarsigner(signed_apk)

        # Verify signature integrity
        self.__jarsigner_verify(signed_apk)

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

        # Clean up any stray DEX files in working directory
        utils.delete_files_by_extension(
            constants.EXTENSION_DEX, self.config.working_dir
        )

    def __get_android_jar(self, app: App) -> str:
        """
        Get Android SDK JAR path for compilation and classpath construction.

        TODO(#23): Implement dynamic Android JAR selection based on app target SDK

        Args:
            app: Android application object (for future SDK targeting)

        Returns:
            Path to Android SDK JAR file
        """
        # Currently uses configured Android JAR path
        # Future enhancement: dynamic selection based on app.sdk_target
        return self.config.android_jar_path

        # Future implementation for dynamic SDK targeting:
        # platform = f"android-{app.sdk_target}"
        # android_jar = os.path.join(self.config.android_platforms_dir, platform, 'android.jar')
        #
        # if os.path.exists(android_jar):
        #     return android_jar
        # else:
        #     return self.config.android_jar_path

    def __jarsigner(self, signed_apk: str) -> None:
        """
        Apply keystore signature to APK using Java jarsigner.

        Args:
            signed_apk: Path to APK file requiring signature
        """
        jarsigner_cmd = Command(
            "jarsigner",
            [
                "-sigalg",
                "SHA256withRSA",
                "-digestalg",
                "SHA-256",
                "-keystore",
                self.config.keystore_file,
                signed_apk,
                "server",
                "-storepass",
                self.config.keystore_password,
            ],
        )
        utils.execute_command(jarsigner_cmd, "jarsigner")

    def __jarsigner_verify(self, signed_apk: str) -> None:
        """
        Verify APK signature integrity using Java jarsigner.

        Args:
            signed_apk: Path to signed APK for verification
        """
        jarsigner_cmd = Command("jarsigner", ["-verify", "-certs", signed_apk])
        utils.execute_command(jarsigner_cmd, "jarsigner_verify")

    @ErrorHandler.handle_errors(
        component="RVInstrumentation", phase="instrumentation_verification"
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
