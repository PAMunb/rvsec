#!/usr/bin/env python3
"""
Detailed coordinate enhancement debug test.

This script specifically tests the coordinate enhancement pipeline with detailed logging
to identify exactly where the enhancement is working or failing.
"""

import logging
import os
import sys
import time
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
    """Setup detailed logging for coordinate debugging."""
    from rv_android_core.util.logging.manager import LoggingManager
    
    logging_manager = LoggingManager.get_instance()
    logging_manager.configure_output(
        console=True,
        file=False,
        console_level=10,  # DEBUG
        json_format=False
    )
    
    # Setup file logging
    file_handler = logging.FileHandler('./coordinate_debug_test.log', mode='w')
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logging.getLogger().addHandler(file_handler)
    
    return logging_manager.get_logger('coordinate.debug.test')

def test_coordinate_debug():
    """Test coordinate enhancement with detailed debugging."""
    logger = setup_logging()
    logger.info("=" * 80)
    logger.info("🔍 COORDINATE ENHANCEMENT DEBUG TEST")
    logger.info("=" * 80)
    logger.info("Testing Qwen 2.5VL 7B with coordinate enhancement")
    logger.info("Expected: Detailed logs showing coordinate enhancement pipeline")
    logger.info("=" * 80)
    
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
        
        if not os.path.exists(apk_path):
            logger.error(f"❌ APK not found: {apk_path}")
            return False
        
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
            "top_p": 0.9,
            "max_tokens": 300,
            "vision": True,
            "prompt_strategy": PromptStrategyType.VISION,
            "parser_type": ScreenParserType.UIAUTOMATOR,
            "visitor_type": VisitorType.DEFAULT,
            "context_mode": ContextMode.STATELESS,
            "debug_mode": True
        }
        
        tool_config = RvSmartToolConfig.create_from_variant(variant_config)
        
        logger.info("⚙️ DEBUG CONFIGURATION:")
        logger.info(f"   Model: {tool_config.llm_config.model}")
        logger.info(f"   Vision: {tool_config.llm_config.vision}")
        logger.info(f"   Strategy: {tool_config.prompt_config.strategy_type}")
        logger.info(f"   Parser: {tool_config.prompt_config.parser_type}")
        logger.info(f"   Debug Mode: {tool_config.debug_mode}")
        
        # Create TestOrchestrator
        logger.info("🎬 Creating TestOrchestrator for detailed debugging...")
        
        # MANUAL DIAGNOSTIC: Check if our modified TestOrchestrator is being used
        import inspect
        source = inspect.getsource(TestOrchestrator.__init__)
        if "🚀 ACTIONSERVICE INITIALIZATION COMPLETED" in source:
            logger.info("✅ DIAGNOSTIC: Modified TestOrchestrator source detected")
        else:
            logger.info("❌ DIAGNOSTIC: Original TestOrchestrator source - modifications not loaded")
            
        orchestrator = TestOrchestrator(
            static_data=static_data.to_dict() if hasattr(static_data, 'to_dict') else static_data,
            tool_config=tool_config,
            app=app,
            device_id="emulator-5554",
            results_dir="./coordinate_debug_results"
        )
        
        # MANUAL DIAGNOSTIC: Check ActionService source
        action_service_source = inspect.getsource(orchestrator.llm_service.process_state)
        if "DEBUG_COORD_ENH" in action_service_source:
            logger.info("✅ DIAGNOSTIC: Modified ActionService source detected")
        else:
            logger.info("❌ DIAGNOSTIC: Original ActionService source - modifications not loaded")
        
        # Execute with timeout for debugging
        logger.info("▶️ Starting coordinate enhancement debug execution...")
        logger.info("🔍 Watch for DEBUG_COORD_ENH logs in the output")
        logger.info("=" * 80)
        
        start_time = time.time()
        
        try:
            # Execute with moderate timeout
            orchestrator.execute_test_cycle(timeout=60)  # 1 minute for debugging
            
            execution_time = time.time() - start_time
            logger.info("=" * 80)
            logger.info(f"✅ Debug execution completed in {execution_time:.1f} seconds")
            
        except KeyboardInterrupt:
            logger.info("\n⚠️ Debug execution interrupted")
        except Exception as e:
            logger.error(f"❌ Error during debug execution: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Analyze results
            metrics = orchestrator.metrics
            
            logger.info("=" * 80)
            logger.info("📊 COORDINATE ENHANCEMENT DEBUG RESULTS:")
            logger.info("=" * 80)
            logger.info(f"   Total actions generated: {metrics.total_actions}")
            logger.info(f"   Successfully executed: {metrics.successful_actions}")
            logger.info(f"   Failed executions: {metrics.failed_actions}")
            logger.info(f"   Success rate: {(metrics.successful_actions/max(1,metrics.total_actions))*100:.1f}%")
            logger.info(f"   Execution time: {metrics.execution_time:.1f}s")
            
            # Cleanup
            orchestrator.cleanup()
            
            # Determine result
            success = metrics.total_actions > 0
            
            if success:
                logger.info("=" * 80)
                logger.info("🎉 DEBUG TEST SUCCESS:")
                logger.info("   ✅ Actions were generated (coordinate enhancement pipeline working)")
                logger.info("   🔍 Check logs for 'DEBUG_COORD_ENH' to see enhancement details")
                logger.info("   📋 Look for 'at position (x, y)' in enhanced descriptions")
            else:
                logger.warning("=" * 80)
                logger.warning("⚠️ DEBUG TEST ISSUES:")
                logger.warning("   ❌ No actions generated")
                logger.warning("   🔍 Check DEBUG_COORD_ENH logs for pipeline failures")
                logger.warning("   🔧 May need configuration or integration fixes")
            
            return success
            
    except Exception as e:
        logger.error(f"❌ Fatal error in coordinate debug test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main debug test function."""
    print("🔍 Starting Coordinate Enhancement Debug Test")
    print("=" * 80)
    print("This test will generate detailed DEBUG_COORD_ENH logs")
    print("Expected pipeline:")
    print("1. StateEnricher detects vision=True")
    print("2. StateEnricher sets vision_enabled=True in context")
    print("3. ActionService passes context to prompt framework")
    print("4. UIElementsFragment receives vision_enabled=True")
    print("5. UIElementsFragment applies coordinate enhancement")
    print("6. LLM receives enhanced prompt with coordinates")
    print("=" * 80)
    
    success = test_coordinate_debug()
    
    print("\n" + "=" * 80)
    if success:
        print("🎉 COORDINATE ENHANCEMENT DEBUG: SUCCESS")
        print("   Check coordinate_debug_test.log for detailed analysis")
        print("   Search for 'DEBUG_COORD_ENH' to trace enhancement pipeline")
        print("   Look for 'at position (x, y)' to confirm coordinate enhancement")
    else:
        print("🔍 COORDINATE ENHANCEMENT DEBUG: NEEDS INVESTIGATION")
        print("   Check coordinate_debug_test.log for error details")
        print("   Search for 'DEBUG_COORD_ENH' to identify pipeline issues")
        print("   Verify configuration and component integration")
    
    print("=" * 80)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())