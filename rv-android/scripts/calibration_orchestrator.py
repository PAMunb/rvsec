#!/usr/bin/env python3
"""
Calibration orchestrator for Docker-based parameter optimization.

Supports two tool families:
- rvagent (default): RVAgent modes (pure_algorithm, multimode)
- aperv: APE-RV variants (sata_mop, sata_mop_llm)

Manages the Optuna study, generates docker-compose files per round of trials,
launches containers via docker compose, and collects results. Runs on the host
machine (not inside Docker).

Each round asks Optuna for N trials (one per container), writes a docker-compose
file with N services, launches them in parallel, waits for completion, scores
results, and tells Optuna. Repeats until n_trials is reached.

Usage:
    # RVAgent calibration (original):
    uv run python scripts/calibration_orchestrator.py \
        --phase macro --n-trials 80 --n-containers 6 \
        --data-dir /path/to/calibration_dataset_v2 \
        --filter-file /path/to/calibration_set_v2.txt \
        --output-dir ./results/calibration_macro_v2 \
        --timeout 300 --agent-mode pure_algorithm --seed 42 \
        --baseline-dir ./results/baseline_v2

    # APE-RV MACRO calibration (no LLM):
    uv run python scripts/calibration_orchestrator.py \
        --tool aperv:sata_mop --phase macro --n-trials 130 --n-containers 10 \
        --data-dir data/apks \
        --filter-file data/apks/aperv_precal_30.txt \
        --output-dir ./results/aperv_precal_macro \
        --timeout 600 --seed 42

    # APE-RV MICRO calibration (with LLM):
    uv run python scripts/calibration_orchestrator.py \
        --tool aperv:sata_mop_llm --phase micro --n-trials 80 --n-containers 8 \
        --data-dir data/apks \
        --filter-file data/apks/aperv_precal_30.txt \
        --output-dir ./results/aperv_precal_micro \
        --timeout 600 --seed 42 \
        --best-macro ./results/aperv_precal_macro/optimal_params.json \
        --sglang-url http://host.docker.internal:30000/v1
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

# Tool-specific imports are loaded dynamically based on --tool flag.
# For rvagent: rv_agent_validation.calibration.{parameter_space,objective}
# For aperv:   scripts/aperv_{parameter_space,objective}.py
_suggest_params = None
_params_to_tool_spec = None
_CalibrationPhase = None
_compute_aperv_score = None
_ObjectiveFunction = None
_get_default_params = None
_fixed_params_v2 = None  # FIXED_PARAMS_V2 loaded when param_version=v2


def _load_tool_modules(tool: str, param_version: str = "v1") -> None:
    """Load parameter space and objective modules for the given tool family.

    Dynamically imports the correct parameter space and objective function
    modules based on the tool family (aperv vs rvagent). This avoids a
    hard dependency on both tool families at import time -- the rvagent
    calibration modules live in a separate package that may not be installed.

    Args:
        tool: Tool identifier string. If it starts with ``"aperv"``, loads
            from ``aperv_parameter_space`` / ``aperv_objective`` (local scripts).
            Otherwise, loads from ``rv_agent_validation.calibration`` package.
        param_version: Parameter space version (``"v1"`` or ``"v2"``).
            v2 uses reduced 10-param search space with fixed params merged
            by the orchestrator. Only applies to aperv tool family.
    """
    global _suggest_params, _params_to_tool_spec, _CalibrationPhase
    global _compute_aperv_score, _ObjectiveFunction, _get_default_params
    global _fixed_params_v2

    if tool.startswith("aperv"):
        from aperv_objective import compute_score
        from aperv_parameter_space import (
            CalibrationPhase,
            params_to_tool_spec,
        )

        if param_version == "v2":
            from aperv_parameter_space import (
                FIXED_PARAMS_V2,
                get_default_params_v2,
                suggest_params_v2,
            )

            _suggest_params = suggest_params_v2
            _get_default_params = get_default_params_v2
            _fixed_params_v2 = FIXED_PARAMS_V2
        else:
            from aperv_parameter_space import (
                get_default_params,
                suggest_params,
            )

            _suggest_params = suggest_params
            _get_default_params = get_default_params
            _fixed_params_v2 = None

        _params_to_tool_spec = params_to_tool_spec
        _CalibrationPhase = CalibrationPhase
        _compute_aperv_score = compute_score
        # aperv uses a standalone compute_score function, not a class
        _ObjectiveFunction = None
    else:
        from rv_agent_validation.calibration.objective import ObjectiveFunction
        from rv_agent_validation.calibration.parameter_space import (
            CalibrationPhase,
            get_default_params,
            params_to_tool_spec,
            suggest_params,
        )

        _suggest_params = suggest_params
        _params_to_tool_spec = params_to_tool_spec
        _CalibrationPhase = CalibrationPhase
        # rvagent uses ObjectiveFunction class with configurable weights
        _compute_aperv_score = None
        _get_default_params = get_default_params
        _ObjectiveFunction = ObjectiveFunction
        _fixed_params_v2 = None


logger = logging.getLogger(__name__)

# Minimum free disk space required to start a calibration round (10 GB)
MIN_DISK_SPACE_BYTES = 10 * 1024 * 1024 * 1024

# Stagger delay between containers to avoid boot-storm on the host (seconds)
CONTAINER_STAGGER_SECONDS = 10

# Overhead per task beyond the tool timeout (emulator boot + teardown + margin)
TASK_OVERHEAD_SECONDS = 120

# Safety margin applied to the computed round timeout
ROUND_TIMEOUT_SAFETY_MARGIN = 1.5


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
    extra_hosts: Optional[List[str]] = None,
    reps: int = 1,
    jar_path: Optional[str] = None,
    broadcast_path: Optional[str] = None,
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
        extra_hosts: Docker extra_hosts entries for container-to-host networking.
            Use ``["host.docker.internal:host-gateway"]`` when containers need to
            reach services on the host (e.g. SGLang for multimode).
        reps: Repetitions per APK per trial (default 1). Sets RV_REPETITIONS.
        jar_path: Host path to ape-rv.jar for volume mounting (GCP calibration).
        broadcast_path: Host path to system-broadcast.json for volume mounting.

    Returns:
        YAML-serializable dict with a ``services`` key.
    """
    services = {}
    for index, (trial_num, tool_spec) in enumerate(batch):
        service_name = f"trial_{trial_num}"
        service: dict = {
            "image": image,
            "environment": {
                "RV_TOOLS": tool_spec,
                "RV_EXPERIMENT_NAME": f"trial_{trial_num}",
                "RV_TIMEOUTS": str(timeout),
                "RV_REPETITIONS": str(reps),
                "RV_APKS_DIR": "/opt/rvsec/rv-android/apks",
                "RV_NO_WINDOW": "true",
                "RV_SPEC_SET": "jca",
                # Skip pre-processing: APKs in data_dir are already instrumented.
                # This saves ~5min/APK of monitor generation + instrumentation.
                "RV_SKIP_MONITORS": "true",
                "RV_SKIP_INSTRUMENT": "true",
                "RV_SKIP_STATIC_ANALYSIS": "true",
                "RV_APKS_FILTER": "/opt/rvsec/rv-android/filters/filter.txt",
                # Stagger emulator boots to avoid a KVM/CPU boot-storm on the host
                "RV_DELAY": str(index * CONTAINER_STAGGER_SECONDS),
                # Activate socat bridge inside the container for LLM variants.
                # The bridge forwards LLM requests to the SGLang server on the host.
                **({"RVSMART_LLM_MODE": "true"} if "llm" in tool_spec else {}),
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
        if jar_path:
            service["volumes"].append(
                f"{jar_path}:/opt/rvsec/rv-android/modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar:ro"
            )
        if broadcast_path:
            service["volumes"].append(
                f"{broadcast_path}:/opt/rvsec/rv-android/modules/aperv-tool/src/aperv_tool/tools/aperv/system-broadcast.json:ro"
            )
        if extra_hosts:
            service["extra_hosts"] = list(extra_hosts)
        services[service_name] = service

    return {"services": services}


def recover_orphaned_trials(
    study: optuna.Study,
    output_dir: str,
    objective_fn,
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


def count_filter_apks(filter_file: str) -> int:
    """Count non-empty lines in a filter file.

    Args:
        filter_file: Path to the APK filter file (one filename per line).

    Returns:
        Number of APKs that will be processed by each container.
    """
    with open(filter_file, "r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def compute_round_timeout(timeout: int, n_apks: int) -> int:
    """Compute a round timeout based on the number of APKs each container processes.

    Each container runs n_apks tasks sequentially. Each task takes approximately
    ``timeout + TASK_OVERHEAD_SECONDS`` seconds (tool execution + emulator
    boot/teardown). A safety margin is applied to account for variance in
    emulator boot times and I/O contention when many containers run in parallel.

    Args:
        timeout: Per-APK tool timeout in seconds.
        n_apks: Number of APKs each container will process.

    Returns:
        Round timeout in seconds (integer).
    """
    per_task = timeout + TASK_OVERHEAD_SECONDS
    return int(n_apks * per_task * ROUND_TIMEOUT_SAFETY_MARGIN)


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
        free_gb = disk.free / (1024**3)
        sys.exit(
            f"Insufficient disk space: {free_gb:.1f} GB free, "
            f"need at least {MIN_DISK_SPACE_BYTES / (1024 ** 3):.0f} GB"
        )


def compute_score_for_trial(
    trial_num: int,
    output_dir: str,
    objective_fn=None,
) -> float:
    """
    Compute the objective score for a single completed trial.

    The rv-experiment container writes results into
    ``{output_dir}/trial_{N}/trial_{N}/`` (the inner directory is created by
    rv-experiment using ``RV_EXPERIMENT_NAME``).

    For aperv tools, uses the aperv_objective.compute_score function directly.
    For rvagent tools, uses the ObjectiveFunction instance.

    Args:
        trial_num: Optuna trial number.
        output_dir: Base calibration output directory.
        objective_fn: Objective function instance (rvagent) or None (aperv).

    Returns:
        Objective score (0-100 scale).
    """
    # Double nesting: outer dir is the Docker volume mount target, inner dir is
    # created by rv-experiment using RV_EXPERIMENT_NAME (which we set to trial_N)
    results_dir = Path(output_dir) / f"trial_{trial_num}" / f"trial_{trial_num}"
    summary_csv = results_dir / "summary.csv"
    if not summary_csv.exists():
        raise FileNotFoundError(f"No summary.csv for trial {trial_num}: {summary_csv}")

    if _compute_aperv_score is not None:
        return _compute_aperv_score(str(results_dir))
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

    # param_string.txt -- ready to paste into --tools <tool>@<spec>
    with open(out / "param_string.txt", "w", encoding="utf-8") as f:
        f.write(_params_to_tool_spec(best_trial.params))
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
    """Build the argument parser for the calibration orchestrator CLI.

    Returns:
        Configured ``ArgumentParser`` with all calibration options.
    """
    parser = argparse.ArgumentParser(
        description="Docker-based calibration orchestrator for RVAgent parameters.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--tool",
        type=str,
        default="rvagent",
        help="Tool family to calibrate. For rvagent: 'rvagent' (uses --agent-mode). "
        "For APE-RV: 'aperv:sata_mop' (MACRO, no LLM) or 'aperv:sata_mop_llm' (MICRO, with LLM). "
        "Default: rvagent.",
    )
    parser.add_argument(
        "--phase",
        choices=["macro", "micro"],
        required=True,
        help="Calibration phase: macro tunes high-impact params, micro tunes fine-tuning params.",
    )
    parser.add_argument(
        "--param-version",
        choices=["v1", "v2"],
        default="v1",
        help="Parameter space version. v1: 14 params (original). "
        "v2: 10 tuned + 6 fixed (calibration v2). Default: v1.",
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
        "--reps",
        type=int,
        default=1,
        help="Repetitions per APK per trial (default: 1). "
        "With reps=2, each APK runs twice; scoring averages reps before trimmed mean.",
    )
    parser.add_argument(
        "--storage",
        type=str,
        default=None,
        help="Optuna storage URL. Default: SQLite in output-dir. "
        "For multi-VM: postgresql://user:pass@host:5432/db",
    )
    parser.add_argument(
        "--jar-path",
        type=str,
        default=None,
        help="Host path to ape-rv.jar for volume mounting (GCP calibration).",
    )
    parser.add_argument(
        "--broadcast-path",
        type=str,
        default=None,
        help="Host path to system-broadcast.json for volume mounting.",
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
        default="phtcosta/rvandroid:0.9.2",
        help="Docker image for trial containers (default: phtcosta/rvandroid:0.9.2).",
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
    parser.add_argument(
        "--sglang-url",
        type=str,
        default=None,
        help="SGLang server URL reachable from containers (e.g. http://host.docker.internal:30000/v1). "
        "Injects llm_base_url into the tool spec for multimode agents.",
    )
    parser.add_argument(
        "--no-enqueue-defaults",
        action="store_true",
        help="Skip injecting default parameter values as the first trial (warm-starting).",
    )
    parser.add_argument(
        "--convergence-rounds",
        type=int,
        default=5,
        help="Stop early if best score hasn't improved for this many rounds (default: 5). "
        "Set to 0 to disable convergence monitoring.",
    )
    return parser


def main() -> None:
    """Run the calibration orchestrator main loop.

    Orchestrates the full Optuna-based calibration workflow:

    1. Parse CLI arguments and validate preconditions.
    2. Create or resume an Optuna study (SQLite-backed for crash resilience).
    3. Optionally warm-start the study with default parameter values.
    4. Loop: ask Optuna for N trial suggestions, generate a docker-compose file,
       launch containers in parallel, wait for completion, score results, and
       report scores back to Optuna.
    5. Stop when all trials are complete or early convergence is detected.
    6. Save best parameters, tool spec string, and full trial history to disk.

    Raises:
        SystemExit: If precondition checks fail (missing data, insufficient disk).
    """
    args = _build_parser().parse_args()

    # --- Setup ---
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Log to both console and file so the orchestrator log survives disconnects
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(output_dir / "orchestrator.log"),
        ],
    )

    # --- Load tool-specific modules ---
    _load_tool_modules(args.tool, param_version=args.param_version)
    is_aperv = args.tool.startswith("aperv")

    logger.info("=" * 60)
    logger.info("Calibration Orchestrator")
    logger.info(
        f"Tool: {args.tool}, Phase: {args.phase}, Trials: {args.n_trials}, Containers/round: {args.n_containers}"
    )
    logger.info(f"Data: {args.data_dir}, Output: {args.output_dir}")
    logger.info("=" * 60)

    # --- Micro phase requires best-macro ---
    if args.phase == "micro" and args.best_macro is None:
        sys.exit("--best-macro is required for --phase micro")

    # --- Preflight ---
    preflight_checks(args.data_dir, args.filter_file, args.agent_mode)

    # --- Objective function ---
    objective_fn = None
    if not is_aperv:
        baseline_max_errors: Optional[float] = None
        if args.baseline_dir:
            baseline_max_errors = _ObjectiveFunction.compute_baseline_max_errors(
                args.baseline_dir
            )
            logger.info(f"Baseline max errors: {baseline_max_errors:.2f}")

        objective_fn = _ObjectiveFunction(
            coverage_weight=0.40,
            errors_weight=0.40,
            ui_coverage_weight=0.20,
            baseline_max_errors=baseline_max_errors,
        )

    # --- Optuna study (SQLite local or PostgreSQL for multi-VM) ---
    if args.storage:
        storage_url = args.storage
    else:
        storage_path = output_dir / "optuna_study.db"
        storage_url = f"sqlite:///{storage_path}"
    study_name = f"calibration_{args.phase}_{args.seed}"

    # constant_liar=True: allows asking for N trials before reporting results,
    # which is needed because we run N containers in parallel per round.
    # multivariate=True: models parameter correlations (e.g., epsilon vs throttle).
    # n_startup_trials: random exploration before TPE kicks in -- set to 2 rounds
    # worth of containers to ensure a diverse initial sample.
    sampler = optuna.samplers.TPESampler(
        seed=args.seed,
        constant_liar=True,
        multivariate=True,
        n_startup_trials=2 * args.n_containers,
    )
    study = optuna.create_study(
        study_name=study_name,
        storage=storage_url,
        sampler=sampler,
        direction="maximize",
        load_if_exists=True,
    )
    logger.info(f"Optuna study: {study_name} (storage: {storage_url})")

    # --- Map phase string to enum ---
    phase = (
        _CalibrationPhase.MACRO if args.phase == "macro" else _CalibrationPhase.MICRO
    )

    # --- Load fixed params for micro phase ---
    fixed_params: Dict[str, Any] = {}
    if args.best_macro:
        with open(args.best_macro, "r", encoding="utf-8") as f:
            macro_results = json.load(f)
        fixed_params = macro_results["best_params"]
        logger.info(
            f"Loaded {len(fixed_params)} fixed macro params from {args.best_macro}"
        )

    # --- Warm-starting: enqueue default params as first trial ---
    # Only on fresh runs (not resume) with no completed trials yet.
    # Gives the TPE a known baseline to learn from instead of pure random.
    existing_trials = len(study.trials)
    if not args.resume and not args.no_enqueue_defaults and existing_trials == 0:
        default_params = _get_default_params(phase)
        if fixed_params:
            default_params = {**fixed_params, **default_params}
        study.enqueue_trial(default_params)
        logger.info(f"Enqueued default params as warm-start trial: {default_params}")

    # --- Resume: recover orphaned trials ---
    if args.resume:
        recovered = recover_orphaned_trials(study, str(output_dir), objective_fn)
        logger.info(f"Recovered {recovered} orphaned trial(s)")

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
    rounds_without_improvement = 0
    best_score_so_far = -float("inf")
    n_apks = count_filter_apks(args.filter_file)
    n_tasks_per_trial = n_apks * args.reps
    round_timeout = compute_round_timeout(args.timeout, n_tasks_per_trial)
    logger.info(
        f"Round timeout: {round_timeout}s ({round_timeout / 3600:.1f}h) "
        f"for {n_apks} APKs × {args.reps} reps = {n_tasks_per_trial} tasks"
    )

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
            params = _suggest_params(trial, phase)

            # Merge layers (lowest to highest priority):
            # 1. FIXED_PARAMS_V2 (when --param-version v2): fixed low-impact params
            # 2. fixed_params (from --best-macro): optimal macro params for micro phase
            # 3. params (from Optuna): the trial's suggested values
            merged = {}
            if _fixed_params_v2:
                merged.update(_fixed_params_v2)
            if fixed_params:
                merged.update(fixed_params)
            merged.update(params)

            param_str = _params_to_tool_spec(merged)
            # SGLang URL is injected into the tool spec so the container can
            # reach the LLM server on the host via host.docker.internal
            if args.sglang_url and not is_aperv:
                param_str += f",llm_base_url={args.sglang_url}"

            # Build tool spec DSL: aperv uses the --tool value directly (e.g.
            # "aperv:sata_mop"), while rvagent needs the agent_mode appended
            # as a variant (e.g. "rvagent:pure_algorithm")
            if is_aperv:
                tool_spec = f"{args.tool}@{param_str}"
            else:
                tool_spec = f"rvagent:{args.agent_mode}@{param_str}"
            batch.append((trial.number, tool_spec))
            logger.info(f"  Trial {trial.number}: {tool_spec[:120]}...")

        # Generate docker-compose file for this round
        needs_sglang = args.sglang_url is not None
        extra_hosts = ["host.docker.internal:host-gateway"] if needs_sglang else None
        compose_dict = generate_calibration_compose(
            batch=batch,
            data_dir=str(Path(args.data_dir).resolve()),
            filter_file=str(Path(args.filter_file).resolve()),
            output_dir=str(output_dir.resolve()),
            image=args.image,
            cpus=args.cpus,
            memory=args.memory,
            timeout=args.timeout,
            extra_hosts=extra_hosts,
            reps=args.reps,
            jar_path=args.jar_path,
            broadcast_path=args.broadcast_path,
        )

        compose_path = output_dir / f"docker-compose.round-{round_number:02d}.yml"
        with open(compose_path, "w", encoding="utf-8") as f:
            yaml.dump(compose_dict, f, default_flow_style=False, sort_keys=False)
        logger.info(f"Compose file: {compose_path}")

        # Launch containers and wait for completion
        logger.info(f"Launching {batch_size} container(s)...")
        start_time = time.monotonic()

        # check=False: we handle failures via Optuna scoring (no summary.csv = FAIL).
        # The finally block ensures containers are torn down even on timeout,
        # freeing resources (KVM, memory) for the next round.
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
                score = compute_score_for_trial(
                    trial.number, str(output_dir), objective_fn
                )
                study.tell(trial.number, score)
                logger.info(f"  Trial {trial.number} -> score {score:.2f}")
            except Exception as e:
                study.tell(trial.number, state=TrialState.FAIL)
                logger.warning(f"  Trial {trial.number} FAILED: {e}")

        # Update remaining count
        completed_count = len(
            [t for t in study.trials if t.state == TrialState.COMPLETE]
        )
        failed_count = len(
            [t for t in study.trials if t.state == TrialState.FAIL]
        )
        remaining = args.n_trials - completed_count
        logger.info(
            f"Progress: {completed_count}/{args.n_trials} complete, {failed_count} failed"
        )

        # Safety: if too many trials are failing, stop. This catches infrastructure
        # bugs (docker compose syntax, missing image, etc.) that would otherwise
        # cause the orchestrator to loop forever asking for replacement trials.
        max_failures = max(args.n_trials, 10)
        if failed_count >= max_failures:
            logger.error(
                f"Aborting: {failed_count} failed trials exceeds threshold "
                f"({max_failures}). Check docker, image, and compose syntax."
            )
            break

        # Convergence monitoring: stop if best score hasn't improved for N rounds
        if args.convergence_rounds > 0 and completed_count > 0:
            current_best = study.best_value
            if current_best > best_score_so_far:
                best_score_so_far = current_best
                rounds_without_improvement = 0
            else:
                rounds_without_improvement += 1

            if rounds_without_improvement >= args.convergence_rounds:
                logger.info(
                    f"Convergence: best score ({best_score_so_far:.2f}) unchanged for "
                    f"{rounds_without_improvement} rounds. Stopping early."
                )
                break

    # --- Save results ---
    _save_results(study, args.phase, args.seed, args.n_trials, str(output_dir))
    _print_summary(study)


def _print_summary(study: optuna.Study) -> None:
    """Print a human-readable summary of the calibration run.

    Args:
        study: Completed Optuna study to summarize.
    """
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
        logger.info(f"  Tool spec:        {_params_to_tool_spec(best.params)}")

    logger.info("=" * 60)


if __name__ == "__main__":
    main()
