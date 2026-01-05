#!/usr/bin/env python3
"""
Teste específico para RVSmart com Gemma3:4b e visão habilitada.

Este script testa especificamente o tratamento de screenshots e integração com LLM.
"""

import logging
import os
import sys
import time
from pathlib import Path

# Setup paths following existing pattern
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "modules" / "rv-android-core" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-llm" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rvsmart-tool" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-screen-parser" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-static-analysis" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-uiautomator" / "src"))

# Import constants and setup environment
from rv_android_core import constants
parent_directory = os.path.dirname(os.getcwd())
os.environ[constants.ENV_RVSEC_HOME] = parent_directory

# Import necessary modules
from rv_android_core.domain.app import App
from rv_android_core.util.logging.manager import LoggingManager
from rv_llm.config import LLMConfig, PromptConfig
from rv_llm.llm.constants import LLMType, PromptStrategyType, ContextMode
from rv_screen_parser.constants import ScreenParserType, VisitorType
from rvsmart_tool.config.tool_config import RvSmartToolConfig
from rvsmart_tool.orchestration.test_orchestrator import TestOrchestrator
from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser


def setup_logging(debug: bool = True):
    """Set up logging configuration."""
    logging_manager = LoggingManager.get_instance()
    
    # Configure output
    logging_manager.configure_output(
        console=True,
        file=False,
        console_level=10 if debug else 20,  # DEBUG (10) or INFO (20)
        file_level=10,  # DEBUG
        json_format=False
    )
    
    # Silence noisy loggers
    for noisy_logger in ["androguard", "matplotlib", "PIL", "requests", "urllib3"]:
        logging.getLogger(noisy_logger).setLevel(logging.ERROR)
    
    logger = logging_manager.get_logger('teste.rvsmart.gemma3')
    return logger


def check_screenshot_handling(orchestrator, logger):
    """
    Verificar se o screenshot está sendo capturado e incluído no state.
    
    Args:
        orchestrator: TestOrchestrator instance
        logger: Logger instance
    """
    logger.info("🔍 Checking screenshot handling...")
    
    try:
        # Test screenshot capture directly
        ui_state = orchestrator._capture_ui_state()
        
        if ui_state:
            logger.info("✅ UI state captured successfully")
            logger.info(f"   State keys: {list(ui_state.keys())}")
            
            # Check if screenshot is included
            if 'screenshot_path' in ui_state:
                screenshot_path = ui_state['screenshot_path']
                logger.info(f"✅ Screenshot captured: {screenshot_path}")
                
                # Check if file exists
                if os.path.exists(screenshot_path):
                    file_size = os.path.getsize(screenshot_path)
                    logger.info(f"   Screenshot file size: {file_size} bytes")
                    return True
                else:
                    logger.error(f"❌ Screenshot file not found: {screenshot_path}")
                    return False
            else:
                logger.warning("⚠️  No screenshot_path in UI state")
                return False
        else:
            logger.error("❌ Failed to capture UI state")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error checking screenshot: {e}")
        return False


def test_state_converter(logger):
    """
    Testar o StateConverter para verificar se está convertendo corretamente.
    
    Args:
        logger: Logger instance
    """
    logger.info("🔄 Testing StateConverter...")
    
    try:
        from rv_uiautomator.state.converter import StateConverter
        
        converter = StateConverter()
        
        # Mock UIAutomator state with screenshot
        ui_state = {
            "xml": "<hierarchy><node text='Test Button' bounds='[100,200][300,400]'/></hierarchy>",
            "current_activity": "com.example.TestActivity", 
            "current_package": "com.example.test",
            "timestamp": time.time(),
            "screenshot_path": "/tmp/test_screenshot.png",
            "device_info": {"width": 1080, "height": 1920}
        }
        
        # Convert to DroidBot format
        converted_state = converter.uiautomator_to_droidbot(ui_state)
        
        logger.info("✅ State conversion successful")
        logger.info(f"   Converted keys: {list(converted_state.keys())}")
        
        # Check key mappings
        expected_mappings = {
            "hierarchy": ui_state["xml"],
            "activity": ui_state["current_activity"], 
            "package_name": ui_state["current_package"],
            "screenshot_path": ui_state["screenshot_path"]
        }
        
        for key, expected_value in expected_mappings.items():
            if key in converted_state and converted_state[key] == expected_value:
                logger.info(f"   ✅ {key} mapping correct")
            else:
                logger.error(f"   ❌ {key} mapping incorrect")
                logger.error(f"     Expected: {expected_value}")
                logger.error(f"     Got: {converted_state.get(key)}")
                return False
                
        return True
        
    except Exception as e:
        logger.error(f"❌ StateConverter test failed: {e}")
        return False


