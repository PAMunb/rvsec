#!/usr/bin/env python3
"""
Test vLLM with Hermes parser on CryptoApp
Validates native tool calling implementation
"""

import json
import time
from datetime import datetime
from pathlib import Path

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.agent_factory import AgentFactory


def test_vllm_hermes_cryptoapp():
    """Test vLLM with Hermes parser using CryptoApp in llm_only mode."""

    print("="*80)
    print("🧪 Testing vLLM with Hermes Parser - CryptoApp (LLM Only Mode)")
    print("="*80)

    # Configuration
    package_name = "br.unb.cic.cryptoapp"
    device_id = "emulator-5554"

    # Create config for llm_only mode to test tool calling
    config = RVAgentConfig(
        package_name=package_name,
        device_id=device_id,
        agent_mode="llm_only",  # Test LLM with tool calling
        strategy="dfs",
        max_iterations=5,  # Short test
        llm_timeout=60,
        # vLLM configuration (port 8000 with XML format)
        llm_base_url="http://localhost:8000/v1",
        llm_model="./models/qwen3-vl-4b-fp8",
        prompt_version="v13",  # Use v13 with XML <tool_call> format
    )

    print(f"\n📱 Package: {package_name}")
    print(f"🔧 Mode: {config.get_agent_mode()}")
    print(f"📊 Strategy: {config.strategy}")
    print(f"🔄 Max iterations: {config.max_iterations}")
    print(f"⏱️  LLM timeout: {config.llm_timeout}s")

    # Create agent
    print("\n🏗️  Creating agent...")
    agent = AgentFactory.create_agent(config)
    print(f"✅ Agent created: {type(agent)}")
    print(f"✅ LLM Client: {type(agent.llm_client)}")
    print(f"✅ Base URL: {agent.llm_client.base_url}")
    print(f"✅ Model: {agent.llm_client.model_name}")
    print(f"✅ Mode: JSON parser (Phase 2)")

    # Execute agent
    print("\n🚀 Starting execution...")
    start_time = time.time()

    try:
        results = agent.run()
        execution_time = time.time() - start_time

        print("\n" + "="*80)
        print("📊 EXECUTION RESULTS")
        print("="*80)

        # Basic metrics
        print(f"\n⏱️  Execution time: {execution_time:.2f}s")
        print(f"🔄 Iterations: {results.get('iterations', 0)}")
        print(f"🎯 Status: {results.get('status', 'unknown')}")

        # State exploration
        print(f"\n🗺️  Unique states: {results.get('unique_states', 0)}")
        print(f"🔀 Transitions: {results.get('total_transitions', 0)}")

        # Action metrics
        print(f"\n🎬 Total actions: {results.get('total_actions', 0)}")
        print(f"🤖 LLM actions: {results.get('llm_executed', 0)}")
        print(f"⚙️  Algorithm actions: {results.get('algorithm_chosen', 0)}")

        # LLM metrics
        print(f"\n💬 LLM tokens (input): {results.get('llm_tokens_input', 0)}")
        print(f"💬 LLM tokens (output): {results.get('llm_tokens_output', 0)}")
        print(f"⏱️  LLM time: {results.get('llm_time_ms', 0):.1f}ms")

        # Recovery actions
        print(f"\n🔄 LLM fallback: {results.get('llm_fallback', 0)}")
        print(f"⬅️  Forced back: {results.get('forced_back', 0)}")
        print(f"🚑 Recovery actions: {results.get('recovery_actions', 0)}")

        # Memory stats
        if 'memory_stats' in results:
            mem_stats = results['memory_stats']

            if 'ui_coverage' in mem_stats:
                ui_cov = mem_stats['ui_coverage']
                print(f"\n📈 UI Coverage:")
                print(f"  - Unique elements: {ui_cov.get('total_unique_elements', 0)}")
                print(f"  - Total interactions: {ui_cov.get('total_interactions', 0)}")
                print(f"  - Avg interactions/element: {ui_cov.get('average_interactions_per_element', 0):.2f}")
                print(f"  - Total screens: {ui_cov.get('total_screens', 0)}")

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"vllm_hermes_cryptoapp_results_{timestamp}.json"

        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\n💾 Results saved to: {output_file}")

        # Validation
        print("\n" + "="*80)
        print("✅ VALIDATION")
        print("="*80)

        # Check if we got LLM actions (means tool calling worked)
        llm_actions = results.get('llm_executed', 0)
        if llm_actions > 0:
            print(f"✅ LLM tool calling WORKING: {llm_actions} actions executed")
        else:
            print(f"⚠️  No LLM actions executed (expected in llm_only mode)")

        # Check for token usage (confirms LLM was called)
        tokens_in = results.get('llm_tokens_input', 0)
        tokens_out = results.get('llm_tokens_output', 0)
        if tokens_in > 0 or tokens_out > 0:
            print(f"✅ LLM invoked: {tokens_in} input tokens, {tokens_out} output tokens")
        else:
            print(f"⚠️  No token usage recorded")

        # Check execution completed
        if results.get('status') == 'completed':
            print(f"✅ Execution completed successfully")
        else:
            print(f"⚠️  Status: {results.get('status', 'unknown')}")

        return True

    except Exception as e:
        execution_time = time.time() - start_time
        print(f"\n❌ Execution failed after {execution_time:.2f}s")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_vllm_hermes_cryptoapp()
    exit(0 if success else 1)
