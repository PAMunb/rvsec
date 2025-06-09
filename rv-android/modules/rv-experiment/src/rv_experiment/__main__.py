#!/usr/bin/env python3
"""
RV-Experiment CLI - Modern Command Line Interface for Android Testing Experiments

### Architectural Overview:
This module serves as the primary command-line interface for orchestrating Android application
testing experiments within the RV-Android platform. It implements a modern CLI architecture
that coordinates configuration across multiple specialized modules while maintaining clear
separation of concerns and module independence.

### Key Architectural Decisions:
- **Configuration Coordination**: Acts as the central coordinator for experiment-specific
  configurations while respecting module autonomy and independence
- **Modern CLI Design**: Uses Click framework for robust argument parsing, subcommands,
  and comprehensive help documentation
- **Component Integration**: Leverages existing ErrorHandler and LoggingManager components
  for consistent error handling and logging across the experiment lifecycle
- **Module Independence**: Maintains strict module boundaries while providing unified
  experiment orchestration capabilities

### Role in the System:
- Primary entry point for all experiment-related operations
- Coordinates configuration distribution across dependent modules
- Provides both interactive CLI and programmatic interfaces for experiment execution
- Implements comprehensive error handling and logging for experiment operations
- Supports both production and development/testing workflows

### Design Patterns:
- **Command Pattern**: Click commands encapsulate experiment operations
- **Factory Pattern**: ExperimentOrchestrator creates and configures experiment components
- **Configuration Pattern**: Centralized configuration coordination with module-specific distribution
- **Event-Driven Pattern**: Integration with event bus for experiment monitoring
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

import click

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT, LOG_START, LOG_COMPLETE
from rv_android_core.event import get_event_bus, EventType, EventBus
from rv_experiment.orchestrator import ExperimentOrchestrator
from rv_experiment.config import ExperimentConfiguration, ToolConfiguration


class CLIContext:
    """
    Context object for maintaining CLI state and shared resources.
    
    ### Architectural Decisions:
    - Provides centralized access to shared resources across CLI commands
    - Implements dependency injection for CLI components
    - Maintains consistent error handling and logging configuration
    - Enables resource sharing and cleanup across command execution
    
    ### Role in the System:
    - Central repository for CLI state and configuration
    - Provides access to logging, error handling, and event management
    - Facilitates consistent behavior across different CLI commands
    - Manages resource lifecycle for CLI operations
    """
    
    def __init__(self):
        """Initialize CLI context with shared components."""
        # Initialize core components using existing architecture
        self.error_handler = ErrorHandler.get_instance()
        self.logging_manager = LoggingManager.get_instance()
        self.event_bus = get_event_bus()
        
        # Set up logger for CLI operations
        self.logger = self.logging_manager.get_logger(
            "rv_experiment.cli",
            {CONTEXT_COMPONENT: "CLI"}
        )
        
        # CLI state
        self.debug = False
        self.config_file = None
        self.experiment_config = None
        
    def configure_logging(self, debug: bool = False):
        """
        Configure logging for CLI operations.
        
        Args:
            debug: Enable debug level logging
        """
        import logging
        
        # Configure logging manager for CLI usage
        self.logging_manager.configure_output(
            console=True,
            file=False,  # File logging will be configured per-experiment
            console_level=logging.DEBUG if debug else logging.INFO,
            console_format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Silence noisy third-party loggers
        logging.getLogger("androguard").setLevel(logging.ERROR)
        logging.getLogger("matplotlib").setLevel(logging.ERROR)
        logging.getLogger("PIL").setLevel(logging.ERROR)
        
        self.debug = debug
        self.logger.info("CLI logging configured")
        
    def load_configuration(self, config_file: Optional[str] = None) -> ExperimentConfiguration:
        """
        Load experiment configuration from file or create default.
        
        Args:
            config_file: Path to configuration file
            
        Returns:
            Loaded experiment configuration
            
        Raises:
            ValueError: If configuration file is invalid
        """
        if config_file and Path(config_file).exists():
            try:
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                self.experiment_config = ExperimentConfiguration.from_dict(config_data)
                self.config_file = config_file
                self.logger.info(f"Loaded configuration from {config_file}")
            except Exception as e:
                error_msg = f"Failed to load configuration from {config_file}: {e}"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
        else:
            # Create default configuration
            self.experiment_config = ExperimentConfiguration()
            self.logger.info("Using default experiment configuration")
            
        return self.experiment_config


# CLI Context setup
pass_context = click.make_pass_decorator(CLIContext, ensure=True)


@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.option('--config', '-c', 'config_file', 
              type=click.Path(exists=False), 
              help='Path to experiment configuration file')
@pass_context
def cli(ctx: CLIContext, debug: bool, config_file: Optional[str]):
    """
    RV-Experiment - Android Application Testing Experiment Orchestrator
    
    A modern CLI for coordinating and executing comprehensive Android application
    testing experiments with runtime verification capabilities.
    
    ### Experiment Types:
    - **Single Tool**: Execute experiments with individual testing tools
    - **Comparative**: Run multiple tools against the same applications
    - **Batch**: Execute experiments across multiple applications
    - **Continuous**: Long-running experiments with monitoring
    
    ### Configuration:
    Use --config to specify a JSON configuration file, or use command-line
    arguments for quick experiment setup.
    
    Examples:
        rv-experiment run-single --tool monkey --timeout 300
        rv-experiment run-comparative --tools monkey,droidbot --repetitions 3
        rv-experiment run-batch --config experiments/batch_config.json
    """
    # Configure CLI context
    ctx.configure_logging(debug)
    
    if config_file:
        try:
            ctx.load_configuration(config_file)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)


@cli.command()
@click.option('--tool', '-t', required=True, 
              help='Testing tool to use with optional variants and parameters\n'
                   'Format: tool_name[:variant1][:variant2][@param1=value1,param2=value2]\n'
                   'Examples: monkey, droidbot:dfs_greedy, rvandroid:llama:batch@temperature=0.3')
@click.option('--timeout', default=300, 
              help='Execution timeout in seconds (default: 300)')
@click.option('--repetitions', '-r', default=1, 
              help='Number of repetitions (default: 1)')
@click.option('--no-window', is_flag=True, 
              help='Run emulator without GUI window')
@click.option('--skip-monitors', is_flag=True, 
              help='Skip monitor generation phase')
@click.option('--skip-instrument', is_flag=True, 
              help='Skip instrumentation phase')
@click.option('--skip-static', is_flag=True, 
              help='Skip static analysis phase')
@click.option('--output-dir', '-o', 
              type=click.Path(), 
              help='Output directory for results')
@pass_context
def run_single(ctx: CLIContext, tool: str, timeout: int, repetitions: int,
               no_window: bool, skip_monitors: bool, skip_instrument: bool,
               skip_static: bool, output_dir: Optional[str]):
    """
    Execute a single-tool experiment.
    
    Runs an experiment using a single testing tool against configured applications.
    This is the most common experiment type for focused testing scenarios.
    
    ### Examples:
        rv-experiment run-single --tool monkey --timeout 600 --repetitions 3
        rv-experiment run-single --tool rvandroid:llama:batch --no-window 
        rv-experiment run-single --tool droidbot:dfs_greedy@count=1000 --output-dir ./results
    """
    with ctx.logger.with_context(
        command="run_single",
        tool=tool,
        timeout=timeout,
        repetitions=repetitions
    ):
        ctx.logger.info(LOG_START.format(operation=f"single-tool experiment with {tool}"))
        
        try:
            # Parse tool specification to extract name, variants, and parameters
            tool_config = ToolConfiguration.from_spec_string(tool)
            
            # Create experiment configuration
            config = ctx.experiment_config or ExperimentConfiguration()
            
            # Update configuration with CLI parameters
            config.tools = [tool_config.name]
            config.tool_configs = [tool_config]
            config.timeouts = [timeout]
            config.repetitions = repetitions
            config.no_window = no_window
            config.generate_monitors = not skip_monitors
            config.instrument = not skip_instrument
            config.static_analysis = not skip_static
            
            if output_dir:
                config.output_dir = output_dir
                
            # Validate configuration
            config.validate()
            
            # Create and execute experiment
            orchestrator = ExperimentOrchestrator(config, ctx.event_bus, ctx.logger)
            success = orchestrator.execute_single_tool_experiment()
            
            if success:
                click.echo(f"✓ Experiment completed successfully")
                ctx.logger.info(LOG_COMPLETE.format(operation=f"single-tool experiment with {tool}"))
            else:
                click.echo(f"✗ Experiment failed", err=True)
                sys.exit(1)
                
        except Exception as e:
            ctx.error_handler.handle_error(e, {
                "component": "CLI",
                "command": "run_single",
                "tool": tool
            })
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)


@cli.command()
@click.option('--tools', '-t', required=True,
              help='Comma-separated list of tools with optional variants and parameters\n'
                   'Format: tool1[:variants][@params],tool2[:variants][@params]\n'
                   'Examples: monkey,droidbot:dfs_greedy,rvandroid:llama:batch@temperature=0.3')
@click.option('--timeouts', default='300',
              help='Comma-separated list of timeouts in seconds (default: 300)')
@click.option('--repetitions', '-r', default=1,
              help='Number of repetitions (default: 1)')
@click.option('--no-window', is_flag=True,
              help='Run emulator without GUI window')
@click.option('--parallel', is_flag=True,
              help='Run tools in parallel (experimental)')
@click.option('--output-dir', '-o',
              type=click.Path(),
              help='Output directory for results')
@pass_context
def run_comparative(ctx: CLIContext, tools: str, timeouts: str, repetitions: int,
                   no_window: bool, parallel: bool, output_dir: Optional[str]):
    """
    Execute a comparative experiment across multiple tools.
    
    Runs the same experiment configuration across multiple testing tools,
    enabling direct comparison of tool effectiveness and coverage.
    
    ### Examples:
        rv-experiment run-comparative --tools monkey,droidbot:dfs_greedy --repetitions 3
        rv-experiment run-comparative --tools monkey,rvandroid:llama:batch@temperature=0.3 --timeouts 300,600,900
    """
    with ctx.logger.with_context(
        command="run_comparative",
        tools=tools,
        timeouts=timeouts,
        repetitions=repetitions
    ):
        tool_specs = [t.strip() for t in tools.split(',')]
        timeout_list = [int(t.strip()) for t in timeouts.split(',')]
        
        # Parse tool specifications
        tool_configs = []
        tool_names = []
        for tool_spec in tool_specs:
            tool_config = ToolConfiguration.from_spec_string(tool_spec)
            tool_configs.append(tool_config)
            tool_names.append(tool_config.name)
        
        ctx.logger.info(LOG_START.format(
            operation=f"comparative experiment with {len(tool_names)} tools"
        ))
        
        try:
            # Create experiment configuration
            config = ctx.experiment_config or ExperimentConfiguration()
            
            # Update configuration with CLI parameters
            config.tools = tool_names
            config.tool_configs = tool_configs
            config.timeouts = timeout_list
            config.repetitions = repetitions
            config.no_window = no_window
            config.parallel_execution = parallel
            
            if output_dir:
                config.output_dir = output_dir
                
            # Validate configuration
            config.validate()
            
            # Create and execute experiment
            orchestrator = ExperimentOrchestrator(config, ctx.event_bus, ctx.logger)
            success = orchestrator.execute_comparative_experiment()
            
            if success:
                click.echo(f"✓ Comparative experiment completed successfully")
                ctx.logger.info(LOG_COMPLETE.format(
                    operation=f"comparative experiment with {len(tool_names)} tools"
                ))
            else:
                click.echo(f"✗ Comparative experiment failed", err=True)
                sys.exit(1)
                
        except Exception as e:
            ctx.error_handler.handle_error(e, {
                "component": "CLI",
                "command": "run_comparative",
                "tools": tools
            })
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)


@cli.command()
@click.option('--config-file', '-c', required=True,
              type=click.Path(exists=True),
              help='Configuration file for batch experiment')
@click.option('--dry-run', is_flag=True,
              help='Validate configuration without executing')
@pass_context
def run_batch(ctx: CLIContext, config_file: str, dry_run: bool):
    """
    Execute a batch experiment from configuration file.
    
    Runs experiments defined in a comprehensive configuration file,
    supporting complex experiment scenarios with multiple applications,
    tools, and configurations.
    
    ### Examples:
        rv-experiment run-batch --config-file experiments/batch_config.json
        rv-experiment run-batch --config-file large_experiment.json --dry-run
    """
    with ctx.logger.with_context(
        command="run_batch",
        config_file=config_file,
        dry_run=dry_run
    ):
        ctx.logger.info(LOG_START.format(operation="batch experiment"))
        
        try:
            # Load configuration from file
            config = ctx.load_configuration(config_file)
            
            if dry_run:
                click.echo("Configuration validation:")
                config.validate()
                click.echo("✓ Configuration is valid")
                ctx.logger.info("Dry run completed successfully")
                return
                
            # Create and execute experiment
            orchestrator = ExperimentOrchestrator(config, ctx.event_bus, ctx.logger)
            success = orchestrator.execute_batch_experiment()
            
            if success:
                click.echo(f"✓ Batch experiment completed successfully")
                ctx.logger.info(LOG_COMPLETE.format(operation="batch experiment"))
            else:
                click.echo(f"✗ Batch experiment failed", err=True)
                sys.exit(1)
                
        except Exception as e:
            ctx.error_handler.handle_error(e, {
                "component": "CLI",
                "command": "run_batch",
                "config_file": config_file
            })
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)


@cli.command()
@click.option('--tools', default='monkey,ape',
              help='Comma-separated list of tools with optional variants for local testing\n'
                   'Format: tool1[:variants][@params],tool2[:variants][@params]\n'
                   'Default: monkey,ape')
@click.option('--timeout', default=120,
              help='Timeout in seconds for local testing (default: 120)')
@click.option('--repetitions', default=1,
              help='Number of repetitions for local testing (default: 1)')
@pass_context
def run_local(ctx: CLIContext, tools: str, timeout: int, repetitions: int):
    """
    Execute a local development experiment with predefined settings.
    
    Designed for development and testing purposes, this command runs
    a quick experiment with sensible defaults for local development.
    Perfect for validating system functionality and testing changes.
    
    ### Purpose:
    - Development and testing workflow support
    - Quick validation of system functionality
    - Local environment testing with minimal configuration
    - Rapid iteration during development cycles
    
    ### Examples:
        rv-experiment run-local
        rv-experiment run-local --tools monkey:fixed_seed --timeout 60
        rv-experiment run-local --tools monkey,droidbot:dfs_greedy@count=500 --repetitions 2
    """
    with ctx.logger.with_context(
        command="run_local",
        tools=tools,
        timeout=timeout,
        repetitions=repetitions
    ):
        ctx.logger.info(LOG_START.format(operation="local development experiment"))
        
        try:
            tool_specs = [t.strip() for t in tools.split(',')]
            
            # Parse tool specifications
            tool_configs = []
            tool_names = []
            for tool_spec in tool_specs:
                tool_config = ToolConfiguration.from_spec_string(tool_spec)
                tool_configs.append(tool_config)
                tool_names.append(tool_config.name)
            
            # Create local experiment configuration
            config = ExperimentConfiguration()
            config.tools = tool_names
            config.tool_configs = tool_configs
            config.timeouts = [timeout]
            config.repetitions = repetitions
            config.no_window = True  # Always headless for local testing
            config.generate_monitors = True
            config.instrument = True
            config.static_analysis = True
            config.output_dir = "./local_experiment_results"
            
            # Validate configuration
            config.validate()
            
            click.echo(f"🧪 Starting local experiment with tools: {', '.join([f'{tc.name}:{':'.join(tc.variants)}' if tc.variants else tc.name for tc in tool_configs])}")
            click.echo(f"⏱️  Timeout: {timeout}s, Repetitions: {repetitions}")
            click.echo(f"📁 Results will be saved to: {config.output_dir}")
            
            # Create and execute experiment
            orchestrator = ExperimentOrchestrator(config, ctx.event_bus, ctx.logger)
            success = orchestrator.execute_single_tool_experiment()
            
            if success:
                click.echo(f"✓ Local experiment completed successfully")
                click.echo(f"📊 Check results in: {config.output_dir}")
                ctx.logger.info(LOG_COMPLETE.format(operation="local development experiment"))
            else:
                click.echo(f"✗ Local experiment failed", err=True)
                sys.exit(1)
                
        except Exception as e:
            ctx.error_handler.handle_error(e, {
                "component": "CLI",
                "command": "run_local",
                "tools": tools
            })
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)


@cli.command()
@click.option('--format', 'output_format', 
              type=click.Choice(['json', 'yaml', 'toml']), 
              default='json',
              help='Output format for configuration template')
@click.option('--output', '-o', 
              type=click.Path(), 
              help='Output file (default: stdout)')
@pass_context
def generate_config(ctx: CLIContext, output_format: str, output: Optional[str]):
    """
    Generate a sample experiment configuration file.
    
    Creates a comprehensive configuration template with examples and
    documentation for all available experiment options.
    
    ### Examples:
        rv-experiment generate-config --format json --output experiment.json
        rv-experiment generate-config --format yaml > config.yaml
    """
    ctx.logger.info(f"Generating {output_format} configuration template")
    
    try:
        # Create sample configuration
        config = ExperimentConfiguration.create_sample_configuration()
        
        # Convert to specified format
        if output_format == 'json':
            config_content = config.to_json(indent=2)
        elif output_format == 'yaml':
            config_content = config.to_yaml()
        elif output_format == 'toml':
            config_content = config.to_toml()
        else:
            raise ValueError(f"Unsupported format: {output_format}")
            
        # Output configuration
        if output:
            with open(output, 'w') as f:
                f.write(config_content)
            click.echo(f"✓ Configuration template saved to: {output}")
        else:
            click.echo(config_content)
            
    except Exception as e:
        ctx.error_handler.handle_error(e, {
            "component": "CLI",
            "command": "generate_config",
            "format": output_format
        })
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@pass_context
def list_tools(ctx: CLIContext):
    """
    List all available testing tools and their capabilities.
    
    Displays comprehensive information about available testing tools,
    including their supported features, variants, and configuration options.
    """
    ctx.logger.info("Listing available testing tools")
    
    try:
        # Import here to avoid circular dependencies
        from rv_tools.registry.registry import ToolRegistry
        
        registry = ToolRegistry.get_instance()
        tools = registry.get_all_tools()
        
        if not tools:
            click.echo("No tools available. Make sure tool modules are properly installed.")
            return
            
        click.echo("\n🔧 Available Testing Tools:")
        click.echo("=" * 50)
        
        for tool in tools:
            click.echo(f"\n📦 {tool.name}")
            click.echo(f"   Description: {getattr(tool, 'description', 'No description available')}")
            
            # Show variants if available
            variants = registry.get_tool_variants(tool.name)
            if variants and len(variants) > 1:  # More than just 'default'
                click.echo(f"   Variants: {', '.join(v for v in variants if v != 'default')}")
                
            # Show capabilities if available
            if hasattr(tool, 'capabilities'):
                capabilities = ', '.join(tool.capabilities)
                click.echo(f"   Capabilities: {capabilities}")
                
        click.echo(f"\n✅ Total: {len(tools)} tools available")
        
    except Exception as e:
        ctx.error_handler.handle_error(e, {
            "component": "CLI",
            "command": "list_tools"
        })
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def main():
    """
    Main entry point for the RV-Experiment CLI.
    
    ### Architectural Decisions:
    - Provides clean separation between CLI interface and experiment logic
    - Implements comprehensive error handling for command-line operations
    - Supports both interactive and programmatic usage patterns
    - Maintains consistent logging and error reporting across all operations
    
    ### Integration Points:
    - Integrates with existing ErrorHandler and LoggingManager components
    - Coordinates with event bus for experiment monitoring and reporting
    - Interfaces with tool registry for dynamic tool discovery and loading
    - Coordinates configuration distribution across dependent modules
    """
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\n🛑 Operation cancelled by user", err=True)
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        # Final safety net for unexpected errors
        error_handler = ErrorHandler.get_instance()
        error_handler.handle_error(e, {
            "component": "CLI",
            "operation": "main_entry_point"
        })
        click.echo(f"Fatal error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()