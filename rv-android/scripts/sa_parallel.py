#!/usr/bin/env python3
"""
Run static analysis in parallel across preprocessed container outputs.

Each worker processes one preprocess_N directory. For each instrumented APK,
checks if SA JSON already exists (skip), validates android.jar for the target
API level, runs GATOR on the original APK, and verifies JSON was produced.

Usage:
    uv run python scripts/sa_parallel.py \
        --preprocess-dir /data/gh50_preprocess_jca \
        --original-apks-dir /data/APKs \
        --timeout 3600 \
        --jvm-memory 16g
"""

import argparse
import multiprocessing
import os
import signal
import sys
import time
from pathlib import Path


def preflight(preprocess_dir: str, original_apks_dir: str) -> list[str]:
    """Validate prerequisites and return list of container dirs."""
    # Check RVSEC_HOME
    rvsec_home = os.environ.get("RVSEC_HOME")
    if not rvsec_home:
        print("ERROR: RVSEC_HOME not set", file=sys.stderr)
        sys.exit(1)

    # Check ANDROID_HOME and platforms
    android_home = os.environ.get("ANDROID_HOME")
    if not android_home:
        print("ERROR: ANDROID_HOME not set", file=sys.stderr)
        sys.exit(1)

    platforms_dir = os.path.join(android_home, "platforms")
    available = sorted(
        d for d in os.listdir(platforms_dir)
        if d.startswith("android-") and os.path.isfile(os.path.join(platforms_dir, d, "android.jar"))
    )
    print(f"Android platforms: {', '.join(available)}")
    max_api = max(int(d.split("-")[1]) for d in available)
    if max_api < 35:
        print(f"WARNING: highest platform is android-{max_api}, modern APKs target 35-36", file=sys.stderr)

    # Find container dirs
    container_dirs = sorted(
        str(d) for d in Path(preprocess_dir).iterdir()
        if d.is_dir() and d.name.startswith("preprocess_")
        and (d / "instrumented_apks").is_dir()
    )
    if not container_dirs:
        print("ERROR: no preprocess_*/instrumented_apks dirs found", file=sys.stderr)
        sys.exit(1)

    return container_dirs


def analyze_container(
    container_dir: str,
    original_apks_dir: str,
    timeout: int,
    jvm_memory: str,
) -> dict:
    """Analyze all instrumented APKs in a single container dir."""
    # Imports inside worker to avoid pickling issues
    from rv_android_core.domain.app import App
    from rv_static_analysis.analysis.static.static_analysis import StaticAnalyzer
    from rv_static_analysis.config import RVStaticAnalysisConfig

    instrumented_dir = os.path.join(container_dir, "instrumented_apks")
    name = os.path.basename(container_dir)
    android_home = os.environ.get("ANDROID_HOME", "")

    results = {
        "name": name,
        "success": 0,
        "partial": 0,
        "failed": 0,
        "skipped": 0,
        "no_platform": 0,
        "no_original": 0,
        "details": [],
    }

    apk_names = sorted(f for f in os.listdir(instrumented_dir) if f.endswith(".apk"))
    total = len(apk_names)

    config = RVStaticAnalysisConfig(
        rvsec_root=os.environ.get("RVSEC_HOME"),
        jvm_memory=jvm_memory,
        analysis_timeout=timeout,
        validate_on_init=False,
    )

    for i, apk_name in enumerate(apk_names, 1):
        json_path = os.path.join(instrumented_dir, f"{apk_name}.json")
        tag = f"[{name}] [{i}/{total}]"

        # 1. Cache check
        if os.path.isfile(json_path):
            results["skipped"] += 1
            print(f"  {tag} SKIP {apk_name}", flush=True)
            continue

        # 2. Original APK check
        original_apk = os.path.join(original_apks_dir, apk_name)
        if not os.path.isfile(original_apk):
            results["no_original"] += 1
            results["details"].append(f"{apk_name}: original not found")
            print(f"  {tag} MISS {apk_name} (no original)", flush=True)
            continue

        # 3. Android platform check (pre-validate before GATOR)
        try:
            app = App(original_apk)
            target_sdk = getattr(app, "sdk_target", None)
            if target_sdk:
                platform_jar = os.path.join(
                    android_home, "platforms", f"android-{target_sdk}", "android.jar"
                )
                if not os.path.isfile(platform_jar):
                    results["no_platform"] += 1
                    results["details"].append(f"{apk_name}: android-{target_sdk} not installed")
                    print(f"  {tag} NOPLATFORM {apk_name} (needs android-{target_sdk})", flush=True)
                    continue
        except Exception as e:
            results["failed"] += 1
            results["details"].append(f"{apk_name}: App init error: {e}")
            print(f"  {tag} ERROR {apk_name}: {e}", flush=True)
            continue

        # 4. Run analysis
        print(f"  {tag} ANALYZING {apk_name} (target={target_sdk})...", flush=True)
        t0 = time.time()

        try:
            analyzer = StaticAnalyzer(app, config, instrumented_dir)
            result = analyzer.analyze()
            elapsed = time.time() - t0

            # 5. Verify JSON produced
            if os.path.isfile(json_path):
                if result.timed_out:
                    results["partial"] += 1
                    print(f"  {tag} PARTIAL {apk_name} ({elapsed:.0f}s, timed out)", flush=True)
                else:
                    results["success"] += 1
                    print(f"  {tag} OK {apk_name} ({elapsed:.0f}s)", flush=True)
            else:
                results["failed"] += 1
                results["details"].append(f"{apk_name}: no JSON after {elapsed:.0f}s")
                print(f"  {tag} FAIL {apk_name} ({elapsed:.0f}s, no JSON)", flush=True)

        except Exception as e:
            elapsed = time.time() - t0
            results["failed"] += 1
            err = str(e)[:120]
            results["details"].append(f"{apk_name}: {err}")
            print(f"  {tag} ERROR {apk_name} ({elapsed:.0f}s): {err}", flush=True)

    return results


