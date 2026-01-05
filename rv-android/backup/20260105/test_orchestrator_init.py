#!/usr/bin/env python3
"""
Test TestOrchestrator initialization to verify diagnostic logging.
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

def setup_logging():
    """Setup detailed logging to see diagnostic messages."""
    import logging
    from rv_android_core.util.logging.manager import LoggingManager
    
    logging_manager = LoggingManager.get_instance()
    logging_manager.configure_output(
        console=True,
        file=False,
        console_level=10,  # DEBUG
        json_format=False
    )
    
    return logging_manager.get_logger('orchestrator.init.test')

def test_orchestrator_init():
    """Test TestOrchestrator initialization to see diagnostic logs."""
    logger = setup_logging()
    
    print("=" * 60)
    print("🔍 TESTORCHESTRATOR INITIALIZATION TEST")
    print("=" * 60)
    
    try:
        # Import necessary components
        from rv_android_core.domain.app import App
        from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser
        from rvsmart_tool.config.tool_config import RvSmartToolConfig
        from rvsmart_tool.orchestration.test_orchestrator import TestOrchestrator
        from rv_llm.llm.constants import LLMType, PromptStrategyType, ContextMode
        from rv_screen_parser.constants import ScreenParserType, VisitorType
        
        # Application setup
        app_folder = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/out/instrumented_apks"
        apk_name = "cryptoapp.apk"
        apk_path = os.path.join(app_folder, apk_name)
        
        # Load app and static data
        logger.info("📱 Loading application and static analysis data...")
        app = App(apk_path)
        parser = StaticAnalysisParser()
        static_data = parser.read_static_analysis_files(app_folder, apk_name, app.package_name)
        
        # Configure with Qwen 2.5VL 7B vision model
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
        
        print("\n" + "=" * 60)
        print("🎬 CREATING TESTORCHESTRATOR - WATCH FOR DIAGNOSTIC LOGS:")
        print("=" * 60)
        
        # Create TestOrchestrator - this should show our diagnostic logging
        orchestrator = TestOrchestrator(
            static_data=static_data.to_dict() if hasattr(static_data, 'to_dict') else static_data,
            tool_config=tool_config,
            app=app,
            device_id="emulator-5554",
            results_dir="./test_init_results"
        )
        
        print("=" * 60)
        print("✅ TestOrchestrator created successfully")
        print("=" * 60)
        
        # Check if we can see the ActionService diagnostic logs too
        print("📋 ActionService configuration:")
        print(f"   LLM Model: {orchestrator.llm_service.llm_config.model}")
        print(f"   Vision: {orchestrator.llm_service.llm_config.vision}")
        print(f"   Strategy: {orchestrator.llm_service.prompt_config.strategy_type}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during initialization test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    success = test_orchestrator_init()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ORCHESTRATOR INITIALIZATION: SUCCESS")
        print("   If diagnostic logs appeared above, the system is working")
    else:
        print("❌ ORCHESTRATOR INITIALIZATION: FAILED")
    print("=" * 60)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())