#!/usr/bin/env python3
"""
APK Static Analysis Filter Script

This script filters APKs by running static analysis tools (GESDA, GATOR, REACH)
with a configurable timeout. APKs that complete all three analyses within the
timeout are considered valid for experiments.

Usage:
    python scripts/filter_apks_static_analysis.py --apks-dir ./apks --output-dir ./filtered_output

    # Parallel execution (recommended for large batches)
    python scripts/filter_apks_static_analysis.py --apks-dir ./apks --output-dir ./out/static -p 4

Output:
    - Analysis results in output_dir/<apk_name>/
    - passed_apks.txt: List of APKs that passed all analyses
    - failed_apks.txt: List of APKs that failed (with reasons)
    - analysis_report.json: Detailed report with timing info
"""

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from multiprocessing import Pool, cpu_count
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Default timeout per tool (in seconds)
DEFAULT_TIMEOUT = 600  # 10 minutes


@dataclass
class ToolResult:
    """Result of a single tool execution."""

    tool_name: str
    success: bool
    execution_time: float
    output_file: str
    error_message: Optional[str] = None
    timed_out: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "execution_time": self.execution_time,
            "output_file": self.output_file,
            "error_message": self.error_message,
            "timed_out": self.timed_out,
        }


@dataclass
class ApkAnalysisResult:
    """Complete analysis result for a single APK."""

    apk_name: str
    apk_path: str
    valid: bool
    tool_results: Dict[str, ToolResult] = field(default_factory=dict)
    total_time: float = 0.0
    error_summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "apk_name": self.apk_name,
            "apk_path": self.apk_path,
            "valid": self.valid,
            "total_time": self.total_time,
            "error_summary": self.error_summary,
            "tools": {k: v.to_dict() for k, v in self.tool_results.items()},
        }


def create_config(
    rvsec_home: Optional[str] = None,
    android_home: Optional[str] = None,
    rt_jar: Optional[str] = None,
    mop_dir: Optional[str] = None,
) -> Dict[str, str]:
    """
    Create configuration dictionary for static analysis tools.
    Returns a plain dict that can be passed to worker processes.
    """
    rvsec_home = rvsec_home or os.environ.get("RVSEC_HOME")
    android_home = android_home or os.environ.get("ANDROID_HOME")
    rt_jar = rt_jar or os.environ.get("RV_RT_JAR")

    if not rvsec_home:
        raise ValueError(
            "RVSEC_HOME not set. Set environment variable or pass --rvsec-home"
        )

    if not android_home:
        raise ValueError(
            "ANDROID_HOME not set. Set environment variable or pass --android-home"
        )

    # Derive paths from RVSEC_HOME
    lib_dir = os.path.join(rvsec_home, "rv-android", "lib")
    gesda_jar = os.path.join(lib_dir, "gesda", "rvsec-gesda.jar")
    gator_dir = os.path.join(lib_dir, "gator")
    gator_python = os.path.join(gator_dir, "gator")
    gator_client_jar = os.path.join(gator_dir, "rvsec-gator-client.jar")
    reach_jar = os.path.join(lib_dir, "reach", "rvsec-reach.jar")

    # Android SDK
    android_platforms_dir = os.path.join(android_home, "platforms")
    android_jar = None
    for api_level in ["29", "28", "27", "26", "30", "31", "32", "33", "34"]:
        candidate = os.path.join(
            android_platforms_dir, f"android-{api_level}", "android.jar"
        )
        if os.path.isfile(candidate):
            android_jar = candidate
            break
    if not android_jar:
        raise ValueError(f"No android.jar found in {android_platforms_dir}")

    # rt.jar
    if not rt_jar:
        candidates = [
            os.path.expanduser("~/.sdkman/candidates/java/8.0.302-open/jre/lib/rt.jar"),
            "/usr/lib/jvm/java-8-openjdk-amd64/jre/lib/rt.jar",
            "/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar",
        ]
        for candidate in candidates:
            if os.path.isfile(candidate):
                rt_jar = candidate
                break

    if not rt_jar or not os.path.isfile(rt_jar):
        raise ValueError("Java rt.jar not found. Set RV_RT_JAR environment variable")

    # MOP directory
    mop_dir = mop_dir or os.path.join(
        rvsec_home, "rvsec", "rvsec-mop", "src", "main", "resources", "jca"
    )

    config = {
        "rvsec_home": rvsec_home,
        "lib_dir": lib_dir,
        "gesda_jar": gesda_jar,
        "gator_dir": gator_dir,
        "gator_python": gator_python,
        "gator_client_jar": gator_client_jar,
        "reach_jar": reach_jar,
        "android_home": android_home,
        "android_platforms_dir": android_platforms_dir,
        "android_jar": android_jar,
        "rt_jar": rt_jar,
        "mop_dir": mop_dir,
    }

    # Validate
    required_files = [
        ("GESDA JAR", gesda_jar),
        ("GATOR Python", gator_python),
        ("GATOR Client JAR", gator_client_jar),
        ("REACH JAR", reach_jar),
        ("Android JAR", android_jar),
        ("rt.jar", rt_jar),
    ]

    for name, path in required_files:
        if not os.path.exists(path):
            raise ValueError(f"{name} not found: {path}")

    if not os.path.isdir(mop_dir):
        raise ValueError(f"MOP directory not found: {mop_dir}")

    return config


