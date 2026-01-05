#!/usr/bin/env python3
"""
Investigate why LLM is not generating tool calls.
Run with full INFO logging to see LLM responses.
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
    level=logging.INFO,  # INFO to capture LLM logs
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.warning("="*80)
logger.warning("INVESTIGATION: LLM Tool Calling")
logger.warning("="*80)
logger.warning("App: br.unb.cic.cryptoapp")
logger.warning("Duration: 60s")
logger.warning("Max iterations: 5 (just to see first LLM calls)")
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
    max_iterations=5,  # Just 5 iterations
    timeout=60,
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
    logger.warning("INVESTIGATION RESULTS")
    logger.warning("="*80)
    logger.warning(f"Iterations: {results.get('iterations', 0)}")
    logger.warning(f"LLM executed: {results.get('llm_executed', 0)}")
    logger.warning(f"Algorithm chosen: {results.get('algorithm_chosen', 0)}")
    logger.warning(f"llm_fallback: {results.get('llm_fallback', 0)}")
    logger.warning("="*80)
    logger.warning("")
    logger.warning("Check the full log above to see:")
    logger.warning("  1. LLM_GENERATE calls")
    logger.warning("  2. Raw LLM responses")
    logger.warning("  3. Tool calls extraction")
    logger.warning("  4. Whether LLM returned empty actions")
    logger.warning("="*80)

    sys.exit(0)

except Exception as e:
    logger.error(f"❌ Investigation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
