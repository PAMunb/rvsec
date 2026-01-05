#!/usr/bin/env python3
"""Test V13 Quick - 3 minute cryptoapp test with 2048 tokens"""

import sys
import json
import time
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent / "modules" / "rv-agent" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "modules" / "rv-android-core" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "modules" / "rv-screen-parser" / "src"))

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.agent_factory import AgentFactory


def test_quick_cryptoapp():
    """Quick 3-minute test with cryptoapp to validate 2048 token limit"""

    print("="*80)
    print("V13 QUICK TEST - 3 MINUTES")
    print("="*80)
    print("App: br.unb.cic.cryptoapp")
    print("Timeout: 180s (3 minutes)")
    print("num_predict: 2048")
    print("Prompt: v13")
    print()

    app_package = "br.unb.cic.cryptoapp"

    config = RVAgentConfig(
        package_name=app_package,
        timeout=180,  # 3 minutes
        prompt_version="v13",
        agent_mode="multimode",
        strategy="greedy",
        llm_model="qwen3-vl-4b-8k:latest",
        llm_probability=0.7,
        device_dimensions=(1080, 1920),
        optimized_dimensions=(704, 1248),
        screenshot_dir=f"/tmp/v13_quick_{app_package}",
        screenshot_rotation_limit=50
    )

    print(f"Creating agent with V13 (2048 tokens)...")
    agent = AgentFactory.create_agent(config=config)

    print(f"Starting exploration...")
    start_time = time.time()

    results = agent.run()

    execution_time = time.time() - start_time

    # Calculate metrics
    total_actions = results.get('total_actions', 0)
    llm_decisions = results.get('llm_decisions', 0)
    algorithm_decisions = results.get('algorithm_decisions', 0)

    tokens_input = results.get('tokens_input', 0)
    tokens_output = results.get('tokens_output', 0)
    tokens_total = tokens_input + tokens_output

    llm_time_total = results.get('llm_time_ms', 0)

    # Calculate per-action and per-call metrics
    tokens_per_action = tokens_total / total_actions if total_actions > 0 else 0
    tokens_per_call = tokens_total / llm_decisions if llm_decisions > 0 else 0
    avg_time_per_call = llm_time_total / llm_decisions if llm_decisions > 0 else 0

    # Max token output per call
    max_output_tokens = tokens_output / llm_decisions if llm_decisions > 0 else 0

    summary = {
        "app_package": app_package,
        "total_actions": total_actions,
        "llm_decisions": llm_decisions,
        "algorithm_decisions": algorithm_decisions,
        "tokens_input": tokens_input,
        "tokens_output": tokens_output,
        "tokens_total": tokens_total,
        "tokens_per_action": round(tokens_per_action, 1),
        "tokens_per_call": round(tokens_per_call, 1),
        "avg_output_per_call": round(max_output_tokens, 1),
        "avg_time_per_call_ms": round(avg_time_per_call, 3),
        "execution_time_s": round(execution_time, 2),
        "validation": {
            "output_under_2048": max_output_tokens < 2048,
            "tokens_reasonable": tokens_per_action < 5000,
            "no_explosion": tokens_per_call < 10000
        }
    }

    summary["all_checks_passed"] = all(summary["validation"].values())

    # Save results
    output_file = Path("v13_quick_result.json")
    with open(output_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    print(f"Total actions: {total_actions}")
    print(f"LLM decisions: {llm_decisions}")
    print(f"Algorithm decisions: {algorithm_decisions}")
    print(f"Tokens: {tokens_input} input / {tokens_output} output = {tokens_total} total")
    print(f"Tokens per action: {tokens_per_action:.1f}")
    print(f"Tokens per call: {tokens_per_call:.1f}")
    print(f"Avg output per call: {max_output_tokens:.1f} (limit: 2048)")
    print(f"Avg time per call: {avg_time_per_call:.1f}ms")
    print(f"Execution time: {execution_time:.2f}s")
    print()
    print("VALIDATION:")
    for check, passed in summary["validation"].items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check}")
    print()
    print(f"All checks passed: {'✅ YES' if summary['all_checks_passed'] else '❌ NO'}")
    print()
    print(f"Results saved to: {output_file}")
    print("="*80)


if __name__ == "__main__":
    test_quick_cryptoapp()
