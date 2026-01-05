#!/usr/bin/env python3
"""
Teste simples para verificar se o TestOrchestrator está sendo chamado.
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

def test_orchestrator_call():
    """Teste se o TestOrchestrator está sendo chamado."""
    print("=" * 60)
    print("🔍 TESTORCHESTRATOR CALL TEST")
    print("=" * 60)
    
    try:
        # Setup logging first
        from rv_android_core.util.logging.manager import LoggingManager
        logging_manager = LoggingManager.get_instance()
        logging_manager.configure_output(
            console=True,
            file=False,
            console_level=10,  # DEBUG
            json_format=False
        )
        
        # Import required components
        from rv_android_core.domain.app import App
        from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser
        from rvsmart_tool.config.tool_config import RvSmartToolConfig
        from rvsmart_tool.orchestration.test_orchestrator import TestOrchestrator
        from rv_llm.llm.constants import LLMType, PromptStrategyType, ContextMode
        from rv_screen_parser.constants import ScreenParserType, VisitorType
        
        print("✅ Imports successful")
        
        # Quick app setup
        app_folder = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/out/instrumented_apks"
        apk_name = "cryptoapp.apk"
        apk_path = os.path.join(app_folder, apk_name)
        
        if not os.path.exists(apk_path):
            print(f"❌ APK not found: {apk_path}")
            return False
            
        print(f"✅ APK found: {apk_path}")
        
        # Load minimal data
        app = App(apk_path)
        print(f"✅ App loaded: {app.package_name}")
        
        # Load static data
        parser = StaticAnalysisParser()
        static_data = parser.read_static_analysis_files(app_folder, apk_name, app.package_name)
        print("✅ Static data loaded")
        
        # Configure
        variant_config = {
            "llm_type": LLMType.OLLAMA,
            "llm_model": "qwen2.5vl:7b",
            "temperature": 0.2,
            "vision": True,
            "prompt_strategy": PromptStrategyType.VISION,
            "parser_type": ScreenParserType.UIAUTOMATOR,
            "visitor_type": VisitorType.DEFAULT,
            "debug_mode": True
        }
        
        tool_config = RvSmartToolConfig.create_from_variant(variant_config)
        print("✅ Config created")
        
        print("\n" + "=" * 60)
        print("🎬 CREATING TESTORCHESTRATOR - WATCH FOR LOGS!")
        print("=" * 60)
        
        # This should trigger our diagnostic logs during __init__
        orchestrator = TestOrchestrator(
            static_data=static_data.to_dict() if hasattr(static_data, 'to_dict') else static_data,
            tool_config=tool_config,
            app=app,
            device_id="emulator-5554",
            results_dir="./test_orchestrator_results"
        )
        
        print("\n✅ TestOrchestrator created successfully!")
        
        # Check if our diagnostic methods were called
        print(f"ActionService type: {type(orchestrator.llm_service).__name__}")
        print(f"Config vision: {orchestrator.llm_service.llm_config.vision}")
        
        print("\n" + "=" * 60)
        print("🎯 CALLING EXECUTE_TEST_CYCLE - WATCH FOR LOGS!")  
        print("=" * 60)
        
        # This should trigger our diagnostic logs during execution
        # Use very short timeout to avoid hanging
        try:
            orchestrator.execute_test_cycle(timeout=5)
        except Exception as e:
            print(f"Expected timeout/error: {e}")
        
        print("\n✅ Test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    success = test_orchestrator_call()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())