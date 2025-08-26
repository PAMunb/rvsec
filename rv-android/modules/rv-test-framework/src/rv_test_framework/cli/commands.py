"""
Command-line interface for test framework operations.

Provides simple, focused commands for framework operation using existing
rv-platform ToolConfig infrastructure for maximum compatibility.

### Design Principles:
- **ToolConfig Integration**: Uses rv-platform ToolConfig directly
- **rv-experiment Compatibility**: Uses same configuration patterns
- **Minimal Options**: Only essential runtime parameters exposed
- **Clear Output**: Structured progress reporting and result summaries
"""

import json
import os
import click
from datetime import datetime
from pathlib import Path

from rv_test_framework.core.framework import TestFramework
from rv_test_framework.core.models import TestFrameworkConfig
from rv_test_framework.config.predefined_configs import (
    get_basic_evaluation_configs,
    get_extended_evaluation_configs,
    get_all_evaluation_configs,
    TEST_EXPERIMENT_CONFIGS
)
from rv_test_framework.metrics.collector import MetricsCollector
from rv_test_framework.metrics.analyzer import MetricsAnalyzer
from rv_test_framework.analysis.plateau_analyzer import PlateauAnalyzer
from rv_test_framework.analysis.report_generator import ReportGenerator


def progress_callback(current: int, total: int, message: str) -> None:
    """Progress callback for framework execution."""
    percentage = (current / total) * 100 if total > 0 else 0
    click.echo(f"[{current}/{total}] ({percentage:.1f}%) {message}")


@click.group()
def cli():
    """RV-Android Test Framework command-line interface."""
    pass


@cli.command()
@click.option('--configs', default='test_experiment', help='Configuration file path or predefined config name')
@click.option('--apps', required=True, help='Directory containing APK files')
@click.option('--workers', default=5, help='Number of parallel workers (default: 5)')
@click.option('--output', default='./test_framework_results', help='Output directory')
@click.option('--repetitions', default=1, help='Number of repetitions per configuration')
@click.option('--timeouts', default='300', help='Comma-separated timeout values (e.g., 300,600)')
@click.option('--no-window', is_flag=True, help='Run emulators without window (headless)')
@click.option('--include-plateau', is_flag=True, help='Include plateau analysis')
def run(configs, apps, workers, output, repetitions, timeouts, no_window, include_plateau):
    """
    Execute complete test framework evaluation.
    
    Runs all configurations using ToolConfig infrastructure, collects metrics,
    and generates analysis reports with full compatibility with rv-experiment patterns.
    """
    click.echo("🚀 Starting RV-Android Test Framework")
    
    if configs.endswith('.json'):
        click.echo(f"Configuration file: {configs}")
    else:
        click.echo(f"Using predefined configurations: {configs}")
    
    click.echo(f"APKs directory: {apps}")
    click.echo(f"Workers: {workers}")
    click.echo(f"Output: {output}")
    click.echo("")
    
    try:
        # Parse timeouts
        timeout_values = [int(t.strip()) for t in timeouts.split(',')]
        
        # Create framework configuration
        config = TestFrameworkConfig(
            max_workers=workers,
            apks_dir=apps,
            output_dir=output,
            no_window=no_window,
            repetitions=repetitions,
            timeouts=timeout_values,
            include_plateau_analysis=include_plateau
        )
        
        # Initialize framework
        click.echo("📋 Initializing test framework...")
        framework = TestFramework(config)
        
        # Load configurations from file or use predefined
        click.echo("⚙️  Loading configurations...")
        if configs.endswith('.json'):
            # Load from file
            framework.load_configurations(configs)
        elif configs == 'basic':
            framework.load_configurations(get_basic_evaluation_configs())
        elif configs == 'extended':
            framework.load_configurations(get_extended_evaluation_configs())
        elif configs == 'all':
            framework.load_configurations(get_all_evaluation_configs())
        else:
            # Default: use test experiment configs that work
            framework.load_configurations(TEST_EXPERIMENT_CONFIGS)
        
        click.echo(f"Loaded {len(framework.config.configurations)} configurations")
        
        # Generate tasks
        click.echo("🔧 Generating tasks...")
        framework.generate_tasks()
        click.echo(f"Generated {len(framework.tasks)} tasks across {len(framework.model_groups)} model groups")
        
        # Execute framework
        click.echo("▶️  Starting execution...")
        
        def execution_progress(current, total, message):
            progress_callback(current, total, message)
        
        summary = framework.execute()
        
        # Display execution summary
        click.echo("")
        click.echo("📊 Execution Summary:")
        click.echo(f"  Total tasks: {summary.total_tasks}")
        click.echo(f"  Successful: {summary.successful_tasks}")
        click.echo(f"  Failed: {summary.failed_tasks}")
        click.echo(f"  Success rate: {summary.success_rate:.1f}%")
        click.echo(f"  Total time: {summary.total_execution_time:.1f}s")
        
        # Collect metrics
        click.echo("")
        click.echo("📈 Collecting metrics...")
        metrics_collector = MetricsCollector(framework.results_dir)
        metrics_data = metrics_collector.collect_all_metrics(framework.results)
        
        # Perform analysis
        click.echo("🔍 Performing analysis...")
        analyzer = MetricsAnalyzer(os.path.join(framework.results_dir, "metrics"))
        analysis_results = analyzer.analyze_comprehensive(framework.results)
        
        # Plateau analysis if requested
        if include_plateau:
            click.echo("📉 Performing plateau analysis...")
            plateau_analyzer = PlateauAnalyzer(os.path.join(framework.results_dir, "analysis"))
            plateau_results = plateau_analyzer.analyze_plateaus(framework.results)
        
        # Generate reports
        click.echo("📄 Generating reports...")
        report_generator = ReportGenerator(framework.results_dir)
        summary_report = report_generator.generate_summary_report(analysis_results)
        
        # Final summary
        click.echo("")
        click.echo("✅ Test framework execution completed!")
        click.echo(f"Results directory: {framework.results_dir}")
        click.echo(f"Summary report: {summary_report}")
        
        if include_plateau:
            click.echo("Plateau analysis included in results")
        
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        raise click.ClickException(str(e))


