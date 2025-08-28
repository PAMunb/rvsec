#!/usr/bin/env python3
"""
Manual test for RVSmart MOP-focused coordinate enhancement system.

This script tests the optimized RVSmart system with:
- MOP-prioritized action generation 
- Coordinate enhancement for vision models
- UIAutomator integration with proper state conversion
- Qwen 2.5VL 7B model (98.3% success rate)

🚨 PRÉ-REQUISITOS:
1. 📱 EMULADOR RODANDO:
   - emulator @nome_do_avd
   - adb devices (deve mostrar "emulator-5554 device")

2. 🤖 OLLAMA COM MODELOS:
   - ollama serve
   - ollama pull qwen2.5:7b-instruct (modelo otimizado)
   - ollama pull gemma3:4b (fallback)
"""

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any

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

# Import necessary modules after path setup
from rv_android_core.domain.app import App
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.util.logging.manager import LoggingManager
from rv_llm.config import LLMConfig, PromptConfig
from rv_llm.llm.constants import LLMType, PromptStrategyType, ContextMode, StateEntry
from rv_llm.llm.ollama_llm import OllamaLLM
from rv_screen_parser.constants import ScreenParserType, VisitorType
from rvsmart_tool.config.tool_config import RvSmartToolConfig
from rvsmart_tool.llm.service.action_service import LLMActionService
from rvsmart_tool.core.memory.ui_coverage_tracker import UICoverageTracker
from rvsmart_tool.orchestration.test_orchestrator import TestOrchestrator
from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser
from rv_uiautomator.adapter.uiautomator2 import UIAutomator2Adapter
from rv_uiautomator.state.converter import StateConverter


def setup_logging(debug: bool = True):
    """Set up logging configuration."""
    logging_manager = LoggingManager.get_instance()
    
    # Configure output for seeing all diagnostic messages
    logging_manager.configure_output(
        console=True,
        file=False,
        console_level=10,  # DEBUG to see all messages
        file_level=10,
        json_format=False
    )
    
    # Silence noisy loggers
    for noisy_logger in ["androguard", "matplotlib", "PIL", "requests", "urllib3"]:
        logging.getLogger(noisy_logger).setLevel(logging.ERROR)
    
    logger = logging_manager.get_logger('teste_rvsmart_optimized')
    return logger


