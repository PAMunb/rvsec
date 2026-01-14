"""
Instrumentation wrapper for rv-agent validation.

This module provides a wrapper around rv-monitor-generator, rv-instrumentation,
and rv-static-analysis to prepare APKs for validation experiments.

Workflow:
1. Generate monitors once from generic MOP specifications
2. Instrument all APKs with the generated monitors
3. Run static analysis on original APKs (GESDA, GATOR, REACH)
4. Organize all data in apks_instrumented/<apk_name>/
5. Copy pre-existing .methods files

Output structure:
    apks_instrumented/
    ├── app1.apk/
    │   ├── app1.apk              # Instrumented APK
    │   ├── app1.apk.gesda        # GESDA: app structure
    │   ├── app1.apk.wtg          # GATOR: Window Transition Graph
    │   ├── app1.apk.reach        # REACH: reachability analysis
    │   └── app1.apk.methods      # Ground truth methods (from all_methods/)
    └── app2.apk/
        └── ...

NOTE: All 3 static analysis files (.gesda, .wtg, .reach) are required
for StaticAnalysisParser to work correctly.
"""

import os
import shutil
import logging
import signal
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from rv_android_core.domain.app import App


logger = logging.getLogger(__name__)

# Timeout for static analysis (30 minutes per APK)
STATIC_ANALYSIS_TIMEOUT_SECONDS = 30 * 60  # 1800 seconds


@dataclass
class InstrumentationResult:
    """Result of the instrumentation process."""

    total_apks: int = 0
    instrumented_apks: List[str] = field(default_factory=list)
    failed_apks: Dict[str, str] = field(default_factory=dict)
    static_analysis_success: List[str] = field(default_factory=list)
    static_analysis_failed: Dict[str, str] = field(default_factory=dict)
    static_analysis_timeout: List[str] = field(default_factory=list)  # APKs that timed out
    complete_apks: List[str] = field(default_factory=list)  # APKs with all 4 required files
    monitors_generated: bool = False

    @property
    def success_rate(self) -> float:
        """Calculate instrumentation success rate."""
        if self.total_apks == 0:
            return 0.0
        return (len(self.instrumented_apks) / self.total_apks) * 100

    @property
    def complete_rate(self) -> float:
        """Calculate rate of APKs with all 4 required files."""
        if self.total_apks == 0:
            return 0.0
        return (len(self.complete_apks) / self.total_apks) * 100


