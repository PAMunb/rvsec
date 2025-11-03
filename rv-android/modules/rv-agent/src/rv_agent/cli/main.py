#!/usr/bin/env python3
"""
RVAgent CLI - Autonomous Android Testing.

Command-line interface for autonomous Android testing using LangGraph with vision capabilities.
"""

import click
import logging
import time
import json
import sys
from pathlib import Path
from typing import Dict, Any

from ..core.langgraph_agent import RVAgent
from ..constants import RVAgentConstants


def run_with_timeout(agent: RVAgent, task: str, thread_id: str, timeout_seconds: int) -> Dict[str, Any]:
    """
    Run agent session with time-based timeout.

    Uses signal.SIGALRM for precise timeout control based on wall-clock time.
    No iteration limits - the agent runs until it decides to stop or timeout occurs.

    Args:
        agent: RVAgent instance
        task: Task description
        thread_id: Session thread ID
        timeout_seconds: Maximum execution time in seconds

    Returns:
        Session results dictionary
    """
    import signal

    start_time = time.time()
    results = None

    def timeout_handler(signum, frame):
        raise TimeoutError(f"Execution exceeded {timeout_seconds}s timeout")

    # Set timeout signal (Unix only)
    if hasattr(signal, 'SIGALRM'):
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)

    try:
        results = agent.run_session(
            task=task,
            thread_id=thread_id
        )

        # Add actual execution time
        results['execution_time'] = time.time() - start_time

    except TimeoutError as e:
        results = {
            "status": "timeout",
            "error": str(e),
            "execution_time": time.time() - start_time,
            "thread_id": thread_id
        }
    finally:
        # Cancel alarm
        if hasattr(signal, 'SIGALRM'):
            signal.alarm(0)

    return results


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
@click.option('--output-dir', '-o',
              default="./rvagent_results",
              help='Output directory for results and logs')
@click.option('--debug', '-v',
              is_flag=True,
              help='Enable debug logging')
@click.option('--objective',
              default="explore_application",
              help='Testing objective description')
def main(package: str, device: str, timeout: int, output_dir: str,
         debug: bool, objective: str):
    """
    RVAgent CLI - Autonomous Android Testing with LangGraph.

    Uses LangGraph with vision capabilities for autonomous Android application testing.

    Examples:
        # Basic usage
        rvagent run --package br.unb.cic.cryptoapp

        # Extended timeout with debug
        rvagent run --package br.unb.cic.cryptoapp --timeout 600 --debug

        # Custom objective
        rvagent run --package br.unb.cic.cryptoapp --objective "Test login flow"
    """

    # Configure logging
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s' if debug else '%(message)s',
        force=True
    )

    logger = logging.getLogger('rv_agent.cli')

    # Startup banner
    click.echo("🤖 RVAgent - Autonomous Android Testing (LangGraph)")
    click.echo("=" * 60)
    click.echo(f"📱 Package: {package}")
    click.echo(f"📱 Device: {device}")
    click.echo(f"⏱️  Timeout: {timeout}s")
    click.echo(f"📂 Output: {output_dir}")
    click.echo(f"🎯 Objective: {objective}")
    if debug:
        click.echo("🐛 Debug: ENABLED")
    click.echo("=" * 60)

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        # Initialize RVAgent with device connection
        click.echo("\n🚀 Initializing RVAgent...")
        agent = RVAgent(device_id=device)

        # Show agent status
        status = agent.get_status()
        click.echo(f"✅ Agent initialized")
        click.echo(f"   Model: {status['model']}")
        click.echo(f"   Device: {status['device']}")
        click.echo(f"   Tools: {status['tools_available']}")
        click.echo(f"   Architecture: {status['architecture']}")

        # Create task description
        task = f"""Test the Android application: {package}

Testing Objective: {objective}

Instructions:
1. Capture screenshots to analyze the UI
2. Explore the application by clicking buttons and interactive elements
3. Test input fields and forms
4. Navigate through different screens
5. Report any findings or issues

Use the available Android tools to interact with the application.
"""

        # Run autonomous session with timeout
        click.echo(f"\n🎯 Starting autonomous testing session...")
        click.echo("   Use Ctrl+C to stop gracefully\n")

        start_time = time.time()
        thread_id = f"rvagent_{package}_{int(start_time)}"

        try:
            results = run_with_timeout(agent, task, thread_id, timeout)
        except KeyboardInterrupt:
            click.echo("\n⚠️  Execution interrupted by user")
            execution_time = time.time() - start_time
            results = {
                "status": "interrupted",
                "execution_time": execution_time,
                "thread_id": thread_id
            }

        # Display results summary
        execution_time = results.get('execution_time', 0)
        result_status = results.get('status', 'unknown')

        click.echo("\n" + "=" * 60)
        click.echo("📊 EXECUTION SUMMARY")
        click.echo("=" * 60)
        click.echo(f"⏱️  Total time: {execution_time:.1f}s")
        click.echo(f"📊 Status: {result_status}")

        metrics = results.get('metrics', {})
        if metrics:
            click.echo(f"💬 Total messages: {metrics.get('total_messages', 0)}")
            click.echo(f"🔧 Total tool calls: {metrics.get('total_tool_calls', 0)}")

            breakdown = metrics.get('tool_breakdown', {})
            if breakdown:
                click.echo(f"\n🔧 Tool Breakdown:")
                for tool_name, count in breakdown.items():
                    if count > 0:
                        click.echo(f"   • {tool_name}: {count}")

        # Save results
        timestamp = int(time.time())
        results_file = output_path / f"{package.replace('.', '_')}_{timestamp}.json"

        # Add CLI metadata
        results["cli_metadata"] = {
            "package": package,
            "device": device,
            "timeout": timeout,
            "objective": objective,
            "execution_time": execution_time,
            "timestamp": timestamp,
            "model": status['model'],
            "architecture": status['architecture']
        }

        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str, ensure_ascii=False)

        click.echo(f"\n💾 Results saved to: {results_file}")
        click.echo("\n✅ RVAgent execution completed")

        return 0 if result_status == "completed" else 1

    except KeyboardInterrupt:
        click.echo("\n⚠️  Interrupted by user")
        return 1
    except Exception as e:
        click.echo(f"\n❌ Unexpected error: {e}")
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


@click.command()
def test():
    """Test RVAgent configuration and connections."""

    logging.basicConfig(level=logging.INFO, format='%(message)s', force=True)

    click.echo("🧪 Testing RVAgent Configuration")
    click.echo("=" * 50)

    try:
        # Test device connection
        click.echo("\n📱 Testing device connection...")
        agent = RVAgent(device_id=RVAgentConstants.DEFAULT_DEVICE_ID)

        status = agent.get_status()
        click.echo("✅ Device connected")
        click.echo(f"   Device: {status['device']}")
        click.echo(f"   Model: {status['model']}")
        click.echo(f"   Tools: {status['tools_available']}")
        click.echo(f"   Memory: {status['memory']}")
        click.echo(f"   Observability: {status['observability']}")
        click.echo(f"   Architecture: {status['architecture']}")

        click.echo("\n✅ All tests passed")
        return 0

    except Exception as e:
        click.echo(f"\n❌ Test failed: {e}")
        return 1


# Multi-command CLI
@click.group()
def cli():
    """RVAgent - Autonomous Android Testing with LangGraph."""
    pass


cli.add_command(main, name="run")
cli.add_command(test, name="test")


if __name__ == "__main__":
    cli()
