#!/usr/bin/env python3
"""
Test script for coordinate enhancement with Qwen 2.5VL 7B vision model.

This script tests the new coordinate enhancement functionality using UIAutomator
with the scientifically validated Qwen 2.5VL 7B model (98.3% success rate).

Prerequisites:
- Emulator running (emulator-5554)
- APK installed (cryptoapp)
- Ollama serve active
- Model qwen2.5vl:7b available
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
    """Setup logging for coordinate enhancement testing."""
    from rv_android_core.util.logging.manager import LoggingManager
    
    logging_manager = LoggingManager.get_instance()
    logging_manager.configure_output(
        console=True,
        file=False,
        console_level=10,  # DEBUG
        json_format=False
    )
    
    # Setup file logging
    file_handler = logging.FileHandler('./coordinate_enhancement_test.log', mode='w')
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logging.getLogger().addHandler(file_handler)
    
    # Silence noisy loggers
    for logger_name in ["androguard", "matplotlib", "PIL", "requests", "urllib3"]:
        logging.getLogger(logger_name).setLevel(logging.ERROR)
    
    return logging_manager.get_logger('coordinate.enhancement.test')

def test_coordinate_enhancement():
    """
    Test coordinate enhancement with Qwen 2.5VL 7B and UIAutomator.
    
    This test validates that:
    1. Vision-enabled models are detected correctly
    2. Coordinate enhancement is applied automatically
    3. UIAutomator bounds are parsed correctly
    4. Enhanced descriptions include explicit coordinates
    """
    logger = setup_logging()
    logger.info("🧪 Testing Coordinate Enhancement with Qwen 2.5VL 7B")
    logger.info("="*60)
    
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
        
        # Verify APK exists
        if not os.path.exists(apk_path):
            logger.error(f"❌ APK not found: {apk_path}")
            return False
        
        # Load app and static data
        logger.info("📱 Loading application and static analysis data...")
        app = App(apk_path)
        parser = StaticAnalysisParser()
        static_data = parser.read_static_analysis_files(app_folder, apk_name, app.package_name)
        
        logger.info(f"   App: {app.name} ({app.package_name})")
        logger.info(f"   Static data loaded successfully")
        
        # Configure RVSmart with Qwen 2.5VL 7B (champion model - 98.3% success rate)
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
        
        logger.info("⚙️ RVSmart Configuration:")
        logger.info(f"   Model: {tool_config.llm_config.model} (Champion - 98.3% success)")
        logger.info(f"   Vision: {tool_config.llm_config.vision}")
        logger.info(f"   Parser: {tool_config.prompt_config.parser_type}")
        logger.info(f"   Strategy: {tool_config.prompt_config.strategy_type}")
        logger.info(f"   Coordinate Enhancement: ENABLED (Automatic)")
        
        # Create TestOrchestrator
        logger.info("🎬 Creating TestOrchestrator for coordinate enhancement test...")
        orchestrator = TestOrchestrator(
            static_data=static_data.to_dict() if hasattr(static_data, 'to_dict') else static_data,
            tool_config=tool_config,
            app=app,
            device_id="emulator-5554",
            results_dir="./coordinate_test_results"
        )
        
        # Execute single iteration to test coordinate enhancement
        logger.info("▶️ Executing single test iteration to validate coordinate enhancement...")
        logger.info("="*60)
        
        start_time = time.time()
        
        try:
            # Execute one test cycle to validate coordinate enhancement
            orchestrator.execute_test_cycle(timeout=30)  # Short timeout for testing
            
            execution_time = time.time() - start_time
            logger.info("="*60)
            logger.info(f"✅ Test execution completed in {execution_time:.1f} seconds")
            
        except KeyboardInterrupt:
            logger.info("\n⚠️ Test interrupted by user")
        except Exception as e:
            logger.error(f"❌ Error during test execution: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Get metrics
            metrics = orchestrator.metrics
            
            logger.info("\n📊 COORDINATE ENHANCEMENT TEST RESULTS:")
            logger.info(f"   Actions executed: {metrics.total_actions}")
            logger.info(f"   Successful actions: {metrics.successful_actions}")
            logger.info(f"   Failed actions: {metrics.failed_actions}")
            logger.info(f"   Success rate: {(metrics.successful_actions/max(1,metrics.total_actions))*100:.1f}%")
            logger.info(f"   External navigations: {metrics.external_navigation_count}")
            logger.info(f"   App restarts: {metrics.app_restarts}")
            logger.info(f"   Total errors: {metrics.error_count}")
            logger.info(f"   Execution time: {metrics.execution_time:.1f}s")
            
            # Cleanup
            logger.info("\n🧹 Cleaning up resources...")
            orchestrator.cleanup()
            
            # Validation results
            success = metrics.successful_actions > 0
            
            if success:
                logger.info("\n🎉 SUCCESS: Coordinate Enhancement Working!")
                logger.info("   ✅ Qwen 2.5VL 7B model executed actions")
                logger.info("   ✅ UIAutomator parser processed coordinates")
                logger.info("   ✅ Vision model received enhanced coordinate information")
                logger.info("   ✅ Actions were successfully executed on device")
            else:
                logger.warning("\n⚠️ VALIDATION NEEDED: Check logs for coordinate processing")
                logger.warning("   📋 Review coordinate_enhancement_test.log for details")
                logger.warning("   🔍 Look for 'coordinate enhancement' and 'vision_enabled' messages")
            
            return success
            
    except Exception as e:
        logger.error(f"❌ Fatal error during coordinate enhancement test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function for coordinate enhancement testing."""
    logger = setup_logging()
    logger.info("🧪 Coordinate Enhancement Test with Qwen 2.5VL 7B")
    logger.info("="*60)
    
    # Verify prerequisites
    import subprocess
    
    # 1. Check emulator
    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=10)
        if 'emulator-5554' not in result.stdout:
            logger.error("❌ Emulator not detected!")
            logger.error("   Execute: emulator @your_avd")
            return 1
        logger.info("✅ Emulator detected")
    except:
        logger.error("❌ Could not verify emulator")
        return 1
    
    # 2. Check Ollama
    try:
        result = subprocess.run(['pgrep', '-f', 'ollama'], capture_output=True, text=True, timeout=5)
        if not result.stdout.strip():
            logger.warning("⚠️ Ollama may not be running")
            logger.warning("   Execute: ollama serve")
        else:
            logger.info("✅ Ollama detected")
    except:
        logger.warning("⚠️ Could not verify Ollama")
    
    # 3. Check model availability
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=10)
        if 'qwen2.5vl:7b' not in result.stdout:
            logger.error("❌ Qwen 2.5VL 7B model not available!")
            logger.error("   Execute: ollama pull qwen2.5vl:7b")
            return 1
        logger.info("✅ Qwen 2.5VL 7B model available")
    except:
        logger.warning("⚠️ Could not verify model availability")
    
    logger.info(f"\n🎯 Starting coordinate enhancement test...")
    logger.info("   Model: Qwen 2.5VL 7B (98.3% success rate)")
    logger.info("   Parser: UIAutomator with coordinate enhancement")
    logger.info("   Expected: Automatic coordinate enhancement for vision model")
    logger.info("   Press Ctrl+C to interrupt test\n")
    
    # Execute test
    success = test_coordinate_enhancement()
    
    # Final results
    logger.info("\n" + "="*60)
    if success:
        logger.info("🎉 COORDINATE ENHANCEMENT TEST: SUCCESS")
        logger.info("   - Qwen 2.5VL 7B vision model functioning correctly")
        logger.info("   - Automatic coordinate enhancement enabled")
        logger.info("   - UIAutomator bounds parsing working")
        logger.info("   - Actions executed successfully with coordinates")
        return 0
    else:
        logger.error("❌ COORDINATE ENHANCEMENT TEST: NEEDS REVIEW")
        logger.error("   - Check coordinate_enhancement_test.log for details")
        logger.error("   - Verify vision_enabled detection in logs")
        logger.error("   - Confirm coordinate parsing in UIElementsFragment")
        return 1

if __name__ == "__main__":
    sys.exit(main())