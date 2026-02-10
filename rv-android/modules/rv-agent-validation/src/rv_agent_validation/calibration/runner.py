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
        seed: Optional[int] = None,
        apks_filter: Optional[str] = None
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
            apks_filter: Path to text file listing APK filenames to process
        """
        self.dataset_dir = Path(dataset_dir)
        self.objective_fn = objective_fn
        self.output_base_dir = Path(output_base_dir)
        self.timeout = timeout
        self.agent_mode = agent_mode
        self.seed = seed
        self.apks_filter = apks_filter

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

    def run_trial(self, trial_id: int, params: Dict[str, Any],
                  device_port: Optional[int] = None) -> float:
        """
        Run a single calibration trial.

        Args:
            trial_id: Trial identifier
            params: Parameter values from Optuna
            device_port: Emulator port for parallel execution

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
        cmd = self._build_command(tool_spec, str(output_dir), trial_id, device_port)

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

            # Find actual results directory
            results_dir = self._find_results_dir(output_dir, trial_id)
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

    def _build_command(self, tool_spec: str, output_dir: str,
                       trial_id: int = 0,
                       device_port: Optional[int] = None) -> List[str]:
        """Build rv-experiment command."""
        cmd = [
            "poetry", "run", "rv-experiment", "run",
            "--tools", tool_spec,
            "--apks-dir", str(self.dataset_dir),
            "--skip-monitors",
            "--skip-instrument",
            "--skip-static",
            "--timeout", str(self.timeout),
            "--output-dir", output_dir,
            "--no-window",
            "--repetitions", "1",
            "--name", f"trial_{trial_id}",
        ]
        if device_port is not None:
            cmd.extend(["--device-port", str(device_port)])
        if self.apks_filter:
            cmd.extend(["--apks-filter", str(self.apks_filter)])
        return cmd

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

    def _find_results_dir(self, output_dir: Path, trial_id: int = 0) -> Optional[Path]:
        """
        Find the actual results directory created by rv-experiment.

        With --name trial_{id}, the results directory is deterministic:
        output_dir/trial_{id}/ contains summary.csv.

        Falls back to mtime-based search for compatibility.

        Args:
            output_dir: The base output directory passed to rv-experiment
            trial_id: Trial identifier used in --name

        Returns:
            Path to the directory containing summary.csv, or None if not found
        """
        # Direct match: --name creates a deterministic directory
        named_dir = output_dir / f"trial_{trial_id}"
        if (named_dir / "summary.csv").exists():
            return named_dir

        # Check output_dir itself
        if (output_dir / "summary.csv").exists():
            return output_dir

        # Sibling results/ directory (rv-experiment default layout)
        sibling_results = output_dir.parent / "results"
        if sibling_results.exists():
            # Try deterministic name first
            named_sibling = sibling_results / f"trial_{trial_id}"
            if (named_sibling / "summary.csv").exists():
                return named_sibling

            # Fallback: most recent experiment directory
            exp_dirs = sorted(
                [d for d in sibling_results.iterdir() if d.is_dir()],
                key=lambda d: d.stat().st_mtime,
                reverse=True
            )
            for exp_dir in exp_dirs:
                if (exp_dir / "summary.csv").exists():
                    return exp_dir

        # Last resort: recursive search
        for summary_file in output_dir.rglob("summary.csv"):
            return summary_file.parent

        logger.warning(f"No summary.csv found in {output_dir}")
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
        coverage_weight=0.40,
        errors_weight=0.40,
        ui_coverage_weight=0.20,
        baseline_max_errors=baseline_max_errors
    )

    return CalibrationRunner(
        dataset_dir=dataset_dir,
        objective_fn=objective_fn,
        output_base_dir=output_dir,
        timeout=timeout,
        agent_mode=agent_mode
    )