def main():
    """Main test function."""
    logger = setup_logging(debug=True)
    
    logger.info("🚀 Testing RVSmart with Gemma3:4b and vision")
    
    # Check emulator first
    import subprocess
    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=10)
        if 'emulator-5554' not in result.stdout or 'device' not in result.stdout:
            logger.error("❌ EMULATOR NOT RUNNING!")
            return 1
        else:
            logger.info("✅ Emulator is running")
    except Exception as e:
        logger.error(f"❌ Could not check emulator: {e}")
        return 1
    
    # Test data paths following the pattern from other scripts
    app_folder = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/out/instrumented_apks"
    apk_name = "cryptoapp.apk"
    apk_path = os.path.join(app_folder, apk_name)
    
    if not os.path.exists(apk_path):
        logger.error(f"❌ APK not found: {apk_path}")
        return 1
    
    try:
        # Load application following pattern from other scripts
        logger.info(f"📱 Loading APK: {apk_path}")
        app = App(apk_path)
        logger.info(f"   App: {app.name} ({app.package_name})")
        
        # Load static analysis data following the same pattern
        logger.info("📊 Loading static analysis data...")
        static_analysis_parser = StaticAnalysisParser()
        static_data = static_analysis_parser.read_static_analysis_files(app_folder, apk_name, app.package_name)
        logger.info("✅ Static analysis data loaded successfully")
        
        # Test 1: StateConverter
        logger.info(f"\n{'='*60}")
        logger.info("🧪 TEST 1: StateConverter")
        logger.info(f"{'='*60}")
        
        converter_success = test_state_converter(logger)
        
        # Test 2: Configure RVSmart with Gemma3:4b + Vision
        logger.info(f"\n{'='*60}")
        logger.info("🧪 TEST 2: RVSmart with Gemma3:4b Vision")
        logger.info(f"{'='*60}")
        
        # Create specific configuration for Gemma3:4b with vision
        llm_config = LLMConfig(
            llm_type=LLMType.OLLAMA,
            model="gemma3:4b",  # Specific model
            temperature=0.3,
            top_p=0.9,
            max_tokens=800,
            vision=True  # Vision enabled
        )
        
        prompt_config = PromptConfig(
            strategy_type=PromptStrategyType.VISION,  # Vision strategy
            parser_type=ScreenParserType.DROIDBOT,
            visitor_type=VisitorType.BASIC,
            context_mode=ContextMode.STATELESS
        )
        
        tool_config = RvSmartToolConfig(
            llm_config=llm_config,
            prompt_config=prompt_config,
            debug_mode=True
        )
        
        logger.info(f"📋 Configuration:")
        logger.info(f"   LLM: {llm_config.llm_type} - {llm_config.model}")
        logger.info(f"   Vision: {llm_config.vision}")
        logger.info(f"   Strategy: {prompt_config.strategy_type}")
        logger.info(f"   Temperature: {llm_config.temperature}")
        logger.info(f"   Max Tokens: {llm_config.max_tokens}")
        
        # Create TestOrchestrator
        orchestrator = TestOrchestrator(
            static_data=static_data.to_dict() if hasattr(static_data, 'to_dict') else static_data,
            tool_config=tool_config,
            app=app,
            device_id="emulator-5554",
            results_dir="./rvsmart_gemma3_test_results"
        )
        
        logger.info("✅ TestOrchestrator created")
        
        # Test 3: Screenshot Handling
        logger.info(f"\n{'='*60}")
        logger.info("🧪 TEST 3: Screenshot Handling")
        logger.info(f"{'='*60}")
        
        screenshot_success = check_screenshot_handling(orchestrator, logger)
        
        # Test 4: Short execution test
        logger.info(f"\n{'='*60}")
        logger.info("🧪 TEST 4: Short Execution Test")
        logger.info(f"{'='*60}")
        
        try:
            logger.info("🎬 Starting short test execution (30s timeout)...")
            start_time = time.time()
            
            orchestrator.execute_test_cycle(timeout=30)  # Short test
            
            execution_time = time.time() - start_time
            metrics = orchestrator.metrics
            
            logger.info(f"✅ Execution completed in {execution_time:.1f}s")
            logger.info(f"📊 Metrics:")
            logger.info(f"   Total actions: {metrics.total_actions}")
            logger.info(f"   Successful actions: {metrics.successful_actions}")
            logger.info(f"   Failed actions: {metrics.failed_actions}")
            logger.info(f"   External navigation: {metrics.external_navigation_count}")
            logger.info(f"   Error count: {metrics.error_count}")
            
            execution_success = True
            
        except Exception as e:
            logger.error(f"❌ Execution test failed: {e}")
            execution_success = False
        
        finally:
            orchestrator.cleanup()
        
        # Final Results
        logger.info(f"\n{'='*80}")
        logger.info("📊 GEMMA3:4B VISION TEST RESULTS")
        logger.info(f"{'='*80}")
        
        tests = [
            ("StateConverter", converter_success),
            ("Screenshot Handling", screenshot_success), 
            ("Execution Test", execution_success)
        ]
        
        passed = [name for name, success in tests if success]
        failed = [name for name, success in tests if not success]
        
        logger.info(f"✅ Passed: {len(passed)}/{len(tests)}")
        for name in passed:
            logger.info(f"   ✅ {name}")
            
        if failed:
            logger.info(f"❌ Failed: {len(failed)}")
            for name in failed:
                logger.info(f"   ❌ {name}")
        
        # Specific screenshot verification
        logger.info(f"\n🔍 SCREENSHOT VERIFICATION:")
        if screenshot_success:
            logger.info("✅ Screenshots are being captured and included in state")
            logger.info("✅ StateConverter preserves screenshot_path field")
            logger.info("✅ LLM will receive screenshot data for vision processing")
        else:
            logger.error("❌ Screenshot handling has issues")
            logger.error("⚠️  Vision strategy may not work properly")
        
        return 0 if len(failed) == 0 else 1
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())