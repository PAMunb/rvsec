#!/usr/bin/env python3
"""
Calibration orchestrator for Docker-based RVAgent parameter optimization.

Manages the Optuna study, generates docker-compose files per round of trials,
launches containers via docker compose, and collects results. Runs on the host
machine (not inside Docker).

Each round asks Optuna for N trials (one per container), writes a docker-compose
file with N services, launches them in parallel, waits for completion, scores
results, and tells Optuna. Repeats until n_trials is reached.

Usage:
    poetry run python scripts/calibration_orchestrator.py \
        --phase macro --n-trials 80 --n-containers 6 \
        --data-dir /path/to/calibration_dataset_v2 \
        --filter-file /path/to/calibration_set_v2.txt \
        --output-dir ./results/calibration_macro_v2 \
        --timeout 300 --agent-mode pure_algorithm --seed 42 \
        --baseline-dir ./results/baseline_v2
"""

import argparse
import json
import logging
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import optuna
import yaml
from optuna.trial import TrialState

# Imports from the existing calibration module
from rv_agent_validation.calibration.objective import ObjectiveFunction
from rv_agent_validation.calibration.parameter_space import (
    CalibrationPhase,
    get_default_params,
    params_to_tool_spec,
    suggest_params,
)

logger = logging.getLogger(__name__)

# Minimum free disk space required to start a calibration round (10 GB)
MIN_DISK_SPACE_BYTES = 10 * 1024 * 1024 * 1024

# Stagger delay between containers to avoid boot-storm on the host (seconds)
CONTAINER_STAGGER_SECONDS = 10

# Per-round timeout multiplier applied to the per-APK timeout.
# Each container runs all APKs sequentially, so the round timeout must be
# generous enough to cover the slowest container.
ROUND_TIMEOUT_MULTIPLIER = 4


# ---------------------------------------------------------------------------
# Pure functions (unit-testable, no Docker or subprocess calls)
# ---------------------------------------------------------------------------


def generate_calibration_compose(
    batch: List[Tuple[int, str]],
    data_dir: str,
    filter_file: str,
    output_dir: str,
    image: str,
    cpus: int,
    memory: str,
    timeout: int,
) -> dict:
    """
    Build a docker-compose dict for one round of calibration trials.

    Each (trial_number, tool_spec) pair in *batch* becomes a service named
    ``trial_{N}``.  Services are staggered by RV_DELAY so emulators don't
    all boot simultaneously.

    Args:
        batch: List of ``(trial_number, tool_spec)`` tuples for this round.
        data_dir: Host path to the pre-instrumented APK dataset (mounted read-only).
        filter_file: Host path to the APK filter list (mounted read-only).
        output_dir: Host path for trial result directories.
        image: Docker image to use for each container.
        cpus: CPU limit per container.
        memory: Memory limit per container (e.g. ``"20g"``).
        timeout: Per-APK timeout in seconds passed to rv-experiment.

    Returns:
        YAML-serializable dict with a ``services`` key.
    """
    services = {}
    for index, (trial_num, tool_spec) in enumerate(batch):
        service_name = f"trial_{trial_num}"
        services[service_name] = {
            "image": image,
            "environment": {
                "RV_TOOLS": tool_spec,
                "RV_EXPERIMENT_NAME": f"trial_{trial_num}",
                "RV_TIMEOUTS": str(timeout),
                "RV_NO_WINDOW": "true",
                "RV_SKIP_MONITORS": "true",
                "RV_SKIP_INSTRUMENT": "true",
                "RV_SKIP_STATIC_ANALYSIS": "true",
                "RV_APKS_FILTER": "/opt/rvsec/rv-android/filters/filter.txt",
                "RV_DELAY": str(index * CONTAINER_STAGGER_SECONDS),
            },
            "volumes": [
                f"{data_dir}:/opt/rvsec/rv-android/apks:ro",
                f"{filter_file}:/opt/rvsec/rv-android/filters/filter.txt:ro",
                f"{output_dir}/trial_{trial_num}:/opt/rvsec/rv-android/results",
            ],
            "devices": ["/dev/kvm:/dev/kvm"],
            "deploy": {
                "resources": {
                    "limits": {
                        "cpus": str(cpus),
                        "memory": memory,
                    }
                }
            },
        }

    return {"services": services}