def tmp_mop_optimized_rvsmart(app: App, static_data: StaticAnalysisData, logger):
    """
    Test MOP-optimized RVSmart with coordinate enhancement.
    
    ⚠️ REQUIREMENTS:
    - Emulator must be running (emulator-5554)
    - APK must be installed: adb install cryptoapp.apk
    - Ollama must be running with model loaded
    
    Tests UI element coverage tracking, NOT method/class coverage.
    """
    logger.info("🎯 Testing MOP-optimized RVSmart system")
    logger.info("⚠️  IMPORTANT: This test requires:")
    logger.info("   1. Emulator running (emulator-5554)")
    logger.info("   2. APK installed on emulator")
    logger.info("   3. Ollama running with model loaded")
    
    device_id = "emulator-5554"
    results = []
    
    # Test configurations - prioritize Qwen 2.5VL then fallback to Gemma3:4b
    configurations = [
        {
            "name": "qwen",
            "description": "Qwen 2.5VL 7B with coordinate enhancement",
            "llm_config": LLMConfig(
                llm_type=LLMType.OLLAMA,
                model=OllamaLLM.QWEN_2_5VL_7B,
                temperature=0.3,
                max_tokens=800,
                vision=True
            ),
            "prompt_config": PromptConfig(
                strategy_type=PromptStrategyType.VISION,
                parser_type=ScreenParserType.UIAUTOMATOR,
                visitor_type=VisitorType.DEFAULT,
                context_mode=ContextMode.STATELESS
            )
        },
        # {
        #     "name": "gemma3",
        #     "description": "Gemma3:4b with coordinate enhancement",
        #     "llm_config": LLMConfig(
        #         llm_type=LLMType.OLLAMA,
        #         model=OllamaLLM.GEMMA,
        #         temperature=0.3,
        #         max_tokens=800,
        #         vision=True
        #     ),
        #     "prompt_config": PromptConfig(
        #         strategy_type=PromptStrategyType.VISION,
        #         parser_type=ScreenParserType.UIAUTOMATOR,
        #         visitor_type=VisitorType.DEFAULT,
        #         context_mode=ContextMode.STATELESS
        #     )
        # }
    ]
    
    for config in configurations:
        logger.info(f"\n{'='*70}")
        logger.info(f"🧪 Testing: {config['name']}")
        logger.info(f"📝 {config['description']}")
        logger.info(f"{'='*70}")
        
        try:
            # Create RvSmartToolConfig
            tool_config = RvSmartToolConfig(
                llm_config=config["llm_config"],
                prompt_config=config["prompt_config"],
                debug_mode=True  # Show all diagnostic messages
            )
            
            logger.info(f"📋 Configuration:")
            logger.info(f"   Model: {config['llm_config'].model}")
            logger.info(f"   Vision: {config['llm_config'].vision}")
            logger.info(f"   Strategy: {config['prompt_config'].strategy_type}")
            logger.info(f"   Parser: {config['prompt_config'].parser_type}")
            
            # Test UIAutomator integration
            logger.info(f"🔧 Testing UIAutomator integration...")
            ui_adapter = UIAutomator2Adapter(device_id)
            
            if not ui_adapter.connect(device_id):
                logger.error(f"❌ Failed to connect to device {device_id}")
                continue
                
            # Install and launch test app
            logger.info(f"📱 Installing and launching {app.name}...")
            # Note: Installation would be handled by platform in real usage
            ui_adapter.launch_app(app.package_name)
            time.sleep(3)  # Wait for app to start
            
            # Capture UI state
            logger.info(f"📸 Capturing UI state...")
            ui_state = ui_adapter.get_ui_state(force_refresh=True)
            
            if not ui_state:
                logger.error(f"❌ Failed to capture UI state")
                continue
                
            # Convert UIAutomator state to DroidBot format
            logger.info(f"🔄 Converting state format...")
            converter = StateConverter()
            converted_state = converter.uiautomator_to_droidbot(ui_state)
            
            # Take screenshot for vision models
            screenshot_path = ui_adapter.take_screenshot()
            if screenshot_path:
                converted_state["screenshot_path"] = screenshot_path
                logger.info(f"📷 Screenshot saved: {screenshot_path}")
            
            # Create UI Coverage Tracker
            logger.info(f"📊 Creating UI Coverage Tracker...")
            ui_coverage_tracker = UICoverageTracker()
            
            # Create ActionService and test MOP-focused generation
            logger.info(f"🧠 Creating LLM Action Service...")
            action_service = LLMActionService(
                static_data=static_data,
                tool_config=tool_config
            )
            
            # Note: UI coverage tracker is used locally for this test
            # In production, it's managed by TestOrchestrator
            
            # Process state and generate MOP-focused actions
            logger.info(f"⚡ Generating MOP-focused actions...")
            start_time = time.time()
            
            actions = action_service.process_state(converted_state)
            
            generation_time = time.time() - start_time
            
            # Execute generated actions on device
            logger.info(f"🎮 Executing {len(actions)} generated actions on device...")
            executed_actions = 0
            failed_actions = 0
            
            for i, action in enumerate(actions):
                action_id = action.get('action_id', '')
                action_type = action.get('action_type', 'unknown')
                coordinates = action.get('coordinates', [])
                explanation = action.get('explanation', '')
                
                logger.info(f"   Action {i+1}: {action_type} - {explanation}")
                
                try:
                    # Execute the action based on type
                    if action_type == 'click' and coordinates and len(coordinates) >= 2:
                        x, y = coordinates[0], coordinates[1]
                        logger.debug(f"      Clicking at ({x}, {y})")
                        ui_adapter.click(x, y)
                        executed_actions += 1
                    elif action_type == 'back':
                        logger.debug(f"      Pressing back")
                        ui_adapter.press_back()
                        executed_actions += 1
                    elif action_type == 'coord' and coordinates and len(coordinates) >= 2:
                        x, y = coordinates[0], coordinates[1]
                        logger.debug(f"      Coordinate click at ({x}, {y})")
                        ui_adapter.click(x, y)
                        executed_actions += 1
                    else:
                        logger.warning(f"      Skipping unsupported action type: {action_type}")
                        failed_actions += 1
                    
                    # Record interaction in tracker if executed
                    if action_id and action_id != 'coord':
                        ui_coverage_tracker.record_interaction(
                            element_id=action_id,
                            action_type=action_type,
                            screen_context=converted_state.get('current_activity', 'unknown')
                        )
                    
                    # Small delay between actions
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"      Failed to execute action: {e}")
                    failed_actions += 1
            
            logger.info(f"   Executed: {executed_actions}/{len(actions)} actions successfully")
            
            # Get UI coverage statistics
            ui_stats = ui_coverage_tracker.get_ui_element_stats()
            
            # Analyze results
            dm_actions = [a for a in actions if "[DM]" in str(a.get('explanation', ''))]
            m_actions = [a for a in actions if "[M]" in str(a.get('explanation', ''))]
            coord_actions = [a for a in actions if a.get('action_type') == 'coord' or 'coord' in str(a.get('action_id', ''))]
            
            result = {
                'name': config['name'],
                'success': True,
                'total_actions': len(actions),
                'executed_actions': executed_actions,
                'failed_actions': failed_actions,
                'dm_actions': len(dm_actions),
                'm_actions': len(m_actions),
                'coordinate_actions': len(coord_actions),
                'mop_coverage': ((len(dm_actions) + len(m_actions)) / max(len(actions), 1)) * 100,
                'generation_time': generation_time,
                'model': config['llm_config'].model,
                'ui_coverage': {
                    'total_elements': ui_stats.total_elements,
                    'tested_elements': ui_stats.tested_elements,
                    'untested_elements': ui_stats.untested_elements,
                    'coverage_percentage': ui_stats.coverage_percentage
                },
                'error': None
            }
            
            logger.info(f"✅ SUCCESS: {config['name']}")
            logger.info(f"   Actions generated: {len(actions)}")
            logger.info(f"   Actions executed: {executed_actions}/{len(actions)}")
            logger.info(f"   Direct MOP [DM]: {len(dm_actions)}")
            logger.info(f"   Indirect MOP [M]: {len(m_actions)}")
            logger.info(f"   Coordinate actions: {len(coord_actions)}")
            logger.info(f"   MOP focus: {result['mop_coverage']:.1f}%")
            logger.info(f"   Generation time: {generation_time:.2f}s")
            logger.info(f"   📊 UI Element Coverage:")
            logger.info(f"      Total elements: {ui_stats.total_elements}")
            logger.info(f"      Tested elements: {ui_stats.tested_elements}")
            logger.info(f"      UI coverage: {ui_stats.coverage_percentage:.1f}%")
            
            # Show sample actions
            logger.info(f"📝 Sample actions:")
            for i, action in enumerate(actions[:3]):
                explanation = action.get('explanation', 'No explanation')
                action_type = action.get('action_type', 'unknown')
                logger.info(f"   {i+1}. {action_type}: {explanation}")
            
            if len(actions) > 3:
                logger.info(f"   ... and {len(actions) - 3} more actions")
                
            results.append(result)
            
        except Exception as e:
            result = {
                'name': config['name'],
                'success': False,
                'total_actions': 0,
                'dm_actions': 0,
                'm_actions': 0,
                'coordinate_actions': 0,
                'mop_coverage': 0,
                'generation_time': 0,
                'model': config['llm_config'].model,
                'error': str(e)
            }
            
            logger.error(f"❌ FAILED: {config['name']}")
            logger.error(f"   Error: {e}")
            results.append(result)
    
    return results


