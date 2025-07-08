#!/usr/bin/env python3
"""
RV-Experiment CLI - Simple Android Testing Orchestration

### Architectural Overview:
This module implements a simplified CLI interface for Android testing experiments
with monitored operations. It follows the direct approach inspired by the original
main.py, eliminating complex DI patterns in favor of straightforward execution flow.

### Key Architectural Decisions:
- **Simple Command Structure**: Four core commands (run, config, list-tools, validate)
- **Direct Execution**: Uses execute_with_config() directly without bridge patterns
- **Tool Specification DSL**: Modern tool:variant@parameter format support
- **Configuration-First**: Both CLI arguments and file-based configuration support
- **Monitored Operations**: Support for JCA crypto and generic specification sets

### Role in the System:
- Primary CLI entry point for experiment execution
- Configuration management for both interactive and file-based workflows
- Tool registry integration with specification parsing
- Direct interface to existing experiment orchestration infrastructure

### Design Patterns:
- **Command Pattern**: Clean CLI command structure with focused responsibilities
- **Factory Pattern**: Tool creation through registry with specification parsing
- **Template Method**: Configuration creation from various sources
- **Strategy Pattern**: Different execution modes based on configuration type

### Command Structure:
- **run**: Execute experiments with tool specification parsing or config files
- **config**: Generate configuration templates for different scenarios
- **list-tools**: Display available tools and their capabilities
- **validate**: Validate configuration files and tool specifications
"""

import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import click

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT, LOG_START, LOG_COMPLETE
from rv_android_core.util.error.exceptions import ConfigurationError
from rv_tools.registry.registry import ToolRegistry
from rv_experiment.config import ExperimentConfig
from rv_platform.config.platform_config import ToolConfig
from rv_experiment.experiment.experiment_controller import execute_with_config
from rv_experiment.constants import (
    DEFAULT_APKS_DIR, DEFAULT_TIMEOUT, DEFAULT_REPETITIONS,
    DEFAULT_SPEC_SET, RESULTS_DIR
)


