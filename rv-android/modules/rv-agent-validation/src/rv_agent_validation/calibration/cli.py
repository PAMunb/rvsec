"""
CLI commands for RVAgent calibration.

Provides commands for running calibration optimization and comparing results.
Supports resume via SQLite storage for long-running calibrations.
"""

import logging
from pathlib import Path
from typing import Optional

import click

from .parameter_space import CalibrationPhase, get_default_params
from .objective import ObjectiveFunction
from .optimizer import CalibrationOptimizer
from .runner import CalibrationRunner

logger = logging.getLogger(__name__)


@click.group()
def calibration():
    """RVAgent calibration commands."""
    pass


@calibration.command()
@click.option(
    '--apks-dir',
    required=True,
    type=click.Path(exists=True),
    help='Path to pre-instrumented APKs dataset (should contain only calibration APKs)'
)
@click.option(
    '--phase',
    type=click.Choice(['macro', 'micro', 'full']),
    default='macro',
    help='Calibration phase'
)
@click.option(
    '--n-trials',
    type=int,
    default=50,
    help='Number of optimization trials'
)
@click.option(
    '--timeout',
    type=int,
    default=300,
    help='Timeout per APK in seconds'
)
@click.option(
    '--seed',
    type=int,
    default=42,
    help='Random seed for reproducibility'
)
@click.option(
    '--output',
    type=click.Path(),
    default='./calibration_output',
    help='Output directory for results'
)
@click.option(
    '--best-macro',
    type=click.Path(exists=True),
    help='Path to optimal_params.json from macro phase (for micro phase)'
)
@click.option(
    '--baseline-dir',
    type=click.Path(exists=True),
    help='Path to baseline results for adaptive error normalization'
)
@click.option(
    '--agent-mode',
    type=click.Choice(['pure_algorithm', 'llm_only', 'multimode']),
    default='pure_algorithm',
    help='Agent execution mode'
)
@click.option(
    '--resume',
    is_flag=True,
    default=False,
    help='Resume interrupted calibration from last checkpoint'
)
@click.option(
    '--n-jobs',
    type=int,
    default=1,
    help='Number of parallel trials (each uses 1 emulator)'
)
def calibrate(
    apks_dir: str,
    phase: str,
    n_trials: int,
    timeout: int,
    seed: int,
    output: str,
    best_macro: Optional[str],
    baseline_dir: Optional[str],
    agent_mode: str,
    resume: bool,
    n_jobs: int
):
    """
    Run calibration optimization.

    Note: The apks-dir should contain only the APKs intended for calibration.
    Create separate directories for calibration vs hold-out validation sets.

    Supports --resume to continue interrupted calibrations.

    Example:
        # Macro phase (8 high-impact parameters)
        python -m rv_agent_validation calibrate \\
            --apks-dir ./data/calibration_dataset \\
            --phase macro \\
            --n-trials 50 \\
            --seed 42 \\
            --output ./calibration_macro

        # Resume interrupted calibration
        python -m rv_agent_validation calibrate \\
            --apks-dir ./data/calibration_dataset \\
            --phase macro \\
            --n-trials 50 \\
            --output ./calibration_macro \\
            --resume

        # Micro phase (using best macro params)
        python -m rv_agent_validation calibrate \\
            --apks-dir ./data/calibration_dataset \\
            --phase micro \\
            --best-macro ./calibration_macro/optimal_params.json \\
            --n-trials 30 \\
            --output ./calibration_micro
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Setup output directory and storage path
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)
    storage_path = str(output_path / "optuna_study.db")

    if resume:
        logger.info(f"Resuming calibration from {storage_path}")
    else:
        logger.info(f"Starting new calibration: phase={phase}, n_trials={n_trials}, seed={seed}")

    # Parse phase
    cal_phase = CalibrationPhase(phase)

    # Load macro params for micro phase
    fixed_params = {}
    if phase == 'micro' and best_macro:
        fixed_params = CalibrationOptimizer.load_best_params(best_macro)
        logger.info(f"Loaded macro params as fixed: {fixed_params}")
        click.echo(f"\nUsing fixed macro params from: {best_macro}")
        click.echo(f"Fixed params: {fixed_params}")

    # Create objective function
    objective_fn = ObjectiveFunction(
        coverage_weight=0.40,
        errors_weight=0.40,
        ui_coverage_weight=0.20
    )

    # Set baseline max errors if available
    if baseline_dir:
        max_errors = ObjectiveFunction.compute_baseline_max_errors(baseline_dir)
        objective_fn.set_baseline_max_errors(max_errors)

    # Create runner
    runner = CalibrationRunner(
        dataset_dir=apks_dir,
        objective_fn=objective_fn,
        output_base_dir=output,
        timeout=timeout,
        agent_mode=agent_mode,
        seed=seed  # Pass seed for rv-agent reproducibility
    )

    # Create optimizer with SQLite storage for resume support
    optimizer = CalibrationOptimizer(
        phase=cal_phase,
        objective_fn=objective_fn,
        trial_runner=runner.run_trial,
        seed=seed,
        study_name=f"rvagent_{phase}",
        storage_path=storage_path,
        resume=resume,
        fixed_params=fixed_params,
        n_jobs=n_jobs
    )

    # Show progress info
    completed = optimizer.get_completed_trials_count()
    remaining = optimizer.get_remaining_trials(n_trials)
    click.echo(f"\nCalibration status: {completed}/{n_trials} trials completed, {remaining} remaining")

    if remaining == 0:
        click.echo("All trials already completed!")
        best_params = optimizer.best_params or {}
    else:
        # Run optimization
        best_params = optimizer.optimize(n_trials=n_trials)

    # Save results
    optimizer.save_results(output)

    # Print summary
    total_completed = optimizer.get_completed_trials_count()
    click.echo("\n" + "=" * 60)
    click.echo("CALIBRATION COMPLETE")
    click.echo("=" * 60)
    click.echo(f"Total trials completed: {total_completed}")
    click.echo(f"Best score: {optimizer.best_score:.2f}")
    click.echo(f"Best parameters: {best_params}")
    click.echo(f"Results saved to: {output}")
    click.echo(f"SQLite storage: {storage_path}")


@calibration.command()
@click.option(
    '--params-file',
    required=True,
    type=click.Path(exists=True),
    help='Path to optimal_params.json'
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

    for name, value in data.get('best_params', {}).items():
        click.echo(f"  {name}: {value}")

    # Show tool spec string
    from .parameter_space import params_to_tool_spec
    spec = params_to_tool_spec(data.get('best_params', {}))
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


if __name__ == '__main__':
    calibration()
