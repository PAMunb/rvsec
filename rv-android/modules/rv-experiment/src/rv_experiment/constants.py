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
RESULTS_DIR = "results"
INSTRUMENTED_DIR = "out"
MONITORS_DIR = "monitors"
INSTRUMENTED_APKS_DIR = "instrumented_apks"
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

# Default timeouts and repetitions
DEFAULT_TIMEOUT = 300
DEFAULT_REPETITIONS = 1
DEFAULT_TOOL_TIMEOUT = 60

# Specification sets for runtime verification monitors.
# JCA and generic are predefined directories under RVSEC_HOME containing .mop files.
# Custom allows user-provided .mop files via --custom-specs-dir.
# An experiment uses exactly one spec set — they are mutually exclusive.
SPEC_SET_JCA = "jca"
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
