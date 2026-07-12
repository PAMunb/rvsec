# rv_platform/__main__.py
"""
CLI entry point for rv-platform.

This module provides command-line interface for the rv-platform system.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from rv_android_core.domain.task import ToolConfig
from rv_android_core.util.logging.manager import LoggingManager
from rv_platform.config.platform_config import PlatformConfig
from rv_platform.platform import Platform
from rv_tools.registry.registry import ToolRegistry


def _parse_timeouts(raw: str) -> list[int]:
    """Parse the ``--timeouts`` CSV string into a list of positive integers.

    Mirror of the rv-experiment helper (INV-PLT-22): comma split, whitespace
    trim, positive integers only, user order preserved, no deduplication. Wired
    as the argument's ``type=`` so argparse runs it during ``parse_args()`` and
    renders a usage error (exit 2) before any ``PlatformConfig`` is built.
    """
    try:
        values = [int(t.strip()) for t in raw.split(",") if t.strip()]
    except ValueError as e:
        raise argparse.ArgumentTypeError(
            f"timeouts must be comma-separated integers: {raw!r}"
        ) from e
    if not values or any(v <= 0 for v in values):
        raise argparse.ArgumentTypeError(f"timeouts must be positive integers: {raw!r}")
    return values


def add_performance_arguments(parser):
    """
    Add performance monitoring arguments to CLI parser.

    Args:
        parser: Command line argument parser
    """
    perf_group = parser.add_argument_group("Performance Monitoring")

    perf_group.add_argument(
        "--disable-performance-monitor",
        action="store_true",
        help="Disable performance monitoring to reduce overhead",
    )

    perf_group.add_argument(
        "--performance-monitor-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "DISABLED"],
        default="DEBUG",
        help="Performance monitor logging level (default: DEBUG)",
    )

    perf_group.add_argument(
        "--performance-monitor-max-samples",
        type=int,
        default=1000,
        help="Maximum number of metrics to store in memory (default: 1000)",
    )

    perf_group.add_argument(
        "--performance-export-enabled",
        action="store_true",
        help="Enable performance metrics export to file",
    )

    perf_group.add_argument(
        "--performance-export-format",
        choices=["JSON", "CSV"],
        default="JSON",
        help="Format for performance metrics export (default: JSON)",
    )


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for rv-platform CLI."""
    parser = argparse.ArgumentParser(
        prog="rv-platform",
        description="Independent and central executor for Android experiments",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Run command with both config file and CLI options
    # allow_abbrev=False so the removed scalar `--timeout` is not silently
    # accepted as a prefix abbreviation of `--timeouts` — the hard rename (P3)
    # must reject it (exit 2), matching the Click side which never abbreviates.
    run_parser = subparsers.add_parser(
        "run", help="Execute platform with configuration", allow_abbrev=False
    )
    run_parser.add_argument(
        "--config", "-c", help="Path to platform configuration file"
    )
    run_parser.add_argument(
        "--tools",
        "-t",
        default="monkey",
        help="Comma-separated tool names (default: monkey)",
    )
    run_parser.add_argument(
        "--apks-dir",
        "-a",
        default="./apks_examples",
        help="Directory containing APK files (default: ./apks_examples)",
    )
    run_parser.add_argument(
        "--results-dir", "-r", help="Results output directory (default: auto-generated)"
    )
    run_parser.add_argument(
        "--repetitions", type=int, default=1, help="Number of repetitions (default: 1)"
    )
    run_parser.add_argument(
        "--timeouts",
        type=_parse_timeouts,
        default=[300],
        help=(
            "Execution timeouts in seconds, comma-separated "
            '(e.g. "300" or "60,300"; default: 300)'
        ),
    )
    run_parser.add_argument(
        "--no-window", action="store_true", help="Run emulator in headless mode"
    )
    run_parser.add_argument(
        "--skip-result-processing",
        action="store_true",
        help="Skip automatic result processing after task execution",
    )
    run_parser.add_argument(
        "--process-results",
        help="Process existing experiment results directory (standalone mode)",
    )

    run_parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log verbosity level (default: INFO)",
    )
    run_parser.add_argument(
        "--debug", action="store_true", help="Shortcut for --log-level DEBUG"
    )
    run_parser.add_argument(
        "--show-context",
        action="store_true",
        help="Show structured context [key=value] in log messages",
    )

    # Performance monitoring arguments
    add_performance_arguments(run_parser)

    # List tools command
    list_parser = subparsers.add_parser("list-tools", help="List available tools")
    list_parser.add_argument(
        "--detailed", action="store_true", help="Show detailed tool information"
    )

    # Validate config command
    validate_parser = subparsers.add_parser(
        "validate-config", help="Validate configuration file"
    )
    validate_parser.add_argument(
        "config_file", help="Path to configuration file to validate"
    )

    # Config template generation command
    config_parser = subparsers.add_parser(
        "config", help="Generate configuration templates"
    )
    config_parser.add_argument(
        "--template-type",
        choices=["basic", "advanced"],
        default="basic",
        help="Configuration template type (default: basic)",
    )
    config_parser.add_argument(
        "--output", "-o", help="Output file path for configuration template"
    )

    return parser


