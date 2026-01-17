#!/usr/bin/env python3
"""
Multimodal validation runner for rv-agent.

Executes validation experiments comparing different agent modes
and collects metrics for analysis.

Usage:
    poetry run python -m validation.run_multimodal --help
    poetry run python -m validation.run_multimodal run --config config.json
    poetry run python -m validation.run_multimodal run --apks-dir ./apks --modes multimode --timeout 300
"""

import argparse
import json
import logging
import random
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Imports for rv-agent execution
try:
    from rv_agent.config.agent_config import RVAgentConfig
    from rv_agent.agent.agent_factory import AgentFactory
    from rv_agent_validation.multimodal.collector import MultimodalMetricsCollector
    from rv_android_core.domain.app import App
    from rv_android_core.domain.static import StaticAnalysisData
    from rv_android_core.util.android.logcat_manager import LogcatManager
    RVAGENT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"rv-agent imports not available: {e}")
    RVAGENT_AVAILABLE = False
    App = None  # Fallback
    StaticAnalysisData = None
    LogcatManager = None

# Coverage tracking (own implementation for compatibility with .methods format)
try:
    from rv_agent_validation.coverage import (
        LogcatCoverageParser,
        MethodsParser,
        CoverageTracker,
        CoverageResult,
    )
    COVERAGE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Coverage imports not available: {e}")
    COVERAGE_AVAILABLE = False
    LogcatCoverageParser = None
    MethodsParser = None
    CoverageTracker = None
    CoverageResult = None

# Import static analysis parser (optional - for WTG experiments)
try:
    from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser
    STATIC_ANALYSIS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"rv-static-analysis imports not available: {e}")
    STATIC_ANALYSIS_AVAILABLE = False
    StaticAnalysisParser = None


# =============================================================================
# Package Detection from CSV
# =============================================================================

# Cache for detected package mapping (apk_name -> detected_package)
_detected_package_cache: Dict[str, str] = {}


def load_detected_packages_from_csv(csv_path: Path) -> Dict[str, str]:
    """
    Load detected package mapping from apks_validation.csv.

    The CSV contains 'apk' and 'detected_package' columns. The detected_package
    is determined by a heuristic that handles game engines, multi-package APKs,
    and package mismatches.

    Returns:
        Dict mapping apk filename to detected package name.
    """
    global _detected_package_cache

    if _detected_package_cache:
        return _detected_package_cache

    if not csv_path.exists():
        logger.warning(f"Package CSV not found: {csv_path}")
        return {}

    try:
        import csv
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                apk_name = row.get('apk', '')
                detected_pkg = row.get('detected_package', '')
                if apk_name and detected_pkg:
                    _detected_package_cache[apk_name] = detected_pkg

        logger.info(f"Loaded {len(_detected_package_cache)} detected packages from CSV")
    except Exception as e:
        logger.warning(f"Failed to load package CSV: {e}")

    return _detected_package_cache


def get_detected_package(apk_name: str, csv_path: Optional[Path] = None) -> Optional[str]:
    """
    Get detected package for an APK from the CSV cache.

    Args:
        apk_name: APK filename (e.g., 'com.example.app_1.apk')
        csv_path: Optional path to CSV (uses default if not provided)

    Returns:
        Detected package name or None if not found.
    """
    if csv_path is None:
        # Default to module's data directory
        module_dir = Path(__file__).parent.parent.parent.parent
        csv_path = module_dir / "data" / "apks_validation.csv"

    packages = load_detected_packages_from_csv(csv_path)
    return packages.get(apk_name)


# =============================================================================
# Retry Configuration
# =============================================================================

# Infrastructure errors that warrant automatic retry
INFRASTRUCTURE_ERRORS = [
    "INSTALL_FAILED",
    "device not found",
    "Connection refused",
    "TimeoutError",
    "ADB server",
    "cannot connect",
    "error: closed",
    "daemon not running",
]

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5


def is_infrastructure_error(error_msg: str) -> bool:
    """Check if error is infrastructure-related (should retry)."""
    error_lower = error_msg.lower()
    return any(e.lower() in error_lower for e in INFRASTRUCTURE_ERRORS)


# =============================================================================
# APK Management Functions
# =============================================================================

def get_package_from_apk(apk_path: Path, device_serial: str = "emulator-5554") -> Optional[str]:
    """Extract package name from APK using androguard via App class."""
    if App is None:
        logger.warning("App class not available - cannot extract package name")
        return None

    try:
        app = App(app_path=str(apk_path), validate_on_init=True)
        return app.package_name
    except Exception as e:
        logger.warning(f"Failed to get package from APK {apk_path.name}: {e}")
    return None


