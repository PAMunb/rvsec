#!/usr/bin/env python3
"""
Test coordinate conversion with CryptoApp.

This test validates that LLM coordinates (in optimized space 704x1248)
are correctly converted to device space (1080x1920) before execution.
"""

import logging
from rv_agent.core.agent_factory import AgentFactory
from rv_agent.config.agent_config import RVAgentConfig

# Setup logging to see coordinate conversion messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Run coordinate conversion test with CryptoApp."""

    # Configure agent for multimode (to test both LLM and algorithm paths)
    # ⚠️ CRITICAL: STOPPING CRITERIA IS *ONLY* TIMEOUT! NOT max_iterations!
    # ⚠️ max_iterations MUST BE SET TO 200 (maximum allowed by Pydantic)
    # ⚠️ The agent will run until timeout - max_iterations will never be reached
    # ⚠️ DO NOT CHANGE THIS! DO NOT DELETE THIS COMMENT!
    config = RVAgentConfig(
        package_name="br.unb.cic.cryptoapp",
        agent_mode="multimode",
        strategy="dfs",
        timeout=60,  # ⚠️ THIS IS THE ONLY STOPPING CRITERIA!
        llm_probability=0.7,  # 70% LLM, 30% algorithm
        max_iterations=200  # ⚠️ MUST BE 200 (max allowed) - will NEVER be reached, only timeout matters!
    )

    print("=" * 80)
    print("COORDINATE CONVERSION TEST - CryptoApp")
    print("=" * 80)
    print(f"Package: {config.package_name}")
    print(f"Mode: {config.agent_mode}")
    print(f"Strategy: {config.strategy}")
    print(f"Timeout: {config.timeout}s (ONLY STOPPING CRITERIA!)")
    print(f"LLM Probability: {config.llm_probability}")
    print(f"Max Iterations: {config.max_iterations} (will never be reached)")
    print("=" * 80)
    print()
    print("🔍 Watch for these log messages:")
    print("  - 'ToolExecutor initialized: device=(1080, 1920), optimized=(704, 1248)'")
    print("  - 'Executing action from llm, convert_coords=True'")
    print("  - 'Executing action from algorithm, convert_coords=False'")
    print("  - '🔄 Coordinate conversion: (X, Y) OPTIMIZED → (X', Y') DEVICE'")
    print("=" * 80)
    print()

    # Create agent
    factory = AgentFactory()
    agent = factory.create_agent(config)

    # Run test
    try:
        results = agent.run()

        print()
        print("=" * 80)
        print("TEST RESULTS")
        print("=" * 80)
        print(f"Status: {results.get('status')}")
        print(f"Iterations: {results.get('iterations')}")
        print(f"Execution time: {results.get('execution_time_s', 0):.1f}s")
        print(f"Unique states: {results.get('unique_states')}")
        print(f"Total transitions: {results.get('total_transitions')}")
        print(f"LLM decisions: {results.get('llm_decisions', 0)}")
        print(f"Algorithm decisions: {results.get('algorithm_decisions', 0)}")
        print("=" * 80)

        return results

    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        return {"status": "interrupted"}
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    main()
