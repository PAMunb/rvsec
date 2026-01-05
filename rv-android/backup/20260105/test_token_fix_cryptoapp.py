#!/usr/bin/env python3
"""
Test token limit fix with cryptoapp.
Verify both:
1. Validation fix from today still works (llm_fallback counter)
2. LLM now consistently generates tool calls (no token exhaustion)
"""

import logging
import sys
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent / "modules" / "rv-agent" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "modules" / "rv-android-core" / "src"))

from rv_agent.core.agent_factory import AgentFactory
from rv_agent.config.agent_config import RVAgentConfig

# Setup logging - INFO to see LLM responses
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.warning("="*80)
logger.warning("TOKEN LIMIT FIX TEST")
logger.warning("="*80)
logger.warning("App: br.unb.cic.cryptoapp")
logger.warning("Duration: 120s")
logger.warning("Max iterations: 20")
logger.warning("")
logger.warning("Verification goals:")
logger.warning("  1. LLM generates tool calls consistently (no 'done_reason: length')")
logger.warning("  2. Validation fix works (llm_fallback counter accurate)")
logger.warning("  3. System works as it did yesterday/this morning")
logger.warning("="*80)
logger.warning("")

# Create config
config = RVAgentConfig(
    package_name="br.unb.cic.cryptoapp",
    agent_mode="multimode",
    strategy="greedy",
    llm_provider="ollama",
    llm_model="qwen3-vl-4b-16k:latest",
    llm_temperature=0.1,
    llm_top_p=0.9,
    llm_top_k=40,
    prompt_version="v13",
    max_iterations=20,
    timeout=120,
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
    logger.warning(f"Iterations: {results.get('iterations', 0)}")
    logger.warning(f"LLM executed: {results.get('llm_executed', 0)}")
    logger.warning(f"Algorithm chosen: {results.get('algorithm_chosen', 0)}")
    logger.warning(f"llm_fallback: {results.get('llm_fallback', 0)}")
    logger.warning(f"Actions executed: {results.get('actions_executed', 0)}")
    logger.warning("")

    # Analysis
    llm_exec = results.get('llm_executed', 0)
    llm_fb = results.get('llm_fallback', 0)

    if llm_exec > 0:
        logger.warning("✅ LLM executed successfully")
        if llm_fb == 0:
            logger.warning("✅ No LLM fallbacks - all LLM calls generated valid actions")
        else:
            fallback_rate = (llm_fb / llm_exec) * 100
            logger.warning(f"⚠️  LLM fallback rate: {fallback_rate:.1f}% ({llm_fb}/{llm_exec})")
            if fallback_rate < 30:
                logger.warning("   ✅ Fallback rate acceptable (<30%)")
            else:
                logger.warning("   ❌ High fallback rate - may still have token issues")
    else:
        logger.warning("❌ LLM never executed - check logs for errors")

    logger.warning("="*80)
    logger.warning("")
    logger.warning("Check full log above for:")
    logger.warning("  - 'done_reason': should be 'stop', not 'length'")
    logger.warning("  - Tool calls: should have actions, not []")
    logger.warning("  - llm_fallback warnings: shows validation fix working")
    logger.warning("="*80)

    sys.exit(0)

except Exception as e:
    logger.error(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