def cmd_run(args) -> int:
    """Execute the run command."""
    try:
        import logging

        # Setup logging with CLI-specified level
        logging_manager = LoggingManager.get_instance()
        log_level = logging.DEBUG if args.debug else getattr(logging, args.log_level)
        show_context = getattr(args, "show_context", False)
        logging_manager.configure_output(
            console=True,
            file=False,
            console_level=log_level,
            console_context=show_context,
        )
        logging_manager.get_logger("rv_platform.cli")

        # Standalone result processing mode: re-generates CSV/JSON from an
        # existing results directory without re-executing any tasks. Useful
        # after fixing a result processor bug or when result processing was
        # skipped during the original run (--skip-result-processing).
        if args.process_results:
            return _process_results_standalone(args.process_results)

        if args.config:
            # Config file mode
            print(f"📝 Loading configuration from: {args.config}")
            config = PlatformConfig.from_file(args.config)
        else:
            # CLI mode - create configuration from arguments
            print("🚀 Creating configuration from CLI arguments")
            config = _create_config_from_cli(args)

        # Display configuration info
        print(f"🔧 Tools: {[t.name for t in config.tools]}")
        print(f"📁 APKs directory: {config.apks_dir}")
        print(f"📊 Repetitions: {config.repetitions}, Timeouts: {config.timeouts}")
        print(f"📂 Results directory: {config.results_dir}")

        # Create and run platform
        print("\n🚀 Starting platform execution...")
        platform = Platform(config)
        results = platform.run()

        # Print summary
        print("\n" + "=" * 60)
        print("📊 EXECUTION SUMMARY")
        print("=" * 60)
        print(f"Total tasks: {results['total_tasks']}")
        if results.get("skipped_tasks", 0) > 0:
            print(f"Skipped (from previous runs): {results['skipped_tasks']}")
        print(f"Successful: {results['successful_tasks']}")
        print(f"Failed: {results['failed_tasks']}")
        print(f"Success rate: {results['success_rate']:.2%}")
        print(f"Total time: {results['total_execution_time']:.2f}s")
        print(f"Average time per task: {results['average_execution_time']:.2f}s")

        if results["failed_tasks"] == 0:
            print("\n✅ All tasks completed successfully!")
        else:
            print(f"\n⚠️ {results['failed_tasks']} tasks failed")

        print(f"\n📂 Results saved to: {config.results_dir}")

        return 0 if results["failed_tasks"] == 0 else 1

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


def cmd_list_tools(args) -> int:
    """Execute the list-tools command."""
    try:
        tool_registry = ToolRegistry.get_instance()
        tools = tool_registry.get_all_tools()

        print("\n🔧 Available Testing Tools:")
        print("=" * 50)

        if not tools:
            print("❌ No tools available. Ensure tool modules are properly installed.")
            return 1

        for tool in sorted(tools, key=lambda t: t.name):
            tool_name = tool.name
            tool_description = getattr(tool, "description", "No description available")

            print(f"\n📦 {tool_name}")
            print(f"   Description: {tool_description}")

            if args.detailed:
                # Show variants if available
                variants = tool_registry.get_tool_variants(tool.name)
                if variants and len(variants) > 1:
                    variant_list = [v for v in variants if v != "default"]
                    if variant_list:
                        print(f"   Variants: {', '.join(variant_list)}")

                # Show capabilities if available
                if hasattr(tool, "capabilities"):
                    capabilities = ", ".join(tool.capabilities)
                    print(f"   Capabilities: {capabilities}")

                # Show example usage
                print(f"   Example: {tool_name}")

        print(f"\n✅ Total: {len(tools)} tools available")

        if not args.detailed:
            print("\n💡 Use --detailed flag for more information")

        return 0

    except Exception as e:
        print(f"❌ Error listing tools: {e}", file=sys.stderr)
        return 1


def cmd_validate_config(args) -> int:
    """Execute the validate-config command."""
    try:
        config_path = Path(args.config_file)

        if not config_path.exists():
            print(f"❌ Configuration file not found: {config_path}", file=sys.stderr)
            return 1

        print(f"🔍 Validating configuration: {config_path}")

        # Load and validate configuration
        config = PlatformConfig.from_file(str(config_path))
        config.validate_dependencies()

        print(f"✅ Configuration is valid: {config_path}")
        print(f"🔧 Tools: {[t.name for t in config.tools]}")
        print(f"📁 APKs directory: {config.apks_dir}")
        print(f"📊 Repetitions: {config.repetitions}")
        print(f"⏱️ Timeouts: {config.timeouts}")
        print(f"📈 Total tasks that will be generated: {config.get_total_tasks()}")

        return 0

    except Exception as e:
        print(f"❌ Configuration validation failed: {e}", file=sys.stderr)
        return 1


