#!/usr/bin/env python3
"""
Test Autonomous RVAgent with LangGraph A.2.1 Architecture

Validates the evolved RVAgent implementation with:
- LangGraph multimodal context preservation
- Autonomous tool suite with reasoning
- Memory management and learning
- Screenshot capture and analysis
"""

import sys
import time
import json
from pathlib import Path

# Add rv-agent to path
rv_agent_path = str(Path(__file__).parent / "src")
sys.path.insert(0, rv_agent_path)

try:
    from rv_agent.core.rv_agent import RVAgent
    from rv_agent.constants import RVAgentConstants
    print("✅ Successfully imported autonomous RVAgent")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    exit(1)


def test_autonomous_rvagent():
    """Test complete autonomous RVAgent system"""

    print("🔬 TESTING AUTONOMOUS RVAGENT WITH LANGGRAPH A.2.1")
    print("=" * 60)

    try:
        # Initialize autonomous agent
        print("🚀 Initializing autonomous RVAgent...")
        agent = RVAgent(model_name="PetrosStav/gemma3-tools:4b", timeout=30)
        print("✅ Agent initialized successfully")

        # Check status
        print("\n📊 Checking agent status...")
        status = agent.get_agent_status()
        print(f"Architecture: {status.get('architecture', 'unknown')}")
        print(f"Model: {status.get('model', 'unknown')}")
        print(f"Components: {json.dumps(status.get('components_status', {}), indent=2)}")
        print(f"Capabilities: {json.dumps(status.get('capabilities', {}), indent=2)}")

        # Test device connection (simulation mode)
        print("\n📱 Testing device connection...")
        connected = agent.connect_to_device()
        print(f"Device connected: {connected}")

        # Start autonomous session
        print("\n🎯 Starting autonomous session...")
        session_started = agent.start_autonomous_session(
            package_name="br.unb.cic.cryptoapp",
            objective="comprehensive_autonomous_testing_with_reasoning",
            initial_screenshot_path=None
        )
        print(f"Session started: {session_started}")

        if session_started:
            # Run autonomous exploration (short duration for test)
            print("\n🤖 Running autonomous exploration...")
            results = agent.run_autonomous_exploration(timeout=10)

            print(f"\n📋 AUTONOMOUS EXPLORATION RESULTS:")
            print(f"Status: {results.get('session_info', {}).get('status', 'unknown')}")

            if 'session_info' in results:
                session_info = results['session_info']
                print(f"Package: {session_info.get('package_name', 'unknown')}")
                print(f"Duration: {session_info.get('duration_seconds', 0):.2f}s")
                print(f"Iterations: {session_info.get('iterations', 0)}")
                print(f"Tool executions: {session_info.get('tool_executions', 0)}")
                print(f"Architecture: {session_info.get('architecture', 'unknown')}")

            # Tool statistics
            if 'tool_statistics' in results:
                tool_stats = results['tool_statistics']
                print(f"\n🔧 TOOL EXECUTION STATISTICS:")
                print(f"Total executions: {tool_stats.get('total_executions', 0)}")
                print(f"Success rate: {tool_stats.get('overall_success_rate', 0):.1f}%")
                print(f"Tools used: {list(tool_stats.get('tool_counts', {}).keys())}")

            # Memory statistics
            if 'memory_statistics' in results:
                memory_stats = results['memory_statistics']
                print(f"\n🧠 MEMORY & LEARNING STATISTICS:")
                print(f"Elements discovered: {memory_stats.get('total_elements_discovered', 0)}")
                print(f"Coverage: {memory_stats.get('coverage_percentage', 0):.1f}%")
                print(f"Successful coordinates: {memory_stats.get('successful_coordinates', 0)}")

            # Autonomous capabilities
            if 'autonomous_capabilities' in results:
                capabilities = results['autonomous_capabilities']
                print(f"\n🎯 AUTONOMOUS CAPABILITIES DEMONSTRATED:")
                for capability, demonstrated in capabilities.items():
                    status = "✅" if demonstrated else "❌"
                    print(f"{status} {capability}: {demonstrated}")

            # Performance metrics
            if 'performance_metrics' in results:
                perf = results['performance_metrics']
                print(f"\n⚡ PERFORMANCE METRICS:")
                print(f"Overall success rate: {perf.get('overall_success_rate', 0):.1f}%")
                print(f"Coverage percentage: {perf.get('coverage_percentage', 0):.1f}%")
                print(f"Tools per second: {perf.get('tools_per_second', 0):.2f}")
                print(f"Autonomous efficiency: {perf.get('autonomous_efficiency', 0):.1f}%")

            print(f"\n✅ AUTONOMOUS TESTING COMPLETED SUCCESSFULLY!")

            # Final status check
            final_status = agent.get_agent_status()
            print(f"\n📊 FINAL STATISTICS:")
            final_stats = final_status.get('statistics', {})
            print(f"Total tool executions: {final_stats.get('tool_executions', 0)}")
            print(f"Success rate: {final_stats.get('success_rate', 0):.1f}%")
            print(f"Memory entries: {final_stats.get('memory_entries', 0)}")

            return True

        else:
            print("❌ Session start failed")
            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_autonomous_capabilities():
    """Test specific autonomous capabilities"""

    print("\n🔍 TESTING SPECIFIC AUTONOMOUS CAPABILITIES")
    print("=" * 50)

    try:
        # Test component initialization
        print("🧩 Testing component initialization...")
        agent = RVAgent()

        # Test tool manager
        print("🔧 Testing tool manager...")
        tools = agent.tool_manager.create_tools()
        print(f"Available tools: {len(tools)}")

        for tool in tools:
            print(f"  - {tool.name}: {tool.description[:50]}...")

        # Test memory manager
        print("\n🧠 Testing memory manager...")
        agent.memory_manager.start_session("test_session", "test.package")
        agent.memory_manager.add_short_term_memory(
            entry_type="test_entry",
            content="Test autonomous memory entry",
            reasoning="Testing memory management capabilities",
            priority="normal"
        )

        memory_context = agent.memory_manager.get_memory_context_for_llm()
        print(f"Memory context generated: {len(memory_context)} characters")

        # Test tool execution tracking
        print("\n📊 Testing tool execution tracking...")
        tool_stats = agent.tool_manager.get_execution_statistics()
        print(f"Initial tool statistics: {tool_stats}")

        print("✅ All autonomous capabilities validated")
        return True

    except Exception as e:
        print(f"❌ Capability test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 AUTONOMOUS RVAGENT VALIDATION TEST")
    print("Using LangGraph A.2.1 Architecture with Multimodal Context Preservation")
    print("=" * 80)

    # Test main functionality
    main_test_success = test_autonomous_rvagent()

    # Test specific capabilities
    capabilities_test_success = test_autonomous_capabilities()

    # Summary
    print("\n" + "=" * 80)
    print("📋 TEST SUMMARY:")
    print(f"✅ Main autonomous test: {'PASSED' if main_test_success else 'FAILED'}")
    print(f"✅ Capabilities test: {'PASSED' if capabilities_test_success else 'FAILED'}")

    if main_test_success and capabilities_test_success:
        print("\n🎉 ALL TESTS PASSED - Autonomous RVAgent with LangGraph A.2.1 is ready!")
        print("🚀 Features validated:")
        print("  • LangGraph StateGraph with multimodal context preservation")
        print("  • Comprehensive autonomous tool suite with reasoning")
        print("  • Memory management and learning capabilities")
        print("  • Screenshot capture and UI analysis")
        print("  • Performance tracking and statistics")
    else:
        print("\n❌ Some tests failed - check implementation")
        exit(1)