def run_command_with_timeout(
    cmd: List[str], timeout: int, tool_name: str, output_file: str
) -> ToolResult:
    """
    Execute a command with timeout.
    Returns ToolResult with success/failure information.
    """
    start_time = time.time()

    try:
        result = subprocess.run(cmd, timeout=timeout, capture_output=True, text=True)

        execution_time = time.time() - start_time

        # Check if output file was created
        if not os.path.isfile(output_file):
            return ToolResult(
                tool_name=tool_name,
                success=False,
                execution_time=execution_time,
                output_file=output_file,
                error_message=f"Output file not created. Exit code: {result.returncode}. Stderr: {result.stderr[:500] if result.stderr else 'N/A'}",
                timed_out=False,
            )

        # Check file size (empty files are invalid)
        if os.path.getsize(output_file) == 0:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                execution_time=execution_time,
                output_file=output_file,
                error_message="Output file is empty",
                timed_out=False,
            )

        return ToolResult(
            tool_name=tool_name,
            success=True,
            execution_time=execution_time,
            output_file=output_file,
        )

    except subprocess.TimeoutExpired:
        execution_time = time.time() - start_time
        return ToolResult(
            tool_name=tool_name,
            success=False,
            execution_time=execution_time,
            output_file=output_file,
            error_message=f"Timeout after {timeout} seconds",
            timed_out=True,
        )

    except Exception as e:
        execution_time = time.time() - start_time
        return ToolResult(
            tool_name=tool_name,
            success=False,
            execution_time=execution_time,
            output_file=output_file,
            error_message=str(e),
        )


def analyze_apk_worker(
    args: Tuple[str, str, Dict[str, str], int, bool],
) -> ApkAnalysisResult:
    """
    Worker function for parallel APK analysis.
    Takes a tuple of arguments to work with multiprocessing.Pool.
    """
    apk_path, output_dir, config, timeout, stop_on_first_failure = args
    return analyze_apk(apk_path, output_dir, config, timeout, stop_on_first_failure)


