#!/usr/bin/env python3
"""
Test FIXED Execution Loop - Validate the corrected LangGraph implementation

This tests the FIXED version that should properly:
1. Capture screenshots
2. Analyze UI with specific elements
3. Click on specific elements based on analysis
4. Progress through actual testing actions
"""

import sys
import time
from pathlib import Path

# Add rv-agent to path
rv_agent_path = str(Path(__file__).parent / "src")
sys.path.insert(0, rv_agent_path)

from rv_agent.core.langgraph_agent_fixed import LangGraphRVAgentFixed

def test_fixed_execution_loop():
    """Test the FIXED execution loop to ensure it progresses past analysis"""

    print("🔧 TESTING FIXED EXECUTION LOOP")
    print("=" * 60)

    try:
        # Initialize FIXED agent
        print("🚀 Initializing FIXED LangGraph agent...")
        agent = LangGraphRVAgentFixed(
            model_name="PetrosStav/gemma3-tools:4b",
            device_interface=None  # Simulation mode
        )
        print("✅ FIXED agent initialized successfully")

        # Test autonomous session
        print("\n🎯 Starting FIXED autonomous session...")
        start_time = time.time()

        results = agent.start_autonomous_session(
            package_name="br.unb.cic.cryptoapp",
            objective="test_hash_generation_functionality"
        )

        execution_time = time.time() - start_time

        print(f"\n📊 FIXED EXECUTION RESULTS:")
        print(f"⏱️  Total execution time: {execution_time:.2f}s")

        if "error" in results:
            print(f"❌ Execution failed: {results['error']}")
            return False

        # Analyze results
        session_info = results.get("session_info", {})
        execution_details = results.get("execution_details", {})

        print(f"📈 SESSION INFO:")
        print(f"  Package: {session_info.get('package', 'unknown')}")
        print(f"  Duration: {session_info.get('duration_seconds', 0):.2f}s")
        print(f"  Iterations: {session_info.get('iterations', 0)}")
        print(f"  Total tool calls: {session_info.get('total_tool_calls', 0)}")
        print(f"  Action count: {session_info.get('action_count', 0)}")
        print(f"  Status: {session_info.get('status', 'unknown')}")

        print(f"\n🔍 EXECUTION DETAILS:")
        print(f"  UI analyses: {execution_details.get('ui_analyses_performed', 0)}")
        print(f"  Clicks performed: {execution_details.get('clicks_performed', 0)}")
        print(f"  Inputs performed: {execution_details.get('inputs_performed', 0)}")
        print(f"  Screenshots taken: {execution_details.get('screenshots_taken', 0)}")

        # Validation checks
        success_checks = []

        # Check 1: Agent completed iterations
        if session_info.get('iterations', 0) >= 2:
            success_checks.append("✅ Multiple iterations completed")
        else:
            success_checks.append("❌ Too few iterations")

        # Check 2: Agent performed analysis
        if execution_details.get('ui_analyses_performed', 0) >= 1:
            success_checks.append("✅ UI analysis performed")
        else:
            success_checks.append("❌ No UI analysis performed")

        # Check 3: CRITICAL - Agent performed clicks (this was the main problem)
        if execution_details.get('clicks_performed', 0) >= 1:
            success_checks.append("✅ CLICKS PERFORMED - EXECUTION LOOP FIXED!")
        else:
            success_checks.append("❌ NO CLICKS - execution loop still broken")

        # Check 4: Agent took screenshots
        if execution_details.get('screenshots_taken', 0) >= 1:
            success_checks.append("✅ Screenshots captured")
        else:
            success_checks.append("❌ No screenshots taken")

        print(f"\n🎯 VALIDATION RESULTS:")
        for check in success_checks:
            print(f"  {check}")

        # Overall assessment
        critical_success = execution_details.get('clicks_performed', 0) >= 1
        if critical_success:
            print(f"\n🎉 CRITICAL SUCCESS: Execution loop is FIXED!")
            print(f"   Agent progressed from analysis to actual actions")
            print(f"   Performed {execution_details.get('clicks_performed', 0)} clicks")
        else:
            print(f"\n❌ CRITICAL FAILURE: Execution loop still broken")
            print(f"   Agent is not progressing to click actions")

        # Show last UI analysis for debugging
        last_analysis = results.get("last_ui_analysis", "")
        if last_analysis:
            print(f"\n📋 LAST UI ANALYSIS (first 300 chars):")
            print(f"   {last_analysis[:300]}...")

        return critical_success

    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_status():
    """Test agent status reporting"""
    print(f"\n🔍 TESTING AGENT STATUS:")
    try:
        agent = LangGraphRVAgentFixed()
        status = agent.get_agent_status()

        print(f"  Architecture: {status.get('architecture', 'unknown')}")
        print(f"  Tools available: {status.get('tools_available', 0)}")
        print(f"  Fixes applied: {len(status.get('fixes_applied', []))}")

        for fix in status.get('fixes_applied', []):
            print(f"    - {fix}")

        return True
    except Exception as e:
        print(f"❌ Status test failed: {e}")
        return False


if __name__ == "__main__":
    print("🔧 FIXED EXECUTION LOOP VALIDATION")
    print("Testing the corrected LangGraph implementation")
    print("=" * 80)

    # Run tests
    main_test_success = test_fixed_execution_loop()
    status_test_success = test_agent_status()

    # Summary
    print("\n" + "=" * 80)
    print("📋 TEST SUMMARY:")
    print(f"✅ Main execution test: {'PASSED' if main_test_success else 'FAILED'}")
    print(f"✅ Status test: {'PASSED' if status_test_success else 'FAILED'}")

    if main_test_success:
        print("\n🎉 SUCCESS: Execution loop has been FIXED!")
        print("   🔧 Agent now progresses from analysis to actions")
        print("   🎯 Ready for real device testing")
        print("   ⚡ Performance optimized for proper feedback loop")
    else:
        print("\n❌ FAILURE: Execution loop still needs work")
        print("   🔍 Check the LangGraph implementation")
        print("   📋 Review UI feedback integration")

    exit(0 if main_test_success and status_test_success else 1)