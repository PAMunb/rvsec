"""
CLI entry point for rv-instrumentation.

This module provides command-line interface for instrumenting Android APKs with
runtime verification monitors, transforming standard APKs into monitored 
operations-enabled artifacts ready for runtime verification testing.
"""

import argparse
import os
import sys
from typing import Dict, Any

from rv_instrumentation.config import RVInstrumentationConfig, ConfigurationError
from rv_instrumentation.rvandroid import RVInstrumentation


def create_parser() -> argparse.ArgumentParser:
    """
    Create and configure the argument parser for rv-instrumentation CLI.
    
    Returns:
        Configured ArgumentParser instance with all command options
    """
    parser = argparse.ArgumentParser(
        prog='rv-instrumentation',
        description='Instrument Android APKs with runtime verification monitors for monitored operations analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Instrument single APK using environment configuration
  rv-instrumentation instrument --apk /path/to/app.apk --output /output/instrumented

  # Batch instrument all APKs in directory
  rv-instrumentation batch --apks-dir /path/to/apks --output /output/instrumented

  # Force re-instrumentation with custom monitor directory
  rv-instrumentation instrument \\
    --apk /path/to/app.apk \\
    --monitor-dir /custom/monitors \\
    --output /output/instrumented \\
    --force

  # Using custom RVSEC installation
  rv-instrumentation batch \\
    --rvsec-root /custom/rvsec \\
    --apks-dir /path/to/apks \\
    --output /output/instrumented \\
    --summary

  # Complete custom configuration
  rv-instrumentation instrument \\
    --apk /path/to/app.apk \\
    --monitor-dir /custom/monitors \\
    --android-jar /custom/android.jar \\
    --keystore /custom/keystore.jks \\
    --keystore-password mypassword \\
    --output /output/instrumented

Configuration Priority (highest to lowest):
  1. Individual configuration parameters (--monitor-dir, --android-jar, etc.)
  2. Explicit --rvsec-root parameter
  3. RVSEC_HOME environment variable
  4. Error if no valid configuration source available

Instrumentation Pipeline:
  1. APK Decompilation (DEX → JAR using dex2jar)
  2. Monitor Integration (inject generated AspectJ and Java monitors)
  3. AspectJ Weaving (integrate monitoring pointcuts with application code)
  4. Dependency Integration (merge runtime verification libraries)
  5. Recompilation (JAR → DEX using Android d8 compiler)
  6. APK Signing (create deployment-ready instrumented APK)
        """
    )

    # Add subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available instrumentation commands')

    # Single APK instrumentation command
    instrument_parser = subparsers.add_parser(
        'instrument',
        help='Instrument a single APK with runtime verification monitors',
        description='Transform a single APK into a monitored operations-enabled artifact'
    )

    # Batch APK instrumentation command
    batch_parser = subparsers.add_parser(
        'batch',
        help='Batch instrument multiple APKs with runtime verification monitors',
        description='Transform multiple APKs in a directory into monitored operations-enabled artifacts'
    )

    # Add common arguments to both parsers
    for cmd_parser in [instrument_parser, batch_parser]:
        _add_configuration_arguments(cmd_parser)
        _add_output_arguments(cmd_parser)
        _add_utility_arguments(cmd_parser)

    # Add APK-specific arguments
    _add_apk_arguments(instrument_parser, batch_parser)

    return parser


def _add_configuration_arguments(parser: argparse.ArgumentParser) -> None:
    """Add configuration-related arguments to parser."""
    config_group = parser.add_argument_group('Configuration Options')
    config_group.add_argument(
        '--rvsec-root',
        help='Root directory of RVSEC installation (alternative to individual paths)'
    )

    # Monitor configuration
    monitor_group = parser.add_argument_group('Monitor Configuration')
    monitor_group.add_argument(
        '--monitor-dir',
        help='Directory containing generated monitor artifacts from rv-monitor-generator'
    )

    # Android SDK configuration
    android_group = parser.add_argument_group('Android SDK Configuration')
    android_group.add_argument(
        '--android-jar',
        help='Path to Android SDK android.jar file'
    )
    android_group.add_argument(
        '--android-platforms-dir',
        help='Directory containing Android SDK platform libraries'
    )

    # Signing configuration
    signing_group = parser.add_argument_group('APK Signing Configuration')
    signing_group.add_argument(
        '--keystore',
        help='Path to keystore file for APK signing'
    )
    signing_group.add_argument(
        '--keystore-password',
        help='Password for keystore access'
    )

    # Directory configuration
    dirs_group = parser.add_argument_group('Working Directory Configuration')
    dirs_group.add_argument(
        '--working-dir',
        help='Base working directory for instrumentation operations'
    )
    dirs_group.add_argument(
        '--tmp-dir',
        help='Temporary directory for intermediate processing files'
    )
    dirs_group.add_argument(
        '--dex2jar-home',
        help='Directory containing dex2jar tool suite'
    )


def _add_apk_arguments(instrument_parser: argparse.ArgumentParser,
                       batch_parser: argparse.ArgumentParser) -> None:
    """Add APK-specific arguments to parsers."""
    # Single APK argument
    apk_group = instrument_parser.add_argument_group('APK Input')
    apk_group.add_argument(
        '--apk',
        required=True,
        help='Path to APK file to be instrumented'
    )

    # Batch APK arguments
    batch_group = batch_parser.add_argument_group('Batch APK Input')
    batch_group.add_argument(
        '--apks-dir',
        required=True,
        help='Directory containing APK files to be instrumented'
    )


def _add_output_arguments(parser: argparse.ArgumentParser) -> None:
    """Add output-related arguments to parser."""
    output_group = parser.add_argument_group('Output Configuration')
    output_group.add_argument(
        '--output',
        required=True,
        help='Output directory for instrumented APKs and logs'
    )
    output_group.add_argument(
        '--force',
        action='store_true',
        help='Force re-instrumentation even if APK already instrumented'
    )


def _add_utility_arguments(parser: argparse.ArgumentParser) -> None:
    """Add utility arguments to parser."""
    util_group = parser.add_argument_group('Utility Options')
    util_group.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output with detailed logging'
    )
    util_group.add_argument(
        '--summary',
        action='store_true',
        help='Display instrumentation summary after completion'
    )
    util_group.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate configuration without performing instrumentation'
    )


def configure_logging(verbose: bool) -> None:
    """
    Configure logging based on verbosity level.
    
    Args:
        verbose: Enable verbose logging if True
    """
    import logging

    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def create_instrumentation_config(args) -> RVInstrumentationConfig:
    """
    Create RVInstrumentationConfig from command line arguments.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Configured RVInstrumentationConfig instance
        
    Raises:
        ConfigurationError: If configuration validation fails
    """
    return RVInstrumentationConfig(
        rvsec_root=args.rvsec_root,
        monitor_output_dir=args.monitor_dir,
        android_jar_path=args.android_jar,
        android_platforms_dir=args.android_platforms_dir,
        keystore_file=args.keystore,
        keystore_password=args.keystore_password,
        working_dir=args.working_dir,
        instrumented_dir=args.output,
        tmp_dir=args.tmp_dir,
        dex2jar_home=args.dex2jar_home
    )


def display_instrumentation_summary(errors: Dict[str, Dict[str, Any]],
                                    total_apks: int,
                                    operation_type: str) -> None:
    """
    Display comprehensive instrumentation summary.
    
    Args:
        errors: Dictionary of instrumentation errors
        total_apks: Total number of APKs processed
        operation_type: Type of operation (single/batch)
    """
    successful = total_apks - len(errors)
    success_rate = (successful / total_apks) * 100 if total_apks > 0 else 0

    print("\n" + "=" * 60)
    print(f"INSTRUMENTATION SUMMARY ({operation_type.upper()})")
    print("=" * 60)
    print(f"Total APKs Processed: {total_apks}")
    print(f"Successfully Instrumented: {successful}")
    print(f"Failed Instrumentations: {len(errors)}")
    print(f"Success Rate: {success_rate:.1f}%")

    if errors:
        print(f"\nFailed APKs:")
        for apk_name, error_details in errors.items():
            tool = error_details.get('tool', 'unknown')
            phase = error_details.get('phase', 'unknown')
            print(f"  • {apk_name} - {tool} ({phase})")

    print("=" * 60)


def handle_instrument_command(args) -> int:
    """
    Handle the single APK instrumentation command execution.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Create configuration from command line arguments
        config = create_instrumentation_config(args)

        if args.dry_run:
            print("✓ Configuration validation successful")
            print(f"Configuration Summary:")
            summary = config.get_configuration_summary()
            print(f"  Monitor Directory: {summary['instrumentation_paths']['monitor_output_dir']}")
            print(f"  Android JAR: {summary['android_integration']['android_jar_path']}")
            print(f"  Keystore: {summary['signing']['keystore_file']}")
            print(f"  Output Directory: {summary['instrumentation_paths']['instrumented_dir']}")
            return 0

        # Validate APK input
        config.validate_apk_input(args.apk)

        # Initialize instrumentation engine
        instrumentation = RVInstrumentation(config)

        # Execute single APK instrumentation
        print(f"Instrumenting APK: {os.path.basename(args.apk)}")
        print(f"Output directory: {args.output}")

        # Create temporary APKs directory for single APK processing
        import tempfile
        with tempfile.TemporaryDirectory() as temp_apks_dir:
            # Copy APK to temporary directory for processing
            import shutil
            temp_apk_path = os.path.join(temp_apks_dir, os.path.basename(args.apk))
            shutil.copy2(args.apk, temp_apk_path)

            # Execute instrumentation
            errors = instrumentation.instrument_apks(
                apks_dir=temp_apks_dir,
                results_dir=args.output,
                force_instrumentation=args.force
            )

        # Display results
        if not errors:
            print("✓ APK instrumentation completed successfully")
            if args.summary:
                display_instrumentation_summary(errors, 1, "single")
            return 0
        else:
            print("✗ APK instrumentation failed")
            if args.summary:
                display_instrumentation_summary(errors, 1, "single")
            return 1

    except ConfigurationError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"File Not Found: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected Error: {e}", file=sys.stderr)
        return 1