class CLIContext:
    """
    CLI context for experiment execution with clean architecture principles.
    
    ### Architectural Overview:
    This class manages CLI state and provides centralized access to system
    components following clean architecture patterns. It serves as the
    coordination point for logging, error handling, and tool registry access.
    
    ### Key Features:
    - **Centralized Logging**: Consistent logging configuration across commands
    - **Error Handling**: Comprehensive error management using rv-android-core patterns
    - **Tool Registry**: Direct access to tool registry for specification parsing
    - **Configuration Management**: Template generation and validation coordination
    
    ### Role in the System:
    - Provides shared context for all CLI commands
    - Manages system component initialization and lifecycle
    - Coordinates configuration creation and validation
    - Facilitates tool specification parsing and registry operations
    """
    
    def __init__(self):
        """Initialize CLI context with system component integration."""
        # Initialize core components from rv-android-core
        self.logging_manager = LoggingManager.get_instance()
        self.error_handler = ErrorHandler.get_instance()
        
        # Configure CLI logger with proper context
        self.logger = self.logging_manager.get_logger(
            "rv_experiment.cli",
            {CONTEXT_COMPONENT: "CLIContext"}
        )
        
        # CLI state management
        self.debug = False
        
        # Initialize tool registry for specification parsing
        self.tool_registry = ToolRegistry.get_instance()
        self._register_available_tools()
        
        self.logger.info("CLI context initialized successfully")
    
    @ErrorHandler.handle_errors(
        component="CLIContext",
        phase="configure_logging"
    )
    def configure_logging(self, debug: bool = False):
        """
        Configure logging for CLI operations with comprehensive setup.
        
        ### Logging Strategy:
        - Console output with appropriate log levels based on debug flag
        - Silences noisy third-party libraries for clean output
        - Maintains consistent logging format across all operations
        - Prepares for experiment-specific file logging during execution
        
        Args:
            debug: Enable debug level logging for development and troubleshooting
        """
        import logging

        logging.basicConfig(
            level=logging.DEBUG if debug else logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            stream=sys.stdout
        )
        
        # Configure logging manager for CLI usage
        self.logging_manager.configure_output(
            console=True,
            file=False,  # File logging enabled during experiment execution
            console_level=logging.DEBUG if debug else logging.INFO,
            file_level=logging.DEBUG,
            console_format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Silence noisy third-party loggers for clean CLI output
        for noisy_logger in ["androguard", "matplotlib", "PIL", "requests", "urllib3"]:
            logging.getLogger(noisy_logger).setLevel(logging.ERROR)
        
        self.debug = debug
        self.logger.info("CLI logging configured successfully")
    
    def _register_available_tools(self):
        """
        Register available tools for experiment execution.
        
        ### Tool Registration Strategy:
        - Auto-registers builtin tools available through rv-tools
        - Manual registration for specialized tools when needed
        - Provides clear documentation for missing tool dependencies
        - Validates tool availability during registration
        
        ### Current Tool Support:
        - Builtin tools: monkey, droidbot, ape, fastbot (auto-registered via rv-tools)
        - Future tools: RVAndroid (requires LLM configuration integration)
        
        Note: RVAndroid tool registration is commented out pending LLM configuration
        modernization as it requires specific LLM backend setup and configuration.
        """
        try:
            # Builtin tools are auto-registered through rv-tools import
            # This includes: monkey, droidbot, ape, fastbot, etc.
            
            # Note: RVAndroid tool registration available when LLM configuration is needed
            
            # Log successful tool registration
            registered_tools = self.tool_registry.get_all_tools()
            tool_names = [tool.name for tool in registered_tools]
            self.logger.info(f"Registered {len(tool_names)} tools: {', '.join(tool_names)}")
            
        except Exception as e:
            self.logger.warning(f"Tool registration encountered issues: {e}")
    
    def parse_tool_specification(self, tool_spec: str) -> Dict[str, Any]:
        """
        Parse tool specification string into structured configuration.
        
        ### Tool Specification DSL:
        Format: `tool_name[:variant1][:variant2][@param1=value1,param2=value2]`
        
        ### Examples:
        - `monkey` -> {name: "monkey", variants: [], parameters: {}}
        - `droidbot:dfs_greedy` -> {name: "droidbot", variants: ["dfs_greedy"], parameters: {}}
        - `rvandroid:llama:batch@temperature=0.3,max_tokens=2048` ->
          {name: "rvandroid", variants: ["llama", "batch"], parameters: {"temperature": "0.3", "max_tokens": "2048"}}
        
        ### Parsing Strategy:
        1. Split tool name/variants from parameters using '@' delimiter
        2. Parse parameter section as key=value pairs separated by commas
        3. Split tool section using ':' to extract name and variants
        4. Validate tool name against registry for early error detection
        
        Args:
            tool_spec: Tool specification string to parse
            
        Returns:
            Structured tool configuration dictionary with name, variants, and parameters
            
        Raises:
            ValueError: If tool specification format is invalid or tool is not available
        """
        try:
            # Split tool name/variants from parameters
            if '@' in tool_spec:
                tool_part, params_part = tool_spec.split('@', 1)
                
                # Parse parameters as key=value pairs
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
            
            # Validate tool availability in registry
            available_tools = [tool.name for tool in self.tool_registry.get_all_tools()]
            if tool_name not in available_tools:
                self.logger.warning(f"Tool '{tool_name}' not found in registry. Available tools: {', '.join(available_tools)}")
            
            return {
                "name": tool_name,
                "variants": variants,
                "parameters": parameters
            }
            
        except Exception as e:
            raise ValueError(f"Invalid tool specification '{tool_spec}': {e}")


# CLI Context setup with clean pattern
pass_context = click.make_pass_decorator(CLIContext, ensure=True)


@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging for development')
@pass_context
def cli(ctx: CLIContext, debug: bool):
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
    - With variants: `droidbot:dfs_greedy`, `rvandroid:llama:batch`
    - With parameters: `rvandroid:llama@temperature=0.3,max_tokens=2048`
    - Multiple tools: `monkey,droidbot:dfs_greedy,rvandroid:llama:batch@temperature=0.2`
    
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
    ctx.configure_logging(debug)


@cli.command()
@click.option('--tools', '-t', default='monkey',
              help='Comma-separated tools with variants and parameters\n'
                   'Format: tool1[:variants][@params],tool2[:variants][@params]\n'
                   'Examples: monkey,droidbot:dfs_greedy,rvandroid:llama:batch@temperature=0.3')
@click.option('--config', '-c', type=click.Path(exists=True),
              help='Configuration file path (JSON format)')
@click.option('--timeout', default=DEFAULT_TIMEOUT,
              help=f'Execution timeout in seconds (default: {DEFAULT_TIMEOUT})')
@click.option('--repetitions', '-r', default=DEFAULT_REPETITIONS,
              help=f'Number of repetitions (default: {DEFAULT_REPETITIONS})')
@click.option('--apks-dir', '-a', default=f'./{DEFAULT_APKS_DIR}/',
              type=click.Path(),
              help=f'Directory containing APK files (default: ./{DEFAULT_APKS_DIR}/)')
@click.option('--specification-set', default=DEFAULT_SPEC_SET,
              type=click.Choice(['jca', 'generic', 'custom']),
              help=f'Monitored operations specification set (default: {DEFAULT_SPEC_SET})')
@click.option('--custom-specs-dir', type=click.Path(exists=True),
              help='Custom specification directory path (required when --specification-set=custom)')
@click.option('--custom-aspects-dir', type=click.Path(exists=True),
              help='Custom AspectJ aspects directory path (optional, defaults to standard RVSEC aspects)')
@click.option('--generate-monitors/--skip-monitors', default=True,
              help='Generate runtime verification monitors (default: enabled)')
@click.option('--instrument-apks/--skip-instrument', default=True,
              help='Instrument APKs with monitors (default: enabled)')
@click.option('--static-analysis/--skip-static', default=True,
              help='Run static analysis on APKs (default: enabled)')
@click.option('--output-dir', type=click.Path(),
              help='Output directory for experiment results (default: auto-generated)')
@click.option('--disable-performance-monitor', is_flag=True,
              help='Disable performance monitoring to reduce overhead')
@click.option('--performance-monitor-level',
              type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'DISABLED']),
              default='DEBUG',
              help='Performance monitor logging level (default: DEBUG)')
