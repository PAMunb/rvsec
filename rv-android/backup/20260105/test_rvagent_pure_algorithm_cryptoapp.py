#!/usr/bin/env python3
"""
Teste RVAgent - Pure Algorithm Mode (Sem LLM)

Configuração:
- Estratégia: rvagent (coverage-optimized DFS com successor tracking)
- Modo: pure_algorithm (sem LLM)
- App: CryptoApp
- Duração: 180s (3 minutos)
- Objetivo: Validar novo algoritmo RVAgent isoladamente

Métricas Coletadas:
- Estados descobertos
- Ações executadas
- UI coverage (elementos testados vs descobertos)
- MOP coverage (métodos únicos alcançados)
- Plateau detection (iterações sem progresso)
- Successor tracking (ações re-habilitadas)
- Input variations (campos testados com múltiplos valores)
"""

import json
import logging
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent / "modules" / "rv-agent" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "modules" / "rv-android-core" / "src"))

from rv_agent.core.agent_factory import AgentFactory
from rv_agent.config.agent_config import RVAgentConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_rvagent_pure_algorithm_test() -> Dict[str, Any]:
    """Run RVAgent in pure algorithm mode (no LLM)."""

    package_name = "br.unb.cic.cryptoapp"

    logger.warning("="*80)
    logger.warning("RVAGENT PURE ALGORITHM TEST")
    logger.warning("="*80)
    logger.warning(f"Package: {package_name}")
    logger.warning("Mode: pure_algorithm (NO LLM)")
    logger.warning("Strategy: rvagent (coverage-optimized DFS)")
    logger.warning("Duration: 180s (3 minutes)")
    logger.warning("")
    logger.warning("RVAgent Features:")
    logger.warning("  ✓ Successor Tracking (solves combobox problem)")
    logger.warning("  ✓ Plateau Detection (auto termination)")
    logger.warning("  ✓ MOP Prioritization ([DM] > [M] > UI)")
    logger.warning("  ✓ Input Variations (2-3 values per field)")
    logger.warning("  ✓ Coverage Metrics (UI + MOP unified)")
    logger.warning("="*80)

    # Create config for pure algorithm mode
    config = RVAgentConfig(
        package_name=package_name,
        agent_mode="pure_algorithm",  # NO LLM
        strategy="rvagent",  # NEW: RVAgent strategy (default)
        plateau_window=10,  # Plateau detection: 10 iterations without progress
        max_input_variations=3,  # Test 3 values per input field
        max_iterations=200,  # High limit (plateau will stop before this)
        timeout=180,  # 3 minutes
        device_id="emulator-5554",
        debug_mode=False
    )

    start_time = time.time()

    try:
        # Create and run agent
        logger.info("Creating RVAgent...")
        agent = AgentFactory.create_agent(config)

        logger.info("Starting pure algorithm execution...")
        logger.warning("⚡ RVAgent will explore systematically without LLM")
        logger.warning("🎯 Goal: 100% coverage with successor tracking")

        results = agent.run()

        execution_time = time.time() - start_time

        # Extract RVAgent-specific metrics
        strategy_stats = agent.strategy.get_statistics()

        # Collect comprehensive metrics
        metrics = {
            "test_info": {
                "package_name": package_name,
                "mode": "pure_algorithm",
                "strategy": "rvagent",
                "duration_s": 180,
                "execution_time_s": round(execution_time, 2),
                "timestamp": datetime.now().isoformat()
            },

            # Core execution metrics
            "execution": {
                "iterations": results.get("iterations", 0),
                "actions_executed": results.get("actions_executed", 0),
                "algorithm_chosen": results.get("algorithm_chosen", 0),
                "llm_executed": results.get("llm_executed", 0),  # Should be 0
                "forced_back": results.get("forced_back", 0)
            },

            # RVAgent strategy metrics
            "rvagent_strategy": {
                "depth": strategy_stats.get("depth", 0),
                "states_visited": strategy_stats.get("states_visited", 0),
                "stack_size": strategy_stats.get("stack_size", 0)
            },

            # Coverage metrics (from CoverageMetrics)
            "coverage": strategy_stats.get("coverage", {}),

            # Plateau detection metrics
            "plateau": strategy_stats.get("plateau", {}),

            # Successor tracking metrics
            "successor_tracking": strategy_stats.get("successor_tracking", {}),

            # Input generation metrics
            "input_generation": strategy_stats.get("input_generation", {}),

            # Memory metrics
            "memory": {
                "ui_coverage": results.get("ui_coverage", {}),
                "dynamic_graph": results.get("dynamic_graph", {})
            }
        }

        # Display results
        logger.warning("")
        logger.warning("="*80)
        logger.warning("RVAGENT PURE ALGORITHM TEST - RESULTS")
        logger.warning("="*80)
        logger.warning(f"Execution Time: {execution_time:.2f}s")
        logger.warning(f"Iterations: {metrics['execution']['iterations']}")
        logger.warning(f"Actions Executed: {metrics['execution']['actions_executed']}")
        logger.warning("")

        logger.warning("--- RVAgent Strategy ---")
        logger.warning(f"States Visited: {metrics['rvagent_strategy']['states_visited']}")
        logger.warning(f"Max Depth: {metrics['rvagent_strategy']['depth']}")
        logger.warning(f"Stack Size: {metrics['rvagent_strategy']['stack_size']}")
        logger.warning("")

        logger.warning("--- Coverage Metrics ---")
        coverage = metrics["coverage"]
        logger.warning(f"States Discovered: {coverage.get('states_discovered', 0)}")
        logger.warning(f"Graph Coverage: {coverage.get('graph_overall_coverage', 0):.1%}")
        logger.warning(f"Actions Executed: {coverage.get('total_actions_executed', 0)}")
        logger.warning(f"UI Elements Tested: {coverage.get('ui_elements_tested', 0)}/{coverage.get('ui_elements_discovered', 0)}")
        logger.warning(f"UI Coverage Rate: {coverage.get('ui_coverage_rate', 0):.1%}")
        logger.warning(f"MOP Methods Reached: {coverage.get('mop_methods_reached', 0)}")
        logger.warning(f"Transitions: {coverage.get('total_transitions', 0)}")
        logger.warning("")

        logger.warning("--- Plateau Detection ---")
        plateau = metrics["plateau"]
        logger.warning(f"Plateau Reached: {plateau.get('plateau_reached', False)}")
        logger.warning(f"Total Iterations: {plateau.get('total_iterations', 0)}")
        logger.warning(f"States in Window: {plateau.get('states_in_window', 0)}")
        logger.warning(f"MOP in Window: {plateau.get('mop_in_window', 0)}")
        logger.warning(f"Total States Discovered: {plateau.get('total_states_discovered', 0)}")
        logger.warning(f"Total MOP Executed: {plateau.get('total_mop_methods_executed', 0)}")
        logger.warning("")

        logger.warning("--- Successor Tracking ---")
        successor = metrics["successor_tracking"]
        logger.warning(f"Successors Tracked: {successor.get('total_successors', 0)}")
        logger.warning(f"Incomplete Successors: {successor.get('incomplete_successors', 0)}")
        logger.warning(f"Actions Re-enabled: {successor.get('actions_re_enabled', 0)}")
        logger.warning("")

        logger.warning("--- Input Generation ---")
        input_gen = metrics["input_generation"]
        logger.warning(f"Elements Tested: {input_gen.get('total_elements_tested', 0)}")
        logger.warning(f"Values Tested: {input_gen.get('total_values_tested', 0)}")
        logger.warning(f"Exhausted Elements: {input_gen.get('exhausted_elements', 0)}")
        logger.warning("="*80)

        return metrics

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return {
            "error": str(e),
            "execution_time_s": time.time() - start_time
        }


