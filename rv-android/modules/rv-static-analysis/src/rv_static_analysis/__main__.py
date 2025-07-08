#!/usr/bin/env python3
"""
CLI for rv-static-analysis module.

This CLI provides command-line interface for static analysis operations
including GATOR, GESDA, and REACH analysis tools.
"""

import argparse
import sys
import time
from pathlib import Path

from rv_android_core.domain.app import App
from rv_android_core.util.error.exceptions import ConfigurationError
from rv_static_analysis import RVStaticAnalysisConfig, StaticAnalyzer, StaticAnalysisException


def setup_argument_parser() -> argparse.ArgumentParser:
    """Set up and return the argument parser."""
    parser = argparse.ArgumentParser(
        description="RV Static Analysis - Android static analysis with GATOR, GESDA, and REACH",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze single APK with environment configuration
  rv-static-analysis analyze --apk /path/to/app.apk --output /output

  # Batch analyze APKs with custom RVSEC root
  rv-static-analysis batch --apks-dir /path/to/apks --rvsec-root /custom/rvsec --output /output

  # Analyze with custom tool paths
  rv-static-analysis analyze --apk app.apk --gesda-jar /custom/gesda.jar --output /output

  # Validate configuration without analysis
  rv-static-analysis analyze --apk app.apk --output /tmp --dry-run
        """
    )

    # Add subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Analyze command (single APK)
    analyze_parser = subparsers.add_parser(
        'analyze',
        help='Analyze a single APK with static analysis tools',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_analyze_arguments(analyze_parser)

    # Batch command (multiple APKs)
    batch_parser = subparsers.add_parser(
        'batch', 
        help='Batch analyze multiple APKs',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_batch_arguments(batch_parser)

    return parser


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """Add common arguments used by multiple commands."""
    # Configuration options
    config_group = parser.add_argument_group('Configuration Options')
    config_group.add_argument(
        '--rvsec-root',
        help='RVSEC installation root directory'
    )
    config_group.add_argument(
        '--lib-dir',
        help='Directory containing static analysis tool JARs'
    )
    config_group.add_argument(
        '--android-platforms-dir',
        help='Android SDK platforms directory'
    )
    config_group.add_argument(
        '--rt-jar',
        help='Java runtime JAR path'
    )
    config_group.add_argument(
        '--mop-dir',
        help='Monitor-Oriented Programming specifications directory'
    )
    config_group.add_argument(
        '--working-dir',
        help='Working directory for temporary files'
    )

    # Tool-specific options
    tools_group = parser.add_argument_group('Tool-Specific Options')
    tools_group.add_argument(
        '--gesda-jar',
        help='Path to GESDA JAR file'
    )
    tools_group.add_argument(
        '--gator-dir',
        help='Path to GATOR tools directory'
    )
    tools_group.add_argument(
        '--reach-jar',
        help='Path to REACH JAR file'
    )

    # Utility options
    util_group = parser.add_argument_group('Utility Options')
    util_group.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    util_group.add_argument(
        '--summary',
        action='store_true',
        help='Display analysis summary'
    )
    util_group.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate configuration only (do not run analysis)'
    )


def add_analyze_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments specific to analyze command."""
    # Input/Output options
    io_group = parser.add_argument_group('Input/Output Options')
    io_group.add_argument(
        '--apk',
        required=True,
        help='APK file to analyze'
    )
    io_group.add_argument(
        '--output',
        required=True,
        help='Output directory for analysis results'
    )

    # Analysis options
    analysis_group = parser.add_argument_group('Analysis Options')
    analysis_group.add_argument(
        '--force',
        action='store_true',
        help='Force re-analysis even if results exist'
    )
    analysis_group.add_argument(
        '--tools',
        nargs='+',
        choices=['gesda', 'gator', 'reach'],
        default=['gesda', 'gator', 'reach'],
        help='Specific tools to run (default: all tools)'
    )

    add_common_arguments(parser)


def add_batch_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments specific to batch command."""
    # Input/Output options
    io_group = parser.add_argument_group('Input/Output Options')
    io_group.add_argument(
        '--apks-dir',
        required=True,
        help='Directory containing APK files to analyze'
    )
    io_group.add_argument(
        '--output',
        required=True,
        help='Output directory for analysis results'
    )

    # Batch options
    batch_group = parser.add_argument_group('Batch Options')
    batch_group.add_argument(
        '--force',
        action='store_true',
        help='Force re-analysis even if results exist'
    )
    batch_group.add_argument(
        '--max-concurrent',
        type=int,
        default=1,
        help='Maximum number of concurrent analyses (default: 1)'
    )
    batch_group.add_argument(
        '--continue-on-error',
        action='store_true',
        help='Continue batch processing if individual APKs fail'
    )

    add_common_arguments(parser)


def create_config_from_args(args: argparse.Namespace) -> RVStaticAnalysisConfig:
    """Create configuration from command line arguments."""
    config_kwargs = {}
    
    # Map arguments to configuration parameters
    arg_mappings = {
        'rvsec_root': 'rvsec_root',
        'lib_dir': 'lib_dir',
        'android_platforms_dir': 'android_platforms_dir',
        'rt_jar': 'rt_jar',
        'mop_dir': 'mop_dir',
        'working_dir': 'working_dir',
        'gesda_jar': 'gesda_jar',
        'gator_dir': 'gator_dir',
        'reach_jar': 'reach_jar'
    }
    
    for arg_name, config_name in arg_mappings.items():
        arg_value = getattr(args, arg_name.replace('_', '-'), None)
        if arg_value:
            config_kwargs[config_name] = arg_value
    
    # Set output directory if provided
    if hasattr(args, 'output') and args.output:
        config_kwargs['output_dir'] = args.output
    
    # Disable validation for dry-run mode
    validate_on_init = not getattr(args, 'dry_run', False)
    
    try:
        return RVStaticAnalysisConfig(validate_on_init=validate_on_init, **config_kwargs)
    except ConfigurationError as e:
        print(f"Configuration Error: {e}")
        sys.exit(1)


def handle_analyze_command(args: argparse.Namespace) -> int:
    """Handle the analyze command for single APK analysis."""
    if args.verbose:
        print(f"Analyzing APK: {args.apk}")
    
    # Create configuration
    config = create_config_from_args(args)
    
    # Validate APK input
    try:
        config.validate_apk_input(args.apk)
    except ConfigurationError as e:
        print(f"APK Validation Error: {e}")
        return 1
    
    # Display configuration summary if requested
    if args.summary:
        display_configuration_summary(config)
    
    # Exit if dry-run
    if args.dry_run:
        print("Configuration validation successful. Dry-run mode - no analysis performed.")
        return 0
    
    # Create App object
    app = App(args.apk)
    
    # Create analyzer
    analyzer = StaticAnalyzer(app, config, args.output)
    
    try:
        # Run analysis
        start_time = time.time()
        result = analyzer.analyze()
        analysis_time = time.time() - start_time
        
        if result.success:
            print(f"Static analysis completed successfully in {analysis_time:.2f} seconds")
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
    """Handle the batch command for multiple APK analysis."""
    if args.verbose:
        print(f"Batch analyzing APKs from: {args.apks_dir}")
    
    # Create configuration
    config = create_config_from_args(args)
    
    # Display configuration summary if requested
    if args.summary:
        display_configuration_summary(config)
    
    # Exit if dry-run
    if args.dry_run:
        print("Configuration validation successful. Dry-run mode - no analysis performed.")
        return 0
    
    # Find APK files
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
    
    # Process APKs
    total_success = 0
    total_errors = 0
    start_time = time.time()
    
    for i, apk_file in enumerate(apk_files, 1):
        if args.verbose:
            print(f"\nProcessing [{i}/{len(apk_files)}]: {apk_file.name}")
        
        try:
            # Create App object
            app = App(str(apk_file))
            
            # Create analyzer with APK-specific output directory
            apk_output_dir = Path(args.output) / app.package_name
            analyzer = StaticAnalyzer(app, config, str(apk_output_dir))
            
            # Run analysis
            result = analyzer.analyze()
            
            if result.success:
                total_success += 1
                if args.verbose:
                    print(f"  ✓ Success: {apk_file.name}")
            else:
                total_errors += 1
                print(f"  ✗ Failed: {apk_file.name}")
                if args.verbose:
                    for error in result.errors:
                        print(f"    - {error}")
                
                if not args.continue_on_error:
                    print("Stopping batch processing due to error (use --continue-on-error to continue)")
                    break
                    
        except Exception as e:
            total_errors += 1
            print(f"  ✗ Exception: {apk_file.name} - {e}")
            
            if not args.continue_on_error:
                print("Stopping batch processing due to exception (use --continue-on-error to continue)")
                break
    
    total_time = time.time() - start_time
    
    # Display batch summary
    print(f"\nBatch Analysis Summary:")
    print(f"  Total APKs: {len(apk_files)}")
    print(f"  Successful: {total_success}")
    print(f"  Failed: {total_errors}")
    print(f"  Total time: {total_time:.2f} seconds")
    
    return 0 if total_errors == 0 else 1


def display_configuration_summary(config: RVStaticAnalysisConfig) -> None:
    """Display configuration summary."""
    print("\nConfiguration Summary:")
    summary = config.get_configuration_summary()
    
    for section, details in summary.items():
        if section == 'validation_status':
            continue
        print(f"  {section.replace('_', ' ').title()}:")
        if isinstance(details, dict):
            for key, value in details.items():
                print(f"    {key}: {value}")
        else:
            print(f"    {details}")
    
    print(f"  Validation: {summary.get('validation_status', 'Unknown')}")


def display_analysis_summary(result, analysis_time: float) -> None:
    """Display analysis result summary."""
    print(f"\nAnalysis Summary:")
    print(f"  Total time: {analysis_time:.2f} seconds")
    print(f"  GESDA output: {result.gesda_file}")
    print(f"  GATOR output: {result.gator_file}")
    print(f"  REACH output: {result.reach_file}")
    
    if result.execution_times:
        print(f"  Tool execution times:")
        for tool, time_taken in result.execution_times.items():
            print(f"    {tool}: {time_taken:.2f} seconds")


def main() -> int:
    """Main CLI entry point."""
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    # Check if command was provided
    if not args.command:
        parser.print_help()
        return 1
    
    # Handle commands
    if args.command == 'analyze':
        return handle_analyze_command(args)
    elif args.command == 'batch':
        return handle_batch_command(args)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())