#!/usr/bin/env python3
"""
Diagnostic test to check if source code modifications are properly loaded.
"""

import os
import sys
from pathlib import Path

# Setup paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "modules" / "rv-android-core" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-llm" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rvsmart-tool" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-screen-parser" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-static-analysis" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-uiautomator" / "src"))

# Environment setup
from rv_android_core import constants
parent_directory = os.path.dirname(os.getcwd())
os.environ[constants.ENV_RVSEC_HOME] = parent_directory

def test_source_modifications():
    """Test if our source code modifications are properly loaded."""
    print("=" * 60)
    print("🔍 SOURCE MODIFICATION DIAGNOSTIC TEST")
    print("=" * 60)
    
    try:
        import inspect
        
        # Test TestOrchestrator
        from rvsmart_tool.orchestration.test_orchestrator import TestOrchestrator
        orchestrator_source = inspect.getsource(TestOrchestrator.execute_test_cycle)
        
        print(f"\n1. TestOrchestrator.execute_test_cycle source check:")
        if "🎬 RVSMART TESTORCHESTRATOR EXECUTION START" in orchestrator_source:
            print("   ✅ Modified TestOrchestrator source loaded")
        else:
            print("   ❌ Original TestOrchestrator source - modifications not loaded")
            
        # Test ActionService
        from rvsmart_tool.llm.service.action_service import LLMActionService
        action_service_init_source = inspect.getsource(LLMActionService.__init__)
        
        print(f"\n2. LLMActionService.__init__ source check:")
        if "🚀 ACTIONSERVICE INITIALIZATION COMPLETED" in action_service_init_source:
            print("   ✅ Modified ActionService __init__ source loaded")
        else:
            print("   ❌ Original ActionService __init__ source - modifications not loaded")
            
        action_service_process_source = inspect.getsource(LLMActionService.process_state)
        
        print(f"\n3. LLMActionService.process_state source check:")
        if "DEBUG_COORD_ENH" in action_service_process_source:
            print("   ✅ Modified ActionService process_state source loaded")
        else:
            print("   ❌ Original ActionService process_state source - modifications not loaded")
            
        # Test StateEnricher  
        from rvsmart_tool.llm.service.state_enricher import StateEnricher
        state_enricher_init_source = inspect.getsource(StateEnricher.__init__)
        
        print(f"\n4. StateEnricher.__init__ source check:")
        if "🔧 STATEENRICHER INITIALIZATION" in state_enricher_init_source:
            print("   ✅ Modified StateEnricher __init__ source loaded")
        else:
            print("   ❌ Original StateEnricher __init__ source - modifications not loaded")
            
        state_enricher_context_source = inspect.getsource(StateEnricher.create_processing_context)
        
        print(f"\n5. StateEnricher.create_processing_context source check:")
        if "DEBUG_COORD_ENH" in state_enricher_context_source:
            print("   ✅ Modified StateEnricher context source loaded")
        else:
            print("   ❌ Original StateEnricher context source - modifications not loaded")
            
        print("\n" + "=" * 60)
        print("📊 DIAGNOSTIC SUMMARY:")
        
        all_modifications = [
            "🎬 RVSMART TESTORCHESTRATOR EXECUTION START" in orchestrator_source,
            "🚀 ACTIONSERVICE INITIALIZATION COMPLETED" in action_service_init_source,
            "DEBUG_COORD_ENH" in action_service_process_source,
            "🔧 STATEENRICHER INITIALIZATION" in state_enricher_init_source,
            "DEBUG_COORD_ENH" in state_enricher_context_source
        ]
        
        if all(all_modifications):
            print("🎉 ALL MODIFICATIONS LOADED SUCCESSFULLY!")
            print("   The diagnostic logging should work in tests")
        else:
            print("⚠️ SOME MODIFICATIONS NOT LOADED!")
            print(f"   Loaded: {sum(all_modifications)}/{len(all_modifications)}")
            print("   This explains why diagnostic logs don't appear")
        
        print("=" * 60)
        return all(all_modifications)
        
    except Exception as e:
        print(f"❌ Error during source diagnostic: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    success = test_source_modifications()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())