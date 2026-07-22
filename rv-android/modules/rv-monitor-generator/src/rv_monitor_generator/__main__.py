"""
CLI entry point for rv-monitor-generator.

This module provides command-line interface for generating runtime verification
monitors from MOP specifications using JavaMOP and RV-Monitor tools.
"""

import argparse
import sys

from rv_monitor_generator.config import ConfigurationError, RVGeneratorConfig
from rv_monitor_generator.runtime_verification_generator import (
    RuntimeVerificationGenerator,
)


def create_parser() -> argparse.ArgumentParser:
    """
    Create and configure the argument parser for rv-monitor-generator CLI.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog="rv-monitor-generator",
        description="Generate runtime verification monitors from MOP specifications",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using RVSEC_HOME environment variable with JCA specs
  rv-monitor-generator generate --specs-dir /path/to/jca --output /output/monitors

  # Specifying rvsec root explicitly  
  rv-monitor-generator generate --rvsec-root /path/to/rvsec --specs-dir /path/to/generic --output /output/monitors

  # Using completely custom paths
  rv-monitor-generator generate \\
    --javamop-bin /custom/javamop \\
    --rvmonitor-bin /custom/rv-monitor \\
    --specs-dir /custom/specs \\
    --aspects-dir /custom/aspects \\
    --output /output/monitors

Configuration Priority (highest to lowest):
  1. Individual tool paths (--javamop-bin, --rvmonitor-bin, etc.)
  2. Explicit --rvsec-root parameter
  3. RVSEC_HOME environment variable
  4. Error if none available
        """,
    )

    # Add subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Generate command
    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate monitors from MOP specifications",
        description="Generate runtime verification monitors and AspectJ files from MOP specifications",
    )

    # Configuration options
    config_group = generate_parser.add_argument_group("Configuration Options")
    config_group.add_argument(
        "--rvsec-root",
        help="Root directory of RVSEC installation (alternative to individual paths)",
    )

    # Individual tool paths
    tools_group = generate_parser.add_argument_group("Individual Tool Paths")
    tools_group.add_argument("--javamop-bin", help="Path to JavaMOP binary executable")
    tools_group.add_argument(
        "--rvmonitor-bin", help="Path to RV-Monitor binary executable"
    )

    # Specification directories
    specs_group = generate_parser.add_argument_group("Specification Directories")
    specs_group.add_argument(
        "--specs-dir", help="Directory containing MOP specification files (.mop)"
    )
    specs_group.add_argument(
        "--aspects-dir", help="Directory containing custom AspectJ files (.aj)"
    )

    # Output configuration
    output_group = generate_parser.add_argument_group("Output Configuration")
    output_group.add_argument(
        "--output",
        required=True,
        help="Output directory for generated monitors and AspectJ files",
    )

    # Utility options
    util_group = generate_parser.add_argument_group("Utility Options")
    util_group.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    util_group.add_argument(
        "--summary",
        action="store_true",
        help="Display generation summary after completion",
    )

    return parser


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
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def handle_generate_command(args) -> int:
    """
    Handle the generate command execution.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Create configuration from command line arguments
        config = RVGeneratorConfig(
            rvsec_root=args.rvsec_root,
            javamop_bin=args.javamop_bin,
            rvmonitor_bin=args.rvmonitor_bin,
            mop_specs_dir=args.specs_dir,
            aspects_dir=args.aspects_dir,
        )

        # Initialize generator
        generator = RuntimeVerificationGenerator(config)

        # Execute generation
        print(f"Generating monitors to: {args.output}")
        success = generator.generate_monitors(args.output)

        if success:
            print("✓ Monitor generation completed successfully")

            # Display summary if requested
            if args.summary:
                summary = generator.get_generation_summary(args.output)
                print("\nGeneration Summary:")
                print(f"  Output Directory: {summary['output_directory']}")
                print(
                    f"  AspectJ Files: {summary['aspectj_files']['count']} ({summary['aspectj_files']['purpose']})"
                )
                print(
                    f"  Monitor Classes: {summary['monitor_classes']['count']} ({summary['monitor_classes']['purpose']})"
                )
                print(
                    f"  Specs Processed: {summary['specs_processed']['count']} from {summary['specs_processed']['source_directory']}"
                )

            return 0
        else:
            print("✗ Monitor generation failed")
            return 1

    except ConfigurationError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected Error: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """
    Main entry point for rv-monitor-generator CLI.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    parser = create_parser()
    args = parser.parse_args()

    # Configure logging
    configure_logging(getattr(args, "verbose", False))

    # Handle commands
    if args.command == "generate":
        return handle_generate_command(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
