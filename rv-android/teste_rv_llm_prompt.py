#!/usr/bin/env python3
"""
Manual test for prompt generation with template architecture.

This test validates that the prompt generation system works correctly with:
- Templates in rvandroid-tool
- RvAndroidToolConfig for parser/visitor configuration
- Template registration with PromptFramework
- Clean LLMConfig integration
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Type

from rv_llm import LLMMessage, LLMRole, LLMTextContent, LLMImageContent
from rv_llm.config import PromptConfig
from rv_screen_parser.parser.screen.visitor.abstract_visitor import AbstractScreenVisitor
from rv_screen_parser.parser.screen.visitor.default_visitor import DefaultTextVisitor
from rvandroid_tool.config.tool_config import RvAndroidToolConfig
from rvandroid_tool.llm.prompt import RVAndroidPromptFramework

# Add the modules to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "modules" / "rv-android-core" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-llm" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rvandroid-tool" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-screen-parser" / "src"))

# Import constants after path setup
from rv_screen_parser.parser.screen.visitor.basic_visitor import BasicTextVisitor
from rv_screen_parser.parser.screen.parser_factory import ParserFactory
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription
from rv_llm.llm.constants import StateEntry
from rv_android_core import constants
from rv_android_core.domain.app import App
from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser
from rv_llm.llm.prompt.framework import PromptFramework
from rv_screen_parser.constants import ScreenParserType, VisitorType
from rv_llm.config.llm_config import LLMConfig
from rv_llm.llm.constants import LLMType, PromptStrategyType, ContextMode
from rv_llm.llm.ollama_llm import OllamaLLM
from rv_android_core.domain.static import StaticAnalysisData
from rvandroid_tool.llm.service.memory_manager import MemoryManager
from rvandroid_tool.llm.service.transition_manager import TransitionManager
from rvandroid_tool.llm.service.action_service import LLMActionService

# Setup RVSEC_HOME before importing modules
current_directory = os.getcwd()
parent_directory = os.path.dirname(current_directory)
os.environ[constants.ENV_RVSEC_HOME] = parent_directory


def setup_logging(debug: bool = True):
    """Set up logging configuration."""
    from rv_android_core.util.logging.manager import LoggingManager

    # Setup basic logging first
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )

    # Silence noisy third-party loggers
    for noisy_logger in ["androguard", "matplotlib", "PIL", "requests", "urllib3"]:
        logging.getLogger(noisy_logger).setLevel(logging.ERROR)

    for noisy_logger in ["rvandroid_core.domain.window", "rvandroid_core.domain.widget", "rv_static_analysis.parser.static", "rvandroid_core.domain.classes"
                         "rv_android_core.util.utils.read_json"]:
        logging.getLogger(noisy_logger).setLevel(logging.INFO)

    # Get the logging manager
    logging_manager = LoggingManager.get_instance()
    logging_manager.configure_output(
        console=True,
        file=False,
        console_level=10 if debug else 20,
        file_level=10,
        json_format=False
    )

    return logging_manager.get_logger('teste_rv_llm_prompt')


def read_droidbot_state(filename: str) -> Dict[str, Any]:
    """Loads a DroidBot state file."""
    with open(filename, 'r') as file:
        return json.load(file)


def enrich_state(state, static_data: StaticAnalysisData, config: RvAndroidToolConfig):
    memory_manager = MemoryManager(static_data=static_data)
    transition_manager = TransitionManager(static_data=static_data)
    llm_service = LLMActionService(
        static_data=static_data,
        tool_config=config
    )

    # Override service's managers with our instances for testing
    llm_service.memory_manager = memory_manager
    llm_service.transition_manager = transition_manager

    llm_service._pre_process_state(state)
    return state


def create_state_from_droidbot_state(droidbot_state_file: str, screenshot_path: str, package: str,
                                     static_data: StaticAnalysisData, visitor: Type[AbstractScreenVisitor]):
    screen_info = read_droidbot_state(droidbot_state_file)
    parser = ParserFactory.create(ScreenParserType.DROIDBOT, visitor)
    screen_description: ScreenDescription = parser.parse_screen(screen_info, static_data)
    state = {
        StateEntry.PACKAGE_NAME: package,
        StateEntry.ACTIVITY: screen_description.activity,
        StateEntry.VIEW_TREE: screen_info[StateEntry.VIEW_TREE],
        StateEntry.SCREENSHOT_PATH: screenshot_path,
        StateEntry.STRUCTURED_SCREEN: screen_description
    }
    return state


def create_mock_iterations():
    """Create mock iteration data for rich context testing."""
    return [
        {
            'activity': 'MainActivity',
            'actions_generated': [
                {'explanation': 'clicked login button to access authentication'},
                {'explanation': 'filled username field with test data'}
            ],
            'coverage_metrics': {
                'method_coverage': 15.5,
                'mop_method_coverage': 8.2,
                'unique_errors': 0
            },
            'mop_errors': []
        },
        {
            'activity': 'LoginActivity',
            'actions_generated': [
                {'explanation': 'entered password in secure field'},
                {'explanation': 'submitted login form [M]'},
                {'explanation': 'verified authentication result'}
            ],
            'coverage_metrics': {
                'method_coverage': 28.7,
                'mop_method_coverage': 12.1,
                'unique_errors': 0
            },
            'mop_errors': []
        },
        {
            'activity': 'DashboardActivity',
            'actions_generated': [
                {'explanation': 'navigated to settings menu [M]'}
            ],
            'coverage_metrics': {
                'method_coverage': 35.2,
                'mop_method_coverage': 18.5,
                'unique_errors': 1
            },
            'mop_errors': [
                {'spec': 'NetworkSpec', 'method': 'sendData', 'message': 'Unencrypted transmission detected'}
            ]
        },
        {
            'activity': 'SettingsActivity',
            'actions_generated': [
                {'explanation': 'opened encryption settings [DM]'},
                {'explanation': 'modified cipher configuration [DM]'}
            ],
            'coverage_metrics': {
                'method_coverage': 42.8,
                'mop_method_coverage': 25.3,
                'unique_errors': 2
            },
            'mop_errors': [
                {'spec': 'CryptoSpec', 'method': 'createCipher', 'message': 'Weak cipher algorithm used'}
            ]
        }
    ]


def tmp_context_mode(droidbot_state_file, screenshot_path, package, static_data, context_mode: str):
    """Test prompt generation with specific context mode."""
    print(f"\n{'='*60}")
    print(f"🧪 TESTING CONTEXT MODE: {context_mode}")
    print(f"{'='*60}")
    
    llm_config = LLMConfig(
        llm_type=LLMType.OLLAMA,
        model=OllamaLLM.GEMMA,
        vision=True,
        temperature=0.3,
        max_tokens=800
    )
    
    # Create prompt config with context mode settings
    prompt_config = PromptConfig(
        strategy_type=PromptStrategyType.VISION,
        parser_type=ScreenParserType.DROIDBOT,
        visitor_type=VisitorType.DEFAULT,
        max_context_length=8192,
        # Context mode configuration
        context_mode=context_mode,
        context_window_size=5,
        context_compression=True,
        include_coverage_timeline=True
    )
    
    tool_config = RvAndroidToolConfig(
        llm_config=llm_config,
        prompt_config=prompt_config
    )

    basic_state = create_state_from_droidbot_state(droidbot_state_file, screenshot_path, package, static_data, DefaultTextVisitor)
    
    # Add mock iterations for rich context testing
    if context_mode == ContextMode.RICH:
        basic_state[StateEntry.RECENT_ITERATIONS] = create_mock_iterations()
        # Add some coverage metrics for testing
        basic_state[StateEntry.COVERAGE_METRICS] = {
            'method_coverage': 42.8,
            'activity_coverage': 75.0,
            'mop_method_coverage': 25.3,
            'unique_errors': 2
        }
        basic_state[StateEntry.MOP_RECENT_ERRORS] = [
            {
                'spec': 'CryptoSpec',
                'class_full_name': 'com.example.crypto.CipherManager',
                'method': 'createCipher',
                'message': 'Weak cipher algorithm used',
                'detected_at': '2025-08-18T10:30:00'
            }
        ]
    
    state = enrich_state(basic_state, static_data, tool_config)

    setup_logging(True)

    framework = RVAndroidPromptFramework.create(prompt_config)

    prompt = framework.generate_prompt(state)
    
    # Print context mode info
    print(f"📋 Context Mode: {context_mode}")
    print(f"📊 State keys: {list(state.keys())}")
    if context_mode == ContextMode.RICH:
        print(f"🔄 Recent iterations: {len(state.get(StateEntry.RECENT_ITERATIONS, []))}")
        print(f"📈 Coverage metrics: {bool(state.get(StateEntry.COVERAGE_METRICS))}")
        print(f"⚠️  MOP errors: {len(state.get(StateEntry.MOP_RECENT_ERRORS, []))}")
    
    print(f"\n🔍 Generated prompt: {len(prompt)} messages")
    
    for i, msg in enumerate(prompt):
        print(f"\n{'─'*40}")
        print(f"MESSAGE {i+1}: {msg.role} ({len(msg.content)} content items)")
        print(f"{'─'*40}")
        
        for j, content in enumerate(msg.content):
            if isinstance(content, LLMTextContent):
                print(f"[TEXT: {content.text}]")
                # # Show first and last few lines of text content
                # lines = content.text.strip().split('\n')
                # if len(lines) <= 10:
                #     print(content.text)
                # else:
                #     print('\n'.join(lines[:5]))
                #     print(f"\n... [{len(lines) - 10} lines omitted] ...\n")
                #     print('\n'.join(lines[-5:]))
            elif isinstance(content, LLMImageContent):
                print(f"[IMAGE: {content.url}]")
            else:
                print(f"[CONTENT: {type(content)}]")
    
    return prompt


def tmp_both_context_modes(droidbot_state_file, screenshot_path, package, static_data):
    """Test both STATELESS and RICH context modes."""
    print("🚀 CONTEXT MODE COMPARISON TEST")
    print("Testing Vision strategy with both context modes\n")
    
    # Test STATELESS mode (default)
    stateless_prompt = tmp_context_mode(
        droidbot_state_file, screenshot_path, package, static_data,
        ContextMode.STATELESS
    )
    
    # Test RICH mode  
    rich_prompt = tmp_context_mode(
        droidbot_state_file, screenshot_path, package, static_data,
        ContextMode.RICH
    )
    
    # Compare results
    print(f"\n{'='*60}")
    print("📊 COMPARISON SUMMARY")
    print(f"{'='*60}")
    print(f"STATELESS mode:")
    print(f"  • Messages: {len(stateless_prompt)}")
    print(f"  • Total content items: {sum(len(msg.content) for msg in stateless_prompt)}")
    
    print(f"\nRICH mode:")
    print(f"  • Messages: {len(rich_prompt)}")
    print(f"  • Total content items: {sum(len(msg.content) for msg in rich_prompt)}")
    
    # Calculate text length difference
    stateless_text = ""
    rich_text = ""
    
    for msg in stateless_prompt:
        for content in msg.content:
            if isinstance(content, LLMTextContent):
                stateless_text += content.text
                
    for msg in rich_prompt:
        for content in msg.content:
            if isinstance(content, LLMTextContent):
                rich_text += content.text
    
    print(f"\nText length comparison:")
    print(f"  • STATELESS: {len(stateless_text)} characters")
    print(f"  • RICH: {len(rich_text)} characters")
    print(f"  • Difference: {len(rich_text) - len(stateless_text):+d} characters")
    
    if len(rich_text) > len(stateless_text):
        print("  ✅ RICH mode provides additional context as expected")
    else:
        print("  ⚠️  RICH mode has similar or less content")
    
    return stateless_prompt, rich_prompt

def save_prompt(prompt: list[LLMMessage], out_dir, prefix):
    for message in prompt:
        text = ""
        image = ""
        for content in message.content:
            if isinstance(content, LLMTextContent):
                text += content.text
            elif isinstance(content, LLMImageContent):
                image += content.encoded_string

        if LLMRole.USER == message.role:
            suffix = "_user.txt"
        else: # LLMRole.SYSTEM == message.role:
            suffix = "_system.txt"

        with open(os.path.join(out_dir, prefix + suffix)  , "w") as file:
            file.write(text)

        if image:
            with open(os.path.join(out_dir, prefix + "_image.txt")  , "w") as file:
                file.write(image)


if __name__ == '__main__':
    # setup_logging(True)

    # Hardcoded test configuration - easy to modify for different tests
    screenshots_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    apk = "cryptoapp.apk"
    prefix = "009"  # Options: 001, 009, 015 - change this to test different states
    
    # Test mode selection - change this to test different scenarios
    TEST_MODE = "STATELESS"  # Options: "STATELESS", "RICH", "BOTH"
    
    # File paths (hardcoded for easy testing)
    app_folder = os.path.join(screenshots_folder, apk)
    reach_file = os.path.join(app_folder, apk + ".reach")
    gator_file = os.path.join(app_folder, apk + ".wtg")
    gesda_file = os.path.join(app_folder, apk + ".gesda")
    screenshot_path = os.path.join(app_folder, prefix + ".png")
    droidbot_state_file = os.path.join(app_folder, prefix + ".state")
    app = App(app_path=os.path.join(app_folder, apk))
    package = app.package_name

    # Parse static analysis data
    static_analysis_parser = StaticAnalysisParser()
    static_data = static_analysis_parser.parse(reach_file, gator_file, gesda_file, package)

    print(f"🎯 CONTEXT MODE TEST CONFIGURATION:")
    print(f"  • APK: {apk}")
    print(f"  • State: {prefix}")
    print(f"  • Package: {package}")
    print(f"  • Test Mode: {TEST_MODE}")
    print(f"  • Screenshot: {screenshot_path}")
    print(f"  • State file: {droidbot_state_file}")

    # Run tests based on mode
    if TEST_MODE == "BOTH":
        stateless_prompt, rich_prompt = tmp_both_context_modes(
            droidbot_state_file, screenshot_path, package, static_data
        )
        
        # Save prompts for comparison (uncomment to enable)
        # outdir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-evaluator/src/rv_evaluator/prompts"
        # save_prompt(stateless_prompt, outdir, f"{prefix}_stateless")
        # save_prompt(rich_prompt, outdir, f"{prefix}_rich")
        
    elif TEST_MODE == "STATELESS":
        prompt = tmp_context_mode(
            droidbot_state_file, screenshot_path, package, static_data,
            ContextMode.STATELESS
        )
        
    elif TEST_MODE == "RICH":
        prompt = tmp_context_mode(
            droidbot_state_file, screenshot_path, package, static_data,
            ContextMode.RICH
        )
        
    else:
        print(f"❌ Invalid TEST_MODE: {TEST_MODE}")
        print("Valid options: STATELESS, RICH, BOTH")
        
    print("\n🎉 Context mode testing completed!")
    print("💡 TIP: Modify TEST_MODE, apk, or prefix variables to test different scenarios")
