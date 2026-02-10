#!/usr/bin/env python3
"""
Fase A: Parallel preprocessing of APKs for validation framework.

Orchestrates three sequential macro phases with internal parallelism:
1. Generate JCA monitors (sequential, ~2 min)
2. Instrument APKs with monitors (parallel, N workers)
3. Run static analysis on original APKs (parallel via filter_apks_static_analysis.py)

Usage:
    python scripts/validation/fase_a_preprocess.py \
        --apks-dir /home/pedro/desenvolvimento/RV_ANDROID/NOVO/APKS \
        --apks-filter ./out/static_analysis_filter/passed_apks.txt \
        --specification-set jca \
        --output-dir ./results/preprocessing_v2 \
        --max-workers 6
"""

import argparse
import logging
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Phase 1: Monitor Generation
# ---------------------------------------------------------------------------

def generate_monitors(rvsec_root: str, specification_set: str, output_dir: str) -> str:
    """
    Generate RV monitors from MOP specifications. One-time, sequential.

    Args:
        rvsec_root: RVSEC installation root directory.
        specification_set: Specification set name (jca or generic).
        output_dir: Base output directory for preprocessing.

    Returns:
        Path to the generated monitors directory.
    """
    from rv_monitor_generator.runtime_verification_generator import RuntimeVerificationGenerator
    from rv_monitor_generator.config import RVGeneratorConfig

    specs_dir = os.path.join(
        rvsec_root, "rvsec", "rvsec-mop", "src", "main", "resources", specification_set
    )
    monitors_dir = os.path.join(output_dir, "monitors")
    os.makedirs(monitors_dir, exist_ok=True)

    log.info("Phase 1: Generating monitors from %s", specs_dir)
    start = time.time()

    config = RVGeneratorConfig(mop_specs_dir=specs_dir, rvsec_root=rvsec_root)
    generator = RuntimeVerificationGenerator(config)
    success = generator.generate_monitors(monitors_dir)

    elapsed = time.time() - start
    if not success:
        raise RuntimeError(f"Monitor generation failed after {elapsed:.0f}s")

    log.info("Phase 1 complete: monitors generated in %.0fs", elapsed)
    return monitors_dir


# ---------------------------------------------------------------------------
# Phase 2: Parallel Instrumentation
# ---------------------------------------------------------------------------

def prepare_instrumentation(rvsec_root: str, monitors_dir: str, output_dir: str) -> dict:
    """
    Run Maven dependency resolution once and return shared config paths.

    The returned dict is picklable for passing to worker processes.

    Args:
        rvsec_root: RVSEC installation root directory.
        monitors_dir: Directory with generated monitor artifacts.
        output_dir: Base output directory for preprocessing.

    Returns:
        Dict with shared paths for workers.
    """
    from rv_instrumentation import RVInstrumentation, RVInstrumentationConfig

    rv_android_dir = os.path.join(rvsec_root, "rv-android")
    instrumented_dir = os.path.join(output_dir, "instrumented_apks")
    os.makedirs(instrumented_dir, exist_ok=True)

    log.info("Phase 2: Preparing instrumentation environment (Maven + lib_tmp)")

    config = RVInstrumentationConfig(
        rvsec_root=rvsec_root,
        monitor_output_dir=monitors_dir,
        working_dir=rv_android_dir,
        instrumented_dir=instrumented_dir,
    )

    instr = RVInstrumentation(config)
    instr.prepare_instrumentation(instrumented_dir)

    # Return shared paths for workers (picklable plain dict)
    return {
        "rvsec_root": rvsec_root,
        "monitors_dir": monitors_dir,
        "instrumented_dir": instrumented_dir,
        "lib_tmp_dir": config.lib_tmp_dir,
        "dex2jar_home": config.dex2jar_home,
        "android_jar_path": config.android_jar_path,
        "android_platforms_dir": config.android_platforms_dir,
        "keystore_file": config.keystore_file,
        "keystore_password": config.keystore_password or "password",
        "workers_base_dir": os.path.join(output_dir, "workers"),
    }


