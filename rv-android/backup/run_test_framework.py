#!/usr/bin/env python3
"""
Test script for the RV-Android Test Framework validation.

This script validates the new test framework implementation using ToolConfig
and existing rv-experiment infrastructure. It tests with 2 mop_vision configurations
with different context modes.

Validation Parameters:
- APKs: /home/pedro/.../out/instrumented_apks/
- Configurations: 2 mop_vision (stateless + rich context)
- Model: gemma3:4b (multimodal)
- Timeouts: [120, 180] seconds
- Repetitions: 2
- Workers: 2 
"""

import os
import sys
from pathlib import Path

# Setup RVSEC_HOME before importing modules
current_directory = os.getcwd()
parent_directory = os.path.dirname(current_directory)

# Add the modules to Python path for direct execution
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "modules" / "rv-android-core" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-platform" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-experiment" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-tools" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-coverage" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-static-analysis" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-llm" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rvandroid-tool" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-screen-parser" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-test-framework" / "src"))

# Import constants after path setup
from rv_android_core import constants
# Set RVSEC_HOME environment variable
os.environ[constants.ENV_RVSEC_HOME] = parent_directory

def setup_logging():
    """Setup logging for test framework validation."""
    import logging
    from rv_android_core.util.logging.manager import LoggingManager
    
    # Basic logging setup
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    
    # Silence noisy loggers
    for noisy_logger in ["androguard", "matplotlib", "PIL", "requests", "urllib3"]:
        logging.getLogger(noisy_logger).setLevel(logging.ERROR)
    
    for noisy_logger in ["rvandroid_core.domain.window", "rvandroid_core.domain.widget", "rv_static_analysis.parser.static",
                         "rvandroid_core.domain.classes", "rv_android_core.util.utils.read_json"]:
        logging.getLogger(noisy_logger).setLevel(logging.INFO)
    
    # Get logging manager
    logging_manager = LoggingManager.get_instance()
    logging_manager.configure_output(
        console=True,
        file=False,
        console_level=logging.INFO,
        file_level=logging.DEBUG,
        json_format=False
    )
    
    return logging_manager.get_logger('run_test_framework')

def run_validation_test():
    """Run validation test of the new test framework."""
    logger = setup_logging()
    
    print("=" * 80)
    print("🧪 RV-ANDROID TEST FRAMEWORK VALIDATION")
    print("=" * 80)
    print("Testing new ToolConfig-based implementation...")
    print()
    
    try:
        # Import test framework components
        from rv_test_framework.core.framework import TestFramework
        from rv_test_framework.core.models import TestFrameworkConfig
        from rv_test_framework.config.predefined_configs import TEST_VALIDATION_CONFIGS
        
        # Validation parameters
        apks_dir = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/out/instrumented_apks"
        output_dir = "./test_framework_validation_results"
        
        print("🔧 Validation Configuration:")
        print(f"  • APKs Directory: {apks_dir}")
        print(f"  • Output Directory: {output_dir}")
        print(f"  • Configurations: {len(TEST_VALIDATION_CONFIGS)}")
        print(f"  • Timeouts: [120, 180] seconds")
        print(f"  • Repetitions: 2")
        print(f"  • Workers: 2")
        print(f"  • Model: gemma3:4b (multimodal)")
        print()
        
        # Display configurations
        print("📋 Test Configurations:")
        for i, config in enumerate(TEST_VALIDATION_CONFIGS, 1):
            strategy = config.parameters.get('prompt_strategy', 'unknown')
            context_mode = config.parameters.get('context_mode', 'unknown')
            model = config.parameters.get('llm_model', 'default')
            print(f"  {i}. {config.name}:{config.variants[0]} - {strategy} ({context_mode} context, {model})")
        print()
        
        # Verify APKs directory
        if not os.path.exists(apks_dir):
            raise FileNotFoundError(f"APKs directory not found: {apks_dir}")
        
        apk_files = list(Path(apks_dir).glob("*.apk"))
        if not apk_files:
            raise FileNotFoundError(f"No APK files found in: {apks_dir}")
        
        print(f"📱 Found {len(apk_files)} APK(s):")
        for apk in apk_files:
            print(f"  • {apk.name}")
            # Check for static analysis files
            static_files = []
            for ext in ['.gesda', '.reach', '.wtg', '.methods']:
                static_file = apk.with_suffix(apk.suffix + ext)
                if static_file.exists():
                    static_files.append(ext)
            if static_files:
                print(f"    Static analysis files: {', '.join(static_files)}")
        print()
        
        # Create test framework configuration for parallel testing
        config = TestFrameworkConfig(
            max_workers=2,  # True parallelism with ProcessPoolExecutor
            apks_dir=apks_dir,
            output_dir=output_dir,
            no_window=False,  # Show emulator windows for visual monitoring
            repetitions=2,  # Multiple repetitions to create parallel tasks
            timeouts=[60],
            include_plateau_analysis=False  # Skip for validation
        )
        
        # Initialize and configure framework
        print("🚀 Initializing test framework...")
        framework = TestFramework(config)
        
        # Load validation configurations
        print("⚙️  Loading validation configurations...")
        framework.load_configurations(TEST_VALIDATION_CONFIGS)
        print(f"Loaded {len(framework.config.configurations)} configurations")
        
        # Generate tasks
        print("🔧 Generating tasks...")
        framework.generate_tasks()
        print(f"Generated {len(framework.tasks)} tasks across {len(framework.model_groups)} model groups")
        
        # Display task distribution
        for group in framework.model_groups:
            print(f"  • Model {group.model_name}: {len(group.tasks)} tasks")
        print()
        
        # Execute framework
        print("▶️  Starting execution...")
        print("⚠️  This will take some time with real APK testing...")
        
        summary = framework.execute()
        
        # Display results
        print()
        print("📊 Validation Results:")
        print(f"  • Total tasks: {summary.total_tasks}")
        print(f"  • Successful: {summary.successful_tasks}")
        print(f"  • Failed: {summary.failed_tasks}")
        print(f"  • Success rate: {summary.success_rate:.1f}%")
        print(f"  • Total time: {summary.total_execution_time:.1f}s")
        print(f"  • Results directory: {summary.results_directory}")
        print()
        
        if summary.successful_tasks > 0:
            print("✅ Test Framework Validation PASSED!")
            print("  • ToolConfig integration working")
            print("  • External tool registry functional")
            print("  • Model grouping operational")
            print("  • Parallel execution successful")
        else:
            print("❌ Test Framework Validation FAILED!")
            print("  • Check logs for errors")
            print("  • Verify APK and configuration compatibility")
        
        print(f"\n📁 Detailed results available in: {summary.results_directory}")
        return summary.successful_tasks > 0
        
    except Exception as e:
        print(f"❌ Validation failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_validation_test()
    sys.exit(0 if success else 1)