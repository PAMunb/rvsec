#!/usr/bin/env python3
"""
RV-Experiment CLI entry point.

Provide the primary CLI interface for Android testing experiments with
runtime verification monitors. Four commands: run (execute experiments),
config (generate templates), list-tools (show available tools), and
validate (check configuration files).

Supports two execution modes: CLI mode with tool specification DSL
(tool:variant@param=value) and config-file mode with JSON configuration.
"""

import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import click
from rv_android_core.constants import (
    ENV_APKS_DIR,
    ENV_APKS_FILTER,
    ENV_DEBUG,
    ENV_DEVICE_PORT,
    ENV_EXPERIMENT_NAME,
    ENV_HUMANOID_URL,
    ENV_INSTRUMENTATION_VARIANT,
    ENV_JVM_MEMORY,
    ENV_LOGCAT_DIAGNOSTICS,
    ENV_NO_QUARANTINE,
    ENV_NO_WINDOW,
    ENV_REPETITIONS,
    ENV_RESUME_DIR,
    ENV_SA_TIMEOUT,
    ENV_SKIP_EXECUTION,
    ENV_SKIP_INSTRUMENT,
    ENV_SKIP_MONITORS,
    ENV_SKIP_STATIC_ANALYSIS,
    ENV_SPEC_SET,
    ENV_TIMEOUTS,
    ENV_TOOLS,
)
from rv_android_core.domain.task import ToolConfig
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import ConfigurationError
from rv_android_core.util.logging.constants import (
    CONTEXT_COMPONENT,
    LOG_COMPLETE,
    LOG_START,
)
from rv_android_core.util.logging.manager import LoggingManager
from rv_experiment.config import ExperimentConfig
from rv_experiment.constants import (
    DEFAULT_APKS_DIR,
    DEFAULT_REPETITIONS,
    DEFAULT_SPEC_SET,
    DEFAULT_TIMEOUT,
    RESULTS_DIR,
)
from rv_experiment.experiment.experiment_controller import execute_with_config
from rv_tools import ToolRegistry


class CLIContext:
    """Manage shared state across CLI commands.

    ### Role in the System:
    Provide centralized access to logging, error handling, and tool registry
    for all Click commands. Passed automatically via Click's context mechanism
    (pass_context decorator).

    ### Key Features:
    - Logging configuration with debug/level/context support
    - Tool specification DSL parsing into ToolConfig instances
    - Tool registry access for validation and listing

    ### Integration Points:
    - LoggingManager: Console and file logging configuration
    - ErrorHandler: Consistent error management across commands
    - ToolRegistry: Tool discovery, variant listing, and validation
    """

    def __init__(self):
        """Initialize CLI context with core infrastructure components.

        State:
            logging_manager: Singleton LoggingManager instance
            error_handler: Singleton ErrorHandler instance
            logger: Logger for CLI operations
            debug: Whether debug logging is enabled
            tool_registry: Singleton ToolRegistry with all registered tools
        """
        # Initialize core components from rv-android-core
        self.logging_manager = LoggingManager.get_instance()
        self.error_handler = ErrorHandler.get_instance()

        # Configure CLI logger with proper context
        self.logger = self.logging_manager.get_logger(
            "rv_experiment.cli", {CONTEXT_COMPONENT: "CLIContext"}
        )

        self.debug = False

        # Tool registry is a singleton populated at import time:
        # - rv-tools registers builtin tools (monkey, droidbot, ape)
        # - rv-platform registers external tools (rvagent, rvsmart, aperv)
        # By the time CLIContext is created, all tools are already registered
        # because rv-platform is a transitive dependency of rv-experiment.
        self.tool_registry = ToolRegistry.get_instance()

        self.logger.info("CLI context initialized successfully")

    @ErrorHandler.handle_errors(component="CLIContext", phase="configure_logging")
    def configure_logging(
        self, debug: bool = False, log_level: str = "INFO", show_context: bool = False
    ):
        """
        Configure logging for CLI operations with comprehensive setup.

        Args:
            debug: Enable debug level logging (shortcut for log_level=DEBUG)
            log_level: Log verbosity level (DEBUG, INFO, WARNING, ERROR)
            show_context: Show structured context [key=value] in console log messages
        """
        import logging

        # --debug flag overrides --log-level
        level = logging.DEBUG if debug else getattr(logging, log_level)

        # Configure logging manager for CLI usage (replaces any basicConfig handlers)
        self.logging_manager.configure_output(
            console=True,
            file=False,  # File logging enabled during experiment execution
            console_level=level,
            file_level=logging.DEBUG,
            console_format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            console_context=show_context,
        )

        # Silence noisy third-party loggers that flood output during APK analysis.
        # androguard is particularly verbose at INFO level during APK parsing.
        for noisy_logger in [
            "androguard",
            "matplotlib",
            "PIL",
            "requests",
            "urllib3",
            "httpcore",
            "werkzeug",
            "httpx",
        ]:
            logging.getLogger(noisy_logger).setLevel(logging.ERROR)

        self.debug = debug
        self.logger.info("CLI logging configured successfully")

    def parse_tool_specification(self, tool_spec: str) -> List[ToolConfig]:
        """
        Parse tool specification string into ToolConfig instances.

        Multi-variant specs are expanded at parse time: `droidbot:dfs_greedy:bfs_greedy`
        produces TWO ToolConfig instances, one per variant.

        ### Tool Specification DSL:
        Format: `tool_name[:variant1][:variant2][@param1=value1,param2=value2]`

        ### Examples:
        - `monkey` -> [ToolConfig(name="monkey", variant="default")]
        - `droidbot:dfs_greedy` -> [ToolConfig(name="droidbot", variant="dfs_greedy")]
        - `droidbot:dfs_greedy:bfs_greedy` -> [ToolConfig(..., variant="dfs_greedy"), ToolConfig(..., variant="bfs_greedy")]

        ### Parsing Strategy:
        1. Split tool name/variants from parameters using '@' delimiter
        2. Parse parameter section as key=value pairs separated by commas
        3. Split tool section using ':' to extract name and variants
        4. Validate tool name against registry for early error detection
        5. Create one ToolConfig per variant (or one with "default" if no variants)

        Args:
            tool_spec: Tool specification string to parse

        Returns:
            List of ToolConfig instances (one per variant, or one with default variant)

        Raises:
            ValueError: If tool specification format is invalid or tool is not available
        """
        try:
            # Split tool name/variants from parameters
            if "@" in tool_spec:
                tool_part, params_part = tool_spec.split("@", 1)

                # Parse parameters as key=value pairs
                parameters = {}
                for param in params_part.split(","):
                    if "=" in param:
                        key, value = param.split("=", 1)
                        parameters[key.strip()] = value.strip()
                    else:
                        # Boolean flag parameter
                        parameters[param.strip()] = True
            else:
                tool_part = tool_spec
                parameters = {}

            # Split tool name and variants
            parts = tool_part.split(":")
            tool_name = parts[0].strip()
            variants = [v.strip() for v in parts[1:] if v.strip()]

            if not tool_name:
                raise ValueError("Tool name cannot be empty")

            # Validate tool availability in registry
            available_tools = [tool.name for tool in self.tool_registry.get_all_tools()]
            if tool_name not in available_tools:
                self.logger.warning(
                    f"Tool '{tool_name}' not found in registry. Available tools: {', '.join(available_tools)}"
                )

            # Expand multi-variant specs into separate ToolConfig instances
            if not variants:
                return [
                    ToolConfig(name=tool_name, variant="default", parameters=parameters)
                ]

            return [
                ToolConfig(name=tool_name, variant=v, parameters=dict(parameters))
                for v in variants
            ]

        except Exception as e:
            raise ValueError(f"Invalid tool specification '{tool_spec}': {e}")