def instrument_apk_worker(args: tuple) -> dict:
    """
    Worker function: instrument a single APK with isolated temp dirs.

    Each worker process uses a directory based on its PID to avoid race
    conditions with d8 (which generates classes.dex in CWD) and tmp/rvm_tmp
    dirs. ProcessPoolExecutor reuses processes sequentially, so PID-based
    dirs are safe — only one task runs per process at a time.

    Args:
        args: Tuple of (apk_path, shared_config_dict).

    Returns:
        Dict with apk name, success status, and error message.
    """
    apk_path, shared = args

    from rv_instrumentation import RVInstrumentation, RVInstrumentationConfig
    from rv_android_core.domain.app import App

    apk_name = os.path.basename(apk_path)
    worker_dir = os.path.join(shared["workers_base_dir"], f"worker_{os.getpid()}")
    os.makedirs(worker_dir, exist_ok=True)

    original_cwd = os.getcwd()
    os.chdir(worker_dir)  # Isolate d8 output (classes.dex) per worker

    try:
        config = RVInstrumentationConfig(
            rvsec_root=shared["rvsec_root"],
            monitor_output_dir=shared["monitors_dir"],
            working_dir=worker_dir,
            instrumented_dir=shared["instrumented_dir"],
            lib_tmp_dir=shared["lib_tmp_dir"],  # Shared, read-only after Maven
            dex2jar_home=shared["dex2jar_home"],  # Shared, read-only
            android_jar_path=shared["android_jar_path"],
            android_platforms_dir=shared["android_platforms_dir"],
            keystore_file=shared["keystore_file"],
            keystore_password=shared["keystore_password"],
        )

        instr = RVInstrumentation(config)
        app = App(apk_path)
        config.validate_apk_input(app.path)
        instr.instrument(app, shared["instrumented_dir"])
        instr.check_if_instrumented(app)

        # Verify instrumented APK actually exists (ErrorHandler may swallow exceptions)
        instrumented_path = os.path.join(shared["instrumented_dir"], apk_name)
        if not os.path.isfile(instrumented_path):
            return {"apk": apk_name, "ok": False, "error": "instrumented APK not produced"}

        return {"apk": apk_name, "ok": True, "error": ""}
    except Exception as e:
        return {"apk": apk_name, "ok": False, "error": str(e)[:500]}
    finally:
        os.chdir(original_cwd)
        # Cleanup worker temp dirs (not worker_dir itself — reused by pool)
        for d in [os.path.join(worker_dir, "tmp"), os.path.join(worker_dir, "rvm_tmp")]:
            if os.path.exists(d):
                shutil.rmtree(d, ignore_errors=True)


def run_parallel_instrumentation(
    apk_paths: list, shared_config: dict, max_workers: int
) -> list:
    """
    Instrument APKs in parallel using ProcessPoolExecutor.

    Assigns worker_id by index modulo max_workers to reuse worker dirs.

    Args:
        apk_paths: List of APK file paths to instrument.
        shared_config: Shared configuration dict from prepare_instrumentation().
        max_workers: Number of parallel workers.

    Returns:
        List of result dicts with apk name, success status, and error.
    """
    results = []
    total = len(apk_paths)
    tasks = [(path, shared_config) for path in apk_paths]

    log.info("Phase 2: Instrumenting %d APKs with %d workers", total, max_workers)
    start = time.time()

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_apk = {executor.submit(instrument_apk_worker, t): t[0] for t in tasks}
        for future in as_completed(future_to_apk):
            result = future.result()
            results.append(result)
            status = "OK" if result["ok"] else "FAIL"
            log.info(
                "[%d/%d] %s %s %s",
                len(results),
                total,
                status,
                result["apk"],
                result["error"] if not result["ok"] else "",
            )

    elapsed = time.time() - start
    ok_count = sum(1 for r in results if r["ok"])
    log.info(
        "Phase 2 complete: %d/%d instrumented in %.0fs (%.1fh)",
        ok_count, total, elapsed, elapsed / 3600,
    )
    return results


# ---------------------------------------------------------------------------
# Phase 3: Static Analysis
# ---------------------------------------------------------------------------

