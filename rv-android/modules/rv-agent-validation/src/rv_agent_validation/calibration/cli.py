"""
CLI commands for RVAgent calibration.

Provides commands for viewing parameter definitions and defaults.
Calibration execution is handled by scripts/calibration_orchestrator.py
and scripts/baseline_docker.py (Docker-based, host-side).
"""

import click

from .parameter_space import get_default_params


@click.group()
def calibration():
    """RVAgent calibration commands."""


@calibration.command()
@click.option(
    "--params-file",
    required=True,
    type=click.Path(exists=True),
    help="Path to optimal_params.json",
)
def show_params(params_file: str):
    """
    Show calibrated parameters.

    Example:
        python -m rv_agent_validation show-params \\
            --params-file ./calibration_macro/optimal_params.json
    """
    import json

    with open(params_file) as f:
        data = json.load(f)

    click.echo("\n" + "=" * 60)
    click.echo("CALIBRATED PARAMETERS")
    click.echo("=" * 60)
    click.echo(f"Phase: {data.get('phase', 'unknown')}")
    click.echo(f"Seed: {data.get('seed', 'unknown')}")
    click.echo(f"Best score: {data.get('best_score', 0):.2f}")
    click.echo(f"Trials: {data.get('n_trials', 0)}")
    click.echo("\nParameters:")

    for name, value in data.get("best_params", {}).items():
        click.echo(f"  {name}: {value}")

    # Show tool spec string
    from .parameter_space import params_to_tool_spec

    spec = params_to_tool_spec(data.get("best_params", {}))
    click.echo(f"\nTool spec string:\n  {spec}")


@calibration.command()
def show_defaults():
    """
    Show default parameter values.

    Example:
        python -m rv_agent_validation show-defaults
    """
    defaults = get_default_params()

    click.echo("\n" + "=" * 60)
    click.echo("DEFAULT PARAMETERS")
    click.echo("=" * 60)

    for name, value in defaults.items():
        click.echo(f"  {name}: {value}")


if __name__ == "__main__":
    calibration()
