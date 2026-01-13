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
    from multimodal.collector import MultimodalMetricsCollector
    from rv_android_core.domain.app import App
    from rv_android_core.domain.static import StaticAnalysisData
    RVAGENT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"rv-agent imports not available: {e}")
    RVAGENT_AVAILABLE = False
    App = None  # Fallback
    StaticAnalysisData = None

# Import static analysis parser (optional - for WTG experiments)
try:
    from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser
    STATIC_ANALYSIS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"rv-static-analysis imports not available: {e}")
    STATIC_ANALYSIS_AVAILABLE = False
    StaticAnalysisParser = None


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

    # Execution settings
    timeout_seconds: int = 300
    seeds: List[int] = field(default_factory=lambda: [42, 123, 456])
    max_iterations: int = 500

    # LLM settings
    llm_base_url: str = "http://192.168.0.21:30000/v1"
    llm_model: str = "Qwen/Qwen3-VL-4B-Instruct"
    llm_temperature: float = 0.001
    llm_top_p: float = 0.6  # RVAgentConfig default, range [0.0, 1.0]
    llm_top_k: int = 50  # RVAgentConfig default, range [1, 100]

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

    Returns:
        Dictionary with run results and metrics path
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"RUN {run_number}/{total_runs}")
    logger.info(f"App: {app_package}")
    logger.info(f"Mode: {mode}")
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

    # Create metrics collector
    collector = MultimodalMetricsCollector(
        app_package=app_package,
        agent_mode=mode,
        timeout_seconds=config.timeout_seconds,
        seed=seed,
        total_activities=0,  # Will be updated if static data available
        output_dir=output_dir,
    )

    # Create agent config
    agent_config = RVAgentConfig(
        package_name=app_package,
        device_id=config.device_serial,
        timeout=config.timeout_seconds,
        agent_mode=mode,
        llm_base_url=config.llm_base_url,
        llm_model=config.llm_model,
        llm_temperature=config.llm_temperature,
        screenshot_dir=str(output_dir / "screenshots" / f"{app_package}_{mode}_seed{seed}"),
    )

    # Override LLM params if set
    if hasattr(agent_config, 'llm_top_p'):
        agent_config.llm_top_p = config.llm_top_p
    if hasattr(agent_config, 'llm_top_k'):
        agent_config.llm_top_k = config.llm_top_k

    start_time = time.time()
    result = {
        "app_package": app_package,
        "mode": mode,
        "seed": seed,
        "wtg_variant": wtg_variant,  # "with_wtg", "without_wtg", or None
        "wtg_enabled": static_data is not None,
        "status": "unknown",
        "error": None,
        "metrics_path": None,
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

        logger.info(f"Agent completed: {result['iterations']} iterations, {result['unique_states']} states")

    except Exception as e:
        logger.error(f"Experiment failed: {e}")
        logger.error(traceback.format_exc())
        result["status"] = "error"
        result["error"] = str(e)

    # Finalize collector (saves metrics)
    try:
        session = collector.finalize()
        # Include WTG variant in filename if present
        wtg_suffix = f"_{wtg_variant}" if wtg_variant else ""
        result["metrics_path"] = str(output_dir / f"multimodal_metrics_{app_package}_{mode}{wtg_suffix}_seed{seed}.json")
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
        apk_mapping = discover_apks(apks_path)
        logger.info(f"Discovered {len(apk_mapping)} APKs in {config.apks_dir}")

        # If no app_packages specified, use all discovered APKs
        if not config.app_packages:
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
        len(config.seeds) *
        len(wtg_variants)
    )

    logger.info("=" * 60)
    logger.info("MULTIMODAL VALIDATION")
    logger.info("=" * 60)
    logger.info(f"Apps: {len(config.app_packages)} - {config.app_packages}")
    logger.info(f"APKs available: {len(apk_mapping)}")
    logger.info(f"Modes: {config.agent_modes}")
    logger.info(f"Seeds: {config.seeds}")
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
            for seed in config.seeds:
                for wtg_variant in wtg_variants:
                    run_number += 1

                    # Determine static_data for this run
                    static_data = None
                    if wtg_variant == "with_wtg":
                        static_data = static_data_cache.get(app_package)
                    # "without_wtg" or None: static_data remains None

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
    from multimodal.analyzer import MultimodalAnalyzer

    analyzer = MultimodalAnalyzer()
    count = analyzer.load_sessions(results_dir)

    if count == 0:
        logger.error(f"No metrics found in {results_dir}")
        return

    analyzer.print_summary()

    if output_path:
        analyzer.generate_report(output_path)


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
            # Allow command-line overrides for WTG options
            if args.use_wtg:
                config.use_wtg = True
            if args.compare_wtg:
                config.compare_wtg = True
            if args.static_data_dir:
                config.static_data_dir = args.static_data_dir
        else:
            config = MultimodalValidationConfig(
                app_packages=args.apps.split(",") if args.apps else [],
                apks_dir=args.apks_dir or "",
                agent_modes=args.modes.split(","),
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