def run_static_analysis(
    apks_dir: str,
    successful_apks: list,
    output_dir: str,
    max_workers: int,
    timeout: int = 600,
) -> None:
    """
    Run static analysis via filter_apks_static_analysis.py subprocess.

    Runs on original (non-instrumented) APKs for the successfully
    instrumented set. Uses --resume to skip APKs with existing results.

    Args:
        apks_dir: Directory with original APK files.
        successful_apks: List of APK filenames that were successfully instrumented.
        output_dir: Base output directory for preprocessing.
        max_workers: Number of parallel workers for static analysis.
        timeout: Timeout per tool in seconds.
    """
    static_dir = os.path.join(output_dir, "static_analysis")
    os.makedirs(static_dir, exist_ok=True)

    # Write list of successfully instrumented APK names (without .apk extension)
    apks_list_file = os.path.join(output_dir, "instrumented_apks_list.txt")
    with open(apks_list_file, "w") as f:
        for name in sorted(successful_apks):
            f.write(os.path.splitext(name)[0] + "\n")

    log.info(
        "Phase 3: Running static analysis on %d APKs with %d workers",
        len(successful_apks), max_workers,
    )
    start = time.time()

    # Find script relative to this file's location
    project_root = Path(__file__).resolve().parent.parent.parent
    script_path = project_root / "scripts" / "filter_apks_static_analysis.py"

    cmd = [
        sys.executable,
        str(script_path),
        "--apks-dir", apks_dir,
        "--apks-list", apks_list_file,
        "--output-dir", static_dir,
        "--max-workers", str(max_workers),
        "--timeout", str(timeout),
        "--resume",
    ]

    log.info("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd)

    elapsed = time.time() - start
    if result.returncode != 0:
        log.warning("Static analysis exited with code %d after %.0fs", result.returncode, elapsed)
    else:
        log.info("Phase 3 complete: static analysis finished in %.0fs (%.1fh)", elapsed, elapsed / 3600)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def write_summary(
    output_dir: str,
    apk_paths: list,
    instr_results: list,
    total_elapsed: float,
) -> None:
    """Write preprocessing summary to output directory."""
    ok = [r for r in instr_results if r["ok"]]
    failed = [r for r in instr_results if not r["ok"]]

    summary_path = os.path.join(output_dir, "summary.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("Fase A: Parallel Preprocessing - Summary\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total APKs in filter: {len(apk_paths)}\n")
        f.write(f"Instrumented OK:      {len(ok)}\n")
        f.write(f"Instrumented FAIL:    {len(failed)}\n")
        f.write(f"Total elapsed time:   {total_elapsed:.0f}s ({total_elapsed/3600:.1f}h)\n\n")

        if failed:
            f.write("Failed APKs:\n")
            for r in sorted(failed, key=lambda x: x["apk"]):
                f.write(f"  {r['apk']}: {r['error'][:200]}\n")

    log.info("Summary written to %s", summary_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Fase A: Parallel APK preprocessing (monitors + instrumentation + static analysis)",
    )
    parser.add_argument("--apks-dir", required=True, help="Directory with original APK files")
    parser.add_argument(
        "--apks-filter", required=True,
        help="Text file with APK names (one per line, without .apk extension)",
    )
    parser.add_argument(
        "--specification-set", default="jca", choices=["jca", "generic"],
        help="MOP specification set (default: jca)",
    )
    parser.add_argument("--output-dir", required=True, help="Output directory for all artifacts")
    parser.add_argument(
        "--max-workers", type=int, default=6,
        help="Number of parallel workers (default: 6)",
    )
    parser.add_argument(
        "--sa-timeout", type=int, default=600,
        help="Static analysis timeout per tool in seconds (default: 600)",
    )
    parser.add_argument(
        "--skip-monitors", action="store_true",
        help="Skip monitor generation (reuse existing monitors in output-dir/monitors)",
    )
    parser.add_argument(
        "--skip-instrumentation", action="store_true",
        help="Skip instrumentation (reuse existing instrumented APKs)",
    )
    parser.add_argument(
        "--skip-static", action="store_true",
        help="Skip static analysis phase",
    )
    args = parser.parse_args()

    total_start = time.time()

    # Convert paths to absolute (workers change CWD, so relative paths would break)
    args.output_dir = os.path.abspath(args.output_dir)
    args.apks_dir = os.path.abspath(args.apks_dir)
    args.apks_filter = os.path.abspath(args.apks_filter)

    # Resolve RVSEC_HOME
    rvsec_root = os.environ.get(
        "RVSEC_HOME",
        "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec",
    )
    if not os.path.isdir(rvsec_root):
        log.error("RVSEC_HOME not found: %s", rvsec_root)
        sys.exit(1)

    log.info("RVSEC_HOME: %s", rvsec_root)
    log.info("Output dir: %s", args.output_dir)
    os.makedirs(args.output_dir, exist_ok=True)

    # Read APK filter list
    filter_text = Path(args.apks_filter).read_text().strip()
    filter_names = sorted(set(filter_text.splitlines()))
    log.info("Filter contains %d APK names", len(filter_names))

    # Resolve APK file paths
    apk_paths = []
    missing = []
    for name in filter_names:
        # Support both with and without .apk extension
        if not name.endswith(".apk"):
            path = os.path.join(args.apks_dir, f"{name}.apk")
        else:
            path = os.path.join(args.apks_dir, name)
        if os.path.isfile(path):
            apk_paths.append(path)
        else:
            missing.append(name)

    if missing:
        log.warning("Missing %d APK files in %s", len(missing), args.apks_dir)
        for m in missing[:10]:
            log.warning("  %s", m)

    if not apk_paths:
        log.error("No APK files found. Exiting.")
        sys.exit(1)

    log.info("Found %d APK files to process", len(apk_paths))

    # ----- Phase 1: Monitor Generation -----
    monitors_dir = os.path.join(args.output_dir, "monitors")
    if args.skip_monitors:
        if not os.path.isdir(monitors_dir):
            log.error("--skip-monitors but monitors dir not found: %s", monitors_dir)
            sys.exit(1)
        log.info("Phase 1: Skipped (--skip-monitors), using %s", monitors_dir)
    else:
        monitors_dir = generate_monitors(rvsec_root, args.specification_set, args.output_dir)

    # ----- Phase 2: Parallel Instrumentation -----
    if args.skip_instrumentation:
        instrumented_dir = os.path.join(args.output_dir, "instrumented_apks")
        if not os.path.isdir(instrumented_dir):
            log.error("--skip-instrumentation but dir not found: %s", instrumented_dir)
            sys.exit(1)
        # Build results from existing instrumented APKs
        existing = set(os.listdir(instrumented_dir))
        instr_results = []
        for apk_path in apk_paths:
            apk_name = os.path.basename(apk_path)
            instr_results.append({
                "apk": apk_name,
                "ok": apk_name in existing,
                "error": "" if apk_name in existing else "not found in instrumented_dir",
            })
        log.info("Phase 2: Skipped (--skip-instrumentation), %d existing APKs", len(existing))
    else:
        shared_config = prepare_instrumentation(rvsec_root, monitors_dir, args.output_dir)
        instr_results = run_parallel_instrumentation(apk_paths, shared_config, args.max_workers)

        # Cleanup worker dirs
        workers_dir = shared_config["workers_base_dir"]
        if os.path.exists(workers_dir):
            shutil.rmtree(workers_dir, ignore_errors=True)
            log.info("Cleaned up worker directories")

    successful_apks = [r["apk"] for r in instr_results if r["ok"]]
    failed = [r for r in instr_results if not r["ok"]]

    log.info("Instrumentation: %d OK, %d FAIL", len(successful_apks), len(failed))

    # ----- Phase 3: Static Analysis -----
    if args.skip_static:
        log.info("Phase 3: Skipped (--skip-static)")
    elif not successful_apks:
        log.warning("Phase 3: Skipped (no successfully instrumented APKs)")
    else:
        run_static_analysis(
            args.apks_dir, successful_apks, args.output_dir,
            args.max_workers, args.sa_timeout,
        )

    # ----- Summary -----
    total_elapsed = time.time() - total_start
    write_summary(args.output_dir, apk_paths, instr_results, total_elapsed)

    log.info(
        "Done: %d/%d instrumented, %d failed, total time %.0fs (%.1fh)",
        len(successful_apks), len(apk_paths), len(failed),
        total_elapsed, total_elapsed / 3600,
    )


if __name__ == "__main__":
    main()
