#!/usr/bin/env python3
"""
Quick test to debug transition tracking issue.
"""
import time
import json
from pathlib import Path
from rv_agent.core.rv_agent import RVAgent
from rv_agent.config.agent_config import RVAgentConfig
from rv_android_core.domain.static import StaticAnalysisData

# Test configuration
print("=" * 80)
print("  TRANSITION DEBUGGING TEST - CryptoApp Only")
print("=" * 80)
print(f"\nTimeout: 60s")
print(f"Model: qwen3-vl:4b")
print()

# Configure agent
config = RVAgentConfig(
    package_name="br.unb.cic.cryptoapp",
    timeout=60,  # 1 minute
    device_id="emulator-5554",
    llm_model="qwen3-vl:4b",
    llm_provider="ollama",
    llm_temperature=0.0,
    strategy="dfs"
)

# Create agent
agent = RVAgent(config=config)

# Run exploration
print("Starting exploration...\n")
start_time = time.time()

try:
    result = agent.run()

    elapsed = time.time() - start_time

    print("\n" + "=" * 80)
    print("  TEST RESULTS")
    print("=" * 80)
    print(f"\nExecution Time: {elapsed:.1f}s")
    print(f"Iterations: {result['iterations']}")
    print(f"Unique States: {result['unique_states']}")
    print(f"Transitions: {result['total_transitions']}")  # KEY METRIC!
    print(f"\nStatus: {result['status']}")

    # Check if transitions were tracked
    if result['total_transitions'] > 0:
        print("\n✅ SUCCESS: Transitions are being tracked!")
    else:
        print("\n❌ BUG STILL PRESENT: No transitions recorded despite state changes")

    # Save results
    result_file = Path("test_transition_debug_result.json")
    with open(result_file, 'w') as f:
        json.dump({
            "app": "CryptoApp",
            "package": "br.unb.cic.cryptoapp",
            "model": "qwen3-vl:4b",
            "timeout": 60,
            "result": result,
            "execution_time": elapsed
        }, f, indent=2)

    print(f"\nResults saved to: {result_file}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