class InstrumentationWrapper:
    """
    Wrapper for APK instrumentation and static analysis.

    This class coordinates the preprocessing of APKs for validation experiments:
    - Generates runtime verification monitors from MOP specifications
    - Instruments APKs with the generated monitors
    - Runs static analysis (GESDA, GATOR, REACH) on original APKs
    - Organizes all output files in apks_instrumented/<apk_name>/

    Output structure:
        apks_instrumented/<apk_name>/
        ├── <apk_name>.apk         # Instrumented APK
        ├── <apk_name>.gesda       # GESDA: app structure
        ├── <apk_name>.wtg         # GATOR: Window Transition Graph
        ├── <apk_name>.reach       # REACH: reachability analysis
        └── <apk_name>.methods     # Ground truth (from all_methods/)

    NOTE: All 3 static analysis files are required for StaticAnalysisParser.
    The .methods files from static analysis are discarded in favor of the
    pre-existing .methods files in all_methods/ directory.
    """

    def __init__(
        self,
        validation_data_dir: str,
        specs_dir: Optional[str] = None,
        temp_dir: Optional[str] = None,
    ):
        """
        Initialize the instrumentation wrapper.

        Args:
            validation_data_dir: Path to validation data directory
            specs_dir: Path to MOP specifications directory (default: data/specs/)
            temp_dir: Temporary directory for intermediate files (default: data/temp/)
        """
        # IMPORTANT: All paths must be absolute to survive os.chdir() calls
        self.validation_data_dir = Path(validation_data_dir).resolve()

        # Input directories (absolute)
        self.apks_dir = (self.validation_data_dir / "apks").resolve()
        self.specs_dir = Path(specs_dir).resolve() if specs_dir else (self.validation_data_dir / "specs").resolve()
        self.all_methods_dir = (self.validation_data_dir / "all_methods").resolve()

        # Output directory (absolute)
        self.output_dir = (self.validation_data_dir / "apks_instrumented").resolve()

        # Temporary directories (absolute)
        self.temp_dir = Path(temp_dir).resolve() if temp_dir else (self.validation_data_dir / "temp").resolve()
        self.monitors_dir = (self.temp_dir / "monitors").resolve()
        self.temp_instrumented_dir = (self.temp_dir / "instrumented").resolve()

        # Validate input directories
        self._validate_inputs()

        logger.info(f"InstrumentationWrapper initialized")
        logger.info(f"  APKs dir (input): {self.apks_dir}")
        logger.info(f"  Specs dir: {self.specs_dir}")
        logger.info(f"  Methods dir: {self.all_methods_dir}")
        logger.info(f"  Output dir: {self.output_dir}")

    def _validate_inputs(self) -> None:
        """Validate that required input directories exist."""
        if not self.apks_dir.exists():
            raise ValueError(f"APKs directory not found: {self.apks_dir}")

        if not self.specs_dir.exists():
            raise ValueError(f"Specifications directory not found: {self.specs_dir}")

        # all_methods is optional but recommended
        if not self.all_methods_dir.exists():
            logger.warning(f"Methods directory not found: {self.all_methods_dir}")

    def _ensure_output_dirs(self) -> None:
        """Create output directories if they don't exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.monitors_dir.mkdir(parents=True, exist_ok=True)
        self.temp_instrumented_dir.mkdir(parents=True, exist_ok=True)

    def run(self, force: bool = False, skip_static_analysis: bool = False) -> InstrumentationResult:
        """
        Execute the complete instrumentation workflow.

        Args:
            force: Force re-instrumentation even if output already exists
            skip_static_analysis: Skip static analysis phase (for testing)

        Returns:
            InstrumentationResult with details of the process
        """
        result = InstrumentationResult()

        # Create output directories
        self._ensure_output_dirs()

        # Step 1: Generate monitors
        logger.info("=" * 60)
        logger.info("Step 1: Generating runtime verification monitors")
        logger.info("=" * 60)
        result.monitors_generated = self._generate_monitors()

        if not result.monitors_generated:
            logger.error("Monitor generation failed - aborting")
            return result

        # Step 2: Instrument APKs
        logger.info("=" * 60)
        logger.info("Step 2: Instrumenting APKs")
        logger.info("=" * 60)
        self._instrument_apks(result, force)

        # Step 3: Run static analysis on ORIGINAL APKs
        if not skip_static_analysis:
            logger.info("=" * 60)
            logger.info("Step 3: Running static analysis on original APKs")
            logger.info("=" * 60)
            self._run_static_analysis(result, force)

        # Step 4: Copy .methods files
        logger.info("=" * 60)
        logger.info("Step 4: Copying pre-existing .methods files")
        logger.info("=" * 60)
        self._copy_methods_files(result)

        # Step 5: Validate complete APKs (must have all 4 files)
        logger.info("=" * 60)
        logger.info("Step 5: Validating complete APKs (all 4 required files)")
        logger.info("=" * 60)
        self._validate_complete_apks(result)

        # Summary
        self._print_summary(result)

        return result

    def _generate_monitors(self) -> bool:
        """
        Generate runtime verification monitors from MOP specifications.

        Returns:
            True if successful, False otherwise
        """
        try:
            from rv_monitor_generator.config import RVGeneratorConfig
            from rv_monitor_generator.runtime_verification_generator import RuntimeVerificationGenerator

            logger.info(f"Using specifications from: {self.specs_dir}")
            logger.info(f"Monitor output directory: {self.monitors_dir}")

            # Configure generator for generic specifications
            config = RVGeneratorConfig(
                mop_specs_dir=str(self.specs_dir),
            )

            generator = RuntimeVerificationGenerator(config)
            success = generator.generate_monitors(str(self.monitors_dir))

            if success:
                logger.info("Monitor generation completed successfully")
                summary = generator.get_generation_summary(str(self.monitors_dir))
                logger.info(f"Generated {summary['aspectj_files']} AspectJ files")
                logger.info(f"Generated {summary['monitor_classes']} monitor classes")
            else:
                logger.error("Monitor generation failed")

            return success

        except ImportError as e:
            logger.error(f"rv-monitor-generator module not available: {e}")
            return False
        except Exception as e:
            logger.error(f"Monitor generation failed: {e}")
            return False

    def _instrument_apks(self, result: InstrumentationResult, force: bool = False) -> None:
        """
        Instrument all APKs with the generated monitors.

        Instrumented APKs are placed in output_dir/<apk_name>/<apk_name>.apk

        IMPORTANT: This method changes to rv-android directory to run Maven
        for dependency resolution, then returns to original directory.

        Args:
            result: InstrumentationResult to update
            force: Force re-instrumentation
        """
        try:
            from rv_instrumentation import RVInstrumentation
            from rv_instrumentation.config import RVInstrumentationConfig

            # Get list of APKs
            apk_files = list(self.apks_dir.glob("*.apk"))
            result.total_apks = len(apk_files)

            logger.info(f"Found {result.total_apks} APKs to instrument")

            if result.total_apks == 0:
                logger.warning("No APKs found in input directory")
                return

            # Find rv-android directory (where pom.xml is located)
            # Maven needs to run from this directory for dependency resolution
            rv_android_dir = self._find_rv_android_dir()
            if not rv_android_dir:
                logger.error("Could not find rv-android directory with pom.xml")
                return

            # Save current directory and change to rv-android
            original_dir = os.getcwd()
            logger.info(f"Changing to rv-android directory: {rv_android_dir}")
            os.chdir(rv_android_dir)

            try:
                # Configure instrumentation to use temp directory
                config = RVInstrumentationConfig(
                    monitor_output_dir=str(self.monitors_dir),
                    instrumented_dir=str(self.temp_instrumented_dir),
                )

                instrumenter = RVInstrumentation(config)

                # Run batch instrumentation to temp directory
                instr_results = instrumenter.instrument_apks(
                    apks_dir=str(self.apks_dir),
                    results_dir=str(self.temp_instrumented_dir),
                    force_instrumentation=force,
                )
            finally:
                # Always return to original directory
                os.chdir(original_dir)
                logger.debug(f"Returned to original directory: {original_dir}")

            # Move instrumented APKs to final structure: output_dir/<apk_name>/<apk_name>.apk
            for apk_file in apk_files:
                apk_name = apk_file.name
                temp_instrumented_path = self.temp_instrumented_dir / apk_name
                final_apk_dir = self.output_dir / apk_name
                final_apk_path = final_apk_dir / apk_name

                if temp_instrumented_path.exists():
                    # Create directory and move APK
                    final_apk_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(temp_instrumented_path), str(final_apk_path))
                    result.instrumented_apks.append(apk_name)
                    logger.info(f"  [OK] {apk_name}")
                else:
                    error_msg = "Unknown error"
                    if apk_name in instr_results.errors:
                        error_msg = instr_results.errors[apk_name].message
                    result.failed_apks[apk_name] = error_msg
                    logger.warning(f"  [FAIL] {apk_name}: {error_msg}")

            logger.info(f"Instrumentation complete: {len(result.instrumented_apks)}/{result.total_apks} successful")

        except ImportError as e:
            logger.error(f"rv-instrumentation module not available: {e}")
        except Exception as e:
            logger.error(f"Instrumentation failed: {e}")

    def _run_static_analysis(self, result: InstrumentationResult, force: bool = False) -> None:
        """
        Run static analysis on ORIGINAL APKs (not instrumented).

        Static analysis should be performed on original APKs to extract
        the unmodified application structure. Only processes APKs that
        were successfully instrumented.

        Generates 3 files per APK (all required for StaticAnalysisParser):
        - <apk_name>.gesda - GESDA: app structure
        - <apk_name>.wtg   - GATOR: Window Transition Graph
        - <apk_name>.reach - REACH: reachability analysis

        TIMEOUT: Each APK has 30 minutes to complete static analysis.
        APKs that exceed this timeout are terminated and marked as failed.

        Args:
            result: InstrumentationResult to update
            force: Force re-analysis even if output files already exist
        """
        try:
            from rv_static_analysis.analysis.static.static_analysis import StaticAnalyzer
            from rv_static_analysis.config import RVStaticAnalysisConfig

            if not result.instrumented_apks:
                logger.warning("No instrumented APKs to analyze")
                return

            logger.info(f"Running static analysis on {len(result.instrumented_apks)} ORIGINAL APKs")
            logger.info(f"Timeout per APK: {STATIC_ANALYSIS_TIMEOUT_SECONDS // 60} minutes")

            for i, apk_name in enumerate(result.instrumented_apks, 1):
                logger.info(f"[{i}/{len(result.instrumented_apks)}] Analyzing {apk_name}")

                # Use ORIGINAL APK for static analysis (not instrumented)
                apk_path = self.apks_dir / apk_name
                # Output goes to the same directory as the instrumented APK
                apk_output_dir = self.output_dir / apk_name

                # Check if analysis already exists
                gesda_file = apk_output_dir / f"{apk_name}.gesda"
                wtg_file = apk_output_dir / f"{apk_name}.wtg"
                reach_file = apk_output_dir / f"{apk_name}.reach"

                if not force and gesda_file.exists() and wtg_file.exists() and reach_file.exists():
                    logger.info(f"  [SKIP] {apk_name} - analysis files already exist")
                    result.static_analysis_success.append(apk_name)
                    continue

                if not apk_path.exists():
                    logger.warning(f"  [FAIL] {apk_name}: Original APK not found at {apk_path}")
                    result.static_analysis_failed[apk_name] = f"Original APK not found"
                    continue

                # Run analysis with timeout
                success, error_msg = self._run_single_static_analysis(
                    apk_name=apk_name,
                    apk_path=apk_path,
                    apk_output_dir=apk_output_dir,
                    timeout_seconds=STATIC_ANALYSIS_TIMEOUT_SECONDS,
                )

                if success:
                    result.static_analysis_success.append(apk_name)
                    logger.info(f"  [OK] {apk_name}")

                    # Remove .methods file if generated (we'll use pre-existing ones)
                    methods_file = apk_output_dir / f"{apk_name}.methods"
                    if methods_file.exists():
                        methods_file.unlink()
                        logger.debug(f"  Removed generated .methods file")
                elif error_msg == "TIMEOUT":
                    result.static_analysis_timeout.append(apk_name)
                    result.static_analysis_failed[apk_name] = f"Timeout after {STATIC_ANALYSIS_TIMEOUT_SECONDS // 60} minutes"
                    logger.warning(f"  [TIMEOUT] {apk_name}: Exceeded {STATIC_ANALYSIS_TIMEOUT_SECONDS // 60} minute limit")
                else:
                    result.static_analysis_failed[apk_name] = error_msg
                    logger.warning(f"  [FAIL] {apk_name}: {error_msg}")

            logger.info(f"Static analysis complete: {len(result.static_analysis_success)}/{len(result.instrumented_apks)} successful")
            if result.static_analysis_timeout:
                logger.info(f"  Timeouts: {len(result.static_analysis_timeout)}")

        except ImportError as e:
            logger.error(f"rv-static-analysis module not available: {e}")
        except Exception as e:
            logger.error(f"Static analysis failed: {e}")

    def _run_single_static_analysis(
        self,
        apk_name: str,
        apk_path: Path,
        apk_output_dir: Path,
        timeout_seconds: int,
    ) -> tuple[bool, str]:
        """
        Run static analysis on a single APK with timeout.

        Args:
            apk_name: Name of the APK
            apk_path: Path to the original APK
            apk_output_dir: Directory for output files
            timeout_seconds: Maximum time allowed for analysis

        Returns:
            Tuple of (success, error_message). error_message is "TIMEOUT" for timeouts.
        """
        from rv_static_analysis.analysis.static.static_analysis import StaticAnalyzer
        from rv_static_analysis.config import RVStaticAnalysisConfig

        def run_analysis():
            """Inner function to run in thread with timeout."""
            app = App(app_path=str(apk_path))
            config = RVStaticAnalysisConfig(
                output_dir=str(apk_output_dir),
                mop_dir=str(self.specs_dir),
            )
            analyzer = StaticAnalyzer(
                app=app,
                config=config,
                output_dir=str(apk_output_dir),
            )
            return analyzer.analyze()

        start_time = time.time()

        try:
            # Use ThreadPoolExecutor for timeout support
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_analysis)
                try:
                    analysis_result = future.result(timeout=timeout_seconds)
                    elapsed = time.time() - start_time
                    logger.debug(f"  Analysis completed in {elapsed:.1f}s")

                    if analysis_result.success:
                        return True, ""
                    else:
                        return False, ", ".join(analysis_result.errors)

                except FuturesTimeoutError:
                    # Analysis exceeded timeout - cancel and cleanup
                    future.cancel()
                    elapsed = time.time() - start_time
                    logger.warning(f"  Analysis timed out after {elapsed:.1f}s - killing Java processes")

                    # Kill any lingering Java processes for this APK
                    self._kill_java_processes(apk_name)

                    return False, "TIMEOUT"

        except Exception as e:
            return False, str(e)

    def _kill_java_processes(self, apk_name: str) -> None:
        """
        Kill any Java processes related to the given APK.

        This is used to cleanup after a timeout in static analysis.
        GATOR/GESDA/REACH run as Java subprocesses that may linger.

        Args:
            apk_name: Name of the APK (used to identify processes)
        """
        import subprocess

        try:
            # Find and kill Java processes for gator/soot that mention this APK
            # This is a best-effort cleanup - some processes may have already terminated
            result = subprocess.run(
                ["pgrep", "-f", f"java.*{apk_name}"],
                capture_output=True,
                text=True,
            )

            if result.stdout.strip():
                pids = result.stdout.strip().split("\n")
                for pid in pids:
                    try:
                        os.kill(int(pid), signal.SIGKILL)
                        logger.debug(f"  Killed Java process {pid}")
                    except (ProcessLookupError, ValueError):
                        pass  # Process already terminated

            # Also kill any gator processes (in case APK name not in command line)
            result = subprocess.run(
                ["pgrep", "-f", "presto.android.Main"],
                capture_output=True,
                text=True,
            )

            if result.stdout.strip():
                pids = result.stdout.strip().split("\n")
                for pid in pids:
                    try:
                        os.kill(int(pid), signal.SIGKILL)
                        logger.debug(f"  Killed GATOR process {pid}")
                    except (ProcessLookupError, ValueError):
                        pass

        except Exception as e:
            logger.debug(f"  Error killing Java processes: {e}")

    def _copy_methods_files(self, result: InstrumentationResult) -> None:
        """
        Copy pre-existing .methods files to APK output directories.

        Uses .methods files from all_methods/ directory, NOT generated ones.
        This preserves the manually curated methods data.

        Output: output_dir/<apk_name>/<apk_name>.methods

        Args:
            result: InstrumentationResult (for list of APKs)
        """
        if not self.all_methods_dir.exists():
            logger.warning("all_methods directory not found - skipping .methods copy")
            return

        copied = 0
        missing = 0

        for apk_name in result.instrumented_apks:
            methods_file = self.all_methods_dir / f"{apk_name}.methods"
            target_dir = self.output_dir / apk_name
            target_file = target_dir / f"{apk_name}.methods"

            if methods_file.exists():
                target_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(methods_file, target_file)
                copied += 1
            else:
                logger.debug(f"Methods file not found for {apk_name}")
                missing += 1

        logger.info(f"Copied {copied} .methods files ({missing} missing)")

    def _validate_complete_apks(self, result: InstrumentationResult) -> None:
        """
        Validate which APKs have all 4 required files.

        Required files for each APK:
        - <apk_name>.apk      - Instrumented APK
        - <apk_name>.gesda    - GESDA analysis
        - <apk_name>.wtg      - GATOR WTG
        - <apk_name>.reach    - REACH analysis
        - <apk_name>.methods  - Ground truth methods

        Only APKs with ALL files are marked as complete and can be used
        for validation experiments.

        Args:
            result: InstrumentationResult to update
        """
        logger.info("Validating APKs with all 4 required files...")

        for apk_name in result.instrumented_apks:
            apk_dir = self.output_dir / apk_name

            # Check all 4 required files
            required_files = [
                apk_dir / apk_name,              # Instrumented APK
                apk_dir / f"{apk_name}.gesda",   # GESDA
                apk_dir / f"{apk_name}.wtg",     # GATOR WTG
                apk_dir / f"{apk_name}.reach",   # REACH
                apk_dir / f"{apk_name}.methods", # Ground truth
            ]

            missing_files = [f.name for f in required_files if not f.exists()]

            if not missing_files:
                result.complete_apks.append(apk_name)
                logger.debug(f"  [COMPLETE] {apk_name}")
            else:
                logger.debug(f"  [INCOMPLETE] {apk_name}: missing {missing_files}")

        logger.info(f"Complete APKs (ready for experiments): {len(result.complete_apks)}/{len(result.instrumented_apks)}")

    def _print_summary(self, result: InstrumentationResult) -> None:
        """Print a summary of the instrumentation process."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("INSTRUMENTATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total APKs: {result.total_apks}")
        logger.info(f"Successfully instrumented: {len(result.instrumented_apks)} ({result.success_rate:.1f}%)")
        logger.info(f"Failed instrumentation: {len(result.failed_apks)}")
        logger.info(f"Static analysis success: {len(result.static_analysis_success)}")
        logger.info(f"Static analysis failed: {len(result.static_analysis_failed)}")
        if result.static_analysis_timeout:
            logger.info(f"Static analysis timeouts: {len(result.static_analysis_timeout)}")
        logger.info("")
        logger.info(f"*** COMPLETE APKs (all 4 files): {len(result.complete_apks)} ({result.complete_rate:.1f}%) ***")
        logger.info("")

        if result.failed_apks:
            logger.info("Failed APKs:")
            for apk, error in list(result.failed_apks.items())[:10]:  # Show first 10
                logger.info(f"  - {apk}: {error[:50]}...")
            if len(result.failed_apks) > 10:
                logger.info(f"  ... and {len(result.failed_apks) - 10} more")

        if result.static_analysis_timeout:
            logger.info("")
            logger.info("Timed out APKs (exceeded 30 min):")
            for apk in result.static_analysis_timeout[:5]:  # Show first 5
                logger.info(f"  - {apk}")
            if len(result.static_analysis_timeout) > 5:
                logger.info(f"  ... and {len(result.static_analysis_timeout) - 5} more")

        logger.info("")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info("Structure: apks_instrumented/<apk_name>/")
        logger.info("  - <apk_name>.apk      (instrumented)")
        logger.info("  - <apk_name>.gesda    (GESDA: app structure)")
        logger.info("  - <apk_name>.wtg      (GATOR: Window Transition Graph)")
        logger.info("  - <apk_name>.reach    (REACH: reachability analysis)")
        logger.info("  - <apk_name>.methods  (ground truth from all_methods/)")
        logger.info("")
        logger.info("NOTE: Only COMPLETE APKs (all 4 files) can be used for experiments.")

    def _find_rv_android_dir(self) -> Optional[Path]:
        """
        Find the rv-android directory from RVSEC_HOME environment variable.

        Returns:
            Path to rv-android directory, or None if not found
        """
        rvsec_home = os.environ.get("RVSEC_HOME")
        if not rvsec_home:
            logger.error("RVSEC_HOME environment variable not set")
            return None

        rv_android_path = Path(rvsec_home) / "rv-android"
        if not rv_android_path.exists():
            logger.error(f"rv-android directory not found: {rv_android_path}")
            return None

        if not (rv_android_path / "pom.xml").exists():
            logger.error(f"pom.xml not found in: {rv_android_path}")
            return None

        return rv_android_path

    def cleanup_temp(self) -> None:
        """Remove temporary files and directories."""
        if self.temp_dir.exists():
            logger.info(f"Cleaning up temporary directory: {self.temp_dir}")
            shutil.rmtree(self.temp_dir)
