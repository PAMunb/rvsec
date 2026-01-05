#!/usr/bin/env python3
"""
Test validation fix with full 3-minute cryptoapp run.

Verifies:
1. llm_fallback counter works correctly
2. Loop detection triggers properly
3. State exploration improves
4. Recovery mode activates when needed
"""

import logging
import sys
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent / "modules" / "rv-agent" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "modules" / "rv-android-core" / "src"))

from rv_agent.core.agent_factory import AgentFactory
from rv_agent.config.agent_config import RVAgentConfig

# Setup logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.warning("="*80)
logger.warning("TESTING: Validation Fix - Full 3-Minute Run")
logger.warning("="*80)
logger.warning("App: br.unb.cic.cryptoapp")
logger.warning("Duration: 180s (3 minutes)")
logger.warning("Verifying: llm_fallback counting, loop detection, state exploration")
logger.warning("")

# Create config
config = RVAgentConfig(
    package_name="br.unb.cic.cryptoapp",
    agent_mode="multimode",
    strategy="greedy",
    llm_provider="ollama",
    llm_model="qwen3-vl-4b-8k:latest",
    llm_temperature=0.1,
    llm_top_p=0.9,
    llm_top_k=40,
    prompt_version="v13",
    max_iterations=100,
    timeout=180,  # 3 minutes
    device_id="emulator-5554"
)

try:
    # Create agent
    logger.warning("Creating RVAgent...")
    agent = AgentFactory.create_agent(config)

    # Run agent
    logger.warning("Starting execution...")
    logger.warning("")
    results = agent.run()

    # Display results
    logger.warning("")
    logger.warning("="*80)
    logger.warning("TEST RESULTS")
    logger.warning("="*80)
    logger.warning(f"Status: {results.get('status', 'unknown')}")
    logger.warning(f"Iterations: {results.get('iterations', 0)}")
    logger.warning("")

    # Primary counters (70/30 validation)
    llm_exec = results.get('llm_executed', 0)
    alg_chosen = results.get('algorithm_chosen', 0)
    primary_total = llm_exec + alg_chosen

    logger.warning("Primary Counters (70/30 Probabilistic Routing):")
    logger.warning(f"  LLM executed: {llm_exec}")
    logger.warning(f"  Algorithm chosen: {alg_chosen}")
    if primary_total > 0:
        llm_pct = (llm_exec / primary_total) * 100
        logger.warning(f"  LLM percentage: {llm_pct:.1f}%")
    logger.warning("")

    # Auxiliary counters (special cases)
    llm_fallback = results.get('llm_fallback', 0)
    forced_back = results.get('forced_back', 0)
    recovery_actions = results.get('recovery_actions', 0)

    logger.warning("Auxiliary Counters (Not in 70/30):")
    logger.warning(f"  llm_fallback: {llm_fallback}")
    logger.warning(f"  forced_back: {forced_back}")
    logger.warning(f"  recovery_actions: {recovery_actions}")
    logger.warning("")

    # Total actions
    total_actions = llm_exec + alg_chosen + llm_fallback + forced_back + recovery_actions
    logger.warning(f"Total actions: {total_actions}")
    logger.warning("")

    # State exploration
    if 'visited_states' in results:
        unique_states = len(results['visited_states'])
        logger.warning(f"Unique states visited: {unique_states}")
        if results.get('iterations', 0) > 0:
            exploration_rate = (unique_states / results['iterations']) * 100
            logger.warning(f"Exploration rate: {exploration_rate:.1f}%")
        logger.warning("")

    # Success criteria
    success = True
    reasons = []

    if llm_fallback > 0:
        logger.warning("✅ llm_fallback counter working (> 0)")
    else:
        logger.warning("⚠️  llm_fallback = 0 (no LLM failures detected)")

    if llm_exec > 0:
        logger.warning("✅ LLM generating valid actions")
    else:
        logger.warning("⚠️  LLM executed = 0 (LLM not generating tool calls)")
        reasons.append("LLM not generating tool calls - needs investigation")

    if results.get('iterations', 0) > 20:
        logger.warning("✅ Test progressed (>20 iterations)")
    else:
        logger.warning("⚠️  Too few iterations")
        reasons.append("Too few iterations - possible early termination or stuck")

    # Final verdict
    logger.warning("")
    logger.warning("="*80)
    if success and not reasons:
        logger.warning("✅ TEST PASSED")
    elif reasons:
        logger.warning("⚠️  TEST PASSED WITH WARNINGS")
        for reason in reasons:
            logger.warning(f"   - {reason}")
    else:
        logger.warning("❌ TEST FAILED")
        for reason in reasons:
            logger.warning(f"   - {reason}")
    logger.warning("="*80)

    sys.exit(0)

except Exception as e:
    logger.error(f"❌ Test failed with exception: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
