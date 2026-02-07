"""
Optuna optimizer wrapper for RVAgent calibration.

Provides TPESampler-based Bayesian optimization with reproducibility support.
Supports resume via SQLite storage for long-running calibrations.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable

import optuna
from optuna.samplers import TPESampler
from optuna.storages import RDBStorage

from .parameter_space import (
    CalibrationPhase,
    suggest_params,
    get_default_params,
    params_to_tool_spec,
)
from .objective import ObjectiveFunction

logger = logging.getLogger(__name__)


class CalibrationOptimizer:
    """
    Optuna-based optimizer for RVAgent calibration.

    Uses Tree-structured Parzen Estimator (TPE) for efficient
    Bayesian optimization of scorer weights and exploration parameters.

    Supports resume via SQLite storage - calibrations can be interrupted
    and resumed without losing progress.
    """

    def __init__(
        self,
        phase: CalibrationPhase,
        objective_fn: ObjectiveFunction,
        trial_runner: Callable[[int, Dict[str, Any]], float],
        seed: int = 42,
        study_name: str = "rvagent_calibration",
        storage_path: Optional[str] = None,
        resume: bool = False,
        fixed_params: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize optimizer.

        Args:
            phase: Calibration phase (macro, micro, or full)
            objective_fn: Objective function for scoring results
            trial_runner: Function that runs a trial and returns score.
                          Signature: (trial_id, params) -> score
            seed: Random seed for reproducibility
            study_name: Name for the Optuna study
            storage_path: Path to SQLite database for persistence.
                          If None, uses in-memory storage (no resume).
            resume: If True, load existing study from storage.
                    If False, create new study (deletes existing if any).
            fixed_params: Optional dict of fixed parameters (e.g., macro params
                          for micro phase). These are not optimized.
        """
        self.phase = phase
        self.objective_fn = objective_fn
        self.trial_runner = trial_runner
        self.seed = seed
        self.study_name = study_name
        self.storage_path = storage_path
        self.resume = resume
        self.fixed_params = fixed_params or {}

        # Create sampler with fixed seed for reproducibility
        self.sampler = TPESampler(seed=seed)

        # Setup storage
        self.storage = self._create_storage(storage_path)

        # Create or load study
        self.study = self._create_or_load_study(resume)

        # Track best params
        self.best_params: Optional[Dict[str, Any]] = None
        self.best_score: float = 0.0

        # Load best from existing trials if resuming
        if resume and len(self.study.trials) > 0:
            completed_trials = [t for t in self.study.trials
                               if t.state == optuna.trial.TrialState.COMPLETE]
            if completed_trials:
                self.best_score = self.study.best_value
                self.best_params = self.study.best_params
                logger.info(f"Resumed study with {len(completed_trials)} completed trials")
                logger.info(f"Current best score: {self.best_score:.2f}")

        logger.info(
            f"CalibrationOptimizer initialized: phase={phase.value}, "
            f"seed={seed}, study={study_name}, resume={resume}"
        )

    def _create_storage(self, storage_path: Optional[str]) -> Optional[RDBStorage]:
        """
        Create SQLite storage for study persistence.

        Args:
            storage_path: Path to SQLite database file

        Returns:
            RDBStorage instance or None for in-memory
        """
        if storage_path is None:
            logger.info("Using in-memory storage (no resume support)")
            return None

        # Ensure parent directory exists
        path = Path(storage_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Create SQLite storage
        storage_url = f"sqlite:///{storage_path}"
        storage = RDBStorage(
            url=storage_url,
            engine_kwargs={"connect_args": {"timeout": 30}}
        )
        logger.info(f"Using SQLite storage: {storage_path}")
        return storage

    def _create_or_load_study(self, resume: bool) -> optuna.Study:
        """
        Create new study or load existing one.

        Args:
            resume: If True, load existing study. If False, create new.

        Returns:
            Optuna Study instance
        """
        if resume and self.storage is not None:
            # Try to load existing study
            try:
                study = optuna.load_study(
                    study_name=self.study_name,
                    storage=self.storage,
                    sampler=self.sampler
                )
                logger.info(f"Loaded existing study '{self.study_name}' with {len(study.trials)} trials")
                return study
            except KeyError:
                logger.warning(f"Study '{self.study_name}' not found, creating new one")

        # Create new study
        if self.storage is not None and not resume:
            # Delete existing study if any
            try:
                optuna.delete_study(study_name=self.study_name, storage=self.storage)
                logger.info(f"Deleted existing study '{self.study_name}'")
            except KeyError:
                pass  # Study doesn't exist, that's fine

        study = optuna.create_study(
            direction="maximize",
            sampler=self.sampler,
            study_name=self.study_name,
            storage=self.storage,
            load_if_exists=resume
        )
        logger.info(f"Created new study '{self.study_name}'")
        return study

    def get_completed_trials_count(self) -> int:
        """Get number of completed trials."""
        return len([t for t in self.study.trials
                   if t.state == optuna.trial.TrialState.COMPLETE])

    def get_remaining_trials(self, n_trials: int) -> int:
        """Get number of remaining trials to reach n_trials."""
        completed = self.get_completed_trials_count()
        return max(0, n_trials - completed)

    def _objective(self, trial: optuna.Trial) -> float:
        """
        Optuna objective function wrapper.

        Args:
            trial: Optuna trial object

        Returns:
            Objective score (higher is better)
        """
        # Suggest parameters for this trial
        params = suggest_params(trial, self.phase)

        # Combine with fixed params (e.g., macro params for micro phase)
        # Fixed params take precedence and are not suggested by Optuna
        combined_params = {**params, **self.fixed_params}

        # Log trial start
        trial_id = trial.number
        logger.info(f"Trial {trial_id}: suggested={params}")
        if self.fixed_params:
            logger.info(f"Trial {trial_id}: fixed={self.fixed_params}")

        try:
            # Run trial and get score using combined params
            score = self.trial_runner(trial_id, combined_params)

            # Update best if improved (store combined params)
            if score > self.best_score:
                self.best_score = score
                self.best_params = combined_params.copy()
                logger.info(f"New best score: {score:.2f}")

            return score

        except Exception as e:
            logger.error(f"Trial {trial_id} failed: {e}")
            return 0.0  # Return 0 for failed trials

    def optimize(self, n_trials: int, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Run optimization.

        When resuming, only runs remaining trials to reach n_trials total.

        Args:
            n_trials: Total number of trials to run (including completed ones)
            timeout: Optional timeout in seconds

        Returns:
            Best parameters found
        """
        completed = self.get_completed_trials_count()
        remaining = self.get_remaining_trials(n_trials)

        if remaining == 0:
            logger.info(f"Already completed {completed} trials, nothing to do")
            if self.study.best_trial:
                self.best_params = self.study.best_params
                self.best_score = self.study.best_value
            return self.best_params or {}

        logger.info(
            f"Starting optimization: target={n_trials} trials, "
            f"completed={completed}, remaining={remaining}, timeout={timeout}"
        )

        self.study.optimize(
            self._objective,
            n_trials=remaining,
            timeout=timeout,
            show_progress_bar=True
        )

        # Get best parameters
        if self.study.best_trial:
            self.best_params = self.study.best_params
            self.best_score = self.study.best_value

        total_completed = self.get_completed_trials_count()
        logger.info(f"Optimization complete. Total trials: {total_completed}")
        logger.info(f"Best score: {self.best_score:.2f}")
        logger.info(f"Best parameters: {self.best_params}")

        return self.best_params or {}

    def save_results(self, output_dir: str):
        """
        Save optimization results to files.

        Args:
            output_dir: Output directory path
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save best parameters as JSON
        params_file = output_path / "optimal_params.json"
        with open(params_file, 'w') as f:
            json.dump({
                "phase": self.phase.value,
                "seed": self.seed,
                "best_score": self.best_score,
                "best_params": self.best_params,
                "n_trials": len(self.study.trials),
            }, f, indent=2)
        logger.info(f"Saved optimal parameters to {params_file}")

        # Save as tool spec string for rv-experiment
        spec_file = output_path / "param_string.txt"
        if self.best_params:
            spec_str = params_to_tool_spec(self.best_params)
            with open(spec_file, 'w') as f:
                f.write(spec_str)
            logger.info(f"Saved parameter string to {spec_file}")

        # Save full trial history
        history_file = output_path / "trial_history.json"
        trials_data = []
        for trial in self.study.trials:
            trials_data.append({
                "number": trial.number,
                "params": trial.params,
                "value": trial.value,
                "state": trial.state.name,
            })
        with open(history_file, 'w') as f:
            json.dump(trials_data, f, indent=2)
        logger.info(f"Saved trial history to {history_file}")

    def get_best_params_with_defaults(self) -> Dict[str, Any]:
        """
        Get best parameters merged with defaults for untuned params.

        Returns:
            Complete parameter dictionary
        """
        defaults = get_default_params()
        if self.best_params:
            defaults.update(self.best_params)
        return defaults

    @staticmethod
    def load_best_params(params_file: str) -> Dict[str, Any]:
        """
        Load best parameters from a previous optimization run.

        Args:
            params_file: Path to optimal_params.json

        Returns:
            Best parameters dictionary
        """
        with open(params_file, 'r') as f:
            data = json.load(f)
        return data.get("best_params", {})
