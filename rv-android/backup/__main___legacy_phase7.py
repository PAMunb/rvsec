#!/usr/bin/env python3
"""
RV-Experiment CLI - Simplified Command Line Interface for Android Testing Experiments

### Architectural Overview:
This module implements the modernized Phase 8 CLI architecture with simplified command structure,
intelligent defaults, and unified experiment orchestration. The CLI provides a streamlined
interface that eliminates complex multi-command patterns in favor of a simple 3-command structure.

### Phase 8 Modernization Features:
- **Simplified Commands**: Reduced from 4 complex commands to 3 intuitive operations
- **Tool Variant Support**: Intelligent parsing of tool specifications with variants and parameters
- **Experiment Directory Standard**: Unified ./out/ directory structure for all operations
- **Intelligent Defaults**: Smart fallbacks that minimize required configuration
- **Continuation Support**: Resume experiments from existing experiment directories

### Key Architectural Decisions:
- **Command Consolidation**: Single `run` command handles all execution scenarios
- **Tool Specification DSL**: Format: `tool[:variant1][:variant2][@param1=value1,param2=value2]`
- **Modern Error Handling**: Integration with rv-android-core ErrorHandler using decorators
- **Centralized Logging**: Comprehensive logging via rv-android-core LoggingManager
- **Directory Standardization**: All operations relative to experiment_dir (default ./out/)

### Breaking Changes Implementation:
- Removed: run-single, run-comparative, run-batch, run-local commands
- Added: Unified run command with intelligent tool parsing
- Replaced: Complex configuration coordination with simple parameter passing
- Modernized: Factory-based component creation instead of ComponentConfigurator

### Role in the System:
- Primary CLI entry point for all experiment operations
- Orchestrates configuration distribution using modern factories
- Provides experiment continuation and state management
- Implements comprehensive error handling and user feedback
- Coordinates with all specialized modules through clean interfaces
"""

import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import click

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT, LOG_START, LOG_COMPLETE
from rv_experiment.config import SimpleExperimentConfig
from rv_experiment.orchestrator import ExperimentOrchestrator