@click.option('--performance-monitor-max-samples', type=int, default=1000,
              help='Maximum number of metrics to store in memory (default: 1000)')
@click.option('--performance-export-enabled', is_flag=True,
              help='Enable performance metrics export to file')
@click.option('--performance-export-format',
              type=click.Choice(['JSON', 'CSV']),
              default='JSON',
              help='Format for performance metrics export (default: JSON)')
@pass_context
@ErrorHandler.handle_errors(
    component="CLIContext",
    phase="run_experiment"
)
def run(ctx: CLIContext, tools: str, config: Optional[str], timeout: int, repetitions: int,
        apks_dir: str, specification_set: str, custom_specs_dir: Optional[str],
        custom_aspects_dir: Optional[str], generate_monitors: bool, instrument_apks: bool, 
        static_analysis: bool, output_dir: Optional[str], disable_performance_monitor: bool,
        performance_monitor_level: str, performance_monitor_max_samples: int,
        performance_export_enabled: bool, performance_export_format: str):
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
    
    # LLM-driven testing with variants (when available)
    rv-experiment run --tools rvandroid:llama:batch@temperature=0.3
    
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
    with ctx.logger.with_context(
        command="run",
        tools=tools,
        config=config,
        timeout=timeout,
        repetitions=repetitions,
        specification_set=specification_set
    ):
        ctx.logger.info(LOG_START.format(phase="experiment execution"))
        
        # Validate custom specifications directory if custom specification set is selected
        if specification_set == "custom" and not custom_specs_dir:
            raise click.ClickException(
                "Custom specification directory (--custom-specs-dir) is required "
                "when using --specification-set=custom"
            )
        
        try:
            if config:
                # Config file mode - load experiment configuration from file
                ctx.logger.info(f"Loading experiment configuration from: {config}")
                experiment_config = ExperimentConfig.from_file(config)
                ctx.logger.info(f"Loaded configuration for experiment: {experiment_config.name}")
                
            else:
                # CLI mode - create experiment configuration from command line arguments
                experiment_config = _create_experiment_config_from_cli(
                    ctx, tools, timeout, repetitions, apks_dir,
                    specification_set, custom_specs_dir, custom_aspects_dir, 
                    generate_monitors, instrument_apks, static_analysis, output_dir,
                    disable_performance_monitor, performance_monitor_level,
                    performance_monitor_max_samples, performance_export_enabled,
                    performance_export_format
                )
            
            # Validate configuration before execution
            experiment_config.validate()
            
            # Display experiment information
            tool_names = [tc.name for tc in experiment_config.tool_configs]
            click.echo(f"🧪 Starting experiment: {experiment_config.name}")
            click.echo(f"🔧 Tools: {', '.join(tool_names)}")
            click.echo(f"📊 Monitored operations: {experiment_config.specification_set}")
            click.echo(f"⏱️  Timeout: {timeout}s, Repetitions: {repetitions}")
            click.echo(f"📁 Output directory: {experiment_config.output_dir}")
            click.echo(f"📱 APK directory: {apks_dir}")
            
            # Execute experiment using existing infrastructure
            ctx.logger.info("Executing experiment via experiment controller")
            execute_with_config(experiment_config)
            
            click.echo(f"✅ Experiment completed successfully!")
            click.echo(f"📊 Results available in: {experiment_config.output_dir}")
            ctx.logger.info(LOG_COMPLETE.format(phase="experiment execution"))
            
        except Exception as e:
            ctx.logger.error(f"Experiment execution failed: {e}")
            click.echo(f"❌ Experiment failed: {e}", err=True)
            sys.exit(1)