@cli.command()
@click.option('--results-dir', required=True, help='Results directory path')
@click.option('--include-plateau', is_flag=True, help='Include plateau analysis')
def analyze(results_dir, include_plateau):
    """
    Perform post-execution analysis on existing results.
    
    Useful for re-analyzing results with different parameters or
    adding additional analysis types without re-executing tests.
    """
    click.echo("🔍 Starting post-execution analysis")
    click.echo(f"Results directory: {results_dir}")
    click.echo("")
    
    try:
        results_path = Path(results_dir)
        if not results_path.exists():
            raise click.ClickException(f"Results directory not found: {results_dir}")
        
        # Load task results from saved data
        task_results = load_task_results_from_directory(results_dir)
        
        if not task_results:
            raise click.ClickException("No task results found in directory")
        
        click.echo(f"Loaded {len(task_results)} task results")
        
        # Perform analysis
        click.echo("📊 Performing comprehensive analysis...")
        analyzer = MetricsAnalyzer(os.path.join(results_dir, "metrics"))
        analysis_results = analyzer.analyze_comprehensive(task_results)
        
        # Plateau analysis if requested
        if include_plateau:
            click.echo("📉 Performing plateau analysis...")
            plateau_analyzer = PlateauAnalyzer(os.path.join(results_dir, "analysis"))
            plateau_results = plateau_analyzer.analyze_plateaus(task_results)
        
        # Generate reports
        click.echo("📄 Generating reports...")
        report_generator = ReportGenerator(results_dir)
        summary_report = report_generator.generate_summary_report(analysis_results)
        
        # Display top configurations
        config_analysis = analysis_results.get("configuration_analysis", {})
        top_configs = config_analysis.get("configuration_ranking", [])[:3]
        
        if top_configs:
            click.echo("")
            click.echo("🏆 Top Configurations:")
            for i, config in enumerate(top_configs, 1):
                click.echo(f"  {i}. {config['configuration']}")
                click.echo(f"     Quality Score: {config['quality_score']:.1f}")
                click.echo(f"     Success Rate: {config['success_rate']:.1f}%")
                click.echo(f"     Avg Time: {config['average_execution_time']:.1f}s")
        
        click.echo("")
        click.echo("✅ Analysis completed!")
        click.echo(f"Summary report: {summary_report}")
        
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        raise click.ClickException(str(e))


@cli.command()
@click.option('--type', 'config_type', default='basic', 
              type=click.Choice(['basic', 'extended']),
              help='Configuration set type')
@click.option('--output', default='test_configs.json', help='Output file path')
def create_config(config_type, output):
    """
    Create predefined configuration file for framework execution.
    
    Generates configuration files with ToolConfig-based testing scenarios
    that are compatible with the existing rv-experiment system.
    """
    click.echo(f"📝 Creating {config_type} configuration set using ToolConfig")
    
    try:
        if config_type == 'basic':
            configs = get_basic_evaluation_configs()
        else:
            configs = get_extended_evaluation_configs()
        
        # Save configuration set as JSON
        config_data = []
        for config in configs:
            config_data.append({
                "name": config.name,
                "variants": config.variants,
                "parameters": config.parameters
            })
        
        with open(output, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        click.echo(f"✅ Configuration file created: {output}")
        click.echo(f"Contains {len(configs)} configurations")
        
        # Display configuration names
        click.echo("\nConfigurations included:")
        for i, config in enumerate(configs):
            strategy = config.parameters.get('prompt_strategy', 'default')
            model = config.parameters.get('llm_model', 'default')
            click.echo(f"  - {config.name}:{config.variants[0] if config.variants else 'default'} (strategy: {strategy}, model: {model})")
        
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        raise click.ClickException(str(e))


def load_task_results_from_directory(results_dir: str):
    """
    Load task results from directory structure.
    
    This would parse the results directory and reconstruct TaskResult objects
    from saved execution data and metrics files.
    
    Args:
        results_dir: Results directory path
        
    Returns:
        List of TaskResult objects
    """
    # Try to load from saved results.json file
    results_file = Path(results_dir) / "results.json"
    if results_file.exists():
        with open(results_file, 'r') as f:
            results_data = json.load(f)
        
        # Convert back to TaskResult objects
        from rv_test_framework.core.models import TaskResult
        task_results = []
        for result_data in results_data:
            task_result = TaskResult(**result_data)
            task_results.append(task_result)
        
        return task_results
    
    # If no results.json, return empty list
    return []


if __name__ == "__main__":
    cli()