"""
RVAgent - Simple Test Entry Point

Main entry point for testing the refactored RVAgent architecture.
Provides quick access to different agent modes with sensible defaults.

Usage:
    # Interactive mode
    poetry run python modules/rv-agent/example_usage.py

    # Direct mode selection
    poetry run python modules/rv-agent/example_usage.py --mode pure_algorithm
    poetry run python modules/rv-agent/example_usage.py --mode pure_llm
    poetry run python modules/rv-agent/example_usage.py --mode multimode

    # Quick test (1 minute)
    poetry run python modules/rv-agent/example_usage.py --quick

    # Custom app
    poetry run python modules/rv-agent/example_usage.py --package com.example.app
"""

import argparse
import logging
import sys
from pathlib import Path

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.agent_factory import AgentFactory


def setup_logging(verbose: bool = False):
    """Configure logging for example execution."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def run_pure_algorithm_test(
    package_name: str = "br.unb.cic.cryptoapp",
    timeout: int = 180,
    device_id: str = "emulator-5554",
    strategy: str = "dfs"
):
    """
    Test pure algorithm (no LLM).

    Supports both DFS and BFS exploration strategies.
    Fast execution, deterministic exploration.
    Good baseline for comparison.
    """
    strategy_name = "DFS" if strategy == "dfs" else "BFS"
    print("\n" + "="*80)
    print(f"PURE ALGORITHM TEST ({strategy_name})")
    print("="*80)
    print(f"Package: {package_name}")
    print(f"Timeout: {timeout}s ({timeout/60:.1f}min)")
    print(f"Mode: Pure algorithm ({strategy_name} - no LLM)")
    print("="*80 + "\n")

    config = RVAgentConfig(
        package_name=package_name,
        device_id=device_id,
        agent_mode="pure_algorithm",
        strategy=strategy,
        timeout=timeout,
        max_iterations=200,
        screenshot_dir="/tmp/rvagent_screenshots",
        screenshot_rotation_limit=50,
        device_dimensions=(1080, 1920),
        optimized_dimensions=(704, 1248)
    )

    # Create agent via factory
    agent = AgentFactory.create_agent(
        config=config,
        static_data=None,
        device=None
    )

    # Run exploration
    print("Starting pure algorithm exploration...\n")
    results = agent.run()

    # Display results
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    print(f"Status: {results.get('status', 'unknown')}")
    print(f"Iterations: {results.get('iterations', 0)}")
    print(f"States: {results.get('unique_states', 0)}")
    print(f"Transitions: {results.get('transitions', 0)}")
    print(f"Time: {results.get('execution_time', 0):.1f}s")
    print("="*80 + "\n")

    return results


def run_pure_llm_test(
    package_name: str = "br.unb.cic.cryptoapp",
    timeout: int = 180,
    device_id: str = "emulator-5554"
):
    """
    Test pure LLM mode.

    All decisions made by LLM.
    Better state discovery but slower.
    """
    print("\n" + "="*80)
    print("PURE LLM TEST")
    print("="*80)
    print(f"Package: {package_name}")
    print(f"Timeout: {timeout}s ({timeout/60:.1f}min)")
    print("Mode: Pure LLM (qwen3-vl-4b-8k)")
    print("="*80 + "\n")

    config = RVAgentConfig(
        package_name=package_name,
        device_id=device_id,
        agent_mode="pure_llm",
        llm_model="qwen3-vl-4b-8k",  # 8k context
        timeout=timeout,
        max_iterations=200,
        screenshot_dir="/tmp/rvagent_screenshots",
        screenshot_rotation_limit=50,
        device_dimensions=(1080, 1920),
        optimized_dimensions=(704, 1248)
    )

    # Create agent via factory
    agent = AgentFactory.create_agent(
        config=config,
        static_data=None,
        device=None
    )

    # Run exploration
    print("Starting pure LLM exploration...\n")
    results = agent.run()

    # Display results
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    print(f"Status: {results.get('status', 'unknown')}")
    print(f"Iterations: {results.get('iterations', 0)}")
    print(f"States: {results.get('unique_states', 0)}")
    print(f"Transitions: {results.get('transitions', 0)}")
    print(f"LLM decisions: {results.get('llm_decisions', 0)}")
    print(f"LLM time: {results.get('llm_time_ms', 0)/1000:.1f}s")
    print(f"Time: {results.get('execution_time', 0):.1f}s")
    print("="*80 + "\n")

    return results


def run_multimode_test(
    package_name: str = "br.unb.cic.cryptoapp",
    timeout: int = 180,
    device_id: str = "emulator-5554",
    llm_probability: float = 0.70
):
    """
    Test multimode (hybrid LLM + algorithm).

    Balances LLM intelligence with algorithm speed.
    LLM is the star (>50% probability).
    """
    print("\n" + "="*80)
    print("MULTIMODE TEST (HYBRID)")
    print("="*80)
    print(f"Package: {package_name}")
    print(f"Timeout: {timeout}s ({timeout/60:.1f}min)")
    print(f"Mode: Multimode (LLM {llm_probability:.0%} / Algorithm {1-llm_probability:.0%})")
    print("Model: qwen3-vl-4b-8k")
    print("="*80 + "\n")

    config = RVAgentConfig(
        package_name=package_name,
        device_id=device_id,
        agent_mode="multimode",
        llm_probability=llm_probability,
        llm_model="qwen3-vl-4b-8k",  # 8k context
        strategy="dfs",
        timeout=timeout,
        max_iterations=200,
        screenshot_dir="/tmp/rvagent_screenshots",
        screenshot_rotation_limit=50,
        device_dimensions=(1080, 1920),
        optimized_dimensions=(704, 1248)
    )

    # Create agent via factory
    agent = AgentFactory.create_agent(
        config=config,
        static_data=None,
        device=None
    )

    # Run exploration
    print("Starting multimode exploration...\n")
    results = agent.run()

    # Display results
    total_decisions = results.get('llm_decisions', 0) + results.get('algorithm_decisions', 0)
    actual_llm_ratio = results.get('llm_decisions', 0) / total_decisions if total_decisions > 0 else 0

    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    print(f"Status: {results.get('status', 'unknown')}")
    print(f"Iterations: {results.get('iterations', 0)}")
    print(f"States: {results.get('unique_states', 0)}")
    print(f"Transitions: {results.get('transitions', 0)}")
    print(f"LLM decisions: {results.get('llm_decisions', 0)}")
    print(f"Algorithm decisions: {results.get('algorithm_decisions', 0)}")
    print(f"Actual LLM ratio: {actual_llm_ratio:.1%} (expected {llm_probability:.0%})")
    print(f"LLM time: {results.get('llm_time_ms', 0)/1000:.1f}s")
    print(f"Time: {results.get('execution_time', 0):.1f}s")
    print("="*80 + "\n")

    return results


def interactive_mode():
    """Interactive mode for selecting tests."""
    print("\n" + "="*80)
    print("RVAgent - Autonomous Android Testing")
    print("="*80)
    print("\nAvailable test modes:")
    print("  1. Pure Algorithm (DFS) - Depth-first, fast")
    print("  2. Pure Algorithm (BFS) - Breadth-first, exhaustive")
    print("  3. Pure LLM - Intelligent, slower")
    print("  4. Multimode (Hybrid) - Balanced (recommended)")
    print("  5. Quick Test (1 minute multimode)")
    print()

    choice = input("Select mode (1-5): ").strip()

    if choice == "1":
        return run_pure_algorithm_test(strategy="dfs")
    elif choice == "2":
        return run_pure_algorithm_test(strategy="bfs")
    elif choice == "3":
        return run_pure_llm_test()
    elif choice == "4":
        return run_multimode_test()
    elif choice == "5":
        return run_multimode_test(timeout=60)
    else:
        print(f"Invalid choice: {choice}. Running multimode test...")
        return run_multimode_test()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="RVAgent - Simple test entry point"
    )
    parser.add_argument(
        "--mode",
        choices=["pure_algorithm", "pure_llm", "multimode"],
        help="Agent mode to test"
    )
    parser.add_argument(
        "--strategy",
        choices=["dfs", "bfs", "greedy", "simulated_annealing", "genetic_algorithm"],
        default="dfs",
        help="Algorithm strategy (for pure_algorithm mode, default: dfs)"
    )
    parser.add_argument(
        "--package",
        default="br.unb.cic.cryptoapp",
        help="Package name to test (default: cryptoapp)"
    )
    parser.add_argument(
        "--device",
        default="emulator-5554",
        help="Device ID (default: emulator-5554)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Timeout in seconds (default: 180 = 3min)"
    )
    parser.add_argument(
        "--llm-probability",
        type=float,
        default=0.70,
        help="LLM probability for multimode (default: 0.70)"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick test (60 seconds multimode)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    # Quick test shortcut
    if args.quick:
        return run_multimode_test(
            package_name=args.package,
            timeout=60,
            device_id=args.device,
            llm_probability=args.llm_probability
        )

    # Direct mode selection
    if args.mode == "pure_algorithm":
        return run_pure_algorithm_test(
            package_name=args.package,
            timeout=args.timeout,
            device_id=args.device,
            strategy=args.strategy
        )
    elif args.mode == "pure_llm":
        return run_pure_llm_test(
            package_name=args.package,
            timeout=args.timeout,
            device_id=args.device
        )
    elif args.mode == "multimode":
        return run_multimode_test(
            package_name=args.package,
            timeout=args.timeout,
            device_id=args.device,
            llm_probability=args.llm_probability
        )
    else:
        # No mode specified - interactive
        return interactive_mode()


if __name__ == "__main__":
    try:
        results = main()
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
