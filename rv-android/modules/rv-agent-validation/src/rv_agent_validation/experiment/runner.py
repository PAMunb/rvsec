#!/usr/bin/env python3
"""
Unified experiment runner for rv-agent validation.

Combines all functionality:
- Checkpoint/resume capability
- Logcat capture for method coverage
- Coverage calculation from .methods files
- Multiple agent modes and strategies
- CLI interface

Usage:
    poetry run python -m rv_agent_validation.experiment.runner run --help
    poetry run python -m rv_agent_validation.experiment.runner run --apks-dir ./apks --timeout 300
"""

import argparse
import json
import logging
import random
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from .config import ExperimentConfig, RunConfig
from .checkpoint import CheckpointManager
from .seed_manager import SeedManager

logger = logging.getLogger(__name__)

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


def _setup_imports():
    """Setup module imports with proper paths."""
    _base = Path(__file__).parent.parent.parent.parent.parent
    _modules = _base.parent

    paths_to_add = [
        _modules / "rv-agent" / "src",
        _modules / "rv-static-analysis" / "src",
        _modules / "rv-android-core" / "src",
        _modules / "rv-agent-validation" / "src",
    ]

    for path in paths_to_add:
        if path.exists() and str(path) not in sys.path:
            sys.path.insert(0, str(path))


_setup_imports()

# Import after path setup
try:
    from rv_agent.config.agent_config import RVAgentConfig
    from rv_agent.agent.agent_factory import AgentFactory
    from rv_android_core.domain.app import App
    from rv_android_core.domain.static import StaticAnalysisData
    from rv_android_core.util.android.logcat_manager import LogcatManager
    RVAGENT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"rv-agent imports not available: {e}")
    RVAGENT_AVAILABLE = False
    App = None
    StaticAnalysisData = None
    LogcatManager = None

# Coverage tracking
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

# Static analysis parser
try:
    from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser
    STATIC_ANALYSIS_AVAILABLE = True
except ImportError:
    STATIC_ANALYSIS_AVAILABLE = False
    StaticAnalysisParser = None

# Metrics collector
try:
    from rv_agent_validation.multimodal.collector import MultimodalMetricsCollector
    METRICS_COLLECTOR_AVAILABLE = True
except ImportError:
    METRICS_COLLECTOR_AVAILABLE = False
    MultimodalMetricsCollector = None

# Calibration metrics (optional)
try:
    from rv_agent_validation.calibration import CalibrationMetricsCollector
    CALIBRATION_AVAILABLE = True
except ImportError:
    CALIBRATION_AVAILABLE = False
    CalibrationMetricsCollector = None


def is_infrastructure_error(error_msg: str) -> bool:
    """Check if error is infrastructure-related (should retry)."""
    error_lower = error_msg.lower()
    return any(e.lower() in error_lower for e in INFRASTRUCTURE_ERRORS)


def get_package_from_apk(apk_path: Path) -> Optional[str]:
    """Extract package name from APK using androguard."""
    if App is None:
        return None
    try:
        app = App(app_path=str(apk_path), validate_on_init=True)
        return app.package_name
    except Exception as e:
        logger.warning(f"Failed to get package from APK {apk_path.name}: {e}")
    return None


