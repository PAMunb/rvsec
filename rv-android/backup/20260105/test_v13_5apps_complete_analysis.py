#!/usr/bin/env python3
"""
Teste completo com 5 apps - Análise profunda de todas as métricas
- Prompt V13 (corrigido)
- Modelo customizado: qwen3-vl-4b-16k (16K context, 8K output)
- Estratégia: DFS (Greedy)
- Duração: 5 minutos por app (300s)
- Métricas: Ações/tools, UI coverage, tokens LLM, tempo inferência, etc
"""

import json
import logging
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

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

# Test apps - 5 apps representativos
TEST_APPS = [
    "br.unb.cic.cryptoapp",          # Crypto app - always tested
    "com.amnesica.kryptey",           # Password manager
    "org.cryptomator.lite",           # Cloud encryption
    "com.securefilemanager.app",     # Secure file manager
    "com.rafapps.simplenotes"         # Simple notes app
]

def run_app_test(package_name: str) -> Dict[str, Any]:
    """Run test for single app with comprehensive metrics collection."""

    logger.warning("="*80)
    logger.warning(f"TESTING: {package_name}")
    logger.warning("="*80)
    logger.warning("Duration: 300s (5 minutes)")
    logger.warning("Strategy: DFS (Greedy)")
    logger.warning("Prompt: V13 (fixed)")
    logger.warning("Model: qwen3-vl-4b-16k (custom, 16K context, 8K output)")
    logger.warning("="*80)

    # Create config
    config = RVAgentConfig(
        package_name=package_name,
        agent_mode="multimode",
        strategy="greedy",  # DFS strategy
        llm_provider="ollama",
        llm_model="qwen3-vl-4b-16k:latest",  # 16K context, 8K output
        llm_temperature=0.1,
        llm_top_p=0.9,
        llm_top_k=40,
        prompt_version="v13",
        max_iterations=100,  # High limit, timeout will stop
        timeout=300,  # 5 minutes
        device_id="emulator-5554"
    )

    start_time = time.time()

    try:
        # Create and run agent
        logger.info(f"Creating RVAgent for {package_name}...")
        agent = AgentFactory.create_agent(config)

        logger.info("Starting execution...")
        results = agent.run()

        execution_time = time.time() - start_time

        # Extract comprehensive metrics
        metrics = {
            "package_name": package_name,
            "execution_time_s": execution_time,
            "timestamp": datetime.now().isoformat(),

            # Core metrics
            "iterations": results.get("iterations", 0),
            "llm_executed": results.get("llm_executed", 0),
            "algorithm_chosen": results.get("algorithm_chosen", 0),
            "llm_fallback": results.get("llm_fallback", 0),
            "actions_executed": results.get("actions_executed", 0),

            # LLM metrics
            "llm_tokens_input": results.get("llm_tokens_input", 0),
            "llm_tokens_output": results.get("llm_tokens_output", 0),
            "llm_time_ms": results.get("llm_time_ms", 0),

            # UI Coverage metrics
            "ui_elements_seen": results.get("ui_elements_seen", 0),
            "ui_elements_interacted": results.get("ui_elements_interacted", 0),
            "states_visited": results.get("states_visited", 0),

            # Calculate derived metrics
            "llm_success_rate": 0.0,
            "llm_fallback_rate": 0.0,
            "avg_tokens_per_call": 0.0,
            "avg_time_per_call_ms": 0.0,
            "ui_interaction_rate": 0.0,
            "iterations_per_minute": 0.0
        }

        # Calculate rates and averages
        llm_total = metrics["llm_executed"] + metrics["llm_fallback"]
        if llm_total > 0:
            metrics["llm_success_rate"] = (metrics["llm_executed"] / llm_total) * 100
            metrics["llm_fallback_rate"] = (metrics["llm_fallback"] / llm_total) * 100

        if metrics["llm_executed"] > 0:
            total_tokens = metrics["llm_tokens_input"] + metrics["llm_tokens_output"]
            metrics["avg_tokens_per_call"] = total_tokens / metrics["llm_executed"]
            metrics["avg_time_per_call_ms"] = metrics["llm_time_ms"] / metrics["llm_executed"]

        if metrics["ui_elements_seen"] > 0:
            metrics["ui_interaction_rate"] = (metrics["ui_elements_interacted"] / metrics["ui_elements_seen"]) * 100

        if execution_time > 0:
            metrics["iterations_per_minute"] = (metrics["iterations"] / execution_time) * 60

        logger.warning("")
        logger.warning("="*80)
        logger.warning(f"RESULTS: {package_name}")
        logger.warning("="*80)
        logger.warning(f"Iterations: {metrics['iterations']}")
        logger.warning(f"LLM executed: {metrics['llm_executed']}")
        logger.warning(f"Algorithm chosen: {metrics['algorithm_chosen']}")
        logger.warning(f"LLM fallback: {metrics['llm_fallback']}")
        logger.warning(f"Actions executed: {metrics['actions_executed']}")
        logger.warning("")
        logger.warning("LLM Metrics:")
        logger.warning(f"  Success rate: {metrics['llm_success_rate']:.1f}%")
        logger.warning(f"  Fallback rate: {metrics['llm_fallback_rate']:.1f}%")
        logger.warning(f"  Tokens input: {metrics['llm_tokens_input']}")
        logger.warning(f"  Tokens output: {metrics['llm_tokens_output']}")
        logger.warning(f"  Avg tokens/call: {metrics['avg_tokens_per_call']:.1f}")
        logger.warning(f"  Avg time/call: {metrics['avg_time_per_call_ms']:.1f}ms")
        logger.warning("")
        logger.warning("UI Coverage:")
        logger.warning(f"  Elements seen: {metrics['ui_elements_seen']}")
        logger.warning(f"  Elements interacted: {metrics['ui_elements_interacted']}")
        logger.warning(f"  Interaction rate: {metrics['ui_interaction_rate']:.1f}%")
        logger.warning(f"  States visited: {metrics['states_visited']}")
        logger.warning("")
        logger.warning(f"Performance: {metrics['iterations_per_minute']:.1f} iterations/min")
        logger.warning("="*80)
        logger.warning("")

        return metrics

    except Exception as e:
        logger.error(f"❌ Test failed for {package_name}: {e}")
        import traceback
        traceback.print_exc()

        return {
            "package_name": package_name,
            "error": str(e),
            "execution_time_s": time.time() - start_time,
            "timestamp": datetime.now().isoformat()
        }