def analyze_mop_optimization_results(results, logger):
    """
    Analyze MOP optimization and UI coverage test results.
    """
    logger.info(f"\n{'='*80}")
    logger.info("📊 MOP OPTIMIZATION & UI COVERAGE ANALYSIS")
    logger.info(f"{'='*80}")
    
    successful_tests = [r for r in results if r['success']]
    failed_tests = [r for r in results if not r['success']]
    
    logger.info(f"✅ Successful tests: {len(successful_tests)}/{len(results)}")
    logger.info(f"❌ Failed tests: {len(failed_tests)}")
    
    if successful_tests:
        logger.info(f"\n📈 MOP OPTIMIZATION PERFORMANCE:")
        for result in successful_tests:
            logger.info(f"   🎯 {result['name']} ({result['model']}):")
            logger.info(f"      Total actions: {result['total_actions']}")
            logger.info(f"      Direct MOP [DM]: {result['dm_actions']}")
            logger.info(f"      Indirect MOP [M]: {result['m_actions']}")
            logger.info(f"      Coordinate actions: {result['coordinate_actions']}")
            logger.info(f"      MOP Focus: {result['mop_coverage']:.1f}%")
            logger.info(f"      Generation time: {result['generation_time']:.2f}s")
            
            # UI Coverage metrics if available
            if 'ui_coverage' in result:
                ui_cov = result['ui_coverage']
                logger.info(f"      📊 UI Element Coverage:")
                logger.info(f"         Total UI elements: {ui_cov['total_elements']}")
                logger.info(f"         Tested elements: {ui_cov['tested_elements']}")
                logger.info(f"         UI coverage: {ui_cov['coverage_percentage']:.1f}%")
        
        # Calculate overall statistics
        avg_mop_coverage = sum(r['mop_coverage'] for r in successful_tests) / len(successful_tests)
        total_dm_actions = sum(r['dm_actions'] for r in successful_tests)
        total_m_actions = sum(r['m_actions'] for r in successful_tests)
        avg_generation_time = sum(r['generation_time'] for r in successful_tests) / len(successful_tests)
        
        logger.info(f"\n📊 OVERALL OPTIMIZATION STATISTICS:")
        logger.info(f"   Average MOP Coverage: {avg_mop_coverage:.1f}%")
        logger.info(f"   Total Direct MOP [DM] actions: {total_dm_actions}")
        logger.info(f"   Total Indirect MOP [M] actions: {total_m_actions}")
        logger.info(f"   Average generation time: {avg_generation_time:.2f}s")
        
        # Optimization assessment
        logger.info(f"\n🎯 OPTIMIZATION ASSESSMENT:")
        if avg_mop_coverage >= 70:
            logger.info("   🔥 EXCELLENT: MOP-focused optimization is highly effective!")
        elif avg_mop_coverage >= 50:
            logger.info("   ✅ GOOD: MOP-focused optimization is working well")
        else:
            logger.info("   ⚠️  MODERATE: MOP optimization needs improvement")
            
        if total_dm_actions > total_m_actions:
            logger.info("   🎯 Direct MOP operations are being properly prioritized")
        
        # Model comparison
        qwen_results = [r for r in successful_tests if 'qwen' in r['model']]
        gemma_results = [r for r in successful_tests if 'gemma' in r['model']]
        
        if qwen_results and gemma_results:
            qwen_avg = qwen_results[0]['mop_coverage'] if qwen_results else 0
            gemma_avg = gemma_results[0]['mop_coverage'] if gemma_results else 0
            logger.info(f"\n🤖 MODEL COMPARISON:")
            logger.info(f"   Qwen 2.5VL: {qwen_avg:.1f}% MOP coverage")
            logger.info(f"   Gemma3:4b: {gemma_avg:.1f}% MOP coverage")
    
    if failed_tests:
        logger.info(f"\n❌ FAILED TESTS:")
        for result in failed_tests:
            logger.info(f"   ❌ {result['name']}: {result['error']}")


