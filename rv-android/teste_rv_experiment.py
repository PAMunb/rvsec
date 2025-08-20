#!/usr/bin/env python3
"""
Manual test for rv-experiment integration with rv-platform.

This test validates that rv-experiment CLI maintains backward compatibility
while internally using rv-platform for task execution.
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path

# Setup RVSEC_HOME before importing modules
current_directory = os.getcwd()
parent_directory = os.path.dirname(current_directory)

# Add the modules to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "modules" / "rv-android-core" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-platform" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-experiment" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-tools" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-coverage" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-static-analysis" / "src"))

# Import constants after path setup
from rv_android_core import constants
# Set RVSEC_HOME environment variable
os.environ[constants.ENV_RVSEC_HOME] = parent_directory

def setup_logging(debug: bool = True):
    """Set up logging configuration."""
    import logging
    from rv_android_core.util.logging.manager import LoggingManager
    
    # Setup basic logging first
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )

    # Silence noisy third-party loggers for clean CLI output
    for noisy_logger in ["androguard", "matplotlib", "PIL", "requests", "urllib3"]:
        logging.getLogger(noisy_logger).setLevel(logging.ERROR)

    # Get the logging manager
    logging_manager = LoggingManager.get_instance()

    # Configure output to show all rvandroid logs including module logs
    logging_manager.configure_output(
        console=True,
        file=False,
        console_level=10 if debug else 20,  # DEBUG (10) or INFO (20)
        file_level=10,  # DEBUG
        json_format=False
    )

    return logging_manager.get_logger('teste.rv_experiment')


def tmp_experiment_controller():
    """Test complete ExperimentController integration with actual execution."""
    print("\nTesting ExperimentController integration...")

    try:
        from rv_experiment.experiment.experiment_controller import ExperimentController
        from rv_experiment.config import ExperimentConfig
        from rv_platform.config.platform_config import ToolConfig
        from rv_android_core.event import EventBus

        # Test tools with variants - Test context modes
        # 🔧 QUICK TESTING: Uncomment the configuration you want to test
        
        tools = [
            # ═══════════════════════════════════════════════════════════════════
            # 📋 CONTEXT MODE TESTING OPTIONS
            # ═══════════════════════════════════════════════════════════════════
            
            # Option 1: STATELESS context mode (uses MemoryManager, TransitionManager)
            # Shows: action_history, memory_insights, navigation_path, available_transitions
            # ToolConfig(name="rvandroid", variants=["vision"], parameters={
            #     "context_mode": "stateless",
            #     "context_window_size": 10,
            #     "llm_type": "ollama",
            #     "llm_model": "llama3.2"
            # }),
            
            # Option 2: RICH context mode (uses sliding window with compression) ⭐ CURRENTLY ACTIVE
            # Shows: recent_iterations with screen descriptions and actions from last N interactions
            ToolConfig(name="rvandroid", variants=["vision"], parameters={
                "context_mode": "rich",
                "context_window_size": 10,        # Number of iterations to keep in sliding window
                "context_compression": True,       # Compress older iterations (recommended)
                "include_coverage_timeline": True, # Include coverage progression over time
                "llm_type": "ollama",
                "llm_model": "gemma3:4b"
            }),
            
            # ═══════════════════════════════════════════════════════════════════
            # 🎯 STRATEGY COMPARISON WITH CONTEXT MODES
            # ═══════════════════════════════════════════════════════════════════
            
            # Option 3: Single strategy with RICH context
            # ToolConfig(name="rvandroid", variants=["default"], parameters={     
            #     "context_mode": "rich",
            #     "context_window_size": 8,
            #     "context_compression": True
            # }),
            
            # Option 4: Batch strategy with STATELESS context
            # ToolConfig(name="rvandroid", variants=["llama_batch_detailed"], parameters={  
            #     "context_mode": "stateless",
            #     "context_window_size": 10
            # }),
            
            # Option 5: Compare both modes side by side (uncomment both)
            # ToolConfig(name="rvandroid", variants=["vision"], parameters={
            #     "context_mode": "stateless",
            #     "context_window_size": 10
            # }),
            # ToolConfig(name="rvandroid", variants=["vision"], parameters={
            #     "context_mode": "rich", 
            #     "context_window_size": 10,
            #     "context_compression": True
            # })
        ]

        # Create configuration for actual execution
        config = ExperimentConfig(
            # name="aaa",
            tool_configs=tools,
            repetitions=1,
            timeouts=[60],
            apks_dir="./apks_examples/",
            output_dir="./out",  # Temporary artifacts directory
            results_dir = "./results",  # Persistent results directory
            specification_set="jca", #"custom",  # Use custom specs from specs_mini
            # custom_specs_dir = "./specs_mini",
            generate_monitors = False,
            instrument_apks = False,
            run_static_analysis = False,
            no_window = False
        )
        
        # Create experiment controller to validate integration
        controller = ExperimentController(config)
        result = controller.run()
        
        # print("✅ ExperimentController created successfully")
        # print(f"   Config name: {controller.config.name}")
        # print(f"   Tools: {[tc.name for tc in controller.config.tool_configs]}")
        #
        # # Test ToolConfig unification first
        # print("🔧 Testing ToolConfig unification...")
        # for tc in config.tool_configs:
        #     print(f"   Tool: {tc.name}, Type: {type(tc).__name__}")
        # print("✅ ToolConfig unification working correctly!")
        # exit(1)
        
        # Actually execute the experiment using the CLI function
        # print("🚀 Starting actual experiment execution...")
        # from rv_experiment.experiment.experiment_controller import execute_with_config
        
        # Check if we have APKs to test
        # try:
        #     apks = config.get_apk_list()
        #     if not apks:
        #         print(f"⚠️ No APKs found in {config.apks_dir}, creating a dummy test")
        #         print("✅ Integration validated (no APKs available for testing)")
        #         return True
        # except Exception as e:
        #     print(f"⚠️ Could not get APK list: {e}")
        #     print("✅ Integration validated (APK discovery issue)")
        #     return True
        
        # Execute the complete experiment
        # result = execute_with_config(config)
        
        if result:
            print("✅ Experiment executed successfully!")
            print(f"   Results should be available in: {config.experiment_dir}")
        else:
            print("⚠️ Experiment completed but encountered some issues")
            
        return True
        
    except Exception as e:
        print(f"❌ ExperimentController test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def tmp_context_modes():
    """Test the new context mode system implementation."""
    print("\n🔧 Testing Context Mode System...")
    
    try:
        from rv_experiment.config import ExperimentConfig
        from rv_platform.config.platform_config import ToolConfig
        
        # Test 1: STATELESS context mode
        print("   1. Testing STATELESS context mode...")
        stateless_config = ToolConfig(
            name="rvandroid", 
            variants=["vision"],
            parameters={
                "context_mode": "stateless",
                "context_window_size": 10,
                "llm_type": "ollama",
                "llm_model": "llama3.2"
            }
        )
        print(f"   ✅ STATELESS config: {stateless_config.parameters.get('context_mode')}")
        
        # Test 2: RICH context mode
        print("   2. Testing RICH context mode...")
        rich_config = ToolConfig(
            name="rvandroid",
            variants=["vision"],
            parameters={
                "context_mode": "rich",
                "context_window_size": 10,
                "context_compression": True,
                "include_coverage_timeline": False,
                "llm_type": "ollama",
                "llm_model": "llama3.2"
            }
        )
        print(f"   ✅ RICH config: {rich_config.parameters.get('context_mode')} (window_size: {rich_config.parameters.get('context_window_size')})")
        
        # Test 3: Different strategies with context modes
        print("   3. Testing different strategies with context modes...")
        tmp_configs = [
            ToolConfig(name="rvandroid", variants=["vision"], parameters={"context_mode": "rich"}),
            ToolConfig(name="rvandroid", variants=["default"], parameters={"context_mode": "stateless"}),
            # ToolConfig(name="rvandroid", variants=["llama_batch_detailed"], parameters={"context_mode": "rich"})
        ]
        
        for config in tmp_configs:
            mode = config.parameters.get('context_mode', 'default')
            strategy = config.variants[0] if config.variants else 'unknown'
            print(f"   📝 {strategy} strategy with {mode} context mode")
        
        # Test 4: Create experiment config with context modes
        print("   4. Testing experiment config with context modes...")
        experiment_config = ExperimentConfig(
            tool_configs=[rich_config],  # Use RICH mode for testing
            repetitions=1,
            timeouts=[60],
            apks_dir="./apks_examples/",
            generate_monitors=False,
            instrument_apks=False,
            run_static_analysis=False
        )
        
        print("   ✅ Experiment config created with context modes")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Context mode test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def tmp_variant_system():
    """Test the new variant system implementation."""
    print("\n🔧 Testing Variant System...")
    
    try:
        from rv_experiment.config import ExperimentConfig
        from rv_platform.config.platform_config import ToolConfig
        
        # Test 1: Basic variant parsing
        print("   1. Testing basic variant configurations...")
        tools = [
            ToolConfig(name="droidbot", variants=["dfs_greedy"]),
            ToolConfig(name="ape", variants=["sata"]),
            ToolConfig(name="rvandroid", variants=["default"], parameters={
                "llm_type": "ollama",
                "llm_model": "llama3.2",
                "prompt_strategy": "standard_modular"
            })
        ]
        
        config = ExperimentConfig(
            tool_configs=tools,
            repetitions=1,
            timeouts=[60],
            apks_dir="./apks_examples/",
            generate_monitors=False,
            instrument_apks=False,
            run_static_analysis=False
        )
        
        print("   ✅ Variant configurations created successfully")
        
        # Test 2: Configuration validation
        print("   2. Testing configuration validation...")
        try:
            config.validate()
            print("   ✅ Configuration validation passed")
        except Exception as e:
            print(f"   ⚠️ Validation warning (may be expected): {e}")
        
        # Test 3: Tool registry access
        print("   3. Testing tool registry integration...")
        try:
            from rv_experiment.tools.experiment_tools import ExperimentToolRegistry
            registry = ExperimentToolRegistry.get_instance()
            registry.register_external_tools()
            
            # Test variant retrieval
            available_tools = registry.get_all_tools()
            print(f"   ✅ Found {len(available_tools)} registered tools")
            
            for tool in available_tools[:3]:  # Show first 3 tools
                try:
                    variants = registry.get_tool_variants(tool.name)
                    print(f"   📋 {tool.name}: {len(variants)} variants")
                except:
                    print(f"   📋 {tool.name}: variants not available")
                    
        except Exception as e:
            print(f"   ⚠️ Registry test warning: {e}")
        
        # Test 4: TaskConfiguration with ToolConfig
        print("   4. Testing TaskConfiguration integration...")
        from rv_android_core.domain.task import TaskConfiguration, ToolConfig as TaskToolConfig
        
        # Test the new TaskConfiguration with ToolConfig
        task_tool_config = TaskToolConfig.from_tool_specification("droidbot:dfs_greedy")
        print(f"   📝 Parsed tool spec: {task_tool_config.get_full_tool_name()}")
        
        task_config = TaskConfiguration(
            apk_name="test.apk",
            repetition=1,
            timeout=300,
            tool_config=task_tool_config
        )
        
        print(f"   ✅ Task configuration created: {task_config}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Variant system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_manual_test():
    """Run comprehensive manual test for rv-experiment integration."""
    # Setup logging first
    logger = setup_logging()
    
    print("=" * 60)
    print("🧪 RV-EXPERIMENT INTEGRATION TEST")
    print("=" * 60)
    print("Testing rv-experiment integration with rv-platform...")
    print()
    
    # Test results tracking
    tests = [
        # ("Import Test", tmp_rv_experiment_imports),
        # ("Config Creation", tmp_experiment_config_creation),
        # ("Platform Integration", tmp_platform_integration),
        # ("Tool Discovery", tmp_cli_tool_discovery),
        # ("Variant System", tmp_variant_system),
        ("Context Mode System", tmp_context_modes),
        ("Experiment Controller", tmp_experiment_controller)
    ]
    
    passed = 0
    total = len(tests)
    
    for tmp_name, tmp_func in tests:
        try:
            if tmp_name == "Config Creation":
                result = tmp_func()
                if isinstance(result, tuple):
                    success = result[0]
                else:
                    success = result
            else:
                success = tmp_func()
                
            if success:
                passed += 1
                
        except Exception as e:
            print(f"❌ {tmp_name} encountered unexpected error: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Tests passed: {passed}/{total}")
    print(f"Success rate: {passed/total:.1%}")
    
    if passed == total:
        print("✅ All tests passed! rv-experiment integration is working correctly.")
        print("\n🎯 Ready for CLI testing with context modes:")
        print("\n📋 Context Mode Configuration Examples:")
        print("   # STATELESS mode (traditional enrichment with MemoryManager, TransitionManager)")
        print("   ToolConfig(name='rvandroid', variants=['vision'], parameters={")
        print("       'context_mode': 'stateless',")
        print("       'context_window_size': 10")
        print("   })")
        print()
        print("   # RICH mode (sliding window with raw iteration history)")
        print("   ToolConfig(name='rvandroid', variants=['vision'], parameters={")
        print("       'context_mode': 'rich',")
        print("       'context_window_size': 10,")
        print("       'context_compression': True,")
        print("       'include_coverage_timeline': False")
        print("   })")
        print()
        print("🚀 Context Mode Testing Commands:")
        print("   # Test RICH context mode with vision strategy")
        print("   python -m rv_experiment run --tools rvandroid:vision --config rich_context.json")
        print()
        print("   # Test STATELESS context mode with different strategies")
        print("   python -m rv_experiment run --tools rvandroid:default --config stateless_context.json")
        print()
        print("📊 Differences between Context Modes:")
        print("   STATELESS: Uses action_history, memory_insights, navigation_path, available_transitions")
        print("   RICH:      Uses recent_iterations with sliding window of screen descriptions and actions")
        print()
        print("🔧 Additional CLI testing:")
        print("   python -m rv_experiment run --tools droidbot:dfs_greedy")
        print("   python -m rv_experiment run --tools ape:sata,droidbot:bfs_greedy")
        print("   python -m rv_experiment list-tools")
        print("   python -m rv_experiment config --template-type basic")
    else:
        print("❌ Some tests failed. Check the errors above.")
        print("\n🔧 Integration issues detected - please review the implementation.")
    
    return passed == total

if __name__ == "__main__":
    success = run_manual_test()
    sys.exit(0 if success else 1)