def main():
    parser = argparse.ArgumentParser(description="SA parallel across preprocess dirs")
    parser.add_argument("--preprocess-dir", required=True)
    parser.add_argument("--original-apks-dir", required=True)
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("--jvm-memory", default="16g")
    parser.add_argument("--max-workers", type=int, default=10)
    args = parser.parse_args()

    container_dirs = preflight(args.preprocess_dir, args.original_apks_dir)

    print(f"\n=== SA Parallel Runner ===")
    print(f"Containers:  {len(container_dirs)}")
    print(f"Timeout:     {args.timeout}s ({args.timeout // 60} min)")
    print(f"JVM memory:  {args.jvm_memory}")
    print(f"Workers:     min({args.max_workers}, {len(container_dirs)})")
    print(flush=True)

    start = time.time()
    workers = []
    result_queue = multiprocessing.Queue()

    def worker_wrapper(cdir, queue):
        try:
            r = analyze_container(cdir, args.original_apks_dir, args.timeout, args.jvm_memory)
            queue.put(r)
        except Exception as e:
            queue.put({"name": os.path.basename(cdir), "error": str(e)})

    # Launch workers as processes (easier to kill than ProcessPoolExecutor)
    for cdir in container_dirs[:args.max_workers]:
        p = multiprocessing.Process(target=worker_wrapper, args=(cdir, result_queue))
        p.start()
        workers.append(p)

    # Handle Ctrl+C
    def signal_handler(sig, frame):
        print("\n\nInterrupted! Killing workers...", flush=True)
        for w in workers:
            w.kill()
        sys.exit(1)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Wait for all workers
    for w in workers:
        w.join()

    elapsed = time.time() - start

    # Collect results
    all_results = []
    while not result_queue.empty():
        all_results.append(result_queue.get())

    # Summary
    print(f"\n{'='*60}")
    print(f"RESULTS ({elapsed:.0f}s = {elapsed/60:.0f} min)")
    print(f"{'='*60}")

    total_s = total_p = total_f = total_sk = total_np = total_no = 0
    for r in sorted(all_results, key=lambda x: x["name"]):
        if "error" in r:
            print(f"  {r['name']}: FATAL ERROR: {r['error']}")
            continue
        total_s += r["success"]
        total_p += r["partial"]
        total_f += r["failed"]
        total_sk += r["skipped"]
        total_np += r["no_platform"]
        total_no += r["no_original"]
        print(
            f"  {r['name']}: "
            f"{r['success']} ok, {r['partial']} partial, "
            f"{r['failed']} fail, {r['skipped']} skip, "
            f"{r['no_platform']} no-platform"
        )

    total_with_json = total_s + total_p + total_sk
    total_all = total_s + total_p + total_f + total_sk + total_np + total_no
    print(f"\n  OK:          {total_s} (new JSON produced)")
    print(f"  Partial:     {total_p} (timed out, partial JSON)")
    print(f"  Failed:      {total_f} (GATOR ran, no JSON)")
    print(f"  Cached:      {total_sk} (JSON already existed)")
    print(f"  No platform: {total_np} (missing android-XX)")
    print(f"  No original: {total_no}")
    print(f"\n  Total with JSON: {total_with_json}/{total_all}")

    # Print failure details
    all_details = []
    for r in all_results:
        all_details.extend(r.get("details", []))
    if all_details:
        print(f"\n--- Failure details ({len(all_details)}) ---")
        for d in sorted(all_details)[:20]:
            print(f"  {d}")
        if len(all_details) > 20:
            print(f"  ... and {len(all_details) - 20} more")


if __name__ == "__main__":
    main()