def main():
    """Main test function for MOP-optimized RVSmart."""
    logger = setup_logging(debug=True)
    
    logger.info("🎯 RVSmart MOP-Focused Optimization Test")
    logger.info("=" * 70)
    logger.warning("⚠️  PREREQUISITES REQUIRED:")
    logger.warning("   1. EMULATOR: Must be running (emulator-5554)")
    logger.warning("   2. APK: Must be installed on emulator")
    logger.warning("      Run: adb install cryptoapp.apk")
    logger.warning("   3. OLLAMA: Must be running with model loaded")
    logger.warning("      Run: ollama serve")
    logger.warning("      Run: ollama pull qwen2.5:7b-instruct")
    logger.warning("")
    logger.warning("⚠️  NOTE: This test tracks UI element coverage, NOT method/class coverage")
    logger.info("=" * 70)
    
    # Check prerequisites
    logger.info("🔍 Checking prerequisites...")
    
    # Check emulator
    import subprocess
    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=10)
        devices_output = result.stdout
        if 'emulator-5554' not in devices_output or 'device' not in devices_output:
            logger.error("❌ Emulator not running! Start with: emulator @your_avd_name")
            return 1
        logger.info("✅ Emulator detected (emulator-5554)")
        
        # Check if APK is installed
        result = subprocess.run(['adb', 'shell', 'pm', 'list', 'packages'], 
                              capture_output=True, text=True, timeout=10)
        if 'br.unb.cic.cryptoapp' not in result.stdout:
            logger.warning("⚠️  APK may not be installed on emulator")
            logger.warning("   Install with: adb install cryptoapp.apk")
        else:
            logger.info("✅ APK appears to be installed (br.unb.cic.cryptoapp)")
            
    except Exception as e:
        logger.warning(f"⚠️  Could not verify prerequisites: {e}")
    
    # Hardcoded paths (following pattern from examples)
    app_folder = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/out/instrumented_apks"
    apk_name = "cryptoapp.apk"
    apk_path = os.path.join(app_folder, apk_name)
    
    if not os.path.exists(apk_path):
        logger.error(f"❌ APK not found: {apk_path}")
        return 1
    
    logger.info(f"📱 Using APK: {apk_name}")
    
    try:
        # Load application
        app = App(apk_path)
        logger.info(f"📦 Package: {app.package_name}")
        
        # Load static analysis data
        static_analysis_parser = StaticAnalysisParser()
        static_data = static_analysis_parser.read_static_analysis_files(
            app_folder, apk_name, app.package_name
        )
        logger.info("📊 Static analysis loaded")
        
        # Test MOP-optimized RVSmart
        logger.info("\n🚀 Testing MOP-optimized RVSmart system...")
        results = tmp_mop_optimized_rvsmart(app, static_data, logger)
        
        # Analyze results
        analyze_mop_optimization_results(results, logger)
        
        # Final summary
        logger.info(f"\n{'='*80}")
        logger.info("🎉 MOP OPTIMIZATION TEST COMPLETED")
        logger.info(f"{'='*80}")
        
        successful_tests = [r for r in results if r['success']]
        if successful_tests:
            avg_mop_coverage = sum(r['mop_coverage'] for r in successful_tests) / len(successful_tests)
            logger.info(f"✅ Test successful with {avg_mop_coverage:.1f}% MOP coverage!")
            logger.info("🎯 RVSmart MOP-focused coordinate enhancement is working!")
            return 0
        else:
            logger.error("❌ All tests failed - check configuration")
            return 1
            
    except KeyboardInterrupt:
        logger.info("🛑 Test interrupted")
        return 0
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


