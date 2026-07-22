#!/usr/bin/env python3
"""
Test RVAgent with HuggingFace Transformers direct backend on CryptoApp.

Uses apply_chat_template(tools=...) for native tool calling support.
"""

import json
import logging
from datetime import datetime
from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.agent_factory import AgentFactory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_hf_direct_cryptoapp():
    """Test HF Direct backend with CryptoApp."""

    print("=" * 80)
    print("🧪 Testing RVAgent with HuggingFace Transformers Direct")
    print("=" * 80)

    # Configuration
    config = RVAgentConfig(
        package_name="br.unb.cic.cryptoapp",
        device_id="emulator-5554",
        agent_mode="llm_only",
        strategy="dfs",
        llm_provider="hf_direct",  # ← Use HF direct instead of vLLM
        llm_model="./models/qwen3-vl-4b-fp8",
        prompt_version="v13",
        timeout=180,  # 3 minutes timeout
        llm_temperature=0.2,
        llm_top_p=0.8,
        llm_top_k=50,
        results_dir="./hf_direct_cryptoapp_results"
    )

    print(f"\n📋 Configuration:")
    print(f"   Package: {config.package_name}")
    print(f"   Device: {config.device_id}")
    print(f"   Mode: {config.agent_mode}")
    print(f"   LLM Provider: {config.llm_provider}")
    print(f"   Model: {config.llm_model}")
    print(f"   Prompt: {config.prompt_version}")
    print(f"   Timeout: {config.timeout}s")

    # Create agent using factory
    print("\n🤖 Creating RVAgent with factory...")
    factory = AgentFactory()
    agent = factory.create_agent(config)

    # Run exploration
    print("\n🚀 Starting exploration...")
    try:
        results = agent.run()  # ← Correct method
    finally:
        # Clean up GPU memory
        print("\n🧹 Cleaning up GPU memory...")
        if hasattr(agent, 'llm_client') and agent.llm_client:
            agent.llm_client.cleanup()

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"hf_direct_cryptoapp_results_{timestamp}.json"

    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 80)
    print("📊 RESULTS SUMMARY:")
    print("=" * 80)
    print(f"Total iterations: {results.get('total_iterations', 0)}")
    print(f"Screens discovered: {results.get('screens_discovered', 0)}")
    print(f"Actions executed: {results.get('actions_executed', 0)}")
    print(f"LLM calls: {results.get('llm_calls', 0)}")
    print(f"Success: {results.get('success', False)}")
    print(f"\nResults saved to: {results_file}")
    print("=" * 80)

    return results


if __name__ == "__main__":
    test_hf_direct_cryptoapp()
