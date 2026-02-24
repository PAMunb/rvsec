#!/usr/bin/env python3
"""
RV-Agent Validation CLI

Command-line interface for rv-agent validation experiments.

Commands:
    run         Run validation experiment from config file
    preprocess  Instrument APKs and run static analysis
    show-params Show calibrated parameters
    show-defaults Show default parameter values
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import click


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """RV-Agent Validation - Experiment and validation framework."""


# Import and register calibration commands
from rv_agent_validation.calibration.cli import calibration

cli.add_command(calibration.get_command(None, "show-params"), "show-params")
cli.add_command(calibration.get_command(None, "show-defaults"), "show-defaults")


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    required=True,
    help="Experiment config JSON file",
)
@click.option(
    "--output", "-o", type=click.Path(), default="results", help="Output directory"
)
@click.option("--resume", is_flag=True, help="Resume from checkpoint")
@click.option(
    "--dry-run", is_flag=True, help="Show what would be executed without running"
)
def run(config, output, resume, dry_run):
    """Run validation experiment from configuration file.

    Example config (JSON):
    {
        "experiment_name": "phase1_test",
        "apk_paths": ["data/apks/app.apk"],
        "strategies": ["rvagent"],
        "timeout_seconds": 300,
        "agent_mode": "llm_only",
        "seeds": [42, 123],
        "device_serial": "emulator-5554"
    }
    """
    from rv_agent_validation.experiment.config import ExperimentConfig
    from rv_agent_validation.experiment.runner import ExperimentRunner

    config_path = Path(config)
    with open(config_path) as f:
        config_data = json.load(f)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Support both direct apk_paths and apks + apks_dir
    apk_paths = config_data.get("apk_paths", [])
    if not apk_paths and "apks" in config_data:
        apks_dir = Path(config_data.get("apks_dir", "data/apks_instrumented"))
        for apk_name in config_data["apks"]:
            apk_path = apks_dir / apk_name / apk_name
            if apk_path.exists():
                apk_paths.append(str(apk_path))
            elif (apks_dir / apk_name).exists():
                apk_paths.append(str(apks_dir / apk_name))
            else:
                click.echo(f"Warning: APK not found: {apk_name}")

    if not apk_paths:
        click.echo("Error: No APKs found. Check apk_paths or apks/apks_dir in config.")
        sys.exit(1)

    seeds = config_data.get("seeds", [42])

    exp_config = ExperimentConfig(
        experiment_id=f"{config_data.get('experiment_id', config_data.get('experiment_name', 'exp'))}_{timestamp}",
        experiment_name=config_data.get("experiment_name", "Experiment"),
        apk_paths=apk_paths,
        strategies=config_data.get("strategies", ["rvagent"]),
        seeds=seeds,
        timeout_seconds=config_data.get(
            "timeout_seconds", config_data.get("timeout", 300)
        ),
        agent_mode=config_data.get(
            "agent_mode", config_data.get("mode", "pure_algorithm")
        ),
        results_dir=Path(output),
        device_serial=config_data.get(
            "device_serial", config_data.get("device", "emulator-5554")
        ),
        static_analysis_variants=config_data.get("static_analysis_variants", [True]),
        prompt_versions=config_data.get("prompt_versions", ["v13"]),
        llm_param_configs=config_data.get("llm_param_configs", ["default"]),
        llm_probability_variants=config_data.get("llm_probability_variants", [0.7]),
    )

    click.echo(f"Experiment: {exp_config.experiment_name}")
    click.echo(f"APKs: {len(apk_paths)}")
    click.echo(f"Strategies: {exp_config.strategies}")
    click.echo(f"Mode: {exp_config.agent_mode}")
    click.echo(f"Prompt versions: {exp_config.prompt_versions}")
    click.echo(f"Seeds: {exp_config.seeds}")
    click.echo(f"Static Analysis Variants: {exp_config.static_analysis_variants}")
    click.echo(f"Timeout: {exp_config.timeout_seconds}s")
    click.echo(f"Output: {output}")

    if dry_run:
        click.echo("\n[DRY RUN] Would execute:")
        runs = exp_config.generate_runs()
        for run in runs:
            apk_name = Path(run.apk_path).name
            prompt = getattr(run, "prompt_version", "v13")
            param = getattr(run, "param_config_name", "default")
            click.echo(
                f"  - {apk_name} | {run.strategy} | {prompt} | {param} | seed={run.seed}"
            )
        click.echo(f"\nTotal runs: {len(runs)}")
        return

    runner = ExperimentRunner(config=exp_config, base_dir=Path(output))
    runner.run_experiment(resume=resume)


@cli.command()
@click.option(
    "--data-dir",
    "-d",
    type=click.Path(exists=True),
    default=None,
    help="Validation data directory",
)
@click.option(
    "--specs-dir",
    "-s",
    type=click.Path(exists=True),
    default=None,
    help="MOP specifications directory",
)
@click.option("--force", "-f", is_flag=True, help="Force re-instrumentation")
@click.option("--skip-static", is_flag=True, help="Skip static analysis phase")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def preprocess(data_dir, specs_dir, force, skip_static, verbose):
    """Preprocess APKs: generate monitors, instrument, and run static analysis."""
    import logging

    from rv_agent_validation.preprocessing import InstrumentationWrapper

    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    if data_dir is None:
        module_dir = Path(__file__).parent.parent.parent.parent
        data_dir = module_dir / "data"

    click.echo(f"Preprocessing APKs from: {data_dir}")

    try:
        wrapper = InstrumentationWrapper(
            validation_data_dir=str(data_dir), specs_dir=specs_dir
        )
        result = wrapper.run(force=force, skip_static_analysis=skip_static)

        if result.total_apks > 0 and len(result.instrumented_apks) > 0:
            click.echo(click.style("Preprocessing completed!", fg="green"))
            click.echo(
                f"  Instrumented: {len(result.instrumented_apks)}/{result.total_apks}"
            )
        else:
            click.echo(click.style("Preprocessing failed!", fg="red"))
            sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