@cli.command()
@click.option('--template-type', 
              type=click.Choice(['basic', 'advanced', 'research']),
              default='basic',
              help='Configuration template type (default: basic)')
@click.option('--output', '-o', type=click.Path(),
              help='Output file path for configuration template')
@click.option('--format', 'output_format',
              type=click.Choice(['json']),
              default='json',
              help='Configuration template format (default: json)')
@pass_context
@ErrorHandler.handle_errors(
    component="CLIContext",
    phase="generate_config"
)
def config(ctx: CLIContext, template_type: str, output: Optional[str], output_format: str):
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
    ctx.logger.info(f"Generating {template_type} {output_format} configuration template")
    
    try:
        # Create template configuration based on type
        template_config = _create_template_configuration(template_type)
        
        # Convert to specified format
        if output_format == 'json':
            config_content = json.dumps(template_config.to_dict(), indent=2)
        else:
            raise ValueError(f"Unsupported format: {output_format}")
        
        # Output configuration
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                f.write(config_content)
            
            click.echo(f"✅ {template_type.title()} configuration template saved to: {output}")
            ctx.logger.info(f"Configuration template saved: {output}")
        else:
            click.echo(config_content)
            
    except Exception as e:
        ctx.logger.error(f"Configuration generation failed: {e}")
        click.echo(f"❌ Configuration generation failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--detailed', is_flag=True,
              help='Show detailed tool information including variants and capabilities')
@click.option('--filter-by', 
              type=click.Choice(['all', 'basic', 'llm', 'research']),
              default='all',
              help='Filter tools by category (default: all)')
