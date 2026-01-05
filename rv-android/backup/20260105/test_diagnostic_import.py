#!/usr/bin/env python3
"""
Simple test to verify diagnostic logging imports are working.
"""

import os
import sys
from pathlib import Path

# Setup paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "modules" / "rv-android-core" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rvsmart-tool" / "src"))

def test_diagnostic_imports():
    """Test that diagnostic logging imports work correctly."""
    print("Testing diagnostic imports...")
    
    try:
        # Test TestOrchestrator import and method inspection
        from rvsmart_tool.orchestration.test_orchestrator import TestOrchestrator
        import inspect
        
        print(f"✅ TestOrchestrator imported from: {inspect.getfile(TestOrchestrator)}")
        
        # Check if the execute_test_cycle method contains our diagnostic logging
        source = inspect.getsource(TestOrchestrator.execute_test_cycle)
        
        if "🎬 RVSMART TESTORCHESTRATOR EXECUTION START" in source:
            print("✅ Diagnostic logging found in TestOrchestrator.execute_test_cycle")
        else:
            print("❌ Diagnostic logging NOT found in TestOrchestrator.execute_test_cycle")
            
        # Test StateEnricher import and method inspection
        from rvsmart_tool.llm.service.state_enricher import StateEnricher
        se_source = inspect.getsource(StateEnricher.__init__)
        
        if "🔧 STATEENRICHER INITIALIZATION" in se_source:
            print("✅ Diagnostic logging found in StateEnricher.__init__")
        else:
            print("❌ Diagnostic logging NOT found in StateEnricher.__init__")
            
        # Test ActionService import and method inspection
        from rvsmart_tool.llm.service.action_service import LLMActionService
        as_source = inspect.getsource(LLMActionService.__init__)
        
        if "🚀 ACTIONSERVICE INITIALIZATION COMPLETED" in as_source:
            print("✅ Diagnostic logging found in LLMActionService.__init__")
        else:
            print("❌ Diagnostic logging NOT found in LLMActionService.__init__")
            
        return True
        
    except Exception as e:
        print(f"❌ Error testing imports: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("🔍 DIAGNOSTIC IMPORT TEST")
    print("=" * 60)
    
    success = test_diagnostic_imports()
    
    print("=" * 60)
    if success:
        print("🎉 DIAGNOSTIC IMPORTS: SUCCESS")
    else:
        print("❌ DIAGNOSTIC IMPORTS: FAILED")
    print("=" * 60)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())