def recover_orphaned_trials(
    study: optuna.Study,
    output_dir: str,
    objective_fn: ObjectiveFunction,
) -> int:
    """
    Recover trials left in RUNNING state from a previous interrupted session.

    After a crash, some trials may still be marked RUNNING in the Optuna
    storage.  For each one, check whether the container actually finished
    (summary.csv exists) and either tell Optuna the score or mark the trial
    as failed.

    Args:
        study: The Optuna study (backed by SQLite for persistence).
        output_dir: Base directory where ``trial_{N}/`` subdirectories live.
        objective_fn: Objective function used to score completed trials.

    Returns:
        Number of trials recovered (scored or failed).
    """
    recovered = 0
    for trial in study.trials:
        if trial.state != TrialState.RUNNING:
            continue

        trial_num = trial.number
        try:
            score = compute_score_for_trial(trial_num, output_dir, objective_fn)
            study.tell(trial_num, score)
            logger.info(f"Recovered trial {trial_num} with score {score:.2f}")
        except Exception:
            study.tell(trial_num, state=TrialState.FAIL)
            logger.info(f"Marked orphaned trial {trial_num} as FAIL (no results)")

        recovered += 1

    return recovered


def preflight_checks(data_dir: str, filter_file: str, agent_mode: str) -> None:
    """
    Validate host-side preconditions before starting calibration.

    Raises ``SystemExit`` if any check fails.  Intentionally does NOT check
    Docker daemon or SGLang availability -- those are runtime concerns handled
    in ``main()``.

    Args:
        data_dir: Path to the APK dataset directory.
        filter_file: Path to the APK filter file.
        agent_mode: Agent execution mode (for logging only).
    """
    data_path = Path(data_dir)
    if not data_path.exists():
        sys.exit(f"Data directory does not exist: {data_dir}")

    filter_path = Path(filter_file)
    if not filter_path.exists():
        sys.exit(f"Filter file does not exist: {filter_file}")

    # Check free disk space on the partition where output will be written
    disk = shutil.disk_usage(data_path)
    if disk.free < MIN_DISK_SPACE_BYTES:
        free_gb = disk.free / (1024 ** 3)
        sys.exit(
            f"Insufficient disk space: {free_gb:.1f} GB free, "
            f"need at least {MIN_DISK_SPACE_BYTES / (1024 ** 3):.0f} GB"
        )


def compute_score_for_trial(
    trial_num: int,
    output_dir: str,
    objective_fn: ObjectiveFunction,
) -> float:
    """
    Compute the objective score for a single completed trial.

    The rv-experiment container writes results into
    ``{output_dir}/trial_{N}/trial_{N}/`` (the inner directory is created by
    rv-experiment using ``RV_EXPERIMENT_NAME``).

    Args:
        trial_num: Optuna trial number.
        output_dir: Base calibration output directory.
        objective_fn: Objective function instance.

    Returns:
        Objective score (0-100 scale).
    """
    results_dir = Path(output_dir) / f"trial_{trial_num}" / f"trial_{trial_num}"
    summary_csv = results_dir / "summary.csv"
    if not summary_csv.exists():
        raise FileNotFoundError(f"No summary.csv for trial {trial_num}: {summary_csv}")
    return objective_fn.compute(str(results_dir))


