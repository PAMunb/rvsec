"""
RVAgent test script.

Simple script for testing RVAgent with a specific APK and static analysis data.

Usage:
    python teste_rvagent.py

Configuration:
    - Set APK name and paths below
    - Adjust timeout and other parameters as needed
    - Requires SGLang server running at configured URL
"""

import logging
import os
import sys
from datetime import datetime
from typing import Optional

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.agent.agent_factory import AgentFactory
from rv_android_core.domain.app import App
from rv_android_core.domain.static import StaticAnalysisData
from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser


def execute(
    config: RVAgentConfig, static_data: Optional[StaticAnalysisData], package: str
):
    """Execute RVAgent with given configuration."""
    try:
        agent = AgentFactory.create_agent(config, static_data)
        result = agent.run()

        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)
        print(f"  Iterations: {result.get('iterations', 'N/A')}")
        print(f"  Unique states: {result.get('unique_states', 'N/A')}")
        print(f"  Actions executed: {result.get('actions_executed', 'N/A')}")
        print(f"  LLM calls: {result.get('llm_calls', 'N/A')}")
        print(f"  Algorithm calls: {result.get('algorithm_calls', 'N/A')}")
        print("=" * 60)
    except Exception as e:
        logging.exception(f"Test failed for {package}")
        print(f"Test failed for {package}: {e}")


if __name__ == "__main__":
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logging.getLogger("androguard").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logging.info("Starting RVAgent test...")

    # ==========================================================================
    # CONFIGURATION - Adjust these values as needed
    # ==========================================================================
    apk = "cryptoapp.apk"
    screenshots_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"

    # ==========================================================================

    app_folder = os.path.join(screenshots_folder, apk)
    apk_path = os.path.join(app_folder, apk)
    reach_file = os.path.join(app_folder, apk + ".reach")
    gator_file = os.path.join(app_folder, apk + ".wtg")
    gesda_file = os.path.join(app_folder, apk + ".gesda")

    print(f"Test files:")
    print(f"  APK: {apk}")

    # Get package name using App class
    app = App(app_path=apk_path)
    package = app.package_name
    print(f"  Package: {package}")

    # Parse static analysis data (optional but recommended for WTG/MOP guidance)
    static_data = None
    if os.path.exists(gator_file):
        print("\nParsing static analysis data...")
        static_analysis_parser = StaticAnalysisParser()
        static_data = static_analysis_parser.parse(
            reach_file, gator_file, gesda_file, package
        )
        print(
            f"  Static data parsed (WTG: {len(static_data.wtg.nodes) if static_data.wtg else 0} nodes)"
        )
    else:
        print("\nNo static analysis data found (running without WTG guidance)")

    # Create configuration
    config = RVAgentConfig(
        package_name=package,
        # Execution mode: "pure_algorithm", "llm_only", or "multimode" (default)
        agent_mode="pure_algorithm",
        # Exploration strategy: "rvagent" (recommended), "dfs", "bfs", "greedy"
        strategy="rvagent",
        # LLM probability for multimode (0.7 = 70% LLM, 30% algorithm)
        llm_probability=0.7,
        # LLM configuration (SGLang server)
        llm_model="Qwen/Qwen3-VL-4B-Instruct",
        llm_base_url="http://192.168.0.36:30000/v1",
        llm_temperature=0.01,  # Low for consistent tool calling
        # Prompt version: "v13" (dialog handling), "v14" (structured reasoning), "v16" (navigation-first)
        prompt_version="v13",
        # Execution parameters
        timeout=120,  # seconds
        screenshot_dir=f"/tmp/test_rvagent_{datetime.now().strftime('%Y%m%d_%H%M%S')}/{package}",
        screenshot_rotation_limit=50,
        # Stochastic exploration (adds variety to action selection)
        stochastic_probability=0.3,  # 30% chance of stochastic selection
        stochastic_temperature=1.0,
        # Debug mode
        debug_mode=False,
        verbose_counters=False,
    )

    print(f"\nConfiguration:")
    print(f"  Mode: {config.agent_mode}")
    print(f"  Strategy: {config.strategy}")
    print(f"  LLM probability: {config.llm_probability}")
    print(f"  Timeout: {config.timeout}s")
    print(f"  Screenshot dir: {config.screenshot_dir}")

    execute(config, static_data, package)
