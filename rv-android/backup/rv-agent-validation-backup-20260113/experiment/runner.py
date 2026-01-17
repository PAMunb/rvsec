"""
Experiment runner for strategy validation.

Orchestrates execution of all experiment runs with checkpointing,
metrics collection, and progress tracking.

Supports:
- Static analysis integration for MOP prioritization metrics
- Extended metrics for action selection analysis
- Composite scoring for strategy comparison
"""

import json
import logging
import random
import subprocess
import time
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add paths for imports
# runner.py is at: modules/rv-agent/validation/experiment/runner.py
# So parent.parent.parent.parent = modules/
_modules_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))  # rv-agent/src
sys.path.insert(0, str(_modules_dir / "rv-static-analysis" / "src"))  # rv-static-analysis/src
sys.path.insert(0, str(_modules_dir / "rv-android-core" / "src"))  # rv-android-core/src

from rv_android_core.domain.app import App
from rv_android_core.domain.static import StaticAnalysisData

from .config import (
    ExperimentConfig,
    RunConfig,
    APPS_WITH_STATIC_ANALYSIS,
    get_apps_with_static_analysis,
)
from .checkpoint import CheckpointManager

logger = logging.getLogger(__name__)


class ExperimentRunner:
    """
    Orchestrates validation experiment execution.

    Handles:
    - Run execution with proper agent configuration
    - Metrics collection and result storage
    - Checkpointing for resume capability
    - Progress logging
    """

    def __init__(
        self,
        config: ExperimentConfig,
        base_dir: Optional[Path] = None
    ):
        """
        Initialize experiment runner.

        Args:
            config: Experiment configuration.
            base_dir: Base directory for results (default: validation/results).
        """
        self.config = config

        # Setup directories
        if base_dir is None:
            base_dir = Path(__file__).parent.parent / "results"

        self.experiment_dir = base_dir / config.experiment_id
        self.runs_dir = self.experiment_dir / "runs"
        self.reports_dir = self.experiment_dir / "reports"

        # Create directories
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # Initialize checkpoint manager
        self.checkpoint = CheckpointManager(
            self.experiment_dir / "checkpoint.json"
        )

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

        # Add to root logger
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

        # Build app info cache (apk_path -> package_name)
        logger.info("Loading APK information...")
        app_info_cache = {}
        for apk_path in self.config.apk_paths:
            try:
                app = self._get_app_info(apk_path)
                app_info_cache[apk_path] = app.package_name
                logger.info(f"  {apk_path} -> {app.package_name}")
            except Exception as e:
                logger.error(f"Failed to load APK {apk_path}: {e}")
                raise

        # Generate all runs with package names
        all_runs = self.config.generate_runs(app_info_cache)

        # Randomize order to avoid bias
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

        # Track currently installed app
        current_installed_package: Optional[str] = None

        # Execute runs
        for i, run in enumerate(pending_runs):
            progress = self.checkpoint.get_progress(len(all_runs))
            logger.info("-" * 40)
            logger.info(f"Run {progress['completed'] + 1}/{progress['total']}: {run.run_id}")
            logger.info(f"Progress: {progress['progress_percent']:.1f}%")

            try:
                # Install app if different from current
                if current_installed_package != run.package_name:
                    # Uninstall previous app
                    if current_installed_package:
                        logger.info(f"Uninstalling previous app: {current_installed_package}")
                        self._uninstall_app(current_installed_package)

                    # Install new app
                    logger.info(f"Installing: {run.apk_path}")
                    if not self._install_app(run.apk_path):
                        raise RuntimeError(f"Failed to install {run.apk_path}")
                    current_installed_package = run.package_name

                # Execute run
                result = self._execute_run(run)
                self._save_run_result(run, result)
                self.checkpoint.mark_completed(run)

                logger.info(f"Completed: {run.run_id}")
                logger.info(f"  States: {result.get('states_discovered', 0)}")
                logger.info(f"  Actions: {result.get('total_actions', 0)}")

            except Exception as e:
                logger.error(f"Failed: {run.run_id} - {e}", exc_info=True)
                self.checkpoint.mark_failed(run, str(e))
                self._save_run_result(run, {
                    "status": "failed",
                    "error": str(e)
                })

        # Cleanup: uninstall last app
        if current_installed_package:
            logger.info(f"Cleanup: uninstalling {current_installed_package}")
            self._uninstall_app(current_installed_package)

        # Final summary
        progress = self.checkpoint.get_progress(len(all_runs))
        logger.info("=" * 60)
        logger.info("EXPERIMENT COMPLETED")
        logger.info(f"Completed: {progress['completed']}/{progress['total']}")
        logger.info(f"Failed: {progress['failed']}")
        logger.info("=" * 60)

        return progress

    def _load_static_analysis(self, apk_path: str, package_name: str) -> Optional[StaticAnalysisData]:
        """
        Load static analysis data for an APK if available.

        Args:
            apk_path: Path to APK file.
            package_name: Package name of the app.

        Returns:
            StaticAnalysisData if available, None otherwise.
        """
        if not self.config.enable_static_analysis:
            return None

        try:
            from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser

            # Find app info from config
            apk_name = Path(apk_path).name
            app_info = None

            for app in APPS_WITH_STATIC_ANALYSIS:
                if app["name"] == apk_name or app["package"] == package_name:
                    app_info = app
                    break

            if not app_info:
                logger.debug(f"No static analysis config for {apk_name}")
                return None

            # Build paths to static files
            static_dir = self.config.static_analysis_dir / app_info["dir"]

            reach_files = list(static_dir.glob("*.reach"))
            wtg_files = list(static_dir.glob("*.wtg"))
            gesda_files = list(static_dir.glob("*.gesda"))

            if not (reach_files and wtg_files and gesda_files):
                logger.debug(f"Missing static files in {static_dir}")
                return None

            # Parse static analysis
            parser = StaticAnalysisParser()
            static_data = parser.parse(
                reach_file=str(reach_files[0]),
                gator_file=str(wtg_files[0]),
                gesda_file=str(gesda_files[0]),
                package=package_name,
            )

            logger.info(f"Loaded static analysis for {package_name}")
            return static_data

        except ImportError:
            logger.warning("rv_static_analysis not available")
            return None
        except Exception as e:
            logger.warning(f"Failed to load static analysis: {e}")
            return None

    def _execute_run(self, run: RunConfig) -> Dict[str, Any]:
        """
        Execute a single run.

        Args:
            run: Run configuration.

        Returns:
            Run results with metrics.
        """
        from rv_agent.config.agent_config import RVAgentConfig
        from rv_agent.agent.agent_factory import AgentFactory

        logger.info(f"Executing: package={run.package_name}, strategy={run.strategy}, rep={run.repetition}")
        logger.info(f"Seed: {run.seed}")

        # Set random seed for reproducibility
        random.seed(run.seed)

        # Clear app data before run
        self._clear_app_data(run.package_name)

        # Load static analysis data if enabled
        static_data = self._load_static_analysis(run.apk_path, run.package_name)

        # Create agent config
        agent_config = RVAgentConfig(
            package_name=run.package_name,
            agent_mode=self.config.agent_mode,
            strategy=run.strategy,
            timeout=self.config.timeout_seconds,
            device_id=self.config.device_serial,
            results_dir=str(self.runs_dir),
        )

        # Create and run agent
        start_time = time.time()

        try:
            agent = AgentFactory.create_agent(
                config=agent_config,
                static_data=static_data,
            )

            result = agent.run()
            end_time = time.time()

            # Extract metrics (extended with MOP and action selection)
            metrics = self._extract_metrics(agent, result, start_time, end_time)
            metrics["status"] = "completed"
            metrics["run_id"] = run.run_id
            metrics["apk_path"] = run.apk_path
            metrics["package_name"] = run.package_name
            metrics["strategy"] = run.strategy
            metrics["repetition"] = run.repetition
            metrics["seed"] = run.seed
            metrics["static_analysis_enabled"] = static_data is not None

            return metrics

        except Exception as e:
            end_time = time.time()
            logger.error(f"Run failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "run_id": run.run_id,
                "apk_path": run.apk_path,
                "package_name": run.package_name,
                "strategy": run.strategy,
                "repetition": run.repetition,
                "seed": run.seed,
                "execution_time_seconds": end_time - start_time,
                "static_analysis_enabled": static_data is not None if 'static_data' in dir() else False,
            }

    def _extract_metrics(
        self,
        agent,
        result: Dict[str, Any],
        start_time: float,
        end_time: float
    ) -> Dict[str, Any]:
        """
        Extract metrics from agent execution.

        Includes:
        - Base metrics (states, actions, coverage)
        - MOP metrics (MOP selection, methods reached)
        - Action selection metrics (repetition, diversity)
        - Efficiency metrics (states per action)
        - Strategy-specific metrics (successor tracker, plateau)

        Args:
            agent: Executed agent instance.
            result: Agent run result.
            start_time: Run start time.
            end_time: Run end time.

        Returns:
            Comprehensive metrics dictionary.
        """
        execution_time = end_time - start_time

        # Get graph metrics from transition graph report
        graph = agent.dynamic_graph
        graph_report = graph.get_transition_graph_report()
        states_discovered = graph_report["total_states"]
        transitions_count = graph_report["total_transitions"]

        # Get coverage metrics from memory coordinator
        memory = agent.memory_coordinator
        ui_coverage = memory.ui_coverage

        # Get UI coverage percentage safely
        ui_coverage_pct = 0.0
        if ui_coverage:
            try:
                stats = ui_coverage.get_overall_statistics()
                ui_coverage_pct = stats.get("coverage_percentage", 0.0)
            except Exception:
                pass

        # Base metrics
        metrics = {
            "execution_time_seconds": round(execution_time, 2),
            "states_discovered": states_discovered,
            "transitions_count": transitions_count,
            "unique_screens": result.get("unique_screens", states_discovered),
            "total_actions": result.get("total_actions", 0),
            "valid_actions": result.get("valid_actions", 0),
            "invalid_actions": result.get("invalid_actions", 0),
            "action_validity_rate": 0.0,
            "actions_per_minute": 0.0,
            "app_crashes": result.get("app_crashes", 0),
            "ui_coverage_percentage": ui_coverage_pct,
            "actions_by_type": result.get("actions_by_type", {}),
            "start_time": datetime.fromtimestamp(start_time).isoformat(),
            "end_time": datetime.fromtimestamp(end_time).isoformat(),
        }

        # Calculate derived base metrics
        total = metrics["total_actions"]
        valid = metrics["valid_actions"]
        if total > 0:
            metrics["action_validity_rate"] = round(valid / total * 100, 2)
            if execution_time > 0:
                metrics["actions_per_minute"] = round(total / (execution_time / 60), 2)

        # =================================================================
        # MOP METRICS (from plateau detector or strategy)
        # =================================================================
        metrics["mop_methods_reached"] = 0
        metrics["unique_mop_methods"] = 0
        metrics["mop_selection_rate"] = 0.0

        strategy = getattr(agent, 'strategy', None)

        if strategy and hasattr(strategy, 'plateau_detector'):
            try:
                plateau_stats = strategy.plateau_detector.get_statistics()
                metrics["mop_methods_reached"] = plateau_stats.get("total_mop_methods_executed", 0)
                metrics["unique_mop_methods"] = len(plateau_stats.get("unique_mop_methods", set()))
                metrics["plateau_reached"] = plateau_stats.get("plateau_reached", False)
                metrics["plateau_iterations"] = plateau_stats.get("total_iterations", 0)
            except Exception as e:
                logger.debug(f"Could not get plateau stats: {e}")

        # MOP selection from coverage metrics if available
        if strategy and hasattr(strategy, 'coverage_metrics'):
            try:
                coverage_stats = strategy.coverage_metrics.get_summary()
                mop_reached = coverage_stats.get("mop_methods_reached", 0)
                if mop_reached > metrics["mop_methods_reached"]:
                    metrics["mop_methods_reached"] = mop_reached
            except Exception:
                pass

        # Calculate MOP selection rate (from result if available)
        mop_actions = result.get("mop_actions_selected", 0)
        if total > 0 and mop_actions > 0:
            metrics["mop_selection_rate"] = round(mop_actions / total * 100, 2)

        # =================================================================
        # ACTION SELECTION METRICS (from dynamic graph)
        # =================================================================
        metrics["action_repetition_rate"] = 0.0
        metrics["max_action_executions"] = 0
        metrics["unique_actions_executed"] = 0
        metrics["failed_actions_count"] = 0

        try:
            action_stats = self._extract_action_stats(graph)
            metrics.update(action_stats)
        except Exception as e:
            logger.debug(f"Could not extract action stats: {e}")

        # =================================================================
        # EFFICIENCY METRICS
        # =================================================================
        if total > 0:
            metrics["states_per_action"] = round(states_discovered / total, 4)
            metrics["actions_per_state"] = round(total / max(1, states_discovered), 2)
        else:
            metrics["states_per_action"] = 0.0
            metrics["actions_per_state"] = 0.0

        if execution_time > 0:
            metrics["states_per_minute"] = round(states_discovered / (execution_time / 60), 2)
        else:
            metrics["states_per_minute"] = 0.0

        # =================================================================
        # STRATEGY-SPECIFIC METRICS
        # =================================================================

        # Successor tracker (RVAgent strategy)
        metrics["successor_re_enables"] = 0
        if strategy and hasattr(strategy, 'successor_tracker'):
            try:
                tracker_stats = strategy.successor_tracker.get_statistics()
                metrics["successor_re_enables"] = tracker_stats.get("actions_re_enabled", 0)
                metrics["total_successors_tracked"] = tracker_stats.get("total_successors_tracked", 0)
                metrics["incomplete_successors"] = tracker_stats.get("incomplete_successors", 0)
            except Exception as e:
                logger.debug(f"Could not get successor tracker stats: {e}")

        return metrics

    def _extract_action_stats(self, graph) -> Dict[str, Any]:
        """
        Extract action execution statistics from dynamic graph.

        Args:
            graph: DynamicStateGraph instance.

        Returns:
            Action statistics dictionary.
        """
        stats = {
            "action_repetition_rate": 0.0,
            "max_action_executions": 0,
            "unique_actions_executed": 0,
            "failed_actions_count": 0,
        }

        if not hasattr(graph, 'states') or not graph.states:
            return stats

        total_executions = 0
        unique_actions = 0
        max_executions = 0
        failed_count = 0

        for state_hash, state_node in graph.states.items():
            if hasattr(state_node, 'action_execution_counts'):
                for action_sig, count in state_node.action_execution_counts.items():
                    unique_actions += 1
                    total_executions += count
                    if count > max_executions:
                        max_executions = count

            if hasattr(state_node, 'failed_actions'):
                failed_count += len(state_node.failed_actions)

        stats["unique_actions_executed"] = unique_actions
        stats["max_action_executions"] = max_executions
        stats["failed_actions_count"] = failed_count

        # Repetition rate: (total executions - unique) / total
        if total_executions > 0 and unique_actions > 0:
            repetitions = total_executions - unique_actions
            stats["action_repetition_rate"] = round(repetitions / total_executions * 100, 2)

        return stats

    def _clear_app_data(self, package_name: str):
        """Clear app data before run."""
        try:
            subprocess.run(
                ["adb", "-s", self.config.device_serial, "shell",
                 "pm", "clear", package_name],
                check=True,
                capture_output=True,
                timeout=30
            )
            logger.debug(f"Cleared data for {package_name}")
            time.sleep(1)
        except Exception as e:
            logger.warning(f"Failed to clear app data: {e}")

    def _install_app(self, apk_path: str) -> bool:
        """
        Install APK with permissions granted (-g flag).

        Args:
            apk_path: Path to APK file.

        Returns:
            True if installation successful.
        """
        try:
            result = subprocess.run(
                ["adb", "-s", self.config.device_serial, "install", "-g", apk_path],
                capture_output=True,
                text=True,
                timeout=120
            )
            if "Success" in result.stdout:
                logger.info(f"Installed APK: {apk_path}")
                time.sleep(2)  # Wait for app to be ready
                return True
            else:
                logger.error(f"Failed to install APK: {result.stdout} {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error installing APK: {e}")
            return False

    def _uninstall_app(self, package_name: str) -> bool:
        """
        Uninstall app from device.

        Args:
            package_name: Package name to uninstall.

        Returns:
            True if uninstallation successful.
        """
        try:
            result = subprocess.run(
                ["adb", "-s", self.config.device_serial, "uninstall", package_name],
                capture_output=True,
                text=True,
                timeout=60
            )
            if "Success" in result.stdout:
                logger.info(f"Uninstalled: {package_name}")
                return True
            else:
                logger.warning(f"Uninstall result: {result.stdout}")
                return False
        except Exception as e:
            logger.warning(f"Error uninstalling app: {e}")
            return False

    def _get_app_info(self, apk_path: str) -> App:
        """
        Get app info from APK using Androguard.

        Args:
            apk_path: Path to APK file.

        Returns:
            App instance with package info.
        """
        return App(app_path=apk_path)

    def _save_config(self):
        """Save experiment configuration."""
        config_file = self.experiment_dir / "config.json"
        with open(config_file, 'w') as f:
            json.dump(self.config.to_dict(), f, indent=2)
        logger.info(f"Saved config to {config_file}")

    def _save_run_result(self, run: RunConfig, result: Dict[str, Any]):
        """Save individual run result."""
        result_file = self.runs_dir / f"{run.run_id}.json"
        with open(result_file, 'w') as f:
            json.dump(result, f, indent=2)
        logger.debug(f"Saved result to {result_file}")

    def run_single(
        self,
        apk_path: str,
        strategy: str,
        repetition: int = 1
    ) -> Dict[str, Any]:
        """
        Run a single configuration for testing.

        Args:
            apk_path: Path to APK file.
            strategy: Strategy name.
            repetition: Repetition number.

        Returns:
            Run result.
        """
        from .seed_manager import SeedManager

        # Get package name from APK
        app = self._get_app_info(apk_path)
        package_name = app.package_name

        # Install app
        logger.info(f"Installing: {apk_path}")
        if not self._install_app(apk_path):
            raise RuntimeError(f"Failed to install {apk_path}")

        seed_manager = SeedManager(self.config.base_seed)
        seed = seed_manager.get_seed(apk_path, strategy, repetition)

        run = RunConfig(
            apk_path=apk_path,
            package_name=package_name,
            strategy=strategy,
            repetition=repetition,
            seed=seed
        )

        try:
            result = self._execute_run(run)
        finally:
            # Cleanup: uninstall app
            logger.info(f"Cleanup: uninstalling {package_name}")
            self._uninstall_app(package_name)

        return result
