"""
Calibration trial runner.

Executes calibration trials via rv-experiment subprocess.
"""

import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List

from .parameter_space import params_to_tool_spec
from .objective import ObjectiveFunction

logger = logging.getLogger(__name__)


class CalibrationRunner:
    """
    Runs calibration trials via rv-experiment.

    Each trial:
    1. Receives parameter suggestions from Optuna
    2. Constructs tool specification DSL
    3. Runs rv-experiment with skip flags (no preprocessing)
    4. Parses results and computes objective score

    Note: The dataset_dir should contain only the APKs intended for calibration.
    Use separate directories for calibration vs hold-out validation sets.
    """

    def __init__(
        self,
        dataset_dir: str,
        objective_fn: ObjectiveFunction,
        output_base_dir: str = "./calibration",
        timeout: int = 300,
        agent_mode: str = "pure_algorithm",
        seed: Optional[int] = None
    ):
        """
        Initialize calibration runner.

        Args:
            dataset_dir: Path to pre-instrumented APKs dataset (should contain
                         only the APKs to be used in calibration)
            objective_fn: Objective function for scoring
            output_base_dir: Base directory for trial outputs
            timeout: Timeout per APK in seconds
            agent_mode: Agent mode (pure_algorithm, llm_only, multimode)
            seed: Random seed for rv-agent reproducibility (passed to all trials)
        """
        self.dataset_dir = Path(dataset_dir)
        self.objective_fn = objective_fn
        self.output_base_dir = Path(output_base_dir)
        self.timeout = timeout
        self.agent_mode = agent_mode
        self.seed = seed

        # Validate dataset directory
        if not self.dataset_dir.exists():
            raise ValueError(f"Dataset directory not found: {dataset_dir}")

        # Count APKs in dataset
        self.apk_count = len(list(self.dataset_dir.glob("*.apk")))
        if self.apk_count == 0:
            raise ValueError(f"No APKs found in dataset directory: {dataset_dir}")

        # Create output directory
        self.output_base_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"CalibrationRunner initialized: dataset={dataset_dir}, "
            f"apks={self.apk_count}, timeout={timeout}s, mode={agent_mode}"
        )

    def run_trial(self, trial_id: int, params: Dict[str, Any]) -> float:
        """
        Run a single calibration trial.

        Args:
            trial_id: Trial identifier
            params: Parameter values from Optuna

        Returns:
            Objective score (0-100)
        """
        # Add seed to params if provided (for rv-agent reproducibility)
        trial_params = params.copy()
        if self.seed is not None:
            trial_params["seed"] = self.seed

        # Build tool specification with parameters
        param_str = params_to_tool_spec(trial_params)
        tool_spec = f"rvagent:{self.agent_mode}@{param_str}"

        output_dir = self.output_base_dir / f"trial_{trial_id}"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Build command
        cmd = self._build_command(tool_spec, str(output_dir))

        logger.info(f"Trial {trial_id}: Running rv-experiment")
        logger.debug(f"Command: {' '.join(cmd)}")

        # Execute
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._estimate_total_timeout()
            )

            if result.returncode != 0:
                logger.warning(f"Trial {trial_id} failed: {result.stderr[:500]}")
                self._save_error_log(output_dir, result)
                return 0.0

            # Find actual results directory (rv-experiment creates subdirectories)
            results_dir = self._find_results_dir(output_dir)
            if not results_dir:
                logger.warning(f"Trial {trial_id}: Could not find results directory")
                return 0.0

            # Compute objective score
            score = self.objective_fn.compute(str(results_dir))

            logger.info(f"Trial {trial_id}: Score = {score:.2f}")
            return score

        except subprocess.TimeoutExpired:
            logger.error(f"Trial {trial_id}: Timeout expired")
            return 0.0
        except Exception as e:
            logger.error(f"Trial {trial_id}: Exception - {e}")
            return 0.0

    def _build_command(self, tool_spec: str, output_dir: str) -> List[str]:
        """Build rv-experiment command."""
        return [
            "poetry", "run", "rv-experiment", "run",
            "--tools", tool_spec,
            "--apks-dir", str(self.dataset_dir),
            "--skip-monitors",
            "--skip-instrument",
            "--skip-static",
            "--timeout", str(self.timeout),
            "--output-dir", output_dir,
            "--no-window",
            "--repetitions", "1"
        ]

    def _estimate_total_timeout(self) -> int:
        """Estimate total timeout for all APKs."""
        # Add buffer for overhead (emulator start, install, etc)
        # Per-APK: timeout + 120s for install/setup
        # Plus 300s global buffer
        return (self.timeout + 120) * self.apk_count + 300

    def _save_error_log(self, output_dir: Path, result: subprocess.CompletedProcess):
        """Save error information for debugging."""
        error_file = output_dir / "error.log"
        with open(error_file, 'w') as f:
            f.write(f"Return code: {result.returncode}\n\n")
            f.write("=== STDOUT ===\n")
            f.write(result.stdout or "(empty)")
            f.write("\n\n=== STDERR ===\n")
            f.write(result.stderr or "(empty)")

    def _find_results_dir(self, output_dir: Path) -> Optional[Path]:
        """
        Find the actual results directory created by rv-experiment.

        rv-experiment directory structure (by design):
        - output_dir: Pre-processing artifacts (monitors, instrumented_apks, static_analysis)
        - output_dir/../results/: Experiment results (summary.csv, coverage files)

        The results_dir is a SIBLING of output_dir, not a child. This is because
        rv-experiment derives results_dir from the parent of output_dir:
        ```python
        if os.path.isabs(output_dir):
            results_dir = os.path.join(os.path.dirname(output_dir), "results")
        ```

        Args:
            output_dir: The base output directory passed to rv-experiment

        Returns:
            Path to the directory containing summary.csv, or None if not found
        """
        # First check if summary.csv is directly in output_dir (unlikely but check)
        if (output_dir / "summary.csv").exists():
            return output_dir

        # Primary location: sibling results/ directory (rv-experiment default)
        # output_dir = /tmp/calibration/trial_0
        # results = /tmp/calibration/results/cli_experiment_TIMESTAMP/
        sibling_results = output_dir.parent / "results"
        if sibling_results.exists():
            # Find the most recent experiment directory
            exp_dirs = sorted(
                [d for d in sibling_results.iterdir() if d.is_dir()],
                key=lambda d: d.stat().st_mtime,
                reverse=True
            )
            for exp_dir in exp_dirs:
                if (exp_dir / "summary.csv").exists():
                    logger.debug(f"Found results in sibling directory: {exp_dir}")
                    return exp_dir

        # Fallback: check inside output_dir/results (older behavior)
        child_results = output_dir / "results"
        if child_results.exists():
            exp_dirs = sorted(
                [d for d in child_results.iterdir() if d.is_dir()],
                key=lambda d: d.stat().st_mtime,
                reverse=True
            )
            for exp_dir in exp_dirs:
                if (exp_dir / "summary.csv").exists():
                    return exp_dir

        # Last resort: recursive search in output_dir
        for summary_file in output_dir.rglob("summary.csv"):
            return summary_file.parent

        logger.warning(f"No summary.csv found in {output_dir} or sibling results/")
        return None


def create_runner_from_config(
    dataset_dir: str,
    output_dir: str,
    timeout: int = 300,
    agent_mode: str = "pure_algorithm",
    baseline_max_errors: Optional[float] = None
) -> CalibrationRunner:
    """
    Create a CalibrationRunner with standard configuration.

    Args:
        dataset_dir: Path to pre-instrumented APKs (should contain only
                     the APKs to be used in calibration)
        output_dir: Output directory for trials
        timeout: Timeout per APK
        agent_mode: Agent execution mode
        baseline_max_errors: Max errors for normalization

    Returns:
        Configured CalibrationRunner
    """
    objective_fn = ObjectiveFunction(
        coverage_weight=0.50,
        errors_weight=0.50,
        baseline_max_errors=baseline_max_errors
    )

    return CalibrationRunner(
        dataset_dir=dataset_dir,
        objective_fn=objective_fn,
        output_base_dir=output_dir,
        timeout=timeout,
        agent_mode=agent_mode
    )