def analyze_aggregate_metrics(all_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze aggregate metrics across all apps."""

    successful = [r for r in all_results if "error" not in r]
    failed = [r for r in all_results if "error" in r]

    if not successful:
        return {"error": "No successful tests"}

    # Aggregate metrics
    total_iterations = sum(r["iterations"] for r in successful)
    total_llm_executed = sum(r["llm_executed"] for r in successful)
    total_algorithm_chosen = sum(r["algorithm_chosen"] for r in successful)
    total_llm_fallback = sum(r["llm_fallback"] for r in successful)
    total_actions = sum(r["actions_executed"] for r in successful)

    total_tokens_in = sum(r["llm_tokens_input"] for r in successful)
    total_tokens_out = sum(r["llm_tokens_output"] for r in successful)
    total_llm_time = sum(r["llm_time_ms"] for r in successful)

    total_ui_seen = sum(r["ui_elements_seen"] for r in successful)
    total_ui_interacted = sum(r["ui_elements_interacted"] for r in successful)
    total_states = sum(r["states_visited"] for r in successful)

    total_time = sum(r["execution_time_s"] for r in successful)

    # Calculate averages
    n_apps = len(successful)
    llm_total = total_llm_executed + total_llm_fallback

    aggregate = {
        "total_apps_tested": len(all_results),
        "successful_apps": n_apps,
        "failed_apps": len(failed),

        # Totals
        "total_iterations": total_iterations,
        "total_llm_executed": total_llm_executed,
        "total_algorithm_chosen": total_algorithm_chosen,
        "total_llm_fallback": total_llm_fallback,
        "total_actions_executed": total_actions,

        # Averages per app
        "avg_iterations_per_app": total_iterations / n_apps,
        "avg_llm_executed_per_app": total_llm_executed / n_apps,
        "avg_actions_per_app": total_actions / n_apps,

        # LLM metrics
        "llm_overall_success_rate": (total_llm_executed / llm_total * 100) if llm_total > 0 else 0,
        "llm_overall_fallback_rate": (total_llm_fallback / llm_total * 100) if llm_total > 0 else 0,
        "total_tokens_input": total_tokens_in,
        "total_tokens_output": total_tokens_out,
        "avg_tokens_per_call": (total_tokens_in + total_tokens_out) / total_llm_executed if total_llm_executed > 0 else 0,
        "avg_time_per_call_ms": total_llm_time / total_llm_executed if total_llm_executed > 0 else 0,

        # UI Coverage
        "total_ui_elements_seen": total_ui_seen,
        "total_ui_elements_interacted": total_ui_interacted,
        "ui_overall_interaction_rate": (total_ui_interacted / total_ui_seen * 100) if total_ui_seen > 0 else 0,
        "total_states_visited": total_states,
        "avg_states_per_app": total_states / n_apps,

        # Performance
        "total_execution_time_s": total_time,
        "avg_iterations_per_minute": (total_iterations / total_time * 60) if total_time > 0 else 0
    }

    return aggregate


def main():
    """Run complete 5-app analysis."""

    logger.warning("="*80)
    logger.warning("COMPLETE 5-APP ANALYSIS - V13 PROMPT (FIXED)")
    logger.warning("="*80)
    logger.warning(f"Apps to test: {len(TEST_APPS)}")
    logger.warning(f"Duration per app: 300s (5 minutes)")
    logger.warning(f"Total estimated time: {len(TEST_APPS) * 5} minutes")
    logger.warning("="*80)
    logger.warning("")

    all_results = []

    # Test each app
    for i, app in enumerate(TEST_APPS, 1):
        logger.warning(f"\n{'='*80}")
        logger.warning(f"APP {i}/{len(TEST_APPS)}: {app}")
        logger.warning(f"{'='*80}\n")

        result = run_app_test(app)
        all_results.append(result)

        # Small delay between apps
        if i < len(TEST_APPS):
            logger.info("Waiting 10s before next app...")
            time.sleep(10)

    # Analyze aggregate metrics
    logger.warning("\n" + "="*80)
    logger.warning("AGGREGATE ANALYSIS")
    logger.warning("="*80 + "\n")

    aggregate = analyze_aggregate_metrics(all_results)

    logger.warning("Overall Results:")
    logger.warning(f"  Apps tested: {aggregate['total_apps_tested']}")
    logger.warning(f"  Successful: {aggregate['successful_apps']}")
    logger.warning(f"  Failed: {aggregate['failed_apps']}")
    logger.warning("")
    logger.warning("Total Metrics:")
    logger.warning(f"  Iterations: {aggregate['total_iterations']}")
    logger.warning(f"  LLM executed: {aggregate['total_llm_executed']}")
    logger.warning(f"  Algorithm chosen: {aggregate['total_algorithm_chosen']}")
    logger.warning(f"  LLM fallback: {aggregate['total_llm_fallback']}")
    logger.warning(f"  Actions executed: {aggregate['total_actions_executed']}")
    logger.warning("")
    logger.warning("LLM Performance:")
    logger.warning(f"  Overall success rate: {aggregate['llm_overall_success_rate']:.1f}%")
    logger.warning(f"  Overall fallback rate: {aggregate['llm_overall_fallback_rate']:.1f}%")
    logger.warning(f"  Total tokens input: {aggregate['total_tokens_input']}")
    logger.warning(f"  Total tokens output: {aggregate['total_tokens_output']}")
    logger.warning(f"  Avg tokens/call: {aggregate['avg_tokens_per_call']:.1f}")
    logger.warning(f"  Avg time/call: {aggregate['avg_time_per_call_ms']:.1f}ms")
    logger.warning("")
    logger.warning("UI Coverage:")
    logger.warning(f"  Total UI elements seen: {aggregate['total_ui_elements_seen']}")
    logger.warning(f"  Total UI interacted: {aggregate['total_ui_elements_interacted']}")
    logger.warning(f"  Overall interaction rate: {aggregate['ui_overall_interaction_rate']:.1f}%")
    logger.warning(f"  Total states visited: {aggregate['total_states_visited']}")
    logger.warning(f"  Avg states/app: {aggregate['avg_states_per_app']:.1f}")
    logger.warning("")
    logger.warning("Performance:")
    logger.warning(f"  Avg iterations/app: {aggregate['avg_iterations_per_app']:.1f}")
    logger.warning(f"  Avg actions/app: {aggregate['avg_actions_per_app']:.1f}")
    logger.warning(f"  Avg iterations/min: {aggregate['avg_iterations_per_minute']:.1f}")
    logger.warning("")

    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"v13_5apps_analysis_{timestamp}.json"

    output_data = {
        "test_config": {
            "prompt_version": "v13",
            "model": "qwen3-vl-4b-16k:latest",
            "context_window": "16K (16384 tokens)",
            "max_output": "8K (8192 tokens)",
            "strategy": "greedy (DFS)",
            "duration_per_app_s": 300,
            "apps": TEST_APPS
        },
        "individual_results": all_results,
        "aggregate_metrics": aggregate,
        "timestamp": timestamp
    }

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    logger.warning(f"Detailed results saved to: {output_file}")
    logger.warning("="*80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