def analyze_apk(
    apk_path: str,
    output_dir: str,
    config: Dict[str, str],
    timeout: int = DEFAULT_TIMEOUT,
    stop_on_first_failure: bool = True,
) -> ApkAnalysisResult:
    """
    Run all static analysis tools on a single APK.

    Args:
        apk_path: Path to APK file
        output_dir: Directory to store output files
        config: Static analysis configuration dictionary
        timeout: Timeout per tool in seconds
        stop_on_first_failure: Stop as soon as one tool fails

    Returns:
        ApkAnalysisResult with all tool results
    """
    apk_name = Path(apk_path).stem
    apk_output_dir = os.path.join(output_dir, apk_name)
    os.makedirs(apk_output_dir, exist_ok=True)

    result = ApkAnalysisResult(apk_name=apk_name, apk_path=apk_path, valid=True)

    start_time = time.time()

    # Define output files
    gesda_file = os.path.join(apk_output_dir, f"{apk_name}.gesda")
    gator_file = os.path.join(apk_output_dir, f"{apk_name}.wtg")
    reach_file = os.path.join(apk_output_dir, f"{apk_name}.reach")

    # 1. Run GESDA (required for REACH)
    gesda_cmd = [
        "java",
        "-jar",
        config["gesda_jar"],
        "--android-dir",
        config["android_platforms_dir"],
        "--rt-jar",
        config["rt_jar"],
        "--output",
        gesda_file,
        "--apk",
        apk_path,
    ]

    gesda_result = run_command_with_timeout(gesda_cmd, timeout, "GESDA", gesda_file)
    result.tool_results["GESDA"] = gesda_result

    if not gesda_result.success:
        result.valid = False
        result.error_summary = f"GESDA failed: {gesda_result.error_message}"
        if stop_on_first_failure:
            result.total_time = time.time() - start_time
            return result

    # 2. Run GATOR
    gator_cmd = [
        "python",
        config["gator_python"],
        "a",
        "-p",
        apk_path,
        "--client-jar",
        config["gator_client_jar"],
        "--out",
        gator_file,
        "-client",
        "RvsecWtgClient",
    ]

    gator_result = run_command_with_timeout(gator_cmd, timeout, "GATOR", gator_file)
    result.tool_results["GATOR"] = gator_result

    if not gator_result.success:
        result.valid = False
        result.error_summary = f"GATOR failed: {gator_result.error_message}"
        if stop_on_first_failure:
            result.total_time = time.time() - start_time
            return result

    # 3. Run REACH (depends on GESDA)
    if gesda_result.success:
        reach_cmd = [
            "java",
            "-jar",
            config["reach_jar"],
            "--android-dir",
            config["android_platforms_dir"],
            "--rt-jar",
            config["rt_jar"],
            "--mop-dir",
            config["mop_dir"],
            "--gesda",
            gesda_file,
            "--writer",
            "csv",
            "--timeout",
            str(timeout),
            "--apk",
            apk_path,
            "--output",
            reach_file,
        ]

        reach_result = run_command_with_timeout(reach_cmd, timeout, "REACH", reach_file)
        result.tool_results["REACH"] = reach_result

        if not reach_result.success:
            result.valid = False
            result.error_summary = f"REACH failed: {reach_result.error_message}"
    else:
        result.tool_results["REACH"] = ToolResult(
            tool_name="REACH",
            success=False,
            execution_time=0.0,
            output_file=reach_file,
            error_message="Skipped: GESDA failed",
        )
        result.valid = False

    result.total_time = time.time() - start_time
    return result


def find_apks(apks_dir: str) -> List[str]:
    """Find all APK files in directory."""
    apks = []
    for root, dirs, files in os.walk(apks_dir):
        for file in files:
            if file.lower().endswith(".apk"):
                apks.append(os.path.join(root, file))
    return sorted(apks)


def run_sequential(
    apks: List[str],
    output_dir: str,
    config: Dict[str, str],
    timeout: int,
    continue_on_failure: bool,
    verbose: bool,
) -> List[ApkAnalysisResult]:
    """Run analysis sequentially."""
    results = []
    for i, apk_path in enumerate(apks, 1):
        apk_name = Path(apk_path).stem
        print(f"\n[{i}/{len(apks)}] Analyzing: {apk_name}")

        result = analyze_apk(
            apk_path=apk_path,
            output_dir=output_dir,
            config=config,
            timeout=timeout,
            stop_on_first_failure=not continue_on_failure,
        )

        results.append(result)

        if result.valid:
            print(f"  => VALID ({result.total_time:.1f}s total)")
        else:
            print(f"  => FAILED: {result.error_summary}")

    return results


