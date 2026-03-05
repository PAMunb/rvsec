#!/usr/bin/env python3
"""Optuna calibration for rvsmart hyperparameters.

Generates rvsmart.properties from a trial, pushes it to the emulator, runs rvsmart,
parses the RVSMART_METRICS: JSON line from stdout, and returns an objective value.

### Objective

Maximize: throughput_evt_per_s * (unique_states / elapsed_s)

Constraints (violations return -inf):
  - crash_rate > 1%  (too unstable)

### Metrics Format (from MetricsCollector.writeFinalReport, INV-RSM-10)

  RVSMART_METRICS: {
    "exploration": {
      "iterations": int,
      "execution_time_s": float,
      "unique_states": int,
      "total_transitions": int,
      "throughput_evt_per_s": float
    },
    "decisions": {
      "total_actions": int,
      "algorithm_actions": int,
      "llm_actions": int,
      "crashes": int,
      "forced_backs": int,
      ...
    },
    "ui_coverage": { ... },
    "confirmed_coverage": { ... },
    "llm": { ... }
  }

### Tunable Parameters and Defaults (from Config.java)

See PARAM_RANGES dict below. All parameters map 1:1 to rvsmart.properties keys.

### Usage

    # Single-package calibration
    python optuna_calibration.py --package br.unb.cic.cryptoapp --timeout 120 --n-trials 50

    # Multi-package calibration (averages objective across packages)
    python optuna_calibration.py \\
        --packages br.unb.cic.cryptoapp,org.secuso.privacyfriendlysudoku \\
        --timeout 120 --n-trials 100 --output rvsmart_best.properties

    # Resume an existing study
    python optuna_calibration.py --package br.unb.cic.cryptoapp \\
        --storage sqlite:///rvsmart_calibration.db \\
        --study-name rvsmart_v1 --n-trials 200

Requirements:
    pip install optuna
    adb must be on PATH and a device/emulator running
    rvsmart.jar must be deployed to /data/local/tmp/rvsmart.jar on device
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

try:
    import optuna
    from optuna.samplers import TPESampler
except ImportError:
    print("ERROR: optuna not installed. Run: pip install optuna")
    sys.exit(1)

# Path on the Android device where rvsmart JAR is deployed.
RVSMART_JAR_DEVICE = "/data/local/tmp/rvsmart.jar"

# Path on device for the properties file pushed per trial.
RVSMART_PROPS_DEVICE = "/sdcard/rvsmart_trial.properties"

# Tunable parameter ranges: (low, high).
# Float ranges use suggest_float; int ranges use suggest_int.
# All names match Config.java property keys exactly.
PARAM_RANGES: dict[str, tuple] = {
    # Execution
    "throttle_ms":                       (50,    500),    # int
    # Scorer weights
    "gradual_decay_base":                (50.0,  500.0),  # float
    "gradual_decay_rate":                (0.3,   0.95),   # float
    "gradual_decay_min_visits":          (3,     20),     # int
    "mop_direct_score":                  (100.0, 1000.0), # float
    "mop_transitive_score":              (50.0,  500.0),  # float
    "coverage_density_weight":           (50.0,  500.0),  # float
    "saturation_bonus":                  (20.0,  300.0),  # float
    "component_high_priority":           (10.0,  200.0),  # float
    "component_medium_priority":         (5.0,   150.0),  # float
    "strength_weight":                   (10.0,  200.0),  # float
    "reward_score_weight":               (0.1,   5.0),    # float
    "visitation_penalty_factor":         (5.0,   50.0),   # float
    # Synthetic actions
    "back_decay_per_repeat":             (50.0,  500.0),  # float
    # Reward propagation
    "reward_gamma":                      (0.5,   0.99),   # float
    "reward_propagation_n":              (3,     15),     # int
    "reward_mop_weight":                 (1.0,   15.0),   # float
    # Successor tracker / backtrack
    "multi_value_saturation_threshold":  (2,     10),     # int
    "ui_coverage_threshold":             (0.5,   0.95),   # float
    "backtrack_saturation_threshold":    (0.5,   0.95),   # float
    "max_backtrack_hops":                (3,     20),     # int
    # Stuck detection
    "stuck_max_blocks":                  (3,     20),     # int
}


def _is_float_param(name: str, low: float, high: float) -> bool:
    """Return True if the parameter should use suggest_float."""
    return isinstance(low, float) or isinstance(high, float)


def generate_properties_from_trial(trial) -> dict:
    """Suggest values for all PARAM_RANGES using the Optuna trial."""
    params = {}
    for name, (low, high) in PARAM_RANGES.items():
        if _is_float_param(name, low, high):
            params[name] = trial.suggest_float(name, float(low), float(high))
        else:
            params[name] = trial.suggest_int(name, int(low), int(high))
    return params


def write_properties_file(params: dict, path: str):
    """Write a Java-style .properties file from a dict.

    Lines are sorted for reproducibility. Comments are not preserved on re-read
    (java.util.Properties ignores them), but help with human inspection.
    """
    with open(path, "w") as f:
        f.write("# Auto-generated by optuna_calibration.py\n")
        f.write("# Do not edit manually — re-run calibration to regenerate.\n")
        for key in sorted(params):
            value = params[key]
            # Write floats with enough precision to avoid rounding loss
            if isinstance(value, float):
                f.write(f"{key}={value:.6f}\n")
            else:
                f.write(f"{key}={value}\n")


def push_properties(local_path: str) -> bool:
    """Push properties file to device. Returns True on success."""
    result = subprocess.run(
        ["adb", "push", local_path, RVSMART_PROPS_DEVICE],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  WARNING: adb push failed: {result.stderr.strip()}")
        return False
    return True


def run_rvsmart(package: str, timeout: int, mode: str = "pure_algorithm") -> dict | None:
    """Run rvsmart on the device and extract the RVSMART_METRICS JSON.

    rvsmart is invoked via app_process which runs the JAR as a host process
    (not installed as an APK). The APK under test must already be installed.

    Returns the parsed metrics dict, or None if execution failed or no metrics
    line was found in stdout.
    """
    cmd = [
        "adb", "shell",
        f"CLASSPATH={RVSMART_JAR_DEVICE}",
        "/system/bin/app_process", "/",
        "br.unb.cic.rvsmart.Main",
        "--package", package,
        "--timeout", str(timeout),
        "--config", RVSMART_PROPS_DEVICE,
        "--mode", mode,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            # Extra buffer beyond rvsmart timeout for startup/shutdown overhead
            timeout=timeout + 60,
        )
    except subprocess.TimeoutExpired:
        print(f"  WARNING: subprocess timed out for {package}")
        return None

    # Extract RVSMART_METRICS: line — always the last output line (INV-RSM-10)
    for line in reversed(result.stdout.splitlines()):
        line = line.strip()
        if line.startswith("RVSMART_METRICS:"):
            metrics_json = line[len("RVSMART_METRICS:"):]
            try:
                return json.loads(metrics_json)
            except json.JSONDecodeError as e:
                print(f"  WARNING: Failed to parse metrics JSON: {e}")
                print(f"  Raw: {metrics_json[:200]}")
                return None

    print(f"  WARNING: No RVSMART_METRICS line found for {package}")
    if result.returncode != 0:
        print(f"  stderr: {result.stderr.strip()[:300]}")
    return None


def _compute_objective_value(metrics: dict) -> float:
    """Compute objective from metrics dict.

    Objective = throughput_evt_per_s * (unique_states / elapsed_s)
    Penalizes trials with crash_rate > 1% by returning -inf.

    This formulation rewards both speed (throughput) and exploration breadth
    (unique_states / elapsed_s = state discovery rate).
    """
    exploration = metrics.get("exploration", {})
    decisions = metrics.get("decisions", {})

    elapsed_s = max(exploration.get("execution_time_s", 1.0), 1.0)
    unique_states = exploration.get("unique_states", 0)
    throughput = exploration.get("throughput_evt_per_s", 0.0)
    total_actions = max(decisions.get("total_actions", 1), 1)
    crashes = decisions.get("crashes", 0)

    crash_rate = crashes / total_actions
    if crash_rate > 0.01:
        return float("-inf")

    state_discovery_rate = unique_states / elapsed_s
    return throughput * state_discovery_rate


def objective_single(trial, package: str, timeout: int,
                     mode: str = "pure_algorithm") -> float:
    """Optuna objective for a single package."""
    params = generate_properties_from_trial(trial)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".properties", delete=False
    ) as f:
        write_properties_file(params, f.name)
        local_path = f.name

    try:
        if not push_properties(local_path):
            return float("-inf")

        metrics = run_rvsmart(package, timeout, mode)
    finally:
        os.unlink(local_path)

    if metrics is None:
        return float("-inf")

    value = _compute_objective_value(metrics)
    # Report intermediate metrics as trial user attributes for analysis
    exploration = metrics.get("exploration", {})
    trial.set_user_attr("unique_states", exploration.get("unique_states", 0))
    trial.set_user_attr("throughput", exploration.get("throughput_evt_per_s", 0.0))
    trial.set_user_attr("crashes", metrics.get("decisions", {}).get("crashes", 0))

    return value


def objective_multi(trial, packages: list[str], timeout: int,
                    mode: str = "pure_algorithm") -> float:
    """Optuna objective averaged across multiple packages.

    Suggests parameters once (shared across packages), then averages the objective
    across all packages. Trials where ANY package returns -inf are penalized as -inf.
    """
    params = generate_properties_from_trial(trial)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".properties", delete=False
    ) as f:
        write_properties_file(params, f.name)
        local_path = f.name

    try:
        if not push_properties(local_path):
            return float("-inf")

        values = []
        for pkg in packages:
            metrics = run_rvsmart(pkg, timeout, mode)
            if metrics is None:
                return float("-inf")
            value = _compute_objective_value(metrics)
            if value == float("-inf"):
                return float("-inf")
            values.append(value)
    finally:
        os.unlink(local_path)

    avg = sum(values) / len(values)
    trial.set_user_attr("packages_tested", len(values))
    return avg


def main():
    parser = argparse.ArgumentParser(
        description="Optuna calibration for rvsmart hyperparameters",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--package", help="Single APK package name")
    group.add_argument("--packages",
                       help="Comma-separated package names (averaged objective)")
    parser.add_argument("--timeout", type=int, default=120,
                        help="Timeout per trial in seconds (default: 120)")
    parser.add_argument("--n-trials", type=int, default=50,
                        help="Number of Optuna trials (default: 50)")
    parser.add_argument("--mode", default="pure_algorithm",
                        choices=["pure_algorithm", "llm_only", "multimode"],
                        help="rvsmart execution mode (default: pure_algorithm)")
    parser.add_argument("--output", default="rvsmart_best.properties",
                        help="Output properties file for best parameters "
                             "(default: rvsmart_best.properties)")
    parser.add_argument("--storage",
                        help="Optuna storage URL for persistence, e.g. "
                             "sqlite:///rvsmart_calibration.db")
    parser.add_argument("--study-name", default="rvsmart_calibration",
                        help="Optuna study name (default: rvsmart_calibration)")
    parser.add_argument("--n-jobs", type=int, default=1,
                        help="Parallel trials (default: 1; >1 requires shared storage)")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable Optuna INFO logging")
    args = parser.parse_args()

    if not args.package and not args.packages:
        parser.error("Specify --package or --packages")

    if not args.verbose:
        optuna.logging.set_verbosity(optuna.logging.WARNING)

    packages = (
        [p.strip() for p in args.packages.split(",") if p.strip()]
        if args.packages
        else [args.package]
    )

    print(f"Calibrating rvsmart for: {packages}")
    print(f"  trials={args.n_trials}, timeout_per_trial={args.timeout}s, mode={args.mode}")
    print(f"  study={args.study_name}, storage={args.storage or 'in-memory'}")
    print()

    study = optuna.create_study(
        direction="maximize",
        sampler=TPESampler(seed=42),
        study_name=args.study_name,
        storage=args.storage,
        load_if_exists=True,
    )

    if len(packages) == 1:
        obj = lambda trial: objective_single(
            trial, packages[0], args.timeout, args.mode
        )
    else:
        obj = lambda trial: objective_multi(
            trial, packages, args.timeout, args.mode
        )

    study.optimize(obj, n_trials=args.n_trials, n_jobs=args.n_jobs,
                   show_progress_bar=True)

    print(f"\nCompleted {len(study.trials)} trials")

    finished = [t for t in study.trials
                if t.value is not None and t.value != float("-inf")]
    if not finished:
        print("All trials failed (returned -inf). Check adb connectivity and rvsmart.jar.")
        sys.exit(1)

    best = study.best_trial
    print(f"Best trial #{best.number}: objective={best.value:.4f}")
    print(f"Best params:")
    for k, v in sorted(best.params.items()):
        print(f"  {k}={v}")

    write_properties_file(best.params, args.output)
    print(f"\nBest parameters written to: {args.output}")

    # Print top-5 trials summary
    sorted_trials = sorted(finished, key=lambda t: t.value, reverse=True)[:5]
    print("\nTop-5 trials:")
    for i, t in enumerate(sorted_trials, 1):
        states = t.user_attrs.get("unique_states", "?")
        throughput = t.user_attrs.get("throughput", "?")
        crashes = t.user_attrs.get("crashes", "?")
        print(f"  #{i} trial={t.number} value={t.value:.4f} "
              f"states={states} throughput={throughput} crashes={crashes}")


if __name__ == "__main__":
    main()