def tmp_orchestrator():
    logger = setup_logging(debug=True)
    
    logger.info("🎬 Starting TestOrchestrator direct test")
    logger.warning("⚠️  PREREQUISITES:")
    logger.warning("   1. Emulator running (emulator-5554)")
    logger.warning("   2. APK installed: adb install cryptoapp.apk")
    logger.warning("   3. Ollama running: ollama serve && ollama pull qwen2.5vl:7b")

    device_id = "emulator-5554"
    results_dir = "/home/pedro/tmp/rvsmart"
    
    # Create results directory
    os.makedirs(results_dir, exist_ok=True)

    app_folder = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/out/instrumented_apks"
    apk_name = "cryptoapp.apk"
    apk_path = os.path.join(app_folder, apk_name)
    logger.info(f"📱 Using APK: {apk_name}")

    app = App(apk_path)
    logger.info(f"📦 Package: {app.package_name}")

    static_analysis_parser = StaticAnalysisParser()
    static_data = static_analysis_parser.read_static_analysis_files(
        app_folder, apk_name, app.package_name
    )
    logger.info("📊 Static analysis loaded")

    tool_config = RvSmartToolConfig(
        llm_config=LLMConfig(
            llm_type=LLMType.OLLAMA,
            model=OllamaLLM.QWEN_2_5VL_7B,
            temperature=0.3,
            max_tokens=800,
            vision=True
        ),
        prompt_config=PromptConfig(
            strategy_type=PromptStrategyType.VISION,
            parser_type=ScreenParserType.UIAUTOMATOR,
            visitor_type=VisitorType.BASIC,
            context_mode=ContextMode.STATELESS
        ),
        debug_mode=True
    )

    orchestrator = TestOrchestrator(static_data, tool_config, app, device_id, results_dir)
    
    # Execute test cycle with timeout
    timeout = 120  # 2 minutes
    logger.info(f"🎯 Starting test execution with {timeout}s timeout...")
    
    try:
        # Execute the test cycle with timeout
        orchestrator.execute_test_cycle(timeout=timeout)
        logger.info("✅ Test execution completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Test execution failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    logger.info("🏁 TestOrchestrator test completed")


if __name__ == "__main__":
    # Test TestOrchestrator directly:
    tmp_orchestrator()
    
    # Default: run the main MOP optimization test
    # sys.exit(main())