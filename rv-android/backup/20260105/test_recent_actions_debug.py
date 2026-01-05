#!/usr/bin/env python3
"""
Debug test to verify recent_action_window state during validation.
"""

import logging
import sys
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent / "modules" / "rv-agent" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "modules" / "rv-android-core" / "src"))

from rv_agent.core.agent_factory import AgentFactory
from rv_agent.config.agent_config import RVAgentConfig

# Setup logging - só WARNING para ver os debugs
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.warning("="*80)
logger.warning("TESTING: recent_action_window DEBUG")
logger.warning("="*80)
logger.warning("App: br.unb.cic.cryptoapp")
logger.warning("Duration: 60s (1 minute)")
logger.warning("Max iterations: 10")
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
    max_iterations=10,  # Só 10 iterações
    timeout=60,  # 1 minuto
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
    logger.warning(f"LLM fallback: {results.get('llm_fallback', 0)}")
    logger.warning("="*80)

    sys.exit(0)

except Exception as e:
    logger.error(f"Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
