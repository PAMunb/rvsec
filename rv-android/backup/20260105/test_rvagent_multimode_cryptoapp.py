#!/usr/bin/env python3
"""
Teste RVAgent - Multimode (LLM + RVAgent Hybrid)

Configuração:
- Estratégia: rvagent (coverage-optimized DFS com successor tracking)
- Modo: multimode (70% LLM, 30% RVAgent)
- LLM: qwen3-vl:4b (Ollama)
- App: CryptoApp
- Duração: 180s (3 minutos)
- Objetivo: Validar integração LLM + RVAgent

Métricas Coletadas:
- Distribuição LLM vs Algorithm
- Estados descobertos
- Ações executadas
- UI coverage
- MOP coverage
- Plateau detection
- Successor tracking
- LLM metrics (tokens, latência)
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


def run_rvagent_multimode_test() -> Dict[str, Any]:
    """Run RVAgent in multimode (LLM + Algorithm hybrid)."""

    package_name = "br.unb.cic.cryptoapp"

    logger.warning("="*80)
    logger.warning("RVAGENT MULTIMODE TEST (LLM + RVAGENT)")
    logger.warning("="*80)
    logger.warning(f"Package: {package_name}")
    logger.warning("Mode: multimode (70% LLM, 30% RVAgent)")
    logger.warning("Strategy: rvagent (coverage-optimized DFS)")
    logger.warning("LLM: Qwen3-VL-4B-FP8 (HuggingFace Transformers Direct)")
    logger.warning("Duration: 180s (3 minutes)")
    logger.warning("")
    logger.warning("Hybrid Exploration:")
    logger.warning("  LLM Path (70%):")
    logger.warning("    ✓ Vision-guided exploration")
    logger.warning("    ✓ Intelligent action selection")
    logger.warning("    ✓ Fallback to RVAgent on errors")
    logger.warning("")
    logger.warning("  RVAgent Path (30%):")
    logger.warning("    ✓ Successor tracking (combobox fix)")
    logger.warning("    ✓ MOP prioritization")
    logger.warning("    ✓ Plateau detection")
    logger.warning("="*80)

    # Create config for multimode
    config = RVAgentConfig(
        package_name=package_name,
        agent_mode="multimode",  # LLM + Algorithm
        llm_probability=0.7,  # 70% LLM, 30% Algorithm
        strategy="rvagent",  # NEW: RVAgent strategy
        llm_provider="hf_direct",  # HuggingFace Transformers Direct
        llm_model="./models/qwen3-vl-4b-fp8",
        llm_temperature=0.2,
        llm_top_p=0.8,
        llm_top_k=50,
        prompt_version="v13",
        plateau_window=10,
        max_input_variations=3,
        max_iterations=200,
        timeout=180,  # 3 minutes
        device_id="emulator-5554",
        debug_mode=False,
        # Fallback settings
        auto_fallback_on_timeout=True,
        auto_fallback_on_error=True,
        llm_max_retries=2
    )

    start_time = time.time()

    try:
        # Create and run agent
        logger.info("Creating RVAgent in multimode...")
        agent = AgentFactory.create_agent(config)

        logger.info("Starting multimode execution...")
        logger.warning("⚡ Agent will route between LLM and RVAgent")
        logger.warning("🎯 Goal: Combine LLM intelligence with RVAgent coverage")

        results = agent.run()

        execution_time = time.time() - start_time

        # Extract RVAgent-specific metrics
        strategy_stats = agent.strategy.get_statistics()

        # Collect comprehensive metrics
        metrics = {
            "test_info": {
                "package_name": package_name,
                "mode": "multimode",
                "strategy": "rvagent",
                "llm_provider": "hf_direct",
                "llm_model": "qwen3-vl-4b-fp8",
                "llm_probability": 0.7,
                "duration_s": 180,
                "execution_time_s": round(execution_time, 2),
                "timestamp": datetime.now().isoformat()
            },

            # Core execution metrics
            "execution": {
                "iterations": results.get("iterations", 0),
                "actions_executed": results.get("actions_executed", 0),
                "llm_executed": results.get("llm_executed", 0),
                "algorithm_chosen": results.get("algorithm_chosen", 0),
                "llm_fallback": results.get("llm_fallback", 0),
                "forced_back": results.get("forced_back", 0)
            },

            # Decision distribution
            "distribution": {
                "llm_percentage": (
                    results.get("llm_executed", 0) / results.get("iterations", 1) * 100
                    if results.get("iterations", 0) > 0 else 0
                ),
                "algorithm_percentage": (
                    results.get("algorithm_chosen", 0) / results.get("iterations", 1) * 100
                    if results.get("iterations", 0) > 0 else 0
                ),
                "fallback_rate": (
                    results.get("llm_fallback", 0) / results.get("llm_executed", 1) * 100
                    if results.get("llm_executed", 0) > 0 else 0
                )
            },

            # LLM metrics
            "llm": {
                "tokens_input": results.get("llm_tokens_input", 0),
                "tokens_output": results.get("llm_tokens_output", 0),
                "time_ms": results.get("llm_time_ms", 0),
                "avg_latency_ms": (
                    results.get("llm_time_ms", 0) / results.get("llm_executed", 1)
                    if results.get("llm_executed", 0) > 0 else 0
                ),
                "tokens_per_second": (
                    (results.get("llm_tokens_input", 0) + results.get("llm_tokens_output", 0)) /
                    (results.get("llm_time_ms", 1) / 1000)
                    if results.get("llm_time_ms", 0) > 0 else 0
                )
            },

            # RVAgent strategy metrics
            "rvagent_strategy": {
                "depth": strategy_stats.get("depth", 0),
                "states_visited": strategy_stats.get("states_visited", 0),
                "stack_size": strategy_stats.get("stack_size", 0)
            },

            # Coverage metrics
            "coverage": strategy_stats.get("coverage", {}),

            # Plateau detection
            "plateau": strategy_stats.get("plateau", {}),

            # Successor tracking
            "successor_tracking": strategy_stats.get("successor_tracking", {}),

            # Input generation
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
        logger.warning("RVAGENT MULTIMODE TEST - RESULTS")
        logger.warning("="*80)
        logger.warning(f"Execution Time: {execution_time:.2f}s")
        logger.warning(f"Iterations: {metrics['execution']['iterations']}")
        logger.warning(f"Actions Executed: {metrics['execution']['actions_executed']}")
        logger.warning("")

        logger.warning("--- Decision Distribution ---")
        logger.warning(f"LLM Executed: {metrics['execution']['llm_executed']} ({metrics['distribution']['llm_percentage']:.1f}%)")
        logger.warning(f"Algorithm Chosen: {metrics['execution']['algorithm_chosen']} ({metrics['distribution']['algorithm_percentage']:.1f}%)")
        logger.warning(f"LLM Fallback: {metrics['execution']['llm_fallback']} ({metrics['distribution']['fallback_rate']:.1f}%)")
        logger.warning("")

        logger.warning("--- LLM Performance ---")
        logger.warning(f"Input Tokens: {metrics['llm']['tokens_input']}")
        logger.warning(f"Output Tokens: {metrics['llm']['tokens_output']}")
        logger.warning(f"Total Time: {metrics['llm']['time_ms']:.0f}ms")
        logger.warning(f"Avg Latency: {metrics['llm']['avg_latency_ms']:.0f}ms/call")
        logger.warning(f"Tokens/sec: {metrics['llm']['tokens_per_second']:.1f}")
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
        logger.warning("")

        logger.warning("--- Successor Tracking ---")
        successor = metrics["successor_tracking"]
        logger.warning(f"Successors Tracked: {successor.get('total_successors', 0)}")
        logger.warning(f"Incomplete Successors: {successor.get('incomplete_successors', 0)}")
        logger.warning(f"Actions Re-enabled: {successor.get('actions_re_enabled', 0)}")
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
    logger.info("Starting RVAgent Multimode Test...")

    result = run_rvagent_multimode_test()

    # Save results
    output_file = "test_rvagent_multimode_cryptoapp_result.json"
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
        llm_pct = result.get("distribution", {}).get("llm_percentage", 0)
        alg_pct = result.get("distribution", {}).get("algorithm_percentage", 0)
        actions_re_enabled = result.get("successor_tracking", {}).get("actions_re_enabled", 0)
        mop_reached = result.get("coverage", {}).get("mop_methods_reached", 0)

        logger.warning(f"\n🎯 Key Indicators:")
        logger.warning(f"  LLM: {llm_pct:.1f}% | Algorithm: {alg_pct:.1f}%")
        logger.warning(f"  Actions Re-enabled: {actions_re_enabled}")
        logger.warning(f"  MOP Methods Reached: {mop_reached}")

        if abs(llm_pct - 70) < 15:  # Within 15% of target
            logger.warning("  ✓ Good LLM/Algorithm distribution")
        if actions_re_enabled > 0:
            logger.warning(f"  ✓ Successor tracking working")
        if mop_reached > 0:
            logger.warning(f"  ✓ MOP methods discovered")

    return 0


if __name__ == "__main__":
    sys.exit(main())
