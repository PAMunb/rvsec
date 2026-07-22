#!/usr/bin/env python3
"""
RVAgent CLI - Autonomous Android Testing.

Command-line interface for autonomous Android testing using LangGraph
with vision capabilities.

PREREQUISITES:
- Emulator running: scripts/run_emulator.sh
- APK already installed on emulator
- SGLang server running (for LLM modes)

NOTE: This CLI does NOT install APKs. Use `adb install` manually or
run via rv-experiment which handles APK installation automatically.
"""

import logging
import sys
from pathlib import Path

import click
from rv_agent.agent.agent_factory import AgentFactory
from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.constants import RVAgentConstants


def setup_logging(debug: bool = False) -> logging.Logger:
    """Configure logging for CLI."""
    log_level = logging.DEBUG if debug else logging.INFO
    log_format = (
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        if debug
        else "%(message)s"
    )
    logging.basicConfig(level=log_level, format=log_format, force=True)
    return logging.getLogger("rv_agent.cli")


@click.group()
def cli():
    """RVAgent - Autonomous Android Testing with LangGraph."""


@cli.command()
@click.option(
    "--package",
    "-p",
    required=True,
    help="Android package name (e.g., br.unb.cic.cryptoapp)",
)
@click.option(
    "--device",
    "-d",
    default=RVAgentConstants.DEFAULT_DEVICE_ID,
    help=f"Device ID (default: {RVAgentConstants.DEFAULT_DEVICE_ID})",
)
@click.option(
    "--timeout",
    "-t",
    type=int,
    default=300,
    help="Execution timeout in seconds (default: 300)",
)
@click.option(
    "--mode",
    "-m",
    type=click.Choice(["multimode", "pure_algorithm", "llm_only"]),
    default="multimode",
    help="Agent execution mode (default: multimode)",
)
@click.option(
    "--strategy",
    "-s",
    default="rvagent",
    help="Exploration strategy (default: rvagent)",
)
@click.option(
    "--results-dir",
    "-o",
    default="./rvagent_results",
    help="Output directory for results",
)
@click.option("--debug", "-v", is_flag=True, help="Enable debug logging")
@click.option(
    "--llm-probability",
    type=float,
    default=0.7,
    help="LLM probability for multimode (default: 0.7)",
)
def run(
    package: str,
    device: str,
    timeout: int,
    mode: str,
    strategy: str,
    results_dir: str,
    debug: bool,
    llm_probability: float,
):
    """
    Run autonomous Android testing.

    PREREQUISITES:
    - Emulator must be running (use scripts/run_emulator.sh)
    - APK must be installed (use: adb install <apk>)
    - For LLM modes: SGLang server must be running

    Examples:

        # Pure algorithm mode (no LLM needed)
        rv-agent run --package br.unb.cic.cryptoapp --mode pure_algorithm --timeout 60

        # Multimode with LLM
        rv-agent run --package br.unb.cic.cryptoapp --mode multimode --timeout 300

        # LLM only mode
        rv-agent run --package br.unb.cic.cryptoapp --mode llm_only --timeout 300
    """
    logger = setup_logging(debug)

    # Banner
    click.echo("=" * 60)
    click.echo("RVAgent - Autonomous Android Testing")
    click.echo("=" * 60)
    click.echo(f"Package: {package}")
    click.echo(f"Device: {device}")
    click.echo(f"Timeout: {timeout}s")
    click.echo(f"Mode: {mode}")
    click.echo(f"Strategy: {strategy}")
    click.echo(f"Results: {results_dir}")
    if mode == "multimode":
        click.echo(f"LLM Probability: {llm_probability}")
    if debug:
        click.echo("Debug: ENABLED")
    click.echo("=" * 60)

    # Create output directory
    output_path = Path(results_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        # Build configuration
        click.echo("\nInitializing RVAgent...")

        config = RVAgentConfig(
            package_name=package,
            device_id=device,
            timeout=timeout,
            agent_mode=mode,
            strategy=strategy,
            metrics_output_dir=results_dir,
            llm_probability=llm_probability,
            debug_mode=debug,
        )

        # Validate
        is_valid, error = config.validate()
        if not is_valid:
            click.echo(f"Configuration error: {error}")
            sys.exit(1)

        # Create agent via factory
        agent = AgentFactory.create_agent(config)
        click.echo(f"Agent initialized (mode: {mode})")

        # Run exploration
        click.echo("\nStarting exploration...")
        click.echo("Press Ctrl+C to stop\n")

        try:
            results = agent.run()
        except KeyboardInterrupt:
            click.echo("\nInterrupted by user")
            results = {"status": "interrupted"}

        # Display results
        click.echo("\n" + "=" * 60)
        click.echo("RESULTS")
        click.echo("=" * 60)

        status = results.get("status", "unknown")
        iterations = results.get("iterations", 0)
        unique_states = results.get("unique_states", 0)
        execution_time = results.get("execution_time", 0)

        click.echo(f"Status: {status}")
        click.echo(f"Iterations: {iterations}")
        click.echo(f"Unique states: {unique_states}")
        click.echo(f"Execution time: {execution_time:.1f}s")

        if "error" in results:
            click.echo(f"Error: {results['error']}")

        click.echo("\nRVAgent execution completed")
        sys.exit(0 if status in ["completed", "timeout"] else 1)

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=debug)
        click.echo(f"\nError: {e}")
        sys.exit(1)


@cli.command()
@click.option(
    "--device",
    "-d",
    default=RVAgentConstants.DEFAULT_DEVICE_ID,
    help=f"Device ID (default: {RVAgentConstants.DEFAULT_DEVICE_ID})",
)
def test(device: str):
    """Test device connection and configuration."""
    setup_logging(False)

    click.echo("Testing RVAgent Configuration")
    click.echo("=" * 50)

    try:
        from rv_agent.agent.device_interface import DeviceInterface

        click.echo(f"\nTesting device connection: {device}")
        dev = DeviceInterface(device_id=device)

        # Test basic operations
        size = dev.get_screen_size()
        click.echo(f"Screen size: {size[0]}x{size[1]}")

        click.echo("\nDevice connection successful")
        sys.exit(0)

    except Exception as e:
        click.echo(f"\nConnection failed: {e}")
        sys.exit(1)


@cli.command()
@click.argument("apk_path", type=click.Path(exists=True))
@click.option(
    "--device",
    "-d",
    default=RVAgentConstants.DEFAULT_DEVICE_ID,
    help=f"Device ID (default: {RVAgentConstants.DEFAULT_DEVICE_ID})",
)
def install(apk_path: str, device: str):
    """Install APK on device (convenience command)."""
    import subprocess

    click.echo(f"Installing {apk_path} on {device}...")

    try:
        result = subprocess.run(
            ["adb", "-s", device, "install", "-r", apk_path],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            click.echo("Installation successful")
            sys.exit(0)
        else:
            click.echo(f"Installation failed: {result.stderr}")
            sys.exit(1)

    except subprocess.TimeoutExpired:
        click.echo("Installation timed out")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}")
        sys.exit(1)


def main():
    """Entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()
