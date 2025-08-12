#!/usr/bin/env python3
"""
Quick variant system verification test.

This is a simple, fast test to verify that the basic variant system
functionality is working without requiring complex setup or mocking.
Ideal for quick validation during development.
"""

def test_basic_variant_parsing():
    """Quick test of basic variant parsing functionality."""
    from rv_android_core.domain.task import ToolConfig
    
    # Test 1: Basic tool specification parsing
    tool_config = ToolConfig.from_tool_specification("droidbot")
    assert tool_config.tool_name == "droidbot"
    assert tool_config.variant == "default"
    assert tool_config.get_full_tool_name() == "droidbot"
    print("✅ Basic tool parsing works")
    
    # Test 2: Tool with variant parsing
    tool_config = ToolConfig.from_tool_specification("droidbot:dfs_greedy")
    assert tool_config.tool_name == "droidbot"
    assert tool_config.variant == "dfs_greedy" 
    assert tool_config.get_full_tool_name() == "droidbot:dfs_greedy"
    print("✅ Variant parsing works")
    
    # Test 3: Tool with parameters
    tool_config = ToolConfig.from_tool_specification("rvandroid:custom", {"temp": 0.1})
    assert tool_config.tool_name == "rvandroid"
    assert tool_config.variant == "custom"
    assert tool_config.additional_params["temp"] == 0.1
    print("✅ Parameter parsing works")


def test_task_configuration_integration():
    """Quick test of TaskConfiguration integration."""
    from rv_android_core.domain.task import TaskConfiguration, ToolConfig
    
    # Test 1: New format with ToolConfig
    tool_config = ToolConfig.from_tool_specification("droidbot:dfs_greedy")
    task_config = TaskConfiguration(
        apk_name="test.apk",
        repetition=1,
        timeout=300,
        tool_config=tool_config
    )
    
    assert "droidbot:dfs_greedy" in str(task_config)
    print("✅ TaskConfiguration integration works")
    
    # Test 2: Serialization
    data = task_config.to_dict()
    assert data["tool_config"]["tool_name"] == "droidbot"
    assert data["tool_config"]["variant"] == "dfs_greedy"
    print("✅ TaskConfiguration serialization works")
    
    # Test 3: Deserialization
    restored = TaskConfiguration.from_dict(data)
    assert restored.tool_config.tool_name == "droidbot"
    assert restored.tool_config.variant == "dfs_greedy"
    print("✅ TaskConfiguration deserialization works")
    
    # Test 4: Legacy compatibility
    legacy_data = {
        "apk_name": "test.apk",
        "repetition": 1,
        "timeout": 300,
        "tool_name": "ape"  # Legacy format
    }
    
    legacy_config = TaskConfiguration.from_dict(legacy_data)
    assert legacy_config.tool_config.tool_name == "ape"
    assert legacy_config.tool_config.variant == "default"
    print("✅ Legacy compatibility works")


def test_experiment_config_basic():
    """Quick test of ExperimentConfig with variants."""
    import tempfile
    from pathlib import Path
    from rv_platform.config.platform_config import ToolConfig
    from rv_experiment.config import ExperimentConfig
    
    # Create tools with variants
    tools = [
        ToolConfig(name="droidbot", variants=["dfs_greedy"]),
        ToolConfig(name="ape", variants=["sata"]),
        ToolConfig(name="rvandroid", variants=["default"], parameters={
            "llm_type": "ollama",
            "llm_model": "llama3.2"
        })
    ]
    
    # Create config with temp directory
    with tempfile.TemporaryDirectory() as temp_dir:
        config = ExperimentConfig(
            tool_configs=tools,
            repetitions=1,
            timeouts=[60],
            apks_dir=temp_dir,
            generate_monitors=False,
            instrument_apks=False,
            run_static_analysis=False
        )
        
        assert len(config.tool_configs) == 3
        assert config.tool_configs[0].name == "droidbot"
        assert "dfs_greedy" in config.tool_configs[0].variants
        print("✅ ExperimentConfig with variants works")


def test_constants_available():
    """Quick test that variant constants are available."""
    from rv_android_core.constants import DEFAULT_VARIANT_NAME, VARIANT_SEPARATOR, TASK_ID_SEPARATOR
    
    assert DEFAULT_VARIANT_NAME == "default"
    assert VARIANT_SEPARATOR == ":"
    assert TASK_ID_SEPARATOR == "__"
    print("✅ Variant constants available")


def test_llm_constants_available():
    """Quick test that LLM constants are available."""
    try:
        from rv_llm.llm.constants import LLMType, PromptStrategyType
        
        assert hasattr(LLMType, 'OLLAMA')
        assert hasattr(LLMType, 'HUGGINGFACE')
        assert hasattr(PromptStrategyType, 'STANDARD')
        assert hasattr(PromptStrategyType, 'BATCH_ACTION')
        print("✅ LLM constants available")
    except ImportError:
        print("⚠️ LLM constants not available (module may not be installed)")


def test_screen_parser_constants_available():
    """Quick test that screen parser constants are available."""
    try:
        from rv_screen_parser.constants import ScreenParserType, VisitorType
        
        assert hasattr(ScreenParserType, 'DROIDBOT')
        assert hasattr(VisitorType, 'DETAILED')
        print("✅ Screen parser constants available")
    except ImportError:
        print("⚠️ Screen parser constants not available (module may not be installed)")


def run_quick_tests():
    """Run all quick tests and report results."""
    print("🚀 Running Quick Variant System Tests")
    print("=" * 50)
    
    tests = [
        ("Basic Variant Parsing", test_basic_variant_parsing),
        ("TaskConfiguration Integration", test_task_configuration_integration),
        ("ExperimentConfig Basic", test_experiment_config_basic),
        ("Constants Available", test_constants_available),
        ("LLM Constants", test_llm_constants_available),
        ("Screen Parser Constants", test_screen_parser_constants_available)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 {test_name}:")
            test_func()
            passed += 1
            print(f"✅ {test_name} - PASSED")
        except Exception as e:
            print(f"❌ {test_name} - FAILED: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed ({passed/total:.1%})")
    
    if passed == total:
        print("🎉 All quick tests passed! Variant system is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the errors above.")
    
    return passed == total


if __name__ == "__main__":
    import sys
    success = run_quick_tests()
    sys.exit(0 if success else 1)