# CLI Context setup with clean pattern
pass_context = click.make_pass_decorator(CLIContext, ensure=True)


def _parse_timeouts(raw: str) -> List[int]:
    """Parse the ``--timeouts`` CSV string into a list of positive integers.

    The option is declared as a string (mirroring ``--tools``) so the same
    value can arrive via the flag, the ``RV_TIMEOUTS`` env var, or the default
    without Click coercing it to ``int`` — that coercion is exactly what breaks
    ``RV_TIMEOUTS="60,300"``. Splitting/validation therefore happens here, at the
    CLI boundary, before any experiment setup (INV-EXP-33). Order is preserved
    and duplicates are kept: the resume mechanism skips identity-colliding tasks.
    """
    try:
        values = [int(t.strip()) for t in raw.split(",") if t.strip()]
    except ValueError as e:
        raise click.BadParameter(
            f"timeouts must be comma-separated integers: {raw!r}"
        ) from e
    if not values or any(v <= 0 for v in values):
        raise click.BadParameter(f"timeouts must be positive integers: {raw!r}")
    return values


def _timeouts_callback(ctx, param, value: str) -> List[int]:
    """Click callback that parses ``--timeouts`` during parameter processing.

    Runs before ``run()`` executes and outside its ``@handle_errors`` wrapper
    (which absorbs every exception and would turn a ``BadParameter`` into a
    silent exit 0). Raising here lets Click render the usage error and exit 2,
    satisfying INV-EXP-33's fail-fast contract. ``value`` is the Click-resolved
    string (flag, ``RV_TIMEOUTS`` env, or default).
    """
    return _parse_timeouts(value)


@click.group()
# gh55 §9 GAMBIARRA — first envvar= entry. See
# `openspec/changes/gh55-env-purity-avd-api30/design.md` "Known Limitations
# (Gambiarra)" and the follow-up change at
# `openspec/changes/gh-tbd-env-vars-architecture/`. Per-flag `envvar=` is the
# minimum patch to make INV-EXP-32 hold inside this Click surface ONLY; do NOT
# expand this pattern to new flags or to argparse modules — the architectural
# fix lives in the follow-up change.
@click.option(
    "--debug",
    is_flag=True,
    envvar=ENV_DEBUG,
    help="Enable debug logging for development",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="INFO",
    help="Log verbosity level (default: INFO)",
)
@click.option(
    "--show-context",
    is_flag=True,
    help="Show structured context [key=value] in log messages",
)
@pass_context
def cli(ctx: CLIContext, debug: bool, log_level: str, show_context: bool):
    """
    RV-Experiment - Android Testing Orchestrator for Monitored Operations

    ### CLI Features:

    **Commands:**
    - `run`: Execute experiments with tool specification parsing or configuration files
    - `config`: Generate configuration templates for different experiment scenarios
    - `list-tools`: Display available testing tools and their capabilities
    - `validate`: Validate configuration files and tool specifications

    **Tool Specification DSL:**
    Format: `tool[:variant1][:variant2][@param1=value1,param2=value2]`

    Examples:
    - Basic: `monkey`, `droidbot`, `ape`
    - With variants: `droidbot:dfs_greedy`, `rvagent:multimode`
    - Multiple tools: `monkey,droidbot:dfs_greedy,rvagent:pure_algorithm`

    **Monitored Operations Support:**
    - `--specification-set jca`: JCA cryptography API monitoring
    - `--specification-set generic`: Generic programming patterns monitoring
    - `--specification-set custom`: User-defined monitored operations

    **Directory Structure:**
    Standard directory structure for experiments and artifacts:
    - results/{experiment_id}/: Individual experiment results
    - out/: Shared pre-processing artifacts (instrumented APKs, static analysis)
    - mop_out/: Generated monitor files

    **Quick Start:**
    ```bash
    # Simple experiment with defaults
    rv-experiment run --tools monkey

    # Advanced experiment with variants and monitored operations
    rv-experiment run --tools monkey,droidbot:dfs_greedy --specification-set jca

    # Use configuration file
    rv-experiment run --config experiment_config.json
    ```
    """
    # Configure CLI context with clean patterns
    ctx.configure_logging(debug, log_level, show_context)


