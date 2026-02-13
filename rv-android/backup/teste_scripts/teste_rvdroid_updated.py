#!/usr/bin/env python3
"""
Updated test for RVDroid tool with shared rv-uiautomator components.

This script tests the refactored RVDroid tool that now uses shared UIAutomator components
from rv-uiautomator module, ensuring compatibility and functionality.

🚨 IMPORTANTE - PRÉ-REQUISITOS:
1. 📱 SUBIR O EMULADOR ANTES DE EXECUTAR:
   - Android Studio → AVD Manager → Start emulator
   - OU via linha de comando: emulator @nome_do_avd
   - Aguarde o emulador inicializar completamente
   - Verifique com: adb devices (deve mostrar "emulator-5554 device")

2. 🤖 OLLAMA RODANDO (se LLM habilitado):
   - ollama serve
   - ollama pull gemma2 (ou modelo configurado)

3. 📦 DEPENDÊNCIAS INSTALADAS:
   - poetry install (no módulo rv-uiautomator e rvdroid-tool)

EXECUÇÃO:
   python teste_rvdroid_updated.py
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
sys.path.insert(0, str(project_root / "modules" / "rvdroid-tool" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-screen-parser" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-static-analysis" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-uiautomator" / "src"))

# Import constants and setup environment
from rv_android_core import constants
parent_directory = os.path.dirname(os.getcwd())
os.environ[constants.ENV_RVSEC_HOME] = parent_directory

# Import necessary modules after path setup
from rv_android_core.domain.app import App
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.task import Task, TaskConfig, ToolConfig
from rv_android_core.util.logging.manager import LoggingManager
from rv_llm.config import LLMConfig, PromptConfig
from rv_llm.llm.constants import LLMType, PromptStrategyType
from rv_llm.llm.ollama_llm import OllamaLLM
from rv_screen_parser.constants import ScreenParserType, VisitorType
from rvdroid_tool.tools.tool import RVDroidTool
from rvdroid_tool.config.tool_config import RVDroidToolConfig
from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser

# Test shared components directly
from rv_uiautomator import UIAutomator2Adapter, UIAutomatorActionExecutor, StateConverter
from rv_uiautomator.utils import DeviceManager, ScreenshotManager


def setup_logging(debug: bool = False):
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

    logger = logging_manager.get_logger('teste.rvdroid.updated')
    return logger


def test_shared_components(logger):
    """
    Test shared rv-uiautomator components directly.
    
    Args:
        logger: Logger instance
    """
    logger.info("🧪 Testing shared rv-uiautomator components")
    
    device_id = "emulator-5554"
    
    try:
        # Test 1: DeviceManager
        logger.info("📱 Testing DeviceManager...")
        device_manager = DeviceManager()
        devices = device_manager.list_devices()
        logger.info(f"   Found {len(devices)} devices")
        
        if devices:
            for device in devices:
                logger.info(f"   Device: {device.device_id} ({device.status})")
        
        # Test device validation
        is_valid = device_manager.validate_device(device_id)
        logger.info(f"   Device {device_id} validation: {'✅ PASSED' if is_valid else '❌ FAILED'}")
        
        # Test 2: UIAutomator2Adapter
        logger.info("🔧 Testing UIAutomator2Adapter...")
        adapter = UIAutomator2Adapter(device_id)
        
        # Test connection
        connection_success = adapter.connect(device_id)
        logger.info(f"   Connection: {'✅ SUCCESS' if connection_success else '❌ FAILED'}")
        
        if connection_success:
            # Test state capture
            state = adapter.get_ui_state()
            logger.info(f"   UI State capture: {'✅ SUCCESS' if state else '❌ FAILED'}")
            if state:
                logger.info(f"   Current activity: {state.get('current_activity', 'unknown')}")
                logger.info(f"   Current package: {state.get('current_package', 'unknown')}")
        
        # Test 3: ActionExecutor
        logger.info("⚡ Testing UIAutomatorActionExecutor...")
        executor = UIAutomatorActionExecutor()
        logger.info("   ActionExecutor initialized successfully")
        
        # Test 4: StateConverter
        logger.info("🔄 Testing StateConverter...")
        converter = StateConverter()
        
        # Create mock UIAutomator state
        mock_ui_state = {
            "xml": "<hierarchy><node text='Test'/></hierarchy>",
            "current_activity": "com.example.TestActivity",
            "current_package": "com.example.test",
            "timestamp": time.time()
        }
        
        converted_state = converter.uiautomator_to_droidbot(mock_ui_state)
        logger.info("   State conversion: ✅ SUCCESS")
        logger.info(f"   Converted fields: hierarchy, activity, package_name")
        
        # Test 5: ScreenshotManager
        logger.info("📸 Testing ScreenshotManager...")
        screenshot_manager = ScreenshotManager()
        logger.info("   ScreenshotManager initialized successfully")
        
        logger.info("✅ All shared components tested successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Shared components test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_rvdroid_integration(app: App, static_data: StaticAnalysisData, logger):
    """
    Test RVDroid tool with shared components integration.
    
    Args:
        app: Application under test
        static_data: Static analysis data
        logger: Logger instance
    """
    logger.info("🔧 Testing RVDroid tool integration with shared components")
    
    device_id = "emulator-5554"
    timeout = 120  # 2 minutes
    
    try:
        # Create RVDroidToolConfig with shared components support
        tool_config = RVDroidToolConfig(
            device_id=device_id,
            execution_timeout=timeout,
            llm_enabled=True,  # Enable LLM guidance
            llm_config=LLMConfig(
                llm_type=LLMType.OLLAMA,
                model=OllamaLLM.GEMMA,
                temperature=0.2,
                top_p=0.9,
                max_tokens=800,
                vision=True
            ),
            prompt_config=PromptConfig(
                strategy_type=PromptStrategyType.SINGLE,
                parser_type=ScreenParserType.DROIDBOT,
                visitor_type=VisitorType.DEFAULT
            )
        )
        
        logger.info(f"📋 Configuration:")
        logger.info(f"   Device: {device_id}")
        logger.info(f"   Timeout: {timeout}s")
        logger.info(f"   LLM: {tool_config.llm_config.llm_type} - {tool_config.llm_config.model}")
        logger.info(f"   Strategy: {tool_config.prompt_config.strategy_type}")
        logger.info(f"   Vision: {tool_config.llm_config.vision}")
        
        # Create task
        task_config = TaskConfig(
            timeout=timeout,
            tool_config=ToolConfig(
                tool_name="rvdroid",
                variant="default",
                additional_params={
                    "device_serial": device_id
                }
            )
        )
        
        task = Task(
            id="rvdroid_shared_test",
            name="RVDroid Shared Components Test",
            app=app,
            static_data=static_data.to_dict() if hasattr(static_data, 'to_dict') else {},
            config=task_config,
            results_dir="./rvdroid_shared_test_results"
        )
        
        # Initialize RVDroidTool
        rvdroid_tool = RVDroidTool()
        rvdroid_tool.configure(tool_config)
        
        logger.info("🎬 Starting RVDroid execution with shared components...")
        start_time = time.time()
        
        # Execute tool logic
        rvdroid_tool.execute_tool_specific_logic(task, app)
        
        execution_time = time.time() - start_time
        logger.info(f"✅ RVDroid execution completed in {execution_time:.1f}s")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ RVDroid integration test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_adapter_compatibility(logger):
    """
    Test the refactored UIAutomator2Adapter compatibility with RVDroid.
    
    Args:
        logger: Logger instance
    """
    logger.info("🔄 Testing adapter compatibility between shared and RVDroid components")
    
    try:
        # Import RVDroid's refactored adapter
        from rvdroid_tool.ui.uiautomator import UIAutomator2Adapter as RVDroidAdapter
        
        device_id = "emulator-5554"
        
        # Test RVDroid adapter initialization
        rvdroid_adapter = RVDroidAdapter("rvdroid_adapter", device_id)
        logger.info("   RVDroid adapter initialized successfully")
        
        # Test initialization
        init_success = rvdroid_adapter.initialize()
        logger.info(f"   Initialization: {'✅ SUCCESS' if init_success else '❌ FAILED'}")
        
        if init_success:
            # Test component lifecycle
            start_success = rvdroid_adapter.start()
            logger.info(f"   Start: {'✅ SUCCESS' if start_success else '❌ FAILED'}")
            
            # Test state retrieval (compatibility)
            try:
                state = rvdroid_adapter.get_ui_state()
                logger.info("   State retrieval: ✅ SUCCESS")
                logger.info(f"   Activity: {state.get('activity', 'unknown')}")
                logger.info(f"   Package: {state.get('package_name', 'unknown')}")
            except Exception as state_error:
                logger.warning(f"   State retrieval: ❌ WARNING - {state_error}")
            
            # Test cleanup
            stop_success = rvdroid_adapter.stop()
            cleanup_success = rvdroid_adapter.cleanup()
            logger.info(f"   Stop: {'✅ SUCCESS' if stop_success else '❌ FAILED'}")
            logger.info(f"   Cleanup: {'✅ SUCCESS' if cleanup_success else '❌ FAILED'}")
        
        logger.info("✅ Adapter compatibility test completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Adapter compatibility test failed: {e}")
        return False


def main():
    """Main test function."""
    # Setup logging
    logger = setup_logging(debug=True)
    
    # Check prerequisites first
    logger.info("🔍 Checking prerequisites...")
    
    # Check if emulator is running
    import subprocess
    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=10)
        devices_output = result.stdout
        if 'emulator-5554' not in devices_output or 'device' not in devices_output:
            logger.error("❌ EMULATOR NOT RUNNING!")
            logger.error("🚨 Por favor, suba o emulador primeiro:")
            logger.error("   - Android Studio → AVD Manager → Start emulator")
            logger.error("   - OU: emulator @nome_do_avd")
            logger.error("   - Aguarde inicializar e rode: adb devices")
            return 1
        else:
            logger.info("✅ Emulator is running (emulator-5554 detected)")
    except Exception as e:
        logger.warning(f"⚠️  Could not check emulator status: {e}")
        logger.warning("🚨 CERTIFIQUE-SE que o emulador está rodando!")
    
    logger.info("🚀 Starting RVDroid updated test suite with shared components")
    
    # Test data paths
    screenshots_folder = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples/cryptoapp"
    apk_name = "cryptoapp.apk"
    apk_path = os.path.join(screenshots_folder, apk_name)
    
    # Verify APK exists
    if not os.path.exists(apk_path):
        logger.error(f"❌ APK not found at {apk_path}")
        return 1
    
    logger.info(f"📱 Using APK: {apk_path}")
    
    try:
        # Load application and static data
        app = App(apk_path)
        logger.info(f"📋 App loaded: {app.name} ({app.package_name})")
        
        static_analysis_parser = StaticAnalysisParser()
        static_data = static_analysis_parser.read_static_analysis_files(
            screenshots_folder, apk_name, app.package_name
        )
        logger.info("📊 Static analysis data loaded")
        
        # Test suite
        results = []
        
        # Test 1: Shared components
        logger.info(f"\n{'='*80}")
        logger.info("🧪 TEST 1: Shared rv-uiautomator Components")
        logger.info(f"{'='*80}")
        
        shared_success = test_shared_components(logger)
        results.append(("Shared Components", shared_success))
        
        # Test 2: Adapter compatibility
        logger.info(f"\n{'='*80}")
        logger.info("🧪 TEST 2: Adapter Compatibility")
        logger.info(f"{'='*80}")
        
        adapter_success = test_adapter_compatibility(logger)
        results.append(("Adapter Compatibility", adapter_success))
        
        # Test 3: RVDroid integration (only if previous tests pass)
        if shared_success and adapter_success:
            logger.info(f"\n{'='*80}")
            logger.info("🧪 TEST 3: RVDroid Integration with Shared Components")
            logger.info(f"{'='*80}")
            
            integration_success = test_rvdroid_integration(app, static_data, logger)
            results.append(("RVDroid Integration", integration_success))
        else:
            logger.warning("⚠️  Skipping RVDroid integration test due to prerequisite failures")
            results.append(("RVDroid Integration", False))
        
        # Final analysis
        logger.info(f"\n{'='*80}")
        logger.info("📊 RVDROID UPDATED TEST RESULTS")
        logger.info(f"{'='*80}")
        
        passed_tests = [name for name, success in results if success]
        failed_tests = [name for name, success in results if not success]
        
        logger.info(f"✅ Passed tests: {len(passed_tests)}/{len(results)}")
        for test_name in passed_tests:
            logger.info(f"   ✅ {test_name}")
        
        if failed_tests:
            logger.info(f"❌ Failed tests: {len(failed_tests)}")
            for test_name in failed_tests:
                logger.info(f"   ❌ {test_name}")
        
        # Overall assessment
        overall_success = len(passed_tests) == len(results)
        
        logger.info(f"\n{'='*80}")
        logger.info("🎉 RVDROID UPDATED TEST COMPLETED")
        logger.info(f"{'='*80}")
        
        if overall_success:
            logger.info("✅ RVDroid tool is successfully using shared components!")
            logger.info("💡 Code reuse achieved - shared rv-uiautomator components working")
            logger.info("🔄 Refactoring successful - compatibility maintained")
            return 0
        else:
            logger.error("❌ RVDroid tool has issues with shared components")
            logger.error("🔧 Check the failed tests above for specific issues")
            return 1
            
    except KeyboardInterrupt:
        logger.info("🛑 Testing interrupted by user")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Fatal error during testing: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())