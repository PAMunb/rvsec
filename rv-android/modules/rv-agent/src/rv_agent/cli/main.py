#!/usr/bin/env python3
"""
RVAgent CLI - MVP standalone execution.

Command-line interface for autonomous Android testing with LangChain tool-calling.
Implements the MVP-first strategy from the comprehensive plan.
"""

import click
import logging
import time
import json
import sys
from pathlib import Path
from typing import Dict, Any

from ..core.rv_agent import RVAgent
from ..constants import RVAgentConstants


@click.command()
@click.option('--package', '-p',
              required=True,
              help='Android package name to test (e.g., br.unb.cic.cryptoapp)')
@click.option('--device', '-d',
              default=RVAgentConstants.DEFAULT_DEVICE_ID,
              help=f'Device ID for connection (default: {RVAgentConstants.DEFAULT_DEVICE_ID})')
@click.option('--timeout', '-t',
              type=int,
              default=RVAgentConstants.DEFAULT_TIMEOUT,
              help=f'Execution timeout in seconds (default: {RVAgentConstants.DEFAULT_TIMEOUT})')
@click.option('--model', '-m',
              default=RVAgentConstants.DEFAULT_MODEL,
              help=f'LLM model to use (default: {RVAgentConstants.DEFAULT_MODEL})')
@click.option('--output-dir', '-o',
              default="./rvagent_results",
              help='Output directory for results and logs')
@click.option('--debug', '-v',
              is_flag=True,
              help='Enable debug logging with detailed [RVAGENT_DEBUG] output')
@click.option('--test-model',
              is_flag=True,
              help='Test LLM model connection and tool-calling before starting')
@click.option('--objective',
              default="explore_application",
              help='Testing objective (default: explore_application)')
def main(package: str, device: str, timeout: int, model: str, output_dir: str,
         debug: bool, test_model: bool, objective: str):
    """
    RVAgent CLI - Autonomous Android Testing with LangChain Tool-Calling.

    This is the MVP standalone client that uses native LangChain tool-calling
    to differentiate from other tools that use prompt engineering.

    Examples:
        # Basic usage with CryptoApp
        rvagent --package br.unb.cic.cryptoapp

        # Extended timeout with debug output
        rvagent --package br.unb.cic.cryptoapp --timeout 600 --debug

        # Test model connection first
        rvagent --package br.unb.cic.cryptoapp --test-model
    """

    # Configure logging with MVP debug prefix
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(message)s',  # Clean format for MVP logs
        force=True
    )

    logger = logging.getLogger('rv_agent.cli')

    # MVP startup banner
    click.echo("🤖 RVAgent MVP - LangChain Tool-Calling for Android Testing")
    click.echo("=" * 60)
    click.echo(f"📱 Package: {package}")
    click.echo(f"📱 Device: {device}")
    click.echo(f"🧠 Model: {model}")
    click.echo(f"⏱️ Timeout: {timeout}s")
    click.echo(f"📂 Output: {output_dir}")
    click.echo(f"🎯 Objective: {objective}")
    if debug:
        click.echo("🐛 Debug logging: ENABLED")
    click.echo("=" * 60)

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        # Initialize RVAgent with MVP configuration
        logger.info("[RVAGENT_DEBUG] Initializing RVAgent MVP...")
        agent = RVAgent(timeout=timeout)

        # Test model connection if requested
        if test_model:
            logger.info("[RVAGENT_DEBUG] Testing LLM model connection...")
            connection_ok = agent.llm_service.test_llm_connection()
            if connection_ok:
                click.echo("✅ LLM model connection test: SUCCESS")
            else:
                click.echo("❌ LLM model connection test: FAILED")
                return 1

        # Step 1: Connect to device
        logger.info("[RVAGENT_DEBUG] Connecting to Android device...")
        if not agent.connect_to_device():
            click.echo("❌ Failed to connect to Android device")
            return 1

        click.echo("✅ Device connected successfully")

        # Step 2: Start testing session
        logger.info("[RVAGENT_DEBUG] Starting autonomous testing session...")
        if not agent.start_testing_session(package, objective):
            click.echo("❌ Failed to start testing session")
            return 1

        click.echo(f"✅ Testing session started for {package}")

        # Step 3: Run autonomous exploration with real-time progress
        logger.info("[RVAGENT_DEBUG] Starting autonomous exploration...")
        click.echo("\n🚀 Starting autonomous exploration...")
        click.echo("   Use Ctrl+C to stop gracefully\n")

        start_time = time.time()

        try:
            results = agent.run_autonomous_exploration(timeout)
        except KeyboardInterrupt:
            click.echo("\n⚠️ Execution interrupted by user")
            logger.info("[RVAGENT_DEBUG] User interrupted execution")
            results = agent._generate_session_summary() if agent.current_session else {}

        # Step 4: Generate results summary
        execution_time = time.time() - start_time
        success = "error" not in results

        if success:
            # Extract summary metrics
            session_info = results.get("session", {})
            iterations = session_info.get("iterations", 0)
            success_rate = session_info.get("success_rate", 0.0)
            coverage_stats = results.get("ui_coverage", {})
            total_elements = coverage_stats.get("total_unique_elements", 0)

            click.echo("\n" + "=" * 60)
            click.echo("📊 EXECUTION SUMMARY")
            click.echo("=" * 60)
            click.echo(f"⏱️ Total time: {execution_time:.1f}s")
            click.echo(f"🔄 Iterations: {iterations}")
            click.echo(f"✅ Success rate: {success_rate:.1%}")
            click.echo(f"🎯 Elements tested: {total_elements}")
            click.echo(f"📱 Package: {package}")
        else:
            click.echo("\n❌ Execution failed:")
            click.echo(f"   Error: {results.get('error', 'Unknown error')}")

        # Step 5: Save results to files
        timestamp = int(time.time())
        results_file = output_path / f"{package.replace('.', '_')}_{timestamp}.json"

        # Add CLI metadata to results
        results["cli_metadata"] = {
            "package": package,
            "device": device,
            "timeout": timeout,
            "model": model,
            "objective": objective,
            "execution_time": execution_time,
            "timestamp": timestamp,
            "success": success
        }

        # Save results
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str, ensure_ascii=False)

        click.echo(f"\n💾 Results saved to: {results_file}")

        # LLM metrics
        llm_metrics = agent.llm_service.get_metrics()
        click.echo(f"🧠 LLM: {llm_metrics['model_name']}")
        click.echo(f"🔧 Tools: {', '.join(llm_metrics['tools_available'])}")

        # Agent status
        agent_status = agent.get_agent_status()
        click.echo(f"📊 Agent status: {'Connected' if agent_status['connected'] else 'Disconnected'}")

        # Cleanup
        agent.stop_session()
        click.echo("\n✅ RVAgent MVP execution completed")

        return 0 if success else 1

    except KeyboardInterrupt:
        click.echo("\n⚠️ Interrupted by user")
        return 1
    except Exception as e:
        click.echo(f"\n❌ Unexpected error: {e}")
        logger.error(f"[RVAGENT_DEBUG] Unexpected error: {e}")
        return 1