@cli.command()
@click.option(
    "--tools",
    "-t",
    default="monkey",
    envvar=ENV_TOOLS,
    help="Comma-separated tools with variants and parameters\n"
    "Format: tool1[:variants][@params],tool2[:variants][@params]\n"
    "Examples: monkey,droidbot:dfs_greedy,rvagent:multimode",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Configuration file path (JSON format)",
)
@click.option(
    "--timeouts",
    default=str(DEFAULT_TIMEOUT),
    envvar=ENV_TIMEOUTS,
    callback=_timeouts_callback,
    help=(
        "Execution timeouts in seconds, comma-separated "
        f'(e.g. "300" or "60,300"; default: {DEFAULT_TIMEOUT})'
    ),
)
@click.option(
    "--repetitions",
    "-r",
    default=DEFAULT_REPETITIONS,
    envvar=ENV_REPETITIONS,
    help=f"Number of repetitions (default: {DEFAULT_REPETITIONS})",
)
@click.option(
    "--apks-dir",
    "-a",
    default=f"./{DEFAULT_APKS_DIR}/",
    envvar=ENV_APKS_DIR,
    type=click.Path(),
    help=f"Directory containing APK files (default: ./{DEFAULT_APKS_DIR}/)",
)
@click.option(
    "--specification-set",
    default=DEFAULT_SPEC_SET,
    envvar=ENV_SPEC_SET,
    type=click.Choice(["jca", "generic", "custom"]),
    help=f"Monitored operations specification set (default: {DEFAULT_SPEC_SET})",
)
@click.option(
    "--custom-specs-dir",
    type=click.Path(exists=True),
    help="Custom specification directory path (required when --specification-set=custom)",
)
@click.option(
    "--custom-aspects-dir",
    type=click.Path(exists=True),
    help="Custom AspectJ aspects directory path (optional, defaults to standard RVSEC aspects)",
)
@click.option(
    "--generate-monitors/--skip-monitors",
    default=True,
    envvar=ENV_SKIP_MONITORS,
    help="Generate runtime verification monitors (default: enabled)",
)
@click.option(
    "--instrument-apks/--skip-instrument",
    default=True,
    envvar=ENV_SKIP_INSTRUMENT,
    help="Instrument APKs with monitors (default: enabled)",
)
@click.option(
    "--instrumentation-variant",
    default="ajc",
    envvar=ENV_INSTRUMENTATION_VARIANT,
    type=click.Choice(["ajc", "dexlib2"]),
    help=(
        "Instrumentation backend (gh52). 'ajc' = legacy dex2jar+ajc+d8 pipeline; "
        "'dexlib2' = DEX-native pipeline via the rvsec-instrumentation-dexlib2 Java CLI. "
        "Default 'ajc' during Phase 4-5 coexistence."
    ),
)
@click.option(
    "--static-analysis/--skip-static",
    default=True,
    envvar=ENV_SKIP_STATIC_ANALYSIS,
    help="Run static analysis on APKs (default: enabled)",
)
@click.option(
    "--output-dir",
    type=click.Path(),
    help="Output directory for experiment results (default: auto-generated)",
)
@click.option(
    "--no-window/--window",
    default=True,
    envvar=ENV_NO_WINDOW,
    help="Run emulator in headless mode (default: headless)",
)
@click.option(
    "--run-execution/--skip-execution",
    default=True,
    envvar=ENV_SKIP_EXECUTION,
    help="Execute tasks after preprocessing (default: enabled)",
)
@click.option(
    "--quarantine/--no-quarantine",
    "enable_quarantine",
    default=True,
    envvar=ENV_NO_QUARANTINE,
    help=(
        "Enable ajc library-class quarantine phase (gh50 §16/§19). "
        "Default: enabled. Use --no-quarantine for empirical comparison "
        "of recovery rate vs MOP visibility loss. Only affects the ajc "
        "variant (dexlib2 has no quarantine phase)."
    ),
)
@click.option(
    "--device-port",
    type=int,
    default=None,
    envvar=ENV_DEVICE_PORT,
    help="Emulator port for parallel execution (default: 5554)",
)
@click.option(
    "--apks-filter",
    type=click.Path(exists=True),
    envvar=ENV_APKS_FILTER,
    help="Text file with APK filenames to process (one per line)",
)
@click.option(
    "--logcat-diagnostics/--no-logcat-diagnostics",
    default=False,
    envvar=ENV_LOGCAT_DIAGNOSTICS,
    help=(
        "Capture execution-level diagnostic events (crashes, VerifyError, ANR) "
        "into app_events.csv (gh72). Default off — capture stays byte-identical "
        "to the RVSEC/RVSEC-COV baseline. Positive flag, so RV_LOGCAT_DIAGNOSTICS "
        "is honored directly by Click without entry-point translation."
    ),
)
@click.option(
    "--name",
    type=str,
    default=None,
    envvar=ENV_EXPERIMENT_NAME,
    help="Experiment name (used for results directory naming)",
)
@click.option(
    "--resume-dir",
    type=click.Path(exists=True),
    default=None,
    envvar=ENV_RESUME_DIR,
    help="Resume experiment from existing results directory",
)
@click.option(
    "--analysis-timeout",
    type=int,
    default=None,
    envvar=ENV_SA_TIMEOUT,
    help="Static analysis timeout in seconds. Overrides RV_SA_TIMEOUT (gh55 INV-EXP-32: CLI > env > default).",
)
@click.option(
    "--jvm-memory",
    type=str,
    default=None,
    envvar=ENV_JVM_MEMORY,
    help="JVM memory for static analysis (e.g. '4g'). Overrides RV_JVM_MEMORY (gh55 INV-EXP-32: CLI > env > default).",
)
@pass_context
@ErrorHandler.handle_errors(component="CLIContext", phase="run_experiment")
def run(
    ctx: CLIContext,
    tools: str,
    config: Optional[str],
    timeouts: List[int],
    repetitions: int,
    apks_dir: str,
    specification_set: str,
    custom_specs_dir: Optional[str],
    custom_aspects_dir: Optional[str],
    generate_monitors: bool,
    instrument_apks: bool,
    instrumentation_variant: str,
    static_analysis: bool,
    output_dir: Optional[str],
    no_window: bool,
    run_execution: bool,
    enable_quarantine: bool,
    device_port: Optional[int],
    apks_filter: Optional[str],
    logcat_diagnostics: bool,
    name: Optional[str],
    resume_dir: Optional[str],
    analysis_timeout: Optional[int],
    jvm_memory: Optional[str],
):
    """
    Execute experiment with modern tool specification parsing and configuration support.

    ### Execution Strategy:
    This command supports two primary execution modes:
    1. **CLI Mode**: Direct tool specification via command line arguments
    2. **Config Mode**: File-based configuration for complex experiment scenarios

    ### CLI Mode Examples:
    ```bash
    # Basic tools
    rv-experiment run --tools monkey
    rv-experiment run --tools droidbot:dfs_greedy

    # Multiple tools comparison
    rv-experiment run --tools monkey,droidbot:dfs_greedy --repetitions 3
    ```

    ### Config Mode Examples:
    ```bash
    # Use predefined configuration file
    rv-experiment run --config experiment_config.json
    ```

    ### Monitored Operations:
    The system supports experiments with different specification sets:
    - `jca`: JCA cryptography API monitoring for security-related operations
    - `generic`: Generic programming pattern monitoring (e.g., Iterator usage patterns)
    - `custom`: Custom specification sets for domain-specific monitored operations
    """
    # `timeouts` arrives already parsed to List[int] by the --timeouts Click
    # callback (INV-EXP-33), which runs before this @handle_errors-wrapped body.
    with ctx.logger.with_context(
        command="run",
        tools=tools,
        config=config,
        timeouts=timeouts,
        repetitions=repetitions,
        specification_set=specification_set,
    ):
        ctx.logger.info(LOG_START.format(phase="experiment execution"))

        # Early validation: "custom" spec set requires a user-provided directory of .mop files.
        # This check happens before config creation to provide a clear CLI error message.
        if specification_set == "custom" and not custom_specs_dir:
            raise click.ClickException(
                "Custom specification directory (--custom-specs-dir) is required "
                "when using --specification-set=custom"
            )

        try:
            # Two mutually exclusive config sources: --config (JSON file) takes
            # precedence over CLI arguments. Both produce an ExperimentConfig that
            # follows the same validation and execution path below.
            if config:
                ctx.logger.info(f"Loading experiment configuration from: {config}")
                experiment_config = ExperimentConfig.from_file(config)
                ctx.logger.info(
                    f"Loaded configuration for experiment: {experiment_config.name}"
                )

            else:
                # CLI mode: parse tool DSL, detect resume, build ExperimentConfig.
                experiment_config = _create_experiment_config_from_cli(
                    ctx,
                    tools,
                    timeouts,
                    repetitions,
                    apks_dir,
                    specification_set,
                    custom_specs_dir,
                    custom_aspects_dir,
                    generate_monitors,
                    instrument_apks,
                    static_analysis,
                    output_dir,
                    no_window,
                    run_execution,
                    device_port,
                    apks_filter,
                    name,
                    resume_dir,
                    instrumentation_variant=instrumentation_variant,
                    enable_quarantine=enable_quarantine,
                    analysis_timeout=analysis_timeout,
                    jvm_memory=jvm_memory,
                    logcat_diagnostics=logcat_diagnostics,
                )

            # Validate before execution to catch errors early (missing APKs, unknown tools,
            # invalid spec set) rather than failing mid-experiment after pre-processing.
            experiment_config.validate()

            # Display experiment information
            tool_names = [tc.name for tc in experiment_config.tool_configs]
            click.echo(f"🧪 Starting experiment: {experiment_config.name}")
            click.echo(f"🔧 Tools: {', '.join(tool_names)}")
            click.echo(
                f"📊 Monitored operations: {experiment_config.specification_set}"
            )
            timeouts_display = ", ".join(f"{t}s" for t in timeouts)
            click.echo(f"⏱️  Timeouts: {timeouts_display}, Repetitions: {repetitions}")
            click.echo(f"📁 Output directory: {experiment_config.output_dir}")
            click.echo(f"📱 APK directory: {apks_dir}")

            # Execute experiment using existing infrastructure
            ctx.logger.info("Executing experiment via experiment controller")
            execute_with_config(experiment_config)

            click.echo("✅ Experiment completed successfully!")
            click.echo(f"📊 Results available in: {experiment_config.output_dir}")
            ctx.logger.info(LOG_COMPLETE.format(phase="experiment execution"))

        except Exception as e:
            ctx.logger.error(f"Experiment execution failed: {e}")
            click.echo(f"❌ Experiment failed: {e}", err=True)
            sys.exit(1)