def run_parallel(
    apks: List[str],
    output_dir: str,
    config: Dict[str, str],
    timeout: int,
    continue_on_failure: bool,
    num_workers: int,
    verbose: bool,
) -> List[ApkAnalysisResult]:
    """Run analysis in parallel using multiprocessing."""
    print(f"\nStarting parallel analysis with {num_workers} workers...")
    print("-" * 60)

    # Prepare arguments for workers
    worker_args = [
        (apk_path, output_dir, config, timeout, not continue_on_failure)
        for apk_path in apks
    ]

    results = []
    completed = 0
    valid_count = 0
    failed_count = 0

    with Pool(processes=num_workers) as pool:
        # Use imap_unordered for better progress reporting
        for result in pool.imap_unordered(analyze_apk_worker, worker_args):
            completed += 1
            results.append(result)

            status = "VALID" if result.valid else "FAILED"
            if result.valid:
                valid_count += 1
            else:
                failed_count += 1

            # Progress update
            error_info = (
                f" - {result.error_summary[:50]}..."
                if not result.valid and result.error_summary
                else ""
            )
            print(
                f"[{completed}/{len(apks)}] {result.apk_name}: {status} ({result.total_time:.1f}s){error_info}"
            )

    print("-" * 60)
    print(f"Parallel execution complete: {valid_count} valid, {failed_count} failed")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Filter APKs by running static analysis with timeout",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic usage (sequential)
    python scripts/filter_apks_static_analysis.py --apks-dir ./apks --output-dir ./out/static

    # Parallel execution with 4 workers
    python scripts/filter_apks_static_analysis.py --apks-dir ./apks --output-dir ./out/static -p 4

    # Custom timeout (5 minutes per tool)
    python scripts/filter_apks_static_analysis.py --apks-dir ./apks --output-dir ./out/static --timeout 300

    # Maximum parallelism (use all CPUs)
    python scripts/filter_apks_static_analysis.py --apks-dir ./apks --output-dir ./out/static -p 0
        """,
    )

    parser.add_argument(
        "--apks-dir", "-a", required=True, help="Directory containing APK files"
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        required=True,
        help="Output directory for analysis results",
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Timeout per tool in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--rvsec-home", help="RVSEC installation root (default: $RVSEC_HOME)"
    )
    parser.add_argument(
        "--android-home", help="Android SDK path (default: $ANDROID_HOME)"
    )
    parser.add_argument(
        "--mop-dir",
        help="MOP specifications directory (default: $RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca)",
    )
    parser.add_argument(
        "--continue-on-failure",
        action="store_true",
        help="Continue running all tools even if one fails",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--parallel",
        "-p",
        type=int,
        default=1,
        help="Number of parallel workers (0 = auto-detect CPU count, default: 1)",
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=0,
        help="Limit number of APKs to analyze (0 = no limit, default: 0)",
    )

    args = parser.parse_args()

    # Validate inputs
    if not os.path.isdir(args.apks_dir):
        print(f"ERROR: APKs directory not found: {args.apks_dir}")
        sys.exit(1)

    # Initialize configuration
    try:
        config = create_config(
            rvsec_home=args.rvsec_home,
            android_home=args.android_home,
            mop_dir=args.mop_dir,
        )
    except ValueError as e:
        print(f"ERROR: Configuration error: {e}")
        sys.exit(1)

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Find APKs
    apks = find_apks(args.apks_dir)

    if not apks:
        print(f"ERROR: No APK files found in {args.apks_dir}")
        sys.exit(1)

    # Apply limit if specified
    if args.limit > 0:
        apks = apks[: args.limit]

    # Determine number of workers
    num_workers = args.parallel
    if num_workers == 0:
        num_workers = cpu_count()
    elif num_workers < 0:
        num_workers = max(1, cpu_count() + num_workers)

    print(f"Found {len(apks)} APK(s) to analyze")
    print(f"Timeout per tool: {args.timeout} seconds ({args.timeout/60:.1f} minutes)")
    print(
        f"Max time per APK: {args.timeout * 3} seconds ({args.timeout * 3 / 60:.1f} minutes)"
    )
    print(f"Parallel workers: {num_workers}")
    print(f"Output directory: {args.output_dir}")

    total_start = time.time()

    # Run analysis
    if num_workers == 1:
        results = run_sequential(
            apks,
            args.output_dir,
            config,
            args.timeout,
            args.continue_on_failure,
            args.verbose,
        )
    else:
        results = run_parallel(
            apks,
            args.output_dir,
            config,
            args.timeout,
            args.continue_on_failure,
            num_workers,
            args.verbose,
        )

    total_time = time.time() - total_start

    # Collect results
    valid_apks = [r.apk_path for r in results if r.valid]
    failed_apks = [(r.apk_path, r.error_summary) for r in results if not r.valid]

    # Summary
    print("\n" + "=" * 60)
    print("ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"Total APKs analyzed: {len(apks)}")
    print(f"Valid APKs: {len(valid_apks)}")
    print(f"Failed APKs: {len(failed_apks)}")
    print(f"Total time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
    if num_workers > 1:
        print(
            f"Speedup: ~{len(apks) * args.timeout * 3 / total_time:.1f}x theoretical max"
        )

    # Write passed APKs list (consumed by select_dataset.py --passed-apks)
    valid_file = os.path.join(args.output_dir, "passed_apks.txt")
    with open(valid_file, "w") as f:
        for apk in valid_apks:
            f.write(f"{apk}\n")
    print(f"\nPassed APKs list: {valid_file}")

    # Write failed APKs list
    failed_file = os.path.join(args.output_dir, "failed_apks.txt")
    with open(failed_file, "w") as f:
        for apk, reason in failed_apks:
            f.write(f"{apk}\t{reason}\n")
    print(f"Failed APKs list: {failed_file}")

    # Write detailed report
    report = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "timeout_per_tool": args.timeout,
            "apks_dir": args.apks_dir,
            "output_dir": args.output_dir,
            "continue_on_failure": args.continue_on_failure,
            "parallel_workers": num_workers,
        },
        "summary": {
            "total_apks": len(apks),
            "valid_apks": len(valid_apks),
            "failed_apks": len(failed_apks),
            "total_time_seconds": total_time,
        },
        "results": [r.to_dict() for r in results],
    }

    report_file = os.path.join(args.output_dir, "analysis_report.json")
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Detailed report: {report_file}")

    # Print valid APKs
    if valid_apks:
        print(f"\n{'='*60}")
        print("VALID APKs (can be used for experiments):")
        print("=" * 60)
        for apk in sorted(valid_apks):
            print(f"  {Path(apk).name}")

    # Print failure summary
    if failed_apks:
        print(f"\n{'='*60}")
        print("FAILED APKs:")
        print("=" * 60)

        # Group by failure reason
        timeout_failures = [
            (apk, reason)
            for apk, reason in failed_apks
            if reason and "Timeout" in reason
        ]
        other_failures = [
            (apk, reason)
            for apk, reason in failed_apks
            if not reason or "Timeout" not in reason
        ]

        if timeout_failures:
            print(f"\n  Timeout failures ({len(timeout_failures)}):")
            for apk, _ in timeout_failures[:10]:
                print(f"    - {Path(apk).name}")
            if len(timeout_failures) > 10:
                print(f"    ... and {len(timeout_failures) - 10} more")

        if other_failures:
            print(f"\n  Other failures ({len(other_failures)}):")
            for apk, reason in other_failures[:10]:
                reason_short = (
                    (reason[:60] + "...")
                    if reason and len(reason) > 60
                    else (reason or "Unknown")
                )
                print(f"    - {Path(apk).name}: {reason_short}")
            if len(other_failures) > 10:
                print(f"    ... and {len(other_failures) - 10} more")

    print("\nDone!")

    # Exit with appropriate code
    if len(valid_apks) == 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