def main():
    """Main entry point."""
    logger.info("Starting RVAgent Pure Algorithm Test...")

    result = run_rvagent_pure_algorithm_test()

    # Save results
    output_file = "test_rvagent_pure_algorithm_cryptoapp_result.json"
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)

    logger.warning(f"\n📊 Results saved to: {output_file}")

    # Check for errors
    if "error" in result:
        logger.error("❌ Test completed with errors")
        sys.exit(1)
    else:
        logger.warning("✅ Test completed successfully!")

        # Key success indicators
        plateau_reached = result.get("plateau", {}).get("plateau_reached", False)
        states_visited = result.get("rvagent_strategy", {}).get("states_visited", 0)
        actions_re_enabled = result.get("successor_tracking", {}).get("actions_re_enabled", 0)

        logger.warning(f"\n🎯 Key Indicators:")
        logger.warning(f"  Plateau Reached: {plateau_reached}")
        logger.warning(f"  States Explored: {states_visited}")
        logger.warning(f"  Actions Re-enabled (Combobox Fix): {actions_re_enabled}")

        if plateau_reached:
            logger.warning("  ✓ Exploration terminated automatically (plateau detected)")
        if actions_re_enabled > 0:
            logger.warning(f"  ✓ Successor tracking working ({actions_re_enabled} actions re-enabled)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
