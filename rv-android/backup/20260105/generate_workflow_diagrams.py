#!/usr/bin/env python3
"""
Generate Mermaid workflow diagrams for all three RVAgent modes.
Shows the optimized architecture with conditional edges.
"""

import sys
from pathlib import Path

# Add rv-agent module to path
sys.path.insert(0, str(Path(__file__).parent / "modules" / "rv-agent" / "src"))

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.rv_agent import RVAgent


def generate_diagrams():
    """Generate workflow diagrams for all three modes."""

    modes = ["pure_dfs", "llm_only", "hybrid"]

    for mode in modes:
        print(f"\n🔧 Generating diagram for {mode} mode...")

        # Create config for this mode (using real device - won't connect, just build graph)
        config = RVAgentConfig(
            package_name="br.unb.cic.cryptoapp",
            device_id="emulator-5554",
            agent_mode=mode,
            timeout=60  # Minimum allowed timeout
        )

        # Create agent instance - this builds the graph
        agent = RVAgent(config)

        # Generate PNG diagram from the compiled graph
        output_path = f"rvagent_workflow_{mode}_optimized.png"
        agent.graph.get_graph().draw_mermaid_png(
            output_file_path=output_path
        )

        print(f"✅ Saved: {output_path}")


if __name__ == "__main__":
    print("🎨 Generating RVAgent workflow diagrams (optimized architecture)")
    generate_diagrams()
    print("\n✨ All diagrams generated successfully!")
