#!/usr/bin/env python3
"""
RV-Agent Validation CLI

Command-line interface for rv-agent validation experiments.
"""

import click
import sys
from pathlib import Path


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """RV-Agent Validation - Experiment and validation framework."""
    pass


@cli.command()
@click.option("--config", "-c", type=click.Path(exists=True), help="Configuration file path")
@click.option("--apks-dir", type=click.Path(exists=True), help="Directory containing APKs")
@click.option("--static-data-dir", type=click.Path(exists=True), help="Directory with static analysis data")
@click.option("--modes", "-m", multiple=True, default=["multimode"], help="Agent modes to test")
@click.option("--seeds", "-s", multiple=True, type=int, default=[42], help="Random seeds")
@click.option("--timeout", "-t", type=int, default=300, help="Timeout per run in seconds")
@click.option("--output", "-o", type=click.Path(), default="results", help="Output directory")
@click.option("--device", "-d", default="emulator-5554", help="Device serial")
def multimodal(config, apks_dir, static_data_dir, modes, seeds, timeout, output, device):
    """Run multimodal validation experiments.

    Compares different agent modes (pure_algorithm, llm_only, multimode)
    and collects metrics like hit rate, unique states, and activity coverage.
    """
    from rv_agent_validation.multimodal.runner import run_multimodal_validation

    run_multimodal_validation(
        config_path=config,
        apks_dir=apks_dir,
        static_data_dir=static_data_dir,
        modes=list(modes),
        seeds=list(seeds),
        timeout=timeout,
        output_dir=output,
        device_serial=device,
    )


@cli.command()
@click.option("--config", "-c", type=click.Path(exists=True), required=True, help="Experiment config file")
@click.option("--output", "-o", type=click.Path(), default="results", help="Output directory")
@click.option("--resume", is_flag=True, help="Resume from checkpoint")
@click.option("--dry-run", is_flag=True, help="Show what would be executed without running")
def experiment(config, output, resume, dry_run):
    """Run validation experiment from configuration file.

    Executes a full validation experiment with multiple APKs, modes, and seeds
    as defined in the configuration file.
    """
    from rv_agent_validation.experiment.runner import ExperimentRunner

    runner = ExperimentRunner(
        config_path=config,
        output_dir=output,
        resume=resume,
        dry_run=dry_run,
    )
    runner.run()


@cli.command()
@click.option("--output", "-o", type=click.Path(), default="results", help="Output directory")
@click.option("--apps", "-a", type=int, default=60, help="Number of apps to test")
@click.option("--timeout", "-t", type=int, default=300, help="Timeout per run in seconds")
def overnight(output, apps, timeout):
    """Run overnight baseline experiment.

    Long-running experiment with many apps and strategies for baseline data.
    """
    from rv_agent_validation.experiment.overnight import run_overnight_baseline

    run_overnight_baseline(
        output_dir=output,
        num_apps=apps,
        timeout=timeout,
    )


@cli.command("select-apps")
@click.option("--source", "-s", type=click.Path(exists=True), required=True, help="Source CSV with APK data")
@click.option("--output", "-o", type=click.Path(), required=True, help="Output CSV path")
@click.option("--count", "-n", type=int, default=50, help="Number of APKs to select")
@click.option("--diversify", is_flag=True, default=True, help="Diversify by category")
def select_apps(source, output, count, diversify):
    """Select APKs for validation experiments.

    Selects APKs from source CSV with category diversification.
    """
    from rv_agent_validation.analysis.app_selector import select_apps_for_validation

    select_apps_for_validation(
        source_csv=source,
        output_csv=output,
        count=count,
        diversify_categories=diversify,
    )


@cli.command()
@click.argument("results_dir", type=click.Path(exists=True))
@click.option("--format", "-f", type=click.Choice(["csv", "json", "latex"]), default="csv")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def report(results_dir, format, output):
    """Generate report from experiment results.

    Exports results to CSV, JSON, or LaTeX format.
    """
    from rv_agent_validation.reports import export_results

    export_results(
        results_dir=results_dir,
        format=format,
        output_path=output,
    )


@cli.command()
@click.argument("results_dir", type=click.Path(exists=True))
@click.option("--test", "-t", type=click.Choice(["kruskal", "wilcoxon", "all"]), default="all")
def analyze(results_dir, test):
    """Run statistical analysis on experiment results.

    Performs Kruskal-Wallis, Wilcoxon tests, and effect size calculations.
    """
    from rv_agent_validation.statistics import run_analysis

    run_analysis(
        results_dir=results_dir,
        test_type=test,
    )


@cli.command()
@click.option(
    "--data-dir", "-d",
    type=click.Path(exists=True),
    default=None,
    help="Validation data directory (default: module's data/)"
)
@click.option(
    "--specs-dir", "-s",
    type=click.Path(exists=True),
    default=None,
    help="MOP specifications directory (default: data/specs/)"
)
@click.option("--force", "-f", is_flag=True, help="Force re-instrumentation")
@click.option("--skip-static", is_flag=True, help="Skip static analysis phase")
@click.option("--cleanup", is_flag=True, help="Cleanup temporary files after completion")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def preprocess(data_dir, specs_dir, force, skip_static, cleanup, verbose):
    """Preprocess APKs: generate monitors, instrument, and run static analysis.

    This command prepares APKs for validation experiments by:
    1. Generating runtime verification monitors from MOP specifications
    2. Instrumenting APKs with the generated monitors
    3. Running static analysis (GESDA, GATOR, REACH)
    4. Organizing output in the validation data directory

    IMPORTANT: .methods files are NOT regenerated - pre-existing files
    in all_methods/ are used instead.

    Example:
        rv-agent-validation preprocess --verbose
        rv-agent-validation preprocess --data-dir ./custom_data --force
    """
    import logging
    from pathlib import Path

    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Default to module's data directory
    if data_dir is None:
        module_dir = Path(__file__).parent.parent.parent.parent
        data_dir = module_dir / "data"

    from rv_agent_validation.preprocessing import InstrumentationWrapper

    click.echo(f"Preprocessing APKs from: {data_dir}")
    click.echo("")

    try:
        wrapper = InstrumentationWrapper(
            validation_data_dir=str(data_dir),
            specs_dir=specs_dir,
        )

        result = wrapper.run(
            force=force,
            skip_static_analysis=skip_static,
        )

        if cleanup:
            wrapper.cleanup_temp()

        # Print final status
        if result.total_apks > 0 and len(result.instrumented_apks) > 0:
            click.echo("")
            click.echo(click.style("Preprocessing completed successfully!", fg="green"))
            click.echo(f"  Instrumented: {len(result.instrumented_apks)}/{result.total_apks}")
            click.echo(f"  Static analysis: {len(result.static_analysis_success)}")
        else:
            click.echo("")
            click.echo(click.style("Preprocessing failed or no APKs processed!", fg="red"))
            sys.exit(1)

    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    cli()