def _save_results(
    study: optuna.Study,
    phase_name: str,
    seed: int,
    n_trials: int,
    output_dir: str,
) -> None:
    """
    Persist calibration artifacts to disk.

    Writes three files:
    - ``optimal_params.json`` -- best trial metadata and parameters.
    - ``param_string.txt`` -- tool spec DSL for direct use with rv-experiment.
    - ``trial_history.json`` -- full trial log for analysis.

    Args:
        study: Completed Optuna study.
        phase_name: Calibration phase name (``"macro"`` or ``"micro"``).
        seed: Random seed used for reproducibility.
        n_trials: Total number of trials requested.
        output_dir: Directory to write result files into.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    best_trial = study.best_trial

    # optimal_params.json
    optimal = {
        "phase": phase_name,
        "seed": seed,
        "best_score": best_trial.value,
        "best_params": best_trial.params,
        "n_trials": n_trials,
    }
    with open(out / "optimal_params.json", "w", encoding="utf-8") as f:
        json.dump(optimal, f, indent=2)

    # param_string.txt -- ready to paste into --tools rvagent:<spec>
    with open(out / "param_string.txt", "w", encoding="utf-8") as f:
        f.write(params_to_tool_spec(best_trial.params))
        f.write("\n")

    # trial_history.json
    history = []
    for trial in study.trials:
        history.append(
            {
                "number": trial.number,
                "params": trial.params,
                "value": trial.value,
                "state": trial.state.name,
            }
        )
    with open(out / "trial_history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    logger.info(f"Results saved to {out}")


# ---------------------------------------------------------------------------
# CLI and main loop
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Docker-based calibration orchestrator for RVAgent parameters.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--phase",
        choices=["macro", "micro"],
        required=True,
        help="Calibration phase: macro tunes 8 high-impact params, micro tunes 16 fine-tuning params.",
    )
    parser.add_argument(
        "--n-trials",
        type=int,
        required=True,
        help="Total number of Optuna trials to run.",
    )
    parser.add_argument(
        "--n-containers",
        type=int,
        default=6,
        help="Parallel containers per round (default: 6).",
    )
    parser.add_argument(
        "--data-dir",
        required=True,
        help="Host path to the pre-instrumented APK dataset.",
    )
    parser.add_argument(
        "--filter-file",
        required=True,
        help="Host path to the APK filter list (one filename per line).",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Host path for calibration output (trials, study DB, results).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Per-APK timeout in seconds (default: 300).",
    )
    parser.add_argument(
        "--agent-mode",
        choices=["pure_algorithm", "multimode"],
        default="pure_algorithm",
        help="RVAgent execution mode (default: pure_algorithm).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume a previous calibration run (recover orphaned trials).",
    )
    parser.add_argument(
        "--best-macro",
        type=str,
        default=None,
        help="Path to optimal_params.json from macro phase (required for --phase micro).",
    )
    parser.add_argument(
        "--baseline-dir",
        type=str,
        default=None,
        help="Path to baseline results for adaptive error normalization.",
    )
    parser.add_argument(
        "--image",
        type=str,
        default="phtcosta/rvandroid:0.8.0",
        help="Docker image for trial containers (default: phtcosta/rvandroid:0.8.0).",
    )
    parser.add_argument(
        "--cpus",
        type=int,
        default=10,
        help="CPU limit per container (default: 10).",
    )
    parser.add_argument(
        "--memory",
        type=str,
        default="20g",
        help="Memory limit per container (default: 20g).",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()

    # --- Setup ---
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(output_dir / "orchestrator.log"),
        ],
    )

    logger.info("=" * 60)
    logger.info("RVAgent Calibration Orchestrator")
    logger.info(f"Phase: {args.phase}, Trials: {args.n_trials}, Containers/round: {args.n_containers}")
    logger.info(f"Data: {args.data_dir}, Output: {args.output_dir}")
    logger.info("=" * 60)

    # --- Micro phase requires best-macro ---
    if args.phase == "micro" and args.best_macro is None:
        sys.exit("--best-macro is required for --phase micro")

    # --- Preflight ---
    preflight_checks(args.data_dir, args.filter_file, args.agent_mode)

    # --- Objective function ---
    baseline_max_errors: Optional[float] = None
    if args.baseline_dir:
        baseline_max_errors = ObjectiveFunction.compute_baseline_max_errors(args.baseline_dir)
        logger.info(f"Baseline max errors: {baseline_max_errors:.2f}")

    objective_fn = ObjectiveFunction(
        coverage_weight=0.40,
        errors_weight=0.40,
        ui_coverage_weight=0.20,
        baseline_max_errors=baseline_max_errors,
    )

    # --- Optuna study (SQLite for crash-resilient persistence) ---
    storage_path = output_dir / "optuna_study.db"
    storage_url = f"sqlite:///{storage_path}"
    study_name = f"calibration_{args.phase}_{args.seed}"

    sampler = optuna.samplers.TPESampler(seed=args.seed)
    study = optuna.create_study(
        study_name=study_name,
        storage=storage_url,
        sampler=sampler,
        direction="maximize",
        load_if_exists=True,
    )
    logger.info(f"Optuna study: {study_name} (storage: {storage_path})")

    # --- Resume: recover orphaned trials ---
    if args.resume:
        recovered = recover_orphaned_trials(study, str(output_dir), objective_fn)
        logger.info(f"Recovered {recovered} orphaned trial(s)")

    # --- Load fixed params for micro phase ---
    fixed_params: Dict[str, Any] = {}
    if args.best_macro:
        with open(args.best_macro, "r", encoding="utf-8") as f:
            macro_results = json.load(f)
        fixed_params = macro_results["best_params"]
        logger.info(f"Loaded {len(fixed_params)} fixed macro params from {args.best_macro}")

    # --- Map phase string to enum ---
    phase = CalibrationPhase.MACRO if args.phase == "macro" else CalibrationPhase.MICRO

    # --- Count already-completed trials ---
    completed_count = len([t for t in study.trials if t.state == TrialState.COMPLETE])
    remaining = args.n_trials - completed_count
    if remaining <= 0:
        logger.info(f"All {args.n_trials} trials already completed. Saving results.")
        _save_results(study, args.phase, args.seed, args.n_trials, str(output_dir))
        _print_summary(study)
        return

    logger.info(f"Completed: {completed_count}, Remaining: {remaining}")

    # --- Main optimization loop ---
    round_number = 0
    round_timeout = args.timeout * ROUND_TIMEOUT_MULTIPLIER

    while remaining > 0:
        round_number += 1
        batch_size = min(args.n_containers, remaining)
        logger.info(f"--- Round {round_number}: asking for {batch_size} trial(s) ---")

        # Ask Optuna for trial suggestions
        batch: List[Tuple[int, str]] = []
        trials_this_round: List[optuna.Trial] = []

        for _ in range(batch_size):
            trial = study.ask()
            trials_this_round.append(trial)

            # Suggest parameters for this trial's phase
            params = suggest_params(trial, phase)

            # For micro phase, merge fixed macro params underneath the tuned micro params
            if fixed_params:
                merged = {**fixed_params, **params}
            else:
                merged = params

            tool_spec = f"rvagent:{args.agent_mode}@{params_to_tool_spec(merged)}"
            batch.append((trial.number, tool_spec))
            logger.info(f"  Trial {trial.number}: {tool_spec[:120]}...")

        # Generate docker-compose file for this round
        compose_dict = generate_calibration_compose(
            batch=batch,
            data_dir=str(Path(args.data_dir).resolve()),
            filter_file=str(Path(args.filter_file).resolve()),
            output_dir=str(output_dir.resolve()),
            image=args.image,
            cpus=args.cpus,
            memory=args.memory,
            timeout=args.timeout,
        )

        compose_path = output_dir / f"docker-compose.round-{round_number:02d}.yml"
        with open(compose_path, "w", encoding="utf-8") as f:
            yaml.dump(compose_dict, f, default_flow_style=False, sort_keys=False)
        logger.info(f"Compose file: {compose_path}")

        # Launch containers and wait for completion
        logger.info(f"Launching {batch_size} container(s)...")
        start_time = time.monotonic()

        try:
            subprocess.run(
                ["docker", "compose", "-f", str(compose_path), "up"],
                check=False,
                timeout=round_timeout,
            )
        except subprocess.TimeoutExpired:
            logger.warning(f"Round {round_number} timed out after {round_timeout}s")
        finally:
            subprocess.run(
                ["docker", "compose", "-f", str(compose_path), "down"],
                check=False,
            )

        elapsed = time.monotonic() - start_time
        logger.info(f"Round {round_number} finished in {elapsed:.0f}s")

        # Score results and tell Optuna
        for trial in trials_this_round:
            try:
                score = compute_score_for_trial(trial.number, str(output_dir), objective_fn)
                study.tell(trial.number, score)
                logger.info(f"  Trial {trial.number} -> score {score:.2f}")
            except Exception as e:
                study.tell(trial.number, state=TrialState.FAIL)
                logger.warning(f"  Trial {trial.number} FAILED: {e}")

        # Update remaining count
        completed_count = len([t for t in study.trials if t.state == TrialState.COMPLETE])
        remaining = args.n_trials - completed_count
        logger.info(f"Progress: {completed_count}/{args.n_trials} trials complete")

    # --- Save results ---
    _save_results(study, args.phase, args.seed, args.n_trials, str(output_dir))
    _print_summary(study)


def _print_summary(study: optuna.Study) -> None:
    """Print a human-readable summary of the calibration run."""
    completed = [t for t in study.trials if t.state == TrialState.COMPLETE]
    failed = [t for t in study.trials if t.state == TrialState.FAIL]

    logger.info("=" * 60)
    logger.info("CALIBRATION SUMMARY")
    logger.info(f"  Completed trials: {len(completed)}")
    logger.info(f"  Failed trials:    {len(failed)}")

    if completed:
        best = study.best_trial
        logger.info(f"  Best score:       {best.value:.2f}")
        logger.info(f"  Best trial:       #{best.number}")
        logger.info(f"  Best params:      {json.dumps(best.params, indent=4)}")
        logger.info(f"  Tool spec:        {params_to_tool_spec(best.params)}")

    logger.info("=" * 60)


if __name__ == "__main__":
    main()
