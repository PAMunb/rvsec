#!/usr/bin/env python3
"""
Provide a CLI for the rv-static-analysis module.

Expose ``analyze`` (single APK) and ``batch`` (directory of APKs) subcommands
that run the unified GATOR-based analysis client. Each invocation produces a
single JSON output per APK with reachability, windows, and transitions sections.

### Role in the System:

- Standalone entry point for running static analysis outside rv-platform
- Used for ad-hoc analysis, debugging, and batch pre-processing of APK sets

### Key Features:

- Single-APK and batch analysis with configurable concurrency
- Dry-run mode for configuration validation without execution
- Verbose output and summary display for debugging
- Continue-on-error option for batch resilience

### Integration Points:

- Creates RVStaticAnalysisConfig from CLI arguments
- Delegates analysis to StaticAnalyzer (analysis/static/static_analysis.py)
- Reports StaticAnalysisResult status and timing to stdout
"""

import argparse
import sys
import time
from pathlib import Path

from rv_android_core.domain.app import App
from rv_android_core.util.error.exceptions import ConfigurationError
from rv_static_analysis import (
    RVStaticAnalysisConfig,
    StaticAnalysisException,
    StaticAnalyzer,
)


def setup_argument_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser with analyze and batch subcommands.

    Returns:
        Configured ArgumentParser with subparsers for each command.
    """
    parser = argparse.ArgumentParser(
        description="RV Static Analysis - Unified GATOR-based Android static analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze single APK
  rv-static-analysis analyze --apk /path/to/app.apk --output /output

  # Batch analyze APKs
  rv-static-analysis batch --apks-dir /path/to/apks --output /output

  # Analyze with custom tool paths
  rv-static-analysis analyze --apk app.apk --analysis-client-jar /custom/jar --output /output

  # Validate configuration without analysis
  rv-static-analysis analyze --apk app.apk --output /tmp --dry-run
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze a single APK",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_analyze_arguments(analyze_parser)

    batch_parser = subparsers.add_parser(
        "batch",
        help="Batch analyze multiple APKs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_batch_arguments(batch_parser)

    return parser


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """Add configuration, tool, and utility arguments shared by all subcommands.

    Args:
        parser: Subparser to add argument groups to.
    """
    config_group = parser.add_argument_group("Configuration Options")
    config_group.add_argument("--rvsec-root", help="RVSEC installation root directory")
    config_group.add_argument(
        "--lib-dir", help="Directory containing static analysis tool JARs"
    )
    config_group.add_argument(
        "--android-platforms-dir", help="Android SDK platforms directory"
    )
    config_group.add_argument("--mop-dir", help="MOP specifications directory")
    config_group.add_argument(
        "--working-dir", help="Working directory for temporary files"
    )

    tools_group = parser.add_argument_group("Tool Options")
    tools_group.add_argument("--gator-dir", help="Path to GATOR tools directory")
    tools_group.add_argument(
        "--analysis-client-jar", help="Path to rvsec-analysis-client.jar"
    )
    tools_group.add_argument(
        "--jvm-memory", default=None, help='JVM heap size (e.g. "8g", "12g")'
    )
    tools_group.add_argument(
        "--analysis-timeout", type=int, default=None, help="Analysis timeout in seconds"
    )

    util_group = parser.add_argument_group("Utility Options")
    util_group.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    util_group.add_argument(
        "--summary", action="store_true", help="Display analysis summary"
    )
    util_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration only (do not run analysis)",
    )


def add_analyze_arguments(parser: argparse.ArgumentParser) -> None:
    """Add input/output and force-reanalysis arguments for the analyze subcommand.

    Args:
        parser: The analyze subparser to add arguments to.
    """
    io_group = parser.add_argument_group("Input/Output Options")
    io_group.add_argument("--apk", required=True, help="APK file to analyze")
    io_group.add_argument(
        "--output", required=True, help="Output directory for analysis results"
    )

    analysis_group = parser.add_argument_group("Analysis Options")
    analysis_group.add_argument(
        "--force", action="store_true", help="Force re-analysis even if results exist"
    )

    add_common_arguments(parser)


def add_batch_arguments(parser: argparse.ArgumentParser) -> None:
    """Add input/output, concurrency, and error-handling arguments for the batch subcommand.

    Args:
        parser: The batch subparser to add arguments to.
    """
    io_group = parser.add_argument_group("Input/Output Options")
    io_group.add_argument(
        "--apks-dir", required=True, help="Directory containing APK files to analyze"
    )
    io_group.add_argument(
        "--output", required=True, help="Output directory for analysis results"
    )

    batch_group = parser.add_argument_group("Batch Options")
    batch_group.add_argument(
        "--force", action="store_true", help="Force re-analysis even if results exist"
    )
    batch_group.add_argument(
        "--max-concurrent",
        type=int,
        default=1,
        help="Maximum number of concurrent analyses (default: 1)",
    )
    batch_group.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue batch processing if individual APKs fail",
    )

    add_common_arguments(parser)


def create_config_from_args(args: argparse.Namespace) -> RVStaticAnalysisConfig:
    """Create an RVStaticAnalysisConfig from parsed CLI arguments.

    Map argument names to config field names, apply overrides for non-None
    values, and handle dry-run mode by deferring validation.

    Args:
        args: Parsed argparse namespace with CLI values.

    Returns:
        Validated RVStaticAnalysisConfig instance. In dry-run mode,
        path validation is deferred (validate_on_init=False).
    """
    config_kwargs = {}

    arg_mappings = {
        "rvsec_root": "rvsec_root",
        "lib_dir": "lib_dir",
        "android_platforms_dir": "android_platforms_dir",
        "mop_dir": "mop_dir",
        "working_dir": "working_dir",
        "gator_dir": "gator_dir",
        "analysis_client_jar": "analysis_client_jar",
    }

    for arg_name, config_name in arg_mappings.items():
        arg_value = getattr(args, arg_name, None)
        if arg_value:
            config_kwargs[config_name] = arg_value

    if hasattr(args, "output") and args.output:
        config_kwargs["output_dir"] = args.output

    if getattr(args, "jvm_memory", None):
        config_kwargs["jvm_memory"] = args.jvm_memory

    if getattr(args, "analysis_timeout", None):
        config_kwargs["analysis_timeout"] = args.analysis_timeout

    validate_on_init = not getattr(args, "dry_run", False)

    try:
        return RVStaticAnalysisConfig(
            validate_on_init=validate_on_init, **config_kwargs
        )
    except ConfigurationError as e:
        print(f"Configuration Error: {e}")
        sys.exit(1)


def handle_analyze_command(args: argparse.Namespace) -> int:
    """Run static analysis on a single APK.

    Validate configuration and APK input, then execute StaticAnalyzer.
    Support dry-run (validate only), verbose, and summary modes.

    Args:
        args: Parsed argparse namespace with analyze subcommand values.

    Returns:
        Exit code: 0 on success, 1 on any failure.
    """
    if args.verbose:
        print(f"Analyzing APK: {args.apk}")

    config = create_config_from_args(args)

    try:
        config.validate_apk_input(args.apk)
    except ConfigurationError as e:
        print(f"APK Validation Error: {e}")
        return 1

    if args.summary:
        display_configuration_summary(config)

    if args.dry_run:
        print(
            "Configuration validation successful. Dry-run mode - no analysis performed."
        )
        return 0

    app = App(args.apk)
    analyzer = StaticAnalyzer(app, config, args.output)

    try:
        start_time = time.time()
        result = analyzer.analyze()
        analysis_time = time.time() - start_time

        if result.success:
            print(f"Static analysis completed in {analysis_time:.2f} seconds")
            if result.timed_out:
                print("  (timed out — partial JSON preserved)")
            if args.summary:
                display_analysis_summary(result, analysis_time)
            return 0
        else:
            print(f"Static analysis failed with {len(result.errors)} errors:")
            for error in result.errors:
                print(f"  - {error}")
            return 1

    except StaticAnalysisException as e:
        print(f"Analysis Error: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected Error: {e}")
        return 1


def handle_batch_command(args: argparse.Namespace) -> int:
    """Run static analysis on all APKs in a directory.

    Iterate over .apk files, analyze each with StaticAnalyzer, and report
    aggregate results. Respect --continue-on-error to keep going after
    individual failures.

    Args:
        args: Parsed argparse namespace with batch subcommand values.

    Returns:
        Exit code: 0 if all APKs succeed, 1 if any fail.
    """
    if args.verbose:
        print(f"Batch analyzing APKs from: {args.apks_dir}")

    config = create_config_from_args(args)

    if args.summary:
        display_configuration_summary(config)

    if args.dry_run:
        print(
            "Configuration validation successful. Dry-run mode - no analysis performed."
        )
        return 0

    apks_dir = Path(args.apks_dir)
    if not apks_dir.is_dir():
        print(f"APKs directory does not exist: {args.apks_dir}")
        return 1

    apk_files = list(apks_dir.glob("*.apk"))
    if not apk_files:
        print(f"No APK files found in: {args.apks_dir}")
        return 1

    if args.verbose:
        print(f"Found {len(apk_files)} APK files to analyze")

    total_success = 0
    total_errors = 0
    start_time = time.time()

    for i, apk_file in enumerate(apk_files, 1):
        if args.verbose:
            print(f"\nProcessing [{i}/{len(apk_files)}]: {apk_file.name}")

        try:
            app = App(str(apk_file))
            apk_output_dir = Path(args.output) / app.package_name
            analyzer = StaticAnalyzer(app, config, str(apk_output_dir))
            result = analyzer.analyze()

            if result.success:
                total_success += 1
                if args.verbose:
                    timeout_note = " (timed out)" if result.timed_out else ""
                    print(f"  Success: {apk_file.name}{timeout_note}")
            else:
                total_errors += 1
                print(f"  Failed: {apk_file.name}")
                if args.verbose:
                    for error in result.errors:
                        print(f"    - {error}")

                if not args.continue_on_error:
                    print(
                        "Stopping batch processing (use --continue-on-error to continue)"
                    )
                    break

        except Exception as e:
            total_errors += 1
            print(f"  Exception: {apk_file.name} - {e}")

            if not args.continue_on_error:
                print("Stopping batch processing (use --continue-on-error to continue)")
                break

    total_time = time.time() - start_time

    print("\nBatch Analysis Summary:")
    print(f"  Total APKs: {len(apk_files)}")
    print(f"  Successful: {total_success}")
    print(f"  Failed: {total_errors}")
    print(f"  Total time: {total_time:.2f} seconds")

    return 0 if total_errors == 0 else 1


def display_configuration_summary(config: RVStaticAnalysisConfig) -> None:
    """Print a human-readable configuration summary to stdout.

    Args:
        config: Configuration instance to summarize.
    """
    print("\nConfiguration Summary:")
    summary = config.get_configuration_summary()

    for section, details in summary.items():
        print(f"  {section.replace('_', ' ').title()}:")
        if isinstance(details, dict):
            for key, value in details.items():
                print(f"    {key}: {value}")
        else:
            print(f"    {details}")


def display_analysis_summary(result, analysis_time: float) -> None:
    """Print analysis result details including timing and output path.

    Args:
        result: StaticAnalysisResult from the analyzer.
        analysis_time: Wall-clock time of the analysis in seconds.
    """
    print("\nAnalysis Summary:")
    print(f"  Total time: {analysis_time:.2f} seconds")
    print(f"  Output: {result.analysis_file}")
    if result.timed_out:
        print("  Status: timed out (partial JSON)")

    if result.execution_times:
        print("  Execution times:")
        for tool, time_taken in result.execution_times.items():
            print(f"    {tool}: {time_taken:.2f} seconds")


def main() -> int:
    """Parse arguments and dispatch to the appropriate subcommand handler.

    Returns:
        Exit code: 0 on success, 1 on failure or missing command.
    """
    parser = setup_argument_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "analyze":
        return handle_analyze_command(args)
    elif args.command == "batch":
        return handle_batch_command(args)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