def handle_batch_command(args) -> int:
    """
    Handle the batch APK instrumentation command execution.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Create configuration from command line arguments
        config = create_instrumentation_config(args)

        if args.dry_run:
            print("✓ Configuration validation successful")
            print(f"Configuration Summary:")
            summary = config.get_configuration_summary()
            print(f"  APKs Directory: {args.apks_dir}")
            print(f"  Monitor Directory: {summary['instrumentation_paths']['monitor_output_dir']}")
            print(f"  Android JAR: {summary['android_integration']['android_jar_path']}")
            print(f"  Output Directory: {summary['instrumentation_paths']['instrumented_dir']}")

            # Count APKs in directory
            from rv_android_core.util import utils
            apks = utils.get_apks(args.apks_dir)
            print(f"  APKs Found: {len(apks)}")
            return 0

        # Validate APKs directory
        if not os.path.isdir(args.apks_dir):
            raise FileNotFoundError(f"APKs directory not found: {args.apks_dir}")

        # Initialize instrumentation engine
        instrumentation = RVInstrumentation(config)

        # Execute batch instrumentation
        print(f"Batch instrumenting APKs from: {args.apks_dir}")
        print(f"Output directory: {args.output}")

        errors = instrumentation.instrument_apks(
            apks_dir=args.apks_dir,
            results_dir=args.output,
            force_instrumentation=args.force
        )

        # Count total APKs for summary
        from rv_android_core.util import utils
        try:
            apks = utils.get_apks(args.apks_dir)
            total_apks = len(apks)
        except:
            total_apks = len(errors) if errors else 1

        # Display results
        if not errors:
            print("✓ All APKs instrumented successfully")
            if args.summary:
                display_instrumentation_summary(errors, total_apks, "batch")
            return 0
        else:
            successful = total_apks - len(errors)
            if successful > 0:
                print(f"⚠ Partial success: {successful}/{total_apks} APKs instrumented")
            else:
                print("✗ All APK instrumentations failed")

            if args.summary:
                display_instrumentation_summary(errors, total_apks, "batch")
            return 1 if successful == 0 else 0

    except ConfigurationError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"File Not Found: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected Error: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """
    Main entry point for rv-instrumentation CLI.
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    parser = create_parser()
    args = parser.parse_args()

    # Configure logging
    configure_logging(getattr(args, 'verbose', False))

    # Handle commands
    if args.command == 'instrument':
        return handle_instrument_command(args)
    elif args.command == 'batch':
        return handle_batch_command(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
