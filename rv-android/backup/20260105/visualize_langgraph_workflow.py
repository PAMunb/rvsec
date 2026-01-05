"""
Visualize RVAgent LangGraph workflow using Mermaid.
"""
from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.rv_agent import RVAgent

# Test different modes
modes = ["pure_dfs", "llm_only", "hybrid"]

for mode in modes:
    print(f"\n{'='*80}")
    print(f"Generating workflow diagram for mode: {mode}")
    print('='*80)
    
    config = RVAgentConfig(
        package_name="br.unb.cic.cryptoapp",
        device_id="emulator-5554",
        agent_mode=mode,
        timeout=120
    )
    
    agent = RVAgent(config)
    
    # Get the compiled graph
    graph = agent.graph
    
    # Generate Mermaid diagram
    try:
        mermaid_png = graph.get_graph().draw_mermaid_png()
        
        # Save to file
        output_file = f"rvagent_workflow_{mode}.png"
        with open(output_file, 'wb') as f:
            f.write(mermaid_png)
        
        print(f"✅ Diagram saved: {output_file}")
        
    except Exception as e:
        print(f"❌ Error generating diagram: {e}")
        print(f"   Trying ASCII representation...")
        try:
            print(graph.get_graph().draw_ascii())
        except:
            pass

print(f"\n{'='*80}")
print("All diagrams generated!")
print('='*80)
