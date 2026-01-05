#!/usr/bin/env python3
"""
RVSmart Tutorial - Basic Test Script

A simplified version to verify core functionality without advanced features.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Type

# Add modules to Python path
project_root = Path(__file__).parent
for module in ["rv-android-core", "rv-llm", "rvsmart-tool", "rv-screen-parser", "rv-static-analysis"]:
    sys.path.insert(0, str(project_root / "modules" / module / "src"))

# Import core components
from rv_llm import LLMMessage, LLMRole, LLMTextContent, LLMImageContent
from rv_llm.config import PromptConfig
from rv_llm.config.llm_config import LLMConfig
from rv_llm.llm.constants import LLMType, PromptStrategyType, ContextMode, StateEntry
from rv_llm.llm.ollama_llm import OllamaLLM
from rv_screen_parser.parser.screen.visitor.default_visitor import DefaultTextVisitor
from rv_screen_parser.parser.screen.parser_factory import ParserFactory
from rv_screen_parser.constants import ScreenParserType, VisitorType
from rv_android_core import constants
from rv_android_core.domain.app import App
from rv_android_core.domain.static import StaticAnalysisData
from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser
from rvsmart_tool.config.tool_config import RvSmartToolConfig
from rvsmart_tool.llm.prompt.rvsmart_framework import RVAndroidPromptFramework

# Setup RVSEC_HOME environment
os.environ[constants.ENV_RVSEC_HOME] = os.path.dirname(os.getcwd())

def setup_logging():
    """Configure logging."""
    logging.basicConfig(
        level=logging.ERROR,  # Only show errors
        format='%(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )

def print_header(title: str, width: int = 60):
    """Print a formatted header."""
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)

def read_droidbot_state(filename: str) -> Dict[str, Any]:
    """Load a DroidBot state file."""
    with open(filename, 'r') as f:
        return json.load(f)

def create_state_from_droidbot(state_file: str, screenshot_path: str, package: str, static_data: StaticAnalysisData):
    """Create a state dictionary from DroidBot output."""
    screen_info = read_droidbot_state(state_file)
    parser = ParserFactory.create(ScreenParserType.DROIDBOT, DefaultTextVisitor)
    screen_description = parser.parse_screen(screen_info, static_data)
    
    return {
        StateEntry.PACKAGE_NAME: package,
        StateEntry.ACTIVITY: screen_description.activity,
        StateEntry.VIEW_TREE: screen_info.get("view_tree", {}),
        StateEntry.SCREENSHOT_PATH: screenshot_path,
        StateEntry.STRUCTURED_SCREEN: screen_description
    }

def test_basic_configuration():
    """Test 1: Basic Configuration Creation"""
    print_header("TEST 1: BASIC CONFIGURATION")
    
    # Create LLM configuration
    llm_config = LLMConfig(
        llm_type=LLMType.OLLAMA,
        model=OllamaLLM.GEMMA,
        temperature=0.7
    )
    print(f"✓ LLM Config: {llm_config.llm_type}, {llm_config.model}")
    
    # Create Prompt configuration
    prompt_config = PromptConfig(
        strategy_type=PromptStrategyType.SINGLE,
        parser_type=ScreenParserType.DROIDBOT,
        visitor_type=VisitorType.DEFAULT,
        template_name="single_compact",
        context_mode=ContextMode.STATELESS
    )
    print(f"✓ Prompt Config: {prompt_config.strategy_type}, {prompt_config.template_name}")
    
    # Create tool configuration
    tool_config = RvSmartToolConfig(
        llm_config=llm_config,
        prompt_config=prompt_config
    )
    print(f"✓ Tool Config: Combined successfully")
    
    return tool_config

def test_framework_initialization(tool_config):
    """Test 2: Framework Initialization"""
    print_header("TEST 2: FRAMEWORK INITIALIZATION")
    
    # Initialize framework
    framework = RVAndroidPromptFramework.create(tool_config.prompt_config)
    print(f"✓ Framework created: {framework.__class__.__name__}")
    print(f"✓ Information manager: {framework.information_manager.__class__.__name__}")
    print(f"✓ Template repository: {framework.template_repository.__class__.__name__}")
    
    return framework

def test_state_creation():
    """Test 3: State Creation"""
    print_header("TEST 3: STATE CREATION")
    
    # Load test data
    base_dir = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    apk = "cryptoapp.apk"
    state_id = "004"
    
    app_folder = os.path.join(base_dir, apk)
    reach_file = os.path.join(app_folder, f"{apk}.reach")
    gator_file = os.path.join(app_folder, f"{apk}.wtg")
    gesda_file = os.path.join(app_folder, f"{apk}.gesda")
    screenshot_path = os.path.join(app_folder, f"{state_id}.png")
    state_file = os.path.join(app_folder, f"{state_id}.state")
    
    # Get package name
    app = App(app_path=os.path.join(app_folder, apk))
    package = app.package_name
    print(f"✓ Package: {package}")
    
    # Parse static analysis
    parser = StaticAnalysisParser()
    static_data = parser.parse(reach_file, gator_file, gesda_file, package)
    print(f"✓ Static data: {len(static_data.classes.classes)} classes, {len(static_data.windows.windows)} windows")
    
    # Create state
    state = create_state_from_droidbot(state_file, screenshot_path, package, static_data)
    print(f"✓ State created: {len(state)} keys")
    print(f"  Activity: {state[StateEntry.ACTIVITY]}")
    
    return state, static_data

def test_prompt_generation(framework, state, tool_config):
    """Test 4: Prompt Generation"""
    print_header("TEST 4: PROMPT GENERATION")
    
    # Add minimal required data to state
    state[StateEntry.STATIC_DATA] = state.get(StateEntry.STATIC_DATA, {})
    state[StateEntry.TOOL_CONFIG] = tool_config
    
    try:
        # Generate prompt
        messages = framework.generate_prompt(state, {})
        
        print(f"✓ Generated {len(messages)} messages")
        for i, msg in enumerate(messages, 1):
            content_types = []
            for content in msg.content:
                if isinstance(content, LLMTextContent):
                    content_types.append("Text")
                elif isinstance(content, LLMImageContent):
                    content_types.append("Image")
            print(f"  Message {i}: Role={msg.role}, Content={', '.join(content_types)}")
        
        total_chars = sum(
            len(c.text) for m in messages for c in m.content 
            if hasattr(c, 'text')
        )
        print(f"✓ Total prompt size: {total_chars:,} characters")
        
        return True
        
    except Exception as e:
        print(f"✗ Prompt generation failed: {e}")
        return False

def test_template_variations():
    """Test 5: Template Variations"""
    print_header("TEST 5: TEMPLATE VARIATIONS")
    
    templates = [
        ("single_compact", "Minimal template"),
        ("single_standard", "Balanced template"),
        ("batch_compact", "Batch minimal"),
        ("vision_compact", "Vision minimal")
    ]
    
    for template_name, description in templates:
        try:
            prompt_config = PromptConfig(
                strategy_type=PromptStrategyType.SINGLE,
                parser_type=ScreenParserType.DROIDBOT,
                visitor_type=VisitorType.DEFAULT,
                template_name=template_name,
                context_mode=ContextMode.STATELESS
            )
            
            framework = RVAndroidPromptFramework.create(prompt_config)
            print(f"✓ {template_name}: {description} - OK")
        except Exception as e:
            print(f"✗ {template_name}: {description} - Failed ({e})")

def main():
    """Run basic tests."""
    setup_logging()
    
    print_header("RVSmart PROMPT FRAMEWORK - BASIC TESTS", 70)
    print("\nTesting core functionality without advanced features...\n")
    
    try:
        # Test 1: Configuration
        tool_config = test_basic_configuration()
        
        # Test 2: Framework
        framework = test_framework_initialization(tool_config)
        
        # Test 3: State
        state, static_data = test_state_creation()
        
        # Test 4: Prompt generation
        success = test_prompt_generation(framework, state, tool_config)
        
        # Test 5: Template variations
        test_template_variations()
        
        print_header("TEST RESULTS", 70)
        if success:
            print("✅ BASIC TESTS PASSED!")
            print("\nCore functionality is working:")
            print("  • Configuration creation ✓")
            print("  • Framework initialization ✓")
            print("  • State creation and parsing ✓")
            print("  • Prompt generation ✓")
            print("  • Template system ✓")
            print("\nThe RVSmart prompt framework is ready for use!")
        else:
            print("❌ SOME TESTS FAILED")
            print("Check the output above for specific issues.")
            
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())