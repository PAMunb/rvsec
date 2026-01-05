#!/usr/bin/env python3
"""Quick test to verify facade is working."""

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.agent_factory import AgentFactory

# Create minimal config
config = RVAgentConfig(
    package_name="br.unb.cic.cryptoapp",
    timeout=60,  # Minimum is 60 seconds
    prompt_version="v10",
    agent_mode="pure_algorithm",  # Faster - no LLM
    strategy="greedy",
    device_dimensions=(1080, 1920),
    optimized_dimensions=(704, 1248),
    screenshot_dir="/tmp/facade_test"
)

print("Creating agent...")
agent = AgentFactory.create_agent(config=config)

print("Running agent (60s - pure algorithm, no LLM)...")
results = agent.run()

print("\n" + "="*60)
print("FACADE TEST RESULTS")
print("="*60)

# Check if memory_stats is in results
if "memory_stats" in results:
    print("✅ memory_stats found in results!")
    memory_stats = results["memory_stats"]

    # Check each component
    ui_coverage = memory_stats.get("ui_coverage", {})
    short_term = memory_stats.get("short_term", {})
    long_term = memory_stats.get("long_term", {})
    dynamic_graph = memory_stats.get("dynamic_graph", {})

    print(f"\n📊 UI Coverage:")
    print(f"   - total_unique_elements: {ui_coverage.get('total_unique_elements', 0)}")
    print(f"   - total_interactions: {ui_coverage.get('total_interactions', 0)}")

    print(f"\n🧠 Short Term Memory:")
    print(f"   - iteration_count: {short_term.get('iteration_count', 0)}")

    print(f"\n📚 Long Term Memory:")
    print(f"   - total_states: {long_term.get('total_states', 0)}")

    print(f"\n🗺️  Dynamic Graph:")
    print(f"   - total_states: {dynamic_graph.get('total_states', 0)}")
    print(f"   - total_transitions: {dynamic_graph.get('total_transitions', 0)}")

    # Validation
    print("\n" + "="*60)
    success = (
        ui_coverage.get('total_unique_elements', 0) > 0 and
        short_term.get('iteration_count', 0) > 0 and
        long_term.get('total_states', 0) > 0 and
        dynamic_graph.get('total_states', 0) > 0
    )

    if success:
        print("✅ VALIDATION PASSED - All memory stats > 0")
    else:
        print("❌ VALIDATION FAILED - Some stats are 0")
        if ui_coverage.get('total_unique_elements', 0) == 0:
            print("   ❌ UI coverage = 0")
        if short_term.get('iteration_count', 0) == 0:
            print("   ❌ Short term = 0")
        if long_term.get('total_states', 0) == 0:
            print("   ❌ Long term = 0")
        if dynamic_graph.get('total_states', 0) == 0:
            print("   ❌ Dynamic graph = 0")
    print("="*60)
else:
    print("❌ memory_stats NOT found in results!")
    print(f"Available keys: {list(results.keys())}")
