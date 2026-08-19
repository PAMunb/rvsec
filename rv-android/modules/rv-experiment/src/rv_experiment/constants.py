"""
Experiment Constants - Directory Structure and Paths

### Directory Structure Overview:
Following the original RV-Android structure with clear separation of concerns:

- INSTRUMENTED_DIR (out/): Shared pre-processing artifacts (APKs, static analysis)
- RESULTS_DIR (results/): Individual experiment results with task tracking
- MONITORS_DIR (mop_out/): Generated runtime verification monitors

### Role in the System:
- Provides consistent directory structure across all experiment components
- Ensures compatibility with original behavior while maintaining modularity
- Enables proper separation between pre-processing and experiment results

Spec cross-reference (openspec/specs/experiment/spec.md): this layout embodies
INV-EXP-14 ("The experiment results directory MUST be a flat path without internal
nesting") — one flat directory per experiment under results/ holds tasks.json and
the *.csv reports directly; INV-EXP-11 (PostProcessor writes instrument_errors.json
"in the results directory"); and INV-EXP-12 (ExperimentConfig defaults: output_dir
"out" = INSTRUMENTED_DIR, results_dir "results" = RESULTS_DIR).
"""

import os

# Base directories following original structure
WORKING_DIR = os.getcwd()

# Core directory structure:
#
#   results/                      <- RESULTS_DIR: persistent experiment results
#     my_experiment/              <- one flat directory per experiment
#       tasks.json                <- rv-platform task tracking (enables resume)
#       experiment_config.json    <- config snapshot for reproducibility
#       experiment_completion.json <- Phase 3 diagnostic marker
#       *.csv                     <- rv-platform result reports
#
#   out/                          <- INSTRUMENTED_DIR: temporary pre-processing artifacts
#     monitors/                   <- MONITORS_DIR: JavaMOP/RV-Monitor output
#     instrumented_apks/          <- INSTRUMENTED_APKS_DIR: woven APKs + static analysis JSON
#     static_analysis/            <- STATIC_ANALYSIS_DIR: (legacy, output now goes to instrumented_apks/)
#
# When --name is used, output_dir is set to results/<name>/ so artifacts
# and results coexist. When not, output_dir defaults to out/ (INSTRUMENTED_DIR).
# RESULTS_DIR is the INV-EXP-12 default for results_dir and the root of the
# INV-EXP-14 flat results path. INSTRUMENTED_DIR is the INV-EXP-12 default for
# output_dir (shared pre-processing artifacts).
RESULTS_DIR = "results"
INSTRUMENTED_DIR = "out"
MONITORS_DIR = "monitors"
# INSTRUMENTED_APKS_DIR is the filter basis for INV-EXP-15 (static-analysis targeting:
# only APKs with a corresponding instrumented file) and INV-EXP-16 (execution targeting:
# only APKs with a matching `.apk.json` static-analysis output in this same dir), and the
# INV-EXP-08 fallback destination (original APKs copied here when instrumentation fails).
# Static-analysis JSON is emitted here, not under STATIC_ANALYSIS_DIR.
INSTRUMENTED_APKS_DIR = "instrumented_apks"
# Legacy: output now goes to instrumented_apks/. INV-EXP-16 reads `.apk.json`
# static-analysis output from instrumented_apks/, not from this directory.
STATIC_ANALYSIS_DIR = "static_analysis"

# Default source directories
DEFAULT_APKS_DIR = "apks_examples"
DEFAULT_APK_PATTERNS = ["*.apk"]

# Experiment structure
EXPERIMENT_LOGS_DIR = "logs"
EXPERIMENT_CONFIG_FILE = "config.json"
EXPERIMENT_TASKS_FILE = "tasks.json"

# File extensions (re-exported from rv-android-core)

EXTENSION_ASPECTJ = ".aj"

# Default timeouts and repetitions.
# DEFAULT_TIMEOUT (300s) and DEFAULT_REPETITIONS (1) are the defaults asserted by
# Scenario "Single Tool With Default Configuration" under Requirement "CLI with Tool
# Specification DSL (FR16, NFR05)": "the experiment MUST execute with default timeout
# (300s), default repetitions (1), and default specification set (jca)".
DEFAULT_TIMEOUT = 300
DEFAULT_REPETITIONS = 1
DEFAULT_TOOL_TIMEOUT = 60

# Specification sets for runtime verification monitors.
# JCA, JCA Android and generic are predefined directories under RVSEC_HOME containing
# .mop files. Custom allows user-provided .mop files via --custom-specs-dir.
# An experiment uses exactly one spec set — they are mutually exclusive.
# SPEC_SET_JCA_ANDROID is the successor of the frozen jca set, targeted at Android
# API 30 / Android 11: all 23 specifications seeded byte-for-byte from jca, predicate
# machinery included, with every allow-list re-transcribed from the generated CrySL
# rules under MetaCrySL/generated/api30 (issue #104). It is selectable by name rather than only through SPEC_SET_CUSTOM
# because it is the only set carrying the specification repairs: a mistyped or stale
# custom path selects an uncorrected instrument while the experiment reports as though
# it ran the corrected one. The derived Android set that held this name before was
# reproved by the 2026-08-08 predicate audit and is archived, unselectable, as
# rvsec-mop/src/main/resources/jca_android_bug_predicate/ — the enumeration below did
# not grow, the name was rebound.
# SPEC_SET_CUSTOM triggers INV-EXP-04: when specification_set is "custom",
# custom_specs_dir MUST be set and point to a directory containing at least one .mop
# file, else the CLI raises ClickException before execution. DEFAULT_SPEC_SET (jca) is
# the default from Scenario "Single Tool With Default Configuration".
SPEC_SET_JCA = "jca"
SPEC_SET_JCA_ANDROID = "jca_android"
SPEC_SET_GENERIC = "generic"
SPEC_SET_CUSTOM = "custom"
DEFAULT_SPEC_SET = SPEC_SET_JCA


def get_absolute_path(relative_path: str) -> str:
    """
    Convert relative path to absolute path from working directory.

    Args:
        relative_path: Relative path from working directory

    Returns:
        Absolute path string
    """
    return os.path.join(WORKING_DIR, relative_path)


def get_experiment_dir(results_dir: str, experiment_id: str) -> str:
    """
    Get experiment directory path within results directory.

    Args:
        results_dir: Results directory path
        experiment_id: Unique experiment identifier

    Returns:
        Experiment directory path
    """
    return os.path.join(results_dir, experiment_id)


def get_apk_results_dir(results_dir: str, experiment_id: str, apk_name: str) -> str:
    """
    Get APK-specific results directory within experiment.

    Args:
        results_dir: Results directory path
        experiment_id: Unique experiment identifier
        apk_name: APK filename

    Returns:
        APK results directory path
    """
    return os.path.join(get_experiment_dir(results_dir, experiment_id), apk_name)


def get_static_analysis_source_path(
    output_dir: str, apk_name: str, extension: str
) -> str:
    """
    Get source path for static analysis file within output directory.

    Args:
        output_dir: Output directory path
        apk_name: APK filename
        extension: File extension (e.g., .json, .methods)

    Returns:
        Source file path in static analysis directory
    """
    return os.path.join(output_dir, STATIC_ANALYSIS_DIR, f"{apk_name}{extension}")


def get_instrumented_apk_path(output_dir: str, apk_name: str) -> str:
    """
    Get path to instrumented APK within output directory.

    Args:
        output_dir: Output directory path
        apk_name: Original APK filename

    Returns:
        Instrumented APK path
    """
    return os.path.join(output_dir, INSTRUMENTED_APKS_DIR, apk_name)
