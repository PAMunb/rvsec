# modules/rv-experiment/src/rv_experiment/experiment/workflow/pre_processor.py
"""
Pre-processor component for RV-Android experiments.
Handles monitor generation, APK instrumentation, and static analysis.
"""

import os
from typing import List

from rv_android_core.constants import EXTENSION_APK, EXTENSION_STATIC_ANALYSIS
from rv_android_core.domain.app import App
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import RVAndroidError
from rv_android_core.util.logging.constants import (
    CONTEXT_COMPONENT,
    LOG_COMPLETE,
    LOG_START,
)
from rv_android_core.util.logging.manager import LoggingManager
from rv_experiment.config import ExperimentConfig
from rv_experiment.constants import (
    INSTRUMENTED_APKS_DIR,
    MONITORS_DIR,
    MONITORS_PROVENANCE_FILE,
)
from rv_instrumentation import get_instrumenter


class PreProcessingConfigurationError(RVAndroidError):
    """A flag combination that would silently disable a requested step.

    Raised before any work starts, so the operator fixes the invocation instead
    of reading a finished run's empty denominators (INV-EXP-37).
    """


class PreProcessor:
    """
    A specialized component for handling the pre-processing phase of experiments.

    This component IS Phase 1 (pre-processing) of the Three-Phase Workflow (FR15).
    Phase 1 supports three independent operations — monitor generation, APK
    instrumentation, and static analysis — each individually enabled or skipped.

    ### Architectural Decisions:
    - Separates pre-processing concerns from the main experiment controller
    - Provides a clear interface for configurable pre-processing operations
    - Encapsulates the logic for monitor generation, APK instrumentation, and static analysis
    - Enables independent testing and reuse of pre-processing functionality

    ### Role in the System:
    - Performs essential setup operations before experiment execution
    - Prepares applications for runtime monitoring and analysis
    - Generates and manages static analysis data for coverage tracking
    - Configures the experiment environment for successful execution
    """

    def __init__(self, config: ExperimentConfig):
        """
        Initialize the pre-processor.

        Args:
            config: Experiment configuration
        """
        self.config = config
        self.results_dir = config.output_dir
        self.error_handler = ErrorHandler.get_instance()

        # Configure logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            "rv_experiment.experiment.workflow.pre_processor",
            {CONTEXT_COMPONENT: "PreProcessor"},
        )

    def process(self, generate_monitors: bool, instrument: bool, static_analysis: bool):
        """
        Execute the pre-processing phase.

        Args:
            generate_monitors: Whether to generate monitors
            instrument: Whether to instrument APKs
            static_analysis: Whether to perform static analysis
        """
        # =====================================================================
        # Pre-processing pipeline — three sequential steps:
        #
        # Step 1: Generate MOP monitors from .mop specs (JavaMOP + RV-Monitor)
        #   Input:  .mop specification files from RVSEC_HOME
        #   Output: AspectJ aspects + monitor classes in out/monitors/
        #
        # Step 2: Instrument APKs with generated monitors (dex2jar + AspectJ + d8)
        #   Input:  Original APKs from apks_dir + monitors from Step 1
        #   Output: Instrumented APKs in out/instrumented_apks/
        #
        # Step 3: Run GATOR static analysis on the ORIGINAL APKs of those that
        #   were successfully instrumented
        #   Input:  Original APKs from apks_dir, filtered by the presence of an
        #           instrumented counterpart (INV-EXP-15) — so this step DOES
        #           depend on Step 2, whatever the reading order suggests
        #   Output: Static analysis JSON alongside the instrumented APKs
        #
        # FR15: Phase 1 operations MUST execute in this order — monitor
        # generation, then instrumentation, then static analysis. Step 2 depends
        # on Step 1's generated monitors, and Step 3 depends on Step 2: it reads
        # unmodified DEX (AspectJ-woven bytecode breaks GATOR's TypeResolver) but
        # only for the APKs that will actually enter the experiment, which is
        # what instrumented_apks/ records. Skipping Step 2 while asking for
        # Step 3 therefore leaves Step 3 with nothing to analyse — which is why
        # that combination now aborts instead of running to a silent zero
        # (INV-EXP-37).
        #
        # On resume, INV-EXP-13 forces all three skip flags at the CLI layer
        # so the pre-processing artifacts from the original run are reused
        # intact rather than regenerated. The three warning branches below
        # enforce INV-EXP-07: a skipped step MUST NOT execute and MUST log a
        # warning (see Scenario "Experiment With All Pre-Processing Skipped").
        # =====================================================================
        with self.logger.with_context(phase="pre_processing"):
            self.logger.info(LOG_START.format(phase="APK pre-processing"))

            # Step 1: Generate MOP monitors from .mop specs (JavaMOP + RV-Monitor)
            if generate_monitors:
                self._generate_monitors()
            else:
                self.logger.warning("Skipping monitor generation")
                self._check_monitors_provenance()

            # Step 2: Instrument APKs with generated monitors (dex2jar + AspectJ + d8)
            if instrument:
                self._instrument_apks()
            else:
                self.logger.warning("Skipping APK instrumentation")

            # Step 3: Run GATOR static analysis on original APKs
            if static_analysis:
                self._assert_instrumentation_available_for_static(instrument)
                self._run_static_analysis()
            else:
                self.logger.warning("Skipping static analysis")

            self._report_missing_static_analysis(static_analysis)

            self.logger.info(LOG_COMPLETE.format(phase="APK pre-processing"))
            self.logger.info("Pre-processing phase completed")

    def _write_monitors_provenance(self, monitor_output_dir: str) -> None:
        """Record which specification set produced these monitors (INV-EXP-38)."""
        marker = os.path.join(monitor_output_dir, MONITORS_PROVENANCE_FILE)
        with open(marker, "w", encoding="utf-8") as handle:
            handle.write(f"{self.config.specification_set}\n")
        self.logger.debug(f"Monitors provenance recorded: {marker}")

    def _check_monitors_provenance(self) -> None:
        """Refuse reused monitors that were generated from another set.

        Under `--skip-monitors` the run instruments with whatever is in
        `out/monitors/`. Inferring the set from the monitor file names does not
        work — the sets share most names, and the ones they do not share are
        exactly the ones a mismatch would hide — so the generator writes a
        marker and this reads it.

        **An absent marker warns; it does not abort.** Both resume paths force
        `generate_monitors=False`, and no existing `out/monitors/` carries a
        marker, so aborting on absence would make every experiment produced
        before this change unresumable.
        """
        marker = os.path.join(
            self.config.output_dir, MONITORS_DIR, MONITORS_PROVENANCE_FILE
        )
        if not os.path.isfile(marker):
            self.logger.warning(
                f"Reusing monitors with no provenance marker ({marker}): cannot "
                f"verify they were generated from '{self.config.specification_set}'. "
                "Monitors generated before this marker existed carry none — "
                "regenerate them if the set is in doubt."
            )
            return

        recorded = open(marker, encoding="utf-8").read().strip()
        if recorded != self.config.specification_set:
            raise PreProcessingConfigurationError(
                f"the monitors in {os.path.dirname(marker)} were generated from "
                f"specification set '{recorded}', and this run asks for "
                f"'{self.config.specification_set}'. Instrumenting with the wrong "
                "set produces an experiment that monitors the wrong properties and "
                "says nothing about it. Run ./clear.sh, or drop --skip-monitors."
            )
        self.logger.info(
            f"Reusing monitors generated from specification set '{recorded}'"
        )

    def _assert_instrumentation_available_for_static(self, instrument: bool) -> None:
        """Refuse the flag combination that silently disables static analysis.

        `--skip-instrument` with `--static-analysis` used to produce a run in
        which Step 3 filtered every APK away — `_get_target_apks_for_analysis`
        returns `[]` when `instrumented_apks/` does not exist — logged one
        warning, and continued to an experiment whose coverage denominators were
        all empty. The user asked for static analysis and got none, and nothing
        in the results said so (INV-EXP-37).

        A previous run's `instrumented_apks/` is a legitimate input, so the test
        is the directory, not the flag alone.
        """
        if instrument:
            return

        instrumented_dir = os.path.join(self.config.output_dir, INSTRUMENTED_APKS_DIR)
        has_apks = os.path.isdir(instrumented_dir) and any(
            f.endswith(EXTENSION_APK) for f in os.listdir(instrumented_dir)
        )
        if has_apks:
            self.logger.info(
                "Static analysis requested with instrumentation skipped: reusing "
                f"the instrumented APKs already in {instrumented_dir}"
            )
            return

        raise PreProcessingConfigurationError(
            "--skip-instrument was given together with --static-analysis, and "
            f"{instrumented_dir} holds no instrumented APK. Static analysis runs "
            "only for APKs that have an instrumented counterpart (INV-EXP-15), so "
            "this combination would analyse nothing and publish empty coverage "
            "denominators for the whole run. Drop --skip-instrument, or point "
            "--apks-dir at a previous run's instrumented_apks/."
        )

    def _report_missing_static_analysis(self, static_analysis: bool) -> None:
        """One consolidated statement of what will run without a denominator.

        The run continues either way (INV-EXP-39): stopping a 200-APK campaign
        because GATOR failed on three is a cost the failure does not justify.
        What was missing was the statement — the per-APK warnings scrolled past
        during a long pre-processing phase and nothing summarised them.

        Under `--skip-static` the report names the flag (INV-EXP-39 as amended by
        task 6.6): "no artefact" and "no artefact because you asked for none" are
        different facts, and only the second is a decision the reader made.
        """
        instrumented_dir = os.path.join(self.config.output_dir, INSTRUMENTED_APKS_DIR)
        if not os.path.isdir(instrumented_dir):
            return

        apks = sorted(
            f for f in os.listdir(instrumented_dir) if f.endswith(EXTENSION_APK)
        )
        missing = [
            f
            for f in apks
            if not os.path.exists(
                os.path.join(instrumented_dir, f + EXTENSION_STATIC_ANALYSIS)
            )
        ]
        if not apks:
            return

        if not static_analysis:
            self.logger.warning(
                f"Static analysis skipped by flag (--skip-static): "
                f"{len(missing)} of {len(apks)} APKs will run without a coverage "
                f"denominator. Their coverage cells are left empty and their rows "
                f"are marked measured=false (INV-PLT-35); their violation columns "
                f"are written as usual."
            )
        elif missing:
            self.logger.warning(
                f"Static analysis produced no artefact for {len(missing)} of "
                f"{len(apks)} APKs. They will still run — violations do not depend "
                f"on static analysis — with empty coverage cells and measured=false "
                f"(INV-PLT-35). Affected: {', '.join(missing)}"
            )
        else:
            self.logger.info(
                f"Static analysis artefact present for all {len(apks)} APKs"
            )

    def _generate_monitors(self):
        """Generate runtime verification monitors using JavaMOP and RV-Monitor."""
        # Monitor generation pipeline:
        # 1. Read .mop specification files from the specification_set directory
        #    (jca/, jca_android/ or generic/ under
        #    RVSEC_HOME/rvsec/rvsec-mop/.../resources/)
        # 2. JavaMOP compiles .mop files into .aj (AspectJ) aspect files
        # 3. RV-Monitor generates runtime monitor classes from .mop files
        # 4. Output (aspects + monitors) goes to out/monitors/
        #
        # ExperimentConfig.specification_set ("jca", "jca_android" or "generic")
        # determines which .mop files are used: "jca" is the frozen Java SE set that
        # produced the published measurements, "jca_android" its successor for
        # Android API 30. The sets are mutually exclusive — an experiment uses
        # exactly one of them, never several.
        with self.logger.with_context(phase="generate_monitors"):
            self.logger.info(LOG_START.format(phase="monitor generation"))

            try:
                monitor_output_dir = os.path.join(self.config.output_dir, MONITORS_DIR)
                os.makedirs(monitor_output_dir, exist_ok=True)

                # FR17 + INV-EXP-05: get_monitored_operations_config() builds an
                # RVGeneratorConfig just-in-time, resolving RVSEC_HOME via the
                # three-level priority hierarchy (rvsec_root field → RVSEC_HOME
                # env var → ConfigurationError) and the spec directory path.
                rv_config = self.config.get_monitored_operations_config()

                # Import and use monitor generator
                from rv_monitor_generator.runtime_verification_generator import (
                    RuntimeVerificationGenerator,
                )

                generator = RuntimeVerificationGenerator(rv_config)

                success = generator.generate_monitors(monitor_output_dir)
                if not success:
                    self.logger.warning("Monitor generation failed")
                else:
                    self._write_monitors_provenance(monitor_output_dir)
                    self.logger.info(LOG_COMPLETE.format(phase="monitor generation"))
                    self.logger.info("Monitors generated")

            except ImportError:
                # Scenario "Module Import Failure for Optional Sub-Modules":
                # the optional monitor-generator module may be absent, so catch
                # ImportError, log the warning, and let process() continue with
                # the remaining steps rather than aborting Phase 1.
                self.logger.warning(
                    "Monitor generator module not available - skipping monitor generation"
                )
            except Exception as e:
                error_context = {
                    "component": "PreProcessor",
                    "operation": "monitor_generation",
                    "config": (
                        str(rv_config) if "rv_config" in locals() else "unavailable"
                    ),
                }
                self.error_handler.handle_error(e, error_context)

    def _instrument_apks(self):
        """Instrument APKs with runtime verification monitors.

        Phase 1 instrumentation step (FR15). If instrumentation fails or the
        module is unavailable, originals are copied as a fallback so the
        experiment does not abort (INV-EXP-08; Scenario "Pre-Processing Failure
        Does Not Abort Experiment").
        """
        # Instrumentation pipeline (per APK):
        # 1. dex2jar: Convert DEX bytecode to JAR (Java bytecode)
        # 2. AspectJ: Weave monitor aspects into the JAR (requires Step 1 monitors)
        # 3. d8: Convert woven JAR back to DEX bytecode
        # 4. Repackage as APK and re-sign with debug keystore
        #
        # This step depends on _generate_monitors() having run first —
        # the monitors/ directory must contain the generated aspects.
        # If instrumentation fails for an APK, the original is copied
        # as fallback so execution can proceed (with no MOP monitoring).
        with self.logger.with_context(phase="instrument_apks"):
            self.logger.info(LOG_START.format(phase="APK instrumentation"))

            try:
                instrumented_dir = os.path.join(
                    self.config.output_dir, INSTRUMENTED_APKS_DIR
                )
                os.makedirs(instrumented_dir, exist_ok=True)

                # Dispatch on the variant flag through the canonical factory
                # (INV-INS-36). Both variants implement Instrumenter so
                # downstream logic doesn't branch further. FR17: the
                # get_*_instrumentation_config() call builds the sub-module
                # config just-in-time when this phase actually runs.
                variant = getattr(self.config, "instrumentation_variant", "ajc")
                instrumentation_config = (
                    self.config.get_dexlib_instrumentation_config()
                    if variant == "dexlib2"
                    else self.config.get_rv_instrumentation_config()
                )
                instrumenter = get_instrumenter(variant, instrumentation_config)

                apk_list = self.config.get_apk_list()

                if not apk_list:
                    self.logger.warning("No APKs configured for instrumentation")
                    return

                # Execute instrumentation
                instrumented_dir = os.path.join(
                    self.config.output_dir, INSTRUMENTED_APKS_DIR
                )
                success = instrumenter.instrument_apks(
                    apks_dir=self.config.apks_dir,
                    results_dir=instrumented_dir,
                    apk_paths=apk_list,
                )

                if not success:
                    self.logger.error("APK instrumentation failed")
                else:
                    # Note: Instrumentation errors JSON will be generated by ResultManager
                    # during post-processing with access to experiment results directory
                    self.logger.info(LOG_COMPLETE.format(phase="APK instrumentation"))
                    self.logger.info("Instrumentation completed")

            except ImportError:
                # INV-EXP-08: module unavailable → copy originals so the
                # experiment does not abort (Scenario "Pre-Processing Failure
                # Does Not Abort Experiment").
                self.logger.warning(
                    "Instrumentation module not available - copying original APKs"
                )
                self._copy_original_apks()
                # Note: Instrumentation errors will be tracked and reported by ResultManager
            except Exception as e:
                # INV-EXP-08: any instrumentation failure → copy originals so
                # the experiment continues rather than aborting (Scenario
                # "Pre-Processing Failure Does Not Abort Experiment").
                error_context = {
                    "component": "PreProcessor",
                    "operation": "apk_instrumentation",
                    "apks_dir": self.config.apks_dir,
                    "output_dir": self.config.output_dir,
                }
                self.error_handler.handle_error(e, error_context)
                self._copy_original_apks()
                # Note: Instrumentation errors will be tracked and reported by ResultManager

    def _copy_original_apks(self):
        """Copy original APKs to output directory as fallback.

        Enforces INV-EXP-08: called when instrumentation fails or the module is
        unavailable, this copies originals to instrumented_apks/ so the
        experiment does not abort (Scenario "Pre-Processing Failure Does Not
        Abort Experiment"). Ensures Phase 2 (execution) always has APKs to work
        with, even though they won't have MOP monitors woven in — coverage will
        be 0% for monitored operations, but the tools can still exercise the app.
        """
        instrumented_dir = os.path.join(self.config.output_dir, INSTRUMENTED_APKS_DIR)
        os.makedirs(instrumented_dir, exist_ok=True)

        import shutil

        for apk_path in self.config.get_apk_list():
            apk_name = os.path.basename(apk_path)
            dest_path = os.path.join(instrumented_dir, apk_name)
            if not os.path.exists(dest_path):
                shutil.copy2(apk_path, dest_path)
                self.logger.debug(f"Copied {apk_name} to instrumented directory")

    def _run_static_analysis(self):
        """
        Run static analysis on all instrumented APKs.

        Phase 1 static-analysis step (FR15). Uses the StaticAnalyzer class to
        perform static analysis on APKs, following the standardized analyzer
        pattern. Per FR15, analysis runs on ORIGINAL APKs because GATOR/Soot
        needs unmodified DEX bytecode — AspectJ-woven bytecode crashes Soot's
        TypeResolver.
        """
        with self.logger.with_context(phase="static_analysis"):
            self.logger.info(LOG_START.format(phase="static analysis"))

            try:
                from rv_static_analysis.analysis.static.static_analysis import (
                    StaticAnalyzer,
                )

                # FR17: get_static_analysis_config() builds the rv-static-analysis
                # sub-module config just-in-time when this phase actually runs.
                static_config = self.config.get_static_analysis_config()

                # Static analysis uses ORIGINAL APKs (not instrumented) because
                # GATOR/Soot needs unmodified DEX bytecode. Instrumented APKs have
                # woven AspectJ aspects that cause TypeResolver errors in GATOR's
                # call graph analysis. The output JSON is placed alongside the
                # instrumented APKs so rv-platform finds both in the same directory.
                target_apks = self._get_target_apks_for_analysis()
                if not target_apks:
                    self.logger.warning("No APKs available for static analysis")
                    return

                self.logger.info(f"Running static analysis on {len(target_apks)} APKs")

                for apk_path in target_apks:
                    apk_name = os.path.basename(apk_path)

                    with self.logger.with_context(app_name=apk_name):
                        try:
                            self.logger.info(
                                LOG_START.format(
                                    phase=f"static analysis for {apk_name}"
                                )
                            )

                            # Output goes to instrumented_apks/ (not a separate static_analysis/ dir)
                            # so rv-platform finds the JSON alongside the APK it belongs to.
                            # Platform looks for <apk_name>.json next to the APK file.
                            apk_output_dir = os.path.join(
                                self.config.output_dir, INSTRUMENTED_APKS_DIR
                            )
                            os.makedirs(apk_output_dir, exist_ok=True)

                            # Create App instance and analyzer under the run's
                            # package policy (INV-EXP-34): the key this analysis
                            # filters on is the run's decision, not a lookup.
                            app = self._build_app(apk_path)

                            analyzer = StaticAnalyzer(
                                app=app, config=static_config, output_dir=apk_output_dir
                            )

                            # Execute analysis
                            result = analyzer.analyze()

                            if not result.success:
                                self.logger.warning(
                                    f"Static analysis failed for {apk_name}: {result.errors}"
                                )
                            else:
                                self.logger.info(
                                    LOG_COMPLETE.format(
                                        phase=f"static analysis for {apk_name}"
                                    )
                                )

                        except Exception as e:
                            error_context = {
                                "component": "PreProcessor",
                                "operation": "static_analysis",
                                "app_name": apk_name,
                                "apk_path": apk_path,
                            }
                            self.error_handler.handle_error(e, error_context)

                self.logger.info(LOG_COMPLETE.format(phase="static analysis"))
                self.logger.info("Static analysis completed")

            except ImportError:
                self.logger.warning(
                    "Static analysis module not available - skipping static analysis"
                )
            except Exception as e:
                error_context = {
                    "component": "PreProcessor",
                    "operation": "static_analysis_setup",
                    "output_dir": self.config.output_dir,
                }
                self.error_handler.handle_error(e, error_context)

    def _get_target_apks_for_analysis(self) -> List[str]:
        """Get original APKs for static analysis, filtered by instrumentation success.

        Enforces INV-EXP-15: only returns original APK paths for APKs that have
        a corresponding instrumented file in instrumented_apks/; APKs that
        failed instrumentation are logged as skipped and excluded (Scenario
        "Mixed instrumentation results filter downstream phases"). GATOR/Soot
        cannot process instrumented APKs (AspectJ-woven bytecode causes
        TypeResolver errors), so static analysis runs on originals — but only
        for APKs that will enter the experiment, which requires successful
        instrumentation.
        """
        instrumented_dir = os.path.join(self.config.output_dir, INSTRUMENTED_APKS_DIR)

        if not os.path.exists(instrumented_dir):
            self.logger.warning(
                f"Instrumented directory does not exist: {instrumented_dir}"
            )
            return []

        instrumented_names = {
            f for f in os.listdir(instrumented_dir) if f.endswith(EXTENSION_APK)
        }

        result = []
        for apk_path in self.config.get_apk_list():
            apk_name = os.path.basename(apk_path)
            if apk_name in instrumented_names:
                result.append(apk_path)
            else:
                self.logger.info(
                    f"Skipping static analysis for {apk_name}: not instrumented"
                )

        return result

    def get_instrumented_apks(self) -> List[App]:
        """
        Every instrumented APK, whether or not it has static analysis data.

        INV-EXP-16 is made true by executing, not by excluding (researcher
        decision, 29/08). An APK in `instrumented_apks/` with no `.apk.json`
        runs; the log says it will run without a coverage denominator instead of
        claiming an exclusion, and its coverage cells are left empty while its
        violation columns are written as usual (INV-PLT-35).

        Three prior decisions force it. Violations do not depend on static
        analysis at all — running an instrumented APK with no static analysis is
        a scenario the report layer already implements — so excluding the APK
        here would destroy that scenario one layer earlier. Excluding APKs so a
        number closes is a named anti-pattern that has already cost this corpus
        55 applications. And once the denominator is a published column
        (INV-PLT-33), dropping a denominator-less row becomes a reader-side
        decision, explicit and revisable, instead of a pipeline-side one that is
        irreversible and invisible.

        The list must stay non-empty when APKs exist: the caller treats an empty
        one as a fatal "No APKs available for execution", which is why the
        fallback to originals below survives — for the case where there are no
        instrumented APKs at all, not for the case where none has an artefact.

        Returns:
            List of App objects for every instrumented APK found
        """
        with self.logger.with_context(phase="find_instrumented_apks"):
            apks = []
            without_static = []
            instrumented_dir = os.path.join(
                self.config.output_dir, INSTRUMENTED_APKS_DIR
            )

            if os.path.exists(instrumented_dir):
                for file in sorted(os.listdir(instrumented_dir)):
                    if file.endswith(EXTENSION_APK):
                        app_path = os.path.join(instrumented_dir, file)
                        sa_json = app_path + EXTENSION_STATIC_ANALYSIS
                        try:
                            app = self._build_app(app_path)
                        except Exception as e:
                            error_context = {
                                "component": "PreProcessor",
                                "operation": "processing_apk",
                                "file_name": file,
                                "instrumented_dir": instrumented_dir,
                            }
                            self.error_handler.handle_error(e, error_context)
                            continue
                        apks.append(app)
                        if os.path.exists(sa_json):
                            self.logger.debug(f"Found instrumented APK with SA: {file}")
                        else:
                            without_static.append(file)

            # The logged set and the executed set are the same set (INV-EXP-16 as
            # modified). The message names what is actually missing rather than
            # announcing an exclusion that does not happen.
            if without_static:
                self.logger.warning(
                    f"{len(without_static)} of {len(apks)} instrumented APKs have no "
                    f"static analysis artefact and will run WITHOUT a coverage "
                    f"denominator: {', '.join(without_static)}"
                )

            # No instrumented APK at all — a different situation from "none has an
            # artefact", and the only one the fallback answers.
            if not apks:
                self.logger.warning("No instrumented APKs found, using original APKs")
                for apk_path in self.config.get_apk_list():
                    apks.append(self._build_app(apk_path))

            self.logger.info(f"Executing {len(apks)} APKs")
            return apks

    def _build_app(self, app_path: str) -> App:
        """One place where this workflow constructs an App under the run policy.

        Both package policies are the run's decision and arrive already resolved
        (INV-EXP-34, INV-EXP-35); nothing below this layer looks either of them
        up. The instrumenter is deliberately not built through here — it
        receives the DECLARED applicationId (INV-EXP-36).
        """
        return App(
            app_path=app_path,
            package_detector=self.config.package_detector,
            strip_build_type_suffix=self.config.strip_build_type_suffix,
        )