@pass_context
@ErrorHandler.handle_errors(
    component="CLIContext",
    phase="list_tools"
)
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
                variants = ctx.tool_registry.get_tool_variants(tool.name)
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
            
        # Show note about RVAndroid availability
        rvandroid_available = any(tool.name == 'rvandroid' for tool in tools)
        if not rvandroid_available:
            click.echo("\n📝 Note: RVAndroid tool will be available after LLM configuration modernization")
        
    except Exception as e:
        ctx.logger.error(f"Tool listing failed: {e}")
        click.echo(f"❌ Tool listing failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('config_file', type=click.Path(exists=True))
@pass_context
@ErrorHandler.handle_errors(
    component="CLIContext",
    phase="validate_config"
)
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
        
        with open(config_path, 'r') as f:
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
                validation_errors.append(f"Tool '{tool_config.name}' not available in registry")
        
        # Report validation results
        if validation_errors:
            click.echo("❌ Configuration validation failed:")
            for error in validation_errors:
                click.echo(f"   • {error}")
            sys.exit(1)
        else:
            click.echo("✅ Configuration file is valid")
            click.echo(f"   • Experiment: {experiment_config.name}")
            click.echo(f"   • Tools: {', '.join([tc.name for tc in experiment_config.tool_configs])}")
            click.echo(f"   • Monitored operations: {experiment_config.specification_set}")
            
        ctx.logger.info(f"Configuration validation completed successfully")
        
    except json.JSONDecodeError as e:
        click.echo(f"❌ Invalid JSON format: {e}")
        sys.exit(1)
    except Exception as e:
        ctx.logger.error(f"Configuration validation failed: {e}")
        click.echo(f"❌ Configuration validation failed: {e}")
        sys.exit(1)


def _create_experiment_config_from_cli(ctx: CLIContext, tools: str, timeout: int, 
                                     repetitions: int, apks_dir: str,
                                     specification_set: str, custom_specs_dir: Optional[str],
                                     custom_aspects_dir: Optional[str], generate_monitors: bool, 
                                     instrument_apks: bool, static_analysis: bool, 
                                     output_dir: Optional[str], disable_performance_monitor: bool,
                                     performance_monitor_level: str, performance_monitor_max_samples: int,
                                     performance_export_enabled: bool, performance_export_format: str) -> ExperimentConfig:
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
        timeout: Execution timeout in seconds
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
        tool_specs = [spec.strip() for spec in tools.split(',')]
        tool_configs = []
        
        for tool_spec in tool_specs:
            parsed_tool = ctx.parse_tool_specification(tool_spec)
            tool_config = ToolConfig(
                name=parsed_tool["name"],
                variants=parsed_tool["variants"],
                parameters=parsed_tool["parameters"]
            )
            tool_configs.append(tool_config)
        
        # APK directory is used directly - no patterns needed
        
        # Generate experiment identifier
        experiment_id = f"cli_experiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # Determine output directory
        if not output_dir:
            output_dir = f"./{RESULTS_DIR}/{experiment_id}"
        
        # Create ExperimentConfig instance
        experiment_config = ExperimentConfig(
            name=experiment_id,
            description="Experiment created via CLI interface",
            output_dir=output_dir,
            experiment_id=experiment_id,
            tool_configs=tool_configs,
            repetitions=repetitions,
            timeouts=[timeout],
            no_window=True,  # Default for CLI usage
            generate_monitors=generate_monitors,
            instrument_apks=instrument_apks,
            run_static_analysis=static_analysis,
            specification_set=specification_set,
            custom_specs_dir=custom_specs_dir,
            custom_aspects_dir=custom_aspects_dir,
            apks_dir=apks_dir,
            metadata={
                "created_via": "cli",
                "tool_specifications": tools,
                "cli_version": "1.0"
            }
        )
        
        ctx.logger.info(f"Created experiment configuration: {experiment_id}")
        return experiment_config
        
    except Exception as e:
        raise ConfigurationError(f"Failed to create experiment configuration from CLI arguments: {e}")


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
    if template_type == 'basic':
        return ExperimentConfig(
            name="basic_experiment_template",
            description="Basic experiment template with standard tools and JCA monitored operations",
            tool_configs=[
                ToolConfig(name="monkey"),
                ToolConfig(name="droidbot", variants=["dfs_greedy"])
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
                "monitored_operations_focus": "JCA cryptography API monitoring"
            }
        )
    
    elif template_type == 'advanced':
        return ExperimentConfig(
            name="advanced_experiment_template",
            description="Advanced experiment template with multiple tools and comprehensive configuration",
            tool_configs=[
                ToolConfig(name="monkey", parameters={"seed": 42, "throttle": 100}),
                ToolConfig(name="droidbot", variants=["dfs_greedy"], parameters={"count": 2000}),
                ToolConfig(name="ape", parameters={"running_minutes": 10})
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
                "resource_requirements": "high"
            }
        )
    
    elif template_type == 'research':
        return ExperimentConfig(
            name="research_experiment_template",
            description="Research-focused template for academic studies with statistical rigor",
            tool_configs=[
                ToolConfig(name="monkey", variants=["fixed_seed"], parameters={"seed": 42}),
                ToolConfig(name="droidbot", variants=["dfs_greedy"], parameters={"count": 3000}),
                ToolConfig(name="ape", parameters={"running_minutes": 15})
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
                "monitored_operations_focus": "Comprehensive JCA cryptography API analysis"
            }
        )
    
    else:
        raise ValueError(f"Unknown template type: {template_type}")


@ErrorHandler.handle_errors(
    component="CLIMain",
    phase="main_entry_point"
)
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


if __name__ == '__main__':
    main()