def cmd_config(args) -> int:
    """Execute the config template generation command."""
    try:
        print(f"📝 Generating {args.template_type} configuration template")

        # Create template configuration
        if args.template_type == "basic":
            template_config = _create_basic_template()
        elif args.template_type == "advanced":
            template_config = _create_advanced_template()
        else:
            print(f"❌ Unknown template type: {args.template_type}", file=sys.stderr)
            return 1

        # Convert to JSON
        config_json = json.dumps(template_config.to_dict(), indent=2)

        if args.output:
            # Save to file
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w") as f:
                f.write(config_json)

            print(
                f"✅ {args.template_type.title()} configuration template saved to: {output_path}"
            )
        else:
            # Print to stdout
            print("\n" + "=" * 60)
            print(f"{args.template_type.upper()} CONFIGURATION TEMPLATE")
            print("=" * 60)
            print(config_json)

        return 0

    except Exception as e:
        print(f"❌ Configuration generation failed: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """Main entry point for rv-platform CLI."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    if args.command == "run":
        return cmd_run(args)
    elif args.command == "list-tools":
        return cmd_list_tools(args)
    elif args.command == "validate-config":
        return cmd_validate_config(args)
    elif args.command == "config":
        return cmd_config(args)
    else:
        print(f"❌ Unknown command: {args.command}", file=sys.stderr)
        return 1


def _create_config_from_cli(args) -> PlatformConfig:
    """Create PlatformConfig from CLI arguments."""
    from datetime import datetime

    # Parse tool specifications from the comma-separated CLI string.
    # Each spec may include a variant after a colon (e.g., "droidbot:dfs_greedy").
    # ToolConfig.from_tool_specification() handles the parsing and defaults
    # variant to "default" when no colon is present.
    tool_specs = [t.strip() for t in args.tools.split(",")]
    tools = []
    for tool_spec in tool_specs:
        tools.append(ToolConfig.from_tool_specification(tool_spec))

    # Auto-generate a timestamped results directory if not specified. Each run
    # gets a unique directory, which prevents accidental overwriting of previous
    # results. When --results-dir points to an existing directory with tasks.json,
    # the platform automatically enters resume mode.
    if not args.results_dir:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_dir = f"./results/platform_{timestamp}"
    else:
        results_dir = args.results_dir

    config = PlatformConfig(
        apks_dir=args.apks_dir,
        tools=tools,
        repetitions=args.repetitions,
        timeouts=args.timeouts,
        results_dir=results_dir,
        no_window=args.no_window,
        log_level="INFO",
    )

    # Set CLI flags
    config.skip_result_processing = args.skip_result_processing

    return config


def _create_basic_template() -> PlatformConfig:
    """Create basic configuration template."""
    return PlatformConfig(
        apks_dir="apks_examples",
        tools=[ToolConfig(name="monkey")],
        repetitions=1,
        timeouts=[300],
        results_dir="./results/basic_experiment",
        no_window=True,
        log_level="INFO",
    )


def _create_advanced_template() -> PlatformConfig:
    """Create advanced configuration template."""
    return PlatformConfig(
        apks_dir="apks_examples",
        tools=[
            ToolConfig(name="monkey", parameters={"event_count": 1000, "seed": 42}),
            ToolConfig(name="droidbot", parameters={"count": 500}),
        ],
        repetitions=3,
        timeouts=[300, 600],
        results_dir="./results/advanced_experiment",
        no_window=True,
        log_level="DEBUG",
    )


def _process_results_standalone(results_dir: str) -> int:
    """
    Process existing experiment results directory in standalone mode.

    Args:
        results_dir: Directory containing experiment results to process

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        from rv_platform.components.result_processor import ResultProcessorComponent
        from rv_platform.storage.task_storage import TaskStorage

        print(f"📊 Processing existing results from: {results_dir}")

        # Check if results directory exists
        results_path = Path(results_dir)
        if not results_path.exists():
            print(f"❌ Results directory not found: {results_dir}", file=sys.stderr)
            return 1

        # Load completed tasks from storage. TaskStorage takes the tasks.json
        # FILE path (not the directory) and must be explicitly loaded before
        # querying — same construction as Platform.__init__.
        tasks_file = os.path.join(results_dir, "tasks.json")
        task_storage = TaskStorage(tasks_file)
        task_storage.load()
        tasks = task_storage.get_tasks()

        if not tasks:
            print(
                f"❌ No tasks found in results directory: {results_dir}",
                file=sys.stderr,
            )
            return 1

        print(f"📋 Found {len(tasks)} tasks to process")

        # Create result processor and process results
        processor = ResultProcessorComponent(tasks, results_dir)
        processor.initialize({})
        processor.execute({})
        processor.cleanup()

        print("✅ Results processing completed successfully")
        print(f"📂 Output files saved to: {results_dir}")

        return 0

    except Exception as e:
        print(f"❌ Error processing results: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