class ModernCLIContext:
    """
    Modern CLI context implementing Phase 8 simplified architecture.
    
    ### Architectural Decisions:
    - **Simplified State Management**: Minimal state, maximum intelligence
    - **Factory Integration**: Direct integration with modern factory pattern
    - **Error Handling**: Comprehensive error handling using rv-android-core decorators
    - **Logging Coordination**: Centralized logging configuration and management
    - **Resource Lifecycle**: Clean resource management across CLI operations
    
    ### Role in the System:
    - Provides shared context for all CLI commands
    - Manages logging configuration and error handling setup
    - Coordinates with simplified experiment configuration
    - Maintains experiment directory and state management
    """
    
    def __init__(self):
        """Initialize modern CLI context with minimal complexity."""
        # Core components from rv-android-core
        self.logging_manager = LoggingManager.get_instance()
        
        # Set up logger for CLI operations
        self.logger = self.logging_manager.get_logger(
            "rv_experiment.cli",
            {CONTEXT_COMPONENT: "ModernCLI"}
        )
        
        # CLI state - minimal and focused
        self.debug = False
        self.experiment_dir = "./out/"
        
    @ErrorHandler.handle_errors(
        component="ModernCLI",
        phase="configure_logging",
    )
    def configure_logging(self, debug: bool = False):
        """
        Configure logging for modern CLI operations.
        
        ### Implementation Details:
        - Configures console output with appropriate log levels
        - Silences noisy third-party libraries
        - Sets up experiment-specific file logging
        - Maintains consistent logging format across operations
        
        Args:
            debug: Enable debug level logging for development
        """
        import logging
        
        # Configure logging manager for CLI usage
        self.logging_manager.configure_output(
            console=True,
            file=False,  # File logging configured per-experiment
            console_level=logging.DEBUG if debug else logging.INFO,
            console_format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Silence noisy third-party loggers
        for noisy_logger in ["androguard", "matplotlib", "PIL", "requests", "urllib3"]:
            logging.getLogger(noisy_logger).setLevel(logging.ERROR)
        
        self.debug = debug
        self.logger.info("Modern CLI logging configured")
        
    def parse_tool_specification(self, tool_spec: str) -> Dict[str, Any]:
        """
        Parse modern tool specification string into structured configuration.
        
        ### Tool Specification DSL:
        Format: `tool_name[:variant1][:variant2][@param1=value1,param2=value2]`
        
        Examples:
        - `monkey` -> {name: "monkey", variants: [], parameters: {}}
        - `droidbot:dfs_greedy` -> {name: "droidbot", variants: ["dfs_greedy"], parameters: {}}
        - `rvandroid:llama:batch@temperature=0.3,max_tokens=2048` -> 
          {name: "rvandroid", variants: ["llama", "batch"], parameters: {"temperature": "0.3", "max_tokens": "2048"}}
        
        Args:
            tool_spec: Tool specification string to parse
            
        Returns:
            Structured tool configuration dictionary
            
        Raises:
            ValueError: If tool specification format is invalid
        """
        try:
            # Split tool name/variants from parameters
            if '@' in tool_spec:
                tool_part, params_part = tool_spec.split('@', 1)
                # Parse parameters
                parameters = {}
                for param in params_part.split(','):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        parameters[key.strip()] = value.strip()
                    else:
                        # Boolean flag parameter
                        parameters[param.strip()] = True
            else:
                tool_part = tool_spec
                parameters = {}
            
            # Split tool name and variants
            parts = tool_part.split(':')
            tool_name = parts[0].strip()
            variants = [v.strip() for v in parts[1:] if v.strip()]
            
            if not tool_name:
                raise ValueError("Tool name cannot be empty")
                
            return {
                "name": tool_name,
                "variants": variants,
                "parameters": parameters
            }
            
        except Exception as e:
            raise ValueError(f"Invalid tool specification '{tool_spec}': {e}")


# CLI Context setup with modern pattern
pass_context = click.make_pass_decorator(ModernCLIContext, ensure=True)


@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging for development')
@click.option('--experiment-dir', default='./out/', 
              type=click.Path(), 
              help='Base experiment directory (default: ./out/)')
@pass_context
def cli(ctx: ModernCLIContext, debug: bool, experiment_dir: str):
    """
    RV-Experiment - Modern Android Testing Experiment Orchestrator
    
    ### Phase 8 Modernized CLI Features:
    
    **Simplified Commands:**
    - `run`: Execute experiments with intelligent tool parsing and variant support
    - `generate-config`: Create configuration templates for complex scenarios
    - `list-tools`: Display available testing tools and their capabilities
    
    **Tool Specification DSL:**
    Format: `tool[:variant1][:variant2][@param1=value1,param2=value2]`
    
    Examples:
    - Basic: `monkey`, `droidbot`, `ape`
    - With variants: `droidbot:dfs_greedy`, `rvandroid:llama:batch`
    - With parameters: `rvandroid:llama@temperature=0.3,max_tokens=2048`
    - Multiple tools: `monkey,droidbot:dfs_greedy,rvandroid:llama:batch@temperature=0.2`
    
    **Experiment Directory Standard:**
    All operations use ./out/ as the standard experiment directory containing:
    - experiments/{experiment_id}/: Individual experiment results
    - instrumented/: Shared instrumented APKs
    - monitors/: Generated monitor files
    - static/: Static analysis results
    - cache/: Component and tool cache
    
    **Quick Start:**
    ```bash
    # Simple experiment with defaults
    rv-experiment run --tools monkey
    
    # Advanced experiment with variants
    rv-experiment run --tools monkey,rvandroid:llama:batch@temperature=0.3
    
    # Continue existing experiment
    rv-experiment run --experiment-dir ./out/experiments/exp_20250106_143022/
    ```
    """
    # Configure CLI context with modern patterns
    ctx.configure_logging(debug)
    ctx.experiment_dir = experiment_dir
    
    # Ensure experiment directory exists
    Path(experiment_dir).mkdir(parents=True, exist_ok=True)


@cli.command()
@click.option('--tools', '-t', default='monkey',
              help='Comma-separated tools with variants and parameters\n'
                   'Format: tool1[:variants][@params],tool2[:variants][@params]\n'
                   'Examples: monkey,droidbot:dfs_greedy,rvandroid:llama:batch@temperature=0.3')
@click.option('--timeout', default=300,
              help='Execution timeout in seconds (default: 300)')
@click.option('--repetitions', '-r', default=1,
              help='Number of repetitions (default: 1)')
@click.option('--experiment-dir', type=click.Path(),
              help='Specific experiment directory (overrides global setting)')
@click.option('--applications-dir', '-a', default='./apks_examples/',
              type=click.Path(),
              help='Directory containing APK files (default: ./apks_examples/)')
@click.option('--apk-patterns', default='*.apk',
              help='Comma-separated APK file patterns (default: *.apk)')
@click.option('--generate-monitors/--skip-monitors', default=True,
              help='Generate runtime verification monitors (default: enabled)')
@click.option('--instrument-apks/--skip-instrument', default=True,
              help='Instrument APKs with monitors (default: enabled)')
@click.option('--static-analysis/--skip-static', default=True,
              help='Run static analysis on APKs (default: enabled)')
@click.option('--continue-experiment', is_flag=True,
              help='Continue existing experiment from experiment directory')
@pass_context
@ErrorHandler.handle_errors(
    component="ModernCLI",
    phase="run_experiment",
)
def run(ctx: ModernCLIContext, tools: str, timeout: int, repetitions: int,
        experiment_dir: Optional[str], applications_dir: str, apk_patterns: str,
        generate_monitors: bool, instrument_apks: bool, static_analysis: bool,
        continue_experiment: bool):
    """
    Execute experiment with modern unified command structure.
    
    ### Modern Experiment Execution:
    This command replaces the previous run-single, run-comparative, run-batch, and run-local
    commands with a single intelligent interface that handles all experiment scenarios.
    
    **Tool Variant Examples:**
    ```bash
    # Basic tools
    rv-experiment run --tools monkey
    rv-experiment run --tools droidbot:dfs_greedy
    
    # LLM-driven testing with variants
    rv-experiment run --tools rvandroid:llama:batch@temperature=0.3
    rv-experiment run --tools rvandroid:llama:standard@max_tokens=2048,temperature=0.1
    
    # Multiple tools comparison
    rv-experiment run --tools monkey,droidbot:dfs_greedy,rvandroid:llama:batch@temperature=0.2
    
    # Continue existing experiment
    rv-experiment run --continue-experiment --experiment-dir ./out/experiments/exp_20250106_143022/
    ```
    
    **Monitored Operations:**
    The system supports experiments with different specification sets:
    - JCA cryptography API monitoring for security-related operations
    - Generic programming pattern monitoring (e.g., Iterator usage patterns)
    - Custom specification sets for domain-specific monitored operations
    """
    with ctx.logger.with_context(
        command="run",
        tools=tools,
        timeout=timeout,
        repetitions=repetitions,
        continue_experiment=continue_experiment
    ):
        ctx.logger.info(LOG_START.format(phase="modern experiment execution"))
        
        # Determine experiment directory
        target_experiment_dir = experiment_dir or ctx.experiment_dir
        
        if continue_experiment:
            # Continue existing experiment
            if not Path(target_experiment_dir).exists():
                raise ValueError(f"Experiment directory not found: {target_experiment_dir}")
                
            # Load existing configuration
            config_file = Path(target_experiment_dir) / "config.json"
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                config = SimpleExperimentConfig.from_dict(config_data)
                ctx.logger.info(f"Continuing experiment from: {target_experiment_dir}")
            else:
                raise ValueError(f"No configuration found in experiment directory: {target_experiment_dir}")
        else:
            # Create new experiment configuration
            experiment_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            
            # Parse tool specifications
            tool_specs = [spec.strip() for spec in tools.split(',')]
            parsed_tools = []
            for tool_spec in tool_specs:
                parsed_tool = ctx.parse_tool_specification(tool_spec)
                parsed_tools.append(parsed_tool)
            
            # Parse APK patterns
            apk_pattern_list = [pattern.strip() for pattern in apk_patterns.split(',')]
            
            # Create simplified experiment configuration
            config = SimpleExperimentConfig(
                experiment_dir=target_experiment_dir,
                experiment_id=experiment_id,
                tools=parsed_tools,
                timeout=timeout,
                repetitions=repetitions,
                apk_dir=applications_dir,
                apk_patterns=apk_pattern_list,
                generate_monitors=generate_monitors,
                instrument_apks=instrument_apks,
                run_static_analysis=static_analysis
            )
            
            # Validate configuration
            config.validate()
            
            # Create experiment directory structure
            experiment_path = Path(target_experiment_dir) / "experiments" / experiment_id
            experiment_path.mkdir(parents=True, exist_ok=True)
            
            # Save configuration
            config_file = experiment_path / "config.json"
            with open(config_file, 'w') as f:
                json.dump(config.to_dict(), f, indent=2)
            
            ctx.logger.info(f"Created new experiment: {experiment_id}")
        
        # Display experiment information
        tool_names = [tool['name'] for tool in config.tools]
        click.echo(f"🧪 Starting experiment: {config.experiment_id}")
        click.echo(f"🔧 Tools: {', '.join(tool_names)}")
        click.echo(f"⏱️  Timeout: {config.timeout}s, Repetitions: {config.repetitions}")
        click.echo(f"📁 Experiment directory: {target_experiment_dir}")
        click.echo(f"📱 APK directory: {config.apk_dir}")
        
        # Create and execute experiment using orchestrator
        orchestrator = ExperimentOrchestrator(config, ctx.event_bus, ctx.logger)
        
        # Determine experiment type and execute accordingly
        tool_count = len(tools) if tools else len(config.tool_configs)
        
        if tool_count == 1:
            success = orchestrator.execute_single_tool_experiment()
        elif tool_count > 1:
            success = orchestrator.execute_comparative_experiment()
        else:
            success = orchestrator.execute_batch_experiment()
        
        if success:
            click.echo(f"✅ Experiment completed successfully!")
            click.echo(f"📊 Results available in: {target_experiment_dir}/experiments/{config.experiment_id}/")
            ctx.logger.info(LOG_COMPLETE.format(phase="modern experiment execution"))
        else:
            click.echo(f"❌ Experiment failed - check logs for details", err=True)
            sys.exit(1)


@cli.command()
@click.option('--format', 'output_format',
              type=click.Choice(['json', 'yaml']),
              default='json',
              help='Configuration template format (default: json)')
@click.option('--output', '-o',
              type=click.Path(),
              help='Output file path (default: stdout)')
@click.option('--template-type', 
              type=click.Choice(['basic', 'advanced', 'llm_focused']),
              default='basic',
              help='Configuration template type (default: basic)')
@pass_context
@ErrorHandler.handle_errors(
    component="ModernCLI",
    phase="generate_config",
)
def generate_config(ctx: ModernCLIContext, output_format: str, output: Optional[str], 
                   template_type: str):
    """
    Generate configuration templates for complex experiment scenarios.
    
    ### Template Types:
    
    **Basic Template:**
    Simple configuration for standard experiments with common tools and settings.
    
    **Advanced Template:**
    Comprehensive configuration showcasing all available options, multiple tools,
    and complex execution scenarios.
    
    **LLM-Focused Template:**
    Specialized configuration for LLM-driven testing with RVAndroid, including
    prompt strategies, model configurations, and monitored operations setup.
    
    ### Examples:
    ```bash
    # Generate basic JSON template
    rv-experiment generate-config --template-type basic --output basic_config.json
    
    # Generate advanced YAML configuration
    rv-experiment generate-config --format yaml --template-type advanced --output advanced_config.yaml
    
    # Generate LLM-focused template for RVAndroid experiments
    rv-experiment generate-config --template-type llm_focused --output llm_experiment.json
    ```
    """
    ctx.logger.info(f"Generating {template_type} {output_format} configuration template")
    
    # Create template based on type
    if template_type == 'basic':
        template_config = SimpleExperimentConfig.create_basic_template()
    elif template_type == 'advanced':
        template_config = SimpleExperimentConfig.create_advanced_template()
    elif template_type == 'llm_focused':
        template_config = SimpleExperimentConfig.create_llm_template()
    else:
        raise ValueError(f"Unknown template type: {template_type}")
    
    # Convert to specified format
    if output_format == 'json':
        config_content = json.dumps(template_config.to_dict(), indent=2)
    elif output_format == 'yaml':
        import yaml
        config_content = yaml.dump(template_config.to_dict(), default_flow_style=False, indent=2)
    else:
        raise ValueError(f"Unsupported format: {output_format}")
    
    # Output configuration
    if output:
        with open(output, 'w') as f:
            f.write(config_content)
        click.echo(f"✅ {template_type.title()} configuration template saved to: {output}")
    else:
        click.echo(config_content)


@cli.command()
@click.option('--detailed', is_flag=True,
              help='Show detailed tool information including variants and capabilities')
@click.option('--filter-by', 
              type=click.Choice(['all', 'basic', 'llm', 'research']),
              default='all',
              help='Filter tools by category (default: all)')
@pass_context
@ErrorHandler.handle_errors(
    component="ModernCLI",
    phase="list_tools",
)
def list_tools(ctx: ModernCLIContext, detailed: bool, filter_by: str):
    """
    List available testing tools and their capabilities.
    
    ### Tool Categories:
    
    **Basic Tools:**
    Traditional Android testing tools (Monkey, DroidBot, APE, etc.)
    
    **LLM Tools:**
    AI-driven testing tools including RVAndroid with various LLM backends
    
    **Research Tools:**
    Experimental and research-oriented testing tools
    
    ### Examples:
    ```bash
    # List all tools with basic information
    rv-experiment list-tools
    
    # Show detailed information including variants
    rv-experiment list-tools --detailed
    
    # Filter LLM-based tools only
    rv-experiment list-tools --filter-by llm --detailed
    ```
    """
    ctx.logger.info(f"Listing available testing tools (filter: {filter_by})")
    
    try:
        # Import here to avoid circular dependencies
        from rv_tools.registry.registry import ToolRegistry
        
        registry = ToolRegistry.get_instance()
        tools = registry.get_all_tools()
        
        if not tools:
            click.echo("❌ No tools available. Ensure tool modules are properly installed.")
            return
        
        # Filter tools by category if specified
        if filter_by != 'all':
            filtered_tools = []
            for tool in tools:
                tool_category = getattr(tool, 'category', 'basic').lower()
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
            tool_description = getattr(tool, 'description', 'No description available')
            tool_category = getattr(tool, 'category', 'basic')
            
            click.echo(f"\n📦 {tool_name} ({tool_category})")
            click.echo(f"   Description: {tool_description}")
            
            if detailed:
                # Show variants if available
                variants = registry.get_tool_variants(tool.name)
                if variants and len(variants) > 1:
                    variant_list = [v for v in variants if v != 'default']
                    if variant_list:
                        click.echo(f"   Variants: {', '.join(variant_list)}")
                
                # Show capabilities if available
                if hasattr(tool, 'capabilities'):
                    capabilities = ', '.join(tool.capabilities)
                    click.echo(f"   Capabilities: {capabilities}")
                
                # Show supported parameters if available
                if hasattr(tool, 'supported_parameters'):
                    params = ', '.join(tool.supported_parameters.keys())
                    click.echo(f"   Parameters: {params}")
                
                # Show example usage
                example_usage = f"{tool_name}"
                if hasattr(tool, 'default_variant') and tool.default_variant != 'default':
                    example_usage += f":{tool.default_variant}"
                if hasattr(tool, 'example_parameters'):
                    param_str = ','.join([f"{k}={v}" for k, v in tool.example_parameters.items()])
                    example_usage += f"@{param_str}"
                
                click.echo(f"   Example: {example_usage}")
        
        click.echo(f"\n✅ Total: {len(tools)} tools available")
        
        if not detailed:
            click.echo("\n💡 Use --detailed flag for more information about tool variants and parameters")
        
    except ImportError:
        click.echo("❌ Tool registry not available. Ensure rv-tools module is properly installed.")
        sys.exit(1)


@ErrorHandler.handle_errors(
    component="ModernCLI",
    phase="main_entry_point",
)
def main():
    """
    Main entry point for the modernized RV-Experiment CLI.
    
    ### Phase 8 Architectural Integration:
    - Implements simplified command structure with intelligent defaults
    - Provides comprehensive error handling using rv-android-core decorators
    - Supports experiment continuation and state management
    - Coordinates with all specialized modules through modern factory pattern
    - Maintains backward compatibility for configuration files while modernizing interface
    
    ### Error Handling Strategy:
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


if __name__ == '__main__':
    main()