@click.command()
@click.option('--model', '-m',
              default=RVAgentConstants.DEFAULT_MODEL,
              help=f'LLM model to test (default: {RVAgentConstants.DEFAULT_MODEL})')
def test_connection(model: str):
    """Test LLM model connection and tool-calling capabilities."""

    logging.basicConfig(level=logging.INFO, format='%(message)s', force=True)

    click.echo("🧪 Testing LLM Connection and Tool-Calling")
    click.echo("=" * 50)
    click.echo(f"🧠 Model: {model}")

    try:
        # Initialize minimal agent for testing
        agent = RVAgent(timeout=60)

        # Test connection
        click.echo("\n🔗 Testing LLM connection...")
        connection_ok = agent.llm_service.test_llm_connection()

        if connection_ok:
            click.echo("✅ Connection: SUCCESS")

            # Get metrics
            metrics = agent.llm_service.get_metrics()
            click.echo(f"🔧 Tools available: {len(metrics['tools_available'])}")
            for tool in metrics['tools_available']:
                click.echo(f"   • {tool}")

            click.echo(f"⚙️ Parameters:")
            params = metrics['parameters']
            click.echo(f"   • Temperature: {params['temperature']}")
            click.echo(f"   • Top-p: {params['top_p']}")
            click.echo(f"   • Top-k: {params['top_k']}")

        else:
            click.echo("❌ Connection: FAILED")
            return 1

        click.echo("\n✅ Test completed successfully")
        return 0

    except Exception as e:
        click.echo(f"\n❌ Test failed: {e}")
        return 1


# Multi-command CLI
@click.group()
def cli():
    """RVAgent - Autonomous Android Testing with LangChain Tool-Calling."""
    pass


cli.add_command(main, name="run")
cli.add_command(test_connection, name="test")


if __name__ == "__main__":
    cli()