@cli.command()
@click.option(
    "--template-type",
    type=click.Choice(["basic", "advanced", "research"]),
    default="basic",
    help="Configuration template type (default: basic)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file path for configuration template",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json"]),
    default="json",
    help="Configuration template format (default: json)",
)
@pass_context
@ErrorHandler.handle_errors(component="CLIContext", phase="generate_config")
def config(
    ctx: CLIContext, template_type: str, output: Optional[str], output_format: str
):
    """
    Generate configuration templates for complex experiment scenarios.

    ### Template Types:

    **Basic Template:**
    Simple configuration for standard experiments with common tools and JCA monitored operations.
    Suitable for initial experiments and basic tool comparisons.

    **Advanced Template:**
    Comprehensive configuration showcasing multiple tools, variants, and extensive
    parameter customization for thorough testing scenarios.

    **Research Template:**
    Specialized configuration for academic research with comprehensive monitored operations
    coverage, statistical rigor, and extensive result collection.

    ### Examples:
    ```bash
    # Generate basic JSON template
    rv-experiment config --template-type basic --output basic_config.json

    # Generate advanced configuration for comprehensive testing
    rv-experiment config --template-type advanced --output advanced_config.json

    # Generate research template for academic studies
    rv-experiment config --template-type research --output research_config.json
    ```

    ### Monitored Operations Integration:
    Each template includes appropriate specification set selection:
    - Basic: JCA cryptography API monitoring
    - Advanced: Configurable specification sets for different scenarios
    - Research: Comprehensive specification coverage for thorough analysis
    """
    ctx.logger.info(
        f"Generating {template_type} {output_format} configuration template"
    )

    try:
        # Create template configuration based on type
        template_config: ExperimentConfig = _create_template_configuration(
            template_type
        )

        # Convert to specified format
        if output_format == "json":
            config_content = json.dumps(template_config.to_dict(), indent=2)
        else:
            raise ValueError(f"Unsupported format: {output_format}")

        # Output configuration
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w") as f:
                f.write(config_content)

            click.echo(
                f"✅ {template_type.title()} configuration template saved to: {output}"
            )
            ctx.logger.info(f"Configuration template saved: {output}")
        else:
            click.echo(config_content)

    except Exception as e:
        ctx.logger.error(f"Configuration generation failed: {e}")
        click.echo(f"❌ Configuration generation failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--detailed",
    is_flag=True,
    help="Show detailed tool information including variants and capabilities",
)
@click.option(
    "--filter-by",
    type=click.Choice(["all", "basic", "llm", "research"]),
    default="all",
    help="Filter tools by category (default: all)",
)
@pass_context
@ErrorHandler.handle_errors(component="CLIContext", phase="list_tools")
def list_tools(ctx: CLIContext, detailed: bool, filter_by: str):
    """
    List available testing tools and their capabilities.

    ### Tool Categories:

    **Basic Tools:**
    Traditional Android testing tools (Monkey, DroidBot, APE, etc.)
    Available immediately without additional configuration.

    **LLM Tools:**
    AI-driven testing tools including RVAndroid with various LLM backends.
    Requires LLM configuration integration (currently in development).

    **Research Tools:**
    Experimental and research-oriented testing tools for academic studies.

    ### Examples:
    ```bash
    # List all tools with basic information
    rv-experiment list-tools

    # Show detailed information including variants
    rv-experiment list-tools --detailed

    # Filter basic tools only
    rv-experiment list-tools --filter-by basic --detailed
    ```

    ### Tool Specification DSL:
    Each tool supports the modern specification format:
    - Basic usage: `tool_name`
    - With variants: `tool_name:variant1:variant2`
    - With parameters: `tool_name@param1=value1,param2=value2`
    - Combined: `tool_name:variant@param1=value1,param2=value2`
    """
    ctx.logger.info(f"Listing available testing tools (filter: {filter_by})")

    try:
        tools = ctx.tool_registry.get_all_tools()

        if not tools:
            click.echo(
                "❌ No tools available. Ensure tool modules are properly installed."
            )
            return

        # Filter tools by category if specified
        if filter_by != "all":
            filtered_tools = []
            for tool in tools:
                tool_category = getattr(tool, "category", "basic").lower()
                if filter_by == tool_category:
                    filtered_tools.append(tool)
            tools = filtered_tools

        if not tools:
            click.echo(f"❌ No tools found for category: {filter_by}")
            return

        click.echo(f"\n🔧 Available Testing Tools ({filter_by.title()}):")
        click.echo("=" * 60)

        for tool in tools:
            tool_name = tool.name
            tool_description = getattr(tool, "description", "No description available")
            tool_category = getattr(tool, "category", "basic")

            click.echo(f"\n📦 {tool_name} ({tool_category})")
            click.echo(f"   Description: {tool_description}")

            if detailed:
                # Show variants if available
                variants = ctx.tool_registry.get_tool_variants(tool.name)
                if variants and len(variants) > 1:
                    variant_list = [v for v in variants if v != "default"]
                    if variant_list:
                        click.echo(f"   Variants: {', '.join(variant_list)}")

                # Show capabilities if available
                if hasattr(tool, "capabilities"):
                    capabilities = ", ".join(tool.capabilities)
                    click.echo(f"   Capabilities: {capabilities}")

                # Show supported parameters if available
                if hasattr(tool, "supported_parameters"):
                    params = ", ".join(tool.supported_parameters.keys())
                    click.echo(f"   Parameters: {params}")

                # Show example usage
                example_usage = f"{tool_name}"
                if (
                    hasattr(tool, "default_variant")
                    and tool.default_variant != "default"
                ):
                    example_usage += f":{tool.default_variant}"
                if hasattr(tool, "example_parameters"):
                    param_str = ",".join(
                        [f"{k}={v}" for k, v in tool.example_parameters.items()]
                    )
                    example_usage += f"@{param_str}"

                click.echo(f"   Example: {example_usage}")

        click.echo(f"\n✅ Total: {len(tools)} tools available")

        if not detailed:
            click.echo(
                "\n💡 Use --detailed flag for more information about tool variants and parameters"
            )

    except Exception as e:
        ctx.logger.error(f"Tool listing failed: {e}")
        click.echo(f"❌ Tool listing failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("config_file", type=click.Path(exists=True))
@pass_context
@ErrorHandler.handle_errors(component="CLIContext", phase="validate_config")
def validate(ctx: CLIContext, config_file: str):
    """
    Validate configuration files and tool specifications.

    ### Validation Features:
    - Configuration file structure and syntax validation
    - Tool specification format verification
    - Tool availability checking against registry
    - Parameter validation for known tools
    - Monitored operations specification validation

    ### Examples:
    ```bash
    # Validate configuration file
    rv-experiment validate experiment_config.json
    ```

    ### Validation Checks:
    1. **File Format**: JSON syntax and structure validation
    2. **Required Fields**: Ensures all necessary configuration fields are present
    3. **Tool Specifications**: Validates tool names against available registry
    4. **Parameter Types**: Checks parameter types and ranges where applicable
    5. **Directory Paths**: Validates APK directories and output paths
    6. **Specification Sets**: Verifies monitored operations specification availability
    """
    ctx.logger.info(f"Validating configuration file: {config_file}")

    try:
        # Load and validate configuration
        config_path = Path(config_file)

        with open(config_path, "r") as f:
            config_data = json.load(f)

        # Create ExperimentConfig to leverage validation logic
        experiment_config = ExperimentConfig.from_dict(config_data)
        experiment_config.validate()

        # Additional CLI-specific validations
        validation_errors = []

        # Validate tool availability
        available_tools = [tool.name for tool in ctx.tool_registry.get_all_tools()]
        for tool_config in experiment_config.tool_configs:
            if tool_config.name not in available_tools:
                validation_errors.append(
                    f"Tool '{tool_config.name}' not available in registry"
                )

        # Report validation results
        if validation_errors:
            click.echo("❌ Configuration validation failed:")
            for error in validation_errors:
                click.echo(f"   • {error}")
            sys.exit(1)
        else:
            click.echo("✅ Configuration file is valid")
            click.echo(f"   • Experiment: {experiment_config.name}")
            click.echo(
                f"   • Tools: {', '.join([tc.name for tc in experiment_config.tool_configs])}"
            )
            click.echo(
                f"   • Monitored operations: {experiment_config.specification_set}"
            )

        ctx.logger.info("Configuration validation completed successfully")

    except json.JSONDecodeError as e:
        click.echo(f"❌ Invalid JSON format: {e}")
        sys.exit(1)
    except Exception as e:
        ctx.logger.error(f"Configuration validation failed: {e}")
        click.echo(f"❌ Configuration validation failed: {e}")
        sys.exit(1)


def _split_tool_specifications(tools_string: str) -> list[str]:
    """
    Split tool specification string into individual tool specs.

    Handles the case where parameters use comma as separator:
    Format: tool1[:variant][@param1=val1,param2=val2],tool2[:variant][@params]

    The split happens at commas that are followed by a tool name pattern
    (word followed by either : or @ or end of string).

    Args:
        tools_string: Comma-separated tool specifications

    Returns:
        List of individual tool specification strings
    """
    import re

    # Strategy: find all tool specs by matching the pattern
    # tool_name[:variant][@params] where params can contain commas
    # A new tool starts with a word that's NOT preceded by = (which would make it a param value)
    # Ambiguity: commas separate BOTH tool specs AND parameter key-value pairs.
    # "monkey,droidbot@a=1,b=2" has 3 comma-separated parts but only 2 tools.
    # Strategy: a part starting with a valid identifier (followed by :, @, or end)
    # is treated as a new tool spec; anything else is a parameter continuation
    # belonging to the previous tool spec.
    specs = []
    current_spec = []
    parts = tools_string.split(",")

    for part in parts:
        stripped = part.strip()
        if not stripped:
            continue

        # Heuristic: parameter continuations look like "b=2" or "value" (no colon/@ prefix).
        # New tool specs look like "droidbot", "droidbot:dfs_greedy", or "rvagent@temp=0.3".
        is_new_tool = bool(re.match(r"^[a-zA-Z_][a-zA-Z0-9_-]*(?::|@|$)", stripped))

        if is_new_tool and current_spec:
            specs.append(",".join(current_spec))
            current_spec = [stripped]
        else:
            current_spec.append(stripped)

    # Don't forget the last spec
    if current_spec:
        specs.append(",".join(current_spec))

    return specs


def _create_experiment_config_from_cli(
    ctx: CLIContext,
    tools: str,
    timeouts: List[int],
    repetitions: int,
    apks_dir: str,
    specification_set: str,
    custom_specs_dir: Optional[str],
    custom_aspects_dir: Optional[str],
    generate_monitors: bool,
    instrument_apks: bool,
    static_analysis: bool,
    output_dir: Optional[str],
    no_window: bool,
    run_execution: bool = True,
    device_port: Optional[int] = None,
    apks_filter: Optional[str] = None,
    name: Optional[str] = None,
    resume_dir: Optional[str] = None,
    # gh52 variant flag — kwarg with default to keep callers (and tests)
    # written before gh52 source-compatible. CLI plumbing always passes it.
    instrumentation_variant: str = "ajc",
    # gh50 §22 quarantine toggle — kwarg with default to keep callers (and
    # tests) written before §22 source-compatible. CLI plumbing always passes it.
    enable_quarantine: bool = True,
    # gh55 INV-EXP-32: precedence CLI > env > default. None means "fall back to
    # env or RVStaticAnalysisConfig default" (resolved in get_static_analysis_config).
    analysis_timeout: Optional[int] = None,
    jvm_memory: Optional[str] = None,
    # gh72 opt-in diagnostics flag — kwarg with default to keep callers (and
    # tests) written before gh72 source-compatible. CLI plumbing always passes it.
    logcat_diagnostics: bool = False,
) -> ExperimentConfig:
    """
    Create ExperimentConfig from CLI arguments with comprehensive tool parsing.

    ### Configuration Creation Strategy:
    - Parses tool specifications using DSL format
    - Creates ToolConfig instances for each parsed tool
    - Generates unique experiment identifier with timestamp
    - Applies intelligent defaults for unspecified parameters
    - Validates configuration integrity before returning

    Args:
        ctx: CLI context with logging and tool registry access
        tools: Comma-separated tool specifications string
        timeouts: Execution timeouts in seconds (already parsed to a list)
        repetitions: Number of experiment repetitions
        apks_dir: Directory containing APK files
        specification_set: Monitored operations specification set (jca, generic, custom)
        custom_specs_dir: Custom specification directory (required for custom specification set)
        custom_aspects_dir: Custom AspectJ aspects directory (optional, defaults to standard RVSEC)
        generate_monitors: Flag to enable monitor generation
        instrument_apks: Flag to enable APK instrumentation
        static_analysis: Flag to enable static analysis
        output_dir: Optional custom output directory

    Returns:
        Configured ExperimentConfig instance ready for execution

    Raises:
        ValueError: If tool specifications are invalid
        ConfigurationError: If configuration cannot be created
    """
    try:
        # Parse tool specifications using DSL
        # Note: Can't simply split by comma because parameters use comma as separator
        # Format: tool1[:variant][@param1=val1,param2=val2],tool2[:variant][@params]
        # We need to split by comma only when NOT inside the @...  parameter section
        tool_specs = _split_tool_specifications(tools)
        tool_configs = []

        for tool_spec in tool_specs:
            tool_configs.extend(ctx.parse_tool_specification(tool_spec))

        # gh55 INV-EXP-30 / gh55 D8: resolve RV_HUMANOID_URL at L5 and inject
        # into ToolConfig.parameters for any humanoid tool entry. The factory
        # merge ({**variant_defaults, **parameters}) places this value last so
        # it overrides the variant default ("127.0.0.1:50405"). When the env
        # var is unset, we DO NOT inject — variant default carries through.
        # No L2 module reads os.environ; this is the canonical resolution site.
        humanoid_url_env = os.environ.get(ENV_HUMANOID_URL)
        if humanoid_url_env:
            for tc in tool_configs:
                if tc.name == "humanoid":
                    tc.parameters["humanoid_url"] = humanoid_url_env

        # Resume detection: three mutually exclusive paths determine how the
        # experiment identity and output directory are resolved.
        # Precedence: --resume-dir > --name (with existing tasks.json) > new experiment.
        #
        # Resume invariant: ALL pre-processing flags are forced to False on resume.
        # This prevents re-generating monitors and re-instrumenting APKs, which
        # would overwrite the artifacts that the original run already produced.
        # rv-platform handles task-level resume via tasks.json independently.
        resume_mode = False

        if resume_dir:
            # Explicit resume: --resume-dir points directly to an existing
            # results directory (e.g., results/my_exp/). The experiment_id is
            # derived from the directory name for consistency.
            experiment_id = Path(resume_dir).name
            output_dir = str(resume_dir)
            resume_mode = True
            generate_monitors = False
            instrument_apks = False
            static_analysis = False
            ctx.logger.info(f"Resuming experiment from {resume_dir}")

        elif name:
            # Named experiment: --name provides a stable identifier across runs.
            # If tasks.json exists from a previous run, this becomes an implicit
            # resume (same pre-processing skip behavior as --resume-dir).
            experiment_id = name
            results_path = Path(f"./{RESULTS_DIR}/{name}")
            tasks_json = results_path / "tasks.json"

            if tasks_json.exists():
                resume_mode = True
                generate_monitors = False
                instrument_apks = False
                static_analysis = False
                ctx.logger.info(
                    f"Resuming experiment '{name}' — auto-skipping pre-processing"
                )

            if not output_dir:
                output_dir = str(results_path)

        else:
            # New experiment: generate a unique ID with timestamp + random suffix
            # to avoid collisions when launching experiments in quick succession.
            experiment_id = f"cli_experiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # Determine output directory (if not already set by resume logic)
        if not output_dir:
            output_dir = f"./{RESULTS_DIR}/{experiment_id}"

        # output_dir and results_dir point to the same flat directory.
        # output_dir is used by pre-processing (monitors, instrumented APKs);
        # results_dir is used by rv-platform (tasks.json, CSV, JSON reports).
        # Both are the same directory to keep all experiment artifacts together.
        experiment_config = ExperimentConfig(
            name=experiment_id,
            description="Experiment created via CLI interface",
            output_dir=output_dir,
            results_dir=output_dir,
            tool_configs=tool_configs,
            repetitions=repetitions,
            timeouts=timeouts,
            no_window=no_window,
            generate_monitors=generate_monitors,
            instrument_apks=instrument_apks,
            instrumentation_variant=instrumentation_variant,
            run_static_analysis=static_analysis,
            run_execution=run_execution,
            enable_quarantine=enable_quarantine,
            logcat_diagnostics=logcat_diagnostics,
            specification_set=specification_set,
            custom_specs_dir=custom_specs_dir,
            custom_aspects_dir=custom_aspects_dir,
            apks_dir=apks_dir,
            device_port=device_port,
            apks_filter=apks_filter,
            analysis_timeout=analysis_timeout,
            jvm_memory=jvm_memory,
            resume_mode=resume_mode,
            metadata={
                "created_via": "cli",
                "tool_specifications": tools,
            },
        )

        ctx.logger.info(f"Created experiment configuration: {experiment_id}")
        return experiment_config

    except Exception as e:
        raise ConfigurationError(
            f"Failed to create experiment configuration from CLI arguments: {e}"
        )


def _create_template_configuration(template_type: str) -> ExperimentConfig:
    """
    Create template configuration for different experiment scenarios.

    ### Template Creation Strategy:
    - Basic: Simple single-tool experiments with standard monitored operations
    - Advanced: Multi-tool comparisons with variants and comprehensive configuration
    - Research: Academic-focused configuration with statistical rigor and documentation

    Args:
        template_type: Type of template to create ('basic', 'advanced', 'research')

    Returns:
        ExperimentConfig instance configured for the specified template type

    Raises:
        ValueError: If template type is not supported
    """
    if template_type == "basic":
        return ExperimentConfig(
            name="basic_experiment_template",
            description="Basic experiment template with standard tools and JCA monitored operations",
            tool_configs=[
                ToolConfig(name="monkey"),
                ToolConfig(name="droidbot", variant="dfs_greedy"),
            ],
            repetitions=DEFAULT_REPETITIONS,
            timeouts=[DEFAULT_TIMEOUT],
            specification_set="jca",
            generate_monitors=True,
            instrument_apks=True,
            run_static_analysis=True,
            metadata={
                "template_type": "basic",
                "target_audience": "general_testing",
                "monitored_operations_focus": "JCA cryptography API monitoring",
            },
        )

    elif template_type == "advanced":
        return ExperimentConfig(
            name="advanced_experiment_template",
            description="Advanced experiment template with multiple tools and comprehensive configuration",
            tool_configs=[
                ToolConfig(name="monkey", parameters={"seed": 42, "throttle": 100}),
                ToolConfig(
                    name="droidbot", variant="dfs_greedy", parameters={"count": 2000}
                ),
                ToolConfig(name="ape", parameters={"running_minutes": 10}),
                # Note: RVAndroid configuration will be added when LLM integration is complete
            ],
            repetitions=3,
            timeouts=[300, 600, 900],
            specification_set="generic",
            generate_monitors=True,
            instrument_apks=True,
            run_static_analysis=True,
            apk_patterns=["*.apk", "!*test*.apk", "!*debug*.apk"],
            metadata={
                "template_type": "advanced",
                "target_audience": "comprehensive_testing",
                "execution_time_estimate": "2-4 hours",
                "resource_requirements": "high",
            },
        )

    elif template_type == "research":
        return ExperimentConfig(
            name="research_experiment_template",
            description="Research-focused template for academic studies with statistical rigor",
            tool_configs=[
                ToolConfig(
                    name="monkey", variant="fixed_seed", parameters={"seed": 42}
                ),
                ToolConfig(
                    name="droidbot", variant="dfs_greedy", parameters={"count": 3000}
                ),
                ToolConfig(name="ape", parameters={"running_minutes": 15}),
            ],
            repetitions=5,  # Higher repetitions for statistical validity
            timeouts=[600, 1200],  # Longer timeouts for thorough exploration
            specification_set="jca",
            generate_monitors=True,
            instrument_apks=True,
            run_static_analysis=True,
            metadata={
                "template_type": "research",
                "target_audience": "academic_research",
                "statistical_design": "repeated_measures",
                "execution_time_estimate": "4-8 hours",
                "citation_ready": True,
                "monitored_operations_focus": "Comprehensive JCA cryptography API analysis",
            },
        )

    else:
        raise ValueError(f"Unknown template type: {template_type}")


@ErrorHandler.handle_errors(component="CLIMain", phase="main_entry_point")
def main():
    """
    Main entry point for the RV-Experiment CLI.

    ### Entry Point Strategy:
    - Provides comprehensive error handling for all CLI operations
    - Supports graceful interruption with proper cleanup
    - Maintains proper exit codes for integration with automation systems
    - Demonstrates clean architectural patterns through CLI usage

    ### Error Handling:
    - Uses rv-android-core ErrorHandler for consistent error management
    - Provides user-friendly error messages with technical details in logs
    - Implements graceful degradation for missing components
    - Supports both interactive and programmatic usage patterns
    """
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\n🛑 Operation cancelled by user", err=True)
        sys.exit(130)  # Standard exit code for SIGINT
    except SystemExit:
        # Re-raise SystemExit to maintain proper exit codes
        raise
    except Exception as e:
        # Final safety net - should be rare due to decorator usage
        click.echo(f"💥 Fatal error: {e}", err=True)
        sys.exit(1)


def run_local():
    ctx = CLIContext()
    ctx.configure_logging(True)

    # for tool in ctx.tool_registry.get_all_tools():
    #     print(f"Tool: {tool.name}")

    config("basic", "/home/pedro/tmp/basic._config.json", "json")


if __name__ == "__main__":
    # main()
    run_local()