def install_apk(apk_path: Path, device_serial: str = "emulator-5554") -> bool:
    """Install APK on device."""
    logger.info(f"Installing APK: {apk_path.name}")
    try:
        result = subprocess.run(
            ["adb", "-s", device_serial, "install", "-r", "-g", str(apk_path)],
            capture_output=True, text=True, timeout=120
        )
        if "Success" in result.stdout:
            logger.info("APK installed successfully")
            return True
        else:
            logger.error(f"APK installation failed: {result.stdout} {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        logger.error("APK installation timed out")
        return False
    except Exception as e:
        logger.error(f"APK installation error: {e}")
        return False


def uninstall_apk(package_name: str, device_serial: str = "emulator-5554") -> bool:
    """Uninstall app from device."""
    logger.info(f"Uninstalling: {package_name}")
    try:
        result = subprocess.run(
            ["adb", "-s", device_serial, "uninstall", package_name],
            capture_output=True, text=True, timeout=60
        )
        return "Success" in result.stdout
    except Exception as e:
        logger.warning(f"Uninstall error: {e}")
        return False


def clear_app_data(package_name: str, device_serial: str = "emulator-5554"):
    """Clear app data before run."""
    try:
        subprocess.run(
            ["adb", "-s", device_serial, "shell", "pm", "clear", package_name],
            check=True, capture_output=True, timeout=30
        )
        time.sleep(1)
    except Exception as e:
        logger.warning(f"Failed to clear app data: {e}")


def load_static_data(apk_path: Path, package_name: str) -> Optional["StaticAnalysisData"]:
    """Load static analysis data from APK directory if available."""
    if not STATIC_ANALYSIS_AVAILABLE or not StaticAnalysisParser:
        return None

    try:
        apk_dir = apk_path.parent
        wtg_file = apk_dir / f"{apk_path.name}.wtg"
        gesda_file = apk_dir / f"{apk_path.name}.gesda"
        reach_file = apk_dir / f"{apk_path.name}.reach"

        if not (wtg_file.exists() and gesda_file.exists() and reach_file.exists()):
            return None

        parser = StaticAnalysisParser()
        static_data = parser.parse(
            reach_file=str(reach_file),
            gator_file=str(wtg_file),
            gesda_file=str(gesda_file),
            package=package_name,
        )
        logger.info(f"Loaded static analysis for {package_name}")
        return static_data
    except Exception as e:
        logger.warning(f"Failed to load static analysis: {e}")
        return None


class ExperimentRunner:
    """
    Unified experiment runner with checkpoint, logcat, and coverage support.
    """

    def __init__(self, config: ExperimentConfig, base_dir: Optional[Path] = None):
        """
        Initialize experiment runner.

        Args:
            config: Experiment configuration.
            base_dir: Base directory for results.
        """
        self.config = config

        # Setup directories
        if base_dir is None:
            base_dir = Path(__file__).parent.parent.parent.parent / "results"

        self.experiment_dir = base_dir / config.experiment_id
        self.runs_dir = self.experiment_dir / "runs"
        self.logcat_dir = self.experiment_dir / "logcat"
        self.reports_dir = self.experiment_dir / "reports"

        for d in [self.runs_dir, self.logcat_dir, self.reports_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # Initialize checkpoint manager
        self.checkpoint = CheckpointManager(self.experiment_dir / "checkpoint.json")

        # Initialize calibration collector if available
        self.calibration_collector = None
        if CALIBRATION_AVAILABLE:
            self.calibration_collector = CalibrationMetricsCollector()

        # Setup logging
        self._setup_logging()

        logger.info(f"ExperimentRunner initialized")
        logger.info(f"Experiment: {config.experiment_id}")
        logger.info(f"Total runs: {config.total_runs}")
        logger.info(f"Estimated time: {config.estimated_time_hours:.1f} hours")

    def _setup_logging(self):
        """Setup file logging for the experiment."""
        log_file = self.experiment_dir / "experiment.log"

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        logging.getLogger().addHandler(file_handler)

    def run_experiment(self, resume: bool = True) -> Dict[str, Any]:
        """
        Execute the full experiment.

        Args:
            resume: Whether to resume from checkpoint.

        Returns:
            Experiment results summary.
        """
        logger.info("=" * 60)
        logger.info("STARTING EXPERIMENT")
        logger.info("=" * 60)

        # Save config
        self._save_config()

        # Build app info cache
        logger.info("Loading APK information...")
        app_info_cache = {}
        for apk_path in self.config.apk_paths:
            try:
                path = Path(apk_path)
                package_name = get_package_from_apk(path)
                if package_name:
                    app_info_cache[apk_path] = package_name
                    logger.info(f"  {path.name} -> {package_name}")
            except Exception as e:
                logger.error(f"Failed to load APK {apk_path}: {e}")
                raise

        # Generate all runs
        all_runs = self.config.generate_runs(app_info_cache)

        # Randomize order
        random.seed(self.config.base_seed)
        random.shuffle(all_runs)

        # Get pending runs
        if resume:
            pending_runs = self.checkpoint.get_pending_runs(all_runs)
        else:
            self.checkpoint.reset()
            pending_runs = all_runs

        self.checkpoint.start_experiment()
        logger.info(f"Pending runs: {len(pending_runs)} of {len(all_runs)}")

        # Track installed app
        current_installed_package: Optional[str] = None

        # Execute runs
        for i, run in enumerate(pending_runs):
            progress = self.checkpoint.get_progress(len(all_runs))
            logger.info("-" * 40)
            logger.info(f"Run {progress['completed'] + 1}/{progress['total']}: {run.run_id}")
            logger.info(f"Progress: {progress['progress_percent']:.1f}%")

            try:
                # Install app if different
                if current_installed_package != run.package_name:
                    if current_installed_package:
                        uninstall_apk(current_installed_package, self.config.device_serial)

                    apk_path = Path(run.apk_path)
                    if not install_apk(apk_path, self.config.device_serial):
                        raise RuntimeError(f"Failed to install {run.apk_path}")
                    current_installed_package = run.package_name
                    time.sleep(2)

                # Execute run with retry
                result = self._execute_run_with_retry(run)
                self._save_run_result(run, result)
                self.checkpoint.mark_completed(run)

                logger.info(f"Completed: {run.run_id}")
                logger.info(f"  States: {result.get('states_discovered', 0)}")
                logger.info(f"  Actions: {result.get('total_actions', 0)}")
                if result.get('coverage_metrics'):
                    cov = result['coverage_metrics']
                    logger.info(f"  Method Coverage: {cov.get('method_coverage', 0):.1f}%")

            except Exception as e:
                logger.error(f"Failed: {run.run_id} - {e}", exc_info=True)
                self.checkpoint.mark_failed(run, str(e))
                self._save_run_result(run, {"status": "failed", "error": str(e)})

        # Cleanup
        if current_installed_package:
            uninstall_apk(current_installed_package, self.config.device_serial)

        # Generate reports
        if self.calibration_collector:
            report_path = self.reports_dir / "calibration_report.txt"
            self.calibration_collector.save_report(str(report_path))

        # Final summary
        progress = self.checkpoint.get_progress(len(all_runs))
        logger.info("=" * 60)
        logger.info("EXPERIMENT COMPLETED")
        logger.info(f"Completed: {progress['completed']}/{progress['total']}")
        logger.info(f"Failed: {progress['failed']}")
        logger.info("=" * 60)

        return progress

    def _execute_run_with_retry(self, run: RunConfig) -> Dict[str, Any]:
        """Execute a run with automatic retry for infrastructure errors."""
        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                result = self._execute_run(run)

                if result.get("status") not in ("error", "failed"):
                    return result

                error_msg = str(result.get("error", ""))
                if is_infrastructure_error(error_msg):
                    logger.warning(f"Infrastructure error (attempt {attempt + 1}/{MAX_RETRIES}): {error_msg}")
                    last_error = error_msg
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY_SECONDS)
                        continue
                else:
                    return result

            except Exception as e:
                error_msg = str(e)
                if is_infrastructure_error(error_msg):
                    logger.warning(f"Infrastructure exception (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                    last_error = error_msg
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY_SECONDS)
                        continue
                else:
                    raise

        return {
            "status": "failed",
            "error": f"All retries exhausted: {last_error}",
            "retries_attempted": MAX_RETRIES,
        }

    def _execute_run(self, run: RunConfig) -> Dict[str, Any]:
        """Execute a single run with logcat capture and coverage calculation."""
        logger.info(f"Executing: package={run.package_name}, strategy={run.strategy}, rep={run.repetition}")

        random.seed(run.seed)
        clear_app_data(run.package_name, self.config.device_serial)

        # Load static analysis if available
        apk_path = Path(run.apk_path)
        static_data = None
        if self.config.enable_static_analysis:
            static_data = load_static_data(apk_path, run.package_name)

        # Setup logcat capture
        logcat_manager = None
        logcat_file = None
        methods_file = None

        if LogcatManager:
            try:
                logcat_file = self.logcat_dir / f"logcat_{run.run_id}.txt"
                logcat_manager = LogcatManager(device_serial=self.config.device_serial)
                logcat_manager.start_capture(str(logcat_file), clear_buffer=True)
                logger.info(f"Started logcat capture: {logcat_file.name}")

                # Find .methods file
                potential_methods = apk_path.parent / f"{apk_path.name}.methods"
                if potential_methods.exists():
                    methods_file = potential_methods
                    logger.info(f"Found methods file: {methods_file.name}")
            except Exception as e:
                logger.warning(f"Failed to setup logcat: {e}")
                logcat_manager = None

        # Create metrics collector
        collector = None
        if METRICS_COLLECTOR_AVAILABLE and MultimodalMetricsCollector:
            total_activities = 0
            if static_data and static_data.classes:
                total_activities = sum(1 for c in static_data.classes.classes.values() if c.is_activity)

            collector = MultimodalMetricsCollector(
                app_package=run.package_name,
                agent_mode=self.config.agent_mode,
                timeout_seconds=self.config.timeout_seconds,
                seed=run.seed,
                total_activities=total_activities,
                output_dir=self.runs_dir,
                strategy=run.strategy,
            )

        # Create agent config
        agent_config = RVAgentConfig(
            package_name=run.package_name,
            agent_mode=self.config.agent_mode,
            strategy=run.strategy,
            timeout=self.config.timeout_seconds,
            device_id=self.config.device_serial,
            results_dir=str(self.runs_dir),
        )

        # Execute agent
        start_time = time.time()
        result = {
            "run_id": run.run_id,
            "apk_path": run.apk_path,
            "package_name": run.package_name,
            "strategy": run.strategy,
            "repetition": run.repetition,
            "seed": run.seed,
            "status": "unknown",
            "error": None,
            "logcat_file": str(logcat_file) if logcat_file else None,
            "coverage_metrics": None,
        }

        try:
            agent = AgentFactory.create_agent(
                config=agent_config,
                static_data=static_data,
                metrics_collector=collector,
            )

            agent_result = agent.run()
            end_time = time.time()

            result["status"] = agent_result.get("status", "completed")
            result["execution_time_seconds"] = round(end_time - start_time, 2)
            result["states_discovered"] = agent_result.get("unique_states", 0)
            result["total_actions"] = agent_result.get("total_actions", 0)
            result["iterations"] = agent_result.get("iterations", 0)

            # Extract metrics from agent
            metrics = self._extract_agent_metrics(agent, agent_result, start_time, end_time)
            result.update(metrics)

            # Capture UI coverage from agent
            ui_coverage = agent_result.get("ui_coverage", {})
            if ui_coverage:
                result["ui_coverage"] = ui_coverage
                if collector:
                    collector.set_ui_coverage_from_agent(ui_coverage)

            # Collect calibration metrics
            if self.calibration_collector:
                self.calibration_collector.extract_metrics(
                    agent=agent,
                    run_id=run.run_id,
                    package_name=run.package_name,
                    seed=run.seed,
                    execution_time=end_time - start_time
                )

        except Exception as e:
            end_time = time.time()
            logger.error(f"Run failed: {e}", exc_info=True)
            result["status"] = "error"
            result["error"] = str(e)
            result["execution_time_seconds"] = round(end_time - start_time, 2)

        # Stop logcat and calculate coverage
        if logcat_manager:
            try:
                logcat_manager.stop_capture()
                logger.info("Stopped logcat capture")
            except Exception as e:
                logger.warning(f"Failed to stop logcat: {e}")

        # Calculate coverage from logcat
        if COVERAGE_AVAILABLE and logcat_file and logcat_file.exists():
            try:
                logcat_parser = LogcatCoverageParser()
                cov_entries, err_entries = logcat_parser.parse_file(logcat_file)
                logger.info(f"Parsed logcat: {len(cov_entries)} coverage, {len(err_entries)} errors")

                if methods_file and methods_file.exists():
                    methods_parser = MethodsParser(methods_file)
                    tracker = CoverageTracker(methods_parser)
                    tracker.process_coverage(cov_entries)
                    tracker.process_errors(err_entries)
                    coverage_result = tracker.get_result()

                    coverage_metrics = coverage_result.to_dict()
                    result["coverage_metrics"] = coverage_metrics

                    if collector:
                        collector.set_coverage_metrics(coverage_metrics)

                    logger.info(
                        f"Coverage: method={coverage_result.method_coverage:.1f}%, "
                        f"reaches_mop={coverage_result.reaches_mop_coverage:.1f}%, "
                        f"errors={coverage_result.unique_errors}"
                    )
                else:
                    result["coverage_metrics"] = {
                        "unique_errors": len(err_entries),
                        "total_errors": len(err_entries),
                    }
            except Exception as e:
                logger.warning(f"Failed to calculate coverage: {e}")

        # Finalize collector
        if collector:
            try:
                collector.finalize()
            except Exception as e:
                logger.warning(f"Failed to finalize collector: {e}")

        return result

    def _extract_agent_metrics(
        self,
        agent,
        result: Dict[str, Any],
        start_time: float,
        end_time: float
    ) -> Dict[str, Any]:
        """Extract detailed metrics from agent execution."""
        execution_time = end_time - start_time

        # Get graph metrics
        graph = agent.dynamic_graph
        graph_report = graph.get_transition_graph_report()
        states_discovered = graph_report["total_states"]
        transitions_count = graph_report["total_transitions"]

        # Get UI coverage
        memory = agent.memory_coordinator
        ui_coverage = memory.ui_coverage

        ui_coverage_pct = 0.0
        ui_coverage_stats = {}
        if ui_coverage:
            try:
                ui_coverage_stats = ui_coverage.get_comprehensive_metrics()
                ui_coverage_pct = ui_coverage_stats.get("element_coverage", 0.0)
            except Exception:
                pass

        metrics = {
            "states_discovered": states_discovered,
            "transitions_count": transitions_count,
            "total_actions": result.get("total_actions", 0),
            "valid_actions": result.get("valid_actions", 0),
            "invalid_actions": result.get("invalid_actions", 0),
            "actions_per_minute": 0.0,
            "ui_coverage_percentage": ui_coverage_pct,
            "ui_total_elements": ui_coverage_stats.get("total_unique_elements", 0),
            "ui_total_interactions": ui_coverage_stats.get("total_interactions", 0),
            "ui_elements_by_type": ui_coverage_stats.get("elements_by_type", {}),
            "ui_interactions_by_type": ui_coverage_stats.get("interactions_by_type", {}),
            "start_time": datetime.fromtimestamp(start_time).isoformat(),
            "end_time": datetime.fromtimestamp(end_time).isoformat(),
        }

        total = metrics["total_actions"]
        if total > 0 and execution_time > 0:
            metrics["actions_per_minute"] = round(total / (execution_time / 60), 2)

        return metrics

    def _save_config(self):
        """Save experiment configuration."""
        config_file = self.experiment_dir / "config.json"
        with open(config_file, 'w') as f:
            json.dump(self.config.to_dict(), f, indent=2)

    def _save_run_result(self, run: RunConfig, result: Dict[str, Any]):
        """Save individual run result."""
        result_file = self.runs_dir / f"{run.run_id}.json"
        with open(result_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)


def main():
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    parser = argparse.ArgumentParser(description="RV-Agent Validation Runner")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run validation experiment")
    run_parser.add_argument("--config", type=Path, help="Path to config JSON file")
    run_parser.add_argument("--apks-dir", type=str, help="Directory containing APKs")
    run_parser.add_argument("--apks", type=str, help="Comma-separated APK paths")
    run_parser.add_argument("--strategies", type=str, default="rvagent",
                          help="Comma-separated strategies (default: rvagent)")
    run_parser.add_argument("--mode", type=str, default="pure_algorithm",
                          help="Agent mode (pure_algorithm, llm_only, multimode)")
    run_parser.add_argument("--timeout", type=int, default=300, help="Timeout per run (seconds)")
    run_parser.add_argument("--repetitions", type=int, default=3, help="Repetitions per config")
    run_parser.add_argument("--seed", type=int, default=42, help="Base random seed")
    run_parser.add_argument("--output", type=str, default="results", help="Output directory")
    run_parser.add_argument("--device", type=str, default="emulator-5554", help="Device serial")
    run_parser.add_argument("--no-resume", action="store_true", help="Don't resume from checkpoint")
    run_parser.add_argument("--no-static", action="store_true", help="Disable static analysis")
    run_parser.add_argument("--name", type=str, help="Experiment name")

    args = parser.parse_args()

    if args.command == "run":
        # Build config
        if args.config:
            with open(args.config) as f:
                data = json.load(f)
            config = ExperimentConfig.from_dict(data)
        else:
            # Discover APKs
            apk_paths = []
            if args.apks_dir:
                apks_dir = Path(args.apks_dir)
                for apk in apks_dir.glob("**/*.apk"):
                    if apk.is_file():
                        apk_paths.append(str(apk.resolve()))
            elif args.apks:
                apk_paths = [p.strip() for p in args.apks.split(",")]

            if not apk_paths:
                logger.error("No APKs specified. Use --apks-dir or --apks")
                sys.exit(1)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name = args.name or "validation"

            config = ExperimentConfig(
                experiment_id=f"{name}_{timestamp}",
                experiment_name=args.name or "Validation Experiment",
                apk_paths=apk_paths,
                strategies=args.strategies.split(","),
                repetitions=args.repetitions,
                timeout_seconds=args.timeout,
                agent_mode=args.mode,
                base_seed=args.seed,
                results_dir=Path(args.output),
                device_serial=args.device,
                enable_static_analysis=not args.no_static,
            )

        # Run experiment
        runner = ExperimentRunner(config, base_dir=Path(args.output))
        runner.run_experiment(resume=not args.no_resume)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