def install_apk(apk_path: Path, device_serial: str = "emulator-5554") -> bool:
    """Install APK on device."""
    logger.info(f"📦 Installing APK: {apk_path.name}")
    try:
        result = subprocess.run(
            ["adb", "-s", device_serial, "install", "-r", "-g", str(apk_path)],
            capture_output=True, text=True, timeout=120
        )
        if "Success" in result.stdout:
            logger.info(f"✅ APK installed successfully")
            return True
        else:
            logger.error(f"❌ APK installation failed: {result.stdout} {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        logger.error("❌ APK installation timed out")
        return False
    except Exception as e:
        logger.error(f"❌ APK installation error: {e}")
        return False


def uninstall_apk(package_name: str, device_serial: str = "emulator-5554") -> bool:
    """Uninstall app from device."""
    logger.info(f"🗑️ Uninstalling: {package_name}")
    try:
        result = subprocess.run(
            ["adb", "-s", device_serial, "uninstall", package_name],
            capture_output=True, text=True, timeout=60
        )
        if "Success" in result.stdout:
            logger.info(f"✅ App uninstalled successfully")
            return True
        else:
            logger.warning(f"⚠️ Uninstall result: {result.stdout.strip()}")
            return False
    except Exception as e:
        logger.warning(f"⚠️ Uninstall error: {e}")
        return False


def discover_apks(apks_dir: Path) -> Dict[str, Path]:
    """
    Discover APKs in directory (recursive) and return mapping of package_name -> apk_path.

    Note: Only processes actual files, not directories that end with .apk
    """
    apk_mapping = {}

    if not apks_dir.exists():
        logger.warning(f"APKs directory does not exist: {apks_dir}")
        return apk_mapping

    # Search recursively for APKs (only files, not directories)
    for apk_path in apks_dir.glob("**/*.apk"):
        # Skip directories that end in .apk
        if not apk_path.is_file():
            continue

        # Resolve to absolute path
        apk_path = apk_path.resolve()

        package_name = get_package_from_apk(apk_path)
        if package_name:
            apk_mapping[package_name] = apk_path
            logger.debug(f"Discovered: {package_name} -> {apk_path.name}")
        else:
            logger.warning(f"Could not get package name for: {apk_path.name}")

    return apk_mapping


# =============================================================================
# Static Analysis Data Loading
# =============================================================================

def load_static_data_for_app(
    static_data_dir: Path,
    package_name: str,
    apk_mapping: Dict[str, Path]
) -> Optional["StaticAnalysisData"]:
    """
    Load static analysis data (WTG, GESDA, REACH) for an app.

    Args:
        static_data_dir: Directory containing static analysis files
        package_name: Package name of the app
        apk_mapping: Mapping of package names to APK paths

    Returns:
        StaticAnalysisData if files found, None otherwise
    """
    if not STATIC_ANALYSIS_AVAILABLE:
        logger.warning("Static analysis parser not available")
        return None

    if not static_data_dir or not static_data_dir.exists():
        logger.warning(f"Static data directory not found: {static_data_dir}")
        return None

    # Find the APK name for this package
    apk_path = apk_mapping.get(package_name)
    if apk_path:
        apk_name = apk_path.name  # e.g., "cryptoapp.apk"
    else:
        # Try to find by matching package in directory names
        apk_name = None
        for subdir in static_data_dir.iterdir():
            if subdir.is_dir() and subdir.name.endswith(".apk"):
                # Check if any file in subdir contains package reference
                apk_name = subdir.name
                break

    if not apk_name:
        logger.warning(f"Could not find APK name for package: {package_name}")
        return None

    # Build path to static data directory for this app
    # Structure: static_data_dir/{apk_name}/{apk_name}.{wtg,gesda,reach}
    app_static_dir = static_data_dir / apk_name

    if not app_static_dir.exists():
        logger.warning(f"Static data directory not found for {apk_name}: {app_static_dir}")
        return None

    # Check if required files exist
    wtg_file = app_static_dir / f"{apk_name}.wtg"
    gesda_file = app_static_dir / f"{apk_name}.gesda"
    reach_file = app_static_dir / f"{apk_name}.reach"

    if not wtg_file.exists():
        logger.warning(f"WTG file not found: {wtg_file}")
        return None

    # Parse static analysis data
    try:
        parser = StaticAnalysisParser()
        static_data = parser.read_static_analysis_files(
            results_dir=str(app_static_dir),
            apk=apk_name,
            package=package_name
        )
        logger.info(f"Loaded static data for {package_name}: {static_data.wtg is not None} WTG")
        return static_data
    except Exception as e:
        logger.error(f"Error loading static data for {package_name}: {e}")
        return None


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class MultimodalValidationConfig:
    """Configuration for multimodal validation experiments."""

    # Apps to test (can be package names or APK paths)
    app_packages: List[str] = field(default_factory=list)
    apks_dir: str = ""

    # APK mapping (package_name -> apk_path) - auto-discovered or manual
    apk_paths: Dict[str, str] = field(default_factory=dict)

    # Agent modes to compare
    agent_modes: List[str] = field(default_factory=lambda: ["multimode"])

    # Exploration strategies (for pure_algorithm mode)
    strategies: List[str] = field(default_factory=lambda: ["rvagent"])

    # LLM/algorithm probability for multimode
    llm_probability: float = 0.7  # Default: 70% LLM, 30% algorithm

    # Execution settings
    timeout_seconds: int = 300
    seeds: List[int] = field(default_factory=lambda: [42, 123, 456])
    max_iterations: int = 500

    # LLM settings
    llm_base_url: str = "http://192.168.0.21:30000/v1"
    llm_model: str = "Qwen/Qwen3-VL-4B-Instruct"
    llm_temperature: float = 0.01
    llm_top_p: float = 0.6  # RVAgentConfig default, range [0.0, 1.0]
    llm_top_k: int = 50  # RVAgentConfig default, range [1, 100]
    prompt_version: str = "v13"  # Prompt version to use (v13, v14, etc.)

    # Device settings
    device_serial: str = "emulator-5554"

    # Output settings
    output_dir: str = "validation_results/multimodal"
    save_screenshots: bool = True
    save_ui_dumps: bool = True

    # WTG integration settings
    use_wtg: bool = False  # Enable WTG guidance (requires static_data_dir)
    compare_wtg: bool = False  # Run with and without WTG for comparison

    # Static analysis data path (required for WTG)
    static_data_dir: Optional[str] = None

    @classmethod
    def from_json(cls, filepath: Path) -> "MultimodalValidationConfig":
        """Load config from JSON file."""
        with open(filepath) as f:
            data = json.load(f)
        return cls(**data)

    def to_json(self, filepath: Path) -> None:
        """Save config to JSON file."""
        with open(filepath, "w") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def default(cls) -> "MultimodalValidationConfig":
        """Create default configuration."""
        return cls(
            app_packages=[
                "com.aidinhut.simpletextcrypt",
                "byrne.utilities.hashpass",
            ],
            apks_dir="/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples",
            agent_modes=["pure_algorithm", "llm_only", "multimode"],
            timeout_seconds=300,
            seeds=[42, 123, 456],
        )


def generate_config_template(output_path: Path) -> None:
    """Generate a template configuration file."""
    config = MultimodalValidationConfig.default()
    config.to_json(output_path)
    logger.info(f"Generated config template: {output_path}")


def validate_config(config: MultimodalValidationConfig) -> List[str]:
    """Validate configuration and return list of errors."""
    errors = []

    if not config.app_packages:
        errors.append("No app_packages specified")

    if not config.agent_modes:
        errors.append("No agent_modes specified")

    valid_modes = {"pure_algorithm", "llm_only", "multimode"}
    for mode in config.agent_modes:
        if mode not in valid_modes:
            errors.append(f"Invalid agent_mode: {mode}")

    if config.timeout_seconds < 60:
        errors.append("timeout_seconds should be at least 60")

    if not config.seeds:
        errors.append("No seeds specified")

    return errors


def run_single_experiment_with_retry(
    app_package: str,
    mode: str,
    seed: int,
    config: MultimodalValidationConfig,
    output_dir: Path,
    run_number: int,
    total_runs: int,
    apk_path: Optional[Path] = None,
    static_data: Optional["StaticAnalysisData"] = None,
    wtg_variant: Optional[str] = None,
    strategy: str = "rvagent",
    disable_static_autoload: bool = False,
) -> Dict[str, Any]:
    """
    Run a single experiment with automatic retry for infrastructure errors.

    Wraps run_single_experiment with retry logic for transient infrastructure failures.
    """
    last_error = None

    for attempt in range(MAX_RETRIES):
        result = run_single_experiment(
            app_package=app_package,
            mode=mode,
            seed=seed,
            config=config,
            output_dir=output_dir,
            run_number=run_number,
            total_runs=total_runs,
            apk_path=apk_path,
            static_data=static_data,
            wtg_variant=wtg_variant,
            strategy=strategy,
            disable_static_autoload=disable_static_autoload,
        )

        # Check if run succeeded
        if result.get("status") not in ("error", "failed"):
            return result

        # Check if infrastructure error (should retry)
        error_msg = str(result.get("error", ""))
        if is_infrastructure_error(error_msg):
            logger.warning(
                f"Infrastructure error on attempt {attempt + 1}/{MAX_RETRIES}: {error_msg}"
            )
            last_error = error_msg
            if attempt < MAX_RETRIES - 1:
                logger.info(f"Retrying in {RETRY_DELAY_SECONDS}s...")
                time.sleep(RETRY_DELAY_SECONDS)
                continue
        else:
            # Agent error, don't retry
            return result

    # All retries exhausted
    logger.error(f"All {MAX_RETRIES} retries exhausted for {app_package}")
    result["retries_attempted"] = MAX_RETRIES
    result["final_error"] = last_error
    return result


def run_single_experiment(
    app_package: str,
    mode: str,
    seed: int,
    config: MultimodalValidationConfig,
    output_dir: Path,
    run_number: int,
    total_runs: int,
    apk_path: Optional[Path] = None,
    static_data: Optional["StaticAnalysisData"] = None,
    wtg_variant: Optional[str] = None,  # "with_wtg" or "without_wtg" for compare mode
    strategy: str = "rvagent",  # Exploration strategy for pure_algorithm mode
    disable_static_autoload: bool = False,  # Disable auto-loading static data from APK dir
) -> Dict[str, Any]:
    """
    Run a single experiment (one app, one mode, one seed).

    Handles APK lifecycle:
    1. Install APK before test (if apk_path provided)
    2. Run test
    3. Uninstall APK after test

    Args:
        static_data: Optional static analysis data for WTG integration
        wtg_variant: Optional variant name for WTG comparison experiments
        strategy: Exploration strategy (rvagent, dfs, bfs, greedy)
        disable_static_autoload: If True, skip auto-loading static data from APK dir

    Returns:
        Dictionary with run results and metrics path
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"RUN {run_number}/{total_runs}")
    logger.info(f"App: {app_package}")
    logger.info(f"Mode: {mode}")
    logger.info(f"Strategy: {strategy}")
    logger.info(f"Seed: {seed}")
    if wtg_variant:
        logger.info(f"WTG: {wtg_variant}")
    elif static_data:
        logger.info(f"WTG: enabled")
    if apk_path:
        logger.info(f"APK: {apk_path.name}")
    logger.info(f"{'='*60}")

    # Set random seed for reproducibility
    random.seed(seed)

    # Install APK if path provided
    installed = False
    if apk_path and apk_path.exists():
        installed = install_apk(apk_path, config.device_serial)
        if not installed:
            return {
                "app_package": app_package,
                "mode": mode,
                "seed": seed,
                "status": "error",
                "error": "APK installation failed",
                "metrics_path": None,
            }
        # Small delay after installation
        time.sleep(2)

    # Setup logcat capture
    logcat_manager = None
    logcat_file = None
    methods_file = None
    wtg_suffix = f"_{wtg_variant}" if wtg_variant else ""

    if LogcatManager:
        try:
            # Create logcat directory and file
            logcat_dir = output_dir / "logcat"
            logcat_dir.mkdir(parents=True, exist_ok=True)
            logcat_file = logcat_dir / f"logcat_{app_package}_{mode}_{strategy}{wtg_suffix}_seed{seed}.txt"

            # Initialize and start logcat capture
            logcat_manager = LogcatManager(device_serial=config.device_serial)
            logcat_manager.start_capture(str(logcat_file), clear_buffer=True)
            logger.info(f"Started logcat capture: {logcat_file.name}")

            # Find .methods file for coverage calculation (same directory as APK)
            if apk_path and apk_path.parent.is_dir():
                potential_methods = apk_path.parent / f"{apk_path.name}.methods"
                if potential_methods.exists():
                    methods_file = potential_methods
                    logger.info(f"Found methods file: {methods_file.name}")

                # Auto-load static analysis data (WTG/GESDA/REACH) from APK directory
                # Skip if explicitly disabled (use_wtg: false)
                if static_data is None and StaticAnalysisParser and not disable_static_autoload:
                    wtg_file = apk_path.parent / f"{apk_path.name}.wtg"
                    gesda_file = apk_path.parent / f"{apk_path.name}.gesda"
                    reach_file = apk_path.parent / f"{apk_path.name}.reach"

                    if wtg_file.exists() and gesda_file.exists() and reach_file.exists():
                        try:
                            # Use detected_package from CSV (handles game engines, multi-package, etc.)
                            # Falls back to app_package if not found in CSV
                            static_pkg = get_detected_package(apk_path.name) or app_package
                            logger.info(f"Static analysis package: {static_pkg}")

                            parser = StaticAnalysisParser()
                            static_data = parser.parse(
                                reach_file=str(reach_file),
                                gator_file=str(wtg_file),
                                gesda_file=str(gesda_file),
                                package=static_pkg,
                            )
                            # Count activities from classes
                            activity_count = sum(1 for c in static_data.classes.classes.values() if c.is_activity)
                            logger.info(f"Loaded static analysis: WTG={static_data.wtg is not None}, "
                                       f"activities={activity_count}")
                        except Exception as e:
                            logger.warning(f"Failed to load static analysis: {e}")

        except Exception as e:
            logger.warning(f"Failed to initialize logcat capture: {e}")
            logcat_manager = None

    # Create metrics collector
    total_activities = 0
    if static_data and static_data.classes:
        total_activities = sum(1 for c in static_data.classes.classes.values() if c.is_activity)

    collector = MultimodalMetricsCollector(
        app_package=app_package,
        agent_mode=mode,
        timeout_seconds=config.timeout_seconds,
        seed=seed,
        total_activities=total_activities,
        output_dir=output_dir,
        strategy=strategy,
    )

    # Create agent config
    screenshot_suffix = f"{app_package}_{mode}_{strategy}_seed{seed}"
    agent_config = RVAgentConfig(
        package_name=app_package,
        device_id=config.device_serial,
        timeout=config.timeout_seconds,
        agent_mode=mode,
        strategy=strategy,  # Exploration strategy
        llm_probability=config.llm_probability,  # LLM/algorithm ratio for multimode
        llm_base_url=config.llm_base_url,
        llm_model=config.llm_model,
        llm_temperature=config.llm_temperature,
        llm_top_p=config.llm_top_p,
        llm_top_k=config.llm_top_k,
        prompt_version=config.prompt_version,
        screenshot_dir=str(output_dir / "screenshots" / screenshot_suffix),
    )

    start_time = time.time()
    result = {
        "app_package": app_package,
        "mode": mode,
        "strategy": strategy,
        "seed": seed,
        "llm_probability": config.llm_probability,
        "prompt_version": config.prompt_version,
        "llm_temperature": config.llm_temperature,
        "llm_top_p": config.llm_top_p,
        "llm_top_k": config.llm_top_k,
        "wtg_variant": wtg_variant,  # "with_wtg", "without_wtg", or None
        "wtg_enabled": static_data is not None,
        "status": "unknown",
        "error": None,
        "metrics_path": None,
        "logcat_file": str(logcat_file) if logcat_file else None,
        "coverage_metrics": None,
    }

    try:
        # Create agent with metrics collector and optional static data
        agent = AgentFactory.create_agent(
            config=agent_config,
            static_data=static_data,  # Pass WTG data if available
            metrics_collector=collector,
        )

        # Run agent
        logger.info(f"Starting agent execution...")
        agent_result = agent.run()

        result["status"] = agent_result.get("status", "completed")
        result["iterations"] = agent_result.get("iterations", 0)
        result["unique_states"] = agent_result.get("unique_states", 0)
        result["execution_time_s"] = agent_result.get("execution_time_s", 0)

        # Capture UI coverage metrics from agent (core metrics, not just validation)
        ui_coverage = agent_result.get("ui_coverage", {})
        if ui_coverage:
            result["ui_coverage"] = ui_coverage
            # Also update collector with core metrics
            collector.set_ui_coverage_from_agent(ui_coverage)
            logger.info(
                f"UI coverage: {ui_coverage.get('total_unique_elements', 0)} elements, "
                f"{ui_coverage.get('element_coverage', 0):.1f}% tested, "
                f"{ui_coverage.get('screens_visited', 0)} screens"
            )

        logger.info(f"Agent completed: {result['iterations']} iterations, {result['unique_states']} states")

    except Exception as e:
        logger.error(f"Experiment failed: {e}")
        logger.error(traceback.format_exc())
        result["status"] = "error"
        result["error"] = str(e)

    # Calculate coverage metrics from logcat
    if COVERAGE_AVAILABLE and logcat_file and logcat_file.exists():
        try:
            # Parse logcat
            logcat_parser = LogcatCoverageParser()
            cov_entries, err_entries = logcat_parser.parse_file(logcat_file)
            logger.info(f"Parsed logcat: {len(cov_entries)} coverage, {len(err_entries)} errors")

            # Calculate coverage if .methods file available
            if methods_file and methods_file.exists():
                methods_parser = MethodsParser(methods_file)
                tracker = CoverageTracker(methods_parser)
                tracker.process_coverage(cov_entries)
                tracker.process_errors(err_entries)
                coverage_result = tracker.get_result()

                coverage_metrics = coverage_result.to_dict()
                result["coverage_metrics"] = coverage_metrics

                # Set coverage metrics in collector for serialization
                collector.set_coverage_metrics(coverage_metrics)
                collector.session.logcat_file = str(logcat_file)

                logger.info(
                    f"Coverage: method={coverage_result.method_coverage:.1f}%, "
                    f"reaches_mop={coverage_result.reaches_mop_coverage:.1f}%, "
                    f"direct_mop={coverage_result.directly_reaches_mop_coverage:.1f}%, "
                    f"errors={coverage_result.unique_errors}"
                )
            else:
                # No .methods file - only report errors
                result["coverage_metrics"] = {
                    "unique_errors": len(err_entries),
                    "total_errors": len(err_entries),
                    "error_specs": list(set(e.spec for e in err_entries)),
                }
                logger.info(f"Coverage: no .methods file, errors={len(err_entries)}")

        except Exception as e:
            logger.warning(f"Failed to calculate coverage metrics: {e}")

    # Stop logcat capture
    if logcat_manager:
        try:
            logcat_manager.stop_capture()
            logger.info("Stopped logcat capture")
        except Exception as e:
            logger.warning(f"Failed to stop logcat capture: {e}")

    # Finalize collector (saves metrics)
    try:
        session = collector.finalize()
        # Include strategy and WTG variant in filename
        wtg_suffix = f"_{wtg_variant}" if wtg_variant else ""
        result["metrics_path"] = str(output_dir / f"multimodal_metrics_{app_package}_{mode}_{strategy}{wtg_suffix}_seed{seed}.json")
        result["hit_rate"] = session.hit_rate
        result["activity_coverage"] = session.activity_coverage
        logger.info(f"Metrics saved: hit_rate={session.hit_rate:.2%}, coverage={session.activity_coverage:.2%}")
    except Exception as e:
        logger.error(f"Failed to finalize metrics: {e}")

    # Uninstall APK if we installed it
    if installed:
        uninstall_apk(app_package, config.device_serial)

    result["total_time_s"] = time.time() - start_time
    return result


def run_validation(config: MultimodalValidationConfig) -> None:
    """
    Run multimodal validation experiments.

    For each app, mode, and seed combination:
    1. Install APK (if apks_dir provided)
    2. Create MultimodalMetricsCollector
    3. Create and run rv-agent with metrics collection
    4. Uninstall APK
    5. Save metrics to output_dir
    6. After all runs: generate summary report
    """
    if not RVAGENT_AVAILABLE:
        logger.error("rv-agent imports not available. Cannot run validation.")
        logger.error("Make sure you're running from the rv-android directory with proper PYTHONPATH")
        sys.exit(1)

    # Discover APKs from directory if provided
    apk_mapping: Dict[str, Path] = {}
    if config.apks_dir:
        apks_path = Path(config.apks_dir)

        # If app_packages specified, find APKs matching those packages (faster)
        if config.app_packages:
            logger.info(f"Looking for {len(config.app_packages)} specified apps in {config.apks_dir}")
            for apk_path in apks_path.glob("**/*.apk"):
                if not apk_path.is_file():
                    continue
                # Check if APK name contains the package name (common pattern)
                apk_name = apk_path.name.lower()
                for pkg in config.app_packages:
                    if pkg.lower() in apk_name or pkg.replace(".", "_") in apk_name:
                        # Verify by parsing APK
                        actual_pkg = get_package_from_apk(apk_path)
                        if actual_pkg == pkg:
                            apk_mapping[pkg] = apk_path.resolve()
                            logger.info(f"Found: {pkg} -> {apk_path.name}")
                            break
        else:
            # Full discovery when no packages specified
            apk_mapping = discover_apks(apks_path)
            logger.info(f"Discovered {len(apk_mapping)} APKs in {config.apks_dir}")
            config.app_packages = list(apk_mapping.keys())
            logger.info(f"Using {len(config.app_packages)} discovered apps")

    # Merge with manual apk_paths config
    for pkg, path_str in config.apk_paths.items():
        apk_mapping[pkg] = Path(path_str)

    # Validate config
    errors = validate_config(config)
    if errors:
        for error in errors:
            logger.error(f"Config error: {error}")
        sys.exit(1)

    # Determine WTG variants for comparison mode
    wtg_variants = []
    if config.compare_wtg:
        wtg_variants = ["with_wtg", "without_wtg"]
    elif config.use_wtg:
        wtg_variants = ["with_wtg"]
    else:
        wtg_variants = [None]  # No WTG

    # Calculate total runs
    total_runs = (
        len(config.app_packages) *
        len(config.agent_modes) *
        len(config.strategies) *
        len(config.seeds) *
        len(wtg_variants)
    )

    logger.info("=" * 60)
    logger.info("MULTIMODAL VALIDATION")
    logger.info("=" * 60)
    logger.info(f"Apps: {len(config.app_packages)} - {config.app_packages}")
    logger.info(f"APKs available: {len(apk_mapping)}")
    logger.info(f"Modes: {config.agent_modes}")
    logger.info(f"Strategies: {config.strategies}")
    logger.info(f"Seeds: {config.seeds}")
    logger.info(f"LLM probability: {config.llm_probability}")
    if config.compare_wtg:
        logger.info(f"WTG comparison: with_wtg vs without_wtg")
    elif config.use_wtg:
        logger.info(f"WTG: enabled")
    else:
        logger.info(f"WTG: disabled")
    logger.info(f"Total runs: {total_runs}")
    logger.info(f"Timeout per run: {config.timeout_seconds}s")
    logger.info(f"LLM: {config.llm_model} @ {config.llm_base_url}")
    logger.info(f"LLM params: T={config.llm_temperature}, top_p={config.llm_top_p}, top_k={config.llm_top_k}")
    logger.info(f"Prompt version: {config.prompt_version}")
    logger.info(f"Output dir: {config.output_dir}")
    logger.info("=" * 60)

    # Pre-load static data for all apps if WTG is enabled
    static_data_cache: Dict[str, Any] = {}  # app_package -> StaticAnalysisData or None
    if config.use_wtg or config.compare_wtg:
        if config.static_data_dir:
            static_data_path = Path(config.static_data_dir)
            logger.info(f"Pre-loading static data from: {static_data_path}")
            for app_package in config.app_packages:
                static_data = load_static_data_for_app(static_data_path, app_package, apk_mapping)
                static_data_cache[app_package] = static_data
                if static_data:
                    logger.info(f"  {app_package}: WTG loaded")
                else:
                    logger.warning(f"  {app_package}: WTG not found")
        else:
            logger.warning("WTG enabled but static_data_dir not set")

    # Create output directory
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save config for reproducibility
    config.to_json(output_dir / "config.json")
    logger.info(f"Config saved to: {output_dir / 'config.json'}")

    # Run experiments
    results = []
    run_number = 0

    for app_package in config.app_packages:
        # Get APK path if available
        apk_path = apk_mapping.get(app_package)

        for mode in config.agent_modes:
            for strategy in config.strategies:
                for seed in config.seeds:
                    for wtg_variant in wtg_variants:
                        run_number += 1

                        # Determine static_data for this run
                        static_data = None
                        if wtg_variant == "with_wtg":
                            static_data = static_data_cache.get(app_package)
                        # "without_wtg" or None: static_data remains None

                        # Disable auto-loading static data when WTG is not wanted:
                        # - "without_wtg" variant (in compare mode)
                        # - use_wtg=False (global setting)
                        disable_autoload = (
                            wtg_variant == "without_wtg" or
                            (wtg_variant is None and not config.use_wtg)
                        )

                        result = run_single_experiment_with_retry(
                            app_package=app_package,
                            mode=mode,
                            seed=seed,
                            config=config,
                            output_dir=output_dir,
                            run_number=run_number,
                            total_runs=total_runs,
                            apk_path=apk_path,
                            static_data=static_data,
                            wtg_variant=wtg_variant,
                            strategy=strategy,
                            disable_static_autoload=disable_autoload,
                        )
                        results.append(result)

                        # Save intermediate results
                        with open(output_dir / "results_progress.json", "w") as f:
                            json.dump(results, f, indent=2)

    # Save final results
    with open(output_dir / "results_final.json", "w") as f:
        json.dump(results, f, indent=2)

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("VALIDATION COMPLETE")
    logger.info("=" * 60)

    successful = sum(1 for r in results if r["status"] == "completed")
    failed = sum(1 for r in results if r["status"] == "error")

    logger.info(f"Total runs: {len(results)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")

    if results:
        hit_rates = [r.get("hit_rate", 0) for r in results if r.get("hit_rate") is not None]
        if hit_rates:
            logger.info(f"Average hit rate: {sum(hit_rates)/len(hit_rates):.2%}")

    logger.info(f"\nResults saved to: {output_dir}")
    logger.info(f"Run 'analyze' command to generate detailed report")


def analyze_results(results_dir: Path, output_path: Optional[Path] = None) -> None:
    """Analyze existing validation results."""
    from rv_agent_validation.multimodal.analyzer import MultimodalAnalyzer

    analyzer = MultimodalAnalyzer()
    count = analyzer.load_sessions(results_dir)

    if count == 0:
        logger.error(f"No metrics found in {results_dir}")
        return

    analyzer.print_summary()

    if output_path:
        analyzer.generate_report(output_path)


def run_multimodal_validation(
    config_path: Optional[str] = None,
    apks_dir: Optional[str] = None,
    static_data_dir: Optional[str] = None,
    modes: Optional[List[str]] = None,
    seeds: Optional[List[int]] = None,
    timeout: int = 300,
    output_dir: str = "results",
    device_serial: str = "emulator-5554",
) -> None:
    """
    CLI wrapper for run_validation.

    Creates a MultimodalValidationConfig from parameters and runs validation.
    """
    if config_path:
        # Load config from file
        import json
        with open(config_path) as f:
            config_data = json.load(f)
        config = MultimodalValidationConfig(**config_data)
    else:
        # Create config from parameters
        config = MultimodalValidationConfig(
            apks_dir=apks_dir or "",
            output_dir=output_dir,
            agent_modes=modes or ["multimode"],
            seeds=seeds or [42],
            timeout_seconds=timeout,
            device_serial=device_serial,
            static_data_dir=static_data_dir,
        )

    run_validation(config)


def main():
    parser = argparse.ArgumentParser(
        description="Multimodal validation for rv-agent"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run validation experiments")
    run_parser.add_argument(
        "--config", type=Path,
        help="Path to config JSON file"
    )
    run_parser.add_argument(
        "--apks-dir", type=str,
        help="Directory containing APK files to test (auto-discovers packages)"
    )
    run_parser.add_argument(
        "--apps", type=str,
        help="Comma-separated list of app packages (or use --apks-dir to auto-discover)"
    )
    run_parser.add_argument(
        "--modes", type=str, default="multimode",
        help="Comma-separated agent modes (default: multimode)"
    )
    run_parser.add_argument(
        "--timeout", type=int, default=300,
        help="Timeout per run in seconds (default: 300)"
    )
    run_parser.add_argument(
        "--seeds", type=str, default="42,123,456",
        help="Comma-separated seeds (default: 42,123,456)"
    )
    run_parser.add_argument(
        "--output", type=str, default="validation_results/multimodal",
        help="Output directory"
    )
    run_parser.add_argument(
        "--strategies", type=str, default="rvagent",
        help="Comma-separated exploration strategies (default: rvagent)"
    )
    run_parser.add_argument(
        "--llm-probability", type=float, default=0.7,
        help="LLM probability for multimode (default: 0.7)"
    )
    run_parser.add_argument(
        "--prompt-version", type=str, default="v13",
        help="Prompt version to use (default: v13)"
    )
    run_parser.add_argument(
        "--llm-temperature", type=float, default=0.01,
        help="LLM temperature (default: 0.01)"
    )
    run_parser.add_argument(
        "--llm-top-p", type=float, default=0.6,
        help="LLM top_p (default: 0.6)"
    )
    run_parser.add_argument(
        "--llm-top-k", type=int, default=50,
        help="LLM top_k (default: 50)"
    )
    run_parser.add_argument(
        "--use-wtg", action="store_true",
        help="Enable WTG navigation guidance (requires --static-data-dir)"
    )
    run_parser.add_argument(
        "--compare-wtg", action="store_true",
        help="Run with and without WTG for comparison (E2 experiment)"
    )
    run_parser.add_argument(
        "--static-data-dir", type=str,
        help="Directory containing static analysis files (.wtg, .gesda, .reach)"
    )

    # Generate config template
    template_parser = subparsers.add_parser(
        "template", help="Generate config template"
    )
    template_parser.add_argument(
        "--output", type=Path, default=Path("multimodal_config.json"),
        help="Output path for template"
    )

    # Analyze results
    analyze_parser = subparsers.add_parser(
        "analyze", help="Analyze existing results"
    )
    analyze_parser.add_argument(
        "results_dir", type=Path,
        help="Directory containing validation results"
    )
    analyze_parser.add_argument(
        "--output", type=Path,
        help="Output path for report JSON"
    )

    args = parser.parse_args()

    if args.command == "run":
        # Load or create config
        if args.config:
            config = MultimodalValidationConfig.from_json(args.config)
            # Allow command-line overrides
            if args.use_wtg:
                config.use_wtg = True
            if args.compare_wtg:
                config.compare_wtg = True
            if args.static_data_dir:
                config.static_data_dir = args.static_data_dir
            if hasattr(args, 'strategies') and args.strategies != "rvagent":
                config.strategies = args.strategies.split(",")
            if hasattr(args, 'llm_probability'):
                config.llm_probability = args.llm_probability
            if hasattr(args, 'prompt_version'):
                config.prompt_version = args.prompt_version
            if hasattr(args, 'llm_temperature'):
                config.llm_temperature = args.llm_temperature
            if hasattr(args, 'llm_top_p'):
                config.llm_top_p = args.llm_top_p
            if hasattr(args, 'llm_top_k'):
                config.llm_top_k = args.llm_top_k
        else:
            config = MultimodalValidationConfig(
                app_packages=args.apps.split(",") if args.apps else [],
                apks_dir=args.apks_dir or "",
                agent_modes=args.modes.split(","),
                strategies=args.strategies.split(","),
                llm_probability=args.llm_probability,
                prompt_version=args.prompt_version,
                llm_temperature=args.llm_temperature,
                llm_top_p=args.llm_top_p,
                llm_top_k=args.llm_top_k,
                timeout_seconds=args.timeout,
                seeds=[int(s) for s in args.seeds.split(",")],
                output_dir=args.output,
                use_wtg=getattr(args, 'use_wtg', False),
                compare_wtg=getattr(args, 'compare_wtg', False),
                static_data_dir=getattr(args, 'static_data_dir', None),
            )

        run_validation(config)

    elif args.command == "template":
        generate_config_template(args.output)

    elif args.command == "analyze":
        analyze_results(args.results_dir, args.output)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
